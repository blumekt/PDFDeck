"""
DiffEngine - Porównywanie wersji dokumentów PDF.

Funkcje:
- Generowanie obrazu porównawczego z zaznaczeniem różnic
- Wykrywanie różnic między stronami
- Kolorowanie tylko rzeczywistych różnic
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
from pathlib import Path
import io

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFilter


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
    zaznaczając tylko rzeczywiste różnice.
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
        color_diff: Tuple[int, int, int] = (255, 0, 0),  # Czerwony dla różnic
        dpi: int = 150,
        threshold: int = 30,  # Próg różnicy kolorów (0-765)
    ) -> Optional[DiffResult]:
        """
        Porównuje pojedynczą stronę z obu dokumentów.

        Pokazuje oryginalny dokument z zaznaczonymi różnicami (ramką i kolorem).

        Args:
            page_index: Indeks strony do porównania
            color_diff: Kolor zaznaczenia różnic (RGB)
            dpi: Rozdzielczość renderowania
            threshold: Próg wykrywania różnic (suma różnic RGB)

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

        # Konwertuj do PIL Image
        img_a = Image.frombytes("RGB", (pix_a.width, pix_a.height), pix_a.samples)
        img_b = Image.frombytes("RGB", (pix_b.width, pix_b.height), pix_b.samples)

        # Dopasuj rozmiary (użyj większego)
        width = max(img_a.width, img_b.width)
        height = max(img_a.height, img_b.height)

        # Rozszerz obrazy do tego samego rozmiaru (białe tło)
        if img_a.size != (width, height):
            new_a = Image.new("RGB", (width, height), (255, 255, 255))
            new_a.paste(img_a, (0, 0))
            img_a = new_a

        if img_b.size != (width, height):
            new_b = Image.new("RGB", (width, height), (255, 255, 255))
            new_b.paste(img_b, (0, 0))
            img_b = new_b

        # Znajdź różnice piksel po pikselu
        pixels_a = img_a.load()
        pixels_b = img_b.load()

        # Utwórz maskę różnic
        diff_mask = Image.new("L", (width, height), 0)
        diff_pixels = diff_mask.load()

        diff_count = 0
        total_pixels = width * height

        for y in range(height):
            for x in range(width):
                r_a, g_a, b_a = pixels_a[x, y]
                r_b, g_b, b_b = pixels_b[x, y]

                # Oblicz różnicę
                diff = abs(r_a - r_b) + abs(g_a - g_b) + abs(b_a - b_b)

                if diff > threshold:
                    diff_count += 1
                    diff_pixels[x, y] = 255  # Różnica

        # Rozmyj maskę żeby połączyć bliskie różnice
        diff_mask = diff_mask.filter(ImageFilter.MaxFilter(5))
        diff_mask = diff_mask.filter(ImageFilter.GaussianBlur(3))

        # Stwórz obraz wynikowy - oryginał z zaznaczonymi różnicami
        result_img = img_b.copy()
        draw = ImageDraw.Draw(result_img)

        # Znajdź regiony różnic (bounding boxes)
        diff_regions = self._find_diff_regions(diff_mask)

        # Narysuj ramki wokół różnic
        for region in diff_regions:
            x1, y1, x2, y2 = region
            # Ramka
            draw.rectangle([x1 - 2, y1 - 2, x2 + 2, y2 + 2], outline=color_diff, width=3)

        # Nałóż półprzezroczystą warstwę na różnice
        if diff_regions:
            overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)

            for region in diff_regions:
                x1, y1, x2, y2 = region
                # Półprzezroczyste wypełnienie
                overlay_draw.rectangle(
                    [x1, y1, x2, y2],
                    fill=(color_diff[0], color_diff[1], color_diff[2], 80)
                )

            # Połącz z wynikiem
            result_img = result_img.convert("RGBA")
            result_img = Image.alpha_composite(result_img, overlay)
            result_img = result_img.convert("RGB")

        # Konwertuj do PNG bytes
        buffer = io.BytesIO()
        result_img.save(buffer, format="PNG")
        png_bytes = buffer.getvalue()

        similarity = 100.0 * (1 - diff_count / max(total_pixels, 1))

        return DiffResult(
            page_index=page_index,
            has_differences=len(diff_regions) > 0,
            diff_image=png_bytes,
            similarity_percent=similarity
        )

    def _find_diff_regions(
        self,
        diff_mask: Image.Image,
        min_size: int = 10
    ) -> List[Tuple[int, int, int, int]]:
        """
        Znajduje regiony różnic w masce.

        Używa prostego algorytmu flood-fill do znalezienia połączonych obszarów.

        Args:
            diff_mask: Maska różnic (biały = różnica)
            min_size: Minimalny rozmiar regionu do uwzględnienia

        Returns:
            Lista bounding boxów (x1, y1, x2, y2)
        """
        width, height = diff_mask.size
        pixels = diff_mask.load()
        visited = [[False] * width for _ in range(height)]
        regions = []

        def flood_fill(start_x: int, start_y: int) -> Tuple[int, int, int, int]:
            """Znajduje bounding box połączonego regionu."""
            stack = [(start_x, start_y)]
            min_x, min_y = start_x, start_y
            max_x, max_y = start_x, start_y

            while stack:
                x, y = stack.pop()

                if x < 0 or x >= width or y < 0 or y >= height:
                    continue
                if visited[y][x]:
                    continue
                if pixels[x, y] < 128:  # Próg dla maski
                    continue

                visited[y][x] = True
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

                # Dodaj sąsiadów (8-connectivity)
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx != 0 or dy != 0:
                            stack.append((x + dx, y + dy))

            return (min_x, min_y, max_x, max_y)

        # Znajdź wszystkie regiony
        for y in range(height):
            for x in range(width):
                if not visited[y][x] and pixels[x, y] >= 128:
                    region = flood_fill(x, y)
                    # Filtruj małe regiony
                    region_width = region[2] - region[0]
                    region_height = region[3] - region[1]
                    if region_width >= min_size and region_height >= min_size:
                        regions.append(region)

        # Połącz nakładające się lub bliskie regiony
        regions = self._merge_close_regions(regions, margin=20)

        return regions

    def _merge_close_regions(
        self,
        regions: List[Tuple[int, int, int, int]],
        margin: int = 20
    ) -> List[Tuple[int, int, int, int]]:
        """
        Łączy regiony które są blisko siebie.

        Args:
            regions: Lista bounding boxów
            margin: Margines do łączenia

        Returns:
            Lista połączonych regionów
        """
        if not regions:
            return []

        # Sortuj po pozycji
        regions = sorted(regions, key=lambda r: (r[1], r[0]))

        merged = []
        current = list(regions[0])

        for region in regions[1:]:
            # Sprawdź czy regiony się nakładają lub są blisko
            if (region[0] <= current[2] + margin and
                region[2] >= current[0] - margin and
                region[1] <= current[3] + margin and
                region[3] >= current[1] - margin):
                # Połącz
                current[0] = min(current[0], region[0])
                current[1] = min(current[1], region[1])
                current[2] = max(current[2], region[2])
                current[3] = max(current[3], region[3])
            else:
                merged.append(tuple(current))
                current = list(region)

        merged.append(tuple(current))

        return merged

    def compare_all_pages(
        self,
        color_diff: Tuple[int, int, int] = (255, 0, 0),
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
            result = self.compare_page(i, color_diff, dpi)
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
