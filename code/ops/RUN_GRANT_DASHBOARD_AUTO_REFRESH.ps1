[CmdletBinding()]
param(
    [string]$Owner = 'Robert Ashworth',
    [string]$TargetTrackingNumber = '',
    [string]$TargetOppNum = '',
    [switch]$RunParityAudit,
    [switch]$IncludeKrakenChecks,
    [switch]$RefreshOpportunities
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$runParityAudit = $RunParityAudit.IsPresent
if (-not $PSBoundParameters.ContainsKey('RunParityAudit')) {
    $runParityAudit = $true
}

$includeKrakenChecks = $IncludeKrakenChecks.IsPresent
if (-not $PSBoundParameters.ContainsKey('IncludeKrakenChecks')) {
    $includeKrakenChecks = $true
}

$root = 'C:\LumaTrader'
$stackRoot = Join-Path $root 'INSTITUTIONAL_STACK_V2'
$opsRoot = Join-Path $stackRoot 'code\ops'
$outOps = Join-Path $stackRoot 'out\ops'
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')

if (-not (Test-Path -LiteralPath $outOps)) {
    New-Item -ItemType Directory -Path $outOps -Force | Out-Null
}

$summaryPath = Join-Path $outOps ("grant_dashboard_auto_refresh_{0}.json" -f $stamp)
$latestPath = Join-Path $outOps 'grant_dashboard_auto_refresh_latest.json'
$lastKnownGoodPath = Join-Path $outOps 'grant_dashboard_auto_refresh_last_known_good.json'
$failureLatestPath = Join-Path $outOps 'grant_dashboard_auto_refresh_failure_latest.json'

$opportunityHarvester = Join-Path $stackRoot 'code\opportunity_harvester.py'
$buildEmailReconciliation = Join-Path $opsRoot 'BUILD_EMAIL_ACTION_RECONCILIATION.py'
$buildOutreachQueue = Join-Path $opsRoot 'BUILD_OUTREACH_FOLLOWUP_ACTION_QUEUE.py'
$buildExternalEngagementRegister = Join-Path $opsRoot 'BUILD_EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER.py'
$buildNearDeadlineBoard = Join-Path $opsRoot 'BUILD_NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD.py'
$buildPackageDecisionGate = Join-Path $opsRoot 'BUILD_NEAR_DEADLINE_PACKAGE_DECISION_GATE.py'
$buildPortalHandoff = Join-Path $opsRoot 'BUILD_LIVE_FUNDING_PORTAL_HANDOFF.py'
$buildSubmissionConformance = Join-Path $opsRoot 'BUILD_SUBMISSION_CONFORMANCE_GATE.py'
$buildReviewerGate = Join-Path $opsRoot 'BUILD_FUNDING_SPRINT_REVIEWER_GATE.py'
$buildHumanActionDocket = Join-Path $opsRoot 'BUILD_HUMAN_ACTION_DOCKET.py'
$buildAgencyAssemblyGate = Join-Path $opsRoot 'BUILD_AGENCY_SUBMISSION_ASSEMBLY_GATE.py'
$buildSubmissionAuthorityMatrix = Join-Path $opsRoot 'BUILD_SUBMISSION_AUTHORITY_MATRIX.py'
$buildMissionSupport = Join-Path $opsRoot 'BUILD_MISSION_CONTROL_SUPPORT_ARTIFACTS.py'
$buildWaitingActions = Join-Path $opsRoot 'BUILD_GRANT_WAITING_ACTIONS.py'
$buildResubChecklist = Join-Path $opsRoot 'BUILD_GRANT_RESUBMISSION_CHECKLIST.py'
$buildFollowupTracker = Join-Path $opsRoot 'BUILD_GRANT_FOLLOWUP_TRACKER.py'
$analyzeTraderBleed = Join-Path $opsRoot 'ANALYZE_TRADER_BLEED.py'
$buildGrantKrakenBrief = Join-Path $opsRoot 'BUILD_GRANT_KRAKEN_ACTION_BRIEF.py'
$parityScript = Join-Path $opsRoot 'AUDIT_DASHBOARD_MIRROR_PARITY.ps1'
$growthController = Join-Path $stackRoot 'code\execution\kraken_live_growth_controller.py'
$nearDeadlineBoardJson = Join-Path $outOps 'near_deadline_submission_command_board_latest.json'
$packageDecisionGateJson = Join-Path $outOps 'near_deadline_package_decision_gate_latest.json'
$portalHandoffJson = Join-Path $outOps 'live_funding_portal_handoff_latest.json'
$humanActionDocketJson = Join-Path $outOps 'human_action_docket_latest.json'

$controllerName = 'Robert'
if (-not [string]::IsNullOrWhiteSpace($Owner)) {
    $controllerName = ($Owner -split '\s+')[0]
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
    throw 'Unable to resolve Python executable for grant dashboard auto refresh'
}

function Write-AtomicJson {
    param(
        [string]$Path,
        [object]$Value,
        [int]$Depth = 12
    )

    $directory = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }
    $temporaryPath = Join-Path $directory (
        ".{0}.{1}.tmp" -f [System.IO.Path]::GetFileName($Path), [guid]::NewGuid()
    )
    try {
        $json = $Value | ConvertTo-Json -Depth $Depth
        [System.IO.File]::WriteAllText(
            $temporaryPath,
            $json + [Environment]::NewLine,
            [System.Text.UTF8Encoding]::new($false)
        )
        if ((Get-Item -LiteralPath $temporaryPath).Length -le 2) {
            throw "Refusing to publish an empty JSON artifact: $Path"
        }
        if (Test-Path -LiteralPath $Path) {
            $backupPath = "$Path.replace-backup"
            if (Test-Path -LiteralPath $backupPath) {
                [System.IO.File]::Delete($backupPath)
            }
            [System.IO.File]::Replace($temporaryPath, $Path, $backupPath, $true)
            if (Test-Path -LiteralPath $backupPath) {
                [System.IO.File]::Delete($backupPath)
            }
        }
        else {
            [System.IO.File]::Move($temporaryPath, $Path)
        }
    }
    finally {
        if (Test-Path -LiteralPath $temporaryPath) {
            [System.IO.File]::Delete($temporaryPath)
        }
    }
}

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

