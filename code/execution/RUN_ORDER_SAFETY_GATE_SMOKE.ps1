$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $RepoRoot

$env:LUMA_STACK_ROOT = $RepoRoot
$env:LUMA_STAGE = "live-data-no-orders"

Write-Host "`n=== LumenCore Order Safety Gate Smoke ===" -ForegroundColor Cyan
Write-Host "Expected result: approved=false, reason=blocked_by_live_data_no_orders_stage" -ForegroundColor Yellow

try {
    py -3 .\code\execution\order_safety_gate.py
} catch {
    python .\code\execution\order_safety_gate.py
}

Write-Host "`nLedger:" -ForegroundColor Green
Write-Host "$RepoRoot\out\safety_reports\order_safety_gate_ledger.jsonl" -ForegroundColor Green
