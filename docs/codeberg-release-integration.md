# Codeberg Release Integration mit GitHub Actions

Diese Anleitung beschreibt, wie die Build-Artefakte aus der GitHub Actions Pipeline automatisch zu Codeberg Releases hochgeladen werden.

## Funktionsweise

1. **Release-Script** erstellt das Release auf Codeberg (via Codeberg API)
2. **Release-Script** pusht Tag zu GitHub
3. **GitHub Actions** wird durch Tag-Push oder manuelles Release getriggert
4. **GitHub Actions** baut die GUI-Artefakte für Windows, Linux, macOS
5. **GitHub Actions** lädt die Artefakte automatisch zu Codeberg hoch

## Voraussetzungen

### 1. GitHub Secrets konfigurieren

Gehe zu deinem GitHub Repository → **Settings** → **Secrets and variables** → **Actions** und füge folgende **Repository Secrets** hinzu:

> **Wichtig**: Verwende **Repository secrets** (nicht Environment secrets), da der Workflow direkt auf `secrets.CODEBERG_TOKEN` zugreift.

#### CODEBERG_TOKEN (erforderlich)
- **Typ**: Repository Secret (nicht Environment Secret)
- **Name**: `CODEBERG_TOKEN`
- **Value**: Dein Codeberg Personal Access Token
- **Erstellen**:
  1. Klicke auf **"New repository secret"** (nicht "New environment secret")
  2. Gehe zu https://codeberg.org/user/settings/applications
  3. Klicke auf "Generate New Token"
  4. Wähle Scope: `repo` (für private Repos) oder `public_repo` (für öffentliche Repos)
  5. Kopiere den Token und füge ihn als Repository Secret hinzu

#### CODEBERG_REPO_OWNER (optional)
- **Typ**: Repository Secret (nicht Environment Secret)
- **Name**: `CODEBERG_REPO_OWNER`
- **Value**: `elpatron/perlentaucher` (Standard-Wert, wenn nicht gesetzt)
- **Hinweis**: Nur nötig, wenn dein Repository einen anderen Namen/Owner hat

### 2. GitHub Release erstellen

Der GitHub Actions Workflow wird durch ein **GitHub Release** getriggert. Du hast zwei Optionen:

#### Option A: Automatisch (empfohlen)
Das Release-Script erstellt automatisch ein GitHub Release, wenn ein GitHub Remote konfiguriert ist und `gh` CLI verfügbar ist.

#### Option B: Manuell
1. Erstelle ein Release auf GitHub: https://github.com/elpatron68/perlentaucher/releases/new
2. Verwende denselben Tag-Namen wie auf Codeberg (z.B. `v0.1.13`)
3. Die GitHub Actions Pipeline wird automatisch gestartet

## Ablauf beim Release

### Schritt 1: Release-Script ausführen

```bash
# Windows
.\scripts\release.ps1

# Linux/macOS
./scripts/release.sh
```

Das Script:
1. ✅ Aktualisiert Version in `src/_version.py`
2. ✅ Erstellt Git-Tag
3. ✅ Pusht Tag zu Codeberg
4. ✅ **Erstellt Release auf Codeberg** (ohne Assets)
5. ✅ Pusht Tag zu GitHub
6. ✅ **Startet GitHub Actions Workflow**
7. ✅ Baut Docker Image
8. ✅ Pusht Docker Image zu Codeberg Registry

### Schritt 2: GitHub Actions läuft

Die GitHub Actions Pipeline:
1. Baut GUI-Artefakte für Windows, Linux, macOS
2. Lädt Artefakte zu GitHub Release hoch
3. **Lädt Artefakte automatisch zu Codeberg Release hoch**

### Schritt 3: Fertig! ✅

Nach ca. 10-20 Minuten:
- ✅ GitHub Release hat Build-Artefakte
- ✅ Codeberg Release hat Build-Artefakte
- ✅ Docker Image ist auf Codeberg Registry verfügbar

## Troubleshooting

### "Release not found on Codeberg"

**Problem**: GitHub Actions kann das Release auf Codeberg nicht finden.

**Lösung**: 
- Stelle sicher, dass das Release-Script das Release auf Codeberg erstellt hat
- Prüfe, ob der Tag-Name übereinstimmt (z.B. `v0.1.13`)
- Prüfe die Release-Script-Ausgabe auf Fehler

### "CODEBERG_TOKEN not found"

**Problem**: GitHub Actions hat keinen Zugriff auf Codeberg API.

**Lösung**:
- Prüfe, ob das Secret `CODEBERG_TOKEN` in GitHub Repository Settings → Secrets gesetzt ist
- Stelle sicher, dass der Token die Berechtigung `repo` hat

### "Upload failed (HTTP 404)"

**Problem**: Release-ID wurde nicht gefunden.

**Lösung**:
- Prüfe, ob das Release auf Codeberg existiert: https://codeberg.org/elpatron/perlentaucher/releases
- Stelle sicher, dass der Tag-Name exakt übereinstimmt (Groß-/Kleinschreibung beachten)

### Build-Artefakte fehlen auf Codeberg

**Problem**: Artefakte wurden nicht hochgeladen.

**Lösung**:
- Prüfe GitHub Actions Logs: Der Job "Upload Assets to Codeberg" zeigt Details
- Prüfe, ob der Release auf Codeberg existiert
- Prüfe, ob das Secret `CODEBERG_TOKEN` korrekt ist

## Manuelle Schritte (falls automatische Integration fehlschlägt)

Falls die automatische Integration nicht funktioniert, kannst du die Artefakte manuell hochladen:

1. **Lade Artefakte von GitHub herunter**:
   - Gehe zu GitHub Release: https://github.com/elpatron68/perlentaucher/releases
   - Lade alle Build-Artefakte herunter

2. **Lade zu Codeberg hoch**:
   - Gehe zu Codeberg Release: https://codeberg.org/elpatron/perlentaucher/releases
   - Klicke auf "Edit Release"
   - Lade die Artefakte manuell hoch

## Workflow-Status überwachen

Du kannst den Workflow-Status überwachen:

```bash
# Workflow-Status prüfen
gh run list --workflow build-gui.yml

# Workflow-Logs anzeigen
gh run watch <RUN_ID>

# Workflow im Browser öffnen
gh run view <RUN_ID> --web
```

## Weitere Informationen

- [GitHub Actions Workflow](../.github/workflows/build-gui.yml)
- [Release Scripts](../scripts/release.ps1) (Windows) / [release.sh](../scripts/release.sh) (Linux/macOS)
- [GitHub Mirror Setup](github-mirror.md)
