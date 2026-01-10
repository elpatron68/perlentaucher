# GitHub Mirror für CI/CD

Dieses Projekt nutzt GitHub Actions für Cross-Platform-Builds über ein Mirror-Repository auf GitHub.

## Schnellstart (Empfohlen)

**Einfachste Methode:** Verwende das Setup-Script:

```bash
# Linux/macOS
./scripts/setup-github-mirror.sh

# Windows PowerShell
.\scripts\setup-github-mirror.ps1
```

Das Script führt dich interaktiv durch den gesamten Setup-Prozess.

## Manuelle Einrichtung: GitHub Mirror Repository

### 1. GitHub Repository erstellen

1. Gehe zu [GitHub](https://github.com) und erstelle ein neues Repository
   - **Name**: `perlentaucher` (oder wie dein Codeberg-Repository heißt)
   - **Beschreibung**: "Mirror of codeberg.org/elpatron/perlentaucher for CI/CD"
   - **Sichtbarkeit**: Öffentlich oder Privat (je nach Bedarf)
   - **WICHTIG**: **KEIN** README, .gitignore oder LICENSE hinzufügen (Repository sollte leer sein)

### 2. GitHub Mirror einrichten

Füge GitHub als zusätzliches Remote hinzu:

```bash
# Prüfe aktuelle Remotes
git remote -v

# Füge GitHub als "github" Remote hinzu
git remote add github https://github.com/DEIN_USERNAME/perlentaucher.git

# Oder mit SSH (empfohlen für automatische Synchronisation):
git remote add github git@github.com:DEIN_USERNAME/perlentaucher.git
```

### 3. Initialen Push zu GitHub

```bash
# Pushe alle Branches und Tags zu GitHub
git push github --all
git push github --tags
```

### 4. GitHub Actions Secrets konfigurieren

**Wichtig:** `GITHUB_TOKEN` ist automatisch verfügbar und muss nicht manuell gesetzt werden.

**Optional:** Für private Codeberg-Repositories oder automatische Synchronisation:

#### Codeberg Token (optional)

Falls dein Codeberg-Repository privat ist, benötigst du einen Codeberg Token:

1. Gehe zu [Codeberg Settings > Applications](https://codeberg.org/user/settings/applications)
2. Erstelle einen Personal Access Token mit Scope `repo`
3. Füge diesen als Secret in deinem **GitHub Repository** hinzu:
   - Gehe zu: **GitHub Repository > Settings > Secrets and variables > Actions**
   - Klicke auf **New repository secret**
   - Name: `CODEBERG_TOKEN`
   - Value: Dein Codeberg Personal Access Token

#### Codeberg Repository Owner (optional)

Falls dein Repository-Name auf Codeberg abweicht:

1. Gehe zu: **GitHub Repository > Settings > Secrets and variables > Actions**
2. Klicke auf **New repository secret**
3. Name: `CODEBERG_REPO_OWNER`
4. Value: `DEIN_USERNAME/REPO_NAME` (z.B. `elpatron/perlentaucher`)

**Standard-Wert:** `elpatron/perlentaucher` (wird automatisch verwendet, wenn Secret nicht gesetzt ist)

## Automatische Synchronisation einrichten

### Option A: GitHub Actions Workflow (empfohlen)

Ein Workflow in `.github/workflows/sync-codeberg.yml` synchronisiert automatisch alle Pushes von Codeberg zu GitHub.

**Wichtig**: Dieser Workflow läuft auf GitHub und benötigt:
- `CODEBERG_TOKEN` Secret (GitHub Personal Access Token mit `repo` Scope)

### Option B: Lokales Git-Hook

Füge einen Post-Push-Hook hinzu, um automatisch zu beiden Remotes zu pushen:

```bash
# Erstelle Post-Push-Hook
cat > .git/hooks/post-push << 'EOF'
#!/bin/bash
# Synchronisiere automatisch mit GitHub nach Push zu Codeberg
git push github --all --follow-tags 2>&1 || echo "GitHub push fehlgeschlagen"
EOF

chmod +x .git/hooks/post-push
```

**Oder** verwende einen Git-Alias:

```bash
# Füge Alias hinzu für Push zu beiden Remotes
git config alias.pushall '!git push origin --all && git push github --all && git push origin --tags && git push github --tags'

# Nutzung:
git pushall
```

### Option C: Manuelle Synchronisation

Bei jedem Release oder wichtigen Push:

```bash
# Synchronisiere alle Branches
git push github --all

# Synchronisiere alle Tags
git push github --tags
```

## Workflow-Ablauf

1. **Entwicklung** erfolgt auf Codeberg (dein Haupt-Repository)
2. **Push zu Codeberg** triggert (optional) automatische Synchronisation zu GitHub
3. **GitHub Actions** läuft automatisch bei jedem Push zu GitHub
4. **Build-Artefakte** werden in GitHub Actions als Artifacts gespeichert
5. **Bei Release**: Build-Artefakte werden automatisch zu GitHub Release hinzugefügt

## Releases verwalten

### Automatische Releases auf GitHub

Wenn du ein Release auf Codeberg erstellst:

1. Erstelle den Tag auf Codeberg (z.B. mit `scripts/release.sh`)
2. Synchronisiere Tag zu GitHub: `git push github --tags`
3. Erstelle manuell ein Release auf GitHub mit demselben Tag
4. GitHub Actions erkennt das Release und fügt die Build-Artefakte automatisch hinzu

### Oder: Release nur auf Codeberg

Die Release-Artefakte werden trotzdem in GitHub Actions als Artifacts gespeichert und können manuell heruntergeladen werden.

## Troubleshooting

### "Permission denied" Fehler

- Stelle sicher, dass dein GitHub Personal Access Token die Berechtigung `repo` hat
- Prüfe, ob der Token in GitHub Repository Secrets korrekt gespeichert ist

### Workflows laufen nicht

- Prüfe, ob GitHub Actions in deinem Repository aktiviert ist:
  - Repository Settings > Actions > General > "Allow all actions and reusable workflows"
- Prüfe die Workflow-Logs im GitHub Actions Tab

### Synchronisation fehlgeschlagen

- Prüfe die Remote-Konfiguration: `git remote -v`
- Teste manuellen Push: `git push github master`
- Prüfe GitHub Actions Logs für Sync-Workflow-Fehler

## Vorteile dieser Lösung

✅ **Kein Selbst-Hosting** nötig (im Gegensatz zu Forgejo Runner)  
✅ **Kostenlos** für öffentliche Repositories  
✅ **Automatische Cross-Platform Builds** für Windows, Linux, macOS  
✅ **Release-Assets** werden automatisch erstellt  
✅ **Codeberg bleibt Haupt-Repository** - GitHub nur für CI/CD  
✅ **Keine Abhängigkeit** von externen CI/CD-Diensten  
