<#
.SYNOPSIS
    LumaTrader Master Platform Launcher
    Starts all three intelligence lanes simultaneously:
      - Trading Execution Dashboard    → port 5016
      - Cross-Sector Intel API         → port 7700
      - LamaScout Artist Dashboard     → port 5017

.USAGE
    .\RUN_ALL_LANES.ps1
    .\RUN_ALL_LANES.ps1 -SkipTrading
    .\RUN_ALL_LANES.ps1 -SkipScout
    .\RUN_ALL_LANES.ps1 -SkipIntel
#>
param(
    [switch]$SkipTrading,
    [switch]$SkipIntel,
    [switch]$SkipScout
)

$ErrorActionPreference = 'Stop'

$PYTHON      = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\.venv\Scripts\python.exe"
$CODE_ROOT   = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\code"
$SCOUT_ROOT  = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\LamaScout"

$TRADING_SCRIPT = "$CODE_ROOT\execution\build_institutional_crypto_paper_dashboard.py"
$INTEL_MODULE   = "execution.sector_opp_gain_server"
$SCOUT_SCRIPT   = "$SCOUT_ROOT\src\lamascout_dashboard.py"

# ── banner ─────────────────────────────────────────────────────────────────
Clear-Host
Write-Host ""
Write-Host "  ██╗     ██╗   ██╗███╗   ███╗ █████╗ ████████╗██████╗  █████╗ ██████╗ ███████╗██████╗ " -ForegroundColor Yellow
Write-Host "  ██║     ██║   ██║████╗ ████║██╔══██╗╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗" -ForegroundColor Yellow
Write-Host "  ██║     ██║   ██║██╔████╔██║███████║   ██║   ██████╔╝███████║██║  ██║█████╗  ██████╔╝" -ForegroundColor Yellow
Write-Host "  ██║     ██║   ██║██║╚██╔╝██║██╔══██║   ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝  ██╔══██╗" -ForegroundColor Yellow
Write-Host "  ███████╗╚██████╔╝██║ ╚═╝ ██║██║  ██║   ██║   ██║  ██║██║  ██║██████╔╝███████╗██║  ██║" -ForegroundColor Yellow
Write-Host "  ╚══════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Institutional Intelligence Platform  ·  φ = 1.6180339887  ·  Three Lanes Active" -ForegroundColor Cyan
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') UTC" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  ┌─────────────────────────────────────────────────────────────┐" -ForegroundColor DarkGray
Write-Host "  │  Lane 1 · Trading Execution          http://localhost:5016  │" -ForegroundColor White
Write-Host "  │  Lane 2 · Cross-Sector Intel API     http://localhost:7700  │" -ForegroundColor White
Write-Host "  │  Lane 3 · LamaScout Artist Intel     http://localhost:5017  │" -ForegroundColor Magenta
Write-Host "  └─────────────────────────────────────────────────────────────┘" -ForegroundColor DarkGray
Write-Host ""

# ── validation ─────────────────────────────────────────────────────────────
if (-not (Test-Path $PYTHON)) {
    Write-Host "[ERROR] Python venv not found: $PYTHON" -ForegroundColor Red; exit 1
}

# ── helper: open a new PowerShell window for each lane ────────────────────
function Start-Lane {
    param(
        [string]$LaneName,
        [string]$Color,
        [string]$Command,
        [string]$WorkDir
    )
    Write-Host "  [LAUNCH] $LaneName" -ForegroundColor $Color
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "Set-Location '$WorkDir'; `$host.UI.RawUI.WindowTitle = '$LaneName'; $Command"
    )
    Start-Sleep -Milliseconds 800
}

# ── Lane 1: Trading Execution Dashboard ────────────────────────────────────
if (-not $SkipTrading) {
    $cmd = "Write-Host '  [TRADING] Starting on port 5016...' -ForegroundColor Yellow; " +
           "& '$PYTHON' -m panel serve '$TRADING_SCRIPT' " +
           "--port 5016 --address 0.0.0.0 --allow-websocket-origin=* --autoreload"
    Start-Lane -LaneName "TRADING · Port 5016" -Color "Yellow" -Command $cmd -WorkDir $CODE_ROOT
}

# ── Lane 2: Cross-Sector Intelligence API ──────────────────────────────────
if (-not $SkipIntel) {
    $cmd = "Write-Host '  [INTEL] Starting FastAPI on port 7700...' -ForegroundColor Cyan; " +
           "Set-Location '$CODE_ROOT'; " +
           "& '$PYTHON' -m uvicorn $INTEL_MODULE`:app --host 0.0.0.0 --port 7700 --reload"
    Start-Lane -LaneName "INTEL API · Port 7700" -Color "Cyan" -Command $cmd -WorkDir $CODE_ROOT
}

# ── Lane 3: LamaScout Artist Intelligence Dashboard ────────────────────────
if (-not $SkipScout) {
    $cmd = "Write-Host '  [SCOUT] Starting on port 5017...' -ForegroundColor Magenta; " +
           "& '$PYTHON' -m panel serve '$SCOUT_SCRIPT' " +
           "--port 5017 --address 0.0.0.0 --allow-websocket-origin=* --autoreload"
    Start-Lane -LaneName "SCOUT · Port 5017" -Color "Magenta" -Command $cmd -WorkDir $SCOUT_ROOT
}

Write-Host ""
Write-Host "  All lanes launched in separate windows." -ForegroundColor Green
Write-Host "  Portal landing page: $((Resolve-Path 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\dashboard\index.html').Path)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  CTRL+C in each window to stop that lane individually." -ForegroundColor DarkGray
Write-Host ""
