#!/bin/bash
# Quickstart-Script für Perlentaucher (macOS)
# Installiert Dependencies und führt interaktive Konfiguration durch

set -e

# Farben für Ausgabe
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Perlentaucher - Quickstart (macOS)"
echo "=========================================="
echo ""

# Funktion: Python-Check
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 7 ]; then
            echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION gefunden"
            return 0
        else
            echo -e "${RED}✗${NC} Python $PYTHON_VERSION gefunden, aber Version 3.7+ erforderlich"
            return 1
        fi
    else
        return 1
    fi
}

# Funktion: Python-Installationshinweise anzeigen
show_python_instructions() {
    echo ""
    echo -e "${YELLOW}Python 3.7+ ist nicht installiert.${NC}"
    echo ""
    echo "Installation auf macOS:"
    echo ""
    
    # Prüfe ob Homebrew installiert ist
    if command -v brew &> /dev/null; then
        echo -e "${GREEN}✓${NC} Homebrew gefunden"
        echo ""
        echo "Installation mit Homebrew (empfohlen):"
        echo "  brew install python3"
        echo ""
        echo "Oder installiere pip:"
        echo "  python3 -m ensurepip --upgrade"
        echo ""
    else
        echo "Option 1: Homebrew (empfohlen)"
        echo "  Installiere Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo "  Dann: brew install python3"
        echo ""
        echo "Option 2: Python.org"
        echo "  Lade Python von https://www.python.org/downloads/ herunter"
        echo "  und folge dem Installer"
        echo ""
    fi
    
    echo "  Oder besuche: https://www.python.org/downloads/"
    echo ""
    exit 1
}

# Funktion: pip-Check
check_pip() {
    if command -v pip3 &> /dev/null || python3 -m pip --version &> /dev/null; then
        echo -e "${GREEN}✓${NC} pip gefunden"
        return 0
    else
        echo -e "${YELLOW}⚠${NC} pip nicht gefunden. Versuche Installation..."
        if python3 -m ensurepip --upgrade 2>/dev/null; then
            echo -e "${GREEN}✓${NC} pip installiert"
            return 0
        else
            echo -e "${RED}✗${NC} pip konnte nicht installiert werden"
            echo ""
            echo "Installiere pip manuell:"
            if command -v brew &> /dev/null; then
                echo "  brew install python3  # installiert auch pip"
            else
                echo "  curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py"
                echo "  python3 get-pip.py"
            fi
            exit 1
        fi
    fi
}

# Prüfe Python
echo "Prüfe Python-Installation..."
if ! check_python; then
    show_python_instructions
fi

# Prüfe pip
echo "Prüfe pip-Installation..."
check_pip

echo ""

# Frage nach virtueller Umgebung
read -p "Soll eine virtuelle Umgebung erstellt werden? (empfohlen) [J/n]: " create_venv
create_venv=${create_venv:-J}

if [[ $create_venv =~ ^[JjYy]$ ]]; then
    echo "Erstelle virtuelle Umgebung..."
    python3 -m venv .venv
    echo -e "${GREEN}✓${NC} Virtuelle Umgebung erstellt"
    echo ""
    echo "Aktivierung der virtuellen Umgebung:"
    echo "  source .venv/bin/activate"
    echo ""
    # Aktiviere venv für diesen Session
    source .venv/bin/activate
    VENV_ACTIVE=true
else
    VENV_ACTIVE=false
fi

# Installiere Dependencies
echo "Installiere Dependencies..."
if [ "$VENV_ACTIVE" = true ] || [ -d ".venv" ]; then
    pip install -r requirements.txt
else
    pip3 install -r requirements.txt --user || pip3 install -r requirements.txt
fi
echo -e "${GREEN}✓${NC} Dependencies installiert"
echo ""

# Hole Script-Verzeichnis
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_DIR"

# Interaktive Parameterabfrage
echo "=========================================="
echo "Konfiguration"
echo "=========================================="
echo ""

# Download-Verzeichnis
read -p "Download-Verzeichnis [./downloads]: " download_dir
download_dir=${download_dir:-./downloads}

# Limit
read -p "Anzahl zu prüfender RSS-Einträge [10]: " limit
limit=${limit:-10}

# Log-Level
echo ""
echo "Log-Level wählen:"
echo "  1) DEBUG"
echo "  2) INFO (Standard)"
echo "  3) WARNING"
echo "  4) ERROR"
read -p "Auswahl [2]: " loglevel_choice
case $loglevel_choice in
    1) loglevel="DEBUG" ;;
    2) loglevel="INFO" ;;
    3) loglevel="WARNING" ;;
    4) loglevel="ERROR" ;;
    *) loglevel="INFO" ;;
esac

# Sprache
echo ""
echo "Bevorzugte Sprache:"
echo "  1) deutsch (Standard)"
echo "  2) englisch"
echo "  3) egal"
read -p "Auswahl [1]: " sprache_choice
case $sprache_choice in
    1) sprache="deutsch" ;;
    2) sprache="englisch" ;;
    3) sprache="egal" ;;
    *) sprache="deutsch" ;;
