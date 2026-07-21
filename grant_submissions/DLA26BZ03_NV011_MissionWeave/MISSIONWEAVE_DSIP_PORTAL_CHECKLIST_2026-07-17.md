# MissionWeave DSIP Portal Checklist - 2026-07-17

Use this sequence only after the user says `I'm in`. Inspect the current in-session browser page before navigating. Preserve any authentication already in progress.

## Deadline Lock

- Topic: `DLA26BZ03-NV011`
- Expected close: `July 22, 2026 at 12:00 p.m. Eastern Time`
- Central-time conversion: `July 22, 2026 at 11:00 a.m. Central Time`
- Internal operating target: finish uploads and the complete portal preview by `July 21 at 3:00 p.m. Central`; reserve the founder's final endorsement for no later than `July 22 at 9:00 a.m. Central`.
- Inbox confirmation: the July 17 DSIP proposal-creation notice repeats the July 22 noon Eastern deadline and warns that every volume must be completed and endorsed before close.
- Recheck the live DSIP countdown before entry and again before final submission.
- Source discrepancy: The Amendment 2 BAA schedule line prints July 22, 2025; the 2026 SBIR topic record, DLA Release 3 schedule, and package sources agree on July 22, 2026.
- Amendment control: use `MISSIONWEAVE_AMENDMENT_2_PORTAL_CONTROL_2026-07-18.md`. Amendment 2 renames the due-diligence program as Foreign Risk Evaluation (FRE), but the required Volume 7 webform and its eight disclosure questions remain. Do not upload a foreign-affiliations PDF in Volume 5.

## Exact Founder Order Of Operations

This sequence covers every currently open gate exactly once. It does not certify a fact, clear a gate, or replace current portal instructions.

1. **Submit the JCP application and retain official evidence** - Use the official JCP portal. Registration or prerequisites in progress are not enough; retain the official application-submission receipt PDF or a current certified DD Form 2345 in the ignored private evidence area. Evidence: Hash-matched official JCP receipt PDF or certified DD Form 2345
2. **Confirm Firm PIN availability inside DSIP** - Confirm that the organization-linked DSIP account can access the Firm PIN. Do not place the PIN itself in chat, Git, logs, or the private gate record. Evidence: Boolean availability state only; never the PIN value
3. **Support and approve the Volume 3 cost basis** - Review the proposed labor rate, 640 PI hours, fringe, indirect base, cloud/data, travel, software/storage, no-subcontractor position, and 100,000 dollar total against actual records before approving the cost volume. Evidence: Current founder records and corporate-official cost review
4. **Review conflicts, cost separation, data rights, CMMC, and export-control planning** - Answer conflicts and joint-venture status from current facts; reconcile the no-duplicate-cost position and technical-data-rights schedule against source records; review the live CMMC requirement; preserve the no-overclaim position; and document whether a Technology Control Plan is a contracting-negotiation deliverable. Evidence: Current source review, hash-bound documentary register, and bounded founder/corporate-official position
5. **Lock the Volume 5 supporting-document set** - Upload only current, applicable documents. For the ITAR-marked scope, include the verified JCP/DD Form 2345 evidence required by the BAA; do not upload the obsolete foreign-affiliations PDF. Evidence: Reviewed attachment list with current file hashes
6. **Review and seal a fresh complete DSIP preview** - After every field and upload is final, inspect all seven volumes, filenames, hashes, cost totals, and the live deadline. Save the current preview receipt privately and bind it with the collector. Evidence: Fresh portal-preview receipt bound to the exact upload set
7. **Perform corporate review and action-time authorization** - Only after the fresh preview is stable, review every volume as corporate official, capture the short-lived approval binding, and authorize the exact final submission. Evidence: Fresh approval timestamp and binding to the current preview/upload set

## Package Lock

