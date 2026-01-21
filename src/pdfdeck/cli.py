"""
PDFDeck CLI - Command-line interface for PDFDeck.

Usage:
    pdfdeck-cli info input.pdf
    pdfdeck-cli merge file1.pdf file2.pdf -o output.pdf
    pdfdeck-cli split input.pdf --pages 1-5 -o output.pdf
    pdfdeck-cli rotate input.pdf --angle 90 -o output.pdf
    pdfdeck-cli compress input.pdf -o output.pdf
    pdfdeck-cli classify document.pdf
    pdfdeck-cli encrypt input.pdf -o output.pdf --password secret
"""

import sys
import argparse
from pathlib import Path
from typing import List, Optional

import fitz  # PyMuPDF

from pdfdeck import __version__
from pdfdeck.core.pdf_manager import PDFManager
from pdfdeck.core.document_classifier import DocumentClassifier
from pdfdeck.core.invoice_parser import InvoiceParser


def cmd_info(args) -> int:
    """Wyświetla informacje o pliku PDF."""
    try:
        doc = fitz.open(str(args.input))

        print(f"Plik: {args.input}")
        print(f"Strony: {len(doc)}")
        print(f"Format: PDF {doc.metadata.get('format', 'nieznany')}")
        print(f"Szyfrowanie: {'Tak' if doc.is_encrypted else 'Nie'}")
        print(f"Autor: {doc.metadata.get('author', '(brak)')}")
        print(f"Tytuł: {doc.metadata.get('title', '(brak)')}")
        print(f"Producent: {doc.metadata.get('producer', '(brak)')}")

        doc.close()
        return 0

    except Exception as e:
        print(f"Błąd: {e}", file=sys.stderr)
        return 1


def cmd_merge(args) -> int:
    """Łączy wiele plików PDF."""
    try:
        if not args.output:
            print("Błąd: brak pliku wyjściowego (-o)", file=sys.stderr)
            return 1

        output_doc = fitz.open()

        for pdf_path in args.inputs:
            doc = fitz.open(str(pdf_path))
            output_doc.insert_pdf(doc)
            doc.close()

        output_doc.save(str(args.output))
        output_doc.close()

        print(f"Połączono {len(args.inputs)} plików do: {args.output}")
        return 0

    except Exception as e:
        print(f"Błąd: {e}", file=sys.stderr)
        return 1


def cmd_split(args) -> int:
    """Dzieli plik PDF na strony."""
    try:
        if not args.output:
            print("Błąd: brak pliku wyjściowego (-o)", file=sys.stderr)
            return 1

        doc = fitz.open(str(args.input))

        # Parsuj zakres stron (np. "1-5" lub "1,3,5")
        pages = parse_page_range(args.pages, len(doc))

        output_doc = fitz.open()
        for page_num in pages:
            output_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

        output_doc.save(str(args.output))
        output_doc.close()
        doc.close()

        print(f"Wyekstrahowano {len(pages)} stron do: {args.output}")
        return 0

    except Exception as e:
        print(f"Błąd: {e}", file=sys.stderr)
        return 1


def cmd_rotate(args) -> int:
    """Obraca strony PDF."""
    try:
        if not args.output:
            print("Błąd: brak pliku wyjściowego (-o)", file=sys.stderr)
            return 1

        doc = fitz.open(str(args.input))

        for page in doc:
            page.set_rotation(args.angle)

        doc.save(str(args.output))
        doc.close()

        print(f"Obrócono wszystkie strony o {args.angle}° i zapisano do: {args.output}")
        return 0

    except Exception as e:
        print(f"Błąd: {e}", file=sys.stderr)
        return 1


def cmd_compress(args) -> int:
    """Kompresuje plik PDF."""
    try:
        if not args.output:
            print("Błąd: brak pliku wyjściowego (-o)", file=sys.stderr)
            return 1

        doc = fitz.open(str(args.input))

        # Zapisz z garbage collection i kompresją
        doc.save(
            str(args.output),
            garbage=4,  # max garbage collection
            deflate=True,  # compression
            clean=True,  # clean up
        )

        original_size = Path(args.input).stat().st_size
        compressed_size = Path(args.output).stat().st_size
        ratio = (1 - compressed_size / original_size) * 100

        doc.close()

        print(f"Skompresowano: {args.input} -> {args.output}")
        print(f"Rozmiar: {original_size} -> {compressed_size} bajtów ({ratio:.1f}% redukcji)")
        return 0

    except Exception as e:
        print(f"Błąd: {e}", file=sys.stderr)
        return 1


def cmd_classify(args) -> int:
    """Klasyfikuje dokument PDF."""
    try:
        classifier = DocumentClassifier()
        result = classifier.classify(Path(args.input))

        print(f"Plik: {args.input}")
        print(f"Kategoria: {result.category}")
        print(f"Pewność: {result.confidence * 100:.1f}%")
        print(f"Sugerowana nazwa: {result.suggested_filename}")
        print(f"Tagi: {', '.join(result.tags)}")

        if args.verbose:
            print("\nWszystkie wyniki:")
            for cat, score in sorted(result.all_scores.items(), key=lambda x: x[1], reverse=True):
                print(f"  {cat}: {score * 100:.1f}%")

        return 0

    except Exception as e:
        print(f"Błąd: {e}", file=sys.stderr)
        return 1


