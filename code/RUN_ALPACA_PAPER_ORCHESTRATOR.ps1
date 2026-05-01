param(
  [switch]$Loop,
  [int]$IntervalSec = 60,
  [int]$MaxSymbols = 400,
  [int]$TopN = 120,
  [switch]$NoOrders,
  [switch]$StatusOnlyWhenClosed = $true
)

$ErrorActionPreference = "Stop"
$root = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$py = Join-Path $root "code\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  $py = Join-Path $root ".venv\Scripts\python.exe"
}
if (-not (Test-Path $py)) {
  throw "Python executable not found."
}

$script = Join-Path $root "code\execution\alpaca_paper_orchestrator.py"
$cli = @($script, "--max-symbols", [string]$MaxSymbols, "--top-n", [string]$TopN)
if ($Loop) { $cli += @("--loop", "--interval-sec", [string]$IntervalSec) }
if ($NoOrders) { $cli += "--no-orders" }
if ($StatusOnlyWhenClosed) { $cli += "--status-only-when-closed" }

Write-Host "[RUN] Alpaca Paper Orchestrator"
Write-Host "[RUN] Python: $py"
Write-Host "[RUN] Script: $script"
Write-Host "[RUN] Args: $($cli -join ' ')"

& $py @cli
