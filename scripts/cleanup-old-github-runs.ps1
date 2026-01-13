# cleanup-old-github-runs.ps1
# Löscht alle GitHub Actions Runs außer den letzten 10

param(
    [string]$WorkflowName = "Build GUI Cross-Platform",
    [int]$KeepCount = 10,
    [switch]$Force
)

Write-Host "=== GitHub Actions Run Cleanup ===" -ForegroundColor Cyan
Write-Host "Workflow: $WorkflowName" -ForegroundColor Yellow
Write-Host "Behalte die letzten $KeepCount Runs" -ForegroundColor Yellow
Write-Host ""

# Prüfe ob gh CLI installiert ist
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Fehler: GitHub CLI (gh) ist nicht installiert!" -ForegroundColor Red
    Write-Host "Installiere es von: https://cli.github.com/" -ForegroundColor Yellow
    exit 1
}

# Prüfe ob wir im richtigen Repo sind
$repoInfo = gh repo view --json nameWithOwner 2>$null | ConvertFrom-Json
if (-not $repoInfo) {
    Write-Host "Fehler: Nicht in einem Git-Repository oder nicht mit GitHub verbunden!" -ForegroundColor Red
    exit 1
}

Write-Host "Repository: $($repoInfo.nameWithOwner)" -ForegroundColor Green
Write-Host ""

# Hole alle Runs für den Workflow
Write-Host "Hole Liste der Runs..." -ForegroundColor Cyan
$allRuns = gh run list --workflow="$WorkflowName" --limit 1000 --json databaseId,number,status,conclusion,createdAt,displayTitle `
    | ConvertFrom-Json

if ($allRuns.Count -eq 0) {
    Write-Host "Keine Runs gefunden für Workflow: $WorkflowName" -ForegroundColor Yellow
    exit 0
}

Write-Host "Gefunden: $($allRuns.Count) Runs" -ForegroundColor Green
Write-Host ""

# Zeige die letzten Runs an, die behalten werden
Write-Host "Die folgenden $KeepCount Runs werden BEHALTEN:" -ForegroundColor Green
$runsToKeep = $allRuns | Select-Object -First $KeepCount
foreach ($run in $runsToKeep) {
    $status = switch ($run.status) {
        "completed" { if ($run.conclusion -eq "success") { "✓" } else { "✗" } }
        "in_progress" { "⟳" }
        default { "?" }
    }
    Write-Host "  $status Run #$($run.number): $($run.displayTitle) ($($run.createdAt))" -ForegroundColor Gray
}
Write-Host ""

# Berechne Runs zum Löschen
$runsToDelete = $allRuns | Select-Object -Skip $KeepCount

if ($runsToDelete.Count -eq 0) {
    Write-Host "Keine Runs zum Löschen - es gibt nur $($allRuns.Count) Runs (behalte $KeepCount)" -ForegroundColor Yellow
    exit 0
}

Write-Host "Die folgenden $($runsToDelete.Count) Runs werden GELÖSCHT:" -ForegroundColor Red
foreach ($run in $runsToDelete) {
    $status = switch ($run.status) {
        "completed" { if ($run.conclusion -eq "success") { "✓" } else { "✗" } }
        "in_progress" { "⟳" }
        default { "?" }
    }
    Write-Host "  $status Run #$($run.number): $($run.displayTitle) ($($run.createdAt))" -ForegroundColor Gray
}
Write-Host ""

# Sicherheitsabfrage (außer wenn -Force gesetzt ist)
if (-not $Force) {
    $confirmation = Read-Host "Möchtest du diese $($runsToDelete.Count) Runs wirklich löschen? (j/N)"
    if ($confirmation -ne "j" -and $confirmation -ne "J" -and $confirmation -ne "y" -and $confirmation -ne "Y") {
        Write-Host "Abgebrochen." -ForegroundColor Yellow
        exit 0
    }
}

# Lösche die Runs
Write-Host ""
Write-Host "Lösche Runs..." -ForegroundColor Cyan
$deleted = 0
$failed = 0

foreach ($run in $runsToDelete) {
    Write-Host "  Lösche Run #$($run.number)..." -NoNewline -ForegroundColor Gray
    
    $result = gh run delete $run.databaseId 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " ✓" -ForegroundColor Green
        $deleted++
    } else {
        Write-Host " ✗ Fehler: $result" -ForegroundColor Red
        $failed++
    }
    
    # Kurze Pause zwischen Löschvorgängen
    Start-Sleep -Milliseconds 500
}

Write-Host ""
Write-Host "=== Zusammenfassung ===" -ForegroundColor Cyan
Write-Host "Gelöscht: $deleted Runs" -ForegroundColor Green
if ($failed -gt 0) {
    Write-Host "Fehler: $failed Runs konnten nicht gelöscht werden" -ForegroundColor Red
}
Write-Host "Behalten: $KeepCount Runs" -ForegroundColor Green
Write-Host ""
Write-Host "Hinweis: GitHub berechnet den Speicherverbrauch alle 6-12 Stunden neu." -ForegroundColor Yellow
Write-Host "Die Quota-Fehlermeldung kann daher noch einige Stunden bestehen bleiben." -ForegroundColor Yellow