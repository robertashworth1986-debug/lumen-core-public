# Live Domain Deployment Feed

Generated UTC: `2026-06-30T00:29:34.955846+00:00`
Live base: `https://lumen-core.ai`

## Current Answer

The local proof stack is ready for reviewer packaging, but the live domain still needs hosted hash verification before we should point reviewers to it.

## Deployment State

- Required local feeds ready: `10/10`
- Required hosted feeds reachable: `7/10`
- Required hosted hash matches: `4/10`
- Live-domain reviewer-ready: `false`
- Domain deployment state: `LOCAL_READY_DOMAIN_NOT_VERIFIED_OR_STALE`

## Current Champion Snapshot

- Family: `kuramoto_phase_coupling`
- Label: `Kuramoto phase coupling`
- Named baseline: `kalman_filter`
- Holdout wins: `24/24`
- Estimated rows replayed: `2507379`
- Source systems: `4`
- Buyer-authorized field replay request ready: `true`
- Field-validation claim allowed: `false`
- Real-dollar savings claim allowed: `false`

## Feed Hash Table

| Feed | Required | Local | Hosted Match | Match URL |
|---|---:|---:|---:|---|
| `champion_metric_gauntlet` | `true` | `true` | `false` | - |
| `kuramoto_holdout_expansion` | `true` | `true` | `false` | - |
| `geometry_champion_of_champions` | `true` | `true` | `false` | - |
| `field_money_truth_sweep` | `true` | `true` | `true` | https://lumen-core.ai/data/field_money_truth_sweep.json |
| `live_proof_value_meter` | `true` | `true` | `true` | https://lumen-core.ai/data/live_proof_value_meter.json |
| `field_validated_dollar_claim_ladder` | `true` | `true` | `true` | https://lumen-core.ai/data/field_validated_dollar_claim_ladder.json |
| `dollar_claim_gate` | `true` | `true` | `true` | https://lumen-core.ai/data/dollar_claim_gate.json |
| `field_validation_control_room` | `true` | `true` | `false` | - |
| `field_validation_outreach_board` | `true` | `true` | `false` | - |
| `proof_to_pilot_control_room` | `true` | `true` | `false` | - |
| `geometry_asset_wiring_board` | `false` | `true` | `true` | https://lumen-core.ai/data/geometry_asset_wiring_board.json |
| `luma_context_dashboard_parity_audit` | `false` | `true` | `false` | - |
| `champion_stress_test_matrix` | `false` | `true` | `true` | https://lumen-core.ai/data/champion_stress_test_matrix.json |
| `proof_to_revenue_engine` | `false` | `true` | `true` | https://lumen-core.ai/data/proof_to_revenue_engine.json |
| `first_buyer_target_board` | `false` | `true` | `true` | https://lumen-core.ai/data/first_buyer_target_board.json |

## Reviewer URLs

- `mission_control`: https://lumen-core.ai/mission_control.html
- `grants_console`: https://lumen-core.ai/grants.html?grant_id=nsf_sbir_phase_i
- `quant_lab`: https://lumen-core.ai/quant_lab.html
- `proof_to_pilot`: https://lumen-core.ai/proof_to_pilot.html
- `champion_feed_primary`: https://lumen-core.ai/data/champion_metric_gauntlet.json
- `champion_feed_fallback`: https://lumen-core.ai/dashboard/data/champion_metric_gauntlet.json
- `field_validation_control_room`: https://lumen-core.ai/data/field_validation_control_room.json
- `field_validation_outreach_board`: https://lumen-core.ai/data/field_validation_outreach_board.json

## Publish And Verify Runbook

- `python .\code\ops\BUILD_CHAMPION_METRIC_GAUNTLET.py`
- `python .\code\ops\BUILD_FIELD_VALIDATION_CONTROL_ROOM.py`
- `python .\code\ops\BUILD_FIELD_VALIDATION_OUTREACH_BOARD.py`
- `python .\code\ops\BUILD_PROOF_TO_PILOT_CONTROL_ROOM.py`
- `python .\code\ops\BUILD_LIVE_DOMAIN_DEPLOYMENT_FEED.py --skip-live-check`
- `python .\code\ops\BUILD_LIVE_DOMAIN_PROOF_FEED_DEPLOY_BUNDLE.py`
- `.\deploy\PUSH_PROOF_FEEDS_TO_VPS.ps1 -DryRun`
- `.\deploy\PUSH_PROOF_FEEDS_TO_VPS.ps1`
- `python .\code\ops\BUILD_LIVE_DOMAIN_DEPLOYMENT_FEED.py`

## What To Ask Next

- Which required proof feed is missing or stale on the live domain?
- What exact URL should a reviewer open first?
- Which claim is safe once hosted hashes match?
- What still blocks field validation after deployment is verified?
- What buyer-authorized replay would turn this from internal proof into a field claim?

## Boundary

Live-domain deployment feed only. Matching hosted hashes prove that the public domain is serving the same local proof feeds. They do not prove field validation, realized savings, grant award certainty, fixed frozen delta pricing, medical efficacy, or live trading performance.

Deployment feed SHA-256: `ef7909bb7be314208776aa4b001b8980c554e25358e5142817ed78cf55d1a5d1`
