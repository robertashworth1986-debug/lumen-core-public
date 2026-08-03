# Agency Submission Assembly Gate - 2026-07-09

Purpose: Convert near-term federal, SBIR, RFI, lab, and IP lanes into a fail-closed assembly checklist that separates artifact presence from source-bound argument conformance and human final authority.

No federal, SBIR, RFI, lab, IP, certification, legal, pricing, portal, trading, or capital-impacting final action is authorized by this packet. It is an assembly and review gate only.

## Status

- Status: `AGENCY_SUBMISSION_ASSEMBLY_BLOCKED`
- Assembly lanes: `19`
- First artifacts present: `true`
- Reviewer gate clear: `false`
- Submission conformance status: `SUBMISSION_CONFORMANCE_BLOCKED`
- Submission conformance covers all current lanes: `true`
- Assembly represents every active conformance lane: `true`
- Unrepresented active conformance lanes: `0`
- Active submission candidates: `3`
- Active argument passes: `0`
- Active argument blocks: `3`
- Argument gate clear: `false`
- Federal protocol status: `FEDERAL_SUBMISSION_PROTOCOL_READY_HUMAN_PORTAL_REQUIRED`
- Agency activation status: `AGENCY_ACCOUNT_ACTIVATION_READY_HUMAN_PORTAL_REQUIRED`
- Agency activation items: `8`
- Agency blocked items: `6`
- Authority lanes: `26`
- All final actions blocked without human: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Live trading allowed: `false`
- Capital movement allowed: `false`
- Unsafe sensitive hits: `0`
- Unsafe claim hits: `0`
- Assembly gate SHA-256: `f651ab806d196a03d78d0e79e9e4c52b7e81a385ee006d962a5ce64fa7731fe5`

## Package Status Counts

- `ARGUMENT_CONFORMANCE_BLOCKED_BEFORE_REVIEW`: `3`
- `CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY`: `1`
- `EXPIRED_NO_VERIFIED_SUBMISSION_REUSE_BLOCKED`: `1`
- `MONITOR_ONLY_NO_DUPLICATE_SUBMISSION`: `3`
- `NO_CURRENT_SUBMISSION_ROUTE`: `5`
- `PARTNER_OR_NO_SOLO_BLOCKED`: `4`
- `SCOUT_READY_NOT_ASSEMBLED`: `1`
- `TECHNICAL_NO_GO_EVIDENCE_SPRINT_ONLY`: `1`

## Assembly Rows

### 0. sam_registration_external_validation_watch

- Name: SAM.gov registration external validation watch
- Channel: `federal_registration`
- Status: `SUBMITTED_EXTERNAL_VALIDATION_PENDING`
- Legacy intake status: `SUBMITTED_EXTERNAL_VALIDATION_PENDING`
- State source: `legacy_intake_baseline`
- Readiness mode: `FEDERAL_REGISTRATION_SUBMITTED_VALIDATION_PENDING`
- Package status: `NO_CURRENT_SUBMISSION_ROUTE`
- Submission conformance: `NO_SUBMISSION_ARGUMENT_GATE_APPLICABLE`
- Argument conformance pass: `false`
- Argument criteria passed: `0/10`
- Urgency: `PAST_DATE_RECHECK`
- Action due: `2026-07-13`
- First artifact: `grant_submissions/funding_sprint_20260709/SAM_SUBMISSION_AND_TODAY_OPPORTUNITY_PUSH_2026-07-09.md` sha256=`7f4f1a90c08f3c4df1b6f2b6d32b5b863a008a300f304feb807823846cdbf528`
- Component gates passed: `6/9`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert verifies SAM status, responds to any official DLA or SAM request, and approves any notarized Entity Administrator letter or correction.
- Next human action: Check SAM status and watch for any DLA email; prepare Entity Administrator letter packet if required.
- Claim boundary: Submitted is not Active; no award eligibility, active registration, or CAGE validation is claimed until SAM confirms it.
- Row SHA-256: `beb1cb23ba6719af8482cfaad9b02d6cf364bc8eeabc42d5390d02a8c2a87693`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` gate_passed=`false`
- `capability_or_technical_narrative` state=`not_required_for_registration_watch` gate_passed=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` gate_passed=`true`
- `program_fit_and_argument_trace` state=`not_applicable_for_current_route` gate_passed=`true`
- `eligibility_account_and_signer_authority` state=`human_authority_required` gate_passed=`false`
- `cost_price_or_budget_basis` state=`not_required_for_registration_watch` gate_passed=`true`
- `cyber_export_and_protected_data_boundary` state=`watch_only` gate_passed=`true`
- `ip_disclosure_and_counsel_boundary` state=`watch_only` gate_passed=`true`
- `human_final_action_authority` state=`blocked_until_human_approval` gate_passed=`false`

Assembly blockers:
- SAM.gov submission is not the same as Active status.
- External IRS/CAGE/DLA or SAM validation must clear before eligibility language is promoted.

### 2. lanl_vision_licensing_followup

