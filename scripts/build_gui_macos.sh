#!/bin/bash
# Build-Script für macOS-GUI

echo "Building Perlentaucher GUI for macOS (universal2: Intel + Apple Silicon)..."

# Stelle sicher, dass PyInstaller installiert ist
python3 -m pip install --upgrade pyinstaller

# Installiere GUI-Abhängigkeiten
python3 -m pip install -r requirements-gui.txt

# Baue Universal Binary (Intel + Apple Silicon)
pyinstaller build.spec --clean --windowed --target-arch universal2

echo ""
echo "Build abgeschlossen! Universal Binary befindet sich in: dist/PerlentaucherGUI.app"
echo "Die App sollte auf Intel- und Apple-Silicon-Macs funktionieren."
