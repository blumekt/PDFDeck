"""
InteractivePagePreview - Interaktywny podgląd strony PDF z możliwością zaznaczania.

Pozwala użytkownikowi zaznaczyć prostokątny obszar na stronie PDF.
"""

from typing import Optional, List, TYPE_CHECKING

from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsRectItem, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QLabel, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPixmap, QPen, QBrush, QColor, QMouseEvent, QWheelEvent

from pdfdeck.core.models import Rect

if TYPE_CHECKING:
    from pdfdeck.core.pdf_manager import PDFManager


class SelectionRectItem(QGraphicsRectItem):
    """Prostokąt zaznaczenia z charakterystycznym stylem."""

    def __init__(self, rect: QRectF = QRectF()):
        super().__init__(rect)
        self._setup_style()

    def _setup_style(self) -> None:
        """Ustawia styl prostokąta."""
        # Żółta ramka, półprzezroczyste żółte wypełnienie
        pen = QPen(QColor(224, 168, 0))  # #e0a800
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.SolidLine)
        self.setPen(pen)

        brush = QBrush(QColor(224, 168, 0, 50))  # Półprzezroczyste żółte
        self.setBrush(brush)


class PageGraphicsView(QGraphicsView):
    """
    Interaktywny widok strony PDF z możliwością zaznaczania prostokątów.

    Sygnały:
        selection_changed: Emitowany gdy zmienia się zaznaczenie (QRectF w pikselach)
        selection_completed: Emitowany gdy zaznaczenie jest zakończone
        zoom_changed: Emitowany gdy zmienia się poziom zoomu (float, np. 1.0 = 100%)
    """

    selection_changed = pyqtSignal(QRectF)
    selection_completed = pyqtSignal(QRectF)
    zoom_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # Elementy sceny
        self._page_item: Optional[QGraphicsPixmapItem] = None
        self._selection_item: Optional[SelectionRectItem] = None

        # Stan zaznaczania
        self._is_selecting = False
        self._start_pos: Optional[QPointF] = None
        self._current_rect = QRectF()

        # Rozmiary PDF (do konwersji współrzędnych)
        self._pdf_width = 0.0
        self._pdf_height = 0.0
        self._pixmap_width = 0
        self._pixmap_height = 0

        # Zoom
        self._zoom_factor = 1.0

        self._setup_view()

    def _setup_view(self) -> None:
        """Konfiguruje widok."""
        self.setRenderHint(self.renderHints().Antialiasing, True)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setBackgroundBrush(QBrush(QColor(15, 22, 41)))  # #0f1629

    def set_page(self, pixmap: QPixmap, pdf_width: float, pdf_height: float) -> None:
        """
        Ustawia obraz strony.

        Args:
            pixmap: Obraz strony jako QPixmap
            pdf_width: Szerokość strony PDF w punktach
            pdf_height: Wysokość strony PDF w punktach
        """
        self._scene.clear()
        self._selection_item = None

        self._pdf_width = pdf_width
        self._pdf_height = pdf_height
        self._pixmap_width = pixmap.width()
        self._pixmap_height = pixmap.height()

        self._page_item = QGraphicsPixmapItem(pixmap)
        self._scene.addItem(self._page_item)
        self._scene.setSceneRect(self._page_item.boundingRect())

        # Ustaw początkowy zoom na 35%
        self.resetTransform()
        self._zoom_factor = 0.35
        self.scale(self._zoom_factor, self._zoom_factor)
        self.centerOn(self._page_item)

    def clear_selection(self) -> None:
        """Czyści aktualne zaznaczenie."""
        if self._selection_item:
            self._scene.removeItem(self._selection_item)
            self._selection_item = None
        self._current_rect = QRectF()

    def get_selection_rect_pdf(self) -> Optional[Rect]:
        """
        Zwraca aktualny prostokąt zaznaczenia w współrzędnych PDF.

        Returns:
            Rect w współrzędnych PDF lub None jeśli brak zaznaczenia
        """
        if self._current_rect.isEmpty():
            return None

        return self._pixel_to_pdf_rect(self._current_rect)

    def _pixel_to_pdf_rect(self, pixel_rect: QRectF) -> Rect:
        """Konwertuje prostokąt z pikseli na współrzędne PDF."""
        if self._pixmap_width == 0 or self._pixmap_height == 0:
            return Rect(0, 0, 0, 0)

        scale_x = self._pdf_width / self._pixmap_width
        scale_y = self._pdf_height / self._pixmap_height

        return Rect(
            x0=pixel_rect.left() * scale_x,
            y0=pixel_rect.top() * scale_y,
            x1=pixel_rect.right() * scale_x,
            y1=pixel_rect.bottom() * scale_y,
        )

    def _pdf_to_pixel_rect(self, pdf_rect: Rect) -> QRectF:
        """Konwertuje prostokąt z współrzędnych PDF na piksele."""
        if self._pdf_width == 0 or self._pdf_height == 0:
            return QRectF()

        scale_x = self._pixmap_width / self._pdf_width
        scale_y = self._pixmap_height / self._pdf_height

        return QRectF(
            pdf_rect.x0 * scale_x,
            pdf_rect.y0 * scale_y,
            pdf_rect.width * scale_x,
            pdf_rect.height * scale_y,
        )

    def set_selection_from_pdf(self, pdf_rect: Rect) -> None:
        """Ustawia zaznaczenie na podstawie współrzędnych PDF."""
        pixel_rect = self._pdf_to_pixel_rect(pdf_rect)
        self._update_selection(pixel_rect)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Rozpoczyna zaznaczanie."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clear_selection()
            scene_pos = self.mapToScene(event.pos())
            self._start_pos = scene_pos
            self._is_selecting = True

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Aktualizuje zaznaczenie podczas przeciągania."""
        if self._is_selecting and self._start_pos:
            scene_pos = self.mapToScene(event.pos())

            # Oblicz prostokąt
            x1 = min(self._start_pos.x(), scene_pos.x())
            y1 = min(self._start_pos.y(), scene_pos.y())
            x2 = max(self._start_pos.x(), scene_pos.x())
            y2 = max(self._start_pos.y(), scene_pos.y())

            rect = QRectF(x1, y1, x2 - x1, y2 - y1)

            # Ogranicz do granic strony
            if self._page_item:
                rect = rect.intersected(self._page_item.boundingRect())

            self._update_selection(rect)
            self.selection_changed.emit(rect)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Kończy zaznaczanie."""
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False
            self._start_pos = None

            if not self._current_rect.isEmpty():
                self.selection_completed.emit(self._current_rect)

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Obsługa scrolla do zoomu. Ctrl+scroll = zoom."""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def zoom_in(self) -> None:
        """Powiększa widok."""
        factor = 1.15
        new_zoom = self._zoom_factor * factor
        if new_zoom <= 5.0:  # Max 500%
            self._zoom_factor = new_zoom
            self.scale(factor, factor)
            self.zoom_changed.emit(self._zoom_factor)

    def zoom_out(self) -> None:
        """Pomniejsza widok."""
        factor = 1.15
        new_zoom = self._zoom_factor / factor
        if new_zoom >= 0.1:  # Min 10%
            self._zoom_factor = new_zoom
            self.scale(1 / factor, 1 / factor)
            self.zoom_changed.emit(self._zoom_factor)

    def zoom_reset(self) -> None:
        """Resetuje zoom do początkowego widoku (35%)."""
        self.resetTransform()
        self._zoom_factor = 0.35
        self.scale(self._zoom_factor, self._zoom_factor)
        self.zoom_changed.emit(self._zoom_factor)

    def get_zoom_factor(self) -> float:
        """Zwraca aktualny współczynnik zoomu."""
        return self._zoom_factor

    def _update_selection(self, rect: QRectF) -> None:
        """Aktualizuje wizualne zaznaczenie."""
        self._current_rect = rect

        if self._selection_item:
            self._selection_item.setRect(rect)
        else:
            self._selection_item = SelectionRectItem(rect)
            self._scene.addItem(self._selection_item)


class InteractivePagePreview(QWidget):
    """
    Kontener dla interaktywnego podglądu strony PDF.

    Zawiera:
    - PageGraphicsView do wyświetlania i zaznaczania
    - Checkbox "Dopasuj do tekstu"
    - Label z informacją o zaznaczeniu

    Sygnały:
        selection_completed: Emitowany gdy zaznaczenie jest zakończone
                            (Rect w PDF, lista słów)
    """

    selection_completed = pyqtSignal(Rect, list)

    def __init__(self, pdf_manager: "PDFManager", parent=None):
        super().__init__(parent)

        self._pdf_manager = pdf_manager
        self._current_page_index = -1
        self._snap_to_text = True

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Tworzy interfejs użytkownika."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Panel górny z kontrolkami zoom
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 4)

        top_layout.addStretch()

        # Przyciski zoom
        zoom_label = QLabel("Zoom:")
        zoom_label.setStyleSheet("color: #8892a0; font-size: 11px;")
        top_layout.addWidget(zoom_label)

        zoom_btn_style = """
            QPushButton {
                background-color: #1f2940;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
                min-width: 28px;
                min-height: 24px;
                padding: 2px 6px;
            }
            QPushButton:hover {
                background-color: #2d3a50;
                border-color: #e0a800;
            }
            QPushButton:pressed {
                background-color: #3d4a60;
            }
        """

        self._zoom_out_btn = QPushButton("-")
        self._zoom_out_btn.setStyleSheet(zoom_btn_style)
        self._zoom_out_btn.setToolTip("Pomniejsz (Ctrl+scroll w dół)")
        self._zoom_out_btn.clicked.connect(self._on_zoom_out)
        top_layout.addWidget(self._zoom_out_btn)

        self._zoom_label = QLabel("0")
        self._zoom_label.setStyleSheet("color: #ffffff; font-size: 11px; min-width: 40px;")
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(self._zoom_label)

        self._zoom_in_btn = QPushButton("+")
        self._zoom_in_btn.setStyleSheet(zoom_btn_style)
        self._zoom_in_btn.setToolTip("Powiększ (Ctrl+scroll w górę)")
        self._zoom_in_btn.clicked.connect(self._on_zoom_in)
        top_layout.addWidget(self._zoom_in_btn)

        self._zoom_reset_btn = QPushButton("Reset")
        self._zoom_reset_btn.setStyleSheet(zoom_btn_style.replace("min-width: 28px", "min-width: 40px"))
        self._zoom_reset_btn.setToolTip("Resetuj zoom do 100%")
        self._zoom_reset_btn.clicked.connect(self._on_zoom_reset)
        top_layout.addWidget(self._zoom_reset_btn)

        layout.addLayout(top_layout)

        # Widok strony
        self._view = PageGraphicsView()
        self._view.selection_changed.connect(self._on_selection_changed)
        self._view.selection_completed.connect(self._on_selection_completed)
        self._view.zoom_changed.connect(self._on_zoom_changed)
        layout.addWidget(self._view, 1)

        # Panel dolny
        bottom_layout = QHBoxLayout()

        self._snap_checkbox = QCheckBox("Dopasuj do granic tekstu")
        self._snap_checkbox.setChecked(True)
        self._snap_checkbox.setStyleSheet("color: #ffffff;")
        self._snap_checkbox.toggled.connect(self._on_snap_toggled)
        bottom_layout.addWidget(self._snap_checkbox)

        bottom_layout.addStretch()

        self._info_label = QLabel("Kliknij i przeciągnij aby zaznaczyć obszar")
        self._info_label.setStyleSheet("color: #8892a0; font-size: 11px;")
        bottom_layout.addWidget(self._info_label)

        layout.addLayout(bottom_layout)

    def set_page(self, page_index: int) -> None:
        """
        Ładuje stronę do podglądu.

        Args:
            page_index: Indeks strony (0-indexed)
        """
        if not self._pdf_manager.is_loaded:
            return

        self._current_page_index = page_index

        # Renderuj stronę jako PNG (wyższe DPI dla lepszej czytelności)
        png_data = self._pdf_manager.generate_preview(page_index, dpi=200)

        # Utwórz QPixmap z PNG
        pixmap = QPixmap()
        pixmap.loadFromData(png_data)

        # Pobierz rozmiar strony PDF
        page_info = self._pdf_manager.get_page_info(page_index)

        self._view.set_page(pixmap, page_info.width, page_info.height)
        self._view.clear_selection()
        self._info_label.setText("Kliknij i przeciągnij aby zaznaczyć obszar")
        # Zaktualizuj label zoomu (0 = początkowy widok 35%)
        self._zoom_label.setText("0")

    def _on_snap_toggled(self, checked: bool) -> None:
        """Obsługuje zmianę checkboxa snap."""
        self._snap_to_text = checked

    def _on_zoom_in(self) -> None:
        """Powiększa podgląd."""
        self._view.zoom_in()

    def _on_zoom_out(self) -> None:
        """Pomniejsza podgląd."""
        self._view.zoom_out()

    def _on_zoom_reset(self) -> None:
        """Resetuje zoom."""
        self._view.zoom_reset()

    def _on_zoom_changed(self, factor: float) -> None:
        """Aktualizuje wyświetlany poziom zoomu."""
        # 0.35 = 0, każde +15% dodaje do wyświetlanej wartości
        # Przelicz: (factor - 0.35) / 0.35 * 100 daje przybliżoną skalę
        display_value = int((factor - 0.35) / 0.0525)  # ~15% kroków od bazy
        self._zoom_label.setText(f"{display_value}")

    def _on_selection_changed(self, rect: QRectF) -> None:
        """Obsługuje zmianę zaznaczenia podczas przeciągania."""
        pdf_rect = self._view.get_selection_rect_pdf()
        if pdf_rect:
            self._info_label.setText(
                f"Zaznaczenie: ({int(pdf_rect.x0)}, {int(pdf_rect.y0)}) - "
                f"({int(pdf_rect.x1)}, {int(pdf_rect.y1)})"
            )

    def _on_selection_completed(self, pixel_rect: QRectF) -> None:
        """Obsługuje zakończenie zaznaczania."""
        pdf_rect = self._view.get_selection_rect_pdf()
        if not pdf_rect:
            return

        selected_words: List[str] = []

        # Dopasuj do tekstu jeśli włączone
        if self._snap_to_text and self._current_page_index >= 0:
            snapped_rect, selected_words = self._pdf_manager.snap_rect_to_words(
                self._current_page_index, pdf_rect
            )

            if selected_words:
                pdf_rect = snapped_rect
                # Zaktualizuj wizualne zaznaczenie
                self._view.set_selection_from_pdf(pdf_rect)

        # Aktualizuj info
        if selected_words:
            words_preview = " ".join(selected_words)
            if len(words_preview) > 40:
                words_preview = words_preview[:37] + "..."
            self._info_label.setText(f'Zaznaczono: "{words_preview}"')
        else:
            self._info_label.setText(
                f"Zaznaczenie: ({int(pdf_rect.x0)}, {int(pdf_rect.y0)}) - "
                f"({int(pdf_rect.x1)}, {int(pdf_rect.y1)})"
            )

        self.selection_completed.emit(pdf_rect, selected_words)

    def get_selection(self) -> Optional[Rect]:
        """Zwraca aktualne zaznaczenie w współrzędnych PDF."""
        return self._view.get_selection_rect_pdf()

    def clear_selection(self) -> None:
        """Czyści zaznaczenie."""
        self._view.clear_selection()
        self._info_label.setText("Kliknij i przeciągnij aby zaznaczyć obszar")
