# Grant Deadline Triage Board

Generated UTC: 2026-07-11T13:25:30.814556+00:00

Source posture: `LOCAL_READY_PORTAL_BLOCKED`

## Executive Read

- DICE is not a Grants.gov submit path for the abstract; it must be handled through DARPA BAAT.
- The DSIP topics are the closest time pressure because the public feed shows TPOC Q&A closing June 24, 2026 at 12:00 UTC.
- Local grant packets show no local blockers, but portal/user gates still block submit authority.
- We can use the proof packets to strengthen reviewer confidence, but we cannot turn them into field, dollar, compliance, or award-guarantee claims.

## Current Counts

- Packages tracked: 5
- Local blockers: 0
- Portal/user blockers: 23

## Official Deadlines

### DICE / HR001126S0010

- Source: `https://files.simpler.grants.gov/opportunities/56b71085-ed91-4468-b7eb-3a04bf840794/attachments/428dc8ae-7fec-4e5f-a82f-0ccc24dfcc26/HR001126S0010.pdf`
- Timescale: Eastern Time Zone (ET)
- Abstract due: Proposal Abstract Due Date: June 30, 2026 at 2:00 PM (2026-06-30T13:00:00-05:00 Central / 2026-06-30T18:00:00+00:00 UTC)
- Full proposal due: Proposal Due Date: August 25, 2026 at 2:00 PM (2026-08-25T13:00:00-05:00 Central / 2026-08-25T18:00:00+00:00 UTC)
- Submission channel: DARPA BAAT
- Boundary: The extract says abstracts must be submitted to BAAT and other channels/late submissions will not be accepted.
- Immediate action: Confirm BAAT account, organization association, DICE opportunity visibility, file requirements, and preview behavior before any upload action.

### DSIP Selected Topics

- Source: `https://www.dodsbirsttr.mil/topics-app/`
- Near-term window: TPOC Q&A closes June 24, 2026 at 12:00 UTC for the selected pre-release topics in the public feed.
- Boundary: Public topic rows show pre-release status and blank proposal due fields; verify proposal due dates inside DSIP.

- HarborSentinel / `DON26BZ03-NV063`: Anomalous Behavior Detection and Alerting for Congested Maritime Environments
  - Status: Pre-Release | Component: NAVY | Program: SBIR | CMMC: Level 2 (Self)
  - TPOC Q&A closes: 2026-06-24T12:00:00+00:00
  - Public Q&A closes: 2026-07-08T16:00:00+00:00
  - Proposal due: blank in public pre-release capture; verify in authenticated DSIP
  - Details: `https://www.dodsbirsttr.mil/topics/api/public/topics/f08fb555d7e5443989d7d3fbd0c6166f_86531/details`
- NV065 / `DON26BZ03-NV065`: Adaptive Sensor Management
  - Status: Pre-Release | Component: NAVY | Program: SBIR | CMMC: Level 2 (Self)
  - TPOC Q&A closes: 2026-06-24T12:00:00+00:00
  - Public Q&A closes: 2026-07-08T16:00:00+00:00
  - Proposal due: blank in public pre-release capture; verify in authenticated DSIP
  - Details: `https://www.dodsbirsttr.mil/topics/api/public/topics/7e471925a66649a482f05198a9448a8f_86533/details`
- MissionWeave / `DLA26BZ03-NV011`: Digital Twin of the Organization for Enhanced Mission Readiness
  - Status: Pre-Release | Component: DLA | Program: SBIR | CMMC: Level 2 (Self)
  - TPOC Q&A closes: 2026-06-24T12:00:00+00:00
  - Public Q&A closes: 2026-07-08T16:00:00+00:00
  - Proposal due: blank in public pre-release capture; verify in authenticated DSIP
  - Details: `https://www.dodsbirsttr.mil/topics/api/public/topics/b935df017cca4b63bd56bbbf6b2183e9_86535/details`

## Portal Sequence

### DARPA BAAT

- Why it matters: DICE abstracts must go through BAAT; Grants.gov is not the submit path for that abstract.
- Current state: Needs user-visible confirmation inside BAAT.
- Capture next:
  - Account can access the BAAT proposer dashboard.
  - Organization is associated with the account.
  - DICE / HR001126S0010 opportunity is visible.
  - Upload/preview rules match the local abstract packet.

### DoD SBIR/STTR DSIP

- Why it matters: NV063, NV065, and DLA26BZ03-NV011 are DSIP topic paths, not Grants.gov workspaces.
- Current state: Needs user-visible confirmation inside DSIP.
- Capture next:
  - Organization linkage and submitter role are visible.
  - Topic workspace/forms are visible for each selected topic.
  - CMMC Level 2 (Self) language is reviewed without making unsupported certification claims.
  - Proposal window and due date are captured from the authenticated portal.

