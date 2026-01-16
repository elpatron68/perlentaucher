# Docker Build Script für PowerShell
# Dieses Script muss aus dem Root-Verzeichnis des Projekts ausgeführt werden
# oder mit dem Build-Kontext auf das Root-Verzeichnis zeigen

# Prüfe ob wir im Root-Verzeichnis sind
if (-not (Test-Path "requirements.txt") -or -not (Test-Path "src")) {
    Write-Host "Fehler: Dieses Script muss aus dem Root-Verzeichnis des Projekts ausgeführt werden." -ForegroundColor Red
    Write-Host "Aktuelles Verzeichnis: $(Get-Location)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Verwendung:" -ForegroundColor Cyan
    Write-Host "  cd C:\pfad\zum\projekt\root"
    Write-Host "  docker build -t perlentaucher:VERSION -t perlentaucher:latest -f docker/Dockerfile ."
    Write-Host ""
    Write-Host "Oder wenn du im docker-Verzeichnis bist:" -ForegroundColor Cyan
    Write-Host "  docker build -t perlentaucher:VERSION -t perlentaucher:latest -f Dockerfile .."
    exit 1
}

# Lese Version aus src/_version.py
try {
    $version = python -c "from src._version import __version__; print(__version__)" 2>$null
    if (-not $version) {
        $version = python3 -c "from src._version import __version__; print(__version__)" 2>$null
    }
    
    if (-not $version) {
        Write-Host "Fehler: Konnte Version nicht aus src/_version.py lesen." -ForegroundColor Red
        exit 1
    }
    
    $version = $version.Trim()
    Write-Host "Baue Docker-Image mit Version: $version" -ForegroundColor Cyan
} catch {
    Write-Host "Fehler beim Lesen der Version: $_" -ForegroundColor Red
    exit 1
}

# Führe den Build aus
docker build -t "perlentaucher:$version" -t perlentaucher:latest -f docker/Dockerfile .
