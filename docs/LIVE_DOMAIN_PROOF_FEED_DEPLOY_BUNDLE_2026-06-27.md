# Live Domain Proof Feed Deploy Bundle

Generated UTC: `2026-06-27T21:19:04Z`
Bundle root: `C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260627T211904Z`
Archive: `C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260627T211904Z.tgz`

## Decision

The feed-only deploy bundle is ready. It can publish proof JSON feeds to the public domain paths without restarting trading, gateway, or dashboard services.

## Safety Gates

- Required ready: `7/7`
- Feed-only deploy ready: `true`
- Broad stack deploy allowed: `false`
- Service restart required: `false`
- Publishes config or secrets: `false`
- Field-validation claim allowed: `false`
- Real-dollar savings claim allowed: `false`

## Feed Table

| Feed | Required | Source | Copied | SHA-256 |
|---|---:|---|---:|---|
| `champion_metric_gauntlet` | `true` | `dashboard/data/champion_metric_gauntlet.json` | `2` | `58a639808624` |
| `kuramoto_holdout_expansion` | `true` | `dashboard/data/kuramoto_holdout_expansion.json` | `2` | `ab594c0ad7e8` |
| `geometry_champion_of_champions` | `true` | `dashboard/data/geometry_champion_of_champions.json` | `2` | `5dbfbaa13140` |
| `field_money_truth_sweep` | `true` | `dashboard/data/field_money_truth_sweep.json` | `2` | `6091c47f79c4` |
| `live_proof_value_meter` | `true` | `dashboard/data/live_proof_value_meter.json` | `2` | `07c416189aba` |
| `field_validated_dollar_claim_ladder` | `true` | `dashboard/data/field_validated_dollar_claim_ladder.json` | `2` | `f29d59bbcc97` |
| `dollar_claim_gate` | `true` | `dashboard/data/dollar_claim_gate.json` | `2` | `9e64ad63466e` |
| `geometry_asset_wiring_board` | `false` | `dashboard/data/geometry_asset_wiring_board.json` | `2` | `e3def388208f` |
| `luma_context_dashboard_parity_audit` | `false` | `dashboard/data/luma_context_dashboard_parity_audit.json` | `2` | `8047d31daef3` |
| `live_domain_deployment_feed` | `false` | `dashboard/data/live_domain_deployment_feed.json` | `2` | `05948a5055ff` |
| `proof_to_revenue_engine` | `false` | `dashboard/data/proof_to_revenue_engine.json` | `2` | `dd221bfa4baa` |

## Commands

- Dry run: `.\deploy\PUSH_PROOF_FEEDS_TO_VPS.ps1 -BundleRoot "C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260627T211904Z" -DryRun`
- Deploy feeds: `.\deploy\PUSH_PROOF_FEEDS_TO_VPS.ps1 -BundleRoot "C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260627T211904Z"`
- Verify domain hashes: `python .\code\ops\BUILD_LIVE_DOMAIN_DEPLOYMENT_FEED.py --timeout 8`

## Remote Web Roots Tried By Deploy Script

- `/opt/lumencore/dashboard`
- `/var/www/lumatrader`
- `/var/www/lumen-core`

## Boundary

Feed-only deploy bundle. It stages reviewer proof JSON for domain hash verification. It does not publish secrets, restart execution services, prove field validation, prove realized savings, set a fixed dollar value per frozen delta, or imply autonomous live trading permission. This is not field validation.

Bundle SHA-256: `a9db7b76ff1beb50429006834b37b5637852c056a0ab78f0cbc52255aaa7f7b0`
Archive SHA-256: `5707bf15b164b65cc8fc296ef12482cecd954c9aa00606655e6d6094eb5fdce3`
