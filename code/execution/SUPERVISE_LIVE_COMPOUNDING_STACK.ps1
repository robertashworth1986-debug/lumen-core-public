$ErrorActionPreference = "Stop"

# LumenCore safety redirect
# Legacy launcher: code\execution\SUPERVISE_LIVE_COMPOUNDING_STACK.ps1
# Backup file: code\execution\SUPERVISE_LIVE_COMPOUNDING_STACK.ps1.bak_pre_safe_redirect
# Safe launcher: code\execution\RUN_LIVE_STACK_SAFE_NO_ORDERS.ps1

# This file is intentionally redirected through the safe live-data/no-orders path.
# It must not call raw broker order execution directly.

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $RepoRoot

$env:LUMA_STACK_ROOT = $RepoRoot
$env:LUMA_STAGE = "live-data-no-orders"

Write-Host "
=== SUPERVISE_LIVE_COMPOUNDING_STACK.ps1 redirected to safe no-orders launcher ===" -ForegroundColor Cyan
Write-Host "No broker orders will be submitted from this redirected launcher." -ForegroundColor Yellow
Write-Host "Original backup: code\execution\SUPERVISE_LIVE_COMPOUNDING_STACK.ps1.bak_pre_safe_redirect" -ForegroundColor Yellow

powershell -ExecutionPolicy Bypass -File ".\code\execution\RUN_LIVE_STACK_SAFE_NO_ORDERS.ps1"
