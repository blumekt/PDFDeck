"""
UpdateChecker - Sprawdzanie dostępności aktualizacji.

Pobiera latest.yml/beta.yml z GitHub i porównuje wersje.
Nie zawiera żadnej logiki UI.
"""

import re
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional

from pdfdeck import __version__
from pdfdeck.core.models import UpdateChannel, UpdateCheckResult, UpdateInfo


class UpdateChecker:
    """
    Sprawdza dostępność aktualizacji.

    Pobiera metadane z:
    - Stable: https://raw.githubusercontent.com/blumekt/PDFDeck-releases/main/latest.yml
    - Beta: https://raw.githubusercontent.com/blumekt/PDFDeck-releases/main/beta.yml
    """

    BASE_URL = "https://raw.githubusercontent.com/blumekt/PDFDeck-releases/main"
    DOWNLOAD_BASE = "https://github.com/blumekt/PDFDeck-releases/releases/download"
    TIMEOUT = 10  # sekundy

    def __init__(self, channel: UpdateChannel = UpdateChannel.STABLE) -> None:
        self._channel = channel

    @property
    def channel(self) -> UpdateChannel:
        return self._channel

    @channel.setter
    def channel(self, value: UpdateChannel) -> None:
        self._channel = value

    @property
    def current_version(self) -> str:
        """Zwraca aktualną wersję aplikacji."""
        return __version__

    def check_for_updates(self) -> UpdateCheckResult:
        """
        Sprawdza czy jest dostępna nowa wersja.

        Returns:
            UpdateCheckResult z informacją o aktualizacji lub błędzie
        """
        current = self.current_version

        try:
            yml_file = "beta.yml" if self._channel == UpdateChannel.BETA else "latest.yml"
            yml_url = f"{self.BASE_URL}/{yml_file}"
            yml_content = self._fetch_url(yml_url)
            update_info = self._parse_yml(yml_content)

            if self._is_newer_version(update_info.version, current):
                return UpdateCheckResult(
                    update_available=True,
                    current_version=current,
                    latest_version=update_info.version,
                    update_info=update_info,
                )
            else:
                return UpdateCheckResult(
                    update_available=False,
                    current_version=current,
                    latest_version=update_info.version,
                )

        except urllib.error.HTTPError as e:
            error_msg = f"Błąd HTTP {e.code}: {e.reason}"
            return UpdateCheckResult(
                update_available=False,
                current_version=current,
                latest_version="",
                error=error_msg,
            )
        except urllib.error.URLError as e:
            error_msg = f"Błąd połączenia: {e.reason}"
            return UpdateCheckResult(
                update_available=False,
                current_version=current,
                latest_version="",
                error=error_msg,
            )
        except Exception as e:
            return UpdateCheckResult(
                update_available=False,
                current_version=current,
                latest_version="",
                error=str(e),
            )

    def _fetch_url(self, url: str) -> str:
        """Pobiera zawartość URL."""
        req = urllib.request.Request(url, headers={"User-Agent": "PDFDeck-Updater"})
        with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:
            return response.read().decode("utf-8")

    def _parse_yml(self, content: str) -> UpdateInfo:
        """Parsuje YAML (prosty parser bez zewnętrznych zależności)."""
        lines = content.strip().split("\n")
        data: dict[str, str] = {}

        for line in lines:
            if ":" in line and not line.strip().startswith("-"):
                key, value = line.split(":", 1)
                data[key.strip()] = value.strip().strip("'\"")

        version = data.get("version", "")
        filename = data.get("path", "")

        # Buduj URL do pobrania
        download_url = f"{self.DOWNLOAD_BASE}/v{version}/{filename}"

        # Parsuj datę
        release_date_str = data.get("releaseDate", "")
        try:
            release_date = datetime.fromisoformat(release_date_str.replace("'", ""))
        except ValueError:
            release_date = datetime.now()

        return UpdateInfo(
            version=version,
            download_url=download_url,
            sha512=data.get("sha512", ""),
            size=int(data.get("size", 0)),
            release_date=release_date,
            filename=filename,
        )

    def _is_newer_version(self, latest: str, current: str) -> bool:
        """Porównuje wersje semantyczne (x.y.z lub x.y.z-beta.n)."""

        def parse_version(v: str) -> tuple[int, int, int, float]:
            # Usuń prefix 'v' jeśli jest
            v = v.lstrip("v")
            # Podziel na część główną i beta
            match = re.match(r"(\d+)\.(\d+)\.(\d+)(?:-beta\.(\d+))?", v)
            if match:
                major = int(match.group(1))
                minor = int(match.group(2))
                patch = int(match.group(3))
                # stable > beta (inf > any number)
                beta = int(match.group(4)) if match.group(4) else float("inf")
                return (major, minor, patch, beta)
            return (0, 0, 0, 0)

        return parse_version(latest) > parse_version(current)
