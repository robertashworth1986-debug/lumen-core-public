param(
    [switch]$Detach,
    [int]$Port = 7700,
    [int]$InfraRefreshSeconds = 30
)

$ErrorActionPreference = "Stop"

$ROOT = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$CODE = Join-Path $ROOT "code"
$PY_CANDIDATES = @(
    (Join-Path $ROOT ".venv\Scripts\python.exe"),
    (Join-Path $CODE ".venv\Scripts\python.exe")
)
$PY = $PY_CANDIDATES | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $PY) { $PY = "python" }

$SectorServer = Join-Path $CODE "execution\sector_opp_gain_server.py"
$CrossSectorRun = Join-Path $CODE "execution\run_cross_sector_intel.py"
$InfraDash = Join-Path $CODE "execution\build_infra_audit_dashboard.py"

function Get-WorkerProcess {
    param([string]$CommandPattern)

    @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -like 'python*' -and $_.CommandLine -like $CommandPattern
    })
}

if (-not (Test-Path $SectorServer)) { throw "Missing: $SectorServer" }
if (-not (Test-Path $CrossSectorRun)) { throw "Missing: $CrossSectorRun" }
if (-not (Test-Path $InfraDash)) { throw "Missing: $InfraDash" }

Write-Host "Cross-sector intelligence stack launcher" -ForegroundColor Cyan
Write-Host "Python: $PY"
Write-Host "Sector URL: http://127.0.0.1:$Port"

# Refresh cross-sector outputs once before serving.
& $PY $CrossSectorRun
& $PY $InfraDash

if ($Detach) {
    $started = New-Object System.Collections.Generic.List[string]
    $skipped = New-Object System.Collections.Generic.List[string]

    if ((Get-WorkerProcess '*execution.sector_opp_gain_server:app*').Count -eq 0) {
        Start-Process -FilePath $PY -ArgumentList @("-m", "uvicorn", "execution.sector_opp_gain_server:app", "--host", "127.0.0.1", "--port", "$Port") -WorkingDirectory $CODE | Out-Null
        $started.Add('sector API') | Out-Null
    } else {
        $skipped.Add('sector API') | Out-Null
    }

    if ((Get-WorkerProcess '*build_infra_audit_dashboard.py*--loop*').Count -eq 0) {
        Start-Process -FilePath $PY -ArgumentList @($InfraDash, "--loop", "--interval", "$InfraRefreshSeconds") -WorkingDirectory $CODE | Out-Null
        $started.Add('infra dashboard loop') | Out-Null
    } else {
        $skipped.Add('infra dashboard loop') | Out-Null
    }

    Write-Host ("Detached mode started: " + ($(if ($started.Count) { $started -join ', ' } else { 'none' }))) -ForegroundColor Green
    if ($skipped.Count) {
        Write-Host ("Already running: " + ($skipped -join ', ')) -ForegroundColor Yellow
    }
    exit 0
}

Write-Host "Starting sector opportunity API in foreground (Ctrl+C to stop)..." -ForegroundColor Yellow
& $PY -m uvicorn execution.sector_opp_gain_server:app --host 127.0.0.1 --port $Port
