param(
    [string]$Controller = "Robert",
    [string]$GatewayHost = "127.0.0.1",
    [int]$GatewayPort = 8787,
    [int]$IntervalSec = 20,
    [int]$MaxExecutorHeartbeatAgeSec = 120
)

$ErrorActionPreference = "Continue"

$stackRoot = "c:\LumaTrader\INSTITUTIONAL_STACK_V2"
$execDir = Join-Path $stackRoot "code\execution"
$launcher = Join-Path $execDir "RUN_LIVE_COMPOUNDING_STACK.ps1"
$outExec = Join-Path $stackRoot "out\execution"
$lockFile = Join-Path $outExec "live_stack_supervisor.lock"
$heartbeatFile = Join-Path $outExec "live_stack_supervisor_heartbeat.json"
$executorHeartbeatFile = Join-Path $outExec "live_executor_heartbeat.json"

New-Item -ItemType Directory -Path $outExec -Force | Out-Null

function Set-HeartbeatState {
    param(
        [string]$Status,
        [string]$Reason,
        [hashtable]$Extra
    )
    $payload = @{
        status = $Status
        reason = $Reason
        generated_utc = (Get-Date).ToUniversalTime().ToString("o")
        interval_sec = $IntervalSec
        gateway_host = $GatewayHost
        gateway_port = $GatewayPort
    }
    if ($Extra) {
        foreach ($k in $Extra.Keys) {
            $payload[$k] = $Extra[$k]
        }
    }
    $payload | ConvertTo-Json -Depth 8 | Set-Content -Path $heartbeatFile -Encoding utf8
}

function Set-SupervisorLock {
    $procId = [int]$PID
    if (Test-Path $lockFile) {
        try {
            $existing = Get-Content $lockFile -Raw | ConvertFrom-Json
            $owner = 0
            if ($null -ne $existing.owner_process_id) {
                $owner = [int]$existing.owner_process_id
            } elseif ($null -ne $existing.pid) {
                $owner = [int]$existing.pid
            }
            if ($owner -gt 0) {
                $running = Get-CimInstance Win32_Process -Filter "ProcessId=$owner" -ErrorAction SilentlyContinue
                if ($running) {
                    Write-Host "[SUPERVISOR] already running (pid=$owner)"
                    return $false
                }
            }
        } catch {}
        Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
    }

    @{ owner_process_id = $procId; started_utc = (Get-Date).ToUniversalTime().ToString("o") } |
        ConvertTo-Json -Depth 4 |
        Set-Content -Path $lockFile -Encoding utf8
    return $true
}

function Clear-SupervisorLock {
    Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
}

function Invoke-Launcher {
    try {
        & $launcher -Controller $Controller -GatewayHost $GatewayHost -GatewayPort $GatewayPort | Out-Host
        Set-HeartbeatState -Status "ok" -Reason "launcher_invoked" -Extra @{}
    } catch {
        $msg = $_.Exception.Message
        Write-Host "[SUPERVISOR] launcher failed: $msg"
        Set-HeartbeatState -Status "error" -Reason "launcher_failed" -Extra @{ error = $msg }
    }
}

function Get-ProcessCount {
    param([string]$Pattern)
    return @(
        Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like $Pattern }
    ).Count
}

function Get-HeartbeatAgeSec {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return [double]::PositiveInfinity
    }

    try {
        $raw = Get-Content $Path -Raw | ConvertFrom-Json
        $stamp = ""
        if ($null -ne $raw.timestamp_utc) {
            $stamp = [string]$raw.timestamp_utc
        } elseif ($null -ne $raw.generated_utc) {
            $stamp = [string]$raw.generated_utc
        }
        if ([string]::IsNullOrWhiteSpace($stamp)) {
            return [double]::PositiveInfinity
        }
        $then = [datetimeoffset]::Parse($stamp)
        return [math]::Max(((Get-Date).ToUniversalTime() - $then.UtcDateTime).TotalSeconds, 0.0)
    } catch {
        return [double]::PositiveInfinity
    }
}

if (-not (Set-SupervisorLock)) {
    exit 0
}

try {
    Write-Host "[SUPERVISOR] started interval=${IntervalSec}s"
    Invoke-Launcher

    while ($true) {
        $gatewayListen = [bool](Get-NetTCPConnection -LocalPort $GatewayPort -State Listen -ErrorAction SilentlyContinue)
        $daemonCount = Get-ProcessCount "*approval_autofire_daemon.py*"
        $executorCount = Get-ProcessCount "*live_executor.py*"
        $executorHeartbeatAgeSec = Get-HeartbeatAgeSec $executorHeartbeatFile
        $executorHeartbeatStale = $executorHeartbeatAgeSec -gt [double]$MaxExecutorHeartbeatAgeSec

        $needsRecover = (-not $gatewayListen) -or ($daemonCount -eq 0) -or ($executorCount -eq 0) -or $executorHeartbeatStale
        if ($needsRecover) {
            Write-Host "[SUPERVISOR] recovery triggered gateway=$gatewayListen daemon=$daemonCount executor=$executorCount hb_age=$([math]::Round($executorHeartbeatAgeSec,2))s"
            Set-HeartbeatState -Status "degraded" -Reason "component_missing_recovering" -Extra @{
                gateway_listen = $gatewayListen
                daemon_count = $daemonCount
                executor_count = $executorCount
                executor_heartbeat_age_sec = [math]::Round($executorHeartbeatAgeSec, 3)
                max_executor_heartbeat_age_sec = [int]$MaxExecutorHeartbeatAgeSec
                executor_heartbeat_stale = [bool]$executorHeartbeatStale
            }
            Invoke-Launcher
        } else {
            Set-HeartbeatState -Status "ok" -Reason "healthy" -Extra @{
                gateway_listen = $gatewayListen
                daemon_count = $daemonCount
                executor_count = $executorCount
                executor_heartbeat_age_sec = [math]::Round($executorHeartbeatAgeSec, 3)
                max_executor_heartbeat_age_sec = [int]$MaxExecutorHeartbeatAgeSec
                executor_heartbeat_stale = [bool]$executorHeartbeatStale
            }
        }

        Start-Sleep -Seconds $IntervalSec
    }
}
finally {
    Clear-SupervisorLock
}
