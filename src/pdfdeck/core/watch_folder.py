"""
WatchFolder - Automatyczne przetwarzanie plików PDF.

Funkcje:
- Monitorowanie folderu wejściowego
- Automatyczne stosowanie profilu przetwarzania
- Przenoszenie przetworzonych do folderu wyjściowego
- Historia operacji
"""

import time
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Callable
from enum import Enum

from pdfdeck.core.processing_profile import ProcessingProfile, ProcessingAction
from pdfdeck.core.pdf_manager import PDFManager
from pdfdeck.core.models import WatermarkConfig, StampConfig


class ProcessingStatus(Enum):
    """Status przetwarzania pliku."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class ProcessingLogEntry:
    """Wpis w logu przetwarzania."""
    timestamp: datetime
    filename: str
    status: ProcessingStatus
    message: str
    output_path: Optional[Path] = None


class WatchFolderService:
    """
    Serwis monitorowania folderu.

    Obserwuje folder wejściowy i automatycznie przetwarza
    nowe pliki PDF według wybranego profilu.
    """

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._watch_dir: Optional[Path] = None
        self._output_dir: Optional[Path] = None
        self._profile: Optional[ProcessingProfile] = None
        self._processed_files: set = set()
        self._log: List[ProcessingLogEntry] = []
        self._on_file_processed: Optional[Callable[[ProcessingLogEntry], None]] = None
        self._check_interval: float = 2.0  # sekundy

    def start(
        self,
        watch_dir: Path,
        output_dir: Path,
        profile: ProcessingProfile,
        on_file_processed: Optional[Callable[[ProcessingLogEntry], None]] = None,
    ) -> bool:
        """
        Rozpoczyna monitorowanie folderu.

        Args:
            watch_dir: Folder do monitorowania
            output_dir: Folder wyjściowy
            profile: Profil przetwarzania
            on_file_processed: Callback wywoływany po przetworzeniu pliku

        Returns:
            True jeśli uruchomiono pomyślnie
        """
        if self._running:
            return False

        # Walidacja ścieżek
        if not watch_dir.exists():
            return False

        output_dir.mkdir(parents=True, exist_ok=True)

        self._watch_dir = watch_dir
        self._output_dir = output_dir
        self._profile = profile
        self._on_file_processed = on_file_processed
        self._running = True

        # Uruchom wątek monitorowania
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

        self._add_log_entry(
            "System",
            ProcessingStatus.SUCCESS,
            f"Rozpoczęto monitorowanie: {watch_dir}"
        )

        return True

    def stop(self) -> None:
        """Zatrzymuje monitorowanie."""
        self._running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

        self._add_log_entry(
            "System",
            ProcessingStatus.SUCCESS,
            "Zatrzymano monitorowanie"
        )

    def _watch_loop(self) -> None:
        """Główna pętla monitorowania."""
        while self._running:
            try:
                self._check_for_new_files()
            except Exception as e:
                self._add_log_entry(
                    "System",
                    ProcessingStatus.ERROR,
                    f"Błąd monitorowania: {e}"
                )

            time.sleep(self._check_interval)

    def _check_for_new_files(self) -> None:
        """Sprawdza nowe pliki PDF w folderze."""
        if not self._watch_dir:
            return

        for pdf_path in self._watch_dir.glob("*.pdf"):
            # Pomiń już przetworzone pliki
            if str(pdf_path) in self._processed_files:
                continue

            # Pomiń pliki, które są jeszcze kopiowane
            if not self._is_file_ready(pdf_path):
                continue

            # Przetwórz plik
            self._process_file(pdf_path)

    def _is_file_ready(self, filepath: Path) -> bool:
        """
        Sprawdza czy plik jest gotowy do przetworzenia.

        Czeka aż rozmiar pliku się ustabilizuje (zakończone kopiowanie).
        """
        try:
            size1 = filepath.stat().st_size
            time.sleep(0.5)
            size2 = filepath.stat().st_size
            return size1 == size2 and size1 > 0
        except Exception:
            return False

    def _process_file(self, pdf_path: Path) -> None:
        """Przetwarza pojedynczy plik PDF."""
        self._processed_files.add(str(pdf_path))

        self._add_log_entry(
            pdf_path.name,
            ProcessingStatus.PROCESSING,
            "Rozpoczęto przetwarzanie"
        )

        try:
            # Wczytaj PDF
            manager = PDFManager()
            manager.load(pdf_path)

            # Wykonaj akcje z profilu
            for action in self._profile.actions:
                self._execute_action(manager, action)

            # Generuj nazwę pliku wyjściowego
            output_name = f"{pdf_path.stem}{self._profile.output_suffix}.pdf"
            output_path = self._output_dir / output_name

            # Zapisz
            optimize = ProcessingAction.COMPRESS in self._profile.actions
            manager.save(output_path, optimize=optimize)
            manager.close()

            self._add_log_entry(
                pdf_path.name,
                ProcessingStatus.SUCCESS,
                f"Przetworzono pomyślnie",
                output_path
            )

        except Exception as e:
            self._add_log_entry(
                pdf_path.name,
                ProcessingStatus.ERROR,
                f"Błąd: {e}"
            )

    def _execute_action(
        self, manager: PDFManager, action: ProcessingAction
    ) -> None:
        """Wykonuje pojedynczą akcję na dokumencie."""
        if action == ProcessingAction.NORMALIZE_A4:
            manager.normalize_to_a4()

        elif action == ProcessingAction.SCRUB_METADATA:
            manager.scrub_metadata()

        elif action == ProcessingAction.FLATTEN:
            manager.flatten()

        elif action == ProcessingAction.ADD_WATERMARK:
            config = self._get_watermark_config()
            if config:
                manager.add_watermark(config)

        elif action == ProcessingAction.ADD_STAMP:
            config = self._get_stamp_config()
            if config:
                # Dodaj pieczątkę do wszystkich stron
                for page_idx in range(manager.page_count):
                    manager.add_stamp(page_idx, config)

        elif action == ProcessingAction.ADD_BATES:
            # Bates wymaga osobnego przetwarzania, pomijamy w batch
            pass

        elif action == ProcessingAction.CONVERT_PDFA:
            # PDF/A konwersja wymaga osobnego przetwarzania
            pass

    def _get_watermark_config(self) -> Optional[WatermarkConfig]:
        """Pobiera WatermarkConfig z profilu lub referencji."""
        # Najpierw sprawdź czy jest zapisany profil
        if self._profile.watermark_profile_name:
            from pdfdeck.core.profile_manager import ProfileManager
            pm = ProfileManager()
            wp = pm.get_watermark_profile(self._profile.watermark_profile_name)
            if wp:
                return wp.config

        # Fallback do legacy parametrów
        if self._profile.watermark_text:
            return WatermarkConfig(
                text=self._profile.watermark_text,
                opacity=self._profile.watermark_opacity,
                rotation=self._profile.watermark_rotation,
            )

        return None

    def _get_stamp_config(self) -> Optional[StampConfig]:
        """Pobiera StampConfig z profilu."""
        if self._profile.stamp_profile_name:
            from pdfdeck.core.profile_manager import ProfileManager
            pm = ProfileManager()
            sp = pm.get_stamp_profile(self._profile.stamp_profile_name)
            if sp:
                return sp.config

        return None

    def _add_log_entry(
        self,
        filename: str,
        status: ProcessingStatus,
        message: str,
        output_path: Optional[Path] = None,
    ) -> None:
        """Dodaje wpis do logu."""
        entry = ProcessingLogEntry(
            timestamp=datetime.now(),
            filename=filename,
            status=status,
            message=message,
            output_path=output_path,
        )
        self._log.append(entry)

        # Ogranicz rozmiar logu
        if len(self._log) > 1000:
            self._log = self._log[-500:]

        # Wywołaj callback
        if self._on_file_processed:
            self._on_file_processed(entry)

    @property
    def is_running(self) -> bool:
        """Sprawdza czy serwis działa."""
        return self._running

    @property
    def log(self) -> List[ProcessingLogEntry]:
        """Zwraca log przetwarzania."""
        return self._log.copy()

    def get_statistics(self) -> dict:
        """Zwraca statystyki przetwarzania."""
        total = len([e for e in self._log if e.filename != "System"])
        success = len([e for e in self._log if e.status == ProcessingStatus.SUCCESS and e.filename != "System"])
        errors = len([e for e in self._log if e.status == ProcessingStatus.ERROR])

        return {
            "total_processed": total,
            "successful": success,
            "errors": errors,
            "is_running": self._running,
            "watch_dir": str(self._watch_dir) if self._watch_dir else None,
            "output_dir": str(self._output_dir) if self._output_dir else None,
        }

    def clear_processed_cache(self) -> None:
        """Czyści pamięć przetworzonych plików."""
        self._processed_files.clear()

    def clear_log(self) -> None:
        """Czyści log."""
        self._log.clear()
