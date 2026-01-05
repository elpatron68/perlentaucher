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
TMDB_API_KEY=${TMDB_API_KEY:-}
OMDB_API_KEY=${OMDB_API_KEY:-}
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
# Prüfe Metadaten-Provider
METADATA_PROVIDER=""
if [ -n "${TMDB_API_KEY}" ] && [ -n "${OMDB_API_KEY}" ]; then
    METADATA_PROVIDER="TMDB, OMDB"
elif [ -n "${TMDB_API_KEY}" ]; then
    METADATA_PROVIDER="TMDB"
elif [ -n "${OMDB_API_KEY}" ]; then
    METADATA_PROVIDER="OMDB"
else
    METADATA_PROVIDER="Keiner"
fi
if [ "${METADATA_PROVIDER}" != "Keiner" ]; then
    echo "Metadaten-Provider: Aktiviert (${METADATA_PROVIDER})"
else
    echo "Metadaten-Provider: Deaktiviert"
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
    
    TMDB_API_KEY_ARGS=""
    if [ -n "${TMDB_API_KEY}" ]; then
        TMDB_API_KEY_ARGS="--tmdb-api-key ${TMDB_API_KEY}"
    fi
    
    OMDB_API_KEY_ARGS=""
    if [ -n "${OMDB_API_KEY}" ]; then
        OMDB_API_KEY_ARGS="--omdb-api-key ${OMDB_API_KEY}"
    fi
    
    python perlentaucher.py \
        --download-dir "${DOWNLOAD_DIR}" \
        --limit "${LIMIT}" \
        --loglevel "${LOGLEVEL}" \
        --sprache "${SPRACHE}" \
        --audiodeskription "${AUDIODESKRIPTION}" \
        --state-file "${STATE_FILE}" \
        ${NOTIFY_ARGS} \
        ${TMDB_API_KEY_ARGS} \
        ${OMDB_API_KEY_ARGS}
    
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

