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
if ($DryRun) {
    $Arguments += "--dry-run"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
Push-Location $RepoRoot
try {
    if ($Quiet) {
        $Output = & $PythonExe @Arguments 2>&1
        $ExitCode = $LASTEXITCODE
        $Output | Out-File -FilePath $SchedulerOutput -Encoding utf8
    }
    else {
        & $PythonExe @Arguments
        $ExitCode = $LASTEXITCODE
    }
    if ($ExitCode -ne 0) {
        throw "Prospective hourly router cycle failed with exit code $ExitCode"
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
