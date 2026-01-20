"""
SplitDialog - Dialog do dzielenia dokumentu PDF.

Funkcje:
- Dzielenie na równe części
- Dzielenie po określonych stronach
- Wybór katalogu docelowego
"""

from typing import Optional, List
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QRadioButton, QButtonGroup,
    QGroupBox, QSpinBox, QFileDialog, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt

from pdfdeck.ui.widgets.styled_button import StyledButton


class SplitDialog(QDialog):
    """
    Dialog do dzielenia dokumentu PDF.

    Pozwala użytkownikowi:
    - Podzielić na równe części
    - Podzielić po określonych stronach
    - Wybrać katalog docelowy
    """

    def __init__(self, page_count: int, parent=None):
        super().__init__(parent)

        self._page_count = page_count
        self._split_points: List[int] = []
        self._output_dir: Optional[Path] = None

        self.setWindowTitle("Podziel dokument")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setStyleSheet("""
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
            QRadioButton {
                color: #ffffff;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #2d3a50;
                border-radius: 8px;
                background-color: #0f1629;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #e0a800;
                border-radius: 8px;
                background-color: #e0a800;
            }
        """)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Tworzy interfejs użytkownika."""
        layout = QVBoxLayout(self)

        # Info
        info_label = QLabel(f"Dokument zawiera {self._page_count} stron")
        info_label.setStyleSheet("color: #8892a0; font-size: 13px;")
        layout.addWidget(info_label)

        # === Metoda podziału ===
        method_group = QGroupBox("Metoda podziału")
        method_layout = QVBoxLayout(method_group)

        self._method_group = QButtonGroup(self)

        self._equal_radio = QRadioButton("Podziel na równe części")
        self._equal_radio.setChecked(True)
        self._method_group.addButton(self._equal_radio, 0)
        method_layout.addWidget(self._equal_radio)

        # Liczba części
        equal_row = QHBoxLayout()
        equal_row.addSpacing(25)
        equal_label = QLabel("Liczba części:")
        equal_label.setStyleSheet("color: #8892a0;")
        equal_row.addWidget(equal_label)

        self._parts_spin = QSpinBox()
        self._parts_spin.setMinimum(2)
        self._parts_spin.setMaximum(self._page_count)
        self._parts_spin.setValue(2)
        self._parts_spin.setStyleSheet("""
            QSpinBox {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
        """)
        self._parts_spin.valueChanged.connect(self._update_preview)
        equal_row.addWidget(self._parts_spin)
        equal_row.addStretch()

        method_layout.addLayout(equal_row)

        self._custom_radio = QRadioButton("Podziel po określonych stronach")
        self._method_group.addButton(self._custom_radio, 1)
        method_layout.addWidget(self._custom_radio)

        self._method_group.buttonClicked.connect(self._on_method_changed)

        layout.addWidget(method_group)

        # === Punkty podziału (dla metody custom) ===
        self._custom_group = QGroupBox("Punkty podziału")
        self._custom_group.setVisible(False)
        custom_layout = QVBoxLayout(self._custom_group)

        custom_desc = QLabel(
            "Dodaj numery stron, po których chcesz podzielić dokument.\n"
            "Np. podział po stronie 5 utworzy dwa pliki: strony 1-5 i 6-końiec."
        )
        custom_desc.setStyleSheet("color: #8892a0; font-size: 12px;")
        custom_layout.addWidget(custom_desc)

        # Dodawanie punktów
        add_row = QHBoxLayout()
        add_label = QLabel("Podziel po stronie:")
        add_label.setStyleSheet("color: #8892a0;")
        add_row.addWidget(add_label)

        self._split_page_spin = QSpinBox()
        self._split_page_spin.setMinimum(1)
        self._split_page_spin.setMaximum(self._page_count - 1)
        self._split_page_spin.setValue(1)
        self._split_page_spin.setStyleSheet("""
            QSpinBox {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
        """)
        add_row.addWidget(self._split_page_spin)

        add_btn = StyledButton("Dodaj", "secondary")
        add_btn.clicked.connect(self._on_add_split_point)
        add_row.addWidget(add_btn)
        add_row.addStretch()

        custom_layout.addLayout(add_row)

        # Lista punktów
        self._split_list = QListWidget()
        self._split_list.setStyleSheet("""
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
                background-color: #1f2940;
            }
        """)
        self._split_list.setMaximumHeight(100)
        custom_layout.addWidget(self._split_list)

        # Usuń punkt
        remove_btn = StyledButton("Usuń zaznaczony", "danger")
        remove_btn.clicked.connect(self._on_remove_split_point)
        custom_layout.addWidget(remove_btn)

        layout.addWidget(self._custom_group)

        # === Podgląd ===
        preview_group = QGroupBox("Podgląd podziału")
        preview_layout = QVBoxLayout(preview_group)

        self._preview_label = QLabel()
        self._preview_label.setStyleSheet("color: #8892a0; font-size: 12px;")
        self._preview_label.setWordWrap(True)
        preview_layout.addWidget(self._preview_label)

        layout.addWidget(preview_group)

        self._update_preview()

        # === Katalog docelowy ===
        output_group = QGroupBox("Katalog docelowy")
        output_layout = QVBoxLayout(output_group)

        output_row = QHBoxLayout()
        self._output_label = QLabel("Nie wybrano (użyj katalogu źródłowego)")
        self._output_label.setStyleSheet(
            "color: #8892a0; background-color: #0f1629; "
            "padding: 8px; border-radius: 4px;"
        )
        output_row.addWidget(self._output_label, 1)

        browse_btn = QPushButton("Przeglądaj...")
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #1f2940;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 8px 16px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #2d3a50;
            }
        """)
        browse_btn.clicked.connect(self._on_browse_output)
        output_row.addWidget(browse_btn)

        output_layout.addLayout(output_row)
        layout.addWidget(output_group)

        # === Przyciski ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = StyledButton("Anuluj", "secondary")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        self._split_btn = StyledButton("Podziel dokument", "primary")
        self._split_btn.clicked.connect(self._on_split)
        buttons_layout.addWidget(self._split_btn)

        layout.addLayout(buttons_layout)

    def _on_method_changed(self, button: QRadioButton) -> None:
        """Obsługa zmiany metody podziału."""
        is_custom = self._method_group.id(button) == 1
        self._custom_group.setVisible(is_custom)
        self._parts_spin.setEnabled(not is_custom)
        self._update_preview()

    def _on_add_split_point(self) -> None:
        """Dodaje punkt podziału."""
        page = self._split_page_spin.value()
        if page not in self._split_points:
            self._split_points.append(page)
            self._split_points.sort()
            self._update_split_list()
            self._update_preview()

    def _on_remove_split_point(self) -> None:
        """Usuwa punkt podziału."""
        row = self._split_list.currentRow()
        if row >= 0 and row < len(self._split_points):
            del self._split_points[row]
            self._update_split_list()
            self._update_preview()

    def _update_split_list(self) -> None:
        """Aktualizuje listę punktów podziału."""
        self._split_list.clear()
        for page in self._split_points:
            item = QListWidgetItem(f"Po stronie {page}")
            self._split_list.addItem(item)

    def _update_preview(self) -> None:
        """Aktualizuje podgląd podziału."""
        if self._method_group.checkedId() == 0:  # Równe części
            parts = self._parts_spin.value()
            pages_per_part = self._page_count // parts
            remainder = self._page_count % parts

            parts_info = []
            start = 1
            for i in range(parts):
                end = start + pages_per_part - 1
                if i < remainder:
                    end += 1
                parts_info.append(f"Część {i + 1}: strony {start}-{end}")
                start = end + 1

            self._preview_label.setText("\n".join(parts_info))
        else:  # Custom
            if not self._split_points:
                self._preview_label.setText("Dodaj punkty podziału")
                return

            parts_info = []
            points = [0] + self._split_points + [self._page_count]
            for i in range(len(points) - 1):
                start = points[i] + 1
                end = points[i + 1]
                parts_info.append(f"Część {i + 1}: strony {start}-{end}")

            self._preview_label.setText("\n".join(parts_info))

    def _on_browse_output(self) -> None:
        """Wybór katalogu docelowego."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Wybierz katalog docelowy"
        )
        if dir_path:
            self._output_dir = Path(dir_path)
            self._output_label.setText(str(self._output_dir))
            self._output_label.setStyleSheet(
                "color: #ffffff; background-color: #0f1629; "
                "padding: 8px; border-radius: 4px;"
            )

    def _on_split(self) -> None:
        """Zatwierdza podział."""
        self.accept()

    def get_split_points(self) -> List[int]:
        """Zwraca punkty podziału."""
        if self._method_group.checkedId() == 0:  # Równe części
            parts = self._parts_spin.value()
            pages_per_part = self._page_count // parts
            remainder = self._page_count % parts

            points = []
            current = 0
            for i in range(parts - 1):
                current += pages_per_part
                if i < remainder:
                    current += 1
                points.append(current)
            return points
        else:
            return self._split_points.copy()

    def get_output_dir(self) -> Optional[Path]:
        """Zwraca katalog docelowy."""
        return self._output_dir

    @staticmethod
    def get_split_config(page_count: int, parent=None) -> Optional[tuple]:
        """
        Statyczna metoda do szybkiego uzyskania konfiguracji.

        Args:
            page_count: Liczba stron dokumentu
            parent: Widget rodzic

        Returns:
            Tuple (split_points, output_dir) lub None jeśli anulowano
        """
        dialog = SplitDialog(page_count, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return (dialog.get_split_points(), dialog.get_output_dir())
        return None
