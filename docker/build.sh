#!/bin/bash
# Docker Build Script
# Dieses Script muss aus dem Root-Verzeichnis des Projekts ausgeführt werden
# oder mit dem Build-Kontext auf das Root-Verzeichnis zeigen

# Prüfe ob wir im Root-Verzeichnis sind
if [ ! -f "requirements.txt" ] || [ ! -d "src" ]; then
    echo "Fehler: Dieses Script muss aus dem Root-Verzeichnis des Projekts ausgeführt werden."
    echo "Aktuelles Verzeichnis: $(pwd)"
    echo ""
    echo "Verwendung:"
    echo "  cd /pfad/zum/projekt/root"
    echo "  docker build -t perlentaucher:0.1.29 -t perlentaucher:latest -f docker/Dockerfile ."
    echo ""
    echo "Oder wenn du im docker-Verzeichnis bist:"
    echo "  docker build -t perlentaucher:0.1.29 -t perlentaucher:latest -f Dockerfile .."
    exit 1
fi

# Führe den Build aus
docker build -t perlentaucher:0.1.29 -t perlentaucher:latest -f docker/Dockerfile .
