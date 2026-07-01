# LumenCore Top-Five Submission Control Room

Date: June 19, 2026

Purpose: coordinate the five highest-fit funding packages without overstating
evidence, submitting through the wrong portal, or treating portal/legal gates
as solved before the user verifies them.

Portal/compliance matrix:
`grant_submissions/PORTAL_COMPLIANCE_ACTION_MATRIX_2026-06-19.md`

Grants.gov AI/cyber triage:
`grant_submissions/GRANTS_GOV_AI_CYBER_TRIAGE_2026-06-19.md`

DICE 11-day abstract sprint:
`grant_submissions/DICE_HR001126S0010/DICE_NEXT_11_DAY_SPRINT_2026-06-19.md`

Automated top-five readiness audit:
`grant_submissions/TOP5_SUBMISSION_READINESS_AUDIT_2026-06-19.md`

## Portal Reality Check

| Package | Primary portal | Grants.gov role |
|---|---|---|
| DARPA DICE HR001126S0010 | DARPA BAAT | Grants.gov can list the opportunity, but BAAT controls submission. |
| Navy NV063 HarborSentinel | DSIP | DoD SBIR/STTR uses DSIP for proposal submission. |
| NSF SBIR Project Pitch | NSF Seed Fund Project Pitch portal | Not a Grants.gov workspace submission at the pitch stage. |
| DLA NV011 MissionWeave | DSIP | DoD SBIR/STTR uses DSIP for proposal submission. |
| Navy NV065 Adaptive Sensor Management | DSIP | DoD SBIR/STTR uses DSIP for proposal submission. |

Codex can draft, verify, navigate, and help paste only after the user logs in.
Codex must not click certification, consent, upload, or submit controls without
fresh action-time approval from the user.

## Submission Priority

Weak workspace paths are parked. HUD construction robotics and partner-only
GlobalX should not consume more build time tonight. NRL remains a reserve
white-paper lane unless the user explicitly chooses one topic; it does not
replace the current top-five submission queue.

| Rank | Package | Current readiness | Upload status |
|---:|---|---|---|
| 1 | DICE | Strong abstract draft, frozen evidence, local submission lock packet, local 7-page visual DOCX QA, source-confirmed visible URLs, normalized citations, and explicit ROM cost wording. | Do not upload until BAAT authority, optional portal/Word layout check, final reference-relevance review, cost boundary, and human approval clear. |
| 2 | HarborSentinel | Strongest Navy technical package; v6 source-lane evidence, audit, cost basis, representative-data/format plan, data-source access audit, AIS pilot source registry, raw NOAA AIS acquisition/hash/profile, held-out public AIS split, single-lane AIS readiness gate, local 6-page Volume 2 DOCX visual QA, and explicit Month 1-6 success gates exist. | Do not upload until DSIP opens and compliance, cost, HarborSentinel detector experiment on the frozen AIS validation split, ADS-B licensing/authorization, clearance-transition gates, and final portal-preview review clear. |
| 3 | NSF Project Pitch | Fastest low-friction cash path; four portal fields drafted and counted. | Ready for human portal paste-check after legal name, PI/title, and duplicate-pitch check. |
| 4 | MissionWeave | Good DLA software fit; concept, audit, and $100,000 ROM cost basis exist. | Do not upload until one bounded process, domain review, DSIP budget, and representative-data path are credible. |
| 5 | NV065 Adaptive Sensor Management | Topic-specific frozen benchmark, audit, and $315,000 ROM cost basis exist. | Do not upload until representative radar-resource assumptions, sensor-domain review, and DSIP/compliance gates clear. |

## Artifact Map

