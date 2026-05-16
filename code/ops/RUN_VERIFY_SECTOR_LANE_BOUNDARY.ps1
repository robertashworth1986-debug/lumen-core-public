$ErrorActionPreference = 'Stop'

$repoRoot = 'C:/LumaTrader/INSTITUTIONAL_STACK_V2'
$python = 'c:/LumaTrader/venv3.11/Scripts/python.exe'
$script = "$repoRoot/code/ops/verify_sector_lane_boundary.py"

if (-not (Test-Path $python)) {
    throw "Python runtime not found: $python"
}
if (-not (Test-Path $script)) {
    throw "Boundary audit script not found: $script"
}

& $python $script
