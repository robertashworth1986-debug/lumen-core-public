$ErrorActionPreference = "Stop"

$ROOT = "c:\LumaTrader\INSTITUTIONAL_STACK_V2"
$CODE = Join-Path $ROOT "code"
$LAMASCOUT = Join-Path $ROOT "LamaScout"
$OUT_EXEC = Join-Path $ROOT "out\execution"
$LOCK_FILE = Join-Path $OUT_EXEC ".kraken_swing_hunter.lock"
$TICKER_LOCK_FILE = Join-Path $CODE ".multi_exchange_paper_ticker.lock"
$TICKER_RUNNER = Join-Path $CODE "RUN_MULTI_EXCHANGE_PAPER_TICKER.ps1"
$INSTITUTIONAL_DASHBOARD_RUNNER = Join-Path $CODE "RUN_INSTITUTIONAL_CRYPTO_DASHBOARD.ps1"
$INSTITUTIONAL_DASHBOARD_HEALTHCHECK_RUNNER = Join-Path $CODE "RUN_INSTITUTIONAL_DASHBOARD_HEALTHCHECK.ps1"
$INSTITUTIONAL_DASHBOARD_PORT = 5016
$INSTITUTIONAL_DASHBOARD_HEARTBEAT = Join-Path $OUT_EXEC "institutional_crypto_dashboard_heartbeat.json"
$INSTITUTIONAL_DASHBOARD_STALE_SECONDS = 180
$INSTITUTIONAL_DASHBOARD_REFRESH_SECONDS = 15
$INSTITUTIONAL_DASHBOARD_HEALTH_LATEST = Join-Path $OUT_EXEC "institutional_crypto_dashboard_health_latest.json"
$INSTITUTIONAL_DASHBOARD_HEALTH_HISTORY = Join-Path $OUT_EXEC "institutional_crypto_dashboard_health_history.jsonl"
$MASTER_CONTEXT_RUNNER = Join-Path $CODE "RUN_BUILD_MASTER_CONTEXT_SNAPSHOT.ps1"

$PY_CODE = Join-Path $CODE ".venv\Scripts\python.exe"
$PY_ROOT = Join-Path $ROOT ".venv\Scripts\python.exe"

if (Test-Path $PY_CODE) {
    $PY = $PY_CODE
} elseif (Test-Path $PY_ROOT) {
    $PY = $PY_ROOT
} else {
    Write-Error "No Python virtual environment found at $PY_CODE or $PY_ROOT"
    exit 1
}

Write-Host "[AUTO] Using Python: $PY"

function Get-TickerProcesses {
    Get-CimInstance Win32_Process |
        Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -like "*multi_exchange_paper_ticker.py*" }
}

function Get-InstitutionalDashboardProcesses {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -eq "python.exe" -and
            $_.CommandLine -like "*build_institutional_crypto_paper_dashboard.py*" -and
            $_.CommandLine -like "*--mode serve*"
        }
}

