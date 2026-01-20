"""
Entry point dla PDFDeck.

Uruchomienie:
    python -m pdfdeck
    lub
    pdfdeck (po instalacji)
"""

import sys


def hide_console() -> None:
    """Ukrywa okno konsoli na Windows."""
    if sys.platform == "win32":
        import ctypes
        # Pobierz uchwyt okna konsoli
        kernel32 = ctypes.windll.kernel32
        console_window = kernel32.GetConsoleWindow()
        if console_window:
            user32 = ctypes.windll.user32
            # SW_HIDE = 0
            user32.ShowWindow(console_window, 0)


def main() -> int:
    """Główna funkcja uruchamiająca aplikację."""
    hide_console()
    from pdfdeck.app import run_app
    return run_app(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
