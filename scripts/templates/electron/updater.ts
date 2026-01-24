/**
 * Universal Auto-Updater for Electron + GitHub Releases
 *
 * Features:
 * - Retry with exponential backoff (3 attempts, 1s/2s/4s delays)
 * - Configurable timeouts (optimized for large files)
 * - Redirect limit protection (max 5)
 * - Full SemVer comparison (alpha, beta, rc, stable)
 * - YML structure validation
 * - Activity timeout detection (retry if stalled)
 * - Structured logging with timestamps
 * - User-friendly error messages (Polish)
 * - SHA512 checksum verification
 *
 * Usage:
 * 1. Copy this file and updater.config.ts to your electron/ folder
 * 2. Edit updater.config.ts with your project settings
 * 3. Import and use in main.ts
 *
 * @author Blumy
 * @license MIT
 */
import { app, BrowserWindow } from 'electron';
import { createWriteStream, existsSync, unlinkSync, readdirSync, statSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';
import { createHash } from 'crypto';
import { spawn } from 'child_process';
import * as https from 'https';
import * as http from 'http';
import { updaterConfig, getYmlUrl, getDownloadUrl, UpdaterConfig } from './updater.config';

// ============================================================================
// Types
// ============================================================================

export interface UpdateFile {
  url: string;
  sha512: string;
  size: number;
}

export interface UpdateInfo {
  version: string;
  files: UpdateFile[];
  path: string;
  sha512: string;
  releaseDate: string;
}

export interface UpdateCheckResult {
  updateAvailable: boolean;
  currentVersion: string;
  latestVersion: string;
  updateInfo: UpdateInfo | null;
  error?: string;
}

export type UpdateChannel = 'stable' | 'beta';

// ============================================================================
// Logging
// ============================================================================

type LogLevel = 'info' | 'warn' | 'error' | 'debug';

function log(level: LogLevel, message: string, data?: unknown): void {
  const timestamp = new Date().toISOString();
  const prefix = `[Updater ${timestamp}]`;

  switch (level) {
    case 'error':
      console.error(prefix, message, data ?? '');
      break;
    case 'warn':
      console.warn(prefix, message, data ?? '');
      break;
    case 'debug':
      if (process.env.NODE_ENV === 'development') {
        console.log(prefix, '[DEBUG]', message, data ?? '');
      }
      break;
    default:
      console.log(prefix, message, data ?? '');
  }
}

// ============================================================================
// Error Handling
// ============================================================================

export class UpdaterError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly userMessage: string,
    public readonly retryable: boolean = true
  ) {
    super(message);
    this.name = 'UpdaterError';
  }
}

function createNetworkError(error: Error): UpdaterError {
  const msg = error.message.toLowerCase();

  if (msg.includes('enotfound') || msg.includes('getaddrinfo')) {
    return new UpdaterError(
      error.message,
      'NETWORK_OFFLINE',
      'Brak połączenia z internetem. Sprawdź połączenie i spróbuj ponownie.',
      true
    );
  }

  if (msg.includes('timeout')) {
    return new UpdaterError(
      error.message,
      'NETWORK_TIMEOUT',
      'Serwer nie odpowiada. Spróbuj ponownie za chwilę.',
      true
    );
  }

  if (msg.includes('econnrefused') || msg.includes('econnreset')) {
    return new UpdaterError(
      error.message,
      'NETWORK_CONNECTION',
      'Nie można połączyć się z serwerem. Spróbuj ponownie.',
      true
    );
  }

  if (msg.includes('too many redirects')) {
    return new UpdaterError(
      error.message,
      'REDIRECT_LOOP',
      'Błąd serwera (przekierowanie). Spróbuj ponownie później.',
      false
    );
  }

  return new UpdaterError(
    error.message,
    'NETWORK_UNKNOWN',
    'Wystąpił błąd sieci. Spróbuj ponownie.',
    true
  );
}

// ============================================================================
// Public API
// ============================================================================

/**
 * Get current app version from package.json
 */
export function getCurrentVersion(): string {
  return app.getVersion();
}

/**
 * Fetch and parse update info from GitHub
 */
export async function fetchUpdateInfo(
  channel: UpdateChannel,
  config: UpdaterConfig = updaterConfig
): Promise<UpdateInfo | null> {
  const url = getYmlUrl(config, channel);

  try {
    log('info', `Fetching update info from ${channel} channel`);
    const ymlContent = await fetchWithRetry(url, config);
    const updateInfo = parseYml(ymlContent);

    if (!validateUpdateInfo(updateInfo)) {
      log('error', 'Invalid YML structure', updateInfo);
      return null;
    }

    log('info', `Found version ${updateInfo.version}`);
    return updateInfo;
  } catch (error) {
    const err = error instanceof UpdaterError ? error : createNetworkError(error as Error);
    log('error', 'Failed to fetch update info', { code: err.code, message: err.message });
    return null;
  }
}

