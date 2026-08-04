[CmdletBinding()]
param(
    [ValidateSet("FRED", "TWELVE_DATA", "ALL")]
    [string]$Source = "ALL",
    [switch]$DryRun,
    [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"
$collector = Join-Path $PSScriptRoot "time_series_source_native_prospective_collector.py"

function Invoke-Collector {
    param([string[]]$Arguments)

    & py -3.11 $collector @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Prospective collector failed with exit code $LASTEXITCODE."
    }
}

Invoke-Collector -Arguments @("verify")

$sources = if ($Source -eq "ALL") { @("FRED", "TWELVE_DATA") } else { @($Source) }
foreach ($name in $sources) {
    if ($name -eq "FRED" -and [string]::IsNullOrWhiteSpace($env:FRED_API_KEY)) {
        throw "FRED_API_KEY is not available in this process environment."
    }
    if ($name -eq "TWELVE_DATA") {
        $available = @(
            $env:TWELVE_DATA_API_KEY,
            $env:TWELVEDATA_API_KEY,
            $env:TWELVE_DATA_KEY
        ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
        if ($available.Count -eq 0) {
            throw "No registered Twelve Data key is available in this process environment."
        }
    }
}

$arguments = @("cycle")
foreach ($name in $sources) {
    $arguments += @("--source", $name)
}
if (-not [string]::IsNullOrWhiteSpace($OutDir)) {
    $arguments += @("--out-dir", $OutDir)
}
if ($DryRun) {
    $arguments += "--dry-run"
}

Invoke-Collector -Arguments $arguments
