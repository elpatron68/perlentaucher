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

# Sammle System-Bibliotheken für Linux (SSL/TLS)
# PyInstaller sollte diese automatisch finden, aber wir können explizit hinzufügen
collect_binaries = []
collect_datas = []

# Hinweis: PyInstaller findet normalerweise automatisch SSL/Crypto-Bibliotheken
# via certifi. Falls Probleme auftreten, können hier manuell Bibliotheken
# hinzugefügt werden, z.B.:
# if sys.platform == 'linux':
#     collect_binaries.append(('/usr/lib64/libssl.so.3', '.'))
#     collect_binaries.append(('/usr/lib64/libcrypto.so.3', '.'))

# Alle Dateien und Daten die eingebunden werden sollen
a = Analysis(
    ['perlentaucher_gui.py'],
    pathex=[],
    binaries=collect_binaries,
    datas=collect_datas + [
        # Icons/Assets falls vorhanden
        # ('assets/*.png', 'assets'),
    ],
    hiddenimports=[
        'feedparser',
        'requests',
        'requests.packages.urllib3',
        'requests.packages.urllib3.util.ssl_',
        'urllib3',
        'urllib3.util.ssl_',
        'certifi',
        'certifi.core',
        'ssl',
        '_ssl',
        '_socket',
        'apprise',
        'semver',
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
        'PyQt6.QtNetwork',
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

# Erstelle EXE für alle Plattformen
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

# macOS: Erstelle zusätzlich APP Bundle aus dem EXE
# PyInstaller erstellt auf macOS automatisch ein .app Bundle wenn console=False
# Für explizite Bundle-Erstellung, uncomment folgendes:
# if sys.platform == 'darwin':
#     app = BUNDLE(
#         exe,
#         name='PerlentaucherGUI.app',
#         icon=None,
#         bundle_identifier='org.perlentaucher.gui',
#         info_plist={
#             'NSPrincipalClass': 'NSApplication',
#             'NSHighResolutionCapable': 'True',
#         },
#     )
