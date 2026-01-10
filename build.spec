# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec-Datei für Perlentaucher GUI.

Build für alle Plattformen:
- Windows: pyinstaller build.spec
- Linux: pyinstaller build.spec
- macOS: pyinstaller build.spec
"""

import os
import sys

block_cipher = None

# Alle Dateien und Daten die eingebunden werden sollen
a = Analysis(
    ['perlentaucher_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Icons/Assets falls vorhanden
        # ('assets/*.png', 'assets'),
    ],
    hiddenimports=[
        'feedparser',
        'requests',
        'apprise',
        'semver',
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
        'perlentaucher',  # Import des Core-Moduls
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'PIL',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PerlentaucherGUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Keine Konsole für GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Kann Icon-Pfad hinzugefügt werden: 'assets/perlerntaucher_512.ico'
)
