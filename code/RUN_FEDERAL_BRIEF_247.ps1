$ErrorActionPreference = "Continue"

$ROOT = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$CODE = Join-Path $ROOT "code\execution"
$OUT  = Join-Path $ROOT "out"
$PY   = Join-Path $ROOT ".venv\Scripts\python.exe"

if (-not (Test-Path $PY)) {
    $PY = "python"
}

$crossScript = Join-Path $CODE "run_cross_sector_intel.py"
$briefScript = Join-Path $CODE "run_federal_brief.py"
$runLedger   = Join-Path $OUT "federal_brief_run_ledger.jsonl"
$heartbeat   = Join-Path $OUT "federal_brief_daemon_heartbeat.json"

$defaultIntervalSec = 300

Write-Host ""
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host " LUMENCORE FEDERAL BRIEF 24/7 DAEMON" -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host " python: $PY"
Write-Host " cross : $crossScript"
Write-Host " brief : $briefScript"
Write-Host ""

if (-not (Test-Path $crossScript)) {
    Write-Host "[FATAL] Missing script: $crossScript" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $briefScript)) {
    Write-Host "[FATAL] Missing script: $briefScript" -ForegroundColor Red
    exit 1
}

$cycle = 0
while ($true) {
    $cycle += 1
    $started = [DateTime]::UtcNow

    $crossOut = & $PY $crossScript 2>&1 | Out-String
    $crossExit = $LASTEXITCODE

    $briefOut = & $PY $briefScript 2>&1 | Out-String
    $briefExit = $LASTEXITCODE

    $ended = [DateTime]::UtcNow
    $ok = ($crossExit -eq 0 -and $briefExit -eq 0)

    $entry = [ordered]@{
        generated_utc = $ended.ToString("o")
        event         = "federal_brief_cycle"
        cycle         = $cycle
        ok            = $ok
        cross_exit    = $crossExit
        brief_exit    = $briefExit
        elapsed_sec   = [math]::Round(($ended - $started).TotalSeconds, 3)
        cross_tail    = [string]($crossOut -split "`r?`n" | Select-Object -Last 12 | Out-String)
        brief_tail    = [string]($briefOut -split "`r?`n" | Select-Object -Last 12 | Out-String)
    }

    ($entry | ConvertTo-Json -Depth 8 -Compress) | Add-Content -Path $runLedger -Encoding UTF8

    $hb = [ordered]@{
        generated_utc = $ended.ToString("o")
        cycle         = $cycle
        ok            = $ok
        cross_exit    = $crossExit
        brief_exit    = $briefExit
        elapsed_sec   = [math]::Round(($ended - $started).TotalSeconds, 3)
        run_ledger    = $runLedger
    }
    ($hb | ConvertTo-Json -Depth 8) | Set-Content -Path $heartbeat -Encoding UTF8

    Write-Host ("[{0}] cycle={1} ok={2} cross_exit={3} brief_exit={4} elapsed={5}s" -f [DateTime]::Now.ToString("HH:mm:ss"), $cycle, $ok, $crossExit, $briefExit, $hb.elapsed_sec) -ForegroundColor $(if ($ok) { "Green" } else { "Red" })

    $sleepSec = $defaultIntervalSec
    try {
        $runtimePath = Join-Path $ROOT "config\cross_sector_intel_runtime.json"
        if (Test-Path $runtimePath) {
            $runtime = Get-Content $runtimePath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($runtime -and $runtime.federal_brief_interval_sec) {
                $sleepSec = [int]$runtime.federal_brief_interval_sec
            }
        }
    } catch {}

    if ($sleepSec -lt 15) { $sleepSec = 15 }
    Start-Sleep -Seconds $sleepSec
}
