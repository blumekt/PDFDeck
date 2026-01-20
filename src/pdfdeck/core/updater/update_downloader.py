"""
UpdateDownloader - Pobieranie aktualizacji w wątku tła.

Używa wzorca Worker Object (zalecany przez Qt).
Komunikacja przez sygnały/sloty.
"""

import base64
import hashlib
import tempfile
import urllib.request
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from pdfdeck.core.models import UpdateInfo


class UpdateDownloadSignals(QObject):
    """Sygnały dla downloadera aktualizacji."""

    # Postęp pobierania (downloaded_bytes, total_bytes)
    progress = pyqtSignal(int, int)

    # Pobieranie zakończone (ścieżka do pliku)
    finished = pyqtSignal(str)

    # Błąd (komunikat błędu)
    error = pyqtSignal(str)

    # Weryfikacja SHA512
    verification_started = pyqtSignal()
    verification_complete = pyqtSignal(bool)  # True = OK


class UpdateDownloader(QObject):
    """
    Worker do pobierania aktualizacji w wątku tła.

    Użycie:
        self.download_thread = QThread()
        self.downloader = UpdateDownloader()
        self.downloader.moveToThread(self.download_thread)

        self.downloader.signals.progress.connect(self.on_progress)
        self.downloader.signals.finished.connect(self.on_download_complete)
        self.downloader.signals.error.connect(self.on_error)

        self.download_thread.start()
    """

    CHUNK_SIZE = 8192

    def __init__(self) -> None:
        super().__init__()
        self._cancelled = False
        self.signals = UpdateDownloadSignals()

    @pyqtSlot(object)
    def download(self, update_info: UpdateInfo) -> None:
        """
        Pobiera plik instalatora.

        Args:
            update_info: Informacje o aktualizacji (URL, SHA512, rozmiar)
        """
        self._cancelled = False

        try:
            # Utwórz folder tymczasowy
            temp_dir = Path(tempfile.gettempdir()) / "pdfdeck_updates"
            temp_dir.mkdir(exist_ok=True)

            filepath = temp_dir / update_info.filename

            # Pobierz plik
            req = urllib.request.Request(
                update_info.download_url, headers={"User-Agent": "PDFDeck-Updater"}
            )

            with urllib.request.urlopen(req, timeout=300) as response:
                total_size = int(
                    response.headers.get("content-length", update_info.size)
                )
                downloaded = 0

                with open(filepath, "wb") as f:
                    while not self._cancelled:
                        chunk = response.read(self.CHUNK_SIZE)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.signals.progress.emit(downloaded, total_size)

            if self._cancelled:
                # Usuń częściowo pobrany plik
                if filepath.exists():
                    filepath.unlink()
                return

            # Weryfikuj SHA512
            self.signals.verification_started.emit()
            is_valid = self._verify_sha512(filepath, update_info.sha512)
            self.signals.verification_complete.emit(is_valid)

            if is_valid:
                self.signals.finished.emit(str(filepath))
            else:
                # Usuń uszkodzony plik
                filepath.unlink()
                self.signals.error.emit(
                    "Weryfikacja SHA512 nie powiodła się. Plik może być uszkodzony."
                )

        except Exception as e:
            self.signals.error.emit(str(e))

    @pyqtSlot()
    def cancel(self) -> None:
        """Anuluje pobieranie."""
        self._cancelled = True

    def _verify_sha512(self, filepath: Path, expected_hash: str) -> bool:
        """Weryfikuje SHA512 pliku (base64)."""
        if not expected_hash:
            # Brak hasha - pomiń weryfikację (kompatybilność wsteczna)
            return True

        sha = hashlib.sha512()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(self.CHUNK_SIZE), b""):
                sha.update(chunk)

        actual_hash = base64.b64encode(sha.digest()).decode("utf-8")
        return actual_hash == expected_hash
