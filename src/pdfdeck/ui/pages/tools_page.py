"""
ToolsPage - Strona narzędzi formatowania.

Funkcje:
- A4 Enforcer (normalizacja do A4)
- N-up (wiele stron na kartce)
- Kompresja/Optymalizacja
"""

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QMessageBox, QFileDialog, QCheckBox,
    QScrollArea, QFrame, QSplitter, QSizePolicy
)
from PyQt6.QtCore import Qt

from pdfdeck.ui.pages.base_page import BasePage
from pdfdeck.ui.widgets.styled_button import StyledButton
from pdfdeck.ui.widgets.styled_combo import StyledComboBox
from pdfdeck.core.models import NupConfig, PageSize

if TYPE_CHECKING:
    from pdfdeck.core.pdf_manager import PDFManager


class ToolsPage(BasePage):
    """
    Strona narzędzi formatowania.

    Układ:
    +------------------------------------------+
    |  Tytuł: Narzędzia                        |
    +------------------------------------------+
    |  +----------------+  +------------------+ |
    |  | A4 Enforcer    |  | N-up            | |
    |  | [Normalizuj]   |  | [2] [4] strony  | |
    |  +----------------+  | [Generuj]       | |
    |  | Kompresja      |  +------------------+ |
    |  | [Optymalizuj]  |                      |
    |  +----------------+                      |
    +------------------------------------------+
    """

    def __init__(self, pdf_manager: "PDFManager", parent=None):
        super().__init__("Narzędzia", parent)

        self._pdf_manager = pdf_manager
        self._setup_tools_ui()

    def _setup_tools_ui(self) -> None:
        """Tworzy interfejs narzędzi."""
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

        # === Lewa kolumna ===
        left_widget = QWidget()
        left_widget.setMinimumWidth(250)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(10)

        # --- A4 Enforcer ---
        a4_group = QGroupBox("A4 Enforcer")
        a4_group.setStyleSheet(self._group_style())
        a4_layout = QVBoxLayout(a4_group)

        a4_desc = QLabel(
            "Normalizuje wszystkie strony do formatu A4.\n\n"
            "• Zachowuje proporcje treści\n"
            "• Dodaje białe marginesy\n"
            "• Idealne do druku"
        )
        a4_desc.setStyleSheet("color: #8892a0; font-size: 13px;")
        a4_desc.setWordWrap(True)
        a4_layout.addWidget(a4_desc)

        self._a4_btn = StyledButton("Normalizuj do A4", "primary")
        self._a4_btn.clicked.connect(self._on_normalize_a4)
        a4_layout.addWidget(self._a4_btn)

        left_layout.addWidget(a4_group)

        # --- Kompresja ---
        compress_group = QGroupBox("Kompresja i optymalizacja")
        compress_group.setStyleSheet(self._group_style())
        compress_layout = QVBoxLayout(compress_group)

        compress_desc = QLabel(
            "Optymalizuje rozmiar pliku PDF.\n\n"
            "• Garbage collection\n"
            "• Kompresja strumieni\n"
            "• Czyszczenie struktury"
        )
        compress_desc.setStyleSheet("color: #8892a0; font-size: 13px;")
        compress_desc.setWordWrap(True)
        compress_layout.addWidget(compress_desc)

        self._compress_btn = StyledButton("Zapisz zoptymalizowany", "primary")
        self._compress_btn.clicked.connect(self._on_optimize)
        compress_layout.addWidget(self._compress_btn)

        left_layout.addWidget(compress_group)
        left_layout.addStretch()

        splitter.addWidget(left_widget)

        # === Prawa kolumna ===
        right_widget = QWidget()
        right_widget.setMinimumWidth(250)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(10)

        # --- N-up ---
        nup_group = QGroupBox("N-up (wiele stron na kartce)")
        nup_group.setStyleSheet(self._group_style())
        nup_layout = QVBoxLayout(nup_group)
        nup_layout.setSpacing(8)

        nup_desc = QLabel(
            "Umieszcza wiele stron na jednej kartce.\n"
            "Idealne do przeglądania lub oszczędzania papieru."
        )
        nup_desc.setStyleSheet("color: #8892a0; font-size: 13px;")
        nup_desc.setWordWrap(True)
        nup_layout.addWidget(nup_desc)

        # Liczba stron na kartce
        pages_row = QHBoxLayout()
        pages_label = QLabel("Stron:")
        pages_label.setStyleSheet("color: #8892a0;")
        pages_label.setFixedWidth(70)
        pages_row.addWidget(pages_label)

        self._nup_combo = StyledComboBox()
        self._nup_combo.addItem("2 strony", 2)
        self._nup_combo.addItem("4 strony", 4)
        self._nup_combo.addItem("6 stron", 6)
        self._nup_combo.addItem("9 stron", 9)
        pages_row.addWidget(self._nup_combo)
        pages_row.addStretch()
        nup_layout.addLayout(pages_row)

        # Orientacja
        orient_row = QHBoxLayout()
        orient_label = QLabel("Orientacja:")
        orient_label.setStyleSheet("color: #8892a0;")
        orient_label.setFixedWidth(70)
        orient_row.addWidget(orient_label)

        self._landscape_checkbox = QCheckBox("Pozioma")
        self._landscape_checkbox.setStyleSheet(self._checkbox_style())
        orient_row.addWidget(self._landscape_checkbox)
        orient_row.addStretch()
        nup_layout.addLayout(orient_row)

        # Rozmiar wyjściowy
        size_row = QHBoxLayout()
        size_label = QLabel("Rozmiar:")
        size_label.setStyleSheet("color: #8892a0;")
        size_label.setFixedWidth(70)
        size_row.addWidget(size_label)

        self._output_size_combo = StyledComboBox()
        self._output_size_combo.addItem("A4", PageSize.A4)
        self._output_size_combo.addItem("A3", PageSize.A3)
        self._output_size_combo.addItem("Letter", PageSize.LETTER)
        size_row.addWidget(self._output_size_combo)
        size_row.addStretch()
        nup_layout.addLayout(size_row)

        self._nup_btn = StyledButton("Generuj N-up", "primary")
        self._nup_btn.clicked.connect(self._on_create_nup)
        nup_layout.addWidget(self._nup_btn)

        right_layout.addWidget(nup_group)
        right_layout.addStretch()

        splitter.addWidget(right_widget)
        splitter.setSizes([350, 350])

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

    def _checkbox_style(self) -> str:
        """Zwraca styl dla QCheckBox."""
        return """
            QCheckBox {
                color: #8892a0;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #2d3a50;
                background-color: #0f1629;
            }
            QCheckBox::indicator:checked {
                background-color: #e0a800;
                border-color: #e0a800;
            }
            QCheckBox::indicator:hover {
                border-color: #e0a800;
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

    def _on_normalize_a4(self) -> None:
        """Obsługa normalizacji do A4."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(
                self,
                "Błąd",
                "Najpierw otwórz dokument PDF"
            )
            return

        try:
            self._pdf_manager.normalize_to_a4()
            QMessageBox.information(
                self,
                "Sukces",
                "Wszystkie strony zostały znormalizowane do A4.\n"
                "Pamiętaj o zapisaniu dokumentu."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie można znormalizować stron:\n{e}"
            )

    def _on_optimize(self) -> None:
        """Obsługa optymalizacji."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(
                self,
                "Błąd",
                "Najpierw otwórz dokument PDF"
            )
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz zoptymalizowany PDF",
            "",
            "Pliki PDF (*.pdf)"
        )

        if filepath:
            try:
                self._pdf_manager.save(filepath, optimize=True)
                QMessageBox.information(
                    self,
                    "Sukces",
                    f"Zoptymalizowany dokument zapisany:\n{filepath}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Błąd",
                    f"Nie można zapisać dokumentu:\n{e}"
                )

    def _on_create_nup(self) -> None:
        """Obsługa tworzenia N-up."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(
                self,
                "Błąd",
                "Najpierw otwórz dokument PDF"
            )
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz N-up PDF",
            "",
            "Pliki PDF (*.pdf)"
        )

        if filepath:
            try:
                config = NupConfig(
                    pages_per_sheet=self._nup_combo.currentData(),
                    landscape=self._landscape_checkbox.isChecked(),
                    output_size=self._output_size_combo.currentData(),
                )

                pdf_bytes = self._pdf_manager.create_nup(config)

                with open(filepath, "wb") as f:
                    f.write(pdf_bytes)

                QMessageBox.information(
                    self,
                    "Sukces",
                    f"N-up PDF zapisany:\n{filepath}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Błąd",
                    f"Nie można utworzyć N-up:\n{e}"
                )

    # === Public API ===

    def on_document_loaded(self) -> None:
        """Wywoływane po załadowaniu dokumentu."""
        pass
