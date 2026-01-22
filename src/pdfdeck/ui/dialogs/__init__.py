"""
PDFDeck Dialogs - Okna dialogowe.
"""

from pdfdeck.ui.dialogs.whiteout_dialog import WhiteoutDialog
from pdfdeck.ui.dialogs.link_dialog import LinkDialog
from pdfdeck.ui.dialogs.link_manager_dialog import LinkManagerDialog
from pdfdeck.ui.dialogs.text_search_link_dialog import TextSearchLinkDialog
from pdfdeck.ui.dialogs.select_area_link_dialog import SelectAreaLinkDialog
from pdfdeck.ui.dialogs.split_dialog import SplitDialog
from pdfdeck.ui.dialogs.nup_dialog import NupDialog, NupConfig
from pdfdeck.ui.dialogs.signature_dialog import SignatureDialog
from pdfdeck.ui.dialogs.bates_dialog import BatesDialog
from pdfdeck.ui.dialogs.header_footer_dialog import HeaderFooterDialog

__all__ = [
    "WhiteoutDialog",
    "LinkDialog",
    "LinkManagerDialog",
    "TextSearchLinkDialog",
    "SelectAreaLinkDialog",
    "SplitDialog",
    "NupDialog",
    "NupConfig",
    "SignatureDialog",
    "BatesDialog",
    "HeaderFooterDialog",
]
