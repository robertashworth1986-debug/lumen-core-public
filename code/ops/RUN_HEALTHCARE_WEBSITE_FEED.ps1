param(
    [int]$ExpiringDays = 45,
    [double]$MinHealthcareScore = 35.0,
    [int]$TopN = 40,
    [switch]$IncludeForecasted,
    [string]$ApiKey,
    [switch]$BypassApiKey
)

$ErrorActionPreference = "Stop"

$root = "C:\LumaTrader"
$stackRoot = Join-Path $root "INSTITUTIONAL_STACK_V2"
$engineRunner = Join-Path $stackRoot "code\ops\RUN_HEALTHCARE_GRANTS_ENGINE.ps1"
$feedScript = Join-Path $stackRoot "code\ops\build_healthcare_website_feed.py"

if (-not (Test-Path $engineRunner)) {
    throw "Engine runner not found: $engineRunner"
}
if (-not (Test-Path $feedScript)) {
    throw "Website feed builder not found: $feedScript"
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
    $resolved = Get-Command python -ErrorAction SilentlyContinue
    if ($resolved) {
        $pythonCmd = "python"
    }
}

if (-not $pythonCmd) {
    throw "Python executable not found. Checked venv3.11, .venv, and system path."
}

$runnerArgs = @{
    ExpiringDays = $ExpiringDays
    MinHealthcareScore = $MinHealthcareScore
    TopN = $TopN
}

if ($IncludeForecasted) {
    $runnerArgs["IncludeForecasted"] = $true
}
if ($BypassApiKey) {
    $runnerArgs["BypassApiKey"] = $true
}
if ($ApiKey) {
    $runnerArgs["ApiKey"] = $ApiKey
}

Write-Output "RUN_HEALTHCARE_WEBSITE_FEED stage=engine"
& $engineRunner @runnerArgs

Write-Output "RUN_HEALTHCARE_WEBSITE_FEED stage=website_feed"
& $pythonCmd $feedScript --top-n $TopN
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    throw "Website feed builder failed with exit code $exitCode"
}

Write-Output "RUN_HEALTHCARE_WEBSITE_FEED_COMPLETE"
