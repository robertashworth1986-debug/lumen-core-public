# Live Domain Proof Feed Deploy Bundle

Generated UTC: `2026-07-05T06:02:43Z`
Bundle root: `C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260705T060243Z`
Archive: `C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260705T060243Z.tgz`

## Decision

The feed-only deploy bundle is ready. It can publish proof JSON feeds to the public domain paths without restarting trading, gateway, or dashboard services.

## Safety Gates

- Required ready: `14/14`
- Feed-only deploy ready: `true`
- Broad stack deploy allowed: `false`
- Service restart required: `false`
- Publishes config or secrets: `false`
- Field-validation claim allowed: `false`
- Real-dollar savings claim allowed: `false`

## Feed Table

| Feed | Required | Source | Copied | SHA-256 |
|---|---:|---|---:|---|
| `champion_metric_gauntlet` | `true` | `dashboard/data/champion_metric_gauntlet.json` | `2` | `34ed58d49672` |
| `locked_source_baseline_replay_sweep` | `true` | `dashboard/data/locked_source_baseline_replay_sweep.json` | `2` | `fe82c1e6b5a6` |
| `kuramoto_holdout_expansion` | `true` | `dashboard/data/kuramoto_holdout_expansion.json` | `2` | `1645f3d74f7e` |
| `geometry_champion_of_champions` | `true` | `dashboard/data/geometry_champion_of_champions.json` | `2` | `1d1975246333` |
| `field_money_truth_sweep` | `true` | `dashboard/data/field_money_truth_sweep.json` | `2` | `88f8242d07ed` |
| `live_proof_value_meter` | `true` | `dashboard/data/live_proof_value_meter.json` | `2` | `07c416189aba` |
| `field_validated_dollar_claim_ladder` | `true` | `dashboard/data/field_validated_dollar_claim_ladder.json` | `2` | `f4ce0d6887d2` |
| `dollar_claim_gate` | `true` | `dashboard/data/dollar_claim_gate.json` | `2` | `9e64ad63466e` |
| `field_validation_control_room` | `true` | `dashboard/data/field_validation_control_room.json` | `2` | `bf7fae7aef04` |
| `field_validation_outreach_board` | `true` | `dashboard/data/field_validation_outreach_board.json` | `2` | `16ad10dc8d8a` |
| `proof_to_pilot_control_room` | `true` | `dashboard/data/proof_to_pilot_control_room.json` | `2` | `20fdcc50fae6` |
| `champion_sample_expansion_and_economic_bridge` | `true` | `dashboard/data/champion_sample_expansion_and_economic_bridge.json` | `2` | `09605006a1d8` |
| `champion_source_ablation` | `true` | `dashboard/data/champion_source_ablation.json` | `2` | `8f0b0c7e9333` |
| `grant_readiness_status` | `true` | `dashboard/data/grant_readiness_status.json` | `2` | `4ec386f09c7c` |
| `top5_live_proof_submission_board` | `false` | `dashboard/data/top5_live_proof_submission_board.json` | `2` | `6af5514deafa` |
| `deadline_evidence_bridge` | `false` | `dashboard/data/deadline_evidence_bridge.json` | `2` | `0b7d583ded97` |
| `baseline_gauntlet_coverage` | `false` | `dashboard/data/baseline_gauntlet_coverage.json` | `2` | `1e235b0e8747` |
| `kuramoto_accepted_metric_audit` | `false` | `dashboard/data/kuramoto_accepted_metric_audit.json` | `2` | `c11a88f12b06` |
| `valuation_proposal_target_packet` | `false` | `dashboard/data/valuation_proposal_target_packet.json` | `2` | `fa5c6b214c12` |
| `outreach_and_application_send_queue` | `false` | `dashboard/data/outreach_and_application_send_queue.json` | `2` | `c573cefc4059` |
| `geometry_asset_wiring_board` | `false` | `dashboard/data/geometry_asset_wiring_board.json` | `2` | `20be445c8852` |
| `luma_context_dashboard_parity_audit` | `false` | `dashboard/data/luma_context_dashboard_parity_audit.json` | `2` | `757fe628616e` |
| `live_domain_deployment_feed` | `false` | `dashboard/data/live_domain_deployment_feed.json` | `2` | `f11a07d22872` |
| `live_domain_consolidation_audit` | `false` | `dashboard/data/live_domain_consolidation_audit.json` | `2` | `84661a38bcd7` |
| `proof_to_revenue_engine` | `false` | `dashboard/data/proof_to_revenue_engine.json` | `2` | `b611e887434a` |
| `champion_stress_test_matrix` | `false` | `dashboard/data/champion_stress_test_matrix.json` | `2` | `6d3857812135` |
| `champion_metric_battery` | `false` | `dashboard/data/champion_metric_battery.json` | `2` | `a7cff739cc16` |
| `champion_expanded_metric_rollup` | `false` | `dashboard/data/champion_expanded_metric_rollup.json` | `2` | `0548a5becf7b` |
| `first_buyer_target_board` | `false` | `dashboard/data/first_buyer_target_board.json` | `2` | `92c19834aa79` |
| `paid_pilot_outreach_queue` | `false` | `dashboard/data/paid_pilot_outreach_queue.json` | `2` | `8cea42048365` |
| `luma_operator_context` | `false` | `dashboard/data/luma_operator_context.json` | `2` | `85427d1cd3ad` |
| `champion_phase_proxy_diagnostics` | `false` | `dashboard/data/champion_phase_proxy_diagnostics.json` | `2` | `0cbb742be157` |
| `safe_key_provider_ping` | `false` | `dashboard/data/safe_key_provider_ping.json` | `2` | `97093efea69a` |
| `live_source_measurement_maximizer` | `false` | `dashboard/data/live_source_measurement_maximizer.json` | `2` | `a1cd1ac97295` |
| `geometry_live_wiring_matrix` | `false` | `dashboard/data/geometry_live_wiring_matrix.json` | `2` | `b559f3668cda` |
| `geometry_live_breadth_proof_queue` | `false` | `dashboard/data/geometry_live_breadth_proof_queue.json` | `2` | `088820432c98` |
| `branching_live_breadth_replay` | `false` | `dashboard/data/branching_live_breadth_replay.json` | `2` | `3abdf878a529` |
| `rolling_champion_gate` | `false` | `dashboard/data/rolling_champion_gate.json` | `2` | `be369c591785` |
| `top_geometry_live_replay_results` | `false` | `dashboard/data/top_geometry_live_replay_results.json` | `2` | `1b4c4644ad06` |
| `real_noise_evidence_boundary_breaker` | `false` | `dashboard/data/real_noise_evidence_boundary_breaker.json` | `2` | `5cfaadff7d47` |
| `real_noise_promotion_sweep` | `false` | `dashboard/data/real_noise_promotion_sweep.json` | `2` | `f20b21e53ea5` |
| `geometry_execution_context_audit` | `false` | `dashboard/data/geometry_execution_context_audit.json` | `2` | `3a4a556c0176` |

## Commands

- Dry run: `.\deploy\PUSH_PROOF_FEEDS_TO_VPS.ps1 -BundleRoot "C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260705T060243Z" -DryRun`
- Deploy feeds: `.\deploy\PUSH_PROOF_FEEDS_TO_VPS.ps1 -BundleRoot "C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260705T060243Z"`
- Verify domain hashes: `python .\code\ops\BUILD_LIVE_DOMAIN_DEPLOYMENT_FEED.py --timeout 8`

## Remote Web Roots Tried By Deploy Script

- `/opt/lumencore/dashboard`
- `/var/www/lumatrader`
- `/var/www/lumen-core`

## Boundary

Feed-only deploy bundle. It stages reviewer proof JSON for domain hash verification. It does not publish secrets, restart execution services, prove field validation, prove realized savings, set a fixed dollar value per frozen delta, or imply autonomous live trading permission. This is not field validation.

Bundle SHA-256: `7b276cd89de9de33b49ac0bed801e06d8648ac86bcd6c0a8eb5641083c0e02f3`
Archive SHA-256: `6f960c733b8791f35e62237795d3c1f8848c64704c3f3e8b6f764bc31197efd1`
