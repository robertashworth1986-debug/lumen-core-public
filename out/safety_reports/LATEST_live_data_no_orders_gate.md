# LumenCore Live-Data No-Orders Gate

- Generated UTC: `2026-06-16T01:11:30.235126+00:00`
- Stage: `live-data-no-orders`
- Stage status: `PASS_READ_ONLY`
- Order permission: `False`
- Reason: `blocked_by_live_data_no_orders_stage`
- Runtime file: `C:\LumenCore_GitHub\lumen-core-public\config\runtime_control.json`
- Runtime SHA-256: `11edba892b1fdad052b0ff8664c383148fffc0b5d8df4349661eef041607c396`
- Control flags SHA-256: `ca3e7572632c96d0ba57d6d9831ee59d00abb8639d21a23ac020006e1c777cbc`

## Blockers

- None for this stage.

## Warnings

- `live_order_config_detected_but_stage_blocks_orders`

## Runtime View, No Secrets

```json
{
  "allow_live_orders": false,
  "kill_switch": false,
  "max_daily_loss_usd": 65.0,
  "max_notional_per_trade_usd": 70.0,
  "max_open_positions": 2,
  "max_portfolio_heat": 0.45,
  "max_position_usd": 850.0,
  "mode": "paper",
  "paper_enabled": true
}
```

## Control Flags View, No Secrets

```json
{
  "deadman_timeout_seconds": 30,
  "default_order_type": "market",
  "default_pair": "XBTUSD",
  "kill_switch": false,
  "live_enabled": true,
  "max_daily_loss_usd": 20.0,
  "max_notional_per_trade_usd": 50.0,
  "max_open_positions": 30,
  "require_controller": true,
  "require_validate_pass": true,
  "runtime_mode": "live"
}
```

## Env Names Present, No Values

```json
{
  "ALPACA_API_KEY": true,
  "ALPACA_API_SECRET": true,
  "ALPACA_SECRET_KEY": false,
  "ALPHAVANTAGE_API_KEY": true,
  "BINANCE_API_KEY": false,
  "BINANCE_API_SECRET": false,
  "COINBASE_API_KEY": false,
  "COINBASE_API_SECRET": false,
  "EIA_API_KEY": true,
  "FRED_API_KEY": true,
  "KRAKEN_API_KEY": true,
  "KRAKEN_API_SECRET": true,
  "OPENAI_API_KEY": true
}
```