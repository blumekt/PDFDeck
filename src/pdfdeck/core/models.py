"""
Modele danych dla PDFDeck.

Zawiera dataclassy używane w całej aplikacji.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional, Tuple


# === Typy podstawowe ===

@dataclass
class Point:
    """Punkt 2D w układzie współrzędnych PDF."""
    x: float
    y: float


@dataclass
class Rect:
    """Prostokąt w układzie współrzędnych PDF."""
    x0: float  # left
    y0: float  # top
    x1: float  # right
    y1: float  # bottom

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def as_tuple(self) -> Tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)


# === Informacje o stronie ===

@dataclass
class PageInfo:
    """Metadane strony PDF."""
    index: int
    width: float
    height: float
    rotation: int = 0


# === Konfiguracje operacji ===

@dataclass
class WhiteoutConfig:
    """Konfiguracja operacji Whiteout & Type."""
    rect: Rect
    text: str = ""
    font_name: str = "helv"
    font_size: float = 12.0
    text_color: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # RGB 0-1
    fill_color: Tuple[float, float, float] = (1.0, 1.0, 1.0)  # White


@dataclass
class LinkConfig:
    """Konfiguracja hiperłącza."""
    rect: Rect
    link_type: str = "url"  # "url", "page", "file"
    uri: Optional[str] = None  # Dla linków zewnętrznych i plików
    target_page: Optional[int] = None  # Dla linków wewnętrznych
    target_point: Optional[Point] = None
    display_text: Optional[str] = None  # Opcjonalny tekst wyświetlany
    add_underline: bool = True  # Czy dodać podkreślenie (adnotację)
    add_border: bool = False  # Czy dodać ramkę wokół obszaru


@dataclass
class LinkInfo:
    """Informacje o istniejącym linku w dokumencie."""
    index: int  # Indeks linku na stronie
    rect: Rect
    link_type: str  # "url", "page", "file", "unknown"
    uri: Optional[str] = None  # Adres URL lub ścieżka pliku
    target_page: Optional[int] = None  # Numer strony docelowej (0-indexed)
    raw_dict: Optional[dict] = None  # Oryginalny słownik PyMuPDF

    @property
    def display_label(self) -> str:
        """Czytelna etykieta linku do wyświetlenia w UI."""
        if self.link_type == "url" and self.uri:
            # Skróć długie URL-e
            if len(self.uri) > 50:
                return self.uri[:47] + "..."
            return self.uri
        elif self.link_type == "page" and self.target_page is not None:
            return f"Strona {self.target_page + 1}"
        elif self.link_type == "file" and self.uri:
            from pathlib import Path
            return Path(self.uri).name
        return "Nieznany link"

    @property
    def type_label(self) -> str:
        """Etykieta typu linku."""
        type_labels = {
            "url": "URL",
            "page": "Wewnętrzny",
            "file": "Plik",
            "unknown": "Inny"
        }
        return type_labels.get(self.link_type, "Inny")


@dataclass
class WatermarkConfig:
    """Konfiguracja znaku wodnego."""
    text: str
    font_size: float = 72.0
    color: Tuple[float, float, float] = (0.5, 0.5, 0.5)  # Gray
    rotation: float = 45.0  # Stopnie
    opacity: float = 0.3  # 0.0 - 1.0
    overlay: bool = True  # True = zawsze ponad zawartością


# === Pieczątki - enumy i konfiguracja ===

class StampShape(Enum):
    """Kształt pieczątki."""
    RECTANGLE = auto()
    CIRCLE = auto()
    OVAL = auto()
    ROUNDED_RECT = auto()


class BorderStyle(Enum):
    """Styl ramki pieczątki."""
    SOLID = auto()
    DOUBLE = auto()
    DASHED = auto()
    THICK = auto()
    THIN = auto()


class WearLevel(Enum):
    """Poziom efektu zużycia pieczątki."""
    NONE = auto()
    LIGHT = auto()
    MEDIUM = auto()
    HEAVY = auto()


@dataclass
class StampConfig:
    """Konfiguracja pieczątki."""
    # === Treść ===
    text: str = ""
    circular_text: Optional[str] = None  # Tekst po obwodzie (dla okrągłych)

    # === Pozycja i transformacja ===
    position: Point = field(default_factory=lambda: Point(100, 100))
    rotation: float = 0.0  # Rotacja w stopniach
    rotation_random: bool = True  # True = losowa rotacja +/- 2°, False = dokładna rotacja
    corner: str = "center"  # Narożnik: top-left, top-center, top-right, center, bottom-left, bottom-center, bottom-right
    scale: float = 1.0

    # === Kształt i styl ===
    shape: StampShape = StampShape.RECTANGLE
    border_style: BorderStyle = BorderStyle.SOLID
    border_width: float = 2.0

    # === Kolory (RGB 0-1) ===
    color: Tuple[float, float, float] = (0.9, 0.1, 0.1)
    fill_color: Optional[Tuple[float, float, float]] = None

    # === Efekty ===
    opacity: float = 1.0  # 0.0 - 1.0
    wear_level: WearLevel = WearLevel.NONE
    vintage_effect: bool = False  # Efekt starodruku (letterpress)
    double_strike: bool = False  # Podwójne odbicie (przesunięte)
    ink_splatter: bool = False  # Rozbryzgi tuszu wokół pieczątki
    auto_date: bool = False  # Automatyczna data w tekście

    # === Rozmiary (w punktach PDF) ===
    width: float = 150.0
    height: float = 60.0
    font_size: float = 24.0
    circular_font_size: float = 10.0

    # === Legacy (kompatybilność wsteczna) ===
    stamp_path: Optional[Path] = None  # Dla zewnętrznych plików SVG/PNG


@dataclass
class RedactionConfig:
    """Konfiguracja redakcji."""
    pattern: str
    is_regex: bool = False
    color: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # Black
    apply_to_all_pages: bool = True


# === Wyniki wyszukiwania ===

@dataclass
class SearchResult:
    """Wynik wyszukiwania tekstu."""
    page_index: int
    rect: Rect
    text: str


@dataclass
class RedactionMatch:
    """Dopasowanie do redakcji."""
    page_index: int
    rect: Rect
    matched_text: str
    pattern: str


@dataclass
class WordBounds:
    """Granice słowa z pozycją na stronie (dla interaktywnego zaznaczania)."""
    text: str
    rect: Rect
    block_no: int
    line_no: int
    word_no: int


# === Analiza dokumentu ===

class PreflightIssueType(Enum):
    """Typ problemu wykrytego przez Preflight Check."""
    EMPTY_PAGE = auto()
    LOW_RESOLUTION_IMAGE = auto()
    MISSING_FONT = auto()
    BROKEN_LINK = auto()
    LARGE_FILE_SIZE = auto()
    UNEMBEDDED_FONT = auto()


@dataclass
class PreflightIssue:
    """Problem wykryty przez Preflight Check."""
    issue_type: PreflightIssueType
    page_index: Optional[int]
    description: str
    severity: str = "warning"  # "info", "warning", "error"


@dataclass
class TableData:
    """Dane wyekstrahowanej tabeli."""
    page_index: int
    bbox: Rect
    rows: int
    cols: int
    data: List[List[str]] = field(default_factory=list)


@dataclass
class Heading:
    """Nagłówek wykryty w dokumencie (do automatycznych zakładek)."""
    page_index: int
    text: str
    level: int  # 1 = główny, 2 = podtytuł, etc.
    font_size: float
    rect: Rect


# === Metadane dokumentu ===

@dataclass
class DocumentMetadata:
    """Metadane dokumentu PDF."""
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None


# === N-up i formatowanie ===

class PageSize(Enum):
    """Standardowe rozmiary stron."""
    A4 = (595.276, 841.890)  # 210mm x 297mm w punktach
    A3 = (841.890, 1190.551)
    LETTER = (612, 792)
    LEGAL = (612, 1008)


@dataclass
class NupConfig:
    """Konfiguracja układu N-up."""
    pages_per_sheet: int = 2  # 2, 4, 6, 8, 9, 16
    output_size: PageSize = PageSize.A4
    landscape: bool = False
    maintain_aspect_ratio: bool = True
    add_borders: bool = False


# === Bulk operations ===

@dataclass
class FormFieldMapping:
    """Mapowanie pola formularza na kolumnę CSV."""
    field_name: str
    csv_column: str
    default_value: str = ""


@dataclass
class BulkFillConfig:
    """Konfiguracja seryjnego wypełniania formularzy."""
    template_path: Path
    csv_path: Path
    output_dir: Path
    field_mappings: List[FormFieldMapping] = field(default_factory=list)
    filename_pattern: str = "output_{index}.pdf"


# === Auto-updater ===

class UpdateChannel(Enum):
    """Kanał aktualizacji."""
    STABLE = auto()
    BETA = auto()


@dataclass
class UpdateInfo:
    """Informacje o dostępnej aktualizacji."""
    version: str
    download_url: str
    sha512: str
    size: int
    release_date: datetime
    filename: str

    @property
    def size_mb(self) -> float:
        """Rozmiar w MB."""
        return self.size / 1024 / 1024


@dataclass
class UpdateCheckResult:
    """Wynik sprawdzenia aktualizacji."""
    update_available: bool
    current_version: str
    latest_version: str
    update_info: Optional[UpdateInfo] = None
    error: Optional[str] = None
