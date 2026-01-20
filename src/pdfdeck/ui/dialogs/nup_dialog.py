"""
NupDialog - Dialog do tworzenia N-up (wiele stron na arkuszu).

Funkcje:
- Wybór liczby stron na arkusz (2, 4, 6, 9)
- Orientacja (pozioma/pionowa)
- Rozmiar wyjściowy
"""

from typing import Optional
from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QRadioButton, QButtonGroup,
    QGroupBox, QComboBox
)
from PyQt6.QtCore import Qt

from pdfdeck.ui.widgets.styled_button import StyledButton


@dataclass
class NupConfig:
    """Konfiguracja N-up."""
    pages_per_sheet: int  # 2, 4, 6, 9
    landscape: bool
    output_size: str  # "A4", "Letter", "A3"


class NupDialog(QDialog):
    """
    Dialog do konfiguracji N-up.

    Pozwala użytkownikowi:
    - Wybrać liczbę stron na arkusz
    - Ustawić orientację
    - Wybrać rozmiar wyjściowy
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._config: Optional[NupConfig] = None

        self.setWindowTitle("N-up - Wiele stron na arkuszu")
        self.setMinimumWidth(400)
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

        # Opis
        desc = QLabel(
            "Umieść wiele stron dokumentu na jednym arkuszu.\n"
            "Idealne do przeglądania lub oszczędzania papieru."
        )
        desc.setStyleSheet("color: #8892a0; font-size: 13px;")
        layout.addWidget(desc)

        # === Liczba stron na arkusz ===
        pages_group = QGroupBox("Liczba stron na arkusz")
        pages_layout = QVBoxLayout(pages_group)

        self._pages_group = QButtonGroup(self)

        # Opcje
        options = [
            (2, "2 strony (1x2)"),
            (4, "4 strony (2x2)"),
            (6, "6 stron (2x3)"),
            (9, "9 stron (3x3)")
        ]

        for i, (value, text) in enumerate(options):
            radio = QRadioButton(text)
            if value == 4:
                radio.setChecked(True)
            self._pages_group.addButton(radio, value)
            pages_layout.addWidget(radio)

        layout.addWidget(pages_group)

        # === Orientacja ===
        orientation_group = QGroupBox("Orientacja wyjściowa")
        orientation_layout = QVBoxLayout(orientation_group)

        self._orientation_group = QButtonGroup(self)

        self._portrait_radio = QRadioButton("Pionowa (portrait)")
        self._orientation_group.addButton(self._portrait_radio, 0)
        orientation_layout.addWidget(self._portrait_radio)

        self._landscape_radio = QRadioButton("Pozioma (landscape)")
        self._landscape_radio.setChecked(True)
        self._orientation_group.addButton(self._landscape_radio, 1)
        orientation_layout.addWidget(self._landscape_radio)

        layout.addWidget(orientation_group)

        # === Rozmiar wyjściowy ===
        size_group = QGroupBox("Rozmiar arkusza wyjściowego")
        size_layout = QVBoxLayout(size_group)

        size_row = QHBoxLayout()
        size_label = QLabel("Rozmiar:")
        size_label.setStyleSheet("color: #8892a0;")
        size_row.addWidget(size_label)

        self._size_combo = QComboBox()
        self._size_combo.addItems(["A4", "A3", "Letter", "Legal"])
        self._size_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 8px;
                color: #ffffff;
                min-width: 150px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #8892a0;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                selection-background-color: #e0a800;
                selection-color: #1a1a2e;
            }
        """)
        size_row.addWidget(self._size_combo)
        size_row.addStretch()

        size_layout.addLayout(size_row)
        layout.addWidget(size_group)

        # === Podgląd układu ===
        preview_group = QGroupBox("Podgląd układu")
        preview_layout = QVBoxLayout(preview_group)

        self._preview_label = QLabel()
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setMinimumHeight(100)
        self._preview_label.setStyleSheet(
            "background-color: #0f1629; border-radius: 4px; padding: 10px;"
        )
        preview_layout.addWidget(self._preview_label)

        layout.addWidget(preview_group)

        # Aktualizuj podgląd
        self._pages_group.buttonClicked.connect(self._update_preview)
        self._orientation_group.buttonClicked.connect(self._update_preview)
        self._update_preview()

        # === Przyciski ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = StyledButton("Anuluj", "secondary")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        apply_btn = StyledButton("Generuj N-up", "primary")
        apply_btn.clicked.connect(self._on_apply)
        buttons_layout.addWidget(apply_btn)

        layout.addLayout(buttons_layout)

    def _update_preview(self) -> None:
        """Aktualizuje podgląd układu."""
        pages = self._pages_group.checkedId()
        landscape = self._orientation_group.checkedId() == 1

        # Określ układ
        layouts = {
            2: ("1 x 2", "▢ ▢"),
            4: ("2 x 2", "▢ ▢\n▢ ▢"),
            6: ("2 x 3", "▢ ▢\n▢ ▢\n▢ ▢"),
            9: ("3 x 3", "▢ ▢ ▢\n▢ ▢ ▢\n▢ ▢ ▢")
        }

        layout_name, layout_ascii = layouts.get(pages, ("?", "?"))
        orientation = "poziomo" if landscape else "pionowo"

        self._preview_label.setText(
            f"<div style='text-align: center;'>"
            f"<div style='font-size: 14px; color: #e0a800;'>{layout_name}</div>"
            f"<div style='font-family: monospace; font-size: 20px; "
            f"color: #ffffff; margin: 10px;'>"
            f"{layout_ascii.replace(chr(10), '<br>')}</div>"
            f"<div style='font-size: 12px; color: #8892a0;'>Orientacja: {orientation}</div>"
            f"</div>"
        )

    def _on_apply(self) -> None:
        """Zatwierdza konfigurację."""
        self._config = NupConfig(
            pages_per_sheet=self._pages_group.checkedId(),
            landscape=self._orientation_group.checkedId() == 1,
            output_size=self._size_combo.currentText()
        )
        self.accept()

    def get_config(self) -> Optional[NupConfig]:
        """Zwraca konfigurację N-up."""
        return self._config

    @staticmethod
    def get_nup_config(parent=None) -> Optional[NupConfig]:
        """
        Statyczna metoda do szybkiego uzyskania konfiguracji.

        Args:
            parent: Widget rodzic

        Returns:
            NupConfig lub None jeśli anulowano
        """
        dialog = NupDialog(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_config()
        return None
