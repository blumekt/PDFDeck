"""
ProfileManager - Zarządzanie profilami watermarków i pieczątek.

Funkcje:
- Zapisywanie/ładowanie profili z plików JSON
- Cache profili w pamięci
- Walidacja profili
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json

from pdfdeck.core.models import (
    WatermarkConfig,
    StampConfig,
    StampShape,
    BorderStyle,
    WearLevel,
    Point,
)


class ProfileType(Enum):
    """Typ profilu."""
    WATERMARK = "watermark"
    STAMP = "stamp"


@dataclass
class ProfileMetadata:
    """Metadane profilu."""
    name: str
    profile_type: ProfileType
    description: str = ""
    created_at: str = ""
    modified_at: str = ""


@dataclass
class WatermarkProfile:
    """Profil znaku wodnego."""
    metadata: ProfileMetadata
    config: WatermarkConfig

    def to_dict(self) -> dict:
        """Serializacja do dict."""
        return {
            "metadata": {
                "name": self.metadata.name,
                "profile_type": self.metadata.profile_type.value,
                "description": self.metadata.description,
                "created_at": self.metadata.created_at,
                "modified_at": self.metadata.modified_at,
            },
            "config": {
                "text": self.config.text,
                "font_size": self.config.font_size,
                "color": list(self.config.color),
                "rotation": self.config.rotation,
                "opacity": self.config.opacity,
                "overlay": self.config.overlay,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WatermarkProfile":
        """Deserializacja z dict."""
        meta_data = data["metadata"]
        config_data = data["config"]

        metadata = ProfileMetadata(
            name=meta_data["name"],
            profile_type=ProfileType(meta_data["profile_type"]),
            description=meta_data.get("description", ""),
            created_at=meta_data.get("created_at", ""),
            modified_at=meta_data.get("modified_at", ""),
        )

        config = WatermarkConfig(
            text=config_data["text"],
            font_size=config_data.get("font_size", 72.0),
            color=tuple(config_data.get("color", [0.5, 0.5, 0.5])),
            rotation=config_data.get("rotation", 45.0),
            opacity=config_data.get("opacity", 0.3),
            overlay=config_data.get("overlay", True),
        )

        return cls(metadata=metadata, config=config)


@dataclass
class StampProfile:
    """Profil pieczątki."""
    metadata: ProfileMetadata
    config: StampConfig

    def to_dict(self) -> dict:
        """Serializacja do dict - konwersja enumów i Point."""
        return {
            "metadata": {
                "name": self.metadata.name,
                "profile_type": self.metadata.profile_type.value,
                "description": self.metadata.description,
                "created_at": self.metadata.created_at,
                "modified_at": self.metadata.modified_at,
            },
            "config": {
                "text": self.config.text,
                "circular_text": self.config.circular_text,
                "position": {"x": self.config.position.x, "y": self.config.position.y},
                "rotation": self.config.rotation,
                "rotation_random": self.config.rotation_random,
                "corner": self.config.corner,
                "scale": self.config.scale,
                "shape": self.config.shape.name,
                "border_style": self.config.border_style.name,
                "border_width": self.config.border_width,
                "color": list(self.config.color),
                "fill_color": list(self.config.fill_color) if self.config.fill_color else None,
                "opacity": self.config.opacity,
                "wear_level": self.config.wear_level.name,
                "vintage_effect": self.config.vintage_effect,
                "double_strike": self.config.double_strike,
                "ink_splatter": self.config.ink_splatter,
                "auto_date": self.config.auto_date,
                "width": self.config.width,
                "height": self.config.height,
                "font_size": self.config.font_size,
                "circular_font_size": self.config.circular_font_size,
                "stamp_path": str(self.config.stamp_path) if self.config.stamp_path else None,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StampProfile":
        """Deserializacja z dict - konwersja string -> enum."""
        meta_data = data["metadata"]
        config_data = data["config"]

        metadata = ProfileMetadata(
            name=meta_data["name"],
            profile_type=ProfileType(meta_data["profile_type"]),
            description=meta_data.get("description", ""),
            created_at=meta_data.get("created_at", ""),
            modified_at=meta_data.get("modified_at", ""),
        )

        # Konwersja pozycji
        pos_data = config_data.get("position", {"x": 100, "y": 100})
        position = Point(x=pos_data["x"], y=pos_data["y"])

        # Konwersja enumów
        shape = StampShape[config_data.get("shape", "RECTANGLE")]
        border_style = BorderStyle[config_data.get("border_style", "SOLID")]
        wear_level = WearLevel[config_data.get("wear_level", "NONE")]

        # Konwersja kolorów
        color = tuple(config_data.get("color", [0.9, 0.1, 0.1]))
        fill_color_data = config_data.get("fill_color")
        fill_color = tuple(fill_color_data) if fill_color_data else None

        # Konwersja stamp_path
        stamp_path_str = config_data.get("stamp_path")
        stamp_path = Path(stamp_path_str) if stamp_path_str else None

        config = StampConfig(
            text=config_data.get("text", ""),
            circular_text=config_data.get("circular_text"),
            position=position,
            rotation=config_data.get("rotation", 0.0),
            rotation_random=config_data.get("rotation_random", True),
            corner=config_data.get("corner", "center"),
            scale=config_data.get("scale", 1.0),
            shape=shape,
            border_style=border_style,
            border_width=config_data.get("border_width", 2.0),
            color=color,
            fill_color=fill_color,
            opacity=config_data.get("opacity", 1.0),
            wear_level=wear_level,
            vintage_effect=config_data.get("vintage_effect", False),
            double_strike=config_data.get("double_strike", False),
            ink_splatter=config_data.get("ink_splatter", False),
            auto_date=config_data.get("auto_date", False),
            width=config_data.get("width", 150.0),
            height=config_data.get("height", 60.0),
            font_size=config_data.get("font_size", 24.0),
            circular_font_size=config_data.get("circular_font_size", 10.0),
            stamp_path=stamp_path,
        )

        return cls(metadata=metadata, config=config)


class ProfileManager:
    """
    Menedżer profili - singleton.

    Odpowiada za:
    - Ładowanie/zapisywanie profili z/do plików
    - Cache profili w pamięci
    - Walidacja profili
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._profiles_dir = Path.home() / ".pdfdeck" / "profiles"
        self._profiles_dir.mkdir(parents=True, exist_ok=True)

        self._watermark_profiles: Dict[str, WatermarkProfile] = {}
        self._stamp_profiles: Dict[str, StampProfile] = {}

        self._load_all_profiles()
        self._initialized = True

    # === Watermark profiles ===

    def get_watermark_profiles(self) -> List[WatermarkProfile]:
        """Zwraca listę wszystkich profili watermark."""
        return list(self._watermark_profiles.values())

    def get_watermark_profile(self, name: str) -> Optional[WatermarkProfile]:
        """Zwraca profil watermark po nazwie."""
        return self._watermark_profiles.get(name)

    def save_watermark_profile(self, profile: WatermarkProfile) -> None:
        """Zapisuje profil watermark."""
        self._watermark_profiles[profile.metadata.name] = profile
        self._save_profile(profile, ProfileType.WATERMARK)

    def delete_watermark_profile(self, name: str) -> bool:
        """Usuwa profil watermark."""
        if name in self._watermark_profiles:
            del self._watermark_profiles[name]
            return self._delete_profile_file(name, ProfileType.WATERMARK)
        return False

    # === Stamp profiles ===

    def get_stamp_profiles(self) -> List[StampProfile]:
        """Zwraca listę wszystkich profili stamp."""
        return list(self._stamp_profiles.values())

    def get_stamp_profile(self, name: str) -> Optional[StampProfile]:
        """Zwraca profil stamp po nazwie."""
        return self._stamp_profiles.get(name)

    def save_stamp_profile(self, profile: StampProfile) -> None:
        """Zapisuje profil stamp."""
        self._stamp_profiles[profile.metadata.name] = profile
        self._save_profile(profile, ProfileType.STAMP)

    def delete_stamp_profile(self, name: str) -> bool:
        """Usuwa profil stamp."""
        if name in self._stamp_profiles:
            del self._stamp_profiles[name]
            return self._delete_profile_file(name, ProfileType.STAMP)
        return False

    # === Internal ===

    def _sanitize_filename(self, name: str) -> str:
        """Sanityzuje nazwę do bezpiecznej nazwy pliku."""
        # Zamień znaki specjalne na podkreślniki
        safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_ ")
        safe_name = "".join(c if c in safe_chars else "_" for c in name)
        return safe_name.strip()

    def _get_profile_path(self, name: str, profile_type: ProfileType) -> Path:
        """Generuje ścieżkę do pliku profilu."""
        safe_name = self._sanitize_filename(name)
        return self._profiles_dir / f"{profile_type.value}_{safe_name}.json"

    def _save_profile(
        self, profile: WatermarkProfile | StampProfile, profile_type: ProfileType
    ) -> None:
        """Zapisuje profil do pliku."""
        path = self._get_profile_path(profile.metadata.name, profile_type)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)

    def _delete_profile_file(self, name: str, profile_type: ProfileType) -> bool:
        """Usuwa plik profilu."""
        path = self._get_profile_path(name, profile_type)
        try:
            if path.exists():
                path.unlink()
                return True
        except Exception:
            pass
        return False

    def _load_all_profiles(self) -> None:
        """Ładuje wszystkie profile z katalogu."""
        for path in self._profiles_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if "metadata" not in data or "profile_type" not in data["metadata"]:
                    continue

                profile_type = ProfileType(data["metadata"]["profile_type"])

                if profile_type == ProfileType.WATERMARK:
                    profile = WatermarkProfile.from_dict(data)
                    self._watermark_profiles[profile.metadata.name] = profile
                elif profile_type == ProfileType.STAMP:
                    profile = StampProfile.from_dict(data)
                    self._stamp_profiles[profile.metadata.name] = profile

            except Exception as e:
                print(f"Błąd ładowania profilu {path}: {e}")

    def refresh(self) -> None:
        """Przeładowuje wszystkie profile z dysku."""
        self._watermark_profiles.clear()
        self._stamp_profiles.clear()
        self._load_all_profiles()
