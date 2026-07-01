# Top 5 Live-Proof Submission Board

Generated UTC: 2026-06-24T19:22:40.914830+00:00

## Start Here

- Active start package: **DICE / `HR001126S0010`**
- Portal: DARPA BAAT
- Why: Closest actual submission deadline and already has bounded proposal-specific live-pulled replay evidence.
- Abstract due: 2026-06-30T18:00:00+00:00 UTC / 2026-06-30T13:00:00-05:00 Central
- Next action: Open BAAT, confirm organization association, DICE visibility, attachment rules, and preview behavior.

## Closest Action Gate

- Portal: DSIP
- Deadline: 2026-06-24T12:00:00+00:00
- Packages: HarborSentinel, MissionWeave, NV065
- Boundary: This is an action cutoff, not a captured final proposal due date.

## Live-Proof Gate

- Proposal-specific live proof: 2/5
- Passing: DICE, HarborSentinel
- Missing: NSF Project Pitch, MissionWeave, NV065
- Ready for any final submit: `False`
- Rule: No final grant submit until the exact proposal has proposal-specific live proof and portal/compliance/action-time gates pass.

## Packages

### 1. DICE / `HR001126S0010`

- Portal: DARPA BAAT
- Deadline type: actual_submission_deadline
- Primary deadline: DICE abstract due June 30, 2026 at 2:00 PM ET / 1:00 PM CT
- External source: https://files.simpler.grants.gov/opportunities/56b71085-ed91-4468-b7eb-3a04bf840794/attachments/428dc8ae-7fec-4e5f-a82f-0ccc24dfcc26/HR001126S0010.pdf
- External source note: Grants.gov-hosted BAA PDF shows DICE abstract due June 30, 2026 at 2:00 PM ET and full proposal due August 25, 2026 at 2:00 PM ET.
- Readiness: `LOCAL_READY_PORTAL_BLOCKED_USER_GATES`
- Local blockers: 0
- Portal/user blockers: 6
- Proposal-specific live proof: `True`
- Proof status: `PASS_BOUNDED_LIVE_PROOF_BUT_SUBMIT_BLOCKED`
- Evidence mode: primary_live_pulled_source_rows_with_deterministic_replay_labels
- Ready for final submit: `False`
- Evidence:
  - 6 live-pulled or previously live-fetched source files frozen for replay.
  - 14 deterministic replay windows.
  - Safe-completion mean delta 0.043650793650793655.
  - Constraint-violation mean delta -0.1215851079511806.
  - Messages-per-safe-completion mean delta -2.815708220375311.
- Boundary: Frozen live-pulled time-series replay adapter. Source rows are live-pulled or previously live-fetched operational/market signals, but task roles, risk tiers, and adversary knobs are deterministic derived labels for replay. Results do not establish DICE metric attainment, operational DoD performance, field validation, semantic correctness, or adversarial security.
- Next action: Open BAAT, confirm organization association, DICE visibility, attachment rules, and preview behavior.

### 2. HarborSentinel / `DON26BZ03-NV063`

- Portal: DSIP
- Deadline type: nearest_action_gate
- Primary deadline: DSIP TPOC Q&A closes June 24, 2026 at 12:00 UTC; proposal due must be verified in DSIP.
- External source: https://www.sbir.gov/topics/12759
- External source note: SBIR.gov copy shows open date June 24, 2026 and due/close date July 22, 2026; page says agency server is controlling.
- Readiness: `LOCAL_READY_PORTAL_BLOCKED_USER_GATES`
- Local blockers: 0
- Portal/user blockers: 5
- Proposal-specific live proof: `True`
- Proof status: `PASS_BOUNDED_PUBLIC_DATA_PROOF_BUT_SUBMIT_BLOCKED`
- Evidence mode: public_noaa_ais_heldout_split_controlled_injection
- Ready for final submit: `False`
- Evidence:
  - NOAA AIS raw source hashed: 03ed1e16f4445361d3d7cd6e0f0b4175dce4e63b0c5c8c99252728c64de9253c.
  - 20000 controlled injected validation segments.
  - Motion-consistency recall 1.0 vs speed-only baseline 0.25835.
  - Recall lift vs speed-only 0.7416499999999999.
  - Held-out validation candidate queue: 1742 candidates across 12 hours.
- Boundary: This is a held-out public AIS controlled-injection benchmark. It demonstrates that a frozen development-threshold motion-consistency detector catches injected kinematic perturbations on validation AIS segments better than multiple single-axis frozen p99 baselines. It does not establish HarborSentinel operational detection performance, real adversary detection, multi-source fusion, ADS-B/radar validation, Navy/SSDS integration, field performance, or operational suitability. This is an unlabeled public AIS review-burden profile. It estimates natural candidate queues, density context, and capped analyst-review workload from held-out validation traffic. It does not measure precision, false positives, real threat detection, multi-source fusion, ADS-B/radar performance, Navy/SSDS integration, field validation, or operational suitability.
- Next action: Open DSIP, capture topic workspace/forms, proposal window, CMMC language, and any safe TPOC Q&A path.

