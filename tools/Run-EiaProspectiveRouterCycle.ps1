param(
    [int]$TimeoutSeconds = 60,
    [switch]$DryRun,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Runner = Join-Path $RepoRoot "code\eia_grid_prospective_router_ops.py"
$OutputDir = Join-Path $RepoRoot "out\eia_grid_prospective_hybrid_router"
$SchedulerOutput = Join-Path $OutputDir "scheduler_cycle_latest.json"
$SchedulerErrors = Join-Path $OutputDir "scheduler_errors.log"
$Arguments = @($Runner, "--timeout", $TimeoutSeconds)
if ($DryRun) {
    $Arguments += "--dry-run"
}

Push-Location $RepoRoot
try {
    if ($Quiet) {
        New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
        $Output = & python @Arguments 2>&1
        $ExitCode = $LASTEXITCODE
        $Output | Out-File -FilePath $SchedulerOutput -Encoding utf8
        if ($ExitCode -ne 0) {
            $Stamp = [DateTime]::UtcNow.ToString("o")
            "[$Stamp] Exit code $ExitCode`n$($Output -join [Environment]::NewLine)" |
                Out-File -FilePath $SchedulerErrors -Encoding utf8 -Append
            throw "Prospective router cycle failed with exit code $ExitCode"
        }
    }
    else {
        & python @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Prospective router cycle failed with exit code $LASTEXITCODE"
        }
    }
}
finally {
    Pop-Location
}
