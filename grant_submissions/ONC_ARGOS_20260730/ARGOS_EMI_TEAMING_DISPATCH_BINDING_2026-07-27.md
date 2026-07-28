# Argos EMI Teaming Dispatch Binding

- Decision: `VERIFIED_SNAPSHOT_READY_FOR_SINGLE_USE_ACTION_TIME_APPROVAL`
- Snapshot UTC: `2026-07-27T23:28:38Z`
- Checks: `12/12` passed; `0` failed
- Send authorized: `false`
- Send performed: `false`
- Approval window: `2026-07-27T23:28:38Z` through `2026-07-27T23:33:38Z`

## Conformance Checks

| Check | Status | Requirement | Evidence |
| --- | --- | --- | --- |
| `REGISTRY_BINDING` | `PASS` | The selected teaming template and registry hashes are current. | template_id=INITIAL_PARTNER_TEAMING_INQUIRY; template_matches=1 |
| `PUBLIC_RECIPIENT_ROUTE` | `PASS` | The named organization route is public, verified, and address-redacted. | organization=EMI Advisors LLC; public_route_verified=True |
| `SUBJECT_SAFETY` | `PASS` | The exact subject is nonempty, bounded, and header-safe. | subject_chars=65; subject_sha256=80FEEDC1540F859AC970FD32A3F9DFF0E03C5B347130C7FFF2E4E24382C5993B |
| `BODY_CUSTODY` | `PASS` | The declared body bytes and SHA-256 match the committed source. | body_bytes=2067; body_sha256=A102BBD27E2BAFBA744D0FD1ADE40565F2D8A97B970A0962344E5E70776EC6E2 |
| `BODY_BOUNDARIES` | `PASS` | The body preserves the notice, qualification, no-attachment, duplicate, and nonbinding controls. | required_markers_present=True; official_notice_present=True; forbidden_promotion_phrase_count=0 |
| `DEADLINE_ORDER` | `PASS` | The snapshot precedes the partner target, which precedes the Government deadline. | generated_utc=2026-07-27T23:28:38Z; partner_target_utc=2026-07-28T17:00:00Z; government_deadline_utc=2026-07-30T21:00:00Z |
| `PRE_DRAFT_DUPLICATE_CHECK` | `PASS` | The full-mailbox preflight found no pre-existing matching message. | checked_utc=2026-07-27T19:34:13Z; matching_before_draft=0 |
| `FRESH_DUPLICATE_RECHECK` | `PASS` | The snapshot has one current draft and no sent or received duplicate. | age_seconds=0; current_drafts=1; sent_or_received=0 |
| `FRESH_DRAFT_READBACK` | `PASS` | The current Gmail draft readback matches the exact route, subject, body, and empty attachment set. | age_seconds=0; draft_present=True; sent=False |
| `ZERO_ATTACHMENT_SET` | `PASS` | The message, CC, BCC, and attachment counts are all zero. | attachments=0; cc=0; bcc=0 |
| `MESSAGE_DECLARATIONS` | `PASS` | The public gate records the official-link and duplicate disclosures. | official_notice=True; duplicate_disclosure=True |
| `FAIL_CLOSED_CONTROLS` | `PASS` | The builder cannot send and the exact approval is binding-scoped and time-limited. | builder_can_send=False; approval_window_seconds=300 |

## Exact Approval

`APPROVE ONE ARGOS TEAMING DISPATCH: recipient EMI Advisors LLC / Evelyn Gallego; template INITIAL_PARTNER_TEAMING_INQUIRY; binding SHA-256 D363D349B1E9D99F3DE3981192FB7AE4F5FE63DA3B07268E742354CF626D5B27; subject SHA-256 80FEEDC1540F859AC970FD32A3F9DFF0E03C5B347130C7FFF2E4E24382C5993B; body SHA-256 A102BBD27E2BAFBA744D0FD1ADE40565F2D8A97B970A0962344E5E70776EC6E2; attachment set SHA-256 EBD556927E470484600924709BAA4E88A21379E9163BC37AB00E4AAD4886BEA8; expires 2026-07-27T23:33:38Z.`

The displayed phrase is single-use and expires at the stated UTC time. Current mailbox and draft validation remain mandatory.

## Claim Boundary

This artifact validates one historical draft snapshot and derives a time-limited binding. It does not send email, prove current mailbox state, authorize partner-name use, certify qualifications, submit a Government response, prove receipt, or establish selection, award, funding, field performance, validation, or savings.

## Safest Next Action

At action time, repeat the full-mailbox duplicate search and Gmail draft readback, update the duplicate counts and the separate readback_checked_utc receipt, rebuild this binding, then accept only the newly displayed unexpired exact approval phrase. Do not send if any bound field changes.
