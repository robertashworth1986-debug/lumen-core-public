# Project Argos Response Conformance Gate

Evaluated UTC: `2026-07-27T19:46:00Z`
Decision: `BLOCK_SEND_MISSING_REQUIRED_FACTS_AND_AUTHORITY`

## Summary

- Checks: `18`
- Pass: `13`
- Blocked: `5`
- Fail: `0`
- Submission authorized: `false`
- External action performed: `false`

## Requirement Matrix

| Check | Status | Requirement | Evidence |
| --- | --- | --- | --- |
| `OFFICIAL_NOTICE_CURRENT` | `PASS` | The official notice is active and its identity and deadline are explicit. | https://sam.gov/opp/062cef11f5384443bfd84bf123404026/view |
| `DEADLINE_OPEN` | `PASS` | The response is evaluated before the exact Government deadline. | evaluated=2026-07-27T19:46:00Z; deadline=2026-07-30T21:00:00Z |
| `ACCEPTED_FILES_PRESENT` | `PASS` | Both accepted review formats and their receipts are present. | docx=True; pdf=True; receipts=True |
| `ARTIFACT_HASH_CUSTODY` | `PASS` | Markdown, DOCX, and PDF hashes reconcile to the current receipts. | docx_sha256=eaf9015d1c2b003ccb8321dc30f5bca4f07a90bd16313e2bb6d2e2c57544e8b4; pdf_sha256=25d8d79e1c2f28fba0876ecbae1f78d618e6147b6f30bd040caed3acbd315173 |
| `US_LETTER_SIZE` | `PASS` | Every DOCX section uses US Letter dimensions. | sections=2; expected_twips=12240x15840 |
| `ONE_INCH_MARGINS` | `PASS` | Every DOCX section uses one-inch content margins. | sections=2; expected_twips=1440 |
| `TWELVE_POINT_TIMES_NEW_ROMAN` | `PASS` | The Normal style is Times New Roman 12 point. | font=Times New Roman; half_points=24 |
| `CONTENT_PAGE_LIMIT` | `PASS` | The response stays within ten content pages excluding the cover. | cover_pages=1; content_pages=9; limit=10 |
| `VISUAL_QA` | `PASS` | Every rendered page is inspected without clipping or overlap. | inspected_pages=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10] |
| `PRIVATE_COVER_FACTS` | `BLOCKED` | Every required cover fact is resolved and no placeholder remains. | placeholder_count=6; required_private_fact_count=9 |
|  |  | **Blocker action** | Insert only currently verified private entity and contact facts in the private final copy. |
| `AUTHORIZED_NAMED_TEAM` | `BLOCKED` | Every named team role, credential, and reference is documented and authorized. | required_teaming_fact_count=7; candidate_name_authorizations=0 |
|  |  | **Blocker action** | Obtain written partner role, name, credential, and reference authorization. |
| `NO_UNAUTHORIZED_PARTNER_NAME` | `PASS` | The Government response names no uncommitted teaming candidate. | unauthorized_names_found=[] |
| `SIMILAR_SCOPE_BOUNDARY` | `PASS` | Adjacent component evidence is not represented as federal-health prior performance. | Explicit similar-scope matrix and acquisition implications are present. |
| `CLAIM_BOUNDARIES` | `PASS` | Unsupported certification, authorization, validation, savings, and prime claims remain prohibited. | forbidden_promotion_phrases_found=[] |
| `PARTNER_DRAFT_UNSENT` | `PASS` | The bounded partner inquiry remains an unsent, no-attachment draft. | draft_present=True; sent=False; attachments=0 |
| `GOVERNMENT_DUPLICATE_RECHECK` | `BLOCKED` | A fresh full-mailbox duplicate check is bound to the final Government response. | last_preliminary_check=2026-07-27T19:05:00Z |
|  |  | **Blocker action** | Repeat the exact Government-response duplicate search immediately before send. |
| `FINAL_DISPATCH_BINDING` | `BLOCKED` | The final Government recipient, subject, body, and attachment set are verified together. | recipient=False; subject=False; body=False; attachments=False |
|  |  | **Blocker action** | Build and inspect the private final action packet after the cover and team gates pass. |
| `ACTION_TIME_APPROVAL` | `BLOCKED` | Single-use action-time human approval is bound to the exact Government dispatch. | approval_required=True; submission_authorized=False |
|  |  | **Blocker action** | Obtain exact action-time approval only after every other blocker is cleared. |

## Claim Boundary

PASS means the named documentary or formatting requirement is supported. BLOCKED means the current artifact is intentionally not send-ready. Neither passing checks nor a polished packet establishes submission, acceptance, selection, award, authorization, certification, external validation, field performance, or savings.

## Safest Next Action

Resolve the private cover and authorized-team blockers first. Then rebuild the private final copy, rerun this gate, repeat the official-notice and full-mailbox duplicate checks, and request exact action-time approval.
