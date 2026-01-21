"""
OCREngine - Rozpoznawanie tekstu ze skanów PDF.

Wykorzystuje darmowe API OCR.space:
- 25,000 zapytań/miesiąc (darmowy tier)
- Engine 2 (lepszy dla większości przypadków)
- Obsługa polskiego, angielskiego, niemieckiego i innych języków
"""

import asyncio
import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor
import urllib.request
import urllib.parse
import ssl

import pymupdf


@dataclass
class OCRResult:
    """Wynik rozpoznawania OCR dla pojedynczej strony."""
    page_index: int
    text: str
    confidence: float
    words: List[Dict[str, Any]]  # Słowa z pozycjami
    lines: List[str]
    error: Optional[str] = None


@dataclass
class OCRConfig:
    """Konfiguracja OCR."""
    language: str = "pol"  # pol, eng, deu, fra, etc.
    engine: int = 2  # 1 lub 2, engine 2 jest lepszy
    scale: bool = True  # Skalowanie dla lepszej dokładności
    detect_orientation: bool = True
    is_table: bool = False  # Lepsze dla tabel
    ocr_exit_code: int = 1  # 1 = OCR zakończone sukcesem


class OCREngine:
    """
    Silnik OCR wykorzystujący OCR.space API.

    Darmowy tier: 25,000 zapytań/miesiąc
    Obsługiwane języki: pol, eng, deu, fra, spa, ita, por, etc.
    """

    API_URL = "https://api.ocr.space/parse/image"

    # Mapowanie języków
    LANGUAGES = {
        "pl": "pol",
        "en": "eng",
        "de": "ger",
        "fr": "fre",
        "es": "spa",
        "it": "ita",
        "pt": "por",
        "ru": "rus",
        "uk": "ukr",
        "cs": "cze",
        "sk": "slk",
        "hu": "hun",
        "ro": "rum",
        "bg": "bul",
        "hr": "hrv",
        "sr": "srp",
        "sl": "slv",
        "nl": "dut",
        "sv": "swe",
        "no": "nor",
        "da": "dan",
        "fi": "fin",
        "el": "gre",
        "tr": "tur",
        "ar": "ara",
        "he": "heb",
        "zh": "chs",  # Simplified Chinese
        "ja": "jpn",
        "ko": "kor",
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicjalizuje silnik OCR.

        Args:
            api_key: Klucz API OCR.space (opcjonalny, używa darmowego demo key)
        """
        self.api_key = api_key or "helloworld"  # Demo key z limitem
        self._executor = ThreadPoolExecutor(max_workers=3)

    def recognize_page_sync(
        self,
        image_bytes: bytes,
        config: Optional[OCRConfig] = None,
    ) -> OCRResult:
        """
        Rozpoznaje tekst z obrazu strony (synchronicznie).

        Args:
            image_bytes: Bajty obrazu PNG/JPG
            config: Konfiguracja OCR

        Returns:
            OCRResult z rozpoznanym tekstem
        """
        config = config or OCRConfig()

        # Przygotuj dane do wysłania
        base64_image = base64.b64encode(image_bytes).decode('utf-8')

        payload = {
            "apikey": self.api_key,
            "language": config.language,
            "OCREngine": str(config.engine),
            "scale": str(config.scale).lower(),
            "detectOrientation": str(config.detect_orientation).lower(),
            "isTable": str(config.is_table).lower(),
            "base64Image": f"data:image/png;base64,{base64_image}",
        }

        try:
            # Przygotuj request
            data = urllib.parse.urlencode(payload).encode('utf-8')

            # Utwórz kontekst SSL (dla Windows)
            context = ssl.create_default_context()

            request = urllib.request.Request(
                self.API_URL,
                data=data,
                method='POST',
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                }
            )

            # Wykonaj request
            with urllib.request.urlopen(request, timeout=60, context=context) as response:
                result = json.loads(response.read().decode('utf-8'))

            # Przetwórz wynik
            if result.get("OCRExitCode") == 1:
                parsed_results = result.get("ParsedResults", [])
                if parsed_results:
                    parsed = parsed_results[0]
                    text = parsed.get("ParsedText", "")

                    # Wyciągnij słowa z pozycjami (jeśli dostępne)
                    words = []
                    text_overlay = parsed.get("TextOverlay", {})
                    for line in text_overlay.get("Lines", []):
                        for word in line.get("Words", []):
                            words.append({
                                "text": word.get("WordText", ""),
                                "left": word.get("Left", 0),
                                "top": word.get("Top", 0),
                                "width": word.get("Width", 0),
                                "height": word.get("Height", 0),
                            })

                    return OCRResult(
                        page_index=0,
                        text=text,
                        confidence=0.9,  # OCR.space nie zwraca confidence
                        words=words,
                        lines=text.split('\n') if text else [],
                    )

            # Błąd OCR
            error_message = result.get("ErrorMessage", ["Unknown error"])
            if isinstance(error_message, list):
                error_message = "; ".join(error_message)

            return OCRResult(
                page_index=0,
                text="",
                confidence=0.0,
                words=[],
                lines=[],
                error=error_message,
            )

        except Exception as e:
            return OCRResult(
                page_index=0,
                text="",
                confidence=0.0,
                words=[],
                lines=[],
                error=str(e),
            )

    async def recognize_page(
        self,
        image_bytes: bytes,
        config: Optional[OCRConfig] = None,
    ) -> OCRResult:
        """
        Rozpoznaje tekst z obrazu strony (asynchronicznie).

        Args:
            image_bytes: Bajty obrazu PNG/JPG
            config: Konfiguracja OCR

        Returns:
            OCRResult z rozpoznanym tekstem
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self.recognize_page_sync,
            image_bytes,
            config,
        )

    def recognize_pdf_page(
        self,
        doc: pymupdf.Document,
        page_index: int,
        config: Optional[OCRConfig] = None,
        dpi: int = 300,
    ) -> OCRResult:
        """
        Rozpoznaje tekst ze strony PDF (używając OCR.space API).

        Args:
            doc: Dokument PyMuPDF
            page_index: Indeks strony
            config: Konfiguracja OCR
            dpi: Rozdzielczość renderowania

        Returns:
            OCRResult z rozpoznanym tekstem
        """
        page = doc[page_index]

        # Renderuj stronę do obrazu
        mat = pymupdf.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        image_bytes = pix.tobytes("png")

        result = self.recognize_page_sync(image_bytes, config)
        result.page_index = page_index

        return result

    def recognize_pdf_page_tesseract(
        self,
        doc: pymupdf.Document,
        page_index: int,
        config: Optional[OCRConfig] = None,
        dpi: int = 300,
    ) -> OCRResult:
        """
        Wyciąga tekst ze strony PDF lokalnie (bez wysyłania na serwer).

        Działa dla PDF-ów które mają warstwę tekstową (nie dla czystych skanów/obrazów).
        Dla skanów bez warstwy tekstowej użyj metody AI OCR (Online).

        Args:
            doc: Dokument PyMuPDF
            page_index: Indeks strony
            config: Konfiguracja OCR
            dpi: Rozdzielczość (nieużywana)

        Returns:
            OCRResult z wyciągniętym tekstem
        """
        config = config or OCRConfig()

        try:
            page = doc[page_index]

            # Tryb tabelaryczny - użyj find_tables() z PyMuPDF
            if config.is_table:
                text = self._extract_tables_as_text(page)
            else:
                # Standardowa ekstrakcja tekstu
                text = page.get_text("text")

            # Wyciągnij słowa z pozycjami
            words = []
            try:
                word_list = page.get_text("words")
                for w in word_list:
                    # w = (x0, y0, x1, y1, "word", block_no, line_no, word_no)
                    words.append({
                        "text": w[4],
                        "left": w[0],
                        "top": w[1],
                        "width": w[2] - w[0],
                        "height": w[3] - w[1],
                    })
            except Exception:
                pass

            lines = [line.strip() for line in text.split('\n') if line.strip()]

            # Sprawdź czy strona ma jakikolwiek tekst
            if not text.strip():
                return OCRResult(
                    page_index=page_index,
                    text="",
                    confidence=0.0,
                    words=[],
                    lines=[],
                    error="Brak tekstu na stronie. Strona może być skanem - użyj AI OCR (Online).",
                )

            return OCRResult(
                page_index=page_index,
                text=text.strip(),
                confidence=1.0,  # Tekst z PDF jest pewny
                words=words,
                lines=lines,
            )

        except Exception as e:
            return OCRResult(
                page_index=page_index,
                text="",
                confidence=0.0,
                words=[],
                lines=[],
                error=str(e),
            )

    def _extract_tables_as_text(self, page) -> str:
        """
        Wyciąga tabele ze strony i formatuje je jako tekst.

        Args:
            page: Strona PyMuPDF

        Returns:
            Tekst z tabelami sformatowanymi w kolumnach
        """
        result_lines = []

        # Znajdź tabele na stronie
        tables = page.find_tables()

        if tables and tables.tables:
            for table_idx, table in enumerate(tables.tables):
                if table_idx > 0:
                    result_lines.append("")  # Separator między tabelami

                # Pobierz dane tabeli
                table_data = table.extract()

                if not table_data:
                    continue

                # Filtruj puste kolumny (kolumny gdzie wszystkie komórki są puste)
                num_cols = max(len(row) for row in table_data) if table_data else 0
                non_empty_cols = []
                for col_idx in range(num_cols):
                    has_content = False
                    for row in table_data:
                        if col_idx < len(row) and row[col_idx] and str(row[col_idx]).strip():
                            has_content = True
                            break
                    if has_content:
                        non_empty_cols.append(col_idx)

                # Przefiltruj dane - zostaw tylko niepuste kolumny
                filtered_data = []
                for row in table_data:
                    filtered_row = []
                    for col_idx in non_empty_cols:
                        if col_idx < len(row):
                            filtered_row.append(row[col_idx])
                        else:
                            filtered_row.append("")
                    filtered_data.append(filtered_row)

                if not filtered_data:
                    continue

                # Oblicz maksymalne szerokości kolumn
                col_widths = []
                for row in filtered_data:
                    for col_idx, cell in enumerate(row):
                        cell_text = str(cell) if cell else ""
                        if col_idx >= len(col_widths):
                            col_widths.append(len(cell_text))
                        else:
                            col_widths[col_idx] = max(col_widths[col_idx], len(cell_text))

                # Formatuj wiersze tabeli
                for row_idx, row in enumerate(filtered_data):
                    formatted_cells = []
                    for col_idx, cell in enumerate(row):
                        cell_text = str(cell) if cell else ""
                        # Wyrównaj do szerokości kolumny
                        if col_idx < len(col_widths):
                            formatted_cells.append(cell_text.ljust(col_widths[col_idx]))
                        else:
                            formatted_cells.append(cell_text)
                    result_lines.append(" | ".join(formatted_cells))

                    # Dodaj separator po nagłówku (pierwszy wiersz)
                    if row_idx == 0:
                        separator = "-+-".join("-" * w for w in col_widths)
                        result_lines.append(separator)

        # Jeśli nie znaleziono tabel, użyj standardowej ekstrakcji
        if not result_lines:
            return page.get_text("text")

        return "\n".join(result_lines)

    async def recognize_pdf_page_async(
        self,
        doc: pymupdf.Document,
        page_index: int,
        config: Optional[OCRConfig] = None,
        dpi: int = 300,
    ) -> OCRResult:
        """
        Rozpoznaje tekst ze strony PDF (asynchronicznie).
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self.recognize_pdf_page,
            doc,
            page_index,
            config,
            dpi,
        )

    def recognize_all_pages(
        self,
        doc: pymupdf.Document,
        config: Optional[OCRConfig] = None,
        dpi: int = 300,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[OCRResult]:
        """
        Rozpoznaje tekst ze wszystkich stron PDF.

        Args:
            doc: Dokument PyMuPDF
            config: Konfiguracja OCR
            dpi: Rozdzielczość renderowania
            progress_callback: Callback (current, total) dla postępu

        Returns:
            Lista OCRResult dla każdej strony
        """
        results = []
        total = len(doc)

        for i in range(total):
            if progress_callback:
                progress_callback(i, total)

            result = self.recognize_pdf_page(doc, i, config, dpi)
            results.append(result)

        if progress_callback:
            progress_callback(total, total)

        return results

    def create_searchable_pdf(
        self,
        doc: pymupdf.Document,
        ocr_results: List[OCRResult],
    ) -> bytes:
        """
        Tworzy PDF z niewidoczną warstwą tekstu (searchable PDF).

        Nakłada rozpoznany tekst jako niewidoczną warstwę,
        co pozwala na wyszukiwanie i kopiowanie tekstu.

        Args:
            doc: Oryginalny dokument PDF
            ocr_results: Wyniki OCR dla każdej strony

        Returns:
            Bajty nowego PDF z warstwą tekstu
        """
        # Skopiuj dokument
        new_doc = pymupdf.open()
        new_doc.insert_pdf(doc)

        for result in ocr_results:
            if result.error or not result.words:
                continue

            page = new_doc[result.page_index]

            # Dodaj niewidoczny tekst w pozycjach słów
            for word in result.words:
                if not word.get("text"):
                    continue

                # Oblicz pozycję (skalowanie z DPI)
                # OCR.space zwraca pozycje w pikselach przy 300 DPI
                scale = 72 / 300  # Konwersja z 300 DPI do punktów PDF

                x = word["left"] * scale
                y = word["top"] * scale

                # Wstaw niewidoczny tekst
                # Używamy bardzo małej czcionki i zerowej opacity
                try:
                    page.insert_text(
                        (x, y + word["height"] * scale),
                        word["text"],
                        fontsize=max(1, word["height"] * scale * 0.8),
                        color=(1, 1, 1),  # Biały (niewidoczny)
                        render_mode=3,  # Invisible
                    )
                except Exception:
                    pass

        return new_doc.tobytes()

    def export_text(
        self,
        ocr_results: List[OCRResult],
        format: str = "txt",
    ) -> str:
        """
        Eksportuje rozpoznany tekst do formatu tekstowego.

        Args:
            ocr_results: Wyniki OCR
            format: Format wyjściowy ("txt", "json")

        Returns:
            Tekst w wybranym formacie
        """
        if format == "json":
            data = []
            for result in ocr_results:
                data.append({
                    "page": result.page_index + 1,
                    "text": result.text,
                    "lines": result.lines,
                    "confidence": result.confidence,
                    "error": result.error,
                })
            return json.dumps(data, ensure_ascii=False, indent=2)

        # Format TXT
        lines = []
        for result in ocr_results:
            lines.append(f"--- Strona {result.page_index + 1} ---")
            if result.error:
                lines.append(f"[Błąd: {result.error}]")
            else:
                lines.append(result.text)
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def get_supported_languages() -> Dict[str, str]:
        """Zwraca słownik obsługiwanych języków."""
        return {
            "pol": "Polski",
            "eng": "English",
            "ger": "Deutsch",
            "fre": "Français",
            "spa": "Español",
            "ita": "Italiano",
            "por": "Português",
            "rus": "Русский",
            "ukr": "Українська",
            "cze": "Čeština",
            "slk": "Slovenčina",
            "hun": "Magyar",
            "rum": "Română",
            "bul": "Български",
            "hrv": "Hrvatski",
            "srp": "Српски",
            "slv": "Slovenščina",
            "dut": "Nederlands",
            "swe": "Svenska",
            "nor": "Norsk",
            "dan": "Dansk",
            "fin": "Suomi",
            "gre": "Ελληνικά",
            "tur": "Türkçe",
            "ara": "العربية",
            "heb": "עברית",
            "chs": "简体中文",
            "jpn": "日本語",
            "kor": "한국어",
        }
