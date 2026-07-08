[CmdletBinding()]
param(
    [string]$StackRoot = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2',
    [string]$RepoUrl = 'https://github.com/robertashworth1986-debug/lumen-core-public.git',
    [int]$Limit = 120,
    [int]$GateTop = 8,
    [switch]$PushToVps,
    [switch]$SkipGitPull
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$started = Get-Date
$startedUtc = $started.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$desktop = [Environment]::GetFolderPath('Desktop')
if ([string]::IsNullOrWhiteSpace($desktop) -or -not (Test-Path -LiteralPath $desktop)) {
    $desktop = (Get-Location).Path
}

$rootParent = Split-Path -Parent $StackRoot
$outOps = Join-Path $StackRoot 'out\ops'
$opsRoot = Join-Path $StackRoot 'code\ops'
$dashboardData = Join-Path $StackRoot 'dashboard\data'
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')

function Write-Step {
    param([string]$Message)
    Write-Host ("[{0}] {1}" -f ((Get-Date).ToUniversalTime().ToString('HH:mm:ssZ')), $Message)
}

function Ensure-Dir {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Read-JsonSafe {
    param([string]$Path)
    try {
        if (Test-Path -LiteralPath $Path) {
            return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -Depth 100
        }
    } catch {}
    return $null
}

function Get-Prop {
    param([object]$Object, [string]$Name, [object]$Default = $null)
    if ($null -eq $Object) { return $Default }
    $prop = $Object.PSObject.Properties[$Name]
    if ($null -ne $prop) { return $prop.Value }
    return $Default
}

function Get-AgeStatus {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return [ordered]@{
            path = $Path
            exists = $false
            modified_utc = $null
            age_hours = $null
            freshness = 'MISSING'
        }
    }
    $item = Get-Item -LiteralPath $Path
    $ageHours = [math]::Round(((Get-Date).ToUniversalTime() - $item.LastWriteTimeUtc).TotalHours, 2)
    $freshness = if ($ageHours -le 24) { 'FRESH' } elseif ($ageHours -le 72) { 'AGING' } else { 'STALE' }
    return [ordered]@{
        path = $Path
        exists = $true
        modified_utc = $item.LastWriteTimeUtc.ToString('yyyy-MM-ddTHH:mm:ssZ')
        age_hours = $ageHours
        freshness = $freshness
    }
}

function Resolve-Python {
    $candidates = @(
        (Join-Path $StackRoot 'code\.venv\Scripts\python.exe'),
        (Join-Path $StackRoot '.venv\Scripts\python.exe'),
        (Join-Path (Split-Path -Parent $StackRoot) 'venv3.11\Scripts\python.exe')
    )
    foreach ($cand in $candidates) {
        if (Test-Path -LiteralPath $cand) { return $cand }
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Invoke-Logged {
    param([string]$Label, [scriptblock]$Action)
    $t0 = Get-Date
    $record = [ordered]@{
        label = $Label
        started_utc = $t0.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        status = 'ok'
        elapsed_sec = 0
        error = ''
    }
    Write-Step "START $Label"
    try {
        $output = & $Action 2>&1
        foreach ($line in @($output)) { Write-Host $line }
    } catch {
        $record.status = 'error'
        $record.error = $_.Exception.Message
        Write-Host ("ERROR {0}: {1}" -f $Label, $record.error)
    }
    $record.elapsed_sec = [math]::Round(((Get-Date) - $t0).TotalSeconds, 2)
    Write-Step "DONE $Label status=$($record.status) elapsed=$($record.elapsed_sec)s"
    return $record
}

Ensure-Dir $rootParent

$steps = New-Object 'System.Collections.Generic.List[object]'

if (-not (Test-Path -LiteralPath $StackRoot)) {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $git) { throw "Stack root not found and git is not installed: $StackRoot" }
    Write-Step "Cloning repo to $StackRoot"
    git clone $RepoUrl $StackRoot
}

Ensure-Dir $outOps
Ensure-Dir $dashboardData

if (-not $SkipGitPull.IsPresent) {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git -and (Test-Path -LiteralPath (Join-Path $StackRoot '.git'))) {
        Push-Location $StackRoot
        try {
            $steps.Add((Invoke-Logged -Label 'git_fetch_pull' -Action {
                git fetch --all --prune
                git pull --ff-only
            }))
        } finally {
            Pop-Location
        }
    }
}

$python = Resolve-Python
if (-not $python) { throw 'Python not found. Install Python 3 or fix the venv path.' }

Push-Location $StackRoot
try {
    $grantHunter = Join-Path $StackRoot 'code\grant_hunter_v2.py'
    if (Test-Path -LiteralPath $grantHunter) {
        $steps.Add((Invoke-Logged -Label 'grant_hunter_v2' -Action {
            & $python $grantHunter
            if ($LASTEXITCODE -ne 0) { throw "grant_hunter_v2 exit code $LASTEXITCODE" }
        }))
    }

    $fastlane = Join-Path $opsRoot 'RUN_GRANT_FACTORY_FASTLANE.ps1'
    if (Test-Path -LiteralPath $fastlane) {
        $steps.Add((Invoke-Logged -Label 'grant_factory_fastlane' -Action {
            $args = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$fastlane,'-State','APPROVED','-Limit',[string]$Limit,'-GateTop',[string]$GateTop,'-RunParityAudit')
            if ($PushToVps.IsPresent) { $args += '-PushToVps' }
            & powershell.exe @args
            if ($LASTEXITCODE -ne 0) { throw "RUN_GRANT_FACTORY_FASTLANE exit code $LASTEXITCODE" }
        }))
    }

    $readiness = Join-Path $opsRoot 'BUILD_GRANT_SUBMISSION_READINESS_AUDIT.py'
    if (Test-Path -LiteralPath $readiness) {
        $steps.Add((Invoke-Logged -Label 'grant_submission_readiness_audit' -Action {
            & $python $readiness
            if ($LASTEXITCODE -ne 0) { throw "BUILD_GRANT_SUBMISSION_READINESS_AUDIT exit code $LASTEXITCODE" }
        }))
    }

    $waiting = Join-Path $opsRoot 'BUILD_GRANT_WAITING_ACTIONS.py'
    if (Test-Path -LiteralPath $waiting) {
        $steps.Add((Invoke-Logged -Label 'grant_waiting_actions' -Action {
            & $python $waiting
            if ($LASTEXITCODE -ne 0) { throw "BUILD_GRANT_WAITING_ACTIONS exit code $LASTEXITCODE" }
        }))
    }

    $followup = Join-Path $opsRoot 'BUILD_GRANT_FOLLOWUP_TRACKER.py'
    if (Test-Path -LiteralPath $followup) {
        $steps.Add((Invoke-Logged -Label 'grant_followup_tracker' -Action {
            & $python $followup
            if ($LASTEXITCODE -ne 0) { throw "BUILD_GRANT_FOLLOWUP_TRACKER exit code $LASTEXITCODE" }
        }))
    }

    $statusFeed = Join-Path $opsRoot 'BUILD_GRANT_DASHBOARD_STATUS_FEED.py'
    if (Test-Path -LiteralPath $statusFeed) {
        $steps.Add((Invoke-Logged -Label 'grant_dashboard_status_feed' -Action {
            & $python $statusFeed
            if ($LASTEXITCODE -ne 0) { throw "BUILD_GRANT_DASHBOARD_STATUS_FEED exit code $LASTEXITCODE" }
        }))
    }
} finally {
    Pop-Location
}

