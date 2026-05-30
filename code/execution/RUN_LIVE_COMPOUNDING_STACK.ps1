param(
    [string]$Controller = "Robert",
    [int]$GatewayPort = 8787,
    [string]$GatewayHost = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

$stackRoot = "c:\LumaTrader\INSTITUTIONAL_STACK_V2"
$codeDir = Join-Path $stackRoot "code"
$execDir = Join-Path $codeDir "execution"

$gatewayPy = Join-Path $stackRoot ".venv\Scripts\python.exe"
$runtimePy = "c:\LumaTrader\venv3.11\Scripts\python.exe"
$systemPy = "C:\Program Files\Python311\python.exe"
if (Test-Path $systemPy) {
    $daemonPy = $systemPy
} else {
    $daemonPy = $runtimePy
}

$gatewayScriptArgs = @(
    "-m", "uvicorn", "luma_experience_gateway:app",
    "--host", $GatewayHost,
    "--port", "$GatewayPort",
    "--log-level", "warning"
)

$daemonScript = Join-Path $execDir "approval_autofire_daemon.py"
$daemonArgs = @(
    $daemonScript,
    "--gateway-url", "http://$GatewayHost`:$GatewayPort",
    "--controller", $Controller,
    "--interval-sec", "5"
)

$executorScript = Join-Path $execDir "live_executor.py"
$executorArgs = @($executorScript)

function Get-ProcsByPattern {
    param([string]$Pattern)
    Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like $Pattern }
}

function Ensure-Gateway {
    $listener = Get-NetTCPConnection -LocalPort $GatewayPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) {
        Write-Host "[STACK] gateway already listening on $GatewayHost`:$GatewayPort (pid=$($listener.OwningProcess))"
        return
    }

    Push-Location $codeDir
    try {
        Start-Process -FilePath $gatewayPy -ArgumentList $gatewayScriptArgs -WindowStyle Hidden | Out-Null
    } finally {
        Pop-Location
    }

    $deadline = (Get-Date).AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 400
        $listener = Get-NetTCPConnection -LocalPort $GatewayPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    } while (-not $listener -and (Get-Date) -lt $deadline)

    if (-not $listener) {
        throw "gateway failed to bind on $GatewayHost`:$GatewayPort"
    }

    Write-Host "[STACK] gateway started on $GatewayHost`:$GatewayPort (pid=$($listener.OwningProcess))"
}

function Ensure-Daemon {
    $running = Get-ProcsByPattern "*approval_autofire_daemon.py*" | Select-Object -First 1
    if ($running) {
        Write-Host "[STACK] autofire daemon already running (pid=$($running.ProcessId))"
        return
    }

    Start-Process -FilePath $daemonPy -ArgumentList $daemonArgs -WindowStyle Hidden | Out-Null

    $deadline = (Get-Date).AddSeconds(15)
    do {
        Start-Sleep -Milliseconds 400
        $running = Get-ProcsByPattern "*approval_autofire_daemon.py*" | Select-Object -First 1
    } while (-not $running -and (Get-Date) -lt $deadline)

    if (-not $running) {
        throw "autofire daemon failed to start"
    }

    Write-Host "[STACK] autofire daemon running (pid=$($running.ProcessId))"
}

function Ensure-LiveExecutor {
    $running = Get-ProcsByPattern "*live_executor.py*" | Select-Object -First 1
    if ($running) {
        Write-Host "[STACK] live executor already running (pid=$($running.ProcessId))"
        return
    }

    # Clear stale duplicate-child marker so PID recycling can't false-block the executor.
    $env:LUMA_LIVE_EXECUTOR_ROOT_PID = ""

    Push-Location $execDir
    try {
        Start-Process -FilePath $runtimePy -ArgumentList $executorArgs -WindowStyle Hidden | Out-Null
    } finally {
        Pop-Location
    }

    $deadline = (Get-Date).AddSeconds(15)
    do {
        Start-Sleep -Milliseconds 400
        $running = Get-ProcsByPattern "*live_executor.py*" | Select-Object -First 1
    } while (-not $running -and (Get-Date) -lt $deadline)

    if (-not $running) {
        throw "live executor failed to start"
    }

    Write-Host "[STACK] live executor running (pid=$($running.ProcessId))"
}

# Enforce live compounding posture in runtime control.
$runtimeControlPath = Join-Path $stackRoot "config\runtime_control.json"
$runtime = Get-Content $runtimeControlPath -Raw | ConvertFrom-Json
$runtime.mode = "live"
$runtime.allow_live_orders = $true
if ([int]$runtime.max_open_positions -lt 10) { $runtime.max_open_positions = 10 }
if ([double]$runtime.loop_seconds -gt 5.0) { $runtime.loop_seconds = 5.0 }
$runtime | ConvertTo-Json -Depth 99 | Set-Content -Path $runtimeControlPath -Encoding utf8
Write-Host "[STACK] runtime control set to live / allow_live_orders=true / max_open_positions=$($runtime.max_open_positions) / loop_seconds=$($runtime.loop_seconds)"

Ensure-Gateway
Ensure-Daemon
Ensure-LiveExecutor

# Final health summary
$q = Invoke-RestMethod -Uri "http://$GatewayHost`:$GatewayPort/api/master/approval-queue" -Method Get
$pending = @($q.tickets | Where-Object { $_.approval_state -eq "PENDING_HUMAN_APPROVAL" }).Count
Write-Host "[STACK] control.max_open_positions=$($q.control_flags.max_open_positions) pending_approvals=$pending"
Write-Host "[STACK] live compounding stack is up"