- Name: LANL VISION licensing opportunity follow-up
- Channel: `federal_lab_tech_transfer`
- Status: `OUTBOUND_SENT_RESPONSE_PENDING`
- Legacy intake status: `WAITING_POC_RETURN`
- State source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json`
- Readiness mode: `INBOUND_ONLY_MONITOR_NO_OUTBOUND_ACTION`
- Package status: `MONITOR_ONLY_NO_DUPLICATE_SUBMISSION`
- Submission conformance: `MONITOR_ONLY_NO_DUPLICATE_SUBMISSION`
- Argument conformance pass: `false`
- Argument criteria passed: `0/10`
- Urgency: `ROLLING_OR_EVENT_GATED`
- Action due: `None`
- First artifact: `grant_submissions/funding_sprint_20260709/OUTREACH_FOLLOWUP_ACTION_QUEUE_2026-07-18.json` sha256=`5ea189d3adcddba52d3aea0b711420238289d9860a5ddaec880d0074151db485`
- Component gates passed: `4/9`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert reviews any new inbound message and separately approves a response only if the lane policy permits one.
- Next human action: The bounded proactive outreach allowance is exhausted. Monitor the existing thread and respond only to a specific inbound request.
- Claim boundary: This queue evaluates communication timing and routing controls only. A hold expiration or open deadline requires a fresh mailbox check that is recent, timestamped, and receipted; a current draft is not a sent message, and prior proactive sends are derived from a sealed receipt ledger. None of those conditions authorizes a draft or send. Any future send must also bind the exact subject, body, recipient route, attachments, mailbox receipt, single-use action-time approval, and possession of a private HumanUnlock bearer token before an explicit Gmail action. The bearer proof records token possession only; it does not establish identity or legal signing authority. The queue does not establish submission, receipt, selection, funding, endorsement, validation, technical performance, or authority to disclose private information.
- Row SHA-256: `3b278d1c8217d1d55a9e0a31424ba4d0592cdfa8c15380b71cfb3efa72039501`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` gate_passed=`false`
- `capability_or_technical_narrative` state=`primary_artifact_ready` gate_passed=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` gate_passed=`true`
- `program_fit_and_argument_trace` state=`not_applicable_for_current_route` gate_passed=`true`
- `eligibility_account_and_signer_authority` state=`human_followup_authority_required` gate_passed=`false`
- `cost_price_or_budget_basis` state=`not_required_for_initial_followup` gate_passed=`true`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` gate_passed=`false`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` gate_passed=`false`
- `human_final_action_authority` state=`blocked_until_human_approval` gate_passed=`false`

Assembly blockers:
- Human approval remains required before external send, portal action, certification, filing, or term action.

### 3. uspto_georgia_patents_route

- Name: USPTO / Georgia PATENTS pro bono routing
- Channel: `ip_readiness`
- Status: `OUTBOUND_SENT_INTAKE_RESPONSE_PENDING`
- Legacy intake status: `PRO_BONO_ROUTE_IDENTIFIED_HUMAN_ACTION_REQUIRED`
- State source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json#related:georgia_patents_pro_bono_intake`
- Readiness mode: `IP_PACKET_READY_COUNSEL_REQUIRED`
- Package status: `NO_CURRENT_SUBMISSION_ROUTE`
- Submission conformance: `NO_SUBMISSION_ARGUMENT_GATE_APPLICABLE`
- Argument conformance pass: `false`
- Argument criteria passed: `0/10`
- Urgency: `PAST_DATE_RECHECK`
- Action due: `2026-07-10`
- First artifact: `grant_submissions/funding_sprint_20260709/IP_COUNSEL_DILIGENCE_PACKET_2026-07-09.md` sha256=`77513cd364b40f6236ffb2a19c337ac3c7c4f4efd0e23bc5d14735b04fb8f02c`
- Component gates passed: `5/9`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Licensed patent counsel and Robert decide any filing, continuation, PCT, disclosure, or claim strategy action.
- Next human action: Prepare Georgia PATENTS intake packet and counsel questions.
- Claim boundary: This receipt records transmission of a nonconfidential intake-routing inquiry only. It does not establish program eligibility, acceptance, attorney-client representation, confidentiality, a verified USPTO deadline, preservation of rights, patentability, prosecution status, funding, or legal advice.
- Row SHA-256: `a0a1e70bd9ff6a893a552de23bedafe03bc865e8731671fde46b366b3a8888f3`

Components:
- `official_source_and_instructions` state=`counsel_or_official_record_required` gate_passed=`false`
- `capability_or_technical_narrative` state=`invention_family_summary_ready` gate_passed=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` gate_passed=`true`
- `program_fit_and_argument_trace` state=`not_applicable_for_current_route` gate_passed=`true`
- `eligibility_account_and_signer_authority` state=`inventor_and_assignment_facts_required` gate_passed=`false`
- `cost_price_or_budget_basis` state=`not_required_for_counsel_packet` gate_passed=`true`
- `cyber_export_and_protected_data_boundary` state=`not_primary_gate` gate_passed=`true`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` gate_passed=`false`
- `human_final_action_authority` state=`blocked_until_human_approval` gate_passed=`false`

Assembly blockers:
- Licensed counsel must verify status, support, disclosure limits, and exact wording before IP claim expansion.

### 3. darpa_dice_full_submission

