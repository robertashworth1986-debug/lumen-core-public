param(
  [switch]$Daemon,
  [int]$IntervalSec = 300,
  [string[]]$IncludeRoot,
  [switch]$IncludeOnlyRoots
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

$script = Join-Path $PSScriptRoot "ecosystem_fabric_engine.py"
$commandLine = '"' + $script + '"'

if ($Daemon) {
  $commandLine += " --daemon --interval-sec $IntervalSec"
}

if ($IncludeOnlyRoots) {
  $commandLine += " --include-only-roots"
}

foreach ($r in $IncludeRoot) {
  if ($r -and $r.Trim().Length -gt 0) {
    $escaped = $r.Replace('"', '""')
    $commandLine += ' --include-root "' + $escaped + '"'
  }
}

Write-Host "[RUN] Ecosystem Fabric Engine"
Write-Host "[RUN] Python: $py"
Write-Host "[RUN] Args: $commandLine"

$expr = '& "' + $py + '" ' + $commandLine
Invoke-Expression $expr
