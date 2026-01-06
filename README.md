# Perlentaucher

![Logo](assets/perlerntaucher_512.png)

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

Eine detaillierte grafische Darstellung des Programmablaufs findest du in der [Dokumentation](docs/programmablauf.md).

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

Eine detaillierte Anleitung zur Docker-Nutzung findest du in der [Docker-Dokumentation](docs/docker.md).

## CI/CD

Informationen zur CI/CD-Pipeline und deren Einrichtung findest du in der [CI/CD-Dokumentation](docs/cicd.md).

## Lizenz
[MIT](LICENSE)
