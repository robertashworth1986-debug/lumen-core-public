param(
    [string]$PythonExe = "python",
    [switch]$FreshLivePull,
    [switch]$StageGlyphVault,
    [string]$VaultRoot = "E:\LumaProofVault",
    [switch]$OpenReports,
    [switch]$SkipTests,
    [switch]$CheckChrome
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Reports = @(
    (Join-Path $Root "docs\FIELD_VALIDATED_DOLLAR_CLAIM_LADDER_2026-06-27.md"),
    (Join-Path $Root "docs\FIELD_MONEY_TRUTH_SWEEP_2026-06-25.md"),
    (Join-Path $Root "docs\GEOMETRY_CHAMPION_OF_CHAMPIONS_2026-06-23.md"),
    (Join-Path $Root "docs\GEOMETRY_ASSET_WIRING_BOARD_2026-06-25.md")
)

function Test-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

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

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Block
    )
    Write-Host ""
    Write-Host "== $Name ==" -ForegroundColor Cyan
    & $Block
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Write-Host "Luma proof unblocker" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host "Admin: $(Test-Admin)"
Write-Host "Fresh live pull: $([bool]$FreshLivePull)"
Write-Host "Stage Glyph/external vault: $([bool]$StageGlyphVault)"

$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$env:Path = "$machinePath;$userPath"

$EnvFiles = @(
    (Join-Path $Root "config\luma_live_keys.env"),
    (Join-Path $Root ".env.live"),
    (Join-Path $Root ".env.sports")
)

Write-Host "Hydrating process env from local key files without printing values..." -ForegroundColor Cyan
foreach ($envFile in $EnvFiles) {
    Import-LumaEnv -Path $envFile
}

if ($StageGlyphVault -and -not (Test-Path -LiteralPath $VaultRoot)) {
    Write-Host "Creating vault root: $VaultRoot" -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path $VaultRoot | Out-Null
}

Write-Host ""
Write-Host "Tool check" -ForegroundColor Cyan
foreach ($tool in @("git", "python", "node", "npm", "pwsh")) {
    $cmd = Get-Command $tool -ErrorAction SilentlyContinue
    if ($cmd) {
        Write-Host ("FOUND {0}: {1}" -f $tool, $cmd.Source) -ForegroundColor Green
    } else {
        Write-Host ("MISSING {0}" -f $tool) -ForegroundColor Yellow
    }
}

if ($CheckChrome) {
    Write-Host ""
    Write-Host "Read-only Chrome/Codex helper process check" -ForegroundColor Cyan
    Get-Process chrome,codex,node,node_repl -ErrorAction SilentlyContinue |
        Select-Object ProcessName, Id, StartTime, CPU, WorkingSet64 |
        Sort-Object ProcessName, StartTime |
        Format-Table -AutoSize
    Write-Host "This script does not kill helpers. Close extra tabs manually or restart Chrome if browser control gets flaky." -ForegroundColor Yellow
}

Set-Location -LiteralPath $Root

$truthArgs = @("-ExecutionPolicy", "Bypass", "-File", (Join-Path $Root "tools\Run-FieldMoneyTruthSweep.ps1"))
if ($FreshLivePull) { $truthArgs += "-FreshLivePull" }
if ($StageGlyphVault) {
    $truthArgs += "-StageGlyphVault"
    $truthArgs += "-VaultRoot"
    $truthArgs += $VaultRoot
}

Invoke-Step "Field money truth sweep" {
    & pwsh @truthArgs
}

Invoke-Step "Geometry champion of champions" {
    & $PythonExe (Join-Path $Root "code\ops\BUILD_GEOMETRY_CHAMPION_OF_CHAMPIONS.py")
}

Invoke-Step "Geometry asset wiring board" {
    & $PythonExe (Join-Path $Root "code\ops\BUILD_GEOMETRY_ASSET_WIRING_BOARD.py")
}

Invoke-Step "Live proof value meter" {
    & $PythonExe (Join-Path $Root "code\ops\BUILD_LIVE_PROOF_VALUE_METER.py")
}

Invoke-Step "Field-validated dollar claim ladder" {
    & $PythonExe (Join-Path $Root "code\ops\BUILD_FIELD_VALIDATED_DOLLAR_CLAIM_LADDER.py")
}

if (-not $SkipTests) {
    Invoke-Step "Focused truth tests" {
        & $PythonExe -m pytest `
            tests\test_field_validated_dollar_claim_ladder.py `
            tests\test_field_money_truth_sweep.py `
            tests\test_geometry_champion_of_champions.py `
            tests\test_geometry_asset_wiring_board.py `
            tests\test_live_proof_value_meter.py `
            -q
    }
}

Write-Host ""
Write-Host "Unblocker run complete." -ForegroundColor Green
Write-Host "Primary dollar claim report: $($Reports[0])"
Write-Host "Primary dashboard feed: $(Join-Path $Root 'dashboard\data\field_validated_dollar_claim_ladder.json')"

if ($OpenReports) {
    foreach ($report in $Reports) {
        if (Test-Path -LiteralPath $report) {
            Start-Process -FilePath $report
        }
    }
}
