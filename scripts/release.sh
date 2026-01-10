#!/bin/bash
# Script zum Inkrementieren des Patch-Levels, Taggen, Pushen und Docker-Image erstellen/pushen

set -e

# Hole den letzten Tag
last_tag=$(git tag --list --sort=-version:refname | head -n 1)

if [ -z "$last_tag" ]; then
    echo "Kein Tag gefunden. Erstelle initialen Tag v0.1.0"
    new_tag="v0.1.0"
else
    echo "Letzter Tag: $last_tag"
    
    # Extrahiere Version (z.B. v0.1.3 -> 0.1.3)
    if [[ $last_tag =~ ^v?([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
        major="${BASH_REMATCH[1]}"
        minor="${BASH_REMATCH[2]}"
        patch="${BASH_REMATCH[3]}"
        
        # Inkrementiere Patch-Level
        patch=$((patch + 1))
        new_tag="v${major}.${minor}.${patch}"
        
        echo "Neuer Tag: $new_tag"
    else
        echo "Fehler: Tag-Format nicht erkannt: $last_tag"
        echo "Erwartetes Format: vX.Y.Z (z.B. v0.1.3)"
        exit 1
    fi
fi

# Prüfe ob es uncommitted Änderungen gibt
if [ -n "$(git status --porcelain)" ]; then
    echo "Warnung: Es gibt uncommitted Änderungen:"
    git status --short
    read -p "Trotzdem fortfahren? (j/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[JjYy]$ ]]; then
        echo "Abgebrochen."
        exit 1
    fi
fi

# Aktualisiere Version in _version.py
version_number=$(echo "$new_tag" | sed 's/^v//')  # Entferne 'v' Präfix
echo "Aktualisiere Version in _version.py: $version_number"
cat > _version.py <<EOF
# Version wird automatisch vom Release-Script aktualisiert
__version__ = "$version_number"
EOF

# Committe Version-Update
echo "Committe Version-Update..."
git add _version.py
git commit -m "Bump version to $version_number" 2>/dev/null || echo "Version bereits aktuell oder kein Commit notwendig"

# Erstelle neuen Tag
echo ""
echo "Erstelle Git-Tag: $new_tag"
git tag -a "$new_tag" -m "Release $new_tag"

# Pushe Tag zu Remote
echo "Pushe Tag zu Remote..."
git push origin "$new_tag"

# Pushe auch master (falls es neue Commits gibt)
echo "Pushe master Branch..."
git push origin master

# Push zu GitHub (falls GitHub Remote vorhanden)
echo ""
echo "Prüfe GitHub Remote..."
if git remote | grep -q "^github$"; then
    echo "GitHub Remote gefunden. Pushe zu GitHub..."
    
    # Pushe Tag zu GitHub
    echo "Pushe Tag zu GitHub: $new_tag"
    if git push github "$new_tag" 2>/dev/null; then
        echo "✓ Tag erfolgreich zu GitHub gepusht"
    else
        echo "⚠ Warnung: Fehler beim Pushen des Tags zu GitHub"
    fi
    
    # Pushe master Branch zu GitHub
    echo "Pushe master Branch zu GitHub..."
    if git push github master 2>/dev/null; then
        echo "✓ master Branch erfolgreich zu GitHub gepusht"
    else
        echo "⚠ Warnung: Fehler beim Pushen des master Branches zu GitHub"
    fi
    
    # Starte GitHub Actions Workflow für GUI Builds
    echo ""
    echo "Starte GitHub Actions Workflow für Cross-Platform GUI Builds..."
    
    # Prüfe ob gh CLI verfügbar ist
    if command -v gh >/dev/null 2>&1; then
        # Prüfe ob authentifiziert
        if gh auth status >/dev/null 2>&1; then
            # Extrahiere GitHub Repository-Informationen
            github_url=$(git remote get-url github)
            if [[ $github_url =~ github\.com[/:]([^/]+)/([^/]+?)(\.git)?$ ]]; then
                github_repo="${BASH_REMATCH[1]}/${BASH_REMATCH[2]%.git}"
                
                echo "Starte Workflow für Repository: $github_repo"
                if gh workflow run build-gui.yml --ref master --repo "$github_repo" 2>/dev/null; then
                    echo "✓ GitHub Actions Workflow erfolgreich gestartet!"
                    
                    # Versuche GitHub Release zu erstellen (triggert Workflow mit release event)
                    echo ""
                    echo "Erstelle GitHub Release für automatischen Asset-Upload..."
                    release_notes_file="RELEASE_NOTES_${version_number}.md"
                    github_release_body=""
                    
                    if [ -f "$release_notes_file" ]; then
                        github_release_body=$(cat "$release_notes_file")
                    else
                        github_release_body="Release $new_tag

Siehe [Changelog](https://codeberg.org/$repo_owner/$repo_name/commits/$new_tag) für Details."
                    fi
                    
                    # Erstelle GitHub Release
                    if gh release create "$new_tag" --repo "$github_repo" --title "Release $new_tag" --notes "$github_release_body" --target master 2>/dev/null; then
                        echo "✓ GitHub Release erfolgreich erstellt!"
                        echo "  Build-Artefakte werden automatisch hochgeladen, wenn Builds abgeschlossen sind."
                        echo "  Artefakte werden auch automatisch zu Codeberg hochgeladen (falls CODEBERG_TOKEN konfiguriert)."
                    else
                        # Prüfe ob Release bereits existiert
                        if gh release view "$new_tag" --repo "$github_repo" >/dev/null 2>&1; then
                            echo "ℹ GitHub Release für Tag $new_tag existiert bereits."
                        else
                            echo "⚠ Warnung: GitHub Release konnte nicht erstellt werden"
                            echo "  Du kannst es manuell erstellen: gh release create $new_tag --repo $github_repo"
                            echo "  Oder auf GitHub.com: https://github.com/$github_repo/releases/new"
                        fi
                    fi
                    
                    # Warte kurz und hole Workflow-Run Status
                    sleep 5
                    latest_run=$(gh run list --workflow build-gui.yml --repo "$github_repo" --limit 1 --json databaseId,status,url,createdAt 2>/dev/null)
                    
                    if [ -n "$latest_run" ]; then
                        run_id=$(echo "$latest_run" | grep -o '"databaseId":[0-9]*' | head -1 | cut -d':' -f2)
                        run_status=$(echo "$latest_run" | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)
                        run_url=$(echo "$latest_run" | grep -o '"url":"[^"]*"' | head -1 | cut -d'"' -f4)
                        
                        if [ -n "$run_id" ]; then
                            echo ""
                            echo "Workflow-Status:"
                            echo "  Run ID: $run_id"
                            echo "  Status: $run_status"
                            if [ -n "$run_url" ]; then
                                echo "  URL: $run_url"
                            fi
                            echo ""
                            echo "Verfolge Build-Status mit:"
                            echo "  gh run watch $run_id --repo $github_repo"
                            if [ -n "$run_url" ]; then
                                echo "  Oder öffne: $run_url"
                            fi
                        fi
                    fi
                else
                    echo "⚠ Warnung: Workflow konnte nicht gestartet werden"
                    echo "  Versuche manuell: gh workflow run build-gui.yml --ref master --repo $github_repo"
                    echo "  Oder erstelle GitHub Release manuell: gh release create $new_tag --repo $github_repo"
                fi
            else
                echo "⚠ Warnung: Konnte GitHub Repository-Informationen nicht extrahieren"
                echo "  Remote URL: $github_url"
            fi
        else
            echo "⚠ Warnung: GitHub CLI nicht authentifiziert"
            echo "  Bitte authentifiziere dich mit: gh auth login"
        fi
    else
        echo "⚠ Warnung: GitHub CLI (gh) nicht verfügbar"
        echo "  Installiere GitHub CLI oder starte Workflow manuell auf GitHub.com"
    fi
else
    echo "ℹ GitHub Remote nicht gefunden. Überspringe GitHub Push und Workflow-Start."
    echo "  Füge GitHub Remote hinzu mit: git remote add github https://github.com/USERNAME/REPO.git"
fi

# Erstelle Release über Codeberg API
echo ""
echo "Erstelle Release über Codeberg API..."

# Extrahiere Repository-Informationen aus Git-Remote
remote_url=$(git remote get-url origin)
if [[ $remote_url =~ codeberg\.org[/:]([^/]+)/([^/]+?)(\.git)?$ ]]; then
    repo_owner="${BASH_REMATCH[1]}"
    repo_name="${BASH_REMATCH[2]}"
    repo_name="${repo_name%.git}"  # Entferne .git falls vorhanden
    
    echo "Repository: $repo_owner/$repo_name"
    
    # Hole Codeberg API Token (aus .env Datei, Umgebungsvariable oder interaktiv)
    codeberg_token=""
    
    # Versuche .env Datei im Scripts-Ordner zu lesen
    script_dir="$(cd "$(dirname "$0")" && pwd)"
    env_file="$script_dir/.env"
    if [ -f "$env_file" ]; then
        echo "Lese .env Datei: $env_file"
        # Lese CODEBERG_TOKEN aus .env (ignoriere Kommentare und Leerzeilen)
        # macOS-kompatibel: verwende awk statt mehrfache sed-Befehle
        codeberg_token=$(grep -E '^\s*CODEBERG_TOKEN\s*=' "$env_file" | head -1 | awk -F'=' '{print $2}' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//' | sed 's/^["'\'']//' | sed 's/["'\'']$//' | sed 's/#.*$//' | sed 's/[[:space:]]*$//')
        if [ -n "$codeberg_token" ]; then
            echo "Token aus .env Datei geladen"
        fi
    fi
    
    # Fallback auf Umgebungsvariable
    if [ -z "$codeberg_token" ]; then
        codeberg_token="${CODEBERG_TOKEN:-}"
    fi
    
    # Fallback auf interaktive Eingabe
    if [ -z "$codeberg_token" ]; then
        echo "Codeberg API Token nicht gefunden."
        echo "Hinweis: Erstelle einen Personal Access Token unter:"
        echo "  https://codeberg.org/user/settings/applications"
        echo "  Benötigte Scopes: 'public_repo' oder 'repo' (für private Repos)"
        echo "  Oder speichere Token in: $env_file"
        read -p "Codeberg API Token (oder Enter zum Überspringen): " codeberg_token
    fi
    
    if [ -n "$codeberg_token" ]; then
        # Lese Release-Notes aus Datei, falls vorhanden
        release_notes_file="RELEASE_NOTES_${version_number}.md"
        release_body=""
        
        if [ -f "$release_notes_file" ]; then
            echo "Lese Release-Notes aus: $release_notes_file"
            release_body=$(cat "$release_notes_file")
        else
            # Fallback: Standard Release-Notes
            release_body="Release $new_tag

Siehe [Changelog](https://codeberg.org/$repo_owner/$repo_name/commits/$new_tag) für Details."
        fi
        
        # Erstelle Release über Codeberg/Gitea API
        api_url="https://codeberg.org/api/v1/repos/$repo_owner/$repo_name/releases"
        
        # Escape JSON-String für release_body (ohne jq)
        # macOS-kompatibel: verwende tr für Newline-Ersetzung statt sed multiline
        release_body_escaped=$(echo "$release_body" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | tr '\n' '|' | sed 's/|/\\n/g')
        
        # Prüfe ob Release bereits existiert
        check_url="$api_url/tags/$new_tag"
        check_response=$(curl -s -w "\n%{http_code}" -H "Authorization: token $codeberg_token" "$check_url" 2>/dev/null)
        check_http_code=$(echo "$check_response" | tail -n1)
        existing_release=$(echo "$check_response" | head -n-1)
        
        if [ "$check_http_code" = "200" ] && [ -n "$existing_release" ] && [ "$existing_release" != "null" ]; then
            echo "⚠ Release für Tag $new_tag existiert bereits."
            read -p "Release aktualisieren? (j/n) [n]: " update_release
            if [[ $update_release =~ ^[JjYy]$ ]]; then
                # Extrahiere Release-ID aus existing_release
                release_id=$(echo "$existing_release" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
                if [ -n "$release_id" ]; then
                    update_url="$api_url/$release_id"
                    json_data="{\"tag_name\":\"$new_tag\",\"name\":\"Release $new_tag\",\"body\":\"$release_body_escaped\",\"draft\":false,\"prerelease\":false}"
                    response=$(curl -s -w "\n%{http_code}" -X PATCH \
                        -H "Authorization: token $codeberg_token" \
                        -H "Content-Type: application/json" \
                        -d "$json_data" \
                        "$update_url" 2>/dev/null)
                    http_code=$(echo "$response" | tail -n1)
                    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
                        echo "✅ Release erfolgreich aktualisiert!"
                        release_url=$(echo "$response" | head -n-1 | grep -o '"html_url":"[^"]*"' | cut -d'"' -f4)
                        if [ -n "$release_url" ]; then
                            echo "  URL: $release_url"
                        fi
                    else
                        echo "⚠ Fehler beim Aktualisieren des Releases (HTTP $http_code)"
                    fi
                fi
            else
                echo "Release wird nicht aktualisiert."
            fi
        else
            # Erstelle neues Release
            json_data="{\"tag_name\":\"$new_tag\",\"name\":\"Release $new_tag\",\"body\":\"$release_body_escaped\",\"draft\":false,\"prerelease\":false}"
            response=$(curl -s -w "\n%{http_code}" -X POST \
                -H "Authorization: token $codeberg_token" \
                -H "Content-Type: application/json" \
                -d "$json_data" \
                "$api_url" 2>/dev/null)
            http_code=$(echo "$response" | tail -n1)
            if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
                echo "✅ Release erfolgreich erstellt!"
                release_url=$(echo "$response" | head -n-1 | grep -o '"html_url":"[^"]*"' | cut -d'"' -f4)
                if [ -n "$release_url" ]; then
                    echo "  URL: $release_url"
                fi
            else
                echo "⚠ Fehler beim Erstellen des Releases (HTTP $http_code)"
                if [ "$http_code" = "409" ]; then
                    echo "  Release für diesen Tag existiert bereits."
                fi
                echo "  Release kann manuell erstellt werden unter:"
                echo "  https://codeberg.org/$repo_owner/$repo_name/releases/new"
            fi
        fi
    else
        echo "Codeberg API Token nicht angegeben. Release wird übersprungen."
        echo "Release kann manuell erstellt werden unter:"
        echo "  https://codeberg.org/$repo_owner/$repo_name/releases/new"
    fi
else
    echo "⚠ Konnte Repository-Informationen nicht aus Git-Remote extrahieren."
    echo "  Remote URL: $remote_url"
    echo "  Release kann manuell erstellt werden."
fi

# Docker-Image bauen
echo ""
echo "Baue Docker-Image: perlentaucher:$new_tag"
docker build -t "perlentaucher:$new_tag" -t perlentaucher:latest .

# Docker-Image für Codeberg Registry taggen
registry_image="codeberg.org/elpatron/perlentaucher:$new_tag"
registry_latest="codeberg.org/elpatron/perlentaucher:latest"

echo "Tagge Docker-Image für Codeberg Registry..."
docker tag "perlentaucher:$new_tag" "$registry_image"
docker tag "perlentaucher:$new_tag" "$registry_latest"

# Docker-Image zu Codeberg Registry pushen
echo "Pushe Docker-Image zu Codeberg Registry..."
echo "  -> $registry_image"
if ! docker push "$registry_image"; then
    echo "Fehler beim Pushen des Docker-Images ($registry_image)!"
    echo "Hinweis: Stelle sicher, dass du bei Codeberg Registry angemeldet bist:"
    echo "  docker login codeberg.org"
    exit 1
fi

echo "  -> $registry_latest"
if ! docker push "$registry_latest"; then
    echo "Fehler beim Pushen des Docker-Images ($registry_latest)!"
    exit 1
fi

echo ""
echo "✅ Erfolgreich abgeschlossen!"
echo "  Tag: $new_tag"
echo "  Docker-Image: $registry_image"
echo "  Docker-Image (latest): $registry_latest"
