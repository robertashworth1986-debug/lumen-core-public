[CmdletBinding()]
param(
    [int]$IntervalSec = 300,
    [double]$MinFitScore = 0.42,
    [int]$Limit = 20,
    [switch]$DryRun
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

$scriptPath = Join-Path $codeDir "email_resume_dispatcher.py"
if (-not (Test-Path $scriptPath)) {
    throw "Missing script: $scriptPath"
}

$args = @("--interval-sec", "$IntervalSec", "--min-fit-score", "$MinFitScore", "--limit", "$Limit")
if ($DryRun) {
    $args += "--dry-run"
}

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host " EMAIL RESUME DISPATCHER" -ForegroundColor Cyan
Write-Host " Script: $scriptPath" -ForegroundColor Cyan
Write-Host " Python: $pythonExe" -ForegroundColor Cyan
Write-Host " IntervalSec=$IntervalSec MinFitScore=$MinFitScore Limit=$Limit DryRun=$DryRun" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

& $pythonExe $scriptPath @args
exit $LASTEXITCODE
