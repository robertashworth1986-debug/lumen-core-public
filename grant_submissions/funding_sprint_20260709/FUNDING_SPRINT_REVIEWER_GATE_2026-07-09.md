# Funding Sprint Reviewer Gate - 2026-07-09

Purpose: machine-check the active funding sprint before agency, investor, or partner use.

This gate does not authorize final submission. It confirms the packet is organized, hashed, and free of unbounded claim/secret hits under the current scanner.

## Gate Status

- Status: `REVIEWER_GATE_CLEAR_HUMAN_SUBMISSION_REQUIRED`
- Reviewer gate clear: `true`
- Markdown files scanned: `41`
- Proof cards: `6`
- Unsafe secret hits: `0`
- Unsafe claim hits: `0`
- Boundary/blocked-language hits: `54`
- Autonomous external action allowed: `false`
- Live trading allowed: `false`
- Final submission without human allowed: `false`
- Gate SHA-256: `6cf0b05c11a5b8900b97f56cdceb6bff3fb61f0f1bc63036daed4b8f327a5885`

## Reviewer Proof Cards

### Air Force Advanced Automation Contract RFI

- Deadline: `2026-07-13`
- Source: https://sam.gov/opp/3fa15f166ec244539c808be5c0496427/view
- Artifact: `AIR_FORCE_AAC_RFI_CAPABILITY_STATEMENT_2026-07-09.md`
- Artifact present: `true`
- Artifact SHA-256: `8d44ce2a3e555ec99a6c6d82a904933b1f09196fa6f8b516b6c05b4cab935aab`
- Reviewer posture: `ready_for_human_review`
- Next gate: Verify SAM attachments, response address, page limit, and time zone before sending.
- Claim boundary: RFI response only; not a contract award or operational deployment.
- Human gate: Human approval before email/submission.
- Card SHA-256: `8c978900d26c1bf870ccb0ee1baccda5ee3122be5b1b91ae5c893b3a9bded1da`

### NASA Data Center Infrastructure RFI

- Deadline: `2026-07-17`
- Source: https://sam.gov/workspace/contract/opp/b6d14a4b9eac476b997894d0c5a47a27/view
- Artifact: `NASA_DATA_CENTER_RFI_RESPONSE_OUTLINE_2026-07-09.md`
- Artifact present: `true`
- Artifact SHA-256: `bcfdd40dfafc7ca0e7822679dba9d2504c2196b5701704d0ba3d46c5ce9448f6`
- Reviewer posture: `ready_for_human_review`
- Next gate: Verify official SAM response instructions and build final PDF.
- Claim boundary: No NASA operational claim, energy-savings claim, or infrastructure deployment claim.
- Human gate: Human approval before response submission.
- Card SHA-256: `ca0815e7fe0216ff861590a7429a97adc04a11253799b4848dae4ebe12120453`

### DLA MissionWeave DSIP SBIR

- Deadline: `2026-07-22`
- Source: https://www.sbir.gov/topics/12778
- Artifact: `DSIP_MISSIONWEAVE_FAST_SUBMISSION_PLAN_2026-07-09.md`
- Artifact present: `true`
- Artifact SHA-256: `cf0d3fd466ecfd8396d17f1c4787a7fa2898f49ee5f81ed377df05aa161029c4`
- Reviewer posture: `ready_for_human_review`
- Next gate: Robert enters Firm PIN directly; then inspect DSIP org authority, certs, cost, and upload preview.
- Claim boundary: No DLA integration, certified readiness, or 10x productivity claim.
- Human gate: Human-only Firm PIN, certifications, cost approval, and final submit.
- Card SHA-256: `a4e2f2d5007f6bf55f2c5081689010eaadaf7c9ecd73f4f5827ece411c3704af`

### FHWA TSMO Data Initiative

- Deadline: `2026-08-03`
- Source: https://sam.gov/opp/82cfdcdb95ae40a7b70dba615c31f89b/view
- Artifact: `FHWA_TSMO_PHASE1_TECHNICAL_CAPABILITY_OUTLINE_2026-07-09.md`
- Artifact present: `true`
- Artifact SHA-256: `f6d090ccc82b6564449476be4c348b21f92554ffad9abe90dbb863744ebfa046`
- Reviewer posture: `ready_for_human_review`
- Next gate: Download SAM package, build compliance matrix, decide prime-vs-team posture.
- Claim boundary: No FHWA field validation, safety benefit, or traffic operations deployment claim.
- Human gate: Human approval before pricing, reps/certs, or submission.
- Card SHA-256: `b5466497b05782a87f0624dbd202d48a6732af4baa3c269b0d4c982ee91e53ae`

### DOE Advanced Nuclear Licensing Cost-Share

- Deadline: `2026-09-30`
- Source: https://www.fedconnect.net/FedConnect/default.aspx?ReturnUrl=%2Ffedconnect%2F%3Fdoc%3DDE-FOA-0003339%26agency%3DDOE&agency=DOE&doc=DE-FOA-0003339
- Artifact: `NUCLEAR_LICENSING_EVIDENCE_PARTNER_ONE_PAGER_2026-07-09.md`
- Artifact present: `true`
- Artifact SHA-256: `5d95bca13c79ed450a91e9330729106969e6c9b28fd6557e9c80d52f509c5b41`
- Reviewer posture: `ready_for_human_review`
- Next gate: Qualified nuclear/licensing applicant or full NOFO review before any solo-prime action.
- Claim boundary: Partner-first; no NRC licensing authority, reactor safety validation, nuclear QA, or plant performance claim.
- Human gate: Human approval before partner outreach or FedConnect action.
- Card SHA-256: `8b8611f5847e39fa30430494e75249db28e6fca63e470f32c09d2cd66ad4172f`

### NSF SBIR/STTR Project Pitch

- Deadline: `rolling_invitation_gate`
- Source: https://seedfund.nsf.gov/project-pitch/
- Artifact: `NSF_PROJECT_PITCH_DRAFT_2026-07-09.md`
- Artifact present: `true`
- Artifact SHA-256: `baa66ab948fdc1bb57e898d8a6e4e0bf776c65ff4c6722ef658720c148f40e6f`
- Reviewer posture: `ready_for_human_review`
- Next gate: Check NSF login and one-pending-pitch rule before submitting.
- Claim boundary: Full proposal remains invitation-gated; no invitation is represented unless issued by NSF.
- Human gate: Human approval before Project Pitch submit.
- Card SHA-256: `3e91f984f177a288262762f5f648c1e76abd9ff683a6f8d45e0bbfef11e02e50`

## Claim Policy

Allowed language:

- proof-to-pilot AI infrastructure validation
- source provenance
- baseline-vs-candidate replay
- hash-verified public proof-feed deployment
- 29-source inventory with 25 measured providers
- human-gated agency submission

Blocked language unless explicitly negated or bounded:

- field validated
- realized savings
- guaranteed award
- guaranteed returns
- certified assurance
- cmmc certified
- nuclear licensing authority
- medical efficacy
- airworthiness
- operational government deployment
- live profit
- risk-free
- autonomous trading system ready
- freedom to operate
- patented

## Scan Notes

Boundary hits are expected when a file says not to use a risky phrase. They remain listed in JSON for audit, but they do not block the gate.

Any unsafe secret or claim hit blocks agency use until removed or rewritten as explicit boundary language.

## Human Submission Rule

No portal submission, email send, certification, affirmation, pricing, Firm PIN entry, IP filing, live trading, or capital movement is authorized by this gate.
