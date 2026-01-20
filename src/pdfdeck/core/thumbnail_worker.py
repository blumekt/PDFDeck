"""
ThumbnailWorker - Generowanie miniatur w wątku tła.

Używa wzorca Worker Object (zalecany przez Qt).
Komunikacja przez sygnały/sloty.
"""

from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from pdfdeck.core.pdf_manager import PDFManager


class ThumbnailSignals(QObject):
    """Sygnały dla workera miniatur."""

    # Emitowany gdy miniatura jest gotowa
    # Args: (page_index, png_bytes)
    thumbnail_ready = pyqtSignal(int, bytes)

    # Emitowany gdy wszystkie miniatury są gotowe
    all_complete = pyqtSignal()

    # Emitowany przy błędzie
    # Args: (page_index, error_message)
    error = pyqtSignal(int, str)

    # Aktualizacja postępu
    # Args: (completed_count, total_count)
    progress = pyqtSignal(int, int)


class ThumbnailWorker(QObject):
    """
    Worker do generowania miniatur w wątku tła.

    Użycie:
        # W MainWindow.__init__:
        self.thumbnail_thread = QThread()
        self.thumbnail_worker = ThumbnailWorker(self.pdf_manager)
        self.thumbnail_worker.moveToThread(self.thumbnail_thread)

        # Połącz sygnały
        self.request_thumbnails.connect(self.thumbnail_worker.generate_all)
        self.thumbnail_worker.signals.thumbnail_ready.connect(self.on_thumbnail_ready)

        # Uruchom wątek
        self.thumbnail_thread.start()
    """

    def __init__(self, pdf_manager: "PDFManager") -> None:
        super().__init__()
        self._pdf_manager = pdf_manager
        self._cancelled = False
        self.signals = ThumbnailSignals()

    @pyqtSlot(int)
    def generate_all(self, max_size: int = 200) -> None:
        """
        Generuje miniatury dla wszystkich stron.

        Wywoływane z głównego wątku przez sygnał,
        wykonywane w wątku workera.

        Args:
            max_size: Maksymalny wymiar miniatury
        """
        self._cancelled = False

        if not self._pdf_manager.is_loaded:
            self.signals.error.emit(-1, "Brak załadowanego dokumentu")
            return

        total = self._pdf_manager.page_count

        for i in range(total):
            if self._cancelled:
                break

            try:
                png_data = self._pdf_manager.generate_thumbnail(i, max_size)
                self.signals.thumbnail_ready.emit(i, png_data)
            except Exception as e:
                self.signals.error.emit(i, str(e))

            self.signals.progress.emit(i + 1, total)

        self.signals.all_complete.emit()

    @pyqtSlot(int, int)
    def generate_single(self, page_index: int, max_size: int = 200) -> None:
        """
        Generuje miniaturę dla pojedynczej strony.

        Args:
            page_index: Indeks strony
            max_size: Maksymalny wymiar miniatury
        """
        try:
            png_data = self._pdf_manager.generate_thumbnail(page_index, max_size)
            self.signals.thumbnail_ready.emit(page_index, png_data)
        except Exception as e:
            self.signals.error.emit(page_index, str(e))

    @pyqtSlot(list, int)
    def generate_range(self, page_indices: list, max_size: int = 200) -> None:
        """
        Generuje miniatury dla zakresu stron.

        Args:
            page_indices: Lista indeksów stron
            max_size: Maksymalny wymiar miniatury
        """
        self._cancelled = False
        total = len(page_indices)

        for idx, page_index in enumerate(page_indices):
            if self._cancelled:
                break

            try:
                png_data = self._pdf_manager.generate_thumbnail(page_index, max_size)
                self.signals.thumbnail_ready.emit(page_index, png_data)
            except Exception as e:
                self.signals.error.emit(page_index, str(e))

            self.signals.progress.emit(idx + 1, total)

        self.signals.all_complete.emit()

    @pyqtSlot()
    def cancel(self) -> None:
        """Anuluje trwające generowanie miniatur."""
        self._cancelled = True


class PreviewWorker(QObject):
    """
    Worker do generowania podglądów wysokiej rozdzielczości.
    """

    # Sygnał gdy podgląd jest gotowy
    # Args: (page_index, png_bytes)
    preview_ready = pyqtSignal(int, bytes)

    # Sygnał błędu
    error = pyqtSignal(int, str)

    def __init__(self, pdf_manager: "PDFManager") -> None:
        super().__init__()
        self._pdf_manager = pdf_manager

    @pyqtSlot(int, int)
    def generate_preview(self, page_index: int, dpi: int = 150) -> None:
        """
        Generuje podgląd strony w wysokiej rozdzielczości.

        Args:
            page_index: Indeks strony
            dpi: Rozdzielczość
        """
        try:
            png_data = self._pdf_manager.generate_preview(page_index, dpi)
            self.preview_ready.emit(page_index, png_data)
        except Exception as e:
            self.error.emit(page_index, str(e))


class ThumbnailManager:
    """
    Menedżer do zarządzania wątkiem i workerem miniatur.

    Upraszcza tworzenie i zarządzanie cyklem życia wątku.
    """

    def __init__(self, pdf_manager: "PDFManager") -> None:
        self._pdf_manager = pdf_manager

        # Utwórz wątek i workera
        self._thread = QThread()
        self._worker = ThumbnailWorker(pdf_manager)
        self._worker.moveToThread(self._thread)

        # Podgląd
        self._preview_thread = QThread()
        self._preview_worker = PreviewWorker(pdf_manager)
        self._preview_worker.moveToThread(self._preview_thread)

    @property
    def signals(self) -> ThumbnailSignals:
        """Zwraca sygnały workera."""
        return self._worker.signals

    @property
    def preview_ready(self):
        """Sygnał gdy podgląd jest gotowy."""
        return self._preview_worker.preview_ready

    @property
    def preview_error(self):
        """Sygnał błędu podglądu."""
        return self._preview_worker.error

    def start(self) -> None:
        """Uruchamia wątki."""
        self._thread.start()
        self._preview_thread.start()

    def stop(self) -> None:
        """Zatrzymuje wątki."""
        self._worker.cancel()

        self._thread.quit()
        self._thread.wait()

        self._preview_thread.quit()
        self._preview_thread.wait()

    def request_all_thumbnails(self, max_size: int = 200) -> None:
        """Żąda wygenerowania wszystkich miniatur."""
        # Używamy invokeMethod dla thread-safe wywołania
        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG

        QMetaObject.invokeMethod(
            self._worker,
            "generate_all",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(int, max_size),
        )

    def request_single_thumbnail(self, page_index: int, max_size: int = 200) -> None:
        """Żąda wygenerowania pojedynczej miniatury."""
        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG

        QMetaObject.invokeMethod(
            self._worker,
            "generate_single",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(int, page_index),
            Q_ARG(int, max_size),
        )

    def request_preview(self, page_index: int, dpi: int = 150) -> None:
        """Żąda wygenerowania podglądu."""
        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG

        QMetaObject.invokeMethod(
            self._preview_worker,
            "generate_preview",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(int, page_index),
            Q_ARG(int, dpi),
        )

    def cancel(self) -> None:
        """Anuluje generowanie."""
        from PyQt6.QtCore import QMetaObject, Qt

        QMetaObject.invokeMethod(
            self._worker,
            "cancel",
            Qt.ConnectionType.QueuedConnection,
        )
