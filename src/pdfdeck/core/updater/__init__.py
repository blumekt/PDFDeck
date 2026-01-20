"""
PDFDeck Auto-Updater.

Moduł odpowiedzialny za sprawdzanie i pobieranie aktualizacji.
"""

from pdfdeck.core.models import UpdateChannel, UpdateCheckResult, UpdateInfo
from pdfdeck.core.updater.update_checker import UpdateChecker
from pdfdeck.core.updater.update_downloader import UpdateDownloader
from pdfdeck.core.updater.update_manager import UpdateManager

__all__ = [
    "UpdateChannel",
    "UpdateCheckResult",
    "UpdateChecker",
    "UpdateDownloader",
    "UpdateInfo",
    "UpdateManager",
]
