# Deadline Action Sentinel

Evaluated UTC: `2026-07-27T20:14:28Z`
Posture: `HUMAN_ACTION_REQUIRED_FAIL_CLOSED`

## Control Boundary

- Read-only builder: `true`
- Autonomous email, portal, agreement, signature, certification, submission, and payment actions: `false`
- Exact action-time human approval required: `true`
- Unknown deadline time or timezone: `FAIL_CLOSED`
- External actions executed by this build: `0`

## Current Lanes

| Priority | Lane | Deadline | State | Blockers | Safest next action |
| --- | --- | --- | --- | ---: | --- |
| 1 | DAF CSDR Support and Curation CSO | July 27, 2026 at 1:00 PM EDT | `PAST_DEADLINE_NO_EXTERNAL_ACTION_AUTHORIZED` | 4 | Do not submit late or duplicate the prior capability email. Monitor only for an inbound request from the Government or a qualified prime. |
| 2 | NSF SBIR/STTR 26-510 full-proposal cycle | 2026-07-27 (time and timezone unverified) | `HUMAN_DATE_ONLY_ACTION_DUE_DATE_UNKNOWN_CUTOFF` | 3 | Do not attempt a July 27 full proposal. Select one bounded research lane and prepare a truthful Project Pitch for the November 4, 2026 cycle. |
| 3 | HHS Project Argos Sources Sought | July 30, 2026 at 5:00 PM EDT | `BLOCKED_HUMAN_ACTION_DUE` | 4 | Resolve the private cover facts and qualified teaming roles, inspect the rendered response, then perform a fresh official-notice and duplicate-send review before requesting exact approval for one bounded response. |
| 4 | Nashville cohort onboarding milestone | 2026-07-31 (time and timezone unverified) | `HUMAN_DATE_ONLY_ACTION_OPEN` | 3 | With the user present, open the official route, verify the exact cutoff and timezone, review all terms, and preserve a completion receipt. Do not accept, sign, submit, or pay autonomously. |
| 5 | Nashville cohort deposit milestone | 2026-08-14 (time and timezone unverified) | `HUMAN_DATE_ONLY_ACTION_OPEN` | 3 | After onboarding terms are accepted by the user, verify the official payment terms and destination with the user present. Do not enter payment details or pay autonomously. |

## Source Custody

- `DAF_CSDR_20260727`: `evidence/opportunity/csdr_deadline_gate_2026-07-27.json` at SHA-256 `cc578d67d891a1bed326331433af5d6b2d3d36c7078e71bb333ef17c4300d23b`; observed gate `PAST_DEADLINE_NO_LATE_OR_DUPLICATE_ACTION`.
- `NSF_26_510_20260727`: `evidence/opportunity/nsf_26_510_deadline_gate_2026-07-27.json` at SHA-256 `6c4ee6bab204851a3e1b83063e7f9e43b9e0ef41c01c67aa87d8ad7a8bd41a94`; observed gate `BLOCKED_NO_OFFICIAL_PROJECT_PITCH_INVITATION`.
- `ONC_ARGOS_20260730`: `grant_submissions/ONC_ARGOS_20260730/ARGOS_SUBMISSION_GATE_2026-07-26.json` at SHA-256 `23b05d0b44d3c2b76bd4bc2e20116baa746ccef8738805a192a348f26ee9e61b`; observed gate `BLOCK_SEND`.
- `NASHVILLE_ONBOARDING_20260731`: private official-event metadata only; source content and identifiers intentionally excluded.
- `NASHVILLE_DEPOSIT_20260814`: private official-event metadata only; source content and identifiers intentionally excluded.

## Claim Boundary

- This sentinel is a read-only deadline and blocker view.
- A warning is not authority to send, open a signed-in portal, upload, accept terms, sign, certify, submit, or pay.
- Date-only milestones never receive an invented cutoff time, timezone, exact countdown, or definitive overdue label.
- Drafted, sent, submitted, accepted, and paid remain distinct evidence states.
