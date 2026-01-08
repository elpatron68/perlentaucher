# Docker-Nutzung

Du kannst das Script auch als Docker-Container ausführen, der automatisch in einem konfigurierbaren Intervall läuft.

## Docker-Image erstellen

```bash
docker build -t perlentaucher .
```

Mit Versions-Tag:
```bash
docker build -t perlentaucher:v0.1.3 -t perlentaucher:latest .
```

## Docker-Image aus Codeberg Container Registry verwenden

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

## Container ausführen

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

Mit Serien-Download-Unterstützung (gesamte Staffel):
```bash
docker run -d \
  --name perlentaucher \
  -v /pfad/zu/downloads:/downloads \
  -v /pfad/zu/serien:/serien \
  -e SERIEN_DOWNLOAD=staffel \
  -e SERIEN_DIR=/serien \
  perlentaucher
```

Mit Serien-Download-Unterstützung (nur erste Episode):
```bash
docker run -d \
  --name perlentaucher \
  -v /pfad/zu/downloads:/downloads \
  -e SERIEN_DOWNLOAD=erste \
  perlentaucher
```

Serien überspringen:
```bash
docker run -d \
  --name perlentaucher \
  -v /pfad/zu/downloads:/downloads \
  -e SERIEN_DOWNLOAD=keine \
  perlentaucher
```

## Umgebungsvariablen

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
- `SERIEN_DOWNLOAD`: Download-Verhalten für Serien (Standard: `erste`). Optionen: `erste` (nur erste Episode), `staffel` (gesamte Staffel), `keine` (Serien überspringen)
- `SERIEN_DIR`: Basis-Verzeichnis für Serien-Downloads im Container (Standard: `DOWNLOAD_DIR`). Episoden werden in Unterordnern `[Titel] (Jahr)/` gespeichert

**Wichtig:** 
- Verwende `-v` um ein Volume für die Downloads zu mounten, damit die Dateien auch nach dem Container-Stopp erhalten bleiben.
- Die State-Datei (`.perlentaucher_state.json`) wird standardmäßig im Download-Verzeichnis gespeichert und wird automatisch mit dem Volume persistiert. Dadurch werden bereits verarbeitete Blog-Beiträge auch nach einem Container-Neustart nicht erneut heruntergeladen.

