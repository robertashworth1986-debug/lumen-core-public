[CmdletBinding()]
param(
    [int]$IntervalSec = 300,
    [double]$MinFitScore = 0.42,
    [int]$Limit = 20,
    [switch]$Once,
    [switch]$DryRun,
    [switch]$ApprovedSend
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
if ($Once) {
    $args += "--once"
}
if ($DryRun) {
    $args += "--dry-run"
}
if ($ApprovedSend) {
    if (-not $Once) {
        throw "-ApprovedSend requires -Once so approval cannot persist across polling cycles."
    }
    $args += "--send-approved"
}

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host " EMAIL RESUME DISPATCHER" -ForegroundColor Cyan
Write-Host " Script: $scriptPath" -ForegroundColor Cyan
Write-Host " Python: $pythonExe" -ForegroundColor Cyan
Write-Host " IntervalSec=$IntervalSec MinFitScore=$MinFitScore Limit=$Limit Once=$Once DryRun=$DryRun ApprovedSend=$ApprovedSend" -ForegroundColor Cyan
if (-not $DryRun -and -not $ApprovedSend) {
    Write-Warning "Outbound delivery is fail-closed. Add -ApprovedSend only after reviewing the current queue."
}
Write-Host "=====================================================" -ForegroundColor Cyan

& $pythonExe $scriptPath @args
exit $LASTEXITCODE
