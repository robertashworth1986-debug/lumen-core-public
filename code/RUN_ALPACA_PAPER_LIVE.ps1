$ErrorActionPreference = 'Stop'

$ROOT = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$CODE = Join-Path $ROOT "code"
$PY = Join-Path $ROOT ".venv\Scripts\python.exe"
$ARM_SCRIPT = Join-Path $CODE "go_live_paper_trader.py"
$LOOP_SCRIPT = Join-Path $CODE "RUN_ALPACA_PAPER_247.ps1"

Write-Host "=== ARMING PAPER TRADER LIVE ===" -ForegroundColor Cyan
& $PY $ARM_SCRIPT

Write-Host "=== STARTING PAPER TRADER LOOP ===" -ForegroundColor Cyan
Start-Process powershell -ArgumentList @('-NoExit', '-File', $LOOP_SCRIPT)
Write-Host "Started paper trader loop in a new PowerShell window."
Write-Host "Check the dashboard or out/paper_go_live_proof.json for live status." -ForegroundColor Green