function Read-RequiredJson {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required JSON artifact is missing: $Path"
    }
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Test-DeadlineSnapshotLineage {
    $board = Read-RequiredJson -Path $nearDeadlineBoardJson
    $packageGate = Read-RequiredJson -Path $packageDecisionGateJson
    $portalHandoff = Read-RequiredJson -Path $portalHandoffJson
    $humanDocket = Read-RequiredJson -Path $humanActionDocketJson

    $boardHash = [string]$board.command_board_sha256
    if ($boardHash -notmatch '^[0-9a-f]{64}$') {
        throw 'Published command board has no valid declared SHA-256'
    }
    if ([string]$packageGate.source_command_board_sha256 -ne $boardHash) {
        throw 'Package decision gate is not bound to the published command board'
    }
    if ([string]$portalHandoff.source_command_board_sha256 -ne $boardHash) {
        throw 'Portal handoff is not bound to the published command board'
    }
    if ($humanDocket.summary.deadline_handoff_source_current -ne $true) {
        throw 'Human action docket does not report a current deadline handoff source'
    }

    $boardFileHash = (Get-FileHash -LiteralPath $nearDeadlineBoardJson -Algorithm SHA256).Hash.ToLowerInvariant()
    $handoffFileHash = (Get-FileHash -LiteralPath $portalHandoffJson -Algorithm SHA256).Hash.ToLowerInvariant()
    if ([string]$humanDocket.source_ledgers.near_deadline_submission_command_board.sha256 -ne $boardFileHash) {
        throw 'Human action docket command-board file receipt is stale'
    }
    if ([string]$humanDocket.source_ledgers.live_funding_portal_handoff.sha256 -ne $handoffFileHash) {
        throw 'Human action docket portal-handoff file receipt is stale'
    }

    $boardByNumber = @{}
    foreach ($lane in @($board.lanes)) {
        $number = [string]$lane.opportunity_number
        if (-not [string]::IsNullOrWhiteSpace($number)) {
            $boardByNumber[$number] = $lane
        }
    }

    $handoffNumbers = New-Object 'System.Collections.Generic.HashSet[string]'
    foreach ($item in @($portalHandoff.queue)) {
        $number = [string]$item.opportunity_number
        if (-not $boardByNumber.ContainsKey($number)) {
            throw "Portal handoff includes a lane absent from the board: $number"
        }
        if ([string]$item.source_lane_sha256 -ne [string]$boardByNumber[$number].lane_sha256) {
            throw "Portal handoff lane hash is stale: $number"
        }
        [void]$handoffNumbers.Add($number)
    }

    $dueWithinSevenDays = @(
        $board.lanes | Where-Object {
            $_.handoff_disposition -eq 'QUEUE' -and
            $_.deadline_actionable -eq $true -and
            $null -ne $_.days_to_close_from_scan_date -and
            [int]$_.days_to_close_from_scan_date -ge 0 -and
            [int]$_.days_to_close_from_scan_date -le 7
        }
    )
    $missingDueLanes = @(
        $dueWithinSevenDays | Where-Object {
            -not $handoffNumbers.Contains([string]$_.opportunity_number)
        }
    )
    if ($missingDueLanes.Count -gt 0) {
        $missingNumbers = ($missingDueLanes | ForEach-Object { $_.opportunity_number }) -join ', '
        throw "Actionable seven-day lanes are absent from the portal handoff: $missingNumbers"
    }

    return [ordered]@{
        verified = $true
        command_board_sha256 = $boardHash
        board_lane_count = @($board.lanes).Count
        portal_handoff_lane_count = @($portalHandoff.queue).Count
        actionable_due_within_seven_days_count = $dueWithinSevenDays.Count
        missing_due_within_seven_days_count = 0
        human_docket_source_current = $true
    }
}

