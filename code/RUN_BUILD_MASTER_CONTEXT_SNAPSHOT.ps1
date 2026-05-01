param(
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

$ROOT = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$CODE = Join-Path $ROOT "code"
$PY = Join-Path $CODE ".venv\Scripts\python.exe"

if (-not (Test-Path $PY)) {
    $PY = "python"
}

$Script = Join-Path $CODE "build_master_context_snapshot.py"
if (-not (Test-Path $Script)) {
    throw "Missing script: $Script"
}

if (-not $Quiet) {
    Write-Host "Building master context snapshot..." -ForegroundColor Cyan
    Write-Host "Python: $PY"
    Write-Host "Script: $Script"
}

& $PY $Script
if ($LASTEXITCODE -ne 0) {
    throw "Master context snapshot generation failed with exit code $LASTEXITCODE"
}

if (-not $Quiet) {
    Write-Host "Master context snapshot ready:" -ForegroundColor Green
    Write-Host " - out/execution/master_context_snapshot.json"
    Write-Host " - out/execution/master_context_snapshot.md"
    Write-Host " - out/execution/copilot_resume_prompt.txt"
}
