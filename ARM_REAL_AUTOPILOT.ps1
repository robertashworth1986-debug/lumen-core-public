param(
    [ValidateSet('dashboard', 'core', 'full')]
    [string]$StackGroup = 'core',

    [ValidateSet('investor', 'ops', 'full')]
    [string]$TabPreset = 'investor',

    [int]$ScanTopN = 2000,
    [int]$UniverseSampleSize = 24,
    [double]$ReserveUsd = 0.25,
    [double]$CachedBalanceTradingCapUsd = 12.0,
    [double]$OrderNotionalPct = 0.28,
    [double]$MaxDeployableCapitalPct = 0.72,
    [double]$BaseRiskFraction = 0.0065,
    [double]$PyramidReinvestmentMultiplier = 1.9,
    [double]$MaxNotionalPerTradeUsd = 0.0,
    [double]$AdaptiveMinWinRatePct = 22.0,
    [int]$AdaptiveRecentTrades = 4,
    [double]$AdaptiveMinAvgNetPnlUsd = -0.5,

    [switch]$UseBestMultiPreference,
    [switch]$DisableCachedBalanceFallback,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$runtimePath = Join-Path $root 'config\runtime_control.json'
$executionStatusPath = Join-Path $root 'execution_status.json'
$controlFlagsPath = Join-Path $root 'control_flags.json'
$startScript = Join-Path $root 'START_COMMAND_CENTER.ps1'
$pairCachePath = Join-Path $root 'out\execution\kraken_asset_pairs_cache.json'
$heartbeatPath = Join-Path $root 'out\execution\live_executor_heartbeat.json'

if (-not (Test-Path $runtimePath)) {
    throw "Runtime config not found at $runtimePath"
}
if (-not (Test-Path $startScript)) {
    throw "Command center launcher not found at $startScript"
}

$applyJsonProperty = {
    param(
        [object]$Object,
        [string]$Name,
        $Value
    )

    if ($Object.PSObject.Properties.Name -contains $Name) {
        $Object.$Name = $Value
    } else {
        $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $Value
    }
}

$runtime = Get-Content $runtimePath -Raw | ConvertFrom-Json
if (-not $runtime) {
    throw "Unable to parse runtime config at $runtimePath"
}

$scanCap = [Math]::Min([Math]::Max([int]$ScanTopN, 200), 5000)
$sampleSize = [Math]::Min([Math]::Max([int]$UniverseSampleSize, 8), 256)
$reserveUsdEffective = [Math]::Min([Math]::Max([double]$ReserveUsd, 0.0), 5.0)
$cachedCap = [Math]::Max([double]$CachedBalanceTradingCapUsd, 1.0)
$orderNotionalPctEffective = [Math]::Min([Math]::Max([double]$OrderNotionalPct, 0.05), 0.95)
$deployableCapitalPctEffective = [Math]::Min([Math]::Max([double]$MaxDeployableCapitalPct, 0.10), 0.95)
$baseRiskFractionEffective = [Math]::Min([Math]::Max([double]$BaseRiskFraction, 0.0005), 0.03)
$pyramidMultiplierEffective = [Math]::Min([Math]::Max([double]$PyramidReinvestmentMultiplier, 0.75), 3.0)
$maxNotionalPerTradeUsdEffective = [Math]::Max([double]$MaxNotionalPerTradeUsd, 0.0)
$adaptiveMinWinRatePctEffective = [Math]::Min([Math]::Max([double]$AdaptiveMinWinRatePct, 0.0), 100.0)
$adaptiveRecentTradesEffective = [Math]::Min([Math]::Max([int]$AdaptiveRecentTrades, 1), 50)
$adaptiveMinAvgNetPnlUsdEffective = [Math]::Min([Math]::Max([double]$AdaptiveMinAvgNetPnlUsd, -10.0), 10.0)
$allowCached = -not $DisableCachedBalanceFallback

& $applyJsonProperty -Object $runtime -Name 'mode' -Value 'live'
& $applyJsonProperty -Object $runtime -Name 'allow_live_orders' -Value $true
& $applyJsonProperty -Object $runtime -Name 'paper_enabled' -Value $false
& $applyJsonProperty -Object $runtime -Name 'kill_switch' -Value $false
& $applyJsonProperty -Object $runtime -Name 'symbol' -Value 'UNIVERSE'
& $applyJsonProperty -Object $runtime -Name 'scan_top_n' -Value $scanCap
& $applyJsonProperty -Object $runtime -Name 'universe_spread_scan_enabled' -Value $true
& $applyJsonProperty -Object $runtime -Name 'universe_sample_size' -Value $sampleSize
& $applyJsonProperty -Object $runtime -Name 'low_balance_sample_trigger_usd' -Value 20.0
& $applyJsonProperty -Object $runtime -Name 'low_balance_sample_size' -Value 180
& $applyJsonProperty -Object $runtime -Name 'low_balance_ticker_scan_cap' -Value 96
& $applyJsonProperty -Object $runtime -Name 'reserve_usd' -Value ([double]$reserveUsdEffective)
& $applyJsonProperty -Object $runtime -Name 'allow_best_multi_preference' -Value ([bool]$UseBestMultiPreference)
& $applyJsonProperty -Object $runtime -Name 'live_reselection_enabled' -Value $true
& $applyJsonProperty -Object $runtime -Name 'live_reselection_interval_sec' -Value 300
& $applyJsonProperty -Object $runtime -Name 'symbol_universe_files' -Value @(
    'out/adaptive_universe.json',
    'adaptive_universe.json'
)
& $applyJsonProperty -Object $runtime -Name 'symbol_universe_extra' -Value @(
    'BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'DOT', 'LINK', 'LTC'
)
& $applyJsonProperty -Object $runtime -Name 'allow_cached_balance_trading' -Value ([bool]$allowCached)
& $applyJsonProperty -Object $runtime -Name 'cached_balance_trading_cap_usd' -Value ([double]$cachedCap)
& $applyJsonProperty -Object $runtime -Name 'profit_reinvestment_enabled' -Value $true
& $applyJsonProperty -Object $runtime -Name 'order_notional_pct' -Value ([double]$orderNotionalPctEffective)
& $applyJsonProperty -Object $runtime -Name 'max_deployable_capital_pct' -Value ([double]$deployableCapitalPctEffective)
& $applyJsonProperty -Object $runtime -Name 'base_risk_fraction' -Value ([double]$baseRiskFractionEffective)
& $applyJsonProperty -Object $runtime -Name 'max_risk_fraction_floor' -Value 0.002
& $applyJsonProperty -Object $runtime -Name 'max_risk_fraction_ceiling' -Value 0.018
& $applyJsonProperty -Object $runtime -Name 'pyramid_reinvestment_multiplier' -Value ([double]$pyramidMultiplierEffective)
& $applyJsonProperty -Object $runtime -Name 'max_drawdown_pct' -Value 10.0
& $applyJsonProperty -Object $runtime -Name 'compounding_growth_sensitivity' -Value 0.8
& $applyJsonProperty -Object $runtime -Name 'compounding_min_notional_usd' -Value 1.0
& $applyJsonProperty -Object $runtime -Name 'compounding_max_notional_usd' -Value 250.0
& $applyJsonProperty -Object $runtime -Name 'max_notional_per_trade_usd' -Value ([double]$maxNotionalPerTradeUsdEffective)
& $applyJsonProperty -Object $runtime -Name 'adaptive_entry_gate_enabled' -Value $true
& $applyJsonProperty -Object $runtime -Name 'adaptive_entry_gate_starvation_sec' -Value 45.0
& $applyJsonProperty -Object $runtime -Name 'adaptive_entry_gate_adjust_cooldown_sec' -Value 20.0
& $applyJsonProperty -Object $runtime -Name 'adaptive_entry_gate_relax_step_score' -Value 0.01
& $applyJsonProperty -Object $runtime -Name 'adaptive_entry_gate_recover_step_score' -Value 0.005
& $applyJsonProperty -Object $runtime -Name 'adaptive_entry_gate_relax_max_offset' -Value 0.12
& $applyJsonProperty -Object $runtime -Name 'adaptive_entry_gate_recent_trades' -Value ([int]$adaptiveRecentTradesEffective)
& $applyJsonProperty -Object $runtime -Name 'adaptive_entry_gate_min_win_rate_pct' -Value ([double]$adaptiveMinWinRatePctEffective)
& $applyJsonProperty -Object $runtime -Name 'adaptive_entry_gate_min_avg_net_pnl_usd' -Value ([double]$adaptiveMinAvgNetPnlUsdEffective)
& $applyJsonProperty -Object $runtime -Name 'generated_utc' -Value ((Get-Date).ToUniversalTime().ToString('o'))

$runtime | ConvertTo-Json -Depth 64 | Set-Content -Path $runtimePath -Encoding UTF8

$executionStatus = [PSCustomObject]@{}
if (Test-Path $executionStatusPath) {
    try {
        $executionStatus = Get-Content $executionStatusPath -Raw | ConvertFrom-Json
    } catch {
        $executionStatus = [PSCustomObject]@{}
    }
}
& $applyJsonProperty -Object $executionStatus -Name 'generated_utc' -Value ((Get-Date).ToUniversalTime().ToString('o'))
& $applyJsonProperty -Object $executionStatus -Name 'execution_mode' -Value 'live'
& $applyJsonProperty -Object $executionStatus -Name 'kill_switch' -Value $false
& $applyJsonProperty -Object $executionStatus -Name 'live_arm' -Value 'ON'
& $applyJsonProperty -Object $executionStatus -Name 'note' -Value 'Live autopilot armed. Autonomous live order submission is enabled.'
$executionStatus | ConvertTo-Json -Depth 32 | Set-Content -Path $executionStatusPath -Encoding UTF8

$controlFlags = [PSCustomObject]@{}
if (Test-Path $controlFlagsPath) {
    try {
        $controlFlags = Get-Content $controlFlagsPath -Raw | ConvertFrom-Json
    } catch {
        $controlFlags = [PSCustomObject]@{}
    }
}
& $applyJsonProperty -Object $controlFlags -Name 'live_enabled' -Value $true
& $applyJsonProperty -Object $controlFlags -Name 'kill_switch' -Value $false
& $applyJsonProperty -Object $controlFlags -Name 'runtime_mode' -Value 'live'
$controlFlags | ConvertTo-Json -Depth 32 | Set-Content -Path $controlFlagsPath -Encoding UTF8

$pairCount = 0
if (Test-Path $pairCachePath) {
    try {
        $pairPayload = Get-Content $pairCachePath -Raw | ConvertFrom-Json
        if ($pairPayload -and $pairPayload.symbols) {
            $pairCount = @($pairPayload.symbols.PSObject.Properties.Name).Count
        }
    } catch {
        $pairCount = 0
    }
}

Write-Output "[AUTOPILOT] Runtime armed for live orders."
Write-Output "[AUTOPILOT] scan_top_n=$scanCap universe_sample_size=$sampleSize reserve_usd=$reserveUsdEffective allow_best_multi_preference=$([bool]$UseBestMultiPreference) allow_cached_balance_trading=$allowCached cached_balance_trading_cap_usd=$cachedCap"
Write-Output "[AUTOPILOT] compounding order_notional_pct=$orderNotionalPctEffective max_deployable_capital_pct=$deployableCapitalPctEffective base_risk_fraction=$baseRiskFractionEffective pyramid_reinvestment_multiplier=$pyramidMultiplierEffective max_notional_per_trade_usd=$maxNotionalPerTradeUsdEffective"
Write-Output "[AUTOPILOT] adaptive_gate recent_trades=$adaptiveRecentTradesEffective min_win_rate_pct=$adaptiveMinWinRatePctEffective min_avg_net_pnl_usd=$adaptiveMinAvgNetPnlUsdEffective"
Write-Output "[AUTOPILOT] kraken_cached_pairs=$pairCount"

& $startScript -StackGroup $StackGroup -TabPreset $TabPreset -Restart -NoBrowser:$NoBrowser

try {
    $headline = (Invoke-RestMethod 'http://127.0.0.1:8787/api/investor/brief').headline
    Write-Output "[AUTOPILOT] services_up=$($headline.services_up) supervisor_tick=$($headline.supervisor_tick)"
} catch {
    Write-Output '[AUTOPILOT] investor brief endpoint unavailable after restart'
}

if (Test-Path $heartbeatPath) {
    try {
        $hb = Get-Content $heartbeatPath -Raw | ConvertFrom-Json
        Write-Output "[AUTOPILOT] heartbeat status=$($hb.status) reason=$($hb.reason) symbol=$($hb.selected_symbol) universe_candidate_count=$($hb.universe_candidate_count)"
    } catch {
        Write-Output '[AUTOPILOT] live executor heartbeat unreadable'
    }
}