/**
 * Check for updates
 */
export async function checkForUpdates(
  channel: UpdateChannel,
  config: UpdaterConfig = updaterConfig
): Promise<UpdateCheckResult> {
  const currentVersion = getCurrentVersion();

  try {
    const updateInfo = await fetchUpdateInfo(channel, config);

    if (!updateInfo) {
      return {
        updateAvailable: false,
        currentVersion,
        latestVersion: currentVersion,
        updateInfo: null,
      };
    }

    const latestVersion = updateInfo.version;
    const comparison = compareVersions(currentVersion, latestVersion);

    log('debug', `Version comparison: ${currentVersion} vs ${latestVersion} = ${comparison}`);

    const updateAvailable = comparison < 0;

    return {
      updateAvailable,
      currentVersion,
      latestVersion,
      updateInfo: updateAvailable ? updateInfo : null,
    };
  } catch (error) {
    const err = error instanceof UpdaterError ? error : createNetworkError(error as Error);
    return {
      updateAvailable: false,
      currentVersion,
      latestVersion: currentVersion,
      updateInfo: null,
      error: err.userMessage,
    };
  }
}

/**
 * Download update with progress callback
 */
export async function downloadUpdate(
  updateInfo: UpdateInfo,
  onProgress?: (progress: number, downloaded: number, total: number) => void,
  config: UpdaterConfig = updaterConfig
): Promise<string> {
  const fileName = updateInfo.path;
  const downloadUrl = getDownloadUrl(config, updateInfo.version, fileName);
  const tempPath = join(tmpdir(), fileName);

  log('info', `Starting download: ${fileName}`);

  // Clean up old downloads
  cleanupOldDownloads(config);

  // Check for existing partial download
  if (existsSync(tempPath)) {
    try {
      unlinkSync(tempPath);
      log('debug', 'Removed existing partial download');
    } catch {
      // Ignore
    }
  }

  // Download file with retry
  await downloadFileWithRetry(
    downloadUrl,
    tempPath,
    updateInfo.files[0]?.size || 0,
    onProgress,
    config
  );

  // Verify checksum
  log('info', 'Verifying checksum...');
  const isValid = await verifyChecksum(tempPath, updateInfo.sha512);

  if (!isValid) {
    unlinkSync(tempPath);
    throw new UpdaterError(
      'Checksum verification failed',
      'CHECKSUM_MISMATCH',
      'Pobrany plik jest uszkodzony. Spróbuj ponownie.',
      true
    );
  }

  log('info', 'Download complete and verified');
  return tempPath;
}

/**
 * Install update (launches installer and quits app)
 */
export function installUpdate(
  installerPath: string,
  config: UpdaterConfig = updaterConfig
): void {
  if (!existsSync(installerPath)) {
    throw new UpdaterError(
      'Installer not found',
      'INSTALLER_NOT_FOUND',
      'Plik instalatora nie został znaleziony.',
      false
    );
  }

  log('info', `Launching installer: ${installerPath}`);

  const installer = spawn(installerPath, config.installerArgs, {
    detached: true,
    stdio: 'ignore',
  });

  installer.unref();

  setTimeout(() => {
    log('info', 'Quitting app for update installation');
    app.quit();
  }, config.quitDelayMs);
}

/**
 * Schedule auto-update check after window is shown
 *
 * IMPORTANT: BrowserWindow must be created with `show: false`
 * and shown manually with `ready-to-show` event for this to work.
 */
export function scheduleUpdateCheck(
  mainWindow: BrowserWindow,
  getSettings: () => Promise<{ autoUpdate: boolean; updateChannel: UpdateChannel }>,
  delayMs: number = 5000,
  config: UpdaterConfig = updaterConfig
): void {
  mainWindow.once('show', () => {
    setTimeout(async () => {
      try {
        const settings = await getSettings();

        if (!settings.autoUpdate) {
          log('info', 'Auto-update disabled in settings');
          return;
        }

        log('info', `Checking for updates (channel: ${settings.updateChannel})...`);
        const result = await checkForUpdates(settings.updateChannel, config);

        if (result.updateAvailable && result.updateInfo) {
          log('info', `Update available: ${result.latestVersion}`);
          mainWindow.webContents.send('update-available', result.updateInfo);
        } else if (result.error) {
          log('warn', `Update check failed: ${result.error}`);
        } else {
          log('info', `No updates available (current: ${result.currentVersion})`);
        }
      } catch (error) {
        log('error', 'Auto-update check failed', error);
      }
    }, delayMs);
  });
}

