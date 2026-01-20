# Release Script - Instrukcja

Uniwersalny skrypt do automatyzacji wydawania nowych wersji aplikacji desktopowych Windows.

**Skopiuj cały katalog `scripts/` do nowego projektu - skrypt automatycznie skonfiguruje się na podstawie `pyproject.toml`.**

---

## Szybki start

```bash
# 1. Sprawdź czy wszystko jest zainstalowane
python scripts/release.py --check

# 2. Napraw błędy (jeśli są)
pip install pyinstaller packaging tomli
winget install JRSoftware.InnoSetup
gh auth login

# 3. Wydaj nową wersję
python scripts/release.py 1.0.0
```

---

## Wymagania

### Oprogramowanie

| Narzędzie | Instalacja | Opis |
|-----------|------------|------|
| **Python 3.9+** | python.org | Interpreter Pythona |
| **Git** | `winget install Git.Git` | System kontroli wersji |
| **GitHub CLI** | `winget install GitHub.cli` | Tworzenie release'ów |
| **PyInstaller** | `pip install pyinstaller` | Budowanie .exe |
| **Inno Setup 6** | `winget install JRSoftware.InnoSetup` | Budowanie instalatora |

### Pakiety Python

```bash
pip install pyinstaller packaging tomli
```

| Pakiet | Wymagany | Opis |
|--------|----------|------|
| `pyinstaller` | Tak | Pakowanie aplikacji do .exe |
| `packaging` | Tak | Porównywanie wersji (dla auto-update) |
| `tomli` | Python < 3.11 | Parsowanie pyproject.toml |

### Autentykacja GitHub

```bash
# Zaloguj się do GitHub CLI
gh auth login

# Jeśli brakuje uprawnień (repo, workflow)
gh auth refresh -h github.com -s repo,workflow
```

---

## Konfiguracja projektu

### pyproject.toml

Dodaj sekcję `[tool.release]` lub `[tool.spectra]`:

```toml
[project]
name = "myapp"
version = "1.0.0"

[tool.release]
app_name = "MyApp"                           # Nazwa aplikacji
releases_repo = "username/myapp-releases"    # Repo na GitHub dla release'ów
installer_name = "MyApp_Setup_{version}.exe" # Nazwa instalatora
spec_file = "myapp.spec"                     # Plik PyInstaller spec
installer_iss = "installer/myapp_installer.iss"  # Plik Inno Setup
```

### Wymagane pliki projektu

```
projekt/
├── pyproject.toml              # Konfiguracja projektu (WYMAGANE)
├── file_version_info.txt       # Metadane Windows EXE (WYMAGANE)
├── myapp.spec                  # Konfiguracja PyInstaller
├── installer/
│   └── myapp_installer.iss     # Skrypt Inno Setup
├── scripts/
│   ├── release.py              # Ten skrypt
│   └── README.md               # Ta instrukcja
└── release/                    # Output (tworzony automatycznie)
    ├── MyApp_Setup_1.0.0.exe
    ├── latest.yml
    └── beta.yml
```

---

## Użycie

### Sprawdzenie wymagań

```bash
python scripts/release.py --check
python scripts/release.py -c
```

Sprawdza:
- Wersję Pythona
- Zainstalowane pakiety
- Git i konfigurację repo
- GitHub CLI i autentykację
- PyInstaller
- Inno Setup
- Wymagane pliki projektu
- Konfigurację w pyproject.toml
- Istnienie releases repo

### Wydanie wersji

```bash
# Wersja stabilna
python scripts/release.py 1.0.0

# Wersja beta
python scripts/release.py 1.0.0-beta.1

# Symulacja (bez zmian)
python scripts/release.py 1.0.0 --dry-run

# Bez potwierdzeń
python scripts/release.py 1.0.0 --force
```

### Opcje

| Opcja | Skrót | Opis |
|-------|-------|------|
| `--check` | `-c` | Sprawdź wymagania |
| `--dry-run` | `-d` | Symulacja bez zmian |
| `--force` | `-f` | Pomiń potwierdzenia |

---

## Co robi skrypt

### Krok 1: Walidacja
- Sprawdza format wersji (x.y.z lub x.y.z-beta.n)
- Sprawdza czy tag nie istnieje
- Sprawdza status git
- Sprawdza GitHub CLI
- Tworzy releases repo jeśli nie istnieje

### Krok 2: Aktualizacja wersji
Aktualizuje wersję w plikach:
- `pyproject.toml` - `version = "x.y.z"`
- `installer/*.iss` - `#define MyAppVersion "x.y.z"`
- `file_version_info.txt` - `filevers=(x, y, z, 0)`

### Krok 3: Build
1. Czyści poprzedni build (`dist/`, `build/`)
2. Uruchamia PyInstaller
3. Uruchamia Inno Setup

### Krok 4: Generowanie YML
Tworzy pliki dla auto-update:
- `release/latest.yml` - dla kanału stable
- `release/beta.yml` - dla kanału beta

