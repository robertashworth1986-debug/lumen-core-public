<#
.SYNOPSIS
  Safe innovation-only autopilot loop for investor-meeting mode.

.DESCRIPTION
  Every IntervalSeconds the loop refreshes the evidence chain end-to-end:
    1. infra_live_loop_builder.py        -> fresh infra_frozen_deltas.jsonl
    2. BUILD_FROZEN_DELTA_TRUTH_CHAIN.py -> advance hash chain
    3. BUILD_GRANT_SUBMIT_NOW_PACK.py    -> per-ticket fresh evidence packs
    4. BUILD_INVESTOR_ONE_PAGER.py       -> rebuild investor one-pager
    5. AUDIT_DASHBOARD_MIRROR_PARITY.ps1 -> dashboard parity check (optional)

  IT NEVER:
    - Touches the live executor or trading runtime
    - Submits grants, sends emails, or makes external POSTs
    - Performs destructive ops (deletes, force pushes, rm -rf)

  All output is appended to a per-cycle log under
    out/ops/autopilot_innovation/<UTC>/cycle_<NNN>.log
  with a rolling latest summary at
    out/ops/autopilot_innovation/STATUS.json

.PARAMETER IntervalSeconds
  Seconds between cycles (default 1200 = 20 min).

.PARAMETER MaxCycles
  Optional hard stop after N cycles. 0 = run forever (default).

.PARAMETER SkipParity
  Skip dashboard parity audit step.
#>

param(
    [int]$IntervalSeconds = 1200,
    [int]$MaxCycles = 0,
    [switch]$SkipParity
)

$ErrorActionPreference = 'Continue'
$env:PYTHONIOENCODING = 'utf-8'

$Stack = Split-Path -Parent $PSScriptRoot
$Stack = Split-Path -Parent $Stack
Set-Location $Stack

$RunTag  = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$LogRoot = Join-Path $Stack "out\ops\autopilot_innovation\$RunTag"
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$StatusPath  = Join-Path $Stack 'out\ops\autopilot_innovation\STATUS.json'
$ManifestPath = Join-Path $LogRoot 'CYCLES.jsonl'

function Write-Status {
    param($Cycle, $LastResult, $NextEpochUtc)
    $obj = [ordered]@{
        schema           = 'lumen.autopilot_status/v1'
        run_tag          = $RunTag
        cycle            = $Cycle
        last_cycle_utc   = (Get-Date).ToUniversalTime().ToString('o')
        last_result      = $LastResult
        next_cycle_utc   = $NextEpochUtc
        log_root         = $LogRoot
        interval_seconds = $IntervalSeconds
    }
    $obj | ConvertTo-Json -Depth 6 | Set-Content -Path $StatusPath -Encoding UTF8
}

function Invoke-Step {
    param([string]$Name, [scriptblock]$Action, [string]$LogFile)
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $output = & $Action 2>&1 | Out-String
        Add-Content -Path $LogFile -Value "===== $Name =====`n$output`n"
        $sw.Stop()
        return [ordered]@{ name = $Name; ok = $true; ms = $sw.ElapsedMilliseconds; tail = ($output -split "`n")[-6..-1] -join "`n" }
    } catch {
        Add-Content -Path $LogFile -Value "===== $Name FAIL =====`n$_`n"
        $sw.Stop()
        return [ordered]@{ name = $Name; ok = $false; ms = $sw.ElapsedMilliseconds; error = "$_" }
    }
}

Write-Host "AUTOPILOT_INNOVATION_LOOP started run_tag=$RunTag interval=$IntervalSeconds cycles=$MaxCycles" -ForegroundColor Green
Write-Host "  log_root: $LogRoot"
Write-Host "  status:   $StatusPath"
Write-Host "  Ctrl+C to stop. Live executor and trading runtime are NOT touched."

$cycle = 0
while ($true) {
    $cycle++
    $cycleStart = Get-Date
    $cycleLog = Join-Path $LogRoot ("cycle_{0:000}.log" -f $cycle)
    Set-Content -Path $cycleLog -Value "CYCLE $cycle start_utc=$($cycleStart.ToUniversalTime().ToString('o'))" -Encoding UTF8

    $steps = @()
    $steps += Invoke-Step 'infra_live_loop_builder' { python code/infra_live_loop_builder.py } $cycleLog
    $steps += Invoke-Step 'frozen_delta_truth_chain' { python code/ops/BUILD_FROZEN_DELTA_TRUTH_CHAIN.py } $cycleLog
    $steps += Invoke-Step 'grant_submit_now_pack' { python code/ops/BUILD_GRANT_SUBMIT_NOW_PACK.py } $cycleLog
    $steps += Invoke-Step 'investor_one_pager' { python code/ops/BUILD_INVESTOR_ONE_PAGER.py } $cycleLog
    if (-not $SkipParity) {
        $steps += Invoke-Step 'dashboard_parity_audit' {
            pwsh -NoProfile -ExecutionPolicy Bypass -File code/ops/AUDIT_DASHBOARD_MIRROR_PARITY.ps1
        } $cycleLog
    }

    $cycleEnd = Get-Date
    $duration = ($cycleEnd - $cycleStart).TotalSeconds
    $okCount  = ($steps | Where-Object { $_.ok }).Count
    $manifest = [ordered]@{
        cycle           = $cycle
        start_utc       = $cycleStart.ToUniversalTime().ToString('o')
        end_utc         = $cycleEnd.ToUniversalTime().ToString('o')
        duration_sec    = [math]::Round($duration, 2)
        steps_total     = $steps.Count
        steps_ok        = $okCount
        steps           = $steps
    }
    Add-Content -Path $ManifestPath -Value ($manifest | ConvertTo-Json -Depth 6 -Compress)

    $color = if ($okCount -eq $steps.Count) { 'Green' } else { 'Yellow' }
    Write-Host ("[{0:HH:mm:ss}] cycle={1,3}  ok={2}/{3}  dur={4:N1}s" -f $cycleEnd, $cycle, $okCount, $steps.Count, $duration) -ForegroundColor $color

    $nextEpoch = (Get-Date).ToUniversalTime().AddSeconds($IntervalSeconds).ToString('o')
    Write-Status -Cycle $cycle -LastResult $manifest -NextEpochUtc $nextEpoch

    if ($MaxCycles -gt 0 -and $cycle -ge $MaxCycles) {
        Write-Host "AUTOPILOT_INNOVATION_LOOP completed cycles=$cycle" -ForegroundColor Cyan
        break
    }
    Start-Sleep -Seconds $IntervalSeconds
}
