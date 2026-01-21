"""
LinkManagerDialog - Dialog do zarządzania linkami na stronie.

Funkcje:
- Wyświetlanie listy linków
- Dodawanie nowych linków
- Edycja istniejących linków
- Usuwanie linków
"""

from typing import Optional, List, Callable

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt

from pdfdeck.core.models import LinkInfo, LinkConfig, Rect
from pdfdeck.ui.widgets.styled_button import StyledButton
from pdfdeck.ui.dialogs.link_dialog import LinkDialog


class LinkManagerDialog(QDialog):
    """
    Dialog do zarządzania linkami na stronie PDF.

    Pozwala użytkownikowi:
    - Przeglądać wszystkie linki na stronie
    - Dodawać nowe linki
    - Edytować istniejące linki
    - Usuwać linki
    """

    def __init__(
        self,
        links: List[LinkInfo],
        page_index: int,
        max_pages: int,
        on_add: Callable[[LinkConfig], None],
        on_edit: Callable[[int, LinkConfig], None],
        on_delete: Callable[[int], None],
        get_links: Callable[[], List[LinkInfo]],
        parent=None
    ):
        """
        Args:
            links: Lista linków na stronie
            page_index: Indeks bieżącej strony (0-indexed)
            max_pages: Całkowita liczba stron w dokumencie
            on_add: Callback wywoływany przy dodawaniu linku
            on_edit: Callback wywoływany przy edycji (link_index, new_config)
            on_delete: Callback wywoływany przy usuwaniu (link_index)
            get_links: Callback do pobierania aktualnej listy linków
            parent: Widget rodzic
        """
        super().__init__(parent)

        self._links = links
        self._page_index = page_index
        self._max_pages = max_pages
        self._on_add = on_add
        self._on_edit = on_edit
        self._on_delete = on_delete
        self._get_links = get_links

        self.setWindowTitle(f"Zarządzanie linkami - Strona {page_index + 1}")
        self.setMinimumSize(600, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #16213e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QTableWidget {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                color: #ffffff;
                gridline-color: #2d3a50;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #1f4068;
            }
            QHeaderView::section {
                background-color: #1f2940;
                color: #ffffff;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #2d3a50;
                font-weight: bold;
            }
        """)

        self._setup_ui()
        self._populate_table()

    def _setup_ui(self) -> None:
        """Tworzy interfejs użytkownika."""
        layout = QVBoxLayout(self)

        # === Nagłówek ===
        header_label = QLabel(f"Linki na stronie {self._page_index + 1}")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header_label)

        # === Tabela linków ===
        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["Typ", "Cel", "Pozycja"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Rozciągnij kolumny
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        self._table.doubleClicked.connect(self._on_edit_clicked)
        layout.addWidget(self._table)

        # === Info jeśli brak linków ===
        self._empty_label = QLabel("Brak linków na tej stronie")
        self._empty_label.setStyleSheet("color: #8892a0; font-style: italic; padding: 20px;")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setVisible(False)
        layout.addWidget(self._empty_label)

        # === Przyciski akcji ===
        buttons_layout = QHBoxLayout()

        add_btn = StyledButton("Dodaj", "primary")
        add_btn.clicked.connect(self._on_add_clicked)
        buttons_layout.addWidget(add_btn)

        self._edit_btn = StyledButton("Edytuj", "secondary")
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        buttons_layout.addWidget(self._edit_btn)

        self._delete_btn = StyledButton("Usuń", "danger")
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        buttons_layout.addWidget(self._delete_btn)

        buttons_layout.addStretch()

        close_btn = StyledButton("Zamknij", "secondary")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

        # Aktualizuj stan przycisków
        self._update_button_states()
        self._table.itemSelectionChanged.connect(self._update_button_states)

    def _populate_table(self) -> None:
        """Wypełnia tabelę danymi linków."""
        self._table.setRowCount(len(self._links))

        if not self._links:
            self._table.setVisible(False)
            self._empty_label.setVisible(True)
            return

        self._table.setVisible(True)
        self._empty_label.setVisible(False)

        for row, link in enumerate(self._links):
            # Typ
            type_item = QTableWidgetItem(link.type_label)
            type_item.setData(Qt.ItemDataRole.UserRole, link.index)
            self._table.setItem(row, 0, type_item)

            # Cel
            target_item = QTableWidgetItem(link.display_label)
            self._table.setItem(row, 1, target_item)

            # Pozycja
            pos_text = f"({int(link.rect.x0)}, {int(link.rect.y0)})"
            pos_item = QTableWidgetItem(pos_text)
            self._table.setItem(row, 2, pos_item)

    def _refresh_links(self) -> None:
        """Odświeża listę linków z dokumentu."""
        self._links = self._get_links()
        self._populate_table()
        self._update_button_states()

    def _update_button_states(self) -> None:
        """Aktualizuje stan przycisków na podstawie zaznaczenia."""
        has_selection = len(self._table.selectedItems()) > 0
        self._edit_btn.setEnabled(has_selection)
        self._delete_btn.setEnabled(has_selection)

    def _get_selected_link_index(self) -> Optional[int]:
        """Zwraca indeks wybranego linku lub None."""
        selected_rows = self._table.selectionModel().selectedRows()
        if not selected_rows:
            return None

        row = selected_rows[0].row()
        item = self._table.item(row, 0)
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _on_add_clicked(self) -> None:
        """Obsługa kliknięcia 'Dodaj'."""
        # Domyślny prostokąt dla nowego linku (stopka strony A4)
        # PyMuPDF: Y=0 to góra, Y=842 to dół dla A4
        # Y=720 to około 85% wysokości strony (dolna część ale nie na marginesie)
        default_rect = Rect(50, 720, 300, 750)

        config = LinkDialog.get_link_config(
            rect=default_rect,
            max_pages=self._max_pages,
            parent=self
        )

        if config:
            self._on_add(config)
            # Odśwież listę linków
            self._refresh_links()

    def _on_edit_clicked(self) -> None:
        """Obsługa kliknięcia 'Edytuj'."""
        selected_rows = self._table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        if row >= len(self._links):
            return

        link = self._links[row]
        config = LinkDialog.edit_link_config(
            existing_link=link,
            max_pages=self._max_pages,
            parent=self
        )

        if config:
            self._on_edit(link.index, config)
            # Odśwież listę linków
            self._refresh_links()

    def _on_delete_clicked(self) -> None:
        """Obsługa kliknięcia 'Usuń'."""
        link_index = self._get_selected_link_index()
        if link_index is None:
            return

        # Potwierdzenie
        reply = QMessageBox.question(
            self,
            "Potwierdzenie usunięcia",
            "Czy na pewno chcesz usunąć wybrany link?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._on_delete(link_index)
            # Odśwież listę linków
            self._refresh_links()

    @staticmethod
    def manage_links(
        links: List[LinkInfo],
        page_index: int,
        max_pages: int,
        on_add: Callable[[LinkConfig], None],
        on_edit: Callable[[int, LinkConfig], None],
        on_delete: Callable[[int], None],
        get_links: Callable[[], List[LinkInfo]],
        parent=None
    ) -> None:
        """
        Statyczna metoda do zarządzania linkami.

        Args:
            links: Lista linków na stronie
            page_index: Indeks bieżącej strony
            max_pages: Całkowita liczba stron
            on_add: Callback dla dodawania
            on_edit: Callback dla edycji
            on_delete: Callback dla usuwania
            get_links: Callback do pobierania aktualnej listy linków
            parent: Widget rodzic
        """
        dialog = LinkManagerDialog(
            links=links,
            page_index=page_index,
            max_pages=max_pages,
            on_add=on_add,
            on_edit=on_edit,
            on_delete=on_delete,
            get_links=get_links,
            parent=parent
        )
        dialog.exec()
