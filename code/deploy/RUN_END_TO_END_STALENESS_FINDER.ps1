param(
    [string]$ApiBase = "http://127.0.0.1:8787",
    [switch]$FailOnBlockers,
    [switch]$PrintJson
)

$ErrorActionPreference = "Stop"

$ROOT = (Resolve-Path (Join-Path $PSScriptRoot "..\.." )).Path
$SCRIPT = Join-Path $PSScriptRoot "end_to_end_staleness_finder.py"

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

$argsList = @($SCRIPT, "--api-base", $ApiBase)
if ($FailOnBlockers) { $argsList += "--fail-on-blockers" }
if ($PrintJson) { $argsList += "--print-json" }

Write-Host "[RUN] End-to-end staleness finder" -ForegroundColor Cyan
Write-Host "[RUN] Python: $PY"
Write-Host "[RUN] API Base: $ApiBase"

& $PY @argsList
$code = $LASTEXITCODE

if ($code -eq 0) {
    Write-Host "[OK] Report written to out/ops/staleness_report.json" -ForegroundColor Green
} elseif ($code -eq 2) {
    Write-Host "[WARN] Critical blockers detected. See out/ops/staleness_report.md" -ForegroundColor Yellow
} else {
    Write-Host "[FAIL] Staleness finder failed (exit $code)." -ForegroundColor Red
}

exit $code
