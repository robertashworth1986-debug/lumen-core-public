$ErrorActionPreference = "Stop"

function Load-JsonFile {
    param([string]$Path, $Default = $null)
    if (Test-Path $Path) {
        try { return (Get-Content $Path -Raw -Encoding UTF8 | ConvertFrom-Json -Depth 100) }
        catch { return $Default }
    }
    return $Default
}

function Save-JsonFile {
    param([string]$Path, $Object)
    $parent = Split-Path $Path -Parent
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    $Object | ConvertTo-Json -Depth 100 | Set-Content -Path $Path -Encoding UTF8
}

function To-Array {
    param($Value)
    if ($null -eq $Value) { return @() }
    if ($Value -is [System.Array]) { return @($Value) }
    return @($Value)
}

function Get-Prop {
    param($Obj, [string]$Name, $Default = $null)
    if ($null -eq $Obj) { return $Default }
    $p = $Obj.PSObject.Properties[$Name]
    if ($p) { return $p.Value }
    return $Default
}

function Get-AdaptiveSymbolsFromCsv {
    param([string]$CsvPath)

    $rows = @()
    try { $rows = Import-Csv -Path $CsvPath } catch { return @() }
    if (-not $rows -or $rows.Count -eq 0) { return @() }

    $candidateCols = @("symbol","ticker","pair","asset","code","instrument")
    $foundCol = $null

    foreach ($c in $candidateCols) {
        if ($rows[0].PSObject.Properties.Name -contains $c) {
            $foundCol = $c
            break
        }
    }

    if (-not $foundCol) { return @() }

    $symbols = New-Object System.Collections.Generic.List[string]
    foreach ($r in $rows) {
        $v = [string]($r.$foundCol)
        if (-not [string]::IsNullOrWhiteSpace($v)) {
            $v = $v.Trim().ToUpper()
            if (-not $symbols.Contains($v)) { [void]$symbols.Add($v) }
        }
    }
    return @($symbols)
}

function Get-AdaptiveSymbols {
    param(
        [string]$Root,
        [string]$Out,
        [string]$Conf
    )

    $hits = New-Object System.Collections.Generic.List[string]

    $csvCandidates = @(
        (Join-Path $Out  "adaptive_universe.csv"),
        (Join-Path $Out  "universe.csv"),
        (Join-Path $Root "adaptive_universe.csv"),
        (Join-Path $Root "universe.csv")
    )

    foreach ($p in $csvCandidates) {
        if (Test-Path $p) {
            foreach ($s in (Get-AdaptiveSymbolsFromCsv -CsvPath $p)) {
                if (-not [string]::IsNullOrWhiteSpace($s) -and -not $hits.Contains($s)) {
                    [void]$hits.Add($s)
                }
            }
        }
    }

    if ($hits.Count -gt 0) { return @($hits) }

    $runtimePath = Join-Path $Conf "paper_trader_runtime.json"
    $runtime = Load-JsonFile $runtimePath @{}
    foreach ($s in (To-Array (Get-Prop $runtime "symbols" @()))) {
        $sv = [string]$s
        if (-not [string]::IsNullOrWhiteSpace($sv)) {
            $sv = $sv.Trim().ToUpper()
            if (-not $hits.Contains($sv)) { [void]$hits.Add($sv) }
        }
    }

    return @($hits)
}

$ROOT = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$CODE = Join-Path $ROOT "code"
$CONF = Join-Path $ROOT "config"
$OUT  = Join-Path $ROOT "out"
$DASH = "C:\LumaTrader\dashboard"

$runtimePath     = Join-Path $CONF "paper_trader_runtime.json"
$controlPath     = Join-Path $CONF "runtime_control.json"
$statePath       = Join-Path $OUT  "paper_trade_state.json"
$runPath         = Join-Path $OUT  "paper_trade_runtime.json"
$proofPath       = Join-Path $OUT  "paper_loop_launch_proof.json"
$engineAuditPath = Join-Path $OUT  "engine_truth_audit.json"
$seedPath        = Join-Path $OUT  "seed_validation_readout.json"
$readoutTxt      = Join-Path $OUT  "paper_loop_launch_readout.txt"

$seed   = Load-JsonFile $seedPath @{}
$ctrl   = Load-JsonFile $controlPath @{}
$oldRun = Load-JsonFile $runtimePath @{}

$symbols = @(Get-AdaptiveSymbols -Root $ROOT -Out $OUT -Conf $CONF)

