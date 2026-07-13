param(
    [string]$PythonExe = "python",
    [switch]$SkipNetwork,
    [switch]$OpenReport,
    [string]$ExtraKeyFile = "C:\Users\Novac\iCloudDrive\Kraken api\text.txt",
    [ValidateRange(1, 5000)]
    [int]$MaxRows = 250,
    [ValidateRange(3, 120)]
    [int]$SourceTimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$EnvPath = Join-Path $Root "config\luma_live_keys.env"
$Runner = Join-Path $Root "code\ops\BUILD_LIVE_EVIDENCE_MAX_HARVEST.py"
$Report = Join-Path $Root ("docs\LIVE_EVIDENCE_MAX_HARVEST_{0}.md" -f (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd"))

function Import-LumaEnv {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        Write-Host "Env file missing: $Path" -ForegroundColor Yellow
        return
    }
    Get-Content -LiteralPath $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or ($line -notmatch "=")) { return }
        $parts = $line.Split("=", 2)
        $name = $parts[0].Trim()
        $value = $parts[1].Trim().Trim('"').Trim("'")
        if ($name -and $value) {
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

Write-Host "Luma live evidence max harvest" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host "Hydrating env keys without printing secrets..." -ForegroundColor Cyan
Import-LumaEnv -Path $EnvPath

$argsList = @($Runner)
if ($SkipNetwork) { $argsList += "--skip-network" }
$argsList += "--max-rows"
$argsList += $MaxRows
$argsList += "--source-timeout"
$argsList += $SourceTimeoutSeconds
if ($ExtraKeyFile -and (Test-Path -LiteralPath $ExtraKeyFile)) {
    $argsList += "--extra-key-file"
    $argsList += $ExtraKeyFile
}

Write-Host "Running evidence harvest..." -ForegroundColor Cyan
& $PythonExe @argsList
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    throw "Live evidence harvest failed with exit code $exitCode"
}

Write-Host "Harvest complete." -ForegroundColor Green
Write-Host "Report: $Report"

if ($OpenReport -and (Test-Path -LiteralPath $Report)) {
    Start-Process -FilePath $Report
}
