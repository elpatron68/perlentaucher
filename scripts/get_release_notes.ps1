#!/usr/bin/env pwsh
# Hilfs-Script zum Generieren von Release Notes aus Git Commits
# Kann optional OpenRouter API für AI-basierte Zusammenfassung verwenden

param(
    [Parameter(Mandatory=$true)]
    [string]$LastTag,
    
    [Parameter(Mandatory=$true)]
    [string]$NewTag,
    
    [string]$OpenRouterApiKey = $null,
    [string]$OpenRouterModel = "anthropic/claude-3.5-sonnet"
)

# Hole Commits zwischen den Tags (oder seit letztem Tag)
if ($LastTag) {
    $commitRange = "${LastTag}..HEAD"
} else {
    # Falls kein letzter Tag, verwende letzten 100 Commits
    $commitRange = "HEAD~100..HEAD"
    Write-Host "Kein letzter Tag gefunden, verwende letzte 100 Commits" -ForegroundColor Yellow
}

$commits = git log $commitRange --pretty=format:"%h|%s|%b" --no-merges 2>&1

if (-not $commits -or ($commits -is [string] -and $commits -match "fatal:")) {
    Write-Host "Fehler beim Abrufen der Commits: $commits" -ForegroundColor Yellow
    $commits = @()
}

if ($null -eq $commits -or ($commits -is [array] -and $commits.Count -eq 0) -or ($commits -is [string] -and $commits.Trim() -eq "")) {
    Write-Host "Keine Commits gefunden zwischen $LastTag und HEAD" -ForegroundColor Yellow
    $releaseNotes = @"
# Release $NewTag

## Änderungen

Keine Änderungen seit dem letzten Release.

---

**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/elpatron/perlentaucher/commits/$NewTag)
"@
    return $releaseNotes
}

# Parse Commits
$commitList = @()
if ($commits -is [string]) {
    # Wenn Commits ein einzelner String ist, splitte nach Zeilen
    $commitLines = $commits -split "`n" | Where-Object { $_.Trim() -ne "" }
    foreach ($commit in $commitLines) {
        if ($commit -match '^([^|]+)\|(.+?)(?:\|(.*))?$') {
            $hash = $matches[1]
            $subject = $matches[2]
            $body = if ($matches[3]) { $matches[3].Trim() } else { "" }
            
            $commitList += @{
                hash = $hash
                subject = $subject
                body = $body
                full = if ($body) { "$subject`n$body" } else { $subject }
            }
        }
    }
} elseif ($commits -is [array]) {
    foreach ($commit in $commits) {
        if ($commit -match '^([^|]+)\|(.+?)(?:\|(.*))?$') {
            $hash = $matches[1]
            $subject = $matches[2]
            $body = if ($matches[3]) { $matches[3].Trim() } else { "" }
            
            $commitList += @{
                hash = $hash
                subject = $subject
                body = $body
                full = if ($body) { "$subject`n$body" } else { $subject }
            }
        }
    }
}

Write-Host "Gefundene Commits: $($commitList.Count)" -ForegroundColor Gray

if ($commitList.Count -eq 0) {
    Write-Host "Keine Commits zum Parsen gefunden" -ForegroundColor Yellow
    $releaseNotes = @"
# Release $NewTag

## Änderungen

Keine Commits gefunden seit dem letzten Release.

---

**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/elpatron/perlentaucher/commits/$NewTag)
"@
    return $releaseNotes
}

# Generiere Release Notes
$releaseNotes = ""

