# MissionWeave Founder Finish Card

- Generated UTC: `2026-07-21T23:24:50Z`
- Deadline: **July 22, 2026 at 12:00 p.m. Eastern Time** (`2026-07-22T16:00:00Z`)
- Time remaining at generation: `16` full hours
- Current gate: **35/50 passed; 15 open**
- Submission-ready: **false**
- Status: `FOUNDER_ACTION_REQUIRED_NOT_SUBMISSION_READY`

## Start Here

1. Open the [official JCP portal](https://www.public.dacs.dla.mil/jcp/ext/).
2. Use the official JCP portal. Registration or prerequisites in progress are not enough; retain the official application-submission receipt PDF or a current certified DD Form 2345 in the ignored private evidence area.
3. Keep the official receipt PDF private. Do not paste a Firm PIN, password, or one-time code into chat or Git.

Why first: Volume 5 cannot be locked without the required official JCP/DD Form 2345 evidence for the current ITAR-marked scope.

## What To Do Now

Work the pre-submission evidence stage first. Do not spend action-time approval or certify final submission until the upload set and fresh portal preview are complete.

- **Do now**: 8 open. Evidence, content, registration, and portal facts required before the bounded final-submission gate can open.
- **Bound the pre-award position**: 2 open. The proposal must state a current bounded position. Implementation proof may occur during pre-award or contract negotiation only if the live portal or contracting office permits it; these gates remain fail-closed now.
- **Do last**: 5 open. Fresh preview, corporate review, and final authorization occur only after the upload set is stable and immediately before the human submit action.

### CMMC And TCP Decision Support

- CMMC projected level: `Level 2 (Self)`.
- CMMC evidence state: `APPLICABILITY_UNRESOLVED`; supported position: `false`.
- CMMC rule: Do not mark the Phase I position supported from projected topic text alone; use current authoritative evidence or a qualified reviewed not-applicable determination.
- TCP rule: Document only the present lifecycle position: a TCP may be requested during contracting negotiation. Do not claim it was submitted, approved, or accepted unless separate evidence proves that event.

## Do These In Order

### 1. Submit the JCP application and retain official evidence

- Do: Use the official JCP portal. Registration or prerequisites in progress are not enough; retain the official application-submission receipt PDF or a current certified DD Form 2345 in the ignored private evidence area.
- Evidence needed: Hash-matched official JCP receipt PDF or certified DD Form 2345
- Human boundary: The founder completes any portal certification or final JCP submit action.
- Clears: `DD2345_OR_JCP_APPLICATION_EVIDENCE`

### 2. Confirm Firm PIN availability inside DSIP

- Do: Confirm that the organization-linked DSIP account can access the Firm PIN. Do not place the PIN itself in chat, Git, logs, or the private gate record.
- Evidence needed: Boolean availability state only; never the PIN value
- Human boundary: The founder handles authentication and any secret value.
- Clears: `DSIP_FIRM_PIN_AVAILABILITY`

### 3. Support and approve the Volume 3 cost basis

- Do: Review the proposed labor rate, 640 PI hours, fringe, indirect base, cloud/data, travel, software/storage, no-subcontractor position, and 100,000 dollar total against actual records before approving the cost volume.
- Evidence needed: Current founder records and corporate-official cost review
- Human boundary: The founder confirms the factual cost basis; the builder checks arithmetic only.
- Clears: `VOLUME3_COST_BASIS`

### 4. Review conflicts, cost separation, data rights, CMMC, and export-control planning

- Do: Answer conflicts and joint-venture status from current facts; reconcile the no-duplicate-cost position and technical-data-rights schedule against source records; review the live CMMC requirement; preserve the no-overclaim position; and document the bounded Technology Control Plan position. The DLA component instructions say an ITAR/EAR topic firm may be required to submit a TCP during contracting negotiation; that does not establish a current proposal-upload requirement or agency acceptance.
- Evidence needed: Current source review, hash-bound documentary register, and bounded founder/corporate-official position
- Human boundary: No compliance, assessment, certification, or contracting-office acceptance is inferred.
- Clears: `CMMC_PHASE_I_SELF_ASSESSMENT_POSITION, CONFLICTS_AND_JOINT_VENTURE_STATUS, CURRENT_CMMC_REQUIREMENTS_REVIEW, NO_DUPLICATE_COST_OR_DELIVERABLE, TECHNICAL_DATA_RIGHTS_ASSERTION, TECHNOLOGY_CONTROL_PLAN_DECISION`

### 5. Lock the Volume 5 supporting-document set

- Do: Upload only current, applicable documents. For the ITAR-marked scope, include the verified JCP/DD Form 2345 evidence required by the BAA; do not upload the obsolete foreign-affiliations PDF.
- Evidence needed: Reviewed attachment list with current file hashes
- Human boundary: Any legally consequential upload or representation remains founder reviewed.
- Clears: `VOLUME5_UPLOAD_SET`

### 6. Review and seal a fresh complete DSIP preview

- Do: After every field and upload is final, inspect all seven volumes, filenames, hashes, cost totals, and the live deadline. Save the current preview receipt privately and bind it with the collector.
- Evidence needed: Fresh portal-preview receipt bound to the exact upload set
- Human boundary: The founder reviews the rendered Government portal preview.
- Clears: `COMPLETE_PORTAL_PREVIEW_REVIEW, PORTAL_PREVIEW_RECEIPT_HASH`

### 7. Perform corporate review and action-time authorization

- Do: Only after the fresh preview is stable, review every volume as corporate official, capture the short-lived approval binding, and authorize the exact final submission.
- Evidence needed: Fresh approval timestamp and binding to the current preview/upload set
- Human boundary: The final certification and submit click are founder-only actions.
- Clears: `ACTION_TIME_APPROVAL_TIMESTAMP, ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION, CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW`

## Email State

- Queue status: `ROUTING_INTEGRITY_EXCEPTION_NO_SEND`
- MissionWeave action: `FOLLOWUP_LIMIT_REACHED_NO_SEND`
- Additional email due now: **false**
- Next action: The bounded proactive follow-up allowance is exhausted. Monitor the existing thread and respond only to a specific inbound request.

## Safe Local Checks

- `python code/ops/CAPTURE_MISSIONWEAVE_JCP_EVIDENCE.py --check-target`
- `python code/ops/CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py --check-target`
- `python code/ops/FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py --check-target`
- `python code/ops/BUILD_MISSIONWEAVE_DSIP_ACTION_GATE.py --private-input grant_submissions/DLA26BZ03_NV011_MissionWeave/private/MISSIONWEAVE_DSIP_ACTION.private.json`
- `python code/ops/CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py --section approval`

After you have reviewed the official receipt PDF and its entity/timestamp, use this template locally:

`python code/ops/CAPTURE_MISSIONWEAVE_JCP_EVIDENCE.py --evidence-file <PRIVATE_OFFICIAL_PDF> --evidence-kind JCP_APPLICATION_SUBMISSION_RECEIPT --source-issued-utc <OFFICIAL_RECEIPT_TIMESTAMP> --confirm-entity-match --confirm-corporate-review`

## Stop Line

Do not certify or click final submit until the regenerated action gate reports `READY_FOR_HUMAN_FINAL_SUBMIT_CLICK`, all 50 gates pass, the complete portal preview is fresh, and Robert performs the final review and action-time authorization.

## Source Lock

- Action gate: `grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json`
- Action-gate canonical-text SHA-256: `5FFF4C4074E8F0879C38662080E90CB5FE595E982359D88BBD10AE58EF5AAB5D`
- Outreach queue canonical-text SHA-256: `88027C4293999BEAEB42DD7847402E91F344546BF70798571CA0327D1FE8C6D3`
- Card SHA-256: `BAFC299ACE777E92DF00FCC92B01342B48206CF77BB95796A11061BD2C0738FF`

This card is a current operator checklist derived from local control artifacts. It does not prove JCP approval, DD Form 2345 certification, CMMC status, ITAR compliance, proposal submission, DLA receipt, eligibility, selection, award, endorsement, deployment, technical validation, funding, or value.
