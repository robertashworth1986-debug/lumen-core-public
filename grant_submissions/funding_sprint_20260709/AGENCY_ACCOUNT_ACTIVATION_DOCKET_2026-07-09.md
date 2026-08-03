# Agency Account Activation Docket - 2026-07-09

Purpose: turn federal account readiness into a reviewer-safe activation board for SAM.gov, Grants.gov, Research.gov, DSIP, DoD cyber scope, IP counsel, signer authority, and proof-vault custody.

This docket is preparation-only. It does not authorize credentials, certifications, final submissions, uploads, external shares, pricing, legal terms, trading, or capital movement.

## Status

- Status: `AGENCY_ACCOUNT_ACTIVATION_READY_HUMAN_PORTAL_REQUIRED`
- Activation items: `8`
- Ready items: `2`
- Blocked items: `6`
- Human-required items: `8`
- Blocked readiness flags: `6`
- SAM active registration observed in private capture: `true`
- SAM expiration date observed: `2026-08-30`
- Reviewer packaging gate clear: `true`
- Submission argument gate clear: `false`
- Unsafe sensitive hits: `0`
- Unsafe claim hits: `0`
- Data-room Markdown artifacts: `104`
- Data-room control artifacts: `56`
- Portal action without human: `false`
- Credential entry without human: `false`
- Certification without human: `false`
- Final submission without human: `false`
- External send without human: `false`
- Live trading allowed: `false`
- Docket SHA-256: `de606ff3e392c634fd6416b1a5778187ac749ee7d2ca76a2f77dabd9091a2188`

## Local Readiness Signals

- Company profile SAM status: `verification_required`
- UEI present locally: `true`
- CAGE present locally: `true`
- SAM portal capture present: `true`
- Ready readiness flags: `0`
- Blocked readiness flags: `grants_gov_account_verified, research_gov_account_verified, nsf_project_pitch_submitted, aor_authority_verified, dsip_account_verified, dod_compliance_verified`
- Private identifier policy: Public docket uses presence/status flags only; exact private identifiers and contact fields stay out of the markdown.

## Activation Rows

### sam_entity_renewal

- Portal: SAM.gov Entity Workspace
- Status: `READY_HUMAN_CERTIFICATION_REQUIRED`
- Evidence signal: Signed-in SAM workspace status capture is available; renewal/update relationship certification remains human-only.
- Human required: `true`
- Portal action without human: `false`
- Credential entry without human: `false`
- Certification without human: `false`
- Final submit without human: `false`
- External share without human: `false`
- Row SHA-256: `978e1142998927802362b32f0b57227f97b587c3b9ec077df07719c5f94dacc3`

Next human actions:
- Review the active entity record in SAM.gov.
- Confirm relationship to entity and authority directly in the portal.
- Review all update/renewal sections before any certification or submit step.
- Save a private portal receipt after final human action.

Blocks:
- SAM-dependent contracts and grants if the registration lapses.
- Any claim that the renewal was submitted unless the portal confirms it.

### grants_gov_profile_aor

- Portal: Grants.gov
- Status: `BLOCKED_ACCOUNT_ROLE_VERIFICATION_REQUIRED`
- Evidence signal: Local readiness flags do not yet verify Grants.gov profile or AOR authority.
- Human required: `true`
- Portal action without human: `false`
- Credential entry without human: `false`
- Certification without human: `false`
- Final submit without human: `false`
- External share without human: `false`
- Row SHA-256: `a66a43596c9a01730d38f235af188edb9a35f0d7658559f52944019b1ab10e6d`

Next human actions:
- Sign in and verify organization profile linkage.
- Confirm Workspace Manager and AOR roles.
- Confirm EBiz POC authorization before any package submit.

Blocks:
- Final Grants.gov package submission.
- Any signature-equivalent certification in Grants.gov.

### research_gov_nsf_pitch

- Portal: Research.gov / NSF Project Pitch
- Status: `BLOCKED_ACCOUNT_OR_PITCH_GATE_REQUIRED`
- Evidence signal: Research.gov account and NSF Project Pitch submission are not verified locally.
- Human required: `true`
- Portal action without human: `false`
- Credential entry without human: `false`
- Certification without human: `false`
- Final submit without human: `false`
- External share without human: `false`
- Row SHA-256: `fa72998b2f7c919cedb8971387912330f8a2ec813274ddaa7d08cf4bd923022f`

