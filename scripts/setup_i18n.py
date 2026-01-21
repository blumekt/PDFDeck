#!/usr/bin/env python3
"""
Universal i18n Setup Script v1.1

Portable setup script for adding internationalization to desktop applications.
Copy this script to any new project - it will auto-configure itself.

Features:
- Auto-detection of project configuration from pyproject.toml
- Support for PyQt6, CustomTkinter, and CLI (framework-aware extraction)
- String extraction from source code (hardcoded strings)
- Translation validation (missing keys, unused keys, param mismatches)
- Coverage statistics (which files use i18n, which don't)
- Generate i18n module files (--init flag)
- Dry-run mode, rollback on errors
- Colored terminal output

Usage:
    python scripts/setup_i18n.py --check                # Check environment
    python scripts/setup_i18n.py --init                 # Generate i18n files
    python scripts/setup_i18n.py --extract              # Extract hardcoded strings
    python scripts/setup_i18n.py --validate             # Validate translations
    python scripts/setup_i18n.py --stats                # Coverage statistics
    python scripts/setup_i18n.py --init --dry-run       # Simulate generation
    python scripts/setup_i18n.py --extract --file path  # Extract from single file

Configuration:
    Add to pyproject.toml:

    [tool.i18n]
    app_name = "MyApp"
    ui_framework = "pyqt6"  # or "customtkinter", "cli"
    default_language = "en"
    supported_languages = ["en", "pl", "de", "fr"]
    translations_dir = "resources/translations"
    i18n_module = "src/{app}/utils/i18n.py"
    source_dirs = ["src/{app}/ui"]
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ============================================================================
# CONSTANTS
# ============================================================================

SCRIPT_VERSION = "1.1"
MIN_PYTHON_VERSION = (3, 10)
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
        "i18n": f"{C.YELLOW}[i18n]{C.RESET}",
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
class I18nConfig:
    """i18n configuration loaded from pyproject.toml."""
    # Required
    app_name: str = "App"
    default_language: str = "en"
    supported_languages: List[str] = field(default_factory=lambda: ["en"])

    # Optional with defaults
    ui_framework: str = "pyqt6"
    translations_dir: str = "resources/translations"
    i18n_module: str = "src/{app}/utils/i18n.py"
    source_dirs: List[str] = field(default_factory=lambda: ["src/{app}/ui"])
    fallback_language: str = "en"
    key_separator: str = "."

    # Computed
    project_root: Path = field(default_factory=Path)
    app_name_lower: str = ""

    @classmethod
    def load(cls, project_root: Optional[Path] = None) -> "I18nConfig":
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
                import tomli as tomllib  # type: ignore
            except ImportError:
                raise ImportError(
                    "tomli package required for Python < 3.11\n"
                    "Install with: pip install tomli"
                )

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        # Get project info
        project = data.get("project", {})

        # Get i18n config
        tool_i18n = data.get("tool", {}).get("i18n", {})

        # Extract app name
        app_name = (
            tool_i18n.get("app_name") or
            project.get("name", "").capitalize() or
            "App"
        )
        app_name_lower = app_name.lower()

        # Create config
        config = cls(
            app_name=app_name,
            project_root=project_root,
            app_name_lower=app_name_lower,
        )

        # Override with custom values
        for key in ["default_language", "supported_languages", "translations_dir",
                    "i18n_module", "source_dirs", "fallback_language", "key_separator", "ui_framework"]:
            if key in tool_i18n:
                setattr(config, key, tool_i18n[key])

        # Substitute {app} placeholder in paths
        config.i18n_module = config.i18n_module.replace("{app}", app_name_lower)
        config.source_dirs = [d.replace("{app}", app_name_lower) for d in config.source_dirs]

        return config

    def resolve_path(self, path: str) -> Path:
        """Resolve a path relative to project root."""
        return self.project_root / path


# ============================================================================
# ENVIRONMENT CHECKER
# ============================================================================

class EnvironmentChecker:
    """Check environment before initializing i18n."""

    def __init__(self, config: I18nConfig):
        self.config = config
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def check_all(self) -> bool:
        """Run all checks."""
        header(f"i18n Environment Check v{SCRIPT_VERSION}")

        subheader("Configuration")
        log(f"App: {self.config.app_name}", "check")
        log(f"Framework: {self.config.ui_framework}", "check")
        log(f"Default language: {self.config.default_language}", "check")
        log(f"Supported: {', '.join(self.config.supported_languages)}", "check")
        log(f"Translations: {self.config.translations_dir}", "check")
        log(f"Source dirs: {', '.join(self.config.source_dirs)}", "check")

        checks = [
            ("Python Version", self.check_python),
            ("Framework Support", self.check_framework),
            ("i18n Module", self.check_i18n_module),
            ("Translation Files", self.check_translation_files),
            ("UI Coverage", self.check_ui_coverage),
            ("Key Consistency", self.check_key_consistency),
        ]

        for name, check_fn in checks:
            subheader(name)
            try:
                check_fn()
            except Exception as e:
                self.errors.append(f"{name}: {e}")
                log(f"Check failed: {e}", "error")

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

    def check_framework(self) -> None:
        """Check if selected framework is supported."""
        if self.config.ui_framework not in SUPPORTED_FRAMEWORKS:
            self.errors.append(f"Unsupported framework: {self.config.ui_framework}")
            log(f"ui_framework: INVALID (use: {', '.join(SUPPORTED_FRAMEWORKS)})", "error")
        else:
            log(f"Framework '{self.config.ui_framework}': OK", "ok")

    def check_i18n_module(self) -> None:
        """Check if i18n module exists."""
        module_path = self.config.resolve_path(self.config.i18n_module)
        log(f"Path: {module_path}", "check")

        if not module_path.exists():
            self.warnings.append(f"i18n module not found: {module_path}")
            log("Module NOT FOUND (will be created with --init)", "warn")
            return

        log("Module exists", "ok")

        # Check for required components
        try:
            with open(module_path, "r", encoding="utf-8") as f:
                content = f.read()

            if "class I18n" in content:
                log("I18n class found", "ok")
            else:
                self.warnings.append("I18n class not found in module")
                log("I18n class MISSING", "warn")

            if "def t(" in content or "def t(key" in content:
                log("t() function exported", "ok")
            else:
                self.warnings.append("t() function not found")
                log("t() function MISSING", "warn")

        except Exception as e:
            self.warnings.append(f"Cannot read module: {e}")
            log(f"Cannot analyze module: {e}", "warn")

    def check_translation_files(self) -> None:
        """Check translation files."""
        trans_dir = self.config.resolve_path(self.config.translations_dir)
        log(f"Directory: {trans_dir}", "check")

        if not trans_dir.exists():
            self.warnings.append(f"Translations directory not found: {trans_dir}")
            log("Directory NOT FOUND (will be created with --init)", "warn")
            return

        for lang in self.config.supported_languages:
            filepath = trans_dir / f"{lang}.json"
            if filepath.exists():
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    # Flatten and count keys
                    keys = self._flatten_dict(data)
                    log(f"{lang}.json: {len(keys)} keys", "ok")
                except Exception as e:
                    self.warnings.append(f"Cannot read {lang}.json: {e}")
                    log(f"{lang}.json: INVALID ({e})", "warn")
            else:
                self.warnings.append(f"Missing translation file: {lang}.json")
                log(f"{lang}.json: NOT FOUND", "warn")

    def check_ui_coverage(self) -> None:
        """Check how many UI files use i18n."""
        total_files = 0
        files_with_i18n = 0
        files_details = []

        for source_dir in self.config.source_dirs:
            source_path = self.config.resolve_path(source_dir)
            log(f"Source: {source_path}", "check")

            if not source_path.exists():
                self.warnings.append(f"Source directory not found: {source_path}")
                log(f"NOT FOUND: {source_path}", "warn")
                continue

            # Scan Python files
            py_files = list(source_path.rglob("*.py"))
            total_files += len(py_files)
            log(f"Files scanned: {len(py_files)}", "check")

            for py_file in py_files:
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Check for i18n imports
                    has_i18n = (
                        "from" in content and "i18n" in content and "import" in content and
                        ("import t" in content or "import get_i18n" in content)
                    )

                    if has_i18n:
                        files_with_i18n += 1
                        files_details.append((py_file, True))
                    else:
                        files_details.append((py_file, False))

                except Exception:
                    pass

        if total_files > 0:
            coverage = (files_with_i18n / total_files) * 100
            log(f"Coverage: {coverage:.0f}% ({files_with_i18n}/{total_files})", "info")

    def check_key_consistency(self) -> None:
        """Check key consistency between languages."""
        trans_dir = self.config.resolve_path(self.config.translations_dir)

        if not trans_dir.exists():
            log("Skipping (no translations directory)", "info")
            return

        # Load all translations
        translations: Dict[str, Set[str]] = {}
        for lang in self.config.supported_languages:
            filepath = trans_dir / f"{lang}.json"
            if filepath.exists():
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    translations[lang] = self._flatten_dict(data)
                except Exception:
                    pass

        if not translations:
            log("No valid translation files to compare", "info")
            return

        # Use default language as reference
        ref_lang = self.config.default_language
        if ref_lang not in translations:
            log(f"Reference language {ref_lang} not found", "warn")
            return

        ref_keys = translations[ref_lang]
        log(f"Reference: {ref_lang} ({len(ref_keys)} keys)", "check")

        # Compare with other languages
        for lang, keys in translations.items():
            if lang == ref_lang:
                continue

            missing = ref_keys - keys
            extra = keys - ref_keys

            if not missing and not extra:
                log(f"{lang}: COMPLETE ({len(keys)} keys)", "ok")
            else:
                if missing:
                    log(f"{lang}: {len(missing)} missing keys", "warn")
                    self.warnings.append(f"{lang}: {len(missing)} missing keys")
                if extra:
                    log(f"{lang}: {len(extra)} extra keys", "info")

    def _flatten_dict(self, data: Dict, prefix: str = "") -> Set[str]:
        """Flatten nested dict to set of keys."""
        keys = set()
        for key, value in data.items():
            full_key = f"{prefix}{key}" if prefix else key
            if isinstance(value, dict):
                keys.update(self._flatten_dict(value, f"{full_key}{self.config.key_separator}"))
            else:
                keys.add(full_key)
        return keys

    def _print_summary(self) -> None:
        """Print summary."""
        header("Summary")

        if self.errors:
            print(f"{C.RED}{C.BOLD}ERRORS ({len(self.errors)}):{C.RESET}")
            for error in self.errors:
                print(f"  {C.RED}✗{C.RESET} {error}")
            print()

        if self.warnings:
            print(f"{C.YELLOW}{C.BOLD}WARNINGS ({len(self.warnings)}):{C.RESET}")
            for warning in self.warnings:
                print(f"  {C.YELLOW}!{C.RESET} {warning}")
            print()

        if not self.errors and not self.warnings:
            print(f"{C.GREEN}{C.BOLD}All checks passed!{C.RESET}")
            print(f"\n{C.CYAN}System is ready for i18n operations.{C.RESET}")
        elif not self.errors:
            print(f"{C.YELLOW}{C.BOLD}Checks passed with warnings.{C.RESET}")
            print(f"\n{C.CYAN}You can proceed, but review warnings first.{C.RESET}")
        else:
            print(f"{C.RED}{C.BOLD}Fix errors before proceeding.{C.RESET}")


# ============================================================================
# STRING EXTRACTOR
# ============================================================================

@dataclass
class ExtractedString:
    """Extracted hardcoded string from code."""
    text: str
    file_path: Path
    line_number: int
    pattern_type: str  # e.g., "setText", "text="
    suggested_key: str
    context: str


class StringExtractor:
    """Extract hardcoded strings from source code."""

    # PyQt specific patterns
    PATTERNS_PYQT = {
        "setText": r'\.setText\s*\(\s*["\']([^"\']+)["\']\s*\)',
        "setWindowTitle": r'\.setWindowTitle\s*\(\s*["\']([^"\']+)["\']\s*\)',
        "setToolTip": r'\.setToolTip\s*\(\s*["\']([^"\']+)["\']\s*\)',
        "setPlaceholderText": r'\.setPlaceholderText\s*\(\s*["\']([^"\']+)["\']\s*\)',
        "setStatusTip": r'\.setStatusTip\s*\(\s*["\']([^"\']+)["\']\s*\)',
        "QLabel": r'QLabel\s*\(\s*["\']([^"\']+)["\']\s*[,)]',
        "QGroupBox": r'QGroupBox\s*\(\s*["\']([^"\']+)["\']\s*[,)]',
        "QPushButton": r'QPushButton\s*\(\s*["\']([^"\']+)["\']\s*[,)]',
        "QCheckBox": r'QCheckBox\s*\(\s*["\']([^"\']+)["\']\s*[,)]',
        "QRadioButton": r'QRadioButton\s*\(\s*["\']([^"\']+)["\']\s*[,)]',
        "StyledButton": r'StyledButton\s*\(\s*["\']([^"\']+)["\']\s*,',
        "addItem": r'\.addItem\s*\(\s*["\']([^"\']+)["\']\s*[,)]',
        "QMessageBox": r'QMessageBox\.\w+\s*\(\s*\w+\s*,\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*\)',
    }

    # CustomTkinter / CLI patterns
    PATTERNS_CTK = {
        # constructor: CTkLabel(..., text="Foo")
        "ctor_text": r'CTk\w+\s*\([^)]*text\s*=\s*["\']([^"\']+)["\']',
        # method: .configure(text="Foo")
        "configure_text": r'\.configure\s*\([^)]*text\s*=\s*["\']([^"\']+)["\']',
        # method: .set("Foo") for string vars or tabview
        "set": r'\.set\s*\(\s*["\']([^"\']+)["\']\s*\)',
        # .add("Foo")
        "add": r'\.add\s*\(\s*["\']([^"\']+)["\']\s*\)',
        # title("Foo")
        "title": r'\.title\s*\(\s*["\']([^"\']+)["\']\s*\)',
        # CTkMessageBox(message="Foo", title="Bar")
        "msg_message": r'CTkMessageBox\s*\([^)]*message\s*=\s*["\']([^"\']+)["\']',
        "msg_title": r'CTkMessageBox\s*\([^)]*title\s*=\s*["\']([^"\']+)["\']',
    }

    # Patterns to ignore (not translatable)
    IGNORE_PATTERNS = [
        r'^["\']$',  # empty string
        r'^[\d\s\.\-\/\\]+$',  # only digits, spaces, separators
        r'^#[0-9a-fA-F]{6}$',  # hex colors
        r'^\s*$',  # whitespace only
        r'\.(?:png|ico|jpg|jpeg|gif|svg|qss|json|txt|py|md)$',  # file extensions
        r'^[a-z_]+\.[a-z_\.]+$',  # already i18n key (e.g., "menu.pages")
        r'^(?:primary|secondary|success|warning|danger|info|center|left|right|top|bottom)$',  # constants
        r'^Qt\.',  # Qt constants
        r'^[\(\)\[\]\{\}]+$',  # brackets only
        r'^\d+\s*(?:px|pt|em|%)?$',  # CSS values
        r'^Arial|Segoe UI|Roboto|Helvetica$',  # Font names
    ]

    def __init__(self, config: I18nConfig):
        self.config = config
        self.extracted: List[ExtractedString] = []

        # Select patterns based on framework
        if self.config.ui_framework == "pyqt6":
            self.patterns = self.PATTERNS_PYQT
        else:
            self.patterns = self.PATTERNS_CTK

    def scan_directory(self, directory: Path) -> List[ExtractedString]:
        """Scan directory recursively for hardcoded strings."""
        results = []
        py_files = list(directory.rglob("*.py"))

        for py_file in py_files:
            try:
                file_results = self.scan_file(py_file)
                results.extend(file_results)
            except Exception as e:
                log(f"Error scanning {py_file}: {e}", "warn")

        return results

    def scan_file(self, filepath: Path) -> List[ExtractedString]:
        """Scan single file for hardcoded strings."""
        results = []

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            log(f"Cannot read {filepath}: {e}", "warn")
            return results

        for line_num, line in enumerate(lines, 1):
            # Skip comments and already translated
            if line.strip().startswith("#") or "t(" in line or "t (" in line:
                continue

            # Try all extraction patterns
            for pattern_type, pattern in self.patterns.items():
                matches = re.finditer(pattern, line)
                for match in matches:
                    if pattern_type == "QMessageBox":
                        # Special case: two strings (title, message)
                        title = match.group(1)
                        message = match.group(2)
                        self._add_result(results, title, filepath, line_num, "QMessageBox_title")
                        self._add_result(results, message, filepath, line_num, "QMessageBox_message")
                    else:
                        # Normal case: one string
                        text = match.group(1)
                        self._add_result(results, text, filepath, line_num, pattern_type)

        return results

    def _add_result(self, results, text, filepath, line_num, pattern_type):
        """Add extraction result if not ignored."""
        if not self.should_ignore(text):
            key = self.generate_key(text, filepath, pattern_type)
            results.append(ExtractedString(
                text=text,
                file_path=filepath,
                line_number=line_num,
                pattern_type=pattern_type,
                suggested_key=key,
                context="",
            ))

    def generate_key(self, text: str, file_path: Path, pattern_type: str) -> str:
        """Generate i18n key from text and context."""
        # Get filename
        filename = file_path.name

        # Determine prefix
        prefix = filename.replace(".py", "")
        for suffix in ["_page", "_dialog", "_view", "_window", "_widget"]:
            prefix = prefix.replace(suffix, "")

        # Determine suffix based on common words
        text_lower = text.lower()
        common_map = {
            "error": "error", "błąd": "error",
            "warning": "warning", "uwaga": "warning",
            "success": "success", "sukces": "success",
            "info": "info", "informacja": "info",
            "confirm": "confirm", "potwierdzenie": "confirm",
            "cancel": "cancel", "anuluj": "cancel",
            "ok": "ok", "save": "save", "zapisz": "save",
            "open": "open", "otwórz": "open",
            "delete": "delete", "usuń": "delete",
        }
        
        suffix = ""
        for k, v in common_map.items():
            if k in text_lower:
                suffix = v
                break
        
        if not suffix:
            suffix = self._slugify(text[:30])

        return f"{prefix}.{suffix}"

    def should_ignore(self, text: str) -> bool:
        """Check if string should be ignored."""
        # Empty or very short
        if not text or len(text) < 2:
            return True
        
        # Check if contains {} but no letters (likely format string pattern)
        if "{" in text and not any(c.isalpha() for c in text):
            return True

        # Check ignore patterns
        for pattern in self.IGNORE_PATTERNS:
            if re.match(pattern, text, re.IGNORECASE):
                return True

        return False

    def _slugify(self, text: str) -> str:
        """Convert text to slug-style key."""
        slug = text.lower()
        slug = re.sub(r'[^\w\s\-]', '', slug)
        slug = re.sub(r'[\s\-]+', '_', slug)
        slug = slug.strip('_')
        if len(slug) > 30:
            slug = slug[:30].rsplit('_', 1)[0]
        return slug


# ============================================================================
# TRANSLATION VALIDATOR
# ============================================================================

@dataclass
class ValidationResult:
    """Result of translation validation."""
    missing_keys: Dict[str, List[str]]
    unused_keys: Dict[str, List[str]]
    param_mismatches: List[Tuple[str, Dict[str, Set[str]]]]
    total_keys: Dict[str, int]


class TranslationValidator:
    """Validate translation completeness and consistency."""

    def __init__(self, config: I18nConfig):
        self.config = config
        self.translations: Dict[str, Dict] = {}

    def load_translations(self) -> None:
        """Load all translation files."""
        trans_dir = self.config.resolve_path(self.config.translations_dir)

        for lang in self.config.supported_languages:
            filepath = trans_dir / f"{lang}.json"
            if filepath.exists():
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        self.translations[lang] = json.load(f)
                except Exception:
                    self.translations[lang] = {}
            else:
                self.translations[lang] = {}

    def validate_all(self, code_keys: Optional[Set[str]] = None) -> ValidationResult:
        """Validate all translations."""
        self.load_translations()

        if not self.translations:
            return ValidationResult({}, {}, [], {})

        # Flatten all translations
        flat_translations: Dict[str, Set[str]] = {}
        for lang, data in self.translations.items():
            flat_translations[lang] = self.flatten_keys(data)

        # Use default language as reference
        ref_lang = self.config.default_language
        if ref_lang not in flat_translations:
            ref_lang = list(flat_translations.keys())[0] if flat_translations else ""

        if not ref_lang:
            return ValidationResult({}, {}, [], {})

        ref_keys = flat_translations[ref_lang]

        # Compare keys
        missing_keys: Dict[str, List[str]] = {}
        for lang, keys in flat_translations.items():
            if lang == ref_lang:
                continue
            missing = ref_keys - keys
            if missing:
                missing_keys[lang] = sorted(list(missing))

        # Find unused keys
        unused_keys: Dict[str, List[str]] = {}
        if code_keys:
            for lang, keys in flat_translations.items():
                unused = keys - code_keys
                if unused:
                    unused_keys[lang] = sorted(list(unused))

        # Check parameter consistency
        param_mismatches = self.check_param_consistency(flat_translations)

        total_keys = {lang: len(keys) for lang, keys in flat_translations.items()}

        return ValidationResult(missing_keys, unused_keys, param_mismatches, total_keys)

    def flatten_keys(self, data: Dict, prefix: str = "") -> Set[str]:
        keys = set()
        for key, value in data.items():
            full_key = f"{prefix}{key}" if prefix else key
            if isinstance(value, dict):
                keys.update(self.flatten_keys(value, f"{full_key}{self.config.key_separator}"))
            else:
                keys.add(full_key)
        return keys

    def check_param_consistency(self, flat_translations: Dict[str, Set[str]]) -> List[Tuple[str, Dict[str, Set[str]]]]:
        mismatches = []
        all_langs = list(flat_translations.keys())
        if not all_langs:
            return mismatches

        common_keys = set.intersection(*[flat_translations[lang] for lang in all_langs])

        for key in common_keys:
            params_by_lang: Dict[str, Set[str]] = {}
            for lang in all_langs:
                value = self._get_nested_value(self.translations[lang], key)
                if value and isinstance(value, str):
                    params = set(re.findall(r'\{(\w+)\}', value))
                    params_by_lang[lang] = params

            if len(set(map(frozenset, params_by_lang.values()))) > 1:
                mismatches.append((key, params_by_lang))

        return mismatches

    def _get_nested_value(self, data: Dict, key: str) -> Optional[str]:
        keys = key.split(self.config.key_separator)
        value = data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None
        return value if isinstance(value, str) else None


# ============================================================================
# COVERAGE ANALYZER
# ============================================================================

@dataclass
class CoverageStats:
    """Statistics about i18n coverage."""
    total_files: int
    files_with_i18n: int
    files_without_i18n: int
    file_coverage: Dict[str, Tuple[int, int]]
    total_i18n_usage: int
    total_hardcoded: int


class CoverageAnalyzer:
    """Analyze i18n coverage in codebase."""

    def __init__(self, config: I18nConfig):
        self.config = config

    def analyze_directory(self, directory: Path) -> CoverageStats:
        file_coverage: Dict[str, Tuple[int, int]] = {}
        total_i18n = 0
        total_hardcoded = 0
        files_with_i18n = 0
        
        py_files = list(directory.rglob("*.py"))

        for py_file in py_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                has_import = "i18n" in content and ("import t" in content or "import get_i18n" in content)
                if has_import:
                    files_with_i18n += 1

                i18n_count = len(re.findall(r'\bt\s*\(', content))
                total_i18n += i18n_count

                extractor = StringExtractor(self.config)
                hardcoded = len(extractor.scan_file(py_file))
                total_hardcoded += hardcoded

                rel_path = str(py_file.relative_to(self.config.project_root))
                file_coverage[rel_path] = (i18n_count, hardcoded)

            except Exception:
                pass

        return CoverageStats(
            len(py_files), files_with_i18n, len(py_files) - files_with_i18n,
            file_coverage, total_i18n, total_hardcoded
        )


# ============================================================================
# TEMPLATES
# ============================================================================

class TemplateRegistry:
    """Registry of code templates for i18n."""

    # Template for PyQt6 (uses QObject/Signals)
    PYQT_TEMPLATE = '''"""
