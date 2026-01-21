#!/usr/bin/env python3
"""
Universal i18n Setup Script v1.0

Portable setup script for adding internationalization to desktop applications.
Copy this script to any new project - it will auto-configure itself.

Features:
- Auto-detection of project configuration from pyproject.toml
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

SCRIPT_VERSION = "1.0"
MIN_PYTHON_VERSION = (3, 10)


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
                    "i18n_module", "source_dirs", "fallback_language", "key_separator"]:
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
        log(f"Default language: {self.config.default_language}", "check")
        log(f"Supported: {', '.join(self.config.supported_languages)}", "check")
        log(f"Translations: {self.config.translations_dir}", "check")
        log(f"Source dirs: {', '.join(self.config.source_dirs)}", "check")

        checks = [
            ("Python Version", self.check_python),
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

            if "language_changed" in content:
                log("language_changed signal present", "ok")
            else:
                self.info.append("language_changed signal not found (optional)")
                log("language_changed signal NOT FOUND (optional)", "info")

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
                        log(f"{py_file.relative_to(self.config.project_root)}: uses i18n", "ok")
                        files_details.append((py_file, True))
                    else:
                        files_details.append((py_file, False))

                except Exception:
                    pass

        # Show first 5 files without i18n
        files_without = [f for f, has in files_details if not has]
        for py_file in files_without[:5]:
            log(f"{py_file.relative_to(self.config.project_root)}: NO i18n", "warn")

        if len(files_without) > 5:
            log(f"... ({len(files_without) - 5} more files without i18n)", "warn")

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
    pattern_type: str  # "setText", "QLabel", "QGroupBox", etc.
    suggested_key: str
    context: str  # class/function name


class StringExtractor:
    """Extract hardcoded strings from source code."""

    # Regex patterns for detecting hardcoded strings
    EXTRACTION_PATTERNS = {
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
        # QMessageBox - captures both title and message
        "QMessageBox": r'QMessageBox\.\w+\s*\(\s*\w+\s*,\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*\)',
    }

    # Patterns to ignore (not translatable)
    IGNORE_PATTERNS = [
        r'^["\']$',  # empty string
        r'^[\d\s\.\-\/\\]+$',  # only digits, spaces, separators
        r'^#[0-9a-fA-F]{6}$',  # hex colors
        r'^\s*$',  # whitespace only
        r'\.(?:png|ico|jpg|jpeg|gif|svg|qss|json|txt|py|md)$',  # file extensions
        r'^[a-z_]+\.[a-z_\.]+$',  # already i18n key (e.g., "menu.pages")
        r'^(?:primary|secondary|success|warning|danger|info)$',  # button types
        r'^Qt\.',  # Qt constants
        r'^[\(\)\[\]\{\}]+$',  # brackets only
        r'^\d+\s*(?:px|pt|em|%)?$',  # CSS values
    ]

    # File name to key prefix mapping
    FILE_PREFIXES = {
        "sidebar.py": "menu",
        "main_window.py": "app",
        "settings_page.py": "settings",
        "pages_view.py": "pages",
        "redaction_page.py": "redaction",
        "watermark_page.py": "watermark",
        "tools_page.py": "tools",
        "security_page.py": "security",
        "analysis_page.py": "analysis",
        "automation_page.py": "automation",
        "ocr_page.py": "ocr",
        "watch_folder_page.py": "watch_folder",
        "bates_dialog.py": "bates",
        "header_footer_dialog.py": "header_footer",
        "signature_dialog.py": "signature",
        "update_dialog.py": "update",
    }

    # Pattern type to suffix mapping
    PATTERN_SUFFIXES = {
        "setWindowTitle": "title",
        "setToolTip": "tooltip",
        "setPlaceholderText": "placeholder",
        "setStatusTip": "status_tip",
    }

    def __init__(self, config: I18nConfig):
        self.config = config
        self.extracted: List[ExtractedString] = []

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
            for pattern_type, pattern in self.EXTRACTION_PATTERNS.items():
                matches = re.finditer(pattern, line)
                for match in matches:
                    if pattern_type == "QMessageBox":
                        # Special case: two strings (title, message)
                        title = match.group(1)
                        message = match.group(2)

                        if not self.should_ignore(title):
                            key = self.generate_key(title, filepath, "QMessageBox_title")
                            results.append(ExtractedString(
                                text=title,
                                file_path=filepath,
                                line_number=line_num,
                                pattern_type="QMessageBox_title",
                                suggested_key=key,
                                context="",
                            ))

                        if not self.should_ignore(message):
                            key = self.generate_key(message, filepath, "QMessageBox_message")
                            results.append(ExtractedString(
                                text=message,
                                file_path=filepath,
                                line_number=line_num,
                                pattern_type="QMessageBox_message",
                                suggested_key=key,
                                context="",
                            ))
                    else:
                        # Normal case: one string
                        text = match.group(1)
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

        return results

    def generate_key(self, text: str, file_path: Path, pattern_type: str) -> str:
        """
        Generate i18n key from text and context.

        Strategy:
        1. Determine prefix from filename
        2. Determine suffix from pattern_type or slugified text
        3. Combine: {prefix}.{suffix}
        """
        # Get filename
        filename = file_path.name

        # Determine prefix
        if filename in self.FILE_PREFIXES:
            prefix = self.FILE_PREFIXES[filename]
        elif filename.endswith("_page.py"):
            prefix = filename.replace("_page.py", "")
        elif filename.endswith("_dialog.py"):
            prefix = filename.replace("_dialog.py", "")
        elif filename.endswith("_view.py"):
            prefix = filename.replace("_view.py", "")
        else:
            prefix = filename.replace(".py", "")

        # Determine suffix
        if pattern_type in self.PATTERN_SUFFIXES:
            suffix = self.PATTERN_SUFFIXES[pattern_type]
        elif pattern_type == "QMessageBox_title":
            # Common dialog titles
            title_lower = text.lower()
            if "error" in title_lower or "błąd" in title_lower:
                return "dialogs.error"
            elif "warning" in title_lower or "uwaga" in title_lower or "ostrzeżenie" in title_lower:
                return "dialogs.warning"
            elif "success" in title_lower or "sukces" in title_lower:
                return "dialogs.success"
            elif "info" in title_lower or "informacja" in title_lower:
                return "dialogs.info"
            elif "confirm" in title_lower or "potwierdzenie" in title_lower:
                return "dialogs.confirm"
            else:
                suffix = self._slugify(text[:30])
        else:
            # Slugify text
            suffix = self._slugify(text[:40])

        return f"{prefix}.{suffix}"

    def should_ignore(self, text: str) -> bool:
        """Check if string should be ignored."""
        # Empty or very short
        if not text or len(text) < 2:
            return True

        # Check ignore patterns
        for pattern in self.IGNORE_PATTERNS:
            if re.match(pattern, text, re.IGNORECASE):
                return True

        return False

    def _slugify(self, text: str) -> str:
        """Convert text to slug-style key."""
        # Lowercase
        slug = text.lower()

        # Remove special chars, keep alphanumeric and spaces
        slug = re.sub(r'[^\w\s\-]', '', slug)

        # Replace spaces and multiple dashes with single dash
        slug = re.sub(r'[\s\-]+', '_', slug)

        # Remove leading/trailing dashes
        slug = slug.strip('_')

        # Limit length
        if len(slug) > 40:
            slug = slug[:40].rsplit('_', 1)[0]  # cut at word boundary

        return slug


# ============================================================================
# TRANSLATION VALIDATOR
# ============================================================================

@dataclass
class ValidationResult:
    """Result of translation validation."""
    missing_keys: Dict[str, List[str]]  # language -> missing keys
    unused_keys: Dict[str, List[str]]   # language -> unused keys
    param_mismatches: List[Tuple[str, Dict[str, Set[str]]]]  # key -> lang -> params
    total_keys: Dict[str, int]  # language -> count


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
                except Exception as e:
                    log(f"Error loading {lang}.json: {e}", "warn")
                    self.translations[lang] = {}
            else:
                self.translations[lang] = {}

    def validate_all(self, code_keys: Optional[Set[str]] = None) -> ValidationResult:
        """
        Validate all translations.

        Args:
            code_keys: Optional set of keys used in code (for unused key detection)
        """
        self.load_translations()

        if not self.translations:
            return ValidationResult(
                missing_keys={},
                unused_keys={},
                param_mismatches=[],
                total_keys={}
            )

        # Flatten all translations
        flat_translations: Dict[str, Set[str]] = {}
        for lang, data in self.translations.items():
            flat_translations[lang] = self.flatten_keys(data)

        # Use default language as reference
        ref_lang = self.config.default_language
        if ref_lang not in flat_translations:
            # Fallback to first available language
            ref_lang = list(flat_translations.keys())[0] if flat_translations else ""

        if not ref_lang:
            return ValidationResult(
                missing_keys={},
                unused_keys={},
                param_mismatches=[],
                total_keys={}
            )

        ref_keys = flat_translations[ref_lang]

        # Compare keys between languages
        missing_keys: Dict[str, List[str]] = {}
        for lang, keys in flat_translations.items():
            if lang == ref_lang:
                continue

            missing = ref_keys - keys
            if missing:
                missing_keys[lang] = sorted(list(missing))

        # Find unused keys (in JSON but not in code)
        unused_keys: Dict[str, List[str]] = {}
        if code_keys:
            for lang, keys in flat_translations.items():
                unused = keys - code_keys
                if unused:
                    unused_keys[lang] = sorted(list(unused))

        # Check parameter consistency
        param_mismatches = self.check_param_consistency(flat_translations)

        # Count keys
        total_keys = {lang: len(keys) for lang, keys in flat_translations.items()}

        return ValidationResult(
            missing_keys=missing_keys,
            unused_keys=unused_keys,
            param_mismatches=param_mismatches,
            total_keys=total_keys
        )

    def flatten_keys(self, data: Dict, prefix: str = "") -> Set[str]:
        """Flatten nested dict to set of keys."""
        keys = set()
        for key, value in data.items():
            full_key = f"{prefix}{key}" if prefix else key
            if isinstance(value, dict):
                keys.update(self.flatten_keys(value, f"{full_key}{self.config.key_separator}"))
            else:
                keys.add(full_key)
        return keys

    def check_param_consistency(self, flat_translations: Dict[str, Set[str]]) -> List[Tuple[str, Dict[str, Set[str]]]]:
        """
        Check if {param} placeholders are consistent across languages.

        Returns:
            List of (key, {lang: {params}}) for mismatched keys
        """
        mismatches = []

        # Get all common keys
        all_langs = list(flat_translations.keys())
        if not all_langs:
            return mismatches

        common_keys = set.intersection(*[flat_translations[lang] for lang in all_langs])

        for key in common_keys:
            # Extract params for each language
            params_by_lang: Dict[str, Set[str]] = {}

            for lang in all_langs:
                # Get actual value from nested dict
                value = self._get_nested_value(self.translations[lang], key)
                if value and isinstance(value, str):
                    params = set(re.findall(r'\{(\w+)\}', value))
                    params_by_lang[lang] = params

            # Check if all languages have same params
            if len(set(map(frozenset, params_by_lang.values()))) > 1:
                mismatches.append((key, params_by_lang))

        return mismatches

    def _get_nested_value(self, data: Dict, key: str) -> Optional[str]:
        """Get value from nested dict using dotted key."""
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
    file_coverage: Dict[str, Tuple[int, int]]  # file -> (i18n_count, total_strings)
    total_i18n_usage: int
    total_hardcoded: int


class CoverageAnalyzer:
    """Analyze i18n coverage in codebase."""

    def __init__(self, config: I18nConfig):
        self.config = config

    def analyze_directory(self, directory: Path) -> CoverageStats:
        """Analyze i18n coverage in directory."""
        file_coverage: Dict[str, Tuple[int, int]] = {}
        total_i18n = 0
        total_hardcoded = 0

        py_files = list(directory.rglob("*.py"))
        files_with_i18n = 0

        for py_file in py_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Count i18n usage
                has_import = (
                    "from" in content and "i18n" in content and "import" in content and
                    ("import t" in content or "import get_i18n" in content)
                )

                if has_import:
                    files_with_i18n += 1

                # Count t() calls
                i18n_count = len(re.findall(r'\bt\s*\(', content))
                total_i18n += i18n_count

                # Count hardcoded strings (rough estimate)
                extractor = StringExtractor(self.config)
                hardcoded = len(extractor.scan_file(py_file))
                total_hardcoded += hardcoded

                # Store per-file stats
                rel_path = str(py_file.relative_to(self.config.project_root))
                file_coverage[rel_path] = (i18n_count, hardcoded)

            except Exception:
                pass

        return CoverageStats(
            total_files=len(py_files),
            files_with_i18n=files_with_i18n,
            files_without_i18n=len(py_files) - files_with_i18n,
            file_coverage=file_coverage,
            total_i18n_usage=total_i18n,
            total_hardcoded=total_hardcoded
        )


# ============================================================================
# TEMPLATES
# ============================================================================

class TemplateRegistry:
    """Registry of code templates for i18n."""

    I18N_MODULE_TEMPLATE = '''"""
