$ErrorActionPreference = 'Stop'

$latest = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\startup_boot_health_latest.json'

if (-not (Test-Path $latest)) {
    Write-Host '[WARN] startup boot health file not found.'
    Write-Host ('Path: ' + $latest)
    exit 0
}

$data = Get-Content -Path $latest -Raw | ConvertFrom-Json

Write-Host '=== Startup Boot Health (Latest) ==='
Write-Host ('timestamp_utc: ' + $data.timestamp_utc)
Write-Host ('all_healthy: ' + $data.all_healthy)
Write-Host ''

$data.services | Select-Object Service, Running, ProcessCount | Format-Table -AutoSize
