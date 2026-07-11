# Luma Continuity Operating Context (2026-07-05)

Generated UTC: 2026-07-05T00:00:00Z

## Why this exists
This is the primary handoff file for future sessions to avoid context reset drift.

## Runtime Truth (as of 2026-07-05)
- Repo: `C:\LumaTrader\INSTITUTIONAL_STACK_V2`
- Branch: `codex/live-domain-proof-feed-bundle`
- Remote: `origin` -> `https://github.com/robertashworth1986-debug/lumen-core-public.git`
- Live domain target: `https://lumen-core.ai/`
- Git status: working tree has uncommitted updates in `RESUME_LUMENCORE.md`, `code/`, `config/`, `dashboard/data/`, `dashboard/` deletions, and several docs / out/ops JSON artifacts.

## Latest measured truth (live proof posture)
- `dashboard/data/live_source_measurement_maximizer.json`:
  - enabled sources: 29
  - measured sources: 25
  - failed/thin sources: 4 (`BINANCE_PUBLIC`, `EPA_AQS`, `NREL`, `THE_ODDS_API`)
  - total measured rows: 1506
  - total measured value surface: `20,586,213,130.8`
- `dashboard/data/geometry_execution_context_audit.json`:
  - current strongest lane: `wave_resonance_timing`
  - strongest family: `kuramoto_phase_coupling`
  - 24/24 holdout wins vs named Kalman baseline (internal replay claim only)
  - estimated rows replayed: ~`2.506M`
  - 140 benchmark families in registry
  - failed-or-thin source count reported in this artifact is still 5 (older snapshot) and should be considered stale versus `live_source_measurement_maximizer.json` for latest 4-source failure list.
- `out/ops/geometry_repeat_proof_validation_latest.json` generated and updated by run
- `out/ops/geometry_execution_context_audit_latest.json` generated and updated by run
- `out/ops/real_noise_promotion_sweep_latest.json` generated and updated by run

## Key governance rules for evidence claims
- Safe to claim internally: reproducible replay/hashing, source-conditioned benchmark structure, candidate-vs-baseline internal wins, and production-safe documentation.
- Not safe to claim yet: field validation, realized savings, fixed frozen-delta sale price, autonomous or live production trading, grant award certainty, medical efficacy, or external ROI commitments.

## User-approved outreach policy snapshot
- Outreach drafts/forms can be prepared and staged.
- External sending/action still needs explicit operator confirmation before dispatch.
- Re-check and use `dashboard/data/outreach_and_application_send_queue.json` and `docs/LINKEDIN_GMAIL_OUTREACH_CONTROL_BRIEF_2026-07-03.md` before any send.

## Files changed in this pass (high priority)
- `code/ops/BUILD_LOCKED_SOURCE_BASELINE_REPLAY_SWEEP.py`
- `code/geometry_branching_transport_benchmark.py`
- `config/live_sources.json`
- `config/live_source_registry.json`
- `config/geometry_championship_v1_registry.json`
- `dashboard/data/geometry_execution_context_audit.json`
- `dashboard/data/outreach_and_application_send_queue.json`
- `dashboard/data/real_noise_promotion_sweep.json`
- multiple `docs/*_2026-07-03.md` evidence snapshots
- `dashboard/kraken_execution_dashboard.html`
- removal of several outdated dashboard pages (`agent_approval_hub.html`, `anomalies.html`, `explain.html`, `forecast.html`, `lab.html`, `lumascout.html`, `operator_home.html`, `proof_to_pilot.html`)

## What to do in the next live pass
1. Decide whether deleted dashboard pages should be reintroduced or permanently retired.
2. Re-run `BUILD_LOCKED_SOURCE_BASELINE_REPLAY_SWEEP.py` only if source matrix changed again.
3. Rebuild live-source manifests and wire updated proof feeds to the live domain pages.
4. Continue outreach queue processing with explicit recipient confirmation for pending lanes.

## Context compaction limitation
- I (and the model) cannot disable automatic context compaction.
- To reduce future resets:
  - read this continuity file at pass start;
  - keep changes small and committed;
  - keep only one source-of-truth board for public claims;
  - update this continuity note after each major run.
## Continuity Update (2026-07-11)

Generated UTC: 2026-07-11T13:00:00Z

### What ran this pass
- Re-opened `C:\LumaTrader\INSTITUTIONAL_STACK_V2` and confirmed branch `codex/live-domain-proof-feed-bundle`.
- Audited and kept a focused set of changes that strengthen reviewer/ funding readiness and evidence packaging.
- Generated/validated new artifacts:
  - `grant_submissions/funding_sprint_20260709/FUNDING_REVIEWER_ZERO_FRICTION_PACK_2026-07-10.md`
  - `grant_submissions/funding_sprint_20260709/LUMENCORE_ESTATE_MASTER_INDEX_2026-07-10.md`
- Updated manifest wiring so data room front-door + control counts include both new artifacts.
- Updated grant readiness payload timestamps and top-level readiness audit output to reflect latest generated feed.
- Added two new production scripts:
  - `code/ops/BUILD_FUNDING_REVIEWER_ZERO_FRICTION_PACK.py`
  - `code/ops/BUILD_LUMENCORE_ESTATE_MASTER_INDEX.py`
- Added tests for both scripts:
  - `tests/test_funding_reviewer_zero_friction_pack.py`
  - `tests/test_lumencore_estate_master_index.py`

### Validation completed
- Ran: `python code/ops/BUILD_FUNDING_REVIEWER_ZERO_FRICTION_PACK.py` (success).
- Ran targeted tests:
  - `test_data_room_manifest.py`
  - `test_funding_reviewer_zero_friction_pack.py`
  - `test_lumencore_estate_master_index.py`
- Result: all passed.

### Important note for continuity
- I can’t disable automatic context compaction from inside this environment.
- The model-side way to preserve continuity is:
  - keep this continuity file updated
  - keep high-impact changes committed + pushed quickly
  - keep one source-of-truth doc/dashboard as the public-facing lead board

