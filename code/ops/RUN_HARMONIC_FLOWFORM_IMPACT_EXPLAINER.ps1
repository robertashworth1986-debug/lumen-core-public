param(
    [double]$MinGainPct = 0.01,
    [int]$TopN = 25
)

$ErrorActionPreference = "Stop"

$root = "C:\LumaTrader"
$stackRoot = Join-Path $root "INSTITUTIONAL_STACK_V2"
$scriptPath = Join-Path $stackRoot "code\ops\harmonic_flowform_impact_explainer.py"

if (-not (Test-Path $scriptPath)) {
    throw "Impact explainer script not found: $scriptPath"
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
    "--stack-root", $stackRoot,
    "--min-gain-pct", $MinGainPct,
    "--top-n", $TopN
)

Write-Output "RUN_HARMONIC_FLOWFORM_IMPACT_EXPLAINER python=$pythonCmd minGainPct=$MinGainPct topN=$TopN"

& $pythonCmd @argsList
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    throw "Harmonic flowform impact explainer failed with exit code $exitCode"
}

Write-Output "RUN_HARMONIC_FLOWFORM_IMPACT_EXPLAINER_COMPLETE"
