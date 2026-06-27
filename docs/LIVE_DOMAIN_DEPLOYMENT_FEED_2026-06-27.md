# Live Domain Deployment Feed

Generated UTC: `2026-06-27T21:56:21.193415+00:00`
Live base: `https://lumen-core.ai`

## Current Answer

The live domain is serving matching hashes for every required reviewer proof feed. This is public deployment verification, not field validation.

## Deployment State

- Required local feeds ready: `7/7`
- Required hosted feeds reachable: `7/7`
- Required hosted hash matches: `7/7`
- Live-domain reviewer-ready: `true`
- Domain deployment state: `LIVE_DOMAIN_HASH_VERIFIED`

## Current Champion Snapshot

- Family: `kuramoto_phase_coupling`
- Label: `Kuramoto phase coupling`
- Named baseline: `kalman_filter`
- Holdout wins: `24/24`
- Estimated rows replayed: `2506267`
- Source systems: `4`
- Buyer-authorized field replay request ready: `true`
- Field-validation claim allowed: `false`
- Real-dollar savings claim allowed: `false`

## Feed Hash Table

| Feed | Required | Local | Hosted Match | Match URL |
|---|---:|---:|---:|---|
| `champion_metric_gauntlet` | `true` | `true` | `true` | https://lumen-core.ai/data/champion_metric_gauntlet.json |
| `kuramoto_holdout_expansion` | `true` | `true` | `true` | https://lumen-core.ai/data/kuramoto_holdout_expansion.json |
| `geometry_champion_of_champions` | `true` | `true` | `true` | https://lumen-core.ai/data/geometry_champion_of_champions.json |
| `field_money_truth_sweep` | `true` | `true` | `true` | https://lumen-core.ai/data/field_money_truth_sweep.json |
| `live_proof_value_meter` | `true` | `true` | `true` | https://lumen-core.ai/data/live_proof_value_meter.json |
| `field_validated_dollar_claim_ladder` | `true` | `true` | `true` | https://lumen-core.ai/data/field_validated_dollar_claim_ladder.json |
| `dollar_claim_gate` | `true` | `true` | `true` | https://lumen-core.ai/data/dollar_claim_gate.json |
| `geometry_asset_wiring_board` | `false` | `true` | `true` | https://lumen-core.ai/data/geometry_asset_wiring_board.json |
| `luma_context_dashboard_parity_audit` | `false` | `true` | `true` | https://lumen-core.ai/data/luma_context_dashboard_parity_audit.json |
| `champion_stress_test_matrix` | `false` | `true` | `true` | https://lumen-core.ai/data/champion_stress_test_matrix.json |

## Reviewer URLs

- `mission_control`: https://lumen-core.ai/mission_control.html
- `grants_console`: https://lumen-core.ai/grants.html?grant_id=nsf_sbir_phase_i
- `champion_feed_primary`: https://lumen-core.ai/data/champion_metric_gauntlet.json
- `champion_feed_fallback`: https://lumen-core.ai/dashboard/data/champion_metric_gauntlet.json

## Publish And Verify Runbook

- `python .\code\ops\BUILD_CHAMPION_METRIC_GAUNTLET.py`
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

Deployment feed SHA-256: `79927b04e65c10f544a6a547974d46bdc7420fa81832da7e6ad2e06d9492a7a9`
