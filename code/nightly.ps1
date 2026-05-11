# LumenCore — nightly innovation pipeline
# =============================================================================
# What this does, every night:
#   1. Refresh all live data + run the full 673-dataset benchmark
#   2. Train the meta-router on the new run
#   3. Score the hybrid stacker (SARIMA+harmonic, linear+harmonic, router-oracle)
#   4. Render the evidence charts + publish the static bundle
#   5. (Optional) Auto-post to LinkedIn if a token exists
#
# Idempotent: every run is hash-chained into out/frozen_delta_ledger.jsonl.
# Errors abort the chain so a partial day never overwrites good evidence.
#
# Schedule via Task Scheduler:
#   schtasks /Create /SC DAILY /ST 03:30 /TN "LumenCore Nightly" ^
#     /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\nightly.ps1" ^
#     /RL HIGHEST /F

$ErrorActionPreference = "Stop"
Set-Location -Path (Split-Path -Parent $PSScriptRoot)

$ROOT = (Get-Location).Path
$PY   = Join-Path $ROOT ".venv\Scripts\python.exe"
$LOG  = Join-Path $ROOT ("out\nightly_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Force -Path (Split-Path $LOG -Parent) | Out-Null

function Step([string]$name, [scriptblock]$block) {
    $t0 = Get-Date
    "[nightly] === $name ===" | Tee-Object -FilePath $LOG -Append | Out-Host
    try {
        & $block 2>&1 | Tee-Object -FilePath $LOG -Append | Out-Host
        $dt = (Get-Date) - $t0
        "[nightly] $name OK ({0:N1}s)" -f $dt.TotalSeconds | Tee-Object -FilePath $LOG -Append | Out-Host
    } catch {
        "[nightly] $name FAILED: $_" | Tee-Object -FilePath $LOG -Append | Out-Host
        throw
    }
}

Step "1/5 master_universe_benchmark_v2 (full)" {
    $env:MASTER_SCALE = "full"
    & $PY -u code\master_universe_benchmark_v2.py
}

Step "2/5 meta_router (innovation #1)" {
    & $PY code\meta_router.py
}

Step "3/5 hybrid_stacker (innovation #2)" {
    & $PY code\hybrid_stacker.py
}

Step "4/5 charts + publish bundle" {
    & $PY code\render_evidence_charts.py
    & $PY code\publish_evidence_bundle.py
}

Step "4b/5 calibration + blender + anomaly + regime (evidence layers 3-7)" {
    & $PY code\ci_calibration.py
    & $PY code\stacking_blender.py
    & $PY code\anomaly_scanner.py
    & $PY code\regime_shift_scanner.py
}

Step "4c/5 grant factory rerank (innovation #17)" {
    & $PY code\grant_application_factory.py
}

Step "4d/5 mirror dashboard pages to served root" {
    $src = Join-Path $ROOT "dashboard"
    $dst = "C:\LumaTrader\dashboard"
    if ((Test-Path $src) -and (Test-Path $dst)) {
        Get-ChildItem $src -Filter *.html | ForEach-Object {
            Copy-Item $_.FullName $dst -Force
        }
    }
}

Step "5/5 LinkedIn auto-post (skipped if no token)" {
    & $PY code\linkedin_publish_evidence.py
}

"[nightly] all steps complete -> $LOG" | Out-Host
