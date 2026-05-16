param(
    [ValidateSet('status', 'start', 'restart')]
    [string]$Action = 'restart',

    [int]$HeartbeatFreshnessSec = 180,
    [int]$HeartbeatWaitSec = 45,

    [switch]$SkipKrakenOpenOrders
)

$ErrorActionPreference = 'Stop'

$stackRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$managerScript = Join-Path $PSScriptRoot 'STACK_RUNTIME_MANAGER.ps1'
$runtimeControlPath = Join-Path $stackRoot 'config\runtime_control.json'
$heartbeatPath = Join-Path $stackRoot 'out\execution\live_executor_heartbeat.json'
$lockPath = Join-Path $stackRoot 'out\execution\live_executor.lock'
$opsOutDir = Join-Path $stackRoot 'out\ops\live_continuity_rehydrate'

New-Item -Path $opsOutDir -ItemType Directory -Force | Out-Null

$stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$reportJsonPath = Join-Path $opsOutDir ("rehydrate_{0}.json" -f $stamp)
$reportMdPath = Join-Path $opsOutDir ("rehydrate_{0}.md" -f $stamp)
$latestJsonPath = Join-Path $opsOutDir 'rehydrate_latest.json'
$latestMdPath = Join-Path $opsOutDir 'rehydrate_latest.md'

function Get-UtcNowIso {
    return [DateTime]::UtcNow.ToString('o')
}

function Get-JsonOrDefault {
    param(
        [string]$Path,
        [object]$DefaultValue
    )

    if (-not (Test-Path $Path)) {
        return $DefaultValue
    }

    try {
        $raw = Get-Content $Path -Raw -ErrorAction Stop
        if ([string]::IsNullOrWhiteSpace($raw)) {
            return $DefaultValue
        }
        return ($raw | ConvertFrom-Json -ErrorAction Stop)
    } catch {
        return $DefaultValue
    }
}

function Get-RuntimeSummary {
    param([object]$Runtime)

    $r = if ($Runtime -is [System.Collections.IDictionary] -or $Runtime.PSObject.Properties.Count -gt 0) { $Runtime } else { @{} }

    return [ordered]@{
        mode = [string]($r.mode)
        allow_live_orders = [bool]$r.allow_live_orders
        kill_switch = [bool]$r.kill_switch
        force_universe_mode = [bool]$r.force_universe_mode
        hybrid_swing_selector_enabled = [bool]$r.hybrid_swing_selector_enabled
        hybrid_swing_long_bias_enabled = [bool]$r.hybrid_swing_long_bias_enabled
        live_operator_queue_enabled = [bool]$r.live_operator_queue_enabled
        loop_seconds = [double]($r.loop_seconds)
        max_notional_per_trade_usd = [double]($r.max_notional_per_trade_usd)
        symbol = [string]($r.symbol)
    }
}

function Get-HeartbeatSnapshot {
    param([int]$FreshnessSec)

    $snapshot = [ordered]@{
        exists = $false
        readable = $false
        timestamp_utc = $null
        age_sec = $null
        is_fresh = $false
        status = $null
        reason = $null
        selected_symbol = $null
        symbol_source = $null
        universe_candidate_count = $null
        heartbeat_path = $heartbeatPath
    }

    if (-not (Test-Path $heartbeatPath)) {
        return [pscustomobject]$snapshot
    }

    $snapshot.exists = $true
    try {
        $hb = Get-Content $heartbeatPath -Raw | ConvertFrom-Json -ErrorAction Stop
        $snapshot.readable = $true
        $snapshot.timestamp_utc = [string]$hb.timestamp_utc
        $snapshot.status = [string]$hb.status
        $snapshot.reason = [string]$hb.reason
        $snapshot.selected_symbol = [string]$hb.selected_symbol
        $snapshot.symbol_source = [string]$hb.symbol_source
        $snapshot.universe_candidate_count = [int]$hb.universe_candidate_count

        if (-not [string]::IsNullOrWhiteSpace($snapshot.timestamp_utc)) {
            $ts = [DateTimeOffset]::Parse($snapshot.timestamp_utc)
            $age = [DateTimeOffset]::UtcNow - $ts.ToUniversalTime()
            $ageSec = [Math]::Max([Math]::Round($age.TotalSeconds, 3), 0.0)
            $snapshot.age_sec = [double]$ageSec
            $snapshot.is_fresh = $ageSec -le [double]$FreshnessSec
        }
    } catch {
        $snapshot.readable = $false
    }

    return [pscustomobject]$snapshot
}

