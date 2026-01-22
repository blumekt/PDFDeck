"""
WatchFolderPage - Strona automatycznego przetwarzania.

Funkcje:
- Konfiguracja folderu obserwowanego
- Wybór profilu przetwarzania
- Podgląd logów
- Statystyki
"""

from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QComboBox, QLineEdit,
    QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from pdfdeck.ui.pages.base_page import BasePage
from pdfdeck.ui.widgets.styled_button import StyledButton
from pdfdeck.ui.widgets.profile_combo import ProfileComboBox
from pdfdeck.core.watch_folder import WatchFolderService, ProcessingStatus
from pdfdeck.core.processing_profile import (
    ProcessingProfile, PRESET_PROFILES, ProcessingAction
)
from pdfdeck.core.profile_manager import ProfileManager, ProfileType


class WatchFolderPage(BasePage):
    """
    Strona automatycznego przetwarzania PDF.

    Pozwala użytkownikowi:
    - Wybrać folder do monitorowania
    - Wybrać folder wyjściowy
    - Wybrać lub utworzyć profil przetwarzania
    - Uruchomić/zatrzymać monitorowanie
    - Przeglądać logi operacji
    """

    def __init__(self, main_window):
        super().__init__(main_window)

        self._service = WatchFolderService()
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh_log)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Tworzy interfejs użytkownika."""
        # Użyj _main_layout z BasePage zamiast tworzyć nowy
        layout = self._main_layout
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Scroll area dla całej zawartości
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(self._scroll_style())

        # Kontener wewnętrzny
        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        # Nagłówek
        header = QLabel("Watch Folder - Automatyczne przetwarzanie")
        header.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 5px;
        """)
        content_layout.addWidget(header)

        desc = QLabel(
            "Automatycznie przetwarzaj pliki PDF pojawiające się w folderze.\n"
            "Przetworzone dokumenty są zapisywane w folderze wyjściowym."
        )
        desc.setStyleSheet("color: #8892a0; font-size: 13px; margin-bottom: 10px;")
        content_layout.addWidget(desc)

        # === Konfiguracja ===
        config_group = QGroupBox("Konfiguracja")
        config_group.setStyleSheet(self._group_style())
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(12)
        config_layout.setContentsMargins(15, 20, 15, 15)

        # Folder wejściowy
        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        input_label = QLabel("Folder wejściowy:")
        input_label.setStyleSheet("color: #8892a0;")
        input_label.setFixedWidth(130)
        input_row.addWidget(input_label)

        self._input_dir_edit = QLineEdit()
        self._input_dir_edit.setReadOnly(True)
        self._input_dir_edit.setPlaceholderText("Wybierz folder do monitorowania...")
        self._input_dir_edit.setStyleSheet(self._input_style())
        input_row.addWidget(self._input_dir_edit)

        input_btn = StyledButton("Przeglądaj", "secondary")
        input_btn.clicked.connect(self._browse_input_dir)
        input_row.addWidget(input_btn)

        config_layout.addLayout(input_row)

        # Folder wyjściowy
        output_row = QHBoxLayout()
        output_row.setSpacing(10)
        output_label = QLabel("Folder wyjściowy:")
        output_label.setStyleSheet("color: #8892a0;")
        output_label.setFixedWidth(130)
        output_row.addWidget(output_label)

        self._output_dir_edit = QLineEdit()
        self._output_dir_edit.setReadOnly(True)
        self._output_dir_edit.setPlaceholderText("Wybierz folder wyjściowy...")
        self._output_dir_edit.setStyleSheet(self._input_style())
        output_row.addWidget(self._output_dir_edit)

        output_btn = StyledButton("Przeglądaj", "secondary")
        output_btn.clicked.connect(self._browse_output_dir)
        output_row.addWidget(output_btn)

        config_layout.addLayout(output_row)

        # Profil przetwarzania
        profile_row = QHBoxLayout()
        profile_row.setSpacing(10)
        profile_label = QLabel("Profil:")
        profile_label.setStyleSheet("color: #8892a0;")
        profile_label.setFixedWidth(130)
        profile_row.addWidget(profile_label)

        self._profile_combo = QComboBox()
        self._profile_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 6px;
                padding: 8px 12px;
                color: #ffffff;
                min-width: 250px;
            }
            QComboBox:focus {
                border-color: #e0a800;
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

        # Dodaj predefiniowane profile
        for key, profile in PRESET_PROFILES.items():
            self._profile_combo.addItem(profile.name, key)

        profile_row.addWidget(self._profile_combo)

        self._profile_info_btn = StyledButton("Info", "secondary")
        self._profile_info_btn.clicked.connect(self._show_profile_info)
        profile_row.addWidget(self._profile_info_btn)

        profile_row.addStretch()
        config_layout.addLayout(profile_row)

        # Profil znaku wodnego
        watermark_row = QHBoxLayout()
        watermark_row.setSpacing(10)
        watermark_label = QLabel("Znak wodny:")
        watermark_label.setStyleSheet("color: #8892a0;")
        watermark_label.setFixedWidth(130)
        watermark_row.addWidget(watermark_label)

        self._watermark_profile_combo = ProfileComboBox(ProfileType.WATERMARK)
        self._watermark_profile_combo.set_save_button_visible(False)
        self._watermark_profile_combo.set_delete_button_visible(False)
        watermark_row.addWidget(self._watermark_profile_combo)
        watermark_row.addStretch()
        config_layout.addLayout(watermark_row)

        # Profil pieczątki
        stamp_row = QHBoxLayout()
        stamp_row.setSpacing(10)
        stamp_label = QLabel("Pieczątka:")
        stamp_label.setStyleSheet("color: #8892a0;")
        stamp_label.setFixedWidth(130)
        stamp_row.addWidget(stamp_label)

        self._stamp_profile_combo = ProfileComboBox(ProfileType.STAMP)
        self._stamp_profile_combo.set_save_button_visible(False)
        self._stamp_profile_combo.set_delete_button_visible(False)
        stamp_row.addWidget(self._stamp_profile_combo)
        stamp_row.addStretch()
        config_layout.addLayout(stamp_row)

        content_layout.addWidget(config_group)

        # === Kontrola ===
        control_layout = QHBoxLayout()
        control_layout.setSpacing(15)

        self._start_btn = StyledButton("▶ Uruchom monitorowanie", "primary")
        self._start_btn.clicked.connect(self._start_watching)
        control_layout.addWidget(self._start_btn)

        self._stop_btn = StyledButton("⬛ Zatrzymaj", "danger")
        self._stop_btn.clicked.connect(self._stop_watching)
        self._stop_btn.setEnabled(False)
        control_layout.addWidget(self._stop_btn)

        # Status
        self._status_label = QLabel("Status: zatrzymany")
        self._status_label.setStyleSheet("color: #8892a0; margin-left: 20px; font-size: 13px;")
        control_layout.addWidget(self._status_label)

        control_layout.addStretch()

        content_layout.addLayout(control_layout)

        # === Log ===
        log_group = QGroupBox("Log operacji")
        log_group.setStyleSheet(self._group_style())
        log_layout = QVBoxLayout(log_group)
        log_layout.setSpacing(10)
        log_layout.setContentsMargins(15, 20, 15, 15)

        # Tabela logów
        self._log_table = QTableWidget()
        self._log_table.setColumnCount(4)
        self._log_table.setHorizontalHeaderLabels(["Czas", "Plik", "Status", "Wiadomość"])
        self._log_table.horizontalHeader().setStretchLastSection(True)
        self._log_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._log_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._log_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._log_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._log_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._log_table.setStyleSheet(self._table_style())
        log_layout.addWidget(self._log_table)

        # Przyciski logu
        log_buttons = QHBoxLayout()

        clear_log_btn = StyledButton("Wyczyść log", "secondary")
        clear_log_btn.clicked.connect(self._clear_log)
        log_buttons.addWidget(clear_log_btn)

        log_buttons.addStretch()

        # Statystyki
        self._stats_label = QLabel("Przetworzono: 0 | Sukces: 0 | Błędy: 0")
        self._stats_label.setStyleSheet("color: #8892a0;")
        log_buttons.addWidget(self._stats_label)

        log_layout.addLayout(log_buttons)

        content_layout.addWidget(log_group, 1)

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _group_style(self) -> str:
        """Zwraca styl dla QGroupBox."""
        return """
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #e0a800;
                border: 1px solid #2d3a50;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 18px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }
        """

    def _input_style(self) -> str:
        """Zwraca styl dla pól input."""
        return """
            QLineEdit {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 6px;
                padding: 8px 12px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #e0a800;
            }
        """

    def _scroll_style(self) -> str:
        """Zwraca styl dla scroll area."""
        return """
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #0f1629;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #2d3a50;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #e0a800;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """

    def _table_style(self) -> str:
        """Zwraca styl dla QTableWidget."""
        return """
            QTableWidget {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 6px;
                gridline-color: #2d3a50;
            }
            QTableWidget::item {
                padding: 6px;
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #e0a800;
                color: #1a1a2e;
            }
            QHeaderView::section {
                background-color: #1f2940;
                color: #8892a0;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #2d3a50;
            }
        """


    def _browse_input_dir(self) -> None:
        """Wybiera folder wejściowy."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Wybierz folder wejściowy",
            "",
        )
        if dir_path:
            self._input_dir_edit.setText(dir_path)

    def _browse_output_dir(self) -> None:
        """Wybiera folder wyjściowy."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Wybierz folder wyjściowy",
            "",
        )
        if dir_path:
            self._output_dir_edit.setText(dir_path)

    def _show_profile_info(self) -> None:
        """Pokazuje informacje o wybranym profilu."""
        profile_key = self._profile_combo.currentData()
        if not profile_key or profile_key not in PRESET_PROFILES:
            return

        profile = PRESET_PROFILES[profile_key]

        # Nazwy akcji
        action_names = {
            ProcessingAction.NORMALIZE_A4: "Normalizacja do A4",
            ProcessingAction.COMPRESS: "Kompresja",
            ProcessingAction.ADD_WATERMARK: "Znak wodny",
            ProcessingAction.ADD_STAMP: "Pieczątka",
            ProcessingAction.ADD_BATES: "Numeracja Bates",
            ProcessingAction.SCRUB_METADATA: "Usunięcie metadanych",
            ProcessingAction.FLATTEN: "Spłaszczenie",
            ProcessingAction.CONVERT_PDFA: "Konwersja do PDF/A",
        }

        lines = [
            f"<b>Profil: {profile.name}</b>",
            "",
            "<b>Akcje:</b>",
        ]

        for action in profile.actions:
            lines.append(f"• {action_names.get(action, action.value)}")

        if profile.watermark_text:
            lines.append(f"<br><b>Znak wodny:</b> {profile.watermark_text}")

        if profile.bates_prefix:
            lines.append(f"<b>Bates prefix:</b> {profile.bates_prefix}")

        QMessageBox.information(
            self,
            "Informacje o profilu",
            "<br>".join(lines)
        )

    def _start_watching(self) -> None:
        """Uruchamia monitorowanie."""
        input_dir = self._input_dir_edit.text()
        output_dir = self._output_dir_edit.text()

        if not input_dir:
            QMessageBox.warning(
                self,
                "Błąd",
                "Wybierz folder wejściowy"
            )
            return

        if not output_dir:
            QMessageBox.warning(
                self,
                "Błąd",
                "Wybierz folder wyjściowy"
            )
            return

        # Pobierz profil
        profile_key = self._profile_combo.currentData()
        if not profile_key or profile_key not in PRESET_PROFILES:
            QMessageBox.warning(
                self,
                "Błąd",
                "Wybierz profil przetwarzania"
            )
            return

        base_profile = PRESET_PROFILES[profile_key]

        # Pobierz wybrane profile watermark i stamp
        watermark_profile_name = self._watermark_profile_combo.get_selected_profile_name()
        stamp_profile_name = self._stamp_profile_combo.get_selected_profile_name()

        # Utwórz zmodyfikowany profil z referencjami do profili
        actions = list(base_profile.actions)

        # Dodaj akcje jeśli wybrano profile
        if watermark_profile_name and ProcessingAction.ADD_WATERMARK not in actions:
            actions.append(ProcessingAction.ADD_WATERMARK)
        if stamp_profile_name and ProcessingAction.ADD_STAMP not in actions:
            actions.append(ProcessingAction.ADD_STAMP)

        profile = ProcessingProfile(
            name=base_profile.name,
            actions=actions,
            watermark_profile_name=watermark_profile_name,
            stamp_profile_name=stamp_profile_name,
            watermark_text=base_profile.watermark_text,
            watermark_opacity=base_profile.watermark_opacity,
            watermark_rotation=base_profile.watermark_rotation,
            bates_prefix=base_profile.bates_prefix,
            bates_suffix=base_profile.bates_suffix,
            bates_start=base_profile.bates_start,
            bates_digits=base_profile.bates_digits,
            pdfa_level=base_profile.pdfa_level,
            output_format=base_profile.output_format,
            output_suffix=base_profile.output_suffix,
        )

        # Uruchom serwis
        success = self._service.start(
            Path(input_dir),
            Path(output_dir),
            profile,
            self._on_file_processed,
        )

        if success:
            self._start_btn.setEnabled(False)
            self._stop_btn.setEnabled(True)
            self._status_label.setText("Status: działa")
            self._status_label.setStyleSheet("color: #27ae60;")

            # Uruchom timer odświeżania
            self._refresh_timer.start(1000)
        else:
            QMessageBox.critical(
                self,
                "Błąd",
                "Nie można uruchomić monitorowania.\n"
                "Sprawdź czy foldery istnieją."
            )

    def _stop_watching(self) -> None:
        """Zatrzymuje monitorowanie."""
        self._service.stop()
        self._refresh_timer.stop()

        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._status_label.setText("Status: zatrzymany")
        self._status_label.setStyleSheet("color: #8892a0;")

    def _on_file_processed(self, entry) -> None:
        """Callback wywoływany po przetworzeniu pliku."""
        # Ta metoda jest wywoływana z innego wątku,
        # więc aktualizację UI wykonujemy przez timer
        pass

    def _refresh_log(self) -> None:
        """Odświeża tabelę logów."""
        log_entries = self._service.log

        self._log_table.setRowCount(len(log_entries))

        for i, entry in enumerate(reversed(log_entries)):
            # Czas
            time_item = QTableWidgetItem(
                entry.timestamp.strftime("%H:%M:%S")
            )
            self._log_table.setItem(i, 0, time_item)

            # Plik
            file_item = QTableWidgetItem(entry.filename)
            self._log_table.setItem(i, 1, file_item)

            # Status
            status_text = {
                ProcessingStatus.PENDING: "⏳ Oczekuje",
                ProcessingStatus.PROCESSING: "🔄 Przetwarzanie",
                ProcessingStatus.SUCCESS: "✅ Sukces",
                ProcessingStatus.ERROR: "❌ Błąd",
                ProcessingStatus.SKIPPED: "⏭️ Pominięty",
            }.get(entry.status, entry.status.value)

            status_item = QTableWidgetItem(status_text)
            self._log_table.setItem(i, 2, status_item)

            # Wiadomość
            msg_item = QTableWidgetItem(entry.message)
            self._log_table.setItem(i, 3, msg_item)

        # Statystyki
        stats = self._service.get_statistics()
        self._stats_label.setText(
            f"Przetworzono: {stats['total_processed']} | "
            f"Sukces: {stats['successful']} | "
            f"Błędy: {stats['errors']}"
        )

    def _clear_log(self) -> None:
        """Czyści log."""
        self._service.clear_log()
        self._log_table.setRowCount(0)
        self._stats_label.setText("Przetworzono: 0 | Sukces: 0 | Błędy: 0")

    def on_document_loaded(self) -> None:
        """Wywoływane po załadowaniu dokumentu."""
        pass

    def showEvent(self, event) -> None:
        """Wywoływane gdy strona staje się widoczna - odświeżamy profile."""
        super().showEvent(event)

        # Odśwież oba comboboxy aby załadować nowo zapisane profile
        self._watermark_profile_combo.refresh()
        self._stamp_profile_combo.refresh()

    def closeEvent(self, event) -> None:
        """Obsługa zamykania."""
        self._service.stop()
        self._refresh_timer.stop()
        super().closeEvent(event)
