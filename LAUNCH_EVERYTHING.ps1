#!/usr/bin/env pwsh
# ═══════════════════════════════════════════════════════════════════════════════
#  LUMA STACK — FULL AUTO LAUNCH
#  Kills duplicates, starts supervisor, waits for health, opens all dashboards
# ═══════════════════════════════════════════════════════════════════════════════
param(
    [switch]$NoOrders,
    [switch]$NoBrowser
)

$ROOT  = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$CODE  = "$ROOT\code"
$DASH  = "C:\LumaTrader\dashboard"
$PY_CANDIDATES = @(
    "$ROOT\.venv\Scripts\python.exe",
    "$CODE\.venv\Scripts\python.exe"
)
$PY = $PY_CANDIDATES | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $PY) {
    $PY = "python"
}
$GW    = "http://localhost:8787"

Write-Host ""
Write-Host "  ██╗     ██╗   ██╗███╗   ███╗ █████╗ " -ForegroundColor Cyan
Write-Host "  ██║     ██║   ██║████╗ ████║██╔══██╗" -ForegroundColor Cyan
Write-Host "  ██║     ██║   ██║██╔████╔██║███████║" -ForegroundColor Cyan
Write-Host "  ██║     ██║   ██║██║╚██╔╝██║██╔══██║" -ForegroundColor Cyan
Write-Host "  ███████╗╚██████╔╝██║ ╚═╝ ██║██║  ██║" -ForegroundColor Cyan
Write-Host "  ╚══════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝" -ForegroundColor Cyan
Write-Host "  INSTITUTIONAL STACK V2 — FULL LAUNCH" -ForegroundColor White
Write-Host ""

# ── 1. KILL ALL DUPLICATE PYTHON PROCESSES ────────────────────────────────────
Write-Host "[1/5] Terminating all managed Python processes..." -ForegroundColor Yellow

$targets = @(
    "luma_supervisor.py",
    "luma_experience_gateway",
    "ecosystem_fabric_engine.py",
    "alpaca_paper_orchestrator.py",
    "dashboard_unified_refresh.py",
    "sector_opp_gain_server",
    "build_infra_audit_dashboard.py",
    "luma_ml_signals.py"
)

$killed = 0
Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'python.exe' -and $_.CommandLine
} | ForEach-Object {
    $cl = $_.CommandLine
    foreach ($t in $targets) {
        if ($cl -like "*$t*") {
            try {
                Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
                $killed++
            } catch {}
            break
        }
    }
}

Write-Host "   Terminated $killed process(es)" -ForegroundColor Gray

# ── 2. FREE PORTS ─────────────────────────────────────────────────────────────
Write-Host "[2/5] Freeing ports 8787 and 7701..." -ForegroundColor Yellow