### SAM.gov

- Why it matters: Entity status supports federal award eligibility, but it does not clear BAAT/DSIP authority or compliance reps.
- Current state: User reports signed in; local readiness audit records active SAM status.
- Capture next:
  - Registration remains Active.
  - Expiration date is still valid for the target submission period.
  - Assertions and reps relevant to the target opportunity are reviewed by the user.

### Grants.gov

- Why it matters: Useful for Grants.gov opportunities and AOR/workspace authority checks, but not the DICE abstract or DSIP submit path.
- Current state: User reports signed in.
- Capture next:
  - AOR/workspace role is visible for any Grants.gov-targeted opportunity.
  - No non-Grants.gov package is accidentally submitted through the wrong channel.

### PIEE / SPRS

- Why it matters: Needed only if the DoD cyber/CMMC/SPRS representation path must be verified.
- Current state: Do not enter or certify anything until factual status is known.
- Capture next:
  - Cyber Vendor User / SPRS access status.
  - CAGE hierarchy and Affirming Official path if applicable.
  - Current CMMC/SPRS status, or explicitly unknown status.

## Package Readiness

### DICE (DARPA BAAT)

- Readiness: `LOCAL_READY_PORTAL_BLOCKED_USER_GATES`
- Required artifacts: 13/13
- Evidence manifest matches: 11/11
- Render QA: True
- Local blockers: 0
- Portal/user blockers: 6
- Verified facts:
  - SAM.gov active registration verified from signed-in workspace: SAM entity identifiers recorded, purpose All Awards, expiration 2026-08-30.
  - DICE frozen live-breadth replay ready: 6 live-source files, 14 deterministic replay windows, safe-completion delta 0.043650793650793655, constraint-violation delta -0.1215851079511806, messages-per-safe-completion delta -2.815708220375311; known cost: false-rejection delta 0.051405746090874886. Boundary: live rows are stress signals with deterministic derived labels, not DICE metric attainment, field validation, or trading proof.
  - Local/iCloud legacy evidence intake ready: 8252 candidate records across local and iCloud roots, 2355 provenance records, 2225 federal-grant context records, 324 DOE/critical-infrastructure records. Boundary: metadata/provenance intake only; not field validation, performance proof, trading profit, or portal authority.
- First portal/user blockers:
  - BAAT account, organization profile, and submitter authority are unverified.
  - DICE local submission lock packet exists; portal upload and certification remain blocked.
  - Heilmeier/reviewer answer matrix exists; final human signoff is still required.
  - Preliminary reference-relevance matrix exists; final human signoff is still required.

### HarborSentinel (DSIP)

- Readiness: `LOCAL_READY_PORTAL_BLOCKED_USER_GATES`
- Required artifacts: 17/17
- Evidence manifest matches: 8/8
- Render QA: True
- Local blockers: 0
- Portal/user blockers: 5
- Verified facts:
  - SAM.gov active registration verified from signed-in workspace: SAM entity identifiers recorded, purpose All Awards, expiration 2026-08-30.
  - HarborSentinel public AIS controlled-injection benchmark ready: 20000 injected validation segments, motion-consistency recall 1.0, speed-only baseline recall 0.25835; best single-axis baseline recall 0.5068; boundary: controlled kinematic injections are not real threat labels, multi-source fusion, or field validation.
  - HarborSentinel AIS review-burden profile ready: validation candidate rate 0.03583182491360869, mean candidates/hour 145.16666666666666, p95 candidates/hour 158.7, sparse-tier candidate rate 0.1190893169877408; boundary: unlabeled review queue, not precision, false-positive rate, field validation, or operational suitability.
  - Local/iCloud legacy evidence intake ready: 8252 candidate records across local and iCloud roots, 2355 provenance records, 2225 federal-grant context records, 324 DOE/critical-infrastructure records. Boundary: metadata/provenance intake only; not field validation, performance proof, trading profit, or portal authority.
- First portal/user blockers:
  - DSIP organization linkage and submitter authority are unverified.
  - DoD representations, FOCI, export, cybersecurity, and U.S. ownership/operation checks remain.
  - CMMC/SPRS/Affirming Official status is unverified.
  - Navy reviewer proof matrix exists; final human/domain signoff is still required.

### NSF Project Pitch (NSF Seed Fund Project Pitch portal)

