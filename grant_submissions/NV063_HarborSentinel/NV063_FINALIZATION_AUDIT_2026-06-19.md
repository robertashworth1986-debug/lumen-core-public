# NV063 HarborSentinel Finalization Audit

Date: June 19, 2026

## Scope

Opportunity: DON26BZ03-NV063, Anomalous Behavior Detection and Alerting for
Congested Maritime Environments.

Portal: Defense SBIR/STTR Innovation Portal (DSIP).

Current local deliverable:
`grant_submissions/NV063_HarborSentinel/NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.md`
and generated DOCX
`grant_submissions/NV063_HarborSentinel/NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.docx`.

Status: strong working technical draft; not approved for submission.

## Official Source Check

- Navy FY-26 Release 3 page lists the release as pre-release June 3, 2026,
  opening June 24, 2026, and closing July 22, 2026 at 12:00 p.m. Eastern Time.
- SBIR.gov topic page lists topic number DON26BZ03-NV063, solicitation 26.BZ,
  open date June 24, 2026, and due/close date July 22, 2026.
- SBIR.gov topic text states the minimum source set includes AIS, ADS-B, and
  notional radar contacts; alerts must include track details, machine
  reasoning, and confidence; solutions should avoid large historical
  pattern-of-life databases; and advanced phases may require Secret facility
  and personnel clearances.

Sources:

- https://www.navysbir.com/topics26_3.htm
- https://www.sbir.gov/topics/12759

## Current Artifact Inventory

| Artifact | Status | Notes |
|---|---|---|
| `NV063_TECHNICAL_VOLUME_REVISED.md` | Present | Rich working technical source draft. |
| `NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.md` | Present | Compact Navy Volume 2-style content source with Base/Option tasks, v6 evidence, representative-data plan, and submission boundary. |
| `NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.docx` | Present | Generated 6-page Volume 2 working DOCX; local visual QA passed. |
| `NV063_READINESS.md` | Present | Blocker register and current recommendation. |
| `NV063_COST_BASIS_WORKING.md` | Present | Planning basis only; not certified. |
| `NV063_REPRESENTATIVE_DATA_AND_FORMAT_PLAN_2026-06-19.md` | Present | Public/authorized data lanes and 10-page Volume 2 conversion plan. |
| `NV063_DATA_SOURCE_ACCESS_AUDIT_2026-06-20.md` | Present | Source-lane access/readiness audit for NOAA/MarineCadastre AIS, authorized ADS-B, and generated/authorized radar-like/composite-track lanes. |
| `NV063_AIS_PILOT_SOURCE_REGISTRY_2026-06-20.md` | Present | Live HEAD-probed NOAA/MarineCadastre AIS pilot registry; daily CSV ZIP and monthly GeoParquet candidates are real but blocked from auto-download by size policy. |
| `NV063_AIS_INJECTION_BENCHMARK_2026-06-20.md` | Present | Bounded public AIS controlled-injection benchmark on frozen held-out validation segments, including four single-axis baselines. |
| `NV063_NAVY_REVIEWER_PROOF_MATRIX_2026-06-20.md` | Present | Reviewer-facing proof/boundary matrix for Navy fit, evidence, objections, and final submission gates. |
| `NV063_VOLUME2_SOURCE_QA_2026-06-19.md` | Present | Source-length, evidence, boundary, manifest, and focused-test QA for the compact Volume 2 draft. |
| `render_qa_20260620_baselines_v1/` | Present | Latest PDF plus six page PNGs generated from the DOCX and visually inspected after adding public AIS full-hash and stronger-baseline evidence. |
| `NAVY_26BZ_PH_I_R3_INSTRUCTIONS.pdf` | Present | Local official Navy Release 3 Phase I instruction copy. |
| `docs/HARBOR_SENTINEL_VALIDATION_2026-06-13.md` | Present | Public validation memo updated with v6 source-lane evidence. |
| `out/harbor_sentinel_validation/20260619T_NV063_V6_SOURCE_LANE_COVERAGE/` | Present | Frozen v6 generated validation run with source-lane coverage. |

## Evidence Package

Canonical run:
`out/harbor_sentinel_validation/20260619T_NV063_V6_SOURCE_LANE_COVERAGE/`.

Verified on June 19, 2026:

- `summary.json`, `scenario_summary.csv`, `source_lane_summary.csv`, and
  `SCORECARD.md` are present.
