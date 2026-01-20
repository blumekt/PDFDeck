"""
UpdateDialog - Dialog aktualizacji aplikacji.

Pokazuje:
- Informacje o nowej wersji
- Postęp pobierania
- Status weryfikacji
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent

from pdfdeck.core.models import UpdateCheckResult
from pdfdeck.core.updater.update_manager import UpdateManager
from pdfdeck.ui.widgets.styled_button import StyledButton


class UpdateDialog(QDialog):
    """
    Dialog informujący o dostępnej aktualizacji.

    Stany:
    1. Informacja o nowej wersji (pobierz / pomiń)
    2. Pobieranie z paskiem postępu
    3. Weryfikacja SHA512
    4. Gotowe do instalacji
    """

    def __init__(self, update_result: UpdateCheckResult, parent=None):
        super().__init__(parent)

        self._update_result = update_result
        self._manager = UpdateManager()
        self._downloaded_path: Optional[str] = None

        self.setWindowTitle("Aktualizacja PDFDeck")
        self.setMinimumWidth(450)
        self.setModal(True)
        self.setStyleSheet(self._dialog_style())

        self._setup_ui()
        self._connect_signals()

    def _dialog_style(self) -> str:
        """Zwraca styl dialogu (dark theme)."""
        return """
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
            QProgressBar {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #e0a800;
                border-radius: 3px;
            }
        """

    def _setup_ui(self) -> None:
        """Tworzy interfejs."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # === Informacje o wersji ===
        info_group = QGroupBox("Dostępna aktualizacja")
        info_layout = QVBoxLayout(info_group)

        version_label = QLabel(
            f"Nowa wersja: <b>{self._update_result.latest_version}</b>"
        )
        version_label.setStyleSheet("font-size: 16px;")
        info_layout.addWidget(version_label)

        current_label = QLabel(
            f"Twoja wersja: {self._update_result.current_version}"
        )
        current_label.setStyleSheet("color: #8892a0; font-size: 13px;")
        info_layout.addWidget(current_label)

        if self._update_result.update_info:
            size_mb = self._update_result.update_info.size_mb
            if size_mb > 0:
                size_label = QLabel(f"Rozmiar: {size_mb:.1f} MB")
                size_label.setStyleSheet("color: #8892a0; font-size: 13px;")
                info_layout.addWidget(size_label)

        layout.addWidget(info_group)

        # === Postęp pobierania (ukryty na początku) ===
        self._progress_group = QGroupBox("Pobieranie")
        progress_layout = QVBoxLayout(self._progress_group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        progress_layout.addWidget(self._progress_bar)

        self._status_label = QLabel("Przygotowanie...")
        self._status_label.setStyleSheet("color: #8892a0; font-size: 12px;")
        progress_layout.addWidget(self._status_label)

        self._progress_group.setVisible(False)
        layout.addWidget(self._progress_group)

        # === Przyciski ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self._skip_btn = StyledButton("Pomiń", "secondary")
        self._skip_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self._skip_btn)

        self._download_btn = StyledButton("Pobierz i zainstaluj", "primary")
        self._download_btn.clicked.connect(self._on_download)
        buttons_layout.addWidget(self._download_btn)

        self._install_btn = StyledButton("Zainstaluj teraz", "success")
        self._install_btn.clicked.connect(self._on_install)
        self._install_btn.setVisible(False)
        buttons_layout.addWidget(self._install_btn)

        layout.addLayout(buttons_layout)

    def _connect_signals(self) -> None:
        """Łączy sygnały managera."""
        self._manager.download_progress.connect(self._on_progress)
        self._manager.download_complete.connect(self._on_complete)
        self._manager.download_error.connect(self._on_error)
        self._manager.verification_started.connect(self._on_verification_started)
        self._manager.verification_complete.connect(self._on_verification_complete)

    def _on_download(self) -> None:
        """Rozpoczyna pobieranie."""
        self._download_btn.setEnabled(False)
        self._skip_btn.setText("Anuluj")
        self._skip_btn.clicked.disconnect()
        self._skip_btn.clicked.connect(self._on_cancel)

        self._progress_group.setVisible(True)
        self._status_label.setText("Pobieranie...")

        # Ustaw info o aktualizacji i zacznij
        self._manager.start_download(self._update_result.update_info)

    def _on_cancel(self) -> None:
        """Anuluje pobieranie."""
        self._manager.cancel_download()
        self.reject()

    def _on_progress(self, downloaded: int, total: int) -> None:
        """Aktualizuje pasek postępu."""
        if total > 0:
            percent = int((downloaded / total) * 100)
            self._progress_bar.setValue(percent)

            downloaded_mb = downloaded / 1024 / 1024
            total_mb = total / 1024 / 1024
            self._status_label.setText(
                f"Pobrano: {downloaded_mb:.1f} / {total_mb:.1f} MB"
            )

    def _on_verification_started(self) -> None:
        """Rozpoczęto weryfikację."""
        self._status_label.setText("Weryfikacja integralności pliku...")
        self._progress_bar.setMaximum(0)  # Indeterminate

    def _on_verification_complete(self, success: bool) -> None:
        """Zakończono weryfikację."""
        self._progress_bar.setMaximum(100)
        if success:
            self._status_label.setText("Weryfikacja pomyślna")
            self._status_label.setStyleSheet("color: #27ae60; font-size: 12px;")
        else:
            self._status_label.setText("Weryfikacja nie powiodła się!")
            self._status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")

    def _on_complete(self, filepath: str) -> None:
        """Pobieranie zakończone."""
        self._downloaded_path = filepath
        self._progress_bar.setValue(100)

        self._skip_btn.setText("Zamknij")
        self._skip_btn.clicked.disconnect()
        self._skip_btn.clicked.connect(self.reject)

        self._download_btn.setVisible(False)
        self._install_btn.setVisible(True)

    def _on_error(self, error: str) -> None:
        """Obsługa błędu."""
        self._status_label.setText(f"Błąd: {error}")
        self._status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)

        self._skip_btn.setText("Zamknij")
        self._skip_btn.clicked.disconnect()
        self._skip_btn.clicked.connect(self.reject)
        self._download_btn.setEnabled(True)

    def _on_install(self) -> None:
        """Uruchamia instalator."""
        if self._downloaded_path:
            if self._manager.launch_installer(self._downloaded_path):
                # Zamknij aplikację (instalator przejmie)
                from PyQt6.QtWidgets import QApplication

                QApplication.instance().quit()
            else:
                self._status_label.setText("Nie można uruchomić instalatora")
                self._status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")

    def closeEvent(self, event: QCloseEvent) -> None:
        """Zamykanie dialogu."""
        self._manager.stop()
        super().closeEvent(event)

    # === Static method (wzorzec z WhiteoutDialog) ===

    @staticmethod
    def show_update_dialog(update_result: UpdateCheckResult, parent=None) -> bool:
        """
        Wyświetla dialog aktualizacji.

        Args:
            update_result: Wynik sprawdzenia aktualizacji
            parent: Okno rodzica

        Returns:
            True jeśli użytkownik zaakceptował instalację
        """
        if not update_result.update_available:
            return False

        dialog = UpdateDialog(update_result, parent)
        return dialog.exec() == QDialog.DialogCode.Accepted