Next human actions:
- Verify Research.gov access.
- Check whether an NSF Project Pitch is pending.
- Submit pitch only after final human review of the bounded language.

Blocks:
- NSF full proposal eligibility claims.
- Any claim that an NSF invitation has been issued.

### dsip_firm_pin_topic_access

- Portal: DSIP / Defense SBIR-STTR
- Status: `BLOCKED_ACCOUNT_LINKAGE_REQUIRED`
- Evidence signal: DSIP account, firm linkage, and topic workspace authority are not verified locally.
- Human required: `true`
- Portal action without human: `false`
- Credential entry without human: `false`
- Certification without human: `false`
- Final submit without human: `false`
- External share without human: `false`
- Row SHA-256: `9903e97e0b3cab567044b35b5f66d4a8eea73decd909062ba6ae58f1c9d28911`

Next human actions:
- Verify DSIP user and firm linkage.
- Confirm firm-level access and topic workspace visibility.
- Keep Firm PIN, certifications, and final submit human-only.

Blocks:
- Defense SBIR/STTR final proposal submit.
- DARPA/DLA package certification or Firm PIN use.

### dod_cyber_cmmc_scope

- Portal: DoD cyber / CMMC / SPRS scope
- Status: `BLOCKED_CYBER_SCOPE_REQUIRED`
- Evidence signal: DoD compliance flag is not verified locally; FCI/CUI scope must be solicitation-specific.
- Human required: `true`
- Portal action without human: `false`
- Credential entry without human: `false`
- Certification without human: `false`
- Final submit without human: `false`
- External share without human: `false`
- Row SHA-256: `ff186f8ab1413cedd32ed3f65f30a6b3ded1b7f30b8072bca044f8d65417acab`

Next human actions:
- Confirm whether the opportunity involves FCI or CUI.
- Confirm CMMC/SPRS level, enclave, and flow-down obligations.
- Do not process protected federal data in ordinary sync or public tools.

Blocks:
- Cybersecurity representations.
- Any CMMC, SPRS, FCI, CUI, or controlled-environment claim.

### ip_patent_center_counsel

- Portal: USPTO Patent Center / counsel
- Status: `BLOCKED_PATENT_CENTER_COUNSEL_REQUIRED`
- Evidence signal: Internal profile lists a nonprovisional application reference, but official status and deadlines require Patent Center/counsel verification.
- Human required: `true`
- Portal action without human: `false`
- Credential entry without human: `false`
- Certification without human: `false`
- Final submit without human: `false`
- External share without human: `false`
- Row SHA-256: `b3126ce0cce82e9e8208e2e4c50ec9367788fb6c8dc21fe5cf09737b5541ca6a`

Next human actions:
- Verify application status and response deadlines in Patent Center.
- Ask licensed counsel to approve disclosure boundaries.
- Separate filed claims from new-matter concepts in reviewer materials.

Blocks:
- Patent-rights expansion language.
- Freedom-to-operate or ownership assertions beyond verified records.

### submission_signer_pricing_authority

- Portal: Human signature, pricing, and final authority
- Status: `BLOCKED_FINAL_AUTHORITY_REQUIRED`
- Evidence signal: The authority matrix blocks all sends, submits, certifications, pricing, and term acceptance without human approval.
- Human required: `true`
- Portal action without human: `false`
- Credential entry without human: `false`
- Certification without human: `false`
- Final submit without human: `false`
- External share without human: `false`
- Row SHA-256: `41dc2b4f09e30f983e90edbdaa0a4faeef93286d2a0f64a766ed8b3e9a65a912`

Next human actions:
- Approve final package contents.
- Approve pricing or cost basis.
- Approve certifications, representations, and signature-equivalent actions.

Blocks:
- All final submissions.
- All external sends and acceptance of legal, financial, or program terms.

### secure_artifact_custody

- Portal: Proof vault / data-room custody
- Status: `READY_HUMAN_SHARE_REQUIRED`
- Evidence signal: Data-room and reviewer gates are clear when all control artifacts are present and unsafe scans remain zero.
- Human required: `true`
- Portal action without human: `false`
- Credential entry without human: `false`
- Certification without human: `false`
- Final submit without human: `false`
- External share without human: `false`
- Row SHA-256: `6eacafbc18895ac7efa2bf7d981901707e729291147df2d143ac58edb9abe561`

Next human actions:
- Share only the public-safe front-door files.
- Keep portal receipts and private identifiers in private custody.
- Run hash checks after each E-drive refresh.