- Name: DARPA DICE full proposal sprint
- Channel: `federal_baa`
- Status: `FULL_PROPOSAL_SPRINT`
- Legacy intake status: `FULL_PROPOSAL_SPRINT`
- State source: `legacy_intake_baseline`
- Readiness mode: `FEDERAL_DRAFT_READY_SUBMISSION_BLOCKED`
- Package status: `CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY`
- Submission conformance: `CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY`
- Argument conformance pass: `false`
- Argument criteria passed: `2/10`
- Urgency: `PAST_DATE_RECHECK`
- Action due: `2026-07-12`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`4f7520b12da081b0395f4ea821fe2be7bb8c6dcec6f6926908d112fe9b16b262`
- Component gates passed: `2/9`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert verifies the controlling BAA instructions, submission account authority, budget, representations, and final package.
- Next human action: Build full-proposal compliance matrix and confirm controlling BAA instructions.
- Claim boundary: Abstract receipt is not award selection and not permission to skip BAA instructions.
- Row SHA-256: `266d3cce463e6257809e36c9dd76c63bf1ade30b1a55589822372e1b5d74bbc8`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` gate_passed=`false`
- `capability_or_technical_narrative` state=`primary_artifact_ready` gate_passed=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` gate_passed=`true`
- `program_fit_and_argument_trace` state=`closed_official_decision_postmortem_only` gate_passed=`false`
- `eligibility_account_and_signer_authority` state=`sam_portal_and_signer_authority_required` gate_passed=`false`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` gate_passed=`false`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` gate_passed=`false`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` gate_passed=`false`
- `human_final_action_authority` state=`blocked_until_human_approval` gate_passed=`false`

Assembly blockers:
- Do not reply or prepare a full proposal under this route. Reuse only generalized lessons in future opportunity screening.
- Official BAA/RFI instructions, attachment limits, and submission channel must be checked at action time.
- Cost, team, compliance, and upload preview remain human-gated.

### 4. fhwa_tsmo_data_initiative

- Name: FHWA TSMO Data Initiative
- Channel: `federal_contract`
- Status: `QUALIFIED_RESPONSE_LEAD_REFERRAL_ACKNOWLEDGED_FIT_CHECK_PENDING`
- Legacy intake status: `PHASE_I_TECH_VOLUME`
- State source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json#related:fhwa_tsmo_qualified_partner_outreach`
- Readiness mode: `HUMAN_REVIEW_REQUIRED_NO_EXTERNAL_ACTION`
- Package status: `NO_CURRENT_SUBMISSION_ROUTE`
- Submission conformance: `NO_SUBMISSION_ARGUMENT_GATE_APPLICABLE`
- Argument conformance pass: `false`
- Argument criteria passed: `0/10`
- Urgency: `ROLLING_OR_EVENT_GATED`
- Action due: `None`
- First artifact: `grant_submissions/funding_sprint_20260709/FHWA_TSMO_PHASE1_TECHNICAL_CAPABILITY_OUTLINE_2026-07-09.md` sha256=`61b9fff2c10b2493265f00c399d2e9822e378a4fc87f95b9325014fcca773dea`
- Component gates passed: `3/9`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert reviews the current official evidence and decides whether this lane remains open, closed, inbound-only, or eligible for a separately approved action.
- Next human action: Monitor the referred response lead for scheduling or a specific question and do not reuse the rejected address. If no response arrives by July 21, send at most one short scheduling follow-up. Before any teaming or proposal claim, verify written role, documentable corporate experience, conflicts, references, facilities, data rights, and schedule.
- Claim boundary: The Gmail records prove that the first route was rejected, the replacement message received a substantive reply, the request was referred to the subject matter expert leading this response, and one bounded acknowledgment was sent in that thread. The referral does not establish pursuit, a fit-check commitment, a teaming relationship, permission to cite corporate experience, independent validation, proposal compliance, submission, award, or funding.
- Row SHA-256: `ec9b27f3824824c6415b587bbb8983ea7c749b3ff0252ebba7f2d472b05ad78a`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` gate_passed=`false`
- `capability_or_technical_narrative` state=`primary_artifact_ready` gate_passed=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` gate_passed=`true`
- `program_fit_and_argument_trace` state=`not_applicable_for_current_route` gate_passed=`true`
- `eligibility_account_and_signer_authority` state=`sam_portal_and_signer_authority_required` gate_passed=`false`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` gate_passed=`false`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` gate_passed=`false`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` gate_passed=`false`
- `human_final_action_authority` state=`blocked_until_human_approval` gate_passed=`false`

Assembly blockers:
- Human approval remains required before external send, portal action, certification, filing, or term action.

### 5. nasa_data_center_rfi

- Name: NASA Data Center Infrastructure RFI
- Channel: `federal_rfi`
- Status: `SENT_VERIFIED_RESPONSE_PENDING`
- Legacy intake status: `RFI_RESPONSE_PREP`
- State source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json`
- Readiness mode: `HUMAN_REVIEW_REQUIRED_NO_EXTERNAL_ACTION`
- Package status: `MONITOR_ONLY_NO_DUPLICATE_SUBMISSION`
- Submission conformance: `MONITOR_ONLY_NO_DUPLICATE_SUBMISSION`
- Argument conformance pass: `false`
- Argument criteria passed: `0/10`
- Urgency: `ROLLING_OR_EVENT_GATED`
- Action due: `None`
- First artifact: `grant_submissions/funding_sprint_20260709/NASA_DATA_CENTER_RFI_RESPONSE_OUTLINE_2026-07-09.md` sha256=`bcfdd40dfafc7ca0e7822679dba9d2504c2196b5701704d0ba3d46c5ce9448f6`
- Component gates passed: `2/9`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert reviews the current official evidence and decides whether this lane remains open, closed, inbound-only, or eligible for a separately approved action.
- Next human action: Retain the SENT receipt and attachment hash; do not resend before the deadline.
- Claim boundary: Transmission does not establish agency acceptance, evaluation, validation, an award, or a contract.
- Row SHA-256: `d11a73670d04ec61dee5f7756a862731d2b0830e92c3a5d663eeaf6f7b3bc93a`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` gate_passed=`false`
- `capability_or_technical_narrative` state=`primary_artifact_ready` gate_passed=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` gate_passed=`true`
- `program_fit_and_argument_trace` state=`argument_conformance_blocked` gate_passed=`false`
- `eligibility_account_and_signer_authority` state=`sam_portal_and_signer_authority_required` gate_passed=`false`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` gate_passed=`false`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` gate_passed=`false`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` gate_passed=`false`
- `human_final_action_authority` state=`blocked_until_human_approval` gate_passed=`false`

Assembly blockers:
- Monitor for a specific clarification or replacement request; apply the full gate before any revised package.

### 6. dla_missionweave_sbir

- Name: DLA MissionWeave DSIP SBIR
- Channel: `federal_sbir`
- Status: `PRIVATE_DSIP_FACTS_CAPTURED_GATES_OPEN`
- Legacy intake status: `DSIP_PACKAGE_PREP`
- State source: `grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json`
- Readiness mode: `PORTAL_READ_ONLY_STATUS_VERIFICATION`
- Package status: `EXPIRED_NO_VERIFIED_SUBMISSION_REUSE_BLOCKED`
- Submission conformance: `EXPIRED_NO_VERIFIED_SUBMISSION_REUSE_BLOCKED`
- Argument conformance pass: `false`
- Argument criteria passed: `0/10`
- Urgency: `ROLLING_OR_EVENT_GATED`
- Action due: `None`
- First artifact: `grant_submissions/funding_sprint_20260709/OFFICIAL_INBOUND_STATUS_EVENT_REGISTER_2026-07-25.json` sha256=`320e8a6351c27a0a395dacde7bbc1fe32d1aceeb8e8a7596c77aeca485f39a6a`
- Component gates passed: `2/9`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert controls the authenticated session and permits only a read-only status check unless a separate exact action is approved.
- Next human action: Archive the official non-submission receipt, retain the failed gates for lessons learned, and do not resend, certify, upload, or represent the proposal as submitted.
- Claim boundary: This privacy-safe register records observed official routing and status events only. It does not establish eligibility, selection, endorsement, funding, an award, a contract, independent validation, licensing, portal completion, or technical performance.
- Row SHA-256: `e53453d3c21ef60940cd47bb61bdfd615c57e2843bae4979116085968be42041`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` gate_passed=`false`
- `capability_or_technical_narrative` state=`primary_artifact_ready` gate_passed=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` gate_passed=`true`
- `program_fit_and_argument_trace` state=`argument_conformance_blocked` gate_passed=`false`
- `eligibility_account_and_signer_authority` state=`dsip_or_sbir_authority_required` gate_passed=`false`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` gate_passed=`false`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` gate_passed=`false`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` gate_passed=`false`
- `human_final_action_authority` state=`blocked_until_human_approval` gate_passed=`false`

