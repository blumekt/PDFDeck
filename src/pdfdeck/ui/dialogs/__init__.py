"""
PDFDeck Dialogs - Okna dialogowe.
"""

from pdfdeck.ui.dialogs.whiteout_dialog import WhiteoutDialog
from pdfdeck.ui.dialogs.link_dialog import LinkDialog
from pdfdeck.ui.dialogs.split_dialog import SplitDialog
from pdfdeck.ui.dialogs.nup_dialog import NupDialog, NupConfig
from pdfdeck.ui.dialogs.signature_dialog import SignatureDialog
from pdfdeck.ui.dialogs.bates_dialog import BatesDialog
from pdfdeck.ui.dialogs.header_footer_dialog import HeaderFooterDialog

__all__ = [
    "WhiteoutDialog",
    "LinkDialog",
    "SplitDialog",
    "NupDialog",
    "NupConfig",
    "SignatureDialog",
    "BatesDialog",
    "HeaderFooterDialog",
]
