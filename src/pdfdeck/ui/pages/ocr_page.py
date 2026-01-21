"""
OCRPage - Strona rozpoznawania tekstu (OCR).

Funkcje:
- Rozpoznawanie tekstu z wybranej strony
- Batch OCR dla całego dokumentu
- Eksport do TXT/JSON
- Tworzenie searchable PDF
"""

from typing import Optional, List
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QTextEdit, QProgressBar,
    QGroupBox, QSpinBox, QFileDialog, QMessageBox,
    QSplitter, QScrollArea, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage

from typing import TYPE_CHECKING

from pdfdeck.ui.pages.base_page import BasePage
from pdfdeck.ui.widgets.styled_button import StyledButton
from pdfdeck.core.ocr_engine import OCREngine, OCRConfig, OCRResult

if TYPE_CHECKING:
    from pdfdeck.core.pdf_manager import PDFManager


def t(key: str, default: str = None) -> str:
    """Lokalna funkcja tłumaczenia - zwraca domyślny tekst lub klucz."""
    return default if default is not None else key


class OCRWorker(QThread):
    """Worker do wykonywania OCR w tle."""

    progress = pyqtSignal(int, int)  # current, total
    page_done = pyqtSignal(int, object)  # page_index, OCRResult
    finished = pyqtSignal(list)  # List[OCRResult]
    error = pyqtSignal(str)

    def __init__(
        self,
        doc,
        pages: List[int],
        config: OCRConfig,
        api_key: Optional[str] = None,
    ):
        super().__init__()
        self.doc = doc
        self.pages = pages
        self.config = config
        self.api_key = api_key
        self._cancelled = False

    def run(self):
        try:
            engine = OCREngine(self.api_key)
            results = []

            for i, page_idx in enumerate(self.pages):
                if self._cancelled:
                    break

                self.progress.emit(i, len(self.pages))

                result = engine.recognize_pdf_page(
                    self.doc,
                    page_idx,
                    self.config,
                )
                results.append(result)
                self.page_done.emit(page_idx, result)

            self.progress.emit(len(self.pages), len(self.pages))
            self.finished.emit(results)

        except Exception as e:
            self.error.emit(st(e))

    def cancel(self):
        self._cancelled = True