Assembly blockers:
- Archive this route as expired without verified submission. Reuse only generalized, non-sensitive material after a fresh solicitation and full conformance audit.

### 7. nsf_project_pitch

- Name: NSF SBIR/STTR Project Pitch
- Channel: `federal_sbir`
- Status: `PITCH_READY_HUMAN_CHECK`
- Legacy intake status: `PITCH_READY_HUMAN_CHECK`
- State source: `legacy_intake_baseline`
- Readiness mode: `ROLLING_GATE_READY_RULE_CHECK_REQUIRED`
- Package status: `ARGUMENT_CONFORMANCE_BLOCKED_BEFORE_REVIEW`
- Submission conformance: `BLOCKED_UNASSESSED_CRITERIA`
- Argument conformance pass: `false`
- Argument criteria passed: `0/10`
- Urgency: `ROLLING_OR_EVENT_GATED`
- Action due: `None`
- First artifact: `grant_submissions/funding_sprint_20260709/NSF_PROJECT_PITCH_DRAFT_2026-07-09.md` sha256=`baa66ab948fdc1bb57e898d8a6e4e0bf776c65ff4c6722ef658720c148f40e6f`
- Component gates passed: `2/9`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert verifies account status, platform-specific rules, one-pending-pitch limits, and final content before submit.
- Next human action: Check the one-pending-pitch rule before any Project Pitch submit.
- Claim boundary: No NSF invitation or full-proposal eligibility is represented unless NSF issues it.
- Row SHA-256: `d16f4860348bf89abe86331ae68048faf2c2ac9eb3e05b41814a622e9e43744e`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` gate_passed=`false`
- `capability_or_technical_narrative` state=`primary_artifact_ready` gate_passed=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` gate_passed=`true`
- `program_fit_and_argument_trace` state=`argument_conformance_blocked` gate_passed=`false`
- `eligibility_account_and_signer_authority` state=`dsip_or_sbir_authority_required` gate_passed=`false`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` gate_passed=`false`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` gate_passed=`false`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` gate_passed=`false`
- `human_final_action_authority` state=`blocked_until_human_approval` gate_passed=`false`

Assembly blockers:
- Refresh the official NSF source and build a criterion crosswalk before calling the pitch reviewer-ready.
- NSF account, pending-pitch status, invitation state, and one-pending-pitch rule must be checked.
- No Research.gov or NSF final action is authorized by local files.

### 8. epa_r10_icpoes_route

- Name: EPA Region 10 ICP-OES RFI route
- Channel: `federal_market_research`
- Status: `ROUTE_ONLY_LOW_FIT`
- Legacy intake status: `ROUTE_ONLY_LOW_FIT`
- State source: `legacy_intake_baseline`
- Readiness mode: `ROUTING_SENT_WAIT_FOR_RESPONSE`
- Package status: `NO_CURRENT_SUBMISSION_ROUTE`
- Submission conformance: `NO_SUBMISSION_ARGUMENT_GATE_APPLICABLE`
- Argument conformance pass: `false`
- Argument criteria passed: `0/10`
- Urgency: `PAST_DATE_RECHECK`
- Action due: `2026-07-21`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`4f7520b12da081b0395f4ea821fe2be7bb8c6dcec6f6926908d112fe9b16b262`
- Component gates passed: `4/9`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert approves any further agency contact after a routing response.
- Next human action: Wait for routing response; do not prepare a prime bid.
- Claim boundary: No instrument supply, OEM, reseller, or lab-services qualification claim.
- Row SHA-256: `0ebb086f98629718a7912e4d36e98159c7c7739af72654f1def6b9fab6d35b36`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` gate_passed=`false`
- `capability_or_technical_narrative` state=`primary_artifact_ready` gate_passed=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` gate_passed=`true`
- `program_fit_and_argument_trace` state=`not_applicable_for_current_route` gate_passed=`true`
- `eligibility_account_and_signer_authority` state=`human_routing_authority_required` gate_passed=`false`
- `cost_price_or_budget_basis` state=`not_required_for_routing_watch` gate_passed=`true`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` gate_passed=`false`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` gate_passed=`false`
- `human_final_action_authority` state=`blocked_until_human_approval` gate_passed=`false`

Assembly blockers:
- Wait for official routing response before claiming a submission path or agency interest.

### 9. epa_ucmr6_partner_only

- Name: EPA UCMR 6 analytical chemistry lab services
- Channel: `federal_sources_sought`
- Status: `PARTNER_ONLY`
- Legacy intake status: `PARTNER_ONLY`
- State source: `legacy_intake_baseline`
- Readiness mode: `PARTNER_REQUIRED_NO_SOLO_SUBMISSION`
- Package status: `PARTNER_OR_NO_SOLO_BLOCKED`
- Submission conformance: `BLOCKED_BEFORE_SUBMISSION_CANDIDATE`
- Argument conformance pass: `false`
- Argument criteria passed: `0/10`
- Urgency: `PARKED_UNLESS_PARTNER`
- Action due: `2026-07-21`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`4f7520b12da081b0395f4ea821fe2be7bb8c6dcec6f6926908d112fe9b16b262`
- Component gates passed: `3/9`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Qualified partner and Robert approve any partner-led response.
- Next human action: Find qualified partner before any response draft.
- Claim boundary: No testing lab, contaminant monitoring, or regulated lab-services claim.
- Row SHA-256: `6d91d2543d57d3b59261b2b8946ce8129226c93686a8917514f1660bb2bd6acf`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` gate_passed=`false`
- `capability_or_technical_narrative` state=`primary_artifact_ready` gate_passed=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` gate_passed=`true`
- `program_fit_and_argument_trace` state=`argument_conformance_blocked` gate_passed=`false`
- `eligibility_account_and_signer_authority` state=`partner_authority_required` gate_passed=`false`
- `cost_price_or_budget_basis` state=`not_required_until_partner_or_sources_sought_response` gate_passed=`true`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` gate_passed=`false`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` gate_passed=`false`
- `human_final_action_authority` state=`blocked_until_human_approval` gate_passed=`false`

Assembly blockers:
- Require a qualified laboratory lead and a current official scope before any package assembly.
- Qualified prime, jurisdictional owner, lab, testbed, or domain partner is required before any solo package is promoted.

### 10. fhwa_infrastructure_baa_call3

- Name: FHWA Infrastructure R&D BAA Call 3.0
- Channel: `federal_baa`
- Status: `SCOUT_TOPIC_MATCH`
- Legacy intake status: `SCOUT_TOPIC_MATCH`
- State source: `legacy_intake_baseline`
- Readiness mode: `TOPIC_SCOUT_READY_SELECTION_REQUIRED`
- Package status: `SCOUT_READY_NOT_ASSEMBLED`
- Submission conformance: `BLOCKED_BEFORE_SUBMISSION_CANDIDATE`
- Argument conformance pass: `false`
- Argument criteria passed: `0/10`
- Urgency: `PAST_DATE_RECHECK`
- Action due: `2026-07-24`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`4f7520b12da081b0395f4ea821fe2be7bb8c6dcec6f6926908d112fe9b16b262`
- Component gates passed: `2/9`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert approves topic selection after official attachments and topic fit are reviewed.
- Next human action: Review official attachments and score topic fit before drafting.
- Claim boundary: No claim that LumenCore fits all BAA topics.
- Row SHA-256: `5d9b0b859dab0015670db79bcfdfcbd1b3e830a8e953a708edd0c4a85604bb6b`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` gate_passed=`false`
- `capability_or_technical_narrative` state=`primary_artifact_ready` gate_passed=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` gate_passed=`true`
- `program_fit_and_argument_trace` state=`argument_conformance_blocked` gate_passed=`false`
- `eligibility_account_and_signer_authority` state=`sam_portal_and_signer_authority_required` gate_passed=`false`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` gate_passed=`false`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` gate_passed=`false`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` gate_passed=`false`
- `human_final_action_authority` state=`blocked_until_human_approval` gate_passed=`false`

