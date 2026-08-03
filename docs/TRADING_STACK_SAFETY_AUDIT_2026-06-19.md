# Trading Stack Safety Audit

Generated UTC: 2026-07-19T20:06:40.443009+00:00

Posture: BLOCK_LIVE

Execution authorized: False

Claim status: NOT_VALIDATED_FOR_ALPHA_OR_LIVE_EXECUTION

## Claim Boundary

Ledger presence and local consistency are necessary controls, not proof of alpha, independent validation, or live readiness.

## Secret Handling

The audit reads control booleans, file metadata, and non-secret ledger fields only. It never emits credentials, order identifiers, fill identifiers, or live-arm contents.

## Runtime Gates

- mode: paper
- allow_live_orders: False
- paper_enabled: True
- kill_switch: False
- max_notional_per_trade_usd: 70.0
- max_daily_loss_usd: 65.0
- max_open_positions: 5

## Evidence Readout

- executor heartbeat age min: 56514.848
- executor status/reason: running / scan_cycle_start
- symbol intel stale: True
- autofire heartbeat age min: 56514.548
- autofire eligible/approved buy: 0 / 0
- growth mode: SAFE_DRY_RUN
- growth guard reasons: ['executor_heartbeat_stale', 'engine_heartbeat_stale']
- actionable/emitted/auto-fired: 0 / 0 / 0
- portfolio estimate USD: 101.527534
- operator pending tickets: 12

## Authority Reconciliation

- canonical runtime: config/runtime_control.json mode=paper allow_live_orders=False paper_enabled=True
- legacy runtime: code/execution/runtime_control.json present=True mode=live allow_live_orders=True
- account runtimes: 2
- nonempty live-arm markers: 2
- paper state writer count: 3
- paper state writers: code/BUILD_AUDIT_GRADE_DERIVATION_PACK.py, code/alpaca_paper_loop_builder.py, code/execution/alpaca_paper_executor.py

## Paper Evidence Integrity

- local paper ledger rows/fills/unique/duplicates: 1743 / 1743 / 100 / 1643
- real-API ledger rows/fills/unique/duplicates: 122349 / 90562 / 422 / 90140
- real-API snapshot rows/max trade_count: 31787 / 119
- real-API ledger external target: True
- real-API ledger changed during scan: False

## Live Promotion Blockers

- legacy runtime contradicts canonical paper authority: code/execution/runtime_control.json
- control flag contradicts canonical paper authority: control_flags.json
- control flag contradicts canonical paper authority: out/control_flags.json
- multi-account policy permits live execution: config/multi_account_policy.json
- stale live-arm marker requires removal or reconciliation: config/live_arm.confirm
- stale live-arm marker requires removal or reconciliation: config/multi_live_arm.confirm
- executor heartbeat stale or missing: 56514.848
- autofire heartbeat stale or missing: 56514.548
- growth controller heartbeat check is not ok
- paper state has 3 write-capable implementations
- paper evidence ledger has duplicate fill identities: out/paper_trade_ledger.jsonl
- paper evidence ledger has duplicate fill identities: out/paper_trade_real_api_ledger.jsonl
- real-API ledger unique fill count disagrees with snapshot trade_count
- external paper ledger target is labeled paused but has recent writes

## Warnings

- kill_switch is false; acceptable only while allow_live_orders=false and runtime mode=paper
- auto_convert_collateral is true; keep disabled for unattended paper governance
- operator queue has 12 pending review tickets
- no actionable candidates in latest growth controller run; this is a research result, not a safety failure
- real-API paper ledger is an external symlink; custody depends on the external target

## Promotion Rule

Live execution remains blocked until authority conflicts and duplicate evidence are removed, one canonical state writer remains, paper/live heartbeats are fresh, full order/fill reconciliation passes, and a human operator grants a separate short-lived action-time approval. This audit never authorizes execution.
