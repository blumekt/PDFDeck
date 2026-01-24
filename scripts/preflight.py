#!/usr/bin/env python3
"""
Universal Preflight Checker v1.0

Pre-release validation script that checks:
- Version consistency across all configured files
- Git state (clean working tree, remote sync)
- Required files existence
- Required tools availability

Copy this entire 'scripts' folder to any new project - it will auto-configure itself.

Usage:
    python scripts/preflight.py              # Full validation
    python scripts/preflight.py --fix        # Auto-fix version inconsistencies
    python scripts/preflight.py --quiet      # Only errors (for CI/CD)
    python scripts/preflight.py --version    # Show detected version

Configuration (pyproject.toml):
    [tool.preflight]
    version_files = [
        "pyproject.toml:version",
        "frontend/package.json:version",
        "backend/app/__init__.py:__version__",
    ]
    required_files = [
        "pyproject.toml",
        "README.md",
    ]
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============================================================================
# CONSTANTS
# ============================================================================

SCRIPT_VERSION = "1.0"
MIN_PYTHON_VERSION = (3, 9)

# Default version files if not configured
DEFAULT_VERSION_FILES = [
    "pyproject.toml:version",
]

# Default required files if not configured
DEFAULT_REQUIRED_FILES = [
    "pyproject.toml",
]


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

class Logger:
    """Logger with quiet mode support."""

    def __init__(self, quiet: bool = False):
        self.quiet = quiet
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def log(self, msg: str, level: str = "info") -> None:
        """Print a colored log message."""
        if self.quiet and level not in ("error", "warn"):
            return

        prefixes = {
            "info": f"{C.CYAN}[INFO]{C.RESET}",
            "ok": f"{C.GREEN}[OK]{C.RESET}",
            "warn": f"{C.YELLOW}[WARN]{C.RESET}",
            "error": f"{C.RED}[ERROR]{C.RESET}",
            "check": f"{C.WHITE}[CHECK]{C.RESET}",
            "fix": f"{C.MAGENTA}[FIX]{C.RESET}",
        }
        prefix = prefixes.get(level, prefixes["info"])
        print(f"{prefix} {msg}")

        if level == "error":
            self.errors.append(msg)
        elif level == "warn":
            self.warnings.append(msg)

    def header(self, title: str) -> None:
        """Print a section header."""
        if self.quiet:
            return
        line = "=" * 60
        print(f"\n{C.BOLD}{C.CYAN}{line}{C.RESET}")
        print(f"{C.BOLD}  {title}{C.RESET}")
        print(f"{C.BOLD}{C.CYAN}{line}{C.RESET}\n")

    def subheader(self, title: str) -> None:
        """Print a subsection header."""
        if self.quiet:
            return
        print(f"\n{C.YELLOW}--- {title} ---{C.RESET}\n")


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class Config:
    """Preflight configuration loaded from pyproject.toml."""
    version_files: List[str] = field(default_factory=lambda: DEFAULT_VERSION_FILES.copy())
    required_files: List[str] = field(default_factory=lambda: DEFAULT_REQUIRED_FILES.copy())
    project_root: Path = field(default_factory=Path)

    @classmethod
    def load(cls, project_root: Optional[Path] = None) -> "Config":
        """Load configuration from pyproject.toml."""
        if project_root is None:
            project_root = Path.cwd()
            for parent in [project_root] + list(project_root.parents):
                if (parent / "pyproject.toml").exists():
                    project_root = parent
                    break

        pyproject_path = project_root / "pyproject.toml"
        if not pyproject_path.exists():
            return cls(project_root=project_root)

        # Load pyproject.toml
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                return cls(project_root=project_root)

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        # Get preflight config
        preflight = data.get("tool", {}).get("preflight", {})

        return cls(
            version_files=preflight.get("version_files", DEFAULT_VERSION_FILES.copy()),
            required_files=preflight.get("required_files", DEFAULT_REQUIRED_FILES.copy()),
            project_root=project_root,
        )

    def resolve_path(self, path: str) -> Path:
        """Resolve a path relative to project root."""
        return self.project_root / path


# ============================================================================
# VERSION EXTRACTORS
# ============================================================================

class VersionExtractor:
    """Extracts and updates versions in various file formats."""

    @staticmethod
    def extract(filepath: Path, key: str) -> Optional[str]:
        """Extract version from a file."""
        if not filepath.exists():
            return None

        content = filepath.read_text(encoding="utf-8")
        suffix = filepath.suffix.lower()

        if suffix == ".toml":
            # TOML: version = "x.y.z"
            match = re.search(rf'^{key}\s*=\s*"([^"]+)"', content, re.MULTILINE)
            return match.group(1) if match else None

        elif suffix == ".json":
            # JSON: "version": "x.y.z"
            try:
                data = json.loads(content)
                return data.get(key)
            except json.JSONDecodeError:
                return None

        elif suffix == ".py":
            # Python: __version__ = "x.y.z"
            match = re.search(rf'^{key}\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
            return match.group(1) if match else None

        elif suffix == ".iss":
            # Inno Setup: #define MyAppVersion "x.y.z"
            match = re.search(rf'#define\s+{key}\s+"([^"]+)"', content)
            return match.group(1) if match else None

        elif suffix == ".txt" and "version_info" in filepath.name.lower():
            # file_version_info.txt: StringStruct(u'FileVersion', u'x.y.z')
            match = re.search(rf"StringStruct\(u'{key}',\s*u'([^']+)'\)", content)
            return match.group(1) if match else None

        return None

    @staticmethod
    def update(filepath: Path, key: str, new_version: str) -> bool:
        """Update version in a file."""
        if not filepath.exists():
            return False

        content = filepath.read_text(encoding="utf-8")
        suffix = filepath.suffix.lower()
        new_content = content

        if suffix == ".toml":
            new_content = re.sub(
                rf'^({key}\s*=\s*")[^"]+"',
                rf'\g<1>{new_version}"',
                content,
                flags=re.MULTILINE
            )

        elif suffix == ".json":
            try:
                data = json.loads(content)
                if key in data:
                    data[key] = new_version
                    new_content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
            except json.JSONDecodeError:
                return False

        elif suffix == ".py":
            new_content = re.sub(
                rf'^({key}\s*=\s*["\'])[^"\']+(["\'])',
                rf'\g<1>{new_version}\g<2>',
                content,
                flags=re.MULTILINE
            )

        elif suffix == ".iss":
            new_content = re.sub(
                rf'(#define\s+{key}\s+")[^"]+(")',
                rf'\g<1>{new_version}\g<2>',
                content
            )
            # Also update numeric version if present
            numeric = re.sub(r"-beta\.\d+$", "", new_version) + ".0"
            new_content = re.sub(
                r'(#define\s+MyAppNumericVersion\s+")[^"]+(")',
                rf'\g<1>{numeric}\g<2>',
                new_content
            )

        elif suffix == ".txt" and "version_info" in filepath.name.lower():
            new_content = re.sub(
                rf"(StringStruct\(u'{key}',\s*u')[^']+(')",
                rf"\g<1>{new_version}\g<2>",
                content
            )
            # Also update filevers and prodvers tuples
            parts = re.sub(r"-beta\.\d+$", "", new_version).split(".")
            ver_tuple = f"({parts[0]}, {parts[1]}, {parts[2]}, 0)"
            new_content = re.sub(
                r"filevers=\([^)]+\)",
                f"filevers={ver_tuple}",
                new_content
            )
            new_content = re.sub(
                r"prodvers=\([^)]+\)",
                f"prodvers={ver_tuple}",
                new_content
            )

        if new_content != content:
            filepath.write_text(new_content, encoding="utf-8")
            return True

        return False


# ============================================================================
# PREFLIGHT CHECKER
# ============================================================================

class PreflightChecker:
    """Main preflight checker class."""

    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.log = logger
        self.versions: Dict[str, str] = {}

    def run_all(self) -> bool:
        """Run all preflight checks."""
        self.log.header(f"Preflight Checker v{SCRIPT_VERSION}")

        checks = [
            ("Python Version", self.check_python),
            ("Version Consistency", self.check_versions),
            ("Required Files", self.check_required_files),
            ("Git State", self.check_git_state),
            ("Required Tools", self.check_tools),
        ]

        for name, check_fn in checks:
            self.log.subheader(name)
            try:
                check_fn()
            except Exception as e:
                self.log.log(f"{name}: {e}", "error")

        self._print_summary()
        return len(self.log.errors) == 0

    def check_python(self) -> None:
        """Check Python version."""
        current = sys.version_info[:2]
        required = MIN_PYTHON_VERSION

        self.log.log(f"Python {current[0]}.{current[1]} (required: {required[0]}.{required[1]}+)", "check")

        if current >= required:
            self.log.log("Python version OK", "ok")
        else:
            self.log.log(f"Python {required[0]}.{required[1]}+ required", "error")

    def check_versions(self) -> None:
        """Check version consistency across all configured files."""
        for entry in self.config.version_files:
            parts = entry.split(":")
            if len(parts) != 2:
                self.log.log(f"Invalid version_files entry: {entry}", "warn")
                continue

            filepath = self.config.resolve_path(parts[0])
            key = parts[1]

            if not filepath.exists():
                self.log.log(f"{parts[0]}: NOT FOUND", "warn")
                continue

            version = VersionExtractor.extract(filepath, key)
            if version:
                self.versions[parts[0]] = version
                self.log.log(f"{parts[0]}: {version}", "check")
            else:
                self.log.log(f"{parts[0]}: Could not extract '{key}'", "warn")

        # Check consistency
        unique_versions = set(self.versions.values())
        if len(unique_versions) == 0:
            self.log.log("No versions found to compare", "warn")
        elif len(unique_versions) == 1:
            version = list(unique_versions)[0]
            self.log.log(f"All versions consistent: {version}", "ok")
        else:
            self.log.log(f"Version MISMATCH detected!", "error")
            for filepath, version in self.versions.items():
                self.log.log(f"  {filepath}: {version}", "error")
            self.log.log("Run with --fix to synchronize versions", "info")

    def check_required_files(self) -> None:
        """Check that all required files exist."""
        for filepath in self.config.required_files:
            path = self.config.resolve_path(filepath)
            if path.exists():
                self.log.log(f"{filepath}: found", "ok")
            else:
                self.log.log(f"{filepath}: NOT FOUND", "error")

    def check_git_state(self) -> None:
        """Check Git repository state."""
        root = self.config.project_root

        # Check if git repo
        result = self._run_cmd("git rev-parse --git-dir", cwd=root)
        if not result[0]:
            self.log.log("Not a git repository", "warn")
            return

        self.log.log("Git repository: OK", "ok")

        # Check for uncommitted changes
        result = self._run_cmd("git status --porcelain", cwd=root)
        if result[0] and result[1].strip():
            lines = result[1].strip().split("\n")
            self.log.log(f"Uncommitted changes: {len(lines)} file(s)", "warn")
            for line in lines[:5]:  # Show first 5
                self.log.log(f"  {line}", "check")
            if len(lines) > 5:
                self.log.log(f"  ... and {len(lines) - 5} more", "check")
        else:
            self.log.log("Working tree: clean", "ok")

        # Check remote sync
        result = self._run_cmd("git fetch --dry-run 2>&1", cwd=root)
        result = self._run_cmd("git status -sb", cwd=root)
        if result[0]:
            status = result[1].strip().split("\n")[0]
            if "ahead" in status:
                match = re.search(r"ahead (\d+)", status)
                count = match.group(1) if match else "?"
                self.log.log(f"Local is ahead of remote by {count} commit(s)", "warn")
            elif "behind" in status:
                match = re.search(r"behind (\d+)", status)
                count = match.group(1) if match else "?"
                self.log.log(f"Local is behind remote by {count} commit(s)", "warn")
            else:
                self.log.log("Remote sync: OK", "ok")

    def check_tools(self) -> None:
        """Check required tools are available."""
        tools = [
            ("git", "git --version"),
            ("gh (GitHub CLI)", "gh --version"),
            ("PyInstaller", "python -m PyInstaller --version"),
        ]

        for name, cmd in tools:
            result = self._run_cmd(cmd)
            if result[0]:
                version = result[1].strip().split("\n")[0]
                self.log.log(f"{name}: {version}", "ok")
            else:
                self.log.log(f"{name}: NOT FOUND", "warn")

        # Check Inno Setup (Windows only)
        if platform.system() == "Windows":
            iscc_paths = [
                r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
                r"C:\Program Files\Inno Setup 6\ISCC.exe",
            ]
            found = any(Path(p).exists() for p in iscc_paths)
            if found:
                self.log.log("Inno Setup 6: found", "ok")
            else:
                self.log.log("Inno Setup 6: NOT FOUND", "warn")

        # Check gh auth
        result = self._run_cmd("gh auth status 2>&1")
        if result[0] and "Logged in" in result[1]:
            self.log.log("gh authentication: OK", "ok")
        else:
            self.log.log("gh authentication: NOT LOGGED IN (run: gh auth login)", "warn")

    def fix_versions(self, target_version: Optional[str] = None) -> bool:
        """Fix version inconsistencies by synchronizing all files."""
        self.log.header("Fix Version Inconsistencies")

        # First, collect current versions
        for entry in self.config.version_files:
            parts = entry.split(":")
            if len(parts) != 2:
                continue

            filepath = self.config.resolve_path(parts[0])
            key = parts[1]

            if filepath.exists():
                version = VersionExtractor.extract(filepath, key)
                if version:
                    self.versions[parts[0]] = version

        if not self.versions:
            self.log.log("No version files found", "error")
            return False

        # Determine target version
        if target_version is None:
            # Use pyproject.toml version as source of truth
            target_version = self.versions.get("pyproject.toml")
            if not target_version:
                # Use the most common version
                from collections import Counter
                counter = Counter(self.versions.values())
                target_version = counter.most_common(1)[0][0]

        self.log.log(f"Target version: {target_version}", "info")

        # Update all files
        updated = 0
        for entry in self.config.version_files:
            parts = entry.split(":")
            if len(parts) != 2:
                continue

            filepath = self.config.resolve_path(parts[0])
            key = parts[1]

            if not filepath.exists():
                self.log.log(f"{parts[0]}: SKIPPED (not found)", "warn")
                continue

            current = self.versions.get(parts[0])
            if current == target_version:
                self.log.log(f"{parts[0]}: already {target_version}", "ok")
                continue

            if VersionExtractor.update(filepath, key, target_version):
                self.log.log(f"{parts[0]}: {current} -> {target_version}", "fix")
                updated += 1
            else:
                self.log.log(f"{parts[0]}: FAILED to update", "error")

        self.log.log(f"\nUpdated {updated} file(s)", "info")
        return True

    def get_version(self) -> Optional[str]:
        """Get the current version from pyproject.toml."""
        for entry in self.config.version_files:
            parts = entry.split(":")
            if len(parts) == 2 and parts[0] == "pyproject.toml":
                filepath = self.config.resolve_path(parts[0])
                return VersionExtractor.extract(filepath, parts[1])
        return None

    def _run_cmd(self, cmd: str, cwd: Optional[Path] = None) -> Tuple[bool, str]:
        """Run a command and return (success, output)."""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=cwd,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)

    def _print_summary(self) -> None:
        """Print check summary."""
        self.log.header("Summary")

        if self.log.errors:
            print(f"{C.RED}{C.BOLD}ERRORS ({len(self.log.errors)}):{C.RESET}")
            for error in self.log.errors:
                print(f"  {C.RED}✗{C.RESET} {error}")
            print()

        if self.log.warnings:
            print(f"{C.YELLOW}{C.BOLD}WARNINGS ({len(self.log.warnings)}):{C.RESET}")
            for warning in self.log.warnings:
                print(f"  {C.YELLOW}!{C.RESET} {warning}")
            print()

        if not self.log.errors and not self.log.warnings:
            print(f"{C.GREEN}{C.BOLD}All checks passed! Ready for release.{C.RESET}\n")
        elif not self.log.errors:
            print(f"{C.YELLOW}{C.BOLD}Checks passed with warnings.{C.RESET}\n")
        else:
            print(f"{C.RED}{C.BOLD}Fix errors before releasing.{C.RESET}\n")


# ============================================================================
# MAIN
# ============================================================================

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=f"Universal Preflight Checker v{SCRIPT_VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{C.CYAN}Examples:{C.RESET}
  python scripts/preflight.py              # Full validation
  python scripts/preflight.py --fix        # Auto-fix version inconsistencies
  python scripts/preflight.py --fix 1.0.0  # Set specific version
  python scripts/preflight.py --quiet      # Only errors (for CI/CD)
  python scripts/preflight.py --version    # Show detected version

{C.CYAN}Configuration (pyproject.toml):{C.RESET}
  [tool.preflight]
  version_files = [
      "pyproject.toml:version",
      "frontend/package.json:version",
      "backend/app/__init__.py:__version__",
  ]
  required_files = [
      "pyproject.toml",
      "README.md",
  ]
        """
    )

    parser.add_argument(
        "--fix",
        nargs="?",
        const="",
        metavar="VERSION",
        help="Fix version inconsistencies (optionally specify target version)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only show errors (for CI/CD)"
    )
    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Show detected version and exit"
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    try:
        config = Config.load()
    except Exception as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    logger = Logger(quiet=args.quiet)
    checker = PreflightChecker(config, logger)

    # Version mode
    if args.version:
        version = checker.get_version()
        if version:
            print(version)
        else:
            print("Unknown")
        sys.exit(0)

    # Fix mode
    if args.fix is not None:
        target = args.fix if args.fix else None
        success = checker.fix_versions(target)
        sys.exit(0 if success else 1)

    # Normal check mode
    success = checker.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