// ============================================================================
// Network Functions with Retry
// ============================================================================

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchWithRetry(
  url: string,
  config: UpdaterConfig,
  attempt: number = 0
): Promise<string> {
  try {
    return await fetchUrl(url, config.network.fetchTimeoutMs, config.network.maxRedirects);
  } catch (error) {
    const isRetryable = error instanceof UpdaterError ? error.retryable : true;

    if (isRetryable && attempt < config.network.maxRetries - 1) {
      const delay = config.network.retryBaseDelayMs * Math.pow(2, attempt);
      log('warn', `Fetch failed, retrying in ${delay}ms (attempt ${attempt + 1}/${config.network.maxRetries})`, error);
      await sleep(delay);
      return fetchWithRetry(url, config, attempt + 1);
    }

    throw error;
  }
}

function fetchUrl(
  url: string,
  timeoutMs: number,
  maxRedirects: number
): Promise<string> {
  return new Promise((resolve, reject) => {
    if (maxRedirects <= 0) {
      reject(new UpdaterError(
        'Too many redirects',
        'REDIRECT_LOOP',
        'Błąd serwera (za dużo przekierowań).',
        false
      ));
      return;
    }

    const protocol = url.startsWith('https') ? https : http;

    const request = protocol.get(url, { timeout: timeoutMs }, (response) => {
      if (response.statusCode === 301 || response.statusCode === 302 || response.statusCode === 307) {
        const redirectUrl = response.headers.location;
        if (redirectUrl) {
          log('debug', `Redirecting to: ${redirectUrl}`);
          fetchUrl(redirectUrl, timeoutMs, maxRedirects - 1)
            .then(resolve)
            .catch(reject);
          return;
        }
      }

      if (response.statusCode !== 200) {
        reject(new UpdaterError(
          `HTTP ${response.statusCode}`,
          'HTTP_ERROR',
          `Serwer zwrócił błąd (${response.statusCode}).`,
          response.statusCode! >= 500
        ));
        return;
      }

      let data = '';
      response.on('data', (chunk) => (data += chunk));
      response.on('end', () => resolve(data));
      response.on('error', (err) => reject(createNetworkError(err)));
    });

    request.on('error', (err) => reject(createNetworkError(err)));
    request.on('timeout', () => {
      request.destroy();
      reject(new UpdaterError(
        'Request timeout',
        'NETWORK_TIMEOUT',
        'Serwer nie odpowiada.',
        true
      ));
    });
  });
}

async function downloadFileWithRetry(
  url: string,
  destPath: string,
  expectedSize: number,
  onProgress?: (progress: number, downloaded: number, total: number) => void,
  config: UpdaterConfig = updaterConfig,
  attempt: number = 0
): Promise<void> {
  try {
    await downloadFile(url, destPath, expectedSize, onProgress, config);
  } catch (error) {
    const isRetryable = error instanceof UpdaterError ? error.retryable : true;

    if (isRetryable && attempt < config.network.maxRetries - 1) {
      const delay = config.network.retryBaseDelayMs * Math.pow(2, attempt);
      log('warn', `Download failed, retrying in ${delay}ms (attempt ${attempt + 1}/${config.network.maxRetries})`, error);

      if (existsSync(destPath)) {
        try {
          unlinkSync(destPath);
        } catch {
          // Ignore
        }
      }

      await sleep(delay);
      return downloadFileWithRetry(url, destPath, expectedSize, onProgress, config, attempt + 1);
    }

    throw error;
  }
}

