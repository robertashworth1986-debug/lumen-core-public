param(
    [switch]$DryRun,
    [switch]$Check,
    [switch]$Quiet,
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Runner = Join-Path $RepoRoot "code\eia_grid_hourly_hybrid_confirmation.py"
$OutputDir = Join-Path $RepoRoot "out\eia_grid_hourly_hybrid_confirmation_v3"
$SchedulerOutput = Join-Path $OutputDir "scheduler_cycle_latest.json"
$SchedulerOutputTemp = Join-Path $OutputDir "scheduler_cycle_latest.json.tmp"
$SchedulerStderrTemp = Join-Path $OutputDir "scheduler_stderr_latest.log.tmp"
$SchedulerErrors = Join-Path $OutputDir "scheduler_errors.log"
$Arguments = @($Runner)

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $PythonExe = (Get-Command python -ErrorAction Stop).Source
}
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw "Python executable not found: $PythonExe"
}
if ($DryRun) {
    $Arguments += "--dry-run"
}
if ($Check) {
    $Arguments += "--check"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
Push-Location $RepoRoot
try {
    if ($Quiet) {
        Remove-Item -LiteralPath $SchedulerOutputTemp -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $SchedulerStderrTemp -Force -ErrorAction SilentlyContinue
        & $PythonExe @Arguments 1> $SchedulerOutputTemp 2> $SchedulerStderrTemp
        $ExitCode = $LASTEXITCODE
        if ($ExitCode -eq 0) {
            Move-Item -LiteralPath $SchedulerOutputTemp -Destination $SchedulerOutput -Force
            Remove-Item -LiteralPath $SchedulerStderrTemp -Force -ErrorAction SilentlyContinue
        }
    }
    else {
        & $PythonExe @Arguments
        $ExitCode = $LASTEXITCODE
    }
    if ($ExitCode -ne 0) {
        $Stderr = ""
        if (Test-Path -LiteralPath $SchedulerStderrTemp) {
            $Stderr = (Get-Content -LiteralPath $SchedulerStderrTemp -Raw).Trim()
        }
        throw "Hourly hybrid confirmation cycle failed with exit code $ExitCode. $Stderr"
    }
}
catch {
    $Stamp = [DateTime]::UtcNow.ToString("o")
    $FailureExitCode = if ($null -ne $LASTEXITCODE) { $LASTEXITCODE } else { "unavailable" }
    $FailureDetails = ($_ | Out-String).Trim()
    $CapturedStderr = ""
    if (Test-Path -LiteralPath $SchedulerStderrTemp) {
        $CapturedStderr = (Get-Content -LiteralPath $SchedulerStderrTemp -Raw).Trim()
    }
    $FailureRecord = @(
        "[$Stamp] hourly hybrid confirmation cycle failed"
        "exit_code=$FailureExitCode"
        $FailureDetails
    )
    if (-not [string]::IsNullOrWhiteSpace($CapturedStderr)) {
        $FailureRecord += "--- captured stderr ---"
        $FailureRecord += $CapturedStderr
    }
    ($FailureRecord -join [Environment]::NewLine) |
        Out-File -FilePath $SchedulerErrors -Encoding utf8 -Append
    throw
}
finally {
    Pop-Location
}