Assembly blockers:
- Select and verify a current official topic before drafting or conformance scoring.
- Topic fit and official package requirements must be selected before drafting becomes submission assembly.

### 11. hhs_ai_power_user_pilot

- Name: HHS AI Power User Advanced Models and Features Pilot
- Channel: `federal_contract`
- Status: `DO_NOT_PRIME_SOLO`
- Legacy intake status: `DO_NOT_PRIME_SOLO`
- State source: `legacy_intake_baseline`
- Readiness mode: `PARKED_NO_SOLO_ACTION`
- Package status: `PARTNER_OR_NO_SOLO_BLOCKED`
- Submission conformance: `BLOCKED_BEFORE_SUBMISSION_CANDIDATE`
- Argument conformance pass: `false`
- Argument criteria passed: `0/10`
- Urgency: `PARKED_UNLESS_PARTNER`
- Action due: `2026-07-14`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`4f7520b12da081b0395f4ea821fe2be7bb8c6dcec6f6926908d112fe9b16b262`
- Component gates passed: `2/9`
- Can prepare internally: `false`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Qualified compliant platform or prime partner must lead before this lane is reopened.
- Next human action: Park as non-solo lane unless a qualified platform or prime partner leads.
- Claim boundary: No FedRAMP, ATO, HHS pilot, or government production-access claim.
- Row SHA-256: `dbfdbe0cf17fbc15617b107ce538de10a2fda0b5a4ce1026a25668772d64c364`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` gate_passed=`false`
- `capability_or_technical_narrative` state=`primary_artifact_ready` gate_passed=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` gate_passed=`true`
- `program_fit_and_argument_trace` state=`argument_conformance_blocked` gate_passed=`false`
- `eligibility_account_and_signer_authority` state=`sam_portal_and_signer_authority_required` gate_passed=`false`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` gate_passed=`false`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` gate_passed=`false`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` gate_passed=`false`
- `human_final_action_authority` state=`blocked_until_human_approval` gate_passed=`false`

Assembly blockers:
- Require a qualified prime or agency invitation before technical package work.
- This lane should not be pursued solo without a qualified partner or lead organization.

### 12. csosa_public_safety_analytics

- Name: CSOSA Public Safety Data Analytics Platform
- Channel: `federal_contract`
- Status: `DO_NOT_PRIME_SOLO`
- Legacy intake status: `DO_NOT_PRIME_SOLO`
- State source: `legacy_intake_baseline`
- Readiness mode: `PARKED_NO_SOLO_ACTION`
- Package status: `PARTNER_OR_NO_SOLO_BLOCKED`
- Submission conformance: `BLOCKED_BEFORE_SUBMISSION_CANDIDATE`
- Argument conformance pass: `false`
- Argument criteria passed: `0/10`
- Urgency: `PARKED_UNLESS_PARTNER`
- Action due: `2026-07-14`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`4f7520b12da081b0395f4ea821fe2be7bb8c6dcec6f6926908d112fe9b16b262`
- Component gates passed: `2/9`
- Can prepare internally: `false`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Qualified compliant platform or prime partner must lead before this lane is reopened.
- Next human action: Park as non-solo lane unless a qualified platform or prime partner leads.
- Claim boundary: No public-safety deployment, law-enforcement feed integration, or FedRAMP authorization claim.
- Row SHA-256: `81898081e4016ac24d6aea41adc49bc324b195976d4b6aa0fa8ade5a333b5372`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` gate_passed=`false`
- `capability_or_technical_narrative` state=`primary_artifact_ready` gate_passed=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` gate_passed=`true`
- `program_fit_and_argument_trace` state=`argument_conformance_blocked` gate_passed=`false`
- `eligibility_account_and_signer_authority` state=`sam_portal_and_signer_authority_required` gate_passed=`false`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` gate_passed=`false`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` gate_passed=`false`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` gate_passed=`false`
- `human_final_action_authority` state=`blocked_until_human_approval` gate_passed=`false`

