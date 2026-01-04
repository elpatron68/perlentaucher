# Perlentaucher

Ein Python-Script, das automatisch Film-Empfehlungen vom RSS-Feed [Mediathekperlen](https://nexxtpress.de/author/mediathekperlen/feed/) parst, bei [MediathekViewWeb](https://mediathekviewweb.de) sucht und die beste Qualität herunterlädt.

## Features

- Parst den RSS Feed nach neuen Filmeinträgen.
- Sucht automatisch nach dem Filmtitel.
- Lädt die beste Fassung basierend auf Ihren Präferenzen herunter.
- Priorisierung nach Sprache (Deutsch/Englisch).
- Priorisierung nach Audiodeskription (mit/ohne).
- Konfigurierbarer Download-Ordner.
- Logging.

## Installation

1. Python 3.x installieren.
2. Repository klonen oder herunterladen.
3. Virtuelle Umgebung erstellen (optional aber empfohlen):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .\.venv\Scripts\activate   # Windows
   ```
4. Abhängigkeiten installieren:
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

## Docker-Nutzung

Das Script kann auch als Docker-Container ausgeführt werden, der automatisch in einem konfigurierbaren Intervall läuft.

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

### Umgebungsvariablen

- `INTERVAL_HOURS`: Stunden zwischen den Ausführungen (Standard: 12)
- `DOWNLOAD_DIR`: Download-Verzeichnis im Container (Standard: /downloads)
- `LIMIT`: Anzahl der zu prüfenden RSS-Einträge (Standard: 10)
- `LOGLEVEL`: Log-Level (Standard: INFO)
- `SPRACHE`: Bevorzugte Sprache: `deutsch`, `englisch`, `egal` (Standard: deutsch)
- `AUDIODESKRIPTION`: Bevorzugte Audiodeskription: `mit`, `ohne`, `egal` (Standard: egal)

**Wichtig:** Verwenden Sie `-v` um ein Volume für die Downloads zu mounten, damit die Dateien auch nach dem Container-Stopp erhalten bleiben.

## Lizenz
[MIT](LICENSE)
