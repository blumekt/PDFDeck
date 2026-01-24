#!/usr/bin/env python3
"""
IconHub Build Script v1.1

Builds both backend (PyInstaller) and frontend (Electron) for distribution.

Usage:
    python scripts/build.py              # Build backend + frontend
    python scripts/build.py --backend    # Build only backend
    python scripts/build.py --frontend   # Build only frontend
    python scripts/build.py --check      # Only check requirements (no build)
    python scripts/build.py --no-icon    # Skip icon conversion
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Project paths
ROOT_DIR = Path(__file__).parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
INSTALLERS_DIR = ROOT_DIR / "installers"
ASSETS_DIR = INSTALLERS_DIR / "assets"


def run_command(cmd: list[str], cwd: Path | None = None, check: bool = True) -> int:
    """Run a command and return exit code."""
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print(f"In: {cwd or os.getcwd()}")
    print('='*60)

    result = subprocess.run(cmd, cwd=cwd, shell=(os.name == 'nt'))

    if check and result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)

    return result.returncode


def check_requirements():
    """Check that required tools are installed."""
    print("\nChecking requirements...")

    # Check Python
    print(f"Python: {sys.version}")

    # Check PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        print("ERROR: PyInstaller not installed. Run: pip install pyinstaller")
        sys.exit(1)

    # Check Node.js
    result = subprocess.run(["node", "--version"], capture_output=True, text=True, shell=(os.name == 'nt'))
    if result.returncode == 0:
        print(f"Node.js: {result.stdout.strip()}")
    else:
        print("ERROR: Node.js not installed")
        sys.exit(1)

    # Check npm
    result = subprocess.run(["npm", "--version"], capture_output=True, text=True, shell=(os.name == 'nt'))
    if result.returncode == 0:
        print(f"npm: {result.stdout.strip()}")
    else:
        print("ERROR: npm not installed")
        sys.exit(1)

    # Check Inno Setup (Windows only)
    if os.name == 'nt':
        iscc_paths = [
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            r"C:\Program Files\Inno Setup 6\ISCC.exe",
        ]
        found = any(Path(p).exists() for p in iscc_paths)
        if found:
            print("Inno Setup 6: found")
        else:
            print("WARNING: Inno Setup 6 not found (installer build may fail)")

    # Check GitHub CLI
    result = subprocess.run(["gh", "--version"], capture_output=True, text=True, shell=(os.name == 'nt'))
    if result.returncode == 0:
        version = result.stdout.strip().split('\n')[0]
        print(f"GitHub CLI: {version}")
    else:
        print("WARNING: GitHub CLI (gh) not found (release upload may fail)")


def convert_svg_to_ico():
    """Convert SVG icon to ICO using Pillow/CairoSVG."""
    print("\nConverting icon to ICO format...")

    svg_path = ASSETS_DIR / "icon.svg"
    ico_path = ASSETS_DIR / "icon.ico"
    png_path = ASSETS_DIR / "icon.png"

    if not svg_path.exists():
        print(f"WARNING: {svg_path} not found, skipping icon conversion")
        return

    try:
        import cairosvg
        from PIL import Image
        import io

        # Convert SVG to PNG at multiple sizes
        sizes = [16, 32, 48, 64, 128, 256]
        images = []

        for size in sizes:
            png_data = cairosvg.svg2png(url=str(svg_path), output_width=size, output_height=size)
            img = Image.open(io.BytesIO(png_data))
            images.append(img)

        # Save as ICO with multiple sizes
        images[0].save(
            ico_path,
            format='ICO',
            sizes=[(s, s) for s in sizes],
            append_images=images[1:]
        )
        print(f"Created: {ico_path}")

        # Also save a PNG for reference
        png_data = cairosvg.svg2png(url=str(svg_path), output_width=256, output_height=256)
        with open(png_path, 'wb') as f:
            f.write(png_data)
        print(f"Created: {png_path}")

    except ImportError as e:
        print(f"WARNING: Cannot convert icon (missing {e.name}). Using placeholder.")
        # Create a simple placeholder ICO
        try:
            from PIL import Image
            img = Image.new('RGBA', (256, 256), (99, 102, 241, 255))  # Indigo color
            img.save(ico_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
            print(f"Created placeholder: {ico_path}")
        except ImportError:
            print("ERROR: Pillow not installed. Cannot create icon.")


def build_backend():
    """Build Python backend with PyInstaller."""
    print("\n" + "="*60)
    print("BUILDING BACKEND")
    print("="*60)

    spec_file = BACKEND_DIR / "iconhub-backend.spec"

    if not spec_file.exists():
        print(f"ERROR: {spec_file} not found")
        sys.exit(1)

    # Clean previous build
    dist_dir = BACKEND_DIR / "dist"
    build_dir = BACKEND_DIR / "build"

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)

    # Run PyInstaller
    run_command(
        [sys.executable, "-m", "PyInstaller", "--clean", str(spec_file)],
        cwd=BACKEND_DIR
    )

    # Verify output
    if os.name == 'nt':
        exe_path = dist_dir / "iconhub-backend.exe"
    else:
        exe_path = dist_dir / "iconhub-backend"

    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\nBackend built successfully: {exe_path}")
        print(f"Size: {size_mb:.1f} MB")
    else:
        print(f"ERROR: Backend executable not found at {exe_path}")
        sys.exit(1)


def build_frontend():
    """Build Electron frontend."""
    print("\n" + "="*60)
    print("BUILDING FRONTEND")
    print("="*60)

    # Install dependencies if needed
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        print("Installing npm dependencies...")
        run_command(["npm", "install"], cwd=FRONTEND_DIR)

    # Build with electron-builder
    run_command(["npm", "run", "electron:build"], cwd=FRONTEND_DIR)

    # Check output
    output_dir = FRONTEND_DIR / "dist-builder"
    if output_dir.exists():
        print(f"\nFrontend built successfully. Output in: {output_dir}")
        # List output files
        for f in output_dir.iterdir():
            if f.is_file():
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"  {f.name}: {size_mb:.1f} MB")
    else:
        print("WARNING: Output directory not found")


def main():
    """Main build process."""
    print("="*60)
    print("IconHub Build Script v1.1")
    print("="*60)

    # Parse arguments
    build_backend_only = "--backend" in sys.argv
    build_frontend_only = "--frontend" in sys.argv
    skip_icon = "--no-icon" in sys.argv
    check_only = "--check" in sys.argv

    check_requirements()

    # Check-only mode
    if check_only:
        print("\n" + "="*60)
        print("REQUIREMENTS CHECK PASSED")
        print("="*60)
        return

    if not skip_icon:
        convert_svg_to_ico()

    if build_frontend_only:
        build_frontend()
    elif build_backend_only:
        build_backend()
    else:
        build_backend()
        build_frontend()

    print("\n" + "="*60)
    print("BUILD COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
