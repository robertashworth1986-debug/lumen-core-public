param(
    [switch]$NoOrders = $true,
    [switch]$OpenDashboards = $true
)

$ErrorActionPreference = 'Stop'

$Root = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2'
$Py = Join-Path $Root '.venv\Scripts\python.exe'
$RunDir = Join-Path $Root 'run'
$ReportPath = Join-Path $Root 'out\execution\local_runtime_recovery_report.json'

function Test-TcpPort {
    param([string]$HostName, [int]$Port)
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $iar = $c.BeginConnect($HostName, $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(1200, $false)
        if (-not $ok) { $c.Close(); return $false }
        $c.EndConnect($iar)
        $c.Close()
        return $true
    } catch {
        return $false
    }
}

function Remove-StaleLock {
    param([string]$LockFile)
    if (-not (Test-Path $LockFile)) { return $false }
    $pidText = (Get-Content $LockFile -Raw).Trim()
    $lockPid = 0
    [void][int]::TryParse($pidText, [ref]$lockPid)
    if ($lockPid -gt 0) {
        $p = Get-Process -Id $lockPid -ErrorAction SilentlyContinue
        if ($p) { return $false }
    }
    Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
    return $true
}

function Start-IfMissing {
    param(
        [string]$Name,
        [scriptblock]$IsRunning,
        [scriptblock]$StartCmd
    )
    if (& $IsRunning) {
        return 'already_running'
    }
    & $StartCmd
    Start-Sleep -Seconds 2
    if (& $IsRunning) { return 'started' }
    return 'failed_to_start'
}

New-Item -ItemType Directory -Path (Split-Path $ReportPath -Parent) -Force | Out-Null

$staleLocks = @()
if (Remove-StaleLock (Join-Path $RunDir 'luma_supervisor.lock')) { $staleLocks += 'luma_supervisor.lock' }
if (Remove-StaleLock (Join-Path $RunDir 'luma_experience_gateway.lock')) { $staleLocks += 'luma_experience_gateway.lock' }

$nodeRedStatus = Start-IfMissing -Name 'node-red' `
    -IsRunning { Test-TcpPort -HostName '127.0.0.1' -Port 1880 } `
    -StartCmd {
        $nr = Get-Command node-red -ErrorAction SilentlyContinue
        if (-not $nr) { return }
        Start-Process -FilePath $nr.Source -WindowStyle Minimized | Out-Null
    }

$supervisorStatus = Start-IfMissing -Name 'supervisor' `
    -IsRunning {
        $procs = Get-CimInstance Win32_Process | Where-Object {
            $_.Name -eq 'python.exe' -and $_.CommandLine -like '*luma_supervisor.py*'
        }
        return [bool]($procs)
    } `
    -StartCmd {
        if (-not (Test-Path $Py)) { return }
        $args = @('code\luma_supervisor.py')
        if ($NoOrders) { $args += '--no-orders' }
        Start-Process -FilePath $Py -ArgumentList $args -WorkingDirectory $Root -WindowStyle Minimized | Out-Null
    }

Start-Sleep -Seconds 3

$health = $null
$snapshot = $null
$unity = $null
$nodeRedFlowsHttp = $null

try { $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8787/health' -TimeoutSec 6 } catch {}
try { $snapshot = Invoke-RestMethod -Uri 'http://127.0.0.1:8787/api/snapshot' -TimeoutSec 6 } catch {}
try { $unity = Invoke-RestMethod -Uri 'http://127.0.0.1:8787/api/unity/edge' -TimeoutSec 6 } catch {}
try {
    $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:1880/flows' -TimeoutSec 6 -UseBasicParsing
    $nodeRedFlowsHttp = $resp.StatusCode
} catch {}

$paperSummary = $null
if (Test-Path $Py) {
    try {
        $paperOut = & $Py 'code\sports_paper_execution_bot.py' '--bankroll' '250000' '--max-bet' '5000' '--min-edge' '1.0' '--kelly-fraction' '0.25' 2>&1
        $paperSummary = ($paperOut | Out-String)
    } catch {
        $paperSummary = "paper_bot_error: $($_.Exception.Message)"
    }
}

if ($OpenDashboards) {
    Start-Process 'file:///C:/LumaTrader/INSTITUTIONAL_STACK_V2/dashboard/investor_wallboard.html' | Out-Null
    Start-Process 'file:///C:/LumaTrader/INSTITUTIONAL_STACK_V2/dashboard/signal_confidence_heatmap.html' | Out-Null
    Start-Process 'file:///C:/LumaTrader/INSTITUTIONAL_STACK_V2/dashboard/index.html' | Out-Null
}

$report = [ordered]@{
    generated_utc = [DateTime]::UtcNow.ToString('o')
    stale_locks_removed = $staleLocks
    node_red_status = $nodeRedStatus
    supervisor_status = $supervisorStatus
    endpoint_health = @{
        gateway_8787_up = [bool]$health
        gateway_health = $health
        snapshot_ok = [bool]$snapshot
        unity_ok = [bool]$unity
        unity_node_count = if ($unity) { $unity.node_count } else { 0 }
        nodered_1880_open = Test-TcpPort -HostName '127.0.0.1' -Port 1880
        nodered_flows_http = $nodeRedFlowsHttp
    }
    paper_bot_run_output = $paperSummary
}

$report | ConvertTo-Json -Depth 8 | Set-Content -Path $ReportPath -Encoding utf8
Write-Host "[OK] Recovery report written: $ReportPath"
Write-Host ($report | ConvertTo-Json -Depth 6)
