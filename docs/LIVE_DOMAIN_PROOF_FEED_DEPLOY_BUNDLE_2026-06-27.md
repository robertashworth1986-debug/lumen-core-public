# Live Domain Proof Feed Deploy Bundle

Generated UTC: `2026-07-29T12:37:12Z`
Bundle root: `C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260729T123712Z`
Archive: `C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260729T123712Z.tgz`

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
| `champion_metric_gauntlet` | `true` | `dashboard/data/champion_metric_gauntlet.json` | `2` | `fce31423840d` |
| `locked_source_baseline_replay_sweep` | `true` | `dashboard/data/locked_source_baseline_replay_sweep.json` | `2` | `9313cc447252` |
| `kuramoto_holdout_expansion` | `true` | `dashboard/data/kuramoto_holdout_expansion.json` | `2` | `a05161515a55` |
| `geometry_champion_of_champions` | `true` | `dashboard/data/geometry_champion_of_champions.json` | `2` | `11abea8b5631` |
| `field_money_truth_sweep` | `true` | `dashboard/data/field_money_truth_sweep.json` | `2` | `07f3fc9e3d03` |
| `live_proof_value_meter` | `true` | `dashboard/data/live_proof_value_meter.json` | `2` | `1fe87e6d1c02` |
| `field_validated_dollar_claim_ladder` | `true` | `dashboard/data/field_validated_dollar_claim_ladder.json` | `2` | `e9edee8d8897` |
| `dollar_claim_gate` | `true` | `dashboard/data/dollar_claim_gate.json` | `2` | `aa847a0ae9f7` |
| `field_validation_control_room` | `true` | `dashboard/data/field_validation_control_room.json` | `2` | `12387908da23` |
| `field_validation_outreach_board` | `true` | `dashboard/data/field_validation_outreach_board.json` | `2` | `5ed34f7b2529` |
| `proof_to_pilot_control_room` | `true` | `dashboard/data/proof_to_pilot_control_room.json` | `2` | `119c97fb0103` |
| `champion_sample_expansion_and_economic_bridge` | `true` | `dashboard/data/champion_sample_expansion_and_economic_bridge.json` | `2` | `0fca1a0064f3` |
| `champion_source_ablation` | `true` | `dashboard/data/champion_source_ablation.json` | `2` | `743be891448b` |
| `grant_readiness_status` | `true` | `dashboard/data/grant_readiness_status.json` | `2` | `949d8a248923` |
| `falcon_permutation_calibrated_router` | `false` | `dashboard/data/falcon_permutation_calibrated_router.json` | `2` | `8527167a0163` |
| `top5_live_proof_submission_board` | `false` | `dashboard/data/top5_live_proof_submission_board.json` | `2` | `6af5514deafa` |
| `deadline_evidence_bridge` | `false` | `dashboard/data/deadline_evidence_bridge.json` | `2` | `0b7d583ded97` |
| `baseline_gauntlet_coverage` | `false` | `dashboard/data/baseline_gauntlet_coverage.json` | `2` | `3a68d32e1904` |
| `kuramoto_accepted_metric_audit` | `false` | `dashboard/data/kuramoto_accepted_metric_audit.json` | `2` | `c97ae6e685cf` |
| `valuation_proposal_target_packet` | `false` | `dashboard/data/valuation_proposal_target_packet.json` | `2` | `ed7c98c8617e` |
| `outreach_and_application_send_queue` | `false` | `dashboard/data/outreach_and_application_send_queue.json` | `2` | `c573cefc4059` |
| `geometry_asset_wiring_board` | `false` | `dashboard/data/geometry_asset_wiring_board.json` | `2` | `20be445c8852` |
| `luma_context_dashboard_parity_audit` | `false` | `dashboard/data/luma_context_dashboard_parity_audit.json` | `2` | `757fe628616e` |
| `live_domain_deployment_feed` | `false` | `dashboard/data/live_domain_deployment_feed.json` | `2` | `976244a0746c` |
| `live_domain_consolidation_audit` | `false` | `dashboard/data/live_domain_consolidation_audit.json` | `2` | `5845a35e5bd9` |
| `proof_to_revenue_engine` | `false` | `dashboard/data/proof_to_revenue_engine.json` | `2` | `16b3ce7bff41` |
| `champion_stress_test_matrix` | `false` | `dashboard/data/champion_stress_test_matrix.json` | `2` | `a0be13058904` |
| `champion_metric_battery` | `false` | `dashboard/data/champion_metric_battery.json` | `2` | `9486eb9494ac` |
| `champion_expanded_metric_rollup` | `false` | `dashboard/data/champion_expanded_metric_rollup.json` | `2` | `57b7f66083c4` |
| `first_buyer_target_board` | `false` | `dashboard/data/first_buyer_target_board.json` | `2` | `bc242600bd02` |
| `paid_pilot_outreach_queue` | `false` | `dashboard/data/paid_pilot_outreach_queue.json` | `2` | `1b336ce29a1e` |
| `luma_operator_context` | `false` | `dashboard/data/luma_operator_context.json` | `2` | `fa9b0c29e187` |
| `champion_phase_proxy_diagnostics` | `false` | `dashboard/data/champion_phase_proxy_diagnostics.json` | `2` | `b1ffc78e5b12` |
| `safe_key_provider_ping` | `false` | `dashboard/data/safe_key_provider_ping.json` | `2` | `ba0d66c7f81f` |
| `live_source_measurement_maximizer` | `false` | `dashboard/data/live_source_measurement_maximizer.json` | `2` | `a208ea39d595` |
| `geometry_live_wiring_matrix` | `false` | `dashboard/data/geometry_live_wiring_matrix.json` | `2` | `c0dd6ccc25cc` |
| `geometry_live_breadth_proof_queue` | `false` | `dashboard/data/geometry_live_breadth_proof_queue.json` | `2` | `c9cd4ed3e0f4` |
| `branching_live_breadth_replay` | `false` | `dashboard/data/branching_live_breadth_replay.json` | `2` | `3abdf878a529` |
| `rolling_champion_gate` | `false` | `dashboard/data/rolling_champion_gate.json` | `2` | `af23fd8641ef` |
| `top_geometry_live_replay_results` | `false` | `dashboard/data/top_geometry_live_replay_results.json` | `2` | `eab52e0a5ab9` |
| `real_noise_evidence_boundary_breaker` | `false` | `dashboard/data/real_noise_evidence_boundary_breaker.json` | `2` | `5cfaadff7d47` |
| `real_noise_promotion_sweep` | `false` | `dashboard/data/real_noise_promotion_sweep.json` | `2` | `f20b21e53ea5` |
| `geometry_execution_context_audit` | `false` | `dashboard/data/geometry_execution_context_audit.json` | `2` | `e9cb5f159488` |
| `market_signal_source_native_benchmark` | `false` | `dashboard/data/market_signal_source_native_benchmark.json` | `2` | `5896626e4729` |
| `source_native_family_baseline_ledger` | `false` | `dashboard/data/source_native_family_baseline_ledger.json` | `2` | `f4ef20f11670` |

