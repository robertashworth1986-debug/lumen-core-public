$ErrorActionPreference = "Stop"

$statusPath = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\public_dashboard_tunnel_status.json"

if (-not (Test-Path -LiteralPath $statusPath)) {
    Write-Host "[WARN] Public tunnel status file not found: $statusPath"
    exit 1
}

$status = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
$status | Format-List