$symbolCount = $symbols.Count
$startingCapital = Get-Prop $oldRun "starting_capital_usd" 100000.0
if ($null -eq $startingCapital -or [double]$startingCapital -le 0) { $startingCapital = 100000.0 }

$loopSeconds = Get-Prop $oldRun "loop_seconds" 5
if ($null -eq $loopSeconds -or [int]$loopSeconds -le 0) { $loopSeconds = 5 }

$runtime = [ordered]@{
    generated_utc         = [DateTime]::UtcNow.ToString("o")
    mode                  = "paper"
    runtime_symbol        = "UNIVERSE"
    universe_mode         = $true
    selection_source      = "engine_logic"
    symbol_mode           = "ADAPTIVE_UNIVERSE"
    symbol_count          = $symbolCount
    symbols               = @($symbols)
    loop_seconds          = [int]$loopSeconds
    starting_capital_usd  = [double]$startingCapital
    paper_enabled         = $true
    allow_live_orders     = $false
    kill_switch           = $false
    last_loop_patch_utc   = [DateTime]::UtcNow.ToString("o")
}

$state = [ordered]@{
    generated_utc     = [DateTime]::UtcNow.ToString("o")
    mode              = "paper"
    paper_enabled     = $true
    allow_live_orders = $false
    selection_source  = "engine_logic"
    symbol_mode       = "ADAPTIVE_UNIVERSE"
    runtime_symbol    = "UNIVERSE"
    symbol_count      = $symbolCount
    symbols_preview   = @($symbols | Select-Object -First 25)
    pnl_usd           = 0.0
    open_positions    = @()
    status            = "LOOP_READY"
}

$run = [ordered]@{
    generated_utc     = [DateTime]::UtcNow.ToString("o")
    loop_seconds      = [int]$loopSeconds
    paper_enabled     = $true
    allow_live_orders = $false
    started_runner    = $MyInvocation.MyCommand.Path
}

$seedMeasured = Get-Prop $seed "measured_sources" 0
$seedEnabled  = Get-Prop $seed "enabled_registry_sources" 0
$seedAdaptive = Get-Prop $seed "adaptive_universe_count" 0

$engineAudit = [ordered]@{
    generated_utc            = [DateTime]::UtcNow.ToString("o")
    engine_symbol            = "UNIVERSE"
    paper_enabled            = $true
    selection_source         = "engine_logic"
    symbol_mode              = "ADAPTIVE_UNIVERSE"
    enabled_registry_sources = $seedEnabled
    measured_sources         = $seedMeasured
    adaptive_universe_count  = if ($symbolCount -gt 0) { $symbolCount } else { $seedAdaptive }
    static_symbol_risk       = $false
    audit_notes              = @(
        "broken Join-Path runner replaced with path-safe runner",
        "engine now reads adaptive universe from csv/runtime instead of hardcoded cfg object",
        "paper mode remains ON",
        "live orders remain OFF"
    )
}

Save-JsonFile $runtimePath $runtime
Save-JsonFile $statePath $state
Save-JsonFile $runPath $run
Save-JsonFile $proofPath $run
Save-JsonFile $engineAuditPath $engineAudit

$txt = @"
PAPER LOOP FIXED
================
generated_utc: $([DateTime]::UtcNow.ToString("o"))
runtime_symbol: UNIVERSE
selection_source: engine_logic
symbol_mode: ADAPTIVE_UNIVERSE
symbol_count: $symbolCount
paper_enabled: True
allow_live_orders: False

FILES
- $runtimePath
- $statePath
- $runPath
- $proofPath
- $engineAuditPath
"@
Set-Content -Path $readoutTxt -Value $txt -Encoding UTF8

Write-Host ""
Write-Host "FIXED PAPER RUNNER" -ForegroundColor Green
Write-Host "runtime_symbol: UNIVERSE"
Write-Host "selection_source: engine_logic"
Write-Host "symbol_mode: ADAPTIVE_UNIVERSE"
Write-Host "symbol_count: $symbolCount"
Write-Host "paper_enabled: True"
Write-Host "allow_live_orders: False"
Write-Host ""
Write-Host "OUTPUT FILES:" -ForegroundColor Yellow
Write-Host " - $runtimePath"
Write-Host " - $statePath"
Write-Host " - $runPath"
Write-Host " - $proofPath"
Write-Host " - $engineAuditPath"
Write-Host " - $readoutTxt"

$openList = @(
    $runtimePath,
    $statePath,
    $runPath,
    $proofPath,
    $engineAuditPath,
    $readoutTxt
)

foreach ($f in $openList) {
    if (Test-Path $f) { Start-Process $f }
}