Zawierają:
- Wersję
- Nazwę pliku instalatora
- Hash SHA512 (base64)
- Rozmiar pliku
- Datę wydania

### Krok 5: Commit i tag
```bash
git add pyproject.toml installer/*.iss file_version_info.txt release/*.yml
git commit -m "release: v1.0.0"
git tag -a "v1.0.0" -m "Release 1.0.0"
```

### Krok 6: Push
```bash
git push origin
git push origin v1.0.0
```

### Krok 7: GitHub Release
- Tworzy release w repo `releases_repo`
- Uploaduje instalator i pliki yml
- Generuje automatyczne release notes

### Krok 8: Push YML do releases repo
- Klonuje releases repo
- Kopiuje latest.yml i beta.yml
- Commituje i pushuje

**To jest kluczowe dla auto-update!** Pliki yml muszą być w branchu `main` releases repo, nie tylko jako assety release'u.

---

## Auto-Update

### Jak działa

1. Aplikacja sprawdza `https://raw.githubusercontent.com/{releases_repo}/main/latest.yml`
2. Porównuje wersję z aktualną
3. Jeśli jest nowsza - pokazuje dialog
4. Pobiera instalator z GitHub Release
5. Weryfikuje SHA512
6. Uruchamia instalator

### Kanały aktualizacji

| Kanał | Plik YML | Opis |
|-------|----------|------|
| Stable | `latest.yml` | Tylko stabilne wersje (x.y.z) |
| Beta | `beta.yml` | Wszystkie wersje (w tym beta) |

### Logika aktualizacji YML

| Typ wydania | latest.yml | beta.yml |
|-------------|------------|----------|
| Stable (1.0.0) | Aktualizowany | Aktualizowany |
| Beta (1.0.0-beta.1) | Bez zmian | Aktualizowany |

---

## Repozytoria

### Source repo (origin)
- Kod źródłowy
- Commity i tagi wersji
- **NIE** uploaduj instalatorów

### Releases repo
- GitHub Releases z instalatorami
- Pliki `latest.yml` i `beta.yml` w branchu `main`
- **NIE** pushuj kodu źródłowego (`git push`)
- Używaj **tylko** `gh release create`

---

## Rozwiązywanie problemów

### "GitHub CLI not authenticated"
```bash
gh auth login
```

### "Missing GitHub scopes"
```bash
gh auth refresh -h github.com -s repo,workflow
```

### "Inno Setup not found"
```bash
winget install JRSoftware.InnoSetup
```
Lub pobierz z: https://jrsoftware.org/isdl.php

### "PyInstaller not installed"
```bash
pip install pyinstaller
```

### "tomli required for Python < 3.11"
```bash
pip install tomli
```

### "Tag already exists"
Tag `vX.Y.Z` już istnieje. Użyj innej wersji lub usuń tag:
```bash
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0
```

### "releases_repo not configured"
Dodaj do `pyproject.toml`:
```toml
[tool.release]
releases_repo = "username/appname-releases"
```

### Build failed - PyInstaller
- Sprawdź czy `spec_file` istnieje
- Uruchom PyInstaller ręcznie: `python -m PyInstaller myapp.spec`
- Sprawdź logi w `build/myapp/warn-myapp.txt`

### Build failed - Inno Setup
- Sprawdź czy `installer_iss` istnieje
- Sprawdź czy Inno Setup jest zainstalowany
- Uruchom ISCC ręcznie: `ISCC.exe installer/myapp_installer.iss`

---

## Przenoszenie do nowego projektu

1. **Skopiuj katalog `scripts/`** do nowego projektu

2. **Dodaj konfigurację** do `pyproject.toml`:
   ```toml
   [tool.release]
   app_name = "NowaAplikacja"
   releases_repo = "username/nowaaplikacja-releases"
   ```

3. **Utwórz wymagane pliki**:
   - `file_version_info.txt` - metadane Windows EXE
   - `nowaaplikacja.spec` - konfiguracja PyInstaller
   - `installer/nowaaplikacja_installer.iss` - skrypt Inno Setup

4. **Sprawdź wymagania**:
   ```bash
   python scripts/release.py --check
   ```

5. **Napraw błędy** i wydaj pierwszą wersję:
   ```bash
   python scripts/release.py 1.0.0
   ```

---

## Struktura pliku YML

```yaml
version: 1.0.0
files:
  - url: MyApp_Setup_1.0.0.exe
    sha512: aZbLkld4HfSUq3Pqxg178mj3NmvEYzGin61sq0qmstTvMk70Of/+l+9+I7IBtJnoisSvV4kiGbUdIWeqr/B6pQ==
    size: 19844635
path: MyApp_Setup_1.0.0.exe
sha512: aZbLkld4HfSUq3Pqxg178mj3NmvEYzGin61sq0qmstTvMk70Of/+l+9+I7IBtJnoisSvV4kiGbUdIWeqr/B6pQ==
releaseDate: '2026-01-20T12:00:00.000000+00:00'
```

---

## Licencja

MIT - używaj jak chcesz, w dowolnym projekcie.
