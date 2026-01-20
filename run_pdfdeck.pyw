#!/usr/bin/env python
"""
Uruchom PDFDeck bez okna konsoli.
Plik .pyw na Windows automatycznie używa pythonw.exe
"""
import sys
from pathlib import Path

# Dodaj src do ścieżki
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from pdfdeck.__main__ import main

if __name__ == "__main__":
    main()
