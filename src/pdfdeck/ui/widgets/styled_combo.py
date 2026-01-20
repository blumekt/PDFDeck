"""
StyledComboBox - Dropdown w stylu MediaDown.

Ciemne tło z żółtą strzałką.
"""

from PyQt6.QtWidgets import QComboBox, QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt


class StyledComboBox(QComboBox):
    """
    ComboBox w stylu MediaDown.

    Ciemne tło, żółta strzałka rozwijana.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_style()

    def _setup_style(self) -> None:
        """Ustawia styl combo box."""
        self.setStyleSheet("""
            QComboBox {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 6px;
                color: #ffffff;
                padding: 10px;
                padding-right: 35px;
                font-size: 14px;
                min-width: 120px;
            }

            QComboBox:hover {
                border-color: #3d4a60;
            }

            QComboBox:focus {
                border-color: #e0a800;
            }

            QComboBox::drop-down {
                border: none;
                width: 30px;
                background-color: transparent;
            }

            QComboBox::down-arrow {
                image: none;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 8px solid #e0a800;
                margin-right: 10px;
            }

            QComboBox::down-arrow:hover {
                border-top-color: #f0b800;
            }

            QComboBox QAbstractItemView {
                background-color: #1f2940;
                border: 1px solid #2d3a50;
                border-radius: 6px;
                color: #ffffff;
                selection-background-color: #e0a800;
                selection-color: #1a1a2e;
                padding: 5px;
                outline: none;
            }

            QComboBox QAbstractItemView::item {
                padding: 10px;
                border-radius: 4px;
                min-height: 25px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #2d3a50;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #e0a800;
                color: #1a1a2e;
            }
        """)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.view().setCursor(Qt.CursorShape.PointingHandCursor)


class LabeledComboBox(QWidget):
    """
    ComboBox z etykietą.

    Układ: [Label] [ComboBox]
    """

    def __init__(self, label: str, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Etykieta
        self._label = QLabel(label)
        self._label.setStyleSheet("color: #ffffff;")
        layout.addWidget(self._label)

        # ComboBox
        self._combo = StyledComboBox()
        layout.addWidget(self._combo)

        layout.addStretch()

    @property
    def combo(self) -> StyledComboBox:
        """Zwraca wewnętrzny ComboBox."""
        return self._combo

    def add_item(self, text: str, data=None) -> None:
        """Dodaje element do listy."""
        self._combo.addItem(text, data)

    def add_items(self, items: list) -> None:
        """Dodaje wiele elementów do listy."""
        self._combo.addItems(items)

    def current_text(self) -> str:
        """Zwraca wybrany tekst."""
        return self._combo.currentText()

    def current_data(self):
        """Zwraca dane wybranego elementu."""
        return self._combo.currentData()

    def set_current_text(self, text: str) -> None:
        """Ustawia wybrany element po tekście."""
        index = self._combo.findText(text)
        if index >= 0:
            self._combo.setCurrentIndex(index)

    def clear(self) -> None:
        """Czyści listę."""
        self._combo.clear()