| Package | Main draft | Readiness or audit | Cost basis | Evidence |
|---|---|---|---|---|
| DICE | `grant_submissions/DICE_HR001126S0010/LumenCore_DICE_Abstract_WORKING_DRAFT.docx` | `grant_submissions/DICE_HR001126S0010/DICE_FINALIZATION_AUDIT_2026-06-19.md`; `grant_submissions/DICE_HR001126S0010/DICE_REFERENCE_RELEVANCE_MATRIX_2026-06-20.md`; `grant_submissions/DICE_HR001126S0010/DICE_SUBMISSION_LOCK_PACKET_2026-06-20.md` | `grant_submissions/DICE_HR001126S0010/DICE_COST_BASIS_WORKING.md` | `out/dice_constraint_contract/20260618T_DICE_CONTRACT_V2_ROLE_SHUFFLE/`; `out/ops/dice_submission_lock_packet_latest.json`; `grant_submissions/DICE_HR001126S0010/render_qa_20260619_manual_clean_v5/` |
| HarborSentinel | `grant_submissions/NV063_HarborSentinel/NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.md`; `grant_submissions/NV063_HarborSentinel/NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.docx`; source memo: `grant_submissions/NV063_HarborSentinel/NV063_TECHNICAL_VOLUME_REVISED.md` | `grant_submissions/NV063_HarborSentinel/NV063_FINALIZATION_AUDIT_2026-06-19.md`; `grant_submissions/NV063_HarborSentinel/NV063_REPRESENTATIVE_DATA_AND_FORMAT_PLAN_2026-06-19.md`; `grant_submissions/NV063_HarborSentinel/NV063_DATA_SOURCE_ACCESS_AUDIT_2026-06-20.md`; `grant_submissions/NV063_HarborSentinel/NV063_AIS_PILOT_SOURCE_REGISTRY_2026-06-20.md`; `grant_submissions/NV063_HarborSentinel/NV063_AIS_PILOT_ACQUISITION_2026-06-20.md`; `grant_submissions/NV063_HarborSentinel/NV063_AIS_HELDOUT_SPLIT_MANIFEST_2026-06-20.md`; `grant_submissions/NV063_HarborSentinel/NV063_PUBLIC_AIS_GATE_2026-06-20.md`; `grant_submissions/NV063_HarborSentinel/NV063_VOLUME2_SOURCE_QA_2026-06-19.md` | `grant_submissions/NV063_HarborSentinel/NV063_COST_BASIS_WORKING.md` | `out/harbor_sentinel_validation/20260619T_NV063_V6_SOURCE_LANE_COVERAGE/`; `out/ops/harbor_data_source_readiness_audit_latest.json`; `out/ops/harbor_ais_pilot_registry_latest.json`; `out/ops/harbor_ais_pilot_acquisition_latest.json`; `out/ops/harbor_ais_heldout_splits_latest.json`; `out/ops/harbor_public_ais_gate_latest.json`; `grant_submissions/NV063_HarborSentinel/render_qa_20260619_volume2_v2/` |
| NSF Project Pitch | `grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_PORTAL_FIELDS_2026-06-19.md` | `grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_READINESS.md`; `grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_PASTE_CHECK_2026-06-19.md` | Full-proposal cost basis not yet needed for pitch | local character-count check |
| MissionWeave | `grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_CONCEPT_DRAFT.md` | `grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_FINALIZATION_AUDIT_2026-06-19.md`; `grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_BOUNDED_PROCESS_PLAN_2026-06-19.md` | `grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_COST_BASIS_WORKING.md` | `out/missionweave_validation/20260613T_MISSIONWEAVE_V3_DEV16_VAL30/` |
| NV065 | `grant_submissions/NV065_AdaptiveSensorManagement/NV065_CONCEPT_DRAFT.md` | `grant_submissions/NV065_AdaptiveSensorManagement/NV065_FINALIZATION_AUDIT_2026-06-19.md` | `grant_submissions/NV065_AdaptiveSensorManagement/NV065_COST_BASIS_WORKING.md` | `out/nv065_sensor_tasking/20260619T_NV065_SENSOR_TASKING_V2_SENSOR_PROFILE/` |

## Verification Snapshot

Verified locally on June 19, 2026:

- Full focused grant evidence refresh, run after the latest trading-safety
  hardening and before any portal submission work:
  `python -m pytest tests\test_dice_preliminary_benchmark.py tests\test_dice_constraint_contract_benchmark.py tests\test_grant_evidence_boundaries.py tests\test_harbor_sentinel_benchmark.py tests\test_harbor_sentinel_validation_suite.py tests\test_missionweave_benchmark.py tests\test_nv065_sensor_tasking_benchmark.py tests\test_geometry_championship_v1.py -q`
  produced 34 passed tests. The matching benchmark scripts also passed
  `py_compile`.
