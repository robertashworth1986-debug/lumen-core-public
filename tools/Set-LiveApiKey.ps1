param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[A-Z0-9_]+$')]
    [string]$Name,

    [string]$StackRoot = "C:\LumaTrader\INSTITUTIONAL_STACK_V2",
    [switch]$SetUserEnv,
    [switch]$FromClipboard
)

$ErrorActionPreference = "Stop"

function Get-Sha256Prefix {
    param([string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return "" }
    $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
    $hash = [Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    return ([BitConverter]::ToString($hash) -replace "-", "").Substring(0, 12)
}

function ConvertFrom-SecureStringPlainText {
    param([Security.SecureString]$Secure)
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

function Read-EnvFile {
    param([string]$Path)
    $map = @{}
    if (-not (Test-Path -LiteralPath $Path)) { return $map }
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) { continue }
        $key, $value = $trimmed.Split("=", 2)
        $map[$key.Trim()] = $value.Trim().Trim('"').Trim("'")
    }
    return $map
}

function Update-EnvLine {
    param([string]$Path, [string]$Name, [string]$Value)
    $lines = @()
    if (Test-Path -LiteralPath $Path) { $lines = @(Get-Content -LiteralPath $Path) }
    $found = $false
    $updated = foreach ($line in $lines) {
        if ($line -match "^\s*$([regex]::Escape($Name))\s*=") {
            $found = $true
            "$Name=$Value"
        } else { $line }
    }
    if (-not $found) { $updated += "$Name=$Value" }
    [IO.File]::WriteAllLines($Path, $updated, [Text.UTF8Encoding]::new($false))
}

$EnvPath = Join-Path $StackRoot "config\luma_live_keys.env"
if (-not (Test-Path -LiteralPath $StackRoot)) { throw "Stack root not found: $StackRoot" }
$configDir = Split-Path -Parent $EnvPath
if (-not (Test-Path -LiteralPath $configDir)) { New-Item -ItemType Directory -Path $configDir | Out-Null }

$existing = Read-EnvFile -Path $EnvPath
$old = [string]$existing[$Name]

Write-Host "Luma live API key updater" -ForegroundColor Cyan
Write-Host "Env file: $EnvPath"
Write-Host "Key name: $Name"
if ($old) { Write-Host "Current saved key hash prefix: $(Get-Sha256Prefix $old)" }
else { Write-Host "Current saved key: none" }

if ($FromClipboard) {
    Write-Host "Reading key from clipboard. The key will not be printed." -ForegroundColor Yellow
    $new = (Get-Clipboard -Raw).Trim()
} else {
    $secure = Read-Host "Paste the full $Name value here. It will not be printed" -AsSecureString
    $new = (ConvertFrom-SecureStringPlainText -Secure $secure).Trim()
}

if ([string]::IsNullOrWhiteSpace($new)) { throw "No value entered. Nothing changed." }
if ($new.Length -lt 4) { throw "Value looks too short. Nothing changed." }

Write-Host "New key hash prefix: $(Get-Sha256Prefix $new)"
if ($old) { Write-Host "Matches current saved key: $($old -eq $new)" }

if (Test-Path -LiteralPath $EnvPath) {
    $backup = "$EnvPath.bak.$(Get-Date -Format 'yyyyMMddTHHmmss')"
    Copy-Item -LiteralPath $EnvPath -Destination $backup
    Write-Host "Backup written: $backup" -ForegroundColor DarkCyan
}

Update-EnvLine -Path $EnvPath -Name $Name -Value $new
Set-Item -Path "Env:$Name" -Value $new

if ($SetUserEnv) {
    [Environment]::SetEnvironmentVariable($Name, $new, "User")
    Write-Host "User environment variable $Name updated." -ForegroundColor Green
}

Write-Host "Saved $Name to luma_live_keys.env." -ForegroundColor Green
Write-Host "No key value was printed. Only hash prefixes were shown." -ForegroundColor Green