Assembly blockers:
- Require a qualified prime, controlled-data boundary, and current official request.
- This lane should not be pursued solo without a qualified partner or lead organization.

### 13. defense_energy_consortium

- Name: Defense Energy Consortium CMO
- Channel: `federal_contract`
- Status: `PARTNER_INTRO_ONLY`
- Legacy intake status: `PARTNER_INTRO_ONLY`
- State source: `legacy_intake_baseline`
- Readiness mode: `INTRO_MATERIAL_READY_NO_SOLO_PROPOSAL`
- Package status: `PARTNER_OR_NO_SOLO_BLOCKED`
- Submission conformance: `BLOCKED_BEFORE_SUBMISSION_CANDIDATE`
- Argument conformance pass: `false`
- Argument criteria passed: `0/10`
- Urgency: `PARKED_UNLESS_PARTNER`
- Action due: `2026-07-30`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`4f7520b12da081b0395f4ea821fe2be7bb8c6dcec6f6926908d112fe9b16b262`
- Component gates passed: `2/9`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert approves any strategic partner or investor introduction before outreach.
- Next human action: Use as strategic-intro material, not a solo proposal.
- Claim boundary: No consortium management, energy project financing, or installation-performance claim.
- Row SHA-256: `aa98d5dccbaf805555e5dd2aed88f47375e3938d424edd660fcf0899c5bb7275`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` gate_passed=`false`
- `capability_or_technical_narrative` state=`primary_artifact_ready` gate_passed=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` gate_passed=`true`
- `program_fit_and_argument_trace` state=`argument_conformance_blocked` gate_passed=`false`
- `eligibility_account_and_signer_authority` state=`sam_portal_and_signer_authority_required` gate_passed=`false`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` gate_passed=`false`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` gate_passed=`false`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` gate_passed=`false`
- `human_final_action_authority` state=`blocked_until_human_approval` gate_passed=`false`

Assembly blockers:
- Wait for a concrete consortium problem statement or teaming request before a technical submission.
- Only intro material is ready; no solo proposal, pricing, or certification should be sent.

### 15. patent_deadline_counsel

- Name: Patent counsel / IP deadline defense
- Channel: `ip_readiness`
- Status: `OUTBOUND_SENT_INTAKE_RESPONSE_PENDING`
- Legacy intake status: `PRO_BONO_ROUTE_IDENTIFIED_HUMAN_ACTION_REQUIRED`
- State source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json#related:georgia_patents_pro_bono_intake`
- Readiness mode: `IP_PACKET_READY_COUNSEL_REQUIRED`
- Package status: `NO_CURRENT_SUBMISSION_ROUTE`
- Submission conformance: `NO_SUBMISSION_ARGUMENT_GATE_APPLICABLE`
- Argument conformance pass: `false`
- Argument criteria passed: `0/10`
- Urgency: `PAST_DATE_RECHECK`
- Action due: `2026-07-25`
- First artifact: `grant_submissions/funding_sprint_20260709/IP_PATENT_CLAIM_BOUNDARY_REGISTER_2026-07-09.md` sha256=`274d6212cdbd25c2a624375cf845ba9f3339c7ca9b111adfefe5034bf9f74cfb`
- Component gates passed: `5/9`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Licensed patent counsel and Robert decide any filing, continuation, PCT, disclosure, or claim strategy action.
- Next human action: Monitor counsel replies and prepare filed-materials packet for licensed review.
- Claim boundary: This receipt records transmission of a nonconfidential intake-routing inquiry only. It does not establish program eligibility, acceptance, attorney-client representation, confidentiality, a verified USPTO deadline, preservation of rights, patentability, prosecution status, funding, or legal advice.
- Row SHA-256: `d87023fc1ef4c12f0ee7b0bed9dfb1d79bb451fed56721c97ae5023fcbf17ee2`

