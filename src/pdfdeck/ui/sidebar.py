"""
Sidebar - Nawigacja w stylu MediaDown.

Menu boczne z logo, elementami nawigacji i opcjonalną grafiką na dole.
"""

from typing import List, Tuple
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QButtonGroup, QFrame, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QFont

from pdfdeck import __version__, __app_name__


class SidebarButton(QPushButton):
    """Przycisk menu sidebar."""

    def __init__(self, text: str, icon_path: str = "", parent=None):
        super().__init__(text, parent)

        self.setCheckable(True)
        self.setObjectName("sidebar_menu_item")

        # Ikona
        if icon_path and Path(icon_path).exists():
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(20, 20))

        self._setup_style()

    def _setup_style(self) -> None:
        """Ustawia styl przycisku."""
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 8px;
                color: #8892a0;
                font-size: 14px;
                padding: 12px 15px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #1f2940;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: transparent;
                color: #e0a800;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class Sidebar(QWidget):
    """
    Sidebar nawigacyjny w stylu MediaDown.

    Zawiera:
    - Logo i wersję na górze
    - Menu nawigacyjne
    - Opcjonalną grafikę na dole
    """

    # Sygnał emitowany przy zmianie strony
    # Args: (page_id)
    page_changed = pyqtSignal(str)

    # Definicja elementów menu
    MENU_ITEMS: List[Tuple[str, str, str]] = [
        ("pages", "Strony", "pages.png"),
        ("redaction", "Redakcja", "redaction.png"),
        ("watermark", "Znaki wodne", "watermark.png"),
        ("tools", "Narzędzia", "tools.png"),
        ("security", "Bezpieczeństwo", "security.png"),
        ("analysis", "Analiza", "analysis.png"),
        ("automation", "Automatyzacja", "automation.png"),
        ("settings", "Ustawienia", "settings.png"),
    ]

    def __init__(self, icons_path: Path | None = None, parent=None):
        super().__init__(parent)

        self._icons_path = icons_path or Path()
        self._buttons: dict[str, SidebarButton] = {}
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Tworzy interfejs sidebar."""
        self.setObjectName("sidebar")
        self.setFixedWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # === Logo ===
        logo_container = QWidget()
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setContentsMargins(15, 20, 15, 5)
        logo_layout.setSpacing(2)

        # Nazwa aplikacji
        logo_label = QLabel(__app_name__)
        logo_label.setObjectName("sidebar_logo")
        logo_font = QFont("Segoe UI", 24, QFont.Weight.Bold)
        logo_label.setFont(logo_font)
        logo_label.setStyleSheet("color: #e0a800;")
        logo_layout.addWidget(logo_label)

        # Wersja
        version_label = QLabel(f"v{__version__}")
        version_label.setObjectName("sidebar_version")
        version_label.setStyleSheet("color: #8892a0; font-size: 12px;")
        logo_layout.addWidget(version_label)

        layout.addWidget(logo_container)

        # === Separator ===
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #2d3a50; max-height: 1px;")
        layout.addWidget(separator)

        # === Menu ===
        menu_container = QWidget()
        menu_layout = QVBoxLayout(menu_container)
        menu_layout.setContentsMargins(5, 15, 5, 15)
        menu_layout.setSpacing(2)

        for page_id, label, icon_name in self.MENU_ITEMS:
            icon_path = str(self._icons_path / icon_name) if self._icons_path else ""
            button = SidebarButton(f"  {label}", icon_path)
            button.clicked.connect(lambda checked, pid=page_id: self._on_button_clicked(pid))

            self._buttons[page_id] = button
            self._button_group.addButton(button)
            menu_layout.addWidget(button)

        layout.addWidget(menu_container)

        # === Spacer ===
        layout.addStretch()

        # === Grafika na dole (opcjonalnie) ===
        # Tutaj można dodać obrazek jak w MediaDown
        # image_label = QLabel()
        # image_label.setPixmap(QPixmap("path/to/image.png").scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio))
        # layout.addWidget(image_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # === Styl ===
        self.setStyleSheet("""
            #sidebar {
                background-color: #1a1a2e;
                border-right: 1px solid #2d3a50;
            }
        """)

    def _on_button_clicked(self, page_id: str) -> None:
        """Obsługa kliknięcia przycisku menu."""
        self.page_changed.emit(page_id)

    def set_active_page(self, page_id: str) -> None:
        """Ustawia aktywną stronę."""
        if page_id in self._buttons:
            self._buttons[page_id].setChecked(True)

    def get_active_page(self) -> str | None:
        """Zwraca ID aktywnej strony."""
        for page_id, button in self._buttons.items():
            if button.isChecked():
                return page_id
        return None
