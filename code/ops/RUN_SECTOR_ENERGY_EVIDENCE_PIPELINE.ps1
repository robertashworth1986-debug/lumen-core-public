param(
    [switch]$RunInvestorSweep,
    [switch]$PushNodeRed,
    [string]$NodeRedBase = "http://127.0.0.1:8787",
    [int]$InvestorMaxFiles = 0,
    [int]$InvestorMaxSeries = 0,
    [int]$InvestorMinRows = 252,
    [double]$InvestorMinSpanYears = 1.0,
    [int]$StepTimeoutSec = 5400
)

$ErrorActionPreference = 'Stop'

$repoRoot = 'C:/LumaTrader/INSTITUTIONAL_STACK_V2'
$script = "$repoRoot/code/ops/run_sector_energy_evidence_pipeline.py"

$pythonCandidates = @(
    'c:/LumaTrader/venv3.11/Scripts/python.exe',
    'c:/LumaTrader/.venv/Scripts/python.exe'
)

$python = $null
foreach ($candidate in $pythonCandidates) {
    if (Test-Path $candidate) {
        $python = $candidate
        break
    }
}

if (-not $python) {
    $resolved = Get-Command python -ErrorAction SilentlyContinue
    if ($resolved) {
        $python = 'python'
    }
}

if (-not $python) {
    throw 'Python runtime not found. Checked venv3.11, .venv, and system path.'
}

if (-not (Test-Path $script)) {
    throw "Sector energy evidence pipeline script not found: $script"
}

$argsList = @(
    $script,
    '--python-exe', $python,
    '--step-timeout-sec', $StepTimeoutSec,
    '--investor-max-files', $InvestorMaxFiles,
    '--investor-max-series', $InvestorMaxSeries,
    '--investor-min-rows', $InvestorMinRows,
    '--investor-min-span-years', $InvestorMinSpanYears
)

if ($RunInvestorSweep) {
    $argsList += '--run-investor-sweep'
}

if ($PushNodeRed) {
    $argsList += @('--push-nodered', '--nodered-base', $NodeRedBase)
}

Write-Output "RUN_SECTOR_ENERGY_EVIDENCE_PIPELINE python=$python"
Write-Output "RUN_SECTOR_ENERGY_EVIDENCE_PIPELINE runInvestorSweep=$RunInvestorSweep pushNodeRed=$PushNodeRed"
Write-Output "RUN_SECTOR_ENERGY_EVIDENCE_PIPELINE investorMaxFiles=$InvestorMaxFiles investorMaxSeries=$InvestorMaxSeries"

& $python @argsList
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    throw "Sector energy evidence pipeline failed with exit code $exitCode"
}

Write-Output "RUN_SECTOR_ENERGY_EVIDENCE_PIPELINE_COMPLETE"
