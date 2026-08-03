# Federal Submission Protocol Packet - 2026-07-09

Purpose: make LumenCore agency, grant, SBIR, RFI, and contracting readiness easy to inspect without overstating portal authority or award eligibility.

This packet is a protocol-control artifact. It does not authorize external sends, final submissions, signatures, certifications, pricing, cybersecurity representations, or portal actions.

## Status

- Status: `FEDERAL_SUBMISSION_PROTOCOL_READY_HUMAN_PORTAL_REQUIRED`
- Official sources: `11`
- Protocol gates: `7`
- Blocked readiness flags: `6`
- Ready flags: `0`
- Reviewer packaging gate clear: `true`
- Submission argument gate clear: `false`
- Unsafe sensitive hits: `0`
- Unsafe claim hits: `0`
- All final actions blocked without human: `true`
- Human protocol required: `true`
- Data-room Markdown artifacts: `104`
- Autonomous governance ready: `true`
- IP counsel packet ready: `true`
- External send without human: `false`
- Final submission without human: `false`
- Portal submit without human: `false`
- Cybersecurity representation without human: `false`
- CUI processing claimed: `false`
- CMMC status claimed: `false`
- Award eligibility claimed: `false`
- Packet SHA-256: `b357af46b7173f0910f72d2f58a3f977d8bac22c6315b93d2ee11ae764c1c611`

## Local Readiness Snapshot

- Local SAM.gov status: `verification_required`
- UEI present locally: `true`
- CAGE present locally: `true`
- Blocked readiness flags: `grants_gov_account_verified, research_gov_account_verified, nsf_project_pitch_submitted, aor_authority_verified, dsip_account_verified, dod_compliance_verified`
- Profile source: `data/company_profile.json`

## Official Sources

### SAM.gov entity registration

- URL: https://sam.gov/entity-registration
- Protocol fact: SAM.gov assigns the Unique Entity ID during entity registration and says registrations must be renewed every 365 days to stay active.
- LumenCore gate: Robert verifies active registration, UEI/CAGE status, renewal date, entity roles, assertions, and representations directly in SAM.gov.

### SAM.gov entity registration checklist

- URL: https://sam.gov/sites/default/files/2024-11/entity-checklist.pdf
- Protocol fact: The checklist says to allow at least ten business days after submitting a SAM registration for it to become active.
- LumenCore gate: Do not treat a local profile field as award eligibility; portal status must be checked before final submission.

### Grants.gov applicant registration

- URL: https://www.grants.gov/applicants/applicant-registration
- Protocol fact: Grants.gov says an organization profile uses the SAM.gov UEI and the EBiz POC assigns roles such as AOR and Workspace Manager.
- LumenCore gate: Robert verifies profile, role, workspace, and application package state before any Grants.gov action.

### Grants.gov EBiz POC role authorization

- URL: https://www.grants.gov/applicants/applicant-registration/ebiz-poc-authorizes-profile-roles
- Protocol fact: Grants.gov says the EBiz POC must authorize roles before a user can complete or submit application packages on behalf of the organization.
- LumenCore gate: AOR authority and signing responsibility remain human verified before final submit.

### Grants.gov Workspace roles

- URL: https://www.grants.gov/applicants/workspace-overview/workspace-roles
- Protocol fact: Grants.gov says Standard AOR can submit the final application and Workspace Manager is the minimum core role to create and start a workspace.
- LumenCore gate: Workspace participation and AOR privileges must be checked opportunity by opportunity.

### SBIR/STTR eligibility tutorial

- URL: https://www.sbir.gov/tutorials/program-basics/tutorial-2
- Protocol fact: SBIR.gov states the small business must be primarily U.S. owned, generally at least 51% by U.S. citizens or permanent residents.
- LumenCore gate: Ownership, affiliate, PI employment, for-profit status, and award-time eligibility stay human verified.

### SBIR/STTR eligibility FAQ

- URL: https://www.sbir.gov/faq/all
- Protocol fact: SBIR.gov says the awardee must qualify as a Small Business Concern under SBA SBIR/STTR rules.
- LumenCore gate: Local small-business posture is evidence for review, not final eligibility certification.

### Defense SBIR/STTR funding opportunities

- URL: https://www.defensesbirsttr.mil/SBIR-STTR/Opportunities/
- Protocol fact: Defense SBIR/STTR says all DoW SBIR and STTR proposals must be submitted electronically through DSIP as described in the BAA or CSO.
- LumenCore gate: DSIP organization linkage, Firm PIN, topic forms, cost package, certifications, and submit button remain human controlled.

### DARPA SBIR/STTR participation guide

- URL: https://www.darpa.mil/work-with-us/communities/small-business/sbir-sttr-participate
- Protocol fact: DARPA says SBIR/STTR proposals are prepared and submitted through DSIP and are not considered submitted until Submit Proposal is clicked.
- LumenCore gate: DICE and other DARPA-package final submit stays blocked until Robert verifies the complete package and portal status.

### DoW CIO CMMC program

- URL: https://dodcio.defense.gov/CMMC/
- Protocol fact: DoW CIO says CMMC Phase 1 implementation runs November 10, 2025 through November 9, 2026 and focuses primarily on Level 1 and Level 2 self-assessments.
- LumenCore gate: No CMMC, SPRS, FCI, CUI, or enclave representation is made unless official evidence supports the exact claim.

### DoW CIO About CMMC

