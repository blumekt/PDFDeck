"""
SelectAreaLinkDialog - Dialog do zaznaczania obszaru i dodawania linków.

Pozwala użytkownikowi interaktywnie zaznaczyć obszar na stronie PDF
i dodać do niego link.
"""

from typing import Optional, List, TYPE_CHECKING

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QGroupBox, QRadioButton, QButtonGroup,
    QSpinBox, QFileDialog, QPushButton, QCheckBox,
    QScrollArea, QWidget
)
from PyQt6.QtCore import Qt

from pdfdeck.core.models import LinkConfig, Rect
from pdfdeck.ui.widgets.styled_button import StyledButton
from pdfdeck.ui.widgets.interactive_page_preview import InteractivePagePreview

if TYPE_CHECKING:
    from pdfdeck.core.pdf_manager import PDFManager


class SelectAreaLinkDialog(QDialog):
    """
    Dialog do interaktywnego zaznaczania obszaru i dodawania linków.

    Pozwala użytkownikowi:
    - Zaznaczyć prostokątny obszar na stronie
    - Opcjonalnie dopasować do granic tekstu
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
        self._selected_rect: Optional[Rect] = None
        self._selected_words: List[str] = []
        self._config: Optional[LinkConfig] = None

        self.setWindowTitle("Zaznacz obszar linku")
        self.setMinimumSize(700, 700)
        self._apply_styles()
        self._setup_ui()

        # Załaduj stronę
        self._preview.set_page(page_index)

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
        main_layout = QVBoxLayout(self)

        # === Scroll Area ===
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #16213e;
            }
            QScrollBar:vertical {
                background-color: #0f1629;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #2d3a50;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #3d4a60;
            }
        """)

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)

        # === Podgląd strony ===
        preview_group = QGroupBox(f"Strona {self._page_index + 1}")
        preview_layout = QVBoxLayout(preview_group)

        self._preview = InteractivePagePreview(self._pdf_manager)
        self._preview.setMinimumHeight(500)
        self._preview.selection_completed.connect(self._on_selection_completed)
        preview_layout.addWidget(self._preview)

        layout.addWidget(preview_group)

        # === Info o zaznaczeniu ===
        self._selection_info = QLabel("Zaznacz obszar na stronie powyżej")
        self._selection_info.setStyleSheet("color: #8892a0; font-style: italic;")
        self._selection_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._selection_info)

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

        # === Wybór oznaczenia linku ===
        marking_group = QGroupBox("Oznaczenie linku")
        marking_layout = QVBoxLayout(marking_group)

        self._marking_group = QButtonGroup(self)

        self._border_radio = QRadioButton("Ramka")
        self._border_radio.setChecked(True)
        self._marking_group.addButton(self._border_radio, 0)
        marking_layout.addWidget(self._border_radio)

        self._underline_radio = QRadioButton("Podkreślenie")
        self._marking_group.addButton(self._underline_radio, 1)
        marking_layout.addWidget(self._underline_radio)

        self._no_marking_radio = QRadioButton("Brak oznaczenia")
        self._marking_group.addButton(self._no_marking_radio, 2)
        marking_layout.addWidget(self._no_marking_radio)

        layout.addWidget(marking_group)

        # Ustaw scroll content
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, 1)

        # === Przyciski (poza scroll area) ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = StyledButton("Anuluj", "secondary")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        self._apply_btn = StyledButton("Dodaj link", "primary")
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._on_apply)
        buttons_layout.addWidget(self._apply_btn)

        main_layout.addLayout(buttons_layout)

    def _on_selection_completed(self, rect: Rect, words: List[str]) -> None:
        """Obsługuje zakończenie zaznaczania."""
        self._selected_rect = rect
        self._selected_words = words

        if words:
            words_text = " ".join(words)
            if len(words_text) > 50:
                words_text = words_text[:47] + "..."
            self._selection_info.setText(f'Zaznaczony tekst: "{words_text}"')
            self._selection_info.setStyleSheet("color: #e0a800;")
        else:
            self._selection_info.setText(
                f"Zaznaczony obszar: ({int(rect.x0)}, {int(rect.y0)}) - "
                f"({int(rect.x1)}, {int(rect.y1)})"
            )
            self._selection_info.setStyleSheet("color: #ffffff;")

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
        if not self._selected_rect:
            return

        link_type_id = self._link_type_group.checkedId()

        # Określ typ oznaczenia: 0=ramka, 1=podkreślenie, 2=brak
        marking_id = self._marking_group.checkedId()
        add_border = (marking_id == 0)
        add_underline = (marking_id == 1)

        if link_type_id == 0:  # URL
            uri = self._url_input.text().strip()
            if not uri:
                return
            if not uri.startswith(('http://', 'https://', 'mailto:')):
                uri = 'https://' + uri

            self._config = LinkConfig(
                rect=self._selected_rect,
                link_type="url",
                uri=uri,
                add_underline=add_underline,
                add_border=add_border
            )

        elif link_type_id == 1:  # Strona
            self._config = LinkConfig(
                rect=self._selected_rect,
                link_type="page",
                target_page=self._page_spin.value() - 1,  # 0-indexed
                add_underline=add_underline,
                add_border=add_border
            )

        elif link_type_id == 2:  # Plik
            if not self._selected_file:
                return
            self._config = LinkConfig(
                rect=self._selected_rect,
                link_type="file",
                uri=self._selected_file,
                add_underline=add_underline,
                add_border=add_border
            )

        self.accept()

    def get_config(self) -> Optional[LinkConfig]:
        """Zwraca konfigurację linku."""
        return self._config

    @staticmethod
    def get_link_from_area(
        pdf_manager: "PDFManager",
        page_index: int,
        max_pages: int,
        parent=None
    ) -> Optional[LinkConfig]:
        """
        Statyczna metoda do uzyskania konfiguracji linku z zaznaczenia.

        Args:
            pdf_manager: Manager PDF
            page_index: Indeks strony
            max_pages: Maksymalna liczba stron
            parent: Widget rodzic

        Returns:
            LinkConfig lub None jeśli anulowano
        """
        dialog = SelectAreaLinkDialog(
            pdf_manager=pdf_manager,
            page_index=page_index,
            max_pages=max_pages,
            parent=parent
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_config()
        return None
