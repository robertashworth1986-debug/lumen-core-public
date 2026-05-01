param(
    [ValidateSet("hybrid", "advanced", "hyperfire", "apex", "breakout", "triplet",
                 "renparity", "tiger", "citpod_lumen", "allweather_lumen", "aqr_factor", "millennium_gate",
                 "lumenstyle", "lumenstradigy")]
    [string]$Profile = "hybrid",
    [double]$Interval = 10,
    [double]$SeedCapital = 10000,
    [switch]$ResetState,
    [switch]$Institutional,
    [switch]$Restart,
    [switch]$Detach
)

$ErrorActionPreference = "Stop"

$ROOT = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$CODE = Join-Path $ROOT "code"
$PY = Join-Path $CODE ".venv\Scripts\python.exe"
if (-not (Test-Path $PY)) {
    $PY = "python"
}

$Script = Join-Path $CODE "multi_exchange_paper_ticker.py"
if (-not (Test-Path $Script)) {
    throw "Missing script: $Script"
}

if ($Institutional) {
    if (-not $PSBoundParameters.ContainsKey("Profile")) {
        $Profile = "apex"
    }
    if (-not $PSBoundParameters.ContainsKey("SeedCapital")) {
        $SeedCapital = 250000
    }
}

$LockFile = Join-Path $CODE ".multi_exchange_paper_ticker.lock"

function Get-TickerProcesses {
    Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -match "multi_exchange_paper_ticker.py" }
}

function Stop-TickerProcesses {
    $procs = Get-TickerProcesses
    foreach ($p in $procs) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
    return $procs
}

if ($Restart) {
    Write-Host "Restart requested: stopping existing ticker processes..." -ForegroundColor Yellow
    [void](Stop-TickerProcesses)
    if (Test-Path $LockFile) {
        Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
    }
}

$existing = @(Get-TickerProcesses)
if ($existing.Count -gt 0) {
    Write-Host "Ticker already running. Refusing duplicate launch." -ForegroundColor Yellow
    $existing | Select-Object ProcessId, CommandLine | Format-List | Out-Host
    Write-Host "Use -Restart to replace existing process." -ForegroundColor Yellow
    exit 0
}

Write-Host "Starting multi-exchange paper ticker..." -ForegroundColor Cyan
Write-Host "Python: $PY"
Write-Host "Script: $Script"
Write-Host "Profile: $Profile"
Write-Host "Interval: $Interval"
Write-Host "Seed Capital: $SeedCapital"
Write-Host "Artifacts: status/report/hash, institutional dashboard HTML, executive brief PDF, and paper ledgers"

$argsList = @($Script, "--interval", "$Interval", "--profile", $Profile, "--seed-capital", "$SeedCapital")
if ($ResetState) {
    $argsList += "--reset-paper-state"
}
if ($Detach) {
    $proc = Start-Process -FilePath $PY -ArgumentList $argsList -WorkingDirectory $CODE -PassThru
    Write-Host "Detached ticker started with PID $($proc.Id)." -ForegroundColor Green
    exit 0
}

& $PY @argsList