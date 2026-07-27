# Project Argos Sources Sought Response

Status: `DRAFT_REVIEW_READY_NOT_SEND_READY`

This directory contains a bounded, partner-first capability response for:

- Notice: `ONC-ARGOS-SSN-2026-OS351107`
- Type: Sources Sought / market research
- Agency: U.S. Department of Health and Human Services
- Response deadline: July 30, 2026 at 5:00 PM Eastern
- Official notice: <https://sam.gov/opp/062cef11f5384443bfd84bf123404026/view>

## Position

LumenCore is presented as an evidence-assurance and deterministic-validation
workstream contributor under a qualified health IT/FHIR and federal
cybersecurity prime or teaming arrangement. The response does not claim current
FHIR R4, CHPL, HHS ATO, 3PAO, or federal health prior performance.

The founder-confirmed LumaArc seal of approval appears on the cover. LumaArc is
the seal name, not a rename of the LumenCore company.

## Files

- `ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.md`: human-readable response
- `output/ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.docx`: editable response
- `output/ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.pdf`: rendered review copy
- `ARGOS_SUBMISSION_GATE_2026-07-26.json`: action-time facts and send gate
- `ARGOS_TEAMING_CANDIDATE_REGISTER_2026-07-27.json`: ranked, source-bound
  teaming candidates and authorization state
- `ARGOS_TEAMING_OUTREACH_DRAFTS_2026-07-27.md`: one-at-a-time partner
  outreach sequence; none sent
- `ARGOS_EMI_TEAMING_INQUIRY_BODY.md`: exact no-attachment primary inquiry
  body used by the current Gmail draft
- `ARGOS_EMI_TEAMING_DISPATCH_GATE_2026-07-27.json`: public-safe duplicate,
  route, body-hash, draft, and send-boundary receipt
- `ARGOS_RESPONSE_CONFORMANCE_GATE_2026-07-27.json`: machine-readable
  requirement verdict, source custody, and fail-closed send decision
- `ARGOS_RESPONSE_CONFORMANCE_GATE_2026-07-27.md`: reviewer-readable
  requirement matrix and blocker actions
- `ARGOS_ACTION_TIME_FINALIZATION_CHECKLIST_2026-07-27.md`: private fact,
  team, evidence, file, duplicate, and dispatch gates
- `build_argos_response.py`: deterministic response builder
- `build_argos_conformance_gate.py`: deterministic format, evidence, claim,
  authority, duplicate, and dispatch conformance builder
- `build_argos_private_action_copy.py`: privacy-preserving action-copy
  finalizer; requires a populated facts file and output directory outside Git
- `ARGOS_PRIVATE_FACTS_SCHEMA_2026-07-27.json`: structure-only schema for the
  nine minimum necessary private cover facts; never populate this tracked file
- `ARGOS_PRIVATE_FINALIZER_READINESS_2026-07-27.json`: redacted tooling and
  privacy-boundary receipt; no private copy has been generated
- `ARGOS_CLAIM_EVIDENCE_MAP_2026-07-27.json`: machine-readable binding from
  each material engineering proof statement to the exact public receipt,
  source commit, evidence-graph node, negative-result boundary, and non-claims
- `build_argos_claim_evidence_map.py`: deterministic offline verifier for the
  claim-to-evidence map; it makes no live-domain availability claim

## Rebuild

```powershell
python .\grant_submissions\ONC_ARGOS_20260730\build_argos_response.py
python .\grant_submissions\ONC_ARGOS_20260730\build_argos_claim_evidence_map.py
python .\grant_submissions\ONC_ARGOS_20260730\build_argos_claim_evidence_map.py --check
python .\grant_submissions\ONC_ARGOS_20260730\build_argos_conformance_gate.py
python .\grant_submissions\ONC_ARGOS_20260730\build_argos_conformance_gate.py --check
```

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
schema, counts, output sizes and hashes, public-template custody, current team
state, false external-action controls, and the absence of individual private
values or private paths. Duplicate JSON keys, altered authorization flags,
partial outputs, and stale receipt metadata fail closed. A generated private
cover does not clear team, duplicate, dispatch, or approval gates.

## Conformance Meaning

`PASS` means the named requirement is supported by the current packet and
receipts. `BLOCKED` means the packet intentionally remains unsendable pending a
required private fact or authority. Any documentary, formatting, hash,
unauthorized-name, or claim-boundary defect produces `FAIL_CONFORMANCE`.

## Submission Boundary

Do not send this response until every required private fact and teaming fact in
the gate file is resolved, the final document is reviewed, duplicate-send state
is rechecked, and the user gives exact action-time approval for the final
recipient, attachment, subject, and body.
