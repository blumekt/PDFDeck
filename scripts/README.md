# Scripts - Uniwersalne narzędzia do aplikacji desktopowych

Zestaw przenośnych skryptów Python do automatyzacji:

- **Instalatora Windows** (PyInstaller + Inno Setup)
- **Auto-Updatera** (sprawdzanie i pobieranie aktualizacji)
- **Wydawania wersji** (build, release, upload)

**Wspierane frameworki:**

- **Python:** PyQt6, CustomTkinter, CLI
- **Electron:** TypeScript/JavaScript (gotowe pliki w `templates/electron/`)
- **Hybrid:** Electron + Python backend (przykład: IconHub)

**Skopiuj cały katalog `scripts/` do nowego projektu - skrypty automatycznie skonfigurują się na podstawie `pyproject.toml`.**

---

## Przykład produkcyjny: IconHub

Ten zestaw skryptów został przetestowany i używany w produkcji w projekcie **IconHub** - hybrydowej aplikacji Electron + Python.

### Architektura IconHub

```text
IconHub/
├── frontend/                 # Electron + React + TypeScript
│   ├── electron/
│   │   ├── main.ts          # Spawns Python backend + auto-updater
│   │   └── updater.ts       # Auto-updater (z templates/electron/)
│   └── dist-builder/
│       └── win-unpacked/    # electron-builder output
├── backend/                  # Python FastAPI
│   └── dist/
│       └── backend/         # PyInstaller output
├── installers/
│   └── iconhub_installer.iss # Inno Setup (z templates/innosetup/)
├── release/
│   ├── IconHub_Setup_1.2.1.exe
│   ├── latest.yml
│   └── beta.yml
└── scripts/                  # Te skrypty
```

### Co działa w IconHub

| Komponent | Status | Opis |
| --------- | ------ | ---- |
| **Auto-updater** | Testowane | Electron updater z retry, timeouts, SHA512 |
| **Inno Setup** | Testowane | Custom pages (About, SmartScreen, License), 5 języków |
| **release.py** | Testowane | Full workflow: build → installer → GitHub Release → YML push |
| **electron-builder** | Testowane | Build method `electron` dla hybrid apps |

### Konfiguracja IconHub (pyproject.toml)

```toml
[project]
name = "iconhub"
version = "1.2.1"

[tool.release]
app_name = "IconHub"
releases_repo = "blumekt/IconHub-releases"
installer_name = "IconHub_Setup_{version}.exe"
installer_iss = "installers/iconhub_installer.iss"
spec_file = "backend.spec"
build_method = "electron"
frontend_dir = "frontend"
package_json = "frontend/package.json"
```

### Workflow wydawania wersji IconHub

```bash
# 1. Sprawdź czy wszystko gotowe
python scripts/release.py --check

# 2. Wydaj wersję
python scripts/release.py 1.2.1

# Skrypt automatycznie:
# - Buduje backend (PyInstaller)
# - Buduje frontend (electron-builder)
# - Tworzy instalator (Inno Setup)
# - Generuje latest.yml z SHA512
# - Commit + tag + push
# - GitHub Release w IconHub-releases
# - Push YML do releases repo (dla auto-updater)
```

---

## ⚠️ KRYTYCZNE: Pilnowanie plików YML

> **Pliki `latest.yml` i `beta.yml` MUSZĄ być aktualne w releases repo!**
> Jeśli są nieaktualne, użytkownicy NIE otrzymają aktualizacji.

### Obowiązkowy workflow wydawania wersji

```bash
# ZAWSZE używaj release.py - NIGDY ręcznych komend!
python scripts/release.py X.Y.Z

# Skrypt automatycznie:
# 1. Buduje instalator
# 2. Generuje YML z SHA512
# 3. Uploaduje do GitHub Releases
# 4. Push YML do main branch releases repo
```

### Co robi release.py z plikami YML

