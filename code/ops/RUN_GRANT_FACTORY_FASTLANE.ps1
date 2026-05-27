[CmdletBinding()]
param(
    [ValidateSet('APPROVED', 'PENDING', 'REVIEW')]
    [string]$State = 'APPROVED',
    [int]$Limit = 120,
    [int]$GateTop = 6,
    [switch]$RunParityAudit,
    [switch]$PushToVps
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = 'C:\LumaTrader'
$stackRoot = Join-Path $root 'INSTITUTIONAL_STACK_V2'
$opsRoot = Join-Path $stackRoot 'code\ops'
$outOps = Join-Path $stackRoot 'out\ops'
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')

if (-not (Test-Path -LiteralPath $outOps)) {
    New-Item -ItemType Directory -Path $outOps -Force | Out-Null
}

$summaryPath = Join-Path $outOps ("grant_factory_fastlane_{0}.json" -f $stamp)
$latestPath = Join-Path $outOps 'grant_factory_fastlane_latest.json'

$fitPackLatestPath = Join-Path $outOps 'grant_submit_fit_pack\grant_submit_fit_pack_latest.json'
$grantsLedgerLatestPath = Join-Path $outOps 'grants_live_submission_ledger_latest.json'
$grantsEmailReceiptsLatestPath = Join-Path $outOps 'grants_email_receipts_latest.json'
$grantFinalGateRoot = Join-Path $outOps 'grant_final_gate'

$buildSkipsScript = Join-Path $opsRoot 'build_skips_grant_autofill_pack.py'
$buildFitPackScript = Join-Path $opsRoot 'BUILD_GRANT_SUBMIT_FIT_PACK.py'
$buildMissionControlSupportScript = Join-Path $opsRoot 'BUILD_MISSION_CONTROL_SUPPORT_ARTIFACTS.py'
$grantFinalGateScript = Join-Path $opsRoot 'RUN_GRANT_FINAL_GATE.py'
$parityScript = Join-Path $opsRoot 'AUDIT_DASHBOARD_MIRROR_PARITY.ps1'
$pushScript = Join-Path $stackRoot 'deploy\PUSH_TO_VPS.ps1'

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
    throw 'Unable to resolve Python executable for grant fastlane pipeline'
}

function Read-JsonFile {
    param(
        [string]$Path,
        [object]$Default = @{}
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $Default
    }

    try {
        return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -Depth 100
    } catch {
        return $Default
    }
}

function To-IntSafe {
    param(
        [object]$Value,
        [int]$Default = 0
    )

    try {
        return [int]([double]$Value)
    } catch {
        return $Default
    }
}

