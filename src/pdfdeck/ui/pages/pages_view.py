"""
PagesView - Główny widok stron PDF.

Zawiera:
- Siatkę miniatur z drag & drop
- Podgląd wybranej strony
- Przyciski akcji (usuń, zapisz)
"""

from typing import TYPE_CHECKING, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from pdfdeck.ui.pages.base_page import BasePage
from pdfdeck.ui.widgets.thumbnail_grid import ThumbnailGrid
from pdfdeck.ui.widgets.styled_button import StyledButton

if TYPE_CHECKING:
    from pdfdeck.core.pdf_manager import PDFManager


class PagePreview(QWidget):
    """Widget podglądu strony."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Tworzy interfejs."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Etykieta z obrazem
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet("""
            QLabel {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 8px;
            }
        """)

        layout.addWidget(self._image_label)

    def set_image(self, png_data: bytes) -> None:
        """Ustawia obraz podglądu."""
        pixmap = QPixmap()
        pixmap.loadFromData(png_data)

        # Skaluj do rozmiaru widgetu zachowując proporcje
        scaled = pixmap.scaled(
            self._image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self._image_label.setPixmap(scaled)

    def clear(self) -> None:
        """Czyści podgląd."""
        self._image_label.clear()

    def resizeEvent(self, event) -> None:
        """Obsługa zmiany rozmiaru."""
        super().resizeEvent(event)
        # Przerysuj obraz jeśli istnieje
        pixmap = self._image_label.pixmap()
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(
                self._image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self._image_label.setPixmap(scaled)


class PagesView(BasePage):
    """
    Widok stron PDF.

    Układ:
    +------------------------------------------+
    |  Tytuł: Strony                           |
    +------------------------------------------+
    |  +------------------+  +---------------+ |
    |  |                  |  |               | |
    |  |  ThumbnailGrid   |  |  PagePreview  | |
    |  |  (Drag & Drop)   |  |               | |
    |  |                  |  |               | |
    |  +------------------+  +---------------+ |
    +------------------------------------------+
    |  Zaznaczono: X stron    [Usuń] [Zapisz]  |
    +------------------------------------------+
    """

    def __init__(self, pdf_manager: "PDFManager", parent=None):
        super().__init__("Strony", parent)

        self._pdf_manager = pdf_manager
        self._selected_page: Optional[int] = None

        self._setup_pages_ui()
        self._connect_signals()

    def _setup_pages_ui(self) -> None:
        """Tworzy interfejs widoku stron."""
        # === Splitter (thumbnail grid | preview) ===
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #2d3a50;
                width: 2px;
            }
            QSplitter::handle:hover {
                background-color: #e0a800;
            }
        """)

        # Lewa strona: ThumbnailGrid
        self._thumbnail_grid = ThumbnailGrid()
        splitter.addWidget(self._thumbnail_grid)

        # Prawa strona: PagePreview
        self._page_preview = PagePreview()
        splitter.addWidget(self._page_preview)

        # Proporcje (60% thumbnails, 40% preview)
        splitter.setSizes([600, 400])

        self.add_widget(splitter)

        # === Dolny pasek (info + przyciski) ===
        bottom_bar = QWidget()
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(0, 10, 0, 0)

        # Info o zaznaczeniu
        self._selection_label = QLabel("Zaznaczono: 0 stron")
        self._selection_label.setStyleSheet("color: #8892a0; font-size: 14px;")
        bottom_layout.addWidget(self._selection_label)

        bottom_layout.addStretch()

        # Przycisk "Usuń"
        self._delete_btn = StyledButton("Usuń", "danger")
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete_pages)
        bottom_layout.addWidget(self._delete_btn)

        # Przycisk "Zapisz PDF"
        self._save_btn = StyledButton("Zapisz PDF", "primary")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._on_save)
        bottom_layout.addWidget(self._save_btn)

        self.add_widget(bottom_bar)

    def _connect_signals(self) -> None:
        """Łączy sygnały."""
        # Zmiana zaznaczenia
        self._thumbnail_grid.selection_changed.connect(self._on_selection_changed)

        # Zmiana kolejności (drag & drop)
        self._thumbnail_grid.order_changed.connect(self._on_order_changed)

        # Drop plików z zewnątrz
        self._thumbnail_grid.files_dropped.connect(self._on_files_dropped)

        # Żądanie usunięcia
        self._thumbnail_grid.delete_requested.connect(self._on_delete_pages_requested)

        # Żądanie podziału
        self._thumbnail_grid.split_requested.connect(self._on_split_requested)

    # === Handlers ===

    def _on_selection_changed(self, page_index: int) -> None:
        """Obsługa zmiany zaznaczenia."""
        self._selected_page = page_index

        # Aktualizuj podgląd
        if page_index >= 0 and self._pdf_manager.is_loaded:
            try:
                png_data = self._pdf_manager.generate_preview(page_index, dpi=150)
                self._page_preview.set_image(png_data)
            except Exception:
                self._page_preview.clear()
        else:
            self._page_preview.clear()

        # Aktualizuj info o zaznaczeniu
        selected = self._thumbnail_grid.get_selected_indices()
        count = len(selected)
        self._selection_label.setText(f"Zaznaczono: {count} stron")
        self._delete_btn.setEnabled(count > 0)

    def _on_order_changed(self, new_order: list) -> None:
        """Obsługa zmiany kolejności stron."""
        try:
            self._pdf_manager.reorder_pages(new_order)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Błąd",
                f"Nie można zmienić kolejności stron:\n{e}"
            )

    def _on_files_dropped(self, file_paths: list, insert_pos: int) -> None:
        """Obsługa drop plików PDF z zewnątrz."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(
                self,
                "Błąd",
                "Najpierw otwórz dokument PDF"
            )
            return

        for filepath in file_paths:
            try:
                self._pdf_manager.merge_document(filepath, insert_pos)
                insert_pos += 1  # Przesuwaj pozycję dla kolejnych plików
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Błąd",
                    f"Nie można połączyć pliku:\n{filepath}\n{e}"
                )

        # Odśwież widok
        self.on_document_loaded()

    def _on_delete_pages_requested(self, page_indices: list) -> None:
        """Obsługa żądania usunięcia stron."""
        self._on_delete_pages()

    def _on_delete_pages(self) -> None:
        """Obsługa usuwania stron."""
        selected = self._thumbnail_grid.get_selected_indices()
        if not selected:
            return

        # Potwierdzenie
        count = len(selected)
        reply = QMessageBox.question(
            self,
            "Potwierdź usunięcie",
            f"Czy na pewno chcesz usunąć {count} stron(y)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._pdf_manager.delete_pages(selected)
                self.on_document_loaded()  # Odśwież widok
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Błąd",
                    f"Nie można usunąć stron:\n{e}"
                )

    def _on_split_requested(self, page_index: int) -> None:
        """Obsługa żądania podziału dokumentu."""
        # Zapytaj o lokalizację zapisu
        save_dir = QFileDialog.getExistingDirectory(
            self,
            "Wybierz katalog do zapisania części",
            ""
        )

        if not save_dir:
            return

        try:
            # Podziel dokument
            parts = self._pdf_manager.split_at([page_index])

            # Zapisz części
            from pathlib import Path
            base_name = self._pdf_manager.filepath.stem if self._pdf_manager.filepath else "document"

            for i, part_data in enumerate(parts):
                output_path = Path(save_dir) / f"{base_name}_part{i + 1}.pdf"
                with open(output_path, "wb") as f:
                    f.write(part_data)

            QMessageBox.information(
                self,
                "Sukces",
                f"Dokument został podzielony na {len(parts)} części"
            )

        except Exception as e:
            QMessageBox.warning(
                self,
                "Błąd",
                f"Nie można podzielić dokumentu:\n{e}"
            )

    def _on_save(self) -> None:
        """Obsługa zapisywania dokumentu."""
        if not self._pdf_manager.is_loaded:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz plik PDF",
            "",
            "Pliki PDF (*.pdf)"
        )

        if filepath:
            try:
                self._pdf_manager.save(filepath)
                QMessageBox.information(
                    self,
                    "Sukces",
                    f"Dokument został zapisany:\n{filepath}"
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Błąd",
                    f"Nie można zapisać dokumentu:\n{e}"
                )

    # === Public API ===

    def on_document_loaded(self) -> None:
        """Wywoływane po załadowaniu dokumentu."""
        if self._pdf_manager.is_loaded:
            self._thumbnail_grid.set_page_count(self._pdf_manager.page_count)
            self._save_btn.setEnabled(True)
            self._page_preview.clear()
        else:
            self._thumbnail_grid.clear()
            self._save_btn.setEnabled(False)
            self._delete_btn.setEnabled(False)
            self._page_preview.clear()

    def on_thumbnail_ready(self, page_index: int, png_data: bytes) -> None:
        """Wywoływane gdy miniatura jest gotowa."""
        self._thumbnail_grid.set_thumbnail(page_index, png_data)