function Wait-ForFreshHeartbeat {
    param(
        [int]$TimeoutSec,
        [int]$FreshnessSec
    )

    $started = [DateTimeOffset]::UtcNow
    $deadline = $started.AddSeconds([Math]::Max($TimeoutSec, 1))
    $latest = Get-HeartbeatSnapshot -FreshnessSec $FreshnessSec

    while (([DateTimeOffset]::UtcNow -lt $deadline) -and (-not [bool]$latest.is_fresh)) {
        Start-Sleep -Milliseconds 900
        $latest = Get-HeartbeatSnapshot -FreshnessSec $FreshnessSec
    }

    $elapsed = [Math]::Round(([DateTimeOffset]::UtcNow - $started).TotalSeconds, 3)
    return [pscustomobject]@{
        snapshot = $latest
        waited_sec = [double]$elapsed
        fresh = [bool]$latest.is_fresh
    }
}

function Resolve-PythonRuntime {
    $candidates = @(
        (Join-Path $stackRoot '.venv\Scripts\python.exe'),
        (Join-Path $stackRoot 'code\.venv\Scripts\python.exe'),
        (Join-Path $stackRoot '..\venv3.11\Scripts\python.exe'),
        'C:\LumaTrader\venv3.11\Scripts\python.exe',
        'C:\LumaTrader\.venv\Scripts\python.exe'
    )

    foreach ($candidate in $candidates) {
        try {
            $resolved = (Resolve-Path $candidate -ErrorAction Stop).Path
            if (Test-Path $resolved) {
                return $resolved
            }
        } catch {
            continue
        }
    }

    return ''
}

function Get-KrakenOpenOrdersEvidence {
    param(
        [string]$PythonExe,
        [switch]$Skip,
        [int]$Attempt = 0
    )

    $result = [ordered]@{
        ok = $false
        skipped = [bool]$Skip
        python = [string]$PythonExe
        open_orders_count = $null
        open_order_ids = @()
        error = ''
    }

    if ($Skip) {
        return [pscustomobject]$result
    }

    if ([string]::IsNullOrWhiteSpace($PythonExe) -or (-not (Test-Path $PythonExe))) {
        $result.error = 'python_runtime_not_found'
        return [pscustomobject]$result
    }

    $stackRootForward = ($stackRoot -replace '\\', '/')
    $pyCode = @"
import json
import sys
from pathlib import Path

root = Path(r"$stackRootForward/code")
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

out = {"ok": False, "open_orders_count": None, "open_order_ids": [], "error": ""}
try:
    import kraken_execution
    payload = kraken_execution.get_open_orders()
    open_orders = payload.get("open", {}) if isinstance(payload, dict) else {}
    if isinstance(open_orders, dict):
        out["ok"] = True
        out["open_orders_count"] = len(open_orders)
        out["open_order_ids"] = list(open_orders.keys())[:25]
    else:
        out["ok"] = True
        out["open_orders_count"] = 0
except Exception as exc:
    out["error"] = str(exc)

print(json.dumps(out, ensure_ascii=True))
"@

    try {
        $raw = & $PythonExe -c $pyCode 2>&1
        if ($LASTEXITCODE -ne 0) {
            $result.error = "python_exit_$LASTEXITCODE"
            return [pscustomobject]$result
        }

        $rawText = ($raw | Out-String).Trim()
        $jsonLine = ($rawText -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Last 1)
        if ([string]::IsNullOrWhiteSpace($jsonLine)) {
            $result.error = 'no_json_output'
            return [pscustomobject]$result
        }

        $parsed = $jsonLine | ConvertFrom-Json -ErrorAction Stop
        $result.ok = [bool]$parsed.ok
        $result.open_orders_count = $parsed.open_orders_count
        $result.open_order_ids = @($parsed.open_order_ids)
        $result.error = [string]$parsed.error

        if ((-not $result.ok) -and ($Attempt -lt 2) -and ($result.error -match 'Invalid nonce')) {
            Start-Sleep -Milliseconds 750
            return Get-KrakenOpenOrdersEvidence -PythonExe $PythonExe -Skip:$Skip -Attempt ($Attempt + 1)
        }
    } catch {
        $result.error = [string]$_.Exception.Message
    }

    return [pscustomobject]$result
}

$runtimeBefore = Get-JsonOrDefault -Path $runtimeControlPath -DefaultValue @{}
$heartbeatBefore = Get-HeartbeatSnapshot -FreshnessSec $HeartbeatFreshnessSec
$pythonExe = Resolve-PythonRuntime
$openOrdersBefore = Get-KrakenOpenOrdersEvidence -PythonExe $pythonExe -Skip:$SkipKrakenOpenOrders

$actionExecuted = 'status'
if ($Action -ne 'status') {
    if (-not (Test-Path $managerScript)) {
        throw "Runtime manager not found at $managerScript"
    }

    $forceSwitch = $false
    if ($Action -eq 'restart') {
        $forceSwitch = $true
    }

    & $managerScript -Action $Action -StackGroup core -Force:$forceSwitch
    $actionExecuted = $Action
}