- Readiness: `LOCAL_READY_PORTAL_BLOCKED_USER_GATES`
- Required artifacts: 3/3
- Evidence manifest matches: 0/0
- Render QA: None
- Local blockers: 0
- Portal/user blockers: 4
- Verified facts:
  - SAM.gov active registration verified from signed-in workspace: SAM entity identifiers recorded, purpose All Awards, expiration 2026-08-30.
- First portal/user blockers:
  - Legal business name and PI/founder title must be confirmed.
  - Duplicate-pitch/open-invitation/full-proposal status must be checked in the portal.
  - Portal paste counts must be confirmed after the user logs in.
  - Fresh action-time approval is required before final save/submit actions.

### MissionWeave (DSIP)

- Readiness: `LOCAL_READY_PORTAL_BLOCKED_USER_GATES`
- Required artifacts: 4/4
- Evidence manifest matches: 3/3
- Render QA: None
- Local blockers: 0
- Portal/user blockers: 4
- Verified facts:
  - SAM.gov active registration verified from signed-in workspace: SAM entity identifiers recorded, purpose All Awards, expiration 2026-08-30.
- First portal/user blockers:
  - Selected bounded process needs user/domain confirmation.
  - DSIP topic budget/form requirements and organization linkage are unverified.
  - Representative-data path and DLA-domain review are not complete.
  - Fresh action-time approval is required before any upload or submit action.

### NV065 (DSIP)

- Readiness: `LOCAL_READY_PORTAL_BLOCKED_USER_GATES`
- Required artifacts: 3/3
- Evidence manifest matches: 4/4
- Render QA: None
- Local blockers: 0
- Portal/user blockers: 4
- Verified facts:
  - SAM.gov active registration verified from signed-in workspace: SAM entity identifiers recorded, purpose All Awards, expiration 2026-08-30.
- First portal/user blockers:
  - Representative radar-resource assumptions need sensor-domain review.
  - DSIP account, organization linkage, and compliance gates are unverified.
  - Cost basis is a ROM planning estimate only.
  - Fresh action-time approval is required before any upload or submit action.

## Evidence To Use

- Public visibility packet available: True
- Public visibility proof claims: 7
- Geometry families tracked: 140
- Generated benchmark lanes: 4
- Proof-build champion: branching_transport / crack_propagation_paths
- Generated-lane champion: optimal_curve_transport / brachistochrone_descent (score delta 0.178449)
- Geometry boundary: Use as bounded proof-building support for reviewers. Do not present generated geometry winners as field validation, safety validation, or dollar-value proof.

## Live-Proof Submission Gate

- Available: True
- Active start package: DICE
- Active start deadline UTC: 2026-06-30T18:00:00+00:00
- Closest action gate: DSIP / 2026-06-24T12:00:00+00:00
- Proposal-specific live proof: 2/5
- Missing live proof: NSF Project Pitch, MissionWeave, NV065
- Ready for any final submit: `False`
- Rule: No final grant submit until the exact proposal has proposal-specific live proof and portal/compliance/action-time gates pass.

## Discarded Workspaces

- `PDR-2600-DC-029Q` / `WS01676964`: `DISCARD_NO_SUBMIT`
  - Reason: Not part of the top-five funding path and appears to require housing/manufacturing/demo-site fit that is not currently verified.
  - Boundary: Do not delete or withdraw this cloud workspace unless the user gives exact action-time confirmation.

## Tonight Action Order

- Inside DSIP: capture proposal-window fields and, if still open, any TPOC Q&A opportunity for NV063/NV065/DLA26BZ03-NV011 before the June 24 cutoff.
- Inside BAAT: confirm DICE / HR001126S0010 opportunity visibility and attachment preview rules for the June 30 abstract deadline.
- Inside SAM.gov: confirm Active Registration and expiration remain valid; do not expose identifiers or tax details in the packet.
- Inside Grants.gov: confirm AOR/workspace authority only for packages that actually submit through Grants.gov.
- Run final local package tests and render/manifest checks before any portal upload preview.

## Safety Boundaries

- No upload, certification, consent, signature, workspace lock, or submission is authorized by this board.
- Do not affirm CMMC, SPRS, cybersecurity, FOCI, export, ownership, facility, partner, demo-site, or cost representations unless the user verifies the fact at action time.
- Geometry, live-breadth, synthetic, public-data, and controlled-injection results are proof-building evidence only unless a field-validation gate explicitly passes.
- Dollar-value and award-likelihood claims remain blocked unless a separate dollar claim gate passes with real measured data and reviewed assumptions.

## Submit Gate

- Ready for submit: `False`
- Why: Local artifacts are ready, but authenticated portal authority, compliance representations, preview checks, and action-time approval remain open.
- Required user phrase at action time: `I approve this exact upload/submit action now.`
