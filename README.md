# Perlentaucher

![Logo](assets/perlerntaucher_1024.png)

Ein Python-Script, das automatisch Film-Empfehlungen vom RSS-Feed [Mediathekperlen](https://nexxtpress.de/author/mediathekperlen/) parst, bei [MediathekViewWeb](https://mediathekviewweb.de) sucht und die beste Qualität herunterlädt.

## Features

- Parst den RSS Feed nach neuen Filmeinträgen.
- Sucht automatisch nach dem Filmtitel.
- Lädt die beste Fassung basierend auf deinen Präferenzen herunter.
- Priorisierung nach Sprache (Deutsch/Englisch).
- Priorisierung nach Audiodeskription (mit/ohne).
- Speichert bereits verarbeitete Blog-Beiträge - verhindert doppelte Downloads.
- Optionale Benachrichtigungen via Apprise (Email, Discord, Telegram, Slack, etc.).
- Jellyfin/Plex-kompatible Dateinamen mit Jahr und Metadata Provider IDs (TMDB/OMDB).
- Optionale Metadata Provider-Integration (TMDB/OMDB) für bessere Film-Erkennung.
- Konfigurierbarer Download-Ordner.
- Logging.
- Automatische Tests mit CI/CD-Pipeline (Codeberg Actions/Woodpecker CI).

## Programmablauf

Das folgende Diagramm zeigt den vollständigen Ablauf des Scripts:

```mermaid
flowchart TD
    Start([Script Start]) --> ParseArgs[Argumente parsen<br/>--download-dir, --limit, --sprache, etc.]
    ParseArgs --> SetupLog[Logging einrichten]
    SetupLog --> CheckDir{Download-<br/>Verzeichnis<br/>vorhanden?}
    CheckDir -->|Nein| CreateDir[Verzeichnis erstellen]
    CheckDir -->|Ja| LoadState
    CreateDir --> LoadState[State-Datei laden<br/>bereits verarbeitete Einträge]
    LoadState --> ParseRSS[RSS-Feed parsen<br/>Mediathekperlen]
    ParseRSS --> FilterNew{Neue<br/>Einträge<br/>vorhanden?}
    FilterNew -->|Nein| End([Ende])
    FilterNew -->|Ja| ExtractTitle[Filmtitel extrahieren<br/>Jahr extrahieren]
    ExtractTitle --> CheckProcessed{Bereits<br/>verarbeitet?}
    CheckProcessed -->|Ja| Skip[Überspringen]
    Skip --> NextEntry{Weitere<br/>Einträge?}
    CheckProcessed -->|Nein| SearchMVW[Suche in MediathekViewWeb<br/>mit API]
    SearchMVW --> Results{Ergebnisse<br/>gefunden?}
    Results -->|Nein| NotifyNotFound[Benachrichtigung:<br/>Film nicht gefunden]
    NotifyNotFound --> MarkProcessed1[Als verarbeitet markieren]
    MarkProcessed1 --> NextEntry
    Results -->|Ja| ScoreResults[Bewerte alle Ergebnisse<br/>Sprache + Audiodeskription + Größe]
    ScoreResults --> SelectBest[Wähle beste Übereinstimmung<br/>höchste Punktzahl]
    SelectBest --> GetMetadata{Metadata Provider<br/>konfiguriert?}
    GetMetadata -->|TMDB vorhanden| QueryTMDB[TMDB API abfragen<br/>Jahr + tmdb_id]
    GetMetadata -->|OMDB vorhanden| QueryOMDB[OMDb API abfragen<br/>Jahr + imdb_id]
    GetMetadata -->|Kein Provider| NoMetadata
    QueryTMDB --> BuildFilename{Build Filename}
    QueryOMDB --> BuildFilename
    NoMetadata[Keine Metadata] --> BuildFilename
    BuildFilename[Dateiname generieren<br/>Name Jahr Provider-ID]
    BuildFilename --> CheckFile{Datei bereits<br/>vorhanden?}
    CheckFile -->|Ja| SkipDownload[Download überspringen]
    SkipDownload --> MarkProcessed2
    CheckFile -->|Nein| Download[Film herunterladen<br/>mit Fortschrittsanzeige]
    Download --> DownloadSuccess{Download<br/>erfolgreich?}
    DownloadSuccess -->|Nein| Cleanup[Partielle Datei löschen]
    Cleanup --> NotifyError[Benachrichtigung:<br/>Download fehlgeschlagen]
    NotifyError --> MarkProcessed2[Als verarbeitet markieren]
    DownloadSuccess -->|Ja| NotifySuccess[Benachrichtigung:<br/>Download erfolgreich]
    NotifySuccess --> MarkProcessed2
    MarkProcessed2 --> NextEntry
    NextEntry -->|Ja| ExtractTitle
    NextEntry -->|Nein| End
    
    style Start fill:#90EE90
    style End fill:#FFB6C1
    style SearchMVW fill:#87CEEB
    style Download fill:#FFD700
    style NotifySuccess fill:#98FB98
    style NotifyError fill:#FFA07A
    style NotifyNotFound fill:#FFA07A
```

**Hauptschritte:**

1. **Initialisierung**: Argumente werden geparst, Logging konfiguriert und das Download-Verzeichnis wird erstellt (falls nicht vorhanden).

2. **RSS-Feed Parsing**: Der RSS-Feed von Mediathekperlen wird gelesen und nach neuen Einträgen durchsucht. Bereits verarbeitete Einträge werden anhand der State-Datei erkannt und übersprungen.

3. **Filmtitel-Extraktion**: Aus jedem RSS-Eintrag wird der Filmtitel (in Anführungszeichen) und das Jahr extrahiert.

4. **MediathekViewWeb Suche**: Für jeden neuen Filmtitel wird die MediathekViewWeb API durchsucht.

5. **Bewertung & Auswahl**: Alle gefundenen Ergebnisse werden basierend auf deinen Präferenzen bewertet:
   - **Sprache** (Deutsch/Englisch/Egal): +1000 Punkte bei Übereinstimmung
   - **Audiodeskription** (Mit/Ohne/Egal): +500 Punkte bei Übereinstimmung
   - **Dateigröße**: Größere Dateien erhalten höhere Punkte (bessere Qualität)

6. **Metadata-Abfrage** (optional): Falls TMDB oder OMDb API-Keys konfiguriert sind, werden zusätzliche Metadaten (Jahr, Provider-ID) abgerufen.

7. **Dateinamen-Generierung**: Der Dateiname wird im Jellyfin/Plex-kompatiblen Format erstellt: `Filmname (Jahr) [tmdbid-123].mp4`

8. **Download**: Der Film wird heruntergeladen. Falls die Datei bereits existiert, wird der Download übersprungen.

9. **Benachrichtigungen** (optional): Bei Erfolg, Fehler oder wenn kein Film gefunden wurde, können Benachrichtigungen via Apprise gesendet werden.

10. **State-Tracking**: Jeder verarbeitete Eintrag wird in der State-Datei gespeichert, um Doppel-Downloads zu vermeiden.

## Installation

1. Installiere Python 3.x.
2. Klone oder lade das Repository herunter. Du kannst auch ein [Release von Codeberg herunterladen](https://codeberg.org/elpatron/Perlentaucher/releases).
3. Erstelle eine virtuelle Umgebung (optional aber empfohlen):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .\.venv\Scripts\activate   # Windows
   ```
4. Installiere die Abhängigkeiten:
   ```bash
   pip install -r requirements.txt
   ```

## Nutzung

```bash
python perlentaucher.py [Optionen]
```

### Argumente

- `--download-dir`: Zielordner für Downloads (Standard: aktuelles Verzeichnis).
- `--limit`: Anzahl der zu prüfenden RSS-Einträge (Standard: 10).
- `--loglevel`: Detailgrad des Logs (Standard: INFO). Optionen: DEBUG, INFO, WARNING, ERROR.
- `--sprache`: Bevorzugte Sprache (Standard: deutsch). Optionen: `deutsch`, `englisch`, `egal`.
- `--audiodeskription`: Bevorzugte Audiodeskription (Standard: egal). Optionen: `mit`, `ohne`, `egal`.
- `--state-file`: Datei zum Speichern des Verarbeitungsstatus (Standard: `.perlentaucher_state.json`).
- `--no-state`: Deaktiviert das Tracking bereits verarbeiteter Einträge.
- `--notify`: Apprise-URL für Benachrichtigungen (optional). Unterstützt viele Dienste wie Email, Discord, Telegram, Slack, etc.
- `--tmdb-api-key`: TMDB API-Key für Metadata-Abfrage (optional). Kann auch über Umgebungsvariable `TMDB_API_KEY` gesetzt werden.
- `--omdb-api-key`: OMDb API-Key für Metadata-Abfrage (optional). Kann auch über Umgebungsvariable `OMDB_API_KEY` gesetzt werden.

### Beispiele

Die letzten 3 Filme suchen und in den Ordner `Filme` herunterladen:
```bash
python perlentaucher.py --download-dir ./Filme --limit 3
```

Nur deutsche Fassungen ohne Audiodeskription bevorzugen:
```bash
python perlentaucher.py --sprache deutsch --audiodeskription ohne
```

Englische Originalfassungen bevorzugen:
```bash
python perlentaucher.py --sprache englisch
```

Mit Benachrichtigungen (z.B. Discord Webhook):
```bash
python perlentaucher.py --notify "discord://webhook_id/webhook_token"
```

Mit Email-Benachrichtigungen:
```bash
python perlentaucher.py --notify "mailto://user:password@smtp.example.com"
```

Mit Metadata Provider-Integration (TMDB):
```bash
python perlentaucher.py --tmdb-api-key "dein_tmdb_api_key"
```

Mit Metadata Provider-Integration (OMDB):
```bash
python perlentaucher.py --omdb-api-key "dein_omdb_api_key"
```

Mit beiden Metadata Providern:
```bash
python perlentaucher.py --tmdb-api-key "dein_tmdb_api_key" --omdb-api-key "dein_omdb_api_key"
```

### Dateinamen-Schema für Jellyfin/Plex

Das Script generiert Dateinamen im Format, das von Jellyfin und Plex automatisch erkannt wird:

- **Mit Jahr und Provider-ID**: `Movie Name (2022) [tmdbid-123456].mp4`
- **Nur mit Jahr**: `Movie Name (2022).mp4`
- **Nur mit Provider-ID**: `Movie Name [imdbid-tt1234567].mp4`
- **Ohne Metadata**: `Movie Name.mp4` (Fallback)

Das Jahr wird automatisch aus dem RSS-Feed-Titel extrahiert. Wenn API-Keys für TMDB oder OMDB angegeben werden, werden zusätzlich Metadata Provider IDs hinzugefügt, um die Film-Erkennung zu verbessern.

**API-Keys beschaffen:**
- **TMDB**: Registriere dich auf [themoviedb.org](https://www.themoviedb.org/) und erstelle einen API-Key unter [Settings > API](https://www.themoviedb.org/settings/api)
- **OMDb**: Registriere dich auf [omdbapi.com](http://www.omdbapi.com/) und erstelle einen API-Key unter [API Key](http://www.omdbapi.com/apikey.aspx)

### Benachrichtigungen

Das Script unterstützt Benachrichtigungen via [Apprise](https://github.com/caronc/apprise), die über viele verschiedene Dienste gesendet werden können:

- **Erfolgreiche Downloads**: Benachrichtigung mit Filmtitel, Dateipfad und Link zum Blog-Eintrag
- **Fehlgeschlagene Downloads**: Benachrichtigung bei Download-Fehlern
- **Nicht gefundene Filme**: Benachrichtigung wenn ein Film nicht in der Mediathek gefunden wurde

<img src="assets/perlentaucher-ntfy.png" alt="Screenshot ntfy-Benachrichtigungen" width="25%">

Unterstützte Dienste (Beispiele):
- Email: `mailto://user:pass@smtp.example.com`
- Discord: `discord://webhook_id/webhook_token`
- Telegram: `tgram://bot_token/chat_id`
- Slack: `slack://token_a/token_b/token_c`
- Pushover: `pover://user_key@token`
- Und viele mehr - siehe [Apprise Dokumentation](https://github.com/caronc/apprise#supported-notifications)

## Docker-Nutzung

Du kannst das Script auch als Docker-Container ausführen, der automatisch in einem konfigurierbaren Intervall läuft.

### Docker-Image erstellen

```bash
docker build -t perlentaucher .
```

Mit Versions-Tag:
```bash
docker build -t perlentaucher:v0.1.3 -t perlentaucher:latest .
```

### Docker-Image aus Codeberg Container Registry verwenden

Du kannst das Image auch direkt aus der Codeberg Container Registry verwenden, ohne es selbst zu bauen:

**Container aus Registry laden und starten:**

Standard-Ausführung (latest Tag):
```bash
docker run -d \
  --name perlentaucher \
  -v /pfad/zu/downloads:/downloads \
  codeberg.org/elpatron/perlentaucher:latest
```

Mit spezifischer Version (z.B. v0.1.3):
```bash
docker run -d \
  --name perlentaucher \
  -v /pfad/zu/downloads:/downloads \
  codeberg.org/elpatron/perlentaucher:v0.1.3
```

**Container manuell aus Registry laden (ohne sofort zu starten):**
```bash
docker pull codeberg.org/elpatron/perlentaucher:latest
# oder mit spezifischer Version:
docker pull codeberg.org/elpatron/perlentaucher:v0.1.3
```

**Verfügbare Tags:**
- `latest` - Immer die neueste Version
- `v0.1.3` - Spezifische Version (siehe [Releases](https://codeberg.org/elpatron/Perlentaucher/releases) für alle verfügbaren Versionen)

**Hinweis:** Wenn du ein privates Repository verwendest oder 2FA aktiviert hast, musst du dich zuerst bei der Codeberg Container Registry anmelden:
```bash
docker login codeberg.org
# Username: dein_benutzername
# Password: dein_personal_access_token (nicht dein Passwort!)
```

Einen Personal Access Token erstellst du unter Codeberg → Settings → Applications → Generate New Token (mit Scopes `read:packages` und `write:packages`).

### Container ausführen

Standard-Ausführung (alle 12 Stunden):
```bash
docker run -d \
  --name perlentaucher \
  -v /pfad/zu/downloads:/downloads \
  perlentaucher
```

Mit angepasstem Intervall (z.B. alle 6 Stunden):
```bash
docker run -d \
  --name perlentaucher \
  -v /pfad/zu/downloads:/downloads \
  -e INTERVAL_HOURS=6 \
  perlentaucher
```

Mit allen Optionen:
```bash
docker run -d \
  --name perlentaucher \
  -v /pfad/zu/downloads:/downloads \
  -e INTERVAL_HOURS=12 \
  -e LIMIT=5 \
  -e SPRACHE=deutsch \
  -e AUDIODESKRIPTION=ohne \
  -e LOGLEVEL=INFO \
  perlentaucher
```

Mit Benachrichtigungen (z.B. Discord):
```bash
docker run -d \
  --name perlentaucher \
  -v /pfad/zu/downloads:/downloads \
  -e NOTIFY="discord://webhook_id/webhook_token" \
  perlentaucher
```

Mit Benachrichtigungen und allen Optionen:
```bash
docker run -d \
  --name perlentaucher \
  -v /pfad/zu/downloads:/downloads \
  -e INTERVAL_HOURS=12 \
  -e LIMIT=5 \
  -e SPRACHE=deutsch \
  -e AUDIODESKRIPTION=ohne \
  -e LOGLEVEL=INFO \
  -e NOTIFY="discord://webhook_id/webhook_token" \
  perlentaucher
```

Mit Metadata Provider-Integration (TMDB):
```bash
docker run -d \
  --name perlentaucher \
  -v /pfad/zu/downloads:/downloads \
  -e TMDB_API_KEY="dein_tmdb_api_key" \
  perlentaucher
```

Mit Metadata Provider-Integration (OMDB):
```bash
docker run -d \
  --name perlentaucher \
  -v /pfad/zu/downloads:/downloads \
  -e OMDB_API_KEY="dein_omdb_api_key" \
  perlentaucher
```

Mit beiden Metadata Providern und allen Optionen:
```bash
docker run -d \
  --name perlentaucher \
  -v /pfad/zu/downloads:/downloads \
  -e INTERVAL_HOURS=12 \
  -e LIMIT=5 \
  -e SPRACHE=deutsch \
  -e AUDIODESKRIPTION=ohne \
  -e LOGLEVEL=INFO \
  -e NOTIFY="discord://webhook_id/webhook_token" \
  -e TMDB_API_KEY="dein_tmdb_api_key" \
  -e OMDB_API_KEY="dein_omdb_api_key" \
  perlentaucher
```

### Umgebungsvariablen

- `INTERVAL_HOURS`: Stunden zwischen den Ausführungen (Standard: 12)
- `DOWNLOAD_DIR`: Download-Verzeichnis im Container (Standard: /downloads)
- `LIMIT`: Anzahl der zu prüfenden RSS-Einträge (Standard: 10)
- `LOGLEVEL`: Log-Level (Standard: INFO)
- `SPRACHE`: Bevorzugte Sprache: `deutsch`, `englisch`, `egal` (Standard: deutsch)
- `AUDIODESKRIPTION`: Bevorzugte Audiodeskription: `mit`, `ohne`, `egal` (Standard: egal)
- `STATE_FILE`: Pfad zur State-Datei (Standard: `{DOWNLOAD_DIR}/.perlentaucher_state.json`)
- `NOTIFY`: Apprise-URL für Benachrichtigungen (optional, z.B. `mailto://user:pass@example.com` oder `discord://webhook_id/webhook_token`)
- `TMDB_API_KEY`: TMDB API-Key für Metadata-Abfrage (optional)
- `OMDB_API_KEY`: OMDb API-Key für Metadata-Abfrage (optional)

**Wichtig:** 
- Verwende `-v` um ein Volume für die Downloads zu mounten, damit die Dateien auch nach dem Container-Stopp erhalten bleiben.
- Die State-Datei (`.perlentaucher_state.json`) wird standardmäßig im Download-Verzeichnis gespeichert und wird automatisch mit dem Volume persistiert. Dadurch werden bereits verarbeitete Blog-Beiträge auch nach einem Container-Neustart nicht erneut heruntergeladen.

## CI/CD

Das Projekt verwendet Codeberg Actions (Forgejo Actions) für automatische Tests. Die Pipeline wird bei jedem Push und Pull Request ausgeführt.

### Aktivierung auf Codeberg

**Wichtig:** Actions müssen für dein Repository aktiviert sein:

1. Gehe zu deinem Repository auf Codeberg
2. Öffne die **Einstellungen** (Settings)
3. Navigiere zu **Units** > **Overview**
4. Aktiviere **Actions** (falls noch nicht aktiviert)

**Runner einrichten:**

Codeberg bietet keine gehosteten Runner. Du musst einen selbstgehosteten Runner einrichten:

1. Lade den [Forgejo Runner](https://codeberg.org/forgejo/runner/releases) herunter
2. Registriere den Runner mit dem Label `self-hosted`:
   ```bash
   ./forgejo-runner register --name myrunner --labels self-hosted
   ```
3. Starte den Runner:
   ```bash
   ./forgejo-runner daemon
   ```

Die Workflow-Datei befindet sich in `.github/workflows/test.yml` und testet das Script mit Python 3.9-3.12.

**Empfohlen: Woodpecker CI**

Da die Einrichtung eines selbstgehosteten Runners aufwendig ist, wird **Woodpecker CI** empfohlen. Eine `.woodpecker.yml` Konfiguration ist bereits vorhanden:

1. Stelle einen Antrag bei [Codeberg Community](https://codeberg.org/Codeberg/Community/issues)
2. Aktiviere dein Repository auf [ci.codeberg.org](https://ci.codeberg.org)

Woodpecker CI ist einfacher zu nutzen und erfordert keine eigene Runner-Einrichtung.

## Lizenz
[MIT](LICENSE)
