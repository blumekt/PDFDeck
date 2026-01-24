/**
 * Universal Auto-Updater Configuration
 *
 * This file configures the auto-updater for any Electron + GitHub Releases project.
 * Simply update these values for your project.
 *
 * @example Usage in another project:
 * 1. Copy updater.ts and updater.config.ts to your project's electron/ folder
 * 2. Update the values below
 * 3. Import and use in main.ts
 */

export interface UpdaterConfig {
  /** GitHub repository in format "owner/repo" */
  releasesRepo: string;

  /** App name prefix for installer files (e.g., "MyApp" -> "MyApp_Setup_1.0.0.exe") */
  appName: string;

  /** Installer file pattern. Use {version} as placeholder */
  installerPattern: string;

  /** Available update channels */
  channels: readonly string[];

  /** Default channel if not specified */
  defaultChannel: string;

  /** Network settings */
  network: {
    /** Timeout for YML fetch in ms (default: 30000) */
    fetchTimeoutMs: number;

    /** Timeout for download in ms (default: 600000 = 10 min) */
    downloadTimeoutMs: number;

    /** Activity timeout - retry if no data received for this long (default: 60000) */
    activityTimeoutMs: number;

    /** Maximum retry attempts (default: 3) */
    maxRetries: number;

    /** Base delay for exponential backoff in ms (default: 1000) */
    retryBaseDelayMs: number;

    /** Maximum redirects to follow (default: 5) */
    maxRedirects: number;
  };

  /** Installer launch arguments (Windows Inno Setup uses /SILENT) */
  installerArgs: string[];

  /** Delay before app.quit() after launching installer in ms */
  quitDelayMs: number;
}

// =============================================================================
// EDIT THIS SECTION FOR YOUR PROJECT
// =============================================================================

/**
 * Your App Auto-Updater Configuration
 *
 * TODO: Update these values for your project
 */
export const updaterConfig: UpdaterConfig = {
  // GitHub repository for releases (format: "owner/repo")
  // TODO: Change to your releases repository
  releasesRepo: 'your-username/your-app-releases',

  // App name (used for installer file detection and cleanup)
  // TODO: Change to your app name
  appName: 'YourApp',

  // Installer file pattern ({version} will be replaced)
  // TODO: Change to match your installer naming
  installerPattern: 'YourApp_Setup_{version}.exe',

  // Available channels
  channels: ['stable', 'beta'] as const,

  // Default channel
  defaultChannel: 'stable',

  // Network configuration - tuned for reliability
  // These defaults work well for most cases
  network: {
    fetchTimeoutMs: 30000,        // 30 seconds for YML fetch
    downloadTimeoutMs: 600000,    // 10 minutes for large installer (~100MB)
    activityTimeoutMs: 60000,     // Retry if no data for 60s
    maxRetries: 3,                // 3 attempts with exponential backoff
    retryBaseDelayMs: 1000,       // 1s, 2s, 4s delays
    maxRedirects: 5,              // Prevent infinite redirect loops
  },

  // Inno Setup silent install arguments
  installerArgs: ['/SILENT'],

  // Wait 1 second before quitting to ensure installer starts
  quitDelayMs: 1000,
};

// =============================================================================
// Helper functions (DO NOT EDIT)
// =============================================================================

export const getYmlBaseUrl = (config: UpdaterConfig): string =>
  `https://raw.githubusercontent.com/${config.releasesRepo}/main`;

export const getReleasesBaseUrl = (config: UpdaterConfig): string =>
  `https://github.com/${config.releasesRepo}/releases/download`;

export const getYmlUrl = (config: UpdaterConfig, channel: string): string => {
  const ymlFile = channel === 'stable' ? 'latest.yml' : `${channel}.yml`;
  return `${getYmlBaseUrl(config)}/${ymlFile}`;
};

export const getDownloadUrl = (config: UpdaterConfig, version: string, fileName: string): string =>
  `${getReleasesBaseUrl(config)}/v${version}/${fileName}`;
