"""
AutomationPage - Strona automatyzacji.

Funkcje:
- Smart Bookmarks (automatyczne zakładki)
- Informacje o nagłówkach
"""

from typing import TYPE_CHECKING, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QHeaderView
)
from PyQt6.QtCore import Qt

from pdfdeck.ui.pages.base_page import BasePage
from pdfdeck.ui.widgets.styled_button import StyledButton
from pdfdeck.core.document_classifier import DocumentClassifier, ClassificationResult

if TYPE_CHECKING:
    from pdfdeck.core.pdf_manager import PDFManager


class AutomationPage(BasePage):
    """
    Strona automatyzacji.

    Układ:
    +------------------------------------------+
    |  Tytuł: Automatyzacja                    |
    +------------------------------------------+
    |  +------------------+  +---------------+ |
    |  | Smart Bookmarks  |  | Podgląd       | |
    |  | [Wykryj nagl.]   |  | - Rozdział 1  | |
    |  | [Generuj TOC]    |  |   - Sekcja 1  | |
    |  +------------------+  |   - Sekcja 2  | |
    |                        +---------------+ |
    +------------------------------------------+
    """

    def __init__(self, pdf_manager: "PDFManager", parent=None):
        super().__init__("Automatyzacja", parent)

        self._pdf_manager = pdf_manager
        self._headings: List = []
        self._classifier = DocumentClassifier()
        self._classification_result: ClassificationResult = None
        self._setup_automation_ui()

    def _setup_automation_ui(self) -> None:
        """Tworzy interfejs automatyzacji."""
        # Main layout
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        # === Lewa strona: Akcje ===
        actions_widget = QWidget()
        actions_layout = QVBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)

        # --- Smart Bookmarks ---
        bookmarks_group = QGroupBox("Smart Bookmarks")
        bookmarks_group.setStyleSheet(self._group_style())
        bookmarks_layout = QVBoxLayout(bookmarks_group)

        bookmarks_desc = QLabel(
            "Automatycznie generuje spis treści\n"
            "na podstawie wykrytych nagłówków.\n\n"
            "Algorytm analizuje wielkość czcionki,\n"
            "aby określić hierarchię nagłówków:\n"
            "• 24pt+ → Poziom 1\n"
            "• 18-24pt → Poziom 2\n"
            "• 14-18pt → Poziom 3"
        )
        bookmarks_desc.setStyleSheet("color: #8892a0; font-size: 13px;")
        bookmarks_layout.addWidget(bookmarks_desc)

        # Przycisk wykryj
        self._detect_btn = StyledButton("Wykryj nagłówki", "primary")
        self._detect_btn.clicked.connect(self._on_detect_headings)
        bookmarks_layout.addWidget(self._detect_btn)

        # Przycisk generuj
        self._generate_btn = StyledButton("Generuj zakładki", "primary")
        self._generate_btn.clicked.connect(self._on_generate_bookmarks)
        self._generate_btn.setEnabled(False)
        bookmarks_layout.addWidget(self._generate_btn)

        actions_layout.addWidget(bookmarks_group)

        # --- Statystyki ---
        stats_group = QGroupBox("Statystyki dokumentu")
        stats_group.setStyleSheet(self._group_style())
        stats_layout = QVBoxLayout(stats_group)

        self._stats_label = QLabel("Załaduj dokument, aby zobaczyć statystyki.")
        self._stats_label.setStyleSheet("color: #8892a0; font-size: 13px;")
        self._stats_label.setWordWrap(True)
        stats_layout.addWidget(self._stats_label)

        actions_layout.addWidget(stats_group)

        # --- Document Classifier ---
        classifier_group = QGroupBox("Klasyfikator dokumentów")
        classifier_group.setStyleSheet(self._group_style())
        classifier_layout = QVBoxLayout(classifier_group)

        classifier_desc = QLabel(
            "Automatycznie rozpoznaje typ dokumentu\n"
            "i sugeruje nazwę pliku.\n\n"
            "Kategorie: faktura, umowa, CV, raport,\n"
            "pismo urzędowe, oferta, inne"
        )
        classifier_desc.setStyleSheet("color: #8892a0; font-size: 13px;")
        classifier_layout.addWidget(classifier_desc)

        self._classify_btn = StyledButton("Klasyfikuj dokument", "primary")
        self._classify_btn.clicked.connect(self._on_classify_document)
        classifier_layout.addWidget(self._classify_btn)

        # Wynik klasyfikacji
        self._classification_label = QLabel("")
        self._classification_label.setStyleSheet(
            "color: #e0a800; font-size: 12px; "
            "background-color: #0f1629; padding: 10px; border-radius: 4px;"
        )
        self._classification_label.setWordWrap(True)
        self._classification_label.setVisible(False)
        classifier_layout.addWidget(self._classification_label)

        # Sugerowana nazwa
        self._suggested_name_label = QLabel("")
        self._suggested_name_label.setStyleSheet(
            "color: #8892a0; font-size: 11px;"
        )
        self._suggested_name_label.setWordWrap(True)
        self._suggested_name_label.setVisible(False)
        classifier_layout.addWidget(self._suggested_name_label)

        # Tagi
        self._tags_label = QLabel("")
        self._tags_label.setStyleSheet(
            "color: #27ae60; font-size: 11px;"
        )
        self._tags_label.setWordWrap(True)
        self._tags_label.setVisible(False)
        classifier_layout.addWidget(self._tags_label)

        actions_layout.addWidget(classifier_group)
        actions_layout.addStretch()

        main_layout.addWidget(actions_widget)

        # === Prawa strona: Podgląd nagłówków ===
        preview_group = QGroupBox("Wykryte nagłówki")
        preview_group.setStyleSheet(self._group_style())
        preview_layout = QVBoxLayout(preview_group)

        self._headings_tree = QTreeWidget()
        self._headings_tree.setHeaderLabels(["Nagłówek", "Strona", "Rozmiar"])
        self._headings_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 6px;
            }
            QTreeWidget::item {
                padding: 8px;
                color: #ffffff;
            }
            QTreeWidget::item:selected {
                background-color: #e0a800;
                color: #1a1a2e;
            }
            QHeaderView::section {
                background-color: #1f2940;
                color: #8892a0;
                padding: 8px;
                border: none;
            }
        """)
        self._headings_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        preview_layout.addWidget(self._headings_tree)

        main_layout.addWidget(preview_group, 1)

        self.add_widget(main_widget)

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

    def _on_detect_headings(self) -> None:
        """Wykrywa nagłówki w dokumencie."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(self, "Błąd", "Najpierw otwórz dokument PDF")
            return

        self._headings_tree.clear()

        try:
            self._headings = self._pdf_manager.detect_headings()

            if not self._headings:
                item = QTreeWidgetItem(["Nie wykryto nagłówków", "", ""])
                self._headings_tree.addTopLevelItem(item)
                self._generate_btn.setEnabled(False)
            else:
                # Buduj drzewo hierarchii
                level_items = {}

                for heading in self._headings:
                    item = QTreeWidgetItem([
                        heading.text[:80] + "..." if len(heading.text) > 80 else heading.text,
                        str(heading.page_index + 1),
                        f"{heading.font_size:.1f}pt"
                    ])

                    # Znajdź rodzica
                    parent = None
                    for lvl in range(heading.level - 1, 0, -1):
                        if lvl in level_items:
                            parent = level_items[lvl]
                            break

                    if parent:
                        parent.addChild(item)
                    else:
                        self._headings_tree.addTopLevelItem(item)

                    level_items[heading.level] = item

                self._headings_tree.expandAll()
                self._generate_btn.setEnabled(True)

                QMessageBox.information(
                    self,
                    "Sukces",
                    f"Wykryto {len(self._headings)} nagłówków.\n"
                    "Przejrzyj listę i kliknij 'Generuj zakładki'."
                )

        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd podczas wykrywania:\n{e}")

    def _on_generate_bookmarks(self) -> None:
        """Generuje zakładki z wykrytych nagłówków."""
        if not self._pdf_manager.is_loaded or not self._headings:
            return

        try:
            self._pdf_manager.generate_bookmarks()

            QMessageBox.information(
                self,
                "Sukces",
                "Zakładki zostały wygenerowane.\n"
                "Pamiętaj o zapisaniu dokumentu."
            )

        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd podczas generowania:\n{e}")

    def _on_classify_document(self) -> None:
        """Klasyfikuje aktualnie otwarty dokument."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(self, "Błąd", "Najpierw otwórz dokument PDF")
            return

        try:
            from pathlib import Path

            filepath = Path(self._pdf_manager._filepath)
            result = self._classifier.classify(filepath)

            self._classification_result = result

            # Wyświetl wynik
            category_desc = DocumentClassifier.get_category_descriptions()
            confidence_icon = "✓" if result.confidence >= 0.7 else "⚠" if result.confidence >= 0.4 else "?"

            classification_text = (
                f"{confidence_icon} <b>Kategoria:</b> {result.category}<br>"
                f"<b>Opis:</b> {category_desc.get(result.category, 'Brak opisu')}<br>"
                f"<b>Pewność:</b> {result.confidence * 100:.1f}%"
            )

            self._classification_label.setText(classification_text)
            self._classification_label.setVisible(True)

            # Sugerowana nazwa
            self._suggested_name_label.setText(
                f"Sugerowana nazwa: <b>{result.suggested_filename}</b>"
            )
            self._suggested_name_label.setVisible(True)

            # Tagi
            self._tags_label.setText(
                f"Tagi: {', '.join(result.tags)}"
            )
            self._tags_label.setVisible(True)

            # Pokaż wszystkie wyniki
            if result.confidence < 0.7:
                scores_text = "Inne możliwe kategorie:\n"
                sorted_scores = sorted(
                    result.all_scores.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                for cat, score in sorted_scores[:3]:
                    if cat != result.category:
                        scores_text += f"  • {cat}: {score * 100:.1f}%\n"

                QMessageBox.information(
                    self, "Klasyfikacja",
                    f"Dokument sklasyfikowany jako: {result.category}\n"
                    f"Pewność: {result.confidence * 100:.1f}%\n\n"
                    f"{scores_text}"
                )
            else:
                QMessageBox.information(
                    self, "Klasyfikacja",
                    f"Dokument sklasyfikowany jako: {result.category}\n"
                    f"Pewność: {result.confidence * 100:.1f}%\n"
                    f"Sugerowana nazwa: {result.suggested_filename}"
                )

        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd klasyfikacji:\n{e}")

    def _update_stats(self) -> None:
        """Aktualizuje statystyki dokumentu."""
        if not self._pdf_manager.is_loaded:
            self._stats_label.setText("Załaduj dokument, aby zobaczyć statystyki.")
            return

        page_count = self._pdf_manager.page_count

        # Pobierz informacje o stronach
        page_info = self._pdf_manager.get_all_page_info()

        # Oblicz statystyki
        total_width = sum(p.width for p in page_info)
        total_height = sum(p.height for p in page_info)
        avg_width = total_width / page_count if page_count > 0 else 0
        avg_height = total_height / page_count if page_count > 0 else 0

        # Wykryj orientację
        portrait = sum(1 for p in page_info if p.height > p.width)
        landscape = page_count - portrait

        stats_text = f"""<b>Liczba stron:</b> {page_count}

<b>Średni rozmiar strony:</b>
{avg_width:.1f} x {avg_height:.1f} pt

<b>Orientacja:</b>
• Pionowa: {portrait} stron
• Pozioma: {landscape} stron"""

        self._stats_label.setText(stats_text)

    # === Public API ===

    def on_document_loaded(self) -> None:
        """Wywoływane po załadowaniu dokumentu."""
        self._headings_tree.clear()
        self._headings = []
        self._generate_btn.setEnabled(False)
        self._update_stats()
