[CmdletBinding()]
param(
    [string]$RepoRoot = "C:\LumenCore_GitHub\lumen-core-public",
    [string]$ConstantsPath = "",
    [string]$LexiconPath = "",
    [switch]$SkipPull,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$branch = "research/qmpl-swarm-validation-sweep"

if (-not (Test-Path $RepoRoot)) {
    throw "Local repository not found: $RepoRoot"
}

Push-Location $RepoRoot
try {
    $dirty = git status --porcelain
    if ($LASTEXITCODE -ne 0) {
        throw "Git status failed in $RepoRoot"
    }
    if ($dirty) {
        throw "The repository has uncommitted changes. Commit or stash them before switching branches."
    }

    if (-not $SkipPull) {
        git fetch origin
        if ($LASTEXITCODE -ne 0) { throw "git fetch origin failed" }

        $localBranch = git branch --list $branch
        if ($localBranch) {
            git switch $branch
        }
        else {
            git switch --track -c $branch "origin/$branch"
        }
        if ($LASTEXITCODE -ne 0) { throw "Could not switch to $branch" }

        git pull --ff-only origin $branch
        if ($LASTEXITCODE -ne 0) { throw "Fast-forward pull failed for $branch" }
    }

    $runner = Join-Path $RepoRoot "research\qmpl\Run-QMPLSweep.ps1"
    if (-not (Test-Path $runner)) {
        throw "QMPL runner not found after branch update: $runner"
    }

    if (-not $ConstantsPath -or -not $LexiconPath) {
        Write-Host "Canonical constants/lexicon paths were not supplied." -ForegroundColor Yellow
        Write-Host "Running a read-only candidate-file search first..." -ForegroundColor Cyan
        & powershell -ExecutionPolicy Bypass -File $runner -FindLumaFiles
        Write-Host "`nSelect the canonical files, then re-run Start-Local-QMPL.ps1 with both paths." -ForegroundColor Yellow
        exit 0
    }

    $argsList = @(
        "-ExecutionPolicy", "Bypass",
        "-File", $runner,
        "-ConstantsPath", $ConstantsPath,
        "-LexiconPath", $LexiconPath
    )
    if ($SkipInstall) {
        $argsList += "-SkipInstall"
    }

    & powershell @argsList
    if ($LASTEXITCODE -ne 0) {
        throw "Local QMPL sweep failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
