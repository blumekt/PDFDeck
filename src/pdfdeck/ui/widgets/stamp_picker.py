"""
StampPicker - Widget do wyboru i zarządzania pieczątkami.

Funkcje:
- Wybór predefiniowanych pieczątek
- Podgląd pieczątki w czasie rzeczywistym
- Konfiguracja rozmiaru, rotacji, przezroczystości
- Różne kształty i style ramek
- Efekt zużycia (worn/aged)
- Okrągłe pieczątki z tekstem po obwodzie
"""

from typing import Optional, Dict
from io import BytesIO
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem,
    QSlider, QGroupBox, QComboBox, QCheckBox,
    QColorDialog, QLineEdit, QScrollArea, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor, QPainter, QFont, QPen, QTransform

from pdfdeck.core.models import (
    StampConfig, StampShape, BorderStyle, WearLevel, Point
)
from pdfdeck.core.stamp_renderer import StampRenderer


# Predefiniowane pieczątki (tekst + kolor + opcjonalne ustawienia)
PRESET_STAMPS = {
    # === Podstawowe ===
    "paid": {
        "text": "ZAPŁACONO",
        "color": "#27ae60",
        "icon": "✓",
        "shape": "rectangle",
        "border_style": "solid",
    },
    "confidential": {
        "text": "POUFNE",
        "color": "#e74c3c",
        "icon": "🔒",
        "shape": "rectangle",
        "border_style": "solid",
    },
    "copy": {
        "text": "KOPIA",
        "color": "#3498db",
        "icon": "📋",
        "shape": "rectangle",
        "border_style": "solid",
    },
    "draft": {
        "text": "PROJEKT",
        "color": "#f39c12",
        "icon": "📝",
        "shape": "rectangle",
        "border_style": "solid",
    },
    "urgent": {
        "text": "PILNE",
        "color": "#e74c3c",
        "icon": "⚠️",
        "shape": "rectangle",
        "border_style": "thick",
    },
    "approved": {
        "text": "ZATWIERDZONE",
        "color": "#27ae60",
        "icon": "✓",
        "shape": "rectangle",
        "border_style": "solid",
    },
    "rejected": {
        "text": "ODRZUCONE",
        "color": "#e74c3c",
        "icon": "✗",
        "shape": "rectangle",
        "border_style": "solid",
    },
    "original": {
        "text": "ORYGINAŁ",
        "color": "#2c3e50",
        "icon": "📄",
        "shape": "rectangle",
        "border_style": "solid",
    },

    # === Nowe - z obrazka ===
    "top_secret": {
        "text": "TOP SECRET",
        "color": "#cc0000",
        "icon": "🔴",
        "shape": "rectangle",
        "border_style": "double",
    },
    "classified": {
        "text": "CLASSIFIED",
        "color": "#cc0000",
        "icon": "📛",
        "shape": "rectangle",
        "border_style": "thick",
    },
    "do_not_copy": {
        "text": "DO NOT COPY",
        "color": "#cc0000",
        "icon": "🚫",
        "shape": "rectangle",
        "border_style": "solid",
    },
    "for_your_eyes_only": {
        "text": "FOR YOUR EYES ONLY",
        "color": "#000066",
        "icon": "👁",
        "shape": "rectangle",
        "border_style": "double",
    },
    "security_clearance": {
        "text": "LEVEL 1",
        "circular_text": "SECURITY CLEARANCE REQUIRED",
        "color": "#cc0000",
        "icon": "🔵",
        "shape": "circle",
        "border_style": "double",
    },
    "do_not_photocopy": {
        "text": "DO NOT",
        "circular_text": "PHOTOCOPY",
        "color": "#cc0000",
        "icon": "📵",
        "shape": "circle",
        "border_style": "solid",
    },
    "original_document": {
        "text": "ORIGINAL",
        "circular_text": "DOCUMENT",
        "color": "#006600",
        "icon": "📃",
        "shape": "circle",
        "border_style": "double",
    },
}

# Mapowanie nazw na enumy
SHAPE_MAP = {
    "rectangle": StampShape.RECTANGLE,
    "circle": StampShape.CIRCLE,
    "oval": StampShape.OVAL,
    "rounded_rect": StampShape.ROUNDED_RECT,
}

