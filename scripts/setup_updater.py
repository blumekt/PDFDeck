#!/usr/bin/env python3
"""
Universal Auto-Updater Setup Script v1.0

Portable setup script for adding auto-update functionality to desktop applications.
Copy this script to any new project - it will auto-configure itself.

Features:
- Auto-detection of project configuration from pyproject.toml
- Support for multiple UI frameworks (PyQt6, CustomTkinter, CLI)
- Full environment validation (--check flag)
- Generate updater module files (--init flag)
- Test connection and parsing (--test flag)
- Dry-run mode, rollback on errors
- Colored terminal output

Usage:
    python scripts/setup_updater.py --check              # Check environment
    python scripts/setup_updater.py --init               # Generate updater files
    python scripts/setup_updater.py --init --dry-run     # Simulate generation
    python scripts/setup_updater.py --init --force       # Overwrite existing
    python scripts/setup_updater.py --test               # Test connection
    python scripts/setup_updater.py --framework pyqt6    # Override framework

Configuration:
    Add to pyproject.toml:

    [tool.updater]
    app_name = "MyApp"
    releases_repo = "username/myapp-releases"
    ui_framework = "pyqt6"  # or "customtkinter", "cli"
"""

from __future__ import annotations

import argparse
import platform
import re
import shutil
import subprocess
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

# ============================================================================
# CONSTANTS
# ============================================================================

SCRIPT_VERSION = "1.0"
MIN_PYTHON_VERSION = (3, 9)

SUPPORTED_FRAMEWORKS = ["pyqt6", "customtkinter", "cli"]


# ============================================================================
# COLORS
# ============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    @classmethod
    def init(cls) -> None:
        """Initialize colors (enable ANSI on Windows if possible)."""
        if platform.system() == "Windows":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except Exception:
                for attr in dir(cls):
                    if not attr.startswith("_") and attr.isupper():
                        setattr(cls, attr, "")


Colors.init()
C = Colors()


# ============================================================================
# LOGGING
# ============================================================================

def log(msg: str, level: str = "info") -> None:
    """Print a colored log message."""
    prefixes = {
        "info": f"{C.CYAN}[INFO]{C.RESET}",
        "ok": f"{C.GREEN}[OK]{C.RESET}",
        "warn": f"{C.YELLOW}[WARN]{C.RESET}",
        "error": f"{C.RED}[ERROR]{C.RESET}",
        "step": f"{C.MAGENTA}[STEP]{C.RESET}",
        "dry": f"{C.BLUE}[DRY]{C.RESET}",
        "check": f"{C.WHITE}[CHECK]{C.RESET}",
    }
    prefix = prefixes.get(level, prefixes["info"])
    print(f"{prefix} {msg}")


def header(title: str) -> None:
    """Print a section header."""
    line = "=" * 60
    print(f"\n{C.BOLD}{C.CYAN}{line}{C.RESET}")
    print(f"{C.BOLD}  {title}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{line}{C.RESET}\n")


def subheader(title: str) -> None:
    """Print a subsection header."""
    print(f"\n{C.YELLOW}--- {title} ---{C.RESET}\n")


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class UpdaterConfig:
    """Auto-updater configuration loaded from pyproject.toml."""
    # Required
    app_name: str = ""
    releases_repo: str = ""

    # Optional with defaults
    ui_framework: str = "pyqt6"
    update_check_delay: int = 2000
    channels: List[str] = field(default_factory=lambda: ["stable", "beta"])
    models_location: str = "separate"  # "separate" or "existing"

    # Paths (computed from app_name)
    updater_module: str = ""
    dialog_file: str = ""
    existing_models_file: str = ""

    # Computed
    project_root: Path = field(default_factory=Path)
    app_name_lower: str = ""
    owner: str = ""
    repo: str = ""

    @classmethod
    def load(cls, project_root: Optional[Path] = None) -> "UpdaterConfig":
        """Load configuration from pyproject.toml."""
        if project_root is None:
            project_root = Path.cwd()
            for parent in [project_root] + list(project_root.parents):
                if (parent / "pyproject.toml").exists():
                    project_root = parent
                    break

        pyproject_path = project_root / "pyproject.toml"
        if not pyproject_path.exists():
            raise FileNotFoundError(
                f"pyproject.toml not found in {project_root}\n"
                "Make sure you're running from the project root directory."
            )

        # Load pyproject.toml
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                raise ImportError(
                    "tomli package required for Python < 3.11\n"
                    "Install with: pip install tomli"
                )

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        # Get project info
        project = data.get("project", {})

        # Get updater config (also check tool.release for compatibility)
        tool_updater = data.get("tool", {}).get("updater", {})
        tool_release = data.get("tool", {}).get("release", {})

        # Merge configs (tool.updater takes precedence)
        config_data = {**tool_release, **tool_updater}

        # Extract app name
        app_name = (
            config_data.get("app_name") or
            project.get("name", "").capitalize() or
            "App"
        )
        app_name_lower = app_name.lower()

        # Extract releases repo
        releases_repo = config_data.get("releases_repo", "")
        owner, repo = "", ""
        if "/" in releases_repo:
            owner, repo = releases_repo.split("/", 1)

        # Create config
        config = cls(
            app_name=app_name,
            releases_repo=releases_repo,
            project_root=project_root,
            app_name_lower=app_name_lower,
            owner=owner,
            repo=repo,
        )

        # Override with custom values
        for key in ["ui_framework", "update_check_delay", "channels", "models_location"]:
            if key in config_data:
                setattr(config, key, config_data[key])

        # Set default paths
        config.updater_module = config_data.get(
            "updater_module",
            f"src/{app_name_lower}/core/updater"
        )
        config.dialog_file = config_data.get(
            "dialog_file",
            f"src/{app_name_lower}/ui/dialogs/update_dialog.py"
        )
        config.existing_models_file = config_data.get(
            "existing_models_file",
            f"src/{app_name_lower}/core/models.py"
        )

        return config

    def resolve_path(self, path: str) -> Path:
        """Resolve a path relative to project root."""
        return self.project_root / path


# ============================================================================
# TEMPLATES
# ============================================================================

