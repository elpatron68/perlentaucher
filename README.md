# Perlentaucher

![Logo](assets/perlerntaucher_512.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Codeberg](https://img.shields.io/badge/Codeberg-Codeberg-blue?logo=codeberg)](https://codeberg.org/elpatron/Perlentaucher)
[![Build Status](https://img.shields.io/github/actions/workflow/status/elpatron68/perlentaucher/build-gui.yml?branch=master&logo=github)](https://github.com/elpatron68/perlentaucher/actions)
[![Codecov](https://img.shields.io/codecov/c/github/elpatron68/perlentaucher?logo=codecov)](https://codecov.io/gh/elpatron68/perlentaucher)
[![Version](https://img.shields.io/badge/version-0.1.27-blue)](https://codeberg.org/elpatron/Perlentaucher/releases)

Ein Python-Script, das automatisch Film-Empfehlungen vom RSS-Feed [Mediathekperlen](https://nexxtpress.de/author/mediathekperlen/) parst, bei [MediathekViewWeb](https://mediathekviewweb.de) sucht und die beste Qualität herunterlädt.

## Features

- **GUI-Anwendung** (neu): Moderne PyQt6-basierte grafische Benutzeroberfläche
  - Cross-Platform: Windows, Linux, macOS
  - Einzelnes Executable möglich (via PyInstaller)
  - Alle Einstellungen als UI-Elemente konfigurierbar
  - RSS-Feed-Einträge in scrollbarer Liste mit Checkboxen
  - Selektiver Download von Filmen/Serien
  - Progress Bars für aktive Downloads
  - Siehe [GUI-Dokumentation](docs/gui.md) für Details
- Parst den RSS Feed der Mediathekperlen nach neuen Filmeinträgen.
- Sucht automatisch nach dem Filmtitel oder Serientitel.
- Lädt die beste Fassung basierend auf deinen Präferenzen herunter.
- **Serien-Unterstützung**: Automatische Erkennung und Download von TV-Serien
  - Optionen: Nur erste Episode, gesamte Staffel oder Serien überspringen
  - Konfigurierbarer Basis-Pfad für Serien-Downloads
  - Episoden werden in Unterordnern `[Titel] (Jahr)/` gespeichert
  - Dateinamen im Format: `[Titel] (Jahr) - S01E01 [provider_id].ext`
- Priorisierung nach Sprache (Deutsch/Englisch).
- Priorisierung nach Audiodeskription (mit/ohne).
- Speichert bereits verarbeitete Blog-Beiträge - verhindert doppelte Downloads.
- Optionale Benachrichtigungen via Apprise (Email, Discord, Telegram, Slack, etc.).
- Jellyfin/Plex-kompatible Dateinamen mit Jahr und Metadata Provider IDs (TMDB/OMDB).
- Optionale Metadata Provider-Integration (TMDB/OMDB) für bessere Film- und Serien-Erkennung.
- Konfigurierbarer Download-Ordner.
- Logging.
- Automatische Tests mit CI/CD-Pipeline (Codeberg Actions/Woodpecker CI).

## Programmablauf

Eine detaillierte grafische Darstellung des Programmablaufs findest du in der [Dokumentation](docs/programmablauf.md).

## Installation

### Schnellstart (empfohlen für Anfänger)

Die einfachste Methode ist die Nutzung der Quickstart-Scripts, die dich interaktiv durch die Installation und Konfiguration führen:

- **Linux:** `./scripts/quickstart.sh`
- **macOS:** `./scripts/quickstart-macos.sh`
- **Windows:** `.\scripts\quickstart.ps1`

Eine ausführliche Anleitung findest du in der [Quickstart-Dokumentation](docs/quickstart.md).

### Manuelle Installation

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

### GUI-Anwendung

Die einfachste Methode ist die grafische Benutzeroberfläche:

```bash
# GUI-Abhängigkeiten installieren
pip install -r requirements-gui.txt

# GUI starten
python perlentaucher_gui.py
```

Eine ausführliche Anleitung zur GUI findest du in der [GUI-Dokumentation](docs/gui.md).

**Als Executable:**
- Windows: `scripts\build_gui_windows.bat`
- Linux: `./scripts/build_gui_linux.sh`
- macOS: `./scripts/build_gui_macos.sh`

Das Executable befindet sich nach dem Build in `dist/`.

### Kommandozeilen-Interface

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
- `--serien-download`: Download-Verhalten für Serien (Standard: `erste`). Optionen: `erste` (nur erste Episode), `staffel` (gesamte Staffel), `keine` (Serien überspringen).
- `--serien-dir`: Basis-Verzeichnis für Serien-Downloads (Standard: `--download-dir`). Episoden werden in Unterordnern `[Titel] (Jahr)/` gespeichert.

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

Serien-Downloads (nur erste Episode):
```bash
python perlentaucher.py --serien-download erste --serien-dir ./Serien
```

Serien-Downloads (gesamte Staffel):
```bash
python perlentaucher.py --serien-download staffel --serien-dir ./Serien
```

Serien überspringen:
```bash
python perlentaucher.py --serien-download keine
```

### Dateinamen-Schema für Jellyfin/Plex

Das Script generiert Dateinamen im Format, das von Jellyfin und Plex automatisch erkannt wird:

**Filme:**
- **Mit Jahr und Provider-ID**: `Movie Name (2022) [tmdbid-123456].mp4`
- **Nur mit Jahr**: `Movie Name (2022).mp4`
- **Nur mit Provider-ID**: `Movie Name [imdbid-tt1234567].mp4`
- **Ohne Metadata**: `Movie Name.mp4` (Fallback)

**Serien:**
- **Mit Episode-Info**: `[serien-dir]/[Titel] (Jahr)/[Titel] (Jahr) - S01E01 [tmdbid-123456].mp4`
- **Beispiel**: `./Serien/Twin Peaks (1992)/Twin Peaks (1992) - S01E01 [tmdbid-1923].mp4`

Das Jahr wird automatisch aus dem RSS-Feed-Titel extrahiert. Wenn API-Keys für TMDB oder OMDB angegeben werden, werden zusätzlich Metadata Provider IDs hinzugefügt, um die Film- und Serien-Erkennung zu verbessern.

**Serien-Erkennung:**
- Automatische Erkennung über RSS-Feed-Kategorie "TV-Serien"
- Zusätzliche Prüfung über TMDB/OMDB Provider-IDs (wenn API-Keys vorhanden)
- Titel-Muster-Erkennung als Fallback

**API-Keys beschaffen:**
- **TMDB**: Registriere dich auf [themoviedb.org](https://www.themoviedb.org/) und erstelle einen API-Key unter [Settings > API](https://www.themoviedb.org/settings/api)
- **OMDb**: Registriere dich auf [omdbapi.com](http://www.omdbapi.com/) und erstelle einen API-Key unter [API Key](http://www.omdbapi.com/apikey.aspx)

### Benachrichtigungen

Das Script unterstützt Benachrichtigungen via [Apprise](https://github.com/caronc/apprise), die über viele verschiedene Dienste gesendet werden können:

- **Erfolgreiche Downloads**: Benachrichtigung mit Filmtitel/Serientitel, Dateipfad und Link zum Blog-Eintrag
- **Fehlgeschlagene Downloads**: Benachrichtigung bei Download-Fehlern
- **Nicht gefundene Filme/Serien**: Benachrichtigung wenn ein Film oder eine Serie nicht in der Mediathek gefunden wurde
- **Staffel-Downloads**: Benachrichtigung mit Anzahl der heruntergeladenen Episoden und Fortschritt

<img src="assets/perlentaucher-ntfy.png" alt="Screenshot ntfy-Benachrichtigungen" width="25%">

Unterstützte Dienste (Beispiele):
- Email: `mailto://user:pass@smtp.example.com`
- Discord: `discord://webhook_id/webhook_token`
- Telegram: `tgram://bot_token/chat_id`
- Slack: `slack://token_a/token_b/token_c`
- Pushover: `pover://user_key@token`
- Und viele mehr - siehe [Apprise Dokumentation](https://github.com/caronc/apprise#supported-notifications)

## Docker-Nutzung

Eine detaillierte Anleitung zur Docker-Nutzung findest du in der [Docker-Dokumentation](docs/docker.md).

## CI/CD

Informationen zur CI/CD-Pipeline und deren Einrichtung findest du in der [CI/CD-Dokumentation](docs/cicd.md).

## Lizenz
[MIT](LICENSE)
