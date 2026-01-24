# Electron Auto-Updater - Uniwersalny moduł

Gotowy do użycia auto-updater dla aplikacji Electron + GitHub Releases.

## Szybki start

### 1. Skopiuj pliki

```bash
cp scripts/templates/electron/updater.ts your-project/electron/
cp scripts/templates/electron/updater.config.ts your-project/electron/
```

### 2. Edytuj konfigurację

W `updater.config.ts` zmień:

```typescript
export const updaterConfig: UpdaterConfig = {
  releasesRepo: 'your-username/your-app-releases',  // <- ZMIEŃ
  appName: 'YourApp',                                // <- ZMIEŃ
  installerPattern: 'YourApp_Setup_{version}.exe',   // <- ZMIEŃ
  // ... reszta domyślna
};
```

### 3. Integracja z main.ts

```typescript
import {
  checkForUpdates,
  downloadUpdate,
  installUpdate,
  scheduleUpdateCheck,
  getCurrentVersion,
  UpdateInfo,
  UpdateChannel,
} from './updater';

let pendingUpdateInfo: UpdateInfo | null = null;

// W app.whenReady():

// IPC handlers
ipcMain.handle('get-app-version', () => getCurrentVersion());

ipcMain.handle('check-for-updates', async (_event, channel: UpdateChannel) =>
  checkForUpdates(channel));

ipcMain.handle('download-update', async () => {
  if (!pendingUpdateInfo) throw new Error('No update info');
  return downloadUpdate(pendingUpdateInfo, (progress, downloaded, total) => {
    mainWindow?.webContents.send('update-download-progress', { progress, downloaded, total });
  });
});

ipcMain.handle('install-update', async (_event, path: string) => installUpdate(path));

ipcMain.handle('set-pending-update', async (_event, info: UpdateInfo) => {
  pendingUpdateInfo = info;
});

ipcMain.handle('clear-pending-update', async () => {
  pendingUpdateInfo = null;
});

// Auto-check po starcie
scheduleUpdateCheck(mainWindow, async () => {
  // Pobierz ustawienia z localStorage
  return { autoUpdate: true, updateChannel: 'stable' as UpdateChannel };
}, 5000);
```

### 4. WAŻNE: BrowserWindow z show: false

```typescript
mainWindow = new BrowserWindow({
  // ... inne opcje
  show: false,  // WYMAGANE dla scheduleUpdateCheck
});

mainWindow.once('ready-to-show', () => {
  mainWindow?.show();
});
```

## Funkcje

| Funkcja | Wartość | Opis |
| ------- | ------- | ---- |
| Retry | 3 próby | Exponential backoff: 1s, 2s, 4s |
| Timeout YML | 30s | Pobranie pliku konfiguracyjnego |
| Timeout Download | 10 min | Pobranie instalatora (~100MB) |
| Activity timeout | 60s | Retry jeśli brak danych |
| Max redirects | 5 | Ochrona przed pętlą |
| SemVer | pełny | dev < alpha < beta < rc < stable |
| Checksum | SHA512 | Base64, weryfikacja po pobraniu |

## Wymagania

- Electron 27+
- TypeScript
- GitHub Releases repo z plikami:
  - `latest.yml` (stable)
  - `beta.yml` (opcjonalnie)
  - `AppName_Setup_X.Y.Z.exe`

## Format YML

```yaml
version: 1.0.0
files:
  - url: AppName_Setup_1.0.0.exe
    sha512: BASE64_HASH
    size: 123456789
path: AppName_Setup_1.0.0.exe
sha512: BASE64_HASH
releaseDate: '2024-01-01T00:00:00.000Z'
```

## Troubleshooting

| Problem | Rozwiązanie |
| ------- | ----------- |
| Nie wykrywa aktualizacji | Sprawdź czy YML jest aktualny w releases repo |
| Checksum mismatch | Ponowny release z prawidłowym SHA512 |
| Timeout | Zwiększ `downloadTimeoutMs` w config |
| Retry loop | Sprawdź logi, może być problem z siecią |

## Licencja

MIT - używaj w dowolnym projekcie.
