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

$heartbeatDir = Join-Path $outDir 'investor_packet_refresh'
$heartbeatPath = Join-Path $heartbeatDir 'investor_packet_refresh_heartbeat_latest.json'
$heartbeatRunPath = Join-Path $heartbeatDir ("investor_packet_refresh_heartbeat_{0}.json" -f $stamp)

if (-not (Test-Path -LiteralPath $heartbeatDir)) {
    New-Item -ItemType Directory -Path $heartbeatDir -Force | Out-Null
}

$pythonCandidates = @(
    (Join-Path $stackRoot 'code\.venv\Scripts\python.exe'),
    (Join-Path $root 'venv3.11\Scripts\python.exe'),
    (Join-Path $stackRoot '.venv\Scripts\python.exe')
)
$pythonExe = $null
foreach ($cand in $pythonCandidates) {
    if (Test-Path -LiteralPath $cand) {
        $pythonExe = $cand
        break
    }
}
if (-not $pythonExe) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) {
        $pythonExe = $cmd.Source
    }
}
if (-not $pythonExe) {
    throw 'Unable to resolve Python executable for investor packet refresh pipeline'
}

$pipelineStart = Get-Date

function Write-RefreshHeartbeat {
    param(
        [string]$Status,
        [string]$Reason,
        [string]$LastStep = '',
        [string]$ErrorMessage = '',
        [hashtable]$Extra = @{}
    )

    $elapsedSec = [math]::Round(((Get-Date) - $pipelineStart).TotalSeconds, 2)
    $payload = [ordered]@{
        generated_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        scope = 'investor_packet_refresh'
        mode = 'pipeline'
        run_stamp = $stamp
        status = $Status
        reason = $Reason
        last_step = $LastStep
        elapsed_sec = $elapsedSec
        top_n = [int]$TopN
        refresh_live_registry = [bool]$RefreshLiveRegistry.IsPresent
        run_investor_proof_sweep = [bool]$RunInvestorProofSweep.IsPresent
        push_nodered = [bool]$PushNodeRed.IsPresent
        python_exe = $pythonExe
    }

    if ($ErrorMessage) {
        $payload.error = $ErrorMessage
    }

    foreach ($k in $Extra.Keys) {
        $payload[$k] = $Extra[$k]
    }

    $json = $payload | ConvertTo-Json -Depth 10
    $json | Set-Content -Path $heartbeatPath -Encoding utf8
    $json | Set-Content -Path $heartbeatRunPath -Encoding utf8
}

Write-RefreshHeartbeat -Status 'running' -Reason 'pipeline_start'

