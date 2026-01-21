"""
InvoiceParser - Automatyczna ekstrakcja danych z faktur PDF.

Funkcje:
- Rozpoznawanie struktury faktury
- Ekstrakcja kluczowych pól (NIP, kwoty, daty)
- Walidacja NIP
- Eksport do JSON/CSV
"""

import re
import json
import csv
import io
from dataclasses import dataclass, field, asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

import fitz  # PyMuPDF


@dataclass
class InvoiceItem:
    """Pozycja na fakturze."""
    name: str = ""
    quantity: float = 0.0
    unit: str = ""
    unit_price: float = 0.0
    net_amount: float = 0.0
    vat_rate: str = ""
    vat_amount: float = 0.0
    gross_amount: float = 0.0


@dataclass
class InvoiceData:
    """Dane faktury."""
    # Identyfikacja
    invoice_number: str = ""
    invoice_type: str = "Faktura VAT"

    # Daty
    issue_date: str = ""
    sale_date: str = ""
    due_date: str = ""

    # Sprzedawca
    seller_name: str = ""
    seller_address: str = ""
    seller_nip: str = ""
    seller_bank_account: str = ""

    # Nabywca
    buyer_name: str = ""
    buyer_address: str = ""
    buyer_nip: str = ""

    # Kwoty
    net_amount: float = 0.0
    vat_amount: float = 0.0
    gross_amount: float = 0.0
    currency: str = "PLN"

    # Pozycje
    items: List[InvoiceItem] = field(default_factory=list)

    # Dodatkowe
    payment_method: str = ""
    notes: str = ""
    source_file: str = ""

    # Pewność ekstrakcji (0-100)
    confidence: float = 0.0


