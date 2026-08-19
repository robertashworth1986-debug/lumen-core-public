$ErrorActionPreference = 'Stop'

$ROOT = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$CODE = Join-Path $ROOT "code"
$LOOP_SCRIPT = Join-Path $CODE "RUN_ALPACA_PAPER_247.ps1"

Write-Warning "Legacy filename retained for compatibility; this launcher is paper-only."
$env:PAPER_MODE = "true"
$env:LIVE_MODE = "false"
$env:FORCE_LIVE = "false"

Write-Host "=== STARTING PAPER-ONLY TRADER LOOP ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File $LOOP_SCRIPT
if ($LASTEXITCODE -ne 0) {
    throw "Paper-only trader loop exited with code $LASTEXITCODE."
}
