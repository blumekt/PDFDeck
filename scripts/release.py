#!/usr/bin/env python3
"""
Universal Release Script v2.1

Portable release automation script for desktop applications.
Copy this entire 'scripts' folder to any new project - it will auto-configure itself.

Features:
- Auto-detection of project configuration from pyproject.toml
- Full environment validation (--check flag)
- Version update in multiple files (pyproject.toml, __init__.py, installer.iss, file_version_info.txt)
- Build: PyInstaller + Inno Setup
- Auto-update support (latest.yml/beta.yml with SHA512)
- GitHub Release with separate releases repository
- Push yml files to releases repo for auto-updater
- Dry-run mode, rollback on errors
- Colored terminal output

Usage:
    python scripts/release.py --check           # Check all requirements
    python scripts/release.py 1.0.1             # Release version 1.0.1
    python scripts/release.py 1.0.1-beta.1      # Release beta version
    python scripts/release.py 1.0.1 --dry-run   # Simulate release
    python scripts/release.py 1.0.1 --force     # Skip confirmations

Configuration:
    Add to pyproject.toml:

    [tool.release]
    app_name = "MyApp"
    releases_repo = "username/myapp-releases"
    installer_name = "MyApp_Setup_{version}.exe"
    spec_file = "myapp.spec"
    installer_iss = "installer/myapp_installer.iss"
    init_file = "src/myapp/__init__.py"  # Optional override
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# ============================================================================
# CONSTANTS
# ============================================================================

SCRIPT_VERSION = "2.2"
MIN_PYTHON_VERSION = (3, 9)

# Required files for release
REQUIRED_FILES = [
    "pyproject.toml",
    "file_version_info.txt",
]

# Required Python packages (module_name: display_name)
REQUIRED_PACKAGES = {
    "PyInstaller": "PyInstaller",
    "packaging": "packaging",
}

# Optional packages (for Python < 3.11)
OPTIONAL_PACKAGES = {
    "tomli": "tomli (for Python < 3.11)",
}


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

    # Disable colors on Windows without ANSI support
    @classmethod
    def init(cls) -> None:
        """Initialize colors (enable ANSI on Windows if possible)."""
        if platform.system() == "Windows":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except Exception:
                # Disable colors if ANSI not supported
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
class Config:
    """Release configuration loaded from pyproject.toml."""
    # Required
    app_name: str = ""
    releases_repo: str = ""

    # Paths (with defaults)
    pyproject_toml: str = "pyproject.toml"
    installer_iss: str = "installer/{app_name}_installer.iss"
    version_info: str = "file_version_info.txt"
    init_file: str = "src/{app_name}/__init__.py"  # Default location for __init__.py
    release_dir: str = "release"
    dist_dir: str = "dist"
    latest_yml: str = "release/latest.yml"
    beta_yml: str = "release/beta.yml"
    installer_name: str = "{app_name}_Setup_{version}.exe"
    spec_file: str = "{app_name}.spec"
    package_json: str = ""  # Optional: path to package.json
    build_method: str = "innosetup"  # "innosetup" or "electron"
    frontend_dir: str = "frontend"  # Directory containing package.json for electron-builder

    # Current version (read from pyproject.toml)
    current_version: str = ""

    # Computed
    project_root: Path = field(default_factory=Path)

    @classmethod
    def load(cls, project_root: Optional[Path] = None) -> "Config":
        """Load configuration from pyproject.toml."""
        if project_root is None:
            # Find project root (directory containing pyproject.toml)
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
        current_version = project.get("version", "0.0.0")

        # Get release config
        tool_release = data.get("tool", {}).get("release", {})
        tool_spectra = data.get("tool", {}).get("spectra", {})  # Backward compat

        # Merge configs (tool.release takes precedence)
        release_config = {**tool_spectra, **tool_release}

        # Extract app name from various sources
        app_name = (
            release_config.get("app_name") or
            tool_spectra.get("app_name") or
            project.get("name", "").capitalize() or
            "App"
        )

        # Extract releases repo
        releases_repo = (
            release_config.get("releases_repo") or
            tool_spectra.get("releases_repo") or
            ""
        )

        # Create config
        config = cls(
            app_name=app_name,
            releases_repo=releases_repo,
            current_version=current_version,
            project_root=project_root,
        )

        # Override with custom values from config
        configurable_paths = [
            "pyproject_toml", "installer_iss", "version_info", "init_file",
            "release_dir", "dist_dir", "latest_yml", "beta_yml",
            "installer_name", "spec_file", "package_json", "build_method",
            "frontend_dir"
        ]

        for key in configurable_paths:
            if key in release_config:
                setattr(config, key, release_config[key])

        # Replace {app_name} placeholder in paths
        for attr in ["installer_iss", "installer_name", "spec_file", "init_file"]:
            value = getattr(config, attr)
            setattr(config, attr, value.replace("{app_name}", app_name.lower()))

        return config

    def resolve_path(self, path: str) -> Path:
        """Resolve a path relative to project root."""
        return self.project_root / path


# ============================================================================
# UTILITIES
# ============================================================================

def validate_version(version: str) -> bool:
    """Validate version format (x.y.z or x.y.z-beta.n)."""
    stable_pattern = r"^\d+\.\d+\.\d+$"
    beta_pattern = r"^\d+\.\d+\.\d+-beta\.\d+$"
    return bool(re.match(stable_pattern, version) or re.match(beta_pattern, version))


def is_beta(version: str) -> bool:
    """Check if version is a beta release."""
    return "-beta" in version


def to_numeric_version(version: str) -> str:
    """Convert version to numeric format (x.y.z.0)."""
    base = re.sub(r"-beta\.\d+$", "", version)
    return f"{base}.0"


def to_file_version_tuple(version: str) -> Tuple[int, int, int, int]:
    """Convert version to tuple for file_version_info.txt."""
    base = re.sub(r"-beta\.\d+$", "", version)
    parts = base.split(".")
    return (int(parts[0]), int(parts[1]), int(parts[2]), 0)


def run(cmd: str, silent: bool = False, ignore_error: bool = False,
        dry_run: bool = False, cwd: Optional[Path] = None) -> Tuple[bool, str]:
    """Execute a shell command."""
    if dry_run:
        log(f"Would run: {cmd}", "dry")
        return True, ""

    if not silent:
        log(f"Running: {cmd}", "info")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=cwd,
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""

        if result.returncode != 0 and not ignore_error:
            if not silent:
                log(f"Command failed: {stderr}", "error")
            return False, stderr
        return True, stdout
    except Exception as e:
        if not ignore_error:
            log(f"Error: {e}", "error")
        return False, str(e)


def sha512_file(filepath: Path) -> str:
    """Calculate SHA512 hash of a file (base64 encoded)."""
    sha = hashlib.sha512()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return base64.b64encode(sha.digest()).decode("utf-8")


def file_size(filepath: Path) -> int:
    """Get file size in bytes."""
    return filepath.stat().st_size


def prompt(question: str) -> str:
    """Ask user for confirmation."""
    return input(question).strip().lower()


def check_command(cmd: str, name: str) -> Tuple[bool, str]:
    """Check if a command is available."""
    success, output = run(cmd, silent=True, ignore_error=True)
    return success, output


def find_executable(name: str, paths: List[str]) -> Optional[str]:
    """Find executable in given paths or PATH."""
    # Check PATH first
    success, _ = run(f"where {name}", silent=True, ignore_error=True)
    if success:
        return name

    # Check specific paths
    for path in paths:
        if Path(path).exists():
            return f'"{path}"'

    return None


# ============================================================================
# ENVIRONMENT CHECKER
# ============================================================================

class EnvironmentChecker:
    """Checks if all requirements are met for release."""

    def __init__(self, config: Config):
        self.config = config
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def check_all(self) -> bool:
        """Run all checks and return True if everything is OK."""
        header(f"Environment Check - Release Script v{SCRIPT_VERSION}")

        checks = [
            ("Python Version", self.check_python),
            ("Required Packages", self.check_packages),
            ("Git", self.check_git),
            ("GitHub CLI", self.check_gh_cli),
            ("PyInstaller", self.check_pyinstaller),
            ("Inno Setup", self.check_inno_setup),
            ("Project Files", self.check_project_files),
            ("Configuration", self.check_configuration),
            ("Git Repository", self.check_git_repo),
            ("Releases Repository", self.check_releases_repo),
        ]

        for name, check_fn in checks:
            subheader(name)
            try:
                check_fn()
            except Exception as e:
                self.errors.append(f"{name}: {e}")

        # Summary
        self._print_summary()

        return len(self.errors) == 0

    def check_python(self) -> None:
        """Check Python version."""
        current = sys.version_info[:2]
        required = MIN_PYTHON_VERSION

        log(f"Current: Python {current[0]}.{current[1]}", "check")
        log(f"Required: Python {required[0]}.{required[1]}+", "check")

        if current >= required:
            log(f"Python version OK", "ok")
        else:
            self.errors.append(
                f"Python {required[0]}.{required[1]}+ required, "
                f"but you have {current[0]}.{current[1]}"
            )

    def check_packages(self) -> None:
        """Check required Python packages."""
        import importlib

        # Check required packages
        for package, display_name in REQUIRED_PACKAGES.items():
            try:
                importlib.import_module(package.replace("-", "_"))
                log(f"{display_name}: installed", "ok")
            except ImportError:
                self.errors.append(f"Package '{package}' not installed. Run: pip install {package}")
                log(f"{display_name}: NOT FOUND", "error")

        # Check optional packages
        if sys.version_info < (3, 11):
            for package, display_name in OPTIONAL_PACKAGES.items():
                try:
                    importlib.import_module(package)
                    log(f"{display_name}: installed", "ok")
                except ImportError:
                    self.errors.append(f"Package '{package}' required for Python < 3.11. Run: pip install {package}")
                    log(f"{display_name}: NOT FOUND (required for Python < 3.11)", "error")
        else:
            log("tomllib: built-in (Python 3.11+)", "ok")

    def check_git(self) -> None:
        """Check Git installation."""
        success, output = check_command("git --version", "Git")
        if success:
            version = output.strip().split()[-1] if output else "unknown"
            log(f"Git version: {version}", "ok")
        else:
            self.errors.append("Git is not installed or not in PATH")
            log("Git: NOT FOUND", "error")
            print(f"\n{C.YELLOW}Install Git:{C.RESET}")
            print("  Windows: https://git-scm.com/download/win")
            print("  Or: winget install Git.Git")

    def check_gh_cli(self) -> None:
        """Check GitHub CLI installation and authentication."""
        # Check if installed
        success, output = check_command("gh --version", "GitHub CLI")
        if not success:
            self.errors.append("GitHub CLI (gh) is not installed")
            log("GitHub CLI: NOT FOUND", "error")
            print(f"\n{C.YELLOW}Install GitHub CLI:{C.RESET}")
            print("  Windows: winget install GitHub.cli")
            print("  Or: https://cli.github.com/")
            return

        version = output.strip().split()[2] if output else "unknown"
        log(f"GitHub CLI version: {version}", "ok")

        # Check authentication
        success, auth_output = check_command("gh auth status", "gh auth")
        if not success:
            self.errors.append("GitHub CLI not authenticated. Run: gh auth login")
            log("GitHub CLI: NOT AUTHENTICATED", "error")
            print(f"\n{C.YELLOW}Authenticate GitHub CLI:{C.RESET}")
            print("  gh auth login")
            return

        log("GitHub CLI: authenticated", "ok")

        # Check scopes
        required_scopes = ["repo", "workflow"]
        missing_scopes = []
        for scope in required_scopes:
            if scope not in auth_output:
                missing_scopes.append(scope)

        if missing_scopes:
            self.warnings.append(f"Missing GitHub scopes: {', '.join(missing_scopes)}")
            log(f"Missing scopes: {', '.join(missing_scopes)}", "warn")
            print(f"\n{C.YELLOW}Add missing scopes:{C.RESET}")
            print(f"  gh auth refresh -h github.com -s {','.join(missing_scopes)}")
        else:
            log("GitHub CLI scopes: OK", "ok")

    def check_pyinstaller(self) -> None:
        """Check PyInstaller installation."""
        success, output = check_command("python -m PyInstaller --version", "PyInstaller")
        if success:
            version = output.strip() if output else "unknown"
            log(f"PyInstaller version: {version}", "ok")
        else:
            self.errors.append("PyInstaller not installed. Run: pip install pyinstaller")
            log("PyInstaller: NOT FOUND", "error")

    def check_inno_setup(self) -> None:
        """Check Inno Setup installation (only for innosetup build method)."""
        if self.config.build_method == "electron":
            log("Inno Setup: skipped (using electron-builder)", "ok")
            # Check npm instead
            frontend_dir = self.config.resolve_path(self.config.frontend_dir)
            if (frontend_dir / "package.json").exists():
                log(f"electron-builder: package.json found in {self.config.frontend_dir}", "ok")
            else:
                self.errors.append(f"package.json not found in {self.config.frontend_dir}")
                log(f"electron-builder: package.json NOT FOUND", "error")
            return

        iscc_paths = [
            "ISCC.exe",
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            r"C:\Program Files\Inno Setup 6\ISCC.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
        ]

        iscc = find_executable("ISCC.exe", iscc_paths[1:])
        if iscc:
            log(f"Inno Setup: found at {iscc}", "ok")
            self.info.append(f"ISCC path: {iscc}")
        else:
            self.errors.append("Inno Setup 6 not found")
            log("Inno Setup: NOT FOUND", "error")
            print(f"\n{C.YELLOW}Install Inno Setup 6:{C.RESET}")
            print("  https://jrsoftware.org/isdl.php")
            print("  Or: winget install JRSoftware.InnoSetup")

    def check_project_files(self) -> None:
        """Check required project files exist."""
        root = self.config.project_root

        # Check required files
        for file in REQUIRED_FILES:
            path = root / file
            if path.exists():
                log(f"{file}: found", "ok")
            else:
                self.errors.append(f"Required file not found: {file}")
                log(f"{file}: NOT FOUND", "error")

        # Check optional/configurable files
        optional_files = [
            ("spec_file", self.config.spec_file),
            ("installer_iss", self.config.installer_iss),
        ]

        for name, file in optional_files:
            path = root / file
            if path.exists():
                log(f"{file}: found", "ok")
            else:
                self.warnings.append(f"File not found: {file} (required for build)")
                log(f"{file}: NOT FOUND (required for build)", "warn")

    def check_configuration(self) -> None:
        """Check release configuration."""
        log(f"App name: {self.config.app_name}", "check")
        log(f"Current version: {self.config.current_version}", "check")
        log(f"Releases repo: {self.config.releases_repo or '(not set)'}", "check")
        log(f"Build method: {self.config.build_method}", "check")
        log(f"Installer name: {self.config.installer_name}", "check")
        log(f"Spec file: {self.config.spec_file}", "check")
        log(f"Init file: {self.config.init_file}", "check")

        if not self.config.app_name:
            self.errors.append("app_name not configured in pyproject.toml")
        else:
            log("app_name: OK", "ok")

        if not self.config.releases_repo:
            self.errors.append(
                "releases_repo not configured in pyproject.toml\n"
                "Add to [tool.release] or [tool.spectra]:\n"
                '  releases_repo = "username/appname-releases"'
            )
        else:
            log("releases_repo: OK", "ok")

    def check_git_repo(self) -> None:
        """Check Git repository status."""
        root = self.config.project_root

        # Check if git repo
        success, _ = run("git rev-parse --git-dir", silent=True, ignore_error=True, cwd=root)
        if not success:
            self.errors.append("Not a git repository. Run: git init")
            log("Git repository: NOT FOUND", "error")
            return

        log("Git repository: OK", "ok")

        # Check remote
        success, output = run("git remote -v", silent=True, cwd=root)
        if success and "origin" in output:
            log("Git remote 'origin': configured", "ok")
        else:
            self.warnings.append("Git remote 'origin' not configured")
            log("Git remote 'origin': NOT CONFIGURED", "warn")

    def check_releases_repo(self) -> None:
        """Check if releases repository exists on GitHub."""
        if not self.config.releases_repo:
            log("Releases repo: skipped (not configured)", "warn")
            return

        success, _ = run(
            f"gh repo view {self.config.releases_repo} --json name",
            silent=True,
            ignore_error=True
        )

        if success:
            log(f"Releases repo '{self.config.releases_repo}': exists", "ok")
        else:
            self.warnings.append(
                f"Releases repo '{self.config.releases_repo}' does not exist.\n"
                "It will be created automatically during first release."
            )
            log(f"Releases repo: NOT FOUND (will be created)", "warn")

    def _print_summary(self) -> None:
        """Print check summary."""
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
            print(f"{C.GREEN}{C.BOLD}All checks passed! Ready to release.{C.RESET}\n")
        elif not self.errors:
            print(f"{C.YELLOW}{C.BOLD}Checks passed with warnings.{C.RESET}\n")
        else:
            print(f"{C.RED}{C.BOLD}Fix errors before releasing.{C.RESET}\n")

            # Print helpful commands
            print(f"{C.CYAN}Helpful commands:{C.RESET}")
            if any("pip install" in e for e in self.errors):
                print("  pip install pyinstaller packaging tomli")
            if any("gh auth" in e for e in self.errors):
                print("  gh auth login")
            if any("Inno Setup" in e for e in self.errors):
                print("  winget install JRSoftware.InnoSetup")
            print()


# ============================================================================
# RELEASE MANAGER
# ============================================================================

class ReleaseManager:
    """Manages the release process."""

    def __init__(self, config: Config, version: str, dry_run: bool = False, force: bool = False):
        self.config = config
        self.version = version
        self.tag = f"v{version}"
        self.beta = is_beta(version)
        self.numeric_version = to_numeric_version(version)
        self.dry_run = dry_run
        self.force = force
        self.rollback_actions: List[Callable] = []

        # Original file contents for rollback
        self.orig_pyproject: Optional[str] = None
        self.orig_installer_iss: Optional[str] = None
        self.orig_version_info: Optional[str] = None
        self.orig_init_py: Optional[str] = None
        self.orig_package_json: Optional[str] = None

        # Working directory
        self.cwd = config.project_root

    def execute(self) -> None:
        """Execute the full release process."""
        header(f"Release Script v{SCRIPT_VERSION}")

        log(f"App: {self.config.app_name}", "info")
        log(f"Version: {self.version}{' (BETA)' if self.beta else ''}", "info")
        log(f"Tag: {self.tag}", "info")
        log(f"Mode: {'DRY-RUN (simulation)' if self.dry_run else 'PRODUCTION'}", "info")

        # Change to project root
        os.chdir(self.cwd)

        try:
            self.step1_validate()
            self.step2_update_versions()
            self.step3_build()
            self.step4_generate_yml()
            self.step5_commit_tag()
            self.step6_push()
            self.step7_release()
            self.step8_push_yml_to_releases()
            self.show_summary()
        except Exception as e:
            log(f"\nRelease FAILED: {e}", "error")
            self.rollback()
            sys.exit(1)

    def step1_validate(self) -> None:
        """Step 1: Validations."""
        subheader("Step 1: Validations")

        # Validate version format
        if not validate_version(self.version):
            raise ValueError(f"Invalid version format '{self.version}'. Expected: x.y.z or x.y.z-beta.n")
        log("Version format OK", "ok")

        # Check if tag already exists
        success, stdout = run("git tag -l \"v*\"", silent=True, cwd=self.cwd)
        if self.tag in stdout.split("\n"):
            raise ValueError(f"Tag {self.tag} already exists!")
        log(f"Tag {self.tag} does not exist - OK", "ok")

        # Check git status
        success, stdout = run("git status --porcelain", silent=True, cwd=self.cwd)
        if stdout.strip():
            log("You have uncommitted changes:", "warn")
            print(stdout)
            if not self.force and not self.dry_run:
                ans = prompt("Continue anyway? (y/N): ")
                if ans != "y":
                    raise ValueError("Aborted")
        else:
            log("Git status clean - OK", "ok")

        # Check for gh CLI
        success, _ = run("gh --version", silent=True, ignore_error=True)
        if not success:
            raise ValueError("GitHub CLI (gh) is not installed. Run: --check for details")
        log("GitHub CLI available - OK", "ok")

        # Check gh auth
        success, _ = run("gh auth status", silent=True, ignore_error=True)
        if not success:
            raise ValueError("GitHub CLI not authenticated. Run: gh auth login")
        log("GitHub CLI authenticated - OK", "ok")

        # Check if releases repo exists, create if not
        success, _ = run(
            f"gh repo view {self.config.releases_repo} --json name",
            silent=True,
            ignore_error=True
        )
        if not success:
            log(f"Releases repo {self.config.releases_repo} does not exist", "warn")
            if not self.dry_run:
                print(f"\n{C.YELLOW}Creating releases repo...{C.RESET}")
                success, _ = run(
                    f'gh repo create {self.config.releases_repo} --public '
                    f'--description "{self.config.app_name} releases and auto-update files"',
                    ignore_error=True
                )
                if success:
                    # Initialize with README
                    with tempfile.TemporaryDirectory() as tmpdir:
                        repo_dir = Path(tmpdir) / "repo"
                        run(f'git clone https://github.com/{self.config.releases_repo}.git "{repo_dir}"', silent=True)
                        readme = repo_dir / "README.md"
                        readme.write_text(
                            f"# {self.config.app_name} Releases\n\n"
                            f"This repository contains releases and auto-update files for {self.config.app_name}.\n\n"
                            f"**Do not push source code here.** This repo is for release assets only.\n"
                        )
                        run("git add README.md", silent=True, cwd=repo_dir)
                        run('git commit -m "Initial commit"', silent=True, cwd=repo_dir)
                        run("git push origin main", silent=True, cwd=repo_dir)
                    log("Releases repo created - OK", "ok")
                else:
                    raise ValueError(f"Failed to create releases repo {self.config.releases_repo}")
        else:
            log(f"Releases repo {self.config.releases_repo} exists - OK", "ok")

        # Check for build tools based on method
        if self.config.build_method == "electron":
            # Check npm
            frontend_dir = self.config.resolve_path(self.config.frontend_dir)
            if not (frontend_dir / "package.json").exists():
                raise ValueError(f"package.json not found in {frontend_dir}")
            log(f"Build method: electron-builder", "ok")
        else:
            # Check for Inno Setup
            iscc_paths = [
                "ISCC.exe",
                r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
                r"C:\Program Files\Inno Setup 6\ISCC.exe",
            ]
            if not any(find_executable("ISCC.exe", iscc_paths[1:])):
                log("Inno Setup (ISCC.exe) not found - build may fail", "warn")
            else:
                log("Inno Setup available - OK", "ok")

        # Check for PyInstaller
        success, _ = run("python -m PyInstaller --version", silent=True, ignore_error=True)
        if not success:
            raise ValueError("PyInstaller is not installed. Run: pip install pyinstaller")
        log("PyInstaller available - OK", "ok")

        # Confirmation
        if not self.force and not self.dry_run:
            print(f"\n{C.YELLOW}Planned actions:{C.RESET}")
            print(f"  1. Update version to {self.version}")
            print(f"  2. Build application (PyInstaller + Inno Setup)")
            print(f"  3. Generate latest.yml/beta.yml")
            print(f"  4. Commit + tag {self.tag}")
            print(f"  5. Push to origin")
            print(f"  6. GitHub Release in {self.config.releases_repo}")
            print(f"  7. Push yml files to releases repo\n")

            ans = prompt("Continue? (y/N): ")
            if ans != "y":
                raise ValueError("Aborted")

    def step2_update_versions(self) -> None:
        """Step 2: Update version in all files."""
        subheader("Step 2: Update Versions")

        # Backup original files
        pyproject_path = self.config.resolve_path(self.config.pyproject_toml)
        installer_path = self.config.resolve_path(self.config.installer_iss)
        version_info_path = self.config.resolve_path(self.config.version_info)
        init_py_path = self.config.resolve_path(self.config.init_file)

        if pyproject_path.exists():
            self.orig_pyproject = pyproject_path.read_text(encoding="utf-8")
        if installer_path.exists():
            self.orig_installer_iss = installer_path.read_text(encoding="utf-8")
        if version_info_path.exists():
            self.orig_version_info = version_info_path.read_text(encoding="utf-8")
        if init_py_path.exists():
            self.orig_init_py = init_py_path.read_text(encoding="utf-8")

        # Backup package.json if configured
        package_json_path = None
        if self.config.package_json:
            package_json_path = self.config.resolve_path(self.config.package_json)
            if package_json_path.exists():
                self.orig_package_json = package_json_path.read_text(encoding="utf-8")

        # Add rollback action
        def rollback_files():
            log("Restoring files...", "warn")
            if self.orig_pyproject:
                pyproject_path.write_text(self.orig_pyproject, encoding="utf-8")
            if self.orig_installer_iss:
                installer_path.write_text(self.orig_installer_iss, encoding="utf-8")
            if self.orig_version_info:
                version_info_path.write_text(self.orig_version_info, encoding="utf-8")
            if self.orig_init_py:
                init_py_path.write_text(self.orig_init_py, encoding="utf-8")
            if self.orig_package_json and package_json_path:
                package_json_path.write_text(self.orig_package_json, encoding="utf-8")

        self.rollback_actions.append(rollback_files)

        if not self.dry_run:
            # Update pyproject.toml
            content = pyproject_path.read_text(encoding="utf-8")
            content = re.sub(
                r'^version = ".*"$',
                f'version = "{self.version}"',
                content,
                flags=re.MULTILINE
            )
            pyproject_path.write_text(content, encoding="utf-8")
            log(f"pyproject.toml -> {self.version}", "ok")

            # Update installer.iss
            if installer_path.exists():
                content = installer_path.read_text(encoding="utf-8")
                content = re.sub(
                    r'#define MyAppVersion ".*"',
                    f'#define MyAppVersion "{self.version}"',
                    content
                )
                content = re.sub(
                    r'#define MyAppNumericVersion ".*"',
                    f'#define MyAppNumericVersion "{self.numeric_version}"',
                    content
                )
                installer_path.write_text(content, encoding="utf-8")
                log(f"installer.iss -> {self.version}", "ok")

            # Update file_version_info.txt
            if version_info_path.exists():
                ver_tuple = to_file_version_tuple(self.version)
                content = version_info_path.read_text(encoding="utf-8")
                content = re.sub(
                    r"filevers=\(\d+, \d+, \d+, \d+\)",
                    f"filevers={ver_tuple}",
                    content
                )
                content = re.sub(
                    r"prodvers=\(\d+, \d+, \d+, \d+\)",
                    f"prodvers={ver_tuple}",
                    content
                )
                content = re.sub(
                    r"StringStruct\(u'FileVersion', u'.*'\)",
                    f"StringStruct(u'FileVersion', u'{self.version}')",
                    content
                )
                content = re.sub(
                    r"StringStruct\(u'ProductVersion', u'.*'\)",
                    f"StringStruct(u'ProductVersion', u'{self.version}')",
                    content
                )
                version_info_path.write_text(content, encoding="utf-8")
                log(f"file_version_info.txt -> {self.version}", "ok")

            # Update __init__.py (dynamically resolved)
            if init_py_path.exists():
                content = init_py_path.read_text(encoding="utf-8")
                content = re.sub(
                    r'__version__ = ".*"',
                    f'__version__ = "{self.version}"',
                    content
                )
                init_py_path.write_text(content, encoding="utf-8")
                log(f"{init_py_path.name} -> {self.version}", "ok")
            else:
                log(f"{init_py_path.name} not found (skipped)", "warn")

            # Update package.json (if configured)
            if package_json_path and package_json_path.exists():
                import json
                with open(package_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                data['version'] = self.version
                with open(package_json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.write('\n')
                log(f"package.json -> {self.version}", "ok")

        else:
            log(f"pyproject.toml -> {self.version}", "dry")
            log(f"installer.iss -> {self.version}", "dry")
            log(f"file_version_info.txt -> {self.version}", "dry")
            log(f"{init_py_path.name} -> {self.version}", "dry")
            if package_json_path:
                log(f"package.json -> {self.version}", "dry")

    def step3_build(self) -> None:
        """Step 3: Build application."""
        subheader("Step 3: Build")

        if self.config.build_method == "electron":
            self._build_electron()
        else:
            self._build_innosetup()

    def _build_electron(self) -> None:
        """Build with electron-builder (for Electron + Python hybrid apps)."""
        frontend_dir = self.config.resolve_path(self.config.frontend_dir)

        # Clean previous builds
        log("Cleaning previous build...", "step")
        if not self.dry_run:
            dist_builder = frontend_dir / "dist-builder"
            if dist_builder.exists():
                shutil.rmtree(dist_builder)
            backend_dist = self.config.resolve_path(self.config.dist_dir)
            if backend_dist.exists():
                shutil.rmtree(backend_dist)

        # Step 1: Build Python backend with PyInstaller (using venv Python)
        log("Building Python backend (PyInstaller)...", "step")
        spec_path = self.config.resolve_path(self.config.spec_file)
        dist_path = self.config.resolve_path(self.config.dist_dir)
        build_path = self.config.resolve_path("build")

        # Use Python from backend venv to ensure all dependencies are available
        venv_python = self.config.resolve_path("backend/venv/Scripts/python.exe")
        if not venv_python.exists():
            venv_python = self.config.resolve_path("backend/venv/bin/python")

        if not venv_python.exists() and not self.dry_run:
            raise ValueError(f"Backend venv Python not found at {venv_python}. Run: cd backend && python -m venv venv && pip install -r requirements.txt")

        success, _ = run(
            f'"{venv_python}" -m PyInstaller --distpath "{dist_path}" --workpath "{build_path}" "{spec_path}"',
            dry_run=self.dry_run, cwd=self.cwd
        )
        if not success and not self.dry_run:
            raise ValueError("PyInstaller build failed")

        # Step 2: Build Electron app with electron-builder
        log("Building Electron app (electron-builder)...", "step")
        success, output = run(
            "npm run electron:build",
            dry_run=self.dry_run, cwd=frontend_dir
        )
        if not success and not self.dry_run:
            raise ValueError(f"electron-builder failed: {output}")

        # Step 3: Build installer with Inno Setup (if configured)
        # electron-builder with target: "dir" creates only win-unpacked folder
        # Inno Setup creates the actual installer from win-unpacked
        installer_name = self.config.installer_name.replace("{version}", self.version)
        iss_path = self.config.resolve_path(self.config.installer_iss)

        if iss_path.exists():
            log("Building installer (Inno Setup)...", "step")
            success, output = run(f'iscc "{iss_path}"', dry_run=self.dry_run, cwd=self.cwd)
            if not success and not self.dry_run:
                raise ValueError(f"Inno Setup failed: {output}")

            # Verify installer was created
            release_dir = self.config.resolve_path(self.config.release_dir)
            final_installer = release_dir / installer_name
            if not self.dry_run and not final_installer.exists():
                raise ValueError(f"Installer not found: {final_installer}")
            log(f"Installer: {installer_name}", "ok")
        else:
            # Fallback: look for electron-builder generated installer
            dist_builder = frontend_dir / "dist-builder"
            if not self.dry_run:
                possible_names = [
                    f"IconHub Setup {self.version}.exe",
                    f"IconHub-Setup-{self.version}.exe",
                    installer_name,
                ]

                found_installer = None
                for name in possible_names:
                    candidate = dist_builder / name
                    if candidate.exists():
                        found_installer = candidate
                        break

                if not found_installer:
                    files = list(dist_builder.glob("*.exe")) if dist_builder.exists() else []
                    raise ValueError(f"Installer not found in {dist_builder}. Found: {[f.name for f in files]}")

                release_dir = self.config.resolve_path(self.config.release_dir)
                release_dir.mkdir(parents=True, exist_ok=True)
                final_installer = release_dir / installer_name
                shutil.copy2(found_installer, final_installer)
                log(f"Installer: {installer_name}", "ok")
            else:
                log(f"Would create installer: {installer_name}", "dry")

    def _build_innosetup(self) -> None:
        """Build with PyInstaller + Inno Setup (standalone Python apps)."""
        # Clean previous build
        log("Cleaning previous build...", "step")
        if not self.dry_run:
            dist_path = self.config.resolve_path(self.config.dist_dir)
            if dist_path.exists():
                shutil.rmtree(dist_path)
            build_path = self.config.resolve_path("build")
            if build_path.exists():
                shutil.rmtree(build_path)

        # Build with PyInstaller
        log("Building with PyInstaller...", "step")
        spec_path = self.config.resolve_path(self.config.spec_file)
        dist_path = self.config.resolve_path(self.config.dist_dir)
        build_path = self.config.resolve_path("build")
        success, _ = run(
            f'python -m PyInstaller --distpath "{dist_path}" --workpath "{build_path}" "{spec_path}"',
            dry_run=self.dry_run, cwd=self.cwd
        )
        if not success and not self.dry_run:
            raise ValueError("PyInstaller build failed")

        # Build installer with Inno Setup
        log("Building installer (Inno Setup)...", "step")
        iss_path = self.config.resolve_path(self.config.installer_iss)

        # Try ISCC.exe in PATH first, then default locations
        iscc_paths = [
            "ISCC.exe",
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            r"C:\Program Files\Inno Setup 6\ISCC.exe",
        ]

        success = False
        for iscc in iscc_paths:
            if not Path(iscc).exists() and iscc != "ISCC.exe":
                continue
            success, _ = run(f'"{iscc}" "{iss_path}"', dry_run=self.dry_run, ignore_error=True, cwd=self.cwd)
            if success or self.dry_run:
                break

        if not success and not self.dry_run:
            raise ValueError("Inno Setup build failed. Make sure Inno Setup 6 is installed.")

        # Verify installer was created
        installer_name = self.config.installer_name.replace("{version}", self.version)
        installer_path = self.config.resolve_path(self.config.release_dir) / installer_name

        if not self.dry_run and not installer_path.exists():
            raise ValueError(f"Installer not found: {installer_path}")

        log(f"Installer: {installer_name}", "ok")

    def step4_generate_yml(self) -> None:
        """Step 4: Generate YML files for auto-update."""
        subheader("Step 4: Generate YML")

        installer_name = self.config.installer_name.replace("{version}", self.version)
        installer_path = self.config.resolve_path(self.config.release_dir) / installer_name

        if self.dry_run:
            if self.beta:
                log(f"Would generate ONLY beta.yml for {installer_name}", "dry")
                log("latest.yml would remain unchanged (beta release)", "dry")
            else:
                log(f"Would generate latest.yml and beta.yml for {installer_name}", "dry")
            return

        # Calculate hash and size
        hash_value = sha512_file(installer_path)
        size = file_size(installer_path)

        log(f"SHA512: {hash_value[:40]}...", "info")
        log(f"Size: {size / 1024 / 1024:.2f} MB", "info")

        # Generate YML content
        yml_content = f"""version: {self.version}