class OCRPage(BasePage):
    """
    Strona rozpoznawania tekstu (OCR).

    Umożliwia:
    - Rozpoznawanie tekstu z wybranych stron
    - Batch OCR dla całego dokumentu
    - Podgląd wyników
    - Eksport do TXT/JSON
    - Tworzenie searchable PDF
    """

    def __init__(self, pdf_manager: "PDFManager", parent=None):
        super().__init__(parent)

        self._pdf_manager = pdf_manager
        self._ocr_results: List[OCRResult] = []
        self._worker: Optional[OCRWorker] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Tworzy interfejs użytkownika."""
        # Użyj _main_layout z BasePage zamiast tworzyć nowy
        layout = self._main_layout
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Nagłówek
        header = QLabel(t("ocr_title", "OCR - Rozpoznawanie tekstu"))
        header.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 10px;
        """)
        layout.addWidget(header)

        desc = QLabel(t(
            "ocr_description",
            "Rozpoznaj tekst ze skanów i obrazów w dokumentach PDF.\n"
            "Wykorzystuje darmowe API OCR.space (25,000 zapytań/miesiąc)."
        ))
        desc.setStyleSheet("color: #8892a0; font-size: 13px;")
        layout.addWidget(desc)

        # Główny splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # === Lewa strona - Konfiguracja ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)

        # === METODA OCR ===
        from PyQt6.QtWidgets import QRadioButton, QButtonGroup

        method_group = QGroupBox("METODA")
        method_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                border: 1px solid #2d3a50;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        method_layout = QVBoxLayout(method_group)
        method_layout.setSpacing(12)

        # Button group dla wzajemnego wykluczania
        self._method_button_group = QButtonGroup()

        # AI OCR (Online)
        ai_ocr_widget = QWidget()
        ai_ocr_layout = QVBoxLayout(ai_ocr_widget)
        ai_ocr_layout.setContentsMargins(0, 0, 0, 0)
        ai_ocr_layout.setSpacing(4)

        self._ai_ocr_radio = QRadioButton("AI OCR (Online)")
        self._ai_ocr_radio.setStyleSheet("""
            QRadioButton {
                color: #ffffff;
                font-size: 13px;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #2d3a50;
                background-color: #0f1629;
            }
            QRadioButton::indicator:checked {
                background-color: #e0a800;
                border-color: #e0a800;
            }
            QRadioButton::indicator:hover {
                border-color: #e0a800;
            }
        """)
        self._method_button_group.addButton(self._ai_ocr_radio, 0)
        ai_ocr_layout.addWidget(self._ai_ocr_radio)

        ai_ocr_desc = QLabel("⚠️  Wysyła obraz na zewnętrzny serwer - nie dla wrażliwych danych")
        ai_ocr_desc.setStyleSheet("""
            color: #f39c12;
            font-size: 11px;
            padding-left: 26px;
        """)
        ai_ocr_desc.setWordWrap(True)
        ai_ocr_layout.addWidget(ai_ocr_desc)

        method_layout.addWidget(ai_ocr_widget)

        # Tesseract (Zalecane)
        tesseract_widget = QWidget()
        tesseract_layout = QVBoxLayout(tesseract_widget)
        tesseract_layout.setContentsMargins(0, 0, 0, 0)
        tesseract_layout.setSpacing(4)

        self._tesseract_radio = QRadioButton("Tesseract (Zalecane)")
        self._tesseract_radio.setStyleSheet(self._ai_ocr_radio.styleSheet())
        self._tesseract_radio.setChecked(True)  # Domyślnie zaznaczone
        self._method_button_group.addButton(self._tesseract_radio, 1)
        tesseract_layout.addWidget(self._tesseract_radio)

        tesseract_desc = QLabel("🔒 100% prywatne - działa lokalnie, offline")
        tesseract_desc.setStyleSheet("""
            color: #27ae60;
            font-size: 11px;
            padding-left: 26px;
        """)
        tesseract_desc.setWordWrap(True)
        tesseract_layout.addWidget(tesseract_desc)

        method_layout.addWidget(tesseract_widget)

        left_layout.addWidget(method_group)

        # Konfiguracja OCR
        config_group = QGroupBox(t("ocr_settings", "Ustawienia OCR"))
        config_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                border: 1px solid #2d3a50;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        config_layout = QVBoxLayout(config_group)

        # Język
        lang_row = QHBoxLayout()
        lang_label = QLabel(t("ocr_language", "Język:"))
        lang_label.setStyleSheet("color: #8892a0;")
        lang_row.addWidget(lang_label)

        self._language_combo = QComboBox()
        self._language_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 8px;
                color: #ffffff;
                min-width: 150px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                selection-background-color: #e0a800;
                selection-color: #1a1a2e;
            }
        """)

        # Dodaj języki
        languages = OCREngine.get_supported_languages()
        for code, name in languages.items():
            self._language_combo.addItem(f"{name} ({code})", code)

        # Ustaw polski jako domyślny
        pol_index = self._language_combo.findData("pol")
        if pol_index >= 0:
            self._language_combo.setCurrentIndex(pol_index)

        lang_row.addWidget(self._language_combo)
        lang_row.addStretch()
        config_layout.addLayout(lang_row)

        # Engine
        engine_row = QHBoxLayout()
        engine_label = QLabel(t("ocr_engine", "Silnik OCR:"))
        engine_label.setStyleSheet("color: #8892a0;")
        engine_row.addWidget(engine_label)

        self._engine_combo = QComboBox()
        self._engine_combo.setStyleSheet(self._language_combo.styleSheet())
        self._engine_combo.addItem("Engine 1 (szybszy)", 1)
        self._engine_combo.addItem("Engine 2 (dokładniejszy)", 2)
        self._engine_combo.setCurrentIndex(1)  # Engine 2 domyślnie
        engine_row.addWidget(self._engine_combo)
        engine_row.addStretch()
        config_layout.addLayout(engine_row)

        # Opcje
        self._table_check = QCheckBox(t("ocr_table_mode", "Tryb tabelaryczny"))
        self._table_check.setStyleSheet("color: #ffffff;")
        config_layout.addWidget(self._table_check)

        self._scale_check = QCheckBox(t("ocr_scale", "Skaluj dla lepszej dokładności"))
        self._scale_check.setStyleSheet("color: #ffffff;")
        self._scale_check.setChecked(True)
        config_layout.addWidget(self._scale_check)

        # API Key
        api_row = QHBoxLayout()
        api_label = QLabel(t("ocr_api_key", "API Key (opcjonalny):"))
        api_label.setStyleSheet("color: #8892a0;")
        api_row.addWidget(api_label)

        from PyQt6.QtWidgets import QLineEdit
        self._api_key_input = QLineEdit()
        self._api_key_input.setPlaceholderText("helloworld (demo)")
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_input.setStyleSheet("""
            QLineEdit {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 8px;
                color: #ffffff;
            }
        """)

        # Załaduj klucz z ustawień
        from pdfdeck.ui.pages.settings_page import SettingsPage
        saved_key = SettingsPage.get_ocr_api_key()
        if saved_key and saved_key != "helloworld":
            self._api_key_input.setText(saved_key)

        api_row.addWidget(self._api_key_input)
        config_layout.addLayout(api_row)

        left_layout.addWidget(config_group)

        # Wybór stron
        pages_group = QGroupBox(t("ocr_pages", "Strony do przetworzenia"))
        pages_group.setStyleSheet(config_group.styleSheet())
        pages_layout = QVBoxLayout(pages_group)

        self._all_pages_radio = QCheckBox(t("ocr_all_pages", "Wszystkie strony"))
        self._all_pages_radio.setStyleSheet("color: #ffffff;")
        self._all_pages_radio.setChecked(True)
        pages_layout.addWidget(self._all_pages_radio)

        page_range_row = QHBoxLayout()
        self._range_radio = QCheckBox(t("ocr_page_range", "Zakres:"))
        self._range_radio.setStyleSheet("color: #ffffff;")
        page_range_row.addWidget(self._range_radio)

        self._from_spin = QSpinBox()
        self._from_spin.setMinimum(1)
        self._from_spin.setStyleSheet("""
            QSpinBox {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
        """)
        page_range_row.addWidget(self._from_spin)

        page_range_row.addWidget(QLabel("-"))

        self._to_spin = QSpinBox()
        self._to_spin.setMinimum(1)
        self._to_spin.setStyleSheet(self._from_spin.styleSheet())
        page_range_row.addWidget(self._to_spin)

        page_range_row.addStretch()
        pages_layout.addLayout(page_range_row)

        # Wzajemne wykluczanie
        self._all_pages_radio.toggled.connect(
            lambda checked: self._range_radio.setChecked(not checked) if checked else None
        )
        self._range_radio.toggled.connect(
            lambda checked: self._all_pages_radio.setChecked(not checked) if checked else None
        )

        left_layout.addWidget(pages_group)

        # Postęp
        self._progress_bar = QProgressBar()
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                height: 20px;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #e0a800;
                border-radius: 3px;
            }
        """)
        self._progress_bar.setVisible(False)
        left_layout.addWidget(self._progress_bar)

        # Przyciski akcji
        buttons_layout = QHBoxLayout()

        self._start_btn = StyledButton(t("ocr_start", "Rozpocznij OCR"), "primary")
        self._start_btn.clicked.connect(self._start_ocr)
        buttons_layout.addWidget(self._start_btn)

        self._cancel_btn = StyledButton(t("ocr_cancel", "Anuluj"), "secondary")
        self._cancel_btn.clicked.connect(self._cancel_ocr)
        self._cancel_btn.setEnabled(False)
        buttons_layout.addWidget(self._cancel_btn)

        left_layout.addLayout(buttons_layout)

        left_layout.addStretch()

        splitter.addWidget(left_widget)

        # === Prawa strona - Wyniki ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)

        results_group = QGroupBox(t("ocr_results", "Wyniki OCR"))
        results_group.setStyleSheet(config_group.styleSheet())
        results_layout = QVBoxLayout(results_group)

        # Wybór strony wyników
        result_page_row = QHBoxLayout()
        result_page_label = QLabel(t("ocr_show_page", "Pokaż stronę:"))
        result_page_label.setStyleSheet("color: #8892a0;")
        result_page_row.addWidget(result_page_label)

        self._result_page_combo = QComboBox()
        self._result_page_combo.setStyleSheet(self._language_combo.styleSheet())
        self._result_page_combo.currentIndexChanged.connect(self._show_page_result)
        result_page_row.addWidget(self._result_page_combo)
        result_page_row.addStretch()
        results_layout.addLayout(result_page_row)

        # Tekst wynikowy
        self._result_text = QTextEdit()
        self._result_text.setReadOnly(True)
        self._result_text.setStyleSheet("""
            QTextEdit {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 10px;
                color: #ffffff;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 13px;
            }
        """)
        self._result_text.setPlaceholderText(
            t("ocr_no_results", "Wyniki OCR pojawią się tutaj...")
        )
        results_layout.addWidget(self._result_text)

        # Przyciski eksportu
        export_layout = QHBoxLayout()

        export_txt_btn = StyledButton(t("ocr_export_txt", "Eksportuj TXT"), "secondary")
        export_txt_btn.clicked.connect(lambda: self._export_results("txt"))
        export_layout.addWidget(export_txt_btn)

        export_json_btn = StyledButton(t("ocr_export_json", "Eksportuj JSON"), "secondary")
        export_json_btn.clicked.connect(lambda: self._export_results("json"))
        export_layout.addWidget(export_json_btn)

        searchable_btn = StyledButton(t("ocr_create_searchable", "Utwórz Searchable PDF"), "primary")
        searchable_btn.clicked.connect(self._create_searchable_pdf)
        export_layout.addWidget(searchable_btn)

        results_layout.addLayout(export_layout)

        right_layout.addWidget(results_group)

        splitter.addWidget(right_widget)

        # Ustaw proporcje splittera
        splitter.setSizes([400, 600])

        layout.addWidget(splitter)

    def on_document_loaded(self) -> None:
        """Wywoływane po załadowaniu dokumentu."""
        if self._pdf_manager and self._pdf_manager.page_count > 0:
            self._from_spin.setMaximum(self._pdf_manager.page_count)
            self._to_spin.setMaximum(self._pdf_manager.page_count)
            self._to_spin.setValue(self._pdf_manager.page_count)

    def _get_config(self) -> OCRConfig:
        """Zwraca aktualną konfigurację OCR."""
        return OCRConfig(
            language=self._language_combo.currentData(),
            engine=self._engine_combo.currentData(),
            scale=self._scale_check.isChecked(),
            is_table=self._table_check.isChecked(),
        )

    def _get_pages_to_process(self) -> List[int]:
        """Zwraca listę stron do przetworzenia."""
        if not self._pdf_manager:
            return []

        if self._all_pages_radio.isChecked():
            return list(range(self._pdf_manager.page_count))
        else:
            from_page = self._from_spin.value() - 1
            to_page = self._to_spin.value()
            return list(range(from_page, to_page))

    def _start_ocr(self) -> None:
        """Rozpoczyna proces OCR."""
        if not self._pdf_manager or not self._pdf_manager._doc:
            QMessageBox.warning(
                self,
                t("warning", "Ostrzeżenie"),
                t("ocr_no_document", "Najpierw załaduj dokument PDF.")
            )
            return

        pages = self._get_pages_to_process()
        if not pages:
            return

        config = self._get_config()
        api_key = self._api_key_input.text().strip() or None

        # Reset wyników
        self._ocr_results = []
        self._result_page_combo.clear()
        self._result_text.clear()

        # Pokaż postęp
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
        self._progress_bar.setMaximum(len(pages))

        # Zablokuj przyciski
        self._start_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)

        # Uruchom worker
        self._worker = OCRWorker(
            self._pdf_manager._doc,
            pages,
            config,
            api_key,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.page_done.connect(self._on_page_done)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _cancel_ocr(self) -> None:
        """Anuluje proces OCR."""
        if self._worker:
            self._worker.cancel()
            self._worker.wait()
            self._worker = None

        self._progress_bar.setVisible(False)
        self._start_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)

    def _on_progress(self, current: int, total: int) -> None:
        """Aktualizuje pasek postępu."""
        self._progress_bar.setValue(current)

    def _on_page_done(self, page_index: int, result: OCRResult) -> None:
        """Wywoływane po przetworzeniu strony."""
        self._ocr_results.append(result)

        # Dodaj do combo
        status = "✓" if not result.error else "✗"
        self._result_page_combo.addItem(
            f"{status} Strona {page_index + 1}",
            page_index,
        )

        # Pokaż pierwszy wynik
        if len(self._ocr_results) == 1:
            self._result_page_combo.setCurrentIndex(0)
            self._show_page_result(0)

    def _on_finished(self, results: List[OCRResult]) -> None:
        """Wywoływane po zakończeniu OCR."""
        self._progress_bar.setVisible(False)
        self._start_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._worker = None

        # Podsumowanie
        success = sum(1 for r in results if not r.error)
        total = len(results)

        QMessageBox.information(
            self,
            t("ocr_complete", "OCR zakończone"),
            t(
                "ocr_complete_msg",
                f"Przetworzono {success}/{total} stron."
            )
        )

    def _on_error(self, error: str) -> None:
        """Wywoływane w przypadku błędu."""
        self._progress_bar.setVisible(False)
        self._start_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._worker = None

        QMessageBox.critical(
            self,
            t("error", "Błąd"),
            t("ocr_error", f"Błąd OCR: {error}")
        )

    def _show_page_result(self, index: int) -> None:
        """Pokazuje wynik dla wybranej strony."""
        if index < 0 or index >= len(self._ocr_results):
            return

        result = self._ocr_results[index]

        if result.error:
            self._result_text.setPlainText(f"[Błąd: {result.error}]")
        else:
            self._result_text.setPlainText(result.text)

    def _export_results(self, format: str) -> None:
        """Eksportuje wyniki do pliku."""
        if not self._ocr_results:
            QMessageBox.warning(
                self,
                t("warning", "Ostrzeżenie"),
                t("ocr_no_results_export", "Brak wyników do eksportu.")
            )
            return

        # Wybierz plik
        ext = "txt" if format == "txt" else "json"
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            t("ocr_export_title", "Eksportuj wyniki OCR"),
            f"ocr_results.{ext}",
            f"{ext.upper()} Files (*.{ext})",
        )

        if not filepath:
            return

        # Eksportuj
        engine = OCREngine()
        content = engine.export_text(self._ocr_results, format)

        Path(filepath).write_text(content, encoding="utf-8")

        QMessageBox.information(
            self,
            t("success", "Sukces"),
            t("ocr_exported", f"Wyniki zapisano do: {filepath}")
        )

    def _create_searchable_pdf(self) -> None:
        """Tworzy searchable PDF."""
        if not self._ocr_results:
            QMessageBox.warning(
                self,
                t("warning", "Ostrzeżenie"),
                t("ocr_no_results_export", "Brak wyników do eksportu.")
            )
            return

        if not self._pdf_manager or not self._pdf_manager._doc:
            return

        # Wybierz plik
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            t("ocr_save_searchable", "Zapisz Searchable PDF"),
            "searchable.pdf",
            "PDF Files (*.pdf)",
        )

        if not filepath:
            return

        # Utwórz searchable PDF
        engine = OCREngine()
        pdf_bytes = engine.create_searchable_pdf(
            self._pdf_manager._doc,
            self._ocr_results,
        )

        Path(filepath).write_bytes(pdf_bytes)

        QMessageBox.information(
            self,
            t("success", "Sukces"),
            t("ocr_searchable_created", f"Searchable PDF zapisano do: {filepath}")
        )
