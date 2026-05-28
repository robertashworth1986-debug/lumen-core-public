param(
    [double]$Bankroll = 10.0,
    [int]$TopN = 12,
    [int]$Pick6Limit = 6
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$py = Join-Path $root 'venv3.11\Scripts\python.exe'
if (-not (Test-Path $py)) {
    $py = 'python'
}

$script = Join-Path $PSScriptRoot 'BUILD_SPORTS_MONTE_CARLO_EDGE.py'

& $py $script --bankroll $Bankroll --top-n $TopN --pick6-limit $Pick6Limit
if ($LASTEXITCODE -ne 0) {
    throw "RUN_SPORTS_MONTE_CARLO_EDGE failed with exit code $LASTEXITCODE"
}

Write-Host 'RUN_SPORTS_MONTE_CARLO_EDGE_COMPLETE' -ForegroundColor Green