if ($OpenRouterApiKey) {
    # Verwende OpenRouter API für AI-basierte Zusammenfassung
    Write-Host "Generiere Release Notes mit AI (OpenRouter)..." -ForegroundColor Cyan
    
    try {
        # Erstelle Prompt für AI
        $commitsText = ""
        foreach ($commit in $commitList) {
            $commitsText += "`n- $($commit.subject)"
            if ($commit.body) {
                $commitsText += "`n  $($commit.body)"
            }
        }
        
        $prompt = @"
Erstelle strukturierte Release Notes für ein Python-Projekt basierend auf folgenden Git Commits seit dem letzten Release:

$commitsText

Kategorisiere die Commits in:
- Neue Features
- Verbesserungen
- Bugfixes
- Technische Änderungen

Format: Markdown, strukturiert, prägnant, auf Deutsch.
Beginne mit: "# Release $NewTag"
"@

        # API Request an OpenRouter
        $apiUrl = "https://openrouter.ai/api/v1/chat/completions"
        $headers = @{
            "Authorization" = "Bearer $OpenRouterApiKey"
            "Content-Type" = "application/json"
            "HTTP-Referer" = "https://codeberg.org/elpatron/perlentaucher"
        }
        
        $body = @{
            model = $OpenRouterModel
            messages = @(
                @{
                    role = "user"
                    content = $prompt
                }
            )
            temperature = 0.7
            max_tokens = 2000
        } | ConvertTo-Json -Depth 10 -Compress
        
        $response = Invoke-RestMethod -Uri $apiUrl -Method Post -Headers $headers -Body $body -ErrorAction Stop
        
        if ($response.choices -and $response.choices.Count -gt 0) {
            $releaseNotes = $response.choices[0].message.content
            
            # Füge Link zu Commits hinzu
            $releaseNotes += "`n`n---`n`n**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/elpatron/perlentaucher/commits/$NewTag)"
            
            Write-Host "✓ Release Notes erfolgreich mit AI generiert" -ForegroundColor Green
        } else {
            throw "Keine Antwort von AI API"
        }
    }
    catch {
        Write-Host "⚠ Fehler bei AI-Generierung: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "Verwende Fallback-Methode..." -ForegroundColor Gray
        $OpenRouterApiKey = $null  # Fallback zu manueller Generierung
    }
}

if (-not $OpenRouterApiKey -or -not $releaseNotes) {
    # Manuelle Generierung ohne AI
    Write-Host "Generiere Release Notes manuell..." -ForegroundColor Gray
    
    $features = @()
    $improvements = @()
    $bugfixes = @()
    $technical = @()
    $other = @()
    
    foreach ($commit in $commitList) {
        $subject = $commit.subject
        $body = $commit.body
        
        # Kategorisiere basierend auf Commit-Message-Patterns
        if ($subject -match '^(feat|feature|add):' -or $subject -match '^(Neue|neue|Add|add)') {
            $features += "- $subject"
        }
        elseif ($subject -match '^(fix|bugfix|bug):' -or $subject -match '^(Fix|fix|Behebe|behebe)') {
            $bugfixes += "- $subject"
        }
        elseif ($subject -match '^(refactor|tech|chore|build|ci):' -or $subject -match '^(Refactor|refactor|Technical|technical)') {
            $technical += "- $subject"
        }
        elseif ($subject -match '^(improve|enhance|perf|update):' -or $subject -match '^(Improve|improve|Verbessere|verbessere)') {
            $improvements += "- $subject"
        }
        else {
            $other += "- $subject"
        }
    }
    
    # Erstelle Release Notes
    $releaseNotes = "# Release $NewTag`n`n"
    
    if ($features.Count -gt 0) {
        $releaseNotes += "## Neue Features`n`n"
        $releaseNotes += ($features -join "`n") + "`n`n"
    }
    
    if ($improvements.Count -gt 0) {
        $releaseNotes += "## Verbesserungen`n`n"
        $releaseNotes += ($improvements -join "`n") + "`n`n"
    }
    
    if ($bugfixes.Count -gt 0) {
        $releaseNotes += "## Bugfixes`n`n"
        $releaseNotes += ($bugfixes -join "`n") + "`n`n"
    }
    
    if ($technical.Count -gt 0) {
        $releaseNotes += "## Technische Änderungen`n`n"
        $releaseNotes += ($technical -join "`n") + "`n`n"
    }
    
    if ($other.Count -gt 0) {
        $releaseNotes += "## Weitere Änderungen`n`n"
        $releaseNotes += ($other -join "`n") + "`n`n"
    }
    
    # Fallback: Wenn keine Kategorisierung, liste alle Commits
    if ($features.Count -eq 0 -and $improvements.Count -eq 0 -and $bugfixes.Count -eq 0 -and $technical.Count -eq 0 -and $other.Count -eq 0) {
        $releaseNotes += "## Änderungen`n`n"
        foreach ($commit in $commitList) {
            $releaseNotes += "- $($commit.subject)`n"
        }
        $releaseNotes += "`n"
    }
    
    # Extrahiere Codeberg Repository-Informationen
    $codebergUrl = git remote get-url origin 2>&1
    $codebergRepo = "elpatron/perlentaucher"
    if ($codebergUrl -match 'codeberg\.org[/:]([^/]+)/([^/]+?)(?:\.git)?$') {
        $codebergRepo = "$($matches[1])/$($matches[2] -replace '\.git$', '')"
    }
    
    $releaseNotes += "---`n`n**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/$codebergRepo/commits/$NewTag)"
}

return $releaseNotes