$keyArtifacts = @(
    'out\grant_approval_queue.json',
    'out\grants\grants_ranked_v2.json',
    'out\ops\grant_submit_fit_pack\grant_submit_fit_pack_latest.json',
    'out\ops\grant_factory_fastlane_latest.json',
    'out\ops\grant_submission_readiness_audit_latest.json',
    'out\ops\grant_dashboard_status_feed_latest.json',
    'dashboard\data\grant_readiness_status.json',
    'out\ops\grants_live_submission_ledger_latest.json',
    'out\ops\grants_email_receipts_latest.json',
    'out\ops\mission_control_support\mission_control_support_latest.json'
)

$freshnessRows = @()
foreach ($rel in $keyArtifacts) {
    $freshnessRows += ,(Get-AgeStatus -Path (Join-Path $StackRoot $rel))
}

$fastLatest = Read-JsonSafe (Join-Path $outOps 'grant_factory_fastlane_latest.json')
$fitLatest = Read-JsonSafe (Join-Path $outOps 'grant_submit_fit_pack\grant_submit_fit_pack_latest.json')
$dashLatest = Read-JsonSafe (Join-Path $outOps 'grant_dashboard_status_feed_latest.json')
$readinessLatest = Read-JsonSafe (Join-Path $outOps 'grant_submission_readiness_audit_latest.json')

$staleCount = @($freshnessRows | Where-Object { $_.freshness -eq 'STALE' }).Count
$missingCount = @($freshnessRows | Where-Object { $_.freshness -eq 'MISSING' }).Count
$errorSteps = @($steps | Where-Object { $_.status -ne 'ok' }).Count

$overall = if ($errorSteps -gt 0) {
    'ERRORS_NEED_REVIEW'
} elseif ($missingCount -gt 0) {
    'MISSING_ARTIFACTS'
} elseif ($staleCount -gt 0) {
    'STALE_ARTIFACTS'
} else {
    'FRESH'
}

