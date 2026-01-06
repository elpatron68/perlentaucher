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
