"""
HeaderFooterEngine - Nagłówki, stopki i numeracja stron.

Funkcje:
- Dodawanie nagłówków i stopek
- Szablony z placeholderami ({page}, {total}, {date})
- Pomijanie pierwszej strony
- Różne nagłówki dla parzystych/nieparzystych
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Callable, Dict

import fitz  # PyMuPDF


class HorizontalAlignment(Enum):
    """Wyrównanie poziome."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class VerticalPosition(Enum):
    """Pozycja pionowa."""
    TOP = "top"
    BOTTOM = "bottom"


@dataclass
class HeaderFooterConfig:
    """Konfiguracja nagłówka/stopki."""

    # Nagłówek
    header_left: str = ""
    header_center: str = ""
    header_right: str = ""

    # Stopka
    footer_left: str = ""
    footer_center: str = "{page} / {total}"
    footer_right: str = ""

    # Czcionka
    font_name: str = "helv"
    font_size: float = 10
    font_color: tuple = (0, 0, 0)  # RGB 0-1

    # Margines od krawędzi (w punktach)
    margin_top: float = 36  # 0.5 inch
    margin_bottom: float = 36
    margin_left: float = 36
    margin_right: float = 36

    # Opcje
    skip_first: bool = False
    different_odd_even: bool = False

    # Nagłówki/stopki dla stron parzystych (jeśli different_odd_even=True)
    even_header_left: str = ""
    even_header_center: str = ""
    even_header_right: str = ""
    even_footer_left: str = ""
    even_footer_center: str = "{page} / {total}"
    even_footer_right: str = ""


@dataclass
class HeaderFooterResult:
    """Wynik dodania nagłówków/stopek."""
    success: bool
    pages_processed: int
    pages_skipped: int
    message: str = ""


class HeaderFooterEngine:
    """
    Silnik do dodawania nagłówków i stopek.

    Obsługuje szablony:
    - {page} - numer bieżącej strony
    - {total} - całkowita liczba stron
    - {date} - bieżąca data (YYYY-MM-DD)
    - {time} - bieżący czas (HH:MM)
    - {datetime} - data i czas
    - {filename} - nazwa pliku
    """

    def __init__(self):
        self._filename = "document.pdf"

    def apply(
        self,
        doc: fitz.Document,
        config: HeaderFooterConfig,
        filename: Optional[str] = None
    ) -> HeaderFooterResult:
        """
        Dodaje nagłówki i stopki do dokumentu.

        Args:
            doc: Dokument PDF
            config: Konfiguracja nagłówka/stopki
            filename: Nazwa pliku (opcjonalnie)

        Returns:
            HeaderFooterResult z wynikiem operacji
        """
        if filename:
            self._filename = filename

        total_pages = len(doc)
        pages_processed = 0
        pages_skipped = 0

        try:
            for page_num, page in enumerate(doc):
                # Pomijanie pierwszej strony
                if config.skip_first and page_num == 0:
                    pages_skipped += 1
                    continue

                # Wybierz nagłówki/stopki dla parzystych/nieparzystych
                is_even = (page_num + 1) % 2 == 0

                if config.different_odd_even and is_even:
                    header_left = config.even_header_left
                    header_center = config.even_header_center
                    header_right = config.even_header_right
                    footer_left = config.even_footer_left
                    footer_center = config.even_footer_center
                    footer_right = config.even_footer_right
                else:
                    header_left = config.header_left
                    header_center = config.header_center
                    header_right = config.header_right
                    footer_left = config.footer_left
                    footer_center = config.footer_center
                    footer_right = config.footer_right

                rect = page.rect

                # === Nagłówek ===
                y_header = config.margin_top

                if header_left:
                    text = self._expand_template(header_left, page_num, total_pages)
                    self._insert_text(
                        page, text, config.margin_left, y_header,
                        HorizontalAlignment.LEFT, config
                    )

                if header_center:
                    text = self._expand_template(header_center, page_num, total_pages)
                    self._insert_text(
                        page, text, rect.width / 2, y_header,
                        HorizontalAlignment.CENTER, config
                    )

                if header_right:
                    text = self._expand_template(header_right, page_num, total_pages)
                    self._insert_text(
                        page, text, rect.width - config.margin_right, y_header,
                        HorizontalAlignment.RIGHT, config
                    )

                # === Stopka ===
                y_footer = rect.height - config.margin_bottom

                if footer_left:
                    text = self._expand_template(footer_left, page_num, total_pages)
                    self._insert_text(
                        page, text, config.margin_left, y_footer,
                        HorizontalAlignment.LEFT, config
                    )

                if footer_center:
                    text = self._expand_template(footer_center, page_num, total_pages)
                    self._insert_text(
                        page, text, rect.width / 2, y_footer,
                        HorizontalAlignment.CENTER, config
                    )

                if footer_right:
                    text = self._expand_template(footer_right, page_num, total_pages)
                    self._insert_text(
                        page, text, rect.width - config.margin_right, y_footer,
                        HorizontalAlignment.RIGHT, config
                    )

                pages_processed += 1

            return HeaderFooterResult(
                success=True,
                pages_processed=pages_processed,
                pages_skipped=pages_skipped,
                message=f"Dodano nagłówki/stopki do {pages_processed} stron"
            )

        except Exception as e:
            return HeaderFooterResult(
                success=False,
                pages_processed=pages_processed,
                pages_skipped=pages_skipped,
                message=f"Błąd: {str(e)}"
            )

    def _expand_template(self, template: str, page_index: int, total: int) -> str:
        """Rozwija szablon z placeholderami."""
        now = datetime.now()

        replacements = {
            "{page}": str(page_index + 1),
            "{total}": str(total),
            "{date}": now.strftime("%Y-%m-%d"),
            "{time}": now.strftime("%H:%M"),
            "{datetime}": now.strftime("%Y-%m-%d %H:%M"),
            "{filename}": self._filename,
        }

        result = template
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)

        return result

    def _insert_text(
        self,
        page: fitz.Page,
        text: str,
        x: float,
        y: float,
        alignment: HorizontalAlignment,
        config: HeaderFooterConfig
    ) -> None:
        """Wstawia tekst na stronę z odpowiednim wyrównaniem."""
        if not text.strip():
            return

        # Oblicz szerokość tekstu
        font = fitz.Font(config.font_name)
        text_width = font.text_length(text, fontsize=config.font_size)

        # Dostosuj pozycję x według wyrównania
        if alignment == HorizontalAlignment.CENTER:
            x = x - text_width / 2
        elif alignment == HorizontalAlignment.RIGHT:
            x = x - text_width

        # Wstaw tekst
        page.insert_text(
            (x, y),
            text,
            fontname=config.font_name,
            fontsize=config.font_size,
            color=config.font_color,
        )

    @staticmethod
    def get_available_templates() -> Dict[str, str]:
        """Zwraca dostępne szablony placeholderów."""
        return {
            "{page}": "Numer bieżącej strony",
            "{total}": "Całkowita liczba stron",
            "{date}": "Bieżąca data (YYYY-MM-DD)",
            "{time}": "Bieżący czas (HH:MM)",
            "{datetime}": "Data i czas",
            "{filename}": "Nazwa pliku",
        }

    @staticmethod
    def get_preset_configs() -> Dict[str, HeaderFooterConfig]:
        """Zwraca predefiniowane konfiguracje."""
        return {
            "page_numbers_bottom": HeaderFooterConfig(
                footer_center="{page} / {total}",
                skip_first=False,
            ),
            "page_numbers_top": HeaderFooterConfig(
                header_center="{page} / {total}",
                footer_center="",
                skip_first=False,
            ),
            "document_header": HeaderFooterConfig(
                header_center="{filename}",
                footer_center="{page} / {total}",
                skip_first=True,
            ),
            "legal_footer": HeaderFooterConfig(
                footer_left="{date}",
                footer_center="Strona {page} z {total}",
                footer_right="{filename}",
                skip_first=False,
            ),
            "book_style": HeaderFooterConfig(
                header_center="{filename}",
                footer_center="{page}",
                skip_first=True,
                different_odd_even=True,
                even_header_left="{filename}",
                even_header_center="",
                even_footer_left="{page}",
                even_footer_center="",
            ),
        }


