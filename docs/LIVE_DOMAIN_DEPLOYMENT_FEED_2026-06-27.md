# Live Domain Deployment Feed

Generated UTC: `2026-06-30T14:14:20.524523+00:00`
Live base: `https://lumen-core.ai`

## Current Answer

The local proof stack is ready for reviewer packaging, but the live domain still needs hosted hash verification before we should point reviewers to it.

## Deployment State

- Required local feeds ready: `12/12`
- Required hosted feeds reachable: `0/12`
- Required hosted hash matches: `0/12`
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
| `locked_source_baseline_replay_sweep` | `true` | `true` | `false` | - |
| `kuramoto_holdout_expansion` | `true` | `true` | `false` | - |
| `geometry_champion_of_champions` | `true` | `true` | `false` | - |
| `field_money_truth_sweep` | `true` | `true` | `false` | - |
| `live_proof_value_meter` | `true` | `true` | `false` | - |
| `field_validated_dollar_claim_ladder` | `true` | `true` | `false` | - |
| `dollar_claim_gate` | `true` | `true` | `false` | - |
| `field_validation_control_room` | `true` | `true` | `false` | - |
| `field_validation_outreach_board` | `true` | `true` | `false` | - |
| `proof_to_pilot_control_room` | `true` | `true` | `false` | - |
| `champion_sample_expansion_and_economic_bridge` | `true` | `true` | `false` | - |
| `geometry_asset_wiring_board` | `false` | `true` | `false` | - |
| `luma_context_dashboard_parity_audit` | `false` | `true` | `false` | - |
| `champion_stress_test_matrix` | `false` | `true` | `false` | - |
| `proof_to_revenue_engine` | `false` | `true` | `false` | - |
| `first_buyer_target_board` | `false` | `true` | `false` | - |
| `live_domain_consolidation_audit` | `false` | `true` | `false` | - |

## Reviewer URLs

- `mission_control`: https://lumen-core.ai/mission_control.html
- `grants_console`: https://lumen-core.ai/grants.html?grant_id=nsf_sbir_phase_i
- `quant_lab`: https://lumen-core.ai/quant_lab.html
- `proof_to_pilot`: https://lumen-core.ai/proof_to_pilot.html
- `champion_feed_primary`: https://lumen-core.ai/data/champion_metric_gauntlet.json
- `champion_feed_fallback`: https://lumen-core.ai/dashboard/data/champion_metric_gauntlet.json
- `locked_source_baseline_replay_sweep`: https://lumen-core.ai/data/locked_source_baseline_replay_sweep.json
- `champion_sample_expansion_and_economic_bridge`: https://lumen-core.ai/data/champion_sample_expansion_and_economic_bridge.json
- `field_validation_control_room`: https://lumen-core.ai/data/field_validation_control_room.json
- `field_validation_outreach_board`: https://lumen-core.ai/data/field_validation_outreach_board.json
- `live_domain_consolidation_audit`: https://lumen-core.ai/data/live_domain_consolidation_audit.json

## Publish And Verify Runbook

- `python .\code\ops\BUILD_CHAMPION_METRIC_GAUNTLET.py`
- `python .\code\ops\BUILD_LOCKED_SOURCE_BASELINE_REPLAY_SWEEP.py`
- `python .\code\ops\BUILD_CHAMPION_SAMPLE_EXPANSION_AND_ECONOMIC_BRIDGE.py`
- `python .\code\ops\BUILD_FIELD_VALIDATION_CONTROL_ROOM.py`
- `python .\code\ops\BUILD_FIELD_VALIDATION_OUTREACH_BOARD.py`
- `python .\code\ops\BUILD_PROOF_TO_PILOT_CONTROL_ROOM.py`
- `python .\code\ops\BUILD_LIVE_DOMAIN_DEPLOYMENT_FEED.py --skip-live-check`
- `python .\code\ops\BUILD_LIVE_DOMAIN_CONSOLIDATION_AUDIT.py`
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

Deployment feed SHA-256: `68351a59931816bedc8e89f5ccac403f8db594ce5699a88beaa74c64c79d423f`
