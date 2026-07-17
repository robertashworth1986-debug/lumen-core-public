# MissionWeave DSIP Private Capture Workflow - 2026-07-17

## Purpose

This workflow replaces manual editing of the ignored MissionWeave DSIP action file with hidden, sectioned prompts and an atomic local write. It captures only completion facts required by the 50-gate action control. It never requests or accepts a Firm PIN, password, one-time code, login token, API key, or other credential.

## Boundaries

- Topic: `DLA26BZ03-NV011`
- Private target: `grant_submissions/DLA26BZ03_NV011_MissionWeave/private/MISSIONWEAVE_DSIP_ACTION.private.json`
- Target must remain inside the bounded private directory and must be Git-ignored.
- Private answers are never printed, returned in the metadata receipt, mirrored, committed, or written to a public artifact.
- The assigned-number DOCX, PDF, build metadata, and final manifest remain in the ignored private directory. Their path, proposal number, and PDF hash are redacted from public gate outputs.
- The collector does not navigate a browser, upload a file, certify an answer, accept terms, send an email, or click final submit.
- A yes/no answer that a Firm PIN is available is permitted. The Firm PIN value itself is never permitted.

## Target Check

This check validates the destination without reading existing private contents:

```powershell
python code\ops\CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py --check-target
```

Expected status: `READY_FOR_HIDDEN_SECTION_CAPTURE`.

## Section Sequence

### 1. Identity

Run only after the authenticated system shows the relevant registration and firm facts:

```powershell
python code\ops\CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py --section identity
```

This section records 13 booleans. It does not record the UEI, CAGE, SBC Control ID, Firm PIN, username, password, or one-time code.

### 2. Proposal

After DSIP assigns the proposal number, capture the proposal section first. Keep the rebuilt-PDF hash unset until the guarded finalizer runs:

```powershell
python code\ops\CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py --section proposal
```

Rebuild the assigned-number document only inside the ignored private area:

```powershell
python code\ops\FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py
```

Require status `PRIVATE_VOLUME2_REBUILT_AND_QA_PASSED`. The finalizer reads the assigned number from the ignored record rather than a command-line argument, verifies the PDF page count, letter geometry, encryption state, searchable text, required sections, assigned header, and absence of the neutral header, then writes the final PDF hash back into the ignored record.

Rerun the proposal section to confirm the remaining proposal facts and hash the fixed ignored final PDF:

```powershell
python code\ops\CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py --section proposal --use-current-volume2-hash
```

The collector validates the proposal-number format, computes only the guarded ignored final Volume 2 PDF hash when requested, enforces the official Phase I ceiling, and accepts only a 64-character SHA-256 for the private portal-preview receipt. It fails closed if the private final PDF does not exist.

When a local preview-receipt file exists, hash it without storing or printing its path:

```powershell
python code\ops\CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py --section proposal --use-current-volume2-hash --preview-receipt-file <private-local-receipt>
```

### 3. Eligibility And Compliance

Run only after each answer is supported by current records or a documented current review:

```powershell
python code\ops\CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py --section compliance
```

Unresolved facts remain false or null. The collector does not infer eligibility, CMMC status, ITAR compliance, foreign-affiliation answers, data-rights assertions, or conflicts.

### Pre-Submit Convenience Route

The following expands to identity, proposal, and compliance. It intentionally excludes approval:

```powershell
python code\ops\CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py --section pre-submit
```

### 4. Action-Time Approval

Run this section separately and only after the corporate official has reviewed every populated field, all seven volumes, the complete portal preview, the live deadline, and all terms:

```powershell
python code\ops\CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py --section approval
```

Final authorization cannot be recorded unless all-volume review is also confirmed. The approval timestamp is generated locally only when action-time authorization is explicitly confirmed.

## Public Gate

After every required fact is supported, run:

```powershell
python code\ops\BUILD_MISSIONWEAVE_DSIP_ACTION_GATE.py --private-input grant_submissions\DLA26BZ03_NV011_MissionWeave\private\MISSIONWEAVE_DSIP_ACTION.private.json
```

Require all of the following before asking for the final human click:

- Status: `READY_FOR_HUMAN_FINAL_SUBMIT_CLICK`
- Required private gates: `50`
- Open gates: `0`
- Source and package integrity: pass
- Assigned proposal number embedded in rebuilt Volume 2: true
- Private Volume 2 hash matches the rebuilt PDF: true
- Portal preview receipt hash present: true
- Action-time authorization and timestamp present: true

## Recovery

- Invalid input is rejected without echoing the entered value.
- Schema drift, non-ignored targets, paths outside the bounded private directory, symlinks, and non-regular files fail closed before prompting.
- Existing records are resumed; blank or `K` keeps the current value.
- The write is atomic. A failed replacement leaves no partial private record.
- Run only the section that changed, then rerun the public gate.

## Claim Boundary

This workflow proves only that a bounded private capture mechanism and fail-closed public gate exist. It does not prove DSIP authentication, registration, eligibility, compliance, proposal submission, Government receipt, acceptance, selection, contract, award, deployment, or performance.
