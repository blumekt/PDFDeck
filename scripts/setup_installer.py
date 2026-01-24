#!/usr/bin/env python3
"""
Universal Installer Setup Script v1.1

Portable setup script for adding Windows installer infrastructure to desktop applications.
Copy this script to any new project - it will auto-configure itself.

Features:
- Auto-detection of project configuration from pyproject.toml
- Support for multiple UI frameworks (PyQt6, CustomTkinter, CLI)
- Generates PyInstaller spec (Anti-Virus friendly), Inno Setup script, version info
- Full environment validation (--check flag)
- Architecture detection (x64/x86)
- Dry-run mode, rollback on errors
- Colored terminal output

Usage:
    python scripts/setup_installer.py --check              # Check environment
    python scripts/setup_installer.py --init               # Generate installer files
    python scripts/setup_installer.py --init --dry-run     # Simulate generation
    python scripts/setup_installer.py --init --force       # Overwrite existing
    python scripts/setup_installer.py --framework pyqt6    # Override framework

Configuration:
    Add to pyproject.toml:

    [tool.installer]
    app_name = "MyApp"
    app_id = "{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}"
    publisher = "Your Name"
    description = "Application description"
    releases_repo = "username/myapp-releases"
    ui_framework = "pyqt6"  # or "customtkinter", "cli"
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# ============================================================================
# CONSTANTS
# ============================================================================

SCRIPT_VERSION = "1.1"
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
class InstallerConfig:
    """Installer configuration loaded from pyproject.toml."""
    # Required
    app_name: str = ""

    # Optional with defaults
    app_id: str = ""  # GUID for Inno Setup
    publisher: str = "Unknown"
    description: str = ""
    url: str = ""
    releases_repo: str = ""
    ui_framework: str = "pyqt6"

    # Entry point
    entry_point: str = "main.py"

    # Paths
    icon_path: str = ""
    assets_dir: str = "assets"
    installer_dir: str = "installer"
    release_dir: str = "release"

    # Languages (for Inno Setup)
    languages: List[str] = field(default_factory=lambda: ["english", "polish"])

    # Hidden imports (framework-specific will be auto-added)
    hidden_imports: List[str] = field(default_factory=list)

    # Data files to include
    data_files: List[str] = field(default_factory=list)

    # Computed
    project_root: Path = field(default_factory=Path)
    app_name_lower: str = ""
    version: str = "1.0.0"
    current_year: int = field(default_factory=lambda: datetime.now().year)
    is_64bit: bool = field(default_factory=lambda: sys.maxsize > 2**32)

    @classmethod
    def load(cls, project_root: Optional[Path] = None) -> "InstallerConfig":
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
        version = project.get("version", "1.0.0")

        # Get installer config (also check tool.release for compatibility)
        tool_installer = data.get("tool", {}).get("installer", {})
        tool_release = data.get("tool", {}).get("release", {})
        tool_spectra = data.get("tool", {}).get("spectra", {})

        # Merge configs (tool.installer takes precedence)
        config_data = {**tool_spectra, **tool_release, **tool_installer}

        # Extract app name
        app_name = (
            config_data.get("app_name") or
            project.get("name", "").replace("-", "").replace("_", "").title() or
            "App"
        )
        app_name_lower = app_name.lower()

        # Generate app_id if not provided
        app_id = config_data.get("app_id", "")
        if not app_id:
            # Generate a unique random GUID for this application
            app_id = "{" + str(uuid.uuid4()).upper() + "}"

        # Create config
        config = cls(
            app_name=app_name,
            app_id=app_id,
            project_root=project_root,
            app_name_lower=app_name_lower,
            version=version,
        )

        # Override with custom values
        simple_fields = [
            "publisher", "description", "url", "releases_repo",
            "ui_framework", "entry_point", "icon_path", "assets_dir",
            "installer_dir", "release_dir"
        ]
        for key in simple_fields:
            if key in config_data:
                setattr(config, key, config_data[key])

        # List fields
        if "languages" in config_data:
            config.languages = config_data["languages"]
        if "hidden_imports" in config_data:
            config.hidden_imports = config_data["hidden_imports"]
        if "data_files" in config_data:
            config.data_files = config_data["data_files"]

        # Auto-detect icon if not specified
        if not config.icon_path:
            for pattern in [
                f"assets/{app_name_lower}_icon.ico",
                f"assets/{app_name_lower}.ico",
                f"resources/icons/{app_name_lower}.ico",
                "assets/icon.ico",
                "icon.ico",
            ]:
                if (project_root / pattern).exists():
                    config.icon_path = pattern
                    break

        # Auto-detect entry point if src layout
        if not (project_root / config.entry_point).exists():
            for pattern in [
                f"src/{app_name_lower}/__main__.py",
                f"{app_name_lower}/__main__.py",
                "__main__.py",
            ]:
                if (project_root / pattern).exists():
                    config.entry_point = pattern
                    break

        return config

    def resolve_path(self, path: str) -> Path:
        """Resolve a path relative to project root."""
        return self.project_root / path

    def get_framework_imports(self) -> List[str]:
        """Get hidden imports for the UI framework."""
        framework_imports = {
            "pyqt6": [
                "PyQt6",
                "PyQt6.QtCore",
                "PyQt6.QtWidgets",
                "PyQt6.QtGui",
                "PyQt6.sip",
            ],
            "customtkinter": [
                "customtkinter",
                "PIL",
                "PIL._tkinter_finder",
                "PIL.Image",
                "PIL.ImageGrab",
                "PIL.ImageTk",
                "tkinter",
                "tkinter.ttk",
            ],
            "cli": [],
        }
        return framework_imports.get(self.ui_framework, [])


# ============================================================================
# TEMPLATES
# ============================================================================

class TemplateRegistry:
    """Registry of installer templates."""

    # ========== PYINSTALLER SPEC TEMPLATE ==========

    SPEC_TEMPLATE = '''# -*- mode: python ; coding: utf-8 -*-
"""
{app_name} PyInstaller Specification File

