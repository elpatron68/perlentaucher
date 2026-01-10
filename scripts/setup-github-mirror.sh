#!/bin/bash
# Setup-Script für GitHub Mirror Repository
# Dieses Script hilft beim Einrichten eines GitHub Mirror für CI/CD

set -e

echo "=========================================="
echo "GitHub Mirror Setup für Perlentaucher"
echo "=========================================="
echo ""

# Prüfe ob Git Repository vorhanden
if [ ! -d .git ]; then
    echo "❌ Fehler: Dies ist kein Git-Repository!"
    exit 1
fi

# Zeige aktuelle Remotes
echo "Aktuelle Git Remotes:"
git remote -v
echo ""

# Frage nach GitHub Repository URL
read -p "GitHub Repository URL (z.B. https://github.com/USERNAME/perlentaucher.git): " GITHUB_URL

if [ -z "$GITHUB_URL" ]; then
    echo "❌ Keine GitHub URL angegeben. Setup abgebrochen."
    exit 1
fi

# Entferne vorhandenen GitHub Remote falls vorhanden
if git remote | grep -q "^github$"; then
    echo "Entferne vorhandenen 'github' Remote..."
    git remote remove github
fi

# Füge GitHub Remote hinzu
echo "Füge GitHub Remote hinzu: $GITHUB_URL"
git remote add github "$GITHUB_URL"

# Prüfe ob Push möglich ist
echo ""
echo "Teste Verbindung zu GitHub..."
if git ls-remote github &>/dev/null; then
    echo "✅ Verbindung zu GitHub erfolgreich!"
else
    echo "⚠️  Warnung: Konnte nicht zu GitHub verbinden. Bitte prüfe die URL und Zugangsdaten."
fi

echo ""
read -p "Möchtest du jetzt alle Branches und Tags zu GitHub pushen? (j/n): " PUSH_NOW

if [ "$PUSH_NOW" = "j" ] || [ "$PUSH_NOW" = "J" ]; then
    echo ""
    echo "Pushe alle Branches zu GitHub..."
    git push github --all || echo "⚠️  Einige Branches konnten nicht gepusht werden"
    
    echo ""
    echo "Pushe alle Tags zu GitHub..."
    git push github --tags || echo "⚠️  Einige Tags konnten nicht gepusht werden"
    
    echo ""
    echo "✅ Push abgeschlossen!"
else
    echo ""
    echo "⏭️  Push übersprungen. Du kannst später manuell pushen mit:"
    echo "   git push github --all"
    echo "   git push github --tags"
fi

echo ""
echo "=========================================="
echo "✅ Setup abgeschlossen!"
echo "=========================================="
echo ""
echo "Nächste Schritte:"
echo "1. Erstelle ein GitHub Personal Access Token unter:"
echo "   https://github.com/settings/tokens"
echo "   Benötigte Berechtigung: 'repo' (vollständiger Zugriff)"
echo ""
echo "2. Füge den Token als Secret in deinem GitHub Repository hinzu:"
echo "   GitHub Repository > Settings > Secrets and variables > Actions"
echo "   Name: GITHUB_TOKEN (wird automatisch verwendet)"
echo ""
echo "3. Optional: Füge CODEBERG_TOKEN hinzu für private Repositories:"
echo "   Erstelle Token unter: https://codeberg.org/user/settings/applications"
echo "   Scope: 'repo'"
echo ""
echo "4. Optional: Füge CODEBERG_REPO_OWNER Secret hinzu, wenn abweichend:"
echo "   Standard-Wert: 'elpatron/perlentaucher'"
echo ""
echo "Die GitHub Actions Workflows sind bereits konfiguriert:"
echo "  - .github/workflows/build-gui.yml (Cross-Platform Builds)"
echo "  - .github/workflows/sync-codeberg.yml (Automatische Synchronisation)"
echo ""
echo "Dokumentation: docs/github-mirror.md"
