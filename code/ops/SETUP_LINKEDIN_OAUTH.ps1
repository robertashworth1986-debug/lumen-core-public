[CmdletBinding()]
param(
    [string]$ClientId = "",
    [string]$ClientSecret = "",
    [string]$RedirectUri = "http://127.0.0.1:8787/auth/linkedin/callback",
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

$appCreateUrl = "https://www.linkedin.com/developers/apps/new"
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
    Start-Process $appCreateUrl
    Start-Process $gatewayStatusUrl
    if ($configured) {
        Start-Process $gatewayLoginUrl
    }
}

$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$summaryPath = Join-Path $outDir "linkedin_oauth_setup_$stamp.json"
$latestPath = Join-Path $outDir "linkedin_oauth_setup_latest.json"

$summary = [ordered]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString("o")
    scope = "linkedin_oauth_setup"
    key_file = $keyPath
    configured = $configured
    missing = $missing
    redirect_uri = $final["LINKEDIN_REDIRECT_URI"]
    app_create_url = $appCreateUrl
    gateway_status_url = $gatewayStatusUrl
    gateway_login_url = $gatewayLoginUrl
    open_browser = [bool]$OpenBrowser
    status = if ($configured) { "ready_for_consent" } else { "keys_pending" }
}

$summary | ConvertTo-Json -Depth 6 | Set-Content -Path $summaryPath -Encoding UTF8
Copy-Item -Path $summaryPath -Destination $latestPath -Force

Write-Output "LINKEDIN_SETUP_STATUS=$($summary.status)"
Write-Output "LINKEDIN_SETUP_CONFIGURED=$configured"
Write-Output "LINKEDIN_SETUP_MISSING=$($missing -join ',')"
Write-Output "LINKEDIN_SETUP_SUMMARY=$summaryPath"
Write-Output "LINKEDIN_SETUP_LATEST=$latestPath"