$payload = [ordered]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    started_utc = $startedUtc
    elapsed_sec = [math]::Round(((Get-Date) - $started).TotalSeconds, 2)
    scope = 'live_grant_freshness_audit'
    stack_root = $StackRoot
    repo_url = $RepoUrl
    python = $python
    overall = $overall
    step_errors = $errorSteps
    stale_artifacts = $staleCount
    missing_artifacts = $missingCount
    steps = @($steps)
    artifact_freshness = @($freshnessRows)
    latest_summaries = [ordered]@{
        fastlane = $fastLatest
        fit_pack_summary = if ($fitLatest) { Get-Prop -Object $fitLatest -Name 'summary' -Default @{} } else { $null }
        dashboard_status = if ($dashLatest) { [ordered]@{ posture = (Get-Prop $dashLatest 'posture' 'UNKNOWN'); summary = (Get-Prop $dashLatest 'summary' @{}) } } else { $null }
        readiness_summary = if ($readinessLatest) { Get-Prop -Object $readinessLatest -Name 'summary' -Default @{} } else { $null }
    }
    boundaries = @(
        'This audit does not submit grants.',
        'Portal certifications, AOR authority, PINs, and final submit remain user-controlled.',
        'Modeled values are not revenue or audited savings.',
        'No autonomous physical control, drone swarm control, weapons, medical diagnosis, or certified safety claim is created by this script.'
    )
}

$jsonPath = Join-Path $outOps ("live_grant_freshness_audit_{0}.json" -f $stamp)
$jsonLatest = Join-Path $outOps 'live_grant_freshness_audit_latest.json'
$mdPath = Join-Path $outOps ("live_grant_freshness_audit_{0}.md" -f $stamp)
$mdLatest = Join-Path $outOps 'live_grant_freshness_audit_latest.md'
$desktopCopy = Join-Path $desktop 'LumenCore_Live_Grant_Freshness_Audit.md'

$payload | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $jsonPath -Encoding utf8
$payload | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $jsonLatest -Encoding utf8

$md = New-Object 'System.Collections.Generic.List[string]'
$md.Add('# LumenCore Live Grant Freshness Audit')
$md.Add('')
$md.Add("Generated UTC: $($payload.generated_utc)")
$md.Add("Overall: $overall")
$md.Add("Stack root: $StackRoot")
$md.Add('')
$md.Add('## Step Results')
foreach ($s in $steps) {
    $line = "- $($s.label): $($s.status) in $($s.elapsed_sec)s"
    if ($s.error) { $line += " — $($s.error)" }
    $md.Add($line)
}
$md.Add('')
$md.Add('## Artifact Freshness')
foreach ($r in $freshnessRows) {
    $rel = $r.path.Replace($StackRoot, '').TrimStart('\')
    $md.Add("- $($r.freshness): $rel | age_hours=$($r.age_hours) | modified_utc=$($r.modified_utc)")
}
$md.Add('')
$md.Add('## Boundaries')
foreach ($b in $payload.boundaries) { $md.Add("- $b") }
$md.Add('')
$md.Add('## Next Move')
if ($overall -eq 'FRESH') {
    $md.Add('- Grant factory is locally fresh. Review final portal gates and mentor/outreach actions next.')
} elseif ($overall -eq 'STALE_ARTIFACTS') {
    $md.Add('- Some artifacts are stale. Re-run this script after checking API keys and source files.')
} elseif ($overall -eq 'MISSING_ARTIFACTS') {
    $md.Add('- Some expected artifacts are missing. Check whether earlier build scripts generated the source queues and packages.')
} else {
    $md.Add('- One or more steps errored. Open the JSON audit and fix the first failed step before submitting anything.')
}

$mdText = ($md -join "`n") + "`n"
$mdText | Set-Content -LiteralPath $mdPath -Encoding utf8
$mdText | Set-Content -LiteralPath $mdLatest -Encoding utf8
$mdText | Set-Content -LiteralPath $desktopCopy -Encoding utf8

$zipPath = Join-Path $desktop ("LumenCore_Live_Grant_Freshness_Audit_{0}.zip" -f $stamp)
$zipItems = @($jsonPath, $jsonLatest, $mdPath, $mdLatest) | Where-Object { Test-Path -LiteralPath $_ }
if ($zipItems.Count -gt 0) {
    Compress-Archive -Path $zipItems -DestinationPath $zipPath -Force
}

Write-Host ''
Write-Host "LIVE_GRANT_FRESHNESS_AUDIT_OVERALL=$overall"
Write-Host "LIVE_GRANT_FRESHNESS_AUDIT_JSON=$jsonLatest"
Write-Host "LIVE_GRANT_FRESHNESS_AUDIT_MD=$mdLatest"
Write-Host "DESKTOP_COPY=$desktopCopy"
Write-Host "ZIP=$zipPath"

if ($overall -eq 'ERRORS_NEED_REVIEW') { exit 2 }
if ($overall -eq 'MISSING_ARTIFACTS') { exit 3 }
if ($overall -eq 'STALE_ARTIFACTS') { exit 4 }
exit 0