Components:
- `official_source_and_instructions` state=`counsel_or_official_record_required` gate_passed=`false`
- `capability_or_technical_narrative` state=`invention_family_summary_ready` gate_passed=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` gate_passed=`true`
- `program_fit_and_argument_trace` state=`not_applicable_for_current_route` gate_passed=`true`
- `eligibility_account_and_signer_authority` state=`inventor_and_assignment_facts_required` gate_passed=`false`
- `cost_price_or_budget_basis` state=`not_required_for_counsel_packet` gate_passed=`true`
- `cyber_export_and_protected_data_boundary` state=`not_primary_gate` gate_passed=`true`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` gate_passed=`false`
- `human_final_action_authority` state=`blocked_until_human_approval` gate_passed=`false`

Assembly blockers:
- Licensed counsel must verify status, support, disclosure limits, and exact wording before IP claim expansion.

### 901. cdc_ai_acquisition_rfi

- Name: CDC AI for Acquisition Support RFI
- Channel: `federal_rfi`
- Status: `MONITOR_ONLY_NO_DUPLICATE_SUBMISSION`
- Legacy intake status: `MONITOR_ONLY_NO_DUPLICATE_SUBMISSION`
- State source: `submission_conformance_supplement`
- Readiness mode: `CONFORMANCE_SUPPLEMENT_ONLY`
- Package status: `MONITOR_ONLY_NO_DUPLICATE_SUBMISSION`
- Submission conformance: `MONITOR_ONLY_NO_DUPLICATE_SUBMISSION`
- Argument conformance pass: `false`
- Argument criteria passed: `0/10`
- Urgency: ``
- Action due: `None`
- First artifact: `grant_submissions/funding_sprint_20260709/CDC_AI_ACQUISITION_RFI_ARTIFACT_MANIFEST_2026-07-15.json` sha256=`68aba554d30f9caec5027705e4a3d8741e00447eedef74d5d089b54c600af7a1`
- Component gates passed: `2/9`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Human action-time authority
- Next human action: Monitor for a specific clarification, replacement request, or scheduling message and do not resend the packet.
- Claim boundary: A receipt acknowledgment is not an award, endorsement, technical validation, or agency selection.
- Row SHA-256: `42bce6c2046ffe2cb2e78b7a82733d8b6300d4b79d68b7deb63668b3bc6ac0d4`

Components:
- `official_source_and_instructions` state=`missing_source_reference` gate_passed=`false`
- `capability_or_technical_narrative` state=`primary_artifact_ready` gate_passed=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` gate_passed=`true`
- `program_fit_and_argument_trace` state=`argument_conformance_blocked` gate_passed=`false`
- `eligibility_account_and_signer_authority` state=`sam_portal_and_signer_authority_required` gate_passed=`false`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` gate_passed=`false`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` gate_passed=`false`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` gate_passed=`false`
- `human_final_action_authority` state=`blocked_until_human_approval` gate_passed=`false`

Assembly blockers:
- Monitor for a specific clarification, replacement request, or scheduling message and do not resend the packet.

### 904. darpa_falcon_dpa26bz04_dv016

