"""
PDFDeck Core - Backend logika PDF.
"""

from pdfdeck.core.pdf_manager import PDFManager
from pdfdeck.core.thumbnail_worker import ThumbnailWorker, ThumbnailManager
from pdfdeck.core.diff_engine import DiffEngine, DiffResult
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
