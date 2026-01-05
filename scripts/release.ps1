#!/usr/bin/env pwsh
# Script zum Inkrementieren des Patch-Levels, Taggen, Pushen und Docker-Image erstellen/pushen

$ErrorActionPreference = "Stop"

# Hole den letzten Tag
$lastTag = git tag --list --sort=-version:refname | Select-Object -First 1

if (-not $lastTag) {
    Write-Host "Kein Tag gefunden. Erstelle initialen Tag v0.1.0" -ForegroundColor Yellow
    $newTag = "v0.1.0"
} else {
    Write-Host "Letzter Tag: $lastTag" -ForegroundColor Cyan
    
    # Extrahiere Version (z.B. v0.1.3 -> 0.1.3)
    if ($lastTag -match '^v?(\d+)\.(\d+)\.(\d+)$') {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        $patch = [int]$matches[3]
        
        # Inkrementiere Patch-Level
        $patch++
        $newTag = "v${major}.${minor}.${patch}"
        
        Write-Host "Neuer Tag: $newTag" -ForegroundColor Green
    } else {
        Write-Host "Fehler: Tag-Format nicht erkannt: $lastTag" -ForegroundColor Red
        Write-Host "Erwartetes Format: vX.Y.Z (z.B. v0.1.3)" -ForegroundColor Red
        exit 1
    }
}

# Prüfe ob es uncommitted Änderungen gibt
$status = git status --porcelain
if ($status) {
    Write-Host "Warnung: Es gibt uncommitted Änderungen:" -ForegroundColor Yellow
    Write-Host $status -ForegroundColor Yellow
    $response = Read-Host "Trotzdem fortfahren? (j/n)"
    if ($response -ne "j" -and $response -ne "J" -and $response -ne "y" -and $response -ne "Y") {
        Write-Host "Abgebrochen." -ForegroundColor Red
        exit 1
    }
}

# Erstelle neuen Tag
Write-Host "`nErstelle Git-Tag: $newTag" -ForegroundColor Cyan
git tag -a $newTag -m "Release $newTag"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Fehler beim Erstellen des Tags!" -ForegroundColor Red
    exit 1
}

# Pushe Tag zu Remote
Write-Host "Pushe Tag zu Remote..." -ForegroundColor Cyan
git push origin $newTag

if ($LASTEXITCODE -ne 0) {
    Write-Host "Fehler beim Pushen des Tags!" -ForegroundColor Red
    exit 1
}

# Pushe auch master (falls es neue Commits gibt)
Write-Host "Pushe master Branch..." -ForegroundColor Cyan
git push origin master

# Docker-Image bauen
Write-Host "`nBaue Docker-Image: perlentaucher:$newTag" -ForegroundColor Cyan
docker build -t perlentaucher:$newTag -t perlentaucher:latest .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Fehler beim Bauen des Docker-Images!" -ForegroundColor Red
    exit 1
}

# Docker-Image für Codeberg Registry taggen
$registryImage = "codeberg.org/elpatron/perlentaucher:$newTag"
$registryLatest = "codeberg.org/elpatron/perlentaucher:latest"

Write-Host "Tagge Docker-Image für Codeberg Registry..." -ForegroundColor Cyan
docker tag perlentaucher:$newTag $registryImage
docker tag perlentaucher:$newTag $registryLatest

# Docker-Image zu Codeberg Registry pushen
Write-Host "Pushe Docker-Image zu Codeberg Registry..." -ForegroundColor Cyan
Write-Host "  -> $registryImage" -ForegroundColor Gray
docker push $registryImage

if ($LASTEXITCODE -ne 0) {
    Write-Host "Fehler beim Pushen des Docker-Images ($registryImage)!" -ForegroundColor Red
    Write-Host "Hinweis: Stelle sicher, dass du bei Codeberg Registry angemeldet bist:" -ForegroundColor Yellow
    Write-Host "  docker login codeberg.org" -ForegroundColor Yellow
    exit 1
}

Write-Host "  -> $registryLatest" -ForegroundColor Gray
docker push $registryLatest

if ($LASTEXITCODE -ne 0) {
    Write-Host "Fehler beim Pushen des Docker-Images ($registryLatest)!" -ForegroundColor Red
    exit 1
}

Write-Host "`n✅ Erfolgreich abgeschlossen!" -ForegroundColor Green
Write-Host "  Tag: $newTag" -ForegroundColor Gray
Write-Host "  Docker-Image: $registryImage" -ForegroundColor Gray
Write-Host "  Docker-Image (latest): $registryLatest" -ForegroundColor Gray
