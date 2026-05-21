param(
    [switch]$PushNodeRed,
    [switch]$RunSectorEnergyPipeline,
    [string]$NodeRedBase = "http://127.0.0.1:8787",
    [int]$MaxSeries = 0,
    [int]$MinRows = 252,
    [double]$MinSpanYears = 1.0
)

$ErrorActionPreference = "Stop"

$root = "C:\LumaTrader"
$scriptPath = Join-Path $root "INSTITUTIONAL_STACK_V2\code\ops\investor_proof_sweep.py"
$valuationLockScript = Join-Path $root "INSTITUTIONAL_STACK_V2\code\ops\LOCK_AUTONOMOUS_GRANT_WIN.py"
$valuationBriefScript = Join-Path $root "INSTITUTIONAL_STACK_V2\code\ops\BUILD_VALUATION_LICENSING_BRIEF.py"
$premiumDeckScript = Join-Path $root "INSTITUTIONAL_STACK_V2\code\ops\BUILD_PREMIUM_3MIN_DROPMIC_DECK.py"
$frozenDeltaChainScript = Join-Path $root "INSTITUTIONAL_STACK_V2\code\ops\BUILD_FROZEN_DELTA_TRUTH_CHAIN.py"

if (-not (Test-Path $scriptPath)) {
    throw "Investor proof sweep script not found: $scriptPath"
}
if (-not (Test-Path $valuationLockScript)) {
    throw "Valuation lock script not found: $valuationLockScript"
}
if (-not (Test-Path $valuationBriefScript)) {
    throw "Valuation licensing brief script not found: $valuationBriefScript"
}
if (-not (Test-Path $premiumDeckScript)) {
    throw "Premium drop-mic deck script not found: $premiumDeckScript"
}
if (-not (Test-Path $frozenDeltaChainScript)) {
    throw "Frozen delta truth chain script not found: $frozenDeltaChainScript"
}

$pythonCandidates = @(
    (Join-Path $root "venv3.11\Scripts\python.exe"),
    (Join-Path $root ".venv\Scripts\python.exe")
)

$pythonCmd = $null
foreach ($candidate in $pythonCandidates) {
    if (Test-Path $candidate) {
        $pythonCmd = $candidate
        break
    }
}

if (-not $pythonCmd) {
    $pythonResolved = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonResolved) {
        $pythonCmd = "python"
    }
}

if (-not $pythonCmd) {
    throw "Python executable not found. Checked venv3.11, .venv, and system path."
}

$argsList = @(
    $scriptPath,
    "--root", $root,
    "--stack-root", (Join-Path $root "INSTITUTIONAL_STACK_V2"),
    "--min-rows", $MinRows,
    "--min-span-years", $MinSpanYears
)

if ($MaxSeries -gt 0) {
    $argsList += @("--max-series", $MaxSeries)
}

if ($PushNodeRed) {
    $argsList += @("--push-nodered", "--nodered-base", $NodeRedBase)
}

Write-Output "RUN_INVESTOR_PROOF_SWEEP python=$pythonCmd"
Write-Output "RUN_INVESTOR_PROOF_SWEEP pushNodeRed=$PushNodeRed nodeRedBase=$NodeRedBase maxSeries=$MaxSeries"
Write-Output "RUN_INVESTOR_PROOF_SWEEP runSectorEnergyPipeline=$RunSectorEnergyPipeline"

& $pythonCmd @argsList
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    throw "Investor proof sweep failed with exit code $exitCode"
}

if ($RunSectorEnergyPipeline) {
    $sectorScript = Join-Path $root "INSTITUTIONAL_STACK_V2\code\ops\run_sector_energy_evidence_pipeline.py"
    if (-not (Test-Path $sectorScript)) {
        throw "Sector energy evidence pipeline script not found: $sectorScript"
    }

    Write-Output "RUN_INVESTOR_PROOF_SWEEP sectorEnergyPipeline=true"
    & $pythonCmd $sectorScript
    $sectorExitCode = $LASTEXITCODE
    if ($sectorExitCode -ne 0) {
        throw "Sector energy evidence pipeline failed with exit code $sectorExitCode"
    }
}

Write-Output "RUN_INVESTOR_PROOF_SWEEP valuationRefresh=true"
& $pythonCmd $valuationLockScript
$valuationExitCode = $LASTEXITCODE
if ($valuationExitCode -ne 0) {
    throw "LOCK_AUTONOMOUS_GRANT_WIN failed with exit code $valuationExitCode"
}

& $pythonCmd $valuationBriefScript
$briefExitCode = $LASTEXITCODE
if ($briefExitCode -ne 0) {
    throw "BUILD_VALUATION_LICENSING_BRIEF failed with exit code $briefExitCode"
}

& $pythonCmd $premiumDeckScript
$deckExitCode = $LASTEXITCODE
if ($deckExitCode -ne 0) {
    throw "BUILD_PREMIUM_3MIN_DROPMIC_DECK failed with exit code $deckExitCode"
}

& $pythonCmd $frozenDeltaChainScript --strict
$frozenDeltaExitCode = $LASTEXITCODE
if ($frozenDeltaExitCode -ne 0) {
    throw "BUILD_FROZEN_DELTA_TRUTH_CHAIN failed with exit code $frozenDeltaExitCode"
}

Write-Output "RUN_INVESTOR_PROOF_SWEEP_COMPLETE"
