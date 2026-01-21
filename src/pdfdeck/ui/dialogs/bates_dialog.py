"""
BatesDialog - Dialog konfiguracji numeracji Bates.

Funkcje:
- Konfiguracja prefix/suffix
- Wybór pozycji
- Ustawienia czcionki
- Podgląd
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QGroupBox, QSpinBox,
    QComboBox, QColorDialog, QFormLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from pdfdeck.ui.widgets.styled_button import StyledButton
from pdfdeck.core.bates_numberer import BatesNumberer, BatesConfig, BatesPosition


class BatesDialog(QDialog):
    """
    Dialog do konfiguracji numeracji Bates.

    Pozwala użytkownikowi:
    - Ustawić prefix i suffix
    - Wybrać numer początkowy
    - Wybrać pozycję na stronie
    - Ustawić parametry czcionki
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._config: Optional[BatesConfig] = None
        self._color = (0, 0, 0)  # Domyślnie czarny

        self.setWindowTitle("Numeracja Bates")
        self.setMinimumWidth(400)
        self.setStyleSheet(self._dialog_style())

        self._setup_ui()

    def _dialog_style(self) -> str:
        """Zwraca styl dialogu."""
        return """
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
            QLineEdit, QSpinBox {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 8px;
                color: #ffffff;
            }
            QLineEdit:focus, QSpinBox:focus {
                border-color: #e0a800;
            }
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
            QComboBox QAbstractItemView {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                selection-background-color: #e0a800;
                selection-color: #1a1a2e;
            }
        """

    def _setup_ui(self) -> None:
        """Tworzy interfejs użytkownika."""
        layout = QVBoxLayout(self)

        # Opis
        desc = QLabel(
            "Numeracja Bates to standard w dokumentach prawniczych.\n"
            "Każda strona otrzymuje unikalny numer identyfikacyjny."
        )
        desc.setStyleSheet("color: #8892a0; font-size: 13px;")
        layout.addWidget(desc)

        # === Format numeracji ===
        format_group = QGroupBox("Format numeracji")
        format_layout = QFormLayout(format_group)

        # Prefix
        self._prefix_input = QLineEdit()
        self._prefix_input.setText("DOC-")
        self._prefix_input.setPlaceholderText("np. DOC-, CASE-")
        format_layout.addRow("Prefix:", self._prefix_input)

        # Suffix
        self._suffix_input = QLineEdit()
        self._suffix_input.setPlaceholderText("np. -2024")
        format_layout.addRow("Suffix:", self._suffix_input)

        # Numer początkowy
        self._start_spin = QSpinBox()
        self._start_spin.setMinimum(1)
        self._start_spin.setMaximum(999999999)
        self._start_spin.setValue(1)
        format_layout.addRow("Numer początkowy:", self._start_spin)

        # Liczba cyfr
        self._digits_spin = QSpinBox()
        self._digits_spin.setMinimum(1)
        self._digits_spin.setMaximum(10)
        self._digits_spin.setValue(6)
        format_layout.addRow("Liczba cyfr:", self._digits_spin)

        # Podgląd
        self._preview_label = QLabel()
        self._preview_label.setStyleSheet(
            "color: #e0a800; font-size: 14px; font-weight: bold;"
        )
        self._update_preview()
        format_layout.addRow("Podgląd:", self._preview_label)

        # Połącz sygnały do aktualizacji podglądu
        self._prefix_input.textChanged.connect(self._update_preview)
        self._suffix_input.textChanged.connect(self._update_preview)
        self._start_spin.valueChanged.connect(self._update_preview)
        self._digits_spin.valueChanged.connect(self._update_preview)

        layout.addWidget(format_group)

        # === Pozycja ===
        position_group = QGroupBox("Pozycja na stronie")
        position_layout = QFormLayout(position_group)

        self._position_combo = QComboBox()
        for label, pos in BatesNumberer.get_position_options():
            self._position_combo.addItem(label, pos)
        # Domyślnie dół-prawo
        self._position_combo.setCurrentIndex(5)
        position_layout.addRow("Pozycja:", self._position_combo)

        # Margines
        self._margin_spin = QSpinBox()
        self._margin_spin.setMinimum(10)
        self._margin_spin.setMaximum(200)
        self._margin_spin.setValue(36)
        self._margin_spin.setSuffix(" pt")
        position_layout.addRow("Margines:", self._margin_spin)

        layout.addWidget(position_group)

        # === Czcionka ===
        font_group = QGroupBox("Czcionka")
        font_layout = QHBoxLayout(font_group)

        font_layout.addWidget(QLabel("Rozmiar:"))
        self._font_size_spin = QSpinBox()
        self._font_size_spin.setMinimum(6)
        self._font_size_spin.setMaximum(72)
        self._font_size_spin.setValue(10)
        font_layout.addWidget(self._font_size_spin)

        font_layout.addWidget(QLabel("Kolor:"))
        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(30, 30)
        self._color_btn.setStyleSheet("background-color: #000000; border-radius: 4px;")
        self._color_btn.clicked.connect(self._choose_color)
        font_layout.addWidget(self._color_btn)

        font_layout.addStretch()

        layout.addWidget(font_group)

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

    def _update_preview(self) -> None:
        """Aktualizuje podgląd numeracji."""
        prefix = self._prefix_input.text()
        suffix = self._suffix_input.text()
        start = self._start_spin.value()
        digits = self._digits_spin.value()

        formatted = f"{prefix}{str(start).zfill(digits)}{suffix}"
        self._preview_label.setText(formatted)

    def _choose_color(self) -> None:
        """Otwiera dialog wyboru koloru."""
        current_color = QColor(
            int(self._color[0] * 255),
            int(self._color[1] * 255),
            int(self._color[2] * 255),
        )

        color = QColorDialog.getColor(current_color, self, "Wybierz kolor")

        if color.isValid():
            self._color = (
                color.redF(),
                color.greenF(),
                color.blueF(),
            )
            self._color_btn.setStyleSheet(
                f"background-color: {color.name()}; border-radius: 4px;"
            )

    def _on_apply(self) -> None:
        """Zatwierdza konfigurację."""
        self._config = BatesConfig(
            prefix=self._prefix_input.text(),
            suffix=self._suffix_input.text(),
            start_number=self._start_spin.value(),
            digits=self._digits_spin.value(),
            position=self._position_combo.currentData(),
            font_size=self._font_size_spin.value(),
            font_color=self._color,
            margin=self._margin_spin.value(),
        )
        self.accept()

    def get_config(self) -> Optional[BatesConfig]:
        """Zwraca konfigurację numeracji."""
        return self._config

    @staticmethod
    def get_bates_config(parent=None) -> Optional[BatesConfig]:
        """
        Statyczna metoda do szybkiego uzyskania konfiguracji.

        Args:
            parent: Widget rodzic

        Returns:
            BatesConfig lub None jeśli anulowano
        """
        dialog = BatesDialog(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_config()
        return None
