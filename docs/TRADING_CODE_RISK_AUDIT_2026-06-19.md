# Trading Code Risk Audit

Generated UTC: 2026-06-20T01:04:00.755707+00:00

Posture: BLOCK_LEGACY_LIVE

## Secret Handling

Scanner intentionally avoids env/key files and reports only source/config risk signals, never credential values.

## Best Current Safe Spine

- code/kraken_execution.py
- code/execution/live_runtime_guard.py
- code/execution/risk_kernel.py
- code/execution/order_router.py
- code/ops/_copilot_watch.py
- code/ops/cancel_open_orders.py
- code/ops/BUILD_TRADING_STACK_SAFETY_AUDIT.py

## Blockers

- code/kraken_auto_withdraw_btc.py: withdraw/liquidation path lacks explicit execute confirmation
- code/ops/LIQUIDATE_ALL_TO_USD.py: direct order path lacks validate/runtime/human gate
- code/micro_position_kraken_bot.py: direct order path lacks validate/runtime/human gate
- code/kraken_swing_hunter.py: direct order path lacks validate/runtime/human gate
- code/ops/LEARN_FROM_TRADE_HISTORY.py: validate=false path lacks a clear human approval gate

## Risk Files

### code/kraken_auto_withdraw_btc.py

- classification: critical_legacy_quarantine
- risk_score: 21
- signals: direct_key_loader, withdrawal_path
- protections: none
- required action: withdraw/liquidation path lacks explicit execute confirmation

### code/kraken_execution.py

- classification: guarded_review
- risk_score: 19
- signals: direct_key_loader, kraken_add_order
- protections: human_approval, runtime_gate, validate_only
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/ops/LIQUIDATE_ALL_TO_USD.py

- classification: high_review
- risk_score: 18
- signals: kraken_add_order, liquidation_path
- protections: dry_run, execute_confirm
- required action: direct order path lacks validate/runtime/human gate

### code/luma_experience_gateway.py

- classification: guarded_review
- risk_score: 16
- signals: direct_key_loader, kraken_add_order, validate_false
- protections: dry_run, execute_confirm, human_approval, runtime_gate, validate_only
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/run_universal_meta_orchestrator.py

- classification: guarded_review
- risk_score: 16
- signals: direct_key_loader, kraken_add_order
- protections: runtime_gate
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/micro_position_kraken_bot.py

- classification: high_review
- risk_score: 15
- signals: direct_key_loader, kraken_add_order
- protections: none
- required action: direct order path lacks validate/runtime/human gate

### code/DISCOVER_AND_ROUTE_ALL_LIVE_KEYS.py

- classification: guarded_review
- risk_score: 12
- signals: direct_key_loader, kill_switch_off_write, live_arm_write
- protections: runtime_gate
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/go_live_paper_trader.py

- classification: guarded_review
- risk_score: 12
- signals: kill_switch_off_write, live_arm_write
- protections: execute_confirm, runtime_gate
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/execution/execution_orchestrator.py

- classification: guarded_review
- risk_score: 11
- signals: direct_key_loader, kraken_add_order, live_arm_write
- protections: runtime_gate
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/kraken_swing_hunter.py

- classification: high_review
- risk_score: 11
- signals: direct_key_loader, kraken_add_order
- protections: none
- required action: direct order path lacks validate/runtime/human gate

### code/FULL_TRUTH_ORCHESTRATOR.py

- classification: guarded_review
- risk_score: 10
- signals: kill_switch_off_write, live_arm_write
- protections: human_approval, runtime_gate
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/REBUILD_FULL_ADAPTIVE_LIVE_STACK.py

- classification: guarded_review
- risk_score: 10
- signals: direct_key_loader, kill_switch_off_write, live_arm_write
- protections: runtime_gate
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/REBUILD_LIVE_AUDIT_AND_PAPER_ENGINE.py

- classification: guarded_review
- risk_score: 10
- signals: direct_key_loader, kill_switch_off_write
- protections: runtime_gate
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/UPGRADE_INSTITUTIONAL_CONTROL_PLANE.py

- classification: guarded_review
- risk_score: 10
- signals: direct_key_loader, kill_switch_off_write
- protections: runtime_gate
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/build_vps_growth_proof.py

- classification: guarded_review
- risk_score: 10
- signals: direct_key_loader
- protections: validate_only
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/linkedin_oauth.py