files:
  - url: {installer_name}
    sha512: {hash_value}
    size: {size}
path: {installer_name}
sha512: {hash_value}
releaseDate: '{datetime.now(timezone.utc).isoformat()}'
"""

        # Create release directory if needed
        release_dir = self.config.resolve_path(self.config.release_dir)
        release_dir.mkdir(parents=True, exist_ok=True)

        # Write YML files
        latest_yml = self.config.resolve_path(self.config.latest_yml)
        beta_yml = self.config.resolve_path(self.config.beta_yml)

        if self.beta:
            beta_yml.write_text(yml_content, encoding="utf-8")
            log("Created beta.yml (latest.yml unchanged)", "ok")
        else:
            latest_yml.write_text(yml_content, encoding="utf-8")
            log("Created latest.yml", "ok")
            beta_yml.write_text(yml_content, encoding="utf-8")
            log("Created beta.yml", "ok")

    def step5_commit_tag(self) -> None:
        """Step 5: Commit and tag."""
        subheader("Step 5: Commit and Tag")

        # Determine which YML files to commit
        if self.beta:
            files = [self.config.pyproject_toml, self.config.installer_iss,
                     self.config.version_info, self.config.beta_yml]
        else:
            files = [self.config.pyproject_toml, self.config.installer_iss,
                     self.config.version_info, self.config.latest_yml, self.config.beta_yml]

        # Add init file if it exists and was modified
        if self.config.resolve_path(self.config.init_file).exists():
            files.append(self.config.init_file)

        # Add package.json if configured
        if self.config.package_json and self.config.resolve_path(self.config.package_json).exists():
            files.append(self.config.package_json)

        # Add files
        for file in files:
            file_path = self.config.resolve_path(file)
            if file_path.exists():
                run(f'git add "{file}"', silent=True, dry_run=self.dry_run, cwd=self.cwd)

        # Commit
        commit_msg = f"release: v{self.version}"
        success, _ = run(f'git commit -m "{commit_msg}"', dry_run=self.dry_run, cwd=self.cwd)

        if not self.dry_run and success:
            def rollback_commit():
                log("Rolling back commit...", "warn")
                run("git reset --soft HEAD~1", silent=True, cwd=self.cwd)
            self.rollback_actions.append(rollback_commit)

        # Tag
        tag_msg = f"Release {self.version}{' (BETA)' if self.beta else ''}"
        success, _ = run(f'git tag -a "{self.tag}" -m "{tag_msg}"', dry_run=self.dry_run, cwd=self.cwd)

        if not self.dry_run and success:
            def rollback_tag():
                log(f"Removing tag {self.tag}...", "warn")
                run(f'git tag -d "{self.tag}"', silent=True, cwd=self.cwd)
            self.rollback_actions.append(rollback_tag)

        log("Commit and tag created", "ok")

    def step6_push(self) -> None:
        """Step 6: Push to origin."""
        subheader("Step 6: Push")

        success, _ = run("git push origin", dry_run=self.dry_run, cwd=self.cwd)
        if not success and not self.dry_run:
            raise ValueError("Push branch failed")

        success, _ = run(f'git push origin "{self.tag}"', dry_run=self.dry_run, cwd=self.cwd)
        if not success and not self.dry_run:
            raise ValueError("Push tag failed")

        log("Push completed", "ok")

    def step7_release(self) -> None:
        """Step 7: Create GitHub release."""
        subheader("Step 7: GitHub Release")

        installer_name = self.config.installer_name.replace("{version}", self.version)
        installer_path = self.config.resolve_path(self.config.release_dir) / installer_name
        title = f"{self.config.app_name} v{self.version}{' [BETA]' if self.beta else ''}"

        body = f"""## {self.config.app_name} v{self.version}{' [BETA]' if self.beta else ''}