$pipelineStart = Get-Date
$steps = New-Object 'System.Collections.Generic.List[object]'
$status = 'ok'
$errorMessage = ''
$deadlineSnapshotLineage = [ordered]@{
    verified = $false
}
$workspaceDrive = [System.IO.DriveInfo]::new(
    [System.IO.Path]::GetPathRoot($stackRoot)
)
$minimumFreeBytes = 1GB
$freeBytesAtStart = $workspaceDrive.AvailableFreeSpace

try {
    $steps.Add((Invoke-Step -Label 'workspace_free_space_preflight' -Action {
        if ($freeBytesAtStart -lt $minimumFreeBytes) {
            throw (
                "Workspace drive free space is below the 1 GiB safety floor: {0} bytes" -f
                $freeBytesAtStart
            )
        }
    }))

    if ($RefreshOpportunities.IsPresent) {
        $steps.Add((Invoke-Step -Label 'refresh_official_opportunity_harvest' -Action {
            & $pythonExe $opportunityHarvester
            if ($LASTEXITCODE -ne 0) {
                throw "opportunity_harvester failed with exit code $LASTEXITCODE"
            }
        }))
    }

    $steps.Add((Invoke-Step -Label 'build_email_action_reconciliation' -Action {
        & $pythonExe $buildEmailReconciliation
        if ($LASTEXITCODE -ne 0) {
            throw "BUILD_EMAIL_ACTION_RECONCILIATION failed with exit code $LASTEXITCODE"
        }
    }))

    $steps.Add((Invoke-Step -Label 'build_outreach_followup_action_queue' -Action {
        & $pythonExe $buildOutreachQueue
        if ($LASTEXITCODE -ne 0) {
            throw "BUILD_OUTREACH_FOLLOWUP_ACTION_QUEUE failed with exit code $LASTEXITCODE"
        }
    }))

    $steps.Add((Invoke-Step -Label 'build_external_engagement_response_register' -Action {
        & $pythonExe $buildExternalEngagementRegister
        if ($LASTEXITCODE -ne 0) {
            throw "BUILD_EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER failed with exit code $LASTEXITCODE"
        }
    }))

    $steps.Add((Invoke-Step -Label 'build_near_deadline_submission_command_board' -Action {
        & $pythonExe $buildNearDeadlineBoard
        if ($LASTEXITCODE -ne 0) {
            throw (
                "BUILD_NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD failed with exit code " +
                $LASTEXITCODE
            )
        }
    }))

    $steps.Add((Invoke-Step -Label 'build_near_deadline_package_decision_gate' -Action {
        & $pythonExe $buildPackageDecisionGate
        if ($LASTEXITCODE -ne 0) {
            throw (
                "BUILD_NEAR_DEADLINE_PACKAGE_DECISION_GATE failed with exit code " +
                $LASTEXITCODE
            )
        }
    }))

    $steps.Add((Invoke-Step -Label 'build_live_funding_portal_handoff' -Action {
        & $pythonExe $buildPortalHandoff
        if ($LASTEXITCODE -ne 0) {
            throw "BUILD_LIVE_FUNDING_PORTAL_HANDOFF failed with exit code $LASTEXITCODE"
        }
    }))

    $steps.Add((Invoke-Step -Label 'build_submission_conformance_gate' -Action {
        & $pythonExe $buildSubmissionConformance
        if ($LASTEXITCODE -ne 0) {
            throw "BUILD_SUBMISSION_CONFORMANCE_GATE failed with exit code $LASTEXITCODE"
        }
    }))

    $steps.Add((Invoke-Step -Label 'build_funding_sprint_reviewer_gate' -Action {
        & $pythonExe $buildReviewerGate
        if ($LASTEXITCODE -ne 0) {
            throw "BUILD_FUNDING_SPRINT_REVIEWER_GATE failed with exit code $LASTEXITCODE"
        }
    }))

    $steps.Add((Invoke-Step -Label 'build_human_action_docket' -Action {
        & $pythonExe $buildHumanActionDocket
        if ($LASTEXITCODE -ne 0) {
            throw "BUILD_HUMAN_ACTION_DOCKET failed with exit code $LASTEXITCODE"
        }
    }))

    $steps.Add((Invoke-Step -Label 'build_agency_submission_assembly_gate' -Action {
        & $pythonExe $buildAgencyAssemblyGate
        if ($LASTEXITCODE -ne 0) {
            throw (
                "BUILD_AGENCY_SUBMISSION_ASSEMBLY_GATE failed with exit code " +
                $LASTEXITCODE
            )
        }
    }))

    $steps.Add((Invoke-Step -Label 'verify_deadline_snapshot_lineage' -Action {
        $script:deadlineSnapshotLineage = Test-DeadlineSnapshotLineage
        $script:deadlineSnapshotLineage | ConvertTo-Json -Compress
    }))

    $steps.Add((Invoke-Step -Label 'build_mission_control_support_artifacts' -Action {
        & $pythonExe $buildMissionSupport
        if ($LASTEXITCODE -ne 0) {
            throw "BUILD_MISSION_CONTROL_SUPPORT_ARTIFACTS failed with exit code $LASTEXITCODE"
        }
    }))

    $steps.Add((Invoke-Step -Label 'build_grant_waiting_actions' -Action {
        & $pythonExe $buildWaitingActions
        if ($LASTEXITCODE -ne 0) {
            throw "BUILD_GRANT_WAITING_ACTIONS failed with exit code $LASTEXITCODE"
        }
    }))

    $steps.Add((Invoke-Step -Label 'build_grant_resubmission_checklist' -Action {
        $args = @($buildResubChecklist, '--owner', $Owner)
        if (-not [string]::IsNullOrWhiteSpace($TargetTrackingNumber)) {
            $args += @('--tracking-number', $TargetTrackingNumber)
        }
        if (-not [string]::IsNullOrWhiteSpace($TargetOppNum)) {
            $args += @('--opp-num', $TargetOppNum)
        }
        & $pythonExe @args
        if ($LASTEXITCODE -ne 0) {
            throw "BUILD_GRANT_RESUBMISSION_CHECKLIST failed with exit code $LASTEXITCODE"
        }
    }))

    $steps.Add((Invoke-Step -Label 'build_grant_followup_tracker' -Action {
        & $pythonExe $buildFollowupTracker
        if ($LASTEXITCODE -ne 0) {
            throw "BUILD_GRANT_FOLLOWUP_TRACKER failed with exit code $LASTEXITCODE"
        }
    }))

    if ($includeKrakenChecks) {
        $steps.Add((Invoke-Step -Label 'analyze_trader_bleed' -Action {
            & $pythonExe $analyzeTraderBleed
            if ($LASTEXITCODE -ne 0) {
                throw "ANALYZE_TRADER_BLEED failed with exit code $LASTEXITCODE"
            }
        }))

        $steps.Add((Invoke-Step -Label 'refresh_kraken_growth_controller_status' -Action {
            $args = @($growthController, '--cached', '--controller', $controllerName)
            & $pythonExe @args
            if ($LASTEXITCODE -ne 0) {
                throw "kraken_live_growth_controller failed with exit code $LASTEXITCODE"
            }
        }))

        $steps.Add((Invoke-Step -Label 'build_grant_kraken_action_brief' -Action {
            & $pythonExe $buildGrantKrakenBrief
            if ($LASTEXITCODE -ne 0) {
                throw "BUILD_GRANT_KRAKEN_ACTION_BRIEF failed with exit code $LASTEXITCODE"
            }
        }))
    }

    if ($runParityAudit) {
        $steps.Add((Invoke-Step -Label 'audit_dashboard_mirror_parity' -Action {
            & pwsh -NoProfile -ExecutionPolicy Bypass -File $parityScript
            if ($LASTEXITCODE -ne 0) {
                throw "AUDIT_DASHBOARD_MIRROR_PARITY failed with exit code $LASTEXITCODE"
            }
        }))
    }
}
catch {
    $status = 'error'
    $errorMessage = $_.Exception.Message
}

