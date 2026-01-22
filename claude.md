# PDFDeck - Project Instructions for Claude

## Język komunikacji

**Zawsze pisz do użytkownika po polsku.**

## Styl komunikacji

- Dawaj eksperckie, trafne odpowiedzi - nawet jeśli nie zgadzają się z rozumowaniem użytkownika
- Ogranicz entuzjazm i automatyczne zgadzanie się ze wszystkim
- Bądź sceptycznie nastawiony do odpowiedzi użytkownika - weryfikuj założenia
- Pamiętaj: ani użytkownik, ani Ty nie zawsze macie rację
- Gdy nie jesteś pewien - zadawaj pytania i rób własny research

## Build Requirements

**WAŻNE:** Po każdej zmianie w kodzie, zawsze testuj aplikację:

```bash
# Uruchom aplikację (development)
python -m pdfdeck

# Lub po instalacji
pdfdeck

# Instalacja w trybie dev (z zależnościami developerskimi)
pip install -e ".[dev]"
```

## Recent Changes

### 2025-01-22: Fix responsywności slidera rozmiaru dla pieczątek z pliku

- **Problem:** Slider rozmiaru nie działał responsywnie - zmiany były praktycznie niewidoczne
- **Root cause:** Zbyt duży mnożnik `size * 8` (domyślnie 48pt * 8 = 384pt = 13.5cm)
- **Fix:** Zmniejszenie mnożnika z 8 do 4 we wszystkich miejscach ([stamp_picker.py:916](src/pdfdeck/ui/widgets/stamp_picker.py#L916), [watermark_page.py:408,520,1071](src/pdfdeck/ui/pages/watermark_page.py#L408))
- **Rezultat:** Spójność z dynamicznymi pieczątkami (również `size * 4`) i bardziej responsywny slider
- **Backward compatibility:** Istniejące profile zachowają zapisane wymiary (width/height), więc zmiana nie wpłynie na załadowane profile

### 2025-01-22: Fix rotacji pieczątek i znaków wodnych

- **Problem:** Podgląd (PyQt6) i PDF (PIL) pokazywały rotację w przeciwnych kierunkach
- **Root cause:** PyQt6 `setRotation()` używa clockwise, a PIL `Image.rotate()` używa counter-clockwise
- **Fix:** Negacja rotacji w podglądzie PyQt6 ([watermark_page.py:443,875](src/pdfdeck/ui/pages/watermark_page.py#L443))
- **Konwencja:** Dodatnie wartości = counter-clockwise (w lewo) - matematyczny standard PIL
- **Backward compatibility:** Feature był nowy (2 dni), prawdopodobnie zero użytkowników dotkniętych

## Project Structure

```text
PDFDeck/
├── pyproject.toml              # Główna konfiguracja projektu
├── scripts/
│   ├── release.py              # Skrypt automatyzacji releasu
│   └── README.md               # Dokumentacja release scriptu
├── resources/
│   ├── icons/                  # Ikony aplikacji
│   ├── stamps/                 # Szablony pieczątek
│   └── styles/                 # Arkusze stylów QSS (dark_theme.qss)
├── src/
│   └── pdfdeck/
│       ├── __init__.py         # Inicjalizacja pakietu, wersja
│       ├── __main__.py         # Entry point
│       ├── app.py              # Inicjalizacja PyQt6
│       ├── core/
│       │   ├── models.py       # Modele danych (dataclasses)
│       │   └── pdf_manager.py  # Operacje na PDF (PyMuPDF)
│       ├── ui/
│       │   ├── dialogs/        # Komponenty dialogów
│       │   ├── pages/          # Panele/strony UI
│       │   └── widgets/        # Własne widgety
│       └── utils/              # Funkcje pomocnicze
└── tests/                      # Testy (pytest)
```

## Technical Stack

- **Language:** Python 3.10+ (wspiera 3.10, 3.11, 3.12)
- **GUI:** PyQt6 6.6.0+
- **PDF Engine:** PyMuPDF (fitz) 1.24.0+
- **Testing:** pytest 8.0.0+ / pytest-qt 4.2.0+
- **Linting:** ruff 0.1.0+
- **Type Checking:** mypy 1.0.0+
- **Packaging:** PyInstaller + Inno Setup 6

## Supported PDF Operations

PDFDeck obsługuje zaawansowane operacje na plikach PDF:

### Zarządzanie dokumentem

- Ładowanie/zapisywanie PDF
- Zmiana kolejności stron, usuwanie
- Łączenie i dzielenie dokumentów
- Generowanie miniatur i podglądu

### Edycja treści

- **Whiteout & Type** - Zakrywanie tekstu i wpisywanie nowego
- **Wyszukiwanie tekstu** - Z obsługą regex
- **Redakcja** - Trwałe usuwanie treści z PDF
- **Watermarki** - Znaki wodne z rotacją i przezroczystością
- **Pieczątki** - Obrazy na stronach
- **Zamiana obrazów** - Podmiana grafik w PDF
- **Linki** - Zewnętrzne (URI) i wewnętrzne (do strony)

### Analiza dokumentu

- **Preflight Check** - Wykrywanie problemów (puste strony, niska rozdzielczość, uszkodzone linki)
- **Ekstrakcja tabel** - Wyciąganie danych tabelarycznych
- **Wykrywanie nagłówków** - Na podstawie rozmiaru fontu
- **Metadane** - Podgląd, edycja, usuwanie
- **Auto-zakładki** - Generowanie spisu treści

### Formatowanie

- **Normalizacja do A4** - Konwersja wszystkich stron
- **N-up Layout** - Wiele stron na arkusz (2, 4, 6, 8, 9, 16)

### Operacje masowe

- **Wypełnianie formularzy** - Z pliku CSV

## Architecture

### Wzorzec Model-View

1. **Core Layer** (`pdfdeck.core`):
   - `PDFManager` - Wszystkie operacje PDF (PyMuPDF)
   - `models.py` - Obiekty transferu danych (dataclasses)
   - Logika biznesowa oddzielona od UI

2. **UI Layer** (`pdfdeck.ui`):
   - `dialogs/` - Komponenty modalne
   - `pages/` - Główne panele aplikacji
   - `widgets/` - Reużywalne widgety

3. **Utils** (`pdfdeck.utils`):
   - Funkcje pomocnicze
   - Ładowanie zasobów

### Kluczowe modele danych

```python
# Geometria
Point, Rect

# Wyniki operacji
PageInfo, SearchResult, RedactionMatch

# Konfiguracje operacji
WhiteoutConfig, LinkConfig, WatermarkConfig, StampConfig, RedactionConfig

# Analiza
DocumentMetadata, PreflightIssue, TableData, Heading

# Layout/bulk
NupConfig, BulkFillConfig
```

### Bezpieczeństwo wątków

- `PDFManager` jest thread-safe dla operacji odczytu
- Operacje zapisu powinny być z głównego wątku

## Development Commands

```bash
# Uruchom aplikację
python -m pdfdeck

# Zainstaluj z zależnościami dev
pip install -e ".[dev]"

# Linting (ruff)
ruff check src/

# Formatowanie (ruff)
ruff format src/

# Type checking (mypy)
mypy src/

# Testy
pytest tests/
```

## Code Quality Configuration

```toml
# ruff
line-length = 100
target-version = "py310"
select = ["E", "F", "W", "I", "N", "UP", "B", "C4"]
ignore = ["E501"]

# mypy
ignore_missing_imports = true
```

## GitHub Repositories

Projekt używa dwóch repozytoriów:

| Repo         | URL                                      | Przeznaczenie              |
|--------------|------------------------------------------|----------------------------|
| **origin**   | `github.com/blumekt/PDFDeck`             | Kod źródłowy               |
| **releases** | `github.com/blumekt/PDFDeck-releases`    | Releasy i pliki auto-update|

**⚠️ WAŻNE:** Do repo `PDFDeck-releases` NIGDY nie pushuj kodu źródłowego. To repo służy TYLKO do GitHub Releases z plikami instalacyjnymi.

### Release Script (PREFEROWANA METODA)

Projekt posiada kompleksowy skrypt `scripts/release.py` który automatyzuje CAŁY proces wydawania nowej wersji.

```bash
# Sprawdź wymagania
python scripts/release.py --check

# Test bez zmian (dry-run)
python scripts/release.py 1.0.0 --dry-run

# Prawdziwy release (stable)
python scripts/release.py 1.0.0

# Release beta
python scripts/release.py 1.0.0-beta.1

# Bez potwierdzeń (force)
python scripts/release.py 1.0.0 --force
```

**Co robi skrypt:**

1. Waliduje wersję i sprawdza wymagania (git, gh CLI, Inno Setup, PyInstaller)
2. Aktualizuje wersję w `pyproject.toml`, `installer.iss`, `file_version_info.txt`
3. Buduje: PyInstaller (.exe) → Inno Setup (installer)
4. Generuje `latest.yml`/`beta.yml` z prawidłowym SHA512 (base64)
5. Commit + tag + push do origin
6. Tworzy GitHub Release w `blumekt/PDFDeck-releases` z załącznikami

**Logika beta vs stable:**

| Typ                 | latest.yml       | beta.yml         |
|---------------------|------------------|------------------|
| Stable (1.0.0)      | ✅ aktualizowany | ✅ aktualizowany |
| Beta (1.0.0-beta.1) | ❌ bez zmian     | ✅ aktualizowany |

## Theme System

- Domyślny ciemny motyw (`dark_theme.qss`)
- Tło: `#16213e`, tekst: biały
- Font: Segoe UI

## Development Guidelines

### Przy zmianach w kodzie

1. Testuj uruchamiając `python -m pdfdeck`
2. Sprawdź czy mypy i ruff nie zgłaszają błędów
3. Testuj różne operacje na PDF
4. Uruchom testy `pytest tests/`

### Debugging

- PyQt6 ma wbudowane logi w konsoli
- Używaj `print()` lub `logging` do debugowania
- Sprawdzaj wyjątki PyMuPDF

## Common Issues

**Aplikacja nie uruchamia się:**

- Sprawdź czy PyQt6 jest zainstalowane: `pip install PyQt6`
- Sprawdź wersję Pythona: `python --version` (wymaga 3.10+)

**Operacje PDF nie działają:**

- Sprawdź czy PyMuPDF jest zainstalowane: `pip install pymupdf`
- Upewnij się że plik PDF nie jest uszkodzony

**Build fails:**

- Usuń `build/`, `dist/` i spróbuj ponownie
- Sprawdź czy PyInstaller jest zainstalowany

## Workflow dla nowych funkcji

1. Zaimplementuj logikę w odpowiednim miejscu:
   - Operacje PDF → `src/pdfdeck/core/pdf_manager.py`
   - Modele danych → `src/pdfdeck/core/models.py`
   - UI/dialogi → `src/pdfdeck/ui/`
2. Dodaj type hints (wymagane przez mypy)
3. Przetestuj ręcznie uruchamiając aplikację
4. Uruchom `ruff check` i `mypy`
5. Napisz testy jeśli to możliwe
6. Commituj zmiany

## Configuration

### OCR API Key

PDFDeck używa OCR.space API do rozpoznawania tekstu. Domyślnie używany jest demo key `"helloworld"` który ma bardzo ograniczone limity.

**Jak uzyskać własny darmowy klucz API:**

1. Odwiedź <https://ocr.space/ocrapi>
2. Zarejestruj się (darmowe konto daje 25,000 zapytań/miesiąc)
3. Skopiuj swój klucz API
4. W PDFDeck:
   - Przejdź do **Ustawienia** (sidebar)
   - W sekcji "Klucze API" wpisz swój klucz
   - Kliknij **Zapisz**

**Gdzie jest przechowywany klucz:**

- Windows: `C:\Users\<username>\.pdfdeck\settings.json`
- Linux/Mac: `~/.pdfdeck/settings.json`

Klucz jest automatycznie ładowany przy każdym uruchomieniu aplikacji i używany w funkcji OCR.

## Application Metadata

| Property    | Value                       |
|-------------|-----------------------------|
| Name        | PDFDeck                     |
| Version     | 0.1.0 (Alpha)               |
| Author      | PDFDeck Team                |
| License     | MIT                         |
| Entry Point | `pdfdeck.__main__:main`     |
