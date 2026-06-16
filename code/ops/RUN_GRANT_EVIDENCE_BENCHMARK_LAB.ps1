$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $RepoRoot

$env:LUMA_STACK_ROOT = $RepoRoot
$env:LUMA_STAGE = "live-data-no-orders"

Write-Host ""
Write-Host "=== LumenCore Grant Evidence Benchmark Lab ===" -ForegroundColor Cyan
Write-Host "Grant science mode. No live trading. No secret values printed." -ForegroundColor Yellow

try {
    py -3 .\code\ops\grant_evidence_benchmark_lab.py
} catch {
    python .\code\ops\grant_evidence_benchmark_lab.py
}

Write-Host ""
Write-Host "Report:" -ForegroundColor Green
Write-Host "$RepoRoot\out\grant_evidence\LATEST_grant_evidence_benchmark_lab.md" -ForegroundColor Green
