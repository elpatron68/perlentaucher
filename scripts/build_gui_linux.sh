#!/usr/bin/env bash
# Build-Script für Linux-GUI
#
# Legt bei Bedarf .venv im Projektroot an und installiert dort Abhängigkeiten
# (kein PEP-668-Konflikt mit systemweitem Python wie unter Arch/CachyOS).
#
# Fish-Shell: nicht `source .venv/bin/activate` nutzen — das ist ein Bash-Skript.
# Stattdessen:  source .venv/bin/activate.fish
# oder einfach weiter dieses Bash-Skript ausführen:  bash scripts/build_gui_linux.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV="$ROOT/.venv"
PY="$VENV/bin/python"
PIP="$PY -m pip"

echo "Building Perlentaucher GUI for Linux..."
echo "Projektroot: $ROOT"

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "Virtuelle Umgebung anlegen: $VENV"
  python3 -m venv "$VENV"
fi

echo "Pakete im venv installieren (pip, PyInstaller, requirements-gui) …"
$PY -m pip install --upgrade pip
$PIP install --upgrade pyinstaller
$PIP install -r requirements-gui.txt

echo "PyInstaller-Build …"
"$PY" -m PyInstaller build.spec --clean --noconfirm

echo ""
echo "Build abgeschlossen! Executable befindet sich in: dist/PerlentaucherGUI"
