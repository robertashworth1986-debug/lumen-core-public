$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $RepoRoot

$env:LUMA_STACK_ROOT = $RepoRoot
$env:LUMA_STAGE = "live-data-no-orders"

Write-Host "`n=== LumenCore Live-Data No-Orders Gate ===" -ForegroundColor Cyan
Write-Host "Read-only gate. No broker order calls. No secret values printed." -ForegroundColor Yellow

$Py = $null
try {
    $Py = (Get-Command py -ErrorAction Stop).Source
    py -3 .\code\execution\live_data_no_orders_gate.py --stage live-data-no-orders --root $RepoRoot
} catch {
    python .\code\execution\live_data_no_orders_gate.py --stage live-data-no-orders --root $RepoRoot
}

Write-Host "`nReport:" -ForegroundColor Green
Write-Host "$RepoRoot\out\safety_reports\LATEST_live_data_no_orders_gate.md" -ForegroundColor Green
