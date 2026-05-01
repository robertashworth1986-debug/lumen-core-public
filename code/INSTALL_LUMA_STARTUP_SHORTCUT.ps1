$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$cmd = Join-Path $PSScriptRoot "START_LUMA_ECOSYSTEM_STACK.cmd"
if (-not (Test-Path $cmd)) {
  throw "Missing launcher: $cmd"
}

$startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
if (-not (Test-Path $startupDir)) {
  New-Item -ItemType Directory -Path $startupDir -Force | Out-Null
}

$target = Join-Path $startupDir "LumaEcosystemAutoStart.cmd"
Copy-Item -Path $cmd -Destination $target -Force

Write-Host "[STARTUP] Installed startup launcher: $target"
Write-Host "[STARTUP] This will auto-start gateway + ecosystem daemon at user login."
