#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Baut das Perlentaucher-Docker-Image, speichert es als Tar, kopiert es per scp
    auf einen Unraid-Host und führt dort "docker load" aus.

.DESCRIPTION
    Voraussetzung: docker, ssh, scp (OpenSSH-Client); passwortloser SSH-Zugang empfohlen.

.EXAMPLE
    .\scripts\build-and-deploy-unraid.ps1

.EXAMPLE
    $env:REMOTE_HOST = "root@192.168.177.5"; $env:REMOTE_DIR = "/mnt/user/appdata/foo"; $env:IMAGE_TAG = "perlentaucher:dev"; .\scripts\build-and-deploy-unraid.ps1
#>

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

$RemoteHost = if ($env:REMOTE_HOST) { $env:REMOTE_HOST } else { "root@192.168.177.5" }
$RemoteDir = if ($env:REMOTE_DIR) { $env:REMOTE_DIR } else { "/mnt/user/appdata/perlentaucher-branch-test" }
$ImageTag = if ($env:IMAGE_TAG) { $env:IMAGE_TAG } else { "perlentaucher:branch-test" }
$TarName = if ($env:TAR_NAME) { $env:TAR_NAME } else { "perlentaucher-branch.tar" }
$TarPath = if ($env:TAR_PATH) { $env:TAR_PATH } else { Join-Path $Root $TarName }

Write-Host "==> Build-Kontext: $Root"
Write-Host "==> Image:        $ImageTag"
Write-Host "==> Ziel:         ${RemoteHost}:${RemoteDir}/${TarName}"

try {
    docker build -t $ImageTag -f docker/Dockerfile .

    Write-Host "==> docker save → $TarPath"
    docker save $ImageTag -o $TarPath

    Write-Host "==> ssh: Verzeichnis anlegen"
    ssh $RemoteHost "mkdir -p '$RemoteDir'"

    Write-Host "==> scp: Tar kopieren"
    scp $TarPath "${RemoteHost}:${RemoteDir}/${TarName}"

    Write-Host "==> ssh: docker load"
    ssh $RemoteHost "docker load -i '$RemoteDir/$TarName'"
}
finally {
    if (Test-Path -LiteralPath $TarPath) {
        Remove-Item -LiteralPath $TarPath -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "==> Fertig. Image auf $RemoteHost geladen ($ImageTag)."
Write-Host ""
Write-Host "WICHTIG: Nur 'docker restart' reicht nicht — der Container nutzt weiter die alte Image-ID." -ForegroundColor Yellow
Write-Host "         Container neu anlegen, z. B.:" -ForegroundColor Yellow
Write-Host "           docker compose -f <dein-compose.yml> up -d --force-recreate" -ForegroundColor Cyan
Write-Host "         oder Docker-UI: Container stoppen, entfernen, mit gleichem Tag neu erstellen." -ForegroundColor Cyan
