# Quickstart-Script für Perlentaucher (Windows)
# Installiert Dependencies und führt interaktive Konfiguration durch

$ErrorActionPreference = "Stop"

# Funktion: Python-Check
function Test-Python {
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $versionString = $pythonVersion -replace "Python ", ""
            $versionParts = $versionString.Split('.')
            $major = [int]$versionParts[0]
            $minor = [int]$versionParts[1]
            
            if ($major -eq 3 -and $minor -ge 7) {
                Write-Host "✓ Python $versionString gefunden" -ForegroundColor Green
                return $true
            } else {
                Write-Host "✗ Python $versionString gefunden, aber Version 3.7+ erforderlich" -ForegroundColor Red
                return $false
            }
        }
    } catch {
        return $false
    }
    return $false
}

# Funktion: Python-Installationshinweise anzeigen
function Show-PythonInstructions {
    Write-Host ""
    Write-Host "Python 3.7+ ist nicht installiert." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Installation auf Windows:"
    Write-Host ""
    Write-Host "Option 1: Winget (Windows Package Manager, empfohlen)"
    Write-Host "  winget install Python.Python.3.11"
    Write-Host ""
    Write-Host "Option 2: Python.org"
    Write-Host "  1. Besuche: https://www.python.org/downloads/"
    Write-Host "  2. Lade die neueste Python 3.x Version herunter"
    Write-Host "  3. Wichtig: Aktiviere 'Add Python to PATH' während der Installation!"
    Write-Host ""
    exit 1
}

# Funktion: pip-Check
function Test-Pip {
    try {
        $pipVersion = pip --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ pip gefunden" -ForegroundColor Green
            return $true
        }
    } catch {
        # Versuche python -m pip
        try {
            $pipVersion = python -m pip --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ pip gefunden (via python -m pip)" -ForegroundColor Green
                return $true
            }
        } catch {
            return $false
        }
    }
    
    Write-Host "⚠ pip nicht gefunden" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "pip sollte mit Python installiert werden."
    Write-Host "Falls nicht, installiere es manuell:"
    Write-Host "  python -m ensurepip --upgrade"
    Write-Host "oder:"
    Write-Host "  curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py"
    Write-Host "  python get-pip.py"
    exit 1
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Perlentaucher - Quickstart (Windows)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Prüfe Python
Write-Host "Prüfe Python-Installation..."
if (-not (Test-Python)) {
    Show-PythonInstructions
}

# Prüfe pip
Write-Host "Prüfe pip-Installation..."
Test-Pip

Write-Host ""

# Frage nach virtueller Umgebung
$createVenv = Read-Host "Soll eine virtuelle Umgebung erstellt werden? (empfohlen) [J/n]"
if ([string]::IsNullOrWhiteSpace($createVenv) -or $createVenv -match '^[JjYy]') {
    Write-Host "Erstelle virtuelle Umgebung..."
    python -m venv .venv
    Write-Host "✓ Virtuelle Umgebung erstellt" -ForegroundColor Green
    Write-Host ""
    Write-Host "Aktivierung der virtuellen Umgebung:"
    Write-Host "  .\.venv\Scripts\Activate.ps1"
    Write-Host ""
    # Aktiviere venv für diesen Session
    & .\.venv\Scripts\Activate.ps1
    $venvActive = $true
} else {
    $venvActive = $false
}

# Installiere Dependencies
Write-Host "Installiere Dependencies..."
if ($venvActive -or (Test-Path ".venv")) {
    pip install -r requirements.txt
} else {
    pip install -r requirements.txt --user
}
Write-Host "✓ Dependencies installiert" -ForegroundColor Green
Write-Host ""

# Hole Script-Verzeichnis
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
Set-Location $projectDir

# Interaktive Parameterabfrage
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Konfiguration" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Download-Verzeichnis
$downloadDir = Read-Host "Download-Verzeichnis [.\downloads]"
if ([string]::IsNullOrWhiteSpace($downloadDir)) {
    $downloadDir = ".\downloads"
}

# Limit
$limit = Read-Host "Anzahl zu prüfender RSS-Einträge [10]"
if ([string]::IsNullOrWhiteSpace($limit)) {
    $limit = 10
} else {
    $limit = [int]$limit
}

# Log-Level
Write-Host ""
Write-Host "Log-Level wählen:"
Write-Host "  1) DEBUG"
Write-Host "  2) INFO (Standard)"
Write-Host "  3) WARNING"
Write-Host "  4) ERROR"
$loglevelChoice = Read-Host "Auswahl [2]"
switch ($loglevelChoice) {
    "1" { $loglevel = "DEBUG" }
    "2" { $loglevel = "INFO" }
    "3" { $loglevel = "WARNING" }
    "4" { $loglevel = "ERROR" }
    default { $loglevel = "INFO" }
}

# Sprache
Write-Host ""
Write-Host "Bevorzugte Sprache:"
Write-Host "  1) deutsch (Standard)"
Write-Host "  2) englisch"
Write-Host "  3) egal"
$spracheChoice = Read-Host "Auswahl [1]"
switch ($spracheChoice) {
    "1" { $sprache = "deutsch" }
    "2" { $sprache = "englisch" }
    "3" { $sprache = "egal" }
    default { $sprache = "deutsch" }
}

