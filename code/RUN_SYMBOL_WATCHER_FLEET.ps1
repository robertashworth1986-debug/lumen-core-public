# RUN_SYMBOL_WATCHER_FLEET.ps1
# ─────────────────────────────────────────────────────────────────────────────
# Launches the per-symbol watcher fleet as a background daemon.
# Each symbol gets its own watcher agent tracking peak_high, peak_low,
# and real vs fake spike detection.  Reports feed into:
#   out/symbol_states/_fleet_summary.json   (top signals, all symbols)
#   out/symbol_states/_real_spike_alerts.json (confirmed real spikes only)
#   out/symbol_states/{SYMBOL}_state.json   (per-symbol detail)
#
# The execution_orchestrator reads _fleet_summary.json to prioritize
# symbols instead of brute-forcing all 1693 every loop.
#
# Usage:
#   .\RUN_SYMBOL_WATCHER_FLEET.ps1                    # default 8 workers, 2.5s poll
#   .\RUN_SYMBOL_WATCHER_FLEET.ps1 -Workers 12        # more workers
#   .\RUN_SYMBOL_WATCHER_FLEET.ps1 -PollSec 1.5       # faster poll cycle
#   .\RUN_SYMBOL_WATCHER_FLEET.ps1 -Detach            # run in background window
# ─────────────────────────────────────────────────────────────────────────────

param(
    [int]    $Workers  = 8,
    [float]  $PollSec  = 2.5,
    [switch] $Detach
)

$Root    = Split-Path $PSScriptRoot -Parent
$Python  = "$Root\code\.venv\Scripts\python.exe"
$Script  = "$Root\code\execution\symbol_watcher_fleet.py"
$LogFile = "$Root\out\symbol_states\_fleet_daemon.log"

# Ensure output directory exists
New-Item -ItemType Directory -Path "$Root\out\symbol_states" -Force | Out-Null

Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  LumaTrader Symbol Watcher Fleet" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Python  : $Python"
Write-Host "  Script  : $Script"
Write-Host "  Workers : $Workers"
Write-Host "  Poll    : ${PollSec}s per cycle"
Write-Host "  Log     : $LogFile"
Write-Host "  Output  : $Root\out\symbol_states\"
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan

if (-not (Test-Path $Python)) {
    Write-Host "[ERROR] Python venv not found: $Python" -ForegroundColor Red
    Write-Host "        Run: cd $Root && python -m venv code\.venv" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $Script)) {
    Write-Host "[ERROR] Fleet script not found: $Script" -ForegroundColor Red
    exit 1
}

$env:WATCHER_WORKERS  = $Workers
$env:WATCHER_POLL_SEC = $PollSec

if ($Detach) {
    Write-Host "[FLEET] Starting in detached background window..." -ForegroundColor Yellow
    $procArgs = @{
        FilePath         = "powershell.exe"
        ArgumentList     = @(
            "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-Command",
            "& '$Python' '$Script' 2>&1 | Tee-Object -FilePath '$LogFile' -Append; Read-Host 'Fleet exited. Press Enter.'"
        )
        WorkingDirectory = $Root
        WindowStyle      = "Normal"
    }
    $proc = Start-Process @procArgs -PassThru
    Write-Host "[FLEET] Fleet daemon PID: $($proc.Id)" -ForegroundColor Green
    Write-Host "[FLEET] Signals at : $Root\out\symbol_states\_fleet_summary.json" -ForegroundColor Green
    Write-Host "[FLEET] Real alerts: $Root\out\symbol_states\_real_spike_alerts.json" -ForegroundColor Green
} else {
    Write-Host "[FLEET] Starting foreground (Ctrl+C to stop)..." -ForegroundColor Yellow
    & $Python $Script 2>&1 | Tee-Object -FilePath $LogFile -Append
}
