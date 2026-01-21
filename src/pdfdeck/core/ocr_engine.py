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
        Rozpoznaje tekst ze strony PDF.

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
