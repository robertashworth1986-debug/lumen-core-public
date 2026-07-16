[CmdletBinding()]
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path,
    [string]$OutputRoot = "",
    [switch]$RepoOnly,
    [switch]$HashMatches
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $OutputRoot) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $OutputRoot = Join-Path $RepoRoot "artifacts\architecture_validation\$stamp"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }
if (-not $python) { throw "Python 3 is required." }

$engine = Join-Path $RepoRoot "research\architecture_validation\architecture_validation_engine.py"
$seed = Join-Path $RepoRoot "research\architecture_validation\config\architecture_registry_seed.json"

$arguments = @(
    $engine,
    "--repo-root", $RepoRoot,
    "--seed", $seed,
    "--output", $OutputRoot
)

if (-not $RepoOnly) {
    $candidateRoots = @(
        "C:\LumaTrader",
        "C:\LumenCore",
        "C:\LumaUniverse",
        "E:\INSTITUTIONAL_STACK_V2",
        "E:\GLYPH_DRIVE"
    ) | Where-Object { Test-Path $_ }

    foreach ($root in $candidateRoots) {
        $arguments += @("--extra-root", $root)
    }
}

if ($HashMatches) {
    $arguments += "--hash-matches"
}

Write-Host "Running read-only LumenCore architecture inventory..." -ForegroundColor Cyan
Write-Host "Output: $OutputRoot"
& $python.Source @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Architecture scan failed with exit code $LASTEXITCODE"
}

& $python.Source -m unittest discover `
    -s (Join-Path $RepoRoot "research\architecture_validation\tests") `
    -p "test_*.py" `
    -q
if ($LASTEXITCODE -ne 0) {
    throw "Architecture engine tests failed with exit code $LASTEXITCODE"
}

Write-Host "`nArchitecture scan complete." -ForegroundColor Green
Write-Host "Registry: $(Join-Path $OutputRoot 'architecture_registry.md')"
Write-Host "Queue:    $(Join-Path $OutputRoot 'experiment_queue.json')"
Write-Host "Hybrids:  $(Join-Path $OutputRoot 'hybrid_candidate_queue.json')"
Write-Host "Manifest: $(Join-Path $OutputRoot 'scan_manifest.json')"
Write-Host "`nRead-only: no lexicon, constants, architecture, or source files were modified." -ForegroundColor Yellow