- classification: guarded_review
- risk_score: 10
- signals: direct_key_loader
- protections: none
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/multi_exchange_paper_ticker.py

- classification: guarded_review
- risk_score: 10
- signals: direct_key_loader
- protections: runtime_gate, validate_only
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/ops/BUILD_LINKEDIN_APP_LAUNCHPACK.py

- classification: guarded_review
- risk_score: 10
- signals: direct_key_loader
- protections: none
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/execution/live_executor.py

- classification: guarded_review
- risk_score: 8
- signals: cancel_all_orders, direct_key_loader, kraken_add_order
- protections: dry_run, execute_confirm, human_approval, runtime_gate, validate_only
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/linkedin_router.py

- classification: guarded_review
- risk_score: 8
- signals: direct_key_loader
- protections: none
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/ops/cancel_open_orders.py

- classification: guarded_review
- risk_score: 8
- signals: cancel_all_orders, direct_key_loader
- protections: dry_run, execute_confirm
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/auto_ticket_producer.py

- classification: guarded_review
- risk_score: 7
- signals: kraken_add_order, validate_false
- protections: dry_run, execute_confirm, human_approval, validate_only
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/ROUTE_AND_BIND_ALL_LIVE_KEYS.py

- classification: guarded_review
- risk_score: 6
- signals: direct_key_loader, kill_switch_off_write
- protections: runtime_gate
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/binance_get_deposit_address.py

- classification: guarded_review
- risk_score: 6
- signals: direct_key_loader
- protections: none
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/email_opportunity_finder.py

- classification: guarded_review
- risk_score: 6
- signals: direct_key_loader
- protections: none
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/email_response_watcher.py

- classification: guarded_review
- risk_score: 6
- signals: direct_key_loader
- protections: none
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/email_resume_dispatcher.py

- classification: guarded_review
- risk_score: 6
- signals: direct_key_loader
- protections: dry_run
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/real_data_fair_benchmark.py

- classification: guarded_review
- risk_score: 6
- signals: direct_key_loader
- protections: none
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/BUILD_ADAPTIVE_UNIVERSE_FROM_LIVE_KEYS.py

- classification: guarded_review
- risk_score: 4
- signals: live_arm_write
- protections: runtime_gate
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/CANONICAL_GOV_DATA_COLLECTOR.py

- classification: guarded_review
- risk_score: 4
- signals: direct_key_loader
- protections: none
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/FIX_PROVIDER_REGISTRY_HARDRESET.py

- classification: guarded_review
- risk_score: 4
- signals: direct_key_loader
- protections: runtime_gate
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/REBUILD_ENGINE_SOURCE_LOGIC.py

- classification: guarded_review
- risk_score: 4
- signals: direct_key_loader, kill_switch_off_write
- protections: runtime_gate
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/application_context_resolver.py

- classification: guarded_review
- risk_score: 4
- signals: direct_key_loader
- protections: runtime_gate
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/beast_mode.py

- classification: guarded_review
- risk_score: 4
- signals: live_arm_write
- protections: dry_run, execute_confirm, runtime_gate
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/execution/alpaca_paper_executor.py

- classification: guarded_review
- risk_score: 4
- signals: direct_key_loader
- protections: dry_run, runtime_gate
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/execution/alpha_harmonic_burst_lab.py

- classification: guarded_review
- risk_score: 4
- signals: direct_key_loader
- protections: none
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/execution/api_key_purpose_registry.py

- classification: guarded_review
- risk_score: 4
- signals: direct_key_loader
- protections: none
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/execution/build_stage_wallboard.py

- classification: guarded_review
- risk_score: 4
- signals: direct_key_loader
- protections: none
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/execution/rebuild_engine_logic.py

- classification: guarded_review
- risk_score: 4
- signals: direct_key_loader, kill_switch_off_write
- protections: runtime_gate
- required action: risk-bearing path has at least one guard, but still needs review before live use

### code/fetch_live_data_and_run_suite.py

- classification: guarded_review
- risk_score: 4
- signals: direct_key_loader
- protections: none
- required action: risk-bearing path has at least one guard, but still needs review before live use

## Promotion Rule

Only route live-capable work through the safe spine after paper evidence, fresh heartbeats, empty blockers, and separate human action-time approval. Legacy direct-order, withdrawal, and liquidation scripts stay quarantined until rewritten behind these guards.
