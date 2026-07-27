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
- `ARGOS_ACTION_TIME_FINALIZATION_CHECKLIST_2026-07-27.md`: private fact,
  team, evidence, file, duplicate, and dispatch gates
- `build_argos_response.py`: deterministic response builder

## Rebuild

```powershell
python .\grant_submissions\ONC_ARGOS_20260730\build_argos_response.py
```

## Submission Boundary

Do not send this response until every required private fact and teaming fact in
the gate file is resolved, the final document is reviewed, duplicate-send state
is rechecked, and the user gives exact action-time approval for the final
recipient, attachment, subject, and body.
