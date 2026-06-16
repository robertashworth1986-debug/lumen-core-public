$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $RepoRoot

Write-Host ""
Write-Host "=== Build Grant Submission Pack ===" -ForegroundColor Cyan

try {
    py -3 .\code\ops\build_grant_submission_pack.py
} catch {
    python .\code\ops\build_grant_submission_pack.py
}

Write-Host ""
Write-Host "Grant submission pack:" -ForegroundColor Green
Write-Host "$RepoRoot\docs\grant_submission_pack\INDEX.md" -ForegroundColor Green