- Name: DARPA FALCON Direct to Phase II
- Channel: `federal_sbir`
- Status: `TECHNICAL_NO_GO_EVIDENCE_SPRINT_ONLY`
- Legacy intake status: `TECHNICAL_NO_GO_EVIDENCE_SPRINT_ONLY`
- State source: `submission_conformance_supplement`
- Readiness mode: `CONFORMANCE_SUPPLEMENT_ONLY`
- Package status: `TECHNICAL_NO_GO_EVIDENCE_SPRINT_ONLY`
- Submission conformance: `TECHNICAL_NO_GO_EVIDENCE_SPRINT_ONLY`
- Argument conformance pass: `false`
- Argument criteria passed: `0/10`
- Urgency: ``
- Action due: `None`
- First artifact: `grant_submissions/DPA26BZ04_DV016_FALCON/DPA26BZ04_DV016_GO_NO_GO_AND_DP2_GAP_MAP_2026-07-15.md` sha256=`b713ca0b0e1293d5bc85093fc3ab9774cd7111b6526777fdd120d95ae820ff6b`
- Component gates passed: `2/9`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Human action-time authority
- Next human action: Continue only the frozen evidence sprint. Do not assemble or submit a proposal unless the technical, source, DP2 eligibility, IP, team, compute, transition, and independent-review gates all close before the official deadline.
- Claim boundary: No hybrid superiority, external validation, agency approval, enterprise-scale performance, universal superiority, scholarly impact, or DP2 eligibility is established.
- Row SHA-256: `852b535d0c324155f9d0a6b0c2615259abb72126200d25cc16cf9e28cb151421`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` gate_passed=`false`
- `capability_or_technical_narrative` state=`primary_artifact_ready` gate_passed=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` gate_passed=`true`
- `program_fit_and_argument_trace` state=`argument_conformance_blocked` gate_passed=`false`
- `eligibility_account_and_signer_authority` state=`dsip_or_sbir_authority_required` gate_passed=`false`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` gate_passed=`false`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` gate_passed=`false`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` gate_passed=`false`
- `human_final_action_authority` state=`blocked_until_human_approval` gate_passed=`false`

Assembly blockers:
- Continue only the frozen evidence sprint. Do not assemble or submit a proposal unless the technical, source, DP2 eligibility, IP, team, compute, transition, and independent-review gates all close before the official deadline.

### 909. erdc_sovereign_cloud_cso

- Name: ERDC Sovereign Defense Cloud CSO
- Channel: `federal_contract`
- Status: `BLOCKED_CRITERION_FAILURE`
- Legacy intake status: `BLOCKED_CRITERION_FAILURE`
- State source: `submission_conformance_supplement`
- Readiness mode: `CONFORMANCE_SUPPLEMENT_ONLY`
- Package status: `ARGUMENT_CONFORMANCE_BLOCKED_BEFORE_REVIEW`
- Submission conformance: `BLOCKED_CRITERION_FAILURE`
- Argument conformance pass: `false`
- Argument criteria passed: `3/10`
- Urgency: ``
- Action due: `None`
- First artifact: `grant_submissions/funding_sprint_20260709/ERDC_SDC_SOLUTION_BRIEF_COMPLIANCE_GATE_2026-07-29.json` sha256=`11fdbfec9044a8a5f23496dd9c3a642942c3ea83622b2e1d4c2ee31601d28389`
- Component gates passed: `2/9`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Human action-time authority
- Next human action: Publish the reviewed exact evidence files, bind a trust root outside the mutable receipt, have ERDC or an approved reviewer select the integrated comparator and HPCMP-representative workflow, lock mission and overhead thresholds, bind team, compute, integration, support, evaluator, and transition commitments, obtain independent execution, then separately complete the private ROM, SAM all-awards, contact, Submittable, and final portal gates.
- Claim boundary: Current-source custody, format and marker checks, a local synthetic ablation, and an explicit objective crosswalk do not establish applicant eligibility, reviewer readiness, public reproducibility, pricing, SAM readiness, technical merit, independent validation, selection, award, deployment, savings, or Government validation.
- Row SHA-256: `1476ca53de41424ba84b78e19e7542d2b6904f152b8e6d507df35a4834b491b3`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` gate_passed=`false`
- `capability_or_technical_narrative` state=`primary_artifact_ready` gate_passed=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` gate_passed=`true`
- `program_fit_and_argument_trace` state=`argument_conformance_blocked` gate_passed=`false`
- `eligibility_account_and_signer_authority` state=`sam_portal_and_signer_authority_required` gate_passed=`false`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` gate_passed=`false`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` gate_passed=`false`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` gate_passed=`false`
- `human_final_action_authority` state=`blocked_until_human_approval` gate_passed=`false`

Assembly blockers:
- Publish the reviewed exact evidence files, bind a trust root outside the mutable receipt, have ERDC or an approved reviewer select the integrated comparator and HPCMP-representative workflow, lock mission and overhead thresholds, bind team, compute, integration, support, evaluator, and transition commitments, obtain independent execution, then separately complete the private ROM, SAM all-awards, contact, Submittable, and final portal gates.

### 914. launchtn_3686_pitch_2026

- Name: Launch Tennessee 3686 Pitch Competition 2026
- Channel: `venture_pitch`
- Status: `BLOCKED_UNASSESSED_CRITERIA`
- Legacy intake status: `BLOCKED_UNASSESSED_CRITERIA`
- State source: `submission_conformance_supplement`
- Readiness mode: `CONFORMANCE_SUPPLEMENT_ONLY`
- Package status: `ARGUMENT_CONFORMANCE_BLOCKED_BEFORE_REVIEW`
- Submission conformance: `BLOCKED_UNASSESSED_CRITERIA`
- Argument conformance pass: `false`
- Argument criteria passed: `0/10`
- Urgency: ``
- Action due: `None`
- First artifact: `grant_submissions/LAUNCHTN_3686_PITCH_2026/LAUNCHTN_3686_PORTAL_FIELD_MAP_2026-07-17.md` sha256=`0fe19453f1595e4af89109824cb6d3ef58bb8234a199c4dd9c88bf7ad629bafd`
- Component gates passed: `2/9`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Human action-time authority
- Next human action: Recheck the first-party application source, resolve applicant facts and terms, and complete the full source-bound pitch argument and independent review before portal finalization.
- Claim boundary: A local application packet does not establish current eligibility, submission, receipt, finalist status, prize eligibility, funding, selection, investment, award, endorsement, or permission to disclose nonpublic information.
- Row SHA-256: `3bf2bf2e8413972df8c3e3f460b6a7bf8e4c28fa4c1d220d30ff1667488d3485`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` gate_passed=`false`
- `capability_or_technical_narrative` state=`primary_artifact_ready` gate_passed=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` gate_passed=`true`
- `program_fit_and_argument_trace` state=`argument_conformance_blocked` gate_passed=`false`
- `eligibility_account_and_signer_authority` state=`human_authority_required` gate_passed=`false`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` gate_passed=`false`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` gate_passed=`false`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` gate_passed=`false`
- `human_final_action_authority` state=`blocked_until_human_approval` gate_passed=`false`

Assembly blockers:
- Recheck the first-party application source, resolve applicant facts and terms, and complete the full source-bound pitch argument and independent review before portal finalization.
