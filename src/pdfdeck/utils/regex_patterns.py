"""
Predefiniowane wzorce regex dla Smart Redaction (RODO/GDPR).

Wzorce dla polskich danych osobowych i wrażliwych.
"""

from typing import Dict

# Predefiniowane wzorce do redakcji
REDACTION_PATTERNS: Dict[str, str] = {
    # Numery identyfikacyjne
    "pesel": r"\b\d{11}\b",
    "nip": r"\b\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}\b|\b\d{10}\b",
    "regon": r"\b\d{9}\b|\b\d{14}\b",
    "dowod": r"\b[A-Z]{3}\s?\d{6}\b",
    "paszport": r"\b[A-Z]{2}\s?\d{7}\b",

    # Kontakt
    "email": r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b",
    "phone": r"\b(?:\+48\s?)?\d{3}[-\s]?\d{3}[-\s]?\d{3}\b",
    "phone_landline": r"\b\(\d{2}\)\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}\b",

    # Finanse
    "iban": r"\b[A-Z]{2}\d{2}\s?(?:\d{4}\s?){4,6}\d{0,4}\b",
    "card_number": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",

    # Daty i kwoty
    "date_pl": r"\b\d{2}[./-]\d{2}[./-]\d{4}\b",
    "date_iso": r"\b\d{4}[-/]\d{2}[-/]\d{2}\b",
    "money_pln": r"\b\d{1,3}(?:[\s,]\d{3})*(?:[.,]\d{2})?\s?(?:PLN|zł|złotych)\b",
    "money_eur": r"\b\d{1,3}(?:[\s,]\d{3})*(?:[.,]\d{2})?\s?(?:EUR|€|euro)\b",

    # Adresy
    "postal_code": r"\b\d{2}[-\s]?\d{3}\b",
    "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",

    # Inne
    "url": r"\bhttps?://[\w\-._~:/?#\[\]@!$&'()*+,;=%]+\b",
}

# Opisy wzorców (do wyświetlenia w UI)
PATTERN_DESCRIPTIONS: Dict[str, str] = {
    "pesel": "PESEL (11 cyfr)",
    "nip": "NIP (XXX-XXX-XX-XX lub 10 cyfr)",
    "regon": "REGON (9 lub 14 cyfr)",
    "dowod": "Nr dowodu osobistego (AAA 123456)",
    "paszport": "Nr paszportu (AA 1234567)",
    "email": "Adres e-mail",
    "phone": "Nr telefonu komórkowego (+48 XXX XXX XXX)",
    "phone_landline": "Nr telefonu stacjonarnego ((XX) XXX-XX-XX)",
    "iban": "Numer konta bankowego IBAN",
    "card_number": "Numer karty płatniczej",
    "date_pl": "Data (DD.MM.RRRR)",
    "date_iso": "Data ISO (RRRR-MM-DD)",
    "money_pln": "Kwota w PLN",
    "money_eur": "Kwota w EUR",
    "postal_code": "Kod pocztowy (XX-XXX)",
    "ip_address": "Adres IP",
    "url": "Adres URL",
}


def get_pattern_description(pattern_name: str) -> str:
    """Zwraca opis wzorca."""
    return PATTERN_DESCRIPTIONS.get(pattern_name, pattern_name)
