# MissionWeave DSIP Action Gate - 2026-07-17

This public-safe gate reports only package integrity and private-workflow completion state. It contains no legal identifiers, Firm PIN, assigned proposal number, private portal evidence, or unsupported compliance answer.

## Decision

- Status: `PRIVATE_DSIP_FACTS_CAPTURED_GATES_OPEN`
- Submission ready for human click: `false`
- Expected deadline: July 22, 2026 at 12:00 p.m. Eastern Time
- Live DSIP recheck required: `true`
- Deadline discrepancy: The Amendment 2 BAA schedule line prints July 22, 2025; the 2026 SBIR topic record, DLA Release 3 schedule, and package sources agree on July 22, 2026.
- Private input present: `true`
- Private target git-ignored: `true`
- Private values exposed: `false`
- Required private gates: `50`
- Passed private gates: `35`
- Open gates: `15`
- Gate SHA-256: `f44725cd96edd1b5c1e65588e125ebbf46f753cf8fca5907b93d670af7165d7e`

## Package Integrity

- Manifest files: `15`
- All manifest files match: `true`
- Volume 2 pages: `12/20`
- Letter size: `true`
- Encrypted: `false`
- Searchable: `true`
- Required sections present: `true`
- Ignored private final Volume 2 used: `true`
- Private final Volume 2 path exposed: `false`
- Private final Volume 2 hash exposed: `false`
- Neutral proposal header still present: `false`
- All source and format checks pass: `true`

## Private Fact State

- Assigned proposal number present: `true`
- Assigned proposal number embedded in Volume 2: `true`
- Assigned proposal number value exposed: `false`
- Volume 2 PDF hash matches private record: `true`
- Volume 3 total matches official ceiling: `true`
- Volume 3 private amount exposed: `false`
- Portal preview receipt present: `false`
- Portal preview receipt timestamp present: `false`
- Portal preview receipt fresh: `false`
- Portal preview binding matches current upload set: `false`
- Portal preview evidence current: `false`
- Corporate official reviewed: `false`
- Action-time authorized: `false`
- Approval timestamp fresh: `false`
- Approval follows the current preview: `false`
- Approval bound to the current preview/upload set: `false`
- Private approval binding exposed: `false`
- DD Form 2345/JCP evidence verified: `false`

## Private Volume 3 Artifact Integrity

- Final workbook present: `true`
- Private receipt present: `true`
- Receipt header valid: `true`
- Workbook size matches receipt: `true`
- Workbook hash matches receipt: `true`
- Workbook OOXML package valid: `true`
- Workbook structure and cell bindings valid: `true`
- Workbook sheets match receipt: `true`
- Workbook formulas inspected: `88`
- Workbook formula errors: `0`
- Workbook error cells: `0`
- Financials derived from workbook contents: `true`
- Workbook content failure code: `None`
- Formula scan clean: `true`
- Export/reimport verified: `true`
- Financial reconciliation passes: `true`
- Corporate-review guardrails preserved: `true`
- Receipt integrity passes: `true`
- Private path exposed: `false`
- Private hash exposed: `false`

## Private DD Form 2345/JCP Evidence Integrity

- Private receipt present: `false`
- Receipt header valid: `false`
- Evidence PDF present: `false`
- Evidence hash matches receipt: `false`
- Portal source metadata valid: `false`
- Entity match confirmed: `false`
- Corporate-official review confirmed: `false`
- Evidence integrity passes: `false`
- Private path exposed: `false`
- Private hash exposed: `false`
- Protocol: `grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_JCP_EVIDENCE_PROTOCOL_2026-07-18.json`
- Protocol SHA-256: `E1ECB611C2284512DD3DCA9BC03030A18F2C997E7F52DE0DBEE14361948B4095`

## CMMC Evidence Packet

- Packet: `grant_submissions/compliance_evidence/CMMC_EXPORT_EVIDENCE_PACKET_2026-07-18.json`
- Schema valid: `true`
- Integrity valid: `true`
- MissionWeave requirement consumed: `true`
- Requirement evidence state: `APPLICABILITY_UNRESOLVED`
- Phase I position supported: `false`
- Overclaim boundary present: `true`

## Certification Documentary Register

- Register: `grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_CERTIFICATION_DOCUMENTARY_REGISTER_2026-07-21.json`
- Integrity valid: `true`
- Source hashes current: `true`
- Register consumed: `true`
- Status: `DOCUMENTARY_PREREQUISITES_OPEN`
- No-duplicate-cost documentary prerequisite clear: `false`
- Technical-data-rights documentary prerequisite clear: `false`
- A private boolean cannot clear either gate without a current, integrity-checked register and a hash-bound review record.

## Reconciliation Groups

