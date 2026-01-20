"""
DiffViewer - Widget do wyświetlania porównania dokumentów PDF.

Funkcje:
- Wyświetlanie obrazu różnic
- Nawigacja między stronami
- Podgląd obu dokumentów obok siebie
"""

from typing import Optional, List
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QSplitter,
    QSpinBox, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage

from pdfdeck.core.diff_engine import DiffEngine, DiffResult
from pdfdeck.utils.i18n import t


class DiffViewer(QWidget):
    """
    Widget do wizualnego porównywania dokumentów PDF.

    Wyświetla nakładkę różnic między dwoma wersjami dokumentu.
    """

    comparison_started = pyqtSignal()
    comparison_finished = pyqtSignal(list)  # List[DiffResult]
    page_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._diff_engine = DiffEngine()
        self._results: List[DiffResult] = []
        self._current_page = 0

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Tworzy interfejs użytkownika."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # === Pasek narzędzi ===
        toolbar = QHBoxLayout()

        # Nawigacja stron
        self._prev_btn = QPushButton("◀")
        self._prev_btn.setFixedWidth(40)
        self._prev_btn.clicked.connect(self._prev_page)
        toolbar.addWidget(self._prev_btn)

        self._page_spin = QSpinBox()
        self._page_spin.setMinimum(1)
        self._page_spin.setMaximum(1)
        self._page_spin.valueChanged.connect(self._on_page_changed)
        toolbar.addWidget(self._page_spin)

        self._page_label = QLabel("/ 1")
        toolbar.addWidget(self._page_label)

        self._next_btn = QPushButton("▶")
        self._next_btn.setFixedWidth(40)
        self._next_btn.clicked.connect(self._next_page)
        toolbar.addWidget(self._next_btn)

        toolbar.addStretch()

        # Status różnic
        self._diff_status = QLabel("")
        self._diff_status.setStyleSheet("color: #8892a0;")
        toolbar.addWidget(self._diff_status)

        # Podobieństwo
        self._similarity_label = QLabel("")
        self._similarity_label.setStyleSheet("font-weight: bold;")
        toolbar.addWidget(self._similarity_label)

        layout.addLayout(toolbar)

        # === Splitter z trzema widokami ===
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # Dokument A
        self._doc_a_frame = self._create_preview_frame("Dokument A (oryginał)")
        self._splitter.addWidget(self._doc_a_frame)

        # Widok różnic (środek)
        self._diff_frame = self._create_preview_frame("Porównanie")
        self._splitter.addWidget(self._diff_frame)

        # Dokument B
        self._doc_b_frame = self._create_preview_frame("Dokument B (nowy)")
        self._splitter.addWidget(self._doc_b_frame)

        # Ustaw proporcje
        self._splitter.setSizes([200, 400, 200])

        layout.addWidget(self._splitter)

        # === Pasek postępu ===
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # Początkowy stan
        self._update_navigation()

    def _create_preview_frame(self, title: str) -> QFrame:
        """Tworzy ramkę z podglądem."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #1f2940;
                border: 1px solid #2d3a50;
                border-radius: 4px;
            }
        """)

        layout = QVBoxLayout(frame)

        # Tytuł
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #ffffff; font-weight: bold; padding: 5px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Scroll area z obrazem
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #16213e;
            }
        """)

        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setStyleSheet("background-color: #16213e;")
        scroll.setWidget(image_label)

        layout.addWidget(scroll)

        # Zapisz referencję do labela
        frame.image_label = image_label

        return frame

    def load_documents(self, path_a: Path, path_b: Path) -> bool:
        """
        Ładuje dwa dokumenty do porównania.

        Args:
            path_a: Ścieżka do pierwszego dokumentu
            path_b: Ścieżka do drugiego dokumentu

        Returns:
            True jeśli udało się załadować
        """
        try:
            pages_a, pages_b = self._diff_engine.load_documents(path_a, path_b)

            max_pages = max(pages_a, pages_b)
            self._page_spin.setMaximum(max_pages)
            self._page_label.setText(f"/ {max_pages}")

            self._current_page = 0
            self._page_spin.setValue(1)

            self._update_navigation()
            return True

        except Exception as e:
            print(f"Błąd ładowania dokumentów: {e}")
            return False

    def compare_current_page(self) -> None:
        """Porównuje aktualnie wybraną stronę."""
        result = self._diff_engine.compare_page(self._current_page)

        if result:
            self._display_result(result)

    def compare_all(self) -> None:
        """Porównuje wszystkie strony."""
        self.comparison_started.emit()
        self._progress.setVisible(True)
        self._progress.setMaximum(max(
            self._diff_engine.page_count_a,
            self._diff_engine.page_count_b
        ))

        self._results = []

        for i in range(self._progress.maximum()):
            self._progress.setValue(i + 1)
            result = self._diff_engine.compare_page(i)
            if result:
                self._results.append(result)

        self._progress.setVisible(False)

        if self._results:
            self._display_result(self._results[0])

        self.comparison_finished.emit(self._results)

    def _display_result(self, result: DiffResult) -> None:
        """Wyświetla wynik porównania."""
        # Pokaż obraz różnic
        if result.diff_image:
            pixmap = QPixmap()
            pixmap.loadFromData(result.diff_image)
            self._diff_frame.image_label.setPixmap(
                pixmap.scaled(
                    400, 600,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )

        # Aktualizuj status
        if result.has_differences:
            self._diff_status.setText("Wykryto różnice")
            self._diff_status.setStyleSheet("color: #e74c3c; font-weight: bold;")
        else:
            self._diff_status.setText("Brak różnic")
            self._diff_status.setStyleSheet("color: #27ae60; font-weight: bold;")

        # Podobieństwo
        similarity = result.similarity_percent
        if similarity >= 95:
            color = "#27ae60"  # Zielony
        elif similarity >= 80:
            color = "#f39c12"  # Pomarańczowy
        else:
            color = "#e74c3c"  # Czerwony

        self._similarity_label.setText(f"Podobieństwo: {similarity:.1f}%")
        self._similarity_label.setStyleSheet(f"color: {color}; font-weight: bold;")

    def _prev_page(self) -> None:
        """Przechodzi do poprzedniej strony."""
        if self._current_page > 0:
            self._page_spin.setValue(self._current_page)  # 1-indexed

    def _next_page(self) -> None:
        """Przechodzi do następnej strony."""
        max_page = max(
            self._diff_engine.page_count_a,
            self._diff_engine.page_count_b
        )
        if self._current_page < max_page - 1:
            self._page_spin.setValue(self._current_page + 2)  # 1-indexed

    def _on_page_changed(self, value: int) -> None:
        """Obsługa zmiany strony."""
        self._current_page = value - 1  # 0-indexed
        self._update_navigation()
        self.compare_current_page()
        self.page_changed.emit(self._current_page)

    def _update_navigation(self) -> None:
        """Aktualizuje stan przycisków nawigacji."""
        max_page = max(
            self._diff_engine.page_count_a,
            self._diff_engine.page_count_b
        )
        self._prev_btn.setEnabled(self._current_page > 0)
        self._next_btn.setEnabled(self._current_page < max_page - 1)

    def close_documents(self) -> None:
        """Zamyka załadowane dokumenty."""
        self._diff_engine.close()
        self._results = []
        self._current_page = 0

        # Wyczyść podglądy
        self._doc_a_frame.image_label.clear()
        self._doc_b_frame.image_label.clear()
        self._diff_frame.image_label.clear()

        self._diff_status.setText("")
        self._similarity_label.setText("")
