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

# Bestimme Projekt-Root-Verzeichnis
# Script sollte aus dem Root-Verzeichnis gestartet werden
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = if ((Split-Path -Leaf $scriptDir) -eq "scripts") { Split-Path -Parent $scriptDir } else { Get-Location }

# Prüfe ob wir im Root-Verzeichnis sind
$currentDir = Get-Location
if ($currentDir.Path -ne $projectRoot) {
    Write-Host "⚠ Warnung: Script sollte aus dem Projekt-Root-Verzeichnis gestartet werden!" -ForegroundColor Yellow
    Write-Host "  Aktuelles Verzeichnis: $currentDir" -ForegroundColor Gray
    Write-Host "  Erwartetes Verzeichnis: $projectRoot" -ForegroundColor Gray
    Write-Host "  Wechsle zum Projekt-Root..." -ForegroundColor Gray
    Set-Location $projectRoot
}

# Aktualisiere Version in src/_version.py
$versionNumber = $newTag.TrimStart('v')  # Entferne 'v' Präfix
Write-Host "Aktualisiere Version in src/_version.py: $versionNumber" -ForegroundColor Cyan
$versionContent = "# Version wird automatisch vom Release-Script aktualisiert`n__version__ = `"$versionNumber`"`n"
Set-Content -Path "src/_version.py" -Value $versionContent -NoNewline

# Generiere Release Notes VOR dem Tag
Write-Host "`nGeneriere Release Notes..." -ForegroundColor Cyan

$releaseNotesDir = "docs/release-notes"
$releaseNotesFile = Join-Path $releaseNotesDir "RELEASE_NOTES_$versionNumber.md"

# Stelle sicher, dass das Verzeichnis existiert
if (-not (Test-Path $releaseNotesDir)) {
    New-Item -ItemType Directory -Path $releaseNotesDir -Force | Out-Null
}

