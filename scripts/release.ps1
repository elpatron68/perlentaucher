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

# Aktualisiere Version in _version.py
$versionNumber = $newTag.TrimStart('v')  # Entferne 'v' Präfix
Write-Host "Aktualisiere Version in _version.py: $versionNumber" -ForegroundColor Cyan
$versionContent = "# Version wird automatisch vom Release-Script aktualisiert`n__version__ = `"$versionNumber`"`n"
Set-Content -Path "_version.py" -Value $versionContent -NoNewline

# Committe Version-Update
Write-Host "Committe Version-Update..." -ForegroundColor Cyan
git add _version.py
$commitOutput = git commit -m "Bump version to $versionNumber" 2>&1
if ($LASTEXITCODE -ne 0 -or $commitOutput -match "nothing to commit") {
    # Wenn nichts zu committen ist (Datei bereits aktuell), ist das OK
    Write-Host "Version bereits aktuell oder kein Commit notwendig" -ForegroundColor Gray
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

# Erstelle Release über Codeberg API
Write-Host "`nErstelle Release über Codeberg API..." -ForegroundColor Cyan

# Extrahiere Repository-Informationen aus Git-Remote
$remoteUrl = git remote get-url origin
if ($remoteUrl -match 'codeberg\.org[/:]([^/]+)/([^/]+?)(?:\.git)?$') {
    $repoOwner = $matches[1]
    $repoName = $matches[2] -replace '\.git$', ''
    
    Write-Host "Repository: $repoOwner/$repoName" -ForegroundColor Gray
    
    # Hole Codeberg API Token (aus .env Datei, Umgebungsvariable oder interaktiv)
    $codebergToken = $null
    
    # Versuche .env Datei im Scripts-Ordner zu lesen
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $envFile = Join-Path $scriptDir ".env"
    if (Test-Path $envFile) {
        Write-Host "Lese .env Datei: $envFile" -ForegroundColor Gray
        $envContent = Get-Content $envFile -Raw
        if ($envContent -match '(?m)^\s*CODEBERG_TOKEN\s*=\s*(.+?)(?:\s*$|\s*#)') {
            $codebergToken = $matches[1].Trim().Trim('"').Trim("'")
            Write-Host "Token aus .env Datei geladen" -ForegroundColor Gray
        }
    }
    
    # Fallback auf Umgebungsvariable
    if (-not $codebergToken) {
        $codebergToken = $env:CODEBERG_TOKEN
    }
    
    # Fallback auf interaktive Eingabe
    if (-not $codebergToken) {
        Write-Host "Codeberg API Token nicht gefunden." -ForegroundColor Yellow
        Write-Host "Hinweis: Erstelle einen Personal Access Token unter:" -ForegroundColor Yellow
        Write-Host "  https://codeberg.org/user/settings/applications" -ForegroundColor Gray
        Write-Host "  Benötigte Scopes: 'public_repo' oder 'repo' (für private Repos)" -ForegroundColor Gray
        Write-Host "  Oder speichere Token in: $envFile" -ForegroundColor Gray
        $codebergToken = Read-Host "Codeberg API Token (oder Enter zum Überspringen)"
    }
    
    if ($codebergToken) {
        # Lese Release-Notes aus Datei, falls vorhanden
        $releaseNotesFile = "RELEASE_NOTES_$versionNumber.md"
        $releaseBody = ""
        
        if (Test-Path $releaseNotesFile) {
            Write-Host "Lese Release-Notes aus: $releaseNotesFile" -ForegroundColor Gray
            $releaseBody = Get-Content $releaseNotesFile -Raw -Encoding UTF8
        } else {
            # Fallback: Standard Release-Notes
            $releaseBody = "Release $newTag`n`nSiehe [Changelog](https://codeberg.org/$repoOwner/$repoName/commits/$newTag) für Details."
        }
        
        # Erstelle Release über Codeberg/Gitea API
        $apiUrl = "https://codeberg.org/api/v1/repos/$repoOwner/$repoName/releases"
        $releaseData = @{
            tag_name = $newTag
            name = "Release $newTag"
            body = $releaseBody
            draft = $false
            prerelease = $false
        } | ConvertTo-Json
        
        $headers = @{
            "Authorization" = "token $codebergToken"
            "Content-Type" = "application/json"
        }
        
        try {
            # Prüfe ob Release bereits existiert
            $checkUrl = "$apiUrl/tags/$newTag"
            try {
                $existingRelease = Invoke-RestMethod -Uri $checkUrl -Method Get -Headers $headers -ErrorAction SilentlyContinue
                if ($existingRelease) {
                    Write-Host "⚠ Release für Tag $newTag existiert bereits." -ForegroundColor Yellow
                    $update = Read-Host "Release aktualisieren? (j/n) [n]"
                    if ($update -match '^[JjYy]$') {
                        # Update Release
                        $updateUrl = "$apiUrl/$($existingRelease.id)"
                        $response = Invoke-RestMethod -Uri $updateUrl -Method Patch -Headers $headers -Body $releaseData -ErrorAction Stop
                        Write-Host "✅ Release erfolgreich aktualisiert!" -ForegroundColor Green
                        Write-Host "  URL: $($response.html_url)" -ForegroundColor Gray
                    } else {
                        Write-Host "Release wird nicht aktualisiert." -ForegroundColor Gray
                        $response = $existingRelease
                    }
                }
            }
            catch {
                # Release existiert nicht, erstelle neues Release
                $response = Invoke-RestMethod -Uri $apiUrl -Method Post -Headers $headers -Body $releaseData -ErrorAction Stop
                Write-Host "✅ Release erfolgreich erstellt!" -ForegroundColor Green
                Write-Host "  URL: $($response.html_url)" -ForegroundColor Gray
            }
        }
        catch {
            Write-Host "⚠ Fehler beim Erstellen/Aktualisieren des Releases über API:" -ForegroundColor Yellow
            Write-Host "  $($_.Exception.Message)" -ForegroundColor Yellow
            if ($_.ErrorDetails.Message) {
                Write-Host "  Details: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
            }
            if ($_.Exception.Response.StatusCode -eq 409) {
                Write-Host "  Release für diesen Tag existiert bereits." -ForegroundColor Yellow
            }
            Write-Host "  Release kann manuell erstellt werden unter:" -ForegroundColor Yellow
            Write-Host "  https://codeberg.org/$repoOwner/$repoName/releases/new" -ForegroundColor Gray
            $response = $null
        }
    } else {
        Write-Host "Codeberg API Token nicht angegeben. Release wird übersprungen." -ForegroundColor Yellow
        Write-Host "Release kann manuell erstellt werden unter:" -ForegroundColor Yellow
        Write-Host "  https://codeberg.org/$repoOwner/$repoName/releases/new" -ForegroundColor Gray
    }
} else {
    Write-Host "⚠ Konnte Repository-Informationen nicht aus Git-Remote extrahieren." -ForegroundColor Yellow
    Write-Host "  Remote URL: $remoteUrl" -ForegroundColor Gray
    Write-Host "  Release kann manuell erstellt werden." -ForegroundColor Yellow
}

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
if ($codebergToken -and $response) {
    Write-Host "  Release: $($response.html_url)" -ForegroundColor Gray
}