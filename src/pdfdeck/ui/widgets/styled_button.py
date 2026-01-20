"""
StyledButton - Przyciski w stylu MediaDown.

Żółty przycisk primary, szary secondary, czerwony danger.
"""

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon


class StyledButton(QPushButton):
    """
    Przycisk w stylu MediaDown.

    Typy:
    - primary: żółte tło (#e0a800), ciemny tekst
    - secondary: ciemne tło, jasny tekst (domyślne)
    - danger: czerwone tło (#e74c3c), biały tekst
    """

    def __init__(
        self,
        text: str = "",
        button_type: str = "primary",
        icon: QIcon | None = None,
        parent=None,
    ):
        super().__init__(text, parent)

        self._button_type = button_type
        self._setup_style()

        if icon:
            self.setIcon(icon)
            self.setIconSize(QSize(18, 18))

    def _setup_style(self) -> None:
        """Ustawia styl przycisku."""
        if self._button_type == "primary":
            self.setProperty("primary", True)
            self.setStyleSheet("""
                QPushButton {
                    background-color: #e0a800;
                    border: none;
                    border-radius: 6px;
                    color: #1a1a2e;
                    font-weight: bold;
                    padding: 10px 20px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #f0b800;
                }
                QPushButton:pressed {
                    background-color: #c09000;
                }
                QPushButton:disabled {
                    background-color: #8a7a00;
                    color: #4a4a4e;
                }
            """)
        elif self._button_type == "danger":
            self.setProperty("danger", True)
            self.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    border: none;
                    border-radius: 6px;
                    color: #ffffff;
                    font-weight: bold;
                    padding: 10px 20px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #ff5c4c;
                }
                QPushButton:pressed {
                    background-color: #c0392b;
                }
                QPushButton:disabled {
                    background-color: #7a3a3a;
                    color: #aaaaaa;
                }
            """)
        elif self._button_type == "success":
            self.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    border: none;
                    border-radius: 6px;
                    color: #ffffff;
                    font-weight: bold;
                    padding: 10px 20px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #2ecc71;
                }
                QPushButton:pressed {
                    background-color: #1e8449;
                }
            """)
        else:  # secondary
            self.setStyleSheet("""
                QPushButton {
                    background-color: #1f2940;
                    border: 1px solid #2d3a50;
                    border-radius: 6px;
                    color: #ffffff;
                    padding: 10px 20px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #2d3a50;
                    border-color: #3d4a60;
                }
                QPushButton:pressed {
                    background-color: #0f1629;
                }
                QPushButton:disabled {
                    background-color: #1a1a2e;
                    color: #5a6a7a;
                }
            """)

        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_button_type(self, button_type: str) -> None:
        """Zmienia typ przycisku."""
        self._button_type = button_type
        self._setup_style()


class IconButton(QPushButton):
    """
    Przycisk tylko z ikoną (bez tekstu).

    Używany w toolbarach i kompaktowych UI.
    """

    def __init__(
        self,
        icon: QIcon,
        tooltip: str = "",
        size: int = 32,
        parent=None,
    ):
        super().__init__(parent)

        self.setIcon(icon)
        self.setIconSize(QSize(size - 8, size - 8))
        self.setFixedSize(QSize(size, size))

        if tooltip:
            self.setToolTip(tooltip)

        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #2d3a50;
            }
            QPushButton:pressed {
                background-color: #1f2940;
            }
        """)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