$stepsArray = @()
foreach ($item in $steps) {
    $stepsArray += ,$item
}

$generatedUtc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$payload = [ordered]@{
    generated_utc = $generatedUtc
    scope = 'grant_dashboard_auto_refresh'
    run_stamp = $stamp
    status = $status
    error = $errorMessage
    params = [ordered]@{
        owner = $Owner
        target_tracking_number = $TargetTrackingNumber
        target_opp_num = $TargetOppNum
        run_parity_audit = [bool]$runParityAudit
        include_kraken_checks = [bool]$includeKrakenChecks
        refresh_opportunities = [bool]$RefreshOpportunities.IsPresent
    }
    free_bytes_at_start = $freeBytesAtStart
    minimum_free_bytes = $minimumFreeBytes
    elapsed_sec = [math]::Round(((Get-Date) - $pipelineStart).TotalSeconds, 2)
    python_exe = $pythonExe
    steps = $stepsArray
    deadline_snapshot_lineage = $deadlineSnapshotLineage
    artifacts = [ordered]@{
        email_action_reconciliation_json = 'INSTITUTIONAL_STACK_V2/grant_submissions/funding_sprint_20260709/EMAIL_ACTION_RECONCILIATION_2026-07-18.json'
        outreach_followup_action_queue_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/outreach_followup_action_queue_latest.json'
        near_deadline_submission_command_board_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/near_deadline_submission_command_board_latest.json'
        near_deadline_package_decision_gate_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/near_deadline_package_decision_gate_latest.json'
        live_funding_portal_handoff_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/live_funding_portal_handoff_latest.json'
        submission_conformance_gate_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/submission_conformance_gate_latest.json'
        funding_sprint_reviewer_gate_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/funding_sprint_reviewer_gate_latest.json'
        human_action_docket_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/human_action_docket_latest.json'
        agency_submission_assembly_gate_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/agency_submission_assembly_gate_latest.json'
        grants_live_submission_ledger_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/grants_live_submission_ledger_latest.json'
        grant_waiting_actions_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/grant_waiting_actions_latest.json'
        grant_resubmission_checklist_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/grant_resubmission_checklist_latest.json'
        grant_followup_tracker_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/grant_followup_tracker_latest.json'
        grant_followup_tracker_latest_csv = 'INSTITUTIONAL_STACK_V2/out/ops/grant_followup_tracker_latest.csv'
        trader_bleed_snapshot_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/trader_bleed_snapshot/trader_bleed_snapshot_latest.json'
        vps_growth_controller_status_json = 'INSTITUTIONAL_STACK_V2/out/execution/vps_growth_controller_status.json'
        grant_kraken_action_brief_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/grant_kraken_action_brief/grant_kraken_action_brief_latest.json'
    }
}