function Invoke-Step {
    param(
        [string]$Label,
        [scriptblock]$Action
    )

    $startedUtc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    $t0 = Get-Date

    Write-Host ("STEP_START {0}" -f $Label)
    Write-RefreshHeartbeat -Status 'running' -Reason 'step_start' -LastStep $Label

    try {
        $stepOutput = & $Action 2>&1
        foreach ($line in @($stepOutput)) {
            Write-Host $line
        }
    } catch {
        $msg = $_.Exception.Message
        Write-RefreshHeartbeat -Status 'error' -Reason 'step_failed' -LastStep $Label -ErrorMessage $msg
        throw
    }

    $elapsedSec = [math]::Round(((Get-Date) - $t0).TotalSeconds, 2)
    Write-Host ("STEP_DONE {0} elapsed_sec={1}" -f $Label, $elapsedSec)
    Write-RefreshHeartbeat -Status 'running' -Reason 'step_complete' -LastStep $Label -Extra @{
        step_elapsed_sec = $elapsedSec
    }

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
$nobelAssetsScript = Join-Path $stackRoot 'code\execution\build_nobel_tier_assets.py'
$alphaEdgeLockScript = Join-Path $opsRoot 'BUILD_ALPHA_EDGE_LOCK_ENGINE.py'
$blueprintVaultScript = Join-Path $opsRoot 'BUILD_GOV_BLUEPRINT_VAULT.py'
$grantFitScript = Join-Path $opsRoot 'BUILD_GRANT_SUBMIT_FIT_PACK.py'
$missionPackScript = Join-Path $opsRoot 'BUILD_INVESTOR_MISSION_CONTROL_PACK.py'
$siteReachMissionScript = Join-Path $opsRoot 'BUILD_SITE_REACH_AND_DOMAIN_MISSION_PUSH.py'

if (-not (Test-Path -LiteralPath $panelScript)) {
    Write-RefreshHeartbeat -Status 'error' -Reason 'missing_script' -ErrorMessage "Missing script: $panelScript"
    throw "Missing script: $panelScript"
}
if (-not (Test-Path -LiteralPath $parityScript)) {
    Write-RefreshHeartbeat -Status 'error' -Reason 'missing_script' -ErrorMessage "Missing script: $parityScript"
    throw "Missing script: $parityScript"
}
if (-not (Test-Path -LiteralPath $nobelAssetsScript)) {
    Write-RefreshHeartbeat -Status 'error' -Reason 'missing_script' -ErrorMessage "Missing script: $nobelAssetsScript"
    throw "Missing script: $nobelAssetsScript"
}
if (-not (Test-Path -LiteralPath $alphaEdgeLockScript)) {
    Write-RefreshHeartbeat -Status 'error' -Reason 'missing_script' -ErrorMessage "Missing script: $alphaEdgeLockScript"
    throw "Missing script: $alphaEdgeLockScript"
}
if (-not (Test-Path -LiteralPath $blueprintVaultScript)) {
    Write-RefreshHeartbeat -Status 'error' -Reason 'missing_script' -ErrorMessage "Missing script: $blueprintVaultScript"
    throw "Missing script: $blueprintVaultScript"
}
if (-not (Test-Path -LiteralPath $grantFitScript)) {
    Write-RefreshHeartbeat -Status 'error' -Reason 'missing_script' -ErrorMessage "Missing script: $grantFitScript"
    throw "Missing script: $grantFitScript"
}
if (-not (Test-Path -LiteralPath $missionPackScript)) {
    Write-RefreshHeartbeat -Status 'error' -Reason 'missing_script' -ErrorMessage "Missing script: $missionPackScript"
    throw "Missing script: $missionPackScript"
}
if (-not (Test-Path -LiteralPath $siteReachMissionScript)) {
    Write-RefreshHeartbeat -Status 'error' -Reason 'missing_script' -ErrorMessage "Missing script: $siteReachMissionScript"
    throw "Missing script: $siteReachMissionScript"
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

$steps.Add((Invoke-Step -Label 'build_nobel_tier_assets' -Action {
    & $pythonExe $nobelAssetsScript
    if ($LASTEXITCODE -ne 0) {
        throw "build_nobel_tier_assets failed with exit code $LASTEXITCODE"
    }
}))

$steps.Add((Invoke-Step -Label 'build_alpha_edge_lock_engine' -Action {
    & $pythonExe $alphaEdgeLockScript --sim-runs 5000 --top-n 12
    if ($LASTEXITCODE -ne 0) {
        throw "BUILD_ALPHA_EDGE_LOCK_ENGINE failed with exit code $LASTEXITCODE"
    }
}))

$steps.Add((Invoke-Step -Label 'build_gov_blueprint_vault' -Action {
    & $pythonExe $blueprintVaultScript --exposure-level highest_level
    if ($LASTEXITCODE -ne 0) {
        throw "BUILD_GOV_BLUEPRINT_VAULT failed with exit code $LASTEXITCODE"
    }
}))

$steps.Add((Invoke-Step -Label 'build_grant_submit_fit_pack' -Action {
    & $pythonExe $grantFitScript --state APPROVED --limit 120
    if ($LASTEXITCODE -ne 0) {
        throw "BUILD_GRANT_SUBMIT_FIT_PACK failed with exit code $LASTEXITCODE"
    }
}))

$steps.Add((Invoke-Step -Label 'build_investor_mission_control_pack' -Action {
    & $pythonExe $missionPackScript --top-sectors $TopN
    if ($LASTEXITCODE -ne 0) {
        throw "BUILD_INVESTOR_MISSION_CONTROL_PACK failed with exit code $LASTEXITCODE"
    }
}))

$steps.Add((Invoke-Step -Label 'build_site_reach_and_domain_mission_push' -Action {
    & $pythonExe $siteReachMissionScript --days 30 --allow-live-push
    if ($LASTEXITCODE -ne 0) {
        throw "BUILD_SITE_REACH_AND_DOMAIN_MISSION_PUSH failed with exit code $LASTEXITCODE"
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
        Write-RefreshHeartbeat -Status 'error' -Reason 'missing_script' -ErrorMessage "Missing script: $proofSweepScript"
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
        nobel_tier_slides_json = 'INSTITUTIONAL_STACK_V2/out/INSTITUTIONAL_REVIEW_BUNDLE/nobel_tier_slides.json'
        alpha_edge_lock_engine_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/alpha_edge_lock/alpha_edge_lock_engine_latest.json'
        alpha_edge_lock_engine_latest_md = 'INSTITUTIONAL_STACK_V2/out/ops/alpha_edge_lock/alpha_edge_lock_engine_latest.md'
        alpha_edge_lock_engine_heartbeat_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/alpha_edge_lock/alpha_edge_lock_engine_heartbeat_latest.json'
        gov_blueprint_vault_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/gov_blueprint_vault/gov_blueprint_vault_latest.json'
        gov_blueprint_vault_latest_md = 'INSTITUTIONAL_STACK_V2/out/ops/gov_blueprint_vault/gov_blueprint_vault_latest.md'
        gov_blueprint_vault_heartbeat_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/gov_blueprint_vault/gov_blueprint_vault_heartbeat_latest.json'
        grant_submit_fit_pack_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/grant_submit_fit_pack/grant_submit_fit_pack_latest.json'
        investor_mission_control_pack_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/investor_mission_control/investor_mission_control_pack_latest.json'
        investor_mission_control_pack_latest_md = 'INSTITUTIONAL_STACK_V2/out/ops/investor_mission_control/investor_mission_control_pack_latest.md'
        investor_mission_control_pack_heartbeat_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/investor_mission_control/investor_mission_control_pack_heartbeat_latest.json'
        investor_3min_nobel_pitch_latest_md = 'INSTITUTIONAL_STACK_V2/out/ops/investor_mission_control/investor_3min_nobel_pitch_latest.md'
        site_reach_mission_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/site_reach_mission/site_reach_mission_latest.json'
        site_reach_mission_latest_md = 'INSTITUTIONAL_STACK_V2/out/ops/site_reach_mission/site_reach_mission_latest.md'
        site_reach_mission_heartbeat_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/site_reach_mission/site_reach_mission_heartbeat_latest.json'
        investor_packet_refresh_heartbeat_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/investor_packet_refresh/investor_packet_refresh_heartbeat_latest.json'
        parity_markdown = 'INSTITUTIONAL_STACK_V2/out/ops/dashboard_mirror_parity_latest.md'
    }
}

$summary | ConvertTo-Json -Depth 10 | Set-Content -Path $summaryPath -Encoding utf8

$latest = [ordered]@{
    generated_utc = $summary.generated_utc
    latest_artifact = $summaryPath
}
$latest | ConvertTo-Json -Depth 4 | Set-Content -Path $latestPath -Encoding utf8

Write-RefreshHeartbeat -Status 'ok' -Reason 'pipeline_complete' -LastStep 'done' -Extra @{
    steps_total = $steps.Count
    summary_path = $summaryPath
    latest_path = $latestPath
}

Write-Output ("INVESTOR_PACKET_REFRESH_SUMMARY={0}" -f $summaryPath)
Write-Output ("INVESTOR_PACKET_REFRESH_LATEST={0}" -f $latestPath)
Write-Output ("INVESTOR_PACKET_REFRESH_HEARTBEAT={0}" -f $heartbeatPath)
