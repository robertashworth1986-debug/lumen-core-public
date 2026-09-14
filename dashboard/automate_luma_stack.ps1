# Collect bounded local inventory and log observations.
# This does not run proofs, alerts, recovery, trades, or compliance certification.
[CmdletBinding()]
param([string]$Python)

$ErrorActionPreference = 'Stop'
$dashboardPath = $PSScriptRoot
$stackRoot = Split-Path -Parent $dashboardPath
if ([string]::IsNullOrWhiteSpace($Python)) {
    $Python = Join-Path $stackRoot '.venv/Scripts/python.exe'
}
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'Python interpreter not found. Supply -Python with the intended local interpreter.'
}

$checks = @(
    @{ Name = 'API-key presence inventory'; Script = 'update_api_key_status.py'; ObservationExit = 0 },
    @{ Name = 'Bounded log observation'; Script = 'orchestrator_watchdog.py'; ObservationExit = 2 },
    @{ Name = 'Implementation artifact inventory'; Script = 'update_compliance_progress.py'; ObservationExit = 0 }
)
$results = @()
foreach ($check in $checks) {
    $script = Join-Path $dashboardPath $check.Script
    if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
        throw "Required observation script missing: $($check.Script)"
    }
    Write-Host "Collecting $($check.Name)..."
    & $Python $script
    $observedExit = $LASTEXITCODE
    $state = if ($observedExit -eq 0) {
        'OBSERVATION_WRITTEN'
    } elseif ($check.ObservationExit -ne 0 -and $observedExit -eq $check.ObservationExit) {
        'LOG_ISSUES_REPORTED'
    } else {
        'COLLECTION_FAILED'
    }
    $results += [pscustomobject]@{ Check = $check.Name; State = $state; ExitCode = $observedExit }
}
$results | Format-Table -AutoSize
Write-Host 'These observations do not establish runtime health, functional completion, compliance, or recovery.'
if (@($results | Where-Object State -eq 'COLLECTION_FAILED').Count -gt 0) {
    exit 1
}
if (@($results | Where-Object State -eq 'LOG_ISSUES_REPORTED').Count -gt 0) {
    exit 2
}
exit 0
