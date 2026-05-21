[CmdletBinding()]
[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSReviewUnusedParameter', '', Justification = 'Compatibility switches are retained for stable invocation contracts across ops flows.')]
param(
    [double]$HarvestMinScore = 0.30,
    [double]$FillMinScore = 0.40,
    [int]$FillLimit = 25,
    [double]$JobMinScore = 0.38,
    [int]$JobLimit = 20,
    [double]$EmailMinScore = 0.90,
    [int]$EmailMaxPerCycle = 80,
    [double]$DispatchMinFitScore = 0.42,
    [int]$DispatchLimit = 20,
    [int]$ResponseMaxPerCycle = 120,
    [switch]$ContextStrict,
    [int]$GrantTop = 8,
    [int]$GrantRows = 180,
    [switch]$NoContextRefreshStrict,
    [switch]$NoFunding,
    [switch]$NoContractLoanPack,
    [switch]$NoEmailFinder,
    [switch]$NoEmailDispatch,
    [switch]$NoEmailResponseWatcher,
    [switch]$DispatchDryRun,
    [switch]$NoPdf,
    [switch]$NoSocialProfiles,
    [switch]$PublishLinkedInSummary,
    [switch]$DryRunLinkedInPost,
    [switch]$TruthStrict,
    [switch]$SkipGrantHunter,
    [string]$FundingChannels = "grant,key-source,contract,loan,crowdfund",
    [switch]$NoHighPerformancePackagePass,
    [switch]$NoSectorEvidencePush,
    [switch]$NoNodeRedPush,
    [string]$NodeRedBase = "http://127.0.0.1:8787"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($ContextStrict) {
    $NoContextRefreshStrict = $false
}

$stackRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$codeDir = Join-Path $stackRoot "code"
$opsOut = Join-Path $stackRoot "out\ops"
$syncPremiumScript = Join-Path $PSScriptRoot "SYNC_PREMIUM_PACKAGE_MIRROR.ps1"
New-Item -ItemType Directory -Path $opsOut -Force | Out-Null

$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$summaryPath = Join-Path $opsOut "opportunity_engine_v2_$stamp.json"

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

$steps = @()

function Invoke-EngineStep {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Script,
        [Parameter(Mandatory = $false)][string[]]$Args = @()
    )

    $scriptPath = Join-Path $codeDir $Script
    if (-not (Test-Path $scriptPath)) {
        throw "Missing script: $scriptPath"
    }

    Write-Output "[step] $Name"
    & $pythonExe $scriptPath @Args
    $rc = $LASTEXITCODE
    $step = [ordered]@{
        name = $Name
        script = $Script
        args = $Args
        rc = $rc
        utc = (Get-Date).ToUniversalTime().ToString("o")
    }
    $script:steps += $step
    if ($rc -ne 0) {
        throw "Step failed: $Name (rc=$rc)"
    }
}

try {
    if (-not $NoHighPerformancePackagePass) {
        if (-not (Test-Path $syncPremiumScript)) {
            throw "Missing script: $syncPremiumScript"
        }

        $syncStarted = Get-Date
        Write-Output "[step] Sync Premium Performance Package Mirror"
        & $syncPremiumScript -LatestZipCountFromProofs 8 -HashLimitMB 32
        $syncRc = $LASTEXITCODE
        if ($null -eq $syncRc) {
            $syncRc = if ($?) { 0 } else { 1 }
        }
        $syncEnded = Get-Date
        $steps += [ordered]@{
            name = "Sync Premium Performance Package Mirror"
            script = "ops/SYNC_PREMIUM_PACKAGE_MIRROR.ps1"
            args = @("-LatestZipCountFromProofs", "8", "-HashLimitMB", "32")
            rc = $syncRc
            utc = $syncEnded.ToUniversalTime().ToString("o")
            elapsed_sec = [Math]::Round(($syncEnded - $syncStarted).TotalSeconds, 3)
        }
        if ($syncRc -ne 0) {
            throw "Step failed: Sync Premium Performance Package Mirror (rc=$syncRc)"
        }
    }

    $useStrictContext = -not $NoContextRefreshStrict
    $contextArgs = @()
    if ($useStrictContext) {
        $contextArgs = @("--strict")
    }
    Invoke-EngineStep -Name "Resolve Application Context" -Script "application_context_resolver.py" -Args $contextArgs

    $linkedinArgs = @("--max-packages", "28")
    if ($NoPdf) {
        $linkedinArgs += "--no-pdf"
    }
    if ($PublishLinkedInSummary) {
        $linkedinArgs += "--publish-linkedin-summary"
        if ($DryRunLinkedInPost) {
            $linkedinArgs += "--dry-run-post"
        }
    }
    Invoke-EngineStep -Name "LinkedIn + Resume V1" -Script "lumalinkedin_resume_engine_v1.py" -Args $linkedinArgs

    if (-not $NoSocialProfiles) {
        Invoke-EngineStep -Name "Social Platform Profiles V1" -Script "social_platform_profile_engine_v1.py" -Args @("--max-platforms", "8", "--publish-mode", "dry_run")
    }

    Invoke-EngineStep -Name "Build SKIP Grant Autofill Pack" -Script "ops/build_skips_grant_autofill_pack.py"

    Invoke-EngineStep -Name "Opportunity Harvest" -Script "opportunity_harvester.py" -Args @("--min-score", "$HarvestMinScore")
    Invoke-EngineStep -Name "Opportunity Fill" -Script "opportunity_filler.py" -Args @("--min-score", "$FillMinScore", "--limit", "$FillLimit")

    if (-not $SkipGrantHunter) {
        Invoke-EngineStep -Name "Federal Grant Hunter Run-All" -Script "grant_hunter_v2.py" -Args @("run-all", "--rows", "$GrantRows", "--top", "$GrantTop")
    }

    if (-not $NoFunding) {
        Invoke-EngineStep -Name "Funding Queue Build" -Script "funding_autopilot.py" -Args @("build", "--top", "12", "--channels", "$FundingChannels")
    }

    if (-not $NoContractLoanPack) {
        Invoke-EngineStep -Name "Generate Contract + Loan Opportunity Pack" -Script "ops/GENERATE_CONTRACT_LOAN_AND_INVESTOR_PACK.py"
    }

    if (-not $NoEmailFinder) {
        Invoke-EngineStep -Name "Email Opportunity Finder (Once)" -Script "email_opportunity_finder.py" -Args @("--once", "--min-score", "$EmailMinScore", "--max-per-cycle", "$EmailMaxPerCycle")
    }

    if (-not $NoEmailDispatch) {
        $dispatchArgs = @("--once", "--min-fit-score", "$DispatchMinFitScore", "--limit", "$DispatchLimit")
        if ($DispatchDryRun) {
            $dispatchArgs += "--dry-run"
        }
        Invoke-EngineStep -Name "Email Resume Dispatch (Once)" -Script "email_resume_dispatcher.py" -Args $dispatchArgs
    }

    if (-not $NoEmailResponseWatcher) {
        Invoke-EngineStep -Name "Email Response Watcher (Once)" -Script "email_response_watcher.py" -Args @("--once", "--max-per-cycle", "$ResponseMaxPerCycle")
    }

    Invoke-EngineStep -Name "Job Application Factory" -Script "job_application_factory.py" -Args @("--min-score", "$JobMinScore", "--limit", "$JobLimit")
    Invoke-EngineStep -Name "Lock Autonomous Grant Win + Valuation" -Script "ops/LOCK_AUTONOMOUS_GRANT_WIN.py"
    Invoke-EngineStep -Name "Build Booth Design Pack" -Script "ops/build_booth_design_pack.py"
    Invoke-EngineStep -Name "Refresh Booth Explainer Brief" -Script "build_booth_explainer_brief.py"

    if (-not $NoSectorEvidencePush) {
        $sectorArgs = @("--run-investor-sweep")
        if (-not $NoNodeRedPush) {
            $sectorArgs += @("--push-nodered", "--nodered-base", "$NodeRedBase")
        }
        Invoke-EngineStep -Name "Sector + Investor Evidence Pipeline" -Script "ops/run_sector_energy_evidence_pipeline.py" -Args $sectorArgs
    }

    $truthArgs = @()
    if ($TruthStrict) { $truthArgs += "--strict" }
    Invoke-EngineStep -Name "Enforce Production Truth Rule" -Script "ops/ENFORCE_PRODUCTION_TRUTH_RULE.py" -Args $truthArgs

    $summary = [ordered]@{
        generated_utc = (Get-Date).ToUniversalTime().ToString("o")
        scope = "opportunity_engine_v2"
        python = $pythonExe
        stack_root = $stackRoot
        steps = $steps
        status = "ok"
    }
}
catch {
    $summary = [ordered]@{
        generated_utc = (Get-Date).ToUniversalTime().ToString("o")
        scope = "opportunity_engine_v2"
        python = $pythonExe
        stack_root = $stackRoot
        steps = $steps
        status = "failed"
        error = $_.Exception.Message
    }
}

$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $summaryPath -Encoding UTF8
Write-Output "SUMMARY=$summaryPath"

if ($summary.status -ne "ok") {
    exit 2
}
exit 0
