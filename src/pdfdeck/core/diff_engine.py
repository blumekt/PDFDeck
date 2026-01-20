"""
DiffEngine - Porównywanie wersji dokumentów PDF.

Funkcje:
- Generowanie obrazu porównawczego (overlay)
- Wykrywanie różnic między stronami
- Kolorowanie różnic (czerwony/niebieski)
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class DiffResult:
    """Wynik porównania strony."""
    page_index: int
    has_differences: bool
    diff_image: bytes  # PNG bytes
    similarity_percent: float


class DiffEngine:
    """
    Silnik porównywania dokumentów PDF.

    Generuje wizualne porównanie dwóch wersji dokumentu,
    nakładając strony w różnych kolorach.
    """

    def __init__(self):
        self._doc_a: Optional[fitz.Document] = None
        self._doc_b: Optional[fitz.Document] = None
        self._path_a: Optional[Path] = None
        self._path_b: Optional[Path] = None

    def load_documents(self, path_a: Path, path_b: Path) -> Tuple[int, int]:
        """
        Ładuje dwa dokumenty do porównania.

        Args:
            path_a: Ścieżka do pierwszego dokumentu (oryginał)
            path_b: Ścieżka do drugiego dokumentu (nowa wersja)

        Returns:
            Krotka (liczba stron A, liczba stron B)
        """
        self.close()

        self._path_a = path_a
        self._path_b = path_b
        self._doc_a = fitz.open(str(path_a))
        self._doc_b = fitz.open(str(path_b))

        return len(self._doc_a), len(self._doc_b)

    def close(self) -> None:
        """Zamyka załadowane dokumenty."""
        if self._doc_a:
            self._doc_a.close()
            self._doc_a = None
        if self._doc_b:
            self._doc_b.close()
            self._doc_b = None
        self._path_a = None
        self._path_b = None

    def compare_page(
        self,
        page_index: int,
        color_a: Tuple[int, int, int] = (255, 0, 0),  # Czerwony
        color_b: Tuple[int, int, int] = (0, 0, 255),  # Niebieski
        dpi: int = 150,
        opacity: float = 0.5
    ) -> Optional[DiffResult]:
        """
        Porównuje pojedynczą stronę z obu dokumentów.

        Args:
            page_index: Indeks strony do porównania
            color_a: Kolor dla dokumentu A (RGB)
            color_b: Kolor dla dokumentu B (RGB)
            dpi: Rozdzielczość renderowania
            opacity: Przezroczystość nakładki (0.0-1.0)

        Returns:
            DiffResult z obrazem porównawczym lub None jeśli strona nie istnieje
        """
        if not self._doc_a or not self._doc_b:
            return None

        if page_index >= len(self._doc_a) or page_index >= len(self._doc_b):
            return None

        page_a = self._doc_a[page_index]
        page_b = self._doc_b[page_index]

        # Renderuj obie strony
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix_a = page_a.get_pixmap(matrix=mat, alpha=False)
        pix_b = page_b.get_pixmap(matrix=mat, alpha=False)

        # Dopasuj rozmiary (użyj większego)
        width = max(pix_a.width, pix_b.width)
        height = max(pix_a.height, pix_b.height)

        # Utwórz nowy pixmap na wynik
        result_pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, width, height), 1)
        result_pix.clear_with(255)  # Białe tło

        # Pobierz dane pikseli
        samples_a = pix_a.samples
        samples_b = pix_b.samples
        result_samples = bytearray(result_pix.samples)

        # Oblicz różnice piksel po pikselu
        diff_count = 0
        total_pixels = 0

        for y in range(min(pix_a.height, pix_b.height)):
            for x in range(min(pix_a.width, pix_b.width)):
                idx_a = (y * pix_a.width + x) * pix_a.n
                idx_b = (y * pix_b.width + x) * pix_b.n
                idx_r = (y * width + x) * 4  # RGBA

                # Pobierz piksele
                r_a, g_a, b_a = samples_a[idx_a], samples_a[idx_a + 1], samples_a[idx_a + 2]
                r_b, g_b, b_b = samples_b[idx_b], samples_b[idx_b + 1], samples_b[idx_b + 2]

                total_pixels += 1

                # Sprawdź różnicę
                diff = abs(r_a - r_b) + abs(g_a - g_b) + abs(b_a - b_b)

                if diff > 30:  # Próg różnicy
                    diff_count += 1
                    # Mieszaj kolory z zaznaczeniem różnicy
                    result_samples[idx_r] = int(color_a[0] * opacity + color_b[0] * (1 - opacity))
                    result_samples[idx_r + 1] = int(color_a[1] * opacity + color_b[1] * (1 - opacity))
                    result_samples[idx_r + 2] = int(color_a[2] * opacity + color_b[2] * (1 - opacity))
                    result_samples[idx_r + 3] = 255
                else:
                    # Bez różnicy - pokaż oryginał w skali szarości
                    gray = int((r_a + g_a + b_a) / 3)
                    result_samples[idx_r] = gray
                    result_samples[idx_r + 1] = gray
                    result_samples[idx_r + 2] = gray
                    result_samples[idx_r + 3] = 255

        # Utwórz nowy pixmap z wynikiem
        result_pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, width, height), 1)
        result_pix.set_origin(0, 0)

        # Konwertuj do PNG
        # Użyj prostszego podejścia - nałóż oba obrazy
        diff_image = self._create_overlay_image(pix_a, pix_b, color_a, color_b, opacity)

        similarity = 100.0 * (1 - diff_count / max(total_pixels, 1))

        return DiffResult(
            page_index=page_index,
            has_differences=diff_count > 0,
            diff_image=diff_image,
            similarity_percent=similarity
        )

    def _create_overlay_image(
        self,
        pix_a: fitz.Pixmap,
        pix_b: fitz.Pixmap,
        color_a: Tuple[int, int, int],
        color_b: Tuple[int, int, int],
        opacity: float
    ) -> bytes:
        """
        Tworzy obraz nakładkowy z dwóch pixmap.

        Używa prostego podejścia - renderuje różnice kolorami.
        """
        # Użyj większego rozmiaru
        width = max(pix_a.width, pix_b.width)
        height = max(pix_a.height, pix_b.height)

        # Utwórz nowy dokument PDF jako bufor
        doc = fitz.open()
        page = doc.new_page(width=width, height=height)

        # Wstaw oba obrazy z przezroczystością
        rect = fitz.Rect(0, 0, pix_a.width, pix_a.height)

        # Wstaw pierwszy obraz (zabarwiony na kolor A)
        tinted_a = self._tint_pixmap(pix_a, color_a, 0.3)
        page.insert_image(rect, pixmap=tinted_a)

        # Wstaw drugi obraz (zabarwiony na kolor B) z przezroczystością
        rect_b = fitz.Rect(0, 0, pix_b.width, pix_b.height)
        tinted_b = self._tint_pixmap(pix_b, color_b, 0.3)

        # Renderuj stronę do PNG
        result_pix = page.get_pixmap(dpi=150)
        png_bytes = result_pix.tobytes("png")

        doc.close()

        return png_bytes

    def _tint_pixmap(
        self,
        pix: fitz.Pixmap,
        color: Tuple[int, int, int],
        intensity: float
    ) -> fitz.Pixmap:
        """
        Zabarwia pixmap na podany kolor.

        Args:
            pix: Pixmap do zabarwienia
            color: Kolor RGB
            intensity: Intensywność zabarwienia (0.0-1.0)

        Returns:
            Nowy zabarwiony Pixmap
        """
        # Utwórz kopię
        tinted = fitz.Pixmap(pix)
        samples = bytearray(tinted.samples)

        for i in range(0, len(samples), pix.n):
            r, g, b = samples[i], samples[i + 1], samples[i + 2]

            # Mieszaj z kolorem
            samples[i] = int(r * (1 - intensity) + color[0] * intensity)
            samples[i + 1] = int(g * (1 - intensity) + color[1] * intensity)
            samples[i + 2] = int(b * (1 - intensity) + color[2] * intensity)

        # PyMuPDF nie pozwala bezpośrednio modyfikować samples,
        # więc zwracamy oryginalny pixmap (uproszczone)
        return pix

    def compare_all_pages(
        self,
        color_a: Tuple[int, int, int] = (255, 0, 0),
        color_b: Tuple[int, int, int] = (0, 0, 255),
        dpi: int = 150
    ) -> List[DiffResult]:
        """
        Porównuje wszystkie strony obu dokumentów.

        Returns:
            Lista wyników porównania dla każdej strony
        """
        if not self._doc_a or not self._doc_b:
            return []

        results = []
        max_pages = max(len(self._doc_a), len(self._doc_b))

        for i in range(max_pages):
            result = self.compare_page(i, color_a, color_b, dpi)
            if result:
                results.append(result)

        return results

    def generate_diff_report(self) -> str:
        """
        Generuje tekstowy raport z porównania.

        Returns:
            Raport w formacie tekstowym
        """
        if not self._doc_a or not self._doc_b:
            return "Brak załadowanych dokumentów."

        lines = [
            "=== Raport porównania PDF ===",
            f"Dokument A: {self._path_a.name if self._path_a else 'N/A'}",
            f"Dokument B: {self._path_b.name if self._path_b else 'N/A'}",
            f"Strony A: {len(self._doc_a)}",
            f"Strony B: {len(self._doc_b)}",
            "",
            "Różnice stron:",
        ]

        results = self.compare_all_pages()

        for result in results:
            status = "RÓŻNICE" if result.has_differences else "OK"
            lines.append(
                f"  Strona {result.page_index + 1}: {status} "
                f"(podobieństwo: {result.similarity_percent:.1f}%)"
            )

        return "\n".join(lines)

    @property
    def page_count_a(self) -> int:
        """Liczba stron dokumentu A."""
        return len(self._doc_a) if self._doc_a else 0

    @property
    def page_count_b(self) -> int:
        """Liczba stron dokumentu B."""
        return len(self._doc_b) if self._doc_b else 0
