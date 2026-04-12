# Perlentaucher

<p align="center">
  <img src="assets/perlerntaucher_512.png" alt="Perlentaucher Logo" width="256" height="256" />
</p>

[License: MIT](https://opensource.org/licenses/MIT)
[Python 3.9+](https://www.python.org/downloads/)
[Codeberg](https://codeberg.org/elpatron/Perlentaucher)
[CI/CD](https://github.com/elpatron68/perlentaucher/actions)
[Code Coverage](https://codecov.io/gh/elpatron68/perlentaucher)
[Version](https://codeberg.org/elpatron/Perlentaucher/releases)

Ein Python-Script, das automatisch Film-Empfehlungen vom RSS-Feed [Mediathekperlen](https://nexxtpress.de/author/mediathekperlen/) parst, bei [MediathekViewWeb](https://mediathekviewweb.de) sucht und die beste Qualität herunterlädt.

**Nicht nur Mediathekperlen:** Über die **Wishlist** (GUI, Web-UI oder CLI) kannst du **beliebige Titel** eintragen, die in den öffentlichen Mediatheken ([ARD, ZDF, …](https://mediathekviewweb.de)) verfügbar sind — unabhängig vom Blog-Feed. So lassen sich Inhalte gezielt suchen, mit deinen Qualitäts- und Spracheinstellungen herunterladen und sauber benennen/taggen, auch wenn sie nie bei Mediathekperlen vorgestellt wurden.

## Vorwort und Motivation

Dieses Projekt entstand anlässlich des ersten [DI.DAY](https://di.day) #diday am 4. Januar 2026. Hintergrund war der Gedanke, einen kleinen Beitrag zur Unabhängigkeit von Big-Tech-Unternehmen zu leisten. Der *Perlentaucher* soll dir die Entscheidung erleichtern, ob du vielleicht das eine oder andere Streaming-Abo kündigen kannst:

Die [Mediathekperlen](https://nexxtpress.de/author/mediathekperlen/) sind für mich schon lange eine fantastische Quelle sehenswerter TV-Inhalte. Allein die Tatsache, dass ich die Empfehlungen manuell nachrecherchieren, mit [Mediathekview](https://mediathekview.de) herunterladen und anschließend in meine private Mediathek ([Jellyfin](https://github.com/jellyfin/jellyfin)) einpflegen musste, sorgte dafür, dass ich dann doch recht häufig die eine oder andere Perle verpasst hatte.

Beim Frühstück am ersten DI.DAY kam mir dann der Gedanke, zwei gute Dinge miteinander zu verbinden: Ein Script, das das alles automatisch erledigt. Am Nachmittag war dann auch schon die erste funktionierende Version [fertig](https://digitalcourage.social/@elpatron/115836626605941873).

Das ursprüngliche Python-Script `perlentaucher.py` war für einen vollautomatischen Betrieb ohne Benutzerinteraktion ausgelegt. Es sucht nach neuen Blog-Posts und lädt dann direkt aus den Mediateken herunter. Das hat den Nachteil, dass es nicht sehr niedrigschwellig war und einige Technik-Kenntnisse (Python bzw. Docker) erforderte. Inzwischen gibt es auch eine GUI-Version, also eine ausführbare Datei mit grafischer Benutzer-Schnittstelle, siehe [GUI-Dokumentation](docs/gui.md). *Für Einsteiger auf jeden Fall der empfohlene Weg*!

Falls du Fehler findest, irgendetwas nicht funktioniert oder falls du eine Idee für eine neue Funktion hast, kannst du gern ein *Issue* [anlegen](https://codeberg.org/elpatron/Perlentaucher/issues) - oder, falls du keinen Codeberg Accounts hast eine [Mail](mailto:elpatron+perlentaucher@mailbox.org) schreiben. Insbesondere bin ich für Informationen zu *Perlentaucher* auf MacOS denkbar, da ich das nicht selbst testen kann.

## Features

- **GUI-Anwendung** (neu): Moderne PyQt6-basierte grafische Benutzeroberfläche
  - Cross-Platform: Windows, Linux, macOS
  - Einzelnes Executable möglich (via PyInstaller)
  - Alle Einstellungen als UI-Elemente konfigurierbar
  - RSS-Feed-Einträge in scrollbarer Liste mit Checkboxen
  - Selektiver Download von Filmen/Serien
  - **Film per Suchbegriff**: Filmtitel eingeben und direkt in MediathekViewWeb suchen und herunterladen (ohne RSS-Feed); optional **Erscheinungsjahr** zur Eingrenzung der Treffer
  - **Wishlist**: Beliebige Titel (Film/Serie, optional Jahr) in den Mediatheken außerhalb des Blog-Feeds; nach dem Hinzufügen Verfügbarkeitsprüfung und Download-Angebot; bei mehreren möglichen Treffern Auswahl des passenden Formats
  - Progress Bars für aktive Downloads
  - Siehe [GUI-Dokumentation](docs/gui.md) für Details
- **Film per Suchbegriff (CLI)**: Mit `--search "Titel"` einen Film direkt nach Namen suchen und herunterladen – entspricht der Suche auf [MediathekViewWeb](https://mediathekviewweb.de/#query=…). Optional `--year` für besseres Matching. Kein RSS-Feed nötig; `--limit` wird ignoriert.
- **Wishlist (CLI/Docker/Web)**: JSON-basierte Merkliste (`--wishlist-file`, Standard: `.perlentaucher_wishlist.json` im Download-Ordner); `--wishlist-process` sucht und lädt bei Treffer; eigenes **Web-UI** mit `python src/perlentaucher.py --wishlist-web` (Host/Port: `--wishlist-web-host`, `--wishlist-web-port` oder Umgebungsvariablen `WISHLIST_WEB_*`). Mit `--no-wishlist-web` bzw. ohne `WISHLIST_WEB_ENABLED` startet kein Webserver. Siehe Abschnitt [Wishlist](#wishlist) unten.
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
python src/perlentaucher_gui.py
```

Eine ausführliche Anleitung zur GUI findest du in der [GUI-Dokumentation](docs/gui.md).

**Als Executable:**

- Windows: `scripts\build_gui_windows.bat`
- Linux: `./scripts/build_gui_linux.sh`
- macOS: `./scripts/build_gui_macos.sh`

Das Executable befindet sich nach dem Build in `dist/`.

### Kommandozeilen-Interface

```bash
python src/perlentaucher.py [Optionen]
```

### Argumente

- `--download-dir`: Zielordner für Downloads (Standard: aktuelles Verzeichnis).
- `--limit`: Anzahl der zu prüfenden RSS-Einträge (Standard: 10). Wird bei `--search` ignoriert.
- `--search`: Film per Suchbegriff (Titel) herunterladen, z. B. `--search "The Quiet Girl"`. Es wird nur dieser eine Film gesucht und heruntergeladen; der RSS-Feed wird nicht verwendet.
- `--year`: Erscheinungsjahr (optional), sinnvoll zusammen mit `--search`.
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
- `--debug-no-download`: Debug-Modus: lädt nichts herunter, aber Feed, Suche und Match-Ausgabe laufen normal (inkl. Top‑Matches mit Scores im Log).
- **Wishlist**: `--wishlist-file` (Pfad zur JSON-Datei), `--wishlist-add "Titel"` mit optional `--wishlist-year` und `--wishlist-kind` (`movie`/`series`), `--wishlist-remove ID`, `--wishlist-list`, `--wishlist-process` (Suche + Download + Eintrag entfernen bei Erfolg).
- **Wishlist-Web-UI**: `--wishlist-web` startet die Oberfläche (blockiert). `--wishlist-web-host` / `--wishlist-web-port` überschreiben `WISHLIST_WEB_HOST` / `WISHLIST_WEB_PORT`. `--no-wishlist-web` verhindert den Start auch bei gesetztem `WISHLIST_WEB_ENABLED`. Optional: `WISHLIST_WEB_TOKEN` für einfachen Schutz (Bearer oder Query `?token=`).

### Wishlist

Die Wishlist speichert Filme und Serien, die du **noch nicht** in der öffentlichen Mediathek findest. Sobald ein Eintrag dort verfügbar ist, kannst du ihn herunterladen:

Tipp: Du kannst die Wishlist auch dafür benutzen, **bereits vorhandene** Titel aus der Mediathek bequem mit Perlentaucher herunterzuladen. Dabei werden deine bevorzugten Einstellungen (Sprache, Auflösung, Download-Verzeichnis) berücksichtigt. Somit sparst du dir die Suche, den Download, das Umbenennen der Datei und das Tagging.

- **GUI**: Tab „Wishlist“ — Einträge hinzufügen (Titel, Jahr, Typ), „Verarbeiten“ für direkten Download bei Treffer, oder „Auswahl wie Feed herunterladen“ für den gleichen Ablauf wie beim RSS-Feed (inkl. Serien-Dialog). Beim Start prüft die GUI im Hintergrund, ob Einträge auffindbar sind, und zeigt einen Hinweis.
- **CLI**: z. B. `python src/perlentaucher.py --wishlist-add "Mein Film" --wishlist-year 2025 --wishlist-kind movie` und später `--wishlist-process` (oft per Taskplaner/Cron).
- **Docker**: Pro Intervall läuft nach dem RSS-Lauf automatisch `--wishlist-process`. Die **Wishlist-Web-UI** ist standardmäßig aus; zum Aktivieren `WISHLIST_WEB_ENABLED=1` (oder `true`) setzen und den Container-Port nach außen mappen (Standard im Container: `8765`, siehe [Docker-Nutzung](#docker-nutzung) und [Docker-Dokumentation](docs/docker.md)).
- **Eigenständiges Web-UI**: `python -m src.wishlist_web --port 8765` oder über `perlentaucher.py --wishlist-web` (benötigt `fastapi`/`uvicorn` aus `requirements.txt`).

**Wishlist-Web startet nicht bzw. die Eingabeaufforderung kehrt sofort zurück?**

- Start immer aus dem **Projektroot** mit dem **venv-Python**, z. B. `python src/perlentaucher.py --wishlist-web` oder `.venv\Scripts\python.exe src\perlentaucher.py --wishlist-web`. Unter Windows führt `.\src\perlentaucher.py` oft über den Launcher `py.exe` — der kann eine andere Installation ohne installierte Abhängigkeiten nutzen.
- **Port 8765 belegt** (z. B. noch laufende alte Instanz): anderen Port setzen, z. B. `--wishlist-web-port 8766`, oder den blockierenden Prozess beenden. Perlentaucher meldet das beim Start auf der Konsole.
- Eine Meldung wie *„wishlist-web is not in the list of known options … Electron/Chromium“* kommt von der **Cursor-/Editor-Umgebung**, nicht von Perlentaucher — den Server im normalen Terminal starten.

### Beispiele

Film per Suchbegriff herunterladen (ohne RSS-Feed):

```bash
python src/perlentaucher.py --search "The Quiet Girl" --download-dir ./Filme
```

Mit Jahr:

```bash
python src/perlentaucher.py --search "The Quiet Girl" --year 2022 --download-dir ./Filme
```

Nur suchen, nicht herunterladen (Debug mit Suchbegriff):

```bash
python src/perlentaucher.py --search "The Quiet Girl" --debug-no-download
```

Die letzten 3 Filme suchen und in den Ordner `Filme` herunterladen:

```bash
python src/perlentaucher.py --download-dir ./Filme --limit 3
```

Nur deutsche Fassungen ohne Audiodeskription bevorzugen:

```bash
python src/perlentaucher.py --sprache deutsch --audiodeskription ohne
```

Englische Originalfassungen bevorzugen:

```bash
python src/perlentaucher.py --sprache englisch
```

Mit Benachrichtigungen (z.B. Discord Webhook):

```bash
python src/perlentaucher.py --notify "discord://webhook_id/webhook_token"
```

Mit Email-Benachrichtigungen:

```bash
python src/perlentaucher.py --notify "mailto://user:password@smtp.example.com"
```

Mit Metadata Provider-Integration (TMDB):

```bash
python src/perlentaucher.py --tmdb-api-key "dein_tmdb_api_key"
```

Mit Metadata Provider-Integration (OMDB):

```bash
python src/perlentaucher.py --omdb-api-key "dein_omdb_api_key"
```

Mit beiden Metadata Providern:

```bash
python src/perlentaucher.py --tmdb-api-key "dein_tmdb_api_key" --omdb-api-key "dein_omdb_api_key"
```

Serien-Downloads (nur erste Episode):

```bash
python src/perlentaucher.py --serien-download erste --serien-dir ./Serien
```

Serien-Downloads (gesamte Staffel):

```bash
python src/perlentaucher.py --serien-download staffel --serien-dir ./Serien
```

Serien überspringen:

```bash
python src/perlentaucher.py --serien-download keine
```

Debug-Modus (kein Download, nur Feed/Suche/Matches):

```bash
python src/perlentaucher.py --debug-no-download
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



Unterstützte Dienste (Beispiele):

- Email: `mailto://user:pass@smtp.example.com`
- Discord: `discord://webhook_id/webhook_token`
- Telegram: `tgram://bot_token/chat_id`
- Slack: `slack://token_a/token_b/token_c`
- Pushover: `pover://user_key@token`
- Und viele mehr - siehe [Apprise Dokumentation](https://github.com/caronc/apprise#supported-notifications)

## Docker-Nutzung

Eine detaillierte Anleitung zur Docker-Nutzung findest du in der [Docker-Dokumentation](docs/docker.md).

**Wishlist-Web-UI aktivieren:** Umgebungsvariable `WISHLIST_WEB_ENABLED=1` setzen und den Port der Web-Oberfläche veröffentlichen (Standard im Container: **8765**):

```bash
docker run -d \
  --name perlentaucher \
  -v /pfad/zu/downloads:/downloads \
  -e WISHLIST_WEB_ENABLED=1 \
  -p 8765:8765 \
  codeberg.org/elpatron/perlentaucher:latest
```

Anschließend z. B. `http://localhost:8765` aufrufen. Optional: `WISHLIST_WEB_PORT`, `WISHLIST_WEB_HOST`, `WISHLIST_WEB_TOKEN` und `WISHLIST_FILE` — siehe Umgebungsvariablen in der [Docker-Dokumentation](docs/docker.md). Der mitgelieferte Entrypoint startet die Web-UI nur einmal im Hintergrund und setzt für RSS- und Wishlist-Process-Läufe `--no-wishlist-web`, damit kein zweiter Server denselben Port belegt.

## CI/CD

Informationen zur CI/CD-Pipeline und deren Einrichtung findest du in der [CI/CD-Dokumentation](docs/cicd.md).

## Lizenz

[MIT](LICENSE)