# === Funkcje pomocnicze ===

def add_page_numbers(
    pdf_path: Path,
    output_path: Optional[Path] = None,
    position: str = "bottom-center",
    format_str: str = "{page} / {total}",
    skip_first: bool = False,
    font_size: float = 10,
    font_color: tuple = (0, 0, 0),
) -> HeaderFooterResult:
    """
    Szybka funkcja do dodania numeracji stron.

    Args:
        pdf_path: Ścieżka do pliku PDF
        output_path: Ścieżka wyjściowa (domyślnie nadpisuje oryginał)
        position: Pozycja numeracji (top-left, top-center, top-right,
                  bottom-left, bottom-center, bottom-right)
        format_str: Format numeracji (szablon)
        skip_first: Czy pominąć pierwszą stronę
        font_size: Rozmiar czcionki
        font_color: Kolor czcionki (RGB 0-1)

    Returns:
        HeaderFooterResult
    """
    doc = fitz.open(str(pdf_path))

    config = HeaderFooterConfig(
        font_size=font_size,
        font_color=font_color,
        skip_first=skip_first,
    )

    # Ustaw pozycję
    parts = position.split("-")
    vertical = parts[0] if parts else "bottom"
    horizontal = parts[1] if len(parts) > 1 else "center"

    if vertical == "top":
        if horizontal == "left":
            config.header_left = format_str
        elif horizontal == "right":
            config.header_right = format_str
        else:
            config.header_center = format_str
        config.footer_center = ""
    else:
        if horizontal == "left":
            config.footer_left = format_str
        elif horizontal == "right":
            config.footer_right = format_str
        else:
            config.footer_center = format_str

    engine = HeaderFooterEngine()
    result = engine.apply(doc, config, pdf_path.name)

    if result.success:
        output = output_path or pdf_path
        doc.save(str(output))

    doc.close()
    return result
