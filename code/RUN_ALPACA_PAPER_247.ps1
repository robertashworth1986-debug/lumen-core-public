[CmdletBinding()]
param(
    [ValidateRange(30, 86400)]
    [int]$DefaultSleepSeconds = 300,

    [switch]$Once,

    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"
$Stack = Split-Path -Parent $PSScriptRoot
$CodeDir = Join-Path $Stack "code"
$ConfigDir = Join-Path $Stack "config"
$Builder = Join-Path $CodeDir "alpaca_paper_loop_builder.py"
$RuntimeConfigFile = Join-Path $ConfigDir "paper_trader_runtime.json"

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $PythonExe = (Get-Command python -ErrorAction Stop).Source
}
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw "Python executable not found: $PythonExe"
}
if (-not (Test-Path -LiteralPath $Builder -PathType Leaf)) {
    throw "Paper-loop builder not found: $Builder"
}

while ($true) {
    Write-Host ""
    Write-Host "=== PAPER TRADING SWEEP === $(Get-Date -Format s)" -ForegroundColor Cyan

    $cycleSucceeded = $false
    try {
        & $PythonExe $Builder
        if ($LASTEXITCODE -ne 0) {
            throw "Paper-loop builder exited with code $LASTEXITCODE."
        }
        $cycleSucceeded = $true
    }
    catch {
        Write-Warning "Paper trading sweep failed: $($_.Exception.Message)"
    }

    $sleepSeconds = $DefaultSleepSeconds
    if (Test-Path -LiteralPath $RuntimeConfigFile -PathType Leaf) {
        try {
            $runtimeConfig = Get-Content -LiteralPath $RuntimeConfigFile -Raw -Encoding UTF8 | ConvertFrom-Json
            $configuredSeconds = 0
            if (
                $runtimeConfig.PSObject.Properties.Name -contains "loop_seconds" -and
                [int]::TryParse([string]$runtimeConfig.loop_seconds, [ref]$configuredSeconds) -and
                $configuredSeconds -ge 30 -and
                $configuredSeconds -le 86400
            ) {
                $sleepSeconds = $configuredSeconds
            }
        }
        catch {
            Write-Warning "Using the default sleep interval because the runtime config is invalid: $($_.Exception.Message)"
        }
    }

    if ($Once) {
        if (-not $cycleSucceeded) {
            exit 1
        }
        break
    }

    Write-Host "Sleeping $sleepSeconds seconds..." -ForegroundColor Yellow
    Start-Sleep -Seconds $sleepSeconds
}
