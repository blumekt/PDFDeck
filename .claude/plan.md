# Plan: Zarządzanie linkami w PDFDeck

## Cel
Dodanie pełnej obsługi linków: pobieranie listy, edytowanie, usuwanie.

## Zidentyfikowane problemy
1. Model `LinkConfig` nie ma pól `link_type` i `display_text` (a dialog ich używa)
2. `PDFManager` ma tylko `insert_link()` - brak get/delete/update
3. Brak UI do zarządzania istniejącymi linkami

---

## Plan implementacji

### Krok 1: Rozszerzenie modelu danych (`models.py`)

**A) Zaktualizować `LinkConfig`** - dodać brakujące pola:
```python
@dataclass
class LinkConfig:
    rect: Rect
    link_type: str = "url"  # "url", "page", "file"
    uri: Optional[str] = None
    target_page: Optional[int] = None
    target_point: Optional[Point] = None
    display_text: Optional[str] = None
```

**B) Dodać nowy model `LinkInfo`** - reprezentacja istniejącego linku:
```python
@dataclass
class LinkInfo:
    index: int  # Indeks linku na stronie
    rect: Rect
    link_type: str  # "url", "page", "file", "unknown"
    uri: Optional[str] = None
    target_page: Optional[int] = None
    raw_dict: Optional[dict] = None  # Oryginalny słownik PyMuPDF
```

---

### Krok 2: Metody w `PDFManager` (`pdf_manager.py`)

**A) `get_page_links(page_index: int) -> List[LinkInfo]`**
- Wywołuje `page.get_links()`
- Konwertuje słowniki PyMuPDF na obiekty `LinkInfo`
- Mapuje typy: LINK_URI → "url", LINK_GOTO → "page", LINK_LAUNCH → "file"

**B) `delete_link(page_index: int, link_index: int) -> None`**
- Pobiera linki przez `get_links()`
- Usuwa link o podanym indeksie przez `page.delete_link(link_dict)`

**C) `update_link(page_index: int, link_index: int, config: LinkConfig) -> None`**
- Usuwa stary link (`delete_link`)
- Wstawia nowy (`insert_link`)

---

### Krok 3: Nowy dialog `LinkManagerDialog` (`ui/dialogs/link_manager_dialog.py`)

**Funkcjonalność:**
- Lista linków na bieżącej stronie (QListWidget lub QTableWidget)
- Przycisk "Usuń" - usuwa zaznaczony link
- Przycisk "Edytuj" - otwiera LinkDialog z wypełnionymi danymi
- Przycisk "Dodaj" - otwiera pusty LinkDialog

**Struktura UI:**
```
┌─────────────────────────────────────────┐
│ Zarządzanie linkami - Strona X          │
├─────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐ │
│ │ 1. https://example.com   [URL]      │ │
│ │ 2. Strona 5              [Wewnętrzny]│ │
│ │ 3. C:\doc.pdf            [Plik]     │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ [Dodaj]  [Edytuj]  [Usuń]    [Zamknij] │
└─────────────────────────────────────────┘
```

---

### Krok 4: Modyfikacja `LinkDialog`

- Dodać tryb edycji (wypełnienie istniejącymi danymi)
- Konstruktor: `__init__(self, rect, max_pages, existing_config=None, parent=None)`
- Jeśli `existing_config` podany → wypełnij pola i zmień tytuł na "Edytuj link"

---

### Krok 5: Integracja z UI

Opcja A: Dodać przycisk "Zarządzaj linkami" w panelu edycji
Opcja B: Dodać do menu kontekstowego miniatur stron

---

## Pliki do modyfikacji

| Plik | Zmiany |
|------|--------|
| `src/pdfdeck/core/models.py` | Dodać `LinkInfo`, rozszerzyć `LinkConfig` |
| `src/pdfdeck/core/pdf_manager.py` | Dodać `get_page_links()`, `delete_link()`, `update_link()` |
| `src/pdfdeck/ui/dialogs/link_dialog.py` | Tryb edycji |
| `src/pdfdeck/ui/dialogs/link_manager_dialog.py` | **NOWY** - główny dialog zarządzania |
| `src/pdfdeck/ui/dialogs/__init__.py` | Export nowego dialogu |
| Panel UI (do ustalenia) | Przycisk wywołujący LinkManagerDialog |

---

## Kolejność implementacji

1. `models.py` - modele danych (fundament)
2. `pdf_manager.py` - logika biznesowa
3. `link_dialog.py` - tryb edycji
4. `link_manager_dialog.py` - nowy dialog
5. Integracja z UI
6. Testy manualne
