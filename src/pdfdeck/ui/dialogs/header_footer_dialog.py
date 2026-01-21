"""
HeaderFooterDialog - Dialog konfiguracji nagłówków i stopek.

Funkcje:
- Konfiguracja nagłówka (lewo/środek/prawo)
- Konfiguracja stopki (lewo/środek/prawo)
- Szablony placeholderów
- Podgląd
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QGroupBox, QSpinBox,
    QComboBox, QColorDialog, QFormLayout, QCheckBox,
    QTabWidget, QWidget, QDoubleSpinBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from pdfdeck.ui.widgets.styled_button import StyledButton
from pdfdeck.core.header_footer import HeaderFooterConfig, HeaderFooterEngine


class HeaderFooterDialog(QDialog):
    """
    Dialog do konfiguracji nagłówków i stopek.

    Pozwala użytkownikowi:
    - Ustawić tekst nagłówka/stopki (lewo/środek/prawo)
    - Użyć szablonów placeholderów
    - Skonfigurować czcionkę i marginesy
    - Ustawić opcje dla parzystych/nieparzystych stron
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._config: Optional[HeaderFooterConfig] = None
        self._color = (0, 0, 0)

        self.setWindowTitle("Nagłówki i stopki")
        self.setMinimumWidth(500)
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
            QLineEdit, QSpinBox, QDoubleSpinBox {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 8px;
                color: #ffffff;
            }
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
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
            QCheckBox {
                color: #ffffff;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #2d3a50;
                background-color: #0f1629;
            }
            QCheckBox::indicator:checked {
                background-color: #e0a800;
                border-color: #e0a800;
            }
            QTabWidget::pane {
                border: 1px solid #2d3a50;
                border-radius: 6px;
                background-color: #16213e;
            }
            QTabBar::tab {
                background-color: #0f1629;
                color: #8892a0;
                padding: 8px 20px;
                border: 1px solid #2d3a50;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #16213e;
                color: #e0a800;
            }
        """

    def _setup_ui(self) -> None:
        """Tworzy interfejs użytkownika."""
        layout = QVBoxLayout(self)

        # Tabs
        tabs = QTabWidget()

        # Tab 1: Podstawowe
        basic_tab = self._create_basic_tab()
        tabs.addTab(basic_tab, "Podstawowe")

        # Tab 2: Strony parzyste/nieparzyste
        odd_even_tab = self._create_odd_even_tab()
        tabs.addTab(odd_even_tab, "Parzyste/Nieparzyste")

        # Tab 3: Czcionka i marginesy
        format_tab = self._create_format_tab()
        tabs.addTab(format_tab, "Formatowanie")

        layout.addWidget(tabs)

        # === Podgląd ===
        preview_group = QGroupBox("Podgląd")
        preview_layout = QVBoxLayout(preview_group)

        self._preview_label = QLabel()
        self._preview_label.setStyleSheet(
            "color: #e0a800; font-size: 12px; padding: 10px; "
            "background-color: #0f1629; border-radius: 4px;"
        )
        self._preview_label.setWordWrap(True)
        self._update_preview()
        preview_layout.addWidget(self._preview_label)

        layout.addWidget(preview_group)

        # === Przyciski ===
        buttons_layout = QHBoxLayout()

        # Presety
        preset_combo = QComboBox()
        preset_combo.addItem("Wybierz szablon...", None)
        for name, desc in self._get_preset_descriptions().items():
            preset_combo.addItem(desc, name)
        preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        buttons_layout.addWidget(preset_combo)

        buttons_layout.addStretch()

        cancel_btn = StyledButton("Anuluj", "secondary")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        apply_btn = StyledButton("Zastosuj", "primary")
        apply_btn.clicked.connect(self._on_apply)
        buttons_layout.addWidget(apply_btn)

        layout.addLayout(buttons_layout)

    def _create_basic_tab(self) -> QWidget:
        """Tworzy zakładkę podstawowych ustawień."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Nagłówek
        header_group = QGroupBox("Nagłówek")
        header_layout = QFormLayout(header_group)

        self._header_left = QLineEdit()
        self._header_left.setPlaceholderText("{filename}")
        self._header_left.textChanged.connect(self._update_preview)
        header_layout.addRow("Lewo:", self._header_left)

        self._header_center = QLineEdit()
        self._header_center.setPlaceholderText("{date}")
        self._header_center.textChanged.connect(self._update_preview)
        header_layout.addRow("Środek:", self._header_center)

        self._header_right = QLineEdit()
        self._header_right.setPlaceholderText("")
        self._header_right.textChanged.connect(self._update_preview)
        header_layout.addRow("Prawo:", self._header_right)

        layout.addWidget(header_group)

        # Stopka
        footer_group = QGroupBox("Stopka")
        footer_layout = QFormLayout(footer_group)

        self._footer_left = QLineEdit()
        self._footer_left.setPlaceholderText("")
        self._footer_left.textChanged.connect(self._update_preview)
        footer_layout.addRow("Lewo:", self._footer_left)

        self._footer_center = QLineEdit()
        self._footer_center.setText("{page} / {total}")
        self._footer_center.textChanged.connect(self._update_preview)
        footer_layout.addRow("Środek:", self._footer_center)

        self._footer_right = QLineEdit()
        self._footer_right.setPlaceholderText("")
        self._footer_right.textChanged.connect(self._update_preview)
        footer_layout.addRow("Prawo:", self._footer_right)

        layout.addWidget(footer_group)

        # Opcje
        options_layout = QHBoxLayout()

        self._skip_first_check = QCheckBox("Pomiń pierwszą stronę")
        options_layout.addWidget(self._skip_first_check)

        self._odd_even_check = QCheckBox("Różne dla parzystych/nieparzystych")
        self._odd_even_check.stateChanged.connect(self._on_odd_even_changed)
        options_layout.addWidget(self._odd_even_check)

        options_layout.addStretch()
        layout.addLayout(options_layout)

        # Dostępne placeholdery
        placeholders_label = QLabel(
            "Dostępne placeholdery: {page}, {total}, {date}, {time}, {datetime}, {filename}"
        )
        placeholders_label.setStyleSheet("color: #8892a0; font-size: 11px;")
        layout.addWidget(placeholders_label)

        layout.addStretch()
        return widget

    def _create_odd_even_tab(self) -> QWidget:
        """Tworzy zakładkę dla stron parzystych/nieparzystych."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info_label = QLabel(
            "Te ustawienia są używane tylko gdy włączona jest opcja\n"
            "'Różne dla parzystych/nieparzystych'."
        )
        info_label.setStyleSheet("color: #8892a0; font-size: 12px;")
        layout.addWidget(info_label)

        # Nagłówek dla stron parzystych
        even_header_group = QGroupBox("Nagłówek (strony parzyste)")
        even_header_layout = QFormLayout(even_header_group)

        self._even_header_left = QLineEdit()
        self._even_header_left.textChanged.connect(self._update_preview)
        even_header_layout.addRow("Lewo:", self._even_header_left)

        self._even_header_center = QLineEdit()
        self._even_header_center.textChanged.connect(self._update_preview)
        even_header_layout.addRow("Środek:", self._even_header_center)

        self._even_header_right = QLineEdit()
        self._even_header_right.textChanged.connect(self._update_preview)
        even_header_layout.addRow("Prawo:", self._even_header_right)

        layout.addWidget(even_header_group)

        # Stopka dla stron parzystych
        even_footer_group = QGroupBox("Stopka (strony parzyste)")
        even_footer_layout = QFormLayout(even_footer_group)

        self._even_footer_left = QLineEdit()
        self._even_footer_left.textChanged.connect(self._update_preview)
        even_footer_layout.addRow("Lewo:", self._even_footer_left)

        self._even_footer_center = QLineEdit()
        self._even_footer_center.setText("{page} / {total}")
        self._even_footer_center.textChanged.connect(self._update_preview)
        even_footer_layout.addRow("Środek:", self._even_footer_center)

        self._even_footer_right = QLineEdit()
        self._even_footer_right.textChanged.connect(self._update_preview)
        even_footer_layout.addRow("Prawo:", self._even_footer_right)

        layout.addWidget(even_footer_group)

        layout.addStretch()
        return widget

    def _create_format_tab(self) -> QWidget:
        """Tworzy zakładkę formatowania."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Czcionka
        font_group = QGroupBox("Czcionka")
        font_layout = QFormLayout(font_group)

        self._font_size_spin = QDoubleSpinBox()
        self._font_size_spin.setMinimum(6)
        self._font_size_spin.setMaximum(72)
        self._font_size_spin.setValue(10)
        self._font_size_spin.setSuffix(" pt")
        font_layout.addRow("Rozmiar:", self._font_size_spin)

        color_row = QHBoxLayout()
        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(30, 30)
        self._color_btn.setStyleSheet("background-color: #000000; border-radius: 4px;")
        self._color_btn.clicked.connect(self._choose_color)
        color_row.addWidget(self._color_btn)
        color_row.addStretch()

        color_widget = QWidget()
        color_widget.setLayout(color_row)
        font_layout.addRow("Kolor:", color_widget)

        layout.addWidget(font_group)

        # Marginesy
        margins_group = QGroupBox("Marginesy")
        margins_layout = QFormLayout(margins_group)

        self._margin_top_spin = QDoubleSpinBox()
        self._margin_top_spin.setMinimum(10)
        self._margin_top_spin.setMaximum(200)
        self._margin_top_spin.setValue(36)
        self._margin_top_spin.setSuffix(" pt")
        margins_layout.addRow("Górny:", self._margin_top_spin)

        self._margin_bottom_spin = QDoubleSpinBox()
        self._margin_bottom_spin.setMinimum(10)
        self._margin_bottom_spin.setMaximum(200)
        self._margin_bottom_spin.setValue(36)
        self._margin_bottom_spin.setSuffix(" pt")
        margins_layout.addRow("Dolny:", self._margin_bottom_spin)

        self._margin_left_spin = QDoubleSpinBox()
        self._margin_left_spin.setMinimum(10)
        self._margin_left_spin.setMaximum(200)
        self._margin_left_spin.setValue(36)
        self._margin_left_spin.setSuffix(" pt")
        margins_layout.addRow("Lewy:", self._margin_left_spin)

        self._margin_right_spin = QDoubleSpinBox()
        self._margin_right_spin.setMinimum(10)
        self._margin_right_spin.setMaximum(200)
        self._margin_right_spin.setValue(36)
        self._margin_right_spin.setSuffix(" pt")
        margins_layout.addRow("Prawy:", self._margin_right_spin)

        layout.addWidget(margins_group)

        layout.addStretch()
        return widget

    def _update_preview(self) -> None:
        """Aktualizuje podgląd."""
        parts = []

        header_left = self._header_left.text()
        header_center = self._header_center.text()
        header_right = self._header_right.text()

        if header_left or header_center or header_right:
            parts.append(f"Nagłówek: [{header_left or '-'}] [{header_center or '-'}] [{header_right or '-'}]")

        footer_left = self._footer_left.text()
        footer_center = self._footer_center.text()
        footer_right = self._footer_right.text()

        if footer_left or footer_center or footer_right:
            parts.append(f"Stopka: [{footer_left or '-'}] [{footer_center or '-'}] [{footer_right or '-'}]")

        if not parts:
            self._preview_label.setText("(Brak tekstu)")
        else:
            # Symuluj rozwinięcie szablonów
            preview = "\n".join(parts)
            preview = preview.replace("{page}", "1")
            preview = preview.replace("{total}", "10")
            preview = preview.replace("{date}", "2024-01-15")
            preview = preview.replace("{time}", "14:30")
            preview = preview.replace("{datetime}", "2024-01-15 14:30")
            preview = preview.replace("{filename}", "dokument.pdf")
            self._preview_label.setText(preview)

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

    def _on_odd_even_changed(self, state: int) -> None:
        """Obsługa zmiany checkbox parzystych/nieparzystych."""
        # Można tutaj włączyć/wyłączyć zakładkę
        pass

    def _on_preset_selected(self, index: int) -> None:
        """Obsługa wyboru predefiniowanej konfiguracji."""
        combo = self.sender()
        preset_name = combo.currentData()

        if not preset_name:
            return

        presets = HeaderFooterEngine.get_preset_configs()
        if preset_name in presets:
            config = presets[preset_name]
            self._load_config(config)

    def _load_config(self, config: HeaderFooterConfig) -> None:
        """Ładuje konfigurację do formularza."""
        self._header_left.setText(config.header_left)
        self._header_center.setText(config.header_center)
        self._header_right.setText(config.header_right)

        self._footer_left.setText(config.footer_left)
        self._footer_center.setText(config.footer_center)
        self._footer_right.setText(config.footer_right)

        self._skip_first_check.setChecked(config.skip_first)
        self._odd_even_check.setChecked(config.different_odd_even)

        self._even_header_left.setText(config.even_header_left)
        self._even_header_center.setText(config.even_header_center)
        self._even_header_right.setText(config.even_header_right)

        self._even_footer_left.setText(config.even_footer_left)
        self._even_footer_center.setText(config.even_footer_center)
        self._even_footer_right.setText(config.even_footer_right)

        self._font_size_spin.setValue(config.font_size)
        self._color = config.font_color

        color = QColor(
            int(self._color[0] * 255),
            int(self._color[1] * 255),
            int(self._color[2] * 255),
        )
        self._color_btn.setStyleSheet(
            f"background-color: {color.name()}; border-radius: 4px;"
        )

        self._margin_top_spin.setValue(config.margin_top)
        self._margin_bottom_spin.setValue(config.margin_bottom)
        self._margin_left_spin.setValue(config.margin_left)
        self._margin_right_spin.setValue(config.margin_right)

        self._update_preview()

    def _get_preset_descriptions(self) -> dict:
        """Zwraca opisy presetów."""
        return {
            "page_numbers_bottom": "Numeracja stron (dół, środek)",
            "page_numbers_top": "Numeracja stron (góra, środek)",
            "document_header": "Nazwa pliku + numeracja",
            "legal_footer": "Prawnicza stopka (data, strona, plik)",
            "book_style": "Styl książkowy (różne parzyste/nieparzyste)",
        }

    def _on_apply(self) -> None:
        """Zatwierdza konfigurację."""
        self._config = HeaderFooterConfig(
            header_left=self._header_left.text(),
            header_center=self._header_center.text(),
            header_right=self._header_right.text(),
            footer_left=self._footer_left.text(),
            footer_center=self._footer_center.text(),
            footer_right=self._footer_right.text(),
            font_size=self._font_size_spin.value(),
            font_color=self._color,
            margin_top=self._margin_top_spin.value(),
            margin_bottom=self._margin_bottom_spin.value(),
            margin_left=self._margin_left_spin.value(),
            margin_right=self._margin_right_spin.value(),
            skip_first=self._skip_first_check.isChecked(),
            different_odd_even=self._odd_even_check.isChecked(),
            even_header_left=self._even_header_left.text(),
            even_header_center=self._even_header_center.text(),
            even_header_right=self._even_header_right.text(),
            even_footer_left=self._even_footer_left.text(),
            even_footer_center=self._even_footer_center.text(),
            even_footer_right=self._even_footer_right.text(),
        )
        self.accept()

    def get_config(self) -> Optional[HeaderFooterConfig]:
        """Zwraca konfigurację."""
        return self._config

    @staticmethod
    def get_header_footer_config(parent=None) -> Optional[HeaderFooterConfig]:
        """
        Statyczna metoda do szybkiego uzyskania konfiguracji.

        Args:
            parent: Widget rodzic

        Returns:
            HeaderFooterConfig lub None jeśli anulowano
        """
        dialog = HeaderFooterDialog(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_config()
        return None
