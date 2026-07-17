# MissionWeave DSIP Action Gate - 2026-07-17

This public-safe gate reports only package integrity and private-workflow completion state. It contains no legal identifiers, Firm PIN, assigned proposal number, private portal evidence, or unsupported compliance answer.

## Decision

- Status: `PRIVATE_DSIP_FACTS_NOT_CAPTURED`
- Submission ready for human click: `false`
- Expected deadline: July 22, 2026 at 12:00 p.m. Eastern Time
- Live DSIP recheck required: `true`
- Deadline discrepancy: The Amendment 2 BAA schedule line prints July 22, 2025; the 2026 SBIR topic record, DLA Release 3 schedule, and package sources agree on July 22, 2026.
- Private input present: `false`
- Private target git-ignored: `true`
- Private values exposed: `false`
- Required private gates: `50`
- Passed private gates: `0`
- Open gates: `50`
- Gate SHA-256: `047097e69d756810565db674784050654893b46aaf980dc7906b0697eb2c1f18`

## Package Integrity

- Manifest files: `15`
- All manifest files match: `true`
- Volume 2 pages: `11/20`
- Letter size: `true`
- Encrypted: `false`
- Searchable: `true`
- Required sections present: `true`
- Neutral proposal header still present: `true`
- All source and format checks pass: `true`

## Private Fact State

- Assigned proposal number present: `false`
- Assigned proposal number embedded in Volume 2: `false`
- Assigned proposal number value exposed: `false`
- Volume 2 PDF hash matches private record: `false`
- Volume 3 total matches official ceiling: `false`
- Volume 3 private amount exposed: `false`
- Portal preview receipt present: `false`
- Corporate official reviewed: `false`
- Action-time authorized: `false`

## Open Gates

- `ACTION_TIME_APPROVAL_TIMESTAMP`
- `ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION`
- `ASSIGNED_PROPOSAL_NUMBER_CAPTURE`
- `CAGE_MATCH`
- `CMMC_PHASE_I_SELF_ASSESSMENT_POSITION`
- `COMPLETE_PORTAL_PREVIEW_REVIEW`
- `CONFLICTS_AND_JOINT_VENTURE_STATUS`
- `CONTROLLED_DATA_EXCLUDED`
- `CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW`
- `CURRENT_CMMC_REQUIREMENTS_REVIEW`
- `DD2345_OR_JCP_APPLICATION_EVIDENCE`
- `DSIP_AUTHENTICATION`
- `DSIP_FIRM_ADMIN`
- `DSIP_FIRM_LEVEL_FORMS`
- `DSIP_FIRM_PIN_AVAILABILITY`
- `DSIP_ORGANIZATION_LINKAGE`
- `FOREIGN_AFFILIATIONS_CURRENT_FACTS`
- `FOREIGN_CITIZEN_ANSWER`
- `ITAR_SCOPE_CONFIRMED`
- `LIVE_DSIP_DEADLINE_CONFIRMATION`
- `NO_CMMC_STATUS_OVERCLAIM`
- `NO_DUPLICATE_COST_OR_DELIVERABLE`
- `OWNERSHIP_AND_AFFILIATES`
- `PI_640_HOURS`
- `PI_PRIMARY_EMPLOYMENT`
- `PORTAL_PREVIEW_RECEIPT_HASH`
- `PRIOR_CURRENT_PENDING_SUPPORT`
- `PRIVATE_INPUT_TIMESTAMP`
- `SAM_ACTIVE_STATUS`
- `SAM_LEGAL_NAME_MATCH`
- `SAM_REPRESENTATIONS_CURRENT`
- `SBA_COMPANY_REGISTRY`
- `SBC_CONTROL_ID`
- `SBIR_PERCENTAGE_OF_WORK`
- `SUBMITTER_AUTHORITY`
- `TECHNICAL_DATA_RIGHTS_ASSERTION`
- `TECHNOLOGY_CONTROL_PLAN_DECISION`
- `UEI_MATCH`
- `US_SMALL_BUSINESS_ELIGIBILITY`
- `VOLUME1_PUBLIC_RELEASE_TEXT_REVIEW`
- `VOLUME2_ASSIGNED_PROPOSAL_NUMBER_EMBEDDED`
- `VOLUME2_PDF_HASH_MATCH`
- `VOLUME2_REBUILD`
- `VOLUME2_VIRUS_SCAN`
- `VOLUME3_COST_BASIS`
- `VOLUME3_TOTAL_MATCHES_PHASE_I_CEILING`
- `VOLUME4_CCR`
- `VOLUME5_UPLOAD_SET`
- `VOLUME6_FWA_TRAINING`
- `VOLUME7_FOREIGN_AFFILIATIONS_WEBFORM`

## Private Workflow

1. Copy `config/missionweave_dsip_action_private_template_v1.json` to `grant_submissions/DLA26BZ03_NV011_MissionWeave/private/MISSIONWEAVE_DSIP_ACTION.private.json`.
2. Set `template_only` to false and complete only supported facts. Never store the Firm PIN or any login credential in the file.
3. After DSIP assigns a proposal number, rebuild Volume 2 through the existing builder and regenerate the package manifest.
4. Save a local preview receipt hash only after all seven volumes are complete and visible.
5. Run this gate with `--private-input`; require every gate to pass before asking for the final human click.

## Controls

- Browser navigation performed: `false`
- External send performed: `false`
- Portal submit performed: `false`
- Builder can click final submit: `false`
- Action-time human required: `true`

## Claim Boundary

This public gate proves package integrity, document-format checks, and the completion state of a bounded private DSIP fact workflow. It does not expose legal identifiers, a Firm PIN, the assigned proposal number, private portal evidence, or unsupported compliance facts. It does not establish DLA validation, CMMC status, ITAR compliance, award eligibility, proposal acceptance, submission, selection, contract, award, deployment, or realized performance.
