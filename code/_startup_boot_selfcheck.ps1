param(
    [int]$WaitSeconds = 45
)

$ErrorActionPreference = 'Stop'

if ($WaitSeconds -gt 0) {
    Start-Sleep -Seconds $WaitSeconds
}

$root = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2'
$outDir = Join-Path $root 'out\execution'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$all = Get-CimInstance Win32_Process

$dashboard = @($all | Where-Object {
    (
        $_.Name -like 'python*' -and (
            $_.CommandLine -like '*dashboard_unified_refresh.py*' -or
            $_.CommandLine -like '*build_institutional_crypto_paper_dashboard.py*'
        )
    ) -or (
        ($_.Name -like 'powershell*' -or $_.Name -like 'pwsh*') -and
        $_.CommandLine -like '*RUN_INSTITUTIONAL_CRYPTO_DASHBOARD.ps1*'
    )
}).Count

$sector = @($all | Where-Object {
    $_.Name -like 'python*' -and $_.CommandLine -like '*sector_opp_gain_server*'
}).Count

$infra = @($all | Where-Object {
    $_.Name -like 'python*' -and $_.CommandLine -like '*build_infra_audit_dashboard.py*'
}).Count

$paper = @($all | Where-Object {
    (
        ($_.Name -like 'powershell*' -or $_.Name -like 'pwsh*') -and (
            $_.CommandLine -like '*RUN_ALPACA_PAPER_247.ps1*' -or
            $_.CommandLine -like '*RUN_MULTI_EXCHANGE_PAPER_TICKER.ps1*'
        )
    ) -or (
        $_.Name -like 'python*' -and
        $_.CommandLine -like '*multi_exchange_paper_ticker.py*'
    )
}).Count

$services = @(
    [PSCustomObject]@{ Service = 'dashboard_loop'; Running = ($dashboard -gt 0); ProcessCount = $dashboard },
    [PSCustomObject]@{ Service = 'sector_api'; Running = ($sector -gt 0); ProcessCount = $sector },
    [PSCustomObject]@{ Service = 'infra_loop'; Running = ($infra -gt 0); ProcessCount = $infra },
    [PSCustomObject]@{ Service = 'paper_trader'; Running = ($paper -gt 0); ProcessCount = $paper }
)

$allHealthy = (@($services | Where-Object { -not $_.Running }).Count -eq 0)

$payload = [ordered]@{
    timestamp_utc = [DateTime]::UtcNow.ToString('o')
    wait_seconds = $WaitSeconds
    all_healthy = $allHealthy
    services = $services
}

$latest = Join-Path $outDir 'startup_boot_health_latest.json'
$history = Join-Path $outDir 'startup_boot_health_history.jsonl'

$json = $payload | ConvertTo-Json -Depth 6
Set-Content -Path $latest -Value $json -Encoding ASCII
Add-Content -Path $history -Value ($json -replace "`r?`n", '') -Encoding ASCII

Write-Host ('[OK] Startup boot self-check written: ' + $latest)
Write-Host ('[OK] All services healthy: ' + $allHealthy)
