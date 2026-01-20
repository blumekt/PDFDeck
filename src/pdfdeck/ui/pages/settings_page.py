"""
SettingsPage - Strona ustawień aplikacji.

Funkcje:
- Wybór języka (PL, EN, DE, FR)
- Zapisywanie preferencji
"""

from typing import TYPE_CHECKING
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QMessageBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt

from pdfdeck.ui.pages.base_page import BasePage
from pdfdeck.ui.widgets.styled_button import StyledButton
from pdfdeck.ui.widgets.styled_combo import StyledComboBox
from pdfdeck.utils.i18n import get_i18n, t

if TYPE_CHECKING:
    from pdfdeck.core.pdf_manager import PDFManager


class SettingsPage(BasePage):
    """
    Strona ustawień aplikacji.

    Układ:
    +------------------------------------------+
    |  Tytuł: Ustawienia                       |
    +------------------------------------------+
    |  +------------------+                    |
    |  | Język            |                    |
    |  | [Polski v]       |                    |
    |  +------------------+                    |
    +------------------------------------------+
    """

    def __init__(self, pdf_manager: "PDFManager" = None, parent=None):
        super().__init__(t("settings.title"), parent)

        self._i18n = get_i18n()
        self._config_path = self._get_config_path()
        self._setup_settings_ui()
        self._load_settings()

        # Połącz sygnał zmiany języka
        self._i18n.language_changed.connect(self._on_language_changed)

    def _get_config_path(self) -> Path:
        """Zwraca ścieżkę do pliku konfiguracji."""
        config_dir = Path.home() / ".pdfdeck"
        config_dir.mkdir(exist_ok=True)
        return config_dir / "settings.json"

    def _setup_settings_ui(self) -> None:
        """Tworzy interfejs ustawień."""
        # Scroll area dla całej zawartości
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(self._scroll_style())

        # Kontener wewnętrzny
        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 10, 0)
        content_layout.setSpacing(15)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # === Grupa: Język ===
        language_group = QGroupBox(t("settings.language"))
        language_group.setStyleSheet(self._group_style())
        language_layout = QVBoxLayout(language_group)

        # Opis
        lang_desc = QLabel(t("settings.language_desc"))
        lang_desc.setStyleSheet("color: #8892a0; font-size: 13px;")
        lang_desc.setWordWrap(True)
        language_layout.addWidget(lang_desc)

        # Wybór języka
        lang_row = QHBoxLayout()

        self._language_combo = StyledComboBox()
        for code, name in self._i18n.get_available_languages():
            self._language_combo.addItem(name, code)

        # Ustaw aktualny język
        current_idx = self._language_combo.findData(self._i18n.current_language)
        if current_idx >= 0:
            self._language_combo.setCurrentIndex(current_idx)

        self._language_combo.currentIndexChanged.connect(self._on_language_selected)
        lang_row.addWidget(self._language_combo)
        lang_row.addStretch()

        language_layout.addLayout(lang_row)

        # Informacja o restarcie
        self._restart_label = QLabel(t("settings.restart_required"))
        self._restart_label.setStyleSheet("color: #e0a800; font-size: 12px; font-style: italic;")
        self._restart_label.setVisible(False)
        language_layout.addWidget(self._restart_label)

        content_layout.addWidget(language_group)

        # === Grupa: Informacje ===
        info_group = QGroupBox("PDFDeck")
        info_group.setStyleSheet(self._group_style())
        info_layout = QVBoxLayout(info_group)

        from pdfdeck import __version__
        version_label = QLabel(f"Wersja: {__version__}")
        version_label.setStyleSheet("color: #8892a0; font-size: 13px;")
        info_layout.addWidget(version_label)

        content_layout.addWidget(info_group)
        content_layout.addStretch()

        scroll.setWidget(content)
        self.add_widget(scroll)

    def _scroll_style(self) -> str:
        """Zwraca styl dla QScrollArea."""
        return """
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #0f1629;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #2d3a50;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #e0a800;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """

    def _group_style(self) -> str:
        """Zwraca styl dla QGroupBox."""
        return """
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                border: 1px solid #2d3a50;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
        """

    def _on_language_selected(self, index: int) -> None:
        """Obsługa wyboru języka."""
        lang_code = self._language_combo.currentData()
        if lang_code and lang_code != self._i18n.current_language:
            self._i18n.set_language(lang_code)
            self._save_settings()
            self._restart_label.setVisible(True)

    def _on_language_changed(self, lang_code: str) -> None:
        """Obsługa zmiany języka."""
        # Tutaj można by odświeżyć teksty, ale wymaga przebudowy UI
        pass

    def _load_settings(self) -> None:
        """Ładuje ustawienia z pliku."""
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)

                lang = settings.get("language", "pl")
                if lang in dict(self._i18n.get_available_languages()):
                    self._i18n.set_language(lang)

                    idx = self._language_combo.findData(lang)
                    if idx >= 0:
                        self._language_combo.blockSignals(True)
                        self._language_combo.setCurrentIndex(idx)
                        self._language_combo.blockSignals(False)

            except Exception as e:
                print(f"Błąd ładowania ustawień: {e}")

    def _save_settings(self) -> None:
        """Zapisuje ustawienia do pliku."""
        settings = {
            "language": self._i18n.current_language
        }

        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Błąd zapisywania ustawień: {e}")

    # === Public API ===

    def on_document_loaded(self) -> None:
        """Wywoływane po załadowaniu dokumentu."""
        pass
