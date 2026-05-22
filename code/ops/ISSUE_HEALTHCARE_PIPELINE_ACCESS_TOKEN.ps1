param(
    [string]$Label = "friend",
    [int]$DaysValid = 90,
    [string]$RegistryPath = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\config\healthcare_pipeline_access_registry.json",
    [switch]$RevokeExistingForLabel
)

$ErrorActionPreference = "Stop"

function New-ApiKey {
    $bytes = New-Object byte[] 24
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    $raw = [Convert]::ToBase64String($bytes).TrimEnd('=')
    $raw = $raw.Replace('+', '-').Replace('/', '_')
    return "hcp_$raw"
}

function Get-KeyDigest {
    param([Parameter(Mandatory = $true)][string]$Value)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($Value))
        return -join ($hash | ForEach-Object { $_.ToString('x2') })
    } finally {
        if ($sha) { $sha.Dispose() }
    }
}

$registryDir = Split-Path -Parent $RegistryPath
if (-not (Test-Path $registryDir)) {
    New-Item -Path $registryDir -ItemType Directory -Force | Out-Null
}

$registry = [ordered]@{
    schema = "healthcare_pipeline_access_v1"
    enabled = $true
    operators = @()
}

if (Test-Path $RegistryPath) {
    try {
        $existing = Get-Content -Path $RegistryPath -Raw | ConvertFrom-Json -Depth 20
        if ($existing) {
            $registry.schema = if ($existing.schema) { [string]$existing.schema } else { "healthcare_pipeline_access_v1" }
            if ($existing.PSObject.Properties.Name -contains 'enabled') {
                $registry.enabled = [bool]$existing.enabled
            }
            $registry.operators = @($existing.operators)
        }
    } catch {
        throw "Access registry JSON parse failed: $RegistryPath"
    }
}

$nowUtc = [datetime]::UtcNow
$apiKey = New-ApiKey
$digest = Get-KeyDigest -Value $apiKey
$keyId = "hpa_" + ([guid]::NewGuid().ToString('N').Substring(0, 12))
$expiresUtc = $nowUtc.AddDays([math]::Max(1, $DaysValid)).ToString("o")

if ($RevokeExistingForLabel) {
    $registry.operators = @($registry.operators | ForEach-Object {
        $entry = $_
        if ($entry -and ([string]$entry.label -eq $Label) -and -not [bool]$entry.revoked) {
            $entry | Add-Member -Force -NotePropertyName revoked -NotePropertyValue $true
            $entry | Add-Member -Force -NotePropertyName revoked_utc -NotePropertyValue $nowUtc.ToString("o")
        }
        $entry
    })
}

$newEntry = [ordered]@{
    label = $Label
    key_id = $keyId
    key_sha256 = $digest
    role = "operator"
    created_utc = $nowUtc.ToString("o")
    expires_utc = $expiresUtc
    revoked = $false
}

$registry.operators = @($registry.operators) + @([pscustomobject]$newEntry)

$registryJson = $registry | ConvertTo-Json -Depth 20
Set-Content -Path $RegistryPath -Value $registryJson -Encoding UTF8

$receiptPath = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\ops\healthcare_grants_poc\latest_access_issue_receipt.json"
$receiptDir = Split-Path -Parent $receiptPath
if (-not (Test-Path $receiptDir)) {
    New-Item -Path $receiptDir -ItemType Directory -Force | Out-Null
}

$receipt = [ordered]@{
    generated_utc = $nowUtc.ToString("o")
    registry_path = $RegistryPath
    label = $Label
    key_id = $keyId
    expires_utc = $expiresUtc
    api_key = $apiKey
}

$receipt | ConvertTo-Json -Depth 20 | Set-Content -Path $receiptPath -Encoding UTF8

Write-Output "ISSUE_HEALTHCARE_PIPELINE_ACCESS_TOKEN_OK"
Write-Output "label=$Label"
Write-Output "key_id=$keyId"
Write-Output "expires_utc=$expiresUtc"
Write-Output "registry_path=$RegistryPath"
Write-Output "receipt_path=$receiptPath"
Write-Output "api_key=$apiKey"