{"> **Note:** This is a beta version. It may contain bugs." + chr(10) if self.beta else ""}
### Installation
1. Download `{installer_name}`
2. Run the installer
3. On first run, Windows SmartScreen may appear - click "More info" > "Run anyway"

### Requirements
- Windows 10/11 (64-bit)
"""

        if self.dry_run:
            log(f"Would create release: {title}", "dry")
            return

        # Write body to temp file
        release_dir = self.config.resolve_path(self.config.release_dir)
        temp_body = release_dir / "release-body-temp.md"
        temp_body.write_text(body, encoding="utf-8")

        # Determine which files to upload
        latest_yml = self.config.resolve_path(self.config.latest_yml)
        beta_yml = self.config.resolve_path(self.config.beta_yml)
        yml_files = [str(beta_yml)] if self.beta else [str(latest_yml), str(beta_yml)]
        files = [str(installer_path)] + [f for f in yml_files if Path(f).exists()]
        files_str = " ".join(f'"{f}"' for f in files)

        cmd = (
            f'gh release create "{self.tag}" '
            f'--repo {self.config.releases_repo} '
            f'--title "{title}" '
            f'--notes-file "{temp_body}" '
            f'{"--prerelease " if self.beta else ""}'
            f'{files_str}'
        )

        log(f"Creating release in {self.config.releases_repo}...", "step")
        success, _ = run(cmd, cwd=self.cwd)

        # Clean up temp file
        if temp_body.exists():
            temp_body.unlink()

        if not success:
            raise ValueError("GitHub Release creation failed")

        log("GitHub Release created!", "ok")

    def step8_push_yml_to_releases(self) -> None:
        """Step 8: Push yml files to releases repo main branch."""
        subheader("Step 8: Push YML to releases repo")

        if self.dry_run:
            log("Would clone releases repo and push yml files", "dry")
            return

        original_cwd = os.getcwd()
        temp_dir = Path(tempfile.mkdtemp(prefix="release_yml_"))
        repo_dir = temp_dir / "releases"

        try:
            # Clone releases repo
            log("Cloning releases repo...", "step")
            success, _ = run(
                f'git clone --depth 1 https://github.com/{self.config.releases_repo}.git "{repo_dir}"',
                silent=True
            )
            if not success:
                raise ValueError("Failed to clone releases repo")

            # Copy yml files
            yml_files = []
            if not self.beta:
                yml_files.append(self.config.resolve_path(self.config.latest_yml))
            yml_files.append(self.config.resolve_path(self.config.beta_yml))

            for yml_file in yml_files:
                if yml_file.exists():
                    dst = repo_dir / yml_file.name
                    shutil.copy2(yml_file, dst)
                    log(f"Copied {yml_file.name}", "ok")

            # Commit and push
            os.chdir(repo_dir)

            run("git add *.yml", silent=True)

            commit_msg = f"update: yml files for v{self.version}"
            success, _ = run(f'git commit -m "{commit_msg}"', silent=True)

            if success:
                log("Pushing to releases repo...", "step")
                success, _ = run("git push origin main", silent=True)
                if not success:
                    log("Failed to push yml to releases repo (non-fatal)", "warn")
                else:
                    log("YML files pushed to releases repo", "ok")
            else:
                log("No yml changes to commit", "info")

        except Exception as e:
            log(f"Failed to push yml to releases repo: {e} (non-fatal)", "warn")
        finally:
            # Return to original directory
            os.chdir(original_cwd)

            # Clean up temp directory (ignore errors on Windows)
            try:
                def remove_readonly(func, path, _):
                    """Clear readonly bit and retry remove."""
                    os.chmod(path, 0o777)
                    func(path)

                shutil.rmtree(temp_dir, onerror=remove_readonly)
            except Exception:
                pass  # Ignore cleanup errors

    def show_summary(self) -> None:
        """Show release summary."""
        header("SUMMARY")

        if self.dry_run:
            log("This was a simulation (--dry-run). No changes were made.", "warn")
            return

        print(f"{C.GREEN}Release {self.version} completed successfully!{C.RESET}\n")

        print("Actions performed:")
        print(f"  {C.GREEN}+{C.RESET} Updated version in files")
        print(f"  {C.GREEN}+{C.RESET} Built application and installer")
        print(f"  {C.GREEN}+{C.RESET} Generated latest.yml/beta.yml")
        print(f"  {C.GREEN}+{C.RESET} Commit and tag {self.tag}")
        print(f"  {C.GREEN}+{C.RESET} Push to origin")
        print(f"  {C.GREEN}+{C.RESET} GitHub Release")
        print(f"  {C.GREEN}+{C.RESET} YML files pushed to releases repo")

        print("\nLinks:")
        print(f"  {C.CYAN}Release:{C.RESET} https://github.com/{self.config.releases_repo}/releases/tag/{self.tag}")

        installer_name = self.config.installer_name.replace("{version}", self.version)
        print(f"\nInstaller: {C.BOLD}{self.config.release_dir}/{installer_name}{C.RESET}")

    def rollback(self) -> None:
        """Execute rollback actions."""
        if self.dry_run:
            return

        log("\nExecuting rollback...", "warn")

        for action in reversed(self.rollback_actions):
            try:
                action()
            except Exception as e:
                log(f"Rollback error: {e}", "error")

        log("Rollback completed", "warn")


# ============================================================================
# MAIN
# ============================================================================

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=f"Universal Release Script v{SCRIPT_VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{C.CYAN}Examples:{C.RESET}
  python scripts/release.py --check           # Check all requirements
  python scripts/release.py 1.0.1             # Release version 1.0.1
  python scripts/release.py 1.0.1-beta.1      # Release beta version
  python scripts/release.py 1.0.1 --dry-run   # Simulate release
  python scripts/release.py 1.0.1 --force     # Skip confirmations

{C.CYAN}Configuration (pyproject.toml):{C.RESET}
  [tool.release]
  app_name = "MyApp"
  releases_repo = "username/myapp-releases"
  installer_name = "MyApp_Setup_{{version}}.exe"
  spec_file = "myapp.spec"
  init_file = "src/myapp/__init__.py"

{C.CYAN}What it does:{C.RESET}
  1. Updates version in pyproject.toml, installer.iss, file_version_info.txt
  2. Builds: PyInstaller + Inno Setup
  3. Generates latest.yml/beta.yml with SHA512 hash
  4. Commit + tag + push to origin
  5. Creates GitHub Release in releases repo
  6. Pushes yml files to releases repo (for auto-updater)
        """
    )

    parser.add_argument(
        "version",
        nargs="?",
        help="Version to release (e.g., 1.0.1 or 1.0.1-beta.1)"
    )
    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="Check all requirements without releasing"
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Simulation without changes"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Skip confirmations"
    )
    parser.add_argument(
        "--preflight", "-p",
        action="store_true",
        help="Run preflight checks before release"
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    try:
        config = Config.load()
    except Exception as e:
        log(f"Configuration error: {e}", "error")
        sys.exit(1)

    # Check mode
    if args.check:
        checker = EnvironmentChecker(config)
        success = checker.check_all()
        sys.exit(0 if success else 1)

    # Preflight mode
    if args.preflight:
        log("Running preflight checks...", "info")
        preflight_path = Path(__file__).parent / "preflight.py"
        if preflight_path.exists():
            result = subprocess.run([sys.executable, str(preflight_path)], cwd=config.project_root)
            if result.returncode != 0:
                log("Preflight checks failed. Fix issues before release.", "error")
                sys.exit(1)
            log("Preflight checks passed!", "ok")
        else:
            log("preflight.py not found, skipping preflight checks", "warn")

    # Release mode
    if not args.version:
        log("Version required. Usage: python scripts/release.py 1.0.1", "error")
        log("Or use --check to verify requirements.", "info")
        sys.exit(1)

    # Remove 'v' prefix if provided
    version = args.version.lstrip("v")

    manager = ReleaseManager(
        config=config,
        version=version,
        dry_run=args.dry_run,
        force=args.force,
    )

    manager.execute()


if __name__ == "__main__":
    main()