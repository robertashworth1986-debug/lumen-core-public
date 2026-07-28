# Project Argos Sources Sought Response

Status: `DRAFT_REVIEW_READY_NOT_SEND_READY`

This directory contains a bounded, standalone small-business capability response for:

- Notice: `ONC-ARGOS-SSN-2026-OS351107`
- Type: Sources Sought / market research
- Agency: U.S. Department of Health and Human Services
- Response deadline: July 30, 2026 at 5:00 PM Eastern
- Official notice: <https://sam.gov/opp/062cef11f5384443bfd84bf123404026/view>
- Submission route: email to the official notice contact; no portal sign-in or
  portal submission is required for this response

## Position

LumenCore is the sole respondent and proposes no teaming arrangement, joint
venture, or subcontractor. It presents bounded evidence-management and
deterministic-validation capabilities while explicitly identifying unproven
FHIR R4, CHPL, HHS ATO, 3PAO, and federal-health delivery qualifications.
The notice permits teaming but requires organizations and roles only if a team
is proposed.

The founder-confirmed LumaArc brand mark appears on the cover. LumaArc is the
mark name, not a rename of the LumenCore company.

## Files

- `ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.md`: human-readable response
- `output/ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.docx`: editable response
- `output/ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.pdf`: rendered review copy
- `ARGOS_SUBMISSION_GATE_2026-07-26.json`: action-time facts and send gate
- `ARGOS_TEAMING_CANDIDATE_REGISTER_2026-07-27.json`: ranked, source-bound
  teaming candidates and authorization state
- `ARGOS_TEAMING_OUTREACH_DRAFTS_2026-07-27.md`: historical one-at-a-time
  partner outreach plan
- `ARGOS_EMI_TEAMING_INQUIRY_BODY.md`: exact no-attachment primary inquiry
  body used by the single sent partner inquiry; includes the official notice
  and duplicate-search disclosure
- `ARGOS_EMI_TEAMING_DISPATCH_GATE_2026-07-27.json`: public-safe duplicate,
  route, selected `INITIAL_PARTNER_TEAMING_INQUIRY` template family, body-hash,
  draft, and historical pre-send boundary receipt
- `ARGOS_EMI_TEAMING_DISPATCH_BINDING_2026-07-27.json`: deterministic
  historical 12-check binding over the then-current registry, public route,
  exact subject/body, deadlines, duplicate search, Gmail readback, and empty
  attachment set; it is expired and not reusable, and its binding hash does
  not reconcile to the separately observed action-time binding hash
- `ARGOS_EMI_TEAMING_DISPATCH_BINDING_2026-07-27.md`: reviewer-readable
  binding, five-minute approval window, and claim boundary
- `ARGOS_RESPONSE_CONFORMANCE_GATE_2026-07-27.json`: machine-readable
  requirement verdict, source custody, and fail-closed send decision
- `ARGOS_RESPONSE_CONFORMANCE_GATE_2026-07-27.md`: reviewer-readable
  requirement matrix and blocker actions
- `ARGOS_ACTION_TIME_FINALIZATION_CHECKLIST_2026-07-27.md`: private fact,
  response-mode, evidence, file, duplicate, and dispatch gates
- `build_argos_response.py`: deterministic response builder
- `build_argos_conformance_gate.py`: deterministic format, evidence, claim,
  authority, duplicate, and dispatch conformance builder
- `build_argos_teaming_dispatch_binding.py`: fail-closed partner-draft
  verifier and time-limited exact-approval binding builder; it cannot send
- `build_argos_private_action_copy.py`: privacy-preserving action-copy
  finalizer; requires a populated facts file and output directory outside Git
- `ARGOS_PRIVATE_FACTS_SCHEMA_2026-07-27.json`: structure-only schema for the
  nine minimum necessary private cover facts; never populate this tracked file
- `ARGOS_PRIVATE_FINALIZER_READINESS_2026-07-27.json`: redacted tooling and
  privacy-boundary receipt; no private copy has been generated
- `ARGOS_CLAIM_EVIDENCE_MAP_2026-07-27.json`: machine-readable binding from
  each material engineering proof statement to exact named first-party receipts,
  source commit, evidence-graph node, negative-result boundary, and non-claims
- `build_argos_claim_evidence_map.py`: deterministic offline verifier for the
  claim-to-evidence map; it makes no live-domain availability claim