| Krok | Akcja |
| ---- | ----- |
| 4 | Generuje `latest.yml` (stable) lub `beta.yml` (beta) z SHA512 checksum |
| 7 | Tworzy GitHub Release z instalatorem |
| 8 | **KRYTYCZNE:** Push plików YML do main branch releases repo |

### Weryfikacja po release

```bash
# Sprawdź czy YML jest aktualny
curl https://raw.githubusercontent.com/USERNAME/APP-releases/main/latest.yml

# Powinno pokazać nową wersję:
# version: X.Y.Z
# sha512: ...
```

### Troubleshooting YML

| Problem | Przyczyna | Rozwiązanie |
| ------- | --------- | ----------- |
| Auto-updater nie wykrywa aktualizacji | YML nieaktualny | `python scripts/release.py X.Y.Z` |
| "Checksum mismatch" | SHA512 nie zgadza się | Ponowny release lub ręczna aktualizacja YML |
| 404 przy pobieraniu YML | Plik nie istnieje | Sprawdź releases repo i branch |

---

## Spis treści

1. [Quick Start - Nowy projekt od zera](#quick-start---nowy-projekt-od-zera)
2. [Szablony](#szablony)
   - [Electron Auto-Updater](#electron---uniwersalny-auto-updater)
   - [Inno Setup Installer](#inno-setup---uniwersalny-instalator)
3. [Skrypty](#skrypty)
   - [setup_installer.py](#1-setup_installerpy---inicjalizacja-instalatora)
   - [setup_updater.py](#2-setup_updaterpy---inicjalizacja-auto-updatera)
   - [release.py](#3-releasepy---wydawanie-wersji)
4. [Konfiguracja pyproject.toml](#konfiguracja-pyprojecttoml)
5. [Wymagania systemowe](#wymagania-systemowe)
6. [Repozytoria GitHub](#repozytoria-github)
7. [Rozwiązywanie problemów](#rozwiązywanie-problemów)
8. [FAQ](#faq)

---

## Quick Start - Nowy projekt od zera

### Krok 1: Skopiuj skrypty

```bash
# Skopiuj cały katalog scripts/ do nowego projektu
cp -r scripts/ /path/to/new-project/scripts/
```

### Krok 2: Dodaj konfigurację do pyproject.toml

```toml
[project]
name = "myapp"
version = "1.0.0"

[tool.installer]
app_name = "MyApp"
app_id = "{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}"
publisher = "Your Name"
description = "My awesome application"
url = "https://github.com/username/myapp"
releases_repo = "username/myapp-releases"
ui_framework = "pyqt6"  # lub "customtkinter", "cli"
icon_path = "assets/icon.ico"

[tool.updater]
app_name = "MyApp"
releases_repo = "username/myapp-releases"
ui_framework = "pyqt6"

[tool.release]
app_name = "MyApp"
releases_repo = "username/myapp-releases"
```

### Krok 3: Sprawdź wymagania

```bash
# Sprawdź czy wszystko jest zainstalowane
python scripts/setup_installer.py --check
python scripts/setup_updater.py --check
python scripts/release.py --check
```

### Krok 4: Wygeneruj pliki

```bash
# 1. Wygeneruj pliki instalatora (spec, iss, version_info)
python scripts/setup_installer.py --init

# 2. Wygeneruj pliki auto-updatera (checker, downloader, dialog)
python scripts/setup_updater.py --init

# 3. Przejrzyj wygenerowane pliki i dostosuj do potrzeb
```

### Krok 5: Wydaj pierwszą wersję

```bash
# Wydaj wersję 1.0.0
python scripts/release.py 1.0.0
```

---

## Szablony

Skrypty zawierają gotowe szablony do użycia w nowych projektach.

```text
scripts/templates/
├── electron/
│   ├── updater.ts           # Auto-updater dla Electron
│   ├── updater.config.ts    # Konfiguracja
│   └── README.md
└── innosetup/
    ├── template.iss         # Szablon instalatora Windows
    └── README.md
```

---

## Inno Setup - Uniwersalny Instalator

Dla projektów wymagających profesjonalnego instalatora Windows.

### Funkcje szablonu

| Funkcja | Opis |
| ------- | ---- |
| **Multi-language** | EN, PL, DE, FR, ES - automatyczne wykrywanie |
| **Custom Pages** | About, SmartScreen, License |
| **Per-user Install** | Bez uprawnień admina |
| **LZMA2 Ultra** | Maksymalna kompresja |
| **Auto-terminate** | Zamyka app przed instalacją |

### Użycie

```bash
# 1. Skopiuj szablon
cp scripts/templates/innosetup/template.iss installers/{app}_installer.iss

# 2. Edytuj placeholdery
# - {{APP_NAME}} -> MyApp
# - {{VERSION}} -> 1.0.0
# - {{PUBLISHER}} -> Your Name
# - {{APP_URL}} -> https://github.com/user/app
# - Wygeneruj GUID: https://www.guidgenerator.com/

# 3. Zbuduj
iscc installers/{app}_installer.iss
```

### Custom Pages (strony wizarda)

Szablon zawiera 3 niestandardowe strony informacyjne:

1. **About** - Przedstaw swoją aplikację
2. **SmartScreen** - Ostrzeżenie dla niepodpisanych app (ważne!)
3. **License** - Warunki użytkowania

Przykład z IconHub (humorystyczny styl):

```innosetup
english.AboutText=Hi! I'm Blumy and I created IconHub because searching for icons was driving me crazy. :)
english.SmartScreenText=Microsoft thinks I'm a hacker (I'm not, I promise)...
english.LicenseText=You can do absolutely anything you want with it... Even smash it with a hammer! (please send video)
```

### Pełna dokumentacja

Zobacz: [templates/innosetup/README.md](templates/innosetup/README.md)

---

## Electron - Uniwersalny Auto-Updater

Dla projektów **Electron + TypeScript** dostępny jest gotowy, przetestowany auto-updater.

### Lokalizacja plików

```text
scripts/
└── templates/
    └── electron/
        ├── updater.ts         # Główny moduł auto-updatera
        └── updater.config.ts  # Konfiguracja (do edycji)
```

### Krok 1: Skopiuj pliki do projektu Electron

```bash
cp scripts/templates/electron/updater.ts your-project/electron/
cp scripts/templates/electron/updater.config.ts your-project/electron/
```

### Krok 2: Edytuj updater.config.ts

```typescript
export const updaterConfig: UpdaterConfig = {
  // GitHub repository for releases
  releasesRepo: 'your-username/your-app-releases',

  // App name (used for installer file detection)
  appName: 'YourApp',

  // Installer file pattern ({version} will be replaced)
  installerPattern: 'YourApp_Setup_{version}.exe',

  // ... reszta konfiguracji
};
```

### Krok 3: Integracja z main.ts

```typescript
import { scheduleUpdateCheck, UpdateChannel } from './updater';

// W app.whenReady():
scheduleUpdateCheck(mainWindow, async () => {
  // Pobierz ustawienia użytkownika
  return { autoUpdate: true, updateChannel: 'stable' as UpdateChannel };
}, 5000);
```

### Funkcje auto-updatera

| Funkcja | Opis |
| ------- | ---- |
| **Retry z exponential backoff** | 3 próby z opóźnieniem 1s, 2s, 4s |
| **Długie timeouty** | YML: 30s, Download: 10 min |
| **Activity timeout** | Retry jeśli brak danych przez 60s |
| **Limit przekierowań** | Max 5 (ochrona przed pętlą) |
| **Pełny SemVer** | Obsługa dev, alpha, beta, rc |
| **Walidacja YML** | Sprawdzenie struktury przed użyciem |
| **Weryfikacja SHA512** | Checksum po pobraniu |
| **User-friendly błędy** | Polskie komunikaty dla użytkowników |

### Konfiguracja sieciowa

```typescript
network: {
  fetchTimeoutMs: 30000,        // 30 sekund na pobranie YML
  downloadTimeoutMs: 600000,    // 10 minut na pobranie instalatora
  activityTimeoutMs: 60000,     // Retry jeśli brak danych przez 60s
  maxRetries: 3,                // 3 próby z exponential backoff
  retryBaseDelayMs: 1000,       // 1s, 2s, 4s delays
  maxRedirects: 5,              // Ochrona przed pętlą przekierowań
}
```

### IPC Handlers (main.ts)

Auto-updater wymaga następujących IPC handlers:

```typescript
// Pobierz wersję aplikacji
ipcMain.handle('get-app-version', () => getCurrentVersion());

// Sprawdź aktualizacje
ipcMain.handle('check-for-updates', async (_event, channel) =>
  checkForUpdates(channel));

// Pobierz aktualizację
ipcMain.handle('download-update', async () => {
  return downloadUpdate(pendingUpdateInfo, (progress, downloaded, total) => {
    mainWindow?.webContents.send('update-download-progress', { progress, downloaded, total });
  });
});

// Zainstaluj aktualizację
ipcMain.handle('install-update', async (_event, path) => installUpdate(path));

// Zapisz pending update info
ipcMain.handle('set-pending-update', async (_event, info) => {
  pendingUpdateInfo = info;
});

// Wyczyść pending update info (ważne dla memory leak!)
ipcMain.handle('clear-pending-update', async () => {
  pendingUpdateInfo = null;
});
```

### Wymagania dla BrowserWindow

```typescript
mainWindow = new BrowserWindow({
  // ... inne opcje
  show: false,  // WAŻNE: potrzebne dla scheduleUpdateCheck
});

mainWindow.once('ready-to-show', () => {
  mainWindow?.show();
});
```

---

## Skrypty

### 1. setup_installer.py - Inicjalizacja instalatora

Generuje infrastrukturę do budowania instalatora Windows.

#### Użycie

```bash
# Sprawdź środowisko
python scripts/setup_installer.py --check

# Wygeneruj pliki instalatora
python scripts/setup_installer.py --init

# Symulacja (bez tworzenia plików)
python scripts/setup_installer.py --init --dry-run

# Nadpisz istniejące pliki
python scripts/setup_installer.py --init --force

# Override frameworka UI
python scripts/setup_installer.py --init --framework customtkinter
```

#### Generowane pliki

| Plik | Opis |
| ---- | ---- |
| `{app}.spec` | Konfiguracja PyInstaller - jak budować .exe |
| `file_version_info.txt` | Metadane Windows (wersja, wydawca, copyright) |
| `installer/{app}_installer.iss` | Skrypt Inno Setup - jak budować instalator |
| `installer/` | Katalog na skrypty instalatora |
| `release/` | Katalog na gotowe instalatory |

#### Konfiguracja [tool.installer]

```toml
[tool.installer]
# WYMAGANE
app_name = "MyApp"              # Nazwa aplikacji (wyświetlana)

# OPCJONALNE (z sensownymi domyślnymi)
app_id = "{GUID}"               # Unikalny ID dla Inno Setup (auto-generowany)
publisher = "Unknown"           # Nazwa wydawcy
description = ""                # Opis aplikacji
url = ""                        # Strona projektu
releases_repo = ""              # Repo na GitHub dla release'ów

# UI Framework (wpływa na hidden imports)
ui_framework = "pyqt6"          # "pyqt6", "customtkinter", "cli"

# Ścieżki
entry_point = "main.py"         # Główny plik aplikacji (auto-wykrywany)
icon_path = ""                  # Ścieżka do ikony .ico (auto-wykrywana)
assets_dir = "assets"           # Katalog z zasobami
installer_dir = "installer"     # Katalog na skrypt .iss
release_dir = "release"         # Katalog na gotowe instalatory

# Języki instalatora (Inno Setup)
languages = ["english", "polish"]

# Dodatkowe hidden imports dla PyInstaller
hidden_imports = ["fitz", "pymupdf"]

# Dodatkowe pliki do dołączenia
data_files = ["resources", "config"]
```

#### Co sprawdza --check

- ✅ Wersja Pythona (3.9+)
- ✅ Konfiguracja w pyproject.toml
- ✅ Struktura projektu (entry point, ikona)
- ✅ PyInstaller zainstalowany
- ✅ Inno Setup zainstalowany
- ✅ Czy pliki już istnieją

---

### 2. setup_updater.py - Inicjalizacja auto-updatera

Generuje system automatycznych aktualizacji dla aplikacji.

#### Użycie

```bash
# Sprawdź środowisko
python scripts/setup_updater.py --check

# Wygeneruj pliki updatera
python scripts/setup_updater.py --init

# Testuj połączenie i parsowanie
python scripts/setup_updater.py --test

# Symulacja (bez tworzenia plików)
python scripts/setup_updater.py --init --dry-run

# Nadpisz istniejące pliki
python scripts/setup_updater.py --init --force

# Override frameworka UI
python scripts/setup_updater.py --init --framework customtkinter
```

#### Generowane pliki updatera

| Plik | Opis |
| ---- | ---- |
| `src/{app}/core/updater/__init__.py` | Eksporty modułu |
| `src/{app}/core/updater/models.py` | UpdateChannel, UpdateInfo, UpdateCheckResult |
| `src/{app}/core/updater/update_checker.py` | Sprawdzanie dostępności aktualizacji |
| `src/{app}/core/updater/update_downloader.py` | Pobieranie z weryfikacją SHA512 |
| `src/{app}/core/updater/update_manager.py` | Koordynacja procesu |
| `src/{app}/ui/dialogs/update_dialog.py` | Dialog aktualizacji (framework-specific) |

#### Konfiguracja [tool.updater]

```toml
[tool.updater]
# WYMAGANE
app_name = "MyApp"                       # Nazwa aplikacji
releases_repo = "username/myapp-releases" # Repo z plikami yml

# OPCJONALNE
ui_framework = "pyqt6"      # "pyqt6", "customtkinter", "cli"
update_check_delay = 2000   # Opóźnienie sprawdzania (ms) po starcie
channels = ["stable", "beta"]
models_location = "separate" # "separate" (nowy plik) lub "existing" (istniejący models.py)
```

#### Co sprawdza --check

- ✅ Wersja Pythona (3.9+)
- ✅ Konfiguracja w pyproject.toml
- ✅ Struktura projektu (src/{app}/core/)
- ✅ Dostęp do GitHub (releases repo)
- ✅ Istnienie latest.yml (info jeśli brak)
- ✅ Zależności frameworka (PyQt6/customtkinter)
- ✅ Czy pliki już istnieją

#### Co sprawdza --test

- ✅ Połączenie z releases repo
- ✅ Pobieranie i parsowanie latest.yml
- ✅ Logika porównywania wersji (stable vs beta)

#### Integracja z aplikacją

Po wygenerowaniu plików, skrypt pokazuje kod integracji:

**PyQt6:**

```python
from PyQt6.QtCore import QTimer
from myapp.core.updater import UpdateManager, UpdateChannel
from myapp.ui.dialogs.update_dialog import UpdateDialog

# W __init__:
QTimer.singleShot(2000, self._check_for_updates)

def _check_for_updates(self):
    channel = self._load_update_channel()  # z settings.json
    self._update_manager = UpdateManager(__version__, channel)
    self._update_manager.check_complete.connect(self._on_update_check)
    self._update_manager.check_for_updates()
```

**CustomTkinter:**

```python
# W __init__:
self.after(2000, self._check_for_updates)
```

#### Ustawienia kanału aktualizacji

Skrypt pokazuje też jak dodać wybór kanału (stable/beta) w ustawieniach aplikacji:

- Zapis/odczyt z `~/.{app}/settings.json`
- Przykładowy QComboBox (PyQt6) lub CTkOptionMenu (CustomTkinter)

---

### 3. release.py - Wydawanie wersji

Automatyzuje cały proces wydawania nowej wersji aplikacji.

#### Użycie

```bash
# Sprawdź wymagania
python scripts/release.py --check

# Wydaj wersję stabilną
python scripts/release.py 1.0.0

# Wydaj wersję beta
python scripts/release.py 1.0.0-beta.1

# Symulacja (bez zmian)
python scripts/release.py 1.0.0 --dry-run

# Bez potwierdzeń
python scripts/release.py 1.0.0 --force
```

#### Co robi skrypt (8 kroków)

| Krok | Opis |
| ---- | ---- |
| 1. Walidacja | Sprawdza format wersji, status git, narzędzia |
| 2. Aktualizacja wersji | pyproject.toml, *.iss, file_version_info.txt |
| 3. Build | PyInstaller → .exe, Inno Setup → installer |
| 4. Generowanie YML | latest.yml i/lub beta.yml z SHA512 |
| 5. Commit + Tag | `git commit` + `git tag vX.Y.Z` |
| 6. Push | Do origin (source repo) |
| 7. GitHub Release | Tworzy release w releases repo |
| 8. Push YML | Pliki yml do main branch releases repo |

#### Konfiguracja [tool.release]

```toml
[tool.release]
# WYMAGANE
app_name = "MyApp"
releases_repo = "username/myapp-releases"

# OPCJONALNE (auto-wykrywane)
installer_name = "MyApp_Setup_{version}.exe"
spec_file = "myapp.spec"
installer_iss = "installer/myapp_installer.iss"
```

#### Kanały aktualizacji (Stable vs Beta)

| Typ wydania | latest.yml | beta.yml |
| ----------- | ---------- | -------- |
| Stable (1.0.0) | ✅ Aktualizowany | ✅ Aktualizowany |
| Beta (1.0.0-beta.1) | ❌ Bez zmian | ✅ Aktualizowany |

Użytkownicy na kanale "stable" otrzymują tylko stabilne wersje.
Użytkownicy na kanale "beta" otrzymują wszystkie wersje.

---

## Konfiguracja pyproject.toml

### Pełna konfiguracja (wszystkie skrypty)

```toml
[project]
name = "myapp"
version = "1.0.0"
description = "My awesome application"
authors = [{name = "Your Name"}]

[tool.installer]
app_name = "MyApp"
app_id = "{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}"
publisher = "Your Name"
description = "My awesome application"
url = "https://github.com/username/myapp"
releases_repo = "username/myapp-releases"
ui_framework = "pyqt6"
entry_point = "src/myapp/__main__.py"
icon_path = "assets/myapp_icon.ico"
assets_dir = "assets"
installer_dir = "installer"
release_dir = "release"
languages = ["english", "polish", "german"]
hidden_imports = []
data_files = ["assets"]

[tool.updater]
app_name = "MyApp"
releases_repo = "username/myapp-releases"
ui_framework = "pyqt6"
update_check_delay = 2000
channels = ["stable", "beta"]

[tool.release]
app_name = "MyApp"
releases_repo = "username/myapp-releases"
installer_name = "MyApp_Setup_{version}.exe"
spec_file = "myapp.spec"
installer_iss = "installer/myapp_installer.iss"
```

### Minimalna konfiguracja

```toml
[project]
name = "myapp"
version = "1.0.0"

[tool.installer]
app_name = "MyApp"
releases_repo = "username/myapp-releases"

[tool.updater]
app_name = "MyApp"
releases_repo = "username/myapp-releases"

[tool.release]
app_name = "MyApp"
releases_repo = "username/myapp-releases"
```

Wszystkie pozostałe wartości zostaną automatycznie wykryte lub użyte domyślne.

---

## Wymagania systemowe

### Oprogramowanie

| Narzędzie | Instalacja | Wymagane przez |
| --------- | ---------- | -------------- |
| **Python 3.9+** | python.org | Wszystkie skrypty |
| **Git** | `winget install Git.Git` | release.py |
| **GitHub CLI** | `winget install GitHub.cli` | release.py |
| **PyInstaller** | `pip install pyinstaller` | release.py |
| **Inno Setup 6** | `winget install JRSoftware.InnoSetup` | release.py |

### Pakiety Python

```bash
# Wymagane
pip install packaging

# Dla Python < 3.11
pip install tomli

# Dla budowania
pip install pyinstaller

# Zależnie od frameworka
pip install PyQt6        # dla pyqt6
pip install customtkinter # dla customtkinter
```

### Autentykacja GitHub

```bash
# Zaloguj się
gh auth login

# Dodaj uprawnienia jeśli brakuje
gh auth refresh -h github.com -s repo,workflow
```

---

## Repozytoria GitHub

### Dlaczego 2 repozytoria?

Skrypty wymagają **2 oddzielnych repozytoriów**:

| Repo | Przykład | Zawartość |
| ---- | -------- | --------- |
| **Source** (origin) | `username/myapp` | Kod źródłowy, commity, tagi |
| **Releases** | `username/myapp-releases` | Instalatory, latest.yml, beta.yml |

**Powody:**

1. **Separacja** - repo z kodem pozostaje lekkie (bez binarek)
2. **Auto-update** - pliki yml muszą być w main branch releases repo
3. **Bezpieczeństwo** - instalatory nie mieszają się z kodem

### Tworzenie repozytoriów

```bash
# 1. Source repo (jeśli nie istnieje)
gh repo create username/myapp --public --source=. --push

# 2. Releases repo (automatycznie przez release.py)
# LUB ręcznie:
gh repo create username/myapp-releases --public --description "MyApp releases"
```

---

## Rozwiązywanie problemów

### setup_installer.py

| Problem | Rozwiązanie |
| ------- | ----------- |
| "PyInstaller not installed" | `pip install pyinstaller` |
| "Inno Setup not found" | `winget install JRSoftware.InnoSetup` lub pobierz z jrsoftware.org |
| "Entry point not found" | Sprawdź `entry_point` w [tool.installer] lub strukturę projektu |
| "Icon not found" | Dodaj plik .ico lub ustaw `icon_path = ""` aby pominąć |

### setup_updater.py

| Problem | Rozwiązanie |
| ------- | ----------- |
| "releases_repo not configured" | Dodaj `releases_repo` w [tool.updater] |
| "src/{app}/core/ not found" | Utwórz strukturę katalogów lub sprawdź nazwę projektu |
| "latest.yml not found" | Normalne dla nowych projektów - pojawi się po pierwszym release |
| "PyQt6/customtkinter not installed" | `pip install PyQt6` lub `pip install customtkinter` |

### release.py

| Problem | Rozwiązanie |
| ------- | ----------- |
| "GitHub CLI not authenticated" | `gh auth login` |
| "Missing GitHub scopes" | `gh auth refresh -h github.com -s repo,workflow` |
| "Tag already exists" | Użyj innej wersji lub usuń tag: `git tag -d vX.Y.Z` |
| "Build failed - PyInstaller" | Sprawdź logi: `build/{app}/warn-{app}.txt` |
| "Build failed - Inno Setup" | Uruchom ręcznie: `ISCC.exe installer/{app}_installer.iss` |

### Ogólne

| Problem | Rozwiązanie |
|---------|-------------|
| "tomli required" | `pip install tomli` (Python < 3.11) |
| "Configuration error" | Sprawdź składnię pyproject.toml |
| "Permission denied" | Uruchom jako administrator lub sprawdź uprawnienia plików |

---

## FAQ

### Czy mogę użyć tylko jednego skryptu?

Tak! Każdy skrypt działa niezależnie:

- `setup_installer.py` - tylko pliki instalatora
- `setup_updater.py` - tylko auto-updater
- `release.py` - wymaga plików wygenerowanych przez setup_installer.py

### Jakie frameworki UI są wspierane?

| Framework | setup_installer.py | setup_updater.py |
|-----------|-------------------|------------------|
| PyQt6 | ✅ (QThread + Signals) | ✅ |
| CustomTkinter | ✅ (threading.Thread) | ✅ |
| CLI | ✅ (console mode) | ✅ (bez dialogu) |

### Jak zmienić język instalatora?

W pyproject.toml:

```toml
[tool.installer]
languages = ["english", "polish", "german", "french"]
```

Dostępne: english, polish, german, french, spanish, italian, russian

### Jak dodać własne hidden imports?

```toml
[tool.installer]
hidden_imports = ["my_module", "another_module"]
```

### Jak zmienić katalog z instalatorami?

```toml
[tool.installer]
release_dir = "dist/installers"
```

### Jak wyłączyć auto-update?

Nie używaj `setup_updater.py` i nie dodawaj kodu sprawdzania aktualizacji.

### Czy muszę mieć releases repo?

Tak, jeśli chcesz:

- Używać auto-updatera
- Wydawać wersje przez release.py

Nie, jeśli budujesz tylko lokalnie.

### Jak zrobić release bez GitHub?

```bash
# Tylko build (bez uploadu)
pyinstaller myapp.spec
ISCC.exe installer/myapp_installer.iss
# Instalator w: release/MyApp_Setup_X.Y.Z.exe
```

---

## Struktura projektu (po inicjalizacji)

```text
projekt/
├── pyproject.toml              # Konfiguracja projektu
├── myapp.spec                  # PyInstaller spec (wygenerowany)
├── file_version_info.txt       # Metadane Windows (wygenerowany)
├── installer/
│   └── myapp_installer.iss     # Inno Setup (wygenerowany)
├── release/
│   ├── MyApp_Setup_1.0.0.exe   # Instalator (po release)
│   ├── latest.yml              # Dla stable (po release)
│   └── beta.yml                # Dla beta (po release)
├── scripts/
│   ├── README.md               # Ta dokumentacja
│   ├── release.py              # Wydawanie wersji
│   ├── setup_installer.py      # Inicjalizacja instalatora
│   └── setup_updater.py        # Inicjalizacja auto-updatera
├── src/
│   └── myapp/
│       ├── __init__.py
│       ├── __main__.py
│       ├── core/
│       │   ├── models.py
│       │   └── updater/        # (wygenerowany)
│       │       ├── __init__.py
│       │       ├── models.py
│       │       ├── update_checker.py
│       │       ├── update_downloader.py
│       │       └── update_manager.py
│       └── ui/
│           └── dialogs/
│               └── update_dialog.py  # (wygenerowany)
└── assets/
    └── myapp_icon.ico
```

---

## Workflow - od zera do release'u

```bash
# 1. Nowy projekt
mkdir myapp && cd myapp
git init

# 2. Skopiuj skrypty
cp -r /path/to/scripts .

# 3. Utwórz pyproject.toml z konfiguracją (patrz wyżej)

# 4. Utwórz strukturę projektu
mkdir -p src/myapp/core src/myapp/ui/dialogs assets

# 5. Dodaj ikonę
# assets/myapp_icon.ico

# 6. Sprawdź i wygeneruj pliki instalatora
python scripts/setup_installer.py --check
python scripts/setup_installer.py --init

# 7. Sprawdź i wygeneruj auto-updater
python scripts/setup_updater.py --check
python scripts/setup_updater.py --init

# 8. Zintegruj auto-updater z aplikacją (patrz instrukcje z --init)

# 9. Sprawdź release
python scripts/release.py --check

# 10. Utwórz repo na GitHub
gh repo create username/myapp --public --source=. --push

# 11. Wydaj pierwszą wersję
python scripts/release.py 1.0.0

# 12. Gotowe! Instalator w release/MyApp_Setup_1.0.0.exe
```

---

## Licencja

MIT - używaj jak chcesz, w dowolnym projekcie.
