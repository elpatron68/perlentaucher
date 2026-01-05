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
- Konfigurierbarer Download-Ordner.
- Logging.
- Automatische Tests mit CI/CD-Pipeline (Codeberg Actions/Woodpecker CI).

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

### Benachrichtigungen

Das Script unterstützt Benachrichtigungen via [Apprise](https://github.com/caronc/apprise), die über viele verschiedene Dienste gesendet werden können:

- **Erfolgreiche Downloads**: Benachrichtigung mit Filmtitel, Dateipfad und Link zum Blog-Eintrag
- **Fehlgeschlagene Downloads**: Benachrichtigung bei Download-Fehlern
- **Nicht gefundene Filme**: Benachrichtigung wenn ein Film nicht in der Mediathek gefunden wurde

<img src="assets/perlentaucher-ntfy.png" alt="Screenshot ntfy-Benachrichtigungen" width="50%">

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

### Umgebungsvariablen

- `INTERVAL_HOURS`: Stunden zwischen den Ausführungen (Standard: 12)
- `DOWNLOAD_DIR`: Download-Verzeichnis im Container (Standard: /downloads)
- `LIMIT`: Anzahl der zu prüfenden RSS-Einträge (Standard: 10)
- `LOGLEVEL`: Log-Level (Standard: INFO)
- `SPRACHE`: Bevorzugte Sprache: `deutsch`, `englisch`, `egal` (Standard: deutsch)
- `AUDIODESKRIPTION`: Bevorzugte Audiodeskription: `mit`, `ohne`, `egal` (Standard: egal)
- `STATE_FILE`: Pfad zur State-Datei (Standard: `{DOWNLOAD_DIR}/.perlentaucher_state.json`)
- `NOTIFY`: Apprise-URL für Benachrichtigungen (optional, z.B. `mailto://user:pass@example.com` oder `discord://webhook_id/webhook_token`)

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