### 3. NSF Project Pitch / `NSF Project Pitch`

- Portal: NSF Seed Fund Project Pitch portal
- Deadline type: rolling_or_portal_state
- Primary deadline: No fixed near-term official deadline captured locally; verify duplicate/open pitch state in NSF portal.
- External source: not captured
- External source note: No current fixed NSF pitch deadline was verified in this pass.
- Readiness: `LOCAL_READY_PORTAL_BLOCKED_USER_GATES`
- Local blockers: 0
- Portal/user blockers: 4
- Proposal-specific live proof: `False`
- Proof status: `BLOCKED_MISSING_PROPOSAL_SPECIFIC_LIVE_PROOF`
- Evidence mode: local_draft_or_synthetic_evidence_only
- Ready for final submit: `False`
- Evidence:
  - Local package artifacts exist, but no proposal-specific live/public data replay or held-out benchmark is recorded for this package.
  - Add proposal-specific live/public evidence beyond draft text and SAM status.
- Boundary: Do not final-submit this package as evidence-backed until its exact proposal has a frozen input manifest, baseline comparison, leakage controls, and proposal-specific live or representative data proof.
- Next action: Create proposal-specific live proof from a bounded public workflow, customer-discovery, or reproducible market need lane before final submit.

### 4. MissionWeave / `DLA26BZ03-NV011`

- Portal: DSIP
- Deadline type: nearest_action_gate
- Primary deadline: DSIP TPOC Q&A closes June 24, 2026 at 12:00 UTC; proposal due must be verified in DSIP.
- External source: https://www.sbir.gov/topics/12778
- External source note: SBIR.gov copy shows open date June 24, 2026 and due/close date July 22, 2026; page says agency server is controlling.
- Readiness: `LOCAL_READY_PORTAL_BLOCKED_USER_GATES`
- Local blockers: 0
- Portal/user blockers: 4
- Proposal-specific live proof: `False`
- Proof status: `BLOCKED_MISSING_PROPOSAL_SPECIFIC_LIVE_PROOF`
- Evidence mode: local_draft_or_synthetic_evidence_only
- Ready for final submit: `False`
- Evidence:
  - Local package artifacts exist, but no proposal-specific live/public data replay or held-out benchmark is recorded for this package.
  - Run a representative organizational-process replay on frozen public or user-approved data.
- Boundary: Do not final-submit this package as evidence-backed until its exact proposal has a frozen input manifest, baseline comparison, leakage controls, and proposal-specific live or representative data proof.
- Next action: Open DSIP, capture topic workspace/forms and convert the draft into a representative process replay plan.

### 5. NV065 / `DON26BZ03-NV065`

- Portal: DSIP
- Deadline type: nearest_action_gate
- Primary deadline: DSIP TPOC Q&A closes June 24, 2026 at 12:00 UTC; proposal due must be verified in DSIP.
- External source: https://www.sbir.gov/topics/12761
- External source note: SBIR.gov copy shows open date June 24, 2026 and due/close date July 22, 2026; page says agency server is controlling.
- Readiness: `LOCAL_READY_PORTAL_BLOCKED_USER_GATES`
- Local blockers: 0
- Portal/user blockers: 4
- Proposal-specific live proof: `False`
- Proof status: `BLOCKED_MISSING_PROPOSAL_SPECIFIC_LIVE_PROOF`
- Evidence mode: local_draft_or_synthetic_evidence_only
- Ready for final submit: `False`
- Evidence:
  - Local package artifacts exist, but no proposal-specific live/public data replay or held-out benchmark is recorded for this package.
  - Run lane-specific live/representative sensor scheduling data against baselines before final submit.
- Boundary: Do not final-submit this package as evidence-backed until its exact proposal has a frozen input manifest, baseline comparison, leakage controls, and proposal-specific live or representative data proof.
- Next action: Open DSIP, capture topic workspace/forms and build a live or representative sensor-tasking replay lane.

## Discarded Workspaces

- `PDR-2600-DC-029Q` / workspace `WS01676964`: `DISCARD_NO_SUBMIT`
  - Title: Mass Market Solutions for Leveraging Robotics and AI Technologies for Home Construction Demonstration
  - Reason: Not part of the top-five funding path and appears to require housing/manufacturing/demo-site fit that is not currently verified.
  - Boundary: Do not delete or withdraw this cloud workspace unless the user gives exact action-time confirmation.

## Geometry Boundary

- Generated lanes: 4
- Live-breadth-backed generated lanes: 0
- Ready as live benchmark: `False`
- Kraken live execution allowed: `False`
- Boundary: Geometry generated lanes can support research direction only. They are not live-breadth proof until lane-specific frozen input manifests, replay windows, leakage controls, and baselines pass.
