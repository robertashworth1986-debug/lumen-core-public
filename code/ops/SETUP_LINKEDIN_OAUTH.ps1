[CmdletBinding()]
param(
    [string]$ClientId = "",
    [string]$ClientSecret = "",
    [string]$RedirectUri = "http://127.0.0.1:8787/auth/linkedin/callback",
    [string]$ProfileUrl = "",
    [string]$CompanyPageUrl = "",
    [string]$GoogleDriveAssetUrl = "",
    [switch]$OpenBrowser,
    [switch]$NoPrompt
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$stackRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$configDir = Join-Path $stackRoot "config"
$keyPath = Join-Path $configDir "luma_outreach_keys.env"
$outDir = Join-Path $stackRoot "out\ops\linkedin_oauth_setup"

New-Item -ItemType Directory -Path $configDir -Force | Out-Null
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

$developerPortalUrl = "https://developer.linkedin.com/"
$developerLoginUrl = "https://www.linkedin.com/developers/login"
$appListUrl = "https://www.linkedin.com/developers/apps?appStatus=active"
$appCreateUrl = "https://www.linkedin.com/developers/apps/new?src=direct%2Fnone&veh=direct%2Fnone"
$companyPageCreateUrl = "https://www.linkedin.com/company/setup/new/"
$gatewayStatusUrl = "http://127.0.0.1:8787/auth/linkedin/status"
$gatewayLoginUrl = "http://127.0.0.1:8787/auth/linkedin/login"

function Get-DefaultTemplateBlock {
    return @(
        "# Luma outreach automation keys (gitignored by *.env pattern)",
        "# Fill values, then restart watchers/loop.",
        "",
        "# LinkedIn OAuth app keys",
        "LINKEDIN_CLIENT_ID=",
        "LINKEDIN_CLIENT_SECRET=",
        "LINKEDIN_REDIRECT_URI=http://127.0.0.1:8787/auth/linkedin/callback",
        "LINKEDIN_PROFILE_URL=",
        "LINKEDIN_COMPANY_PAGE_URL=",
        "LINKEDIN_BRAND_ASSET_URL=",
        "",
        "# SMTP outbound (resume dispatch)",
        "LUMA_SMTP_HOST=",
        "LUMA_SMTP_PORT=587",
        "LUMA_SMTP_USER=",
        "LUMA_SMTP_PASSWORD=",
        "LUMA_SMTP_FROM=",
        "LUMA_SMTP_STARTTLS=true",
        "LUMA_SMTP_USE_SSL=false",
        "",
        "# IMAP inbound (opportunity + response watchers)",
        "LUMA_EMAIL_IMAP_HOST=",
        "LUMA_EMAIL_IMAP_PORT=993",
        "LUMA_EMAIL_IMAP_USER=",
        "LUMA_EMAIL_IMAP_PASSWORD=",
        "LUMA_EMAIL_IMAP_FOLDER=INBOX",
        "LUMA_EMAIL_IMAP_SEARCH=UNSEEN"
    )
}

function Get-EnvMapFromBlock {
    param(
        [Parameter(Mandatory = $true)]
        [object]$EnvLineBlock
    )

    $map = @{}
    foreach ($line in $EnvLineBlock) {
        $match = [regex]::Match($line, '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$')
        if (-not $match.Success) {
            continue
        }
        $k = $match.Groups[1].Value.Trim()
        $v = $match.Groups[2].Value.Trim()
        $map[$k] = $v
    }
    return $map
}

function Write-EnvKeyValue {
    param(
        [Parameter(Mandatory = $true)]
        [object]$EnvLineBlock,
        [Parameter(Mandatory = $true)]
        [string]$Key,
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    if ($EnvLineBlock -is [System.Collections.Generic.List[string]]) {
        $lineList = $EnvLineBlock
    }
    else {
        $lineList = [System.Collections.Generic.List[string]]::new()
        foreach ($entry in @($EnvLineBlock)) {
            $lineList.Add([string]$entry)
        }
    }

    $pattern = '^\s*' + [regex]::Escape($Key) + '\s*='
    $replacement = "$Key=$Value"

    for ($i = 0; $i -lt $lineList.Count; $i++) {
        if ($lineList[$i] -match $pattern) {
            $lineList[$i] = $replacement
            return
        }
    }

    if ($lineList.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace($lineList[$lineList.Count - 1])) {
        $lineList.Add("")
    }
    $lineList.Add($replacement)
}

$envLines = [System.Collections.Generic.List[string]]::new()
if (Test-Path $keyPath) {
    foreach ($line in (Get-Content -Path $keyPath)) {
        $envLines.Add($line)
    }
}
else {
    foreach ($line in (Get-DefaultTemplateBlock)) {
        $envLines.Add($line)
    }
}

$current = Get-EnvMapFromBlock -EnvLineBlock $envLines

if (-not $NoPrompt) {
    if (-not $ClientId -and [string]::IsNullOrWhiteSpace(($current["LINKEDIN_CLIENT_ID"]))) {
        $inClientId = Read-Host "Enter LINKEDIN_CLIENT_ID (blank to keep empty)"
        if (-not [string]::IsNullOrWhiteSpace($inClientId)) {
            $ClientId = $inClientId.Trim()
        }
    }
    if (-not $ClientSecret -and [string]::IsNullOrWhiteSpace(($current["LINKEDIN_CLIENT_SECRET"]))) {
        $inClientSecret = Read-Host "Enter LINKEDIN_CLIENT_SECRET (blank to keep empty)"
        if (-not [string]::IsNullOrWhiteSpace($inClientSecret)) {
            $ClientSecret = $inClientSecret.Trim()
        }
    }
    if (-not $RedirectUri) {
        $inRedirect = Read-Host "Enter LINKEDIN_REDIRECT_URI (blank to use default)"
        if (-not [string]::IsNullOrWhiteSpace($inRedirect)) {
            $RedirectUri = $inRedirect.Trim()
        }
    }
    if (-not $ProfileUrl -and [string]::IsNullOrWhiteSpace(($current["LINKEDIN_PROFILE_URL"]))) {
        $inProfileUrl = Read-Host "Enter LINKEDIN_PROFILE_URL (optional, blank to skip)"
        if (-not [string]::IsNullOrWhiteSpace($inProfileUrl)) {
            $ProfileUrl = $inProfileUrl.Trim()
        }
    }
    if (-not $CompanyPageUrl -and [string]::IsNullOrWhiteSpace(($current["LINKEDIN_COMPANY_PAGE_URL"]))) {
        $inCompanyPageUrl = Read-Host "Enter LINKEDIN_COMPANY_PAGE_URL (optional, blank to skip)"
        if (-not [string]::IsNullOrWhiteSpace($inCompanyPageUrl)) {
            $CompanyPageUrl = $inCompanyPageUrl.Trim()
        }
    }
    if (-not $GoogleDriveAssetUrl -and [string]::IsNullOrWhiteSpace(($current["LINKEDIN_BRAND_ASSET_URL"]))) {
        $inGoogleAssetUrl = Read-Host "Enter LINKEDIN_BRAND_ASSET_URL (optional, Google Drive/file link)"
        if (-not [string]::IsNullOrWhiteSpace($inGoogleAssetUrl)) {
            $GoogleDriveAssetUrl = $inGoogleAssetUrl.Trim()
        }
    }
}

if (-not $RedirectUri) {
    $RedirectUri = "http://127.0.0.1:8787/auth/linkedin/callback"
}

if ($ClientId) {
    Write-EnvKeyValue -EnvLineBlock $envLines -Key "LINKEDIN_CLIENT_ID" -Value $ClientId
}
if ($ClientSecret) {
    Write-EnvKeyValue -EnvLineBlock $envLines -Key "LINKEDIN_CLIENT_SECRET" -Value $ClientSecret
}
Write-EnvKeyValue -EnvLineBlock $envLines -Key "LINKEDIN_REDIRECT_URI" -Value $RedirectUri
if ($ProfileUrl) {
    Write-EnvKeyValue -EnvLineBlock $envLines -Key "LINKEDIN_PROFILE_URL" -Value $ProfileUrl
}
if ($CompanyPageUrl) {
    Write-EnvKeyValue -EnvLineBlock $envLines -Key "LINKEDIN_COMPANY_PAGE_URL" -Value $CompanyPageUrl
}
if ($GoogleDriveAssetUrl) {
    Write-EnvKeyValue -EnvLineBlock $envLines -Key "LINKEDIN_BRAND_ASSET_URL" -Value $GoogleDriveAssetUrl
}

$afterWriteProbe = Get-EnvMapFromBlock -EnvLineBlock $envLines
if (-not $afterWriteProbe.ContainsKey("LINKEDIN_CLIENT_ID")) {
    Write-EnvKeyValue -EnvLineBlock $envLines -Key "LINKEDIN_CLIENT_ID" -Value ""
}
if (-not $afterWriteProbe.ContainsKey("LINKEDIN_CLIENT_SECRET")) {
    Write-EnvKeyValue -EnvLineBlock $envLines -Key "LINKEDIN_CLIENT_SECRET" -Value ""
}
if (-not $afterWriteProbe.ContainsKey("LINKEDIN_REDIRECT_URI")) {
    Write-EnvKeyValue -EnvLineBlock $envLines -Key "LINKEDIN_REDIRECT_URI" -Value "http://127.0.0.1:8787/auth/linkedin/callback"
}
if (-not $afterWriteProbe.ContainsKey("LINKEDIN_PROFILE_URL")) {
    Write-EnvKeyValue -EnvLineBlock $envLines -Key "LINKEDIN_PROFILE_URL" -Value ""
}
if (-not $afterWriteProbe.ContainsKey("LINKEDIN_COMPANY_PAGE_URL")) {
    Write-EnvKeyValue -EnvLineBlock $envLines -Key "LINKEDIN_COMPANY_PAGE_URL" -Value ""
}
if (-not $afterWriteProbe.ContainsKey("LINKEDIN_BRAND_ASSET_URL")) {
    Write-EnvKeyValue -EnvLineBlock $envLines -Key "LINKEDIN_BRAND_ASSET_URL" -Value ""
}

Set-Content -Path $keyPath -Value ($envLines -join "`r`n") -Encoding UTF8

$final = Get-EnvMapFromBlock -EnvLineBlock $envLines
$required = @("LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET", "LINKEDIN_REDIRECT_URI")
$missing = @()
foreach ($k in $required) {
    if ([string]::IsNullOrWhiteSpace(($final[$k]))) {
        $missing += $k
    }
}
$configured = ($missing.Count -eq 0)

if ($OpenBrowser) {
    Start-Process $developerPortalUrl
    Start-Process $developerLoginUrl
    Start-Process $appListUrl
    Start-Process $appCreateUrl
    Start-Process $gatewayStatusUrl
    if ($configured) {
        Start-Process $gatewayLoginUrl
    }
}

$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$summaryPath = Join-Path $outDir "linkedin_oauth_setup_$stamp.json"
$latestPath = Join-Path $outDir "linkedin_oauth_setup_latest.json"

$metadataMissing = @()
if ([string]::IsNullOrWhiteSpace(($final["LINKEDIN_PROFILE_URL"]))) {
    $metadataMissing += "LINKEDIN_PROFILE_URL"
}
if ([string]::IsNullOrWhiteSpace(($final["LINKEDIN_COMPANY_PAGE_URL"]))) {
    $metadataMissing += "LINKEDIN_COMPANY_PAGE_URL"
}

$status = "keys_pending"
if ($configured) {
    $status = "ready_for_consent"
    if ($metadataMissing.Count -gt 0) {
        $status = "ready_for_consent_metadata_pending"
    }
}

$summary = [ordered]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString("o")
    scope = "linkedin_oauth_setup"
    key_file = $keyPath
    configured = $configured
    missing = $missing
    metadata_missing = $metadataMissing
    redirect_uri = $final["LINKEDIN_REDIRECT_URI"]
    profile_url = $final["LINKEDIN_PROFILE_URL"]
    company_page_url = $final["LINKEDIN_COMPANY_PAGE_URL"]
    brand_asset_url = $final["LINKEDIN_BRAND_ASSET_URL"]
    developer_portal_url = $developerPortalUrl
    developer_login_url = $developerLoginUrl
    app_list_url = $appListUrl
    app_create_url = $appCreateUrl
    company_page_create_url = $companyPageCreateUrl
    gateway_status_url = $gatewayStatusUrl
    gateway_login_url = $gatewayLoginUrl
    open_browser = [bool]$OpenBrowser
    status = $status
}

$summary | ConvertTo-Json -Depth 6 | Set-Content -Path $summaryPath -Encoding UTF8
Copy-Item -Path $summaryPath -Destination $latestPath -Force

Write-Output "LINKEDIN_SETUP_STATUS=$($summary.status)"
Write-Output "LINKEDIN_SETUP_CONFIGURED=$configured"
Write-Output "LINKEDIN_SETUP_MISSING=$($missing -join ',')"
Write-Output "LINKEDIN_SETUP_METADATA_MISSING=$($metadataMissing -join ',')"
Write-Output "LINKEDIN_SETUP_BRAND_ASSET_URL=$($summary.brand_asset_url)"
Write-Output "LINKEDIN_SETUP_DEVELOPER_PORTAL=$developerPortalUrl"
Write-Output "LINKEDIN_SETUP_DEVELOPER_LOGIN=$developerLoginUrl"
Write-Output "LINKEDIN_SETUP_COMPANY_PAGE_CREATE=$companyPageCreateUrl"
Write-Output "LINKEDIN_SETUP_SUMMARY=$summaryPath"
Write-Output "LINKEDIN_SETUP_LATEST=$latestPath"