- URL: https://dodcio.defense.gov/cmmc/About/
- Protocol fact: DoW CIO says CMMC addresses safeguarding requirements for FCI and CUI and requires specified levels as a condition of contract award when applicable.
- LumenCore gate: Any FCI/CUI work requires a scoped environment, solicitation-specific requirements, and human-approved cybersecurity representation.

## Protocol Gates

### SAM/UEI/CAGE

- Local signal: company_profile.sam_gov_status
- Required human check: Confirm active SAM.gov status, UEI, CAGE if assigned, renewal date, entity administrator, entity POCs, and current representations.
- Blocked without check: Do not submit federal contract or assistance material as eligible from local profile alone.

### Grants.gov AOR/Workspace

- Local signal: submission_readiness.grants_gov_account_verified and aor_authority_verified
- Required human check: Confirm Grants.gov account, organization profile, EBiz POC authorization, AOR role, workspace access, and package status.
- Blocked without check: Do not click final submission, certification, or signature-equivalent steps.

### Research.gov / NSF

- Local signal: submission_readiness.research_gov_account_verified and nsf_project_pitch_submitted
- Required human check: Confirm NSF Project Pitch pending status, invitation status, Research.gov access, PI eligibility, and one-pending-pitch rule.
- Blocked without check: Do not represent an NSF invitation or full-proposal eligibility unless NSF issued it.

### DSIP / Defense SBIR-STTR

- Local signal: submission_readiness.dsip_account_verified and dod_compliance_verified
- Required human check: Confirm DSIP account, firm linkage, Firm PIN, topic forms, cost volume, reps, certifications, and final upload preview.
- Blocked without check: Do not submit, certify, or claim DoW integration or procurement readiness.

### Cyber / FCI / CUI

- Local signal: proposal material currently treated as Unclassified and non-CUI unless official source marks otherwise
- Required human check: Confirm whether the solicitation involves FCI, CUI, export controls, SPRS, CMMC level, enclave scope, or flow-down obligations.
- Blocked without check: Do not process protected federal information in general-purpose public tooling or ordinary sync folders.

### IP / Disclosure

- Local signal: ip_counsel_diligence_packet
- Required human check: Confirm official patent status, support, new-matter risk, disclosure limits, and counsel-approved language.
- Blocked without check: Do not expand patent-rights or exclusivity language in agency or investor materials.

### Runtime / Autonomy

- Local signal: autonomous_quant_governance_packet
- Required human check: Confirm paper/runtime state, external-action authority, and no capital-impacting step before any operational escalation.
- Blocked without check: Do not let autonomous systems submit, sign, certify, transact, or move capital.

## Human Gate

- sam_update_allowed_without_human: `False`
- grants_gov_submit_allowed_without_human: `False`
- dsip_submit_allowed_without_human: `False`
- research_gov_submit_allowed_without_human: `False`
- cybersecurity_representation_allowed_without_human: `False`
- pricing_or_cost_submission_allowed_without_human: `False`
- rule: `Federal submissions remain preparation-only until Robert verifies official portal status, authority, package contents, cybersecurity implications, cost, and final submission intent.`

## Evidence Sources

- `grant_submissions/funding_sprint_20260709/AGENCY_GOV_PROTOCOL_READINESS_CONTROL_ROOM_2026-07-09.md` | present=`true` | bytes=`8929` | sha256=`fa76de6bcef22a4eb33adf7558ac0f0f5a28f031da9c918fb4c26ac7ee6d9c82`
- `grant_submissions/funding_sprint_20260709/AGENCY_ACCOUNT_ACTIVATION_DOCKET_2026-07-09.md` | present=`true` | bytes=`12244` | sha256=`77be584815223c7940817ba6355603ff6f93f8475a6ec1fdcabdbad0d43479e5`
- `grant_submissions/funding_sprint_20260709/SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md` | present=`true` | bytes=`24099` | sha256=`cbd2ebec0acc44b92b5b16b96973675c19f5435c6ad521f8f15fb2b6a888b390`
- `grant_submissions/funding_sprint_20260709/HUMAN_ACTION_DOCKET_2026-07-09.md` | present=`true` | bytes=`23598` | sha256=`10f5206c8b65e329041c28caefec7f51c0744fcef70c0761b711470d62f13021`
- `grant_submissions/funding_sprint_20260709/IP_COUNSEL_DILIGENCE_PACKET_2026-07-09.md` | present=`true` | bytes=`11183` | sha256=`77513cd364b40f6236ffb2a19c337ac3c7c4f4efd0e23bc5d14735b04fb8f02c`
- `grant_submissions/funding_sprint_20260709/AUTONOMOUS_QUANT_GOVERNANCE_PACKET_2026-07-09.md` | present=`true` | bytes=`6354` | sha256=`6c97cd16f416812308a01c554759b6e67e9157e8b6c0af65813360ffc4cd6956`
- `grant_submissions/funding_sprint_20260709/DATA_ROOM_MANIFEST_2026-07-09.md` | present=`true` | bytes=`39846` | sha256=`24ef5bb644a01bb86fc6889298afe68b6be8fc9e44cd41f14a0fff2a8691eb6a`
- `grant_submissions/funding_sprint_20260709/FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md` | present=`true` | bytes=`17487` | sha256=`db8e56ed557b78bdd69fa27fddbc516eb4e00b2e4448fe24c030c393c52b9e1a`
- `data/company_profile.json` | present=`true` | bytes=`3682` | sha256=`16086b05d3d5e4af4910fec49cafefc8918ac05ed237f68f471a2834898efe55`
