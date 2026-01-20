"""
BasePage - Bazowa klasa dla stron aplikacji.

Wszystkie strony dziedziczą po tej klasie.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class BasePage(QWidget):
    """
    Bazowa klasa dla wszystkich stron aplikacji.

    Zapewnia spójny wygląd i podstawową strukturę.
    """

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)

        self._title = title
        self._setup_base_ui()

    def _setup_base_ui(self) -> None:
        """Tworzy podstawową strukturę UI."""
        self.setObjectName("page")
        self.setStyleSheet("""
            #page {
                background-color: #16213e;
            }
        """)

        # Główny layout
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(20, 20, 20, 20)
        self._main_layout.setSpacing(15)

        # Tytuł strony (opcjonalny)
        if self._title:
            title_label = QLabel(self._title)
            title_label.setObjectName("page_title")
            title_font = QFont("Segoe UI", 20, QFont.Weight.Bold)
            title_label.setFont(title_font)
            title_label.setStyleSheet("color: #ffffff;")
            self._main_layout.addWidget(title_label)

    def add_widget(self, widget: QWidget) -> None:
        """Dodaje widget do strony."""
        self._main_layout.addWidget(widget)

    def add_stretch(self) -> None:
        """Dodaje rozciągacz."""
        self._main_layout.addStretch()

    def create_card(self, title: str = "") -> tuple[QWidget, QVBoxLayout]:
        """
        Tworzy kartę (sekcję) w stylu MediaDown.

        Returns:
            Tuple (widget karty, layout wewnętrzny)
        """
        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet("""
            #card {
                background-color: #1f2940;
                border: 1px solid #2d3a50;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        if title:
            title_label = QLabel(title)
            title_label.setObjectName("card_header")
            title_font = QFont("Segoe UI", 14, QFont.Weight.Bold)
            title_label.setFont(title_font)
            title_label.setStyleSheet("color: #ffffff;")
            layout.addWidget(title_label)

            # Separator
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setStyleSheet("background-color: #2d3a50; max-height: 1px;")
            layout.addWidget(separator)

        return card, layout


class PlaceholderPage(BasePage):
    """
    Tymczasowa strona placeholder.

    Wyświetla informację o nazwie strony i jej opisie.
    """

    def __init__(self, title: str, description: str = "", parent=None):
        super().__init__(title, parent)

        self._description = description
        self._setup_placeholder()

    def _setup_placeholder(self) -> None:
        """Tworzy zawartość placeholder."""
        # Karta z informacją
        card, layout = self.create_card()

        # Ikona/emoji
        icon_label = QLabel("🚧")
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Tekst "W budowie"
        info_label = QLabel("Strona w budowie")
        info_label.setStyleSheet("color: #e0a800; font-size: 18px; font-weight: bold;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        # Opis
        if self._description:
            desc_label = QLabel(self._description)
            desc_label.setStyleSheet("color: #8892a0; font-size: 14px;")
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        layout.addStretch()

        self.add_widget(card)
        self.add_stretch()


class ScrollablePage(BasePage):
    """
    Strona z przewijalną zawartością.

    Używana dla stron z dużą ilością treści.
    """

    def __init__(self, title: str = "", parent=None):
        super().__init__(title, parent)

        self._setup_scroll()

    def _setup_scroll(self) -> None:
        """Tworzy przewijalny obszar."""
        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("background-color: transparent;")

        # Container widget
        self._scroll_content = QWidget()
        self._scroll_content.setStyleSheet("background-color: transparent;")

        self._content_layout = QVBoxLayout(self._scroll_content)
        self._content_layout.setContentsMargins(0, 0, 10, 0)  # Padding na scrollbar
        self._content_layout.setSpacing(15)

        self._scroll.setWidget(self._scroll_content)
        self._main_layout.addWidget(self._scroll)

    def add_to_scroll(self, widget: QWidget) -> None:
        """Dodaje widget do przewijalnej zawartości."""
        self._content_layout.addWidget(widget)

    def add_scroll_stretch(self) -> None:
        """Dodaje rozciągacz do przewijalnej zawartości."""
        self._content_layout.addStretch()