class TemplateRegistry:
    """Registry of code templates for different frameworks."""

    # ========== COMMON TEMPLATES ==========

    MODELS_TEMPLATE = '''"""
Auto-Updater models for {app_name}.
Generated by setup_updater.py
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Optional


class UpdateChannel(Enum):
    """Update channel."""
    STABLE = auto()
    BETA = auto()


@dataclass
class UpdateInfo:
    """Information about available update."""
    version: str
    download_url: str
    sha512: str
    size: int
    release_date: datetime
    filename: str

    @property
    def size_mb(self) -> float:
        """Size in MB."""
        return self.size / 1024 / 1024


@dataclass
class UpdateCheckResult:
    """Result of update check."""
    update_available: bool
    current_version: str
    latest_version: str
    update_info: Optional[UpdateInfo] = None
    error: Optional[str] = None
'''

    CHECKER_TEMPLATE = '''"""
UpdateChecker - Check for available updates.
Pure Python, no framework dependencies.
Generated by setup_updater.py
"""

import re
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional

from {models_import} import UpdateChannel, UpdateCheckResult, UpdateInfo


class UpdateChecker:
    """Check for updates from GitHub releases."""

    BASE_URL = "https://raw.githubusercontent.com/{releases_repo}/main"
    DOWNLOAD_BASE = "https://github.com/{releases_repo}/releases/download"
    TIMEOUT = 10

    def __init__(self, current_version: str, channel: UpdateChannel = UpdateChannel.STABLE):
        self._current_version = current_version
        self._channel = channel

    @property
    def channel(self) -> UpdateChannel:
        return self._channel

    @channel.setter
    def channel(self, value: UpdateChannel) -> None:
        self._channel = value

    @property
    def current_version(self) -> str:
        return self._current_version

    def check_for_updates(self) -> UpdateCheckResult:
        """Check if new version is available."""
        try:
            yml_file = "beta.yml" if self._channel == UpdateChannel.BETA else "latest.yml"
            yml_url = f"{{self.BASE_URL}}/{{yml_file}}"
            yml_content = self._fetch_url(yml_url)
            update_info = self._parse_yml(yml_content)

            if self._is_newer_version(update_info.version, self._current_version):
                return UpdateCheckResult(
                    update_available=True,
                    current_version=self._current_version,
                    latest_version=update_info.version,
                    update_info=update_info,
                )
            return UpdateCheckResult(
                update_available=False,
                current_version=self._current_version,
                latest_version=update_info.version,
            )

        except urllib.error.HTTPError as e:
            return UpdateCheckResult(
                update_available=False,
                current_version=self._current_version,
                latest_version="",
                error=f"HTTP {{e.code}}: {{e.reason}}",
            )
        except urllib.error.URLError as e:
            return UpdateCheckResult(
                update_available=False,
                current_version=self._current_version,
                latest_version="",
                error=f"Connection error: {{e.reason}}",
            )
        except Exception as e:
            return UpdateCheckResult(
                update_available=False,
                current_version=self._current_version,
                latest_version="",
                error=str(e),
            )

    def _fetch_url(self, url: str) -> str:
        req = urllib.request.Request(url, headers={{"User-Agent": "{app_name}-Updater"}})
        with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:
            return response.read().decode("utf-8")

    def _parse_yml(self, content: str) -> UpdateInfo:
        lines = content.strip().split("\\n")
        data: dict[str, str] = {{}}

        for line in lines:
            if ":" in line and not line.strip().startswith("-"):
                key, value = line.split(":", 1)
                data[key.strip()] = value.strip().strip("'\\"")

        version = data.get("version", "")
        filename = data.get("path", "")
        download_url = f"{{self.DOWNLOAD_BASE}}/v{{version}}/{{filename}}"

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
        def parse_version(v: str) -> tuple[int, int, int, float]:
            v = v.lstrip("v")
            match = re.match(r"(\\d+)\\.(\\d+)\\.(\\d+)(?:-beta\\.(\\d+))?", v)
            if match:
                major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
                beta = int(match.group(4)) if match.group(4) else float("inf")
                return (major, minor, patch, beta)
            return (0, 0, 0, 0)

        return parse_version(latest) > parse_version(current)
'''

    INIT_TEMPLATE = '''"""
{app_name} Auto-Updater.
Generated by setup_updater.py
"""

from {models_import} import UpdateChannel, UpdateCheckResult, UpdateInfo
from {app_name_lower}.core.updater.update_checker import UpdateChecker
from {app_name_lower}.core.updater.update_downloader import UpdateDownloader
from {app_name_lower}.core.updater.update_manager import UpdateManager

__all__ = [
    "UpdateChannel",
    "UpdateCheckResult",
    "UpdateChecker",
    "UpdateDownloader",
    "UpdateInfo",
    "UpdateManager",
]
'''

    # ========== PYQT6 TEMPLATES ==========

    PYQT6_DOWNLOADER_TEMPLATE = '''"""
UpdateDownloader - Download updates in background thread.
PyQt6 implementation with signals.
Generated by setup_updater.py
"""

import base64
import hashlib
import tempfile
import urllib.request
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from {models_import} import UpdateInfo


class UpdateDownloadSignals(QObject):
    """Signals for update downloader."""
    progress = pyqtSignal(int, int)  # downloaded, total
    finished = pyqtSignal(str)  # filepath
    error = pyqtSignal(str)
    verification_started = pyqtSignal()
    verification_complete = pyqtSignal(bool)


class UpdateDownloader(QObject):
    """Worker for downloading updates in background thread."""

    CHUNK_SIZE = 8192

    def __init__(self) -> None:
        super().__init__()
        self._cancelled = False
        self.signals = UpdateDownloadSignals()

    @pyqtSlot(object)
    def download(self, update_info: UpdateInfo) -> None:
        """Download installer file."""
        self._cancelled = False

        try:
            temp_dir = Path(tempfile.gettempdir()) / "{app_name_lower}_updates"
            temp_dir.mkdir(exist_ok=True)
            filepath = temp_dir / update_info.filename

            req = urllib.request.Request(
                update_info.download_url,
                headers={{"User-Agent": "{app_name}-Updater"}}
            )

            with urllib.request.urlopen(req, timeout=300) as response:
                total = int(response.headers.get("content-length", update_info.size))
                downloaded = 0

                with open(filepath, "wb") as f:
                    while not self._cancelled:
                        chunk = response.read(self.CHUNK_SIZE)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.signals.progress.emit(downloaded, total)

            if self._cancelled:
                if filepath.exists():
                    filepath.unlink()
                return

            self.signals.verification_started.emit()
            is_valid = self._verify_sha512(filepath, update_info.sha512)
            self.signals.verification_complete.emit(is_valid)

            if is_valid:
                self.signals.finished.emit(str(filepath))
            else:
                filepath.unlink()
                self.signals.error.emit("SHA512 verification failed")

        except Exception as e:
            self.signals.error.emit(str(e))

    @pyqtSlot()
    def cancel(self) -> None:
        """Cancel download."""
        self._cancelled = True

    def _verify_sha512(self, filepath: Path, expected: str) -> bool:
        if not expected:
            return True
        sha = hashlib.sha512()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(self.CHUNK_SIZE), b""):
                sha.update(chunk)
        actual = base64.b64encode(sha.digest()).decode("utf-8")
        return actual == expected
'''

    PYQT6_MANAGER_TEMPLATE = '''"""
UpdateManager - Coordinate update process.
PyQt6 implementation.
Generated by setup_updater.py
"""

import os
from typing import Optional

from PyQt6.QtCore import QMetaObject, QObject, Qt, QThread, pyqtSignal, Q_ARG

from {models_import} import UpdateChannel, UpdateCheckResult, UpdateInfo
from {app_name_lower}.core.updater.update_checker import UpdateChecker
from {app_name_lower}.core.updater.update_downloader import UpdateDownloader


class UpdateManager(QObject):
    """Manage the update process."""

    check_complete = pyqtSignal(object)  # UpdateCheckResult
    download_progress = pyqtSignal(int, int)
    download_complete = pyqtSignal(str)
    download_error = pyqtSignal(str)
    verification_started = pyqtSignal()
    verification_complete = pyqtSignal(bool)

    def __init__(self, current_version: str, channel: UpdateChannel = UpdateChannel.STABLE) -> None:
        super().__init__()
        self._checker = UpdateChecker(current_version, channel)
        self._downloader: Optional[UpdateDownloader] = None
        self._download_thread: Optional[QThread] = None
        self._current_update: Optional[UpdateInfo] = None

    @property
    def channel(self) -> UpdateChannel:
        return self._checker.channel

    @channel.setter
    def channel(self, value: UpdateChannel) -> None:
        self._checker.channel = value

    @property
    def current_version(self) -> str:
        return self._checker.current_version

    def check_for_updates(self) -> None:
        """Check for updates (synchronous). Emits check_complete."""
        result = self._checker.check_for_updates()
        if result.update_info:
            self._current_update = result.update_info
        self.check_complete.emit(result)

    def start_download(self, update_info: Optional[UpdateInfo] = None) -> None:
        """Start downloading update in background thread."""
        if update_info:
            self._current_update = update_info

        if not self._current_update:
            self.download_error.emit("No update info available")
            return

        self._download_thread = QThread()
        self._downloader = UpdateDownloader()
        self._downloader.moveToThread(self._download_thread)

        self._downloader.signals.progress.connect(self.download_progress.emit)
        self._downloader.signals.finished.connect(self._on_download_finished)
        self._downloader.signals.error.connect(self.download_error.emit)
        self._downloader.signals.verification_started.connect(self.verification_started.emit)
        self._downloader.signals.verification_complete.connect(self.verification_complete.emit)

        self._download_thread.start()

        QMetaObject.invokeMethod(
            self._downloader,
            "download",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(object, self._current_update),
        )

    def cancel_download(self) -> None:
        """Cancel ongoing download."""
        if self._downloader:
            QMetaObject.invokeMethod(
                self._downloader,
                "cancel",
                Qt.ConnectionType.QueuedConnection,
            )

    def _on_download_finished(self, filepath: str) -> None:
        self._cleanup_thread()
        self.download_complete.emit(filepath)

    def _cleanup_thread(self) -> None:
        if self._download_thread:
            self._download_thread.quit()
            self._download_thread.wait()
            self._download_thread = None
            self._downloader = None

    def launch_installer(self, filepath: str) -> bool:
        """Launch the installer executable."""
        try:
            os.startfile(filepath)
            return True
        except Exception:
            return False

    def stop(self) -> None:
        """Stop all operations."""
        self.cancel_download()
        self._cleanup_thread()
'''

    PYQT6_DIALOG_TEMPLATE = '''"""
UpdateDialog - Update notification dialog.
PyQt6 implementation.
Generated by setup_updater.py
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QGroupBox, QHBoxLayout, QLabel,
    QProgressBar, QVBoxLayout,
)
from PyQt6.QtGui import QCloseEvent

from {models_import} import UpdateCheckResult
from {app_name_lower}.core.updater.update_manager import UpdateManager


class StyledButton:
    """Simple styled button factory."""
    @staticmethod
    def create(text: str, button_type: str = "primary"):
        from PyQt6.QtWidgets import QPushButton
        from PyQt6.QtCore import Qt
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if button_type == "primary":
            btn.setStyleSheet("""
                QPushButton {{
                    background-color: #e0a800; border: none; border-radius: 6px;
                    color: #1a1a2e; font-weight: bold; padding: 10px 20px; font-size: 14px;
                }}
                QPushButton:hover {{ background-color: #f0b800; }}
                QPushButton:pressed {{ background-color: #c09000; }}
                QPushButton:disabled {{ background-color: #8a7a00; color: #4a4a4e; }}
            """)
        elif button_type == "success":
            btn.setStyleSheet("""
                QPushButton {{
                    background-color: #27ae60; border: none; border-radius: 6px;
                    color: #ffffff; font-weight: bold; padding: 10px 20px; font-size: 14px;
                }}
                QPushButton:hover {{ background-color: #2ecc71; }}
                QPushButton:pressed {{ background-color: #1e8449; }}
            """)
        else:  # secondary
            btn.setStyleSheet("""
                QPushButton {{
                    background-color: #1f2940; border: 1px solid #2d3a50; border-radius: 6px;
                    color: #ffffff; padding: 10px 20px; font-size: 14px;
                }}
                QPushButton:hover {{ background-color: #2d3a50; border-color: #3d4a60; }}
                QPushButton:pressed {{ background-color: #0f1629; }}
                QPushButton:disabled {{ background-color: #1a1a2e; color: #5a6a7a; }}
            """)
        return btn


class UpdateDialog(QDialog):
    """Update notification dialog."""

    def __init__(self, update_result: UpdateCheckResult, parent=None):
        super().__init__(parent)

        self._update_result = update_result
        self._manager = UpdateManager(update_result.current_version)
        self._downloaded_path: Optional[str] = None

        self.setWindowTitle("{app_name} Update")
        self.setMinimumWidth(450)
        self.setModal(True)
        self.setStyleSheet(self._dialog_style())

        self._setup_ui()
        self._connect_signals()

    def _dialog_style(self) -> str:
        return """
            QDialog {{ background-color: #16213e; color: #ffffff; }}
            QLabel {{ color: #ffffff; }}
            QGroupBox {{
                font-size: 13px; font-weight: bold; color: #ffffff;
                border: 1px solid #2d3a50; border-radius: 6px;
                margin-top: 10px; padding-top: 10px;
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; }}
            QProgressBar {{
                background-color: #0f1629; border: 1px solid #2d3a50;
                border-radius: 4px; text-align: center; color: #ffffff; height: 20px;
            }}
            QProgressBar::chunk {{ background-color: #e0a800; border-radius: 3px; }}
        """

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Version info
        info_group = QGroupBox("Update Available")
        info_layout = QVBoxLayout(info_group)

        version_label = QLabel(f"New version: <b>{{self._update_result.latest_version}}</b>")
        version_label.setStyleSheet("font-size: 16px;")
        info_layout.addWidget(version_label)

        current_label = QLabel(f"Your version: {{self._update_result.current_version}}")
        current_label.setStyleSheet("color: #8892a0; font-size: 13px;")
        info_layout.addWidget(current_label)

        if self._update_result.update_info:
            size_mb = self._update_result.update_info.size_mb
            if size_mb > 0:
                size_label = QLabel(f"Size: {{size_mb:.1f}} MB")
                size_label.setStyleSheet("color: #8892a0; font-size: 13px;")
                info_layout.addWidget(size_label)

        layout.addWidget(info_group)

        # Progress (hidden initially)
        self._progress_group = QGroupBox("Downloading")
        progress_layout = QVBoxLayout(self._progress_group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        progress_layout.addWidget(self._progress_bar)

        self._status_label = QLabel("Preparing...")
        self._status_label.setStyleSheet("color: #8892a0; font-size: 12px;")
        progress_layout.addWidget(self._status_label)

        self._progress_group.setVisible(False)
        layout.addWidget(self._progress_group)

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self._skip_btn = StyledButton.create("Skip", "secondary")
        self._skip_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self._skip_btn)

        self._download_btn = StyledButton.create("Download && Install", "primary")
        self._download_btn.clicked.connect(self._on_download)
        buttons_layout.addWidget(self._download_btn)

        self._install_btn = StyledButton.create("Install Now", "success")
        self._install_btn.clicked.connect(self._on_install)
        self._install_btn.setVisible(False)
        buttons_layout.addWidget(self._install_btn)

        layout.addLayout(buttons_layout)

    def _connect_signals(self) -> None:
        self._manager.download_progress.connect(self._on_progress)
        self._manager.download_complete.connect(self._on_complete)
        self._manager.download_error.connect(self._on_error)
        self._manager.verification_started.connect(self._on_verification_started)
        self._manager.verification_complete.connect(self._on_verification_complete)

    def _on_download(self) -> None:
        self._download_btn.setEnabled(False)
        self._skip_btn.setText("Cancel")
        self._skip_btn.clicked.disconnect()
        self._skip_btn.clicked.connect(self._on_cancel)
        self._progress_group.setVisible(True)
        self._status_label.setText("Downloading...")
        self._manager.start_download(self._update_result.update_info)

    def _on_cancel(self) -> None:
        self._manager.cancel_download()
        self.reject()

    def _on_progress(self, downloaded: int, total: int) -> None:
        if total > 0:
            percent = int((downloaded / total) * 100)
            self._progress_bar.setValue(percent)
            self._status_label.setText(f"Downloaded: {{downloaded / 1024 / 1024:.1f}} / {{total / 1024 / 1024:.1f}} MB")

    def _on_verification_started(self) -> None:
        self._status_label.setText("Verifying file integrity...")
        self._progress_bar.setMaximum(0)

    def _on_verification_complete(self, success: bool) -> None:
        self._progress_bar.setMaximum(100)
        if success:
            self._status_label.setText("Verification successful")
            self._status_label.setStyleSheet("color: #27ae60; font-size: 12px;")
        else:
            self._status_label.setText("Verification failed!")
            self._status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")

    def _on_complete(self, filepath: str) -> None:
        self._downloaded_path = filepath
        self._progress_bar.setValue(100)
        self._skip_btn.setText("Close")
        self._skip_btn.clicked.disconnect()
        self._skip_btn.clicked.connect(self.reject)
        self._download_btn.setVisible(False)
        self._install_btn.setVisible(True)

    def _on_error(self, error: str) -> None:
        self._status_label.setText(f"Error: {{error}}")
        self._status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        self._skip_btn.setText("Close")
        self._skip_btn.clicked.disconnect()
        self._skip_btn.clicked.connect(self.reject)
        self._download_btn.setEnabled(True)

    def _on_install(self) -> None:
        if self._downloaded_path:
            if self._manager.launch_installer(self._downloaded_path):
                from PyQt6.QtWidgets import QApplication
                QApplication.instance().quit()
            else:
                self._status_label.setText("Cannot launch installer")
                self._status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")

    def closeEvent(self, event: QCloseEvent) -> None:
        self._manager.stop()
        super().closeEvent(event)

    @staticmethod
    def show_update_dialog(update_result: UpdateCheckResult, parent=None) -> bool:
        if not update_result.update_available:
            return False
        dialog = UpdateDialog(update_result, parent)
        return dialog.exec() == QDialog.DialogCode.Accepted
'''

    # ========== CUSTOMTKINTER TEMPLATES ==========

    CTK_DOWNLOADER_TEMPLATE = '''"""
UpdateDownloader - Download updates in background thread.
CustomTkinter implementation with callbacks.
Generated by setup_updater.py
"""

import base64
import hashlib
import tempfile
import threading
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from {models_import} import UpdateInfo


class UpdateDownloader:
    """Downloads updates in background thread."""

    CHUNK_SIZE = 8192

    def __init__(self):
        self._cancelled = False
        self._thread: Optional[threading.Thread] = None

        # Callbacks
        self.on_progress: Optional[Callable[[int, int], None]] = None
        self.on_finished: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_verification: Optional[Callable[[bool], None]] = None

    def download(self, update_info: UpdateInfo) -> None:
        """Start download in background thread."""
        self._cancelled = False
        self._thread = threading.Thread(
            target=self._download_thread,
            args=(update_info,),
            daemon=True
        )
        self._thread.start()

    def cancel(self) -> None:
        """Cancel download."""
        self._cancelled = True

    def _download_thread(self, update_info: UpdateInfo) -> None:
        try:
            temp_dir = Path(tempfile.gettempdir()) / "{app_name_lower}_updates"
            temp_dir.mkdir(exist_ok=True)
            filepath = temp_dir / update_info.filename

            req = urllib.request.Request(
                update_info.download_url,
                headers={{"User-Agent": "{app_name}-Updater"}}
            )

            with urllib.request.urlopen(req, timeout=300) as response:
                total = int(response.headers.get("content-length", update_info.size))
                downloaded = 0

                with open(filepath, "wb") as f:
                    while not self._cancelled:
                        chunk = response.read(self.CHUNK_SIZE)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if self.on_progress:
                            self.on_progress(downloaded, total)

            if self._cancelled:
                filepath.unlink(missing_ok=True)
                return

            is_valid = self._verify_sha512(filepath, update_info.sha512)
            if self.on_verification:
                self.on_verification(is_valid)

            if is_valid:
                if self.on_finished:
                    self.on_finished(str(filepath))
            else:
                filepath.unlink()
                if self.on_error:
                    self.on_error("SHA512 verification failed")

        except Exception as e:
            if self.on_error:
                self.on_error(str(e))

    def _verify_sha512(self, filepath: Path, expected: str) -> bool:
        if not expected:
            return True
        sha = hashlib.sha512()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(self.CHUNK_SIZE), b""):
                sha.update(chunk)
        actual = base64.b64encode(sha.digest()).decode("utf-8")
        return actual == expected
'''

    CTK_MANAGER_TEMPLATE = '''"""
UpdateManager - Coordinate update process.
CustomTkinter implementation.
Generated by setup_updater.py
"""

import os
from typing import Optional

from {models_import} import UpdateChannel, UpdateCheckResult, UpdateInfo
from {app_name_lower}.core.updater.update_checker import UpdateChecker
from {app_name_lower}.core.updater.update_downloader import UpdateDownloader


class UpdateManager:
    """Manage the update process."""

    def __init__(self, current_version: str, channel: UpdateChannel = UpdateChannel.STABLE):
        self._checker = UpdateChecker(current_version, channel)
        self.downloader = UpdateDownloader()
        self._current_update: Optional[UpdateInfo] = None

    @property
    def channel(self) -> UpdateChannel:
        return self._checker.channel

    @channel.setter
    def channel(self, value: UpdateChannel) -> None:
        self._checker.channel = value

    @property
    def current_version(self) -> str:
        return self._checker.current_version

    def check_for_updates(self) -> UpdateCheckResult:
        """Check for updates (synchronous)."""
        result = self._checker.check_for_updates()
        if result.update_info:
            self._current_update = result.update_info
        return result

    def start_download(self, update_info: Optional[UpdateInfo] = None) -> None:
        """Start downloading update in background thread."""
        if update_info:
            self._current_update = update_info
        if self._current_update:
            self.downloader.download(self._current_update)

    def cancel_download(self) -> None:
        """Cancel ongoing download."""
        self.downloader.cancel()

    def launch_installer(self, filepath: str) -> bool:
        """Launch the installer executable."""
        try:
            os.startfile(filepath)
            return True
        except Exception:
            return False
'''

    CTK_DIALOG_TEMPLATE = '''"""
UpdateDialog - Update notification dialog.
CustomTkinter implementation.
Generated by setup_updater.py
"""

import customtkinter as ctk
from typing import Optional

from {models_import} import UpdateCheckResult
from {app_name_lower}.core.updater.update_manager import UpdateManager


class UpdateDialog(ctk.CTkToplevel):
    """Update notification dialog."""

    def __init__(self, parent, update_result: UpdateCheckResult):
        super().__init__(parent)

        self._result = update_result
        self._manager = UpdateManager(update_result.current_version)
        self._downloaded_path: Optional[str] = None

        self.title("{app_name} Update")
        self.geometry("450x300")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._setup_ui()
        self._connect_callbacks()

    def _setup_ui(self) -> None:
        ctk.CTkLabel(
            self,
            text=f"New version: {{self._result.latest_version}}",
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            self,
            text=f"Your version: {{self._result.current_version}}",
            text_color="gray"
        ).pack()

        if self._result.update_info:
            size_mb = self._result.update_info.size_mb
            if size_mb > 0:
                ctk.CTkLabel(self, text=f"Size: {{size_mb:.1f}} MB", text_color="gray").pack()

        self._progress_frame = ctk.CTkFrame(self)
        self._progress_bar = ctk.CTkProgressBar(self._progress_frame)
        self._progress_bar.set(0)
        self._progress_bar.pack(fill="x", padx=20, pady=5)
        self._status_label = ctk.CTkLabel(self._progress_frame, text="Preparing...", text_color="gray")
        self._status_label.pack()

        self._btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._btn_frame.pack(side="bottom", fill="x", padx=20, pady=20)

        self._skip_btn = ctk.CTkButton(self._btn_frame, text="Skip", command=self.destroy)
        self._skip_btn.pack(side="left")

        self._download_btn = ctk.CTkButton(self._btn_frame, text="Download && Install", command=self._on_download)
        self._download_btn.pack(side="right")

        self._install_btn = ctk.CTkButton(self._btn_frame, text="Install Now", fg_color="green", command=self._on_install)

    def _connect_callbacks(self) -> None:
        self._manager.downloader.on_progress = self._on_progress
        self._manager.downloader.on_finished = self._on_complete
        self._manager.downloader.on_error = self._on_error
        self._manager.downloader.on_verification = self._on_verification

    def _on_download(self) -> None:
        self._download_btn.configure(state="disabled")
        self._skip_btn.configure(text="Cancel", command=self._on_cancel)
        self._progress_frame.pack(fill="x", padx=20, pady=10)
        self._manager.start_download(self._result.update_info)

    def _on_cancel(self) -> None:
        self._manager.cancel_download()
        self.destroy()

    def _on_progress(self, downloaded: int, total: int) -> None:
        if total > 0:
            self._progress_bar.set(downloaded / total)
            self._status_label.configure(text=f"{{downloaded / 1024 / 1024:.1f}} / {{total / 1024 / 1024:.1f}} MB")

    def _on_verification(self, success: bool) -> None:
        color = "green" if success else "red"
        text = "Verification OK" if success else "Verification failed!"
        self._status_label.configure(text=text, text_color=color)

    def _on_complete(self, filepath: str) -> None:
        self._downloaded_path = filepath
        self._progress_bar.set(1)
        self._skip_btn.configure(text="Close", command=self.destroy)
        self._download_btn.pack_forget()
        self._install_btn.pack(side="right")

    def _on_error(self, error: str) -> None:
        self._status_label.configure(text=f"Error: {{error}}", text_color="red")
        self._download_btn.configure(state="normal")

    def _on_install(self) -> None:
        if self._downloaded_path:
            self._manager.launch_installer(self._downloaded_path)
            self.master.destroy()
'''

    # ========== CLI TEMPLATES ==========

    CLI_DOWNLOADER_TEMPLATE = CTK_DOWNLOADER_TEMPLATE  # Same as CTK (threading-based)

    CLI_MANAGER_TEMPLATE = CTK_MANAGER_TEMPLATE  # Same as CTK

    @classmethod
    def get_templates(cls, framework: str) -> Dict[str, str]:
        """Return templates for given framework."""
        base = {
            "models": cls.MODELS_TEMPLATE,
            "checker": cls.CHECKER_TEMPLATE,
            "__init__": cls.INIT_TEMPLATE,
        }

        if framework == "pyqt6":
            base.update({
                "downloader": cls.PYQT6_DOWNLOADER_TEMPLATE,
                "manager": cls.PYQT6_MANAGER_TEMPLATE,
                "dialog": cls.PYQT6_DIALOG_TEMPLATE,
            })
        elif framework == "customtkinter":
            base.update({
                "downloader": cls.CTK_DOWNLOADER_TEMPLATE,
                "manager": cls.CTK_MANAGER_TEMPLATE,
                "dialog": cls.CTK_DIALOG_TEMPLATE,
            })
        elif framework == "cli":
            base.update({
                "downloader": cls.CLI_DOWNLOADER_TEMPLATE,
                "manager": cls.CLI_MANAGER_TEMPLATE,
            })

        return base


