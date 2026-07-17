# MissionWeave DSIP Portal Checklist - 2026-07-17

Use this sequence only after the user says `I'm in`. Inspect the current in-session browser page before navigating. Preserve any authentication already in progress.

## Deadline Lock

- Topic: `DLA26BZ03-NV011`
- Expected close: `July 22, 2026 at 12:00 p.m. Eastern Time`
- Recheck the live DSIP countdown before entry and again before final submission.
- Source discrepancy: The Amendment 2 BAA schedule line prints July 22, 2025; the 2026 SBIR topic record, DLA Release 3 schedule, and package sources agree on July 22, 2026.

## Package Lock

- Manifest files verified: `15`
- All manifest hashes and sizes match: `true`
- Volume 2 candidate: `11` pages of `20` allowed, letter size, searchable, and unencrypted.
- The candidate still contains the neutral proposal-number header: `true`.
- Ignored assigned-number final PDF selected by the gate: `false`.
- Do not upload the tracked neutral PDF after DSIP assigns a proposal number. Run `code/ops/FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py`; the final PDF remains ignored and its path, number, and hash remain absent from public artifacts.

## Registration And Firm Controls

1. Complete Login.gov and DSIP authentication without copying credentials into chat, Git, or artifacts.
2. Verify the exact DSIP organization linkage, Firm Admin, Firm PIN availability, and all firm-level forms.
3. Verify active SAM status, current representations, legal-name match, UEI match, and CAGE match inside authenticated systems.
4. Verify SBA Company Registry completion and the SBC Control ID. Store neither the Firm PIN nor login credentials in the private gate file.
5. Confirm submitter and corporate-official authority.
6. Record only the resulting yes/no completion state with `code/ops/CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py --section identity`; the collector has no Firm PIN or credential field.

## Seven Volumes

1. Volume 1 - Proposal Cover Sheet: paste only the bounded public abstract and anticipated-benefits text. Each field must remain within 3,000 characters and contain no proprietary or classified material.
2. Volume 2 - Technical Volume: capture the assigned DSIP proposal number in the ignored record, run the guarded private finalizer, require its PDF QA to pass with no neutral header, run a local malware scan, and upload one PDF no longer than 20 pages. Keep the public 15-file neutral manifest unchanged.
3. Volume 3 - Cost Volume: use the DSIP spreadsheet/form, keep the Phase I base at or below the official $100,000 ceiling, support the direct labor and indirect treatment, and reconcile every task, ODC, and percentage-of-work entry.
4. Volume 4 - Company Commercialization Report: answer from actual SBIR/STTR award history and ensure the current company report is complete.
5. Volume 5 - Supporting Documents: upload only applicable and current evidence. Because the topic is ITAR-marked, include a certified DD Form 2345 or acceptable JCP application evidence when required. Do not upload the old foreign-affiliations PDF form.
6. Volume 6 - Fraud, Waste, and Abuse Training: complete the current annual DSIP training review.
7. Volume 7 - Foreign Affiliations: complete the current DSIP webform from current facts. The corporate official cannot certify the proposal until this webform is complete.

## Compliance Locks

- Confirm U.S. small-business eligibility, ownership and affiliates, PI primary employment, the proposed 640 PI hours, and the SBIR percentage-of-work rule.
- Compare MissionWeave with every prior, current, pending, or planned proposal. Disclose overlap and request no duplicate PI hours, cloud costs, software work, or deliverables.
- Treat the topic as ITAR-marked. Keep controlled technical data out of the proposal and document the DD Form 2345/JCP and Technology Control Plan decisions.
- Projected CMMC level: `Level 2 (Self)`. Amendment 2 says CMMC Phase II implementation was suspended on July 13, 2026 while Phase I self-assessment requirements remain in place; the current live requirement must be reviewed before submission. Do not claim an assessment, certification, or compliant enclave without current evidence.
- Confirm foreign-citizen participation, foreign affiliations, conflicts, joint-venture status, and each technical-data/software-rights assertion from current records.
- TABA is not requested. Do not add a provider without a named, supported, topic-specific need and a reconciled cost entry.

## Final Preview Gate

1. Run `python code\ops\FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py` after the assigned proposal number is captured. Require `PRIVATE_VOLUME2_REBUILT_AND_QA_PASSED`.
2. Inspect every populated field, all seven volumes, every attachment filename and hash, the cost total, and the live deadline.
3. Save a private local preview receipt and record only its SHA-256 in the ignored private gate file.
4. Capture the action-time approval section separately. This command never clicks submit:

```powershell
python code\ops\CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py --section approval
```

5. Run:

```powershell
python code\ops\BUILD_MISSIONWEAVE_DSIP_ACTION_GATE.py --private-input grant_submissions\DLA26BZ03_NV011_MissionWeave\private\MISSIONWEAVE_DSIP_ACTION.private.json
```

6. Require status `READY_FOR_HUMAN_FINAL_SUBMIT_CLICK` and zero open gates.
7. Stop for the final human review. The builder does not click submit, certify facts, accept terms, or create a Government transmission receipt.

## Public Claim Boundary

This public gate proves package integrity, document-format checks, and the completion state of a bounded private DSIP fact workflow. It does not expose legal identifiers, a Firm PIN, the assigned proposal number, private portal evidence, or unsupported compliance facts. It does not establish DLA validation, CMMC status, ITAR compliance, award eligibility, proposal acceptance, submission, selection, contract, award, deployment, or realized performance.
