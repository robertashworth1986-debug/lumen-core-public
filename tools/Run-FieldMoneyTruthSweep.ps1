param(
    [string]$PythonExe = "python",
    [switch]$FreshLivePull,
    [switch]$StageGlyphVault,
    [string]$VaultRoot = "E:\LumaProofVault",
    [string]$ExtraKeyFile = "C:\Users\Novac\iCloudDrive\Kraken api\text.txt",
    [switch]$OpenReport
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Runner = Join-Path $Root "code\ops\BUILD_FIELD_MONEY_TRUTH_SWEEP.py"
$Report = Join-Path $Root "docs\FIELD_MONEY_TRUTH_SWEEP_2026-06-25.md"
$EnvFiles = @(
    (Join-Path $Root "config\luma_live_keys.env"),
    (Join-Path $Root ".env.live"),
    (Join-Path $Root ".env.sports")
)

function Import-LumaEnv {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }
    Get-Content -LiteralPath $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or ($line -notmatch "=")) { return }
        $parts = $line.Split("=", 2)
        $name = $parts[0].Trim()
        $value = $parts[1].Trim().Trim('"').Trim("'")
        if ($name -and $value -and -not [Environment]::GetEnvironmentVariable($name, "Process")) {
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

Write-Host "Luma field-money truth sweep" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host "Hydrating env keys without printing values..." -ForegroundColor Cyan
foreach ($envFile in $EnvFiles) {
    Import-LumaEnv -Path $envFile
}

$argsList = @($Runner, "--run-pipeline")
if (-not $FreshLivePull) {
    $argsList += "--skip-network"
}
if ($StageGlyphVault) {
    $argsList += "--stage-vault"
    $argsList += "--vault-root"
    $argsList += $VaultRoot
}
if ($ExtraKeyFile -and (Test-Path -LiteralPath $ExtraKeyFile)) {
    $argsList += "--extra-key-file"
    $argsList += $ExtraKeyFile
}

Write-Host "Fresh live pull: $([bool]$FreshLivePull)" -ForegroundColor Cyan
Write-Host "Stage external proof vault: $([bool]$StageGlyphVault)" -ForegroundColor Cyan
Write-Host "Vault root: $VaultRoot"
& $PythonExe @argsList
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    throw "Field-money truth sweep failed with exit code $exitCode"
}

Write-Host "Truth sweep complete." -ForegroundColor Green
Write-Host "Report: $Report"
if ($OpenReport -and (Test-Path -LiteralPath $Report)) {
    Start-Process -FilePath $Report
}
