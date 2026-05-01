$ErrorActionPreference = "Stop"

$statusPath = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\public_dashboard_tunnel_status.json"
$urlPath = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\public_dashboard_url.txt"

$url = ""
if (Test-Path -LiteralPath $statusPath) {
    try {
        $status = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
        $url = [string]$status.url
    } catch {
    }
}

if (-not $url -and (Test-Path -LiteralPath $urlPath)) {
    $url = (Get-Content -LiteralPath $urlPath -Raw -ErrorAction SilentlyContinue).Trim()
}

if (-not $url) {
    throw "Public dashboard URL not found. Run RUN_PUBLIC_DASHBOARD_TUNNEL.ps1 first."
}

Write-Host "Opening: $url"
Start-Process $url | Out-Null