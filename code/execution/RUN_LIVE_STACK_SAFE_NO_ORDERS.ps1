$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $RepoRoot

$env:LUMA_STACK_ROOT = $RepoRoot
$env:LUMA_STAGE = "live-data-no-orders"

Write-Host "`n=== LumenCore Safe Live Stack: Live Data / No Orders ===" -ForegroundColor Cyan
Write-Host "This launcher is the safe replacement entrypoint before touching raw live_executor paths." -ForegroundColor Yellow
Write-Host "It may inspect live-executor surface, but it must not call a broker order function in this stage." -ForegroundColor Yellow

Write-Host "`n[1/3] Live-data no-orders gate..." -ForegroundColor Cyan
try {
    py -3 .\code\execution\live_data_no_orders_gate.py --stage live-data-no-orders --root $RepoRoot
} catch {
    python .\code\execution\live_data_no_orders_gate.py --stage live-data-no-orders --root $RepoRoot
}

Write-Host "`n[2/3] Safe live executor smoke..." -ForegroundColor Cyan
try {
    py -3 .\code\execution\safe_live_executor.py
} catch {
    python .\code\execution\safe_live_executor.py
}

Write-Host "`n[3/3] Raw live entrypoint audit..." -ForegroundColor Cyan
try {
    py -3 .\code\execution\audit_live_entrypoints.py
} catch {
    python .\code\execution\audit_live_entrypoints.py
}

Write-Host "`nSafe no-orders stack complete." -ForegroundColor Green
Write-Host "Reports:" -ForegroundColor Cyan
Write-Host "$RepoRoot\out\safety_reports\LATEST_live_data_no_orders_gate.md" -ForegroundColor Green
Write-Host "$RepoRoot\out\safety_reports\LATEST_safe_live_executor_smoke.md" -ForegroundColor Green
Write-Host "$RepoRoot\out\safety_reports\LATEST_live_entrypoint_audit.md" -ForegroundColor Green
