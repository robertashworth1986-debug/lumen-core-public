# ═══════════════════════════════════════════════════════════════════════════
#  LumenCore — Sector Opportunity Gain Dashboard Launcher
#  Port  : 7700
#  Opens : http://localhost:7700
# ═══════════════════════════════════════════════════════════════════════════

param(
    [switch]$Detach,
    [int]$Port = 7700
)

$ErrorActionPreference = 'Stop'
# Script lives in code\ — PSScriptRoot IS the code folder
$CODE = $PSScriptRoot
$ROOT = Split-Path $CODE -Parent

# ── Python venv ──────────────────────────────────────────────────────────────
$VENV_PYTHON = Join-Path $CODE '.venv\Scripts\python.exe'
if (-not (Test-Path $VENV_PYTHON)) {
    $VENV_PYTHON = Join-Path $ROOT 'code\.venv\Scripts\python.exe'
}
if (-not (Test-Path $VENV_PYTHON)) {
    Write-Warning "venv python not found; falling back to system python"
    $VENV_PYTHON = 'python'
}

$SERVER_SCRIPT = Join-Path $CODE 'execution\sector_opp_gain_server.py'

if (-not (Test-Path $SERVER_SCRIPT)) {
    Write-Error "Server script not found: $SERVER_SCRIPT"
    exit 1
}

Write-Host ""
Write-Host "  ⚡  LumenCore Sector Opportunity Gain Dashboard" -ForegroundColor Cyan
Write-Host "  ─────────────────────────────────────────────────"
Write-Host "  Server  : $SERVER_SCRIPT"
Write-Host "  Python  : $VENV_PYTHON"
Write-Host "  Port    : $Port"
Write-Host "  Browser : http://localhost:$Port"
Write-Host ""

$existingServer = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -like 'python*' -and $_.CommandLine -like '*execution.sector_opp_gain_server:app*'
})

if ($Detach) {
    if ($existingServer.Count -gt 0) {
        Write-Host "  [SKIP] Sector API already running in background." -ForegroundColor Yellow
        exit 0
    }

    # Launch detached process (no console window steal)
    Start-Process `
        -FilePath $VENV_PYTHON `
        -ArgumentList "-m uvicorn execution.sector_opp_gain_server:app --host 0.0.0.0 --port $Port" `
        -WorkingDirectory $CODE `
        -WindowStyle Minimized

    Write-Host "  [DETACHED] Server started in background." -ForegroundColor Green
    Start-Sleep -Seconds 2
} else {
    if ($existingServer.Count -gt 0) {
        Write-Host "  Existing sector API detected on port $Port; opening browser without launching another server." -ForegroundColor Yellow
        Start-Process "http://localhost:$Port"
        exit 0
    }

    # Launch server in background job so we can open the browser
    Write-Host "  Starting server…" -ForegroundColor Yellow

    $job = Start-Job -ScriptBlock {
        param($py, $code, $port)
        Set-Location $code
        & $py -m uvicorn execution.sector_opp_gain_server:app --host 0.0.0.0 --port $port 2>&1
    } -ArgumentList $VENV_PYTHON, $CODE, $Port

    # Wait for server to become ready (up to 12s)
    $ready = $false
    for ($i = 0; $i -lt 24; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $null = Invoke-WebRequest -Uri "http://localhost:$Port/api/tick" -UseBasicParsing -TimeoutSec 1
            $ready = $true
            break
        } catch { }
    }

    if ($ready) {
        Write-Host "  Server ready." -ForegroundColor Green
    } else {
        Write-Host "  Server may still be starting — opening browser anyway." -ForegroundColor Yellow
    }

    # Open browser
    Start-Process "http://localhost:$Port"
    Write-Host "  Browser opened → http://localhost:$Port" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  [Press Ctrl+C to stop]" -ForegroundColor Magenta
    Write-Host ""

    # Stream server output to console until stopped
    try {
        while ($true) {
            $out = Receive-Job $job 2>&1
            if ($out) { $out | ForEach-Object { Write-Host "  $_" } }

            if ($job.State -eq 'Failed' -or $job.State -eq 'Stopped') {
                Write-Host "  Server process ended (state: $($job.State))." -ForegroundColor Red
                break
            }
            Start-Sleep -Milliseconds 800
        }
    } finally {
        Remove-Job $job -Force -ErrorAction SilentlyContinue
        Write-Host "  Dashboard stopped." -ForegroundColor Yellow
    }
}
