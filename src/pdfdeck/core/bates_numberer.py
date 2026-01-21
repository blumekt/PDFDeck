"""
BatesNumberer - Numeracja Bates dla dokumentów prawniczych.

Funkcje:
- Dodawanie numeracji Bates do dokumentów
- Konfigurowalny prefix i suffix
- Wybór pozycji (góra/dół, lewo/środek/prawo)
- Batch numbering wielu plików
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional
from enum import Enum

import pymupdf


class BatesPosition(Enum):
    """Pozycja numeracji Bates na stronie."""
    TOP_LEFT = "top-left"
    TOP_CENTER = "top-center"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_CENTER = "bottom-center"
    BOTTOM_RIGHT = "bottom-right"


@dataclass
class BatesConfig:
    """Konfiguracja numeracji Bates."""
    prefix: str = "DOC"
    suffix: str = ""
    start_number: int = 1
    digits: int = 6  # Ilość cyfr (000001)
    position: BatesPosition = BatesPosition.BOTTOM_RIGHT
    font_size: int = 10
    font_color: Tuple[float, float, float] = (0, 0, 0)  # RGB 0-1
    margin: int = 36  # Margines w punktach (0.5 cala)
    font_name: str = "helv"  # Helvetica


@dataclass
class BatesResult:
    """Wynik numeracji Bates."""
    file_path: Path
    start_number: int
    end_number: int
    page_count: int
    success: bool
    error: Optional[str] = None


class BatesNumberer:
    """
    Numeracja Bates dla dokumentów prawniczych.

    Standard w kancelariach prawnych dla identyfikacji stron
    w procesach i dokumentacji.

    Format: PREFIX-000001, PREFIX-000002, ...
    """

    def __init__(self):
        pass

    def apply_bates(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
        config: Optional[BatesConfig] = None,
    ) -> BatesResult:
        """
        Dodaje numerację Bates do dokumentu.

        Args:
            input_path: Ścieżka do pliku wejściowego
            output_path: Ścieżka wyjściowa (domyślnie nadpisuje)
            config: Konfiguracja numeracji

        Returns:
            BatesResult z informacjami o numeracji
        """
        config = config or BatesConfig()
        output_path = output_path or input_path

        try:
            doc = pymupdf.open(str(input_path))
            page_count = len(doc)

            for i, page in enumerate(doc):
                number = config.start_number + i
                bates_text = self._format_bates_number(number, config)

                # Oblicz pozycję
                pos = self._calculate_position(page.rect, config)

                # Wstaw tekst
                page.insert_text(
                    pos,
                    bates_text,
                    fontname=config.font_name,
                    fontsize=config.font_size,
                    color=config.font_color,
                )

            doc.save(str(output_path))
            doc.close()

            return BatesResult(
                file_path=output_path,
                start_number=config.start_number,
                end_number=config.start_number + page_count - 1,
                page_count=page_count,
                success=True,
            )

        except Exception as e:
            return BatesResult(
                file_path=output_path,
                start_number=config.start_number,
                end_number=config.start_number,
                page_count=0,
                success=False,
                error=str(e),
            )

    def batch_bates(
        self,
        pdf_paths: List[Path],
        output_dir: Path,
        config: Optional[BatesConfig] = None,
    ) -> List[BatesResult]:
        """
        Numeruje wiele plików zachowując ciągłość numeracji.

        Args:
            pdf_paths: Lista ścieżek do plików PDF
            output_dir: Katalog wyjściowy
            config: Konfiguracja numeracji

        Returns:
            Lista BatesResult dla każdego pliku
        """
        config = config or BatesConfig()
        results = []
        current_number = config.start_number

        # Utwórz katalog wyjściowy jeśli nie istnieje
        output_dir.mkdir(parents=True, exist_ok=True)

        for pdf_path in pdf_paths:
            # Utwórz kopię konfiguracji z aktualnym numerem
            file_config = BatesConfig(
                prefix=config.prefix,
                suffix=config.suffix,
                start_number=current_number,
                digits=config.digits,
                position=config.position,
                font_size=config.font_size,
                font_color=config.font_color,
                margin=config.margin,
                font_name=config.font_name,
            )

            # Generuj nazwę pliku wyjściowego
            output_path = output_dir / f"bates_{pdf_path.name}"

            result = self.apply_bates(pdf_path, output_path, file_config)
            results.append(result)

            # Aktualizuj numer dla następnego pliku
            if result.success:
                current_number = result.end_number + 1

        return results

    def _format_bates_number(self, number: int, config: BatesConfig) -> str:
        """Formatuje numer Bates."""
        formatted_number = str(number).zfill(config.digits)
        return f"{config.prefix}{formatted_number}{config.suffix}"

    def _calculate_position(
        self, rect: pymupdf.Rect, config: BatesConfig
    ) -> Tuple[float, float]:
        """
        Oblicza pozycję tekstu na stronie.

        Args:
            rect: Prostokąt strony
            config: Konfiguracja numeracji

        Returns:
            Tuple (x, y) pozycji
        """
        margin = config.margin
        text_width = config.font_size * (config.digits + len(config.prefix) + len(config.suffix)) * 0.6

        # Pozycja Y
        if config.position.value.startswith("top"):
            y = margin + config.font_size
        else:  # bottom
            y = rect.height - margin

        # Pozycja X
        if config.position.value.endswith("left"):
            x = margin
        elif config.position.value.endswith("center"):
            x = (rect.width - text_width) / 2
        else:  # right
            x = rect.width - margin - text_width

        return (x, y)

    def preview_bates(
        self,
        doc: pymupdf.Document,
        page_index: int,
        config: BatesConfig,
    ) -> bytes:
        """
        Generuje podgląd strony z numeracją Bates.

        Args:
            doc: Dokument PyMuPDF
            page_index: Indeks strony
            config: Konfiguracja numeracji

        Returns:
            Bajty obrazu PNG
        """
        # Kopiuj stronę do tymczasowego dokumentu
        temp_doc = pymupdf.open()
        temp_doc.insert_pdf(doc, from_page=page_index, to_page=page_index)
        page = temp_doc[0]

        # Dodaj numerację
        number = config.start_number + page_index
        bates_text = self._format_bates_number(number, config)
        pos = self._calculate_position(page.rect, config)

        page.insert_text(
            pos,
            bates_text,
            fontname=config.font_name,
            fontsize=config.font_size,
            color=config.font_color,
        )

        # Renderuj do obrazu
        pix = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5))
        png_bytes = pix.tobytes("png")

        temp_doc.close()
        return png_bytes

    def remove_bates(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
        config: Optional[BatesConfig] = None,
    ) -> bool:
        """
        Próbuje usunąć numerację Bates (redakcja obszaru).

        Uwaga: To jest uproszczone rozwiązanie - usuwa tekst
        z obszaru gdzie typowo znajduje się numeracja.

        Args:
            input_path: Ścieżka do pliku
            output_path: Ścieżka wyjściowa
            config: Konfiguracja (do określenia pozycji)

        Returns:
            True jeśli sukces
        """
        config = config or BatesConfig()
        output_path = output_path or input_path

        try:
            doc = pymupdf.open(str(input_path))

            for page in doc:
                rect = page.rect
                margin = config.margin
                height = config.font_size + 10

                # Określ obszar do redakcji
                if config.position.value.startswith("top"):
                    redact_rect = pymupdf.Rect(
                        0, 0, rect.width, margin + height
                    )
                else:
                    redact_rect = pymupdf.Rect(
                        0, rect.height - margin - height,
                        rect.width, rect.height
                    )

                # Dodaj redakcję
                page.add_redact_annot(redact_rect, fill=(1, 1, 1))
                page.apply_redactions()

            doc.save(str(output_path))
            doc.close()

            return True

        except Exception:
            return False

    @staticmethod
    def get_position_options() -> List[Tuple[str, BatesPosition]]:
        """Zwraca listę opcji pozycji dla UI."""
        return [
            ("Góra - lewo", BatesPosition.TOP_LEFT),
            ("Góra - środek", BatesPosition.TOP_CENTER),
            ("Góra - prawo", BatesPosition.TOP_RIGHT),
            ("Dół - lewo", BatesPosition.BOTTOM_LEFT),
            ("Dół - środek", BatesPosition.BOTTOM_CENTER),
            ("Dół - prawo", BatesPosition.BOTTOM_RIGHT),
        ]
