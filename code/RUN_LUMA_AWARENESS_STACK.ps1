$ErrorActionPreference = 'Stop'

$root = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$code = Join-Path $root "code"
$execCode = Join-Path $code "execution"

$gatewayPyCandidates = @(
  (Join-Path $code ".venv\Scripts\python.exe"),
  (Join-Path $root "env311\Scripts\python.exe"),
  "C:\LumaTrader\.venv\Scripts\python.exe"
)

$daemonPyCandidates = @(
  (Join-Path $root "env311\Scripts\python.exe"),
  (Join-Path $code ".venv\Scripts\python.exe"),
  "C:\LumaTrader\.venv\Scripts\python.exe"
)

$gatewayPython = $gatewayPyCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$daemonPython = $daemonPyCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $gatewayPython) {
  throw "No gateway Python runtime found in expected locations."
}
if (-not $daemonPython) {
  throw "No daemon Python runtime found in expected locations."
}

Write-Host "[AWARENESS] Gateway Python: $gatewayPython"
Write-Host "[AWARENESS] Daemon Python:  $daemonPython"

# 1) Ensure Node-RED bidirectional Luma flow exists
$importScript = Join-Path $code "IMPORT_NODERED_LUMA_FLOWS.ps1"
if (Test-Path $importScript) {
  try {
    & powershell -ExecutionPolicy Bypass -File $importScript
    Write-Host "[AWARENESS] Node-RED flow verified."
  }
  catch {
    Write-Warning "Node-RED flow verification failed (continuing): $($_.Exception.Message)"
  }
}

# 2) Start Luma Experience Gateway (ws/live) if not running
$gatewayArgs = "`"$code\luma_experience_gateway.py`""
Start-Process -FilePath $gatewayPython -ArgumentList $gatewayArgs -WorkingDirectory $code -WindowStyle Minimized
Write-Host "[AWARENESS] Launched luma_experience_gateway.py"

# 3) Start symbol-awareness daemon
$daemonArgs = "`"$execCode\luma_symbol_awareness_daemon.py`" --loop-seconds 1.0"
Start-Process -FilePath $daemonPython -ArgumentList $daemonArgs -WorkingDirectory $execCode -WindowStyle Minimized
Write-Host "[AWARENESS] Launched luma_symbol_awareness_daemon.py"

Write-Host "[AWARENESS] Stack launch submitted."
Write-Host "[AWARENESS] Snapshot endpoint: http://127.0.0.1:8787/api/snapshot"
Write-Host "[AWARENESS] WS endpoint: http://127.0.0.1:8787/ws/live"
