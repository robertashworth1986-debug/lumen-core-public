param(
    [string]$StackRoot = "C:\LumaTrader\INSTITUTIONAL_STACK_V2",
    [switch]$Validate,
    [switch]$SetUserEnv,
    [switch]$FromClipboard
)

$ErrorActionPreference = "Stop"

function Get-Sha256Prefix {
    param([string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return ""
    }
    $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
    $hash = [Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    return ([BitConverter]::ToString($hash) -replace "-", "").Substring(0, 12)
}

function ConvertFrom-SecureStringPlainText {
    param([Security.SecureString]$Secure)
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

function Read-EnvFile {
    param([string]$Path)
    $map = @{}
    if (-not (Test-Path -LiteralPath $Path)) {
        return $map
    }
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
            continue
        }
        $key, $value = $trimmed.Split("=", 2)
        $map[$key.Trim()] = $value.Trim().Trim('"').Trim("'")
    }
    return $map
}

function Update-EnvLine {
    param(
        [string]$Path,
        [string]$Name,
        [string]$Value
    )

    $lines = @()
    if (Test-Path -LiteralPath $Path) {
        $lines = @(Get-Content -LiteralPath $Path)
    }

    $found = $false
    $updated = foreach ($line in $lines) {
        if ($line -match "^\s*$([regex]::Escape($Name))\s*=") {
            $found = $true
            "$Name=$Value"
        }
        else {
            $line
        }
    }

    if (-not $found) {
        $updated += "$Name=$Value"
    }

    [IO.File]::WriteAllLines($Path, $updated, [Text.UTF8Encoding]::new($false))
}

function Test-SamKey {
    param([string]$Key)
    $encodedKey = [Uri]::EscapeDataString($Key)
    $today = (Get-Date).ToString("MM/dd/yyyy")
    $url = "https://api.sam.gov/opportunities/v2/search?limit=1&postedFrom=01/01/2026&postedTo=$today&api_key=$encodedKey"
    try {
        $response = Invoke-RestMethod -Uri $url -TimeoutSec 30
        $rows = 0
        if ($response.opportunitiesData) {
            $rows = @($response.opportunitiesData).Count
        }
        if ($rows -gt 0) {
            Write-Host "SAM.gov validation: OK ($rows row returned)." -ForegroundColor Green
            return $true
        }
        Write-Host "SAM.gov validation: API responded but no usable rows returned." -ForegroundColor Yellow
        return $false
    }
    catch {
        $message = $_.Exception.Message
        $message = $message -replace [regex]::Escape($Key), "[REDACTED]"
        Write-Host "SAM.gov validation failed: $message" -ForegroundColor Red
        return $false
    }
}

$EnvPath = Join-Path $StackRoot "config\luma_live_keys.env"
$RegistryPath = Join-Path $StackRoot "config\live_source_registry.json"

if (-not (Test-Path -LiteralPath $StackRoot)) {
    throw "Stack root not found: $StackRoot"
}

$configDir = Split-Path -Parent $EnvPath
if (-not (Test-Path -LiteralPath $configDir)) {
    New-Item -ItemType Directory -Path $configDir | Out-Null
}

$existingEnv = Read-EnvFile -Path $EnvPath
$oldKey = [string]$existingEnv["SAM_GOV_API_KEY"]
if (-not $oldKey) {
    $oldKey = [string]$existingEnv["SAM_API_KEY"]
}

$registryExpectsSam = $false
$registryStatus = "unknown"
if (Test-Path -LiteralPath $RegistryPath) {
    try {
        $registry = Get-Content -Raw -LiteralPath $RegistryPath | ConvertFrom-Json
        $samRow = @($registry.rows | Where-Object { $_.source -eq "SAM_GOV" }) | Select-Object -First 1
        if ($samRow) {
            $registryExpectsSam = (@($samRow.env_names) -contains "SAM_GOV_API_KEY") -or (@($samRow.env_names) -contains "SAM_API_KEY")
            $registryStatus = [string]$samRow.status
        }
    }
    catch {
        $registryStatus = "unreadable"
    }
}

Write-Host "Luma SAM.gov API key updater" -ForegroundColor Cyan
Write-Host "Env file: $EnvPath"
Write-Host "Registry expects SAM key: $registryExpectsSam"
Write-Host "Current registry SAM_GOV status: $registryStatus"
if ($oldKey) {
    Write-Host "Current saved SAM key hash prefix: $(Get-Sha256Prefix $oldKey)"
}
else {
    Write-Host "Current saved SAM key: none"
}

if ($FromClipboard) {
    Write-Host "Reading SAM.gov key from clipboard. The key will not be printed." -ForegroundColor Yellow
    $newKey = (Get-Clipboard -Raw).Trim()
}
else {
    $secure = Read-Host "Paste the full SAM.gov API key here. It will not be printed" -AsSecureString
    $newKey = (ConvertFrom-SecureStringPlainText -Secure $secure).Trim()
}

if ([string]::IsNullOrWhiteSpace($newKey)) {
    throw "No key was entered."
}

if ($newKey.Length -lt 16) {
    throw "That key looks too short. Nothing was changed."
}

if ($newKey -notmatch "^SAM-[A-Za-z0-9-]{20,}$") {
    throw "That does not look like a SAM.gov key. Nothing was changed."
}

Write-Host "New SAM key hash prefix: $(Get-Sha256Prefix $newKey)"
if ($oldKey) {
    Write-Host "Matches current saved key: $($oldKey -eq $newKey)"
}

if (Test-Path -LiteralPath $EnvPath) {
    $backup = "$EnvPath.bak.$(Get-Date -Format 'yyyyMMddTHHmmss')"
    Copy-Item -LiteralPath $EnvPath -Destination $backup
    Write-Host "Backup written: $backup" -ForegroundColor DarkCyan
}

Update-EnvLine -Path $EnvPath -Name "SAM_GOV_API_KEY" -Value $newKey
$env:SAM_GOV_API_KEY = $newKey
$env:SAM_API_KEY = $newKey

if ($SetUserEnv) {
    [Environment]::SetEnvironmentVariable("SAM_GOV_API_KEY", $newKey, "User")
    Write-Host "User environment variable SAM_GOV_API_KEY updated." -ForegroundColor Green
}

Write-Host "Saved SAM_GOV_API_KEY to luma_live_keys.env." -ForegroundColor Green

if ($Validate) {
    [void](Test-SamKey -Key $newKey)
}
else {
    Write-Host "Validation skipped. Re-run with -Validate to test the SAM.gov endpoint." -ForegroundColor Yellow
}
