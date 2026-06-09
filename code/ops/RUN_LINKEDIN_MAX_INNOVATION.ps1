[CmdletBinding()]
param(
    [string]$ProfileUrl = "https://www.linkedin.com/in/robert-ashworth-40a9b7376",
    [string]$CompanyPageUrl = "",
    [string]$ClientId = "",
    [string]$ClientSecret = "",
    [string]$RedirectUri = "http://127.0.0.1:8787/auth/linkedin/callback",
    [string]$GoogleDriveFileUrl = "https://drive.google.com/file/d/1v1aWtCBYzs6R8EWAs5cMkqXtG7bbr5DC/edit",
    [string]$LocalLogoPath = "",
    [switch]$OpenBrowser,
    [switch]$SkipGatewayProbe,
    [int]$GatewayProbeTimeoutSec = 8
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$stackRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$setupScript = Join-Path $PSScriptRoot "SETUP_LINKEDIN_OAUTH.ps1"
$launchpackScript = Join-Path $PSScriptRoot "BUILD_LINKEDIN_APP_LAUNCHPACK.py"
$outDir = Join-Path $stackRoot "out\ops\linkedin_max_innovation"
$setupLatestPath = Join-Path $stackRoot "out\ops\linkedin_oauth_setup\linkedin_oauth_setup_latest.json"
$launchpackLatestPath = Join-Path $stackRoot "out\ops\linkedin_app_launchpack\linkedin_app_launchpack_latest.json"

New-Item -ItemType Directory -Path $outDir -Force | Out-Null

function Get-NowIso {
    return (Get-Date).ToUniversalTime().ToString("o")
}

function Select-PythonExe {
    $candidatePaths = @(
        (Join-Path (Split-Path -Parent $stackRoot) "venv3.11\Scripts\python.exe"),
        (Join-Path $stackRoot "venv3.11\Scripts\python.exe"),
        (Join-Path $stackRoot "code\.venv\Scripts\python.exe")
    )

    foreach ($candidate in $candidatePaths) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) {
        return "python"
    }

    throw "No Python interpreter found for launchpack build."
}

function Find-LocalLogoCandidate {
    param(
        [string]$ExplicitPath = ""
    )

    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        if (Test-Path $ExplicitPath) {
            return (Resolve-Path $ExplicitPath).Path
        }
    }

    $roots = @(
        "C:\Users\Novac\Downloads",
        "C:\Users\Novac\OneDrive\Downloads"
    )
    $patterns = @(
        "IMG_6468*.jpeg",
        "IMG_6468*.jpg",
        "IMG_6468*.png",
        "IMG_*.jpeg",
        "IMG_*.jpg",
        "IMG_*.png"
    )

    $hits = @()
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) {
            continue
        }
        foreach ($pattern in $patterns) {
            $hits += Get-ChildItem -Path $root -Filter $pattern -File -ErrorAction SilentlyContinue
        }
    }

    $picked = $hits | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
    if ($picked) {
        return $picked.FullName
    }
    return ""
}

function Read-JsonFile {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path $Path)) {
        return $null
    }

    try {
        return Get-Content -Path $Path -Raw | ConvertFrom-Json
    }
    catch {
        return $null
    }
}

$setupParams = @{
    NoPrompt = $true
    RedirectUri = $RedirectUri
}
if (-not [string]::IsNullOrWhiteSpace($ProfileUrl)) {
    $setupParams.ProfileUrl = $ProfileUrl
}
if (-not [string]::IsNullOrWhiteSpace($CompanyPageUrl)) {
    $setupParams.CompanyPageUrl = $CompanyPageUrl
}
if (-not [string]::IsNullOrWhiteSpace($GoogleDriveFileUrl)) {
    $setupParams.GoogleDriveAssetUrl = $GoogleDriveFileUrl
}
if (-not [string]::IsNullOrWhiteSpace($ClientId)) {
    $setupParams.ClientId = $ClientId
}
if (-not [string]::IsNullOrWhiteSpace($ClientSecret)) {
    $setupParams.ClientSecret = $ClientSecret
}
if ($OpenBrowser) {
    $setupParams.OpenBrowser = $true
}

$setupStdout = @()
$setupSucceeded = $true
$setupError = ""
try {
    $setupStdout = & $setupScript @setupParams 2>&1 | ForEach-Object { "$_" }
}
catch {
    $setupSucceeded = $false
    $setupError = $_.Exception.Message
}

