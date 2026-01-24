# Inno Setup Installer Template

Uniwersalny szablon instalatora Windows dla aplikacji Electron + Python (i innych).

## Funkcje szablonu

| Funkcja | Opis |
| ------- | ---- |
| **Multi-language** | EN, PL, DE, FR, ES - automatyczne wykrywanie systemu |
| **Custom Pages** | About, SmartScreen, License - informacyjne strony w wizardzie |
| **Per-user Install** | Instalacja do `%LOCALAPPDATA%` - bez uprawnień admina |
| **LZMA2 Ultra** | Maksymalna kompresja - najmniejszy instalator |
| **64-bit** | Tylko systemy x64 (Windows 10/11) |
| **Auto-terminate** | Zamyka aplikację przed instalacją/odinstalowaniem |
| **Registry** | Zapisuje wersję i ścieżkę w rejestrze |

## Szybki start

### 1. Skopiuj szablon

```bash
mkdir installers
cp scripts/templates/innosetup/template.iss installers/{app_name}_installer.iss
```

### 2. Dostosuj wartości

Znajdź i zamień wszystkie `{{PLACEHOLDER}}`:

| Placeholder | Przykład | Opis |
| ----------- | -------- | ---- |
| `{{APP_NAME}}` | `MyApp` | Nazwa aplikacji |
| `{{VERSION}}` | `1.0.0` | Wersja (aktualizowana przez `release.py`) |
| `{{PUBLISHER}}` | `Your Name` | Wydawca |
| `{{APP_URL}}` | `https://github.com/user/app` | URL projektu |
| `{{APP_EXT}}` | `myapp` | Rozszerzenie plików (opcjonalne) |
| `{{XXXXXXXX-...}}` | GUID | Unikalny ID aplikacji |

### 3. Wygeneruj GUID (KRYTYCZNE!)

> **UWAGA: AppId MUSI być unikalny dla każdej aplikacji!**
>
> Jeśli dwa różne projekty mają ten sam AppId, Windows potraktuje je jako tę samą aplikację:
>
> - Instalacja jednej nadpisze drugą
> - Odinstalowanie jednej uszkodzi drugą
> - Wpisy rejestru będą kolidować

**Wygeneruj nowy GUID dla każdego projektu:**

```text
https://www.guidgenerator.com/
```

Format: `{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}`

Wklej w `AppId=` w sekcji `[Setup]`:

```innosetup
[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
```

**NIGDY nie kopiuj AppId z innego projektu!**

### 4. Dostosuj ścieżki plików

W sekcji `[Files]` wskaż źródło plików:

**Dla Electron apps:**

```innosetup
Source: "..\frontend\dist-builder\win-unpacked\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
```

**Dla Python apps:**

```innosetup
Source: "..\dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
```

### 5. Zbuduj instalator

```bash
iscc installers/{app_name}_installer.iss
# Output: release/{APP_NAME}_Setup_{VERSION}.exe
```

---

## Custom Pages (strony wizarda)

Szablon zawiera 3 dodatkowe strony po Welcome:

### 1. About Page

Przedstaw swoją aplikację użytkownikowi.

```innosetup
[CustomMessages]
english.AboutTitle=About MyApp
english.AboutSubtitle=A few words from the author
english.AboutText=Welcome to MyApp!%n%nThis app does...
```

### 2. SmartScreen Page

**WAŻNE dla niepodpisanych aplikacji!**

Informuje użytkownika o ostrzeżeniu Windows SmartScreen i jak je ominąć.

```innosetup
english.SmartScreenTitle=Windows SmartScreen Information
english.SmartScreenText=When you first run MyApp, a blue warning may appear...
```

### 3. License Page

Twoje warunki użytkowania.

```innosetup
english.LicenseTitle=License
english.LicenseText=This software is free...
```

### Kolejność stron

```text
Welcome → About → SmartScreen → License → [Select Destination] → [Installing] → Finish
```

---

## Języki

Szablon obsługuje 5 języków. Inno Setup automatycznie wybiera język systemu.