# ============================================================================
# ENVIRONMENT CHECKER
# ============================================================================

class EnvironmentChecker:
    """Check environment before initializing updater."""

    def __init__(self, config: UpdaterConfig):
        self.config = config
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def check_all(self) -> bool:
        """Run all checks."""
        header(f"Setup Updater - Environment Check v{SCRIPT_VERSION}")

        checks = [
            ("Python Version", self.check_python),
            ("Configuration", self.check_configuration),
            ("Project Structure", self.check_structure),
            ("GitHub Access", self.check_github),
            ("Existing Files", self.check_existing),
            ("Dependencies", self.check_dependencies),
        ]

        for name, check_fn in checks:
            subheader(name)
            try:
                check_fn()
            except Exception as e:
                self.errors.append(f"{name}: {e}")

        self._print_summary()
        return len(self.errors) == 0

    def check_python(self) -> None:
        """Check Python version."""
        current = sys.version_info[:2]
        log(f"Current: Python {current[0]}.{current[1]}", "check")
        log(f"Required: Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+", "check")

        if current >= MIN_PYTHON_VERSION:
            log("Python version OK", "ok")
        else:
            self.errors.append(f"Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+ required")
            log("Python version too old", "error")

    def check_configuration(self) -> None:
        """Check pyproject.toml configuration."""
        log(f"App name: {self.config.app_name}", "check")
        log(f"Releases repo: {self.config.releases_repo}", "check")
        log(f"UI framework: {self.config.ui_framework}", "check")
        log(f"Update delay: {self.config.update_check_delay} ms", "check")

        if not self.config.app_name:
            self.errors.append("app_name not configured in [tool.updater]")
            log("app_name: NOT SET", "error")
        else:
            log("app_name: OK", "ok")

        if not self.config.releases_repo:
            self.errors.append("releases_repo not configured in [tool.updater]")
            log("releases_repo: NOT SET", "error")
        else:
            log("releases_repo: OK", "ok")

        if self.config.ui_framework not in SUPPORTED_FRAMEWORKS:
            self.errors.append(f"Unsupported framework: {self.config.ui_framework}")
            log(f"ui_framework: INVALID (use: {', '.join(SUPPORTED_FRAMEWORKS)})", "error")
        else:
            log("ui_framework: OK", "ok")

    def check_structure(self) -> None:
        """Check project structure."""
        src_dir = self.config.project_root / "src" / self.config.app_name_lower
        core_dir = src_dir / "core"

        if src_dir.exists():
            log(f"src/{self.config.app_name_lower}/ exists", "ok")
        else:
            self.errors.append(f"src/{self.config.app_name_lower}/ not found")
            log(f"src/{self.config.app_name_lower}/ NOT FOUND", "error")
            return

        if core_dir.exists():
            log(f"src/{self.config.app_name_lower}/core/ exists", "ok")
        else:
            self.warnings.append(f"src/{self.config.app_name_lower}/core/ not found (will be created)")
            log(f"src/{self.config.app_name_lower}/core/ NOT FOUND (will be created)", "warn")

    def check_github(self) -> None:
        """Check GitHub access."""
        if not self.config.releases_repo:
            log("Skipping (no releases_repo configured)", "warn")
            return

        # Check if repo exists
        url = f"https://github.com/{self.config.releases_repo}"
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "SetupUpdater"})
            urllib.request.urlopen(req, timeout=10)
            log(f"Releases repo accessible: {self.config.releases_repo}", "ok")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.warnings.append(f"Releases repo not found: {self.config.releases_repo}")
                log(f"Releases repo NOT FOUND (will need to create)", "warn")
                print(f"\n{C.YELLOW}Create with:{C.RESET}")
                print(f"  gh repo create {self.config.releases_repo} --public")
            else:
                self.errors.append(f"Cannot access releases repo: HTTP {e.code}")
                log(f"Cannot access releases repo: HTTP {e.code}", "error")
        except Exception as e:
            self.errors.append(f"Cannot access GitHub: {e}")
            log(f"Cannot access GitHub: {e}", "error")

        # Check for latest.yml
        yml_url = f"https://raw.githubusercontent.com/{self.config.releases_repo}/main/latest.yml"
        try:
            req = urllib.request.Request(yml_url, headers={"User-Agent": "SetupUpdater"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode("utf-8")
                if "version:" in content:
                    # Extract version
                    for line in content.split("\n"):
                        if line.startswith("version:"):
                            version = line.split(":", 1)[1].strip().strip("'\"")
                            log(f"latest.yml found (v{version})", "ok")
                            break
                else:
                    self.warnings.append("latest.yml has invalid format")
                    log("latest.yml: INVALID FORMAT", "warn")
        except urllib.error.HTTPError:
            self.info.append("No latest.yml yet (normal for new projects)")
            log("latest.yml: NOT FOUND (normal for new projects)", "info")
        except Exception:
            pass

    def check_existing(self) -> None:
        """Check for existing updater files."""
        updater_dir = self.config.resolve_path(self.config.updater_module)

        if updater_dir.exists():
            files = list(updater_dir.glob("*.py"))
            if files:
                self.warnings.append(f"Updater already exists at {updater_dir}")
                log(f"Updater exists: {updater_dir}", "warn")
                print(f"\n{C.YELLOW}Files found:{C.RESET}")
                for f in files:
                    print(f"  - {f.name}")
                print(f"\n{C.YELLOW}Use --force to overwrite{C.RESET}")
            else:
                log("Updater directory empty", "ok")
        else:
            log("No existing updater (ready to create)", "ok")

    def check_dependencies(self) -> None:
        """Check framework dependencies."""
        framework = self.config.ui_framework

        if framework == "pyqt6":
            try:
                import PyQt6
                log("PyQt6: installed", "ok")
            except ImportError:
                self.warnings.append("PyQt6 not installed")
                log("PyQt6: NOT INSTALLED", "warn")
                print(f"\n{C.YELLOW}Install with:{C.RESET}")
                print("  pip install PyQt6")
        elif framework == "customtkinter":
            try:
                import customtkinter
                log("customtkinter: installed", "ok")
            except ImportError:
                self.warnings.append("customtkinter not installed")
                log("customtkinter: NOT INSTALLED", "warn")
                print(f"\n{C.YELLOW}Install with:{C.RESET}")
                print("  pip install customtkinter")
        elif framework == "cli":
            log("CLI mode: no UI dependencies required", "ok")

    def _print_summary(self) -> None:
        """Print summary."""
        header("Summary")

        if self.errors:
            print(f"{C.RED}{C.BOLD}ERRORS ({len(self.errors)}):{C.RESET}")
            for error in self.errors:
                print(f"  {C.RED}X{C.RESET} {error}")
            print()

        if self.warnings:
            print(f"{C.YELLOW}{C.BOLD}WARNINGS ({len(self.warnings)}):{C.RESET}")
            for warning in self.warnings:
                print(f"  {C.YELLOW}!{C.RESET} {warning}")
            print()

        if not self.errors and not self.warnings:
            print(f"{C.GREEN}{C.BOLD}All checks passed! Ready to initialize.{C.RESET}")
            print(f"\n{C.CYAN}Next step:{C.RESET}")
            print("  python scripts/setup_updater.py --init")
        elif not self.errors:
            print(f"{C.YELLOW}{C.BOLD}Checks passed with warnings.{C.RESET}")
            print(f"\n{C.CYAN}Next step:{C.RESET}")
            print("  python scripts/setup_updater.py --init")
        else:
            print(f"{C.RED}{C.BOLD}Fix errors before initializing.{C.RESET}")


# ============================================================================
# SETUP MANAGER
# ============================================================================

class SetupManager:
    """Manage updater initialization."""

    def __init__(self, config: UpdaterConfig, dry_run: bool = False, force: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.force = force
        self.created_files: List[Path] = []
        self.created_dirs: List[Path] = []

    def execute(self) -> None:
        """Execute full initialization."""
        header(f"Setup Updater v{SCRIPT_VERSION}")

        log(f"App: {self.config.app_name}", "info")
        log(f"Framework: {self.config.ui_framework}", "info")
        log(f"Mode: {'DRY-RUN' if self.dry_run else 'PRODUCTION'}", "info")

        try:
            self.step1_validate()
            self.step2_create_directories()
            self.step3_generate_models()
            self.step4_generate_checker()
            self.step5_generate_downloader()
            self.step6_generate_manager()
            self.step7_generate_init()
            self.step8_generate_dialog()
            self.step9_show_integration()
            self.show_summary()
        except Exception as e:
            log(f"Setup FAILED: {e}", "error")
            self.rollback()
            sys.exit(1)

    def step1_validate(self) -> None:
        """Validate before generating."""
        subheader("Step 1: Validate")

        updater_dir = self.config.resolve_path(self.config.updater_module)
        if updater_dir.exists() and list(updater_dir.glob("*.py")):
            if not self.force:
                raise ValueError(
                    f"Updater already exists at {updater_dir}\n"
                    "Use --force to overwrite"
                )
            log("Existing files will be overwritten (--force)", "warn")
        else:
            log("No conflicts", "ok")

    def step2_create_directories(self) -> None:
        """Create directories."""
        subheader("Step 2: Create Directories")

        dirs = [self.config.resolve_path(self.config.updater_module)]

        if self.config.ui_framework != "cli":
            dialog_dir = self.config.resolve_path(self.config.dialog_file).parent
            if dialog_dir not in dirs:
                dirs.append(dialog_dir)

        for dir_path in dirs:
            if not dir_path.exists():
                if not self.dry_run:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    self.created_dirs.append(dir_path)
                log(f"Created: {dir_path}", "ok" if not self.dry_run else "dry")
            else:
                log(f"Exists: {dir_path}", "ok")

    def step3_generate_models(self) -> None:
        """Generate models.py."""
        subheader("Step 3: Generate Models")
        self._write_template("models", "models.py")

    def step4_generate_checker(self) -> None:
        """Generate update_checker.py."""
        subheader("Step 4: Generate Checker")
        self._write_template("checker", "update_checker.py")

    def step5_generate_downloader(self) -> None:
        """Generate update_downloader.py."""
        subheader("Step 5: Generate Downloader")
        self._write_template("downloader", "update_downloader.py")

    def step6_generate_manager(self) -> None:
        """Generate update_manager.py."""
        subheader("Step 6: Generate Manager")
        self._write_template("manager", "update_manager.py")

    def step7_generate_init(self) -> None:
        """Generate __init__.py."""
        subheader("Step 7: Generate __init__.py")
        self._write_template("__init__", "__init__.py")

    def step8_generate_dialog(self) -> None:
        """Generate dialog UI."""
        subheader("Step 8: Generate Dialog")

        if self.config.ui_framework == "cli":
            log("CLI mode - skipping dialog generation", "info")
            return

        templates = TemplateRegistry.get_templates(self.config.ui_framework)
        content = templates["dialog"].format(**self._get_placeholders())

        dialog_path = self.config.resolve_path(self.config.dialog_file)

        if not self.dry_run:
            dialog_path.parent.mkdir(parents=True, exist_ok=True)
            dialog_path.write_text(content, encoding="utf-8")
            self.created_files.append(dialog_path)

        log(f"Generated: {dialog_path}", "ok" if not self.dry_run else "dry")

    def step9_show_integration(self) -> None:
        """Show integration code."""
        subheader("Step 9: Integration Code")

        if self.config.ui_framework == "pyqt6":
            print(f"""
{C.CYAN}Add to your MainWindow.__init__():{C.RESET}

    from PyQt6.QtCore import QTimer
    from {self.config.app_name_lower}.core.updater import UpdateManager, UpdateChannel
    from {self.config.app_name_lower}.ui.dialogs.update_dialog import UpdateDialog
    from {self.config.app_name_lower} import __version__

    # In __init__:
    QTimer.singleShot({self.config.update_check_delay}, self._check_for_updates)

    def _check_for_updates(self):
        channel = self._load_update_channel()
        self._update_manager = UpdateManager(__version__, channel)
        self._update_manager.check_complete.connect(self._on_update_check)
        self._update_manager.check_for_updates()

    def _load_update_channel(self) -> UpdateChannel:
        \"\"\"Load update channel from settings.\"\"\"
        import json
        from pathlib import Path
        config_path = Path.home() / ".{self.config.app_name_lower}" / "settings.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    channel = settings.get("update_channel", "stable")
                    return UpdateChannel.BETA if channel == "beta" else UpdateChannel.STABLE
        except Exception:
            pass
        return UpdateChannel.STABLE

    def _on_update_check(self, result):
        if result.update_available:
            UpdateDialog.show_update_dialog(result, self)

{C.YELLOW}--- Settings Page (Channel Selection) ---{C.RESET}

{C.CYAN}Add to your SettingsPage (example code):{C.RESET}

    import json
    from pathlib import Path
    from PyQt6.QtWidgets import QComboBox, QLabel, QHBoxLayout

    # Create update channel selector:
    channel_layout = QHBoxLayout()
    channel_label = QLabel("Update Channel:")
    self._channel_combo = QComboBox()
    self._channel_combo.addItems(["stable", "beta"])
    self._channel_combo.setCurrentText(self._load_channel_setting())
    self._channel_combo.currentTextChanged.connect(self._on_channel_changed)
    channel_layout.addWidget(channel_label)
    channel_layout.addWidget(self._channel_combo)

    def _load_channel_setting(self) -> str:
        config_path = Path.home() / ".{self.config.app_name_lower}" / "settings.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f).get("update_channel", "stable")
        except Exception:
            pass
        return "stable"

    def _on_channel_changed(self, channel: str):
        config_dir = Path.home() / ".{self.config.app_name_lower}"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "settings.json"
        try:
            settings = {{}}
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            settings["update_channel"] = channel
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save channel setting: {{e}}")
""")
        elif self.config.ui_framework == "customtkinter":
            print(f"""
{C.CYAN}Add to your App class:{C.RESET}

    import json
    from pathlib import Path
    from {self.config.app_name_lower}.core.updater import UpdateManager, UpdateChannel
    from {self.config.app_name_lower}.ui.dialogs.update_dialog import UpdateDialog

    # In __init__:
    self.after({self.config.update_check_delay}, self._check_for_updates)

    def _check_for_updates(self):
        channel = self._load_update_channel()
        manager = UpdateManager(self._get_version(), channel)
        result = manager.check_for_updates()
        if result.update_available:
            UpdateDialog(self, result)

    def _load_update_channel(self) -> UpdateChannel:
        config_path = Path.home() / ".{self.config.app_name_lower}" / "settings.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    channel = json.load(f).get("update_channel", "stable")
                    return UpdateChannel.BETA if channel == "beta" else UpdateChannel.STABLE
        except Exception:
            pass
        return UpdateChannel.STABLE

{C.YELLOW}--- Settings (Channel Selection) ---{C.RESET}

{C.CYAN}Add channel selector to settings:{C.RESET}

    import customtkinter as ctk

    # Create dropdown for update channel:
    ctk.CTkLabel(self, text="Update Channel:").pack()
    self._channel_var = ctk.StringVar(value=self._load_channel_setting())
    ctk.CTkOptionMenu(
        self,
        values=["stable", "beta"],
        variable=self._channel_var,
        command=self._on_channel_changed
    ).pack()

    def _load_channel_setting(self) -> str:
        config_path = Path.home() / ".{self.config.app_name_lower}" / "settings.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f).get("update_channel", "stable")
        except Exception:
            pass
        return "stable"

    def _on_channel_changed(self, channel: str):
        config_dir = Path.home() / ".{self.config.app_name_lower}"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "settings.json"
        settings = {{}}
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
        except Exception:
            pass
        settings["update_channel"] = channel
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
""")
        elif self.config.ui_framework == "cli":
            print(f"""
{C.CYAN}Add to your main():{C.RESET}

    import json
    from pathlib import Path
    from {self.config.app_name_lower}.core.updater import UpdateManager, UpdateChannel

    def load_update_channel() -> UpdateChannel:
        config_path = Path.home() / ".{self.config.app_name_lower}" / "settings.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    channel = json.load(f).get("update_channel", "stable")
                    return UpdateChannel.BETA if channel == "beta" else UpdateChannel.STABLE
        except Exception:
            pass
        return UpdateChannel.STABLE

    def check_for_updates(current_version: str):
        channel = load_update_channel()
        manager = UpdateManager(current_version, channel)
        result = manager.check_for_updates()
        if result.update_available:
            print(f"Update available: {{result.latest_version}}")
            print(f"Download: {{result.update_info.download_url}}")

{C.YELLOW}--- CLI option for channel selection ---{C.RESET}

    # Add --channel argument:
    parser.add_argument("--channel", choices=["stable", "beta"], help="Update channel")

    # Save channel setting:
    def set_update_channel(channel: str):
        config_dir = Path.home() / ".{self.config.app_name_lower}"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "settings.json"
        settings = {{}}
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
        except Exception:
            pass
        settings["update_channel"] = channel
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        print(f"Update channel set to: {{channel}}")
""")

    def _write_template(self, template_name: str, filename: str) -> None:
        """Write template to file."""
        templates = TemplateRegistry.get_templates(self.config.ui_framework)
        content = templates[template_name].format(**self._get_placeholders())

        filepath = self.config.resolve_path(self.config.updater_module) / filename

        if not self.dry_run:
            filepath.write_text(content, encoding="utf-8")
            self.created_files.append(filepath)

        log(f"Generated: {filepath}", "ok" if not self.dry_run else "dry")

    def _get_placeholders(self) -> Dict[str, str]:
        """Get template placeholders."""
        models_import = (
            f"{self.config.app_name_lower}.core.updater.models"
            if self.config.models_location == "separate"
            else f"{self.config.app_name_lower}.core.models"
        )

        return {
            "app_name": self.config.app_name,
            "app_name_lower": self.config.app_name_lower,
            "releases_repo": self.config.releases_repo,
            "owner": self.config.owner,
            "repo": self.config.repo,
            "models_import": models_import,
        }

    def rollback(self) -> None:
        """Remove created files on error."""
        if self.dry_run:
            return

        log("Rolling back...", "warn")

        for f in reversed(self.created_files):
            if f.exists():
                f.unlink()
                log(f"Removed: {f}", "warn")

        for d in reversed(self.created_dirs):
            if d.exists() and not any(d.iterdir()):
                d.rmdir()
                log(f"Removed dir: {d}", "warn")

    def show_summary(self) -> None:
        """Show summary."""
        header("SUMMARY")

        if self.dry_run:
            log("Dry-run mode - no files created", "warn")
            return

        print(f"{C.GREEN}Updater setup completed!{C.RESET}\n")

        print("Created files:")
        for f in self.created_files:
            print(f"  {C.GREEN}+{C.RESET} {f}")

        print(f"\n{C.YELLOW}Next steps:{C.RESET}")
        print("  1. Review generated files")
        print("  2. Add integration code to main window")
        print(f"  3. Test: python -m {self.config.app_name_lower}")
        print(f"  4. Release: python scripts/release.py X.Y.Z")


# ============================================================================
# UPDATE TESTER
# ============================================================================

class UpdateTester:
    """Test update system."""

    def __init__(self, config: UpdaterConfig):
        self.config = config

    def run_tests(self) -> bool:
        """Run all tests."""
        header(f"Update System Test v{SCRIPT_VERSION}")

        tests = [
            ("Connection to releases repo", self.test_connection),
            ("Fetch latest.yml", self.test_fetch_yml),
            ("Version comparison", self.test_version_comparison),
        ]

        all_passed = True
        for name, test_fn in tests:
            subheader(name)
            try:
                test_fn()
                log("PASSED", "ok")
            except Exception as e:
                log(f"FAILED: {e}", "error")
                all_passed = False

        header("Summary")
        if all_passed:
            print(f"{C.GREEN}All tests passed!{C.RESET}")
        else:
            print(f"{C.RED}Some tests failed.{C.RESET}")

        return all_passed

    def test_connection(self) -> None:
        """Test HTTP connection."""
        url = f"https://github.com/{self.config.releases_repo}"
        log(f"Testing: {url}", "info")

        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "SetupUpdater"})
        urllib.request.urlopen(req, timeout=10)
        log("Connection successful", "ok")

    def test_fetch_yml(self) -> None:
        """Test fetching latest.yml."""
        url = f"https://raw.githubusercontent.com/{self.config.releases_repo}/main/latest.yml"
        log(f"Fetching: {url}", "info")

        req = urllib.request.Request(url, headers={"User-Agent": "SetupUpdater"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode("utf-8")
                log(f"Content ({len(content)} bytes):", "info")
                for line in content.strip().split("\n")[:5]:
                    print(f"    {line}")
                if "version:" not in content:
                    raise ValueError("Invalid YML format (missing 'version' field)")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                log("latest.yml not found (no releases yet)", "warn")
            else:
                raise

    def test_version_comparison(self) -> None:
        """Test version comparison logic."""
        test_cases = [
            ("1.0.1", "1.0.0", True, "newer patch"),
            ("1.1.0", "1.0.0", True, "newer minor"),
            ("2.0.0", "1.0.0", True, "newer major"),
            ("1.0.0", "1.0.1", False, "older"),
            ("1.0.0", "1.0.0", False, "same"),
            ("1.0.0", "1.0.0-beta.1", True, "stable > beta"),
            ("1.0.0-beta.2", "1.0.0-beta.1", True, "newer beta"),
        ]

        for latest, current, expected, desc in test_cases:
            result = self._is_newer(latest, current)
            status = "OK" if result == expected else "FAIL"
            symbol = C.GREEN + "[OK]" if result == expected else C.RED + "[FAIL]"
            print(f"  {symbol}{C.RESET} {latest} > {current} = {result} ({desc})")
            if result != expected:
                raise ValueError(f"Version comparison failed: {latest} vs {current}")

    def _is_newer(self, latest: str, current: str) -> bool:
        """Check if latest > current."""
        def parse(v: str) -> Tuple[int, int, int, float]:
            v = v.lstrip("v")
            match = re.match(r"(\d+)\.(\d+)\.(\d+)(?:-beta\.(\d+))?", v)
            if match:
                major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
                beta = int(match.group(4)) if match.group(4) else float("inf")
                return (major, minor, patch, beta)
            return (0, 0, 0, 0)

        return parse(latest) > parse(current)


# ============================================================================
# MAIN
# ============================================================================

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=f"Setup Auto-Updater v{SCRIPT_VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/setup_updater.py --check              # Check environment
  python scripts/setup_updater.py --init               # Generate updater files
  python scripts/setup_updater.py --init --dry-run     # Simulate generation
  python scripts/setup_updater.py --init --force       # Overwrite existing
  python scripts/setup_updater.py --test               # Test connection
""",
    )

    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="Check environment without changes"
    )
    parser.add_argument(
        "--init", "-i",
        action="store_true",
        help="Initialize updater (generate files)"
    )
    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="Test connection and parsing"
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Simulate without creating files"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing files"
    )
    parser.add_argument(
        "--framework",
        choices=SUPPORTED_FRAMEWORKS,
        help="Override UI framework"
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    try:
        config = UpdaterConfig.load()
    except Exception as e:
        log(f"Configuration error: {e}", "error")
        sys.exit(1)

    # Override framework if specified
    if args.framework:
        config.ui_framework = args.framework

    if args.check:
        checker = EnvironmentChecker(config)
        success = checker.check_all()
        sys.exit(0 if success else 1)

    if args.test:
        tester = UpdateTester(config)
        success = tester.run_tests()
        sys.exit(0 if success else 1)

    if args.init:
        manager = SetupManager(config, dry_run=args.dry_run, force=args.force)
        manager.execute()
        sys.exit(0)

    # Default: show help
    print(f"{C.BOLD}Setup Auto-Updater v{SCRIPT_VERSION}{C.RESET}\n")
    print("Usage:")
    print("  python scripts/setup_updater.py --check    # Check environment")
    print("  python scripts/setup_updater.py --init     # Generate updater files")
    print("  python scripts/setup_updater.py --test     # Test connection")
    print("\nRun with -h for more options.")


if __name__ == "__main__":
    main()
