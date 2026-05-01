param(
  [int]$LoopMinutes = 5,
  [double]$MinTurnoverUsd = 150000,
  [double]$DiscountThreshold = 0.60,
  [double]$KrMinTurnoverUsd = 150000,
  [double]$BnMinTurnoverUsd = 10000,
  [double]$KrDiscountThreshold = 0.60,
  [double]$BnDiscountThreshold = 0.45,
  [int]$LookbackDays = 180,
  [int]$MaxTargetsPerExchange = 35,
  [switch]$RunOnce
)

$ErrorActionPreference = 'Stop'
$root = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\code"
$python = Join-Path $root ".venv\Scripts\python.exe"
$scanScript = Join-Path $root "dual_exchange_moonshot_engine.py"
$reportScript = Join-Path $root "moonshot_horizon_tracker.py"
$selectorScript = Join-Path $root "moonshot_front_runner_selector.py"
$allocationRouterScript = Join-Path $root "moonshot_allocation_router.py"
$handoffBuilderScript = Join-Path $root "moonshot_execution_handoff_builder.py"

if (-not (Test-Path $python)) { throw "Missing python at $python" }
if (-not (Test-Path $scanScript)) { throw "Missing $scanScript" }
if (-not (Test-Path $reportScript)) { throw "Missing $reportScript" }
if (-not (Test-Path $selectorScript)) { throw "Missing $selectorScript" }
if (-not (Test-Path $allocationRouterScript)) { throw "Missing $allocationRouterScript" }
if (-not (Test-Path $handoffBuilderScript)) { throw "Missing $handoffBuilderScript" }

function Invoke-Scan {
  $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  Write-Host "[MOONSHOT] scan start $ts"
  & $python $scanScript `
    --min-turnover-usd $MinTurnoverUsd `
    --discount-threshold $DiscountThreshold `
    --kr-min-turnover-usd $KrMinTurnoverUsd `
    --bn-min-turnover-usd $BnMinTurnoverUsd `
    --kr-discount-threshold $KrDiscountThreshold `
    --bn-discount-threshold $BnDiscountThreshold `
    --lookback-days $LookbackDays `
    --max-targets-per-exchange $MaxTargetsPerExchange

  if ($LASTEXITCODE -ne 0) {
    Write-Warning "Scan exited with code $LASTEXITCODE"
  }

  & $python $reportScript
  if ($LASTEXITCODE -ne 0) {
    Write-Warning "Horizon tracker exited with code $LASTEXITCODE"
  }

  & $python $selectorScript
  if ($LASTEXITCODE -ne 0) {
    Write-Warning "Front runner selector exited with code $LASTEXITCODE"
  }

  & $python $allocationRouterScript
  if ($LASTEXITCODE -ne 0) {
    Write-Warning "Allocation router exited with code $LASTEXITCODE"
  }

  & $python $handoffBuilderScript
  if ($LASTEXITCODE -ne 0) {
    Write-Warning "Execution handoff builder exited with code $LASTEXITCODE"
  }

  $te = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  Write-Host "[MOONSHOT] scan end   $te"
}

Invoke-Scan
if ($RunOnce) { return }

while ($true) {
  Start-Sleep -Seconds ($LoopMinutes * 60)
  Invoke-Scan
}