- Automated top-five readiness audit now exists at
  `grant_submissions/TOP5_SUBMISSION_READINESS_AUDIT_2026-06-19.md` with
  machine-readable output at
  `out/ops/grant_submission_readiness_audit_latest.json`. It verifies required
  package artifacts, DICE and Harbor render packets, NSF field counts, frozen
  SHA-256 manifests, the geometry registry manifest, and risky-claim boundary
  context. Latest posture: `LOCAL_READY_PORTAL_BLOCKED` with 0 local blockers
  and 23 portal/user blockers.
- DICE constraint-contract manifest matched `summary.json`, `trials.csv`, and
  `SCORECARD.md`; targeted DICE tests passed.
- Public-safe geometry/evidence-governance commit `fb97266` was pushed to
  `robertashworth1986-debug/lumen-core-public` main, and the GitHub Pages
  build completed successfully. This is operational/public evidence hygiene,
  not proof of DICE or Harbor performance.
- Public-safe dashboard/runtime hardening commit `ce09480` was pushed to
  branch `codex/public-safe-compat-20260619` on
  `robertashworth1986-debug/lumen-core-public`. The branch adds compatibility
  JSON feeds with explicit claim boundaries, bounded paper-ticker ledger
  rotation, architecture notes, and focused tests. It does not include private
  grant packets, portal material, contact details, secrets, or submission
  attachments.
- DICE DOCX structural and visual checks passed. A repaired workspace-local
  LibreOffice copy at `C:\LumaTrader\.tools\LibreOffice\program` rendered the
  abstract to a 7-page PDF in
  `grant_submissions/DICE_HR001126S0010/render_qa_20260619_manual_clean_v5/`;
  all seven page PNGs were inspected.
- DICE DOCX package cleanup passed: the regenerated working draft no longer
  carries hidden template comments, comments-extended parts, stale
  SharePoint/custom XML, custom document properties, tracked changes, or
  visible comment anchors.
- DICE DOCX reference/URL QA now exists at
  `grant_submissions/DICE_HR001126S0010/DICE_DOCX_QA_AND_REFERENCE_CHECK_2026-06-19.md`;
  12 visible URLs were extracted with no trailing punctuation, and the
  previously unlinked Friston, ReSo, and Fujimoto references now have source
  links. Follow-up source checks confirmed the two previously blocked DOI
  records using SAGE/source metadata and Crossref metadata.
- DICE bibliography style is now normalized in the generated DOCX, and the
  cover sheet/cost section identify the `$4.92 million` figure as an
  abstract-stage ROM planning estimate requiring full-proposal validation.
- DICE preliminary reference relevance matrix now exists at
  `grant_submissions/DICE_HR001126S0010/DICE_REFERENCE_RELEVANCE_MATRIX_2026-06-20.md`;
  it maps every visible external reference to supported and unsupported claim
  uses. Final human signoff still remains before upload.
- DICE submission lock packet now exists at
  `grant_submissions/DICE_HR001126S0010/DICE_SUBMISSION_LOCK_PACKET_2026-06-20.md`
  with machine-readable output at
  `out/ops/dice_submission_lock_packet_latest.json`. Latest lock posture:
  `LOCAL_LOCKED_PORTAL_BLOCKED`, 0 local blockers, 7-page render packet
  present, 12 visible URLs with no trailing URL punctuation, no placeholder
  hits, and a ROM-cost boundary present. BAAT/SAM, cost validation, final
  human signoff, upload preview, and fresh action-time approval remain gates.
- HarborSentinel v6 manifest matched `summary.json`, `scenario_summary.csv`,
  `source_lane_summary.csv`, and `SCORECARD.md`; Harbor benchmark and
  validation tests passed.
- HarborSentinel v6 adds generated source-lane coverage for AIS-like,
  ADS-B-like, and notional radar-like observations while explicitly excluding
  NOAA AIS, OpenSky ADS-B, Navy radar, SSDS, and government-furnished
  operational data.
- HarborSentinel now has an official-instruction-backed representative-data
  and format plan: public AIS through NOAA/MarineCadastre, authorized ADS-B
  through OpenSky or equivalent, generated/authorized radar-like/composite
  tracks, and Navy Volume 2 conversion under the 10-page limit.