Write-AtomicJson -Path $summaryPath -Value $payload

$pointer = [ordered]@{
    generated_utc = $generatedUtc
    scope = 'grant_dashboard_auto_refresh'
    status = $status
    latest_artifact = $summaryPath
}

if ($status -eq 'ok') {
    # The docket evaluates this receipt. Publish a provisional current pointer,
    # then rebuild receipt-dependent controls before sealing the run.
    Write-AtomicJson -Path $latestPath -Value $pointer -Depth 6
    try {
        $steps.Add((Invoke-Step -Label 'reconcile_human_action_docket_after_refresh_receipt' -Action {
            & $pythonExe $buildHumanActionDocket
            if ($LASTEXITCODE -ne 0) {
                throw (
                    "Post-receipt BUILD_HUMAN_ACTION_DOCKET failed with exit code " +
                    $LASTEXITCODE
                )
            }
        }))

        $steps.Add((Invoke-Step -Label 'reconcile_agency_submission_assembly_gate_after_refresh_receipt' -Action {
            & $pythonExe $buildAgencyAssemblyGate
            if ($LASTEXITCODE -ne 0) {
                throw (
                    "Post-receipt BUILD_AGENCY_SUBMISSION_ASSEMBLY_GATE failed with exit code " +
                    $LASTEXITCODE
                )
            }
        }))

        $steps.Add((Invoke-Step -Label 'reconcile_submission_authority_matrix_after_refresh_receipt' -Action {
            & $pythonExe $buildSubmissionAuthorityMatrix
            if ($LASTEXITCODE -ne 0) {
                throw (
                    "Post-receipt BUILD_SUBMISSION_AUTHORITY_MATRIX failed with exit code " +
                    $LASTEXITCODE
                )
            }
        }))
    }
    catch {
        $status = 'error'
        $errorMessage = $_.Exception.Message
    }

    $stepsArray = @()
    foreach ($item in $steps) {
        $stepsArray += ,$item
    }
    $payload['status'] = $status
    $payload['error'] = $errorMessage
    $payload['elapsed_sec'] = [math]::Round(((Get-Date) - $pipelineStart).TotalSeconds, 2)
    $payload['steps'] = $stepsArray
    Write-AtomicJson -Path $summaryPath -Value $payload
    $pointer['status'] = $status

    if ($status -eq 'ok') {
        Write-AtomicJson -Path $latestPath -Value $pointer -Depth 6
        Write-AtomicJson -Path $lastKnownGoodPath -Value $pointer -Depth 6
    }
    else {
        $pointer['last_known_good_pointer'] = $lastKnownGoodPath
        Write-AtomicJson -Path $latestPath -Value $pointer -Depth 6
        Write-AtomicJson -Path $failureLatestPath -Value $pointer -Depth 6
    }
}
else {
    $pointer['last_known_good_pointer'] = $lastKnownGoodPath
    Write-AtomicJson -Path $latestPath -Value $pointer -Depth 6
    Write-AtomicJson -Path $failureLatestPath -Value $pointer -Depth 6
}

Write-Output ("GRANT_DASHBOARD_AUTO_REFRESH_STATUS={0}" -f $status)
Write-Output ("GRANT_DASHBOARD_AUTO_REFRESH_SUMMARY={0}" -f $summaryPath)
Write-Output (
    "GRANT_DASHBOARD_AUTO_REFRESH_POINTER={0}" -f
    $(if ($status -eq 'ok') { $latestPath } else { $failureLatestPath })
)

if ($status -ne 'ok') {
    throw $errorMessage
}
