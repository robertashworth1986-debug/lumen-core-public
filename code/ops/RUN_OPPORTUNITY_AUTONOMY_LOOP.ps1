[CmdletBinding()]
param(
    [int]$IntervalSec = 420,
    [int]$MaxPackages = 28,
    [double]$EmailMinScore = 0.90,
    [int]$EmailMaxPerCycle = 80,
    [double]$DispatchMinFitScore = 0.42,
    [int]$DispatchLimit = 20,
    [double]$JobMinScore = 0.38,
    [int]$JobLimit = 20,
    [int]$ResponseMaxPerCycle = 120,
    [switch]$NoPdf,
    [switch]$PublishLinkedInSummary,
    [switch]$DryRunLinkedInPost,
    [switch]$DryRunEmailDispatch,
    [switch]$NoTruthStrict
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$stackRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$codeDir = Join-Path $stackRoot "code"
$opsOut = Join-Path $stackRoot "out\ops\opportunity_autonomy_loop"
New-Item -ItemType Directory -Path $opsOut -Force | Out-Null

$pythonCandidates = @(
    (Join-Path $stackRoot ".venv\Scripts\python.exe"),
    (Join-Path $stackRoot "..\venv3.11\Scripts\python.exe"),
    (Join-Path $stackRoot "venv3.11\Scripts\python.exe")
)

$pythonExe = $null
foreach ($candidate in $pythonCandidates) {
    if (Test-Path $candidate) {
        $pythonExe = (Resolve-Path $candidate).Path
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
    throw "Python executable not found. Activate a venv or install python."
}

function Invoke-CycleStep {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Script,
        [Parameter(Mandatory = $false)][string[]]$Args = @()
    )

    $scriptPath = Join-Path $codeDir $Script
    if (-not (Test-Path $scriptPath)) {
        throw "Missing script: $scriptPath"
    }

    $started = Get-Date
    Write-Host "[cycle-step] $Name" -ForegroundColor Cyan
    & $pythonExe $scriptPath @Args
    $rc = $LASTEXITCODE
    $ended = Get-Date

    $step = [ordered]@{
        name = $Name
        script = $Script
        args = $Args
        rc = $rc
        started_utc = $started.ToUniversalTime().ToString("o")
        ended_utc = $ended.ToUniversalTime().ToString("o")
        elapsed_sec = [Math]::Round(($ended - $started).TotalSeconds, 3)
    }

    if ($rc -ne 0) {
        throw "Step failed: $Name (rc=$rc)"
    }

    return $step
}

Write-Host "=====================================================" -ForegroundColor Green
Write-Host " OPPORTUNITY AUTONOMY LOOP" -ForegroundColor Green
Write-Host " Stack: $stackRoot" -ForegroundColor Green
Write-Host " Python: $pythonExe" -ForegroundColor Green
Write-Host " IntervalSec=$IntervalSec" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Green

$cycle = 0
while ($true) {
    $cycle += 1
    $cycleStamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
    $summaryPath = Join-Path $opsOut "cycle_$cycleStamp.json"
    $latestPath = Join-Path $opsOut "cycle_latest.json"

    $steps = @()
    $status = "ok"
    $errorMessage = $null

    try {
        $steps += Invoke-CycleStep -Name "Resolve Application Context" -Script "application_context_resolver.py" -Args @("--strict")

        $linkedinArgs = @("--max-packages", "$MaxPackages")
        if ($NoPdf) {
            $linkedinArgs += "--no-pdf"
        }
        if ($PublishLinkedInSummary) {
            $linkedinArgs += "--publish-linkedin-summary"
            if ($DryRunLinkedInPost) {
                $linkedinArgs += "--dry-run-post"
            }
        }
        $steps += Invoke-CycleStep -Name "LinkedIn Resume Refresh" -Script "lumalinkedin_resume_engine_v1.py" -Args $linkedinArgs

        $steps += Invoke-CycleStep -Name "Email Opportunity Finder" -Script "email_opportunity_finder.py" -Args @("--once", "--min-score", "$EmailMinScore", "--max-per-cycle", "$EmailMaxPerCycle")

        $dispatchArgs = @("--once", "--min-fit-score", "$DispatchMinFitScore", "--limit", "$DispatchLimit")
        if ($DryRunEmailDispatch) {
            $dispatchArgs += "--dry-run"
        }
        $steps += Invoke-CycleStep -Name "Email Resume Dispatch" -Script "email_resume_dispatcher.py" -Args $dispatchArgs

        $steps += Invoke-CycleStep -Name "Email Response Watcher" -Script "email_response_watcher.py" -Args @("--once", "--max-per-cycle", "$ResponseMaxPerCycle")

        $steps += Invoke-CycleStep -Name "Job Application Factory" -Script "job_application_factory.py" -Args @("--min-score", "$JobMinScore", "--limit", "$JobLimit")

        $truthArgs = @()
        if (-not $NoTruthStrict) {
            $truthArgs += "--strict"
        }
        $steps += Invoke-CycleStep -Name "Enforce Production Truth Rule" -Script "ops/ENFORCE_PRODUCTION_TRUTH_RULE.py" -Args $truthArgs
    }
    catch {
        $status = "failed"
        $errorMessage = $_.Exception.Message
        Write-Warning $errorMessage
    }

    $summary = [ordered]@{
        generated_utc = (Get-Date).ToUniversalTime().ToString("o")
        scope = "opportunity_autonomy_loop"
        cycle = $cycle
        status = $status
        error = $errorMessage
        stack_root = $stackRoot
        python = $pythonExe
        interval_sec = $IntervalSec
        steps = $steps
    }

    $summary | ConvertTo-Json -Depth 8 | Set-Content -Path $summaryPath -Encoding UTF8
    $summary | ConvertTo-Json -Depth 8 | Set-Content -Path $latestPath -Encoding UTF8

    Write-Host "CYCLE=$cycle STATUS=$status SUMMARY=$summaryPath"
    Start-Sleep -Seconds ([Math]::Max(30, $IntervalSec))
}
