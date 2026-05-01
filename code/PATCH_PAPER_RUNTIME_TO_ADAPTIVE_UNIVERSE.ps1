$ErrorActionPreference = "Stop"

$ROOT = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$CONF = Join-Path $ROOT "config"
$OUT  = Join-Path $ROOT "out"

$adaptiveUniversePath = Join-Path $OUT  "adaptive_universe.json"
$paperRuntimePath     = Join-Path $CONF "paper_trader_runtime.json"
$paperStatePath       = Join-Path $OUT  "paper_trade_state.json"
$paperRunPath         = Join-Path $OUT  "paper_trade_runtime.json"

if (!(Test-Path $adaptiveUniversePath)) {
    throw "Missing adaptive universe: $adaptiveUniversePath"
}

$u = Get-Content $adaptiveUniversePath -Raw | ConvertFrom-Json
$symbols = @()

if ($u -is [System.Array]) {
    $symbols = $u
}
elseif ($null -ne $u.symbols) {
    $symbols = $u.symbols
}
elseif ($null -ne $u.preview) {
    $symbols = $u.preview
}

$symbols = $symbols |
    ForEach-Object { "$_".Trim().ToUpper() } |
    Where-Object { $_ -match '^[A-Z0-9._-]{2,20}$' } |
    Sort-Object -Unique

if ($symbols.Count -lt 5) {
    throw "Adaptive universe too small after cleaning. Count=$($symbols.Count)"
}

$runtime = [ordered]@{
    generated_utc         = [DateTime]::UtcNow.ToString("o")
    runtime_symbol        = "UNIVERSE"
    selection_source      = "engine_logic"
    symbol_mode           = "ADAPTIVE_UNIVERSE"
    universe_mode         = $true
    paper_enabled         = $true
    allow_live_orders     = $false
    symbol_count          = $symbols.Count
    symbols               = $symbols
    loop_seconds          = 5
    starting_capital_usd  = 200000
    last_loop_patch_utc   = [DateTime]::UtcNow.ToString("o")
}
$runtime | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $paperRuntimePath

$state = [ordered]@{
    generated_utc        = [DateTime]::UtcNow.ToString("o")
    mode                 = "paper"
    paper_enabled        = $true
    allow_live_orders    = $false
    selection_source     = "engine_logic"
    symbol_mode          = "ADAPTIVE_UNIVERSE"
    runtime_symbol       = "UNIVERSE"
    symbol_count         = $symbols.Count
    symbols_preview      = @($symbols | Select-Object -First 25)
    pnl_usd              = 0.0
    open_positions       = @()
    status               = "LOOP_READY"
}
$state | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $paperStatePath

$run = [ordered]@{
    generated_utc      = [DateTime]::UtcNow.ToString("o")
    loop_seconds       = 5
    paper_enabled      = $true
    allow_live_orders  = $false
    selection_source   = "engine_logic"
    symbol_mode        = "ADAPTIVE_UNIVERSE"
    runtime_symbol     = "UNIVERSE"
    symbol_count       = $symbols.Count
    ready              = $true
}
$run | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $paperRunPath

Write-Host ""
Write-Host "Paper runtime patched to adaptive universe." -ForegroundColor Green
Write-Host "Symbol count: $($symbols.Count)" -ForegroundColor Cyan
Write-Host "Runtime file: $paperRuntimePath"
Write-Host "State file:   $paperStatePath"
Write-Host "Run file:     $paperRunPath"
