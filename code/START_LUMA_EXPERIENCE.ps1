$ErrorActionPreference = 'Stop'

$root = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\code"
$repo = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$candidates = @(
  (Join-Path $repo ".venv\Scripts\python.exe"),
  (Join-Path $root ".venv\Scripts\python.exe")
)
$python = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not (Test-Path $python)) {
  throw "Python runtime not found at $python"
}

Write-Host "[LUMA] Building immersive web app..."
& $python (Join-Path $root "BUILD_LUMA_EXPERIENCE_WEBAPP.py")

Write-Host "[LUMA] Starting gateway on http://127.0.0.1:8787 ..."
& $python (Join-Path $root "luma_experience_gateway.py")