BORDER_STYLE_MAP = {
    "solid": BorderStyle.SOLID,
    "double": BorderStyle.DOUBLE,
    "dashed": BorderStyle.DASHED,
    "thick": BorderStyle.THICK,
    "thin": BorderStyle.THIN,
}

WEAR_LEVEL_MAP = {
    "none": WearLevel.NONE,
    "light": WearLevel.LIGHT,
    "medium": WearLevel.MEDIUM,
    "heavy": WearLevel.HEAVY,
}


def _styled_combo() -> QComboBox:
    """Tworzy wystylizowany ComboBox."""
    combo = QComboBox()
    combo.setStyleSheet("""
        QComboBox {
            background-color: #0f1629;
            border: 1px solid #2d3a50;
            border-radius: 4px;
            padding: 6px 10px;
            color: #ffffff;
            min-width: 120px;
        }
        QComboBox:hover {
            border-color: #e0a800;
        }
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #8892a0;
            margin-right: 5px;
        }
        QComboBox QAbstractItemView {
            background-color: #0f1629;
            border: 1px solid #2d3a50;
            selection-background-color: #e0a800;
            selection-color: #1a1a2e;
            color: #ffffff;
        }
    """)
    return combo


def _styled_slider() -> QSlider:
    """Tworzy wystylizowany Slider."""
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setStyleSheet("""
        QSlider::groove:horizontal {
            background-color: #0f1629;
            height: 6px;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background-color: #e0a800;
            width: 16px;
            height: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }
        QSlider::sub-page:horizontal {
            background-color: #e0a800;
            border-radius: 3px;
        }
    """)
    return slider