- HarborSentinel now has a data-source access audit at
  `grant_submissions/NV063_HarborSentinel/NV063_DATA_SOURCE_ACCESS_AUDIT_2026-06-20.md`
  with machine-readable output at
  `out/ops/harbor_data_source_readiness_audit_latest.json`. It records NOAA/
  MarineCadastre AIS as the public surface-traffic lane, OpenSky or equivalent
  ADS-B as an authorization/licensing gate, and radar/composite tracks as
  generated or Navy-authorized only. Posture:
  `SOURCE_LANES_IDENTIFIED_REPRESENTATIVE_DATA_NOT_EXECUTED`.
- HarborSentinel now has an AIS pilot source registry at
  `grant_submissions/NV063_HarborSentinel/NV063_AIS_PILOT_SOURCE_REGISTRY_2026-06-20.md`
  with machine-readable output at
  `out/ops/harbor_ais_pilot_registry_latest.json`. Live HEAD probes confirmed
  NOAA daily CSV ZIP and analysis-ready GeoParquet candidates, but both remain
  blocked from auto-download by the 50 MiB size policy. Recommended raw-data
  workspace: external Glyph drive via `LUMA_HARBOR_DATA_ROOT`, with only
  manifests, hashes, schema profiles, and bounded summaries committed.
- HarborSentinel now has a public AIS pilot acquisition proof at
  `grant_submissions/NV063_HarborSentinel/NV063_AIS_PILOT_ACQUISITION_2026-06-20.md`
  with machine-readable output at
  `out/ops/harbor_ais_pilot_acquisition_latest.json`. The raw NOAA daily AIS
  ZIP is staged on `G:\LumaData\HarborSentinel\raw\noaa_ais\`, is
  290,340,871 bytes, and hashes to
  `03ed1e16f4445361d3d7cd6e0f0b4175dce4e63b0c5c8c99252728c64de9253c`.
  The profile sampled 10,000 rows and extracted the AIS schema. This is data
  acquisition proof only; held-out split generation and HarborSentinel gate
  execution remain next.
- HarborSentinel now has a frozen held-out public AIS split manifest at
  `grant_submissions/NV063_HarborSentinel/NV063_AIS_HELDOUT_SPLIT_MANIFEST_2026-06-20.md`
  with machine-readable output at
  `out/ops/harbor_ais_heldout_splits_latest.json`. The split uses the New
  Orleans / Mississippi River Delta region from the NOAA daily AIS file,
  freezes 50,000 development rows and 50,000 validation rows, and records
  split hashes.
- HarborSentinel now has a public AIS single-lane gate at
  `grant_submissions/NV063_HarborSentinel/NV063_PUBLIC_AIS_GATE_2026-06-20.md`
  with machine-readable output at
  `out/ops/harbor_public_ais_gate_latest.json`. Latest posture:
  `PUBLIC_AIS_SINGLE_LANE_GATE_READY`, with 1,046 overlapping MMSI between
  development and validation. This is public AIS data-readiness evidence, not
  HarborSentinel detection-performance, multi-source fusion, Navy/SSDS, radar,
  ADS-B, or field validation.
- HarborSentinel now also has a compact Navy Volume 2-style content source at
  `grant_submissions/NV063_HarborSentinel/NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.md`;
  a generated 6-page DOCX at
  `grant_submissions/NV063_HarborSentinel/NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.docx`
  passed local LibreOffice PDF/PNG visual QA. The source now includes Month
  1-6 milestones and success criteria. Final DSIP portal-preview review remains
  a blocker.
- HarborSentinel Volume 2 source QA is recorded at
  `grant_submissions/NV063_HarborSentinel/NV063_VOLUME2_SOURCE_QA_2026-06-19.md`;
  it now records DOCX structural cleanup, hidden custom XML sidecar removal,
  a 6-page v2 render packet, all-page PNG inspection, the milestone update,
  and a 4/4 frozen-manifest recheck.
- NSF Project Pitch fields were locally counted below official limits:
  2,852/3,500; 2,419/3,500; 1,517/1,750; 1,223/1,750 characters.
- NSF paste-check file now captures official duplicate-pitch/open-invitation
  gates and the rule that an invitation to full proposal does not imply Phase I
  funding.
- MissionWeave manifest matched `summary.json`, `scenario_summary.csv`, and
  `SCORECARD.md`; MissionWeave benchmark tests passed.
- MissionWeave now has a bounded-process assumption/evaluation contract:
  Critical Supply Exception Triage and Disposition, with no DLA-data,
  no-productivity-proof, and no-10x-claim boundaries.
- NV065 v2 manifest matched `summary.json`, `sensor_resource_profile.json`,
  `scenario_summary.csv`, and `SCORECARD.md`; NV065 benchmark tests passed.
- NV065 v2 adds a generated sensor-resource profile for SPS-48, SPQ-9B,
  MK-9, and SPY-6(V)3 while explicitly excluding radar physics, SSDS data,
  classified sensor performance, and operator workload evidence.
- `test_grant_evidence_boundaries.py` passed after the latest package updates.

Latest focused command results:

- `test_dice_constraint_contract_benchmark.py`: 4 passed.
- `test_harbor_sentinel_validation_suite.py`: 1 passed.
- `test_harbor_sentinel_benchmark.py`: 11 passed.
- `test_grant_evidence_boundaries.py`: 4 passed.
- `test_missionweave_benchmark.py`: 4 passed.
- `test_nv065_sensor_tasking_benchmark.py`: 4 passed.

Latest full focused grant rerun:

- `python -m pytest tests\test_dice_preliminary_benchmark.py tests\test_dice_constraint_contract_benchmark.py tests\test_grant_evidence_boundaries.py tests\test_harbor_sentinel_benchmark.py tests\test_harbor_sentinel_validation_suite.py tests\test_missionweave_benchmark.py tests\test_nv065_sensor_tasking_benchmark.py tests\test_geometry_championship_v1.py tests\test_grant_submission_readiness_audit.py -q`:
  37 passed.
- `python -m py_compile code\dice_preliminary_benchmark.py code\dice_constraint_contract_benchmark.py code\harbor_sentinel_benchmark.py code\harbor_sentinel_validation_suite.py code\missionweave_benchmark.py code\nv065_sensor_tasking_benchmark.py code\geometry_championship_v1.py`:
  passed.
- `python code\ops\BUILD_DICE_SUBMISSION_LOCK_PACKET.py`:
  `LOCAL_LOCKED_PORTAL_BLOCKED`, 0 local blockers, 6 portal/user blockers.
- `python code\ops\BUILD_GRANT_SUBMISSION_READINESS_AUDIT.py`:
  `LOCAL_READY_PORTAL_BLOCKED`, 0 local blockers, 23 portal/user blockers.
- `python -m pytest tests\test_grant_submission_readiness_audit.py tests\test_grant_evidence_boundaries.py -q`:
  7 passed.

Latest trading/security hygiene check:

- `code/ops/BUILD_TRADING_STACK_SAFETY_AUDIT.py` still reports `BLOCK_LIVE`
  for the local trading stack; this is the correct conservative posture while
  heartbeats, candidate quality, and user action-time approval remain
  unresolved.
- `code/ops/BUILD_TRADING_CODE_RISK_AUDIT.py` reports
  `BLOCK_LEGACY_LIVE` and identifies a safe review spine while quarantining
  legacy direct-order, liquidation, withdrawal, and validate-false paths. This
  is platform-governance evidence only. It is not grant-performance evidence,
  not a trading-profit claim, and not permission to run live orders.

Latest Harbor-focused rerun after Volume 2 DOCX render QA:

- `python -m pytest tests\test_grant_evidence_boundaries.py tests\test_harbor_sentinel_benchmark.py tests\test_harbor_sentinel_validation_suite.py`:
  16 passed.
- HarborSentinel v6 manifest recompute: 4/4 files matched byte counts and
  SHA-256 hashes.

Latest DICE-focused rerun after citation/cost regeneration:

- `python -m pytest tests\test_dice_preliminary_benchmark.py tests\test_dice_constraint_contract_benchmark.py tests\test_grant_evidence_boundaries.py`:
  9 passed.
- DICE DOCX package recheck: 33,868 bytes, 68 paragraphs, 2 tables, 1
  section, all required sections present, no hidden comments/custom
  XML/custom properties, 12 visible URLs with no trailing URL punctuation, and
  the working-draft warning remains present.
- DICE render packet recheck:
  `grant_submissions/DICE_HR001126S0010/render_qa_20260619_manual_clean_v5/`
  contains a 154,979-byte, 7-page PDF and seven inspected page PNGs.

Latest public-safe branch verification:

- Clean worktree branch: `codex/public-safe-compat-20260619`.
- Commit: `ce09480` (`Add public dashboard compatibility feeds`).
- `python -m pytest tests\test_public_dashboard_compat.py`: 2 passed,
  1 skipped locally because FastAPI is not installed in the local Python.
- `python -m py_compile code\luma_experience_gateway.py code\multi_exchange_paper_ticker.py tests\test_public_dashboard_compat.py`:
  passed.

## Evidence Boundaries To Preserve

- Synthetic benchmarks are generated software evidence, not field validation.
- Geometry Championship V1 is currently a frozen family registry and promotion
  gate, not a performance tournament; do not cite fungus, slime, bird,
  ant-trail, field, branching, or ventilation families as winners until a
  lane-specific benchmark passes the frozen validation gate. The latest
  readiness packet is
  `out/geometry_championship_v1/20260619T_GEOMETRY_READINESS_V2_EXPANDED/`.
- Do not claim SSDS integration, operational harbor/sensor performance,
  classified-environment performance, adversarial robustness, trading profit,
  medical/clinical performance, or CMMC certification from the current files.
- Do not cite Kraken, dashboard, or trading-risk audits as financial
  performance. They support fail-closed engineering discipline only.
- Cost bases are ROM planning estimates unless reviewed by qualified
  federal-contract cost support.
- Do not name collaborators, consultants, customers, pilots, or demo sites as
  committed without written permission.
- Preserve negative results: DICE high-collusion tradeoffs, Harbor severe
  stress limits, NSF V7 no-universal-edge result, MissionWeave low absolute
  combined-stress performance, and NV065 low-value-task tradeoffs.

## User-Only Gates

The user must verify or decide these; Codex can document the result after the
user reports it.

1. Legal business name, UEI, SAM.gov active status, expiration date, and CAGE
   if applicable.
2. BAAT account, organization profile, and submitter authority for DICE.
3. DSIP account, organization linkage, and submitter authority for Navy/DLA.
4. NSF account identity, founder/PI name, title, and duplicate-pitch status.
5. Whether any collaborator, consultant, customer, or reviewer can be named.
6. Whether any material is FCI, CUI, export controlled, classified, or subject
   to a sponsor-specific marking rule.
7. For DoD packages, whether SPRS/PIEE access, CMMC status/scope, and the
   Affirming Official role exist and are current.
8. Action-time consent before any upload, certification, or submit click.

## Next Action Order

1. **Fastest possible portal movement:** paste-check the NSF Project Pitch
   fields after confirming legal business name, PI/title, and duplicate-pitch
   status.
2. **Highest near-term technical value:** verify DICE reference relevance,
   BAAT authority, and optional BAAT/Word layout preview before upload while
   preserving ROM cost/evidence boundaries.
3. **DoD account prep:** log into DSIP after the June 24 opening window and
   confirm organization linkage for NV063, NV065, and DLA NV011.
4. **HarborSentinel:** execute the representative-data plan, then check the
   generated 6-page Volume 2 DOCX through the final Navy/DSIP upload preview.
5. **MissionWeave:** confirm or replace the selected Critical Supply Exception
   Triage and Disposition process, then extend the benchmark to emit a
   process-profile mapping.
6. **NV065:** review or replace the generated v2 sensor-resource archetypes,
   then add covariance-filter, latency, and measurement-cost tests.

## Do-Not-Submit Rules

- Do not submit any DoD Release 3 package before the June 24, 2026 opening
  window.
- Do not remove a working-draft warning unless the package has passed portal,
  cost, compliance, evidence, format, and human approval gates.
- Do not upload a DOCX/PDF that has not been visually checked for page limits,
  table wrapping, broken formatting, and final portal-preview behavior.
- Do not submit any certification or representation that the user has not
  personally verified.
- Do not treat Grants.gov login as sufficient for BAAT, DSIP, or NSF.

## Working Decision

The five-package strategy is credible but not yet submission-complete. The
best near-term funding sequence is NSF pitch first for speed, DICE abstract
second for strategic upside, then Navy HarborSentinel, MissionWeave, and NV065
through DSIP once the DoD window opens and compliance gates are verified.
