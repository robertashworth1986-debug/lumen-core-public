param(
    [int]$TopN = 8,
    [switch]$RefreshLiveRegistry,
    [switch]$RunInvestorProofSweep,
    [switch]$PushNodeRed
)

$ErrorActionPreference = 'Stop'

$root = 'C:\LumaTrader'
$stackRoot = Join-Path $root 'INSTITUTIONAL_STACK_V2'
$opsRoot = Join-Path $stackRoot 'code\ops'
$outDir = Join-Path $stackRoot 'out\ops'
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')

if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

$summaryPath = Join-Path $outDir ("investor_packet_refresh_{0}.json" -f $stamp)
$latestPath = Join-Path $outDir 'investor_packet_refresh_latest.json'

function Invoke-Step {
    param(
        [string]$Label,
        [scriptblock]$Action
    )

    $startedUtc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    $t0 = Get-Date

    Write-Host ("STEP_START {0}" -f $Label)
    $stepOutput = & $Action 2>&1
    foreach ($line in @($stepOutput)) {
        Write-Host $line
    }

    $elapsedSec = [math]::Round(((Get-Date) - $t0).TotalSeconds, 2)
    Write-Host ("STEP_DONE {0} elapsed_sec={1}" -f $Label, $elapsedSec)

    return [ordered]@{
        label = $Label
        started_utc = $startedUtc
        elapsed_sec = $elapsedSec
        status = 'ok'
    }
}

$steps = New-Object 'System.Collections.Generic.List[object]'

$panelScript = Join-Path $opsRoot 'RUN_LIVE_BREADTH_VALUE_PANEL.ps1'
$parityScript = Join-Path $opsRoot 'AUDIT_DASHBOARD_MIRROR_PARITY.ps1'
$proofSweepScript = Join-Path $opsRoot 'RUN_INVESTOR_PROOF_SWEEP.ps1'

if (-not (Test-Path -LiteralPath $panelScript)) {
    throw "Missing script: $panelScript"
}
if (-not (Test-Path -LiteralPath $parityScript)) {
    throw "Missing script: $parityScript"
}

$panelArgs = @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', $panelScript,
    '-TopN', [string]$TopN
)
if ($RefreshLiveRegistry.IsPresent) {
    $panelArgs += '-RefreshLiveRegistry'
}
$steps.Add((Invoke-Step -Label 'build_live_breadth_and_investor_readiness' -Action {
    & pwsh @panelArgs
    if ($LASTEXITCODE -ne 0) {
        throw "RUN_LIVE_BREADTH_VALUE_PANEL failed with exit code $LASTEXITCODE"
    }
}))

$parityArgs = @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', $parityScript
)
$steps.Add((Invoke-Step -Label 'audit_dashboard_mirror_parity' -Action {
    & pwsh @parityArgs
    if ($LASTEXITCODE -ne 0) {
        throw "AUDIT_DASHBOARD_MIRROR_PARITY failed with exit code $LASTEXITCODE"
    }
}))

if ($RunInvestorProofSweep.IsPresent) {
    if (-not (Test-Path -LiteralPath $proofSweepScript)) {
        throw "Missing script: $proofSweepScript"
    }

    $proofArgs = @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', $proofSweepScript
    )
    if ($PushNodeRed.IsPresent) {
        $proofArgs += '-PushNodeRed'
    }

    $steps.Add((Invoke-Step -Label 'run_investor_proof_sweep' -Action {
        & pwsh @proofArgs
        if ($LASTEXITCODE -ne 0) {
            throw "RUN_INVESTOR_PROOF_SWEEP failed with exit code $LASTEXITCODE"
        }
    }))
}

$summary = [ordered]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    scope = 'investor_packet_refresh'
    top_n = $TopN
    refresh_live_registry = [bool]$RefreshLiveRegistry.IsPresent
    run_investor_proof_sweep = [bool]$RunInvestorProofSweep.IsPresent
    push_nodered = [bool]$PushNodeRed.IsPresent
    steps = $steps
    artifacts = [ordered]@{
        live_breadth_value_panel_json = 'INSTITUTIONAL_STACK_V2/out/ops/live_breadth_value_panel.json'
        investor_metric_readiness_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/investor_metric_readiness_latest.json'
        investor_metric_readiness_latest_md = 'INSTITUTIONAL_STACK_V2/out/ops/investor_metric_readiness_latest.md'
        parity_markdown = 'out/ops/universe_map_20260510_213648/dashboard_mirror_parity_audit.md'
    }
}

$summary | ConvertTo-Json -Depth 10 | Set-Content -Path $summaryPath -Encoding utf8

$latest = [ordered]@{
    generated_utc = $summary.generated_utc
    latest_artifact = $summaryPath
}
$latest | ConvertTo-Json -Depth 4 | Set-Content -Path $latestPath -Encoding utf8

Write-Output ("INVESTOR_PACKET_REFRESH_SUMMARY={0}" -f $summaryPath)
Write-Output ("INVESTOR_PACKET_REFRESH_LATEST={0}" -f $latestPath)
