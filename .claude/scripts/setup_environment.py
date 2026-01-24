#!/usr/bin/env python3
"""
Universal Setup Hook for .claude Framework

This script runs on --init, --init-only, or --maintenance.
It detects project type and initializes the appropriate environment.

Supported project types:
- Node.js (package.json)
- Python (requirements.txt, pyproject.toml, setup.py)
- Rust (Cargo.toml)
- Go (go.mod)
- Ruby (Gemfile)
- PHP (composer.json)
- .NET (*.csproj, *.sln)
- Flutter/Dart (pubspec.yaml)
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    """Get the project root directory (where .claude is located)."""
    script_dir = Path(__file__).parent
    # Script is in .claude/scripts/, so go up 2 levels
    return script_dir.parent.parent


def run_command(cmd: list[str], cwd: Optional[Path] = None, check: bool = False) -> bool:
    """Run a command and return success status."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check
        )
        if result.returncode == 0 and result.stdout:
            print(result.stdout.strip())
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"  Warning: {e.stderr.strip() if e.stderr else str(e)}")
        return False
    except FileNotFoundError:
        return False


def detect_project_type(root: Path) -> dict[str, bool]:
    """Detect project types based on config files."""
    return {
        "nodejs": (root / "package.json").exists(),
        "python_req": (root / "requirements.txt").exists(),
        "python_pyproject": (root / "pyproject.toml").exists(),
        "python_setup": (root / "setup.py").exists(),
        "rust": (root / "Cargo.toml").exists(),
        "go": (root / "go.mod").exists(),
        "ruby": (root / "Gemfile").exists(),
        "php": (root / "composer.json").exists(),
        "dotnet": any(root.glob("*.csproj")) or any(root.glob("*.sln")),
        "flutter": (root / "pubspec.yaml").exists(),
    }


def ensure_logs_dir(root: Path) -> None:
    """Ensure .claude/logs directory exists."""
    logs_dir = root / ".claude" / "logs"
    if not logs_dir.exists():
        logs_dir.mkdir(parents=True, exist_ok=True)
        print("  Created .claude/logs/")


def setup_nodejs(root: Path) -> None:
    """Setup Node.js project."""
    node_modules = root / "node_modules"
    if node_modules.exists():
        print("  node_modules/ already exists")
        return

    # Try package managers in order of preference
    for pm, install_cmd in [
        ("pnpm", ["pnpm", "install"]),
        ("yarn", ["yarn", "install"]),
        ("bun", ["bun", "install"]),
        ("npm", ["npm", "install"]),
    ]:
        if run_command([pm, "--version"], check=False):
            print(f"  Installing with {pm}...")
            if run_command(install_cmd, cwd=root):
                return
            break

    print("  Warning: Could not install Node.js dependencies")


def setup_python(root: Path, project_types: dict) -> None:
    """Setup Python project."""
    # Check for existing venv
    venv_paths = [root / "venv", root / ".venv", root / "env"]
    venv_exists = any(p.exists() for p in venv_paths)

    if not venv_exists:
        print("  Creating Python virtual environment...")
        if not run_command([sys.executable, "-m", "venv", "venv"], cwd=root):
            print("  Warning: Could not create venv")
            return

    # Determine pip path
    if sys.platform == "win32":
        pip_candidates = [
            root / "venv" / "Scripts" / "pip.exe",
            root / ".venv" / "Scripts" / "pip.exe",
        ]
    else:
        pip_candidates = [
            root / "venv" / "bin" / "pip",
            root / ".venv" / "bin" / "pip",
        ]

    pip_path = next((p for p in pip_candidates if p.exists()), None)
    if not pip_path:
        print("  Warning: pip not found in venv")
        return

    # Install dependencies
    if project_types.get("python_req"):
        print("  Installing from requirements.txt...")
        run_command([str(pip_path), "install", "-r", "requirements.txt"], cwd=root)
    elif project_types.get("python_pyproject"):
        print("  Installing from pyproject.toml...")
        run_command([str(pip_path), "install", "-e", "."], cwd=root)


def setup_rust(root: Path) -> None:
    """Setup Rust project."""
    target_dir = root / "target"
    if target_dir.exists():
        print("  Rust target/ already exists")
        return

    print("  Running cargo build...")
    run_command(["cargo", "build"], cwd=root)


def setup_go(root: Path) -> None:
    """Setup Go project."""
    print("  Running go mod download...")
    run_command(["go", "mod", "download"], cwd=root)


def setup_ruby(root: Path) -> None:
    """Setup Ruby project."""
    if (root / "vendor" / "bundle").exists():
        print("  Ruby gems already installed")
        return

    print("  Running bundle install...")
    run_command(["bundle", "install"], cwd=root)


def setup_php(root: Path) -> None:
    """Setup PHP project."""
    if (root / "vendor").exists():
        print("  PHP vendor/ already exists")
        return

    print("  Running composer install...")
    run_command(["composer", "install"], cwd=root)


def setup_dotnet(root: Path) -> None:
    """Setup .NET project."""
    print("  Running dotnet restore...")
    run_command(["dotnet", "restore"], cwd=root)


def setup_flutter(root: Path) -> None:
    """Setup Flutter project."""
    if (root / ".dart_tool").exists():
        print("  Flutter already initialized")
        return

    print("  Running flutter pub get...")
    run_command(["flutter", "pub", "get"], cwd=root)


def main() -> int:
    """Main setup function."""
    print("=" * 50)
    print("[Setup] Universal Environment Setup")
    print("=" * 50)

    root = get_project_root()
    print(f"[Setup] Project root: {root}")

    # Always ensure logs directory exists
    ensure_logs_dir(root)

    # Detect project types
    project_types = detect_project_type(root)
    detected = [k for k, v in project_types.items() if v]

    if not detected:
        print("[Setup] No recognized project type detected")
        print("[Setup] Done!")
        return 0

    print(f"[Setup] Detected: {', '.join(detected)}")
    print("-" * 50)

    # Setup each detected type
    if project_types["nodejs"]:
        print("[Setup] Node.js project")
        setup_nodejs(root)

    if any(project_types.get(k) for k in ["python_req", "python_pyproject", "python_setup"]):
        print("[Setup] Python project")
        setup_python(root, project_types)

    if project_types["rust"]:
        print("[Setup] Rust project")
        setup_rust(root)

    if project_types["go"]:
        print("[Setup] Go project")
        setup_go(root)

    if project_types["ruby"]:
        print("[Setup] Ruby project")
        setup_ruby(root)

    if project_types["php"]:
        print("[Setup] PHP project")
        setup_php(root)

    if project_types["dotnet"]:
        print("[Setup] .NET project")
        setup_dotnet(root)

    if project_types["flutter"]:
        print("[Setup] Flutter project")
        setup_flutter(root)

    print("=" * 50)
    print("[Setup] Done!")
    print("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())
