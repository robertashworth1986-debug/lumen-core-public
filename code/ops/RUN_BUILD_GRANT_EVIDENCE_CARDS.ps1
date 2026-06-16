$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $RepoRoot

Write-Host "`n=== Build Grant Evidence Cards ===" -ForegroundColor Cyan

try {
    py -3 .\code\ops\build_grant_evidence_cards.py
} catch {
    python .\code\ops\build_grant_evidence_cards.py
}

Write-Host "`nCards:" -ForegroundColor Green
Write-Host "$RepoRoot\docs\grant_evidence_cards" -ForegroundColor Green
Write-Host "`nTrackCast triage:" -ForegroundColor Yellow
Write-Host "$RepoRoot\out\grant_evidence\TRACKCAST_FAILURE_TRIAGE.md" -ForegroundColor Yellow
