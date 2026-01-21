"""
ThumbnailGrid - Siatka miniatur stron PDF z drag & drop.

Killer feature: wizualne przeciąganie stron do zmiany kolejności.
Obsługuje też drop plików PDF z zewnątrz (multi-file merge).
"""

from typing import List, Optional

from PyQt6.QtWidgets import (
    QListWidget, QListWidgetItem, QAbstractItemView, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QMimeData, QUrl
from PyQt6.QtGui import QPixmap, QIcon, QDragEnterEvent, QDropEvent, QAction


class ThumbnailGrid(QListWidget):
    """
    Siatka miniatur stron PDF.

    Funkcje:
    - Wyświetlanie miniatur w siatce (IconMode)
    - Drag & drop do zmiany kolejności stron
    - Multi-select dla operacji grupowych
    - Drop plików PDF z zewnątrz (merge)
    - Menu kontekstowe
    """

    # Sygnał zmiany zaznaczenia
    # Args: (page_index) - -1 jeśli nic nie zaznaczono
    selection_changed = pyqtSignal(int)

    # Sygnał zmiany kolejności stron
    # Args: (new_order) - lista indeksów stron w nowej kolejności
    order_changed = pyqtSignal(list)

    # Sygnał drop plików z zewnątrz
    # Args: (file_paths, insert_position)
    files_dropped = pyqtSignal(list, int)

    # Sygnał żądania usunięcia stron
    # Args: (page_indices)
    delete_requested = pyqtSignal(list)

    # Sygnał żądania podziału
    # Args: (page_index) - indeks strony PO której podzielić
    split_requested = pyqtSignal(int)

    # Rozmiary miniatur
    THUMBNAIL_SIZE = 180
    ITEM_SIZE = 200  # Z paddingiem na etykietę

    def __init__(self, parent=None):
        super().__init__(parent)

        self._page_count = 0
        self._dragged_item: Optional[QListWidgetItem] = None
        self._setup_widget()
        self._setup_context_menu()

    def _setup_widget(self) -> None:
        """Konfiguruje widget."""
        # Tryb widoku: IconMode = siatka
        self.setViewMode(QListWidget.ViewMode.IconMode)

        # Rozmiary ikon i siatki
        self.setIconSize(QSize(self.THUMBNAIL_SIZE, self.THUMBNAIL_SIZE))
        self.setGridSize(QSize(self.ITEM_SIZE, self.ITEM_SIZE + 25))

        # Ruch: Snap - elementy wskakują do siatki
        self.setMovement(QListWidget.Movement.Snap)

        # Resize mode: dopasuj układ przy zmianie rozmiaru
        self.setResizeMode(QListWidget.ResizeMode.Adjust)

        # Drag & drop dla wewnętrznego reorderingu
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

        # Multi-select z Ctrl/Shift
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # Uniform item sizes dla wydajności
        self.setUniformItemSizes(True)

        # Spacing - szersze separatory między stronami
        self.setSpacing(20)

        # Wyrównanie - flow i wrapping
        self.setFlow(QListWidget.Flow.LeftToRight)
        self.setWrapping(True)
        self.setLayoutMode(QListWidget.LayoutMode.Batched)
        self.setBatchSize(100)

        # Styl
        self.setStyleSheet("""
            QListWidget {
                background-color: #1f2940;
                border: 1px solid #2d3a50;
                border-radius: 10px;
                padding: 20px;
                outline: none;
            }
            QListWidget::item {
                background-color: #0f1629;
                border: 2px solid transparent;
                border-radius: 8px;
                padding: 5px;
                margin: 10px;
            }
            QListWidget::item:hover {
                border-color: #3d4a60;
            }
            QListWidget::item:selected {
                background-color: #0f1629;
                border-color: #e0a800;
            }
        """)

        # Połącz sygnał zmiany zaznaczenia
        self.currentRowChanged.connect(self._on_selection_changed)

    def _setup_context_menu(self) -> None:
        """Tworzy menu kontekstowe."""
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos) -> None:
        """Wyświetla menu kontekstowe."""
        item = self.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1f2940;
                border: 1px solid #2d3a50;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                background-color: transparent;
                color: #ffffff;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #e0a800;
                color: #1a1a2e;
            }
        """)

        # Usuń
        delete_action = QAction("Usuń", self)
        delete_action.triggered.connect(self._on_delete_selected)
        menu.addAction(delete_action)

        # Podziel tutaj
        page_index = item.data(Qt.ItemDataRole.UserRole)
        if page_index is not None and page_index < self._page_count - 1:
            split_action = QAction(f"Rozdziel PDF na dwa od strony {page_index + 2}", self)
            split_action.triggered.connect(lambda: self.split_requested.emit(page_index))
            menu.addAction(split_action)

        menu.exec(self.mapToGlobal(pos))

    def _on_delete_selected(self) -> None:
        """Obsługa usuwania zaznaczonych stron."""
        indices = self.get_selected_indices()
        if indices:
            self.delete_requested.emit(indices)

    def set_page_count(self, count: int) -> None:
        """
        Inicjalizuje siatkę z placeholder items.

        Args:
            count: Liczba stron
        """
        self.clear()
        self._page_count = count

        for i in range(count):
            item = QListWidgetItem()
            item.setText(f"Strona {i + 1}")
            item.setData(Qt.ItemDataRole.UserRole, i)  # Oryginalny indeks

            # Placeholder icon
            item.setIcon(self._create_placeholder_icon())

            # Włącz drag
            item.setFlags(
                item.flags() |
                Qt.ItemFlag.ItemIsDragEnabled |
                Qt.ItemFlag.ItemIsSelectable
            )

            self.addItem(item)

    def set_thumbnail(self, page_index: int, png_data: bytes) -> None:
        """
        Ustawia miniaturę dla strony.

        Args:
            page_index: Indeks strony (0-based)
            png_data: Dane PNG
        """
        # Znajdź item po zapisanym indeksie strony
        for i in range(self.count()):
            item = self.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == page_index:
                pixmap = QPixmap()
                pixmap.loadFromData(png_data)
                item.setIcon(QIcon(pixmap))
                break

    def _create_placeholder_icon(self) -> QIcon:
        """Tworzy placeholder icon (szary prostokąt)."""
        pixmap = QPixmap(self.THUMBNAIL_SIZE, self.THUMBNAIL_SIZE)
        pixmap.fill(Qt.GlobalColor.darkGray)
        return QIcon(pixmap)

    def get_selected_indices(self) -> List[int]:
        """Zwraca listę zaznaczonych indeksów stron (oryginalne indeksy)."""
        indices = []
        for item in self.selectedItems():
            idx = item.data(Qt.ItemDataRole.UserRole)
            if idx is not None:
                indices.append(idx)
        return sorted(indices)

    def get_current_order(self) -> List[int]:
        """
        Zwraca aktualną kolejność stron.

        Returns:
            Lista oryginalnych indeksów w obecnej kolejności wyświetlania
        """
        order = []
        for i in range(self.count()):
            item = self.item(i)
            order.append(item.data(Qt.ItemDataRole.UserRole))
        return order

    def _on_selection_changed(self, current_row: int) -> None:
        """Obsługa zmiany zaznaczenia."""
        if current_row >= 0:
            item = self.item(current_row)
            page_index = item.data(Qt.ItemDataRole.UserRole)
            self.selection_changed.emit(page_index)
        else:
            self.selection_changed.emit(-1)

    # === Drag & Drop ===

    def startDrag(self, supportedActions) -> None:
        """Zapamiętaj przeciągany element przed rozpoczęciem drag."""
        self._dragged_item = self.currentItem()
        super().startDrag(supportedActions)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Obsługa wejścia drag."""
        if event.mimeData().hasUrls():
            # Sprawdź czy to pliki PDF
            urls = event.mimeData().urls()
            if any(url.toLocalFile().lower().endswith('.pdf') for url in urls):
                event.acceptProposedAction()
                return
            event.ignore()
            return

        # Wewnętrzny drag & drop - zawsze akceptuj
        event.accept()

    def dragMoveEvent(self, event) -> None:
        """Obsługa ruchu drag."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return

        # Wewnętrzny drag - zawsze akceptuj (wstawianie między elementy)
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        """
        Obsługa drop.

        Obsługuje:
        1. Drop plików PDF z zewnątrz (merge)
        2. Wewnętrzny drag & drop (reorder)
        """
        if event.mimeData().hasUrls():
            # Pliki z zewnątrz
            filepaths = [
                url.toLocalFile() for url in event.mimeData().urls()
                if url.toLocalFile().lower().endswith('.pdf')
            ]

            if filepaths:
                # Znajdź pozycję wstawienia
                drop_pos = event.position().toPoint()
                target_item = self.itemAt(drop_pos)
                insert_pos = self.row(target_item) if target_item else self.count()

                self.files_dropped.emit(filepaths, insert_pos)
                event.acceptProposedAction()
                return

        # Wewnętrzny drag & drop - reorder
        source_item = self._dragged_item
        if not source_item:
            event.ignore()
            return

        source_row = self.row(source_item)
        drop_pos = event.position().toPoint()

        # Oblicz pozycję wstawienia na podstawie współrzędnych
        insert_row = self._calculate_insert_position(drop_pos)

        # Nie rób nic jeśli pozycja się nie zmienia
        if insert_row == source_row or insert_row == source_row + 1:
            event.ignore()
            self._dragged_item = None
            return

        # Oblicz nową kolejność
        current_order = self.get_current_order()
        page_index = current_order.pop(source_row)

        # Dostosuj pozycję wstawienia po usunięciu źródłowego elementu
        if source_row < insert_row:
            insert_row -= 1

        current_order.insert(insert_row, page_index)

        # Emituj nową kolejność - pages_view odświeży widok
        self.order_changed.emit(current_order)
        event.accept()

        # Reset
        self._dragged_item = None

    def _calculate_insert_position(self, pos) -> int:
        """Oblicza pozycję wstawienia na podstawie współrzędnych kursora."""
        if self.count() == 0:
            return 0

        # Znajdź najbliższy element
        min_dist = float('inf')
        closest_idx = 0
        insert_before = True

        for i in range(self.count()):
            item = self.item(i)
            rect = self.visualItemRect(item)
            center = rect.center()

            # Odległość od lewej krawędzi (wstawienie przed)
            left_dist = abs(pos.x() - rect.left()) + abs(pos.y() - center.y())
            # Odległość od prawej krawędzi (wstawienie za)
            right_dist = abs(pos.x() - rect.right()) + abs(pos.y() - center.y())

            if left_dist < min_dist:
                min_dist = left_dist
                closest_idx = i
                insert_before = True

            if right_dist < min_dist:
                min_dist = right_dist
                closest_idx = i
                insert_before = False

        if insert_before:
            return closest_idx
        else:
            return closest_idx + 1

    def _update_page_numbers(self) -> None:
        """Aktualizuje wyświetlane numery stron po reorderingu."""
        for i in range(self.count()):
            item = self.item(i)
            # Wyświetlany numer to pozycja + 1, ale UserRole zachowuje oryginalny indeks
            item.setText(f"Strona {i + 1}")

    # === Keyboard shortcuts ===

    def keyPressEvent(self, event) -> None:
        """Obsługa skrótów klawiszowych."""
        if event.key() == Qt.Key.Key_Delete:
            indices = self.get_selected_indices()
            if indices:
                self.delete_requested.emit(indices)
        elif event.key() == Qt.Key.Key_A and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.selectAll()
        else:
            super().keyPressEvent(event)
