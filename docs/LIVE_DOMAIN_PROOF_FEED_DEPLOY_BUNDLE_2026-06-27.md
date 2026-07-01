# Live Domain Proof Feed Deploy Bundle

Generated UTC: `2026-07-01T15:01:03Z`
Bundle root: `C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260701T150103Z`
Archive: `C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260701T150103Z.tgz`

## Decision

The feed-only deploy bundle is ready. It can publish proof JSON feeds to the public domain paths without restarting trading, gateway, or dashboard services.

## Safety Gates

- Required ready: `12/12`
- Feed-only deploy ready: `true`
- Broad stack deploy allowed: `false`
- Service restart required: `false`
- Publishes config or secrets: `false`
- Field-validation claim allowed: `false`
- Real-dollar savings claim allowed: `false`

## Feed Table

| Feed | Required | Source | Copied | SHA-256 |
|---|---:|---|---:|---|
| `champion_metric_gauntlet` | `true` | `dashboard/data/champion_metric_gauntlet.json` | `2` | `797609dce08f` |
| `locked_source_baseline_replay_sweep` | `true` | `dashboard/data/locked_source_baseline_replay_sweep.json` | `2` | `123883dabde2` |
| `kuramoto_holdout_expansion` | `true` | `dashboard/data/kuramoto_holdout_expansion.json` | `2` | `1645f3d74f7e` |
| `geometry_champion_of_champions` | `true` | `dashboard/data/geometry_champion_of_champions.json` | `2` | `b7e2aa3f77e1` |
| `field_money_truth_sweep` | `true` | `dashboard/data/field_money_truth_sweep.json` | `2` | `88f8242d07ed` |
| `live_proof_value_meter` | `true` | `dashboard/data/live_proof_value_meter.json` | `2` | `07c416189aba` |
| `field_validated_dollar_claim_ladder` | `true` | `dashboard/data/field_validated_dollar_claim_ladder.json` | `2` | `f29d59bbcc97` |
| `dollar_claim_gate` | `true` | `dashboard/data/dollar_claim_gate.json` | `2` | `9e64ad63466e` |
| `field_validation_control_room` | `true` | `dashboard/data/field_validation_control_room.json` | `2` | `bf7fae7aef04` |
| `field_validation_outreach_board` | `true` | `dashboard/data/field_validation_outreach_board.json` | `2` | `46087b9ea514` |
| `proof_to_pilot_control_room` | `true` | `dashboard/data/proof_to_pilot_control_room.json` | `2` | `20fdcc50fae6` |
| `champion_sample_expansion_and_economic_bridge` | `true` | `dashboard/data/champion_sample_expansion_and_economic_bridge.json` | `2` | `f0262523045d` |
| `geometry_asset_wiring_board` | `false` | `dashboard/data/geometry_asset_wiring_board.json` | `2` | `20be445c8852` |
| `luma_context_dashboard_parity_audit` | `false` | `dashboard/data/luma_context_dashboard_parity_audit.json` | `2` | `757fe628616e` |
| `live_domain_deployment_feed` | `false` | `dashboard/data/live_domain_deployment_feed.json` | `2` | `817aea66ae66` |
| `live_domain_consolidation_audit` | `false` | `dashboard/data/live_domain_consolidation_audit.json` | `2` | `63cfd938154e` |
| `proof_to_revenue_engine` | `false` | `dashboard/data/proof_to_revenue_engine.json` | `2` | `b611e887434a` |
| `champion_stress_test_matrix` | `false` | `dashboard/data/champion_stress_test_matrix.json` | `2` | `4f800ce00512` |
| `champion_metric_battery` | `false` | `dashboard/data/champion_metric_battery.json` | `2` | `ded3057b2266` |
| `champion_expanded_metric_rollup` | `false` | `dashboard/data/champion_expanded_metric_rollup.json` | `2` | `7096797dca9a` |
| `first_buyer_target_board` | `false` | `dashboard/data/first_buyer_target_board.json` | `2` | `eab5d0cc7e85` |
| `paid_pilot_outreach_queue` | `false` | `dashboard/data/paid_pilot_outreach_queue.json` | `2` | `8cea42048365` |
| `luma_operator_context` | `false` | `dashboard/data/luma_operator_context.json` | `2` | `1f2a0d355449` |
| `champion_phase_proxy_diagnostics` | `false` | `dashboard/data/champion_phase_proxy_diagnostics.json` | `2` | `259ee745a7d0` |
| `safe_key_provider_ping` | `false` | `dashboard/data/safe_key_provider_ping.json` | `2` | `97093efea69a` |
| `live_source_measurement_maximizer` | `false` | `dashboard/data/live_source_measurement_maximizer.json` | `2` | `40cbb1b03299` |
| `geometry_live_wiring_matrix` | `false` | `dashboard/data/geometry_live_wiring_matrix.json` | `2` | `b559f3668cda` |
| `geometry_live_breadth_proof_queue` | `false` | `dashboard/data/geometry_live_breadth_proof_queue.json` | `2` | `088820432c98` |
| `branching_live_breadth_replay` | `false` | `dashboard/data/branching_live_breadth_replay.json` | `2` | `3abdf878a529` |
| `rolling_champion_gate` | `false` | `dashboard/data/rolling_champion_gate.json` | `2` | `755aaab1a172` |
| `top_geometry_live_replay_results` | `false` | `dashboard/data/top_geometry_live_replay_results.json` | `2` | `1b4c4644ad06` |

## Commands

- Dry run: `.\deploy\PUSH_PROOF_FEEDS_TO_VPS.ps1 -BundleRoot "C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260701T150103Z" -DryRun`
- Deploy feeds: `.\deploy\PUSH_PROOF_FEEDS_TO_VPS.ps1 -BundleRoot "C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260701T150103Z"`
- Verify domain hashes: `python .\code\ops\BUILD_LIVE_DOMAIN_DEPLOYMENT_FEED.py --timeout 8`

## Remote Web Roots Tried By Deploy Script

- `/opt/lumencore/dashboard`
- `/var/www/lumatrader`
- `/var/www/lumen-core`

## Boundary

Feed-only deploy bundle. It stages reviewer proof JSON for domain hash verification. It does not publish secrets, restart execution services, prove field validation, prove realized savings, set a fixed dollar value per frozen delta, or imply autonomous live trading permission. This is not field validation.

Bundle SHA-256: `1867147709589bddf893eeef3dc2ea1150f329bf9fd22c514571444707cc1e88`
Archive SHA-256: `f17a2d604b9cc07c6733fe5222db97a2492084f7d58f747b88b2707c7132432b`
