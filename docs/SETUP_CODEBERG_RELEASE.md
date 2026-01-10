# Schnellstart: Codeberg Release Integration einrichten

## Was wurde implementiert?

✅ GitHub Actions Workflow lädt Build-Artefakte automatisch zu Codeberg hoch  
✅ Release-Scripts erstellen automatisch GitHub Release (triggert Workflow)  
✅ Vollständige Integration zwischen Codeberg und GitHub Actions  

## Was musst du tun?

### 1. GitHub Secrets konfigurieren (5 Minuten)

Gehe zu: **GitHub Repository → Settings → Secrets and variables → Actions**

> **Wichtig**: Verwende **Repository secrets** (klicke auf "New repository secret"), nicht Environment secrets!

#### Secret 1: CODEBERG_TOKEN (erforderlich)
- **Typ**: Repository Secret
- **Name**: `CODEBERG_TOKEN`
- **Value**: Dein Codeberg Personal Access Token
- **Erstellen**:
  1. Klicke auf **"New repository secret"**
  2. Öffne https://codeberg.org/user/settings/applications
  3. Klicke "Generate New Token"
  4. Scope: `repo` (für private Repos) oder `public_repo` (für öffentliche Repos)
  5. Kopiere den Token und füge ihn als Repository Secret hinzu

#### Secret 2: CODEBERG_REPO_OWNER (optional)
- **Typ**: Repository Secret
- **Name**: `CODEBERG_REPO_OWNER`
- **Value**: `elpatron/perlentaucher` (Standard-Wert, nur nötig wenn abweichend)

### 2. Testen (optional)

Führe ein Test-Release aus:

```bash
# Windows
.\scripts\release.ps1

# Linux/macOS
./scripts/release.sh
```

Das Script wird:
1. ✅ Version aktualisieren
2. ✅ Tag erstellen und zu Codeberg pushen
3. ✅ **Codeberg Release erstellen** (ohne Assets)
4. ✅ Tag zu GitHub pushen
5. ✅ **GitHub Release erstellen** (triggert Workflow)
6. ✅ **GitHub Actions Workflow starten**
7. ✅ Docker Image bauen

Nach ca. 10-20 Minuten:
- ✅ GitHub Release hat Build-Artefakte
- ✅ **Codeberg Release hat automatisch Build-Artefakte** ✨
- ✅ Docker Image auf Codeberg Registry

## Ablauf beim Release

```
Release-Script
    ↓
[1] Erstellt Codeberg Release (ohne Assets)
    ↓
[2] Pusht zu GitHub
    ↓
[3] Erstellt GitHub Release (triggert Workflow)
    ↓
GitHub Actions
    ↓
[4] Baut GUI-Artefakte (Windows, Linux, macOS)
    ↓
[5] Lädt Artefakte zu GitHub Release hoch
    ↓
[6] Lädt Artefakte automatisch zu Codeberg Release hoch ✨
```

## Workflow-Status überwachen

```bash
# Status prüfen
gh run list --workflow build-gui.yml

# Workflow verfolgen
gh run watch <RUN_ID>

# Im Browser öffnen
gh run view <RUN_ID> --web
```

## Troubleshooting

**"Release not found on Codeberg"**
→ Stelle sicher, dass das Release-Script das Release auf Codeberg erstellt hat

**"CODEBERG_TOKEN not found"**
→ Prüfe, ob das Secret `CODEBERG_TOKEN` in GitHub Settings → Secrets gesetzt ist

**Build-Artefakte fehlen auf Codeberg**
→ Prüfe GitHub Actions Logs (Job "Upload Assets to Codeberg")

Siehe [vollständige Dokumentation](docs/codeberg-release-integration.md) für Details.