This spec file configures PyInstaller to build a Windows executable.
Run with: pyinstaller {app_name_lower}.spec
Generated by setup_installer.py
"""

import sys
from pathlib import Path

# Read version from pyproject.toml
try:
    import tomllib
except ImportError:
    import tomli as tomllib

pyproject_path = Path("pyproject.toml")
if pyproject_path.exists():
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)
        VERSION = pyproject.get("project", {{}}).get("version", "1.0.0")
else:
    VERSION = "1.0.0"

print(f"Building {app_name} v{{VERSION}}")

block_cipher = None

# Analysis - collect all necessary files and dependencies
a = Analysis(
    ['{entry_point}'],
    pathex=[],
    binaries=[],
    datas=[
{datas_section}
    ],
    hiddenimports=[
{hiddenimports_section}
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'setuptools',
        'wheel',
        'pip',
        'black',
        'ruff',
        'mypy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove unnecessary files to reduce size
a.datas = [d for d in a.datas if not d[0].startswith('tcl/tzdata')]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{app_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX is disabled to prevent False Positives from Antivirus
    console={console},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
{icon_line}
    version='file_version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='{app_name}',
)
'''

    # ========== FILE VERSION INFO TEMPLATE ==========

    VERSION_INFO_TEMPLATE = '''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [StringStruct(u'CompanyName', u'{publisher}'),
          StringStruct(u'FileDescription', u'{description}'),
          StringStruct(u'FileVersion', u'{version}'),
          StringStruct(u'InternalName', u'{app_name}'),
          StringStruct(u'LegalCopyright', u'Copyright (c) {year_range} {publisher}'),
          StringStruct(u'OriginalFilename', u'{app_name}.exe'),
          StringStruct(u'ProductName', u'{app_name}'),
          StringStruct(u'ProductVersion', u'{version}')])
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''

    # ========== INNO SETUP TEMPLATE ==========

    ISS_TEMPLATE = '''; {app_name} Inno Setup Installer Script
; Creates a Windows installer for {app_name}
;
; Requirements:
; - Inno Setup 6.x (https://jrsoftware.org/isinfo.php)
; - {app_name} must be built first with PyInstaller
;
; To compile:
; - Open in Inno Setup Compiler, or
; - Run: ISCC.exe {app_name_lower}_installer.iss
;
; Generated by setup_installer.py

#define MyAppName "{app_name}"
#define MyAppVersion "{version}"
#define MyAppNumericVersion "{version}.0"
#define MyAppPublisher "{publisher}"
#define MyAppURL "{url}"
#define MyAppExeName "{app_name}.exe"
#define MyAppDescription "{description}"

[Setup]
; Application info
AppId={app_id}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppVerName={{#MyAppName}} {{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
AppPublisherURL={{#MyAppURL}}
AppSupportURL={{#MyAppURL}}
AppUpdatesURL={{#MyAppURL}}
AppMutex={{#MyAppName}}Mutex

; Install location - always ends with app name
DefaultDirName={{localappdata}}\\Programs\\{{#MyAppName}}
DefaultGroupName={{#MyAppName}}

; Install without admin privileges (user folder)
PrivilegesRequired=lowest

; Directory selection
DisableDirPage=no
UsePreviousAppDir=yes

; Output settings
OutputDir=..\\{release_dir}
OutputBaseFilename={app_name}_Setup_{{#MyAppVersion}}
{icon_line}

; Compression settings (high compression)
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=4

; Visual settings
WizardStyle=modern

; Installer info
VersionInfoVersion={{#MyAppNumericVersion}}
VersionInfoCompany={{#MyAppPublisher}}
VersionInfoDescription={{#MyAppDescription}}
VersionInfoProductName={{#MyAppName}}
VersionInfoProductVersion={{#MyAppNumericVersion}}

; Start Menu
AllowNoIcons=yes
DisableProgramGroupPage=yes

; Uninstaller
UninstallDisplayIcon={{app}}\\{{#MyAppExeName}}
UninstallDisplayName={{#MyAppName}}

; Close applications for smooth updates
CloseApplications=force
CloseApplicationsFilter={app_name}.exe
RestartApplications=yes

; Architecture Settings
{architecture_section}

{languages_section}

[Messages]
english.StatusClosingApplications=Closing applications... (this may take up to 30 seconds)
polish.StatusClosingApplications=Zamykanie aplikacji... (moze to potrwac do 30 sekund)
german.StatusClosingApplications=Anwendungen werden geschlossen... (kann bis zu 30 Sekunden dauern)

[CustomMessages]
{custom_messages_section}

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked
Name: "startmenuicon"; Description: "{{cm:StartMenuIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: checkedonce

[Files]
; All files from PyInstaller output (dist/{app_name} folder)
Source: "..\\dist\\{app_name}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu shortcut
Name: "{{userprograms}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: startmenuicon

; Desktop shortcut (optional)
Name: "{{userdesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon

[Run]
; Option to launch after install
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "{{cm:LaunchProgram,{{#StringChange(MyAppName, '&', '&&')}}}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up on uninstall
Type: files; Name: "{{app}}\\*.log"

[Code]
var
  BackupCreated: Boolean;

function InitializeSetup: Boolean;
begin
  Result := True;
end;

procedure CreateBackup;
var
  ExePath: String;
  BackupPath: String;
  RestoreBatPath: String;
  RestoreContent: String;
begin
  ExePath := ExpandConstant('{{app}}\\{app_name}.exe');
  BackupPath := ExpandConstant('{{app}}\\{app_name}.exe.backup');
  RestoreBatPath := ExpandConstant('{{app}}\\restore_backup.bat');

  if FileExists(ExePath) then
  begin
    if FileExists(BackupPath) then
      DeleteFile(BackupPath);

    if CopyFile(ExePath, BackupPath, False) then
    begin
      BackupCreated := True;

      RestoreContent := '@echo off' + #13#10 +
        'echo Restoring {app_name} backup...' + #13#10 +
        'if exist "{app_name}.exe.backup" (' + #13#10 +
        '  copy /Y "{app_name}.exe.backup" "{app_name}.exe"' + #13#10 +
        '  echo Previous version restored!' + #13#10 +
        ') else (' + #13#10 +
        '  echo No backup found!' + #13#10 +
        ')' + #13#10 +
        'pause';

      SaveStringToFile(RestoreBatPath, RestoreContent, False);
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    CreateBackup;
  end;

  if CurStep = ssPostInstall then
  begin
    if BackupCreated then
    begin
      MsgBox(ExpandConstant('{{cm:BackupCreated}}'), mbInformation, MB_OK);
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    RemoveDir(ExpandConstant('{{app}}'));
  end;
end;
'''

    # ========== CUSTOM MESSAGES TEMPLATES ==========

    CUSTOM_MESSAGES = {
        "english": '''english.StartMenuIcon=Create a Start Menu shortcut
english.BackupCreated=A backup of the previous version was created.%nIf the new version doesn't work, run 'restore_backup.bat' in the installation folder.''',
        "polish": '''polish.StartMenuIcon=Utworz skrot w Menu Start
polish.BackupCreated=Utworzono kopie zapasowa poprzedniej wersji.%nJesli nowa wersja nie dziala, uruchom 'restore_backup.bat' w folderze instalacji.''',
        "german": '''german.StartMenuIcon=Startmenu-Verknupfung erstellen
german.BackupCreated=Ein Backup der vorherigen Version wurde erstellt.%nWenn die neue Version nicht funktioniert, fuhren Sie 'restore_backup.bat' im Installationsordner aus.''',
    }

    LANGUAGE_DEFINITIONS = {
        "english": 'Name: "english"; MessagesFile: "compiler:Default.isl"',
        "polish": 'Name: "polish"; MessagesFile: "compiler:Languages\\Polish.isl"',
        "german": 'Name: "german"; MessagesFile: "compiler:Languages\\German.isl"',
        "french": 'Name: "french"; MessagesFile: "compiler:Languages\\French.isl"',
        "spanish": 'Name: "spanish"; MessagesFile: "compiler:Languages\\Spanish.isl"',
        "italian": 'Name: "italian"; MessagesFile: "compiler:Languages\\Italian.isl"',
        "russian": 'Name: "russian"; MessagesFile: "compiler:Languages\\Russian.isl"',
    }


# ============================================================================
# ENVIRONMENT CHECKER
# ============================================================================

class EnvironmentChecker:
    """Check environment before initializing installer."""

    def __init__(self, config: InstallerConfig):
        self.config = config
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def check_all(self) -> bool:
        """Run all checks."""
        header(f"Setup Installer - Environment Check v{SCRIPT_VERSION}")

        checks = [
            ("Python Version", self.check_python),
            ("Configuration", self.check_configuration),
            ("Project Structure", self.check_structure),
            ("PyInstaller", self.check_pyinstaller),
            ("Inno Setup", self.check_inno_setup),
            ("Existing Files", self.check_existing),
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
        log(f"Current: Python {current[0]}.{current[1]} ({'64-bit' if self.config.is_64bit else '32-bit'})", "check")
        log(f"Required: Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+", "check")

        if current >= MIN_PYTHON_VERSION:
            log("Python version OK", "ok")
        else:
            self.errors.append(f"Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+ required")
            log("Python version too old", "error")

    def check_configuration(self) -> None:
        """Check pyproject.toml configuration."""
        log(f"App name: {self.config.app_name}", "check")
        log(f"App ID: {self.config.app_id}", "check")
        log(f"Version: {self.config.version}", "check")
        log(f"Publisher: {self.config.publisher}", "check")
        log(f"UI framework: {self.config.ui_framework}", "check")
        log(f"Entry point: {self.config.entry_point}", "check")

        if not self.config.app_name:
            self.errors.append("app_name not configured")
            log("app_name: NOT SET", "error")
        else:
            log("app_name: OK", "ok")

        if self.config.ui_framework not in SUPPORTED_FRAMEWORKS:
            self.errors.append(f"Unsupported framework: {self.config.ui_framework}")
            log(f"ui_framework: INVALID (use: {', '.join(SUPPORTED_FRAMEWORKS)})", "error")
        else:
            log("ui_framework: OK", "ok")

        # Check entry point exists
        entry_path = self.config.resolve_path(self.config.entry_point)
        if entry_path.exists():
            log(f"Entry point: OK ({self.config.entry_point})", "ok")
        else:
            self.errors.append(f"Entry point not found: {self.config.entry_point}")
            log(f"Entry point: NOT FOUND", "error")

    def check_structure(self) -> None:
        """Check project structure."""
        # Check icon
        if self.config.icon_path:
            icon_path = self.config.resolve_path(self.config.icon_path)
            if icon_path.exists():
                log(f"Icon: {self.config.icon_path}", "ok")
            else:
                self.warnings.append(f"Icon not found: {self.config.icon_path}")
                log(f"Icon: NOT FOUND (will build without icon)", "warn")
        else:
            self.warnings.append("No icon configured")
            log("Icon: NOT CONFIGURED", "warn")
            print(f"\n{C.YELLOW}Add icon to: assets/{self.config.app_name_lower}_icon.ico{C.RESET}")

        # Check assets dir
        assets_path = self.config.resolve_path(self.config.assets_dir)
        if assets_path.exists():
            log(f"Assets: {self.config.assets_dir}/", "ok")
        else:
            self.info.append(f"Assets dir not found: {self.config.assets_dir}")
            log(f"Assets: NOT FOUND (optional)", "info")

    def check_pyinstaller(self) -> None:
        """Check PyInstaller installation."""
        try:
            result = subprocess.run(
                ["pyinstaller", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                log(f"PyInstaller: {version}", "ok")
            else:
                raise FileNotFoundError()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.errors.append("PyInstaller not installed")
            log("PyInstaller: NOT INSTALLED", "error")
            print(f"\n{C.YELLOW}Install with:{C.RESET}")
            print("  pip install pyinstaller")

    def check_inno_setup(self) -> None:
        """Check Inno Setup installation."""
        iscc_paths = [
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            r"C:\Program Files\Inno Setup 6\ISCC.exe",
        ]

        # Also check PATH
        iscc_in_path = shutil.which("ISCC")
        if iscc_in_path:
            iscc_paths.insert(0, iscc_in_path)

        for path in iscc_paths:
            if Path(path).exists():
                log(f"Inno Setup: {path}", "ok")
                return

        self.errors.append("Inno Setup not installed")
        log("Inno Setup: NOT INSTALLED", "error")
        print(f"\n{C.YELLOW}Download from:{C.RESET}")
        print("  https://jrsoftware.org/isinfo.php")

    def check_existing(self) -> None:
        """Check for existing installer files."""
        files_to_check = [
            (f"{self.config.app_name_lower}.spec", "PyInstaller spec"),
            ("file_version_info.txt", "Version info"),
            (f"{self.config.installer_dir}/{self.config.app_name_lower}_installer.iss", "Inno Setup script"),
        ]

        existing = []
        for filepath, desc in files_to_check:
            full_path = self.config.resolve_path(filepath)
            if full_path.exists():
                existing.append(f"{desc}: {filepath}")
                log(f"{desc}: EXISTS ({filepath})", "warn")
            else:
                log(f"{desc}: NOT FOUND (will be created)", "ok")

        if existing:
            self.warnings.append("Some installer files already exist")
            print(f"\n{C.YELLOW}Use --force to overwrite{C.RESET}")

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
            print("  python scripts/setup_installer.py --init")
        elif not self.errors:
            print(f"{C.YELLOW}{C.BOLD}Checks passed with warnings.{C.RESET}")
            print(f"\n{C.CYAN}Next step:{C.RESET}")
            print("  python scripts/setup_installer.py --init")
        else:
            print(f"{C.RED}{C.BOLD}Fix errors before initializing.{C.RESET}")


# ============================================================================
# SETUP MANAGER
# ============================================================================

class SetupManager:
    """Manage installer initialization."""

    def __init__(self, config: InstallerConfig, dry_run: bool = False, force: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.force = force
        self.created_files: List[Path] = []
        self.created_dirs: List[Path] = []

    def execute(self) -> None:
        """Execute full initialization."""
        header(f"Setup Installer v{SCRIPT_VERSION}")

        log(f"App: {self.config.app_name}", "info")
        log(f"Version: {self.config.version}", "info")
        log(f"Framework: {self.config.ui_framework}", "info")
        log(f"Arch: {'64-bit' if self.config.is_64bit else '32-bit'}", "info")
        log(f"Mode: {'DRY-RUN' if self.dry_run else 'PRODUCTION'}", "info")

        try:
            self.step1_validate()
            self.step2_create_directories()
            self.step3_generate_spec()
            self.step4_generate_version_info()
            self.step5_generate_iss()
            self.step6_show_usage()
            self.show_summary()
        except Exception as e:
            log(f"Setup FAILED: {e}", "error")
            self.rollback()
            sys.exit(1)

    def step1_validate(self) -> None:
        """Validate before generating."""
        subheader("Step 1: Validate")

        spec_path = self.config.resolve_path(f"{self.config.app_name_lower}.spec")
        if spec_path.exists() and not self.force:
            raise ValueError(
                f"Spec file already exists: {spec_path}\n"
                "Use --force to overwrite"
            )

        log("Validation passed", "ok")

    def step2_create_directories(self) -> None:
        """Create directories."""
        subheader("Step 2: Create Directories")

        dirs = [
            self.config.resolve_path(self.config.installer_dir),
            self.config.resolve_path(self.config.release_dir),
        ]

        for dir_path in dirs:
            if not dir_path.exists():
                if not self.dry_run:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    self.created_dirs.append(dir_path)
                log(f"Created: {dir_path}", "ok" if not self.dry_run else "dry")
            else:
                log(f"Exists: {dir_path}", "ok")

    def step3_generate_spec(self) -> None:
        """Generate PyInstaller spec file."""
        subheader("Step 3: Generate PyInstaller Spec")

        # Build datas section
        datas = []
        if self.config.assets_dir and (self.config.project_root / self.config.assets_dir).exists():
            datas.append(f"        ('{self.config.assets_dir}', '{self.config.assets_dir}'),")
        if (self.config.project_root / "pyproject.toml").exists():
            datas.append("        ('pyproject.toml', '.'),")
        if (self.config.project_root / "resources").exists():
            datas.append("        ('resources', 'resources'),")
        for df in self.config.data_files:
            datas.append(f"        ('{df}', '{df}'),")
        datas_section = "\n".join(datas)

        # Build hiddenimports section
        imports = self.config.get_framework_imports() + self.config.hidden_imports
        imports.extend(["packaging", "packaging.version"])
        hiddenimports_section = "\n".join([f"        '{imp}'," for imp in imports])

        # Icon line
        icon_line = ""
        if self.config.icon_path:
            icon_line = f"    icon='{self.config.icon_path}',"

        # Console mode
        console = "True" if self.config.ui_framework == "cli" else "False"

        content = TemplateRegistry.SPEC_TEMPLATE.format(
            app_name=self.config.app_name,
            app_name_lower=self.config.app_name_lower,
            entry_point=self.config.entry_point,
            datas_section=datas_section,
            hiddenimports_section=hiddenimports_section,
            icon_line=icon_line,
            console=console,
        )

        spec_path = self.config.resolve_path(f"{self.config.app_name_lower}.spec")
        self._write_file(spec_path, content)

    def step4_generate_version_info(self) -> None:
        """Generate file_version_info.txt."""
        subheader("Step 4: Generate Version Info")

        # Parse version to tuple (cleaning non-digit suffix)
        clean_version = re.sub(r'[^\d.]+', '', self.config.version)
        version_parts = clean_version.split(".")
        # Pad with zeros to 4 parts
        while len(version_parts) < 4:
            version_parts.append("0")
        version_tuple = f"({', '.join(version_parts[:4])})"

        # Year range
        start_year = 2024
        if self.config.current_year > start_year:
            year_range = f"{start_year}-{self.config.current_year}"
        else:
            year_range = str(start_year)

        content = TemplateRegistry.VERSION_INFO_TEMPLATE.format(
            app_name=self.config.app_name,
            version=self.config.version,
            version_tuple=version_tuple,
            publisher=self.config.publisher,
            description=self.config.description or f"{self.config.app_name} Application",
            year_range=year_range,
        )

        version_path = self.config.resolve_path("file_version_info.txt")
        self._write_file(version_path, content)

    def step5_generate_iss(self) -> None:
        """Generate Inno Setup script."""
        subheader("Step 5: Generate Inno Setup Script")

        # Languages section
        lang_lines = []
        for lang in self.config.languages:
            if lang in TemplateRegistry.LANGUAGE_DEFINITIONS:
                lang_lines.append(TemplateRegistry.LANGUAGE_DEFINITIONS[lang])
        languages_section = "[Languages]\n" + "\n".join(lang_lines)

        # Custom messages section
        msg_lines = []
        for lang in self.config.languages:
            if lang in TemplateRegistry.CUSTOM_MESSAGES:
                msg_lines.append(TemplateRegistry.CUSTOM_MESSAGES[lang])
        custom_messages_section = "\n".join(msg_lines)

        # Icon line
        icon_line = ""
        if self.config.icon_path:
            # Convert to relative path from installer dir
            icon_rel = "..\\" + self.config.icon_path.replace("/", "\\")
            icon_line = f"SetupIconFile={icon_rel}"

        # Architecture section
        if self.config.is_64bit:
            architecture_section = "; Architecture - 64-bit Windows\nArchitecturesAllowed=x64compatible\nArchitecturesInstallIn64BitMode=x64compatible"
        else:
            architecture_section = "; Architecture - 32-bit Windows\n; (No specific architecture flags needed for x86)"

        content = TemplateRegistry.ISS_TEMPLATE.format(
            app_name=self.config.app_name,
            app_name_lower=self.config.app_name_lower,
            app_id=self.config.app_id,
            version=self.config.version,
            publisher=self.config.publisher,
            description=self.config.description or f"{self.config.app_name} Application",
            url=self.config.url or f"https://github.com/{self.config.releases_repo}",
            release_dir=self.config.release_dir,
            icon_line=icon_line,
            languages_section=languages_section,
            custom_messages_section=custom_messages_section,
            architecture_section=architecture_section,
        )

        iss_path = self.config.resolve_path(
            f"{self.config.installer_dir}/{self.config.app_name_lower}_installer.iss"
        )
        self._write_file(iss_path, content)

    def step6_show_usage(self) -> None:
        """Show usage instructions."""
        subheader("Step 6: Usage Instructions")

        print(f"""
{C.CYAN}Build Process:{C.RESET}

  1. Build executable with PyInstaller:
      pyinstaller {self.config.app_name_lower}.spec

  2. Create installer with Inno Setup:
      ISCC.exe {self.config.installer_dir}/{self.config.app_name_lower}_installer.iss

  3. Find installer in:
      {self.config.release_dir}/{self.config.app_name}_Setup_{self.config.version}.exe

