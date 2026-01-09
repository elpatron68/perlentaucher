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
SERIEN_DOWNLOAD=${SERIEN_DOWNLOAD:-erste}
SERIEN_DIR=${SERIEN_DIR:-${DOWNLOAD_DIR}}
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
echo "Serien-Download: ${SERIEN_DOWNLOAD}"
if [ "${SERIEN_DIR}" != "${DOWNLOAD_DIR}" ]; then
    echo "Serien-Verzeichnis: ${SERIEN_DIR}"
else
    echo "Serien-Verzeichnis: ${DOWNLOAD_DIR} (Standard)"
fi
echo "=========================================="
echo ""

# Erstelle Download-Verzeichnis falls nicht vorhanden
mkdir -p "${DOWNLOAD_DIR}"

# Update-Prüfung beim Start
echo "$(date '+%Y-%m-%d %H:%M:%S') - Prüfe auf Updates..."
if python -c "
import sys
import requests
import semver

try:
    # Lese aktuelle Version aus _version.py
    from _version import __version__
    current_version = __version__
    
    # API-Aufruf zur Codeberg/Gitea API
    response = requests.get(
        'https://codeberg.org/api/v1/repos/elpatron/Perlentaucher/releases/latest',
        timeout=5
    )
    response.raise_for_status()
    data = response.json()
    
    # Extrahiere Version aus tag_name
    latest_tag_raw = data.get('tag_name', '')
    if not latest_tag_raw:
        print('⚠️  Update-Prüfung fehlgeschlagen: Keine Version gefunden')
        sys.exit(0)
    
    # Entferne 'v' Präfix für semver-Vergleich
    latest_tag_clean = latest_tag_raw.lstrip('v')
    current_clean = current_version.lstrip('v')
    
    # Überspringe Prüfung wenn aktuelle Version 'unknown' ist
    if current_clean == 'unknown' or not latest_tag_clean:
        print('⚠️  Update-Prüfung übersprungen: Ungültige Version')
        sys.exit(0)
    
    # Versionsvergleich mit semver
    comparison = semver.compare(current_clean, latest_tag_clean)
    if comparison < 0:
        print('⚠️  Eine neuere Version ist verfügbar: ' + latest_tag_raw + ' (aktuell: v' + current_version + ')')
        print('   Download: https://codeberg.org/elpatron/Perlentaucher/releases/tag/' + latest_tag_raw)
    elif comparison == 0:
        print('✅ Auf dem neuesten Stand: v' + current_version)
    # Wenn comparison > 0, ist die aktuelle Version neuer (z.B. Entwicklung), keine Meldung nötig
except Exception as e:
    # Stillschweigend überspringen bei Fehlern
    pass
" 2>/dev/null; then
    echo ""
else
    echo "⚠️  Update-Prüfung fehlgeschlagen (keine Internetverbindung oder API-Fehler)"
    echo ""
fi

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
    
    SERIEN_DOWNLOAD_ARGS="--serien-download ${SERIEN_DOWNLOAD}"
    SERIEN_DIR_ARGS=""
    if [ "${SERIEN_DIR}" != "${DOWNLOAD_DIR}" ]; then
        SERIEN_DIR_ARGS="--serien-dir ${SERIEN_DIR}"
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
        ${OMDB_API_KEY_ARGS} \
        ${SERIEN_DOWNLOAD_ARGS} \
        ${SERIEN_DIR_ARGS}
    
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

