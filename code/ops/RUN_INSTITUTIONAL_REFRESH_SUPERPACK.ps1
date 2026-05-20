[CmdletBinding()]
param(
    [ValidateSet('none', 'dry_run', 'post')]
    [string]$LinkedInPublishMode = 'dry_run',
    [switch]$RunInvestorPacketRefresh,
    [int]$TopN = 8,
    [switch]$SkipParityAudit
)

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$outOps = Join-Path $root 'out\ops'
New-Item -ItemType Directory -Path $outOps -Force | Out-Null

$pythonCandidates = @(
    (Join-Path $root '..\venv3.11\Scripts\python.exe'),
    (Join-Path $root 'venv3.11\Scripts\python.exe'),
    'python'
)
$pythonExe = $null
foreach ($candidate in $pythonCandidates) {
    if ($candidate -eq 'python') {
        $pythonExe = $candidate
        break
    }
    if (Test-Path $candidate) {
        $pythonExe = $candidate
        break
    }
}
if (-not $pythonExe) {
    throw 'Python executable not found.'
}

$generatedUtc = (Get-Date).ToUniversalTime().ToString('o')
$tag = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')

$summary = [ordered]@{
    generated_utc = $generatedUtc
    scope = 'institutional_refresh_superpack'
    options = [ordered]@{
        linkedin_publish_mode = $LinkedInPublishMode
        run_investor_packet_refresh = [bool]$RunInvestorPacketRefresh
        top_n = [int]$TopN
        skip_parity_audit = [bool]$SkipParityAudit
    }
    python = $pythonExe
    stack_root = $root
    steps = @()
    overall_status = 'running'
}

function Add-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory
    )

    $started = (Get-Date).ToUniversalTime().ToString('o')
    $step = [ordered]@{
        name = $Name
        started_utc = $started
        command = $Command
        args = $Arguments
        cwd = $WorkingDirectory
        rc = -1
        duration_sec = 0
        status = 'running'
    }

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $rc = 0
    $errMsg = $null

    Push-Location $WorkingDirectory
    try {
        & $Command @Arguments
        $rc = if ($LASTEXITCODE -is [int]) { $LASTEXITCODE } else { 0 }
    }
    catch {
        $rc = if ($LASTEXITCODE -is [int] -and $LASTEXITCODE -ne 0) { $LASTEXITCODE } else { 1 }
        $errMsg = $_.Exception.Message
    }
    finally {
        Pop-Location
        $sw.Stop()
    }

    $step.rc = $rc
    $step.duration_sec = [math]::Round($sw.Elapsed.TotalSeconds, 2)
    $step.status = if ($rc -eq 0) { 'ok' } else { 'failed' }
    if ($errMsg) {
        $step.error = $errMsg
    }

    $summary.steps += $step

    if ($rc -ne 0) {
        throw "step_failed:$Name rc=$rc"
    }
}

try {
    Add-Step -Name 'hard_truth_live_measurement_audit' -Command $pythonExe -Arguments @('code/HARD_TRUTH_LIVE_MEASUREMENT_AUDIT.py') -WorkingDirectory $root
    Add-Step -Name 'live_key_measurement_audit' -Command $pythonExe -Arguments @('code/ops/live_key_measurement_audit.py') -WorkingDirectory $root
    Add-Step -Name 'provider_kpi_roi_plot_pack' -Command $pythonExe -Arguments @('code/ops/build_provider_kpi_roi_plot_pack.py') -WorkingDirectory $root
    Add-Step -Name 'external_context_inventory' -Command $pythonExe -Arguments @('code/ops/ingest_external_context_inventory.py') -WorkingDirectory $root

    $linkedinArgs = @('code/lumalinkedin_resume_engine_v1.py')
    if ($LinkedInPublishMode -eq 'dry_run') {
        $linkedinArgs += '--publish-linkedin-summary'
        $linkedinArgs += '--dry-run-post'
    }
    elseif ($LinkedInPublishMode -eq 'post') {
        $linkedinArgs += '--publish-linkedin-summary'
    }
    Add-Step -Name 'linkedin_resume_engine_v1' -Command $pythonExe -Arguments $linkedinArgs -WorkingDirectory $root

    Add-Step -Name 'social_platform_profile_engine_v1' -Command $pythonExe -Arguments @('code/social_platform_profile_engine_v1.py', '--max-platforms', '8', '--publish-mode', 'dry_run') -WorkingDirectory $root

    Add-Step -Name 'alpaca_paper_status_no_orders' -Command $pythonExe -Arguments @('-m', 'execution.alpaca_paper_executor', '--status-only', '--no-orders') -WorkingDirectory (Join-Path $root 'code')

    if ($RunInvestorPacketRefresh) {
        Add-Step -Name 'investor_packet_refresh_with_proof_sweep' -Command 'pwsh' -Arguments @(
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            'code/ops/RUN_INVESTOR_PACKET_REFRESH.ps1',
            '-TopN',
            [string]$TopN,
            '-RunInvestorProofSweep'
        ) -WorkingDirectory $root
    }

    if (-not $SkipParityAudit) {
        Add-Step -Name 'dashboard_mirror_parity_audit' -Command 'pwsh' -Arguments @(
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            'code/ops/AUDIT_DASHBOARD_MIRROR_PARITY.ps1'
        ) -WorkingDirectory $root
    }

    $summary.overall_status = 'ok'
}
catch {
    $summary.overall_status = 'failed'
    $summary.error = $_.Exception.Message
}

$summary.completed_utc = (Get-Date).ToUniversalTime().ToString('o')
$summary.successful_steps = @($summary.steps | Where-Object { $_.status -eq 'ok' }).Count
$summary.failed_steps = @($summary.steps | Where-Object { $_.status -eq 'failed' }).Count

$summaryPath = Join-Path $outOps "institutional_refresh_superpack_$tag.json"
$latestPath = Join-Path $outOps 'institutional_refresh_superpack_latest.json'
$mdPath = Join-Path $outOps "institutional_refresh_superpack_$tag.md"
$latestMdPath = Join-Path $outOps 'institutional_refresh_superpack_latest.md'

$summary | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $summaryPath
$summary | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $latestPath

$md = @()
$md += '# Institutional Refresh Superpack'
$md += ''
$md += "Generated UTC: $($summary.generated_utc)"
$md += "Completed UTC: $($summary.completed_utc)"
$md += "Status: $($summary.overall_status)"
$md += ''
$md += '## Step Results'
$md += '| Step | Status | RC | Duration (s) |'
$md += '|---|---|---:|---:|'
foreach ($step in $summary.steps) {
    $md += "| $($step.name) | $($step.status) | $($step.rc) | $($step.duration_sec) |"
}
$md += ''
$md += '## Evidence Paths'
$md += "- JSON: $summaryPath"
$md += "- Latest JSON: $latestPath"
$md += "- Markdown: $mdPath"
$md += "- Latest Markdown: $latestMdPath"

$mdText = ($md -join "`n") + "`n"
Set-Content -Encoding UTF8 -Path $mdPath -Value $mdText
Set-Content -Encoding UTF8 -Path $latestMdPath -Value $mdText

Write-Output "SUMMARY_JSON=$summaryPath"
Write-Output "SUMMARY_MD=$mdPath"
Write-Output "STATUS=$($summary.overall_status)"

if ($summary.overall_status -ne 'ok') {
    exit 1
}

exit 0