i18n - Internationalization system for {app_name}.
Framework: PyQt6
Generated by setup_i18n.py

Supported languages: {languages}
"""

import json
from pathlib import Path
from typing import Dict, Optional, List

from PyQt6.QtCore import QObject, pyqtSignal


class I18n(QObject):
    """Translation manager singleton."""

    language_changed = pyqtSignal(str)

    LANGUAGES = {{{languages_dict}}}

    _instance: Optional["I18n"] = None

    def __new__(cls) -> "I18n":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        self._current_language = "{default_language}"
        self._translations: Dict[str, Dict] = {{}}
        self._translations_path: Optional[Path] = None

    def set_translations_path(self, path: Path) -> None:
        """Set path to translations directory."""
        self._translations_path = path
        self._load_translations()

    def _load_translations(self) -> None:
        """Load all translation files."""
        if not self._translations_path:
            return
        for lang_code in self.LANGUAGES.keys():
            filepath = self._translations_path / f"{{lang_code}}.json"
            if filepath.exists():
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        self._translations[lang_code] = json.load(f)
                except Exception as e:
                    print(f"Error loading translations {{lang_code}}: {{e}}")
                    self._translations[lang_code] = {{}}
            else:
                self._translations[lang_code] = {{}}

    def set_language(self, lang_code: str) -> None:
        """Change current language."""
        if lang_code in self.LANGUAGES and lang_code != self._current_language:
            self._current_language = lang_code
            self.language_changed.emit(lang_code)

    @property
    def current_language(self) -> str:
        return self._current_language

    def t(self, key: str, **kwargs) -> str:
        """
        Get translation for key.
        Args:
            key: Translation key (e.g. "menu.pages")
            **kwargs: Format parameters
        """
        translations = self._translations.get(self._current_language, {{}})
        keys = key.split("{key_separator}")
        value = translations
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                value = None
                break
        
        if value is None and self._current_language != "{fallback_language}":
            fallback = self._translations.get("{fallback_language}", {{}})
            value = fallback
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    value = None
                    break

        if value is None:
            return key

        if kwargs and isinstance(value, str):
            try:
                return value.format(**kwargs)
            except KeyError:
                return value
        return value if isinstance(value, str) else key

_i18n = I18n()

def get_i18n() -> I18n:
    return _i18n

def t(key: str, **kwargs) -> str:
    return _i18n.t(key, **kwargs)

def set_language(lang_code: str) -> None:
    _i18n.set_language(lang_code)
'''

    # Template for CustomTkinter/CLI (Pure Python Observer)
    PURE_PYTHON_TEMPLATE = '''"""
