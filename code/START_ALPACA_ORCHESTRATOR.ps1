param(
  [int]$IntervalSec = 60,
  [int]$MaxSymbols = 5000,
  [int]$TopN = 300,
  [switch]$NoOrders,
  [switch]$Detach = $true,
  [switch]$NoRestart
)

$ErrorActionPreference = "Stop"
$runner = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\RUN_ALPACA_PAPER_ORCHESTRATOR.ps1"
if (-not (Test-Path $runner)) {
  throw "Runner not found: $runner"
}

if (-not $NoRestart) {
  $running = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "python.exe" -and $_.CommandLine -like "*alpaca_paper_orchestrator.py*"
  }
  foreach ($p in $running) {
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
  }
  if ($running.Count -gt 0) {
    Write-Host "[START] Restart cleanup: stopped $($running.Count) old orchestrator process(es)."
  }
}

$argParts = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", ('"' + $runner + '"'),
  "-Loop",
  "-IntervalSec", [string]$IntervalSec,
  "-MaxSymbols", [string]$MaxSymbols,
  "-TopN", [string]$TopN,
  "-StatusOnlyWhenClosed"
)
if ($NoOrders) { $argParts += "-NoOrders" }

if ($Detach) {
  Start-Process -FilePath "pwsh" -ArgumentList $argParts -WindowStyle Minimized
  Write-Host "[START] Alpaca orchestrator started detached."
} else {
  & pwsh @argParts
}
