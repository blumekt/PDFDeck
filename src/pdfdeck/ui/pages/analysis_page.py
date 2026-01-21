"""
AnalysisPage - Strona analizy dokumentu.

Funkcje:
- Preflight Check (wykrywanie problemów)
- Table Sniffer (ekstrakcja tabel)
- Visual Diff (porównywanie dokumentów)
"""

from typing import TYPE_CHECKING, List
from pathlib import Path
import csv
import io

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QListWidget, QListWidgetItem, QFileDialog,
    QSplitter, QTabWidget, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage

from pdfdeck.ui.pages.base_page import BasePage
from pdfdeck.ui.widgets.styled_button import StyledButton
from pdfdeck.ui.widgets.styled_combo import StyledComboBox
from pdfdeck.core.diff_engine import DiffEngine
from pdfdeck.core.invoice_parser import InvoiceParser, InvoiceData

if TYPE_CHECKING:
    from pdfdeck.core.pdf_manager import PDFManager


class AnalysisPage(BasePage):
    """
    Strona analizy dokumentu.

    Układ:
    +------------------------------------------+
    |  Tytuł: Analiza                          |
    +------------------------------------------+
    |  +------------------+  +---------------+ |
    |  | Preflight        |  | Table Sniffer | |
    |  | [!] Pusta str 3  |  | Strona: [v]   | |
    |  | [i] Link str 5   |  | [Tabela 1]    | |
    |  +------------------+  | [Eksportuj]   | |
    |                        +---------------+ |
    +------------------------------------------+
    """

    def __init__(self, pdf_manager: "PDFManager", parent=None):
        super().__init__("Analiza", parent)

        self._pdf_manager = pdf_manager
        self._current_tables: List = []
        self._diff_engine = DiffEngine()
        self._invoice_parser = InvoiceParser()
        self._diff_path_a: Path = None
        self._diff_path_b: Path = None
        self._invoice_results: List = []
        self._setup_analysis_ui()

    def _setup_analysis_ui(self) -> None:
        """Tworzy interfejs analizy."""
        # Tabs dla różnych narzędzi
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #2d3a50;
                border-radius: 4px;
                background-color: #16213e;
            }
            QTabBar::tab {
                background-color: #1f2940;
                color: #8892a0;
                padding: 10px 20px;
                border: 1px solid #2d3a50;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #16213e;
                color: #e0a800;
            }
            QTabBar::tab:hover {
                color: #ffffff;
            }
        """)

        # Tab 1: Preflight & Tables
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout(analysis_tab)
        analysis_layout.setContentsMargins(10, 10, 10, 10)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #2d3a50;
                width: 2px;
            }
            QSplitter::handle:hover {
                background-color: #e0a800;
            }
        """)

        # === Lewa strona: Preflight Check ===
        preflight_group = QGroupBox("Preflight Check")
        preflight_group.setStyleSheet(self._group_style())
        preflight_layout = QVBoxLayout(preflight_group)

        preflight_desc = QLabel(
            "Wykrywa potencjalne problemy:\n"
            "• Puste strony\n"
            "• Obrazki niskiej rozdzielczości\n"
            "• Uszkodzone linki"
        )
        preflight_desc.setStyleSheet("color: #8892a0; font-size: 13px;")
        preflight_layout.addWidget(preflight_desc)

        self._preflight_btn = StyledButton("Uruchom Preflight", "primary")
        self._preflight_btn.clicked.connect(self._on_preflight)
        preflight_layout.addWidget(self._preflight_btn)

        # Lista problemów
        self._issues_list = QListWidget()
        self._issues_list.setStyleSheet("""
            QListWidget {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 6px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #2d3a50;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #1f2940;
            }
        """)
        preflight_layout.addWidget(self._issues_list, 1)

        splitter.addWidget(preflight_group)

        # === Prawa strona: Table Sniffer ===
        tables_group = QGroupBox("Table Sniffer")
        tables_group.setStyleSheet(self._group_style())
        tables_layout = QVBoxLayout(tables_group)

        tables_desc = QLabel(
            "Ekstrahuje tabele z dokumentu.\n"
            "Eksportuj do CSV lub kopiuj do Excela."
        )
        tables_desc.setStyleSheet("color: #8892a0; font-size: 13px;")
        tables_layout.addWidget(tables_desc)

        # Wybór strony
        page_row = QHBoxLayout()
        page_label = QLabel("Strona:")
        page_label.setStyleSheet("color: #8892a0;")
        page_row.addWidget(page_label)

        self._page_combo = StyledComboBox()
        self._page_combo.currentIndexChanged.connect(self._on_page_selected)
        page_row.addWidget(self._page_combo)
        page_row.addStretch()
        tables_layout.addLayout(page_row)

        # Przyciski
        btn_row = QHBoxLayout()
        self._find_tables_btn = StyledButton("Znajdź tabele", "primary")
        self._find_tables_btn.clicked.connect(self._on_find_tables)
        btn_row.addWidget(self._find_tables_btn)

        self._export_btn = StyledButton("Eksportuj CSV", "secondary")
        self._export_btn.clicked.connect(self._on_export_table)
        self._export_btn.setEnabled(False)
        btn_row.addWidget(self._export_btn)
        tables_layout.addLayout(btn_row)

        # Lista tabel
        tables_label = QLabel("Znalezione tabele:")
        tables_label.setStyleSheet("color: #8892a0; font-size: 13px;")
        tables_layout.addWidget(tables_label)

        self._tables_list = QListWidget()
        self._tables_list.setStyleSheet("""
            QListWidget {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 6px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #2d3a50;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #e0a800;
                color: #1a1a2e;
            }
        """)
        self._tables_list.currentRowChanged.connect(self._on_table_selected)
        tables_layout.addWidget(self._tables_list)

        # Podgląd tabeli
        preview_label = QLabel("Podgląd:")
        preview_label.setStyleSheet("color: #8892a0; font-size: 13px;")
        tables_layout.addWidget(preview_label)

        self._table_preview = QTableWidget()
        self._table_preview.setStyleSheet("""
            QTableWidget {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 6px;
                gridline-color: #2d3a50;
            }
            QTableWidget::item {
                padding: 5px;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #1f2940;
                color: #8892a0;
                padding: 5px;
                border: none;
            }
        """)
        self._table_preview.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tables_layout.addWidget(self._table_preview, 1)

        splitter.addWidget(tables_group)
        splitter.setSizes([400, 600])

        analysis_layout.addWidget(splitter)
        tabs.addTab(analysis_tab, "Preflight & Tabele")

        # Tab 2: Visual Diff
        diff_tab = self._create_diff_tab()
        tabs.addTab(diff_tab, "Visual Diff")

        # Tab 3: Invoice Parser
        invoice_tab = self._create_invoice_tab()
        tabs.addTab(invoice_tab, "Parser faktur")

        self.add_widget(tabs)

    def _create_diff_tab(self) -> QWidget:
        """Tworzy zakładkę Visual Diff."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Opis
        desc = QLabel(
            "Porównaj dwa dokumenty PDF i zobacz różnice.\n"
            "Różnice są wyświetlane w kolorach: czerwony (dokument A) i niebieski (dokument B)."
        )
        desc.setStyleSheet("color: #8892a0; font-size: 13px; margin-bottom: 10px;")
        layout.addWidget(desc)

        # Wybór plików
        files_layout = QHBoxLayout()

        # Dokument A
        doc_a_layout = QVBoxLayout()
        doc_a_label = QLabel("Dokument A (oryginał):")
        doc_a_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        doc_a_layout.addWidget(doc_a_label)

        doc_a_row = QHBoxLayout()
        self._diff_file_a_label = QLabel("Nie wybrano")
        self._diff_file_a_label.setStyleSheet(
            "color: #8892a0; background-color: #0f1629; "
            "padding: 8px; border-radius: 4px;"
        )
        doc_a_row.addWidget(self._diff_file_a_label, 1)

        self._diff_file_a_btn = StyledButton("Wybierz...", "secondary")
        self._diff_file_a_btn.clicked.connect(self._on_select_diff_file_a)
        doc_a_row.addWidget(self._diff_file_a_btn)
        doc_a_layout.addLayout(doc_a_row)

        self._use_current_a_btn = StyledButton("Użyj aktualnego dokumentu", "secondary")
        self._use_current_a_btn.clicked.connect(self._on_use_current_as_a)
        doc_a_layout.addWidget(self._use_current_a_btn)

        files_layout.addLayout(doc_a_layout)

        # Separator
        separator = QLabel("vs")
        separator.setStyleSheet("color: #e0a800; font-size: 18px; font-weight: bold;")
        separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        separator.setFixedWidth(50)
        files_layout.addWidget(separator)

        # Dokument B
        doc_b_layout = QVBoxLayout()
        doc_b_label = QLabel("Dokument B (nowy):")
        doc_b_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        doc_b_layout.addWidget(doc_b_label)

        doc_b_row = QHBoxLayout()
        self._diff_file_b_label = QLabel("Nie wybrano")
        self._diff_file_b_label.setStyleSheet(
            "color: #8892a0; background-color: #0f1629; "
            "padding: 8px; border-radius: 4px;"
        )
        doc_b_row.addWidget(self._diff_file_b_label, 1)

        self._diff_file_b_btn = StyledButton("Wybierz...", "secondary")
        self._diff_file_b_btn.clicked.connect(self._on_select_diff_file_b)
        doc_b_row.addWidget(self._diff_file_b_btn)
        doc_b_layout.addLayout(doc_b_row)

        files_layout.addLayout(doc_b_layout)

        layout.addLayout(files_layout)

        # Przyciski akcji
        actions_row = QHBoxLayout()

        self._compare_btn = StyledButton("Porównaj dokumenty", "primary")
        self._compare_btn.clicked.connect(self._on_compare_documents)
        actions_row.addWidget(self._compare_btn)

        actions_row.addStretch()

        # Nawigacja stron
        self._diff_prev_btn = StyledButton("◀ Poprzednia", "secondary")
        self._diff_prev_btn.clicked.connect(self._on_diff_prev_page)
        self._diff_prev_btn.setEnabled(False)
        actions_row.addWidget(self._diff_prev_btn)

        self._diff_page_label = QLabel("Strona: -/-")
        self._diff_page_label.setStyleSheet("color: #8892a0; padding: 0 10px;")
        actions_row.addWidget(self._diff_page_label)

        self._diff_next_btn = StyledButton("Następna ▶", "secondary")
        self._diff_next_btn.clicked.connect(self._on_diff_next_page)
        self._diff_next_btn.setEnabled(False)
        actions_row.addWidget(self._diff_next_btn)

        layout.addLayout(actions_row)

        # Status
        self._diff_status_label = QLabel("")
        self._diff_status_label.setStyleSheet("color: #8892a0; font-size: 13px;")
        layout.addWidget(self._diff_status_label)

        # Podgląd różnic
        preview_splitter = QSplitter(Qt.Orientation.Horizontal)
        preview_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #2d3a50;
                width: 2px;
            }
        """)

        # Podgląd A
        self._diff_preview_a = self._create_diff_preview("Dokument A")
        preview_splitter.addWidget(self._diff_preview_a)

        # Podgląd różnic (środek)
        self._diff_preview_result = self._create_diff_preview("Różnice")
        preview_splitter.addWidget(self._diff_preview_result)

        # Podgląd B
        self._diff_preview_b = self._create_diff_preview("Dokument B")
        preview_splitter.addWidget(self._diff_preview_b)

        preview_splitter.setSizes([250, 500, 250])

        layout.addWidget(preview_splitter, 1)

        # Zmienne stanu
        self._diff_current_page = 0
        self._diff_max_pages = 0

        return tab

    def _create_diff_preview(self, title: str) -> QGroupBox:
        """Tworzy grupę z podglądem dla diff."""
        group = QGroupBox(title)
        group.setStyleSheet(self._group_style())
        layout = QVBoxLayout(group)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #0f1629;
            }
        """)

        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setStyleSheet("background-color: #0f1629;")
        scroll.setWidget(image_label)

        layout.addWidget(scroll)

        # Zapisz referencję
        group.image_label = image_label

        return group

    def _create_invoice_tab(self) -> QWidget:
        """Tworzy zakładkę parsera faktur."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Opis
        desc = QLabel(
            "Automatyczna ekstrakcja danych z polskich faktur PDF.\n"
            "Rozpoznawane pola: NIP, kwoty, daty, dane sprzedawcy i nabywcy."
        )
        desc.setStyleSheet("color: #8892a0; font-size: 13px; margin-bottom: 10px;")
        layout.addWidget(desc)

        # Przyciski
        btn_row = QHBoxLayout()

        self._parse_current_btn = StyledButton("Parsuj aktualny dokument", "primary")
        self._parse_current_btn.clicked.connect(self._on_parse_current_invoice)
        btn_row.addWidget(self._parse_current_btn)

        self._parse_batch_btn = StyledButton("Batch - wiele faktur", "secondary")
        self._parse_batch_btn.clicked.connect(self._on_parse_batch_invoices)
        btn_row.addWidget(self._parse_batch_btn)

        btn_row.addStretch()

        self._export_invoice_btn = StyledButton("Eksportuj CSV", "secondary")
        self._export_invoice_btn.clicked.connect(self._on_export_invoices)
        self._export_invoice_btn.setEnabled(False)
        btn_row.addWidget(self._export_invoice_btn)

        layout.addLayout(btn_row)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #2d3a50;
                width: 2px;
            }
        """)

        # Lista faktur
        list_group = QGroupBox("Przetworzone faktury")
        list_group.setStyleSheet(self._group_style())
        list_layout = QVBoxLayout(list_group)

        self._invoice_list = QListWidget()
        self._invoice_list.setStyleSheet("""
            QListWidget {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 6px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #2d3a50;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #e0a800;
                color: #1a1a2e;
            }
        """)
        self._invoice_list.currentRowChanged.connect(self._on_invoice_selected)
        list_layout.addWidget(self._invoice_list)

        splitter.addWidget(list_group)

        # Szczegóły faktury
        details_group = QGroupBox("Szczegóły faktury")
        details_group.setStyleSheet(self._group_style())
        details_layout = QVBoxLayout(details_group)

        # Tabela z danymi
        self._invoice_table = QTableWidget()
        self._invoice_table.setColumnCount(2)
        self._invoice_table.setHorizontalHeaderLabels(["Pole", "Wartość"])
        self._invoice_table.setStyleSheet("""
            QTableWidget {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 6px;
                gridline-color: #2d3a50;
            }
            QTableWidget::item {
                padding: 8px;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #1f2940;
                color: #8892a0;
                padding: 8px;
                border: none;
            }
        """)
        self._invoice_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._invoice_table.horizontalHeader().setStretchLastSection(True)
        self._invoice_table.verticalHeader().setVisible(False)
        details_layout.addWidget(self._invoice_table)

        # Ostrzeżenia
        self._invoice_warnings = QLabel()
        self._invoice_warnings.setStyleSheet(
            "color: #f39c12; font-size: 12px; padding: 5px;"
        )
        self._invoice_warnings.setWordWrap(True)
        details_layout.addWidget(self._invoice_warnings)

        splitter.addWidget(details_group)
        splitter.setSizes([300, 500])

        layout.addWidget(splitter, 1)

        return tab

    def _on_parse_current_invoice(self) -> None:
        """Parsuje aktualnie otwarty dokument jako fakturę."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(self, "Błąd", "Najpierw otwórz dokument PDF")
            return

        try:
            filepath = Path(self._pdf_manager._filepath)
            result = self._invoice_parser.parse(filepath)

            self._invoice_results = [result]
            self._update_invoice_list()

            if result.success:
                self._invoice_list.setCurrentRow(0)

                if result.warnings:
                    QMessageBox.warning(
                        self, "Uwagi",
                        "Parsowanie zakończone z uwagami:\n\n" +
                        "\n".join(f"• {w}" for w in result.warnings)
                    )
            else:
                QMessageBox.critical(
                    self, "Błąd",
                    "Nie udało się sparsować faktury:\n\n" +
                    "\n".join(result.errors)
                )

        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd parsowania:\n{e}")

    def _on_parse_batch_invoices(self) -> None:
        """Parsuje wiele faktur."""
        filepaths, _ = QFileDialog.getOpenFileNames(
            self,
            "Wybierz faktury PDF",
            "",
            "Pliki PDF (*.pdf)"
        )

        if not filepaths:
            return

        try:
            pdf_paths = [Path(f) for f in filepaths]
            results = self._invoice_parser.batch_parse(pdf_paths)

            self._invoice_results = results
            self._update_invoice_list()

            # Statystyki
            success_count = sum(1 for r in results if r.success)
            fail_count = len(results) - success_count

            QMessageBox.information(
                self, "Batch zakończony",
                f"Przetworzono {len(results)} faktur:\n"
                f"• Sukces: {success_count}\n"
                f"• Błędy: {fail_count}"
            )

            self._export_invoice_btn.setEnabled(success_count > 0)

            if results:
                self._invoice_list.setCurrentRow(0)

        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd batch:\n{e}")

    def _update_invoice_list(self) -> None:
        """Aktualizuje listę faktur."""
        self._invoice_list.clear()

        for result in self._invoice_results:
            if result.success and result.data:
                data = result.data
                confidence_icon = "✓" if data.confidence >= 70 else "⚠" if data.confidence >= 40 else "?"

                text = (
                    f"{confidence_icon} {data.invoice_number or 'Brak numeru'} | "
                    f"{data.gross_amount:.2f} {data.currency} | "
                    f"{data.issue_date or 'Brak daty'}"
                )
                item = QListWidgetItem(text)

                if data.confidence >= 70:
                    item.setForeground(Qt.GlobalColor.green)
                elif data.confidence >= 40:
                    item.setForeground(Qt.GlobalColor.yellow)
                else:
                    item.setForeground(Qt.GlobalColor.red)
            else:
                text = f"❌ {result.errors[0] if result.errors else 'Błąd'}"
                item = QListWidgetItem(text)
                item.setForeground(Qt.GlobalColor.red)

            self._invoice_list.addItem(item)

    def _on_invoice_selected(self, row: int) -> None:
        """Obsługa wyboru faktury."""
        if row < 0 or row >= len(self._invoice_results):
            self._invoice_table.setRowCount(0)
            self._invoice_warnings.clear()
            return

        result = self._invoice_results[row]

        if not result.success or not result.data:
            self._invoice_table.setRowCount(1)
            self._invoice_table.setItem(0, 0, QTableWidgetItem("Błąd"))
            self._invoice_table.setItem(
                0, 1, QTableWidgetItem(result.errors[0] if result.errors else "Nieznany błąd")
            )
            self._invoice_warnings.clear()
            return

        data = result.data

        # Wypełnij tabelę
        fields = [
            ("Numer faktury", data.invoice_number),
            ("Data wystawienia", data.issue_date),
            ("Data sprzedaży", data.sale_date),
            ("Termin płatności", data.due_date),
            ("", ""),  # separator
            ("NIP sprzedawcy", data.seller_nip),
            ("Sprzedawca", data.seller_name),
            ("NIP nabywcy", data.buyer_nip),
            ("Nabywca", data.buyer_name),
            ("", ""),  # separator
            ("Kwota netto", f"{data.net_amount:.2f} {data.currency}"),
            ("Kwota VAT", f"{data.vat_amount:.2f} {data.currency}"),
            ("Kwota brutto", f"{data.gross_amount:.2f} {data.currency}"),
            ("", ""),  # separator
            ("Metoda płatności", data.payment_method),
            ("Konto bankowe", data.seller_bank_account),
            ("", ""),  # separator
            ("Pewność ekstrakcji", f"{data.confidence:.1f}%"),
            ("Plik źródłowy", data.source_file),
        ]

        self._invoice_table.setRowCount(len(fields))

        for i, (field, value) in enumerate(fields):
            field_item = QTableWidgetItem(field)
            field_item.setForeground(Qt.GlobalColor.gray)
            self._invoice_table.setItem(i, 0, field_item)

            value_item = QTableWidgetItem(str(value) if value else "-")
            self._invoice_table.setItem(i, 1, value_item)

        self._invoice_table.resizeColumnToContents(0)

        # Ostrzeżenia
        if result.warnings:
            self._invoice_warnings.setText(
                "Uwagi:\n" + "\n".join(f"• {w}" for w in result.warnings)
            )
        else:
            self._invoice_warnings.clear()

    def _on_export_invoices(self) -> None:
        """Eksportuje faktury do CSV."""
        if not self._invoice_results:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz jako CSV",
            "faktury.csv",
            "Pliki CSV (*.csv)"
        )

        if filepath:
            try:
                self._invoice_parser.export_batch_csv(
                    self._invoice_results,
                    Path(filepath)
                )

                QMessageBox.information(
                    self, "Sukces",
                    f"Faktury wyeksportowane:\n{filepath}"
                )

            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Błąd eksportu:\n{e}")

    def _on_select_diff_file_a(self) -> None:
        """Wybór dokumentu A do porównania."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz dokument A",
            "",
            "Pliki PDF (*.pdf)"
        )
        if filepath:
            self._diff_path_a = Path(filepath)
            self._diff_file_a_label.setText(Path(filepath).name)
            self._diff_file_a_label.setStyleSheet(
                "color: #ffffff; background-color: #0f1629; "
                "padding: 8px; border-radius: 4px;"
            )

    def _on_select_diff_file_b(self) -> None:
        """Wybór dokumentu B do porównania."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz dokument B",
            "",
            "Pliki PDF (*.pdf)"
        )
        if filepath:
            self._diff_path_b = Path(filepath)
            self._diff_file_b_label.setText(Path(filepath).name)
            self._diff_file_b_label.setStyleSheet(
                "color: #ffffff; background-color: #0f1629; "
                "padding: 8px; border-radius: 4px;"
            )

    def _on_use_current_as_a(self) -> None:
        """Użyj aktualnie otwartego dokumentu jako A."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(self, "Błąd", "Najpierw otwórz dokument PDF")
            return

        self._diff_path_a = self._pdf_manager.filepath
        self._diff_file_a_label.setText(self._diff_path_a.name)
        self._diff_file_a_label.setStyleSheet(
            "color: #ffffff; background-color: #0f1629; "
            "padding: 8px; border-radius: 4px;"
        )

    def _on_compare_documents(self) -> None:
        """Porównuje dwa dokumenty."""
        if not self._diff_path_a or not self._diff_path_b:
            QMessageBox.warning(
                self, "Błąd",
                "Wybierz oba dokumenty do porównania"
            )
            return

        try:
            pages_a, pages_b = self._diff_engine.load_documents(
                self._diff_path_a, self._diff_path_b
            )

            self._diff_max_pages = max(pages_a, pages_b)
            self._diff_current_page = 0

            self._diff_status_label.setText(
                f"Załadowano: A={pages_a} stron, B={pages_b} stron"
            )

            self._update_diff_navigation()
            self._show_diff_page(0)

        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd podczas porównywania:\n{e}")

    def _show_diff_page(self, page_index: int) -> None:
        """Wyświetla porównanie strony."""
        if page_index < 0 or page_index >= self._diff_max_pages:
            return

        # Renderuj strony osobno dla podglądu
        try:
            # Strona A
            if page_index < self._diff_engine.page_count_a:
                pix_a = self._diff_engine._doc_a[page_index].get_pixmap(dpi=100)
                img_a = QImage(
                    pix_a.samples, pix_a.width, pix_a.height,
                    pix_a.stride, QImage.Format.Format_RGB888
                )
                self._diff_preview_a.image_label.setPixmap(
                    QPixmap.fromImage(img_a).scaled(
                        300, 400,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )
            else:
                self._diff_preview_a.image_label.setText("Brak strony")

            # Strona B
            if page_index < self._diff_engine.page_count_b:
                pix_b = self._diff_engine._doc_b[page_index].get_pixmap(dpi=100)
                img_b = QImage(
                    pix_b.samples, pix_b.width, pix_b.height,
                    pix_b.stride, QImage.Format.Format_RGB888
                )
                self._diff_preview_b.image_label.setPixmap(
                    QPixmap.fromImage(img_b).scaled(
                        300, 400,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )
            else:
                self._diff_preview_b.image_label.setText("Brak strony")

            # Porównanie
            result = self._diff_engine.compare_page(page_index)
            if result and result.diff_image:
                pixmap = QPixmap()
                pixmap.loadFromData(result.diff_image)
                self._diff_preview_result.image_label.setPixmap(
                    pixmap.scaled(
                        400, 500,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )

                # Status
                if result.has_differences:
                    self._diff_status_label.setText(
                        f"Strona {page_index + 1}: RÓŻNICE wykryte "
                        f"(podobieństwo: {result.similarity_percent:.1f}%)"
                    )
                    self._diff_status_label.setStyleSheet(
                        "color: #e74c3c; font-weight: bold;"
                    )
                else:
                    self._diff_status_label.setText(
                        f"Strona {page_index + 1}: Brak różnic "
                        f"(podobieństwo: {result.similarity_percent:.1f}%)"
                    )
                    self._diff_status_label.setStyleSheet(
                        "color: #27ae60; font-weight: bold;"
                    )

        except Exception as e:
            self._diff_status_label.setText(f"Błąd: {e}")
            self._diff_status_label.setStyleSheet("color: #e74c3c;")

    def _on_diff_prev_page(self) -> None:
        """Poprzednia strona diff."""
        if self._diff_current_page > 0:
            self._diff_current_page -= 1
            self._show_diff_page(self._diff_current_page)
            self._update_diff_navigation()

    def _on_diff_next_page(self) -> None:
        """Następna strona diff."""
        if self._diff_current_page < self._diff_max_pages - 1:
            self._diff_current_page += 1
            self._show_diff_page(self._diff_current_page)
            self._update_diff_navigation()

    def _update_diff_navigation(self) -> None:
        """Aktualizuje nawigację diff."""
        self._diff_prev_btn.setEnabled(self._diff_current_page > 0)
        self._diff_next_btn.setEnabled(
            self._diff_current_page < self._diff_max_pages - 1
        )
        self._diff_page_label.setText(
            f"Strona: {self._diff_current_page + 1}/{self._diff_max_pages}"
        )

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

    def _on_preflight(self) -> None:
        """Uruchamia preflight check."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(self, "Błąd", "Najpierw otwórz dokument PDF")
            return

        self._issues_list.clear()

        try:
            issues = self._pdf_manager.preflight_check()

            if not issues:
                item = QListWidgetItem("✓ Nie znaleziono problemów")
                item.setForeground(Qt.GlobalColor.green)
                self._issues_list.addItem(item)
            else:
                for issue in issues:
                    # Ikona według severity
                    if issue.severity == "error":
                        icon = "❌"
                        color = Qt.GlobalColor.red
                    elif issue.severity == "warning":
                        icon = "⚠️"
                        color = Qt.GlobalColor.yellow
                    else:
                        icon = "ℹ️"
                        color = Qt.GlobalColor.cyan

                    item = QListWidgetItem(f"{icon} {issue.description}")
                    item.setForeground(color)
                    self._issues_list.addItem(item)

        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd podczas analizy:\n{e}")

    def _on_page_selected(self, index: int) -> None:
        """Obsługa wyboru strony."""
        self._tables_list.clear()
        self._table_preview.clear()
        self._table_preview.setRowCount(0)
        self._table_preview.setColumnCount(0)
        self._current_tables = []
        self._export_btn.setEnabled(False)

    def _on_find_tables(self) -> None:
        """Wyszukuje tabele na wybranej stronie."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(self, "Błąd", "Najpierw otwórz dokument PDF")
            return

        page_idx = self._page_combo.currentIndex()
        if page_idx < 0:
            return

        self._tables_list.clear()
        self._table_preview.clear()
        self._table_preview.setRowCount(0)
        self._table_preview.setColumnCount(0)

        try:
            self._current_tables = self._pdf_manager.extract_tables(page_idx)

            if not self._current_tables:
                item = QListWidgetItem("Nie znaleziono tabel")
                self._tables_list.addItem(item)
            else:
                for i, table in enumerate(self._current_tables):
                    item = QListWidgetItem(f"Tabela {i + 1}: {table.rows}x{table.cols}")
                    self._tables_list.addItem(item)

        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd podczas wyszukiwania tabel:\n{e}")

    def _on_table_selected(self, row: int) -> None:
        """Obsługa wyboru tabeli."""
        if row < 0 or row >= len(self._current_tables):
            self._export_btn.setEnabled(False)
            return

        table = self._current_tables[row]
        self._export_btn.setEnabled(True)

        # Wyświetl podgląd
        self._table_preview.setRowCount(table.rows)
        self._table_preview.setColumnCount(table.cols)

        for r, row_data in enumerate(table.data):
            for c, cell in enumerate(row_data):
                item = QTableWidgetItem(str(cell) if cell else "")
                self._table_preview.setItem(r, c, item)

        self._table_preview.resizeColumnsToContents()

    def _on_export_table(self) -> None:
        """Eksportuje wybraną tabelę do CSV."""
        row = self._tables_list.currentRow()
        if row < 0 or row >= len(self._current_tables):
            return

        table = self._current_tables[row]

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz tabelę jako CSV",
            f"tabela_{row + 1}.csv",
            "Pliki CSV (*.csv)"
        )

        if filepath:
            try:
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    for row_data in table.data:
                        writer.writerow(row_data)

                QMessageBox.information(
                    self,
                    "Sukces",
                    f"Tabela zapisana:\n{filepath}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Błąd podczas zapisu:\n{e}")

    # === Public API ===

    def on_document_loaded(self) -> None:
        """Wywoływane po załadowaniu dokumentu."""
        self._issues_list.clear()
        self._tables_list.clear()
        self._table_preview.clear()
        self._table_preview.setRowCount(0)
        self._table_preview.setColumnCount(0)
        self._current_tables = []

        # Aktualizuj listę stron
        self._page_combo.clear()
        if self._pdf_manager.is_loaded:
            for i in range(self._pdf_manager.page_count):
                self._page_combo.addItem(f"Strona {i + 1}", i)
