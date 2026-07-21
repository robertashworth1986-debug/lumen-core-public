param(
    [int]$TimeoutSeconds = 90,
    [int]$CycleTimeoutSeconds = 420,
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
if ($CycleTimeoutSeconds -lt 30) {
    throw "CycleTimeoutSeconds must be at least 30 seconds."
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
        $Process = Start-Process `
            -FilePath $PythonExe `
            -ArgumentList $Arguments `
            -PassThru `
            -WindowStyle Hidden `
            -RedirectStandardOutput $SchedulerOutputTemp `
            -RedirectStandardError $SchedulerStderrTemp
        $Completed = $Process.WaitForExit($CycleTimeoutSeconds * 1000)
        if (-not $Completed) {
            Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
            $Process.WaitForExit()
            throw "Prospective hourly router cycle exceeded the $CycleTimeoutSeconds-second process limit. Child process $($Process.Id) was terminated; the last good scheduler receipt was preserved."
        }
        $ExitCode = $Process.ExitCode
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
    "[$Stamp] $($_ | Out-String)" | Out-File -FilePath $SchedulerErrors -Encoding utf8 -Append
    throw
}
finally {
    Pop-Location
}