# Prüfe ob Release Notes bereits existieren, sonst generiere sie
if (-not (Test-Path $releaseNotesFile)) {
    # Hole OpenRouter API Key (optional)
    $openRouterKey = $env:OPENROUTER_API_KEY
    if (-not $openRouterKey) {
        # Versuche aus .env Datei
        $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
        $envFile = Join-Path $scriptDir ".env"
        if (Test-Path $envFile) {
            $envContent = Get-Content $envFile -Raw
            if ($envContent -match '(?m)^\s*OPENROUTER_API_KEY\s*=\s*(.+?)(?:\s*$|\s*#)') {
                $openRouterKey = $matches[1].Trim().Trim('"').Trim("'")
            }
        }
    }
    
    # Rufe Hilfs-Script auf
    $getReleaseNotesScript = Join-Path $scriptDir "get_release_notes.ps1"
    
    if (Test-Path $getReleaseNotesScript) {
        try {
            # Bestimme letzten Tag (falls nicht vorhanden, verwende ersten Commit)
            $previousTag = $lastTag
            if (-not $previousTag) {
                $firstCommit = git rev-list --max-parents=0 HEAD 2>&1
                if ($LASTEXITCODE -eq 0 -and $firstCommit) {
                    $previousTag = $firstCommit.Trim()
                    Write-Host "Verwende ersten Commit als Referenz: $previousTag" -ForegroundColor Gray
                } else {
                    $previousTag = "HEAD~100"  # Fallback: letzte 100 Commits
                }
            }
            
            if ($openRouterKey) {
                Write-Host "Verwende OpenRouter API für AI-basierte Zusammenfassung..." -ForegroundColor Gray
                $releaseNotesContent = & $getReleaseNotesScript -LastTag $previousTag -NewTag $newTag -OpenRouterApiKey $openRouterKey
            } else {
                Write-Host "Generiere Release Notes manuell (ohne AI)..." -ForegroundColor Gray
                $releaseNotesContent = & $getReleaseNotesScript -LastTag $previousTag -NewTag $newTag
            }
            
            # Speichere generierte Release Notes
            Set-Content -Path $releaseNotesFile -Value $releaseNotesContent -Encoding UTF8
            Write-Host "✓ Release Notes erfolgreich generiert: $releaseNotesFile" -ForegroundColor Green
            Write-Host "ℹ Du kannst die Datei vor dem Commit noch bearbeiten." -ForegroundColor Gray
        }
        catch {
            Write-Host "⚠ Fehler beim Generieren der Release Notes: $($_.Exception.Message)" -ForegroundColor Yellow
            Write-Host "Erstelle Fallback Template..." -ForegroundColor Gray
            
            # Fallback: Template erstellen
            $codebergUrl = git remote get-url origin 2>&1
            $codebergRepo = "elpatron/perlentaucher"
            if ($codebergUrl -match 'codeberg\.org[/:]([^/]+)/([^/]+?)(?:\.git)?$') {
                $codebergRepo = "$($matches[1])/$($matches[2] -replace '\.git$', '')"
            }
            $template = @"
# Release $newTag

## Neue Features

<!-- Hier neue Features beschreiben -->

## Verbesserungen

<!-- Hier Verbesserungen beschreiben -->

## Bugfixes

<!-- Hier Bugfixes beschreiben -->

## Technische Änderungen

<!-- Hier technische Änderungen beschreiben -->

## Bekannte Einschränkungen

<!-- Hier bekannte Einschränkungen beschreiben -->

---

**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/$codebergRepo/commits/$newTag)
"@
            Set-Content -Path $releaseNotesFile -Value $template -Encoding UTF8
            Write-Host "⚠ Release Notes Template wurde erstellt. Bitte bearbeite die Datei vor dem Release:" -ForegroundColor Yellow
            Write-Host "  $releaseNotesFile" -ForegroundColor Gray
        }
    } else {
        Write-Host "⚠ get_release_notes.ps1 nicht gefunden. Erstelle Fallback Template..." -ForegroundColor Yellow
        $codebergUrl = git remote get-url origin 2>&1
        $codebergRepo = "elpatron/perlentaucher"
        if ($codebergUrl -match 'codeberg\.org[/:]([^/]+)/([^/]+?)(?:\.git)?$') {
            $codebergRepo = "$($matches[1])/$($matches[2] -replace '\.git$', '')"
        }
        $template = @"
# Release $newTag

## Neue Features

<!-- Hier neue Features beschreiben -->

## Verbesserungen

<!-- Hier Verbesserungen beschreiben -->

## Bugfixes

<!-- Hier Bugfixes beschreiben -->

## Technische Änderungen

<!-- Hier technische Änderungen beschreiben -->

## Bekannte Einschränkungen

<!-- Hier bekannte Einschränkungen beschreiben -->

---

**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/$codebergRepo/commits/$newTag)
"@
        Set-Content -Path $releaseNotesFile -Value $template -Encoding UTF8
    }
} else {
    Write-Host "Release Notes existieren bereits: $releaseNotesFile" -ForegroundColor Gray
}

# Committe Version-Update und Release Notes zusammen
Write-Host "`nCommitte Version-Update und Release Notes..." -ForegroundColor Cyan
git add src/_version.py
if (Test-Path $releaseNotesFile) {
    git add $releaseNotesFile
}
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

