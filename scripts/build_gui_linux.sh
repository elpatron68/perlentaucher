#!/bin/bash
# Build-Script für Linux-GUI

echo "Building Perlentaucher GUI for Linux..."

# Stelle sicher, dass PyInstaller installiert ist
python3 -m pip install --upgrade pyinstaller

# Installiere GUI-Abhängigkeiten
python3 -m pip install -r requirements-gui.txt

# Baue Executable
pyinstaller build.spec --clean

echo ""
echo "Build abgeschlossen! Executable befindet sich in: dist/PerlentaucherGUI"