$pythonExe = Select-PythonExe
$resolvedLocalLogoPath = Find-LocalLogoCandidate -ExplicitPath $LocalLogoPath
$launchpackArgs = @(
    $launchpackScript,
    "--profile-url", $ProfileUrl,
    "--redirect-uri", $RedirectUri
)
if (-not [string]::IsNullOrWhiteSpace($CompanyPageUrl)) {
    $launchpackArgs += @("--company-page-url", $CompanyPageUrl)
}
if (-not [string]::IsNullOrWhiteSpace($GoogleDriveFileUrl)) {
    $launchpackArgs += @("--google-drive-file-url", $GoogleDriveFileUrl)
    $launchpackArgs += @("--brand-asset-url", $GoogleDriveFileUrl)
}
if (-not [string]::IsNullOrWhiteSpace($resolvedLocalLogoPath)) {
    $launchpackArgs += @("--local-logo-path", $resolvedLocalLogoPath)
}

$launchpackStdout = @()
$launchpackSucceeded = $true
$launchpackError = ""
try {
    $launchpackStdout = & $pythonExe @launchpackArgs 2>&1 | ForEach-Object { "$_" }
}
catch {
    $launchpackSucceeded = $false
    $launchpackError = $_.Exception.Message
}

$setupLatest = Read-JsonFile -Path $setupLatestPath
$launchpackLatest = Read-JsonFile -Path $launchpackLatestPath

$gatewayProbe = [ordered]@{
    attempted = (-not $SkipGatewayProbe)
    reachable = $false
    connected = $false
    error = ""
    status_url = "http://127.0.0.1:8787/auth/linkedin/status"
    payload = $null
}

if (-not $SkipGatewayProbe) {
    try {
        $payload = Invoke-RestMethod -Uri $gatewayProbe.status_url -Method Get -TimeoutSec $GatewayProbeTimeoutSec
        $gatewayProbe.reachable = $true
        $gatewayProbe.payload = $payload
        if ($payload -and $null -ne $payload.connected) {
            $gatewayProbe.connected = [bool]$payload.connected
        }
    }
    catch {
        $gatewayProbe.error = $_.Exception.Message
    }
}

$readinessScore = 0
if ($launchpackLatest -and $null -ne $launchpackLatest.readiness_score_pct) {
    $readinessScore = [int]$launchpackLatest.readiness_score_pct
}

$blockers = [System.Collections.Generic.List[string]]::new()
if (-not $setupSucceeded) {
    $blockers.Add("setup_script_failed")
}
if (-not $launchpackSucceeded) {
    $blockers.Add("launchpack_build_failed")
}
if ($setupLatest -and $setupLatest.missing) {
    $joined = ($setupLatest.missing | ForEach-Object { "$_" }) -join ","
    if (-not [string]::IsNullOrWhiteSpace($joined)) {
        $blockers.Add("missing_keys:$joined")
    }
}
if ($setupLatest -and $setupLatest.metadata_missing) {
    $joinedMeta = ($setupLatest.metadata_missing | ForEach-Object { "$_" }) -join ","
    if (-not [string]::IsNullOrWhiteSpace($joinedMeta)) {
        $blockers.Add("metadata_missing:$joinedMeta")
    }
}
if ($launchpackLatest -and $launchpackLatest.blockers) {
    foreach ($item in $launchpackLatest.blockers) {
        $blockers.Add("$item")
    }
}
if ($gatewayProbe.attempted -and -not $gatewayProbe.reachable) {
    $blockers.Add("gateway_status_unreachable")
}

$uniqueBlockers = @($blockers | Where-Object { -not [string]::IsNullOrWhiteSpace("$_") } | Select-Object -Unique)
$blockers.Clear()
foreach ($item in $uniqueBlockers) {
    $blockers.Add("$item")
}

$nextActions = [System.Collections.Generic.List[string]]::new()
if ($launchpackLatest -and $launchpackLatest.next_actions) {
    foreach ($action in $launchpackLatest.next_actions) {
        if (-not [string]::IsNullOrWhiteSpace("$action")) {
            $nextActions.Add("$action")
        }
    }
}
if ($gatewayProbe.attempted -and -not $gatewayProbe.reachable) {
    $nextActions.Add("Start gateway and re-run status probe at http://127.0.0.1:8787/auth/linkedin/status.")
}
if ($nextActions.Count -eq 0) {
    $nextActions.Add("No blockers detected. Proceed with OAuth consent and publish dry-run.")
}