- `A_DOCUMENTARY_RETRIEVAL`: `3` gates (`OPEN`)
- `B_FOUNDER_FACTUAL_ANSWER`: `2` gates (`OPEN`)
- `C_LEGAL_CERTIFICATION_DECISION`: `7` gates (`OPEN`)
- `D_PORTAL_MECHANICS`: `1` gates (`OPEN`)
- `E_TECHNICAL_VOLUME_CONSISTENCY`: `2` gates (`OPEN`)
- `F_CLEARED_BY_EVIDENCE`: `35` gates (`CLEARED`)

## Lifecycle Boundaries

This classification is explanatory only. It cannot clear a gate or change submission readiness, and current live portal or contracting-office instructions still control.

### A_PRE_SUBMISSION_CONTENT_AND_EVIDENCE

Evidence, content, registration, and portal facts required before the bounded final-submission gate can open.

- Submission effect: `RESOLVE_BEFORE_FINAL_SUBMISSION`
- Open gates: `8`
- `CONFLICTS_AND_JOINT_VENTURE_STATUS`
- `CURRENT_CMMC_REQUIREMENTS_REVIEW`
- `DD2345_OR_JCP_APPLICATION_EVIDENCE`
- `DSIP_FIRM_PIN_AVAILABILITY`
- `NO_DUPLICATE_COST_OR_DELIVERABLE`
- `TECHNICAL_DATA_RIGHTS_ASSERTION`
- `VOLUME3_COST_BASIS`
- `VOLUME5_UPLOAD_SET`

### B_PRE_AWARD_OR_CONTRACT_NEGOTIATION_READINESS

The proposal must state a current bounded position. Implementation proof may occur during pre-award or contract negotiation only if the live portal or contracting office permits it; these gates remain fail-closed now.

- Submission effect: `REVIEW_AND_BOUND_POSITION_BEFORE_SUBMISSION`
- Open gates: `2`
- `CMMC_PHASE_I_SELF_ASSESSMENT_POSITION`
- `TECHNOLOGY_CONTROL_PLAN_DECISION`

### C_FINAL_PREVIEW_AND_ACTION_TIME_HUMAN

Fresh preview, corporate review, and final authorization occur only after the upload set is stable and immediately before the human submit action.

- Submission effect: `ACTION_TIME_HUMAN_ONLY`
- Open gates: `5`
- `ACTION_TIME_APPROVAL_TIMESTAMP`
- `ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION`
- `COMPLETE_PORTAL_PREVIEW_REVIEW`
- `CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW`
- `PORTAL_PREVIEW_RECEIPT_HASH`

## Founder Action Sequence

### 1. Submit the JCP application and retain official evidence

Use the official JCP portal. Registration or prerequisites in progress are not enough; retain the official application-submission receipt PDF or a current certified DD Form 2345 in the ignored private evidence area.

- Evidence required: Hash-matched official JCP receipt PDF or certified DD Form 2345
- Human boundary: The founder completes any portal certification or final JCP submit action.
- Open gates: `1`
- `DD2345_OR_JCP_APPLICATION_EVIDENCE`

### 2. Confirm Firm PIN availability inside DSIP

Confirm that the organization-linked DSIP account can access the Firm PIN. Do not place the PIN itself in chat, Git, logs, or the private gate record.

- Evidence required: Boolean availability state only; never the PIN value
- Human boundary: The founder handles authentication and any secret value.
- Open gates: `1`
- `DSIP_FIRM_PIN_AVAILABILITY`

### 3. Support and approve the Volume 3 cost basis

Review the proposed labor rate, 640 PI hours, fringe, indirect base, cloud/data, travel, software/storage, no-subcontractor position, and 100,000 dollar total against actual records before approving the cost volume.

- Evidence required: Current founder records and corporate-official cost review
- Human boundary: The founder confirms the factual cost basis; the builder checks arithmetic only.
- Open gates: `1`
- `VOLUME3_COST_BASIS`

### 4. Review conflicts, cost separation, data rights, CMMC, and export-control planning

Answer conflicts and joint-venture status from current facts; reconcile the no-duplicate-cost position and technical-data-rights schedule against source records; review the live CMMC requirement; preserve the no-overclaim position; and document whether a Technology Control Plan is a contracting-negotiation deliverable.

- Evidence required: Current source review, hash-bound documentary register, and bounded founder/corporate-official position
- Human boundary: No compliance, assessment, certification, or contracting-office acceptance is inferred.
- Open gates: `6`
- `CMMC_PHASE_I_SELF_ASSESSMENT_POSITION`
- `CONFLICTS_AND_JOINT_VENTURE_STATUS`
- `CURRENT_CMMC_REQUIREMENTS_REVIEW`
- `NO_DUPLICATE_COST_OR_DELIVERABLE`
- `TECHNICAL_DATA_RIGHTS_ASSERTION`
- `TECHNOLOGY_CONTROL_PLAN_DECISION`

