"""
TextSearchLinkDialog - Dialog do wyszukiwania tekstu i dodawania linków.

Pozwala użytkownikowi wyszukać tekst na stronie i dodać do niego link.
"""

from typing import Optional, List, TYPE_CHECKING

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QGroupBox, QRadioButton, QButtonGroup,
    QSpinBox, QFileDialog, QPushButton, QScrollArea, QWidget, QCheckBox
)
from PyQt6.QtCore import Qt

from pdfdeck.core.models import LinkConfig, SearchResult, Rect
from pdfdeck.ui.widgets.styled_button import StyledButton

if TYPE_CHECKING:
    from pdfdeck.core.pdf_manager import PDFManager


class TextSearchLinkDialog(QDialog):
    """
    Dialog do wyszukiwania tekstu i dodawania linków.

    Pozwala użytkownikowi:
    - Wpisać tekst do wyszukania
    - Zobaczyć wszystkie wystąpienia na stronie
    - Wybrać konkretne wystąpienie
    - Skonfigurować link (URL/strona/plik)
    """

    def __init__(
        self,
        pdf_manager: "PDFManager",
        page_index: int,
        max_pages: int,
        parent=None
    ):
        super().__init__(parent)

        self._pdf_manager = pdf_manager
        self._page_index = page_index
        self._max_pages = max_pages
        self._search_results: List[SearchResult] = []
        self._selected_result: Optional[SearchResult] = None
        self._config: Optional[LinkConfig] = None

        self.setWindowTitle("Dodaj link do tekstu")
        self.setMinimumSize(500, 550)
        self._apply_styles()
        self._setup_ui()

    def _apply_styles(self) -> None:
        """Stosuje style do dialogu."""
        self.setStyleSheet("""
            QDialog {
                background-color: #16213e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
                color: #ffffff;
                border: 1px solid #2d3a50;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QRadioButton {
                color: #ffffff;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #2d3a50;
                border-radius: 8px;
                background-color: #0f1629;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #e0a800;
                border-radius: 8px;
                background-color: #e0a800;
            }
            QLineEdit {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 8px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #e0a800;
            }
            QSpinBox {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
        """)

    def _setup_ui(self) -> None:
        """Tworzy interfejs użytkownika."""
        layout = QVBoxLayout(self)

        # === Sekcja wyszukiwania ===
        search_group = QGroupBox("Wyszukaj tekst")
        search_layout = QVBoxLayout(search_group)

        search_row = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Wpisz tekst do wyszukania...")
        self._search_input.returnPressed.connect(self._on_search)
        search_row.addWidget(self._search_input, 1)

        search_btn = StyledButton("Szukaj", "primary")
        search_btn.clicked.connect(self._on_search)
        search_row.addWidget(search_btn)

        search_layout.addLayout(search_row)
        layout.addWidget(search_group)

        # === Sekcja wyników ===
        results_group = QGroupBox("Znalezione wystąpienia")
        results_layout = QVBoxLayout(results_group)

        # Scroll area dla wyników
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
            }
        """)
        scroll.setMinimumHeight(120)
        scroll.setMaximumHeight(150)

        self._results_container = QWidget()
        self._results_layout = QVBoxLayout(self._results_container)
        self._results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._results_group = QButtonGroup(self)
        self._results_group.buttonClicked.connect(self._on_result_selected)

        scroll.setWidget(self._results_container)
        results_layout.addWidget(scroll)

        self._no_results_label = QLabel("Wpisz tekst i kliknij 'Szukaj'")
        self._no_results_label.setStyleSheet("color: #8892a0; font-style: italic;")
        self._no_results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        results_layout.addWidget(self._no_results_label)

        layout.addWidget(results_group)

        # === Sekcja typu linku ===
        type_group = QGroupBox("Typ linku")
        type_layout = QVBoxLayout(type_group)

        self._link_type_group = QButtonGroup(self)

        self._url_radio = QRadioButton("Link do strony WWW (URL)")
        self._url_radio.setChecked(True)
        self._link_type_group.addButton(self._url_radio, 0)
        type_layout.addWidget(self._url_radio)

        self._page_radio = QRadioButton("Link do strony dokumentu")
        self._link_type_group.addButton(self._page_radio, 1)
        type_layout.addWidget(self._page_radio)

        self._file_radio = QRadioButton("Link do pliku zewnętrznego")
        self._link_type_group.addButton(self._file_radio, 2)
        type_layout.addWidget(self._file_radio)

        self._link_type_group.buttonClicked.connect(self._on_link_type_changed)

        layout.addWidget(type_group)

        # === Sekcja URL ===
        self._url_group = QGroupBox("Adres URL")
        url_layout = QVBoxLayout(self._url_group)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://example.com")
        url_layout.addWidget(self._url_input)

        url_hint = QLabel("Wprowadź pełny adres URL wraz z protokołem (https://)")
        url_hint.setStyleSheet("color: #8892a0; font-size: 11px;")
        url_layout.addWidget(url_hint)

        layout.addWidget(self._url_group)

        # === Sekcja strony docelowej ===
        self._page_group = QGroupBox("Strona docelowa")
        self._page_group.setVisible(False)
        page_layout = QHBoxLayout(self._page_group)

        page_label = QLabel("Przejdź do strony:")
        page_label.setStyleSheet("color: #8892a0;")
        page_layout.addWidget(page_label)

        self._page_spin = QSpinBox()
        self._page_spin.setMinimum(1)
        self._page_spin.setMaximum(self._max_pages)
        self._page_spin.setValue(1)
        page_layout.addWidget(self._page_spin)

        page_info = QLabel(f"(1-{self._max_pages})")
        page_info.setStyleSheet("color: #8892a0;")
        page_layout.addWidget(page_info)
        page_layout.addStretch()

        layout.addWidget(self._page_group)

        # === Sekcja pliku ===
        self._file_group = QGroupBox("Plik docelowy")
        self._file_group.setVisible(False)
        file_layout = QHBoxLayout(self._file_group)

        self._file_path_label = QLabel("Nie wybrano pliku")
        self._file_path_label.setStyleSheet(
            "color: #8892a0; background-color: #0f1629; "
            "padding: 8px; border-radius: 4px;"
        )
        file_layout.addWidget(self._file_path_label, 1)

        file_browse_btn = QPushButton("Przeglądaj...")
        file_browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #1f2940;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 8px 16px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #2d3a50;
            }
        """)
        file_browse_btn.clicked.connect(self._on_browse_file)
        file_layout.addWidget(file_browse_btn)

        layout.addWidget(self._file_group)

        self._selected_file: Optional[str] = None

        # === Checkbox podkreślenia ===
        self._underline_checkbox = QCheckBox("Dodaj podkreślenie")
        self._underline_checkbox.setChecked(True)
        self._underline_checkbox.setStyleSheet("color: #ffffff;")
        layout.addWidget(self._underline_checkbox)

        # === Przyciski ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = StyledButton("Anuluj", "secondary")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        self._apply_btn = StyledButton("Dodaj link", "primary")
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._on_apply)
        buttons_layout.addWidget(self._apply_btn)

        layout.addLayout(buttons_layout)

    def _on_search(self) -> None:
        """Wyszukuje tekst na stronie."""
        query = self._search_input.text().strip()
        if not query:
            return

        # Wyczyść poprzednie wyniki
        self._clear_results()

        # Wyszukaj tekst
        self._search_results = self._pdf_manager.search_text_on_page(
            self._page_index, query
        )

        if not self._search_results:
            self._no_results_label.setText("Nie znaleziono tekstu")
            self._no_results_label.setVisible(True)
            self._apply_btn.setEnabled(False)
            return

        self._no_results_label.setVisible(False)

        # Dodaj wyniki jako radio buttony
        for i, result in enumerate(self._search_results):
            pos_text = f'"{result.text}" - pozycja ({int(result.rect.x0)}, {int(result.rect.y0)})'
            radio = QRadioButton(pos_text)
            radio.setStyleSheet("color: #ffffff; padding: 4px;")
            self._results_group.addButton(radio, i)
            self._results_layout.addWidget(radio)

            # Zaznacz pierwszy wynik
            if i == 0:
                radio.setChecked(True)
                self._selected_result = result
                self._apply_btn.setEnabled(True)

    def _clear_results(self) -> None:
        """Czyści listę wyników."""
        # Usuń wszystkie radio buttony
        for button in self._results_group.buttons():
            self._results_group.removeButton(button)
            self._results_layout.removeWidget(button)
            button.deleteLater()

        self._search_results = []
        self._selected_result = None

    def _on_result_selected(self, button: QRadioButton) -> None:
        """Obsługuje wybór wyniku."""
        idx = self._results_group.id(button)
        if 0 <= idx < len(self._search_results):
            self._selected_result = self._search_results[idx]
            self._apply_btn.setEnabled(True)

    def _on_link_type_changed(self, button: QRadioButton) -> None:
        """Obsługuje zmianę typu linku."""
        btn_id = self._link_type_group.id(button)
        self._url_group.setVisible(btn_id == 0)
        self._page_group.setVisible(btn_id == 1)
        self._file_group.setVisible(btn_id == 2)

    def _on_browse_file(self) -> None:
        """Wybór pliku docelowego."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz plik",
            "",
            "Wszystkie pliki (*.*)"
        )
        if filepath:
            self._selected_file = filepath
            from pathlib import Path
            self._file_path_label.setText(Path(filepath).name)
            self._file_path_label.setStyleSheet(
                "color: #ffffff; background-color: #0f1629; "
                "padding: 8px; border-radius: 4px;"
            )

    def _on_apply(self) -> None:
        """Zatwierdza konfigurację."""
        if not self._selected_result:
            return

        link_type_id = self._link_type_group.checkedId()

        add_underline = self._underline_checkbox.isChecked()

        if link_type_id == 0:  # URL
            uri = self._url_input.text().strip()
            if not uri:
                return
            if not uri.startswith(('http://', 'https://', 'mailto:')):
                uri = 'https://' + uri

            self._config = LinkConfig(
                rect=self._selected_result.rect,
                link_type="url",
                uri=uri,
                add_underline=add_underline
            )

        elif link_type_id == 1:  # Strona
            self._config = LinkConfig(
                rect=self._selected_result.rect,
                link_type="page",
                target_page=self._page_spin.value() - 1,  # 0-indexed
                add_underline=add_underline
            )

        elif link_type_id == 2:  # Plik
            if not self._selected_file:
                return
            self._config = LinkConfig(
                rect=self._selected_result.rect,
                link_type="file",
                uri=self._selected_file,
                add_underline=add_underline
            )

        self.accept()

    def get_config(self) -> Optional[LinkConfig]:
        """Zwraca konfigurację linku."""
        return self._config

    @staticmethod
    def get_link_from_text(
        pdf_manager: "PDFManager",
        page_index: int,
        max_pages: int,
        parent=None
    ) -> Optional[LinkConfig]:
        """
        Statyczna metoda do uzyskania konfiguracji linku z wyszukiwania tekstu.

        Args:
            pdf_manager: Manager PDF
            page_index: Indeks strony
            max_pages: Maksymalna liczba stron
            parent: Widget rodzic

        Returns:
            LinkConfig lub None jeśli anulowano
        """
        dialog = TextSearchLinkDialog(
            pdf_manager=pdf_manager,
            page_index=page_index,
            max_pages=max_pages,
            parent=parent
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_config()
        return None
