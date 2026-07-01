# Live Domain Proof Feed Deploy Bundle

Generated UTC: `2026-07-01T09:28:31Z`
Bundle root: `C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260701T092831Z`
Archive: `C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260701T092831Z.tgz`

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
| `champion_metric_gauntlet` | `true` | `dashboard/data/champion_metric_gauntlet.json` | `2` | `59b353e2efbc` |
| `locked_source_baseline_replay_sweep` | `true` | `dashboard/data/locked_source_baseline_replay_sweep.json` | `2` | `9af7cce37629` |
| `kuramoto_holdout_expansion` | `true` | `dashboard/data/kuramoto_holdout_expansion.json` | `2` | `2dfca076b3f4` |
| `geometry_champion_of_champions` | `true` | `dashboard/data/geometry_champion_of_champions.json` | `2` | `6d5eaee3a9a9` |
| `field_money_truth_sweep` | `true` | `dashboard/data/field_money_truth_sweep.json` | `2` | `88f8242d07ed` |
| `live_proof_value_meter` | `true` | `dashboard/data/live_proof_value_meter.json` | `2` | `07c416189aba` |
| `field_validated_dollar_claim_ladder` | `true` | `dashboard/data/field_validated_dollar_claim_ladder.json` | `2` | `f29d59bbcc97` |
| `dollar_claim_gate` | `true` | `dashboard/data/dollar_claim_gate.json` | `2` | `9e64ad63466e` |
| `field_validation_control_room` | `true` | `dashboard/data/field_validation_control_room.json` | `2` | `bf7fae7aef04` |
| `field_validation_outreach_board` | `true` | `dashboard/data/field_validation_outreach_board.json` | `2` | `02533cbdc458` |
| `proof_to_pilot_control_room` | `true` | `dashboard/data/proof_to_pilot_control_room.json` | `2` | `20fdcc50fae6` |
| `champion_sample_expansion_and_economic_bridge` | `true` | `dashboard/data/champion_sample_expansion_and_economic_bridge.json` | `2` | `71b94312eef3` |
| `geometry_asset_wiring_board` | `false` | `dashboard/data/geometry_asset_wiring_board.json` | `2` | `20be445c8852` |
| `luma_context_dashboard_parity_audit` | `false` | `dashboard/data/luma_context_dashboard_parity_audit.json` | `2` | `757fe628616e` |
| `live_domain_deployment_feed` | `false` | `dashboard/data/live_domain_deployment_feed.json` | `2` | `a201ddd89c06` |
| `live_domain_consolidation_audit` | `false` | `dashboard/data/live_domain_consolidation_audit.json` | `2` | `63cfd938154e` |
| `proof_to_revenue_engine` | `false` | `dashboard/data/proof_to_revenue_engine.json` | `2` | `b611e887434a` |
| `champion_stress_test_matrix` | `false` | `dashboard/data/champion_stress_test_matrix.json` | `2` | `eee5624d7393` |
| `first_buyer_target_board` | `false` | `dashboard/data/first_buyer_target_board.json` | `2` | `eab5d0cc7e85` |
| `paid_pilot_outreach_queue` | `false` | `dashboard/data/paid_pilot_outreach_queue.json` | `2` | `8cea42048365` |

## Commands

- Dry run: `.\deploy\PUSH_PROOF_FEEDS_TO_VPS.ps1 -BundleRoot "C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260701T092831Z" -DryRun`
- Deploy feeds: `.\deploy\PUSH_PROOF_FEEDS_TO_VPS.ps1 -BundleRoot "C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260701T092831Z"`
- Verify domain hashes: `python .\code\ops\BUILD_LIVE_DOMAIN_DEPLOYMENT_FEED.py --timeout 8`

## Remote Web Roots Tried By Deploy Script

- `/opt/lumencore/dashboard`
- `/var/www/lumatrader`
- `/var/www/lumen-core`

## Boundary

Feed-only deploy bundle. It stages reviewer proof JSON for domain hash verification. It does not publish secrets, restart execution services, prove field validation, prove realized savings, set a fixed dollar value per frozen delta, or imply autonomous live trading permission. This is not field validation.

Bundle SHA-256: `4bdd3620cd1ba5ec5e79f34912bfab667c7f35f52c47aad95ece6781e037e88f`
Archive SHA-256: `4efe4d15ed1f77a7a1e901cfba51174f5d44dfbd12955bc09c2fa3ecf77d72ed`
