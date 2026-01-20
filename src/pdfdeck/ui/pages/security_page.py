"""
SecurityPage - Strona bezpieczeństwa dokumentu.

Funkcje:
- Metadata Scrubber (usuwanie metadanych)
- Flatten (spłaszczanie formularzy i adnotacji)
- Podgląd metadanych
"""

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QScrollArea, QFrame, QSplitter, QSizePolicy
)
from PyQt6.QtCore import Qt

from pdfdeck.ui.pages.base_page import BasePage
from pdfdeck.ui.widgets.styled_button import StyledButton

if TYPE_CHECKING:
    from pdfdeck.core.pdf_manager import PDFManager


class SecurityPage(BasePage):
    """
    Strona bezpieczeństwa dokumentu.

    Układ:
    +------------------------------------------+
    |  Tytuł: Bezpieczeństwo                   |
    +------------------------------------------+
    |  +------------------+  +---------------+ |
    |  | Metadane         |  | Akcje         | |
    |  | Autor: ...       |  | [Usuń meta]   | |
    |  | Data: ...        |  | [Spłaszcz]    | |
    |  | ...              |  |               | |
    |  +------------------+  +---------------+ |
    +------------------------------------------+
    """

    def __init__(self, pdf_manager: "PDFManager", parent=None):
        super().__init__("Bezpieczeństwo", parent)

        self._pdf_manager = pdf_manager
        self._setup_security_ui()

    def _setup_security_ui(self) -> None:
        """Tworzy interfejs bezpieczeństwa."""
        # Scroll area dla całej zawartości
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(self._scroll_style())

        # Kontener wewnętrzny
        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 10, 0)
        content_layout.setSpacing(15)

        # Splitter dla dwóch kolumn
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #2d3a50;
                width: 3px;
            }
            QSplitter::handle:hover {
                background-color: #e0a800;
            }
        """)

        # === Lewa strona: Metadane ===
        metadata_group = QGroupBox("Metadane dokumentu")
        metadata_group.setMinimumWidth(250)
        metadata_group.setStyleSheet(self._group_style())
        metadata_layout = QVBoxLayout(metadata_group)

        # Tabela metadanych
        self._metadata_table = QTableWidget()
        self._metadata_table.setColumnCount(2)
        self._metadata_table.setHorizontalHeaderLabels(["Pole", "Wartość"])
        self._metadata_table.horizontalHeader().setStretchLastSection(True)
        self._metadata_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._metadata_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._metadata_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._metadata_table.setStyleSheet(self._table_style())
        metadata_layout.addWidget(self._metadata_table)

        # Przycisk odśwież
        refresh_btn = StyledButton("Odśwież metadane", "secondary")
        refresh_btn.clicked.connect(self._refresh_metadata)
        metadata_layout.addWidget(refresh_btn)

        splitter.addWidget(metadata_group)

        # === Prawa strona: Akcje ===
        actions_widget = QWidget()
        actions_widget.setMinimumWidth(250)
        actions_layout = QVBoxLayout(actions_widget)
        actions_layout.setContentsMargins(10, 0, 0, 0)
        actions_layout.setSpacing(10)

        # --- Metadata Scrubber ---
        scrub_group = QGroupBox("Usuwanie metadanych")
        scrub_group.setStyleSheet(self._group_style())
        scrub_layout = QVBoxLayout(scrub_group)

        scrub_desc = QLabel(
            "Usuwa wszystkie metadane:\n"
            "• Autor, Tytuł\n"
            "• Daty utworzenia/modyfikacji\n"
            "• Producent, Słowa kluczowe\n"
            "• XMP metadata"
        )
        scrub_desc.setStyleSheet("color: #8892a0; font-size: 13px;")
        scrub_desc.setWordWrap(True)
        scrub_layout.addWidget(scrub_desc)

        self._scrub_btn = StyledButton("Usuń metadane", "danger")
        self._scrub_btn.clicked.connect(self._on_scrub_metadata)
        scrub_layout.addWidget(self._scrub_btn)

        actions_layout.addWidget(scrub_group)

        # --- Flatten ---
        flatten_group = QGroupBox("Spłaszczanie dokumentu")
        flatten_group.setStyleSheet(self._group_style())
        flatten_layout = QVBoxLayout(flatten_group)

        flatten_desc = QLabel(
            "Spłaszcza interaktywne elementy:\n"
            "• Formularze PDF\n"
            "• Adnotacje i komentarze\n\n"
            "Elementy staną się nieedytowalne."
        )
        flatten_desc.setStyleSheet("color: #8892a0; font-size: 13px;")
        flatten_desc.setWordWrap(True)
        flatten_layout.addWidget(flatten_desc)

        self._flatten_btn = StyledButton("Spłaszcz dokument", "warning")
        self._flatten_btn.clicked.connect(self._on_flatten)
        flatten_layout.addWidget(self._flatten_btn)

        actions_layout.addWidget(flatten_group)
        actions_layout.addStretch()

        splitter.addWidget(actions_widget)
        splitter.setSizes([400, 300])

        content_layout.addWidget(splitter, 1)

        scroll.setWidget(content)
        self.add_widget(scroll)

    def _group_style(self) -> str:
        """Zwraca styl dla QGroupBox."""
        return """
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                border: 1px solid #2d3a50;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
        """

    def _table_style(self) -> str:
        """Zwraca styl dla QTableWidget."""
        return """
            QTableWidget {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 6px;
                gridline-color: #2d3a50;
            }
            QTableWidget::item {
                padding: 8px;
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #e0a800;
                color: #1a1a2e;
            }
            QHeaderView::section {
                background-color: #1f2940;
                color: #8892a0;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #2d3a50;
            }
        """

    def _scroll_style(self) -> str:
        """Zwraca styl dla QScrollArea."""
        return """
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #0f1629;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #2d3a50;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #e0a800;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background-color: #0f1629;
                height: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background-color: #2d3a50;
                border-radius: 5px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #e0a800;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """

    def _refresh_metadata(self) -> None:
        """Odświeża widok metadanych."""
        self._metadata_table.setRowCount(0)

        if not self._pdf_manager.is_loaded:
            return

        try:
            meta = self._pdf_manager.get_metadata()

            fields = [
                ("Tytuł", meta.title),
                ("Autor", meta.author),
                ("Temat", meta.subject),
                ("Słowa kluczowe", meta.keywords),
                ("Twórca", meta.creator),
                ("Producent", meta.producer),
                ("Data utworzenia", meta.creation_date),
                ("Data modyfikacji", meta.modification_date),
            ]

            for name, value in fields:
                row = self._metadata_table.rowCount()
                self._metadata_table.insertRow(row)
                self._metadata_table.setItem(row, 0, QTableWidgetItem(name))
                self._metadata_table.setItem(row, 1, QTableWidgetItem(value or "(brak)"))

        except Exception as e:
            QMessageBox.warning(
                self,
                "Błąd",
                f"Nie można odczytać metadanych:\n{e}"
            )

    def _on_scrub_metadata(self) -> None:
        """Obsługa usuwania metadanych."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(
                self,
                "Błąd",
                "Najpierw otwórz dokument PDF"
            )
            return

        reply = QMessageBox.question(
            self,
            "Potwierdź usunięcie",
            "Czy na pewno chcesz usunąć wszystkie metadane?\n\n"
            "Ta operacja jest nieodwracalna.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._pdf_manager.scrub_metadata()
                self._refresh_metadata()
                QMessageBox.information(
                    self,
                    "Sukces",
                    "Metadane zostały usunięte.\n"
                    "Pamiętaj o zapisaniu dokumentu."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Błąd",
                    f"Nie można usunąć metadanych:\n{e}"
                )

    def _on_flatten(self) -> None:
        """Obsługa spłaszczania dokumentu."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(
                self,
                "Błąd",
                "Najpierw otwórz dokument PDF"
            )
            return

        reply = QMessageBox.question(
            self,
            "Potwierdź spłaszczenie",
            "Czy na pewno chcesz spłaszczyć dokument?\n\n"
            "Formularze i adnotacje staną się nieedytowalne.\n"
            "Ta operacja jest nieodwracalna.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._pdf_manager.flatten()
                QMessageBox.information(
                    self,
                    "Sukces",
                    "Dokument został spłaszczony.\n"
                    "Pamiętaj o zapisaniu dokumentu."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Błąd",
                    f"Nie można spłaszczyć dokumentu:\n{e}"
                )

    # === Public API ===

    def on_document_loaded(self) -> None:
        """Wywoływane po załadowaniu dokumentu."""
        self._refresh_metadata()