- `../funding_sprint_20260709/ARGOS_PARTNER_OUTREACH_STATUS_2026-07-28.json`:
  post-send receipt proving one sent copy, zero current drafts, zero inbound
  replies, and a duplicate-send prohibition
- `../funding_sprint_20260709/source_attachments/Project Argos SOW - SSN.pdf`:
  exact four-page official SOW attachment, SHA-256
  `6a1608c024bd87b0204370baab58b0a218c044d403bce6dbe0cfb5164faf6354`
- `../funding_sprint_20260709/source_attachments/PROJECT_ARGOS_SOW_OFFICIAL_SOURCE_RECEIPT_2026-07-28.json`:
  read-only SAM notice observation and direct public attachment refresh receipt
- `ARGOS_PUBLIC_REPOSITORY_SECURITY_GATE_2026-07-28.json`: public-safe
  credential and Git-history gate; the current file is placeholder-only, but
  provider rotations and public-history remediation remain unproven. It permits
  only a self-contained external response with no repository or live-site route
- `../../code/ops/VERIFY_PUBLIC_REPO_CREDENTIAL_HYGIENE.py`: deterministic
  verifier that never prints credential values

## Rebuild

```powershell
python .\grant_submissions\ONC_ARGOS_20260730\build_argos_response.py
python .\grant_submissions\ONC_ARGOS_20260730\build_argos_claim_evidence_map.py
python .\grant_submissions\ONC_ARGOS_20260730\build_argos_claim_evidence_map.py --check
python .\grant_submissions\ONC_ARGOS_20260730\build_argos_conformance_gate.py
python .\grant_submissions\ONC_ARGOS_20260730\build_argos_conformance_gate.py --check
python .\code\ops\VERIFY_PUBLIC_REPO_CREDENTIAL_HYGIENE.py --check
```

The committed teaming binding is a historical pre-send snapshot, not standing
send authority. The inquiry was sent once at `2026-07-28T15:39:34Z` with no
attachment, CC, or BCC. No inbound reply was present at the recorded check.
Its observed action-time binding hash does not match the committed historical
snapshot, so the public authorization chain is explicitly unreconciled even
though the sent subject and body match committed source hashes. Do not rebuild
the historical binding or resend the inquiry. The inquiry is optional to this
standalone response. A partner may be named only after written role
confirmation and a deliberate switch to teamed-response mode.

The private finalizer intentionally has no in-repository default:

```powershell
python .\grant_submissions\ONC_ARGOS_20260730\build_argos_private_action_copy.py `
  --facts C:\private\argos_facts.json `
  --output-dir C:\private\argos_action_copy_20260727

python .\grant_submissions\ONC_ARGOS_20260730\build_argos_private_action_copy.py `
  --facts C:\private\argos_facts.json `
  --output-dir C:\private\argos_action_copy_20260727 `
  --check
```

The populated facts file and generated private action copy must remain outside
Git and public mirrors, including `E:\LumaProofVault`. The finalizer rejects
EIN, TIN, SSN, banking, credential, password, API-key, and OTP fields because
the Argos cover does not request them. Its check mode verifies exact receipt
schema, counts, output sizes and hashes, public-template custody, current
response mode, false external-action controls, and the absence of individual private
values or private paths. Duplicate JSON keys, altered authorization flags,
partial outputs, and stale receipt metadata fail closed. A generated private
cover does not clear duplicate, dispatch, or approval gates. The finalizer
always removes repository and live-site routes from the external attachment and
rejects external DOCX relationships.

## Conformance Meaning

`PASS` means the named requirement is supported by the current packet and
receipts. `BLOCKED` with `blocks_send=true` means the packet remains unsendable.
`BLOCKED` with `blocks_send=false` records a separate public-promotion or
operational gap. Any send-relevant documentary, formatting, hash,
unauthorized-name, route-isolation, or claim-boundary defect produces
`FAIL_CONFORMANCE`.

## Submission Boundary

Do not send this response until every required private fact is resolved, the
standalone disclosure remains exact, the self-contained attachment is reviewed,
the official notice and duplicate-send state are rechecked, and the user gives
exact action-time approval for the final recipient, attachment, subject, and
body. Provider credential rotation and public-history remediation remain
mandatory before linking or promoting the repository, but they do not block a
verified link-free attachment. The separate partner inquiry is already sent
once and is duplicate-locked.
