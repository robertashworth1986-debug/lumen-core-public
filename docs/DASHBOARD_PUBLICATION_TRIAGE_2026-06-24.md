# Dashboard Publication Triage

Generated: 2026-06-24

## Immediate Answer

The public-domain shape is close, but it is not reviewer-grade yet.

`https://lumen-core.ai/mission_control.html` is reachable, but the key proof feeds currently return 404 from the live domain:

- `https://lumen-core.ai/dashboard/data/reviewer_evidence_gate.json`
- `https://lumen-core.ai/dashboard/data/live_proof_value_meter.json`
- `https://lumen-core.ai/dashboard/data/geometry_champion_of_champions.json`
- `https://lumen-core.ai/dashboard/data/top5_live_proof_submission_board.json`
- matching `/data/...` fallback paths

Until those feeds are deployed or routed, the live site is a public dashboard shell, not a fully live proof surface.

## Reviewer-Facing Public Spine

These are the surfaces that should be treated as the public path for reviewers, agencies, partners, and serious collaborators:

- `dashboard/index.html`
- `dashboard/dashboard_portal.html`
- `dashboard/mission_control.html`
- `dashboard/quant_lab.html`
- `dashboard/grants.html`
- `dashboard/live_source_registry.html`
- `dashboard/hard_truth_live_measurement_audit.html`
- `dashboard/advanced_fleet_validation.html`, after its generator overwrite issue is pinned
- `dashboard/staleness_command_center.html`
- `dashboard/harmonic_proofpack_mission.html`

These pages should be clean, current, and conservative. They should show what is measured, what is simulated, what is paper-only, and what is blocked.

## Internal Or Private Surfaces

These are useful but should not be the first public reviewer doorway:

- `dashboard/kraken_execution_dashboard.html`
- `dashboard/alpaca_paper_live_dashboard.html`
- `dashboard/vps_growth_proof_3d.html`
- `dashboard/agent_approval_hub.html`
- exchange, paper-trading, API-key, and approval-control pages

Reason: they are operationally useful but easy to misunderstand as profit proof, live trading readiness, or autonomous execution authority.

## Supporting Demo And Commercial Pages

These can stay linked from the public spine, but should not carry hard performance claims by themselves:

- `dashboard/luma_experience.html`
- `dashboard/investor_command_room.html`
- `dashboard/investor_wallboard.html`
- `dashboard/pitch_sequence_console.html`
- `dashboard/scenario_mission.html`
- `dashboard/lumascout_dashboard.html`
- `dashboard/luma_voice_context_console.html`

Use these for story, navigation, and demo impact. Hard claims still need to resolve back to proof JSON, hashes, and frozen replay artifacts.

## Archive Candidates

Do not delete these automatically. Move them only after a commit/snapshot and Robert approval.

- Empty or stale proof files: `proof_live_*.json`, especially 2-byte JSON files
- March dashboard generations: `level2_dashboard.json`, `level3_truth_dashboard.json`, `level4_live_summary.json`, `level5_execution_dashboard.json`, `level6_paper_guardrail.json`, `master_dashboard.json`, `live_ops_state.json`
- old status helpers: `api_key_status.txt`, `self_heal_log.txt`, `orchestrator_watchdog_status.txt`
- stale lightweight JSON pages: `infra_live_dashboard.json`, `grid_value_live.json`, unless still referenced by a current canonical page
- duplicate master pages: keep one canonical master dashboard and archive the duplicate after link checks

## Do Not Archive Yet

These are active proof-chain feeds and should stay:

- `dashboard/data/reviewer_evidence_gate.json`
- `dashboard/data/live_proof_value_meter.json`
- `dashboard/data/dollar_claim_gate.json`
- `dashboard/data/top5_live_proof_submission_board.json`
- `dashboard/data/grant_deadline_triage.json`
- `dashboard/data/live_source_measurement_maximizer.json`
- `dashboard/data/geometry_*`
- `dashboard/data/luma_context_dashboard_parity_audit.json`
- `dashboard/data/public_visibility_packet.json`

## Current Proof Posture

The local reviewer gate is useful and bounded:

- ready for reviewer packet: true
- live measured sources: 17
- live measured rows in current gate: 417
- geometry families in current gate: 140
- geometry status: live-wired, not claim-ready
- real dollar claim status: not ready

Safe language: the system has a hashable live-source measurement chain and replay queue.

Unsafe language: field validation, realized savings, trading profit, guaranteed funding, or live geometry winner claims.

## Golden-Ticket Path

The strong version is not “cool dashboards.” The strong version is:

1. Fresh public or authorized live data is pulled.
2. Raw inputs, configs, splits, and hashes are frozen.
3. Geometry and baseline families run on identical windows.
4. Winners and losers are both recorded.
5. Claim gates decide what can be said.
6. The live domain serves the exact same proof feeds the local dashboards use.
7. Grants cite bounded results, not hype.

If the reviewer can open the site, download the JSON, verify the hashes, and see the same proof state as the proposal, that becomes a serious trust signal.

## Public Domain Fix List

Priority 1:

- deploy or route `dashboard/data/*.json` to `https://lumen-core.ai/dashboard/data/*.json`
- optionally mirror the same files to `https://lumen-core.ai/data/*.json`
- rerun `code/ops/BUILD_LUMA_CONTEXT_DASHBOARD_PARITY_AUDIT.py`
- require feed probes to pass before calling the live site reviewer-ready

Priority 2:

- fix missing dashboard links from `quant_lab.html` and `mission_control.html`:
  - `/master_evidence.html`
  - `/lumaq_brain_command_center.html`
  - `/lumencore_master_v2.html`
  - `/alpha_burst_lab_holo_3d.html`
- either restore those pages or replace links with existing canonical proof pages

Priority 3:

- pin `advanced_fleet_validation.html` generation so local measured evidence is not overwritten by an older skinny generator
- make the Grants page display today status from `grant_deadline_triage.json`, `top5_live_proof_submission_board.json`, and `reviewer_evidence_gate.json`

## DARPA/SAM Note

Robert is signed into DARPA BAAT and SAM.gov. Chrome browser control is currently blocked by the local Codex/Chrome bridge, so portal actions should be handled by manual handoff until the extension connection is repaired. Do not final-submit, certify, or upload without fresh action-time approval.
