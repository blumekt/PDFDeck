"""
StyledToggle - Toggle switch w stylu MediaDown.

Żółty suwak na ciemnym tle.
"""

from PyQt6.QtWidgets import QCheckBox, QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush


class StyledToggle(QCheckBox):
    """
    Toggle switch w stylu MediaDown.

    Animowany przełącznik z żółtym suwakiem.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Wymiary
        self._width = 50
        self._height = 26
        self._handle_size = 20
        self._margin = 3

        # Kolory
        self._bg_color_off = QColor("#2d3a50")
        self._bg_color_on = QColor("#e0a800")
        self._handle_color = QColor("#ffffff")

        # Pozycja suwaka (0.0 - 1.0)
        self._handle_position = 0.0

        # Animacja
        self._animation = QPropertyAnimation(self, b"handle_position")
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Styl
        self.setFixedSize(self._width, self._height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Połącz sygnał
        self.stateChanged.connect(self._on_state_changed)

    def _on_state_changed(self, state: int) -> None:
        """Obsługa zmiany stanu."""
        target = 1.0 if state == Qt.CheckState.Checked.value else 0.0
        self._animation.stop()
        self._animation.setStartValue(self._handle_position)
        self._animation.setEndValue(target)
        self._animation.start()

    @property
    def handle_position(self) -> float:
        return self._handle_position

    @handle_position.setter
    def handle_position(self, value: float) -> None:
        self._handle_position = value
        self.update()

    def paintEvent(self, event) -> None:
        """Rysuje toggle switch."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Interpolacja koloru tła
        bg_color = self._interpolate_color(
            self._bg_color_off, self._bg_color_on, self._handle_position
        )

        # Rysuj tło (zaokrąglony prostokąt)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(
            0, 0, self._width, self._height,
            self._height / 2, self._height / 2
        )

        # Pozycja suwaka
        handle_x = self._margin + (
            self._width - self._handle_size - 2 * self._margin
        ) * self._handle_position
        handle_y = (self._height - self._handle_size) / 2

        # Rysuj suwak (kółko)
        painter.setBrush(QBrush(self._handle_color))
        painter.drawEllipse(
            int(handle_x), int(handle_y),
            self._handle_size, self._handle_size
        )

    def _interpolate_color(
        self, color1: QColor, color2: QColor, factor: float
    ) -> QColor:
        """Interpolacja między dwoma kolorami."""
        r = int(color1.red() + (color2.red() - color1.red()) * factor)
        g = int(color1.green() + (color2.green() - color1.green()) * factor)
        b = int(color1.blue() + (color2.blue() - color1.blue()) * factor)
        return QColor(r, g, b)

    def sizeHint(self):
        from PyQt6.QtCore import QSize
        return QSize(self._width, self._height)


class LabeledToggle(QWidget):
    """
    Toggle z etykietą.

    Układ: [Label] [Toggle]
    """

    toggled = pyqtSignal(bool)

    def __init__(self, label: str, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Etykieta
        self._label = QLabel(label)
        self._label.setStyleSheet("color: #ffffff;")
        layout.addWidget(self._label)

        layout.addStretch()

        # Toggle
        self._toggle = StyledToggle()
        self._toggle.toggled.connect(self.toggled.emit)
        layout.addWidget(self._toggle)

    def is_checked(self) -> bool:
        """Czy toggle jest włączony."""
        return self._toggle.isChecked()

    def set_checked(self, checked: bool) -> None:
        """Ustawia stan toggle."""
        self._toggle.setChecked(checked)

    def set_label(self, text: str) -> None:
        """Zmienia tekst etykiety."""
        self._label.setText(text)
