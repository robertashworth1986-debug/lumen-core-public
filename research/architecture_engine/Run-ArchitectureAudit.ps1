[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [string[]]$AdditionalRoots = @(),
    [string]$ConstantsPath = "",
    [string]$LexiconPath = "",
    [string]$OutputRoot = "",
    [switch]$ExternalContentScan,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

if (-not $OutputRoot) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $OutputRoot = Join-Path $RepoRoot "artifacts\architecture_audit\$stamp"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "Python 3 was not found. Install Python 3 and rerun."
}

$engine = Join-Path $RepoRoot "research\architecture_engine\architecture_discovery.py"
if (-not (Test-Path $engine)) {
    throw "Architecture engine not found: $engine"
}

New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

$arguments = @(
    $engine,
    "--repo-root", $RepoRoot,
    "--output", $OutputRoot
)

$rootIndex = 0
foreach ($root in $AdditionalRoots) {
    $rootIndex += 1
    if (Test-Path $root) {
        $arguments += @("--additional-root", (Resolve-Path $root).Path)
    }
    else {
        Write-Warning "Authorized root not found and skipped: $root"
    }
}

if ($ExternalContentScan) {
    Write-Warning "External content scanning is enabled. Review outputs before committing them."
    $arguments += "--external-content-scan"
}

if ($ConstantsPath) {
    if (-not (Test-Path $ConstantsPath)) { throw "Constants file not found: $ConstantsPath" }
    $arguments += @("--constants", (Resolve-Path $ConstantsPath).Path)
}

if ($LexiconPath) {
    if (-not (Test-Path $LexiconPath)) { throw "Lexicon file not found: $LexiconPath" }
    $arguments += @("--lexicon", (Resolve-Path $LexiconPath).Path)
}

Write-Host "Running LumenCore architecture discovery and validation planning..." -ForegroundColor Cyan
Write-Host "Repository: $RepoRoot"
Write-Host "Output:     $OutputRoot"
Write-Host "External roots default to metadata-only scanning." -ForegroundColor Yellow

& $python.Source @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Architecture audit failed with exit code $LASTEXITCODE"
}

if (-not $SkipTests) {
    $tests = Join-Path $RepoRoot "research\architecture_engine\tests"
    if (Test-Path $tests) {
        & $python.Source -m pytest $tests -q
        if ($LASTEXITCODE -ne 0) {
            throw "Architecture-engine tests failed with exit code $LASTEXITCODE"
        }
    }
}

$manifest = Join-Path $OutputRoot "run_manifest.json"
if (-not (Test-Path $manifest)) {
    throw "Audit completed without a run manifest."
}

Write-Host "`nArchitecture audit complete." -ForegroundColor Green
Write-Host "Inventory:  $(Join-Path $OutputRoot 'architecture_inventory.json')"
Write-Host "Backlog:    $(Join-Path $OutputRoot 'validation_backlog.md')"
Write-Host "Risk file:  $(Join-Path $OutputRoot 'claim_risk_register.md')"
Write-Host "Manifest:   $manifest"
Write-Host "`nNo discovered architecture was executed or modified." -ForegroundColor Yellow
