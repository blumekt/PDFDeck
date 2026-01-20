"""
Inicjalizacja aplikacji PyQt6.

Odpowiada za:
- Tworzenie QApplication
- Ładowanie stylów (QSS)
- Uruchamianie głównego okna
"""

import sys
from pathlib import Path
from typing import List

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from pdfdeck import __version__, __app_name__


def get_resources_path() -> Path:
    """Zwraca ścieżkę do katalogu resources."""
    # W trybie development
    dev_path = Path(__file__).parent.parent.parent / "resources"
    if dev_path.exists():
        return dev_path

    # W trybie frozen (PyInstaller)
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / "resources"

    return dev_path


def load_stylesheet() -> str:
    """Ładuje stylesheet QSS z pliku."""
    qss_path = get_resources_path() / "styles" / "dark_theme.qss"

    if qss_path.exists():
        return qss_path.read_text(encoding="utf-8")

    # Fallback - podstawowy ciemny motyw
    return """
    QWidget {
        background-color: #16213e;
        color: #ffffff;
        font-family: "Segoe UI", Arial, sans-serif;
        font-size: 14px;
    }
    """


def init_i18n() -> None:
    """Inicjalizuje system tłumaczeń."""
    from pdfdeck.utils.i18n import get_i18n

    i18n = get_i18n()
    translations_path = get_resources_path() / "translations"
    i18n.set_translations_path(translations_path)

    # Załaduj zapisany język z ustawień
    config_path = Path.home() / ".pdfdeck" / "settings.json"
    if config_path.exists():
        try:
            import json
            with open(config_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
            lang = settings.get("language", "pl")
            i18n.set_language(lang)
        except Exception:
            pass


def run_app(argv: List[str]) -> int:
    """
    Uruchamia aplikację PDFDeck.

    Args:
        argv: Argumenty linii poleceń

    Returns:
        Kod wyjścia aplikacji
    """
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("PDFDeck")

    # Inicjalizuj i18n
    init_i18n()

    # Ustaw ikonę aplikacji
    icon_path = get_resources_path() / "icons" / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Załaduj stylesheet
    stylesheet = load_stylesheet()
    app.setStyleSheet(stylesheet)

    # Import tutaj, żeby uniknąć circular imports
    from pdfdeck.ui.main_window import MainWindow

    # Utwórz i pokaż główne okno
    window = MainWindow()
    window.show()

    return app.exec()
