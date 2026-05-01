param(
  [int]$EcosystemIntervalSec = 300,
  [switch]$IncludeICloud,
  [switch]$IncludeSystemCrawl,
  [switch]$NoRestart
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  $py = Join-Path $root "code\.venv\Scripts\python.exe"
}
if (-not (Test-Path $py)) {
  throw "Python executable not found in code\.venv or .venv"
}

$gatewayModule = "luma_experience_gateway:app"
$ecosystemScript = Join-Path $PSScriptRoot "ecosystem_fabric_engine.py"

$roots = @("C:\LumaTrader\INSTITUTIONAL_STACK_V2")
if ($IncludeICloud) {
  $roots += "C:\Users\Novac\iCloudDrive"
}
if ($IncludeSystemCrawl) {
  $roots += "C:\"
}

# Build ecosystem daemon arguments.
$ecoArgs = '"' + $ecosystemScript + '" --daemon --interval-sec ' + $EcosystemIntervalSec + ' --include-only-roots'
foreach ($r in $roots) {
  $escaped = $r.Replace('"', '""')
  $ecoArgs += ' --include-root "' + $escaped + '"'
}

$gatewayCmd = '"' + $py + '" -m uvicorn ' + $gatewayModule + ' --app-dir "' + $PSScriptRoot + '" --host 0.0.0.0 --port 8787'
$ecoCmd = '"' + $py + '" ' + $ecoArgs
$gatewayWrapped = 'Set-Location "' + $root + '"; ' + $gatewayCmd
$ecoWrapped = 'Set-Location "' + $root + '"; ' + $ecoCmd

if (-not $NoRestart) {
  $running = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "python.exe" -and (
      $_.CommandLine -like "*uvicorn luma_experience_gateway:app*" -or
      $_.CommandLine -like "*ecosystem_fabric_engine.py*"
    )
  }
  foreach ($p in $running) {
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
  }
  if ($running.Count -gt 0) {
    Write-Host "[START] Restart cleanup: stopped $($running.Count) old gateway/ecosystem process(es)."
  }
}

Write-Host "[START] Luma Ecosystem Stack"
Write-Host "[START] Gateway command: $gatewayCmd"
Write-Host "[START] Ecosystem command: $ecoCmd"

Start-Process -FilePath "pwsh" -WorkingDirectory $root -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $gatewayWrapped) -WindowStyle Minimized
Start-Process -FilePath "pwsh" -WorkingDirectory $root -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $ecoWrapped) -WindowStyle Minimized

Write-Host "[START] Started gateway + ecosystem daemon in background PowerShell windows."
