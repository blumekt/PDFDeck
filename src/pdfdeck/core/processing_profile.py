"""
ProcessingProfile - Profile przetwarzania PDF.

Definiuje zestaw akcji do wykonania na dokumentach PDF.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import json
from pathlib import Path


class ProcessingAction(Enum):
    """Dostępne akcje przetwarzania."""
    NORMALIZE_A4 = "normalize_a4"
    COMPRESS = "compress"
    ADD_WATERMARK = "add_watermark"
    ADD_STAMP = "add_stamp"
    ADD_BATES = "add_bates"
    SCRUB_METADATA = "scrub_metadata"
    FLATTEN = "flatten"
    CONVERT_PDFA = "convert_pdfa"


@dataclass
class ProcessingProfile:
    """
    Profil przetwarzania PDF.

    Definiuje zestaw akcji do wykonania na dokumentach.
    """
    name: str
    actions: List[ProcessingAction] = field(default_factory=list)

    # Referencje do zapisanych profili (nowe)
    watermark_profile_name: Optional[str] = None
    stamp_profile_name: Optional[str] = None

    # Parametry dla poszczególnych akcji (legacy - dla kompatybilności)
    watermark_text: Optional[str] = None
    watermark_opacity: float = 0.3
    watermark_rotation: int = 45

    bates_prefix: Optional[str] = None
    bates_suffix: Optional[str] = None
    bates_start: int = 1
    bates_digits: int = 6

    pdfa_level: str = "1b"

    # Output
    output_format: str = "pdf"  # pdf, pdfa
    output_suffix: str = "_processed"

    def to_dict(self) -> Dict[str, Any]:
        """Konwertuje profil do słownika."""
        return {
            "name": self.name,
            "actions": [a.value for a in self.actions],
            "watermark_profile_name": self.watermark_profile_name,
            "stamp_profile_name": self.stamp_profile_name,
            "watermark_text": self.watermark_text,
            "watermark_opacity": self.watermark_opacity,
            "watermark_rotation": self.watermark_rotation,
            "bates_prefix": self.bates_prefix,
            "bates_suffix": self.bates_suffix,
            "bates_start": self.bates_start,
            "bates_digits": self.bates_digits,
            "pdfa_level": self.pdfa_level,
            "output_format": self.output_format,
            "output_suffix": self.output_suffix,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessingProfile":
        """Tworzy profil ze słownika."""
        actions = [ProcessingAction(a) for a in data.get("actions", [])]
        return cls(
            name=data.get("name", "Unnamed"),
            actions=actions,
            watermark_profile_name=data.get("watermark_profile_name"),
            stamp_profile_name=data.get("stamp_profile_name"),
            watermark_text=data.get("watermark_text"),
            watermark_opacity=data.get("watermark_opacity", 0.3),
            watermark_rotation=data.get("watermark_rotation", 45),
            bates_prefix=data.get("bates_prefix"),
            bates_suffix=data.get("bates_suffix"),
            bates_start=data.get("bates_start", 1),
            bates_digits=data.get("bates_digits", 6),
            pdfa_level=data.get("pdfa_level", "1b"),
            output_format=data.get("output_format", "pdf"),
            output_suffix=data.get("output_suffix", "_processed"),
        )

    def save(self, filepath: Path) -> None:
        """Zapisuje profil do pliku JSON."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, filepath: Path) -> "ProcessingProfile":
        """Wczytuje profil z pliku JSON."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


# Predefiniowane profile
PRESET_PROFILES = {
    "office_standard": ProcessingProfile(
        name="Biurowy standardowy",
        actions=[
            ProcessingAction.NORMALIZE_A4,
            ProcessingAction.COMPRESS,
            ProcessingAction.SCRUB_METADATA,
        ],
    ),
    "legal_bates": ProcessingProfile(
        name="Prawniczy z Bates",
        actions=[
            ProcessingAction.NORMALIZE_A4,
            ProcessingAction.ADD_BATES,
            ProcessingAction.FLATTEN,
        ],
        bates_prefix="DOC-",
        bates_digits=6,
    ),
    "archive_pdfa": ProcessingProfile(
        name="Archiwalny PDF/A",
        actions=[
            ProcessingAction.SCRUB_METADATA,
            ProcessingAction.FLATTEN,
            ProcessingAction.CONVERT_PDFA,
        ],
        pdfa_level="1b",
        output_format="pdfa",
    ),
    "confidential": ProcessingProfile(
        name="Poufny z watermarkiem",
        actions=[
            ProcessingAction.ADD_WATERMARK,
            ProcessingAction.SCRUB_METADATA,
        ],
        watermark_text="POUFNE",
        watermark_opacity=0.2,
    ),
}
