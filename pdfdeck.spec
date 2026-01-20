# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PDFDeck
"""

import sys
from pathlib import Path

block_cipher = None

# Project paths
PROJECT_ROOT = Path(SPECPATH)
SRC_DIR = PROJECT_ROOT / 'src'
RESOURCES_DIR = PROJECT_ROOT / 'resources'

# Analysis
a = Analysis(
    [str(SRC_DIR / 'pdfdeck' / '__main__.py')],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=[
        # Resources
        (str(RESOURCES_DIR / 'styles'), 'resources/styles'),
        (str(RESOURCES_DIR / 'stamps'), 'resources/stamps'),
        (str(RESOURCES_DIR / 'translations'), 'resources/translations'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        'fitz',
        'PIL',
        'PIL.Image',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'pytest',
        'mypy',
        'ruff',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove unnecessary Qt plugins to reduce size
excluded_binaries = [
    'Qt6WebEngine',
    'Qt6Quick',
    'Qt6Qml',
    'Qt6Designer',
    'Qt6Network',
    'Qt6Sql',
    'Qt6Test',
    'opengl32sw.dll',
]

a.binaries = [
    (name, path, type_)
    for name, path, type_ in a.binaries
    if not any(exc in name for exc in excluded_binaries)
]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PDFDeck',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI application - no console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='file_version_info.txt',
    icon=str(RESOURCES_DIR / 'icons' / 'pdfdeck.ico') if (RESOURCES_DIR / 'icons' / 'pdfdeck.ico').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PDFDeck',
)