foreach ($port in @(8787, 7701)) {
    $pids = (netstat -ano 2>$null | Select-String ":$port\s" | ForEach-Object {
        ($_ -split '\s+')[-1]
    } | Where-Object { $_ -match '^\d+$' } | Sort-Object -Unique)
    foreach ($p in $pids) {
        if ($p -ne "0") {
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    }
}

Start-Sleep -Milliseconds 1200

# ── 3. CLEAN UP LOCK FILES ────────────────────────────────────────────────────
Write-Host "[3/5] Clearing lock files..." -ForegroundColor Yellow
Get-ChildItem "$ROOT\run\*.lock" -ErrorAction SilentlyContinue | Remove-Item -Force
Write-Host "   Lock files cleared" -ForegroundColor Gray

# ── 4. START SUPERVISOR ───────────────────────────────────────────────────────
Write-Host "[4/5] Starting supervisor (7 services)..." -ForegroundColor Yellow

$supervisorArgs = @("$CODE\luma_supervisor.py")
if ($NoOrders) { $supervisorArgs += "--no-orders" }

$sup = Start-Process -FilePath $PY `
    -ArgumentList $supervisorArgs `
    -WorkingDirectory $CODE `
    -WindowStyle Minimized `
    -PassThru

Write-Host "   Supervisor PID: $($sup.Id)" -ForegroundColor Gray

# ── 5. WAIT FOR GATEWAY HEALTH ────────────────────────────────────────────────
Write-Host "[5/5] Waiting for gateway at $GW/health ..." -ForegroundColor Yellow

$healthy = $false
$attempts = 0
$maxAttempts = 60   # 60 × 2s = 120s timeout
$healthUris = @(
    "$GW/health",
    "http://127.0.0.1:8787/health"
)

while (-not $healthy -and $attempts -lt $maxAttempts) {
    Start-Sleep -Seconds 2
    $attempts++
    foreach ($uri in $healthUris) {
        try {
            $resp = Invoke-WebRequest -Uri $uri -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
            if ($resp.StatusCode -eq 200) {
                $healthy = $true
                $data = $resp.Content | ConvertFrom-Json -ErrorAction SilentlyContinue
                $up = if ($data.supervisor) { $data.supervisor.services_up } else { "?" }
                $total = if ($data.supervisor) { $data.supervisor.services_total } else { "?" }
                Write-Host "   Gateway HEALTHY via $uri  (services $up/$total up)" -ForegroundColor Green
                break
            }
        } catch {
            # keep trying alternate URI
        }
    }
    if (-not $healthy) {
        Write-Host "   Attempt $attempts/$maxAttempts — waiting..." -ForegroundColor DarkGray
    }
}

if (-not $healthy) {
    Write-Host "   WARNING: Gateway did not respond in time. Check supervisor output." -ForegroundColor Red
}

# ── BUILD POSITIVE PROOF PACK ────────────────────────────────────────────────
Write-Host "Building Kraken positive proof pack..." -ForegroundColor Yellow
try {
    & $PY "$CODE\build_kraken_positive_proof.py" | Out-Null
    Write-Host "   Proof pack generated" -ForegroundColor Gray
} catch {
    Write-Host "   WARNING: Proof pack build failed: $($_.Exception.Message)" -ForegroundColor Red
}

# ── OPEN ALL DASHBOARDS ───────────────────────────────────────────────────────
if (-not $NoBrowser) {
    Write-Host ""
    Write-Host "Opening dashboards in browser..." -ForegroundColor Cyan

    $pages = @(
        @{ url = "$GW/investor";                           label = "Investor Command Room"         },
        @{ url = "$GW/";                                   label = "Main Dashboard"                },
        @{ url = "$GW/api/investor/kraken-positive-proof"; label = "Kraken Positive Proof (JSON)"  },
        @{ url = "$GW/api/investor/execution-proof";       label = "Execution Proof Chain"         },
        @{ url = "$GW/health";                             label = "Health / System Status"        },
        @{ url = "$GW/metrics";                            label = "Prometheus Metrics"            },
        @{ url = "$GW/api/ml/signal";                      label = "ML Ensemble Signal"            },
        @{ url = "$GW/api/investor/brief";                 label = "Investor Brief (JSON)"         },
        @{ url = "$GW/api/system/metrics-summary";         label = "System Metrics Summary"        }
    )

    # Open local HTML dashboards from file system
    $localPages = @(
        @{ path = "$DASH\investor_command_room.html";       label = "Investor Command Room (file)" },
        @{ path = "$DASH\dashboard_analytics.html";         label = "Analytics Dashboard"          },
        @{ path = "$ROOT\dashboard\kraken_positive_proof.html"; label = "Kraken Positive Proof (file)" }
    )

    # Use Start-Process to open in default browser
    foreach ($p in $pages) {
        Write-Host "  → $($p.label)" -ForegroundColor DarkCyan
        Start-Process $p.url
        Start-Sleep -Milliseconds 400
    }

    foreach ($p in $localPages) {
        if (Test-Path $p.path) {
            Write-Host "  → $($p.label)" -ForegroundColor DarkCyan
            Start-Process $p.path
            Start-Sleep -Milliseconds 300
        }
    }

}

# ── STATUS SUMMARY ────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  LUMA STACK LAUNCH COMPLETE" -ForegroundColor White
Write-Host "══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Gateway      →  $GW" -ForegroundColor Cyan
Write-Host "  Investor UI  →  $GW/investor" -ForegroundColor Cyan
Write-Host "  ML Signals   →  $GW/api/ml/signal" -ForegroundColor Cyan
Write-Host "  Prometheus   →  $GW/metrics" -ForegroundColor Cyan
Write-Host "  Health       →  $GW/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Supervisor PID : $($sup.Id)" -ForegroundColor Gray
Write-Host "  Logs stream from supervisor window (minimized)" -ForegroundColor Gray
Write-Host ""

# Live tail — show supervisor health file every 10s
Write-Host "  Live health monitor (Ctrl+C to exit):" -ForegroundColor Yellow
Write-Host ""

$healthFile = "$CODE\out\execution\supervisor_health.json"
while ($true) {
    Start-Sleep -Seconds 10
    if (Test-Path $healthFile) {
        $h = Get-Content $healthFile -Raw -ErrorAction SilentlyContinue | ConvertFrom-Json -ErrorAction SilentlyContinue
        if ($h) {
            $ts   = $h.generated_utc -replace 'T',' ' -replace '\.\d+.*',''
            $ok   = if ($h.all_healthy) { "ALL HEALTHY" } else { "DEGRADED" }
            $col  = if ($h.all_healthy) { "Green" } else { "Red" }
            $tick = $h.tick
            Write-Host "  [$ts]  tick=$tick  $($h.services_up)/$($h.services_total) up  STATUS: $ok" -ForegroundColor $col
            foreach ($svc in $h.services) {
                $icon    = if ($svc.running) { "●" } else { "○" }
                $svcCol  = if ($svc.running) { "DarkGreen" } else { "Red" }
                $restart = if ($svc.restart_count -gt 0) { " restarts=$($svc.restart_count)" } else { "" }
                Write-Host "    $icon $($svc.name.PadRight(15)) pid=$($svc.pid)$restart" -ForegroundColor $svcCol
            }
            Write-Host ""
        }
    } else {
        Write-Host "  Waiting for supervisor health file..." -ForegroundColor DarkGray
    }
}