i18n - Internationalization system for {app_name}.
Framework: Pure Python / CustomTkinter
Generated by setup_i18n.py

Supported languages: {languages}
"""

import json
from pathlib import Path
from typing import Dict, Optional, List, Callable, Any

class I18n:
    """Translation manager singleton."""

    LANGUAGES = {{{languages_dict}}}

    _instance: Optional["I18n"] = None

    def __new__(cls) -> "I18n":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._current_language = "{default_language}"
        self._translations: Dict[str, Dict] = {{}}
        self._translations_path: Optional[Path] = None
        self._observers: List[Callable[[str], Any]] = []

    def set_translations_path(self, path: Path) -> None:
        """Set path to translations directory."""
        self._translations_path = path
        self._load_translations()

    def add_observer(self, callback: Callable[[str], Any]) -> None:
        """Subscribe to language changes."""
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback: Callable[[str], Any]) -> None:
        """Unsubscribe."""
        if callback in self._observers:
            self._observers.remove(callback)

    def _load_translations(self) -> None:
        if not self._translations_path:
            return
        for lang_code in self.LANGUAGES.keys():
            filepath = self._translations_path / f"{{lang_code}}.json"
            if filepath.exists():
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        self._translations[lang_code] = json.load(f)
                except Exception as e:
                    print(f"Error loading translations {{lang_code}}: {{e}}")
                    self._translations[lang_code] = {{}}
            else:
                self._translations[lang_code] = {{}}

    def set_language(self, lang_code: str) -> None:
        if lang_code in self.LANGUAGES and lang_code != self._current_language:
            self._current_language = lang_code
            self._notify_observers()

    def _notify_observers(self) -> None:
        for callback in self._observers:
            try:
                callback(self._current_language)
            except Exception as e:
                print(f"Error in i18n observer: {{e}}")

    @property
    def current_language(self) -> str:
        return self._current_language

    def t(self, key: str, **kwargs) -> str:
        translations = self._translations.get(self._current_language, {{}})
        keys = key.split("{key_separator}")
        value = translations
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                value = None
                break
        
        if value is None and self._current_language != "{fallback_language}":
            fallback = self._translations.get("{fallback_language}", {{}})
            value = fallback
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    value = None
                    break

        if value is None:
            return key

        if kwargs and isinstance(value, str):
            try:
                return value.format(**kwargs)
            except KeyError:
                return value
        return value if isinstance(value, str) else key

_i18n = I18n()

def get_i18n() -> I18n:
    return _i18n

def t(key: str, **kwargs) -> str:
    return _i18n.t(key, **kwargs)

def set_language(lang_code: str) -> None:
    _i18n.set_language(lang_code)
'''

    @classmethod
    def get_i18n_module(cls, config: I18nConfig) -> str:
        """Get i18n module template based on framework."""
        languages_dict = ", ".join([f'"{code}": "{name}"' for code, name in [
            ("en", "English"), ("pl", "Polski"), ("de", "Deutsch"), ("fr", "Français")
        ] if code in config.supported_languages])
        languages_str = ", ".join(config.supported_languages)

        template = cls.PYQT_TEMPLATE if config.ui_framework == "pyqt6" else cls.PURE_PYTHON_TEMPLATE

        return template.format(
            app_name=config.app_name,
            languages=languages_str,
            languages_dict=languages_dict,
            default_language=config.default_language,
            fallback_language=config.fallback_language,
            key_separator=config.key_separator,
        )

    @classmethod
    def get_empty_translation(cls) -> Dict:
        return {
            "app": {"name": "App", "ready": "Ready"},
            "menu": {},
            "dialogs": {"error": "Error", "ok": "OK", "cancel": "Cancel"}
        }


# ============================================================================
# SETUP MANAGER
# ============================================================================

class SetupManager:
    """Manage i18n setup operations."""

    def __init__(self, config: I18nConfig, dry_run: bool = False, force: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.force = force
        self.created_files: List[Path] = []
        self.created_dirs: List[Path] = []

    def execute_init(self) -> None:
        """Initialize i18n for new project."""
        header(f"i18n Setup - Initialize")
        log(f"Framework: {self.config.ui_framework}", "info")
        
        try:
            self.step1_validate()
            self.step2_create_directories()
            self.step3_generate_i18n_module()
            self.step4_generate_translation_files()
            self.step5_show_integration()
            self.show_summary()
        except Exception as e:
            log(f"Setup FAILED: {e}", "error")
            self.rollback()
            sys.exit(1)

    def step1_validate(self) -> None:
        module_path = self.config.resolve_path(self.config.i18n_module)
        if module_path.exists() and not self.force:
            raise ValueError(f"i18n module already exists: {module_path}\nUse --force to overwrite")

    def step2_create_directories(self) -> None:
        dirs = [
            self.config.resolve_path(self.config.i18n_module).parent,
            self.config.resolve_path(self.config.translations_dir)
        ]
        for d in dirs:
            if not d.exists():
                if not self.dry_run:
                    d.mkdir(parents=True, exist_ok=True)
                    self.created_dirs.append(d)
                log(f"Created: {d.relative_to(self.config.project_root)}", "ok" if not self.dry_run else "dry")

    def step3_generate_i18n_module(self) -> None:
        module_path = self.config.resolve_path(self.config.i18n_module)
        content = TemplateRegistry.get_i18n_module(self.config)
        if not self.dry_run:
            module_path.write_text(content, encoding="utf-8")
            self.created_files.append(module_path)
        log(f"Generated: {module_path.relative_to(self.config.project_root)}", "ok" if not self.dry_run else "dry")

    def step4_generate_translation_files(self) -> None:
        trans_dir = self.config.resolve_path(self.config.translations_dir)
        template = TemplateRegistry.get_empty_translation()
        for lang in self.config.supported_languages:
            filepath = trans_dir / f"{lang}.json"
            if filepath.exists() and not self.force:
                continue
            if not self.dry_run:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(template, f, indent=2, ensure_ascii=False)
                self.created_files.append(filepath)
            log(f"Generated: {lang}.json", "ok" if not self.dry_run else "dry")

    def step5_show_integration(self) -> None:
        subheader("Integration Code")
        if self.config.ui_framework == "pyqt6":
            print(f"""
{C.CYAN}PyQt6 Integration (in app.py):{C.RESET}
    from {self.config.app_name_lower}.utils.i18n import get_i18n, t
    
    i18n = get_i18n()
    i18n.set_translations_path(Path("resources/translations"))
    i18n.language_changed.connect(self.retranslateUi)
