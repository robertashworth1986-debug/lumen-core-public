param(
    [string]$StackRoot = "C:\LumaTrader\INSTITUTIONAL_STACK_V2",
    [switch]$Validate,
    [switch]$SetUserEnv
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

function Test-EiaKey {
    param([string]$Key)
    $encodedKey = [Uri]::EscapeDataString($Key)
    $url = "https://api.eia.gov/v2/electricity/rto/daily-region-data/data/?api_key=$encodedKey&frequency=daily&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=1"
    try {
        $response = Invoke-RestMethod -Uri $url -TimeoutSec 30
        $rows = 0
        if ($response.response -and $response.response.data) {
            $rows = @($response.response.data).Count
        }
        if ($rows -gt 0) {
            Write-Host "EIA validation: OK ($rows row returned)." -ForegroundColor Green
            return $true
        }
        Write-Host "EIA validation: no usable rows returned." -ForegroundColor Yellow
        return $false
    }
    catch {
        $message = $_.Exception.Message
        $message = $message -replace [regex]::Escape($Key), "[REDACTED]"
        Write-Host "EIA validation failed: $message" -ForegroundColor Red
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
$oldKey = [string]$existingEnv["EIA_API_KEY"]

$registryExpectsEia = $false
$registryStatus = "unknown"
if (Test-Path -LiteralPath $RegistryPath) {
    try {
        $registry = Get-Content -Raw -LiteralPath $RegistryPath | ConvertFrom-Json
        $eiaRow = @($registry.rows | Where-Object { $_.source -eq "EIA" }) | Select-Object -First 1
        if ($eiaRow) {
            $registryExpectsEia = @($eiaRow.env_names) -contains "EIA_API_KEY"
            $registryStatus = [string]$eiaRow.status
        }
    }
    catch {
        $registryStatus = "unreadable"
    }
}

Write-Host "Luma EIA API key updater" -ForegroundColor Cyan
Write-Host "Env file: $EnvPath"
Write-Host "Registry expects EIA_API_KEY: $registryExpectsEia"
Write-Host "Current registry EIA status: $registryStatus"
if ($oldKey) {
    Write-Host "Current saved EIA key hash prefix: $(Get-Sha256Prefix $oldKey)"
}
else {
    Write-Host "Current saved EIA key: none"
}

$secure = Read-Host "Paste the full EIA API key here. It will not be printed" -AsSecureString
$newKey = (ConvertFrom-SecureStringPlainText -Secure $secure).Trim()

if ([string]::IsNullOrWhiteSpace($newKey)) {
    throw "No key was entered."
}

if ($newKey.Length -lt 12) {
    throw "That key looks too short. Nothing was changed."
}

Write-Host "New EIA key hash prefix: $(Get-Sha256Prefix $newKey)"
if ($oldKey) {
    Write-Host "Matches current saved key: $($oldKey -eq $newKey)"
}

if (Test-Path -LiteralPath $EnvPath) {
    $backup = "$EnvPath.bak.$(Get-Date -Format 'yyyyMMddTHHmmss')"
    Copy-Item -LiteralPath $EnvPath -Destination $backup
    Write-Host "Backup written: $backup" -ForegroundColor DarkCyan
}

Update-EnvLine -Path $EnvPath -Name "EIA_API_KEY" -Value $newKey
$env:EIA_API_KEY = $newKey

if ($SetUserEnv) {
    [Environment]::SetEnvironmentVariable("EIA_API_KEY", $newKey, "User")
    Write-Host "User environment variable EIA_API_KEY updated." -ForegroundColor Green
}

Write-Host "Saved EIA_API_KEY to luma_live_keys.env." -ForegroundColor Green

if ($Validate) {
    [void](Test-EiaKey -Key $newKey)
}
else {
    Write-Host "Validation skipped. Re-run with -Validate to test the EIA endpoint." -ForegroundColor Yellow
}
