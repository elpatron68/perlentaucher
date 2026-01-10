# Setup-Script für GitHub Mirror Repository (PowerShell)
# Dieses Script hilft beim Einrichten eines GitHub Mirror für CI/CD

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "GitHub Mirror Setup für Perlentaucher" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Prüfe ob Git Repository vorhanden
if (-not (Test-Path .git)) {
    Write-Host "❌ Fehler: Dies ist kein Git-Repository!" -ForegroundColor Red
    exit 1
}

# Zeige aktuelle Remotes
Write-Host "Aktuelle Git Remotes:" -ForegroundColor Yellow
git remote -v
Write-Host ""

# Frage nach GitHub Repository URL
$githubUrl = Read-Host "GitHub Repository URL (z.B. https://github.com/USERNAME/perlentaucher.git)"

if ([string]::IsNullOrWhiteSpace($githubUrl)) {
    Write-Host "❌ Keine GitHub URL angegeben. Setup abgebrochen." -ForegroundColor Red
    exit 1
}

# Entferne vorhandenen GitHub Remote falls vorhanden
$remotes = git remote
if ($remotes -contains "github") {
    Write-Host "Entferne vorhandenen 'github' Remote..." -ForegroundColor Yellow
    git remote remove github
}

# Füge GitHub Remote hinzu
Write-Host "Füge GitHub Remote hinzu: $githubUrl" -ForegroundColor Green
git remote add github $githubUrl

# Prüfe ob Push möglich ist
Write-Host ""
Write-Host "Teste Verbindung zu GitHub..." -ForegroundColor Yellow
try {
    git ls-remote github | Out-Null
    Write-Host "✅ Verbindung zu GitHub erfolgreich!" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Warnung: Konnte nicht zu GitHub verbinden. Bitte prüfe die URL und Zugangsdaten." -ForegroundColor Yellow
}

Write-Host ""
$pushNow = Read-Host "Möchtest du jetzt alle Branches und Tags zu GitHub pushen? (j/n)"

if ($pushNow -eq "j" -or $pushNow -eq "J") {
    Write-Host ""
    Write-Host "Pushe alle Branches zu GitHub..." -ForegroundColor Yellow
    git push github --all
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  Einige Branches konnten nicht gepusht werden" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Pushe alle Tags zu GitHub..." -ForegroundColor Yellow
    git push github --tags
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  Einige Tags konnten nicht gepusht werden" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "✅ Push abgeschlossen!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "⏭️  Push übersprungen. Du kannst später manuell pushen mit:" -ForegroundColor Yellow
    Write-Host "   git push github --all" -ForegroundColor Gray
    Write-Host "   git push github --tags" -ForegroundColor Gray
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ Setup abgeschlossen!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Nächste Schritte:" -ForegroundColor Yellow
Write-Host "1. Erstelle ein GitHub Personal Access Token unter:" -ForegroundColor White
Write-Host "   https://github.com/settings/tokens" -ForegroundColor Gray
Write-Host "   Benötigte Berechtigung: 'repo' (vollständiger Zugriff)" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Füge den Token als Secret in deinem GitHub Repository hinzu:" -ForegroundColor White
Write-Host "   GitHub Repository > Settings > Secrets and variables > Actions" -ForegroundColor Gray
Write-Host "   Name: GITHUB_TOKEN (wird automatisch verwendet)" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Optional: Füge CODEBERG_TOKEN hinzu für private Repositories:" -ForegroundColor White
Write-Host "   Erstelle Token unter: https://codeberg.org/user/settings/applications" -ForegroundColor Gray
Write-Host "   Scope: 'repo'" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Optional: Füge CODEBERG_REPO_OWNER Secret hinzu, wenn abweichend:" -ForegroundColor White
Write-Host "   Standard-Wert: 'elpatron/perlentaucher'" -ForegroundColor Gray
Write-Host ""
Write-Host "Die GitHub Actions Workflows sind bereits konfiguriert:" -ForegroundColor Green
Write-Host "  - .github/workflows/build-gui.yml (Cross-Platform Builds)" -ForegroundColor Gray
Write-Host "  - .github/workflows/sync-codeberg.yml (Automatische Synchronisation)" -ForegroundColor Gray
Write-Host ""
Write-Host "Dokumentation: docs/github-mirror.md" -ForegroundColor Cyan
