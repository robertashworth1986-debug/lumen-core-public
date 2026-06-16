$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $RepoRoot

$env:LUMA_STACK_ROOT = $RepoRoot
$env:LUMA_STAGE = "live-data-no-orders"

Write-Host "`n=== Tiny-Live Manual Arm Readiness: DESIGN ONLY ===" -ForegroundColor Cyan
Write-Host "This does not activate live trading." -ForegroundColor Yellow

try {
    py -3 .\code\execution\tiny_live_manual_arm_readiness.py
} catch {
    python .\code\execution\tiny_live_manual_arm_readiness.py
}

Write-Host "`nReport:" -ForegroundColor Green
Write-Host "$RepoRoot\out\safety_reports\LATEST_tiny_live_manual_arm_readiness.md" -ForegroundColor Green
