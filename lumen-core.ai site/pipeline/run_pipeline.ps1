$ErrorActionPreference = "Stop"

$siteRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $siteRoot

Write-Host "[LUMENCORE] Building site bundle..." -ForegroundColor Cyan
python ".\pipeline\build_site_bundle.py"

Write-Host "[LUMENCORE] Running smoke test..." -ForegroundColor Cyan
python ".\pipeline\smoke_test.py"

Write-Host "[LUMENCORE] Pipeline complete ✅" -ForegroundColor Green
Write-Host "Public output: $siteRoot\public"