# Push zu GitHub (falls GitHub Remote vorhanden)
Write-Host "`nPrüfe GitHub Remote..." -ForegroundColor Cyan
$githubRemote = git remote | Select-String -Pattern "^github$"
if ($githubRemote) {
    Write-Host "GitHub Remote gefunden. Pushe zu GitHub..." -ForegroundColor Cyan
    
    # Pushe Tag zu GitHub
    Write-Host "Pushe Tag zu GitHub: $newTag" -ForegroundColor Gray
    git push github $newTag
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠ Warnung: Fehler beim Pushen des Tags zu GitHub" -ForegroundColor Yellow
    } else {
        Write-Host "✓ Tag erfolgreich zu GitHub gepusht" -ForegroundColor Green
    }
    
    # Pushe master Branch zu GitHub
    Write-Host "Pushe master Branch zu GitHub..." -ForegroundColor Gray
    git push github master
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠ Warnung: Fehler beim Pushen des master Branches zu GitHub" -ForegroundColor Yellow
    } else {
        Write-Host "✓ master Branch erfolgreich zu GitHub gepusht" -ForegroundColor Green
    }
    
    # Starte GitHub Actions Workflow für GUI Builds
    Write-Host "`nStarte GitHub Actions Workflow für Cross-Platform GUI Builds..." -ForegroundColor Cyan
    
    # Prüfe ob gh CLI verfügbar ist
    $ghAvailable = Get-Command gh -ErrorAction SilentlyContinue
    if ($ghAvailable) {
        try {
            # Prüfe ob authentifiziert
            $null = gh auth status 2>&1
            if ($LASTEXITCODE -eq 0) {
                # Extrahiere GitHub Repository-Informationen
                $githubUrl = git remote get-url github
                if ($githubUrl -match 'github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$') {
                    $githubRepo = "$($matches[1])/$($matches[2] -replace '\.git$', '')"
                    
                    # Versuche GitHub Release zu erstellen (triggert Workflow mit release event)
                    Write-Host "Erstelle GitHub Release für automatischen Asset-Upload..." -ForegroundColor Cyan
                    $releaseNotesFileFull = Join-Path $releaseNotesDir "RELEASE_NOTES_$versionNumber.md"
                    $githubReleaseBody = ""
                    
                    # Lese Release Notes (sollten bereits vor dem Tag generiert worden sein)
                    if (Test-Path $releaseNotesFileFull) {
                        Write-Host "Lese Release-Notes aus: $releaseNotesFileFull" -ForegroundColor Gray
                        $githubReleaseBody = Get-Content $releaseNotesFileFull -Raw -Encoding UTF8
                    } else {
                        Write-Host "⚠ Warnung: Release Notes Datei nicht gefunden: $releaseNotesFileFull" -ForegroundColor Yellow
                        # Fallback: Standard Release Notes
                        $codebergUrl = git remote get-url origin 2>&1
                        $codebergRepo = "elpatron/perlentaucher"
                        if ($codebergUrl -match 'codeberg\.org[/:]([^/]+)/([^/]+?)(?:\.git)?$') {
                            $codebergRepo = "$($matches[1])/$($matches[2] -replace '\.git$', '')"
                        }
                        $githubReleaseBody = "Release $newTag`n`nSiehe [Changelog](https://codeberg.org/$codebergRepo/commits/$newTag) für Details."
                    }
                    
                    # Erstelle GitHub Release (triggert automatisch den Workflow)
                    $ghReleaseOutput = gh release create $newTag --repo $githubRepo --title "Release $newTag" --notes $githubReleaseBody --target master 2>&1
                    
                    if ($LASTEXITCODE -eq 0) {
                        Write-Host "✓ GitHub Release erfolgreich erstellt!" -ForegroundColor Green
                        Write-Host "  GitHub Actions Workflow wird automatisch durch Release-Event getriggert." -ForegroundColor Gray
                        Write-Host "  Build-Artefakte werden automatisch hochgeladen, wenn Builds abgeschlossen sind." -ForegroundColor Gray
                        Write-Host "  Artefakte werden auch automatisch zu Codeberg hochgeladen (falls CODEBERG_TOKEN konfiguriert)." -ForegroundColor Gray
                        
                        # Warte kurz und hole Workflow-Run Status
                        Start-Sleep -Seconds 5
                        $latestRunOutput = gh run list --workflow build-gui.yml --repo $githubRepo --limit 1 --json databaseId,status,url,createdAt 2>&1
                        if ($LASTEXITCODE -eq 0 -and $latestRunOutput) {
                            $latestRun = $latestRunOutput | ConvertFrom-Json
                        
                            if ($latestRun) {
                                Write-Host "`nWorkflow-Status:" -ForegroundColor Cyan
                                Write-Host "  Run ID: $($latestRun.databaseId)" -ForegroundColor Gray
                                Write-Host "  Status: $($latestRun.status)" -ForegroundColor Gray
                                Write-Host "  URL: $($latestRun.url)" -ForegroundColor Gray
                                Write-Host "`nVerfolge Build-Status mit:" -ForegroundColor Cyan
                                Write-Host "  gh run watch $($latestRun.databaseId) --repo $githubRepo" -ForegroundColor Gray
                                Write-Host "  Oder öffne: $($latestRun.url)" -ForegroundColor Gray
                            }
                        }
                    } else {
                        # Prüfe ob Release bereits existiert
                        $existingRelease = gh release view $newTag --repo $githubRepo 2>&1
                        if ($LASTEXITCODE -eq 0) {
                            Write-Host "ℹ GitHub Release für Tag $newTag existiert bereits." -ForegroundColor Gray
                            Write-Host "  GitHub Actions Workflow sollte bereits getriggert worden sein." -ForegroundColor Gray
                        } else {
                            Write-Host "⚠ Warnung: GitHub Release konnte nicht erstellt werden" -ForegroundColor Yellow
                            Write-Host "  Fehler: $ghReleaseOutput" -ForegroundColor Gray
                            Write-Host "  Du kannst es manuell erstellen: gh release create $newTag --repo $githubRepo" -ForegroundColor Gray
                            Write-Host "  Oder auf GitHub.com: https://github.com/$githubRepo/releases/new" -ForegroundColor Gray
                        }
                    }
                } else {
                    Write-Host "⚠ Warnung: Konnte GitHub Repository-Informationen nicht extrahieren" -ForegroundColor Yellow
                    Write-Host "  Remote URL: $githubUrl" -ForegroundColor Gray
                }
            } else {
                Write-Host "⚠ Warnung: GitHub CLI nicht authentifiziert" -ForegroundColor Yellow
                Write-Host "  Bitte authentifiziere dich mit: gh auth login" -ForegroundColor Gray
            }
        }
        catch {
            Write-Host "⚠ Warnung: Fehler beim Starten des GitHub Actions Workflows:" -ForegroundColor Yellow
            Write-Host "  $($_.Exception.Message)" -ForegroundColor Gray
        }
    } else {
        Write-Host "⚠ Warnung: GitHub CLI (gh) nicht verfügbar" -ForegroundColor Yellow
        Write-Host "  Installiere GitHub CLI oder starte Workflow manuell auf GitHub.com" -ForegroundColor Gray
    }
} else {
    Write-Host "ℹ GitHub Remote nicht gefunden. Überspringe GitHub Push und Workflow-Start." -ForegroundColor Gray
    Write-Host "  Füge GitHub Remote hinzu mit: git remote add github https://github.com/USERNAME/REPO.git" -ForegroundColor Gray
}

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
        # Lese Release-Notes aus Datei (sollten bereits vor dem Tag generiert worden sein)
        $releaseNotesFileFull = Join-Path $releaseNotesDir "RELEASE_NOTES_$versionNumber.md"
        $releaseBody = ""
        
        if (Test-Path $releaseNotesFileFull) {
            Write-Host "Lese Release-Notes aus: $releaseNotesFileFull" -ForegroundColor Gray
            $releaseBody = Get-Content $releaseNotesFileFull -Raw -Encoding UTF8
        } else {
            Write-Host "⚠ Warnung: Release Notes Datei nicht gefunden: $releaseNotesFileFull" -ForegroundColor Yellow
            Write-Host "Verwende Fallback Release Notes..." -ForegroundColor Gray
            # Fallback: Standard Release Notes
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
        }
        
        # Konvertiere zu JSON mit UTF-8 Encoding (sicherstellen, dass UTF-8 Zeichen korrekt behandelt werden)
        $releaseDataJson = $releaseData | ConvertTo-Json -Depth 10 -Compress
        
        # Konvertiere JSON-String zu UTF-8 Bytes für korrektes Encoding
        $utf8Encoding = [System.Text.Encoding]::UTF8
        $releaseDataBytes = $utf8Encoding.GetBytes($releaseDataJson)
        
        $headers = @{
            "Authorization" = "token $codebergToken"
            "Content-Type" = "application/json; charset=utf-8"
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
                        # Update Release mit UTF-8 Bytes
                        $updateUrl = "$apiUrl/$($existingRelease.id)"
                        $response = Invoke-WebRequest -Uri $updateUrl -Method Patch -Headers $headers -Body $releaseDataBytes -ContentType "application/json; charset=utf-8" -UseBasicParsing | ConvertFrom-Json
                        Write-Host "✅ Release erfolgreich aktualisiert!" -ForegroundColor Green
                        Write-Host "  URL: $($response.html_url)" -ForegroundColor Gray
                    } else {
                        Write-Host "Release wird nicht aktualisiert." -ForegroundColor Gray
                        $response = $existingRelease
                    }
                }
            }
            catch {
                # Release existiert nicht, erstelle neues Release mit UTF-8 Bytes
                $response = Invoke-WebRequest -Uri $apiUrl -Method Post -Headers $headers -Body $releaseDataBytes -ContentType "application/json; charset=utf-8" -UseBasicParsing | ConvertFrom-Json
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