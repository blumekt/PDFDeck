"""
i18n - System internacjonalizacji PDFDeck.

Obsługuje języki: polski, angielski, niemiecki, francuski.
"""

import json
from pathlib import Path
from typing import Dict, Optional, Callable, List

from PyQt6.QtCore import QObject, pyqtSignal


class I18n(QObject):
    """
    Menedżer tłumaczeń.

    Singleton zapewniający dostęp do tłumaczeń z całej aplikacji.
    """

    # Sygnał zmiany języka
    language_changed = pyqtSignal(str)

    # Dostępne języki
    LANGUAGES = {
        "pl": "Polski",
        "en": "English",
        "de": "Deutsch",
        "fr": "Français",
    }

    _instance: Optional["I18n"] = None

    def __new__(cls) -> "I18n":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        super().__init__()
        self._initialized = True
        self._current_language = "pl"
        self._translations: Dict[str, Dict[str, str]] = {}
        self._translations_path: Optional[Path] = None

    def set_translations_path(self, path: Path) -> None:
        """Ustawia ścieżkę do katalogu z tłumaczeniami."""
        self._translations_path = path
        self._load_translations()

    def _load_translations(self) -> None:
        """Ładuje wszystkie pliki tłumaczeń."""
        if not self._translations_path:
            return

        for lang_code in self.LANGUAGES.keys():
            filepath = self._translations_path / f"{lang_code}.json"
            if filepath.exists():
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        self._translations[lang_code] = json.load(f)
                except Exception as e:
                    print(f"Błąd ładowania tłumaczeń {lang_code}: {e}")
                    self._translations[lang_code] = {}
            else:
                self._translations[lang_code] = {}

    def set_language(self, lang_code: str) -> None:
        """Zmienia aktualny język."""
        if lang_code in self.LANGUAGES and lang_code != self._current_language:
            self._current_language = lang_code
            self.language_changed.emit(lang_code)

    @property
    def current_language(self) -> str:
        """Zwraca kod aktualnego języka."""
        return self._current_language

    @property
    def current_language_name(self) -> str:
        """Zwraca nazwę aktualnego języka."""
        return self.LANGUAGES.get(self._current_language, "Polski")

    def get_available_languages(self) -> List[tuple]:
        """Zwraca listę dostępnych języków jako (kod, nazwa)."""
        return list(self.LANGUAGES.items())

    def t(self, key: str, **kwargs) -> str:
        """
        Zwraca tłumaczenie dla klucza.

        Args:
            key: Klucz tłumaczenia (np. "menu.pages")
            **kwargs: Parametry do formatowania

        Returns:
            Przetłumaczony tekst lub klucz jeśli brak tłumaczenia
        """
        translations = self._translations.get(self._current_language, {})

        # Obsługa zagnieżdżonych kluczy (np. "menu.pages")
        keys = key.split(".")
        value = translations

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                value = None
                break

        if value is None:
            # Fallback do angielskiego
            if self._current_language != "en":
                en_translations = self._translations.get("en", {})
                value = en_translations
                for k in keys:
                    if isinstance(value, dict):
                        value = value.get(k)
                    else:
                        value = None
                        break

        if value is None:
            return key

        # Formatowanie z parametrami
        if kwargs and isinstance(value, str):
            try:
                return value.format(**kwargs)
            except KeyError:
                return value

        return value if isinstance(value, str) else key


# Globalna instancja
_i18n = I18n()


def get_i18n() -> I18n:
    """Zwraca globalną instancję I18n."""
    return _i18n


def t(key: str, **kwargs) -> str:
    """Skrót do tłumaczenia."""
    return _i18n.t(key, **kwargs)


def set_language(lang_code: str) -> None:
    """Skrót do zmiany języka."""
    _i18n.set_language(lang_code)