$waitResult = Wait-ForFreshHeartbeat -TimeoutSec $HeartbeatWaitSec -FreshnessSec $HeartbeatFreshnessSec
$runtimeAfter = Get-JsonOrDefault -Path $runtimeControlPath -DefaultValue @{}
$heartbeatAfter = Get-HeartbeatSnapshot -FreshnessSec $HeartbeatFreshnessSec
$openOrdersAfter = Get-KrakenOpenOrdersEvidence -PythonExe $pythonExe -Skip:$SkipKrakenOpenOrders

$runtimeOk = [bool](Test-Path $runtimeControlPath)
$heartbeatOk = [bool]$heartbeatAfter.is_fresh
$openOrdersOk = if ($SkipKrakenOpenOrders) { $true } else { [bool]$openOrdersAfter.ok }
$triadPass = [bool]($runtimeOk -and $heartbeatOk -and $openOrdersOk)

$report = [ordered]@{
    generated_utc = Get-UtcNowIso
    scope = 'live_continuity_rehydrate'
    action_requested = $Action
    action_executed = $actionExecuted
    validation = [ordered]@{
        runtime_control_ok = $runtimeOk
        heartbeat_fresh = $heartbeatOk
        kraken_open_orders_ok = $openOrdersOk
        triad_pass = $triadPass
    }
    runtime_before = Get-RuntimeSummary -Runtime $runtimeBefore
    runtime_after = Get-RuntimeSummary -Runtime $runtimeAfter
    heartbeat_before = $heartbeatBefore
    heartbeat_after = $heartbeatAfter
    heartbeat_wait = [ordered]@{
        waited_sec = [double]$waitResult.waited_sec
        fresh = [bool]$waitResult.fresh
        freshness_threshold_sec = [int]$HeartbeatFreshnessSec
    }
    kraken_open_orders_before = $openOrdersBefore
    kraken_open_orders_after = $openOrdersAfter
    evidence_paths = [ordered]@{
        runtime_control = $runtimeControlPath
        heartbeat = $heartbeatPath
        lock_file = $lockPath
        report_json = $reportJsonPath
        report_md = $reportMdPath
    }
}

$reportJson = $report | ConvertTo-Json -Depth 12
Set-Content -Path $reportJsonPath -Value $reportJson -Encoding UTF8
Set-Content -Path $latestJsonPath -Value $reportJson -Encoding UTF8

$mdLines = @(
    '# Live Continuity Rehydrate Report',
    '',
    ('- generated_utc: {0}' -f $report.generated_utc),
    ('- action_requested: {0}' -f $report.action_requested),
    ('- action_executed: {0}' -f $report.action_executed),
    ('- triad_pass: {0}' -f $report.validation.triad_pass),
    ('- runtime_control_ok: {0}' -f $report.validation.runtime_control_ok),
    ('- heartbeat_fresh: {0} (age_sec={1})' -f $report.validation.heartbeat_fresh, $report.heartbeat_after.age_sec),
    ('- kraken_open_orders_ok: {0}' -f $report.validation.kraken_open_orders_ok),
    '',
    '## Runtime After',
    '',
    ('- mode: {0}' -f $report.runtime_after.mode),
    ('- allow_live_orders: {0}' -f $report.runtime_after.allow_live_orders),
    ('- kill_switch: {0}' -f $report.runtime_after.kill_switch),
    ('- force_universe_mode: {0}' -f $report.runtime_after.force_universe_mode),
    ('- hybrid_swing_selector_enabled: {0}' -f $report.runtime_after.hybrid_swing_selector_enabled),
    ('- hybrid_swing_long_bias_enabled: {0}' -f $report.runtime_after.hybrid_swing_long_bias_enabled),
    ('- live_operator_queue_enabled: {0}' -f $report.runtime_after.live_operator_queue_enabled),
    '',
    '## Heartbeat After',
    '',
    ('- status: {0}' -f $report.heartbeat_after.status),
    ('- reason: {0}' -f $report.heartbeat_after.reason),
    ('- selected_symbol: {0}' -f $report.heartbeat_after.selected_symbol),
    ('- symbol_source: {0}' -f $report.heartbeat_after.symbol_source),
    ('- universe_candidate_count: {0}' -f $report.heartbeat_after.universe_candidate_count),
    '',
    '## Evidence Paths',
    '',
    ('- runtime_control: {0}' -f $runtimeControlPath),
    ('- heartbeat: {0}' -f $heartbeatPath),
    ('- lock_file: {0}' -f $lockPath),
    ('- report_json: {0}' -f $reportJsonPath),
    ('- report_md: {0}' -f $reportMdPath)
)

$reportMd = ($mdLines -join "`n")
Set-Content -Path $reportMdPath -Value $reportMd -Encoding UTF8
Set-Content -Path $latestMdPath -Value $reportMd -Encoding UTF8

Write-Host ("[REHYDRATE] triad_pass={0} heartbeat_fresh={1} open_orders_ok={2}" -f $triadPass, $heartbeatOk, $openOrdersOk)
Write-Host ("[REHYDRATE] report_json={0}" -f $reportJsonPath)
Write-Host ("[REHYDRATE] report_md={0}" -f $reportMdPath)
