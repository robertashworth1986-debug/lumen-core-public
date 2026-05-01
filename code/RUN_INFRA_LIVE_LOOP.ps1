$ErrorActionPreference = "Continue"
$ROOT  = "C:\LumaTrader"
$STACK = Join-Path $ROOT "INSTITUTIONAL_STACK_V2"
$CODE  = Join-Path $STACK "code"
$CFG   = Join-Path $STACK "config"
$DASH  = Join-Path $ROOT "dashboard"

while ($true) {
    Write-Host ""
    Write-Host "=== INFRA LIVE SWEEP === $(Get-Date -Format s)" -ForegroundColor Cyan
    python (Join-Path $CODE "infra_live_loop_builder.py")
    $cfgFile = Join-Path $CFG "infra_live_runtime.json"
    $sleepSec = 300
    if (Test-Path $cfgFile) {
        try {
            $cfg = Get-Content $cfgFile -Raw | ConvertFrom-Json
            if ($cfg.loop_seconds) { $sleepSec = [int]$cfg.loop_seconds }
        } catch {}
    }
    Write-Host "Sleeping $sleepSec seconds..." -ForegroundColor Yellow
    Start-Sleep -Seconds $sleepSec
}
