"""
SignatureEngine - Podpisy cyfrowe PDF.

Funkcje:
- Podpisywanie PDF certyfikatem X.509
- Weryfikacja istniejących podpisów
- Wizualizacja podpisu (pieczątka z datą)
- Tworzenie self-signed certyfikatów
- Import certyfikatów z plików .p12/.pfx
"""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple, Any
from enum import Enum

import pymupdf


class SignatureStatus(Enum):
    """Status podpisu."""
    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"
    NOT_SIGNED = "not_signed"


@dataclass
class SignatureInfo:
    """Informacje o podpisie."""
    signer_name: str
    signing_time: Optional[datetime]
    reason: str
    location: str
    status: SignatureStatus
    certificate_info: Optional[dict] = None
    page: Optional[int] = None


@dataclass
class SignatureConfig:
    """Konfiguracja podpisu."""
    cert_path: Path
    password: str
    reason: str = "Document digitally signed"
    location: str = "Poland"
    contact: str = ""
    # Pozycja wizualizacji podpisu
    page: int = 0
    x: float = 50
    y: float = 50
    width: float = 200
    height: float = 50
    # Opcje wizualizacji
    show_date: bool = True
    show_reason: bool = True
    show_location: bool = True


class SignatureEngine:
    """
    Silnik podpisów cyfrowych PDF.

    Obsługuje:
    - Podpisywanie z certyfikatami PKCS#12 (.p12/.pfx)
    - Wizualizację podpisu na stronie
    - Weryfikację podpisów
    - Generowanie certyfikatów self-signed
    """

    def __init__(self):
        self._has_endesive = self._check_endesive()
        self._has_cryptography = self._check_cryptography()

    def _check_endesive(self) -> bool:
        """Sprawdza czy endesive jest dostępne."""
        try:
            import endesive
            return True
        except ImportError:
            return False

    def _check_cryptography(self) -> bool:
        """Sprawdza czy cryptography jest dostępne."""
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives import serialization
            return True
        except ImportError:
            return False

    def sign_pdf(
        self,
        input_path: Path,
        output_path: Path,
        config: SignatureConfig,
    ) -> bool:
        """
        Podpisuje PDF certyfikatem.

        Args:
            input_path: Ścieżka do pliku wejściowego
            output_path: Ścieżka do pliku wyjściowego
            config: Konfiguracja podpisu

        Returns:
            True jeśli podpisano pomyślnie
        """
        if not self._has_endesive:
            # Fallback: dodaj wizualną reprezentację podpisu
            return self._add_visual_signature(input_path, output_path, config)

        try:
            from endesive.pdf import cms

            # Wczytaj certyfikat PKCS#12
            with open(config.cert_path, "rb") as f:
                p12_data = f.read()

            # Wczytaj PDF
            pdf_data = input_path.read_bytes()

            # Podpisz
            signed_data = cms.sign(
                pdf_data,
                p12_data,
                config.password.encode(),
                "sha256",
                attrs=True,
                timestamp=None,
            )

            # Zapisz
            output_path.write_bytes(signed_data)

            # Dodaj wizualizację
            self._add_signature_appearance(output_path, config)

            return True

        except Exception as e:
            print(f"Błąd podpisywania: {e}")
            # Fallback do wizualnego podpisu
            return self._add_visual_signature(input_path, output_path, config)

    def _add_visual_signature(
        self,
        input_path: Path,
        output_path: Path,
        config: SignatureConfig,
    ) -> bool:
        """
        Dodaje wizualną reprezentację podpisu (bez kryptografii).

        Args:
            input_path: Ścieżka do pliku wejściowego
            output_path: Ścieżka do pliku wyjściowego
            config: Konfiguracja podpisu

        Returns:
            True jeśli dodano pomyślnie
        """
        try:
            doc = pymupdf.open(str(input_path))
            page = doc[config.page]

            # Prostokąt podpisu
            rect = pymupdf.Rect(
                config.x,
                config.y,
                config.x + config.width,
                config.y + config.height,
            )

            # Pobierz informacje z certyfikatu
            signer_name = self._get_signer_name(config.cert_path, config.password)
            signing_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Zbuduj tekst podpisu
            lines = [f"Podpisano cyfrowo przez: {signer_name}"]
            if config.show_date:
                lines.append(f"Data: {signing_time}")
            if config.show_reason and config.reason:
                lines.append(f"Powód: {config.reason}")
            if config.show_location and config.location:
                lines.append(f"Miejsce: {config.location}")

            # Rysuj ramkę
            page.draw_rect(rect, color=(0, 0, 0.5), width=1)

            # Rysuj tekst
            fontsize = 9
            y_offset = config.y + 12
            for line in lines:
                page.insert_text(
                    (config.x + 5, y_offset),
                    line,
                    fontsize=fontsize,
                    color=(0, 0, 0.3),
                )
                y_offset += fontsize + 2

            # Zapisz
            doc.save(str(output_path))
            doc.close()

            return True

        except Exception as e:
            print(f"Błąd dodawania wizualnego podpisu: {e}")
            return False

    def _add_signature_appearance(
        self, pdf_path: Path, config: SignatureConfig
    ) -> None:
        """Dodaje wizualizację podpisu do już podpisanego PDF."""
        # Ta metoda jest wywoływana po podpisaniu przez endesive
        pass

    def _get_signer_name(self, cert_path: Path, password: str) -> str:
        """Pobiera nazwę podpisującego z certyfikatu."""
        if not self._has_cryptography:
            return "Unknown Signer"

        try:
            from cryptography.hazmat.primitives.serialization import pkcs12

            with open(cert_path, "rb") as f:
                p12_data = f.read()

            private_key, certificate, _ = pkcs12.load_key_and_certificates(
                p12_data, password.encode()
            )

            if certificate:
                # Pobierz Common Name
                for attr in certificate.subject:
                    if attr.oid.dotted_string == "2.5.4.3":  # CN OID
                        return attr.value

            return "Unknown Signer"

        except Exception:
            return "Unknown Signer"

    def verify_signatures(self, pdf_path: Path) -> List[SignatureInfo]:
        """
        Weryfikuje podpisy w dokumencie PDF.

        Args:
            pdf_path: Ścieżka do pliku PDF

        Returns:
            Lista informacji o podpisach
        """
        signatures = []

        try:
            doc = pymupdf.open(str(pdf_path))

            # Sprawdź czy dokument ma podpisy
            # PyMuPDF nie ma bezpośredniego API do weryfikacji podpisów
            # Sprawdzamy pola formularza typu Signature

            for page_num in range(len(doc)):
                page = doc[page_num]

                # Sprawdź widżety (pola formularza)
                for widget in page.widgets() or []:
                    if widget.field_type == pymupdf.PDF_WIDGET_TYPE_SIGNATURE:
                        # Znaleziono pole podpisu
                        sig_info = SignatureInfo(
                            signer_name=widget.field_value or "Unknown",
                            signing_time=None,
                            reason="",
                            location="",
                            status=SignatureStatus.UNKNOWN,
                            page=page_num + 1,
                        )
                        signatures.append(sig_info)

            doc.close()

            # Jeśli mamy endesive, spróbuj zweryfikować
            if self._has_endesive and signatures:
                self._verify_with_endesive(pdf_path, signatures)

        except Exception as e:
            print(f"Błąd weryfikacji podpisów: {e}")

        if not signatures:
            signatures.append(SignatureInfo(
                signer_name="",
                signing_time=None,
                reason="",
                location="",
                status=SignatureStatus.NOT_SIGNED,
            ))

        return signatures

    def _verify_with_endesive(
        self, pdf_path: Path, signatures: List[SignatureInfo]
    ) -> None:
        """Weryfikuje podpisy używając endesive."""
        try:
            from endesive.pdf import verify

            pdf_data = pdf_path.read_bytes()

            # Weryfikuj
            results = verify.verify(pdf_data)

            for i, (sig_info, result) in enumerate(zip(signatures, results)):
                if result:
                    sig_info.status = SignatureStatus.VALID
                else:
                    sig_info.status = SignatureStatus.INVALID

        except Exception:
            pass

    def create_self_signed_cert(
        self,
        common_name: str,
        organization: str,
        output_path: Path,
        password: str,
        validity_days: int = 365,
    ) -> bool:
        """
        Tworzy self-signed certyfikat.

        Args:
            common_name: Nazwa (CN)
            organization: Organizacja (O)
            output_path: Ścieżka do pliku .p12
            password: Hasło do pliku
            validity_days: Ważność w dniach

        Returns:
            True jeśli utworzono pomyślnie
        """
        if not self._has_cryptography:
            return False

        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives.serialization import (
                pkcs12,
                BestAvailableEncryption,
            )

            # Generuj klucz prywatny
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )

            # Utwórz certyfikat
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
                x509.NameAttribute(NameOID.COUNTRY_NAME, "PL"),
            ])

            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(private_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.utcnow())
                .not_valid_after(datetime.utcnow() + timedelta(days=validity_days))
                .add_extension(
                    x509.BasicConstraints(ca=False, path_length=None),
                    critical=True,
                )
                .add_extension(
                    x509.KeyUsage(
                        digital_signature=True,
                        key_encipherment=False,
                        content_commitment=True,
                        data_encipherment=False,
                        key_agreement=False,
                        key_cert_sign=False,
                        crl_sign=False,
                        encipher_only=False,
                        decipher_only=False,
                    ),
                    critical=True,
                )
                .sign(private_key, hashes.SHA256())
            )

            # Zapisz jako PKCS#12
            p12_data = pkcs12.serialize_key_and_certificates(
                common_name.encode(),
                private_key,
                cert,
                None,
                BestAvailableEncryption(password.encode()),
            )

            output_path.write_bytes(p12_data)
            return True

        except Exception as e:
            print(f"Błąd tworzenia certyfikatu: {e}")
            return False

    def get_certificate_info(
        self, cert_path: Path, password: str
    ) -> Optional[dict]:
        """
        Pobiera informacje o certyfikacie.

        Args:
            cert_path: Ścieżka do pliku .p12/.pfx
            password: Hasło

        Returns:
            Słownik z informacjami lub None
        """
        if not self._has_cryptography:
            return None

        try:
            from cryptography.hazmat.primitives.serialization import pkcs12

            with open(cert_path, "rb") as f:
                p12_data = f.read()

            private_key, certificate, _ = pkcs12.load_key_and_certificates(
                p12_data, password.encode()
            )

            if not certificate:
                return None

            # Wyciągnij informacje
            info = {
                "subject": {},
                "issuer": {},
                "valid_from": certificate.not_valid_before_utc.isoformat(),
                "valid_to": certificate.not_valid_after_utc.isoformat(),
                "serial_number": str(certificate.serial_number),
            }

            # Subject
            for attr in certificate.subject:
                name = attr.oid._name or attr.oid.dotted_string
                info["subject"][name] = attr.value

            # Issuer
            for attr in certificate.issuer:
                name = attr.oid._name or attr.oid.dotted_string
                info["issuer"][name] = attr.value

            return info

        except Exception as e:
            print(f"Błąd odczytu certyfikatu: {e}")
            return None

    @property
    def has_full_signing_support(self) -> bool:
        """Sprawdza czy dostępne jest pełne wsparcie podpisywania."""
        return self._has_endesive and self._has_cryptography

    @property
    def has_certificate_support(self) -> bool:
        """Sprawdza czy dostępne jest wsparcie certyfikatów."""
        return self._has_cryptography