esac

# Audiodeskription
echo ""
echo "Bevorzugte Audiodeskription:"
echo "  1) mit"
echo "  2) ohne"
echo "  3) egal (Standard)"
read -p "Auswahl [3]: " audiodeskription_choice
case $audiodeskription_choice in
    1) audiodeskription="mit" ;;
    2) audiodeskription="ohne" ;;
    3) audiodeskription="egal" ;;
    *) audiodeskription="egal" ;;
esac

# State-Datei
echo ""
read -p "State-Datei [.perlentaucher_state.json]: " state_file
state_file=${state_file:-.perlentaucher_state.json}

# State-Tracking
echo ""
read -p "State-Tracking aktivieren? [J/n]: " state_tracking
state_tracking=${state_tracking:-J}
if [[ $state_tracking =~ ^[Nn]$ ]]; then
    no_state="true"
else
    no_state="false"
fi

# Benachrichtigungen
echo ""
echo "Benachrichtigungen (optional):"
echo "  Beispiele:"
echo "    - Discord: discord://webhook_id/webhook_token"
echo "    - Email: mailto://user:pass@smtp.example.com"
echo "    - Telegram: tgram://bot_token/chat_id"
read -p "Apprise-URL (leer lassen zum Überspringen): " notify

# TMDB API-Key
echo ""
read -p "TMDB API-Key (optional, leer lassen zum Überspringen): " tmdb_api_key

# OMDb API-Key
echo ""
read -p "OMDb API-Key (optional, leer lassen zum Überspringen): " omdb_api_key

# Erstelle Config-Datei
echo ""
echo "Erstelle Konfigurationsdatei..."
config_file=".perlentaucher_config.json"

cat > "$config_file" <<EOF
{
  "download_dir": "$download_dir",
  "limit": $limit,
  "loglevel": "$loglevel",
  "sprache": "$sprache",
  "audiodeskription": "$audiodeskription",
  "state_file": "$state_file",
  "no_state": $no_state,
  "notify": "$notify",
  "tmdb_api_key": "$tmdb_api_key",
  "omdb_api_key": "$omdb_api_key"
}
EOF

# Setze sichere Berechtigungen (600 = nur Eigentümer lesbar/schreibbar)
chmod 600 "$config_file"
echo -e "${GREEN}✓${NC} Konfiguration gespeichert: $config_file"

# Erstelle Wrapper-Script (gleich wie Linux)
echo ""
echo "Erstelle Wrapper-Script..."
wrapper_script="run_perlentaucher.sh"

cat > "$wrapper_script" <<'WRAPPER_EOF'
#!/bin/bash
# Wrapper-Script für Perlentaucher
# Liest Konfiguration und startet das Hauptprogramm

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

CONFIG_FILE=".perlentaucher_config.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Fehler: Konfigurationsdatei $CONFIG_FILE nicht gefunden!"
    echo "Führe zuerst das Quickstart-Script aus: ./scripts/quickstart-macos.sh"
    exit 1
fi

# Aktiviere virtuelle Umgebung falls vorhanden
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Lese Konfiguration
download_dir=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['download_dir'])")
limit=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['limit'])")
loglevel=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['loglevel'])")
sprache=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['sprache'])")
audiodeskription=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['audiodeskription'])")
state_file=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['state_file'])")
no_state=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['no_state'])")
notify=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['notify'])")
tmdb_api_key=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['tmdb_api_key'])")
omdb_api_key=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['omdb_api_key'])")

# Baue Argumente
ARGS="--download-dir \"$download_dir\" --limit $limit --loglevel $loglevel --sprache $sprache --audiodeskription $audiodeskription"

if [ "$no_state" = "true" ]; then
    ARGS="$ARGS --no-state"
else
    ARGS="$ARGS --state-file \"$state_file\""
fi

if [ -n "$notify" ]; then
    ARGS="$ARGS --notify \"$notify\""
fi

if [ -n "$tmdb_api_key" ]; then
    ARGS="$ARGS --tmdb-api-key \"$tmdb_api_key\""
fi

if [ -n "$omdb_api_key" ]; then
    ARGS="$ARGS --omdb-api-key \"$omdb_api_key\""
fi

# Starte Perlentaucher
eval "python3 perlentaucher.py $ARGS"
WRAPPER_EOF

chmod +x "$wrapper_script"
echo -e "${GREEN}✓${NC} Wrapper-Script erstellt: $wrapper_script"

echo ""
echo "=========================================="
echo -e "${GREEN}Setup abgeschlossen!${NC}"
echo "=========================================="
echo ""
echo "Starten mit:"
if [ "$VENV_ACTIVE" = true ] || [ -d ".venv" ]; then
    echo "  source .venv/bin/activate"
fi
echo "  ./run_perlentaucher.sh"
echo ""
echo "Oder manuell:"
echo "  python3 perlentaucher.py [Optionen]"
echo ""

