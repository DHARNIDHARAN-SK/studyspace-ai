<#
.SYNOPSIS
  StudySpace AI - Canonical Local Teardown Script
.DESCRIPTION
  Gracefully tears down Docker services and frees local ports.
#>

[CmdletBinding()]
param(
    [switch]$Volumes
)

$ErrorActionPreference = "Continue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "        StudySpace AI - Service Teardown Sequence         " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$composeFile = "infra/compose/docker-compose.yml"
$dockerRunning = $false
try {
    docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { $dockerRunning = $true }
} catch {
    $dockerRunning = $false
}

if ($dockerRunning -and (Test-Path $composeFile)) {
    Write-Host "`nStopping Docker services..." -ForegroundColor Yellow
    if ($Volumes) {
        docker compose -f $composeFile down -v
    } else {
        docker compose -f $composeFile down
    }
} else {
    Write-Host "`nDocker daemon not detected. Checking for local processes..." -ForegroundColor Yellow
}

# Stop local FastAPI backend process on port 8000 if running
$backendConns = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($backendConns) {
    $backendPids = $backendConns | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($p in $backendPids) {
        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
    }
    Write-Host "  -> Stopped local backend process on port 8000." -ForegroundColor Green
}

# Stop local Web Frontend process on port 3000 if running
$frontendConns = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue
if ($frontendConns) {
    $frontendPids = $frontendConns | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($p in $frontendPids) {
        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
    }
    Write-Host "  -> Stopped local frontend process on port 3000." -ForegroundColor Green
}

Write-Host "`nAll StudySpace AI services have stopped cleanly." -ForegroundColor Green
