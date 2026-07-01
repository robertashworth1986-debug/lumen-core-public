# LumenCore Submission Blocker Board

Date: June 19, 2026

Purpose: keep the highest-fit packages moving without pretending that portal,
compliance, teaming, or evidence gaps are solved.

Control room:
`grant_submissions/TOP5_SUBMISSION_CONTROL_ROOM_2026-06-19.md`

Portal/compliance matrix:
`grant_submissions/PORTAL_COMPLIANCE_ACTION_MATRIX_2026-06-19.md`

Portal/user-gate capture worksheet:
`grant_submissions/PORTAL_USER_GATE_CAPTURE_WORKSHEET_2026-06-20.md`

Action-time submission board:
`grant_submissions/ACTION_TIME_SUBMISSION_BOARD_2026-06-20.md`

## Executive Queue

| Rank | Package | Window | Current posture | Submit only when |
|---:|---|---|---|---|
| 1 | DARPA DICE HR001126S0010 | Abstract due June 30, 2026 at 2:00 p.m. ET | Strongest near-term fit; working DOCX package cleanup, normalized citations, ROM cost wording, local submission lock packet, and local 7-page visual render QA passed | BAAT access, final portal/Word preview, reference relevance, cost boundary, and human approval clear |
| 2 | Navy NV063 HarborSentinel | Opens June 24, closes July 22, 2026 at 12:00 p.m. ET | Strong topic-specific synthetic evidence; finalization audit, ROM cost basis, representative-data/format plan, data-source access audit, AIS pilot source registry, raw NOAA AIS acquisition/hash/profile, held-out public AIS split, single-lane AIS readiness gate, local split-cache recovery, current AIS split I/O preflight, bounded controlled-injection benchmark, Month 1-6 success gates, and local 6-page Volume 2 DOCX visual QA now exist | DSIP authority, reviewed cost basis, DoD reps, CMMC/SPRS/FOCI/export checks, clearance plan, ADS-B licensing/authorization, and final portal preview clear |
| 3 | NSF SBIR Project Pitch | Rolling | Portal-ready fields drafted and counted; no demo site or research partner required for pitch | Legal business name, PI/title consistency, duplicate-pitch check, and portal paste-count check clear |
| 4 | DLA NV011 MissionWeave | Opens June 24, closes July 22, 2026 | Good software fit; generated-workflow benchmark, finalization audit, ROM cost basis, and bounded-process assumption now exist | Confirmed process, representative-data/domain-review plan, and DSIP-confirmed budget are credible |
| 5 | Navy NV065 Adaptive Sensor Management | Opens June 24, closes July 22, 2026 | Topic-specific v2 benchmark with sensor-resource profile, finalization audit, and $315,000 ROM cost basis now exist | DSIP/compliance gates, reviewed cost basis, sensor-domain review, and approved representative radar-resource model clear |

Reserve: Navy NV061 TrackCast remains relevant but should not outrank NV065
until a trajectory-specific benchmark beats or responsibly abstains against
kinematic and historical-pattern baselines.

## Cross-Cutting Submission Gates

### Portal and Authority

- SAM.gov active registration is verified from the signed-in workspace:
  legal/entity name visible, UEI and CAGE/NCAGE recorded in the private local
  SAM capture, purpose is `All Awards`, and expiration is `2026-08-30`.
  Monitor renewal timing and do not treat this as BAAT/DSIP submitter authority.
- Verify BAAT access for DARPA DICE.
- Verify DSIP account, organization linkage, and submitter authority before
  DoD SBIR uploads.
- Verify Research.gov/NSF account identity before NSF full-proposal work.
- Verify SPRS/PIEE access, Affirming Official status, and any recorded CMMC
  score/status/UID before making DoD cybersecurity representations.
- Verify the `SPRS Cyber Vendor User` role and SAM-imported CAGE hierarchy
  before attempting any Level 2 self-assessment entry.
- Codex must receive action-time confirmation before clicking consent,
  upload, certification, or submit controls.

### Compliance and Security

- Keep all current packages Unclassified and free of CUI unless an authorized
  source marks material otherwise.
- Do not claim CMMC Level 2, facility clearance, personnel clearance, SPRS
  score, or export-control determination without current evidence.
- Do not affirm a CMMC assessment, SPRS status, or cybersecurity
  representation unless the company Affirming Official has reviewed the
  evidence and personally approves the statement at action time.
- For DoD packages, complete foreign ownership/control/influence,
  cybersecurity, export-control, and U.S. ownership/operation checks.
- Use the CMMC readiness file as an enclave plan, not as a representation of
  certification.

### Patent / IP Protection

