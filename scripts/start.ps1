<#
.SYNOPSIS
  StudySpace AI — Canonical Local Startup Script
.DESCRIPTION
  Launches all required local services:
  1. Ollama model verification (nomic-embed-text:latest, phi4-mini:latest)
  2. Multi-container orchestration (PostgreSQL 16 pgvector, Redis 7, FastAPI, Web UI)
  3. Health validation and service accessibility status
#>

[CmdletBinding()]
param(
    [switch]$LocalProcesses,
    [switch]$NoBuild
)

$ErrorActionPreference = "Continue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "        StudySpace AI — Service Startup Sequence          " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Ollama
Write-Host "`n[1/4] Checking Ollama Local LLM & Embedding Service..." -ForegroundColor Yellow
try {
    $ollamaCheck = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 3 -ErrorAction Stop
    $models = $ollamaCheck.models | ForEach-Object { $_.name }
    Write-Host "  -> Ollama is online." -ForegroundColor Green

    $requiredModels = @("nomic-embed-text:latest", "phi4-mini:latest")
    foreach ($m in $requiredModels) {
        if ($models -contains $m -or $models -contains ($m -replace ":latest", "")) {
            Write-Host "  -> Verified model: $m" -ForegroundColor Green
        } else {
            Write-Host "  [!] Warning: Model '$m' not found in local Ollama list." -ForegroundColor Yellow
            Write-Host "      Run: 'ollama pull $m' to install." -ForegroundColor DarkGray
        }
    }
} catch {
    Write-Host "  [!] Warning: Ollama not reachable at http://localhost:11434. Local inference may fail open." -ForegroundColor Yellow
    Write-Host "      Start Ollama desktop app or run 'ollama serve'." -ForegroundColor DarkGray
}

# 2. Start Services via Docker Compose
Write-Host "`n[2/4] Starting StudySpace AI Services via Docker Compose..." -ForegroundColor Yellow

$composeFile = "infra/compose/docker-compose.yml"
if (-not (Test-Path $composeFile)) {
    Write-Host "  [ERROR] Compose file not found at $composeFile!" -ForegroundColor Red
    exit 1
}

$dockerRunning = $false
try {
    docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { $dockerRunning = $true }
} catch {
    $dockerRunning = $false
}

if ($dockerRunning -and -not $LocalProcesses) {
    Write-Host "  -> Docker daemon detected. Bringing up services..." -ForegroundColor Green
    if ($NoBuild) {
        docker compose -f $composeFile up -d
    } else {
        docker compose -f $composeFile up -d --build
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [!] Docker compose failed. Falling back to local process inspection." -ForegroundColor Yellow
    }
} else {
    Write-Host "  -> Docker not detected or -LocalProcesses specified." -ForegroundColor Yellow
    Write-Host "  -> Starting background FastAPI (.venv) and Vite frontend..." -ForegroundColor Cyan

    # Start FastAPI backend if not already on 8000
    $backendPort = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    if (-not $backendPort) {
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd services/api; ..\..\.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
        Write-Host "  -> Launched FastAPI backend on port 8000." -ForegroundColor Green
    } else {
        Write-Host "  -> Port 8000 already active." -ForegroundColor Green
    }

    # Start Vite frontend if not already on 3000/5173
    $frontendPort = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue
    if (-not $frontendPort) {
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd apps/web; npm.cmd run dev"
        Write-Host "  -> Launched Web Frontend on port 3000 / 5173." -ForegroundColor Green
    } else {
        Write-Host "  -> Frontend port already active." -ForegroundColor Green
    }
}

# 3. Health Checks
Write-Host "`n[3/4] Validating Backend API Health..." -ForegroundColor Yellow
$apiHealthy = $false
$retries = 15
while ($retries -gt 0) {
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
        if ($health.status -eq "ok" -or $health.status -eq "healthy") {
            $apiHealthy = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 2
        $retries--
    }
}

if ($apiHealthy) {
    Write-Host "  -> Backend API probe passed: status=ok (http://localhost:8000/api/v1/health)" -ForegroundColor Green
} else {
    Write-Host "  [!] Backend API is still initializing or offline. Check container/service logs." -ForegroundColor Yellow
}

# 4. Service Directory & Access Endpoints
Write-Host "`n[4/4] StudySpace AI Ready — Access Endpoints:" -ForegroundColor Cyan
Write-Host "----------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "  Web Frontend:        http://localhost:3000" -ForegroundColor White
Write-Host "  Backend API:         http://localhost:8000" -ForegroundColor White
Write-Host "  Swagger UI Docs:     http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Health Probe:        http://localhost:8000/api/v1/health" -ForegroundColor White
Write-Host "  Ollama Local LLM:    http://localhost:11434" -ForegroundColor White
Write-Host "----------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "To stop all services: .\scripts\stop.ps1`n" -ForegroundColor DarkCyan