function Get-ObjectProperty {
    param(
        [object]$Object,
        [string]$Name,
        [object]$Default = $null
    )

    if ($null -eq $Object) {
        return $Default
    }

    if ($Object -is [System.Collections.IDictionary]) {
        if ($Object.Contains($Name)) {
            return $Object[$Name]
        }
        return $Default
    }

    $prop = $Object.PSObject.Properties[$Name]
    if ($null -ne $prop) {
        return $prop.Value
    }

    return $Default
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
$gateResults = New-Object 'System.Collections.Generic.List[object]'
$status = 'ok'
$errorMessage = ''

try {
    if (Test-Path -LiteralPath $buildSkipsScript) {
        $steps.Add((Invoke-Step -Label 'build_skips_grant_autofill_pack' -Action {
            & $pythonExe $buildSkipsScript
            if ($LASTEXITCODE -ne 0) {
                throw "build_skips_grant_autofill_pack failed with exit code $LASTEXITCODE"
            }
        }))
    }

    $steps.Add((Invoke-Step -Label 'build_grant_submit_fit_pack' -Action {
        & $pythonExe $buildFitPackScript --state $State --limit $Limit
        if ($LASTEXITCODE -ne 0) {
            throw "BUILD_GRANT_SUBMIT_FIT_PACK failed with exit code $LASTEXITCODE"
        }
    }))

    $steps.Add((Invoke-Step -Label 'build_mission_control_support_artifacts' -Action {
        & $pythonExe $buildMissionControlSupportScript
        if ($LASTEXITCODE -ne 0) {
            throw "BUILD_MISSION_CONTROL_SUPPORT_ARTIFACTS failed with exit code $LASTEXITCODE"
        }
    }))

    $steps.Add((Invoke-Step -Label 'run_grant_final_gate_for_top_fit_likely' -Action {
        $fitPayload = Read-JsonFile -Path $fitPackLatestPath -Default @{}
        $opportunities = @()
        $fitOpps = Get-ObjectProperty -Object $fitPayload -Name 'opportunities' -Default @()
        if ($fitOpps) {
            $opportunities = @($fitOpps)
        }

        $sortProperties = @(
            @{ Expression = { try { [double]$_.days_to_close } catch { 9999.0 } }; Ascending = $true },
            @{ Expression = { try { [double]$_.blueprint_alignment_score } catch { -9999.0 } }; Descending = $true }
        )

        $candidates = @($opportunities |
            Where-Object { $_ -and ([string]$_.fit_status).ToUpperInvariant() -eq 'FIT_LIKELY' } |
            Sort-Object -Property $sortProperties)

        if ($GateTop -gt 0) {
            $candidates = @($candidates | Select-Object -First $GateTop)
        }

        foreach ($row in $candidates) {
            if (-not $row) {
                continue
            }
            $oppNum = [string]$row.opp_num
            if ([string]::IsNullOrWhiteSpace($oppNum)) {
                continue
            }

            & $pythonExe $grantFinalGateScript --opp-num $oppNum
            if ($LASTEXITCODE -ne 0) {
                throw "RUN_GRANT_FINAL_GATE failed for $oppNum with exit code $LASTEXITCODE"
            }

            $oppSlug = ($oppNum.ToLowerInvariant() -replace '[^a-z0-9]+', '_').Trim('_')
            if ([string]::IsNullOrWhiteSpace($oppSlug)) {
                $oppSlug = 'unknown'
            }

            $gatePath = Join-Path $grantFinalGateRoot ("grant_final_gate_{0}_latest.json" -f $oppSlug)
            $gatePayload = Read-JsonFile -Path $gatePath -Default @{}
            $blockers = @((Get-ObjectProperty -Object $gatePayload -Name 'blockers' -Default @()))
            $warnings = @((Get-ObjectProperty -Object $gatePayload -Name 'warnings' -Default @()))
            $decision = [string](Get-ObjectProperty -Object $gatePayload -Name 'decision' -Default '')

            $gateResults.Add([ordered]@{
                opp_num = $oppNum
                title = [string]$row.title
                decision = $decision
                blocker_count = $blockers.Count
                warning_count = $warnings.Count
                gate_json = $gatePath
            })
        }
    }))

    if ($RunParityAudit.IsPresent) {
        $steps.Add((Invoke-Step -Label 'audit_dashboard_mirror_parity' -Action {
            & pwsh -NoProfile -ExecutionPolicy Bypass -File $parityScript
            if ($LASTEXITCODE -ne 0) {
                throw "AUDIT_DASHBOARD_MIRROR_PARITY failed with exit code $LASTEXITCODE"
            }
        }))
    }

    if ($PushToVps.IsPresent) {
        $steps.Add((Invoke-Step -Label 'push_stack_to_vps' -Action {
            & pwsh -NoProfile -ExecutionPolicy Bypass -File $pushScript
            if ($LASTEXITCODE -ne 0) {
                throw "PUSH_TO_VPS failed with exit code $LASTEXITCODE"
            }
        }))
    }
} catch {
    $status = 'error'
    $errorMessage = $_.Exception.Message
}

$fitPayload = Read-JsonFile -Path $fitPackLatestPath -Default @{}
$fitSummary = Get-ObjectProperty -Object $fitPayload -Name 'summary' -Default @{}

$ledgerPayload = Read-JsonFile -Path $grantsLedgerLatestPath -Default @{}
$ledgerSummary = Get-ObjectProperty -Object $ledgerPayload -Name 'summary' -Default @{}

$emailPayload = Read-JsonFile -Path $grantsEmailReceiptsLatestPath -Default @{}
$emailSummary = Get-ObjectProperty -Object $emailPayload -Name 'summary' -Default @{}

$gateApproved = @($gateResults | Where-Object { ([string]$_.decision).ToUpperInvariant() -eq 'APPROVED' }).Count
$gateBlocked = @($gateResults | Where-Object { ([string]$_.decision).ToUpperInvariant() -eq 'BLOCKED' }).Count

$fitSelected = To-IntSafe -Value (Get-ObjectProperty -Object $fitSummary -Name 'selected_opportunities' -Default 0)
$fitLikely = To-IntSafe -Value (Get-ObjectProperty -Object $fitSummary -Name 'fit_likely' -Default 0)
$fitManual = To-IntSafe -Value (Get-ObjectProperty -Object $fitSummary -Name 'manual_check' -Default 0)
$fitHardExclude = To-IntSafe -Value (Get-ObjectProperty -Object $fitSummary -Name 'hard_exclude' -Default 0)
$externalSubmissionRecords = To-IntSafe -Value (Get-ObjectProperty -Object $ledgerSummary -Name 'record_count' -Default 0)
$emailReceiptRecords = To-IntSafe -Value (Get-ObjectProperty -Object $emailSummary -Name 'record_count' -Default 0)

$stepsArray = @()
foreach ($item in $steps) {
    $stepsArray += ,$item
}

$gateResultsArray = @()
foreach ($item in $gateResults) {
    $gateResultsArray += ,$item
}

$payload = [ordered]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    scope = 'grant_factory_fastlane'
    run_stamp = $stamp
    status = $status
    error = $errorMessage
    params = [ordered]@{
        state = $State
        limit = [int]$Limit
        gate_top = [int]$GateTop
        run_parity_audit = [bool]$RunParityAudit.IsPresent
        push_to_vps = [bool]$PushToVps.IsPresent
    }
    elapsed_sec = [math]::Round(((Get-Date) - $pipelineStart).TotalSeconds, 2)
    python_exe = $pythonExe
    steps = $stepsArray
    metrics = [ordered]@{
        fit_selected_opportunities = $fitSelected
        fit_likely = $fitLikely
        manual_check = $fitManual
        hard_exclude = $fitHardExclude
        external_submission_records = $externalSubmissionRecords
        email_receipt_records = $emailReceiptRecords
        gate_checked = $gateResults.Count
        gate_approved = $gateApproved
        gate_blocked = $gateBlocked
    }
    gate_results = $gateResultsArray
    artifacts = [ordered]@{
        grant_submit_fit_pack_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/grant_submit_fit_pack/grant_submit_fit_pack_latest.json'
        grants_live_submission_ledger_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/grants_live_submission_ledger_latest.json'
        grants_email_receipts_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/grants_email_receipts_latest.json'
        mission_control_support_latest_json = 'INSTITUTIONAL_STACK_V2/out/ops/mission_control_support/mission_control_support_latest.json'
        grant_final_gate_root = 'INSTITUTIONAL_STACK_V2/out/ops/grant_final_gate'
    }
}

$payload | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $summaryPath -Encoding utf8

@{
    generated_utc = $payload.generated_utc
    scope = 'grant_factory_fastlane'
    status = $status
    latest_artifact = $summaryPath
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $latestPath -Encoding utf8

Write-Output ("GRANT_FACTORY_FASTLANE_STATUS={0}" -f $status)
Write-Output ("GRANT_FACTORY_FASTLANE_SUMMARY={0}" -f $summaryPath)
Write-Output ("GRANT_FACTORY_FASTLANE_LATEST={0}" -f $latestPath)

if ($status -ne 'ok') {
    throw $errorMessage
}
