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
    QTabWidget, QScrollArea, QSplitter, QSizePolicy,
    QGraphicsView, QGraphicsScene, QGraphicsTextItem,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap, QPainter, QFont, QBrush

from pdfdeck.ui.pages.base_page import BasePage
from pdfdeck.ui.widgets.styled_button import StyledButton
from pdfdeck.ui.widgets.styled_combo import StyledComboBox
from pdfdeck.ui.widgets.stamp_picker import StampPicker
from pdfdeck.ui.widgets.profile_combo import ProfileComboBox
from pdfdeck.core.models import WatermarkConfig
from pdfdeck.core.profile_manager import (
    ProfileManager,
    ProfileType,
    ProfileMetadata,
    WatermarkProfile,
    StampProfile,
)

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
        self._loaded_stamp_config = None  # Konfiguracja załadowana z profilu
        self._selected_stamp_config = None  # Aktualnie wybrana pieczątka z pickera
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

        # --- Grupa: Ustawienia pieczątki ---
        stamp_group = QGroupBox("Ustawienia pieczątki")
        stamp_group.setStyleSheet(self._group_style())
        stamp_layout = QVBoxLayout(stamp_group)
        stamp_layout.setSpacing(8)

        # Profil
        profile_label = QLabel("Profil:")
        profile_label.setStyleSheet("color: #8892a0; font-size: 13px;")
        stamp_layout.addWidget(profile_label)

        self._stamp_profile_combo = ProfileComboBox(
            ProfileType.STAMP,
            on_save_clicked=self._save_stamp_profile,
        )
        self._stamp_profile_combo.profile_selected.connect(self._load_stamp_profile)
        stamp_layout.addWidget(self._stamp_profile_combo)

        stamp_layout.addSpacing(5)

        # Rotacja
        rotation_row = QHBoxLayout()
        rotation_label = QLabel("Rotacja:")
        rotation_label.setStyleSheet("color: #8892a0;")
        rotation_label.setFixedWidth(70)
        rotation_row.addWidget(rotation_label)

        self._stamp_rotation_slider = QSlider(Qt.Orientation.Horizontal)
        self._stamp_rotation_slider.setMinimum(-45)
        self._stamp_rotation_slider.setMaximum(45)
        self._stamp_rotation_slider.setValue(0)
        self._stamp_rotation_slider.setStyleSheet(self._slider_style())
        self._stamp_rotation_slider.valueChanged.connect(self._update_stamp_preview)
        rotation_row.addWidget(self._stamp_rotation_slider)

        self._stamp_rotation_value = QLabel("0°")
        self._stamp_rotation_value.setStyleSheet("color: #8892a0; min-width: 35px;")
        self._stamp_rotation_slider.valueChanged.connect(
            lambda v: self._stamp_rotation_value.setText(f"{v}°")
        )
        rotation_row.addWidget(self._stamp_rotation_value)
        stamp_layout.addLayout(rotation_row)

        # Rozmiar
        size_row = QHBoxLayout()
        size_label = QLabel("Rozmiar:")
        size_label.setStyleSheet("color: #8892a0;")
        size_label.setFixedWidth(70)
        size_row.addWidget(size_label)

        self._stamp_size_slider = QSlider(Qt.Orientation.Horizontal)
        self._stamp_size_slider.setMinimum(24)
        self._stamp_size_slider.setMaximum(120)
        self._stamp_size_slider.setValue(48)
        self._stamp_size_slider.setStyleSheet(self._slider_style())
        self._stamp_size_slider.valueChanged.connect(self._on_stamp_size_changed)
        size_row.addWidget(self._stamp_size_slider)

        self._stamp_size_value = QLabel("48pt")
        self._stamp_size_value.setStyleSheet("color: #8892a0; min-width: 45px;")
        self._stamp_size_slider.valueChanged.connect(
            lambda v: self._stamp_size_value.setText(f"{v}pt")
        )
        size_row.addWidget(self._stamp_size_value)
        stamp_layout.addLayout(size_row)

        # Narożnik
        corner_row = QHBoxLayout()
        corner_label = QLabel("Narożnik:")
        corner_label.setStyleSheet("color: #8892a0;")
        corner_label.setFixedWidth(70)
        corner_row.addWidget(corner_label)

        self._stamp_corner_combo = StyledComboBox()
        self._stamp_corner_combo.addItem("Środek", "center")
        self._stamp_corner_combo.addItem("Górny lewy", "top-left")
        self._stamp_corner_combo.addItem("Górny środek", "top-center")
        self._stamp_corner_combo.addItem("Górny prawy", "top-right")
        self._stamp_corner_combo.addItem("Dolny lewy", "bottom-left")
        self._stamp_corner_combo.addItem("Dolny środek", "bottom-center")
        self._stamp_corner_combo.addItem("Dolny prawy", "bottom-right")
        self._stamp_corner_combo.currentIndexChanged.connect(lambda: self._update_stamp_preview())
        corner_row.addWidget(self._stamp_corner_combo)
        corner_row.addStretch()
        stamp_layout.addLayout(corner_row)

        # Przycisk dodaj
        self._add_stamp_btn = StyledButton("Dodaj pieczątkę", "primary")
        self._add_stamp_btn.clicked.connect(self._on_add_stamp)
        stamp_layout.addWidget(self._add_stamp_btn)

        config_layout.addWidget(stamp_group)

        # --- Grupa: Wybór pieczątki ---
        picker_group = QGroupBox("Dostępne pieczątki")
        picker_group.setStyleSheet(self._group_style())
        picker_layout = QVBoxLayout(picker_group)
        picker_layout.setSpacing(6)

        # StampPicker widget
        self._stamp_picker = StampPicker()
        self._stamp_picker.stamp_selected.connect(self._on_stamp_selected)

        # Scroll area dla stamp picker
        picker_scroll = QScrollArea()
        picker_scroll.setWidget(self._stamp_picker)
        picker_scroll.setWidgetResizable(True)
        picker_scroll.setStyleSheet("""
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
        picker_scroll.setMinimumHeight(200)
        picker_layout.addWidget(picker_scroll)

        config_layout.addWidget(picker_group, 1)

        splitter.addWidget(config_widget)

        # === Prawa strona: Podgląd ===
        preview_widget = QWidget()
        preview_widget.setMinimumWidth(200)
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(10, 0, 0, 0)

        preview_label = QLabel("Podgląd:")
        preview_label.setStyleSheet("color: #8892a0; font-size: 14px;")
        preview_layout.addWidget(preview_label)

        # Scena i widok dla podglądu pieczątki
        self._stamp_preview_scene = QGraphicsScene()
        self._stamp_preview_scene.setBackgroundBrush(QBrush(QColor("#ffffff")))

        self._stamp_preview_view = QGraphicsView(self._stamp_preview_scene)
        self._stamp_preview_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._stamp_preview_view.setStyleSheet("""
            QGraphicsView {
                background-color: #ffffff;
                border: 1px solid #2d3a50;
                border-radius: 8px;
            }
        """)
        self._stamp_preview_view.setMinimumSize(200, 280)
        self._stamp_preview_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        preview_layout.addWidget(self._stamp_preview_view, 1)

        splitter.addWidget(preview_widget)
        splitter.setSizes([350, 450])

        content_layout.addWidget(splitter, 1)

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _on_stamp_selected(self, config) -> None:
        """Obsługa wyboru pieczątki."""
        self._selected_stamp_config = config
        # Resetuj profil gdy użytkownik wybiera nową pieczątkę w pickerze
        self._loaded_stamp_config = None
        # Aktualizuj podgląd
        self._update_stamp_preview()

    def _update_stamp_preview(self) -> None:
        """Aktualizuje podgląd pieczątki z rotacją."""
        from pdfdeck.core.stamp_renderer import StampRenderer

        # Wyczyść scenę
        self._stamp_preview_scene.clear()

        # Użyj konfiguracji z profilu jeśli jest załadowana, w przeciwnym razie z pickera
        if self._loaded_stamp_config is not None:
            # Użyj kopii żeby nie modyfikować oryginału
            from copy import deepcopy
            config = deepcopy(self._loaded_stamp_config)
        else:
            config = self._stamp_picker.get_stamp_config()

        if not config:
            # Brak wybranej pieczątki - pokaż tekst
            text_item = QGraphicsTextItem("Wybierz pieczątkę\nz listy")
            font = QFont("Arial", 16)
            text_item.setFont(font)
            text_item.setDefaultTextColor(QColor(150, 150, 150))
            self._stamp_preview_scene.addItem(text_item)
            self._stamp_preview_scene.setSceneRect(self._stamp_preview_scene.itemsBoundingRect())
            return

        try:
            # Nadpisz rozmiar wartością z lokalnego slidera (dla spójności UI)
            size = self._stamp_size_slider.value()

            # Dla pieczątek z pliku zachowaj oryginalne proporcje obrazka
            # Mnożnik 4 (taki sam jak dla dynamicznych pieczątek)
            if config.stamp_path:
                # Wczytaj aspect ratio z pliku
                try:
                    from PIL import Image
                    img = Image.open(config.stamp_path)
                    aspect_ratio = img.width / img.height
                    img.close()
                except Exception:
                    aspect_ratio = 1.0  # Fallback na kwadrat

                if aspect_ratio >= 1.0:
                    config.width = size * 4
                    config.height = config.width / aspect_ratio
                else:
                    config.height = size * 4
                    config.width = config.height * aspect_ratio
            else:
                from pdfdeck.core.models import StampShape
                config.width = size * 4
                config.height = size * 2 if config.shape != StampShape.CIRCLE else size * 4

            config.font_size = size * 0.6
            config.circular_font_size = size * 0.25

            # Użyj renderera do wygenerowania pieczątki
            renderer = StampRenderer()
            png_data = renderer.render_to_png(config)

            # Załaduj jako pixmap
            pixmap = QPixmap()
            pixmap.loadFromData(png_data)

            if pixmap.isNull():
                # Fallback - pokaż tekst
                text_item = QGraphicsTextItem(config.text)
                font = QFont("Arial", 16)
                text_item.setFont(font)
                text_item.setDefaultTextColor(QColor(150, 150, 150))
                self._stamp_preview_scene.addItem(text_item)
                self._stamp_preview_scene.setSceneRect(self._stamp_preview_scene.itemsBoundingRect())
                return

            # Skaluj do rozsądnego rozmiaru dla podglądu (max 300px)
            max_size = 300
            if pixmap.width() > max_size or pixmap.height() > max_size:
                pixmap = pixmap.scaled(
                    max_size, max_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

            # Dodaj do sceny
            pixmap_item = self._stamp_preview_scene.addPixmap(pixmap)

            # Zastosuj rotację z slidera (nadpisuje rotację z StampPickera)
            rotation = self._stamp_rotation_slider.value()
            rect = pixmap_item.boundingRect()
            pixmap_item.setTransformOriginPoint(rect.center())
            # Neguj rotację bo PyQt6 używa clockwise, a PIL (w PDF) używa counter-clockwise
            pixmap_item.setRotation(-rotation)

            # Wycentruj w scenie
            self._stamp_preview_scene.setSceneRect(self._stamp_preview_scene.itemsBoundingRect())
            scene_rect = self._stamp_preview_scene.sceneRect()
            scene_rect.adjust(-50, -50, 50, 50)
            self._stamp_preview_view.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)

        except Exception as e:
            # W przypadku błędu pokaż komunikat
            text_item = QGraphicsTextItem(f"Błąd podglądu:\n{str(e)}")
            font = QFont("Arial", 12)
            text_item.setFont(font)
            text_item.setDefaultTextColor(QColor(200, 50, 50))
            self._stamp_preview_scene.addItem(text_item)
            self._stamp_preview_scene.setSceneRect(self._stamp_preview_scene.itemsBoundingRect())

    def _on_stamp_size_changed(self, value: int) -> None:
        """Obsługa zmiany rozmiaru pieczątki."""
        # Po prostu zaktualizuj podgląd
        self._update_stamp_preview()

    def _on_add_stamp(self) -> None:
        """Obsługa dodawania pieczątki do PDF."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(
                self,
                "Błąd",
                "Najpierw otwórz dokument PDF"
            )
            return

        # Użyj konfiguracji z profilu jeśli jest załadowana, w przeciwnym razie z pickera
        if self._loaded_stamp_config is not None:
            # Użyj konfiguracji z profilu ale skopiuj ją, żeby nie modyfikować oryginału
            from copy import deepcopy
            config = deepcopy(self._loaded_stamp_config)
        else:
            config = self._stamp_picker.get_stamp_config()
            if not config:
                QMessageBox.warning(
                    self,
                    "Błąd",
                    "Wybierz pieczątkę z listy lub stwórz własną"
                )
                return

        # ZAWSZE zastosuj rotację i narożnik z UI (użytkownik mógł je zmienić)
        config.rotation = float(self._stamp_rotation_slider.value())
        config.corner = self._stamp_corner_combo.currentData()

        # Zaktualizuj rozmiar z slidera (dla spójności z podglądem)
        size = self._stamp_size_slider.value()
        if config.stamp_path:
            # Dla zewnętrznych plików zachowaj oryginalne proporcje
            try:
                from PIL import Image
                img = Image.open(config.stamp_path)
                aspect_ratio = img.width / img.height
                img.close()
            except Exception:
                aspect_ratio = 1.0

            if aspect_ratio >= 1.0:
                config.width = size * 4
                config.height = config.width / aspect_ratio
            else:
                config.height = size * 4
                config.width = config.height * aspect_ratio
        else:
            from pdfdeck.core.models import StampShape
            config.width = size * 4
            config.height = size * 2 if config.shape != StampShape.CIRCLE else size * 4
        config.font_size = size * 0.6
        config.circular_font_size = size * 0.25

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

        # Profil
        profile_label = QLabel("Profil:")
        profile_label.setStyleSheet("color: #8892a0; font-size: 13px;")
        watermark_layout.addWidget(profile_label)

        self._watermark_profile_combo = ProfileComboBox(
            ProfileType.WATERMARK,
            on_save_clicked=self._save_watermark_profile,
        )
        self._watermark_profile_combo.profile_selected.connect(self._load_watermark_profile)
        watermark_layout.addWidget(self._watermark_profile_combo)

        watermark_layout.addSpacing(5)

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

        # Scena i widok dla podglądu z rotacją
        self._preview_scene = QGraphicsScene()
        self._preview_scene.setBackgroundBrush(QBrush(QColor("#ffffff")))

        self._preview_view = QGraphicsView(self._preview_scene)
        self._preview_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._preview_view.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self._preview_view.setStyleSheet("""
            QGraphicsView {
                background-color: #ffffff;
                border: 1px solid #2d3a50;
                border-radius: 8px;
            }
        """)
        self._preview_view.setMinimumSize(200, 280)
        self._preview_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # Tekst podglądu
        self._preview_text_item = QGraphicsTextItem("PRZYKŁAD")
        font = QFont("Arial", 48)
        font.setBold(True)
        self._preview_text_item.setFont(font)
        self._preview_text_item.setDefaultTextColor(QColor(128, 128, 128, 76))
        self._preview_scene.addItem(self._preview_text_item)

        preview_layout.addWidget(self._preview_view, 1)

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
        """Aktualizuje podgląd znaku wodnego z rotacją."""
        text = self._watermark_text.text() or "PRZYKŁAD"
        size = self._font_size.value()
        opacity = self._opacity_slider.value() / 100.0
        rotation = self._rotation.value()
        color = self._color_btn.color

        # Aktualizuj tekst i font
        self._preview_text_item.setPlainText(text)
        font = QFont("Arial", size)
        font.setBold(True)
        self._preview_text_item.setFont(font)

        # Kolor z przezroczystością
        preview_color = QColor(color)
        preview_color.setAlphaF(opacity)
        self._preview_text_item.setDefaultTextColor(preview_color)

        # Rotacja - najpierw reset, potem ustaw punkt obrotu i rotację
        self._preview_text_item.setRotation(0)
        rect = self._preview_text_item.boundingRect()
        self._preview_text_item.setTransformOriginPoint(rect.center())
        # Neguj rotację bo PyQt6 używa clockwise, a PIL (w PDF) używa counter-clockwise
        self._preview_text_item.setRotation(-rotation)

        # Wycentruj w scenie
        self._preview_scene.setSceneRect(self._preview_scene.itemsBoundingRect())
        # Dodaj marginesy wokół tekstu
        scene_rect = self._preview_scene.sceneRect()
        scene_rect.adjust(-50, -50, 50, 50)
        self._preview_view.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)

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

    # === Profile management ===

    def _save_watermark_profile(self) -> None:
        """Zapisuje aktualną konfigurację jako profil watermark."""
        from PyQt6.QtWidgets import QInputDialog
        from datetime import datetime

        text = self._watermark_text.text().strip()
        if not text:
            QMessageBox.warning(
                self,
                "Błąd",
                "Wpisz tekst znaku wodnego przed zapisaniem profilu",
            )
            return

        name, ok = QInputDialog.getText(self, "Zapisz profil", "Nazwa profilu:")
        if not ok or not name.strip():
            return

        color = self._color_btn.color
        config = WatermarkConfig(
            text=text,
            font_size=float(self._font_size.value()),
            rotation=float(self._rotation.value()),
            color=(color.redF(), color.greenF(), color.blueF()),
            opacity=self._opacity_slider.value() / 100.0,
            overlay=self._overlay_combo.currentData(),
        )

        profile = WatermarkProfile(
            metadata=ProfileMetadata(
                name=name.strip(),
                profile_type=ProfileType.WATERMARK,
                description=f"Znak wodny: {text}",
                created_at=datetime.now().isoformat(),
                modified_at=datetime.now().isoformat(),
            ),
            config=config,
        )

        pm = ProfileManager()
        pm.save_watermark_profile(profile)

        self._watermark_profile_combo.refresh()
        QMessageBox.information(self, "Sukces", f"Profil '{name}' zapisany!")

    def _load_watermark_profile(self, name: str) -> None:
        """Ładuje profil watermark do kontrolek UI."""
        pm = ProfileManager()
        profile = pm.get_watermark_profile(name)
        if not profile:
            return

        config = profile.config
        self._watermark_text.setText(config.text)
        self._font_size.setValue(int(config.font_size))
        self._rotation.setValue(int(config.rotation))
        self._opacity_slider.setValue(int(config.opacity * 100))

        # Kolor - konwersja RGB 0-1 -> QColor
        color = QColor.fromRgbF(config.color[0], config.color[1], config.color[2])
        self._color_btn.color = color

        # Overlay
        self._overlay_combo.setCurrentIndex(1 if config.overlay else 0)

        self._update_preview()

    def _save_stamp_profile(self) -> None:
        """Zapisuje aktualną konfigurację jako profil pieczątki."""
        from PyQt6.QtWidgets import QInputDialog
        from datetime import datetime
        from copy import deepcopy

        # Użyj załadowanego profilu jeśli istnieje, w przeciwnym razie z pickera
        if self._loaded_stamp_config is not None:
            config = deepcopy(self._loaded_stamp_config)
        else:
            config = self._stamp_picker.get_stamp_config()

        if not config:
            QMessageBox.warning(
                self,
                "Błąd",
                "Wybierz lub skonfiguruj pieczątkę przed zapisaniem profilu",
            )
            return

        name, ok = QInputDialog.getText(self, "Zapisz profil", "Nazwa profilu:")
        if not ok or not name.strip():
            return

        # Zastosuj rotację, narożnik i rozmiar z UI (użytkownik mógł je zmienić)
        config.rotation = float(self._stamp_rotation_slider.value())
        config.corner = self._stamp_corner_combo.currentData()

        # Zaktualizuj rozmiar z slidera
        size = self._stamp_size_slider.value()
        if config.stamp_path:
            # Dla zewnętrznych plików zachowaj oryginalne proporcje
            try:
                from PIL import Image
                img = Image.open(config.stamp_path)
                aspect_ratio = img.width / img.height
                img.close()
            except Exception:
                aspect_ratio = 1.0

            if aspect_ratio >= 1.0:
                config.width = size * 4
                config.height = config.width / aspect_ratio
            else:
                config.height = size * 4
                config.width = config.height * aspect_ratio
        else:
            from pdfdeck.core.models import StampShape
            config.width = size * 4
            config.height = size * 2 if config.shape != StampShape.CIRCLE else size * 4
        config.font_size = size * 0.6
        config.circular_font_size = size * 0.25

        profile = StampProfile(
            metadata=ProfileMetadata(
                name=name.strip(),
                profile_type=ProfileType.STAMP,
                description=f"Pieczątka: {config.text}",
                created_at=datetime.now().isoformat(),
                modified_at=datetime.now().isoformat(),
            ),
            config=config,
        )

        pm = ProfileManager()
        pm.save_stamp_profile(profile)

        # Odśwież listę profili
        self._stamp_profile_combo.refresh()

        # Ważne: Ustaw combo na "(brak profilu)" żeby użytkownik mógł dalej pracować z pickerem
        # bez ładowania zapisanego profilu
        self._stamp_profile_combo._combo.setCurrentIndex(0)  # "(brak profilu)"

        # Resetuj załadowany profil, żeby użytkownik mógł kontynuować pracę z pickerem
        self._loaded_stamp_config = None
        self._update_stamp_preview()

        QMessageBox.information(self, "Sukces", f"Profil '{name}' zapisany!")

    def _load_stamp_profile(self, name: str) -> None:
        """Ładuje profil pieczątki do kontrolek UI."""
        pm = ProfileManager()
        profile = pm.get_stamp_profile(name)
        if not profile:
            return

        config = profile.config

        # Oblicz rozmiar z zapisanej konfiguracji (odwrócenie mnożnika)
        if config.stamp_path:
            # Dla obrazków: odtwórz size z width lub height (w zależności od aspect_ratio)
            try:
                from PIL import Image
                img = Image.open(config.stamp_path)
                aspect_ratio = img.width / img.height
                img.close()
            except Exception:
                aspect_ratio = 1.0

            # Użyj większego wymiaru jako bazę
            if aspect_ratio >= 1.0:
                size = int(config.width / 8)
            else:
                size = int(config.height / 8)
        else:
            # Dla zwykłych: width = size * 4
            size = int(config.width / 4)

        # Ogranicz rozmiar do zakresu slidera (24-120)
        size = max(24, min(120, size))

        # Ustaw rozmiar w sliderze
        self._stamp_size_slider.setValue(size)
        self._stamp_size_value.setText(f"{size}pt")

        # Ustaw rotację w UI
        self._stamp_rotation_slider.setValue(int(config.rotation))
        self._stamp_rotation_value.setText(f"{int(config.rotation)}°")

        # Znajdź i ustaw narożnik w combo
        for i in range(self._stamp_corner_combo.count()):
            if self._stamp_corner_combo.itemData(i) == config.corner:
                self._stamp_corner_combo.setCurrentIndex(i)
                break

        # Zapisz konfigurację do użycia przy dodawaniu pieczątki
        self._loaded_stamp_config = config

        # Aktualizuj podgląd z załadowaną konfiguracją
        self._update_stamp_preview()

    # === Public API ===

    def on_document_loaded(self) -> None:
        """Wywoływane po załadowaniu dokumentu."""
        pass
