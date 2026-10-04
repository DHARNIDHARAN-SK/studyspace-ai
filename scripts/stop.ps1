<#
.SYNOPSIS
  StudySpace AI — Canonical Local Teardown Script
.DESCRIPTION
  Gracefully tears down Docker services and frees local ports.
#>

[CmdletBinding()]
param(
    [switch]$Volumes
)

$ErrorActionPreference = "Continue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "        StudySpace AI — Service Teardown Sequence         " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$composeFile = "infra/compose/docker-compose.yml"
if (Test-Path $composeFile) {
    Write-Host "`nStopping Docker services..." -ForegroundColor Yellow
    if ($Volumes) {
        docker compose -f $composeFile down -v
    } else {
        docker compose -f $composeFile down
    }
}

Write-Host "`nAll StudySpace AI services have stopped cleanly." -ForegroundColor Green