| Kod | Język |
| --- | ----- |
| `english` | English (domyślny) |
| `polish` | Polski |
| `german` | Deutsch |
| `french` | Français |
| `spanish` | Español |

### Dodanie nowego języka

1. W `[Languages]`:

   ```innosetup
   Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
   ```

2. Dodaj tłumaczenia w `[CustomMessages]`:

   ```innosetup
   italian.AboutTitle=Informazioni su MyApp
   italian.AboutText=Benvenuto in MyApp!...
   ```

### Dostępne języki w Inno Setup

```text
Default.isl (English)
Languages\Polish.isl
Languages\German.isl
Languages\French.isl
Languages\Spanish.isl
Languages\Italian.isl
Languages\Russian.isl
Languages\Japanese.isl
Languages\BrazilianPortuguese.isl
Languages\Dutch.isl
... i więcej
```

---

## Struktura katalogów

```text
project/
├── installers/
│   ├── {app}_installer.iss    # Skrypt instalatora
│   └── assets/
│       ├── icon.ico           # Ikona (256x256)
│       ├── wizard.bmp         # Duży obraz (164x314) - opcjonalny
│       └── wizard_small.bmp   # Mały obraz (55x55) - opcjonalny
├── frontend/
│   └── dist-builder/
│       └── win-unpacked/      # Electron app
├── dist/
│   └── {app}/                 # PyInstaller output
└── release/
    └── {App}_Setup_1.0.0.exe  # Gotowy instalator
```

---

## Integracja z release.py

Skrypt `release.py` automatycznie:

1. **Aktualizuje wersję** w pliku `.iss`:

   ```innosetup
   #define MyAppVersion "1.0.0"
   #define MyAppNumericVersion "1.0.0.0"
   ```

2. **Buduje instalator** po zbudowaniu aplikacji:

   ```bash
   iscc installers/{app}_installer.iss
   ```

3. **Generuje YML** z SHA512 checksum dla auto-updater

### Konfiguracja w pyproject.toml

```toml
[tool.release]
app_name = "MyApp"
releases_repo = "username/myapp-releases"
installer_iss = "installers/myapp_installer.iss"
build_method = "electron"  # lub "innosetup" dla standalone Python
```

---

## Opcje kompresji

Szablon używa maksymalnej kompresji:

```innosetup
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
```

| Opcja | Opis |
| ----- | ---- |
| `lzma2/ultra64` | Najlepsza kompresja, wolniejsze budowanie |
| `lzma2/max` | Bardzo dobra kompresja, szybsze |
| `lzma2/fast` | Szybkie budowanie, większy plik |
| `zip` | Najszybsze, największy plik |

---

## Uprawnienia instalacji

Szablon pozwala na instalację bez uprawnień administratora:

```innosetup
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline
DefaultDirName={localappdata}\Programs\{#MyAppName}
```

| Tryb      | Ścieżka                      | Wymaga admina? |
| --------- | ---------------------------- | -------------- |
| Per-user  | `%LOCALAPPDATA%\Programs\`   | Nie            |
| All users | `C:\Program Files\`          | Tak            |

Użytkownik może wybrać tryb podczas instalacji.

---

## Troubleshooting

| Problem | Rozwiązanie |
| ------- | ----------- |
| "ISCC not found" | Zainstaluj Inno Setup 6: `winget install JRSoftware.InnoSetup` |
| Brak ikony | Sprawdź ścieżkę `SetupIconFile` |
| Pliki nie kopiują się | Sprawdź ścieżki `Source` w `[Files]` |
| Język nie działa | Sprawdź czy plik `.isl` istnieje w Inno Setup |

---

## Przykład: IconHub

Ten szablon powstał na podstawie `installers/iconhub_installer.iss` z projektu IconHub.

IconHub to aplikacja Electron + Python z:

- Niestandardowymi stronami About (z humorem)
- Ostrzeżeniem SmartScreen
- Licencją "zrób co chcesz"
- 5 językami
- Automatycznym zamykaniem przed aktualizacją

Zobacz pełny przykład: [installers/iconhub_installer.iss](../../../installers/iconhub_installer.iss)

---

## Licencja

MIT - używaj w dowolnym projekcie.
