[CmdletBinding()]
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string]$OutputRoot = "",
    [string]$ConstantsPath = "",
    [string]$LexiconPath = "",
    [switch]$FindLumaFiles,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $OutputRoot) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $OutputRoot = Join-Path $RepoRoot "artifacts\qmpl\$stamp"
}

if ($FindLumaFiles) {
    $roots = @("C:\LumenCore", "C:\LumaUniverse", "C:\LumaTrader", "E:\INSTITUTIONAL_STACK_V2", "E:\GLYPH_DRIVE") |
        Where-Object { Test-Path $_ }

    Write-Host "`nRead-only search for likely lexicon/constants files:" -ForegroundColor Cyan
    foreach ($root in $roots) {
        Get-ChildItem -Path $root -File -Recurse -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Name -match "(?i)(lexicon|constant|parameter|config|glyph|dictionary)"
            } |
            Select-Object FullName, Length, LastWriteTime
    }
    Write-Host "`nRe-run with -ConstantsPath and -LexiconPath after selecting the canonical files."
    exit 0
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "Python 3 was not found. Install Python 3, then re-run."
}

if (-not $SkipInstall) {
    & $python.Source -m pip install --disable-pip-version-check -r (Join-Path $RepoRoot "research\qmpl\requirements.txt")
}

$config = Join-Path $RepoRoot "research\qmpl\config\default_sweep.json"
$runner = Join-Path $RepoRoot "research\qmpl\qmpl_sim.py"
$reporter = Join-Path $RepoRoot "research\qmpl\qmpl_report.py"

New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

$argsList = @(
    $runner,
    "--config", $config,
    "--output", $OutputRoot
)

if ($ConstantsPath) {
    if (-not (Test-Path $ConstantsPath)) { throw "Constants file not found: $ConstantsPath" }
    $argsList += @("--constants", (Resolve-Path $ConstantsPath).Path)
}
if ($LexiconPath) {
    if (-not (Test-Path $LexiconPath)) { throw "Lexicon file not found: $LexiconPath" }
    $argsList += @("--lexicon", (Resolve-Path $LexiconPath).Path)
}

Write-Host "Running QMPL public-safe validation sweep..." -ForegroundColor Cyan
Write-Host "Output: $OutputRoot"
& $python.Source @argsList

if ($LASTEXITCODE -ne 0) {
    throw "QMPL sweep failed with exit code $LASTEXITCODE"
}

& $python.Source $reporter "--output" $OutputRoot
if ($LASTEXITCODE -ne 0) {
    throw "QMPL report generation failed with exit code $LASTEXITCODE"
}

& $python.Source -m pytest (Join-Path $RepoRoot "research\qmpl\tests") -q
if ($LASTEXITCODE -ne 0) {
    throw "QMPL tests failed with exit code $LASTEXITCODE"
}

$manifest = Join-Path $OutputRoot "manifest.json"
if (-not (Test-Path $manifest)) {
    throw "Run completed without a manifest."
}

Write-Host "`nQMPL sweep complete." -ForegroundColor Green
Write-Host "Manifest: $manifest"
Write-Host "Results:  $(Join-Path $OutputRoot 'phase_sweep_results.csv')"
Write-Host "Formation: $(Join-Path $OutputRoot 'formation_transition_results.csv')"
Write-Host "`nSimulation only. Do not treat outputs as external validation or flight evidence." -ForegroundColor Yellow