function downloadFile(
  url: string,
  destPath: string,
  expectedSize: number,
  onProgress?: (progress: number, downloaded: number, total: number) => void,
  config: UpdaterConfig = updaterConfig
): Promise<void> {
  return new Promise((resolve, reject) => {
    const protocol = url.startsWith('https') ? https : http;
    let activityTimer: NodeJS.Timeout | null = null;
    let fileStream: ReturnType<typeof createWriteStream> | null = null;

    const resetActivityTimer = () => {
      if (activityTimer) clearTimeout(activityTimer);
      activityTimer = setTimeout(() => {
        if (fileStream) fileStream.destroy();
        reject(new UpdaterError(
          'Download stalled',
          'DOWNLOAD_STALLED',
          'Pobieranie zatrzymało się. Spróbuj ponownie.',
          true
        ));
      }, config.network.activityTimeoutMs);
    };

    const cleanup = () => {
      if (activityTimer) clearTimeout(activityTimer);
    };

    const request = protocol.get(url, { timeout: config.network.downloadTimeoutMs }, (response) => {
      if (response.statusCode === 301 || response.statusCode === 302 || response.statusCode === 307) {
        cleanup();
        const redirectUrl = response.headers.location;
        if (redirectUrl) {
          log('debug', `Download redirecting to: ${redirectUrl}`);
          downloadFile(redirectUrl, destPath, expectedSize, onProgress, config)
            .then(resolve)
            .catch(reject);
          return;
        }
      }

      if (response.statusCode !== 200) {
        cleanup();
        reject(new UpdaterError(
          `HTTP ${response.statusCode}`,
          'HTTP_ERROR',
          `Serwer zwrócił błąd (${response.statusCode}).`,
          response.statusCode! >= 500
        ));
        return;
      }

      const totalSize = parseInt(response.headers['content-length'] || '0', 10) || expectedSize;
      let downloadedSize = 0;

      fileStream = createWriteStream(destPath);
      resetActivityTimer();

      response.on('data', (chunk: Buffer) => {
        resetActivityTimer();
        downloadedSize += chunk.length;

        if (onProgress && totalSize > 0) {
          const progress = Math.round((downloadedSize / totalSize) * 100);
          onProgress(progress, downloadedSize, totalSize);
        }
      });

      response.pipe(fileStream);

      fileStream.on('finish', () => {
        cleanup();
        fileStream!.close();
        resolve();
      });

      fileStream.on('error', (err) => {
        cleanup();
        if (existsSync(destPath)) {
          try { unlinkSync(destPath); } catch { /* Ignore */ }
        }
        reject(createNetworkError(err));
      });

      response.on('error', (err) => {
        cleanup();
        if (existsSync(destPath)) {
          try { unlinkSync(destPath); } catch { /* Ignore */ }
        }
        reject(createNetworkError(err));
      });
    });

    request.on('error', (err) => {
      cleanup();
      reject(createNetworkError(err));
    });

    request.on('timeout', () => {
      cleanup();
      request.destroy();
      reject(new UpdaterError(
        'Download timeout',
        'NETWORK_TIMEOUT',
        'Pobieranie trwało zbyt długo.',
        true
      ));
    });
  });
}

// ============================================================================
// YAML Parsing and Validation
// ============================================================================

function parseYml(content: string): UpdateInfo {
  const lines = content.split('\n');
  const result: Partial<UpdateInfo> = {
    files: [],
  };

  let inFiles = false;
  let currentFile: Partial<UpdateFile> = {};

  for (const line of lines) {
    const trimmed = line.trim();

    if (!trimmed || trimmed.startsWith('#')) {
      continue;
    }

    if (trimmed.startsWith('version:')) {
      result.version = extractValue(trimmed, 'version:');
    } else if (trimmed.startsWith('path:') && !inFiles) {
      result.path = extractValue(trimmed, 'path:');
    } else if (trimmed.startsWith('sha512:') && !inFiles) {
      result.sha512 = extractValue(trimmed, 'sha512:');
    } else if (trimmed.startsWith('releaseDate:')) {
      result.releaseDate = extractValue(trimmed, 'releaseDate:');
    } else if (trimmed === 'files:') {
      inFiles = true;
    } else if (inFiles) {
      if (trimmed.startsWith('- url:')) {
        if (currentFile.url) {
          result.files!.push(currentFile as UpdateFile);
        }
        currentFile = { url: extractValue(trimmed, '- url:') };
      } else if (trimmed.startsWith('sha512:')) {
        currentFile.sha512 = extractValue(trimmed, 'sha512:');
      } else if (trimmed.startsWith('size:')) {
        currentFile.size = parseInt(extractValue(trimmed, 'size:'), 10) || 0;
      } else if (!trimmed.startsWith('-') && !trimmed.startsWith(' ') && trimmed.includes(':')) {
        if (currentFile.url) {
          result.files!.push(currentFile as UpdateFile);
          currentFile = {};
        }
        inFiles = false;
      }
    }
  }

  if (currentFile.url) {
    result.files!.push(currentFile as UpdateFile);
  }

  return result as UpdateInfo;
}

