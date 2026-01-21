"""
LinkDialog - Dialog do dodawania i edycji hiperłączy.

Funkcje:
- Wstawianie linków URL
- Linki do stron dokumentu
- Linki do innych plików
- Edycja istniejących linków
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QRadioButton, QButtonGroup,
    QGroupBox, QSpinBox, QFileDialog
)
from PyQt6.QtCore import Qt

from pdfdeck.core.models import LinkConfig, LinkInfo, Rect
from pdfdeck.ui.widgets.styled_button import StyledButton


class LinkDialog(QDialog):
    """
    Dialog do konfiguracji linków w PDF.

    Pozwala użytkownikowi:
    - Dodać link do URL
    - Dodać link do strony dokumentu
    - Dodać link do zewnętrznego pliku
    - Edytować istniejący link
    """

    def __init__(
        self,
        rect: Rect = None,
        max_pages: int = 1,
        existing_link: LinkInfo = None,
        parent=None
    ):
        super().__init__(parent)

        self._rect = rect or Rect(0, 0, 100, 20)
        self._max_pages = max_pages
        self._existing_link = existing_link
        self._config: Optional[LinkConfig] = None
        self._edit_mode = existing_link is not None

        # Tytuł zależny od trybu
        if self._edit_mode:
            self.setWindowTitle("Edytuj link")
        else:
            self.setWindowTitle("Dodaj link")
        self.setMinimumWidth(450)
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
        """)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Tworzy interfejs użytkownika."""
        layout = QVBoxLayout(self)

        # === Typ linku ===
        type_group = QGroupBox("Typ linku")
        type_layout = QVBoxLayout(type_group)

        self._type_group = QButtonGroup(self)

        self._url_radio = QRadioButton("Link do strony WWW (URL)")
        self._url_radio.setChecked(True)
        self._type_group.addButton(self._url_radio, 0)
        type_layout.addWidget(self._url_radio)

        self._page_radio = QRadioButton("Link do strony dokumentu")
        self._type_group.addButton(self._page_radio, 1)
        type_layout.addWidget(self._page_radio)

        self._file_radio = QRadioButton("Link do pliku zewnętrznego")
        self._type_group.addButton(self._file_radio, 2)
        type_layout.addWidget(self._file_radio)

        self._type_group.buttonClicked.connect(self._on_type_changed)

        layout.addWidget(type_group)

        # === URL ===
        self._url_group = QGroupBox("Adres URL")
        url_layout = QVBoxLayout(self._url_group)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://example.com")
        self._url_input.setStyleSheet("""
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
        """)
        url_layout.addWidget(self._url_input)

        url_hint = QLabel("Wprowadź pełny adres URL wraz z protokołem (https://)")
        url_hint.setStyleSheet("color: #8892a0; font-size: 11px;")
        url_layout.addWidget(url_hint)

        layout.addWidget(self._url_group)

        # === Strona dokumentu ===
        self._page_group = QGroupBox("Strona docelowa")
        self._page_group.setVisible(False)
        page_layout = QVBoxLayout(self._page_group)

        page_row = QHBoxLayout()
        page_label = QLabel("Przejdź do strony:")
        page_label.setStyleSheet("color: #8892a0;")
        page_row.addWidget(page_label)

        self._page_spin = QSpinBox()
        self._page_spin.setMinimum(1)
        self._page_spin.setMaximum(self._max_pages)
        self._page_spin.setValue(1)
        self._page_spin.setStyleSheet("""
            QSpinBox {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
        """)
        page_row.addWidget(self._page_spin)

        page_info = QLabel(f"(1-{self._max_pages})")
        page_info.setStyleSheet("color: #8892a0;")
        page_row.addWidget(page_info)
        page_row.addStretch()

        page_layout.addLayout(page_row)
        layout.addWidget(self._page_group)

        # === Plik zewnętrzny ===
        self._file_group = QGroupBox("Plik docelowy")
        self._file_group.setVisible(False)
        file_layout = QVBoxLayout(self._file_group)

        file_row = QHBoxLayout()
        self._file_path_label = QLabel("Nie wybrano pliku")
        self._file_path_label.setStyleSheet(
            "color: #8892a0; background-color: #0f1629; "
            "padding: 8px; border-radius: 4px;"
        )
        file_row.addWidget(self._file_path_label, 1)

        self._file_browse_btn = QPushButton("Przeglądaj...")
        self._file_browse_btn.setStyleSheet("""
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
        self._file_browse_btn.clicked.connect(self._on_browse_file)
        file_row.addWidget(self._file_browse_btn)

        file_layout.addLayout(file_row)
        layout.addWidget(self._file_group)

        # === Tekst wyświetlany ===
        text_group = QGroupBox("Tekst linku (opcjonalnie)")
        text_layout = QVBoxLayout(text_group)

        self._display_text = QLineEdit()
        self._display_text.setPlaceholderText("Tekst wyświetlany jako link...")
        self._display_text.setStyleSheet("""
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
        """)
        text_layout.addWidget(self._display_text)

        text_hint = QLabel("Jeśli puste, użyty zostanie istniejący tekst w dokumencie")
        text_hint.setStyleSheet("color: #8892a0; font-size: 11px;")
        text_layout.addWidget(text_hint)

        layout.addWidget(text_group)

        # === Przyciski ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = StyledButton("Anuluj", "secondary")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        # Tekst przycisku zależny od trybu
        apply_text = "Zapisz" if self._edit_mode else "Dodaj link"
        self._apply_btn = StyledButton(apply_text, "primary")
        self._apply_btn.clicked.connect(self._on_apply)
        buttons_layout.addWidget(self._apply_btn)

        layout.addLayout(buttons_layout)

        # Zmienne stanu
        self._selected_file: Optional[str] = None

        # Wypełnij dane jeśli edytujemy istniejący link
        if self._edit_mode and self._existing_link:
            self._populate_from_existing()

    def _populate_from_existing(self) -> None:
        """Wypełnia pola danymi z istniejącego linku."""
        link = self._existing_link
        if not link:
            return

        # Ustaw typ linku
        if link.link_type == "url":
            self._url_radio.setChecked(True)
            self._url_group.setVisible(True)
            self._page_group.setVisible(False)
            self._file_group.setVisible(False)
            if link.uri:
                self._url_input.setText(link.uri)

        elif link.link_type == "page":
            self._page_radio.setChecked(True)
            self._url_group.setVisible(False)
            self._page_group.setVisible(True)
            self._file_group.setVisible(False)
            if link.target_page is not None:
                self._page_spin.setValue(link.target_page + 1)  # 1-indexed w UI

        elif link.link_type == "file":
            self._file_radio.setChecked(True)
            self._url_group.setVisible(False)
            self._page_group.setVisible(False)
            self._file_group.setVisible(True)
            if link.uri:
                self._selected_file = link.uri
                from pathlib import Path
                self._file_path_label.setText(Path(link.uri).name)
                self._file_path_label.setStyleSheet(
                    "color: #ffffff; background-color: #0f1629; "
                    "padding: 8px; border-radius: 4px;"
                )

    def _on_type_changed(self, button: QRadioButton) -> None:
        """Obsługa zmiany typu linku."""
        btn_id = self._type_group.id(button)

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
            # Pokaż tylko nazwę pliku
            from pathlib import Path
            self._file_path_label.setText(Path(filepath).name)
            self._file_path_label.setStyleSheet(
                "color: #ffffff; background-color: #0f1629; "
                "padding: 8px; border-radius: 4px;"
            )

    def _on_apply(self) -> None:
        """Zatwierdza konfigurację."""
        link_type = self._type_group.checkedId()

        if link_type == 0:  # URL
            uri = self._url_input.text().strip()
            if not uri:
                return
            # Dodaj protokół jeśli brak
            if not uri.startswith(('http://', 'https://', 'mailto:')):
                uri = 'https://' + uri

            self._config = LinkConfig(
                rect=self._rect,
                link_type="url",
                uri=uri,
                display_text=self._display_text.text() or None
            )

        elif link_type == 1:  # Strona
            self._config = LinkConfig(
                rect=self._rect,
                link_type="page",
                target_page=self._page_spin.value() - 1,  # 0-indexed
                display_text=self._display_text.text() or None
            )

        elif link_type == 2:  # Plik
            if not self._selected_file:
                return

            self._config = LinkConfig(
                rect=self._rect,
                link_type="file",
                uri=self._selected_file,
                display_text=self._display_text.text() or None
            )

        self.accept()

    def get_config(self) -> Optional[LinkConfig]:
        """Zwraca konfigurację linku."""
        return self._config

    @staticmethod
    def get_link_config(rect: Rect, max_pages: int = 1, parent=None) -> Optional[LinkConfig]:
        """
        Statyczna metoda do szybkiego uzyskania konfiguracji (dodawanie).

        Args:
            rect: Prostokąt linku
            max_pages: Maksymalna liczba stron (dla linków wewnętrznych)
            parent: Widget rodzic

        Returns:
            LinkConfig lub None jeśli anulowano
        """
        dialog = LinkDialog(rect, max_pages, parent=parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_config()
        return None

    @staticmethod
    def edit_link_config(
        existing_link: LinkInfo,
        max_pages: int = 1,
        parent=None
    ) -> Optional[LinkConfig]:
        """
        Statyczna metoda do edycji istniejącego linku.

        Args:
            existing_link: Istniejący link do edycji
            max_pages: Maksymalna liczba stron (dla linków wewnętrznych)
            parent: Widget rodzic

        Returns:
            LinkConfig z nowymi danymi lub None jeśli anulowano
        """
        dialog = LinkDialog(
            rect=existing_link.rect,
            max_pages=max_pages,
            existing_link=existing_link,
            parent=parent
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_config()
        return None
