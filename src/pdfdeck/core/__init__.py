"""
PDFDeck Core - Backend logika PDF.
"""

from pdfdeck.core.pdf_manager import PDFManager
from pdfdeck.core.thumbnail_worker import ThumbnailWorker, ThumbnailManager
from pdfdeck.core.diff_engine import DiffEngine, DiffResult
from pdfdeck.core.ocr_engine import OCREngine, OCRConfig, OCRResult
from pdfdeck.core.processing_profile import ProcessingProfile, ProcessingAction, PRESET_PROFILES
from pdfdeck.core.watch_folder import WatchFolderService, ProcessingLogEntry, ProcessingStatus
from pdfdeck.core.header_footer import HeaderFooterEngine, HeaderFooterConfig, HeaderFooterResult
from pdfdeck.core.invoice_parser import InvoiceParser, InvoiceData, InvoiceParseResult
from pdfdeck.core.document_classifier import DocumentClassifier, ClassificationResult, DocumentFeatures
from pdfdeck.core.models import (
    PageInfo,
    Rect,
    Point,
    WhiteoutConfig,
    LinkConfig,
    WatermarkConfig,
    StampConfig,
    StampShape,
    BorderStyle,
    WearLevel,
    SearchResult,
    DocumentMetadata,
)
from pdfdeck.core.stamp_renderer import StampRenderer

__all__ = [
    "PDFManager",
    "ThumbnailWorker",
    "ThumbnailManager",
    "DiffEngine",
    "DiffResult",
    "OCREngine",
    "OCRConfig",
    "OCRResult",
    "ProcessingProfile",
    "ProcessingAction",
    "PRESET_PROFILES",
    "WatchFolderService",
    "ProcessingLogEntry",
    "ProcessingStatus",
    "HeaderFooterEngine",
    "HeaderFooterConfig",
    "HeaderFooterResult",
    "InvoiceParser",
    "InvoiceData",
    "InvoiceParseResult",
    "DocumentClassifier",
    "ClassificationResult",
    "DocumentFeatures",
    "PageInfo",
    "Rect",
    "Point",
    "WhiteoutConfig",
    "LinkConfig",
    "WatermarkConfig",
    "StampConfig",
    "StampShape",
    "BorderStyle",
    "WearLevel",
    "StampRenderer",
    "SearchResult",
    "DocumentMetadata",
]