function Get-InstitutionalDashboardHeartbeat {
    if (-not (Test-Path $INSTITUTIONAL_DASHBOARD_HEARTBEAT)) {
        return $null
    }

    try {
        return Get-Content $INSTITUTIONAL_DASHBOARD_HEARTBEAT -Raw | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Test-InstitutionalDashboardHealthy {
    $heartbeat = Get-InstitutionalDashboardHeartbeat
    if ($null -eq $heartbeat) {
        return $false
    }

    if ($heartbeat.status -ne "ok") {
        return $false
    }

    $mode = [string]$heartbeat.mode
    $portOk = $true
    if ($mode -eq "serve") {
        $portOk = ([int]$heartbeat.port -eq $INSTITUTIONAL_DASHBOARD_PORT)
    } elseif ($mode -eq "export") {
        $portOk = $true
    } else {
        return $false
    }

    if (-not $portOk) {
        return $false
    }

    try {
        $beatTime = [datetimeoffset]::Parse($heartbeat.timestamp_utc)
        $age = ([datetimeoffset]::UtcNow - $beatTime).TotalSeconds
        return ($age -le $INSTITUTIONAL_DASHBOARD_STALE_SECONDS)
    } catch {
        return $false
    }
}

function Test-InstitutionalDashboardHttpHealthy {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$INSTITUTIONAL_DASHBOARD_PORT" -UseBasicParsing -TimeoutSec 5
        if ($resp.StatusCode -ne 200) {
            return $false
        }
        $body = [string]$resp.Content
        return ($body -like "*Nobel Tier Institutional Crypto Deck*")
    } catch {
        return $false
    }
}

function Invoke-InstitutionalDashboardHealthcheck {
    if (-not (Test-Path $INSTITUTIONAL_DASHBOARD_HEALTHCHECK_RUNNER)) {
        return @{ healthy = $false; reason = "missing_healthcheck_runner" }
    }

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $INSTITUTIONAL_DASHBOARD_HEALTHCHECK_RUNNER `
        -BindHost "127.0.0.1" `
        -Port $INSTITUTIONAL_DASHBOARD_PORT `
        -MaxHeartbeatAgeSeconds $INSTITUTIONAL_DASHBOARD_STALE_SECONDS `
        -LatestFile $INSTITUTIONAL_DASHBOARD_HEALTH_LATEST `
        -HistoryFile $INSTITUTIONAL_DASHBOARD_HEALTH_HISTORY `
        -Quiet

    $ok = ($LASTEXITCODE -eq 0)
    if (-not (Test-Path $INSTITUTIONAL_DASHBOARD_HEALTH_LATEST)) {
        return @{ healthy = $false; reason = "missing_health_artifact" }
    }

    try {
        $payload = Get-Content $INSTITUTIONAL_DASHBOARD_HEALTH_LATEST -Raw | ConvertFrom-Json
        return @{ healthy = $ok; payload = $payload }
    } catch {
        return @{ healthy = $ok; reason = "unreadable_health_artifact" }
    }
}

function Ensure-InstitutionalTickerRunning {
    $ticker = @(Get-TickerProcesses)
    if ($ticker.Count -gt 0) {
        Write-Host "[AUTO] Institutional paper ticker already running"
        return
    }

    if (Test-Path $TICKER_LOCK_FILE) {
        Remove-Item $TICKER_LOCK_FILE -Force -ErrorAction SilentlyContinue
    }

    if (-not (Test-Path $TICKER_RUNNER)) {
        Write-Warning "[AUTO] Missing ticker runner: $TICKER_RUNNER"
        return
    }

    Write-Host "[AUTO] Starting institutional paper ticker (detached)..."
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $TICKER_RUNNER,
        "-Institutional",
        "-Detach"
    ) -WorkingDirectory $CODE -WindowStyle Minimized | Out-Null
}

function Ensure-InstitutionalDashboardRunning {
    $dashboard = @(Get-InstitutionalDashboardProcesses)
    $heartbeatHealthy = Test-InstitutionalDashboardHealthy
    $httpHealthy = Test-InstitutionalDashboardHttpHealthy
    $healthcheck = Invoke-InstitutionalDashboardHealthcheck
    $externalHealthy = $false
    if ($healthcheck.ContainsKey("healthy")) {
        $externalHealthy = [bool]$healthcheck.healthy
    }

    if ($dashboard.Count -gt 0 -and $heartbeatHealthy -and $httpHealthy -and $externalHealthy) {
        Write-Host "[AUTO] Institutional crypto dashboard already running with healthy heartbeat and HTTP response"
        return
    }

    if ($dashboard.Count -gt 0 -and (-not $heartbeatHealthy -or -not $httpHealthy -or -not $externalHealthy)) {
        Write-Warning "[AUTO] Institutional crypto dashboard unhealthy (heartbeat/http/healthcheck); restarting"
        foreach ($proc in $dashboard) {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }

    if (-not (Test-Path $INSTITUTIONAL_DASHBOARD_RUNNER)) {
        Write-Warning "[AUTO] Missing institutional dashboard runner: $INSTITUTIONAL_DASHBOARD_RUNNER"
        return
    }

    Write-Host "[AUTO] Starting institutional crypto dashboard (detached)..."
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $INSTITUTIONAL_DASHBOARD_RUNNER,
        "-Mode", "serve",
        "-BindHost", "127.0.0.1",
        "-Port", "$INSTITUTIONAL_DASHBOARD_PORT",
        "-RefreshSeconds", "$INSTITUTIONAL_DASHBOARD_REFRESH_SECONDS",
        "-Detach"
    ) -WorkingDirectory $CODE -WindowStyle Minimized | Out-Null

    Start-Sleep -Seconds 4
    $postRestart = Invoke-InstitutionalDashboardHealthcheck
    if ($postRestart.ContainsKey("healthy") -and [bool]$postRestart.healthy) {
        Write-Host "[AUTO] Institutional crypto dashboard restart validated by healthcheck"
    } else {
        Write-Warning "[AUTO] Institutional crypto dashboard restart did not pass healthcheck yet"
    }
}

