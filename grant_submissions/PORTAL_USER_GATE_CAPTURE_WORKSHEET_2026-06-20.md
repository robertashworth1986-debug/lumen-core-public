# Portal User-Gate Capture Worksheet

Date: June 20, 2026 UTC

Purpose: convert the remaining submission blockers into safe, non-secret facts
the user can verify while logged into each portal. This worksheet is not legal
advice, a cybersecurity certification, a cost certification, or authorization
to submit.

## Safety Rule

Record status facts only. Do not record passwords, MFA/OTP codes, API keys,
banking details, tax IDs, private account tokens, payment screens, or
screenshots containing sensitive personal/business data.

## Minimum Facts To Capture

| Gate | Facts to capture | Unlocks | Do not capture |
|---|---|---|---|
| SAM.gov | Legal entity name, active/inactive status, expiration date, UEI, CAGE if assigned, entity administrator status, whether reps/certs appear current. | DICE BAAT linkage, DSIP organization linkage, federal award eligibility checks. | TIN/EIN, banking details, login credentials, full private profile screenshots. |
| DARPA BAAT | Whether organization exists, whether user is associated with it, role/submitter authority, DICE opportunity visibility, required abstract fields, allowed file types, upload/preview behavior. | DICE upload readiness and final portal format check. | Passwords, MFA, private profile details unrelated to DICE. |
| DSIP | Organization linkage, user role, submitter authority, Release 3 topic visibility, required volumes, budget/forms visible, attachment preview behavior, certification pages present. | HarborSentinel, MissionWeave, NV065 upload readiness. | Passwords, MFA, private tokens, certification clicks without action-time approval. |
| NSF Project Pitch | Account identity, company name, PI/founder name/title, duplicate-pitch status, open invitation/full-proposal status, field character counts after paste. | Fastest low-friction funding path. | Passwords, MFA, personal identifiers beyond portal-required application data. |
| SPRS/PIEE | PIEE account exists, SPRS Cyber Vendor User role exists, CAGE hierarchy visible/imported from SAM, Affirming Official identity/status, whether any CMMC score/status/UID is already recorded, expiration/affirmation date if shown. | DoD cybersecurity representation readiness. | Control evidence screenshots, scores, or affirmations unless reviewed by a CMMC advisor and Affirming Official. |
| CMMC Level 2 path | Scope boundary, whether Level 2 Self or C3PAO applies for the specific topic/award, whether POA&M/conditional path is relevant, who can be Affirming Official. | Prevents unsupported CMMC claims in DoD submissions. | Claiming certification/status not actually current. |
| Teaming | Whether a collaborator/consultant/customer can be named, written permission status, proposed role, conflict/export/security constraints. | DICE full proposal strength and DoD package credibility. | Names as committed without written permission. |
| Cost | Whether rates/fringe/indirect treatment, consultant scopes, cloud quotes, travel, and materials are reviewed by qualified cost support. | Converts ROM planning estimates into defensible proposal budgets. | Presenting ROM as certified cost. |

## Package-Specific Capture

### DICE / DARPA BAAT

- BAAT login successful: `yes/no`
- Organization profile visible: `yes/no`
- User submitter authority: `yes/no/unclear`
- DICE opportunity visible: `yes/no`
- Abstract upload file type accepted: `docx/pdf/other`
- Portal preview checked: `yes/no`
- Working draft warning intentionally retained until final approval: `yes/no`
- Final human reference-relevance signoff completed:
  `yes/no`; source:
  `grant_submissions/DICE_HR001126S0010/DICE_REFERENCE_RELEVANCE_MATRIX_2026-06-20.md`
- Cost boundary accepted as ROM only: `yes/no`
- Fresh action-time approval before upload/submit: `required`

### Navy NV063 HarborSentinel / DSIP

- DSIP Release 3 visible after opening window: `yes/no`
- Organization linked: `yes/no`
- User submitter authority: `yes/no/unclear`
- NV063 topic visible: `yes/no`
- Volume 2 upload preview checked: `yes/no`
- Representative-data plan execution status: `not started/public AIS/authorized ADS-B/generated radar-like/completed`
- DoD reps/FOCI/export/cybersecurity pages reviewed by user: `yes/no`
- CMMC/SPRS/AO path verified: `yes/no`
- Secret clearance transition narrative reviewed: `yes/no`
- Fresh action-time approval before upload/submit: `required`

### NSF Project Pitch

- Legal company name confirmed: `yes/no`
- PI/founder name and title confirmed: `yes/no`
- Duplicate-pitch status checked: `yes/no`
- Open invitation/full-proposal status checked: `yes/no`
- Portal paste counts checked:
  - Technology Innovation: `____ / 3500`
  - Technical Objectives and Challenges: `____ / 3500`
  - Market Opportunity: `____ / 1750`
  - Company and Team: `____ / 1750`
- Fresh action-time approval before final save/submit: `required`

### MissionWeave / DSIP

- DLA topic visible: `yes/no`
- Bounded process confirmed or replaced: `yes/no`
- DSIP budget/form requirements known: `yes/no`
- Domain reviewer or process owner available: `yes/no`
- Representative-data path credible: `yes/no`
- Fresh action-time approval before upload/submit: `required`

### NV065 / DSIP

- NV065 topic visible: `yes/no`
- Sensor-resource assumptions reviewed by domain-informed person: `yes/no`
- Cost basis reviewed: `yes/no`
- CMMC/SPRS/compliance path verified: `yes/no`
- Fresh action-time approval before upload/submit: `required`

## Current Decision

Local package readiness is clean, but the submissions are not complete until
the portal/user facts above are verified. Codex can help navigate, compare,
paste, and record safe status facts after login; Codex must not click submit,
certify, sign, consent, final upload, lock workspace, or affirm any
representation without fresh action-time approval.
