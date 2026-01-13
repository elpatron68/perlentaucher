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
    ['src/perlentaucher_gui.py'],
    pathex=[],
    binaries=collect_binaries,
    datas=collect_datas + [
        # Icons/Assets - müssen eingebunden werden für PyInstaller-Executables
        ('assets/icon_256.png', 'assets'),
        ('assets/icon_512.png', 'assets'),
        ('assets/logo_about.png', 'assets'),
    ],
    hiddenimports=[
        'feedparser',
        'requests',
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
        'src.perlentaucher',  # Import des Core-Moduls
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
# Für macOS: PyInstaller erstellt automatisch ein .app Bundle wenn console=False
# target_arch='universal2' wird NICHT in build.spec unterstützt, sondern nur als Kommandozeilen-Argument
# Für Universal Binary verwende: pyinstaller build.spec --target-arch universal2
if sys.platform == 'darwin':
    # macOS: Standard-Build (wird auf der Runner-Architektur erstellt)
    # Für Universal Binary muss --target-arch universal2 als Kommandozeilen-Argument verwendet werden
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
        codesign_identity=None,
        entitlements_file=None,
        icon='assets/icon.ico',
    )
else:
    # Windows/Linux: Standard-Build
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
        codesign_identity=None,
        entitlements_file=None,
        icon='assets/icon.ico',  # Icon für Windows Executable
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