i18n - Internationalization system for {app_name}.
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

    @property
    def current_language_name(self) -> str:
        return self.LANGUAGES.get(self._current_language, "Unknown")

    def get_available_languages(self) -> List[tuple]:
        return list(self.LANGUAGES.items())

    def t(self, key: str, **kwargs) -> str:
        """
        Get translation for key.

        Args:
            key: Translation key (e.g. "menu.pages")
            **kwargs: Format parameters

        Returns:
            Translated text or key if missing
        """
        translations = self._translations.get(self._current_language, {{}})

        # Handle nested keys
        keys = key.split("{key_separator}")
        value = translations
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                value = None
                break

        # Fallback to {fallback_language}
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

        # Format with parameters
        if kwargs and isinstance(value, str):
            try:
                return value.format(**kwargs)
            except KeyError:
                return value

        return value if isinstance(value, str) else key


# Global instance
_i18n = I18n()


def get_i18n() -> I18n:
    """Get global I18n instance."""
    return _i18n


def t(key: str, **kwargs) -> str:
    """Translation shortcut."""
    return _i18n.t(key, **kwargs)


def set_language(lang_code: str) -> None:
    """Language change shortcut."""
    _i18n.set_language(lang_code)
'''

    @classmethod
    def get_i18n_module(cls, config: I18nConfig) -> str:
        """Get i18n module template with substitutions."""
        # Format languages dict
        languages_dict = ", ".join([f'"{code}": "{name}"' for code, name in [
            ("en", "English"),
            ("pl", "Polski"),
            ("de", "Deutsch"),
            ("fr", "Français"),
        ] if code in config.supported_languages])

        languages_str = ", ".join(config.supported_languages)

        return cls.I18N_MODULE_TEMPLATE.format(
            app_name=config.app_name,
            languages=languages_str,
            languages_dict=languages_dict,
            default_language=config.default_language,
            fallback_language=config.fallback_language,
            key_separator=config.key_separator,
        )

    @classmethod
    def get_empty_translation(cls) -> Dict:
        """Get empty translation template."""
        return {
            "app": {
                "name": "App",
                "ready": "Ready",
            },
            "menu": {},
            "dialogs": {
                "error": "Error",
                "warning": "Warning",
                "success": "Success",
                "info": "Information",
                "ok": "OK",
                "cancel": "Cancel",
            }
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

        log(f"App: {self.config.app_name}", "info")
        log(f"Languages: {', '.join(self.config.supported_languages)}", "info")
        log(f"Mode: {'DRY-RUN' if self.dry_run else 'PRODUCTION'}", "info")

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
        """Validate before generating."""
        subheader("Step 1: Validate")

        module_path = self.config.resolve_path(self.config.i18n_module)
        if module_path.exists():
            if not self.force:
                raise ValueError(
                    f"i18n module already exists: {module_path}\n"
                    "Use --force to overwrite"
                )
            log("Existing module will be overwritten (--force)", "warn")
        else:
            log("No conflicts", "ok")

    def step2_create_directories(self) -> None:
        """Create directories."""
        subheader("Step 2: Create Directories")

        # Module directory
        module_path = self.config.resolve_path(self.config.i18n_module)
        module_dir = module_path.parent
        if not module_dir.exists():
            if not self.dry_run:
                module_dir.mkdir(parents=True, exist_ok=True)
                self.created_dirs.append(module_dir)
            log(f"Created: {module_dir.relative_to(self.config.project_root)}", "ok" if not self.dry_run else "dry")
        else:
            log(f"Exists: {module_dir.relative_to(self.config.project_root)}", "ok")

        # Translations directory
        trans_dir = self.config.resolve_path(self.config.translations_dir)
        if not trans_dir.exists():
            if not self.dry_run:
                trans_dir.mkdir(parents=True, exist_ok=True)
                self.created_dirs.append(trans_dir)
            log(f"Created: {trans_dir.relative_to(self.config.project_root)}", "ok" if not self.dry_run else "dry")
        else:
            log(f"Exists: {trans_dir.relative_to(self.config.project_root)}", "ok")

    def step3_generate_i18n_module(self) -> None:
        """Generate i18n module."""
        subheader("Step 3: Generate i18n Module")

        module_path = self.config.resolve_path(self.config.i18n_module)
        content = TemplateRegistry.get_i18n_module(self.config)

        if not self.dry_run:
            module_path.write_text(content, encoding="utf-8")
            self.created_files.append(module_path)

        log(f"Generated: {module_path.relative_to(self.config.project_root)}", "ok" if not self.dry_run else "dry")

    def step4_generate_translation_files(self) -> None:
        """Generate translation files."""
        subheader("Step 4: Generate Translation Files")

        trans_dir = self.config.resolve_path(self.config.translations_dir)
        template = TemplateRegistry.get_empty_translation()

        for lang in self.config.supported_languages:
            filepath = trans_dir / f"{lang}.json"

            if filepath.exists() and not self.force:
                log(f"Skipped: {lang}.json (already exists)", "warn")
                continue

            if not self.dry_run:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(template, f, indent=2, ensure_ascii=False)
                self.created_files.append(filepath)

            log(f"Generated: {lang}.json", "ok" if not self.dry_run else "dry")

    def step5_show_integration(self) -> None:
        """Show integration instructions."""
        subheader("Step 5: Integration Code")

        print(f"""
{C.CYAN}Add to your application initialization (e.g., app.py):{C.RESET}

    from pathlib import Path
    from {self.config.app_name_lower}.utils.i18n import get_i18n

    # Initialize i18n
    i18n = get_i18n()
    resources_dir = Path(__file__).parent.parent / "resources"
    i18n.set_translations_path(resources_dir / "translations")

{C.CYAN}Use in UI files:{C.RESET}

    from {self.config.app_name_lower}.utils.i18n import t

    # In your widgets/dialogs:
    self.setWindowTitle(t("app.name"))
    label = QLabel(t("menu.pages"))
    button = QPushButton(t("dialogs.ok"))

{C.CYAN}Change language:{C.RESET}

    from {self.config.app_name_lower}.utils.i18n import set_language

    set_language("pl")  # Switch to Polish
""")

    def rollback(self) -> None:
        """Rollback on error."""
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

        print(f"{C.GREEN}i18n setup completed!{C.RESET}\n")

        print("Created files:")
        for f in self.created_files:
            rel_path = f.relative_to(self.config.project_root)
            print(f"  {C.GREEN}+{C.RESET} {rel_path}")

        print(f"\n{C.YELLOW}Next steps:{C.RESET}")
        print("  1. Review generated files")
        print("  2. Add integration code to your app")
        print("  3. Start using t() in UI components")
        print("  4. Run: python scripts/setup_i18n.py --check")

    def execute_extract(self, single_file: Optional[str] = None, output_file: Optional[str] = None) -> None:
        """Extract hardcoded strings from code."""
        header(f"String Extraction Report")

        extractor = StringExtractor(self.config)

        if single_file:
            # Extract from single file
            filepath = Path(single_file)
            if not filepath.is_absolute():
                filepath = self.config.project_root / single_file

            if not filepath.exists():
                log(f"File not found: {single_file}", "error")
                return

            try:
                rel_path = filepath.relative_to(self.config.project_root)
            except ValueError:
                rel_path = filepath

            log(f"Scanning file: {rel_path}", "info")
            results = extractor.scan_file(filepath)
        else:
            # Extract from all source directories
            results = []
            for source_dir in self.config.source_dirs:
                source_path = self.config.resolve_path(source_dir)
                if not source_path.exists():
                    log(f"Source directory not found: {source_path}", "warn")
                    continue

                log(f"Scanning directory: {source_path.relative_to(self.config.project_root)}", "info")
                dir_results = extractor.scan_directory(source_path)
                results.extend(dir_results)

        if not results:
            log("No hardcoded strings found!", "ok")
            return

        # Group by file
        by_file: Dict[Path, List[ExtractedString]] = {}
        for item in results:
            if item.file_path not in by_file:
                by_file[item.file_path] = []
            by_file[item.file_path].append(item)

        # Print report
        for filepath in sorted(by_file.keys()):
            subheader(f"File: {filepath.relative_to(self.config.project_root)}")

            for item in sorted(by_file[filepath], key=lambda x: x.line_number):
                print(f"\n  {C.YELLOW}LINE {item.line_number:4d}{C.RESET} | {item.pattern_type}")
                print(f"    Text:      \"{item.text[:60]}{'...' if len(item.text) > 60 else ''}\"")
                print(f"    Suggested: {C.GREEN}t(\"{item.suggested_key}\"){C.RESET}")

                # Show replacement suggestion
                if item.pattern_type in ["setText", "setWindowTitle", "setToolTip"]:
                    print(f"    Replace:   .{item.pattern_type}({C.GREEN}t(\"{item.suggested_key}\"){C.RESET})")
                elif item.pattern_type in ["QLabel", "QGroupBox", "QPushButton"]:
                    print(f"    Replace:   {item.pattern_type}({C.GREEN}t(\"{item.suggested_key}\"){C.RESET})")
                elif item.pattern_type == "StyledButton":
                    print(f"    Replace:   StyledButton({C.GREEN}t(\"{item.suggested_key}\"){C.RESET}, ...)")
                elif item.pattern_type in ["QMessageBox_title", "QMessageBox_message"]:
                    print(f"    Replace:   QMessageBox.xxx(self, {C.GREEN}t(\"{item.suggested_key}\"){C.RESET}, ...)")

        # Summary
        header("Summary")
        total_files = len(by_file)
        total_strings = len(results)

        print(f"Files scanned:       {C.BOLD}{total_files}{C.RESET}")
        print(f"Strings extracted:   {C.BOLD}{total_strings}{C.RESET}")

        # Collect unique keys
        unique_keys = set(item.suggested_key for item in results)
        print(f"Unique keys:         {C.BOLD}{len(unique_keys)}{C.RESET}")

        # Save to JSON if requested
        if output_file:
            output_path = Path(output_file)
            try:
                data = {
                    "total_files": total_files,
                    "total_strings": total_strings,
                    "unique_keys": sorted(list(unique_keys)),
                    "strings": [
                        {
                            "text": item.text,
                            "file": str(item.file_path.relative_to(self.config.project_root)),
                            "line": item.line_number,
                            "pattern": item.pattern_type,
                            "key": item.suggested_key,
                        }
                        for item in results
                    ]
                }

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                print(f"\n{C.GREEN}Output saved to:{C.RESET} {output_path}")

            except Exception as e:
                log(f"Cannot save output file: {e}", "error")

        # Show next steps
        print(f"\n{C.CYAN}Next steps:{C.RESET}")
        print("  1. Review suggested keys above")
        print(f"  2. Add keys to {self.config.translations_dir}/en.json")
        print("  3. Translate to other languages")
        print("  4. Update code with t() calls")
        print("  5. Run: python scripts/setup_i18n.py --validate")

    def execute_validate(self, fix: bool = False, target_language: Optional[str] = None) -> None:
        """Validate translation completeness."""
        header("Translation Validation Report")

        validator = TranslationValidator(self.config)
        result = validator.validate_all()

        # Reference language
        ref_lang = self.config.default_language
        ref_count = result.total_keys.get(ref_lang, 0)
        print(f"Reference language: {C.BOLD}{ref_lang}{C.RESET} ({ref_count} keys)\n")

        # Languages
        for lang in self.config.supported_languages:
            if target_language and lang != target_language:
                continue

            count = result.total_keys.get(lang, 0)
            missing = result.missing_keys.get(lang, [])
            missing_count = len(missing)

            if missing_count == 0:
                status = f"{C.GREEN}COMPLETE [OK]{C.RESET}"
            else:
                status = f"{C.YELLOW}INCOMPLETE [!]{C.RESET}"

            subheader(f"Language: {lang}")
            print(f"  Status:  {status}")
            print(f"  Keys:    {count} / {ref_count} ({(count/ref_count*100) if ref_count > 0 else 0:.0f}%)")

            if missing_count > 0:
                print(f"  Missing: {C.YELLOW}{missing_count}{C.RESET}")
                # Show first 10 missing keys
                for key in missing[:10]:
                    print(f"    - {key}")
                if missing_count > 10:
                    print(f"    ... ({missing_count - 10} more)")

        # Unused keys
        if result.unused_keys:
            subheader("Unused Keys")
            print("  (keys in JSON but not in reference language)\n")
            for lang, keys in result.unused_keys.items():
                if keys:
                    print(f"  {lang}: {len(keys)} unused")
                    for key in keys[:5]:
                        print(f"    - {key}")
                    if len(keys) > 5:
                        print(f"    ... ({len(keys) - 5} more)")

        # Parameter mismatches
        if result.param_mismatches:
            subheader("Parameter Mismatches")
            print("  (keys with inconsistent {param} across languages)\n")
            for key, params_by_lang in result.param_mismatches[:10]:
                print(f"  Key: {C.YELLOW}{key}{C.RESET}")
                for lang, params in params_by_lang.items():
                    params_str = ', '.join(sorted(params)) if params else "(none)"
                    print(f"    {lang}: {{{params_str}}}")
            if len(result.param_mismatches) > 10:
                print(f"    ... ({len(result.param_mismatches) - 10} more)")

        # Summary
        header("Summary")
        complete_langs = [lang for lang in self.config.supported_languages if lang not in result.missing_keys]
        incomplete_langs = [lang for lang in result.missing_keys.keys()]

        print(f"Total keys:      {ref_count}")
        print(f"Complete langs:  {len(complete_langs)} ({', '.join(complete_langs)})")
        if incomplete_langs:
            print(f"Incomplete:      {len(incomplete_langs)} ({', '.join(incomplete_langs)})")
        print(f"Param issues:    {len(result.param_mismatches)}")

        # Fix missing keys if requested
        if fix and result.missing_keys and not self.dry_run:
            print(f"\n{C.YELLOW}Fixing missing keys...{C.RESET}")
            # TODO: Implement auto-fix (add empty strings to JSON)
            log("--fix not implemented yet", "warn")

    def execute_stats(self) -> None:
        """Show coverage statistics."""
        header("i18n Coverage Statistics")

        # Translation files stats
        validator = TranslationValidator(self.config)
        result = validator.validate_all()

        subheader("Translation Files")
        print(f"  {'Language':<12} {'Keys':<8} {'Coverage':<12} {'Status'}")
        print(f"  {'-'*12} {'-'*8} {'-'*12} {'-'*20}")

        ref_lang = self.config.default_language
        ref_count = result.total_keys.get(ref_lang, 0)

        for lang in self.config.supported_languages:
            count = result.total_keys.get(lang, 0)
            coverage = (count / ref_count * 100) if ref_count > 0 else 0
            missing_count = len(result.missing_keys.get(lang, []))

            if lang == ref_lang:
                status = f"{C.GREEN}[OK] (reference){C.RESET}"
                bar = "=" * 10
            elif missing_count == 0:
                status = f"{C.GREEN}[OK]{C.RESET}"
                bar = "=" * 10
            else:
                status = f"{C.YELLOW}[!] ({missing_count} missing){C.RESET}"
                bar_len = int(coverage / 10)
                bar = "=" * bar_len + "." * (10 - bar_len)

            print(f"  {lang:<12} {count:<8} [{bar}] {coverage:>5.0f}%  {status}")

        # UI Files coverage
        subheader("UI Files Coverage")

        analyzer = CoverageAnalyzer(self.config)
        all_stats = CoverageStats(
            total_files=0,
            files_with_i18n=0,
            files_without_i18n=0,
            file_coverage={},
            total_i18n_usage=0,
            total_hardcoded=0
        )

        for source_dir in self.config.source_dirs:
            source_path = self.config.resolve_path(source_dir)
            if not source_path.exists():
                continue

            stats = analyzer.analyze_directory(source_path)
            all_stats.total_files += stats.total_files
            all_stats.files_with_i18n += stats.files_with_i18n
            all_stats.files_without_i18n += stats.files_without_i18n
            all_stats.total_i18n_usage += stats.total_i18n_usage
            all_stats.total_hardcoded += stats.total_hardcoded
            all_stats.file_coverage.update(stats.file_coverage)

        # Show top files needing i18n
        print(f"  {'File':<45} {'i18n':<8} {'Hardcoded':<10} {'Status'}")
        print(f"  {'-'*45} {'-'*8} {'-'*10} {'-'*15}")

        # Sort by hardcoded count (descending)
        sorted_files = sorted(
            all_stats.file_coverage.items(),
            key=lambda x: x[1][1],  # sort by hardcoded count
            reverse=True
        )

        for filepath, (i18n_count, hardcoded_count) in sorted_files[:15]:
            total = i18n_count + hardcoded_count
            if total == 0:
                continue

            coverage_pct = (i18n_count / total * 100) if total > 0 else 0

            # Shorten filepath
            short_path = filepath
            if len(short_path) > 45:
                parts = short_path.split('/')
                short_path = f".../{'/'.join(parts[-2:])}"

            if hardcoded_count == 0:
                status = f"{C.GREEN}[OK]{C.RESET}"
            elif coverage_pct > 80:
                status = f"{C.YELLOW}[!]{C.RESET}"
            else:
                status = f"{C.RED}[X]{C.RESET}"

            print(f"  {short_path:<45} {i18n_count:<8} {hardcoded_count:<10} {coverage_pct:>5.0f}% {status}")

        if len(sorted_files) > 15:
            print(f"\n  ... ({len(sorted_files) - 15} more files)")

        # Overall summary
        subheader("Overall Summary")

        total_strings = all_stats.total_i18n_usage + all_stats.total_hardcoded
        coverage_pct = (all_stats.total_i18n_usage / total_strings * 100) if total_strings > 0 else 0
        file_coverage_pct = (all_stats.files_with_i18n / all_stats.total_files * 100) if all_stats.total_files > 0 else 0

        print(f"  Total UI files:             {all_stats.total_files}")
        print(f"  Files using i18n:           {all_stats.files_with_i18n}  ({file_coverage_pct:.0f}%)")
        print(f"  Files without i18n:         {all_stats.files_without_i18n}  ({100-file_coverage_pct:.0f}%)")
        print()
        print(f"  Total translatable strings: {total_strings}")
        print(f"  Already translated:         {all_stats.total_i18n_usage}  ({coverage_pct:.0f}%)")
        print(f"  Pending translation:        {all_stats.total_hardcoded}  ({100-coverage_pct:.0f}%)")

        # Estimated work
        if all_stats.total_hardcoded > 0:
            print(f"\n  {C.YELLOW}Estimated work:{C.RESET}")
            print(f"    - Keys to add:           ~{all_stats.total_hardcoded}")
            print(f"    - Files to modify:       {all_stats.files_without_i18n}")
            print(f"    - Code lines to change:  ~{all_stats.total_hardcoded * 1.5:.0f}")

        # Recommendations
        print(f"\n{C.CYAN}Recommendation:{C.RESET}")
        if all_stats.total_hardcoded > 0:
            print(f"  Run: python scripts/setup_i18n.py --extract --output pending.json")
            print(f"  Then add keys to translations and update UI files.")
        else:
            print(f"  {C.GREEN}All strings are already translated!{C.RESET}")


# ============================================================================
# MAIN
# ============================================================================

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=f"i18n Setup Tool v{SCRIPT_VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/setup_i18n.py --check              # Check environment
  python scripts/setup_i18n.py --init               # Generate i18n files
  python scripts/setup_i18n.py --extract            # Extract hardcoded strings
  python scripts/setup_i18n.py --validate           # Validate translations
  python scripts/setup_i18n.py --stats              # Coverage statistics
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
        help="Initialize i18n (generate files)"
    )
    parser.add_argument(
        "--extract", "-e",
        action="store_true",
        help="Extract hardcoded strings from code"
    )
    parser.add_argument(
        "--validate", "-v",
        action="store_true",
        help="Validate translation completeness"
    )
    parser.add_argument(
        "--stats", "-s",
        action="store_true",
        help="Show coverage statistics"
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
        "--output", "-o",
        type=str,
        help="Output file for extract/validate"
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Single file to process (extract mode)"
    )
    parser.add_argument(
        "--language",
        type=str,
        help="Target language (validate/stats mode)"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix missing keys (validate mode)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    # Fix Windows console encoding
    if platform.system() == "Windows":
        try:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except Exception:
            pass

    args = parse_args()

    try:
        config = I18nConfig.load()
    except Exception as e:
        log(f"Configuration error: {e}", "error")
        sys.exit(1)

    if args.check:
        checker = EnvironmentChecker(config)
        success = checker.check_all()
        sys.exit(0 if success else 1)

    if args.extract:
        manager = SetupManager(config, dry_run=args.dry_run, force=args.force)
        manager.execute_extract(single_file=args.file, output_file=args.output)
        sys.exit(0)

    if args.validate:
        manager = SetupManager(config, dry_run=args.dry_run, force=args.force)
        manager.execute_validate(fix=args.fix, target_language=args.language)
        sys.exit(0)

    if args.stats:
        manager = SetupManager(config, dry_run=args.dry_run, force=args.force)
        manager.execute_stats()
        sys.exit(0)

    if args.init:
        manager = SetupManager(config, dry_run=args.dry_run, force=args.force)
        manager.execute_init()
        sys.exit(0)

    # Default: show help
    print(f"{C.BOLD}i18n Setup Tool v{SCRIPT_VERSION}{C.RESET}\n")
    print("Usage:")
    print("  python scripts/setup_i18n.py --check      # Check environment")
    print("  python scripts/setup_i18n.py --init       # Generate i18n files")
    print("  python scripts/setup_i18n.py --extract    # Extract strings")
    print("  python scripts/setup_i18n.py --validate   # Validate translations")
    print("  python scripts/setup_i18n.py --stats      # Show statistics")
    print("\nRun with -h for more options.")


if __name__ == "__main__":
    main()
