"""
RedactionPage - Strona Smart Redaction (RODO/GDPR).

Funkcje:
- Wyszukiwanie tekstu i wzorców regex
- Podgląd wyników wyszukiwania
- Redakcja (nieodwracalne zamazywanie)
- Whiteout & Type (zakrywanie bez usuwania)
"""

from typing import TYPE_CHECKING, List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QListWidget, QListWidgetItem,
    QSplitter, QMessageBox, QCheckBox, QGroupBox,
    QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from pdfdeck.ui.pages.base_page import BasePage
from pdfdeck.ui.widgets.styled_button import StyledButton
from pdfdeck.ui.widgets.styled_combo import StyledComboBox
from pdfdeck.utils.regex_patterns import REDACTION_PATTERNS, get_pattern_description
from pdfdeck.core.models import SearchResult

if TYPE_CHECKING:
    from pdfdeck.core.pdf_manager import PDFManager


class RedactionPage(BasePage):
    """
    Strona Smart Redaction.

    Układ:
    +------------------------------------------+
    |  Tytuł: Redakcja                         |
    +------------------------------------------+
    |  [Wzorzec v] [Szukaj...]     [Szukaj]    |
    +------------------------------------------+
    |  +------------------+  +---------------+ |
    |  | Lista wyników    |  | Podgląd       | |
    |  | [ ] PESEL: 123.. |  | strony        | |
    |  | [x] Email: ...   |  |               | |
    |  +------------------+  +---------------+ |
    +------------------------------------------+
    |  [Zaznacz wszystkie]   [Redaguj]         |
    +------------------------------------------+
    """

    def __init__(self, pdf_manager: "PDFManager", parent=None):
        super().__init__("Redakcja", parent)

        self._pdf_manager = pdf_manager
        self._search_results: List[SearchResult] = []

        self._setup_redaction_ui()

    def _setup_redaction_ui(self) -> None:
        """Tworzy interfejs redakcji."""
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
        content_layout.setSpacing(10)

        # === Pasek wyszukiwania ===
        search_group = QGroupBox("Wyszukiwanie")
        search_group.setStyleSheet(self._group_style())
        search_inner = QVBoxLayout(search_group)

        # Pierwszy wiersz: wzorzec
        pattern_row = QHBoxLayout()
        pattern_label = QLabel("Wzorzec:")
        pattern_label.setStyleSheet("color: #8892a0;")
        pattern_label.setFixedWidth(60)
        pattern_row.addWidget(pattern_label)

        self._pattern_combo = StyledComboBox()
        self._pattern_combo.addItem("-- Własny tekst --", "")
        for pattern_name, pattern in REDACTION_PATTERNS.items():
            description = get_pattern_description(pattern_name)
            self._pattern_combo.addItem(description, pattern_name)
        self._pattern_combo.setMinimumWidth(180)
        self._pattern_combo.currentIndexChanged.connect(self._on_pattern_changed)
        pattern_row.addWidget(self._pattern_combo, 1)
        search_inner.addLayout(pattern_row)

        # Drugi wiersz: tekst + checkbox + przycisk
        input_row = QHBoxLayout()
        input_label = QLabel("Szukaj:")
        input_label.setStyleSheet("color: #8892a0;")
        input_label.setFixedWidth(60)
        input_row.addWidget(input_label)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Wpisz tekst lub regex...")
        self._search_input.setStyleSheet(self._input_style())
        self._search_input.returnPressed.connect(self._on_search)
        input_row.addWidget(self._search_input, 1)

        self._regex_checkbox = QCheckBox("Regex")
        self._regex_checkbox.setStyleSheet(self._checkbox_style())
        input_row.addWidget(self._regex_checkbox)

        self._search_btn = StyledButton("Szukaj", "primary")
        self._search_btn.clicked.connect(self._on_search)
        input_row.addWidget(self._search_btn)
        search_inner.addLayout(input_row)

        content_layout.addWidget(search_group)

        # === Splitter (wyniki | podgląd) ===
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

        # Lista wyników
        results_widget = QWidget()
        results_widget.setMinimumWidth(200)
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(0, 0, 10, 0)

        results_label = QLabel("Wyniki wyszukiwania:")
        results_label.setStyleSheet("color: #8892a0; font-size: 14px;")
        results_layout.addWidget(results_label)

        self._results_list = QListWidget()
        self._results_list.setStyleSheet(self._list_style())
        self._results_list.currentRowChanged.connect(self._on_result_selected)
        results_layout.addWidget(self._results_list, 1)

        splitter.addWidget(results_widget)

        # Podgląd strony
        preview_widget = QWidget()
        preview_widget.setMinimumWidth(200)
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(10, 0, 0, 0)

        preview_label = QLabel("Podgląd strony:")
        preview_label.setStyleSheet("color: #8892a0; font-size: 14px;")
        preview_layout.addWidget(preview_label)

        self._preview_label = QLabel()
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setMinimumSize(200, 280)
        self._preview_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._preview_label.setStyleSheet("""
            QLabel {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 8px;
            }
        """)
        preview_layout.addWidget(self._preview_label, 1)

        splitter.addWidget(preview_widget)
        splitter.setSizes([350, 450])

        content_layout.addWidget(splitter, 1)

        # === Dolny pasek akcji ===
        actions_bar = QWidget()
        actions_layout = QHBoxLayout(actions_bar)
        actions_layout.setContentsMargins(0, 10, 0, 0)

        self._results_label = QLabel("Znaleziono: 0 wyników")
        self._results_label.setStyleSheet("color: #8892a0; font-size: 14px;")
        actions_layout.addWidget(self._results_label)

        actions_layout.addStretch()

        self._select_all_btn = StyledButton("Zaznacz wszystkie", "secondary")
        self._select_all_btn.clicked.connect(self._on_select_all)
        self._select_all_btn.setEnabled(False)
        actions_layout.addWidget(self._select_all_btn)

        self._redact_btn = StyledButton("Redaguj", "danger")
        self._redact_btn.clicked.connect(self._on_redact)
        self._redact_btn.setEnabled(False)
        actions_layout.addWidget(self._redact_btn)

        content_layout.addWidget(actions_bar)

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

    def _input_style(self) -> str:
        """Zwraca styl dla QLineEdit."""
        return """
            QLineEdit {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 6px;
                padding: 8px 12px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #e0a800;
            }
        """

    def _checkbox_style(self) -> str:
        """Zwraca styl dla QCheckBox."""
        return """
            QCheckBox {
                color: #8892a0;
                spacing: 6px;
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

    def _list_style(self) -> str:
        """Zwraca styl dla QListWidget."""
        return """
            QListWidget {
                background-color: #1f2940;
                border: 1px solid #2d3a50;
                border-radius: 8px;
                padding: 5px;
            }
            QListWidget::item {
                background-color: #0f1629;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 8px;
                margin: 2px;
                color: #ffffff;
            }
            QListWidget::item:hover {
                border-color: #3d4a60;
            }
            QListWidget::item:selected {
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

    # === Handlers ===

    def _on_pattern_changed(self, index: int) -> None:
        """Obsługa zmiany wzorca."""
        pattern_name = self._pattern_combo.currentData()
        if pattern_name and pattern_name in REDACTION_PATTERNS:
            self._search_input.setText(REDACTION_PATTERNS[pattern_name])
            self._regex_checkbox.setChecked(True)
        else:
            self._search_input.clear()
            self._regex_checkbox.setChecked(False)

    def _on_search(self) -> None:
        """Obsługa wyszukiwania."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(
                self,
                "Błąd",
                "Najpierw otwórz dokument PDF"
            )
            return

        query = self._search_input.text().strip()
        if not query:
            QMessageBox.warning(
                self,
                "Błąd",
                "Wpisz tekst do wyszukania"
            )
            return

        is_regex = self._regex_checkbox.isChecked()

        try:
            self._search_results = self._pdf_manager.search_text(query, regex=is_regex)
            self._update_results_list()
        except Exception as e:
            QMessageBox.warning(
                self,
                "Błąd wyszukiwania",
                f"Nieprawidłowe wyrażenie:\n{e}"
            )

    def _update_results_list(self) -> None:
        """Aktualizuje listę wyników."""
        self._results_list.clear()

        for i, result in enumerate(self._search_results):
            item = QListWidgetItem()
            item.setText(f"Strona {result.page_index + 1}: \"{result.text[:50]}...\"" if len(result.text) > 50 else f"Strona {result.page_index + 1}: \"{result.text}\"")
            item.setData(Qt.ItemDataRole.UserRole, i)
            item.setCheckState(Qt.CheckState.Unchecked)
            self._results_list.addItem(item)

        count = len(self._search_results)
        self._results_label.setText(f"Znaleziono: {count} wyników")
        self._select_all_btn.setEnabled(count > 0)
        self._redact_btn.setEnabled(False)

    def _on_result_selected(self, row: int) -> None:
        """Obsługa wyboru wyniku."""
        if row < 0 or row >= len(self._search_results):
            return

        result = self._search_results[row]

        # Pokaż podgląd strony
        try:
            png_data = self._pdf_manager.generate_preview(result.page_index, dpi=100)
            pixmap = QPixmap()
            pixmap.loadFromData(png_data)

            # Skaluj
            scaled = pixmap.scaled(
                self._preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self._preview_label.setPixmap(scaled)
        except Exception:
            pass

        # Sprawdź czy cokolwiek jest zaznaczone
        self._update_redact_button()

    def _on_select_all(self) -> None:
        """Zaznacza wszystkie wyniki."""
        for i in range(self._results_list.count()):
            item = self._results_list.item(i)
            item.setCheckState(Qt.CheckState.Checked)
        self._update_redact_button()

    def _update_redact_button(self) -> None:
        """Aktualizuje stan przycisku redakcji."""
        has_checked = False
        for i in range(self._results_list.count()):
            item = self._results_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                has_checked = True
                break
        self._redact_btn.setEnabled(has_checked)

    def _on_redact(self) -> None:
        """Obsługa redakcji."""
        # Pobierz zaznaczone wyniki
        selected_results = []
        for i in range(self._results_list.count()):
            item = self._results_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                idx = item.data(Qt.ItemDataRole.UserRole)
                selected_results.append(self._search_results[idx])

        if not selected_results:
            return

        # Potwierdzenie
        count = len(selected_results)
        reply = QMessageBox.warning(
            self,
            "Potwierdź redakcję",
            f"Czy na pewno chcesz zredagować {count} fragmentów?\n\n"
            "Ta operacja jest NIEODWRACALNA!\n"
            "Tekst zostanie trwale usunięty z dokumentu.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._pdf_manager.apply_redaction(selected_results)
                QMessageBox.information(
                    self,
                    "Sukces",
                    f"Zredagowano {count} fragmentów.\n"
                    "Pamiętaj o zapisaniu dokumentu."
                )
                # Wyczyść wyniki
                self._search_results = []
                self._results_list.clear()
                self._results_label.setText("Znaleziono: 0 wyników")
                self._select_all_btn.setEnabled(False)
                self._redact_btn.setEnabled(False)
                self._preview_label.clear()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Błąd",
                    f"Nie można wykonać redakcji:\n{e}"
                )

    # === Public API ===

    def on_document_loaded(self) -> None:
        """Wywoływane po załadowaniu dokumentu."""
        # Wyczyść poprzednie wyniki
        self._search_results = []
        self._results_list.clear()
        self._results_label.setText("Znaleziono: 0 wyników")
        self._select_all_btn.setEnabled(False)
        self._redact_btn.setEnabled(False)
        self._preview_label.clear()