Blocks:
- Unreviewed archive sharing.
- Credential, portal, meeting-access, or private-identifier leakage.

## Official Source Map

### SAM.gov entity registration

- URL: https://sam.gov/entity-registration
- Activation use: Entity registration, renewal, Entity Workspace review, and active-status verification.

### Grants.gov applicant registration

- URL: https://www.grants.gov/applicants/applicant-registration
- Activation use: Organization profile and applicant registration path.

### Grants.gov Workspace roles

- URL: https://www.grants.gov/applicants/workspace-overview/workspace-roles
- Activation use: Workspace Manager and AOR role checks before package submit.

### NSF Project Pitch

- URL: https://seedfund.nsf.gov/project-pitch/
- Activation use: Project Pitch and invitation-gated full proposal path.

### Defense SBIR/STTR opportunities

- URL: https://www.defensesbirsttr.mil/SBIR-STTR/Opportunities/
- Activation use: DSIP topic workspace, firm linkage, and Defense SBIR/STTR submission path.

### DARPA SBIR/STTR participation guide

- URL: https://www.darpa.mil/work-with-us/communities/small-business/sbir-sttr-participate
- Activation use: DARPA/DSIP preparation and final submit boundary.

### DoD CIO CMMC

- URL: https://dodcio.defense.gov/CMMC/
- Activation use: Cybersecurity representation boundary for FCI/CUI and CMMC/SPRS implications.

### USPTO Patent Center

- URL: https://patentcenter.uspto.gov/
- Activation use: Patent status, deadlines, and counsel-confirmed IP posture.

## Source Statuses

- `federal_submission_protocol_packet`: `FEDERAL_SUBMISSION_PROTOCOL_READY_HUMAN_PORTAL_REQUIRED`
- `submission_authority_matrix`: `SUBMISSION_AUTHORITY_MATRIX_READY`
- `data_room_manifest`: `DATA_ROOM_MANIFEST_READY`
- `funding_sprint_reviewer_gate`: `REVIEWER_GATE_BLOCKED_SOURCE_BOUND_ARGUMENT_CONFORMANCE`
- `ip_counsel_diligence_packet`: `IP_COUNSEL_DILIGENCE_READY_HUMAN_COUNSEL_REQUIRED`
- `autonomous_quant_governance_packet`: `AUTONOMOUS_QUANT_GOVERNANCE_READY_HUMAN_RUNTIME_REQUIRED`

## Evidence Sources

- `data/company_profile.json` | present=`true` | bytes=`3682` | sha256=`16086b05d3d5e4af4910fec49cafefc8918ac05ed237f68f471a2834898efe55`
- `out/ops/sam_gov_entity_status_capture_latest.json` | present=`true` | bytes=`1655` | sha256=`570ab86d35f12b860b4e7929f2b406fa09571c570b84b77c09c75f654ab66228`
- `out/ops/federal_submission_protocol_packet_latest.json` | present=`true` | bytes=`12448` | sha256=`bad5334a73520a8f5d422e7ae16475ccc8068c16509773a8ac51d53b0aa4affd`
- `out/ops/submission_authority_matrix_latest.json` | present=`true` | bytes=`33418` | sha256=`616519280f524711e6e11c43e059a90cb5490efbcd3f29f4e22530dd3f6fa1ca`
- `out/ops/data_room_manifest_latest.json` | present=`true` | bytes=`73099` | sha256=`6e95b708125d4a4ab81f730fa7c5e692505125106cf93f58b407d7f1f8346127`
- `out/ops/funding_sprint_reviewer_gate_latest.json` | present=`true` | bytes=`107666` | sha256=`ae50f0f8d570a105fc87d13cdf8732c1657d7ee3e1e1cf72eb591f3c0f8443ba`
- `out/ops/ip_counsel_diligence_packet_latest.json` | present=`true` | bytes=`13089` | sha256=`d1ef448f97a2360f191f3f07d2cf61627ff1c527ee5fe4a82c1455166ce54d41`
- `out/ops/autonomous_quant_governance_packet_latest.json` | present=`true` | bytes=`10096` | sha256=`58cd3145ac2982918b96943dcb7ba0c20610492f21c608c2fbd87c9fa13e433c`

## Human Stop Rule

Prepare only. Human controls credentials, legal authority certifications, portal submit, uploads, shares, pricing, representations, and final acceptance.
