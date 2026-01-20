"""
WhiteoutDialog - Dialog do zakrywania tekstu i wstawiania nowego.

Funkcje:
- Wybór obszaru do zakrycia
- Kolor zakrycia
- Opcjonalne wstawianie nowego tekstu
"""

from typing import Optional, Tuple

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QColorDialog, QSpinBox,
    QGroupBox, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from pdfdeck.core.models import WhiteoutConfig, Rect
from pdfdeck.ui.widgets.styled_button import StyledButton


class WhiteoutDialog(QDialog):
    """
    Dialog do konfiguracji whiteout (zakrycia tekstu).

    Pozwala użytkownikowi:
    - Wybrać kolor zakrycia
    - Opcjonalnie wstawić nowy tekst
    - Ustawić rozmiar i styl tekstu
    """

    def __init__(self, rect: Rect = None, parent=None):
        super().__init__(parent)

        self._rect = rect or Rect(0, 0, 100, 20)
        self._fill_color = "#ffffff"
        self._text_color = "#000000"
        self._config: Optional[WhiteoutConfig] = None

        self.setWindowTitle("Whiteout - Zakryj i wstaw tekst")
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
        """)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Tworzy interfejs użytkownika."""
        layout = QVBoxLayout(self)

        # === Obszar zakrycia ===
        area_group = QGroupBox("Obszar zakrycia")
        area_layout = QVBoxLayout(area_group)

        area_info = QLabel(
            f"Wybrany obszar: ({self._rect.x:.0f}, {self._rect.y:.0f}) - "
            f"({self._rect.x + self._rect.width:.0f}, {self._rect.y + self._rect.height:.0f})"
        )
        area_info.setStyleSheet("color: #8892a0; font-size: 12px;")
        area_layout.addWidget(area_info)

        # Kolor wypełnienia
        fill_row = QHBoxLayout()
        fill_label = QLabel("Kolor zakrycia:")
        fill_label.setStyleSheet("color: #8892a0;")
        fill_row.addWidget(fill_label)

        self._fill_preview = QLabel()
        self._fill_preview.setFixedSize(30, 30)
        self._fill_preview.setStyleSheet(
            f"background-color: {self._fill_color}; "
            "border: 1px solid #2d3a50; border-radius: 4px;"
        )
        fill_row.addWidget(self._fill_preview)

        self._fill_btn = QPushButton("Zmień")
        self._fill_btn.setStyleSheet("""
            QPushButton {
                background-color: #1f2940;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 5px 10px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #2d3a50;
            }
        """)
        self._fill_btn.clicked.connect(self._on_fill_color)
        fill_row.addWidget(self._fill_btn)
        fill_row.addStretch()

        area_layout.addLayout(fill_row)
        layout.addWidget(area_group)

        # === Opcjonalny tekst ===
        text_group = QGroupBox("Nowy tekst (opcjonalnie)")
        text_layout = QVBoxLayout(text_group)

        self._add_text_check = QCheckBox("Wstaw tekst po zakryciu")
        self._add_text_check.setStyleSheet("color: #ffffff;")
        self._add_text_check.toggled.connect(self._on_text_toggle)
        text_layout.addWidget(self._add_text_check)

        # Pole tekstowe
        self._text_input = QLineEdit()
        self._text_input.setPlaceholderText("Wpisz tekst do wstawienia...")
        self._text_input.setStyleSheet("""
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
            QLineEdit:disabled {
                background-color: #1a1a2e;
                color: #5a5a5a;
            }
        """)
        self._text_input.setEnabled(False)
        text_layout.addWidget(self._text_input)

        # Rozmiar czcionki
        font_row = QHBoxLayout()
        font_label = QLabel("Rozmiar czcionki:")
        font_label.setStyleSheet("color: #8892a0;")
        font_row.addWidget(font_label)

        self._font_size = QSpinBox()
        self._font_size.setMinimum(6)
        self._font_size.setMaximum(72)
        self._font_size.setValue(12)
        self._font_size.setEnabled(False)
        self._font_size.setStyleSheet("""
            QSpinBox {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
            QSpinBox:disabled {
                background-color: #1a1a2e;
                color: #5a5a5a;
            }
        """)
        font_row.addWidget(self._font_size)
        font_row.addStretch()

        text_layout.addLayout(font_row)

        # Kolor tekstu
        text_color_row = QHBoxLayout()
        text_color_label = QLabel("Kolor tekstu:")
        text_color_label.setStyleSheet("color: #8892a0;")
        text_color_row.addWidget(text_color_label)

        self._text_color_preview = QLabel()
        self._text_color_preview.setFixedSize(30, 30)
        self._text_color_preview.setStyleSheet(
            f"background-color: {self._text_color}; "
            "border: 1px solid #2d3a50; border-radius: 4px;"
        )
        text_color_row.addWidget(self._text_color_preview)

        self._text_color_btn = QPushButton("Zmień")
        self._text_color_btn.setStyleSheet("""
            QPushButton {
                background-color: #1f2940;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 5px 10px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #2d3a50;
            }
            QPushButton:disabled {
                background-color: #1a1a2e;
                color: #5a5a5a;
            }
        """)
        self._text_color_btn.setEnabled(False)
        self._text_color_btn.clicked.connect(self._on_text_color)
        text_color_row.addWidget(self._text_color_btn)
        text_color_row.addStretch()

        text_layout.addLayout(text_color_row)

        layout.addWidget(text_group)

        # === Przyciski ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = StyledButton("Anuluj", "secondary")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        apply_btn = StyledButton("Zastosuj", "primary")
        apply_btn.clicked.connect(self._on_apply)
        buttons_layout.addWidget(apply_btn)

        layout.addLayout(buttons_layout)

    def _on_fill_color(self) -> None:
        """Wybór koloru wypełnienia."""
        color = QColorDialog.getColor(
            QColor(self._fill_color),
            self,
            "Wybierz kolor zakrycia"
        )
        if color.isValid():
            self._fill_color = color.name()
            self._fill_preview.setStyleSheet(
                f"background-color: {self._fill_color}; "
                "border: 1px solid #2d3a50; border-radius: 4px;"
            )

    def _on_text_color(self) -> None:
        """Wybór koloru tekstu."""
        color = QColorDialog.getColor(
            QColor(self._text_color),
            self,
            "Wybierz kolor tekstu"
        )
        if color.isValid():
            self._text_color = color.name()
            self._text_color_preview.setStyleSheet(
                f"background-color: {self._text_color}; "
                "border: 1px solid #2d3a50; border-radius: 4px;"
            )

    def _on_text_toggle(self, checked: bool) -> None:
        """Włącza/wyłącza opcje tekstu."""
        self._text_input.setEnabled(checked)
        self._font_size.setEnabled(checked)
        self._text_color_btn.setEnabled(checked)

    def _on_apply(self) -> None:
        """Zatwierdza konfigurację."""
        # Konwertuj kolor hex na RGB tuple
        fill_rgb = self._hex_to_rgb(self._fill_color)
        text_rgb = self._hex_to_rgb(self._text_color)

        self._config = WhiteoutConfig(
            rect=self._rect,
            fill_color=fill_rgb,
            text=self._text_input.text() if self._add_text_check.isChecked() else None,
            text_color=text_rgb,
            font_size=self._font_size.value()
        )
        self.accept()

    def _hex_to_rgb(self, hex_color: str) -> Tuple[float, float, float]:
        """Konwertuje kolor hex na RGB (0-1)."""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16) / 255
        g = int(hex_color[2:4], 16) / 255
        b = int(hex_color[4:6], 16) / 255
        return (r, g, b)

    def get_config(self) -> Optional[WhiteoutConfig]:
        """Zwraca konfigurację whiteout."""
        return self._config

    @staticmethod
    def get_whiteout_config(rect: Rect, parent=None) -> Optional[WhiteoutConfig]:
        """
        Statyczna metoda do szybkiego uzyskania konfiguracji.

        Args:
            rect: Prostokąt do zakrycia
            parent: Widget rodzic

        Returns:
            WhiteoutConfig lub None jeśli anulowano
        """
        dialog = WhiteoutDialog(rect, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_config()
        return None