- Treat the non-provisional deadline as a funding-risk gate, not a side quest.
- Use `PATENT_LEGAL_RESCUE_PACKET_2026-06-20.md` to contact patent pro bono,
  law-clinic, or reduced-fee counsel immediately.
- Before publishing new claim-critical details, confirm whether the material is
  already supported by the provisional, needs a new provisional, or should be
  held back until counsel reviews.
- Required user facts: provisional application number, filing date, title,
  filing receipt, current claims, public-disclosure list, and any co-inventor
  or contributor facts.

### Evidence and Claims

- Do not claim operational, classified, medical, harbor, SSDS, adversarial,
  trading-profit, or field performance from synthetic benchmarks.
- Do not cite Kraken, dashboard, live-breadth, frozen-delta, or trading-risk
  audits as proof of profitability, institutional-grade execution, or funding
  performance. Current audits support fail-closed governance only and still
  block legacy live paths.
- Preserve negative results and failure modes in every proposal.
- Every cited benchmark needs a frozen run directory, manifest, scorecard,
  source file, test file, and claim-boundary paragraph.
- Any fifth DoD package must get its own topic-specific benchmark before
  portal entry.

### Teaming and Cost

- DICE needs at least one credible distributed-systems/consensus collaborator
  target and one inference-control/AI-safety collaborator target before full
  proposal.
- Harbor/Navy packages need a realistic advanced-phase Secret
  facility/personnel clearance transition plan.
- Cost bases are ROM planning estimates until rates, fringe/indirect bases,
  consultant scopes, cloud quotes, and travel assumptions are reviewed.
- Do not name collaborators, consultants, or subcontractors as committed
  without written permission.

## Tonight's Useful Work

0. Refresh cross-package verification:
   - completed: focused grant evidence/test suite across DICE, HarborSentinel,
     MissionWeave, NV065, geometry registry, and evidence boundaries returned
     34 passed tests;
   - completed: expanded focused suite including the new top-five readiness
     audit returned 37 passed tests;
   - completed: matching benchmark scripts passed `py_compile`;
   - completed: automated top-five readiness audit returned
     `LOCAL_READY_PORTAL_BLOCKED`, 0 local blockers, and 23 portal/user
     blockers after verifying required artifacts, render packets, NSF field
     counts, frozen manifests, and claim-boundary context;
   - completed: SAM.gov active registration was verified from the signed-in
     workspace, which cleared only the SAM entity-status uncertainty and did
     not clear BAAT/DSIP submit authority, CMMC/SPRS, cost, or action-time
     approval gates;
   - completed: DICE preliminary reference-relevance matrix added at
     `grant_submissions/DICE_HR001126S0010/DICE_REFERENCE_RELEVANCE_MATRIX_2026-06-20.md`;
   - completed: DICE Heilmeier/reviewer answer matrix added at
     `grant_submissions/DICE_HR001126S0010/DICE_HEILMEIER_REVIEWER_MATRIX_2026-06-20.md`;
     this gives the reviewer one grounded answer surface for the technical bet,
     evidence map, objections, baseline metrics, and no-overclaim boundaries;
   - completed: portal/user-gate capture worksheet added at
     `grant_submissions/PORTAL_USER_GATE_CAPTURE_WORKSHEET_2026-06-20.md`;
   - completed: submission gate evidence ledger added at
     `grant_submissions/SUBMISSION_GATE_EVIDENCE_LEDGER_2026-06-20.md`;
     this converts BAAT, DSIP, CMMC/SPRS, cost, team/domain signoff, and
     action-time approval blockers into exact evidence gates.
   - completed: trading stack audit remains `BLOCK_LIVE`, and source-code risk
     audit remains `BLOCK_LEGACY_LIVE`, which keeps money-moving legacy code
     out of any grant or live-execution claim path.
1. Finalize DICE abstract review package:
   - completed: local LibreOffice render produced a 7-page PDF and all seven
     page PNGs were visually inspected;
   - completed: package cleanup removed hidden template comments/custom XML;
   - completed: generated citation style normalized and cost language marked
     as abstract-stage ROM;
   - completed: local submission lock packet returned
     `LOCAL_LOCKED_PORTAL_BLOCKED`, 0 local blockers, 7-page render packet
     present, 12 visible URLs with no trailing URL punctuation, no placeholder
     hits, and ROM-cost boundary present;
   - remaining: optionally preview in Word/BAAT and review final reference
     relevance;
   - remaining: keep `WORKING DRAFT` until portal/cost/human approval clear.
2. Prepare BAAT and DSIP account verification:
   - login only by the user;
   - record organization linkage status and submitter authority;
   - do not submit anything during discovery.
