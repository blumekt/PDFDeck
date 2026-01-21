"""
WatermarkPage - Strona znaków wodnych i pieczątek.

Funkcje:
- Dodawanie tekstu jako znaku wodnego
- Konfiguracja przezroczystości, rotacji, pozycji
- Biblioteka pieczątek (ZAPŁACONO, PILNE, itp.)
"""

from typing import TYPE_CHECKING, Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QSpinBox, QDoubleSpinBox, QSlider,
    QGroupBox, QMessageBox, QColorDialog, QFrame,
    QTabWidget, QScrollArea, QSplitter, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap

from pdfdeck.ui.pages.base_page import BasePage
from pdfdeck.ui.widgets.styled_button import StyledButton
from pdfdeck.ui.widgets.styled_combo import StyledComboBox
from pdfdeck.ui.widgets.stamp_picker import StampPicker
from pdfdeck.core.models import WatermarkConfig

if TYPE_CHECKING:
    from pdfdeck.core.pdf_manager import PDFManager


class ColorButton(StyledButton):
    """Przycisk wyboru koloru."""

    def __init__(self, initial_color: QColor = QColor(128, 128, 128), parent=None):
        super().__init__("", "secondary", parent)
        self._color = initial_color
        self.setFixedSize(40, 40)
        self._update_style()
        self.clicked.connect(self._on_click)

    def _update_style(self) -> None:
        """Aktualizuje styl przycisku."""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color.name()};
                border: 2px solid #2d3a50;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                border-color: #e0a800;
            }}
        """)

    def _on_click(self) -> None:
        """Obsługa kliknięcia - wybór koloru."""
        color = QColorDialog.getColor(self._color, self, "Wybierz kolor")
        if color.isValid():
            self._color = color
            self._update_style()

    @property
    def color(self) -> QColor:
        return self._color

    @color.setter
    def color(self, value: QColor) -> None:
        self._color = value
        self._update_style()


class WatermarkPage(BasePage):
    """
    Strona znaków wodnych i pieczątek.

    Układ:
    +------------------------------------------+
    |  Tytuł: Znaki wodne                      |
    +------------------------------------------+
    |  +----------------+  +------------------+ |
    |  | Znak wodny     |  | Podgląd         | |
    |  | [Tekst...]     |  |                 | |
    |  | Rozmiar: [__]  |  |   PRZYKŁAD      | |
    |  | Rotacja: [__]  |  |                 | |
    |  | Kolor: [_]     |  |                 | |
    |  | [Dodaj]        |  |                 | |
    |  +----------------+  +------------------+ |
    +------------------------------------------+
    """

    def __init__(self, pdf_manager: "PDFManager", parent=None):
        super().__init__("Znaki wodne i pieczątki", parent)

        self._pdf_manager = pdf_manager
        self._setup_tabs_ui()

    def _setup_tabs_ui(self) -> None:
        """Tworzy interfejs z zakładkami."""
        # Tab widget
        self._tab_widget = QTabWidget()
        self._tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #2d3a50;
                border-radius: 8px;
                background-color: #16213e;
            }
            QTabBar::tab {
                background-color: #0f1629;
                color: #8892a0;
                border: 1px solid #2d3a50;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 10px 20px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #16213e;
                color: #ffffff;
                border-bottom: 2px solid #e0a800;
            }
            QTabBar::tab:hover:!selected {
                background-color: #1a2744;
            }
        """)

        # Zakładka 1: Znaki wodne
        watermark_tab = QWidget()
        self._setup_watermark_tab(watermark_tab)
        self._tab_widget.addTab(watermark_tab, "Znaki wodne")

        # Zakładka 2: Pieczątki
        stamp_tab = QWidget()
        self._setup_stamp_tab(stamp_tab)
        self._tab_widget.addTab(stamp_tab, "Pieczątki")

        self.add_widget(self._tab_widget)

    def _setup_stamp_tab(self, tab: QWidget) -> None:
        """Tworzy interfejs zakładki pieczątek."""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # StampPicker widget
        self._stamp_picker = StampPicker()
        self._stamp_picker.stamp_selected.connect(self._on_stamp_selected)

        # Scroll area dla stamp picker
        scroll = QScrollArea()
        scroll.setWidget(self._stamp_picker)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
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
        """)

        layout.addWidget(scroll, 1)

        # Przycisk dodania pieczątki
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._add_stamp_btn = StyledButton("Dodaj pieczątkę do strony", "primary")
        self._add_stamp_btn.clicked.connect(self._on_add_stamp)
        btn_row.addWidget(self._add_stamp_btn)

        layout.addLayout(btn_row)

    def _on_stamp_selected(self, config) -> None:
        """Obsługa wyboru pieczątki."""
        self._selected_stamp_config = config

    def _on_add_stamp(self) -> None:
        """Obsługa dodawania pieczątki do PDF."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(
                self,
                "Błąd",
                "Najpierw otwórz dokument PDF"
            )
            return

        config = self._stamp_picker.get_stamp_config()
        if not config:
            QMessageBox.warning(
                self,
                "Błąd",
                "Wybierz pieczątkę z listy lub stwórz własną"
            )
            return

        try:
            # Dodaj do aktualnej strony (index 0)
            # TODO: pozwól użytkownikowi wybrać stronę i pozycję
            self._pdf_manager.add_stamp(0, config)

            QMessageBox.information(
                self,
                "Sukces",
                "Pieczątka została dodana do strony.\n"
                "Pamiętaj o zapisaniu dokumentu."
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie można dodać pieczątki:\n{e}"
            )

    def _setup_watermark_tab(self, tab: QWidget) -> None:
        """Tworzy interfejs zakładki znaków wodnych."""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area dla całej zawartości
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(self._scroll_style())

        # Kontener wewnętrzny
        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(15)

        # Splitter - pozwala użytkownikowi zmieniać proporcje
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

        # === Lewa strona: Konfiguracja ===
        config_widget = QWidget()
        config_widget.setMinimumWidth(280)
        config_layout = QVBoxLayout(config_widget)
        config_layout.setContentsMargins(0, 0, 10, 0)
        config_layout.setSpacing(10)

        # --- Grupa: Znak wodny tekstowy ---
        watermark_group = QGroupBox("Znak wodny tekstowy")
        watermark_group.setStyleSheet(self._group_style())
        watermark_layout = QVBoxLayout(watermark_group)
        watermark_layout.setSpacing(8)

        # Tekst
        text_row = QHBoxLayout()
        text_label = QLabel("Tekst:")
        text_label.setStyleSheet("color: #8892a0;")
        text_label.setFixedWidth(70)
        text_row.addWidget(text_label)

        self._watermark_text = QLineEdit()
        self._watermark_text.setPlaceholderText("np. POUFNE, KOPIA...")
        self._watermark_text.setStyleSheet(self._input_style())
        self._watermark_text.textChanged.connect(self._update_preview)
        text_row.addWidget(self._watermark_text)
        watermark_layout.addLayout(text_row)

        # Rozmiar czcionki
        size_row = QHBoxLayout()
        size_label = QLabel("Rozmiar:")
        size_label.setStyleSheet("color: #8892a0;")
        size_label.setFixedWidth(70)
        size_row.addWidget(size_label)

        self._font_size = QSpinBox()
        self._font_size.setRange(12, 200)
        self._font_size.setValue(72)
        self._font_size.setStyleSheet(self._input_style())
        self._font_size.valueChanged.connect(self._update_preview)
        size_row.addWidget(self._font_size)
        size_row.addStretch()
        watermark_layout.addLayout(size_row)

        # Rotacja
        rotation_row = QHBoxLayout()
        rotation_label = QLabel("Rotacja:")
        rotation_label.setStyleSheet("color: #8892a0;")
        rotation_label.setFixedWidth(70)
        rotation_row.addWidget(rotation_label)

        self._rotation = QSpinBox()
        self._rotation.setRange(-180, 180)
        self._rotation.setValue(-45)
        self._rotation.setSuffix("°")
        self._rotation.setStyleSheet(self._input_style())
        self._rotation.valueChanged.connect(self._update_preview)
        rotation_row.addWidget(self._rotation)
        rotation_row.addStretch()
        watermark_layout.addLayout(rotation_row)

        # Kolor
        color_row = QHBoxLayout()
        color_label = QLabel("Kolor:")
        color_label.setStyleSheet("color: #8892a0;")
        color_label.setFixedWidth(70)
        color_row.addWidget(color_label)

        self._color_btn = ColorButton(QColor(128, 128, 128))
        color_row.addWidget(self._color_btn)
        color_row.addStretch()
        watermark_layout.addLayout(color_row)

        # Przezroczystość
        opacity_row = QHBoxLayout()
        opacity_label = QLabel("Przezr.:")
        opacity_label.setStyleSheet("color: #8892a0;")
        opacity_label.setFixedWidth(70)
        opacity_row.addWidget(opacity_label)

        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(10, 100)
        self._opacity_slider.setValue(30)
        self._opacity_slider.setStyleSheet(self._slider_style())
        self._opacity_slider.valueChanged.connect(self._update_preview)
        opacity_row.addWidget(self._opacity_slider)

        self._opacity_value = QLabel("30%")
        self._opacity_value.setStyleSheet("color: #8892a0; min-width: 35px;")
        self._opacity_slider.valueChanged.connect(
            lambda v: self._opacity_value.setText(f"{v}%")
        )
        opacity_row.addWidget(self._opacity_value)
        watermark_layout.addLayout(opacity_row)

        # Pozycja
        overlay_row = QHBoxLayout()
        overlay_label = QLabel("Pozycja:")
        overlay_label.setStyleSheet("color: #8892a0;")
        overlay_label.setFixedWidth(70)
        overlay_row.addWidget(overlay_label)

        self._overlay_combo = StyledComboBox()
        self._overlay_combo.addItem("Pod tekstem", False)
        self._overlay_combo.addItem("Nad tekstem", True)
        self._overlay_combo.setCurrentIndex(1)  # Domyślnie "Nad tekstem"
        overlay_row.addWidget(self._overlay_combo)
        overlay_row.addStretch()
        watermark_layout.addLayout(overlay_row)

        # Przycisk dodaj
        self._add_watermark_btn = StyledButton("Dodaj znak wodny", "primary")
        self._add_watermark_btn.clicked.connect(self._on_add_watermark)
        watermark_layout.addWidget(self._add_watermark_btn)

        config_layout.addWidget(watermark_group)

        # --- Grupa: Szybkie predefiniowane ---
        presets_group = QGroupBox("Szybkie znaki wodne")
        presets_group.setStyleSheet(self._group_style())
        presets_layout = QVBoxLayout(presets_group)
        presets_layout.setSpacing(6)

        presets = [
            ("POUFNE", (255, 0, 0)),
            ("KOPIA", (128, 128, 128)),
            ("PROJEKT", (0, 128, 255)),
            ("WERSJA ROBOCZA", (255, 165, 0)),
        ]

        for text, color in presets:
            btn = StyledButton(text, "secondary")
            btn.clicked.connect(lambda checked, t=text, c=color: self._apply_preset(t, c))
            presets_layout.addWidget(btn)

        config_layout.addWidget(presets_group)
        config_layout.addStretch()

        splitter.addWidget(config_widget)

        # === Prawa strona: Podgląd ===
        preview_widget = QWidget()
        preview_widget.setMinimumWidth(200)
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(10, 0, 0, 0)

        preview_label = QLabel("Podgląd:")
        preview_label.setStyleSheet("color: #8892a0; font-size: 14px;")
        preview_layout.addWidget(preview_label)

        self._preview_frame = QFrame()
        self._preview_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #2d3a50;
                border-radius: 8px;
            }
        """)
        self._preview_frame.setMinimumSize(200, 280)
        self._preview_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        preview_inner_layout = QVBoxLayout(self._preview_frame)
        preview_inner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._preview_text = QLabel("PRZYKŁAD")
        self._preview_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_text.setWordWrap(True)
        self._preview_text.setStyleSheet("""
            color: rgba(128, 128, 128, 0.3);
            font-size: 48px;
            font-weight: bold;
        """)
        preview_inner_layout.addWidget(self._preview_text)

        preview_layout.addWidget(self._preview_frame, 1)

        splitter.addWidget(preview_widget)
        splitter.setSizes([350, 450])

        content_layout.addWidget(splitter, 1)

        scroll.setWidget(content)
        layout.addWidget(scroll)

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
        """Zwraca styl dla pól input."""
        return """
            QLineEdit, QSpinBox {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 6px;
                padding: 6px 10px;
                color: #ffffff;
            }
            QLineEdit:focus, QSpinBox:focus {
                border-color: #e0a800;
            }
        """

    def _slider_style(self) -> str:
        """Zwraca styl dla sliderów."""
        return """
            QSlider::groove:horizontal {
                background: #0f1629;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #e0a800;
                width: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #e0a800;
                border-radius: 4px;
            }
        """

    def _scroll_style(self) -> str:
        """Zwraca styl dla scroll area."""
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

    def _update_preview(self) -> None:
        """Aktualizuje podgląd znaku wodnego."""
        text = self._watermark_text.text() or "PRZYKŁAD"
        size = self._font_size.value()
        opacity = self._opacity_slider.value() / 100.0
        color = self._color_btn.color

        # Skaluj rozmiar do podglądu (max 60px)
        preview_size = min(size, 60)

        # Aktualizuj podgląd
        self._preview_text.setText(text)
        self._preview_text.setStyleSheet(f"""
            color: rgba({color.red()}, {color.green()}, {color.blue()}, {opacity});
            font-size: {preview_size}px;
            font-weight: bold;
        """)

    def _apply_preset(self, text: str, color: tuple) -> None:
        """Stosuje preset znaku wodnego."""
        self._watermark_text.setText(text)
        self._color_btn.color = QColor(*color)
        self._update_preview()

    def _on_add_watermark(self) -> None:
        """Obsługa dodawania znaku wodnego."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(
                self,
                "Błąd",
                "Najpierw otwórz dokument PDF"
            )
            return

        text = self._watermark_text.text().strip()
        if not text:
            QMessageBox.warning(
                self,
                "Błąd",
                "Wpisz tekst znaku wodnego"
            )
            return

        try:
            color = self._color_btn.color
            config = WatermarkConfig(
                text=text,
                font_size=self._font_size.value(),
                rotation=self._rotation.value(),
                color=(color.redF(), color.greenF(), color.blueF()),
                opacity=self._opacity_slider.value() / 100.0,
                overlay=self._overlay_combo.currentData(),
            )

            self._pdf_manager.add_watermark(config)

            QMessageBox.information(
                self,
                "Sukces",
                "Znak wodny został dodany do wszystkich stron.\n"
                "Pamiętaj o zapisaniu dokumentu."
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie można dodać znaku wodnego:\n{e}"
            )

    # === Public API ===

    def on_document_loaded(self) -> None:
        """Wywoływane po załadowaniu dokumentu."""
        pass
