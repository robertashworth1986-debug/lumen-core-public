param(
    [int]$TimeoutSeconds = 90,
    [switch]$DryRun,
    [switch]$Quiet,
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Runner = Join-Path $RepoRoot "code\eia_grid_prospective_hourly_router.py"
$OutputDir = Join-Path $RepoRoot "out\eia_grid_prospective_hourly_router"
$SchedulerOutput = Join-Path $OutputDir "scheduler_cycle_latest.json"
$SchedulerOutputTemp = Join-Path $OutputDir "scheduler_cycle_latest.json.tmp"
$SchedulerStderrTemp = Join-Path $OutputDir "scheduler_stderr_latest.log.tmp"
$SchedulerErrors = Join-Path $OutputDir "scheduler_errors.log"
$Arguments = @($Runner, "--timeout", $TimeoutSeconds)

$UserEiaKey = [Environment]::GetEnvironmentVariable("EIA_API_KEY", "User")
$UserEiaPremiumKey = [Environment]::GetEnvironmentVariable("EIA_API_KEY_PREMIUM", "User")
if (-not [string]::IsNullOrWhiteSpace($UserEiaKey)) {
    $env:EIA_API_KEY = $UserEiaKey
}
elseif (-not [string]::IsNullOrWhiteSpace($UserEiaPremiumKey)) {
    $env:EIA_API_KEY_PREMIUM = $UserEiaPremiumKey
}
else {
    throw "No user-level EIA API key is configured."
}
if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $PythonExe = (Get-Command python -ErrorAction Stop).Source
}
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw "Python executable not found: $PythonExe"
}
if ($DryRun) {
    $Arguments += "--dry-run"
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
        throw "Prospective hourly router cycle failed with exit code $ExitCode. $Stderr"
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
        "[$Stamp] prospective hourly router cycle failed"
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
