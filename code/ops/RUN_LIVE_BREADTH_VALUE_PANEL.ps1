param(
    [int]$TopN = 8,
    [switch]$RefreshLiveRegistry
)

$ErrorActionPreference = "Stop"

$root = "C:\LumaTrader"
$stackRoot = Join-Path $root "INSTITUTIONAL_STACK_V2"
$panelScript = Join-Path $stackRoot "code\ops\build_live_breadth_value_panel.py"
$liveProbeScript = Join-Path $stackRoot "code\HARD_TRUTH_LIVE_MEASUREMENT_AUDIT.py"

if (-not (Test-Path $panelScript)) {
    throw "Live breadth panel script not found: $panelScript"
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

Write-Output "RUN_LIVE_BREADTH_VALUE_PANEL python=$pythonCmd topN=$TopN refreshLiveRegistry=$RefreshLiveRegistry"

if ($RefreshLiveRegistry -and (Test-Path $liveProbeScript)) {
    Write-Output "Refreshing live source registry via HARD_TRUTH_LIVE_MEASUREMENT_AUDIT.py"
    & $pythonCmd $liveProbeScript
    $refreshExit = $LASTEXITCODE
    if ($refreshExit -ne 0) {
        throw "Live registry refresh failed with exit code $refreshExit"
    }
}

& $pythonCmd $panelScript --stack-root $stackRoot --top-n $TopN
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    throw "Live breadth panel build failed with exit code $exitCode"
}

Write-Output "RUN_LIVE_BREADTH_VALUE_PANEL_COMPLETE"
