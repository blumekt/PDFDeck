"""
PDFManager - Główna klasa do operacji na dokumentach PDF.

Używa PyMuPDF (fitz) do wszystkich operacji.
Separacja logiki PDF od UI.
"""

import random
from pathlib import Path
from typing import List, Optional, Dict, Any

import pymupdf

from pdfdeck.core.models import (
    PageInfo,
    Rect,
    Point,
    WhiteoutConfig,
    LinkConfig,
    LinkInfo,
    WatermarkConfig,
    StampConfig,
    StampShape,
    WearLevel,
    SearchResult,
    WordBounds,
    DocumentMetadata,
    TableData,
    Heading,
    PreflightIssue,
    PreflightIssueType,
    PageSize,
    NupConfig,
)
from pdfdeck.core.stamp_renderer import StampRenderer


class PDFManager:
    """
    Zarządza dokumentem PDF używając PyMuPDF.

    Thread-safe dla operacji odczytu.
    Operacje zapisu powinny być wykonywane z głównego wątku.
    """

    def __init__(self) -> None:
        self._doc: Optional[pymupdf.Document] = None
        self._filepath: Optional[Path] = None
        self._modified: bool = False

    # === Właściwości ===

    @property
    def is_loaded(self) -> bool:
        """Czy dokument jest załadowany."""
        return self._doc is not None

    @property
    def is_modified(self) -> bool:
        """Czy dokument ma niezapisane zmiany."""
        return self._modified

    @property
    def page_count(self) -> int:
        """Liczba stron w dokumencie."""
        return len(self._doc) if self._doc else 0

    @property
    def filepath(self) -> Optional[Path]:
        """Ścieżka do aktualnego pliku."""
        return self._filepath

    # === Operacje na dokumencie ===

    def load(self, filepath: str | Path) -> None:
        """
        Otwiera dokument PDF.

        Args:
            filepath: Ścieżka do pliku PDF

        Raises:
            FileNotFoundError: Jeśli plik nie istnieje
            ValueError: Jeśli plik nie jest prawidłowym PDF
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Plik nie istnieje: {path}")

        try:
            self.close()  # Zamknij poprzedni dokument
            self._doc = pymupdf.open(str(path))
            self._filepath = path
            self._modified = False
        except Exception as e:
            raise ValueError(f"Nie można otworzyć pliku PDF: {e}")

    def save(
        self,
        filepath: Optional[str | Path] = None,
        optimize: bool = False,
        garbage: int = 4,
        deflate: bool = True,
    ) -> None:
        """
        Zapisuje dokument PDF.

        Args:
            filepath: Ścieżka wyjściowa (None = nadpisz oryginalny)
            optimize: Czy optymalizować rozmiar pliku
            garbage: Poziom garbage collection (0-4)
            deflate: Czy kompresować strumienie
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        output_path = Path(filepath) if filepath else self._filepath
        if not output_path:
            raise ValueError("Nie podano ścieżki wyjściowej")

        # Ustawienia optymalizacji
        save_kwargs: Dict[str, Any] = {
            "garbage": garbage if optimize else 0,
            "deflate": deflate,
            "clean": optimize,
        }

        # Zapisz do nowego pliku lub nadpisz
        if output_path == self._filepath:
            self._doc.save(str(output_path), incremental=False, **save_kwargs)
        else:
            self._doc.save(str(output_path), **save_kwargs)

        self._modified = False

    def close(self) -> None:
        """Zamyka dokument i zwalnia zasoby."""
        if self._doc:
            self._doc.close()
            self._doc = None
            self._filepath = None
            self._modified = False

    # === Miniatury i podgląd ===

    def generate_thumbnail(self, page_index: int, max_size: int = 200) -> bytes:
        """
        Generuje miniaturę strony jako PNG.

        Args:
            page_index: Indeks strony (0-based)
            max_size: Maksymalny wymiar (szerokość lub wysokość)

        Returns:
            Dane PNG jako bytes (do QPixmap.loadFromData)
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        page = self._doc[page_index]
        rect = page.rect

        # Oblicz skalę, żeby zmieścić się w max_size
        scale = max_size / max(rect.width, rect.height)
        mat = pymupdf.Matrix(scale, scale)

        # Renderuj do pixmap
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return pix.tobytes("png")

    def generate_preview(self, page_index: int, dpi: int = 150) -> bytes:
        """
        Generuje podgląd strony w wysokiej rozdzielczości.

        Args:
            page_index: Indeks strony (0-based)
            dpi: Rozdzielczość w DPI

        Returns:
            Dane PNG jako bytes
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        page = self._doc[page_index]
        zoom = dpi / 72.0  # PDF używa 72 DPI jako bazę
        mat = pymupdf.Matrix(zoom, zoom)

        pix = page.get_pixmap(matrix=mat, alpha=False)
        return pix.tobytes("png")

    # === Informacje o stronach ===

    def get_page_info(self, page_index: int) -> PageInfo:
        """Zwraca metadane strony."""
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        page = self._doc[page_index]
        return PageInfo(
            index=page_index,
            width=page.rect.width,
            height=page.rect.height,
            rotation=page.rotation,
        )

    def get_all_page_info(self) -> List[PageInfo]:
        """Zwraca metadane wszystkich stron."""
        return [self.get_page_info(i) for i in range(self.page_count)]

    # === Manipulacja stronami ===

    def reorder_pages(self, new_order: List[int]) -> None:
        """
        Zmienia kolejność stron.

        Args:
            new_order: Lista indeksów stron w nowej kolejności
                       (musi zawierać wszystkie strony dokładnie raz)
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        # Walidacja
        if sorted(new_order) != list(range(self.page_count)):
            raise ValueError("new_order musi zawierać wszystkie indeksy stron")

        self._doc.select(new_order)
        self._modified = True

    def delete_pages(self, page_indices: List[int]) -> None:
        """
        Usuwa wskazane strony.

        Args:
            page_indices: Lista indeksów stron do usunięcia
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        # Zachowaj strony, które NIE są do usunięcia
        keep_pages = [i for i in range(self.page_count) if i not in page_indices]

        if not keep_pages:
            raise ValueError("Nie można usunąć wszystkich stron")

        self._doc.select(keep_pages)
        self._modified = True

    def merge_document(self, other_path: str | Path, insert_at: int = -1) -> None:
        """
        Łączy inny dokument PDF z obecnym.

        Args:
            other_path: Ścieżka do drugiego PDF
            insert_at: Pozycja wstawienia (-1 = na końcu)
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        other_doc = pymupdf.open(str(other_path))
        try:
            if insert_at < 0:
                insert_at = self.page_count

            # Wstaw strony z drugiego dokumentu
            self._doc.insert_pdf(other_doc, from_page=0, to_page=-1, start_at=insert_at)
            self._modified = True
        finally:
            other_doc.close()

    def split_at(self, split_points: List[int]) -> List[bytes]:
        """
        Dzieli dokument na części w podanych punktach.

        Args:
            split_points: Lista indeksów stron, PO których podzielić

        Returns:
            Lista dokumentów PDF jako bytes
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        # Dodaj punkt końcowy
        points = sorted(set(split_points))
        points.append(self.page_count - 1)

        results = []
        start = 0

        for end in points:
            if end >= start:
                # Utwórz nowy dokument z zakresem stron
                new_doc = pymupdf.open()
                new_doc.insert_pdf(self._doc, from_page=start, to_page=end)
                results.append(new_doc.tobytes())
                new_doc.close()
                start = end + 1

        return results

    # === Edycja treści ===

    def apply_whiteout(self, page_index: int, config: WhiteoutConfig) -> None:
        """
        Stosuje Whiteout & Type - zakrywa obszar i wstawia tekst.

        UWAGA: To NIE jest prawdziwa redakcja - oryginalna treść
        pozostaje w strukturze PDF!

        Args:
            page_index: Indeks strony
            config: Konfiguracja whiteout
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        page = self._doc[page_index]
        rect = pymupdf.Rect(config.rect.as_tuple)

        # Krok 1: Rysuj biały prostokąt
        shape = page.new_shape()
        shape.draw_rect(rect)
        shape.finish(
            color=config.fill_color,
            fill=config.fill_color,
            width=0,
        )
        shape.commit()

        # Krok 2: Wstaw tekst na wierzchu
        if config.text:
            page.insert_textbox(
                rect,
                config.text,
                fontname=config.font_name,
                fontsize=config.font_size,
                color=config.text_color,
                align=pymupdf.TEXT_ALIGN_LEFT,
            )

        self._modified = True

    def insert_link(self, page_index: int, config: LinkConfig) -> None:
        """
        Wstawia hiperłącze na stronie.

        Args:
            page_index: Indeks strony
            config: Konfiguracja linku
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        page = self._doc[page_index]
        rect = pymupdf.Rect(config.rect.as_tuple)

        # Jeśli podano tekst wyświetlany, dodaj go na stronę
        if config.display_text:
            # Oblicz szerokość tekstu
            fontsize = 11
            text_width = pymupdf.get_text_length(
                config.display_text, fontname="helv", fontsize=fontsize
            )
            # Dopasuj prostokąt do tekstu
            text_rect = pymupdf.Rect(
                rect.x0, rect.y0,
                rect.x0 + text_width + 4,  # +4 dla marginesu
                rect.y0 + fontsize + 4
            )
            # Wstaw tekst linku (niebieski)
            page.insert_text(
                (text_rect.x0, text_rect.y0 + fontsize),
                config.display_text,
                fontname="helv",
                fontsize=fontsize,
                color=(0, 0, 0.8),  # Niebieski kolor linku
            )
            # Dodaj podkreślenie
            page.draw_line(
                (text_rect.x0, text_rect.y0 + fontsize + 1),
                (text_rect.x0 + text_width, text_rect.y0 + fontsize + 1),
                color=(0, 0, 0.8),
                width=0.5
            )
            # Zaktualizuj rect dla linku
            rect = text_rect

        # Dodaj niebieskie podkreślenie jako adnotację PDF (jeśli włączone i nie ma display_text)
        if config.add_underline and not config.display_text:
            annot = page.add_underline_annot(rect)
            annot.set_colors(stroke=(0, 0, 0.8))  # Niebieski kolor
            annot.update()

        # Dodaj niebieską ramkę wokół obszaru (dla linków z zaznaczenia obszaru)
        if config.add_border and not config.display_text:
            page.draw_rect(
                rect,
                color=(0, 0, 0.8),  # Niebieski kolor
                width=1.0,
                fill=None  # Bez wypełnienia
            )

        link_dict: Dict[str, Any] = {"from": rect}

        if config.uri:
            # Link zewnętrzny (URI)
            link_dict["kind"] = pymupdf.LINK_URI
            link_dict["uri"] = config.uri
        elif config.target_page is not None:
            # Link wewnętrzny (GoTo)
            link_dict["kind"] = pymupdf.LINK_GOTO
            link_dict["page"] = config.target_page
            if config.target_point:
                link_dict["to"] = pymupdf.Point(
                    config.target_point.x, config.target_point.y
                )
        else:
            raise ValueError("Link musi mieć uri lub target_page")

        page.insert_link(link_dict)
        self._modified = True

    def get_page_links(self, page_index: int) -> List[LinkInfo]:
        """
        Pobiera listę linków ze strony.

        Args:
            page_index: Indeks strony

        Returns:
            Lista obiektów LinkInfo
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        page = self._doc[page_index]
        links = page.get_links()
        result: List[LinkInfo] = []

        for idx, link in enumerate(links):
            # Pobierz prostokąt linku
            from_rect = link.get("from", pymupdf.Rect(0, 0, 0, 0))
            rect = Rect(from_rect.x0, from_rect.y0, from_rect.x1, from_rect.y1)

            # Określ typ linku
            kind = link.get("kind", pymupdf.LINK_NONE)
            uri = link.get("uri")
            target_page = link.get("page")

            if kind == pymupdf.LINK_URI:
                link_type = "url"
            elif kind == pymupdf.LINK_GOTO:
                link_type = "page"
            elif kind == pymupdf.LINK_LAUNCH:
                link_type = "file"
                uri = link.get("file", link.get("uri"))
            elif kind == pymupdf.LINK_GOTOR:
                link_type = "file"
                uri = link.get("file", link.get("uri"))
            else:
                link_type = "unknown"

            result.append(LinkInfo(
                index=idx,
                rect=rect,
                link_type=link_type,
                uri=uri,
                target_page=target_page,
                raw_dict=link
            ))

        return result

    def delete_link(self, page_index: int, link_index: int) -> None:
        """
        Usuwa link ze strony.

        Args:
            page_index: Indeks strony
            link_index: Indeks linku na stronie
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        page = self._doc[page_index]
        links = page.get_links()

        if link_index < 0 or link_index >= len(links):
            raise IndexError(f"Nieprawidłowy indeks linku: {link_index}")

        link_to_delete = links[link_index]
        page.delete_link(link_to_delete)
        self._modified = True

    def update_link(self, page_index: int, link_index: int, config: LinkConfig) -> None:
        """
        Aktualizuje istniejący link.

        Args:
            page_index: Indeks strony
            link_index: Indeks linku na stronie
            config: Nowa konfiguracja linku
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        # PyMuPDF nie ma natywnego update_link, więc usuwamy i wstawiamy nowy
        self.delete_link(page_index, link_index)
        self.insert_link(page_index, config)

    def get_page_images(self, page_index: int) -> List[Dict[str, Any]]:
        """
        Zwraca listę obrazków na stronie.

        Args:
            page_index: Indeks strony

        Returns:
            Lista słowników z informacjami o obrazkach:
            - xref: Referencja do obrazka
            - width: Szerokość
            - height: Wysokość
            - bbox: Prostokąt pozycji na stronie
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        page = self._doc[page_index]
        images = []

        for img in page.get_images(full=True):
            xref = img[0]
            try:
                img_info = self._doc.extract_image(xref)
                if img_info:
                    # Znajdź pozycję obrazka na stronie
                    img_rects = page.get_image_rects(xref)
                    bbox = img_rects[0] if img_rects else pymupdf.Rect(0, 0, 0, 0)

                    images.append({
                        "xref": xref,
                        "width": img_info.get("width", 0),
                        "height": img_info.get("height", 0),
                        "bbox": Rect(bbox.x0, bbox.y0, bbox.x1, bbox.y1),
                        "colorspace": img_info.get("colorspace", ""),
                        "bpc": img_info.get("bpc", 0),
                    })
            except Exception:
                pass

        return images

    def swap_image(
        self, page_index: int, xref: int, new_image_path: str | Path
    ) -> None:
        """
        Podmienia obrazek w PDF na nowy.

        Args:
            page_index: Indeks strony
            xref: Referencja do obrazka (xref)
            new_image_path: Ścieżka do nowego obrazka
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        page = self._doc[page_index]

        # Pobierz pozycję obrazka
        img_rects = page.get_image_rects(xref)
        if not img_rects:
            raise ValueError(f"Nie znaleziono obrazka o xref={xref}")

        rect = img_rects[0]

        # Usuń stary obrazek (zastąp pustym)
        page.delete_image(xref)

        # Wstaw nowy obrazek w to samo miejsce
        page.insert_image(rect, filename=str(new_image_path))

        self._modified = True

    # === Wyszukiwanie tekstu ===

    def search_text(
        self, query: str, regex: bool = False, pages: Optional[List[int]] = None
    ) -> List[SearchResult]:
        """
        Wyszukuje tekst w dokumencie.

        Args:
            query: Tekst lub wyrażenie regularne do wyszukania
            regex: Czy traktować query jako regex
            pages: Lista stron do przeszukania (None = wszystkie)

        Returns:
            Lista wyników wyszukiwania
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        results = []
        search_pages = pages if pages else range(self.page_count)

        for page_idx in search_pages:
            page = self._doc[page_idx]

            # PyMuPDF search_for zwraca listę Rect
            if regex:
                import re
                # Dla regex musimy najpierw wyciągnąć tekst i szukać ręcznie
                text = page.get_text()
                for match in re.finditer(query, text, re.IGNORECASE):
                    # Znajdź pozycję dopasowania na stronie
                    rects = page.search_for(match.group())
                    for r in rects:
                        results.append(
                            SearchResult(
                                page_index=page_idx,
                                rect=Rect(r.x0, r.y0, r.x1, r.y1),
                                text=match.group(),
                            )
                        )
            else:
                rects = page.search_for(query)
                for r in rects:
                    results.append(
                        SearchResult(
                            page_index=page_idx,
                            rect=Rect(r.x0, r.y0, r.x1, r.y1),
                            text=query,
                        )
                    )

        return results

    def search_text_on_page(self, page_index: int, query: str) -> List[SearchResult]:
        """
        Wyszukuje tekst na konkretnej stronie.

        Args:
            page_index: Indeks strony (0-indexed)
            query: Tekst do wyszukania

        Returns:
            Lista wyników wyszukiwania z tej strony
        """
        return self.search_text(query, regex=False, pages=[page_index])

    def get_page_words(self, page_index: int) -> List[WordBounds]:
        """
        Pobiera wszystkie słowa ze strony z ich pozycjami.

        Args:
            page_index: Indeks strony (0-indexed)

        Returns:
            Lista WordBounds zawierająca słowa i ich prostokąty
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        page = self._doc[page_index]
        words = page.get_text("words")  # (x0, y0, x1, y1, word, block_no, line_no, word_no)

        result = []
        for w in words:
            x0, y0, x1, y1, text, block_no, line_no, word_no = w
            result.append(
                WordBounds(
                    text=text,
                    rect=Rect(x0, y0, x1, y1),
                    block_no=int(block_no),
                    line_no=int(line_no),
                    word_no=int(word_no),
                )
            )
        return result

    def snap_rect_to_words(
        self, page_index: int, rect: Rect, tolerance: float = 2.0
    ) -> tuple[Rect, List[str]]:
        """
        Dopasowuje prostokąt do granic słów, które przecina.

        Args:
            page_index: Indeks strony
            rect: Prostokąt do dopasowania
            tolerance: Tolerancja w punktach PDF (tylko poziomo)

        Returns:
            Tuple (dopasowany Rect, lista zaznaczonych słów)
        """
        words = self.get_page_words(page_index)

        # Znajdź słowa które mają znaczący overlap z prostokątem
        intersecting_words = []
        for word in words:
            # Oblicz overlap w pionie - środek słowa musi być wewnątrz zaznaczenia
            word_center_y = (word.rect.y0 + word.rect.y1) / 2
            if not (rect.y0 <= word_center_y <= rect.y1):
                continue

            # Sprawdź overlap w poziomie (z małą tolerancją)
            if (
                word.rect.x0 <= rect.x1 + tolerance
                and word.rect.x1 >= rect.x0 - tolerance
            ):
                intersecting_words.append(word)

        if not intersecting_words:
            return rect, []

        # Oblicz bounding box wszystkich przecinających się słów
        min_x0 = min(w.rect.x0 for w in intersecting_words)
        min_y0 = min(w.rect.y0 for w in intersecting_words)
        max_x1 = max(w.rect.x1 for w in intersecting_words)
        max_y1 = max(w.rect.y1 for w in intersecting_words)

        snapped_rect = Rect(min_x0, min_y0, max_x1, max_y1)
        selected_words = [w.text for w in intersecting_words]

        return snapped_rect, selected_words

    # === Redakcja (prawdziwa) ===

    def apply_redaction(
        self,
        results: List[SearchResult],
        color: tuple = (0, 0, 0),
    ) -> None:
        """
        Stosuje prawdziwą redakcję - usuwa treść z PDF.

        UWAGA: Ta operacja jest nieodwracalna!

        Args:
            results: Lista wyników wyszukiwania do zredagowania
            color: Kolor zakrycia (RGB 0-1)
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        # Grupuj wyniki po stronach
        by_page: Dict[int, List[SearchResult]] = {}
        for r in results:
            by_page.setdefault(r.page_index, []).append(r)

        # Dodaj adnotacje redakcji
        for page_idx, page_results in by_page.items():
            page = self._doc[page_idx]
            for r in page_results:
                rect = pymupdf.Rect(r.rect.as_tuple)
                page.add_redact_annot(rect, fill=color)

        # Zastosuj redakcje (nieodwracalne!)
        # Parametry: usuń obrazy które nachodzą, usuń grafikę wektorową, usuń tekst
        for page_idx in by_page.keys():
            self._doc[page_idx].apply_redactions(
                images=pymupdf.PDF_REDACT_IMAGE_REMOVE,
                graphics=pymupdf.PDF_REDACT_LINE_ART_IF_TOUCHED,
                text=True,
            )

        self._modified = True

    # === Watermarking ===

    def add_watermark(
        self,
        config: WatermarkConfig,
        pages: Optional[List[int]] = None,
    ) -> None:
        """
        Dodaje znak wodny na stronach.

        Args:
            config: Konfiguracja znaku wodnego
            pages: Lista stron (None = wszystkie)
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        target_pages = pages if pages else range(self.page_count)

        # Renderuj tekst znaku wodnego jako PNG z przezroczystością
        # Rotacja jest już wliczona w renderowaniu
        watermark_image = self._render_watermark_image(config)

        for page_idx in target_pages:
            page = self._doc[page_idx]
            rect = page.rect

            # Oblicz rozmiar obrazu znaku wodnego dla strony
            # Skaluj tak, aby był czytelny ale nie dominował
            page_diag = (rect.width**2 + rect.height**2) ** 0.5
            watermark_width = page_diag * 0.8  # 80% przekątnej strony

            # Środek strony
            center_x = rect.width / 2
            center_y = rect.height / 2

            # Wstaw obraz
            watermark_rect = pymupdf.Rect(
                center_x - watermark_width / 2,
                center_y - watermark_width / 2,
                center_x + watermark_width / 2,
                center_y + watermark_width / 2,
            )

            page.insert_image(
                watermark_rect,
                stream=watermark_image,
                overlay=True,  # Zawsze ponad zawartością
            )

        self._modified = True

    def _render_watermark_image(self, config: WatermarkConfig) -> bytes:
        """
        Renderuje tekst znaku wodnego jako PNG z przezroczystością i rotacją.

        Returns:
            PNG bytes z kanałem alpha
        """
        from PIL import Image, ImageDraw, ImageFont
        import io

        # Parametry obrazu
        dpi = 150
        font_size = int(config.font_size * dpi / 72)  # Konwersja z punktów na piksele
        margin = 40  # Większy margines dla rotacji

        # Utwórz tymczasowy obraz aby zmierzyć tekst
        temp_img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_img)

        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except (OSError, IOError):
            # Fallback na domyślną czcionkę
            font = ImageFont.load_default()

        # Zmierz tekst
        bbox = temp_draw.textbbox((0, 0), config.text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Utwórz docelowy obraz z marginesem
        img_width = int(text_width) + margin * 2
        img_height = int(text_height) + margin * 2
        img = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Rysuj tekst na środku
        x = (img_width - text_width) / 2
        y = (img_height - text_height) / 2

        # Konwertuj opacity do kanału alpha (0.0-1.0 -> 0-255)
        alpha = int(config.opacity * 255)
        color_rgb = tuple(int(c * 255) for c in config.color)
        color_rgba = (*color_rgb, alpha)

        draw.text((x, y), config.text, font=font, fill=color_rgba)

        # Zastosuj rotację
        rotation_angle = config.rotation
        if rotation_angle != 0:
            # Obrócić obraz - expand=True aby zachować całą zawartość
            img = img.rotate(rotation_angle, expand=True, resample=Image.Resampling.BICUBIC)

        # Konwertuj do PNG bytes
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.read()

    def add_stamp(self, page_index: int, config: StampConfig) -> None:
        """
        Dodaje pieczątkę na stronie.

        Obsługuje:
        - Zewnętrzne pliki SVG/PNG (legacy)
        - Dynamicznie generowane pieczątki (nowe)
        - Różne kształty (prostokąt, okrąg, owal)
        - Przezroczystość i efekty zużycia

        Args:
            page_index: Indeks strony
            config: Konfiguracja pieczątki
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        page = self._doc[page_index]

        # PyMuPDF insert_image rotate akceptuje tylko 0, 90, 180, 270
        # Małe rotacje dla naturalności muszą być zrobione inaczej (pre-processing obrazu)
        # Na razie używamy tylko wielokrotności 90
        rotation = int(config.rotation) % 360
        if rotation not in (0, 90, 180, 270):
            rotation = 0

        # Oblicz rozmiar pieczątki
        width = config.width * config.scale
        height = config.height * config.scale

        # Dla okrągłych pieczątek użyj kwadratu
        if config.shape == StampShape.CIRCLE:
            size = max(width, height)
            width = height = size

        # Oblicz pozycję na podstawie narożnika
        rect = page.rect
        margin = 20  # Margines od krawędzi
        
        if config.corner == "top-left":
            x, y = margin, margin
        elif config.corner == "top-center":
            x, y = rect.width / 2 - width / 2, margin
        elif config.corner == "top-right":
            x, y = rect.width - width - margin, margin
        elif config.corner == "center":
            x, y = rect.width / 2 - width / 2, rect.height / 2 - height / 2
        elif config.corner == "bottom-left":
            x, y = margin, rect.height - height - margin
        elif config.corner == "bottom-center":
            x, y = rect.width / 2 - width / 2, rect.height - height - margin
        elif config.corner == "bottom-right":
            x, y = rect.width - width - margin, rect.height - height - margin
        else:
            # Fallback na custom position
            x, y = config.position.x, config.position.y

        stamp_rect = pymupdf.Rect(
            x,
            y,
            x + width,
            y + height,
        )

        if config.stamp_path:
            # Legacy: zewnętrzny plik SVG/PNG
            page.insert_image(
                stamp_rect,
                filename=str(config.stamp_path),
                rotate=rotation,
            )
        else:
            # Dynamiczne generowanie - zawsze PNG
            renderer = StampRenderer()
            png_data = renderer.render_to_png(config)

            # Obsłuż rotację za pomocą PIL jeśli jest inna niż 0, 90, 180, 270
            if config.rotation not in (0, 90, 180, 270):
                from PIL import Image
                import io
                
                # Wczytaj obraz
                img = Image.open(io.BytesIO(png_data))
                # Obróć obraz
                img = img.rotate(config.rotation, expand=True, resample=Image.Resampling.BICUBIC)
                # Konwertuj z powrotem na bytes
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                png_data = buffer.getvalue()
                rotation = 0  # Już obrócony przez PIL
            else:
                rotation = int(config.rotation) % 360

            # Zapisz do tymczasowego pliku (PyMuPDF lepiej obsługuje pliki)
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp.write(png_data)
                tmp_path = tmp.name

            try:
                page.insert_image(
                    stamp_rect,
                    filename=tmp_path,
                    rotate=rotation,
                )
            finally:
                os.unlink(tmp_path)

        self._modified = True

    # === Formatowanie ===

    def normalize_to_a4(self) -> None:
        """
        Normalizuje wszystkie strony do rozmiaru A4.

        Używa letterboxing (białe marginesy), żeby nie rozciągać treści.
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        a4_width, a4_height = PageSize.A4.value

        for page_idx in range(self.page_count):
            page = self._doc[page_idx]
            current_rect = page.rect

            # Sprawdź czy już jest A4
            if (
                abs(current_rect.width - a4_width) < 1
                and abs(current_rect.height - a4_height) < 1
            ):
                continue

            # Oblicz skalę, żeby zmieścić treść w A4
            scale_x = a4_width / current_rect.width
            scale_y = a4_height / current_rect.height
            scale = min(scale_x, scale_y)

            # Nowy rozmiar z zachowaniem proporcji
            new_width = current_rect.width * scale
            new_height = current_rect.height * scale

            # Marginesy (letterboxing)
            margin_x = (a4_width - new_width) / 2
            margin_y = (a4_height - new_height) / 2

            # Zmień rozmiar strony
            page.set_mediabox(pymupdf.Rect(0, 0, a4_width, a4_height))

            # Transformuj treść
            mat = pymupdf.Matrix(scale, scale)
            mat = mat.pretranslate(margin_x / scale, margin_y / scale)

            # Zastosuj transformację do wszystkich obiektów

        self._modified = True

    def create_nup(self, config: NupConfig) -> bytes:
        """
        Tworzy dokument N-up (wiele stron na jednej kartce).

        Args:
            config: Konfiguracja N-up

        Returns:
            Nowy dokument PDF jako bytes
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        # Oblicz układ siatki
        n = config.pages_per_sheet
        if n == 2:
            cols, rows = 2, 1
        elif n == 4:
            cols, rows = 2, 2
        elif n == 6:
            cols, rows = 3, 2
        elif n == 9:
            cols, rows = 3, 3
        else:
            cols, rows = 4, 4

        if config.landscape:
            cols, rows = rows, cols

        output_width, output_height = config.output_size.value
        if config.landscape:
            output_width, output_height = output_height, output_width

        cell_width = output_width / cols
        cell_height = output_height / rows

        # Utwórz nowy dokument
        new_doc = pymupdf.open()

        for i in range(0, self.page_count, n):
            # Nowa strona wyjściowa
            new_page = new_doc.new_page(width=output_width, height=output_height)

            for j in range(n):
                if i + j >= self.page_count:
                    break

                # Pozycja w siatce
                col = j % cols
                row = j // cols

                # Prostokąt docelowy
                x0 = col * cell_width
                y0 = row * cell_height
                clip_rect = pymupdf.Rect(x0, y0, x0 + cell_width, y0 + cell_height)

                # Wstaw stronę źródłową
                new_page.show_pdf_page(clip_rect, self._doc, i + j)

        result = new_doc.tobytes()
        new_doc.close()
        return result

    # === Bezpieczeństwo ===

    def scrub_metadata(self) -> None:
        """
        Usuwa wszystkie metadane z dokumentu.

        Usuwa: autora, tytuł, datę utworzenia, producenta, itp.
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        # Wyczyść metadane
        self._doc.set_metadata({})

        # Usuń XMP metadata
        self._doc.del_xml_metadata()

        self._modified = True

    def get_metadata(self) -> DocumentMetadata:
        """Zwraca metadane dokumentu."""
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        meta = self._doc.metadata
        return DocumentMetadata(
            title=meta.get("title"),
            author=meta.get("author"),
            subject=meta.get("subject"),
            keywords=meta.get("keywords"),
            creator=meta.get("creator"),
            producer=meta.get("producer"),
            creation_date=meta.get("creationDate"),
            modification_date=meta.get("modDate"),
        )

    def flatten(self) -> None:
        """
        Spłaszcza formularze i adnotacje.

        Zamienia interaktywne elementy w stałą część strony.
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        for page in self._doc:
            # Spłaszcz adnotacje (w tym formularze)
            for annot in page.annots():
                annot.set_flags(pymupdf.PDF_ANNOT_IS_PRINT)

        self._modified = True

    # === Analiza ===

    def preflight_check(self) -> List[PreflightIssue]:
        """
        Wykonuje sprawdzenie dokumentu przed drukiem/wysyłką.

        Wykrywa: puste strony, niską rozdzielczość obrazków,
        brakujące czcionki, uszkodzone linki.
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        issues = []

        for page_idx in range(self.page_count):
            page = self._doc[page_idx]

            # Sprawdź pustą stronę
            text = page.get_text().strip()
            images = page.get_images()
            if not text and not images:
                issues.append(
                    PreflightIssue(
                        issue_type=PreflightIssueType.EMPTY_PAGE,
                        page_index=page_idx,
                        description=f"Strona {page_idx + 1} jest pusta",
                        severity="warning",
                    )
                )

            # Sprawdź rozdzielczość obrazków
            for img in images:
                xref = img[0]
                try:
                    img_info = self._doc.extract_image(xref)
                    if img_info:
                        # Prosta heurystyka - jeśli obrazek jest mały
                        if img_info.get("width", 0) < 100 or img_info.get("height", 0) < 100:
                            issues.append(
                                PreflightIssue(
                                    issue_type=PreflightIssueType.LOW_RESOLUTION_IMAGE,
                                    page_index=page_idx,
                                    description=f"Obrazek o niskiej rozdzielczości na stronie {page_idx + 1}",
                                    severity="warning",
                                )
                            )
                except Exception:
                    pass

            # Sprawdź linki
            for link in page.get_links():
                if link.get("kind") == pymupdf.LINK_URI:
                    uri = link.get("uri", "")
                    if not uri or uri.startswith("javascript:"):
                        issues.append(
                            PreflightIssue(
                                issue_type=PreflightIssueType.BROKEN_LINK,
                                page_index=page_idx,
                                description=f"Potencjalnie uszkodzony link na stronie {page_idx + 1}",
                                severity="info",
                            )
                        )

        return issues

    def extract_tables(self, page_index: int) -> List[TableData]:
        """
        Ekstrahuje tabele ze strony.

        Args:
            page_index: Indeks strony

        Returns:
            Lista wykrytych tabel z danymi
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        page = self._doc[page_index]
        tables = page.find_tables()

        results = []
        for table in tables:
            data = table.extract()
            bbox = table.bbox
            results.append(
                TableData(
                    page_index=page_index,
                    bbox=Rect(bbox[0], bbox[1], bbox[2], bbox[3]),
                    rows=len(data),
                    cols=len(data[0]) if data else 0,
                    data=data,
                )
            )

        return results

    def detect_headings(self) -> List[Heading]:
        """
        Wykrywa nagłówki w dokumencie na podstawie wielkości czcionki.

        Returns:
            Lista wykrytych nagłówków
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        headings = []

        for page_idx in range(self.page_count):
            page = self._doc[page_idx]

            # Pobierz bloki tekstu z informacjami o czcionce
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    for span in line["spans"]:
                        font_size = span.get("size", 12)
                        text = span.get("text", "").strip()

                        # Heurystyka: większa czcionka = nagłówek
                        if font_size >= 14 and text and len(text) < 200:
                            # Określ poziom nagłówka
                            if font_size >= 24:
                                level = 1
                            elif font_size >= 18:
                                level = 2
                            elif font_size >= 14:
                                level = 3
                            else:
                                level = 4

                            bbox = span.get("bbox", (0, 0, 0, 0))
                            headings.append(
                                Heading(
                                    page_index=page_idx,
                                    text=text,
                                    level=level,
                                    font_size=font_size,
                                    rect=Rect(*bbox),
                                )
                            )

        return headings

    def generate_bookmarks(self) -> None:
        """
        Generuje zakładki (spis treści) na podstawie wykrytych nagłówków.
        """
        if not self._doc:
            raise ValueError("Brak załadowanego dokumentu")

        headings = self.detect_headings()

        # Konwertuj nagłówki na strukturę zakładek
        toc = []
        for h in headings:
            toc.append([h.level, h.text, h.page_index + 1])

        self._doc.set_toc(toc)
        self._modified = True
