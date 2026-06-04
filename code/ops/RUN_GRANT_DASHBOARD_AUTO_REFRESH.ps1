[CmdletBinding()]
param(
    [string]$Owner = 'Robert Ashworth',
    [string]$TargetTrackingNumber = '',
    [string]$TargetOppNum = '',
    [switch]$RunParityAudit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$runParityAudit = $RunParityAudit.IsPresent
if (-not $PSBoundParameters.ContainsKey('RunParityAudit')) {
    $runParityAudit = $true
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

$buildMissionSupport = Join-Path $opsRoot 'BUILD_MISSION_CONTROL_SUPPORT_ARTIFACTS.py'
$buildWaitingActions = Join-Path $opsRoot 'BUILD_GRANT_WAITING_ACTIONS.py'
$buildResubChecklist = Join-Path $opsRoot 'BUILD_GRANT_RESUBMISSION_CHECKLIST.py'
$buildFollowupTracker = Join-Path $opsRoot 'BUILD_GRANT_FOLLOWUP_TRACKER.py'
$parityScript = Join-Path $opsRoot 'AUDIT_DASHBOARD_MIRROR_PARITY.ps1'

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

$pipelineStart = Get-Date
$steps = New-Object 'System.Collections.Generic.List[object]'
$status = 'ok'
$errorMessage = ''

try {
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

$payload = [ordered]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    scope = 'grant_dashboard_auto_refresh'
    run_stamp = $stamp
    status = $status
    error = $errorMessage
    params = [ordered]@{
        owner = $Owner
        target_tracking_number = $TargetTrackingNumber
        target_opp_num = $TargetOppNum
        run_parity_audit = [bool]$runParityAudit
    }
    elapsed_sec = [math]::Round(((Get-Date) - $pipelineStart).TotalSeconds, 2)
    python_exe = $pythonExe
    steps = $stepsArray
    artifacts = [ordered]@{
        grants_live_submission_ledger_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/grants_live_submission_ledger_latest.json'
        grant_waiting_actions_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/grant_waiting_actions_latest.json'
        grant_resubmission_checklist_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/grant_resubmission_checklist_latest.json'
        grant_followup_tracker_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/grant_followup_tracker_latest.json'
        grant_followup_tracker_latest_csv = 'INSTITUTIONAL_STACK_V2/out/ops/grant_followup_tracker_latest.csv'
    }
}

$payload | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $summaryPath -Encoding utf8

@{
    generated_utc = $payload.generated_utc
    scope = 'grant_dashboard_auto_refresh'
    status = $status
    latest_artifact = $summaryPath
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $latestPath -Encoding utf8

Write-Output ("GRANT_DASHBOARD_AUTO_REFRESH_STATUS={0}" -f $status)
Write-Output ("GRANT_DASHBOARD_AUTO_REFRESH_SUMMARY={0}" -f $summaryPath)
Write-Output ("GRANT_DASHBOARD_AUTO_REFRESH_LATEST={0}" -f $latestPath)

if ($status -ne 'ok') {
    throw $errorMessage
}
