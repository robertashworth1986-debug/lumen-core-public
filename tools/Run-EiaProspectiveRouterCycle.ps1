param(
    [int]$TimeoutSeconds = 60,
    [switch]$DryRun,
    [switch]$Quiet,
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Runner = Join-Path $RepoRoot "code\eia_grid_prospective_router_ops.py"
$OutputDir = Join-Path $RepoRoot "out\eia_grid_prospective_hybrid_router"
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
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw "Python executable not found: $PythonExe"
}
if ($DryRun) {
    $Arguments += "--dry-run"
}

Push-Location $RepoRoot
try {
    if ($Quiet) {
        New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
        $PreviousErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $Output = & $PythonExe @Arguments 2>&1
            $ExitCode = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $PreviousErrorActionPreference
        }
        $Output | Out-File -FilePath $SchedulerOutput -Encoding utf8
        if ($ExitCode -ne 0) {
            $Stamp = [DateTime]::UtcNow.ToString("o")
            "[$Stamp] Exit code $ExitCode`n$($Output -join [Environment]::NewLine)" |
                Out-File -FilePath $SchedulerErrors -Encoding utf8 -Append
            throw "Prospective router cycle failed with exit code $ExitCode"
        }
    }
    else {
        & $PythonExe @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Prospective router cycle failed with exit code $LASTEXITCODE"
        }
    }
}
catch {
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
    $Stamp = [DateTime]::UtcNow.ToString("o")
    "[$Stamp] $($_ | Out-String)" | Out-File -FilePath $SchedulerErrors -Encoding utf8 -Append
    throw
}
finally {
    Pop-Location
}
