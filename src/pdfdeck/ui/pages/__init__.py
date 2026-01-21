"""
PDFDeck Pages - Widoki/strony aplikacji.
"""

from pdfdeck.ui.pages.base_page import BasePage, PlaceholderPage, ScrollablePage
from pdfdeck.ui.pages.pages_view import PagesView
from pdfdeck.ui.pages.redaction_page import RedactionPage
from pdfdeck.ui.pages.watermark_page import WatermarkPage
from pdfdeck.ui.pages.security_page import SecurityPage
from pdfdeck.ui.pages.tools_page import ToolsPage
from pdfdeck.ui.pages.analysis_page import AnalysisPage
from pdfdeck.ui.pages.automation_page import AutomationPage
from pdfdeck.ui.pages.ocr_page import OCRPage
from pdfdeck.ui.pages.watch_folder_page import WatchFolderPage
from pdfdeck.ui.pages.settings_page import SettingsPage

__all__ = [
    "BasePage",
    "PlaceholderPage",
    "ScrollablePage",
    "PagesView",
    "RedactionPage",
    "WatermarkPage",
    "SecurityPage",
    "ToolsPage",
    "AnalysisPage",
    "AutomationPage",
    "OCRPage",
    "WatchFolderPage",
    "SettingsPage",
]
