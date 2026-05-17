[CmdletBinding()]
param(
    [int]$IntervalSec = 180,
    [double]$MinScore = 0.90,
    [int]$MaxPerCycle = 80
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$stackRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$codeDir = Join-Path $stackRoot "code"

$pythonCandidates = @(
    (Join-Path $stackRoot ".venv\Scripts\python.exe"),
    (Join-Path $stackRoot "..\venv3.11\Scripts\python.exe"),
    (Join-Path $stackRoot "venv3.11\Scripts\python.exe")
)

$pythonExe = $null
foreach ($candidate in $pythonCandidates) {
    if (Test-Path $candidate) {
        $pythonExe = (Resolve-Path $candidate).Path
        break
    }
}
if (-not $pythonExe) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) {
        $pythonExe = $cmd.Source
    }
}
if (-not $pythonExe) {
    throw "Python executable not found."
}

$scriptPath = Join-Path $codeDir "email_opportunity_finder.py"
if (-not (Test-Path $scriptPath)) {
    throw "Missing script: $scriptPath"
}

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host " EMAIL OPPORTUNITY WATCHER" -ForegroundColor Cyan
Write-Host " Script: $scriptPath" -ForegroundColor Cyan
Write-Host " Python: $pythonExe" -ForegroundColor Cyan
Write-Host " IntervalSec=$IntervalSec MinScore=$MinScore MaxPerCycle=$MaxPerCycle" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

& $pythonExe $scriptPath --interval-sec "$IntervalSec" --min-score "$MinScore" --max-per-cycle "$MaxPerCycle"
exit $LASTEXITCODE
