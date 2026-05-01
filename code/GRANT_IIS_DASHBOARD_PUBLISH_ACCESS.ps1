param(
    [string]$WebRoot = 'C:\inetpub\wwwroot',
    [string]$Principal = "$env:USERDOMAIN\$env:USERNAME"
)

$ErrorActionPreference = 'Stop'

function Assert-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
        throw 'Run this script from an elevated PowerShell session.'
    }
}

Assert-Admin

if (-not (Test-Path -LiteralPath $WebRoot)) {
    throw "Web root not found: $WebRoot"
}

$targets = @(
    $WebRoot,
    (Join-Path $WebRoot 'index.html'),
    (Join-Path $WebRoot 'LUMENCORE_MASTER_DASHBOARD_UNIFIED_20260425.html')
)

foreach ($target in $targets) {
    if (Test-Path -LiteralPath $target) {
        & icacls $target /grant "${Principal}:(M)" | Out-Null
    }
}

& icacls $WebRoot /grant "${Principal}:(OI)(CI)(M)" | Out-Null

Write-Host "Granted Modify on $WebRoot to $Principal"
Write-Host 'Dashboard refresh loop can now publish into IIS webroot without elevation.'