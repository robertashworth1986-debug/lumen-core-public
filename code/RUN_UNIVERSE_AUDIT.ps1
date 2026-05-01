$ErrorActionPreference = "Stop"

$ROOT = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$CODE = Join-Path $ROOT "code"
$PY = Join-Path $CODE ".venv\Scripts\python.exe"
if (-not (Test-Path $PY)) {
    $PY = "python"
}

$SCRIPT = Join-Path $CODE "execution\universe_audit_runner.py"
if (-not (Test-Path $SCRIPT)) {
    throw "Missing script: $SCRIPT"
}

Write-Host "Running full universe audit..." -ForegroundColor Cyan
& $PY $SCRIPT
if ($LASTEXITCODE -ne 0) {
    throw "Universe audit failed with exit code $LASTEXITCODE"
}

Write-Host "Audit artifacts:" -ForegroundColor Green
Write-Host " - C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\universe_audit_report.json"
Write-Host " - C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\universe_audit_report.md"
