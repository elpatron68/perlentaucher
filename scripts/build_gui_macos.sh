#!/bin/bash
# Build-Script für macOS-GUI

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Venv nutzen falls vorhanden
if [ -d ".venv" ]; then
  echo "Aktiviere .venv..."
  # shellcheck source=/dev/null
  source .venv/bin/activate
else
  echo "Hinweis: Kein .venv gefunden, nutze System-Python."
fi

echo "Building Perlentaucher GUI for macOS (native Architektur)..."

# Stelle sicher, dass PyInstaller installiert ist
python -m pip install --upgrade pyinstaller

# Installiere GUI-Abhängigkeiten
python -m pip install -r requirements-gui.txt

# Baue für die aktuelle Architektur (arm64 oder x86_64)
# Hinweis: universal2 würde alle Abhängigkeiten als Fat Binary erfordern (z. B. PyYAML).
pyinstaller build.spec --clean

echo ""
echo "Build abgeschlossen! Ausführbare Datei: dist/PerlentaucherGUI"
echo "Starten mit: open dist/PerlentaucherGUI  oder  ./dist/PerlentaucherGUI"
