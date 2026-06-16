$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $RepoRoot

$env:LUMA_STACK_ROOT = $RepoRoot
$env:LUMA_STAGE = "live-data-no-orders"

Write-Host "`n=== LumenCore Safe Live Executor Smoke ===" -ForegroundColor Cyan
Write-Host "Expected: blocked=true, executor_called=false, reason=blocked_by_live_data_no_orders_stage" -ForegroundColor Yellow

try {
    py -3 .\code\execution\safe_live_executor.py
} catch {
    python .\code\execution\safe_live_executor.py
}

Write-Host "`nReport:" -ForegroundColor Green
Write-Host "$RepoRoot\out\safety_reports\LATEST_safe_live_executor_smoke.md" -ForegroundColor Green