## Commands

- Dry run: `.\deploy\PUSH_PROOF_FEEDS_TO_VPS.ps1 -BundleRoot "C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260729T123712Z" -DryRun`
- Apply feeds after separate action-time HumanUnlock: `.\deploy\PUSH_PROOF_FEEDS_TO_VPS.ps1 -BundleRoot "C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260729T123712Z" -Apply`
- Verify domain hashes: `python .\code\ops\BUILD_LIVE_DOMAIN_DEPLOYMENT_FEED.py --timeout 8`
- Apply prerequisite: set `LUMA_HUMAN_UNLOCK_TOKEN` privately in the process environment with at least `32` characters.
- Building this bundle does not authorize deployment.

## Remote Web Roots Tried By Deploy Script

- `/opt/lumencore/dashboard`
- `/var/www/lumatrader`
- `/var/www/lumen-core`

## Boundary

Feed-only deploy bundle. It stages reviewer proof JSON for domain hash verification. It does not publish secrets, restart execution services, prove field validation, prove realized savings, set a fixed dollar value per frozen delta, or imply autonomous live trading permission. This is not field validation.

Bundle SHA-256: `621ffb68ed084d13484c34a80e32de7cf9c7d7b9cf361c2f8cfc0a329ad22647`
Archive SHA-256: `bf845f814a377e1fb0407e16f6ae1692cc877c9ec1f635e928fe8fec30b052e5`
