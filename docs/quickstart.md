# Quickstart-Anleitung

Diese Anleitung hilft dir dabei, Perlentaucher schnell und einfach einzurichten.

## Übersicht

Die Quickstart-Scripts führen dich interaktiv durch die Installation und Konfiguration von Perlentaucher. Sie:

- Prüfen Python und pip Installation
- Installieren automatisch alle benötigten Dependencies
- Erstellen optional eine virtuelle Umgebung
- Fragen alle Konfigurationsparameter interaktiv ab
- Speichern die Konfiguration in einer JSON-Datei
- Erstellen ein Wrapper-Script zum einfachen Starten

## Plattform-spezifische Anleitungen

### Linux

1. Öffne ein Terminal im Projekt-Verzeichnis
2. Führe das Quickstart-Script aus:
   ```bash
   ./scripts/quickstart.sh
   ```
3. Folge den Anweisungen auf dem Bildschirm

**Voraussetzungen:**
- Python 3.7+ (wird beim Start geprüft)
- pip (wird automatisch installiert falls möglich)

**Installation von Python (falls nicht vorhanden):**

- **Debian/Ubuntu:**
  ```bash
  sudo apt-get update
  sudo apt-get install python3 python3-pip python3-venv
  ```

- **RHEL/CentOS:**
  ```bash
  sudo yum install python3 python3-pip
  ```

- **Fedora:**
  ```bash
  sudo dnf install python3 python3-pip
  ```

- **Arch Linux:**
  ```bash
  sudo pacman -S python python-pip
  ```

### macOS

1. Öffne Terminal im Projekt-Verzeichnis
2. Führe das macOS-Quickstart-Script aus:
   ```bash
   ./scripts/quickstart-macos.sh
   ```
3. Folge den Anweisungen auf dem Bildschirm

**Voraussetzungen:**
- Python 3.7+ (wird beim Start geprüft)
- pip (wird automatisch installiert falls möglich)

**Installation von Python (falls nicht vorhanden):**

**Option 1: Homebrew (empfohlen)**
```bash
# Installiere Homebrew falls nicht vorhanden
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Installiere Python
brew install python3
```

**Option 2: Python.org**
1. Besuche https://www.python.org/downloads/
2. Lade die neueste Python 3.x Version herunter
3. Folge dem Installer

### Windows

1. Öffne PowerShell im Projekt-Verzeichnis
2. Führe das Quickstart-Script aus:
   ```powershell
   .\scripts\quickstart.ps1
   ```
3. Folge den Anweisungen auf dem Bildschirm

**Hinweis:** Falls die Ausführung von Scripts blockiert ist, führe zuerst aus:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Voraussetzungen:**
- Python 3.7+ (wird beim Start geprüft)
- pip (wird automatisch installiert falls möglich)

**Installation von Python (falls nicht vorhanden):**

**Option 1: Microsoft Store (empfohlen)**
1. Öffne Microsoft Store
2. Suche nach "Python 3.11" oder neuer
3. Installiere Python

**Option 2: Python.org**
1. Besuche https://www.python.org/downloads/
2. Lade die neueste Python 3.x Version herunter
3. **Wichtig:** Aktiviere "Add Python to PATH" während der Installation!

**Option 3: Winget (Windows Package Manager)**
```powershell
winget install Python.Python.3.11
```

## Interaktive Konfiguration

Das Quickstart-Script fragt dich nach folgenden Parametern:

### Download-Verzeichnis
- Standard: `./downloads`
- Ordner, in dem die heruntergeladenen Filme gespeichert werden

### Anzahl zu prüfender RSS-Einträge
- Standard: `10`
- Wie viele der neuesten RSS-Einträge geprüft werden sollen

### Log-Level
- Optionen: DEBUG, INFO, WARNING, ERROR
- Standard: INFO
- Bestimmt die Detailliertheit der Log-Ausgabe

### Bevorzugte Sprache
- Optionen: deutsch, englisch, egal
- Standard: deutsch
- Welche Sprachfassung bevorzugt wird

### Bevorzugte Audiodeskription
- Optionen: mit, ohne, egal
- Standard: egal
- Ob Filme mit Audiodeskription bevorzugt werden