def cmd_parse_invoice(args) -> int:
    """Parsuje fakturę PDF."""
    try:
        parser = InvoiceParser()
        result = parser.parse(Path(args.input))

        if not result.success:
            print(f"Błąd parsowania: {', '.join(result.errors)}", file=sys.stderr)
            return 1

        data = result.data

        print(f"Plik: {args.input}")
        print(f"Numer faktury: {data.invoice_number}")
        print(f"Data wystawienia: {data.issue_date}")
        print(f"NIP sprzedawcy: {data.seller_nip}")
        print(f"NIP nabywcy: {data.buyer_nip}")
        print(f"Kwota netto: {data.net_amount:.2f} {data.currency}")
        print(f"Kwota VAT: {data.vat_amount:.2f} {data.currency}")
        print(f"Kwota brutto: {data.gross_amount:.2f} {data.currency}")
        print(f"Pewność: {data.confidence:.1f}%")

        if result.warnings:
            print("\nUwagi:")
            for warning in result.warnings:
                print(f"  - {warning}")

        if args.json:
            import json
            print("\nJSON:")
            print(parser.to_json(data))

        return 0

    except Exception as e:
        print(f"Błąd: {e}", file=sys.stderr)
        return 1


def cmd_encrypt(args) -> int:
    """Szyfruje plik PDF hasłem."""
    try:
        if not args.output:
            print("Błąd: brak pliku wyjściowego (-o)", file=sys.stderr)
            return 1

        if not args.password:
            print("Błąd: brak hasła (--password)", file=sys.stderr)
            return 1

        doc = fitz.open(str(args.input))

        # Domyślne uprawnienia: drukowanie i wypełnianie formularzy
        permissions = fitz.PDF_PERM_PRINT | fitz.PDF_PERM_FORM

        doc.save(
            str(args.output),
            encryption=fitz.PDF_ENCRYPT_AES_256,  # AES-256
            owner_pw=args.password,
            user_pw=args.user_password if args.user_password else None,
            permissions=permissions,
        )
        doc.close()

        print(f"Zaszyfrowano: {args.input} -> {args.output}")
        print(f"Hasło właściciela: (ustawione)")
        if args.user_password:
            print(f"Hasło użytkownika: (ustawione)")
        return 0

    except Exception as e:
        print(f"Błąd: {e}", file=sys.stderr)
        return 1


def parse_page_range(range_str: str, max_pages: int) -> List[int]:
    """
    Parsuje zakres stron.

    Args:
        range_str: String typu "1-5" lub "1,3,5" lub "1-3,7,9-11"
        max_pages: Maksymalna liczba stron

    Returns:
        Lista numerów stron (0-indexed)
    """
    pages = []

    for part in range_str.split(","):
        part = part.strip()

        if "-" in part:
            start, end = part.split("-")
            start = int(start) - 1  # 1-indexed -> 0-indexed
            end = int(end) - 1
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part) - 1)

    # Filtruj nieprawidłowe strony
    return [p for p in pages if 0 <= p < max_pages]


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="pdfdeck-cli",
        description="PDFDeck - Command-line PDF manipulation tool",
    )
    parser.add_argument("--version", action="version", version=f"PDFDeck {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # === Info ===
    info_parser = subparsers.add_parser("info", help="Display PDF information")
    info_parser.add_argument("input", type=Path, help="Input PDF file")

    # === Merge ===
    merge_parser = subparsers.add_parser("merge", help="Merge multiple PDF files")
    merge_parser.add_argument("inputs", type=Path, nargs="+", help="Input PDF files")
    merge_parser.add_argument("-o", "--output", type=Path, help="Output PDF file")

    # === Split ===
    split_parser = subparsers.add_parser("split", help="Split/extract pages from PDF")
    split_parser.add_argument("input", type=Path, help="Input PDF file")
    split_parser.add_argument("--pages", default="1-", help="Page range (e.g. 1-5, 1,3,5)")
    split_parser.add_argument("-o", "--output", type=Path, help="Output PDF file")

    # === Rotate ===
    rotate_parser = subparsers.add_parser("rotate", help="Rotate PDF pages")
    rotate_parser.add_argument("input", type=Path, help="Input PDF file")
    rotate_parser.add_argument("--angle", type=int, choices=[90, 180, 270], default=90, help="Rotation angle")
    rotate_parser.add_argument("-o", "--output", type=Path, help="Output PDF file")

    # === Compress ===
    compress_parser = subparsers.add_parser("compress", help="Compress/optimize PDF")
    compress_parser.add_argument("input", type=Path, help="Input PDF file")
    compress_parser.add_argument("-o", "--output", type=Path, help="Output PDF file")

    # === Classify ===
    classify_parser = subparsers.add_parser("classify", help="Classify document type")
    classify_parser.add_argument("input", type=Path, help="Input PDF file")
    classify_parser.add_argument("-v", "--verbose", action="store_true", help="Show all scores")

    # === Parse Invoice ===
    invoice_parser = subparsers.add_parser("parse-invoice", help="Parse invoice data")
    invoice_parser.add_argument("input", type=Path, help="Input PDF file")
    invoice_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # === Encrypt ===
    encrypt_parser = subparsers.add_parser("encrypt", help="Encrypt PDF with password")
    encrypt_parser.add_argument("input", type=Path, help="Input PDF file")
    encrypt_parser.add_argument("-o", "--output", type=Path, help="Output PDF file")
    encrypt_parser.add_argument("--password", help="Owner password (required)")
    encrypt_parser.add_argument("--user-password", help="User password (optional)")

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Dispatch to command handler
    commands = {
        "info": cmd_info,
        "merge": cmd_merge,
        "split": cmd_split,
        "rotate": cmd_rotate,
        "compress": cmd_compress,
        "classify": cmd_classify,
        "parse-invoice": cmd_parse_invoice,
        "encrypt": cmd_encrypt,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
