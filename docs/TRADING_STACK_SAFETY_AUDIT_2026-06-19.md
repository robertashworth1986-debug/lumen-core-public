# Trading Stack Safety Audit

Generated UTC: 2026-06-20T00:46:43.880523+00:00

Posture: BLOCK_LIVE

## Runtime Gates

- mode: paper
- allow_live_orders: False
- paper_enabled: True
- kill_switch: False
- max_notional_per_trade_usd: 70.0
- max_daily_loss_usd: 65.0
- max_open_positions: 5

## Evidence Readout

- executor heartbeat age min: 13594.905
- executor status/reason: running / scan_cycle_start
- symbol intel stale: True
- autofire heartbeat age min: 13594.605
- autofire eligible/approved buy: 0 / 0
- growth mode: SAFE_DRY_RUN
- growth guard reasons: ['executor_heartbeat_stale', 'engine_heartbeat_stale']
- actionable/emitted/auto-fired: 0 / 0 / 0
- portfolio estimate USD: 101.527534
- operator pending tickets: 12

## Live Promotion Blockers

- executor heartbeat stale or missing: 13594.905
- autofire heartbeat stale or missing: 13594.605
- growth controller heartbeat check is not ok
- no actionable candidates in latest growth controller run

## Warnings

- kill_switch is false; acceptable only while allow_live_orders=false and runtime mode=paper
- auto_convert_collateral is true; keep disabled for unattended paper governance
- operator queue has 12 pending review tickets

## Promotion Rule

Live execution remains blocked until blockers are empty, paper/live heartbeats are fresh, actionable candidates exist, auto-fire count is zero unless explicitly approved, and a human operator signs a separate action-time approval.
