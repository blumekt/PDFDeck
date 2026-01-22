"""
PDFDeck Widgets - Reużywalne komponenty UI.
"""

from pdfdeck.ui.widgets.styled_button import StyledButton, IconButton
from pdfdeck.ui.widgets.styled_toggle import StyledToggle, LabeledToggle
from pdfdeck.ui.widgets.styled_combo import StyledComboBox, LabeledComboBox
from pdfdeck.ui.widgets.thumbnail_grid import ThumbnailGrid
from pdfdeck.ui.widgets.stamp_picker import StampPicker, PRESET_STAMPS
from pdfdeck.ui.widgets.diff_viewer import DiffViewer
from pdfdeck.ui.widgets.interactive_page_preview import (
    InteractivePagePreview,
    PageGraphicsView,
)

__all__ = [
    "StyledButton",
    "IconButton",
    "StyledToggle",
    "LabeledToggle",
    "StyledComboBox",
    "LabeledComboBox",
    "ThumbnailGrid",
    "StampPicker",
    "PRESET_STAMPS",
    "DiffViewer",
    "InteractivePagePreview",
    "PageGraphicsView",
]