function extractValue(line: string, prefix: string): string {
  const value = line.substring(prefix.length).trim();
  return value.replace(/^['"]|['"]$/g, '');
}

function validateUpdateInfo(info: Partial<UpdateInfo>): info is UpdateInfo {
  if (!info.version || typeof info.version !== 'string') {
    log('error', 'Missing or invalid version field');
    return false;
  }

  if (!info.sha512 || typeof info.sha512 !== 'string') {
    log('error', 'Missing or invalid sha512 field');
    return false;
  }

  if (!info.path || typeof info.path !== 'string') {
    log('error', 'Missing or invalid path field');
    return false;
  }

  if (!/^\d+\.\d+\.\d+/.test(info.version)) {
    log('error', 'Invalid version format', info.version);
    return false;
  }

  if (info.sha512.length < 80 || info.sha512.length > 100) {
    log('error', 'Invalid sha512 length', info.sha512.length);
    return false;
  }

  return true;
}

// ============================================================================
// Version Comparison (Full SemVer)
// ============================================================================

function compareVersions(a: string, b: string): number {
  const cleanA = a.replace(/^v/, '');
  const cleanB = b.replace(/^v/, '');

  const [versionA, prereleaseA] = splitVersion(cleanA);
  const [versionB, prereleaseB] = splitVersion(cleanB);

  const baseComparison = compareBaseVersions(versionA, versionB);
  if (baseComparison !== 0) {
    return baseComparison;
  }

  return comparePrerelease(prereleaseA, prereleaseB);
}

function splitVersion(version: string): [string, string | null] {
  const withoutBuild = version.split('+')[0];
  const hyphenIndex = withoutBuild.indexOf('-');

  if (hyphenIndex === -1) {
    return [withoutBuild, null];
  }

  return [
    withoutBuild.substring(0, hyphenIndex),
    withoutBuild.substring(hyphenIndex + 1),
  ];
}

function compareBaseVersions(a: string, b: string): number {
  const partsA = a.split('.').map(Number);
  const partsB = b.split('.').map(Number);

  for (let i = 0; i < Math.max(partsA.length, partsB.length); i++) {
    const numA = partsA[i] || 0;
    const numB = partsB[i] || 0;

    if (numA < numB) return -1;
    if (numA > numB) return 1;
  }

  return 0;
}

function comparePrerelease(a: string | null, b: string | null): number {
  if (!a && b) return 1;
  if (a && !b) return -1;
  if (!a && !b) return 0;

  const prereleaseOrder: Record<string, number> = {
    dev: 0,
    alpha: 1,
    a: 1,
    beta: 2,
    b: 2,
    rc: 3,
    pre: 3,
  };

  const parsePrerelease = (pre: string): { type: string; num: number } => {
    const parts = pre.toLowerCase().split('.');
    const type = parts[0].replace(/[0-9]/g, '');
    const numStr = pre.replace(/[^0-9]/g, '');
    const num = numStr ? parseInt(numStr, 10) : 0;
    return { type, num };
  };

  const parsedA = parsePrerelease(a!);
  const parsedB = parsePrerelease(b!);

  const orderA = prereleaseOrder[parsedA.type] ?? 999;
  const orderB = prereleaseOrder[parsedB.type] ?? 999;

  if (orderA < orderB) return -1;
  if (orderA > orderB) return 1;

  if (parsedA.num < parsedB.num) return -1;
  if (parsedA.num > parsedB.num) return 1;

  return 0;
}

// ============================================================================
// Checksum Verification
// ============================================================================

async function verifyChecksum(filePath: string, expectedHash: string): Promise<boolean> {
  return new Promise((resolve, reject) => {
    const hash = createHash('sha512');
    const fs = require('fs');
    const stream = fs.createReadStream(filePath);

    stream.on('data', (data: Buffer) => hash.update(data));
    stream.on('end', () => {
      const actualHash = hash.digest('base64');
      const isValid = actualHash === expectedHash;

      if (!isValid) {
        log('error', 'Checksum mismatch', {
          expected: expectedHash.substring(0, 20) + '...',
          actual: actualHash.substring(0, 20) + '...',
        });
      }

      resolve(isValid);
    });
    stream.on('error', reject);
  });
}

// ============================================================================
// Cleanup
// ============================================================================

function cleanupOldDownloads(config: UpdaterConfig = updaterConfig): void {
  const tempDir = tmpdir();
  const pattern = new RegExp(`^${config.appName}_Setup_.*\\.exe$`, 'i');

  try {
    const files = readdirSync(tempDir);

    for (const file of files) {
      if (pattern.test(file)) {
        const filePath = join(tempDir, file);

        try {
          const stats = statSync(filePath);
          const ageMs = Date.now() - stats.mtimeMs;
          const ageHours = ageMs / (1000 * 60 * 60);

          if (ageHours > 24) {
            unlinkSync(filePath);
            log('debug', `Cleaned up old installer: ${file}`);
          }
        } catch {
          // Ignore errors (file might be in use)
        }
      }
    }
  } catch (error) {
    log('debug', 'Cleanup failed', error);
  }
}
