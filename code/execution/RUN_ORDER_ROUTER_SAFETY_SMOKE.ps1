$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $RepoRoot

$env:LUMA_STACK_ROOT = $RepoRoot
$env:LUMA_STAGE = "live-data-no-orders"

Write-Host "`n=== LumenCore Order Router Safety Smoke ===" -ForegroundColor Cyan
Write-Host "Expected: routed=false, blocked=true, reason=blocked_by_live_data_no_orders_stage" -ForegroundColor Yellow

try {
    py -3 .\code\execution\order_router.py
} catch {
    python .\code\execution\order_router.py
}