- `manifest.sha256.json` matched all four frozen files.
- The scorecard preserves the synthetic-only evidence boundary.
- The v6 source-quality gate and source-lane coverage are framed as generated
  feasibility evidence, not operational degraded-sensor or sensor-feed claims.

Headline synthetic results:

- Nominal F1: 0.952.
- Combined-stress F1: 0.927.
- Severe-stress F1: 0.888.
- Nominal beacon-silence median delay: four simulation steps.
- Severe-stress behavior-based threat-candidate false alerts: 77.0 per
  10,000 normal points.
- Generated source-lane coverage: nominal AIS-like availability 0.960,
  ADS-B-like availability 1.000, radar-like availability 1.000; severe-stress
  AIS-like availability 0.904 and ADS-B-like availability 0.945.

## Proposal Strengths

- Direct topic fit: AIS, ADS-B, radar-like observations, compact
  pattern-of-life state, alerts with machine reasoning/confidence, and SSDS
  transition concept.
- Official Navy instruction extraction confirms Volume 2 must fit 10 pages,
  use single-column single-spaced 8.5 x 11 inch pages with 1-inch margins, and
  include both Base and Option work inside the Technical Volume.
- A compact Volume 2-style content source now exists, separate from the richer
  technical memo, so final DSIP formatting can start from a page-disciplined
  draft instead of the full evidence memo.
- A Volume 2 source QA note now records the 1,757-word length, v6 evidence
  alignment, explicit claim boundaries, manifest check, DOCX cleanup, 6-page
  render, visual QA, and focused test results.
- The compact Volume 2 source now includes Month 1 through Month 6 milestones
  and success criteria that distinguish reproducible Phase I evidence from
  SSDS integration, classified sensor validation, operational threat
  classification, or CMMC/clearance readiness.
- Representative-data plan and data-source access audit separate public
  NOAA/MarineCadastre AIS, ADS-B requiring written commercial/government-
  contractor authorization or equivalent licensing, and generated/authorized
  radar-like/composite-track assumptions; v6 now reports generated
  source-lane coverage without overstating SSDS or operational validation.
- AIS pilot source registry confirms two executable public NOAA/MarineCadastre
  AIS acquisition candidates by HEAD probe. The NOAA daily AIS CSV ZIP has now
  been rehydrated into local private storage, hash-matched to the previous
  external-drive acquisition, split into frozen 50,000-row development and
  50,000-row validation files, full-file SHA-256 verified for both split
  files, and run through a bounded controlled-injection benchmark with reported
  speed, derived trajectory speed, speed-gap consistency, and heading-rate
  single-axis baselines.
- A Navy reviewer proof matrix now maps each evidence claim to what it supports
  and what it does not support.
- Evidence improved a prior failure mode rather than hiding it.
- Source-integrity alerts are separated from behavior-based threat candidates.
- Negative boundaries remain explicit: no SSDS integration, field sensor
  validation, adversarial-security proof, or operational harbor performance.

## Submission Blockers

1. DSIP account, organization linkage, and submitter authority are unverified.
2. SAM.gov active status, expiration date, legal business name, UEI, and CAGE
   if applicable must be verified.
3. DoD representations, U.S. ownership/operation, foreign influence, export
   control, and cybersecurity representations are not complete.
4. The advanced-phase Secret facility/personnel clearance path is not yet
   credible enough for final submission.
5. The $315,000 cost basis is a planning estimate only and needs reviewed
   direct/indirect treatment plus consultant/subcontract scopes.
6. The compact Volume 2-style source draft has a generated 6-page DOCX with
   local visual QA passed, but the final DSIP upload/portal preview must still
   be checked after the window opens.
7. Representative public/authorized data plan, data-source access audit, AIS
   source registry, frozen public AIS split, local split cache, full-hash I/O
   preflight, and controlled-injection benchmark now exist; ADS-B,
   radar/composite-track, and any government-authorized operational evaluation
   remain unexecuted.
8. Projected CMMC Level 2 (Self), SPRS, CUI/FCI, export, FOCI, and advanced
   phase Secret clearance path remain unverified.
9. No Navy/domain reviewer has signed off on the technical approach.

## Submission Recommendation

Do not upload yet. HarborSentinel is one of the strongest technical packages
after DICE, and it now has a compact Volume 2-style source draft, latest
six-page render QA, public AIS held-out split full-hash evidence, a bounded
controlled-injection benchmark, and a Navy reviewer proof matrix. The package
still needs portal authority, compliance, clearance-transition, cost
validation, final DSIP portal-preview review, ADS-B/radar authorization paths,
and human action-time approval before submission.