### State-Datei
- Standard: `.perlentaucher_state.json`
- Speichert bereits verarbeitete Einträge

### State-Tracking
- Standard: aktiviert
- Verhindert doppelte Downloads

### Benachrichtigungen (optional)
- Apprise-URL für Benachrichtigungen
- Beispiele:
  - Discord: `discord://webhook_id/webhook_token`
  - Email: `mailto://user:pass@smtp.example.com`
  - Telegram: `tgram://bot_token/chat_id`
  - ntfy: `ntfy://topic_name`
- Siehe [Apprise Dokumentation](https://github.com/caronc/apprise#supported-notifications) für alle Optionen

### TMDB API-Key (optional)
- API-Key für The Movie Database
- Verbessert die Film-Erkennung
- Registrierung: https://www.themoviedb.org/settings/api

### OMDb API-Key (optional)
- API-Key für OMDb
- Alternative Metadata-Provider
- Registrierung: http://www.omdbapi.com/apikey.aspx

## Konfigurationsdatei

Die Konfiguration wird in `.perlentaucher_config.json` gespeichert:

```json
{
  "download_dir": "./downloads",
  "limit": 10,
  "loglevel": "INFO",
  "sprache": "deutsch",
  "audiodeskription": "egal",
  "state_file": ".perlentaucher_state.json",
  "no_state": false,
  "notify": "",
  "tmdb_api_key": "",
  "omdb_api_key": ""
}
```

**Sicherheit:**
- Die Datei enthält möglicherweise API-Keys
- Auf Linux/macOS wird sie mit Berechtigung 600 (nur Eigentümer lesbar/schreibbar) erstellt
- Auf Windows ist sie normal gespeichert - achte darauf, sie nicht zu teilen

## Wrapper-Scripts

Nach der Konfiguration erstellt das Quickstart-Script ein Wrapper-Script zum einfachen Starten:

### Linux/macOS
```bash
./run_perlentaucher.sh
```

### Windows
```batch
.\run_perlentaucher.bat
```

Das Wrapper-Script:
- Liest automatisch die Konfiguration
- Aktiviert die virtuelle Umgebung (falls vorhanden)
- Startet Perlentaucher mit allen gespeicherten Parametern

## Manuelle Nutzung

Du kannst Perlentaucher auch manuell mit allen Optionen aufrufen:

```bash
python perlentaucher.py --download-dir ./downloads --limit 10 --sprache deutsch
```

Siehe [README.md](../README.md) für alle verfügbaren Optionen.

## Troubleshooting

### Python wird nicht gefunden

**Linux:**
- Stelle sicher, dass Python 3 installiert ist: `python3 --version`
- Falls nicht, installiere es über deinen Package Manager (siehe oben)

**macOS:**
- Prüfe mit `python3 --version`
- Installiere über Homebrew oder python.org (siehe oben)

**Windows:**
- Prüfe mit `python --version`
- Stelle sicher, dass Python im PATH ist
- Neuinstallation mit "Add Python to PATH" Option

### pip wird nicht gefunden

- pip sollte automatisch mit Python installiert werden
- Falls nicht, installiere es manuell:
  ```bash
  python3 -m ensurepip --upgrade  # Linux/macOS
  python -m ensurepip --upgrade   # Windows
  ```

### Virtuelle Umgebung wird nicht aktiviert

**Linux/macOS:**
```bash
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```batch
.venv\Scripts\activate.bat
```

### Wrapper-Script funktioniert nicht

- Stelle sicher, dass `.perlentaucher_config.json` existiert
- Führe das Quickstart-Script erneut aus
- Prüfe die Berechtigungen (Linux/macOS): `chmod +x run_perlentaucher.sh`

### Config-Datei wird nicht gefunden

- Die Config-Datei muss im Projekt-Root-Verzeichnis liegen
- Führe das Quickstart-Script erneut aus, um sie zu erstellen

### Abhängigkeiten können nicht installiert werden

- Stelle sicher, dass du Internet-Verbindung hast
- Prüfe ob pip aktuell ist: `pip install --upgrade pip`
- Versuche manuell: `pip install -r requirements.txt`

