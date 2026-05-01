$ErrorActionPreference = 'Stop'

$root = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\code"
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
  throw "Python runtime not found at $python"
}

Write-Host "[IMMERSIVE] Building immersive artifacts..."
& $python (Join-Path $root "BUILD_LUMA_EXPERIENCE_WEBAPP.py")
& $python -c "import BUILD_DASHBOARD_PORTAL; BUILD_DASHBOARD_PORTAL.main()"
& $python -c "import dashboard_unified_refresh as r; r.publish_master_dashboard_to_iis()"

Write-Host "[IMMERSIVE] Handing off to AUTO_START_LUMA_KEYNOTE.ps1..."
& (Join-Path $root "AUTO_START_LUMA_KEYNOTE.ps1")
