param(
    [int]$TopLiquid = 36,
    [int]$Limit = 20,
    [double]$MinTurnoverUsd = 300000,
    [double]$MaxSpreadBps = 45,
    [double]$SpikeThresholdPct = 3.0,
    [string]$Quotes = "ZUSD,USDT"
)

$ErrorActionPreference = "Stop"

$root = "C:\LumaTrader"
$stackRoot = Join-Path $root "INSTITUTIONAL_STACK_V2"
$scriptPath = Join-Path $stackRoot "code\ops\build_kraken_multi_tf_alpha_map.py"

if (-not (Test-Path $scriptPath)) {
    throw "Kraken multi-timeframe alpha map script not found: $scriptPath"
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

Write-Output "RUN_KRAKEN_MULTI_TF_ALPHA_MAP python=$pythonCmd topLiquid=$TopLiquid limit=$Limit minTurnoverUsd=$MinTurnoverUsd maxSpreadBps=$MaxSpreadBps quotes=$Quotes"

& $pythonCmd $scriptPath `
    --stack-root $stackRoot `
    --top-liquid $TopLiquid `
    --limit $Limit `
    --min-turnover-usd $MinTurnoverUsd `
    --max-spread-bps $MaxSpreadBps `
    --spike-threshold-pct $SpikeThresholdPct `
    --quotes $Quotes

$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    throw "Kraken multi-timeframe alpha map failed with exit code $exitCode"
}

Write-Output "RUN_KRAKEN_MULTI_TF_ALPHA_MAP_COMPLETE"
