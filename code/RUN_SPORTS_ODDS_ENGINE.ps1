<#
.SYNOPSIS
    Launch the Sports Odds Engine daemon.

.DESCRIPTION
    Scans all sports_data/*_live_odds.json files for:
      - Cross-bookmaker price-dispersion candidates (not a guaranteed outcome)
      - Statistical value signals (significant edge vs consensus market price)
      - Line gaps (extreme price dispersion / steam moves)

    Outputs to:
      out/sports_signals/_live_signals.json
      out/sports_signals/_arbitrage_only.json
      out/sports_signals/_value_bets.json
      out/sports_states/_sports_summary.json

.PARAMETER ScanSec
    Seconds between full re-scans (default: 30)

.PARAMETER ValueEdgeMin
    Minimum value edge % vs consensus to flag a statistical value signal (default: 4.0)

.PARAMETER TopN
    How many signals to keep in _live_signals.json (default: 50)

.PARAMETER Once
    Run a single scan and exit (no daemon loop)

.PARAMETER Detach
    Launch in a new visible window and return immediately

.EXAMPLE
    .\code\RUN_SPORTS_ODDS_ENGINE.ps1
    .\code\RUN_SPORTS_ODDS_ENGINE.ps1 -ScanSec 15 -ValueEdgeMin 3.0
    .\code\RUN_SPORTS_ODDS_ENGINE.ps1 -Once
    .\code\RUN_SPORTS_ODDS_ENGINE.ps1 -Detach
#>

param(
    [int]   $ScanSec      = 30,
    [double]$ValueEdgeMin = 4.0,
    [int]   $TopN         = 50,
    [switch]$Once,
    [switch]$Detach
)

$Root   = Split-Path $PSScriptRoot -Parent
if (-not $Root) { $Root = "C:\LumaTrader\INSTITUTIONAL_STACK_V2" }

$Python = "$Root\code\.venv\Scripts\python.exe"
$Script = "$Root\code\sports_odds_engine.py"
$LogDir = "$Root\out\sports_signals"

if (-not (Test-Path $Python)) {
    Write-Error "Python venv not found: $Python"
    exit 1
}
if (-not (Test-Path $Script)) {
    Write-Error "Engine script not found: $Script"
    exit 1
}

# Ensure output dirs exist
New-Item -ItemType Directory -Force -Path $LogDir              | Out-Null
New-Item -ItemType Directory -Force -Path "$Root\out\sports_states" | Out-Null

$env:SPORTS_SCAN_SEC      = "$ScanSec"
$env:SPORTS_VALUE_EDGE_MIN = "$ValueEdgeMin"
$env:SPORTS_TOP_N         = "$TopN"

$Args = @()
if ($Once) { $Args += "--once" }

if ($Detach) {
    $procArgs = $Args -join " "
    $cmd = """$Python"" ""$Script"" $procArgs"
    Write-Host "[SportsOddsEngine] Launching detached window..."
    Start-Process powershell -ArgumentList "-NoExit", "-Command",
        "`$env:SPORTS_SCAN_SEC='$ScanSec'; `$env:SPORTS_VALUE_EDGE_MIN='$ValueEdgeMin'; `$env:SPORTS_TOP_N='$TopN'; & '$Python' '$Script' $procArgs" `
        -WindowStyle Normal
    Write-Host "[SportsOddsEngine] Detached. Monitor output at:"
    Write-Host "  $LogDir\_live_signals.json"
    Write-Host "  $LogDir\_arbitrage_only.json"
    Write-Host "  $Root\out\sports_states\_sports_summary.json"
} else {
    Write-Host "================================================="
    Write-Host "  Sports Odds Engine"
    Write-Host "  Scan interval : ${ScanSec}s"
    Write-Host "  Value edge min: ${ValueEdgeMin}%"
    Write-Host "  Top N signals : $TopN"
    if ($Once) { Write-Host "  Mode          : SINGLE SCAN" }
    else       { Write-Host "  Mode          : DAEMON LOOP (Ctrl+C to stop)" }
    Write-Host "================================================="
    & $Python $Script @Args
}
