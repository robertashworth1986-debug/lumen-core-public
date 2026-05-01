param(
  [switch]$IncludeICloud,
  [switch]$NoOrders,
  [switch]$Foreground
)

$ErrorActionPreference = "Stop"
$code = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\code"
$root = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$candidates = @(
  (Join-Path $root ".venv\Scripts\python.exe"),
  (Join-Path $code ".venv\Scripts\python.exe")
)
$py = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $py) {
  throw "Python runtime not found in .venv candidates: $($candidates -join ', ')"
}

$supervisorScript = Join-Path $code "luma_supervisor.py"

$pyArgs = @($supervisorScript)
if ($IncludeICloud) { $pyArgs += "--include-icloud" }
if ($NoOrders)      { $pyArgs += "--no-orders" }

Write-Host "[START] Luma Supervisor — launching all services via unified supervisor"
Write-Host "[START] Supervisor: $supervisorScript"
Write-Host "[START] Args: $($pyArgs -join ' ')"

if ($Foreground) {
  # Run in this window (useful for debugging)
  & $py @pyArgs
} else {
  # Run detached in a minimized window
  Start-Process -FilePath $py `
    -ArgumentList $pyArgs `
    -WorkingDirectory $code `
    -WindowStyle Minimized
  Write-Host "[START] Supervisor started in background. Health: $code\out\execution\supervisor_health.json"
  Write-Host "[START] REST health check: http://localhost:8787/health"
}
