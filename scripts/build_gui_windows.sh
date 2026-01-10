#!/bin/bash
# Build-Script für Windows-GUI (mit Git Bash oder WSL)

echo "Building Perlentaucher GUI for Windows..."

# Stelle sicher, dass PyInstaller installiert ist
python -m pip install --upgrade pyinstaller

# Installiere GUI-Abhängigkeiten
python -m pip install -r requirements-gui.txt

# Baue Executable
pyinstaller build.spec --clean

echo ""
echo "Build abgeschlossen! Executable befindet sich in: dist/PerlentaucherGUI.exe"
