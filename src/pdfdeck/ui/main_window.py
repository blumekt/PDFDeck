"""
MainWindow - Główne okno aplikacji PDFDeck.

Układ:
- Sidebar po lewej stronie
- Content area po prawej (QStackedWidget)
- Statusbar na dole
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QStatusBar, QMessageBox, QFileDialog, QLabel
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QCloseEvent

from pdfdeck import __app_name__, __version__
from pdfdeck.app import get_resources_path
from pdfdeck.core.pdf_manager import PDFManager
from pdfdeck.core.thumbnail_worker import ThumbnailManager
from pdfdeck.ui.sidebar import Sidebar


class MainWindow(QMainWindow):
    """
    Główne okno aplikacji PDFDeck.

    Układ:
    +------------------+------------------------------------------+
    |                  |  Header (ścieżka pliku + przyciski)      |
    |     Sidebar      +------------------------------------------+
    |                  |                                          |
    |  [Menu items]    |     Content Area (QStackedWidget)        |
    |                  |                                          |
    |                  |     [PagesView / RedactionPage / ...]    |
    |                  |                                          |
    +------------------+------------------------------------------+
    |  Status Bar                                                  |
    +--------------------------------------------------------------+
    """

    def __init__(self) -> None:
        super().__init__()

        # Core components
        self._pdf_manager = PDFManager()
        self._thumbnail_manager: Optional[ThumbnailManager] = None

        # Ścieżki
        self._resources_path = get_resources_path()
        self._icons_path = self._resources_path / "icons"

        # UI setup
        self._setup_ui()
        self._setup_statusbar()
        self._connect_signals()

        # Window config
        self.setWindowTitle(f"Blumy -> PdfDeck {__version__}")
        self.setMinimumSize(900, 400)
        self.resize(1000, 600)

        # Ustaw początkową stronę
        self._sidebar.set_active_page("pages")

        # Sprawdź aktualizacje po uruchomieniu (z opóźnieniem)
        QTimer.singleShot(2000, self._check_for_updates)

    def _setup_ui(self) -> None:
        """Tworzy główny interfejs."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Main layout (horizontal)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === Sidebar ===
        self._sidebar = Sidebar(self._icons_path)
        main_layout.addWidget(self._sidebar)

        # === Content Area ===
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Header (ścieżka pliku + przyciski)
        self._header = self._create_header()
        content_layout.addWidget(self._header)

        # Stacked widget dla stron
        self._stack = QStackedWidget()
        self._stack.setObjectName("content_area")
        content_layout.addWidget(self._stack)

        main_layout.addWidget(content_widget)

        # === Tworzenie stron ===
        self._create_pages()

    def _create_header(self) -> QWidget:
        """Tworzy nagłówek z informacją o pliku."""
        header = QWidget()
        header.setFixedHeight(60)
        header.setStyleSheet("""
            QWidget {
                background-color: #1a1a2e;
                border-bottom: 1px solid #2d3a50;
            }
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)

        # Etykieta "Plik PDF:"
        label = QLabel("Plik PDF:")
        label.setStyleSheet("color: #8892a0; font-size: 14px;")
        layout.addWidget(label)

        # Ścieżka pliku
        self._file_path_label = QLabel("Nie wybrano pliku")
        self._file_path_label.setStyleSheet("""
            color: #ffffff;
            font-size: 14px;
            background-color: #0f1629;
            border: 1px solid #2d3a50;
            border-radius: 6px;
            padding: 8px 15px;
        """)
        self._file_path_label.setMinimumWidth(400)
        layout.addWidget(self._file_path_label, 1)

        # Przycisk "Otwórz"
        from pdfdeck.ui.widgets.styled_button import StyledButton

        self._open_btn = StyledButton("Otwórz", "primary")
        self._open_btn.setFixedWidth(100)
        self._open_btn.clicked.connect(self._on_open_file)
        layout.addWidget(self._open_btn)

        return header

    def _create_pages(self) -> None:
        """Tworzy wszystkie strony aplikacji."""
        # Import stron
        from pdfdeck.ui.pages.pages_view import PagesView
        from pdfdeck.ui.pages.redaction_page import RedactionPage
        from pdfdeck.ui.pages.watermark_page import WatermarkPage
        from pdfdeck.ui.pages.security_page import SecurityPage
        from pdfdeck.ui.pages.tools_page import ToolsPage
        from pdfdeck.ui.pages.analysis_page import AnalysisPage
        from pdfdeck.ui.pages.automation_page import AutomationPage
        from pdfdeck.ui.pages.settings_page import SettingsPage

        # Mapa stron
        self._pages = {}

        # Strona "Strony" (główna)
        pages_view = PagesView(self._pdf_manager)
        self._pages["pages"] = pages_view
        self._stack.addWidget(pages_view)

        # Strona "Redakcja"
        redaction_page = RedactionPage(self._pdf_manager)
        self._pages["redaction"] = redaction_page
        self._stack.addWidget(redaction_page)

        # Strona "Znaki wodne"
        watermark_page = WatermarkPage(self._pdf_manager)
        self._pages["watermark"] = watermark_page
        self._stack.addWidget(watermark_page)

        # Strona "Narzędzia"
        tools_page = ToolsPage(self._pdf_manager)
        self._pages["tools"] = tools_page
        self._stack.addWidget(tools_page)

        # Strona "Bezpieczeństwo"
        security_page = SecurityPage(self._pdf_manager)
        self._pages["security"] = security_page
        self._stack.addWidget(security_page)

        # Strona "Analiza"
        analysis_page = AnalysisPage(self._pdf_manager)
        self._pages["analysis"] = analysis_page
        self._stack.addWidget(analysis_page)

        # Strona "Automatyzacja"
        automation_page = AutomationPage(self._pdf_manager)
        self._pages["automation"] = automation_page
        self._stack.addWidget(automation_page)

        # Strona "Ustawienia"
        settings_page = SettingsPage(self._pdf_manager)
        self._pages["settings"] = settings_page
        self._stack.addWidget(settings_page)

    def _setup_statusbar(self) -> None:
        """Tworzy pasek stanu."""
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("Gotowy")

    def _connect_signals(self) -> None:
        """Łączy sygnały."""
        # Sidebar navigation
        self._sidebar.page_changed.connect(self._on_page_changed)

    # === Handlers ===

    def _on_page_changed(self, page_id: str) -> None:
        """Obsługa zmiany strony."""
        if page_id in self._pages:
            self._stack.setCurrentWidget(self._pages[page_id])

    def _on_open_file(self) -> None:
        """Obsługa otwierania pliku."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Otwórz plik PDF",
            "",
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)"
        )

        if filepath:
            self._load_document(filepath)

    def _load_document(self, filepath: str) -> None:
        """Ładuje dokument PDF."""
        try:
            # Anuluj trwające generowanie miniatur
            if self._thumbnail_manager:
                self._thumbnail_manager.cancel()

            # Załaduj dokument
            self._pdf_manager.load(filepath)

            # Aktualizuj UI
            filename = Path(filepath).name
            self._file_path_label.setText(filename)
            self._file_path_label.setToolTip(filepath)

            # Utwórz menedżer miniatur
            if not self._thumbnail_manager:
                self._thumbnail_manager = ThumbnailManager(self._pdf_manager)
                self._thumbnail_manager.start()

                # Połącz sygnały z widokiem stron
                if "pages" in self._pages:
                    pages_view = self._pages["pages"]
                    self._thumbnail_manager.signals.thumbnail_ready.connect(
                        pages_view.on_thumbnail_ready
                    )
                    self._thumbnail_manager.signals.progress.connect(
                        self._on_thumbnail_progress
                    )
                    self._thumbnail_manager.signals.all_complete.connect(
                        self._on_thumbnails_complete
                    )

            # Powiadom widoki o załadowaniu dokumentu
            for page_id in ["pages", "redaction", "watermark", "tools", "security", "analysis", "automation"]:
                if page_id in self._pages:
                    self._pages[page_id].on_document_loaded()

            # Rozpocznij generowanie miniatur
            self._thumbnail_manager.request_all_thumbnails(200)

            self._statusbar.showMessage(
                f"Załadowano: {filename} ({self._pdf_manager.page_count} stron)"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie można otworzyć pliku:\n{e}"
            )

    def _on_thumbnail_progress(self, completed: int, total: int) -> None:
        """Aktualizacja postępu generowania miniatur."""
        self._statusbar.showMessage(f"Generowanie miniatur: {completed}/{total}")

    def _on_thumbnails_complete(self) -> None:
        """Zakończenie generowania miniatur."""
        self._statusbar.showMessage("Gotowy")

    # === Events ===

    def closeEvent(self, event: QCloseEvent) -> None:
        """Obsługa zamykania okna."""
        # Zatrzymaj wątek miniatur
        if self._thumbnail_manager:
            self._thumbnail_manager.stop()

        # Sprawdź niezapisane zmiany
        if self._pdf_manager.is_modified:
            reply = QMessageBox.question(
                self,
                "Niezapisane zmiany",
                "Dokument ma niezapisane zmiany.\nCzy chcesz je zapisać?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Save:
                self._on_save_file()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return

        # Zamknij dokument
        self._pdf_manager.close()
        event.accept()

    def _on_save_file(self) -> None:
        """Obsługa zapisywania pliku."""
        if not self._pdf_manager.is_loaded:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz plik PDF",
            "",
            "Pliki PDF (*.pdf)"
        )

        if filepath:
            try:
                self._pdf_manager.save(filepath)
                self._statusbar.showMessage(f"Zapisano: {filepath}")
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Błąd",
                    f"Nie można zapisać pliku:\n{e}"
                )

    # === Auto-update ===

    def _check_for_updates(self) -> None:
        """Sprawdza aktualizacje przy starcie."""
        try:
            from pdfdeck.core.updater import UpdateManager, UpdateChannel

            # Wczytaj kanał z ustawień
            channel = self._load_update_channel()

            self._update_manager = UpdateManager(channel)
            self._update_manager.check_complete.connect(self._on_update_check_complete)

            # Sprawdź w tle
            self._update_manager.check_for_updates()
        except Exception as e:
            # Ciche niepowodzenie - nie blokuj startu aplikacji
            print(f"Błąd sprawdzania aktualizacji: {e}")

    def _load_update_channel(self) -> "UpdateChannel":
        """Wczytuje kanał aktualizacji z ustawień."""
        from pdfdeck.core.updater import UpdateChannel
        import json

        config_path = Path.home() / ".pdfdeck" / "settings.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    channel = settings.get("update_channel", "stable")
                    return UpdateChannel.BETA if channel == "beta" else UpdateChannel.STABLE
        except Exception:
            pass
        return UpdateChannel.STABLE

    def _on_update_check_complete(self, result: "UpdateCheckResult") -> None:
        """Obsługa wyniku sprawdzenia aktualizacji."""
        if result.update_available:
            from pdfdeck.ui.dialogs.update_dialog import UpdateDialog

            UpdateDialog.show_update_dialog(result, self)

    # === Public API ===

    @property
    def pdf_manager(self) -> PDFManager:
        """Zwraca menedżer PDF."""
        return self._pdf_manager

    @property
    def thumbnail_manager(self) -> Optional[ThumbnailManager]:
        """Zwraca menedżer miniatur."""
        return self._thumbnail_manager