""")
        else:
            print(f"""
{C.CYAN}CustomTkinter/CLI Integration (in app.py):{C.RESET}
    from {self.config.app_name_lower}.utils.i18n import get_i18n, t
    
    i18n = get_i18n()
    i18n.set_translations_path(Path("resources/translations"))
    i18n.add_observer(self.on_language_change)

    def on_language_change(self, lang):
        self.label.configure(text=t("menu.title"))
""")

    def rollback(self) -> None:
        if self.dry_run: return
        log("Rolling back...", "warn")
        for f in reversed(self.created_files):
            if f.exists(): f.unlink()

    def show_summary(self) -> None:
        header("SUMMARY")
        if self.dry_run:
            log("Dry-run complete", "warn")
        else:
            print(f"{C.GREEN}i18n setup completed for {self.config.ui_framework}!{C.RESET}")

    # ... (extract/validate/stats methods remain similar but use new logic)
    
    def execute_extract(self, single_file: Optional[str] = None, output_file: Optional[str] = None) -> None:
        extractor = StringExtractor(self.config)
        results = []
        
        if single_file:
            path = Path(single_file)
            results = extractor.scan_file(path)
        else:
            for source_dir in self.config.source_dirs:
                path = self.config.resolve_path(source_dir)
                if path.exists():
                    results.extend(extractor.scan_directory(path))
        
        if not results:
            log("No hardcoded strings found", "ok")
            return
            
        header(f"Found {len(results)} strings")
        for item in results[:10]:
            print(f"Line {item.line_number}: {item.text} -> t('{item.suggested_key}')")
        
        if output_file:
            data = [{"text": r.text, "key": r.suggested_key, "file": str(r.file_path)} for r in results]
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            log(f"Saved to {output_file}", "ok")

    def execute_validate(self, fix: bool = False, target_language: Optional[str] = None) -> None:
        validator = TranslationValidator(self.config)
        res = validator.validate_all()
        header("Validation Results")
        for lang, missing in res.missing_keys.items():
            if target_language and lang != target_language: continue
            print(f"{lang}: {len(missing)} missing keys")
            if missing:
                print(f"  First few: {', '.join(missing[:3])}...")

    def execute_stats(self) -> None:
        analyzer = CoverageAnalyzer(self.config)
        total_files = 0
        total_i18n = 0
        total_hard = 0
        
        for source_dir in self.config.source_dirs:
            path = self.config.resolve_path(source_dir)
            if path.exists():
                stats = analyzer.analyze_directory(path)
                total_files += stats.total_files
                total_i18n += stats.total_i18n_usage
                total_hard += stats.total_hardcoded
        
        header("Statistics")
        print(f"Files: {total_files}")
        print(f"Translated calls: {total_i18n}")
        print(f"Hardcoded strings: {total_hard}")
        if total_i18n + total_hard > 0:
            cov = total_i18n / (total_i18n + total_hard) * 100
            print(f"Coverage: {cov:.1f}%")


# ============================================================================
# MAIN
# ============================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"i18n Setup Tool v{SCRIPT_VERSION}")
    parser.add_argument("--check", "-c", action="store_true", help="Check environment")
    parser.add_argument("--init", "-i", action="store_true", help="Initialize i18n")
    parser.add_argument("--extract", "-e", action="store_true", help="Extract strings")
    parser.add_argument("--validate", "-v", action="store_true", help="Validate translations")
    parser.add_argument("--stats", "-s", action="store_true", help="Show statistics")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Simulate")
    parser.add_argument("--force", "-f", action="store_true", help="Overwrite")
    parser.add_argument("--output", "-o", type=str, help="Output file")
    parser.add_argument("--file", type=str, help="Single file")
    parser.add_argument("--language", type=str, help="Target language")
    parser.add_argument("--fix", action="store_true", help="Auto-fix")
    return parser.parse_args()


def main() -> None:
    if platform.system() == "Windows":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception: pass

    args = parse_args()

    try:
        config = I18nConfig.load()
    except Exception as e:
        log(f"Configuration error: {e}", "error")
        sys.exit(1)

    manager = SetupManager(config, dry_run=args.dry_run, force=args.force)

    if args.check:
        EnvironmentChecker(config).check_all()
    elif args.init:
        manager.execute_init()
    elif args.extract:
        manager.execute_extract(single_file=args.file, output_file=args.output)
    elif args.validate:
        manager.execute_validate(fix=args.fix, target_language=args.language)
    elif args.stats:
        manager.execute_stats()
    else:
        print(f"{C.BOLD}i18n Setup Tool v{SCRIPT_VERSION}{C.RESET}")
        print("Run with -h for options.")

if __name__ == "__main__":
    main()