- Manifest files verified: `15`
- All manifest hashes and sizes match: `true`
- Volume 2 candidate: `12` pages of `20` allowed, letter size, searchable, and unencrypted.
- The candidate still contains the neutral proposal-number header: `false`.
- Ignored assigned-number final PDF selected by the gate: `true`.
- Do not upload the tracked neutral PDF after DSIP assigns a proposal number. Run `code/ops/FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py`; the final PDF remains ignored and its path, number, and hash remain absent from public artifacts.
- Private Volume 3 receipt integrity passes: `true`. This verifies the ignored workbook against its ignored receipt without publishing either path or hash; it does not replace corporate-official cost-basis review.
- Private DD Form 2345/JCP evidence integrity passes: `false`. A checked private flag cannot clear this gate unless an official portal PDF exists, its SHA-256 matches the ignored receipt, and entity/corporate review are confirmed.
- CMMC/export evidence packet consumed with valid integrity: `true`. MissionWeave CMMC evidence state: `APPLICABILITY_UNRESOLVED`. An unresolved packet cannot support the Phase I position.
- Certification documentary register consumed with valid integrity: `true`. Source hashes current: `true`. A private checkbox cannot clear the no-duplicate-cost or technical-data-rights gate without its source-bound documentary decision and hash-bound review record.

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
5. Volume 5 - Supporting Documents: upload only applicable and current evidence. Because the topic is ITAR-marked, include a certified DD Form 2345 or acceptable JCP application-submission receipt when required. Use the official JCP portal at `https://www.public.dacs.dla.mil/jcp/ext/`; keep the downloaded evidence and its receipt private, require the file hash to match, and do not treat portal registration or prerequisites-in-progress as submission evidence. Do not upload the old foreign-affiliations PDF form.
6. Volume 6 - Fraud, Waste, and Abuse Training: complete the current annual DSIP training review.
7. Volume 7 - Foreign Affiliations: complete the current DSIP webform from current facts. The corporate official cannot certify the proposal until this webform is complete.

## Compliance Locks

- Confirm U.S. small-business eligibility, ownership and affiliates, PI primary employment, the proposed 640 PI hours, and the SBIR percentage-of-work rule.
- Compare MissionWeave with every prior, current, pending, or planned proposal. Disclose overlap and request no duplicate PI hours, cloud costs, software work, or deliverables.
- Keep `NO_DUPLICATE_COST_OR_DELIVERABLE` open until the authoritative proposal/award record, 640-hour schedule, cost categories, background/proposal separation, and final corporate review are reconciled in `grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_CERTIFICATION_DOCUMENTARY_REGISTER_2026-07-21.json`.
- Treat the topic as ITAR-marked. Keep controlled technical data out of the proposal and document the DD Form 2345/JCP and Technology Control Plan decisions.
- Projected CMMC level: `Level 2 (Self)`. Amendment 2 says CMMC Phase II implementation was suspended on July 13, 2026 while Phase I self-assessment requirements remain in place; the current live requirement must be reviewed before submission. Consume `grant_submissions/compliance_evidence/CMMC_EXPORT_EVIDENCE_PACKET_2026-07-18.json` and do not claim an assessment, certification, or compliant enclave without current authoritative evidence.
- Confirm foreign-citizen participation, foreign affiliations, conflicts, joint-venture status, and each technical-data/software-rights assertion from current records.
- Keep `TECHNICAL_DATA_RIGHTS_ASSERTION` open until every asserted item is mapped to a version and funding-history record, MIT/open-source/public interfaces are separated from any restriction, and qualified rights plus corporate-official review is hash-bound in the documentary register.
- TABA is not requested. Do not add a provider without a named, supported, topic-specific need and a reconciled cost entry.

## Final Preview Gate

1. Run `python code\ops\FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py` after the assigned proposal number is captured. Require `PRIVATE_VOLUME2_REBUILT_AND_QA_PASSED`.
2. Inspect every populated field, all seven volumes, every attachment filename and hash, the cost total, and the live deadline.
3. Save a private local preview receipt and capture it with `--section proposal --preview-receipt-file <private-preview-receipt>`. The collector records only private consistency metadata and rejects a stale receipt; a manually entered digest cannot establish freshness.
4. Capture the action-time approval section separately. It cryptographically binds approval to the current preview/upload set and expires after 15 minutes. This command never clicks submit:

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
