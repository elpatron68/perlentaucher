#!/bin/bash
set -e

# Lese Umgebungsvariablen mit Standardwerten
INTERVAL_HOURS=${INTERVAL_HOURS:-12}
DOWNLOAD_DIR=${DOWNLOAD_DIR:-/downloads}
LIMIT=${LIMIT:-10}
LOGLEVEL=${LOGLEVEL:-INFO}
SPRACHE=${SPRACHE:-deutsch}
AUDIODESKRIPTION=${AUDIODESKRIPTION:-egal}
NOTIFY=${NOTIFY:-}
# State-Datei standardmäßig im Download-Verzeichnis speichern
STATE_FILE=${STATE_FILE:-${DOWNLOAD_DIR}/.perlentaucher_state.json}

# Konvertiere Stunden in Sekunden
INTERVAL_SECONDS=$((INTERVAL_HOURS * 3600))

echo "=========================================="
echo "Perlentaucher - Mediathek Downloader"
echo "=========================================="
echo "Intervall: ${INTERVAL_HOURS} Stunden (${INTERVAL_SECONDS} Sekunden)"
echo "Download-Verzeichnis: ${DOWNLOAD_DIR}"
echo "Limit: ${LIMIT}"
echo "Sprache: ${SPRACHE}"
echo "Audiodeskription: ${AUDIODESKRIPTION}"
echo "Log-Level: ${LOGLEVEL}"
if [ -n "${NOTIFY}" ]; then
    echo "Benachrichtigungen: Aktiviert"
else
    echo "Benachrichtigungen: Deaktiviert"
fi
echo "=========================================="
echo ""

# Erstelle Download-Verzeichnis falls nicht vorhanden
mkdir -p "${DOWNLOAD_DIR}"

# Endlosschleife
while true; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Starte Download-Zyklus..."
    
    # Führe das Script aus
    NOTIFY_ARGS=""
    if [ -n "${NOTIFY}" ]; then
        NOTIFY_ARGS="--notify ${NOTIFY}"
    fi
    
    python perlentaucher.py \
        --download-dir "${DOWNLOAD_DIR}" \
        --limit "${LIMIT}" \
        --loglevel "${LOGLEVEL}" \
        --sprache "${SPRACHE}" \
        --audiodeskription "${AUDIODESKRIPTION}" \
        --state-file "${STATE_FILE}" \
        ${NOTIFY_ARGS}
    
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Download-Zyklus erfolgreich abgeschlossen."
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Download-Zyklus mit Fehler beendet (Exit-Code: $EXIT_CODE)."
    fi
    
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Warte ${INTERVAL_HOURS} Stunden bis zum nächsten Zyklus..."
    echo ""
    
    # Warte auf das nächste Intervall
    sleep "${INTERVAL_SECONDS}"
done

