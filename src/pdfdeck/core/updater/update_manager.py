"""
UpdateManager - Zarządzanie procesem aktualizacji.

Koordynuje sprawdzanie i pobieranie aktualizacji.
Zarządza wątkami i cyklem życia komponentów.
"""

import os
from typing import Optional

from PyQt6.QtCore import QMetaObject, QObject, Qt, QThread, pyqtSignal, Q_ARG

from pdfdeck.core.models import UpdateChannel, UpdateCheckResult, UpdateInfo
from pdfdeck.core.updater.update_checker import UpdateChecker
from pdfdeck.core.updater.update_downloader import UpdateDownloader


class UpdateManager(QObject):
    """
    Menedżer aktualizacji.

    Obsługuje cały proces:
    1. Sprawdzanie dostępności aktualizacji
    2. Pobieranie z paskiem postępu
    3. Weryfikacja SHA512
    4. Uruchomienie instalatora
    """

    # Sygnały do UI
    check_complete = pyqtSignal(object)  # UpdateCheckResult
    download_progress = pyqtSignal(int, int)  # (downloaded, total)
    download_complete = pyqtSignal(str)  # filepath
    download_error = pyqtSignal(str)
    verification_started = pyqtSignal()
    verification_complete = pyqtSignal(bool)

    def __init__(self, channel: UpdateChannel = UpdateChannel.STABLE) -> None:
        super().__init__()

        self._checker = UpdateChecker(channel)
        self._downloader: Optional[UpdateDownloader] = None
        self._download_thread: Optional[QThread] = None
        self._current_update: Optional[UpdateInfo] = None

    @property
    def channel(self) -> UpdateChannel:
        return self._checker.channel

    @channel.setter
    def channel(self, value: UpdateChannel) -> None:
        self._checker.channel = value

    @property
    def current_version(self) -> str:
        """Zwraca aktualną wersję aplikacji."""
        return self._checker.current_version

    def check_for_updates(self) -> None:
        """
        Sprawdza aktualizacje (synchronicznie).
        Emituje check_complete z wynikiem.
        """
        result = self._checker.check_for_updates()
        if result.update_info:
            self._current_update = result.update_info
        self.check_complete.emit(result)

    def start_download(self, update_info: Optional[UpdateInfo] = None) -> None:
        """Rozpoczyna pobieranie aktualizacji w wątku tła."""
        if update_info:
            self._current_update = update_info

        if not self._current_update:
            self.download_error.emit("Brak informacji o aktualizacji")
            return

        # Utwórz wątek i workera
        self._download_thread = QThread()
        self._downloader = UpdateDownloader()
        self._downloader.moveToThread(self._download_thread)

        # Połącz sygnały
        self._downloader.signals.progress.connect(self.download_progress.emit)
        self._downloader.signals.finished.connect(self._on_download_finished)
        self._downloader.signals.error.connect(self.download_error.emit)
        self._downloader.signals.verification_started.connect(
            self.verification_started.emit
        )
        self._downloader.signals.verification_complete.connect(
            self.verification_complete.emit
        )

        # Uruchom wątek
        self._download_thread.start()

        # Wywołaj download w wątku workera
        QMetaObject.invokeMethod(
            self._downloader,
            "download",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(object, self._current_update),
        )

    def cancel_download(self) -> None:
        """Anuluje pobieranie."""
        if self._downloader:
            QMetaObject.invokeMethod(
                self._downloader,
                "cancel",
                Qt.ConnectionType.QueuedConnection,
            )

    def _on_download_finished(self, filepath: str) -> None:
        """Obsługa zakończenia pobierania."""
        self._cleanup_thread()
        self.download_complete.emit(filepath)

    def _cleanup_thread(self) -> None:
        """Czyści wątek pobierania."""
        if self._download_thread:
            self._download_thread.quit()
            self._download_thread.wait()
            self._download_thread = None
            self._downloader = None

    def launch_installer(self, filepath: str) -> bool:
        """
        Uruchamia instalator.

        Args:
            filepath: Ścieżka do pliku instalatora

        Returns:
            True jeśli uruchomiono pomyślnie
        """
        try:
            os.startfile(filepath)
            return True
        except Exception:
            return False

    def stop(self) -> None:
        """Zatrzymuje wszystkie operacje."""
        self.cancel_download()
        self._cleanup_thread()
