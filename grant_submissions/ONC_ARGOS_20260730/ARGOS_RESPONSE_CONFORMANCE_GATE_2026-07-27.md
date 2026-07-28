# Project Argos Response Conformance Gate

Evaluated UTC: `2026-07-28T17:32:56Z`
Decision: `BLOCK_SEND_MISSING_REQUIRED_FACTS_AND_AUTHORITY`

## Summary

- Checks: `22`
- Pass: `16`
- Blocked: `6`
- Fail: `0`
- Submission authorized: `false`
- External action performed: `false`

## Requirement Matrix

| Check | Status | Requirement | Evidence |
| --- | --- | --- | --- |
| `OFFICIAL_NOTICE_CURRENT` | `PASS` | The official notice is active and its identity and deadline are explicit. | https://sam.gov/opp/062cef11f5384443bfd84bf123404026/view; checked_utc=2026-07-28T17:21:48Z; age_seconds=668; amendment_observed=False |
| `OFFICIAL_SOW_SOURCE_CUSTODY` | `PASS` | The official four-page draft SOW attachment is preserved with exact binary custody. | bytes=174359; sha256=6a1608c024bd87b0204370baab58b0a218c044d403bce6dbe0cfb5164faf6354; source_receipt_sha256=5479d7db1dc3777d9e6c177f92800bd198392105d46a2cf78c56554c86b8820d |
| `PUBLIC_REPOSITORY_CREDENTIAL_RECEIPT` | `PASS` | The current public credential configuration contains environment references only and its receipt matches the current file. | placeholder_only=True; non_placeholder_value_count=0; required_environment_references_present=True; scan_complete=True; scan_failure_count=0 |
| `PUBLIC_REPOSITORY_ROTATION_AND_HISTORY` | `BLOCKED` | Previously exposed provider credentials are rotated and prior public Git objects are remediated before the repository is linked or the final response is sent. | provider_rotations_confirmed=False; history_remediation_confirmed=False; remote_public_history_verification_confirmed=False; historical_exposure_detected=True; public_repository_link_allowed=False |
|  |  | **Blocker action** | Rotate the affected provider credentials, record non-secret receipts, remediate reachable public Git history, and verify the remote before linking the repository or sending. |
| `DEADLINE_OPEN` | `PASS` | The response is evaluated before the exact Government deadline. | evaluated=2026-07-28T17:32:56Z; deadline=2026-07-30T21:00:00Z |
| `ACCEPTED_FILES_PRESENT` | `PASS` | Both accepted review formats and their receipts are present. | docx=True; pdf=True; receipts=True |
| `ARTIFACT_HASH_CUSTODY` | `PASS` | Markdown, DOCX, and PDF hashes reconcile to the current receipts. | docx_sha256=7d17d228d88acbd06b5fb5d8aaff513bf476dd31920e9a5660ff71147145dea5; pdf_sha256=6260617bb2ae0de6d6b6817c70d3146351889db16d1c288a6edb48c8c19d0c04 |
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
| `CLAIM_EVIDENCE_TRACEABILITY` | `PASS` | Each affirmative engineering proof statement is bound to named public evidence and explicit non-claims. | claim_count=3; status=VERIFIED_BOUNDED_CLAIM_MAP; source_custody_hold=True |
| `PARTNER_OUTREACH_SENT_ONCE` | `PASS` | The bounded partner inquiry was sent exactly once without attachments, CC, or BCC and is now duplicate-locked while awaiting a reply. | drafts=0; sent=1; inbound=0; sent_copy_verified=True; duplicate_send_prohibited=True |
| `GOVERNMENT_DUPLICATE_RECHECK` | `BLOCKED` | A fresh full-mailbox duplicate check is bound to the final Government response. | last_preliminary_check=2026-07-27T19:05:00Z |
|  |  | **Blocker action** | Repeat the exact Government-response duplicate search immediately before send. |
| `FINAL_DISPATCH_BINDING` | `BLOCKED` | The final Government recipient, subject, body, and attachment set are verified together. | recipient=False; subject=False; body=False; attachments=False |
|  |  | **Blocker action** | Build and inspect the private final action packet after the cover and team gates pass. |
| `ACTION_TIME_APPROVAL` | `BLOCKED` | Single-use action-time human approval is bound to the exact Government dispatch. | approval_required=True; submission_authorized=False |
|  |  | **Blocker action** | Obtain exact action-time approval only after every other blocker is cleared. |

## Claim Boundary

PASS means the named documentary or formatting requirement is supported. BLOCKED means the current artifact is intentionally not send-ready. Neither passing checks nor a polished packet establishes submission, acceptance, selection, award, authorization, certification, external validation, field performance, or savings.

## Safest Next Action

Complete provider credential rotation and public-history remediation, then resolve the private cover and authorized-team blockers. Rebuild the private final copy, rerun this gate, repeat the official-notice and full-mailbox duplicate checks, and request exact action-time approval.