### 5. Lock the Volume 5 supporting-document set

Upload only current, applicable documents. For the ITAR-marked scope, include the verified JCP/DD Form 2345 evidence required by the BAA; do not upload the obsolete foreign-affiliations PDF.

- Evidence required: Reviewed attachment list with current file hashes
- Human boundary: Any legally consequential upload or representation remains founder reviewed.
- Open gates: `1`
- `VOLUME5_UPLOAD_SET`

### 6. Review and seal a fresh complete DSIP preview

After every field and upload is final, inspect all seven volumes, filenames, hashes, cost totals, and the live deadline. Save the current preview receipt privately and bind it with the collector.

- Evidence required: Fresh portal-preview receipt bound to the exact upload set
- Human boundary: The founder reviews the rendered Government portal preview.
- Open gates: `2`
- `COMPLETE_PORTAL_PREVIEW_REVIEW`
- `PORTAL_PREVIEW_RECEIPT_HASH`

### 7. Perform corporate review and action-time authorization

Only after the fresh preview is stable, review every volume as corporate official, capture the short-lived approval binding, and authorize the exact final submission.

- Evidence required: Fresh approval timestamp and binding to the current preview/upload set
- Human boundary: The final certification and submit click are founder-only actions.
- Open gates: `3`
- `ACTION_TIME_APPROVAL_TIMESTAMP`
- `ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION`
- `CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW`

## Open Gates

- `ACTION_TIME_APPROVAL_TIMESTAMP`
- `ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION`
- `CMMC_PHASE_I_SELF_ASSESSMENT_POSITION`
- `COMPLETE_PORTAL_PREVIEW_REVIEW`
- `CONFLICTS_AND_JOINT_VENTURE_STATUS`
- `CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW`
- `CURRENT_CMMC_REQUIREMENTS_REVIEW`
- `DD2345_OR_JCP_APPLICATION_EVIDENCE`
- `DSIP_FIRM_PIN_AVAILABILITY`
- `NO_DUPLICATE_COST_OR_DELIVERABLE`
- `PORTAL_PREVIEW_RECEIPT_HASH`
- `TECHNICAL_DATA_RIGHTS_ASSERTION`
- `TECHNOLOGY_CONTROL_PLAN_DECISION`
- `VOLUME3_COST_BASIS`
- `VOLUME5_UPLOAD_SET`

## Private Workflow

1. Run `code/ops/CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py --check-target`. This validates the ignored destination without reading private contents.
2. Run the hidden collector with `--section pre-submit`. It captures identity, proposal, and compliance sections but deliberately excludes action-time approval.
3. After DSIP assigns a proposal number, run `code/ops/FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py`. It reads the number only from the ignored private record, writes the assigned-number DOCX/PDF only to the ignored private area, performs PDF QA, and updates the private PDF hash without exposing either value publicly. Hash the completed portal-preview receipt with `--preview-receipt-file`; a manually entered digest does not establish freshness.
4. For the ITAR-marked topic, save only an official JCP portal submission receipt or certified DD Form 2345 as a private PDF and complete `config/missionweave_jcp_evidence_private_template_v1.json` beside it. A boolean answer cannot clear this gate without a matching file hash.
5. Review the consumed CMMC packet at `grant_submissions/compliance_evidence/CMMC_EXPORT_EVIDENCE_PACKET_2026-07-18.json`. An unresolved packet leaves the supported-position gate open even when a private boolean is checked.
6. Resolve the source-bound prerequisites in `grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_CERTIFICATION_DOCUMENTARY_REGISTER_2026-07-21.json`. Preserve each review receipt privately and bind only its SHA-256 in the register; a private checkbox alone cannot clear the no-duplicate-cost or technical-data-rights gates.
7. Run `--section approval` only after the corporate official reviews the fresh complete portal preview at action time. The collector binds that authorization to the current preview/upload-set identity and never requests or accepts a Firm PIN or login credential.
8. Run this public gate with `--private-input`; require every gate to pass before asking for the final human click.

## Controls

- Browser navigation performed: `false`
- External send performed: `false`
- Portal submit performed: `false`
- Builder can click final submit: `false`
- Action-time human required: `true`
- Private boolean can clear documentary gate: `false`

## Claim Boundary

This public gate proves package integrity, document-format checks, and the completion state of a bounded private DSIP fact workflow. It does not expose legal identifiers, a Firm PIN, the assigned proposal number, private portal evidence, or unsupported compliance facts. It does not establish DLA validation, CMMC status, ITAR compliance, award eligibility, proposal acceptance, submission, selection, contract, award, deployment, or realized performance.
