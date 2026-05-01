param(
    [switch]$RunReconnect,
    [switch]$RunEliteOptimizer,
    [string]$DashboardHost = "0.0.0.0",
    [int]$DashboardPort = 5016,
    [double]$DashboardRefreshSeconds = 15,
    [string]$LamaHost = "0.0.0.0",
    [int]$LamaPort = 8000
)

$ErrorActionPreference = "Stop"

$ROOT = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$CODE = Join-Path $ROOT "code"
$PY = Join-Path $CODE ".venv\Scripts\python.exe"
if (-not (Test-Path $PY)) {
    $PY = "python"
}

$ReconnectRunner = Join-Path $CODE "RUN_ONE_BUTTON_RECONNECT.ps1"
$EliteRunner = Join-Path $CODE "RUN_ELITE_STACK_OPTIMIZER.ps1"
$DashboardBuilder = Join-Path $CODE "execution\build_institutional_crypto_paper_dashboard.py"
$LamaIntegration = Join-Path $CODE "LAMASCOUT_INTEGRATION.py"

Write-Host "Lumen Core public stack launcher" -ForegroundColor Cyan
Write-Host "Root: $ROOT"
Write-Host "Python: $PY"

if ($RunReconnect) {
    if (Test-Path $ReconnectRunner) {
        Write-Host "Running reconnect bootstrap..." -ForegroundColor Yellow
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $ReconnectRunner -KillAllAndStartAutopilot
    } else {
        Write-Warning "Reconnect runner missing: $ReconnectRunner"
    }
}

if ($RunEliteOptimizer) {
    if (Test-Path $EliteRunner) {
        Write-Host "Running elite optimizer..." -ForegroundColor Yellow
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $EliteRunner
    } else {
        Write-Warning "Elite runner missing: $EliteRunner"
    }
}

if (Test-Path $DashboardBuilder) {
    Write-Host "Starting institutional dashboard server..." -ForegroundColor Yellow
    Start-Process -FilePath $PY -ArgumentList @(
        $DashboardBuilder,
        "--mode", "serve",
        "--host", $DashboardHost,
        "--port", "$DashboardPort",
        "--refresh-seconds", "$DashboardRefreshSeconds"
    ) -WorkingDirectory $CODE -WindowStyle Minimized | Out-Null
} else {
    Write-Warning "Dashboard builder missing: $DashboardBuilder"
}

if (Test-Path $LamaIntegration) {
    Write-Host "Starting LamaScout API..." -ForegroundColor Yellow
    Start-Process -FilePath $PY -ArgumentList @(
        $LamaIntegration,
        "--serve",
        "--host", $LamaHost,
        "--port", "$LamaPort"
    ) -WorkingDirectory $CODE -WindowStyle Minimized | Out-Null
} else {
    Write-Warning "Lama integration script missing: $LamaIntegration"
}

Write-Host "Public stack launch issued." -ForegroundColor Green
Write-Host ("Dashboard local URL: http://127.0.0.1:{0}" -f $DashboardPort)
Write-Host ("LamaScout local URL: http://127.0.0.1:{0}/ui" -f $LamaPort)
Write-Host "Next: put Caddy in front and map lumen-core.ai DNS to this VPS."