3. Convert NSF Project Pitch into the fastest cash-path package:
   - completed: trustworthy-AI primary topic selected;
   - completed: four portal-ready fields drafted and counted;
   - completed: portal paste-check and duplicate-pitch gates documented;
   - remaining: portal paste-check the four NSF fields;
   - avoid universal harmonic or trading-performance claims.
4. Strengthen NV063:
   - completed: v6 source-quality gate and generated source-lane coverage
     evidence carried into the working technical volume;
   - completed: topic traceability, finalization audit, and ROM cost basis;
   - completed: official-instruction-backed representative-data and format
     plan;
   - completed: data-source access audit identifying NOAA/MarineCadastre AIS,
     ADS-B authorization/licensing, and generated/authorized radar/composite
     lanes while preserving no-field-validation boundaries;
   - completed: AIS pilot source registry with live HEAD probes for NOAA daily
     CSV ZIP and analysis-ready GeoParquet candidates; both are blocked from
     auto-download by size policy and should be stored on the Glyph/external
     raw-data drive before scoring;
   - completed: raw NOAA daily AIS ZIP acquired on `G:\LumaData\HarborSentinel`,
     SHA-256 hashed, and schema-profiled over a 10,000-row sample;
   - completed: held-out public AIS development/validation splits frozen for
     the New Orleans / Mississippi River Delta region with 50,000 rows in each
     split;
   - completed: public AIS single-lane gate returned
     `PUBLIC_AIS_SINGLE_LANE_GATE_READY`, with 1,046 overlapping MMSI and
     frozen development-derived diagnostics applied to validation;
   - completed: AIS split I/O preflight builder and dashboard-safe summary
     added;
   - completed: external-drive split paths later resolved as missing, so the
     NOAA daily AIS ZIP was rehydrated into local private `out/private_data`
     storage, rebuilt using the same deterministic New Orleans / Mississippi
     River Delta split rules, and verified to match the original frozen split
     SHA-256 values;
   - completed: refreshed AIS split I/O preflight returned
     `PUBLIC_AIS_SPLIT_IO_READY`, 2/2 required split files readable;
   - completed: local split-cache recovery returned
     `PUBLIC_AIS_LOCAL_SPLIT_CACHE_READY`, 2/2 required files hash-matched;
   - completed: controlled public AIS injection benchmark returned
     `PUBLIC_AIS_INJECTION_BENCHMARK_READY`: 48,624 development segments,
     48,616 validation segments, 20,000 injected validation segments,
     motion-consistency recall 1.0000 vs speed-only baseline recall 0.25835
     and recall lift 0.74165;
   - completed: generated 6-page Volume 2 DOCX passed local LibreOffice
     PDF/PNG visual QA;
   - completed: added Month 1-6 milestones and success criteria while
     preserving synthetic-only and no-SSDS-integration boundaries;
   - completed: HarborSentinel proposal/reviewer language now cites the
     controlled-injection result only as a bounded public AIS
     detector-vs-baseline benchmark, including the best current single-axis
     baseline, without claiming real adversary detection, multi-source fusion,
     Navy/SSDS integration, or field validation;
   - remaining: confirm final DSIP upload preview after the window opens.
5. Strengthen MissionWeave:
   - completed: bounded unclassified process assumption drafted for Critical
     Supply Exception Triage and Disposition;
   - remaining: confirm or replace the process with user/domain review;
   - remaining: emit process-profile mapping in the next public-safe benchmark
     packet.
6. Build one fifth-package benchmark:
   - completed: NV065 constrained sensor-tasking simulation using marginal
     contribution, generated source quality, confirmation release, and human
     review boundary;
   - completed: generated sensor-resource profile for SPS-48, SPQ-9B, MK-9,
     and SPY-6(V)3 added to the v2 evidence packet;
   - next: decide whether to freeze a TrackCast trajectory benchmark as a
     sixth package or keep TrackCast in reserve.

## Current Do-Not-Submit Conditions

- Any package that claims a partner, demo site, clearance, certification, or
  field result that is not actually verified.
- Any DoD Release 3 package before the June 24 opening window.
- Any package with unresolved placeholders, unverified portal authority, or a
  cost number presented as certified when it is only a planning estimate.
- Any package whose local DOCX/PDF visual QA has passed but whose portal upload
  preview has not been checked by the user.
- Any package that relies on trading, Kraken, frozen-delta, dashboard, or
  live-breadth evidence as a financial outcome claim rather than as bounded
  software-governance evidence.
- Any HarborSentinel package language that presents controlled-injection
  detector evidence as real adversary detection, ADS-B/radar validation,
  multi-source fusion, Navy/SSDS integration, operational suitability, or field
  performance.