{C.YELLOW}Or use the release script (if available):{C.RESET}
  python scripts/release.py {self.config.version}

{C.CYAN}Configuration in pyproject.toml:{C.RESET}

  [tool.installer]
  app_name = "{self.config.app_name}"
  app_id = "{self.config.app_id}"
  publisher = "{self.config.publisher}"
  description = "{self.config.description or 'Your app description'}"
  releases_repo = "{self.config.releases_repo or 'username/repo-releases'}"
  ui_framework = "{self.config.ui_framework}"
  icon_path = "{self.config.icon_path or 'assets/icon.ico'}"
""")

    def _write_file(self, filepath: Path, content: str) -> None:
        """Write content to file."""
        if not self.dry_run:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
            self.created_files.append(filepath)

        log(f"Generated: {filepath}", "ok" if not self.dry_run else "dry")

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

        print(f"{C.GREEN}Installer setup completed!{C.RESET}\n")

        print("Created files:")
        for f in self.created_files:
            print(f"  {C.GREEN}+{C.RESET} {f}")

        print(f"\n{C.YELLOW}Next steps:{C.RESET}")
        print("  1. Review generated files")
        print(f"  2. Add icon to: {self.config.icon_path or 'assets/' + self.config.app_name_lower + '_icon.ico'}")
        print(f"  3. Build: pyinstaller {self.config.app_name_lower}.spec")
        print(f"  4. Create installer: ISCC.exe {self.config.installer_dir}/{self.config.app_name_lower}_installer.iss")


# ============================================================================
# MAIN
# ============================================================================

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=f"Setup Installer v{SCRIPT_VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/setup_installer.py --check              # Check environment
  python scripts/setup_installer.py --init               # Generate installer files
  python scripts/setup_installer.py --init --dry-run     # Simulate generation
  python scripts/setup_installer.py --init --force       # Overwrite existing
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
        help="Initialize installer (generate files)"
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
        config = InstallerConfig.load()
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

    if args.init:
        manager = SetupManager(config, dry_run=args.dry_run, force=args.force)
        manager.execute()
        sys.exit(0)

    # Default: show help
    print(f"{C.BOLD}Setup Installer v{SCRIPT_VERSION}{C.RESET}\n")
    print("Usage:")
    print("  python scripts/setup_installer.py --check    # Check environment")
    print("  python scripts/setup_installer.py --init     # Generate installer files")
    print("\nRun with -h for more options.")


if __name__ == "__main__":
    main()