$uniqueNextActions = @($nextActions | Where-Object { -not [string]::IsNullOrWhiteSpace("$_") } | Select-Object -Unique)
$nextActions.Clear()
foreach ($item in $uniqueNextActions) {
    $nextActions.Add("$item")
}

$status = "in_progress"
$statusReason = "action_required"
if ($blockers.Count -eq 0 -and $readinessScore -ge 100 -and $gatewayProbe.connected) {
    $status = "hyperready"
    $statusReason = "all_checks_passed"
}
elseif ($readinessScore -ge 80 -and $gatewayProbe.reachable -and -not $gatewayProbe.connected) {
    $status = "consent_pending"
    $statusReason = "oauth_token_missing"
}
elseif ($readinessScore -lt 80) {
    $status = "setup_pending"
    $statusReason = "missing_setup_inputs"
}

$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$summaryPath = Join-Path $outDir "linkedin_max_innovation_$stamp.json"
$latestPath = Join-Path $outDir "linkedin_max_innovation_latest.json"
$mdPath = Join-Path $outDir "linkedin_max_innovation_$stamp.md"
$mdLatest = Join-Path $outDir "linkedin_max_innovation_latest.md"

$summary = [ordered]@{
    generated_utc = Get-NowIso
    scope = "linkedin_max_innovation_run"
    status = $status
    status_reason = $statusReason
    readiness_score_pct = $readinessScore
    input = [ordered]@{
        profile_url = $ProfileUrl
        company_page_url = $CompanyPageUrl
        redirect_uri = $RedirectUri
        google_drive_file_url = $GoogleDriveFileUrl
        google_drive_asset_url = $GoogleDriveFileUrl
        local_logo_path_requested = $LocalLogoPath
        local_logo_path_resolved = $resolvedLocalLogoPath
        open_browser = [bool]$OpenBrowser
    }
    scripts = [ordered]@{
        setup_script = $setupScript
        launchpack_script = $launchpackScript
        python_exe = $pythonExe
    }
    setup_run = [ordered]@{
        success = $setupSucceeded
        error = $setupError
        stdout_tail = @($setupStdout | Select-Object -Last 12)
        setup_latest_path = $setupLatestPath
    }
    launchpack_run = [ordered]@{
        success = $launchpackSucceeded
        error = $launchpackError
        stdout_tail = @($launchpackStdout | Select-Object -Last 12)
        launchpack_latest_path = $launchpackLatestPath
    }
    gateway_probe = $gatewayProbe
    blockers = @($blockers)
    next_actions = @($nextActions)
}

$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $summaryPath -Encoding UTF8
Copy-Item -Path $summaryPath -Destination $latestPath -Force

$md = @(
    "# LinkedIn Max Innovation Run",
    "",
    "- generated_utc: $($summary.generated_utc)",
    "- status: $status",
    "- status_reason: $statusReason",
    "- readiness_score_pct: $readinessScore",
    "- google_drive_asset_url: $GoogleDriveFileUrl",
    "",
    "## Blockers",
    $(if ($blockers.Count -gt 0) { $blockers | ForEach-Object { "- $_" } } else { "- none" }),
    "",
    "## Next Actions",
    ($nextActions | ForEach-Object { "- $_" }),
    "",
    "## Artifacts",
    "- run_summary_json: $summaryPath",
    "- latest_summary_json: $latestPath",
    "- setup_latest_json: $setupLatestPath",
    "- launchpack_latest_json: $launchpackLatestPath"
) -join "`n"

Set-Content -Path $mdPath -Value $md -Encoding UTF8
Copy-Item -Path $mdPath -Destination $mdLatest -Force

Write-Output "LINKEDIN_MAX_INNOVATION_STATUS=$status"
Write-Output "LINKEDIN_MAX_INNOVATION_REASON=$statusReason"
Write-Output "LINKEDIN_MAX_INNOVATION_READINESS=$readinessScore"
Write-Output "LINKEDIN_MAX_INNOVATION_SUMMARY=$summaryPath"
Write-Output "LINKEDIN_MAX_INNOVATION_LATEST=$latestPath"