def _styled_line_edit(placeholder: str = "") -> QLineEdit:
    """Tworzy wystylizowany LineEdit."""
    line_edit = QLineEdit()
    line_edit.setPlaceholderText(placeholder)
    line_edit.setStyleSheet("""
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
    return line_edit


def _styled_groupbox(title: str) -> QGroupBox:
    """Tworzy wystylizowany GroupBox."""
    group = QGroupBox(title)
    group.setStyleSheet("""
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
    return group


class StampPicker(QWidget):
    """
    Widget do wyboru pieczątek z rozszerzonymi funkcjami.

    Emituje sygnały po wyborze pieczątki z konfiguracją.
    """

    stamp_selected = pyqtSignal(object)  # StampConfig

    def __init__(self, parent=None):
        super().__init__(parent)

        self._selected_stamp: Optional[str] = None
        self._custom_text: str = ""
        self._custom_color: str = "#e0a800"
        self._circular_text: str = ""
        self._size: int = 48
        self._rotation: float = 0
        self._corner: str = "center"  # Nowy parametr
        self._opacity: float = 1.0
        self._shape: StampShape = StampShape.RECTANGLE
        self._border_style: BorderStyle = BorderStyle.SOLID
        self._wear_level: WearLevel = WearLevel.NONE
        self._vintage_effect: bool = False
        self._double_strike: bool = False
        self._ink_splatter: bool = False
        self._auto_date: bool = False

        # Lista załadowanych własnych pieczątek z plików
        self._custom_stamps: Dict[str, Path] = {}  # klucz -> ścieżka do pliku

        self._renderer = StampRenderer()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Tworzy interfejs użytkownika."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area dla całości
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #0f1629;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #2d3a50;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #e0a800;
            }
        """)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 8, 0)

        # === Lista pieczątek ===
        stamps_label = QLabel("Wybierz pieczątkę:")
        stamps_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        layout.addWidget(stamps_label)

        self._stamps_list = QListWidget()
        self._stamps_list.setStyleSheet("""
            QListWidget {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 6px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #2d3a50;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #e0a800;
                color: #1a1a2e;
            }
            QListWidget::item:hover {
                background-color: #1f2940;
            }
        """)
        self._stamps_list.setMaximumHeight(250)

        # Dodaj predefiniowane pieczątki
        for key, stamp in PRESET_STAMPS.items():
            item = QListWidgetItem(f"{stamp['icon']} {stamp['text']}")
            item.setData(Qt.ItemDataRole.UserRole, key)
            self._stamps_list.addItem(item)

        # Dodaj opcję własnej pieczątki
        custom_item = QListWidgetItem("✏️ Własna pieczątka...")
        custom_item.setData(Qt.ItemDataRole.UserRole, "custom")
        self._stamps_list.addItem(custom_item)

        self._stamps_list.currentRowChanged.connect(self._on_stamp_selected)
        layout.addWidget(self._stamps_list)

        # Przycisk załaduj z pliku
        load_btn = QPushButton("📁 Załaduj pieczątkę z pliku")
        load_btn.setStyleSheet("""
            QPushButton {
                background-color: #1f2940;
                border: 1px solid #2d3a50;
                border-radius: 6px;
                padding: 8px;
                color: #e0a800;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2d3a50;
                border-color: #e0a800;
            }
            QPushButton:pressed {
                background-color: #0f1629;
            }
        """)
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.clicked.connect(self._on_load_from_file)
        layout.addWidget(load_btn)

        # === Panel własnej pieczątki ===
        self._custom_group = _styled_groupbox("Własna pieczątka")
        self._custom_group.setVisible(False)
        custom_layout = QVBoxLayout(self._custom_group)

        # Tekst główny
        text_row = QHBoxLayout()
        text_label = QLabel("Tekst:")
        text_label.setStyleSheet("color: #8892a0;")
        text_label.setFixedWidth(100)
        text_row.addWidget(text_label)

        self._custom_text_input = _styled_line_edit("Wpisz tekst pieczątki...")
        self._custom_text_input.textChanged.connect(self._on_custom_text_changed)
        text_row.addWidget(self._custom_text_input)
        custom_layout.addLayout(text_row)

        # Tekst po obwodzie (dla okrągłych)
        circular_row = QHBoxLayout()
        circular_label = QLabel("Tekst obwód:")
        circular_label.setStyleSheet("color: #8892a0;")
        circular_label.setFixedWidth(100)
        circular_row.addWidget(circular_label)

        self._circular_text_input = _styled_line_edit("Tekst po obwodzie (okrągłe)...")
        self._circular_text_input.textChanged.connect(self._on_circular_text_changed)
        circular_row.addWidget(self._circular_text_input)
        custom_layout.addLayout(circular_row)

        # Kolor
        color_row = QHBoxLayout()
        color_label = QLabel("Kolor:")
        color_label.setStyleSheet("color: #8892a0;")
        color_label.setFixedWidth(100)
        color_row.addWidget(color_label)

        self._color_preview = QLabel()
        self._color_preview.setFixedSize(30, 30)
        self._color_preview.setStyleSheet(
            f"background-color: {self._custom_color}; "
            "border: 1px solid #2d3a50; border-radius: 4px;"
        )
        color_row.addWidget(self._color_preview)

        self._color_btn = QPushButton("Zmień")
        self._color_btn.setStyleSheet("""
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
        self._color_btn.clicked.connect(self._on_color_pick)
        color_row.addWidget(self._color_btn)
        color_row.addStretch()
        custom_layout.addLayout(color_row)

        layout.addWidget(self._custom_group)

        # === Kształt i styl ===
        shape_group = _styled_groupbox("Kształt i styl")
        shape_layout = QVBoxLayout(shape_group)

        # Kształt
        shape_row = QHBoxLayout()
        shape_label = QLabel("Kształt:")
        shape_label.setStyleSheet("color: #8892a0;")
        shape_label.setFixedWidth(100)
        shape_row.addWidget(shape_label)

        self._shape_combo = _styled_combo()
        self._shape_combo.addItem("Prostokąt", "rectangle")
        self._shape_combo.addItem("Okrągła", "circle")
        self._shape_combo.addItem("Owalna", "oval")
        self._shape_combo.currentIndexChanged.connect(self._on_shape_changed)
        shape_row.addWidget(self._shape_combo)
        shape_row.addStretch()
        shape_layout.addLayout(shape_row)

        # Styl ramki
        border_row = QHBoxLayout()
        border_label = QLabel("Ramka:")
        border_label.setStyleSheet("color: #8892a0;")
        border_label.setFixedWidth(100)
        border_row.addWidget(border_label)

        self._border_combo = _styled_combo()
        self._border_combo.addItem("Pojedyncza", "solid")
        self._border_combo.addItem("Podwójna", "double")
        self._border_combo.addItem("Przerywana", "dashed")
        self._border_combo.addItem("Gruba", "thick")
        self._border_combo.addItem("Cienka", "thin")
        self._border_combo.currentIndexChanged.connect(self._on_border_changed)
        border_row.addWidget(self._border_combo)
        border_row.addStretch()
        shape_layout.addLayout(border_row)

        layout.addWidget(shape_group)

        # === Ustawienia ===
        settings_group = _styled_groupbox("Ustawienia")
        settings_layout = QVBoxLayout(settings_group)

        # Rozmiar
        size_row = QHBoxLayout()
        size_label = QLabel("Rozmiar:")
        size_label.setStyleSheet("color: #8892a0;")
        size_label.setFixedWidth(100)
        size_row.addWidget(size_label)

        self._size_slider = _styled_slider()
        self._size_slider.setMinimum(24)
        self._size_slider.setMaximum(120)
        self._size_slider.setValue(self._size)
        self._size_slider.valueChanged.connect(self._on_size_changed)
        size_row.addWidget(self._size_slider)

        self._size_value = QLabel(f"{self._size}pt")
        self._size_value.setStyleSheet("color: #ffffff;")
        self._size_value.setFixedWidth(50)
        size_row.addWidget(self._size_value)
        settings_layout.addLayout(size_row)

        # Rotacja
        rotation_row = QHBoxLayout()
        rotation_label = QLabel("Rotacja:")
        rotation_label.setStyleSheet("color: #8892a0;")
        rotation_label.setFixedWidth(100)
        rotation_row.addWidget(rotation_label)

        self._rotation_slider = _styled_slider()
        self._rotation_slider.setMinimum(-45)
        self._rotation_slider.setMaximum(45)
        self._rotation_slider.setValue(0)
        self._rotation_slider.valueChanged.connect(self._on_rotation_changed)
        rotation_row.addWidget(self._rotation_slider)

        self._rotation_value = QLabel("0°")
        self._rotation_value.setStyleSheet("color: #ffffff;")
        self._rotation_value.setFixedWidth(50)
        rotation_row.addWidget(self._rotation_value)
        settings_layout.addLayout(rotation_row)

        # Narożnik
        corner_row = QHBoxLayout()
        corner_label = QLabel("Narożnik:")
        corner_label.setStyleSheet("color: #8892a0;")
        corner_label.setFixedWidth(100)
        corner_row.addWidget(corner_label)

        self._corner_combo = _styled_combo()
        self._corner_combo.addItem("Środek", "center")
        self._corner_combo.addItem("Górny lewy", "top-left")
        self._corner_combo.addItem("Górny środek", "top-center")
        self._corner_combo.addItem("Górny prawy", "top-right")
        self._corner_combo.addItem("Dolny lewy", "bottom-left")
        self._corner_combo.addItem("Dolny środek", "bottom-center")
        self._corner_combo.addItem("Dolny prawy", "bottom-right")
        self._corner_combo.currentIndexChanged.connect(self._update_preview)
        corner_row.addWidget(self._corner_combo)
        corner_row.addStretch()
        settings_layout.addLayout(corner_row)

        # === Efekty ===
        effects_group = _styled_groupbox("Efekty")
        effects_layout = QVBoxLayout(effects_group)

        # Przezroczystość
        opacity_row = QHBoxLayout()
        opacity_label = QLabel("Przezroczystość:")
        opacity_label.setStyleSheet("color: #8892a0;")
        opacity_label.setFixedWidth(100)
        opacity_row.addWidget(opacity_label)

        self._opacity_slider = _styled_slider()
        self._opacity_slider.setMinimum(10)
        self._opacity_slider.setMaximum(100)
        self._opacity_slider.setValue(100)
        self._opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_row.addWidget(self._opacity_slider)

        self._opacity_value = QLabel("100%")
        self._opacity_value.setStyleSheet("color: #ffffff;")
        self._opacity_value.setFixedWidth(50)
        opacity_row.addWidget(self._opacity_value)
        effects_layout.addLayout(opacity_row)

        # Efekt zużycia
        wear_row = QHBoxLayout()
        wear_label = QLabel("Zużycie:")
        wear_label.setStyleSheet("color: #8892a0;")
        wear_label.setFixedWidth(100)
        wear_row.addWidget(wear_label)

        self._wear_combo = _styled_combo()
        self._wear_combo.addItem("Brak", "none")
        self._wear_combo.addItem("Lekkie", "light")
        self._wear_combo.addItem("Średnie", "medium")
        self._wear_combo.addItem("Mocne", "heavy")
        self._wear_combo.currentIndexChanged.connect(self._on_wear_changed)
        wear_row.addWidget(self._wear_combo)
        wear_row.addStretch()
        effects_layout.addLayout(wear_row)

        # Starodruk (vintage/letterpress)
        vintage_row = QHBoxLayout()
        vintage_label = QLabel("Starodruk:")
        vintage_label.setStyleSheet("color: #8892a0;")
        vintage_label.setFixedWidth(100)
        vintage_row.addWidget(vintage_label)

        self._vintage_checkbox = QCheckBox("Efekt letterpress")
        self._vintage_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #2d3a50;
                border-radius: 4px;
                background-color: #0f1629;
            }
            QCheckBox::indicator:checked {
                background-color: #e0a800;
                border-color: #e0a800;
            }
            QCheckBox::indicator:hover {
                border-color: #e0a800;
            }
        """)
        self._vintage_checkbox.stateChanged.connect(self._on_vintage_changed)
        vintage_row.addWidget(self._vintage_checkbox)
        vintage_row.addStretch()
        effects_layout.addLayout(vintage_row)

        # Podwójne odbicie
        double_row = QHBoxLayout()
        double_label = QLabel("Podwójne:")
        double_label.setStyleSheet("color: #8892a0;")
        double_label.setFixedWidth(100)
        double_row.addWidget(double_label)

        self._double_checkbox = QCheckBox("Efekt podwójnego odbicia")
        self._double_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #2d3a50;
                border-radius: 4px;
                background-color: #0f1629;
            }
            QCheckBox::indicator:checked {
                background-color: #e0a800;
                border-color: #e0a800;
            }
            QCheckBox::indicator:hover {
                border-color: #e0a800;
            }
        """)
        self._double_checkbox.stateChanged.connect(self._on_double_changed)
        double_row.addWidget(self._double_checkbox)
        double_row.addStretch()
        effects_layout.addLayout(double_row)

        # Rozbryzgi tuszu
        splatter_row = QHBoxLayout()
        splatter_label = QLabel("Rozbryzgi:")
        splatter_label.setStyleSheet("color: #8892a0;")
        splatter_label.setFixedWidth(100)
        splatter_row.addWidget(splatter_label)

        self._splatter_checkbox = QCheckBox("Kropelki tuszu wokół")
        self._splatter_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #2d3a50;
                border-radius: 4px;
                background-color: #0f1629;
            }
            QCheckBox::indicator:checked {
                background-color: #e0a800;
                border-color: #e0a800;
            }
            QCheckBox::indicator:hover {
                border-color: #e0a800;
            }
        """)
        self._splatter_checkbox.stateChanged.connect(self._on_splatter_changed)
        splatter_row.addWidget(self._splatter_checkbox)
        splatter_row.addStretch()
        effects_layout.addLayout(splatter_row)

        # Auto data
        date_row = QHBoxLayout()
        date_label = QLabel("Data:")
        date_label.setStyleSheet("color: #8892a0;")
        date_label.setFixedWidth(100)
        date_row.addWidget(date_label)

        self._date_checkbox = QCheckBox("Wstaw [DATA] → dziś")
        self._date_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #2d3a50;
                border-radius: 4px;
                background-color: #0f1629;
            }
            QCheckBox::indicator:checked {
                background-color: #e0a800;
                border-color: #e0a800;
            }
            QCheckBox::indicator:hover {
                border-color: #e0a800;
            }
        """)
        self._date_checkbox.stateChanged.connect(self._on_date_changed)
        date_row.addWidget(self._date_checkbox)
        date_row.addStretch()
        effects_layout.addLayout(date_row)

        layout.addWidget(effects_group)

        layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _on_load_from_file(self) -> None:
        """Obsługa załadowania pieczątki z pliku."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz plik pieczątki",
            "",
            "Pliki obrazów (*.png *.jpg *.jpeg *.bmp);;Wszystkie pliki (*.*)"
        )

        if not file_path:
            return  # Użytkownik anulował

        # Utwórz klucz dla custom stamp (bazując na nazwie pliku)
        file_name = Path(file_path).stem
        key = f"custom_file_{len(self._custom_stamps)}"

        # Zapisz w słowniku
        self._custom_stamps[key] = Path(file_path)

        # Dodaj do listy (przed opcją "Własna pieczątka...")
        insert_index = self._stamps_list.count() - 1  # Przed ostatnim elementem
        item = QListWidgetItem(f"🖼️ {file_name}")
        item.setData(Qt.ItemDataRole.UserRole, key)
        self._stamps_list.insertItem(insert_index, item)

        # Automatycznie wybierz załadowaną pieczątkę
        self._stamps_list.setCurrentRow(insert_index)

    def _on_stamp_selected(self, row: int) -> None:
        """Obsługa wyboru pieczątki."""
        if row < 0:
            return

        item = self._stamps_list.item(row)
        key = item.data(Qt.ItemDataRole.UserRole)

        if key == "custom":
            self._selected_stamp = None
            self._custom_group.setVisible(True)
        elif key.startswith("custom_file_"):
            # Pieczątka załadowana z pliku
            self._selected_stamp = key
            self._custom_group.setVisible(False)
        else:
            self._selected_stamp = key
            self._custom_group.setVisible(False)

            # Ustaw kontrolki na podstawie presetu
            stamp = PRESET_STAMPS[key]
            shape_str = stamp.get("shape", "rectangle")
            border_str = stamp.get("border_style", "solid")

            # Znajdź i ustaw kształt
            for i in range(self._shape_combo.count()):
                if self._shape_combo.itemData(i) == shape_str:
                    self._shape_combo.setCurrentIndex(i)
                    break

            # Znajdź i ustaw styl ramki
            for i in range(self._border_combo.count()):
                if self._border_combo.itemData(i) == border_str:
                    self._border_combo.setCurrentIndex(i)
                    break

        self._update_preview()

    def _on_custom_text_changed(self, text: str) -> None:
        """Obsługa zmiany tekstu własnej pieczątki."""
        self._custom_text = text
        self._update_preview()

    def _on_circular_text_changed(self, text: str) -> None:
        """Obsługa zmiany tekstu po obwodzie."""
        self._circular_text = text
        self._update_preview()

    def _on_color_pick(self) -> None:
        """Wybór koloru pieczątki."""
        color = QColorDialog.getColor(
            QColor(self._custom_color),
            self,
            "Wybierz kolor pieczątki"
        )
        if color.isValid():
            self._custom_color = color.name()
            self._color_preview.setStyleSheet(
                f"background-color: {self._custom_color}; "
                "border: 1px solid #2d3a50; border-radius: 4px;"
            )
            self._update_preview()

    def _on_shape_changed(self, index: int) -> None:
        """Obsługa zmiany kształtu."""
        shape_str = self._shape_combo.itemData(index)
        self._shape = SHAPE_MAP.get(shape_str, StampShape.RECTANGLE)

        # Włącz/wyłącz tekst po obwodzie
        is_circular = self._shape == StampShape.CIRCLE
        self._circular_text_input.setEnabled(is_circular)

        self._update_preview()

    def _on_border_changed(self, index: int) -> None:
        """Obsługa zmiany stylu ramki."""
        border_str = self._border_combo.itemData(index)
        self._border_style = BORDER_STYLE_MAP.get(border_str, BorderStyle.SOLID)
        self._update_preview()

    def _on_size_changed(self, value: int) -> None:
        """Obsługa zmiany rozmiaru."""
        self._size = value
        self._size_value.setText(f"{value}pt")
        self._update_preview()

    def _on_rotation_changed(self, value: int) -> None:
        """Obsługa zmiany rotacji."""
        self._rotation = value
        self._rotation_value.setText(f"{value}°")
        self._update_preview()

    def _on_opacity_changed(self, value: int) -> None:
        """Obsługa zmiany przezroczystości."""
        self._opacity = value / 100.0
        self._opacity_value.setText(f"{value}%")
        self._update_preview()

    def _on_wear_changed(self, index: int) -> None:
        """Obsługa zmiany efektu zużycia."""
        wear_str = self._wear_combo.itemData(index)
        self._wear_level = WEAR_LEVEL_MAP.get(wear_str, WearLevel.NONE)
        self._update_preview()

    def _on_vintage_changed(self, state: int) -> None:
        """Obsługa zmiany efektu starodruku."""
        self._vintage_effect = state == 2  # Qt.CheckState.Checked = 2
        self._update_preview()

    def _on_double_changed(self, state: int) -> None:
        """Obsługa zmiany efektu podwójnego odbicia."""
        self._double_strike = state == 2
        self._update_preview()

    def _on_splatter_changed(self, state: int) -> None:
        """Obsługa zmiany efektu rozbryzgów."""
        self._ink_splatter = state == 2
        self._update_preview()

    def _on_date_changed(self, state: int) -> None:
        """Obsługa zmiany automatycznej daty."""
        self._auto_date = state == 2
        self._update_preview()

    def _build_config(self) -> Optional[StampConfig]:
        """Buduje StampConfig z aktualnych ustawień."""
        # Obsługa pieczątek z plików
        if self._selected_stamp and self._selected_stamp.startswith("custom_file_"):
            stamp_path = self._custom_stamps.get(self._selected_stamp)
            if not stamp_path:
                return None

            # Dla pieczątek z pliku używamy uproszczonej konfiguracji
            # Większe mnożniki dla lepszego skalowania własnych obrazów
            return StampConfig(
                text="",  # Brak tekstu, używamy obrazu
                position=Point(100, 100),
                rotation=float(self._rotation),
                rotation_random=False,
                corner="center",
                scale=1.0,
                shape=StampShape.RECTANGLE,  # Nie ma znaczenia dla obrazów
                border_style=BorderStyle.SOLID,  # Nie ma znaczenia
                border_width=0.0,  # Brak ramki dla obrazów
                color=(0, 0, 0),  # Nie ma znaczenia
                opacity=self._opacity,
                wear_level=self._wear_level,
                vintage_effect=self._vintage_effect,
                double_strike=self._double_strike,
                ink_splatter=self._ink_splatter,
                auto_date=False,  # Nie ma sensu dla obrazów
                width=self._size * 8,  # Podwojony mnożnik dla lepszego skalowania
                height=self._size * 4,  # Podwojony mnożnik
                font_size=self._size * 0.6,
                circular_font_size=self._size * 0.25,
                stamp_path=stamp_path,  # KLUCZ: ścieżka do pliku
            )

        # Obsługa predefiniowanych pieczątek
        if self._selected_stamp:
            stamp = PRESET_STAMPS[self._selected_stamp]
            text = stamp["text"]
            color_hex = stamp["color"]
            circular_text = stamp.get("circular_text")
            # Kształt i styl ramki zawsze z combo (użytkownik może zmienić)
            shape_str = self._shape_combo.currentData()
            border_str = self._border_combo.currentData()
        elif self._custom_text:
            text = self._custom_text.upper()
            color_hex = self._custom_color
            circular_text = self._circular_text if self._circular_text else None
            shape_str = self._shape_combo.currentData()
            border_str = self._border_combo.currentData()
        else:
            return None

        # Konwertuj kolor hex na RGB 0-1
        color = QColor(color_hex)
        color_rgb = (color.redF(), color.greenF(), color.blueF())

        # Mapuj enumy
        shape = SHAPE_MAP.get(shape_str, StampShape.RECTANGLE)
        border_style = BORDER_STYLE_MAP.get(border_str, BorderStyle.SOLID)

        # Oblicz rozmiary
        width = self._size * 4  # Skalowanie dla czytelności
        height = self._size * 2 if shape != StampShape.CIRCLE else self._size * 4

        return StampConfig(
            text=text,
            circular_text=circular_text,
            position=Point(100, 100),  # Domyślna pozycja
            rotation=float(self._rotation),
            rotation_random=False,  # Nie losowa - dokładna rotacja
            corner="center",  # Narożnik ustawiany w watermark_page.py
            scale=1.0,
            shape=shape,
            border_style=border_style,
            border_width=2.0,
            color=color_rgb,
            opacity=self._opacity,
            wear_level=self._wear_level,
            vintage_effect=self._vintage_effect,
            double_strike=self._double_strike,
            ink_splatter=self._ink_splatter,
            auto_date=self._auto_date,
            width=width,
            height=height,
            font_size=self._size * 0.6,
            circular_font_size=self._size * 0.25,
        )

    def _update_preview(self) -> None:
        """Emituje sygnał stamp_selected gdy zmienią się parametry."""
        config = self._build_config()
        if config:
            self.stamp_selected.emit(config)

    def get_stamp_config(self) -> Optional[StampConfig]:
        """Zwraca aktualną konfigurację pieczątki."""
        return self._build_config()