# Audiodeskription
Write-Host ""
Write-Host "Bevorzugte Audiodeskription:"
Write-Host "  1) mit"
Write-Host "  2) ohne"
Write-Host "  3) egal (Standard)"
$audiodeskriptionChoice = Read-Host "Auswahl [3]"
switch ($audiodeskriptionChoice) {
    "1" { $audiodeskription = "mit" }
    "2" { $audiodeskription = "ohne" }
    "3" { $audiodeskription = "egal" }
    default { $audiodeskription = "egal" }
}

# State-Datei
Write-Host ""
$stateFile = Read-Host "State-Datei [.perlentaucher_state.json]"
if ([string]::IsNullOrWhiteSpace($stateFile)) {
    $stateFile = ".perlentaucher_state.json"
}

# State-Tracking
Write-Host ""
$stateTracking = Read-Host "State-Tracking aktivieren? [J/n]"
if ([string]::IsNullOrWhiteSpace($stateTracking) -or $stateTracking -match '^[JjYy]') {
    $noState = $false
} else {
    $noState = $true
}

# Benachrichtigungen
Write-Host ""
Write-Host "Benachrichtigungen (optional):"
Write-Host "  Beispiele:"
Write-Host "    - Discord: discord://webhook_id/webhook_token"
Write-Host "    - Email: mailto://user:pass@smtp.example.com"
Write-Host "    - Telegram: tgram://bot_token/chat_id"
$notify = Read-Host "Apprise-URL (leer lassen zum Überspringen)"

# TMDB API-Key
Write-Host ""
$tmdbApiKey = Read-Host "TMDB API-Key (optional, leer lassen zum Überspringen)"

# OMDb API-Key
Write-Host ""
$omdbApiKey = Read-Host "OMDb API-Key (optional, leer lassen zum Überspringen)"

# Erstelle Config-Datei
Write-Host ""
Write-Host "Erstelle Konfigurationsdatei..."
$configFile = ".perlentaucher_config.json"

$config = @{
    download_dir = $downloadDir
    limit = $limit
    loglevel = $loglevel
    sprache = $sprache
    audiodeskription = $audiodeskription
    state_file = $stateFile
    no_state = $noState
    notify = $notify
    tmdb_api_key = $tmdbApiKey
    omdb_api_key = $omdbApiKey
} | ConvertTo-Json

$config | Set-Content -Path $configFile -Encoding UTF8
Write-Host "✓ Konfiguration gespeichert: $configFile" -ForegroundColor Green

# Erstelle Wrapper-Script (Batch)
Write-Host ""
Write-Host "Erstelle Wrapper-Script..."
$wrapperScript = "run_perlentaucher.bat"

# Erstelle Python-Helper-Script für Batch
$helperScript = "run_perlentaucher_helper.py"
$helperContent = @'
import json
import sys

try:
    with open('.perlentaucher_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    args = []
    args.append(f"--download-dir")
    args.append(config['download_dir'])
    args.append("--limit")
    args.append(str(config['limit']))
    args.append("--loglevel")
    args.append(config['loglevel'])
    args.append("--sprache")
    args.append(config['sprache'])
    args.append("--audiodeskription")
    args.append(config['audiodeskription'])
    
    if config['no_state']:
        args.append("--no-state")
    else:
        args.append("--state-file")
        args.append(config['state_file'])
    
    if config.get('notify'):
        args.append("--notify")
        args.append(config['notify'])
    
    if config.get('tmdb_api_key'):
        args.append("--tmdb-api-key")
        args.append(config['tmdb_api_key'])
    
    if config.get('omdb_api_key'):
        args.append("--omdb-api-key")
        args.append(config['omdb_api_key'])
    
    print(' '.join(f'"{arg}"' if ' ' in arg or arg.startswith('--') == False else arg for arg in args))
except Exception as e:
    print(f"Fehler beim Lesen der Konfiguration: {e}", file=sys.stderr)
    sys.exit(1)
'@
$helperContent | Set-Content -Path $helperScript -Encoding UTF8

$wrapperContent = @"
@echo off
REM Wrapper-Script für Perlentaucher
REM Liest Konfiguration und startet das Hauptprogramm

cd /d "%~dp0"

if not exist ".perlentaucher_config.json" (
    echo Fehler: Konfigurationsdatei .perlentaucher_config.json nicht gefunden!
    echo Führe zuerst das Quickstart-Script aus: .\scripts\quickstart.ps1
    exit /b 1
)

REM Aktiviere virtuelle Umgebung falls vorhanden
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Lese Argumente aus Python-Helper
for /f "delims=" %%i in ('python run_perlentaucher_helper.py') do set ARGS=%%i

REM Starte Perlentaucher
python perlentaucher.py %ARGS%
"@

$wrapperContent | Set-Content -Path $wrapperScript -Encoding ASCII
Write-Host "✓ Wrapper-Script erstellt: $wrapperScript" -ForegroundColor Green

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setup abgeschlossen!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starten mit:"
if ($venvActive -or (Test-Path ".venv")) {
    Write-Host "  .\.venv\Scripts\Activate.ps1"
}
Write-Host "  .\run_perlentaucher.bat"
Write-Host ""
Write-Host "Oder manuell:"
Write-Host "  python perlentaucher.py [Optionen]"
Write-Host ""

