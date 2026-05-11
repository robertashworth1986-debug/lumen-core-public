param(
    [int]$MaxFiles = 50000,
    [switch]$FailOnCritical,
    [switch]$PrintJson
)

$ErrorActionPreference = "Stop"

$ROOT = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$SCRIPT = Join-Path $PSScriptRoot "lumaq_brain_builder.py"

if (-not (Test-Path $SCRIPT)) {
    Write-Host "[FATAL] Missing script: $SCRIPT" -ForegroundColor Red
    exit 1
}

$pythonCandidates = @(
    (Join-Path $ROOT "venv3.11\Scripts\python.exe"),
    (Join-Path $ROOT "..\venv3.11\Scripts\python.exe"),
    (Join-Path $ROOT "venv\Scripts\python.exe"),
    (Join-Path $ROOT "..\venv\Scripts\python.exe"),
    "python"
)

$PY = $null
foreach ($cand in $pythonCandidates) {
    try {
        if ($cand -eq "python") {
            $cmd = Get-Command python -ErrorAction Stop
            if ($cmd) { $PY = "python"; break }
        } elseif (Test-Path $cand) {
            $PY = $cand
            break
        }
    } catch {
    }
}

if (-not $PY) {
    Write-Host "[FATAL] No Python runtime found (checked venv3.11, venv, and PATH)." -ForegroundColor Red
    exit 1
}

$argsList = @($SCRIPT, "--max-files", [string]$MaxFiles)
if ($FailOnCritical) { $argsList += "--fail-on-critical" }
if ($PrintJson) { $argsList += "--print-json" }

Write-Host "[RUN] LumaQ micro/meso/macro brain builder" -ForegroundColor Cyan
Write-Host "[RUN] Python: $PY"
Write-Host "[RUN] Max files: $MaxFiles"

& $PY @argsList
$code = $LASTEXITCODE

if ($code -eq 0) {
    Write-Host "[OK] Wrote out/ops/lumaq_brain_report.json and markdown talk track artifacts." -ForegroundColor Green
} elseif ($code -eq 2) {
    Write-Host "[WARN] Critical micro blockers detected. Review out/ops/lumaq_brain_report.md." -ForegroundColor Yellow
} else {
    Write-Host "[FAIL] LumaQ brain builder failed (exit $code)." -ForegroundColor Red
}

exit $code