function Refresh-MasterContextSnapshot {
    if (-not (Test-Path $MASTER_CONTEXT_RUNNER)) {
        return
    }

    try {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $MASTER_CONTEXT_RUNNER -Quiet
    } catch {
        Write-Warning "[AUTO] Master context snapshot refresh failed: $($_.Exception.Message)"
    }
}

# 1) Hard reset swing hunter runtime to exactly one process
Write-Host "[AUTO] Killing any duplicate swing hunter processes..."
Get-CimInstance Win32_Process |
    Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -like "*kraken_swing_hunter.py*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

if (Test-Path $LOCK_FILE) {
    Remove-Item $LOCK_FILE -Force -ErrorAction SilentlyContinue
}

Write-Host "[AUTO] Starting one swing hunter process..."
$bot = Start-Process -FilePath $PY -ArgumentList ".\kraken_swing_hunter.py" -WorkingDirectory $CODE -WindowStyle Minimized -PassThru
Write-Host "[AUTO] Swing hunter PID: $($bot.Id)"

# 1b) Ensure institutional crypto paper ticker is alive for elite presentation artifacts
Ensure-InstitutionalTickerRunning

# 1c) Ensure institutional crypto live dashboard is available alongside the ticker artifacts
Ensure-InstitutionalDashboardRunning

# 1d) Keep continuity artifacts fresh for instant chat/session recovery
Refresh-MasterContextSnapshot

# 2) Boot dashboard API if not already running
$apiRunning = Get-CimInstance Win32_Process |
    Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -like "*uvicorn*src.dashboard_api:app*" }

if (-not $apiRunning) {
    Write-Host "[AUTO] Starting LamaScout API..."
    Start-Process -FilePath $PY -ArgumentList "-m uvicorn src.dashboard_api:app --host 0.0.0.0 --port 8000" -WorkingDirectory $LAMASCOUT -WindowStyle Minimized | Out-Null
} else {
    Write-Host "[AUTO] LamaScout API already running"
}

# 3) Continuous LamaScout refresh loop (every 30 minutes)
Write-Host "[AUTO] Entering zero-touch refresh loop (30 min cadence)..."
Write-Host "[AUTO] Press Ctrl+C to stop this controller"

while ($true) {
    try {
        $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

        # Keep institutional ticker alive so dashboard + executive PDF stay fresh.
        Ensure-InstitutionalTickerRunning
        Ensure-InstitutionalDashboardRunning
        Refresh-MasterContextSnapshot

        Write-Host "[AUTO][$ts] Running LamaScout pipeline..."
        Push-Location $LAMASCOUT
        & $PY -m src.artist_scout_engine
        Pop-Location

        # Generate top-10 unsigned names snapshot from production-cleaned candidates
        $prodTop10 = Join-Path $LAMASCOUT "reports\\top10_unsigned_production.csv"
        if (Test-Path $prodTop10) {
            $dest = Join-Path $LAMASCOUT "reports\\top10_unsigned_snapshot.csv"
            Copy-Item $prodTop10 $dest -Force
            Write-Host "[AUTO][$ts] Wrote production top10 snapshot -> $dest"
        }

        # Health ping (with short retry window)
        $healthy = $false
        for ($i = 0; $i -lt 10; $i++) {
            try {
                $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 5
                Write-Host "[AUTO][$ts] API health: $($health.status)"
                $healthy = $true
                break
            } catch {
                Start-Sleep -Seconds 2
            }
        }
        if (-not $healthy) {
            Write-Warning "[AUTO][$ts] API health check failed after retries"
        }

    } catch {
        if ($PWD.Path -ne $CODE) {
            try { Pop-Location } catch {}
        }
        Write-Warning "[AUTO] Pipeline loop error: $($_.Exception.Message)"
    }

    Start-Sleep -Seconds 1800
}