@dataclass
class InvoiceParseResult:
    """Wynik parsowania faktury."""
    success: bool
    data: Optional[InvoiceData] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class InvoiceParser:
    """
    Parser faktur PDF.

    Automatycznie wykrywa i ekstrahuje dane z polskich faktur.
    """

    # Wzorce regex do rozpoznawania pól
    PATTERNS = {
        # Numer faktury
        "invoice_number": [
            r"(?:Faktura|Invoice|FV|F\.?\s*VAT)[:\s]*(?:nr|no\.?|#)?\s*[:\s]*([A-Za-z0-9\-/]+)",
            r"Nr\s+faktury[:\s]*([A-Za-z0-9\-/]+)",
            r"Numer[:\s]*([A-Za-z0-9\-/]+)",
        ],

        # NIP
        "nip": [
            r"NIP[:\s]*(\d{3}[\-\s]?\d{3}[\-\s]?\d{2}[\-\s]?\d{2})",
            r"NIP[:\s]*(\d{10})",
        ],

        # IBAN / Konto bankowe
        "bank_account": [
            r"(?:IBAN|Konto|Nr\s+konta)[:\s]*([A-Z]{2}\d{2}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4})",
            r"(\d{2}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4})",
        ],

        # Daty
        "date": [
            r"(\d{4}[\-./]\d{2}[\-./]\d{2})",  # YYYY-MM-DD
            r"(\d{2}[\-./]\d{2}[\-./]\d{4})",  # DD-MM-YYYY
            r"(\d{2}\s+\w+\s+\d{4})",  # DD Month YYYY
        ],

        # Kwoty
        "amount": [
            r"(\d{1,3}(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:PLN|zł|EUR|USD)?",
        ],

        # Kwota brutto (priorytet)
        "gross_amount": [
            r"(?:Razem|Suma|Łącznie|Total|Brutto|Gross|Do\s+zapłaty)[:\s]*(\d{1,3}(?:[\s,]\d{3})*[.,]\d{2})",
            r"(\d{1,3}(?:[\s,]\d{3})*[.,]\d{2})\s*(?:PLN|zł)\s*(?:brutto|gross)?",
        ],

        # Kwota netto
        "net_amount": [
            r"(?:Netto|Net)[:\s]*(\d{1,3}(?:[\s,]\d{3})*[.,]\d{2})",
            r"Wartość\s+netto[:\s]*(\d{1,3}(?:[\s,]\d{3})*[.,]\d{2})",
        ],

        # VAT
        "vat_amount": [
            r"(?:VAT|PTU)[:\s]*(\d{1,3}(?:[\s,]\d{3})*[.,]\d{2})",
            r"Podatek[:\s]*(\d{1,3}(?:[\s,]\d{3})*[.,]\d{2})",
        ],

        # Data wystawienia
        "issue_date": [
            r"(?:Data\s+wystawienia|Data\s+faktury|Wystawiono)[:\s]*(\d{2}[\-./]\d{2}[\-./]\d{4}|\d{4}[\-./]\d{2}[\-./]\d{2})",
        ],

        # Data sprzedaży
        "sale_date": [
            r"(?:Data\s+sprzedaży|Data\s+wykonania)[:\s]*(\d{2}[\-./]\d{2}[\-./]\d{4}|\d{4}[\-./]\d{2}[\-./]\d{2})",
        ],

        # Termin płatności
        "due_date": [
            r"(?:Termin\s+płatności|Płatność\s+do|Zapłata\s+do)[:\s]*(\d{2}[\-./]\d{2}[\-./]\d{4}|\d{4}[\-./]\d{2}[\-./]\d{2})",
        ],

        # Metoda płatności
        "payment_method": [
            r"(?:Forma\s+płatności|Metoda\s+płatności|Płatność)[:\s]*(przelew|gotówka|karta|przedpłata)",
        ],
    }

    def __init__(self):
        self._text = ""
        self._blocks: List[Dict] = []

    def parse(self, pdf_path: Path) -> InvoiceParseResult:
        """
        Parsuje fakturę PDF i ekstrahuje dane.

        Args:
            pdf_path: Ścieżka do pliku PDF

        Returns:
            InvoiceParseResult z danymi lub błędami
        """
        errors = []
        warnings = []

        try:
            # Otwórz dokument
            doc = fitz.open(str(pdf_path))

            if len(doc) == 0:
                return InvoiceParseResult(
                    success=False,
                    errors=["Dokument jest pusty"]
                )

            # Ekstrahuj tekst ze wszystkich stron
            self._text = ""
            self._blocks = []

            for page in doc:
                self._text += page.get_text()
                blocks = page.get_text("dict")["blocks"]
                self._blocks.extend(blocks)

            doc.close()

            # Parsuj dane
            data = InvoiceData(source_file=pdf_path.name)

            # Numer faktury
            data.invoice_number = self._find_first("invoice_number") or ""
            if not data.invoice_number:
                warnings.append("Nie znaleziono numeru faktury")

            # NIP-y
            nips = self._find_all_nip()
            if len(nips) >= 1:
                data.seller_nip = nips[0]
                if not self.validate_nip(data.seller_nip):
                    warnings.append(f"NIP sprzedawcy {data.seller_nip} może być nieprawidłowy")
            if len(nips) >= 2:
                data.buyer_nip = nips[1]
                if not self.validate_nip(data.buyer_nip):
                    warnings.append(f"NIP nabywcy {data.buyer_nip} może być nieprawidłowy")

            # Daty
            data.issue_date = self._find_first("issue_date") or ""
            data.sale_date = self._find_first("sale_date") or ""
            data.due_date = self._find_first("due_date") or ""

            # Kwoty
            gross = self._find_first("gross_amount")
            if gross:
                data.gross_amount = self._parse_amount(gross)

            net = self._find_first("net_amount")
            if net:
                data.net_amount = self._parse_amount(net)

            vat = self._find_first("vat_amount")
            if vat:
                data.vat_amount = self._parse_amount(vat)

            # Konto bankowe
            data.seller_bank_account = self._find_first("bank_account") or ""

            # Metoda płatności
            payment = self._find_first("payment_method")
            if payment:
                data.payment_method = payment.capitalize()

            # Próbuj wyciągnąć nazwy firm
            seller, buyer = self._extract_company_names()
            if seller:
                data.seller_name = seller
            if buyer:
                data.buyer_name = buyer

            # Oblicz pewność
            data.confidence = self._calculate_confidence(data)

            if data.confidence < 30:
                warnings.append("Niska pewność ekstrakcji - zweryfikuj dane ręcznie")

            return InvoiceParseResult(
                success=True,
                data=data,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            return InvoiceParseResult(
                success=False,
                errors=[f"Błąd parsowania: {str(e)}"]
            )

    def _find_first(self, pattern_name: str) -> Optional[str]:
        """Znajduje pierwsze dopasowanie dla danego wzorca."""
        patterns = self.PATTERNS.get(pattern_name, [])

        for pattern in patterns:
            match = re.search(pattern, self._text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()

        return None

    def _find_all_nip(self) -> List[str]:
        """Znajduje wszystkie NIP-y w dokumencie."""
        nips = []
        seen = set()

        for pattern in self.PATTERNS["nip"]:
            for match in re.finditer(pattern, self._text, re.IGNORECASE):
                nip = self._normalize_nip(match.group(1))
                if nip and nip not in seen:
                    nips.append(nip)
                    seen.add(nip)

        return nips

    def _normalize_nip(self, nip: str) -> str:
        """Normalizuje NIP do formatu bez myślników."""
        return re.sub(r"[\s\-]", "", nip)

    def _parse_amount(self, amount_str: str) -> float:
        """Parsuje kwotę do float."""
        try:
            # Usuń spacje i zamień przecinek na kropkę
            cleaned = amount_str.replace(" ", "").replace(",", ".")
            # Usuń walutę
            cleaned = re.sub(r"[A-Za-złzłPLNEURUSD]", "", cleaned)
            return float(cleaned)
        except (ValueError, AttributeError):
            return 0.0

    def _extract_company_names(self) -> Tuple[Optional[str], Optional[str]]:
        """Próbuje wyciągnąć nazwy firm sprzedawcy i nabywcy."""
        seller = None
        buyer = None

        # Szukaj sekcji "Sprzedawca" i "Nabywca"
        seller_match = re.search(
            r"Sprzedawca[:\s]*\n?([^\n]+)",
            self._text,
            re.IGNORECASE
        )
        if seller_match:
            seller = seller_match.group(1).strip()

        buyer_match = re.search(
            r"(?:Nabywca|Odbiorca|Kupujący)[:\s]*\n?([^\n]+)",
            self._text,
            re.IGNORECASE
        )
        if buyer_match:
            buyer = buyer_match.group(1).strip()

        return seller, buyer

    def _calculate_confidence(self, data: InvoiceData) -> float:
        """Oblicza pewność ekstrakcji (0-100)."""
        score = 0
        max_score = 0

        # Numer faktury (15 punktów)
        max_score += 15
        if data.invoice_number:
            score += 15

        # NIP sprzedawcy (15 punktów)
        max_score += 15
        if data.seller_nip:
            score += 10
            if self.validate_nip(data.seller_nip):
                score += 5

        # NIP nabywcy (10 punktów)
        max_score += 10
        if data.buyer_nip:
            score += 7
            if self.validate_nip(data.buyer_nip):
                score += 3

        # Data wystawienia (10 punktów)
        max_score += 10
        if data.issue_date:
            score += 10

        # Kwota brutto (20 punktów)
        max_score += 20
        if data.gross_amount > 0:
            score += 20

        # Kwota netto (10 punktów)
        max_score += 10
        if data.net_amount > 0:
            score += 10

        # VAT (10 punktów)
        max_score += 10
        if data.vat_amount > 0:
            score += 10

        # Spójność kwot (10 punktów)
        max_score += 10
        if data.net_amount > 0 and data.vat_amount > 0 and data.gross_amount > 0:
            expected_gross = data.net_amount + data.vat_amount
            tolerance = data.gross_amount * 0.02  # 2% tolerancja
            if abs(expected_gross - data.gross_amount) <= tolerance:
                score += 10

        return (score / max_score) * 100 if max_score > 0 else 0

    @staticmethod
    def validate_nip(nip: str) -> bool:
        """
        Waliduje NIP (polska suma kontrolna).

        Args:
            nip: Numer NIP (z lub bez myślników)

        Returns:
            True jeśli NIP jest prawidłowy
        """
        # Normalizuj
        nip = re.sub(r"[\s\-]", "", nip)

        if len(nip) != 10:
            return False

        try:
            digits = [int(d) for d in nip]
        except ValueError:
            return False

        # Wagi dla sumy kontrolnej
        weights = [6, 5, 7, 2, 3, 4, 5, 6, 7]

        # Oblicz sumę kontrolną
        checksum = sum(digits[i] * weights[i] for i in range(9))
        expected = checksum % 11

        # Cyfra kontrolna (ostatnia) musi być równa oczekiwanej
        # Jeśli expected == 10, NIP jest nieprawidłowy
        return expected != 10 and expected == digits[9]

    def to_json(self, data: InvoiceData) -> str:
        """Konwertuje dane faktury do JSON."""
        d = asdict(data)
        d["items"] = [asdict(item) for item in data.items]
        return json.dumps(d, ensure_ascii=False, indent=2)

    def to_csv_row(self, data: InvoiceData) -> Dict[str, Any]:
        """Konwertuje dane faktury do słownika dla CSV."""
        return {
            "Numer faktury": data.invoice_number,
            "Data wystawienia": data.issue_date,
            "Data sprzedaży": data.sale_date,
            "Termin płatności": data.due_date,
            "NIP sprzedawcy": data.seller_nip,
            "Sprzedawca": data.seller_name,
            "NIP nabywcy": data.buyer_nip,
            "Nabywca": data.buyer_name,
            "Kwota netto": data.net_amount,
            "Kwota VAT": data.vat_amount,
            "Kwota brutto": data.gross_amount,
            "Waluta": data.currency,
            "Metoda płatności": data.payment_method,
            "Plik źródłowy": data.source_file,
            "Pewność [%]": round(data.confidence, 1),
        }

    def batch_parse(
        self,
        pdf_paths: List[Path],
        progress_callback: Optional[callable] = None
    ) -> List[InvoiceParseResult]:
        """
        Parsuje wiele faktur.

        Args:
            pdf_paths: Lista ścieżek do plików PDF
            progress_callback: Callback(current, total, filename)

        Returns:
            Lista wyników parsowania
        """
        results = []
        total = len(pdf_paths)

        for i, path in enumerate(pdf_paths):
            if progress_callback:
                progress_callback(i + 1, total, path.name)

            result = self.parse(path)
            results.append(result)

        return results

    def export_batch_csv(
        self,
        results: List[InvoiceParseResult],
        output_path: Path
    ) -> None:
        """Eksportuje wyniki batch do CSV."""
        rows = []

        for result in results:
            if result.success and result.data:
                rows.append(self.to_csv_row(result.data))

        if not rows:
            return

        # Zapisz CSV
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    def export_batch_json(
        self,
        results: List[InvoiceParseResult],
        output_path: Path
    ) -> None:
        """Eksportuje wyniki batch do JSON."""
        data = []

        for result in results:
            if result.success and result.data:
                d = asdict(result.data)
                d["items"] = [asdict(item) for item in result.data.items]
                data.append(d)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# === Funkcje pomocnicze ===

def parse_invoice(pdf_path: Path) -> InvoiceParseResult:
    """Szybka funkcja do parsowania pojedynczej faktury."""
    parser = InvoiceParser()
    return parser.parse(pdf_path)


def validate_polish_nip(nip: str) -> bool:
    """Waliduje polski NIP."""
    return InvoiceParser.validate_nip(nip)
