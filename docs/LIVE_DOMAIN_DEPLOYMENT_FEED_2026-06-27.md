# Live Domain Deployment Feed

Generated UTC: `2026-06-27T20:02:09.842204+00:00`
Live base: `https://lumen-core.ai`

## Current Answer

The local proof stack is ready for reviewer packaging, but the live domain still needs hosted hash verification before we should point reviewers to it.

## Deployment State

- Required local feeds ready: `7/7`
- Required hosted feeds reachable: `0/7`
- Required hosted hash matches: `0/7`
- Live-domain reviewer-ready: `false`
- Domain deployment state: `LOCAL_READY_DOMAIN_NOT_VERIFIED_OR_STALE`

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
| `champion_metric_gauntlet` | `true` | `true` | `false` | - |
| `kuramoto_holdout_expansion` | `true` | `true` | `false` | - |
| `geometry_champion_of_champions` | `true` | `true` | `false` | - |
| `field_money_truth_sweep` | `true` | `true` | `false` | - |
| `live_proof_value_meter` | `true` | `true` | `false` | - |
| `field_validated_dollar_claim_ladder` | `true` | `true` | `false` | - |
| `dollar_claim_gate` | `true` | `true` | `false` | - |
| `geometry_asset_wiring_board` | `false` | `true` | `false` | - |
| `luma_context_dashboard_parity_audit` | `false` | `true` | `false` | - |

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

Deployment feed SHA-256: `02fc6dc23aef2ace7dc0f0f435eb1ce12b23cb0752a688f564963aded7d84f82`
