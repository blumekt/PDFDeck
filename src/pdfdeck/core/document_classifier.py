"""
DocumentClassifier - Automatyczna klasyfikacja dokumentów PDF.

Funkcje:
- Klasyfikacja typu dokumentu (faktura, umowa, CV, etc.)
- Sugestia nazwy pliku
- Automatyczne tagowanie
- Możliwość trenowania własnego modelu
"""

import re
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Any
from collections import Counter

import fitz  # PyMuPDF

# Opcjonalne: scikit-learn dla zaawansowanej klasyfikacji
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import Pipeline
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


@dataclass
class ClassificationResult:
    """Wynik klasyfikacji dokumentu."""
    category: str
    confidence: float  # 0.0 - 1.0
    all_scores: Dict[str, float]  # wszystkie kategorie z wynikami
    suggested_filename: str
    tags: List[str]


@dataclass
class DocumentFeatures:
    """Cechy dokumentu do klasyfikacji."""
    text: str
    page_count: int
    has_tables: bool
    has_images: bool
    keywords: List[str]
    dates_found: List[str]
    amounts_found: List[str]
    nip_count: int
    email_count: int


class DocumentClassifier:
    """
    Klasyfikator typów dokumentów PDF.

    Kategorie:
    - faktura: Faktury VAT, rachunki
    - umowa: Umowy, kontrakty
    - pismo_urzedowe: Pisma urzędowe, decyzje
    - cv: CV, życiorysy
    - raport: Raporty, sprawozdania
    - oferta: Oferty handlowe
    - inne: Dokumenty nie pasujące do innych kategorii
    """

    CATEGORIES = [
        "faktura",
        "umowa",
        "pismo_urzedowe",
        "cv",
        "raport",
        "oferta",
        "inne",
    ]

    # Słowa kluczowe dla każdej kategorii (rule-based fallback)
    CATEGORY_KEYWORDS = {
        "faktura": [
            "faktura", "invoice", "vat", "netto", "brutto", "kwota",
            "termin płatności", "nip", "sprzedawca", "nabywca",
            "wartość", "stawka", "podatek", "rachunek", "paragon"
        ],
        "umowa": [
            "umowa", "contract", "strony", "przedmiot umowy", "warunki",
            "zobowiązania", "paragraf", "§", "aneks", "wypowiedzenie",
            "zleceniodawca", "zleceniobiorca", "najemca", "wynajmujący"
        ],
        "pismo_urzedowe": [
            "decyzja", "postanowienie", "wezwanie", "zawiadomienie",
            "urząd", "minister", "dyrektor", "zarządzenie", "rozporzadzenie",
            "na podstawie", "art.", "ustawa", "dz.u.", "obwieszczenie"
        ],
        "cv": [
            "curriculum vitae", "cv", "doświadczenie zawodowe", "wykształcenie",
            "umiejętności", "języki obce", "hobby", "zainteresowania",
            "stanowisko", "pracodawca", "kariera", "resume"
        ],
        "raport": [
            "raport", "sprawozdanie", "podsumowanie", "wnioski",
            "analiza", "zestawienie", "wykres", "tabela", "statystyka",
            "wyniki", "kwartał", "rok", "miesięczny", "roczny"
        ],
        "oferta": [
            "oferta", "cennik", "propozycja", "quotation", "proposal",
            "rabat", "zniżka", "promocja", "dostawa", "wykonanie",
            "zakres", "termin realizacji", "wartość zamówienia"
        ],
    }

    # Wzorce regex do ekstrakcji cech
    PATTERNS = {
        "date": r"\d{2}[./-]\d{2}[./-]\d{4}|\d{4}[./-]\d{2}[./-]\d{2}",
        "amount": r"\d{1,3}(?:[\s,]\d{3})*[.,]\d{2}\s*(?:PLN|zł|EUR|USD)?",
        "nip": r"NIP[:\s]*\d{3}[\-\s]?\d{3}[\-\s]?\d{2}[\-\s]?\d{2}",
        "email": r"[\w.-]+@[\w.-]+\.\w+",
        "phone": r"(?:\+48\s?)?\d{3}[\s-]?\d{3}[\s-]?\d{3}",
    }

    def __init__(self, model_path: Optional[Path] = None):
        """
        Inicjalizuje klasyfikator.

        Args:
            model_path: Ścieżka do zapisanego modelu (opcjonalnie)
        """
        self._model = None
        self._vectorizer = None

        if model_path and model_path.exists() and SKLEARN_AVAILABLE:
            try:
                self._model = joblib.load(model_path)
            except Exception:
                pass

        if self._model is None and SKLEARN_AVAILABLE:
            # Domyślny pipeline
            self._model = Pipeline([
                ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
                ("clf", MultinomialNB()),
            ])
            self._is_trained = False
        else:
            self._is_trained = self._model is not None

    def classify(self, pdf_path: Path) -> ClassificationResult:
        """
        Klasyfikuje dokument PDF.

        Args:
            pdf_path: Ścieżka do pliku PDF

        Returns:
            ClassificationResult z kategorią i pewnością
        """
        # Ekstrahuj cechy
        features = self._extract_features(pdf_path)

        # Klasyfikacja
        if self._is_trained and SKLEARN_AVAILABLE:
            category, confidence, all_scores = self._classify_ml(features)
        else:
            category, confidence, all_scores = self._classify_rules(features)

        # Tagi
        tags = self._generate_tags(features, category)

        # Sugerowana nazwa
        suggested_name = self._suggest_filename(features, category, pdf_path.name)

        return ClassificationResult(
            category=category,
            confidence=confidence,
            all_scores=all_scores,
            suggested_filename=suggested_name,
            tags=tags,
        )

    def _extract_features(self, pdf_path: Path) -> DocumentFeatures:
        """Ekstrahuje cechy dokumentu."""
        doc = fitz.open(str(pdf_path))

        text = ""
        has_images = False

        for page in doc:
            text += page.get_text()
            if page.get_images():
                has_images = True

        # Sprawdź tabele
        has_tables = False
        try:
            for page in doc:
                tables = page.find_tables()
                if tables:
                    has_tables = True
                    break
        except Exception:
            pass

        doc.close()

        # Znajdź wzorce
        dates = re.findall(self.PATTERNS["date"], text)
        amounts = re.findall(self.PATTERNS["amount"], text)
        nips = re.findall(self.PATTERNS["nip"], text, re.IGNORECASE)
        emails = re.findall(self.PATTERNS["email"], text)

        # Słowa kluczowe (top 50 najczęstszych słów > 4 znaki)
        words = re.findall(r"\b\w{5,}\b", text.lower())
        keywords = [w for w, _ in Counter(words).most_common(50)]

        return DocumentFeatures(
            text=text,
            page_count=doc.page_count if hasattr(doc, 'page_count') else len(list(doc)),
            has_tables=has_tables,
            has_images=has_images,
            keywords=keywords,
            dates_found=dates[:10],  # max 10
            amounts_found=amounts[:10],
            nip_count=len(nips),
            email_count=len(emails),
        )

    def _classify_ml(self, features: DocumentFeatures) -> Tuple[str, float, Dict[str, float]]:
        """Klasyfikacja z użyciem ML."""
        try:
            probas = self._model.predict_proba([features.text])[0]
            classes = self._model.classes_

            all_scores = {c: float(p) for c, p in zip(classes, probas)}
            best_idx = probas.argmax()
            category = classes[best_idx]
            confidence = probas[best_idx]

            return category, confidence, all_scores

        except Exception:
            # Fallback do rule-based
            return self._classify_rules(features)

    def _classify_rules(self, features: DocumentFeatures) -> Tuple[str, float, Dict[str, float]]:
        """Klasyfikacja oparta na regułach (fallback)."""
        text_lower = features.text.lower()
        scores = {}

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = 0
            for kw in keywords:
                if kw.lower() in text_lower:
                    score += 1

            # Normalizuj
            scores[category] = score / len(keywords) if keywords else 0

        # Dodatkowe heurystyki
        if features.nip_count >= 2 and features.has_tables:
            scores["faktura"] = scores.get("faktura", 0) + 0.3

        if "§" in features.text or "paragraf" in text_lower:
            scores["umowa"] = scores.get("umowa", 0) + 0.2

        if features.email_count >= 1 and "doświadczenie" in text_lower:
            scores["cv"] = scores.get("cv", 0) + 0.2

        # "inne" jako domyślne
        scores["inne"] = 0.1

        # Normalizuj do 0-1
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}

        # Najlepsza kategoria
        best_category = max(scores, key=scores.get)
        confidence = scores[best_category]

        return best_category, confidence, scores

    def _generate_tags(self, features: DocumentFeatures, category: str) -> List[str]:
        """Generuje tagi dla dokumentu."""
        tags = [category]

        # Tagi na podstawie cech
        if features.has_tables:
            tags.append("tabele")

        if features.has_images:
            tags.append("obrazy")

        if features.nip_count > 0:
            tags.append("nip")

        if features.page_count > 10:
            tags.append("długi_dokument")
        elif features.page_count == 1:
            tags.append("jednostronicowy")

        if features.dates_found:
            tags.append("daty")

        if features.amounts_found:
            tags.append("kwoty")

        return tags

    def _suggest_filename(
        self,
        features: DocumentFeatures,
        category: str,
        original_name: str
    ) -> str:
        """Sugeruje nazwę pliku."""
        # Wyciągnij datę
        date_str = ""
        if features.dates_found:
            date_str = features.dates_found[0].replace("/", "-").replace(".", "-")

        # Wyciągnij numer faktury jeśli to faktura
        number = ""
        if category == "faktura":
            match = re.search(
                r"(?:faktura|fv|invoice)[:\s#]*([a-z0-9\-/]+)",
                features.text,
                re.IGNORECASE
            )
            if match:
                number = match.group(1).replace("/", "-")

        # Zbuduj nazwę
        parts = [category]
        if date_str:
            parts.append(date_str)
        if number:
            parts.append(number)

        # Fallback do oryginalnej nazwy
        if len(parts) == 1:
            name_stem = Path(original_name).stem
            parts.append(name_stem[:30])

        suggested = "_".join(parts) + ".pdf"
        return suggested

    def train(self, texts: List[str], labels: List[str]) -> None:
        """
        Trenuje model na nowych danych.

        Args:
            texts: Lista tekstów dokumentów
            labels: Lista etykiet kategorii
        """
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn nie jest zainstalowany")

        self._model = Pipeline([
            ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
            ("clf", MultinomialNB()),
        ])
        self._model.fit(texts, labels)
        self._is_trained = True

    def save(self, path: Path) -> None:
        """Zapisuje model."""
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn nie jest zainstalowany")

        if self._model is not None:
            joblib.dump(self._model, path)

    @staticmethod
    def get_category_descriptions() -> Dict[str, str]:
        """Zwraca opisy kategorii."""
        return {
            "faktura": "Faktury VAT, rachunki, paragony",
            "umowa": "Umowy, kontrakty, aneksy",
            "pismo_urzedowe": "Pisma urzędowe, decyzje administracyjne",
            "cv": "CV, życiorysy, resume",
            "raport": "Raporty, sprawozdania, analizy",
            "oferta": "Oferty handlowe, cenniki",
            "inne": "Dokumenty nie pasujące do innych kategorii",
        }


# === Funkcje pomocnicze ===

def classify_document(pdf_path: Path) -> ClassificationResult:
    """Szybka funkcja do klasyfikacji dokumentu."""
    classifier = DocumentClassifier()
    return classifier.classify(pdf_path)


def suggest_filename(pdf_path: Path) -> str:
    """Szybka funkcja do sugestii nazwy pliku."""
    result = classify_document(pdf_path)
    return result.suggested_filename
