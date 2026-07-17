# Agency Submission Assembly Gate - 2026-07-09

Purpose: Convert near-term federal, SBIR, RFI, lab, and IP lanes into an assembly checklist showing what is review-ready, what remains blocked, and who must authorize final action.

No federal, SBIR, RFI, lab, IP, certification, legal, pricing, portal, trading, or capital-impacting final action is authorized by this packet. It is an assembly and review gate only.

## Status

- Status: `AGENCY_SUBMISSION_ASSEMBLY_READY_HUMAN_GATED`
- Assembly lanes: `15`
- First artifacts present: `true`
- Reviewer gate clear: `true`
- Federal protocol status: `FEDERAL_SUBMISSION_PROTOCOL_READY_HUMAN_PORTAL_REQUIRED`
- Agency activation status: `AGENCY_ACCOUNT_ACTIVATION_READY_HUMAN_PORTAL_REQUIRED`
- Agency activation items: `8`
- Agency blocked items: `6`
- Authority lanes: `19`
- All final actions blocked without human: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Live trading allowed: `false`
- Capital movement allowed: `false`
- Unsafe sensitive hits: `0`
- Unsafe claim hits: `0`
- Assembly gate SHA-256: `9f96aa63f3abe5a2e8af671103a41a3ddb094ec35ed210e269577b57f45e7809`

## Package Status Counts

- `ASSEMBLED_FOR_REVIEW_FINAL_ACTION_BLOCKED`: `5`
- `COUNSEL_PACKET_READY_LEGAL_ACTION_BLOCKED`: `2`
- `FOLLOWUP_PACKET_READY_HUMAN_SEND_REQUIRED`: `1`
- `PARTNER_OR_NO_SOLO_BLOCKED`: `4`
- `SCOUT_READY_NOT_ASSEMBLED`: `1`
- `VALIDATION_WATCH_NOT_SUBMISSION`: `1`
- `WAIT_FOR_RESPONSE`: `1`

## Assembly Rows

### 0. sam_registration_external_validation_watch

- Name: SAM.gov registration external validation watch
- Channel: `federal_registration`
- Status: `SUBMITTED_EXTERNAL_VALIDATION_PENDING`
- Legacy intake status: `SUBMITTED_EXTERNAL_VALIDATION_PENDING`
- State source: `legacy_intake_baseline`
- Readiness mode: `FEDERAL_REGISTRATION_SUBMITTED_VALIDATION_PENDING`
- Package status: `VALIDATION_WATCH_NOT_SUBMISSION`
- Urgency: `URGENT_5D`
- Action due: `2026-07-13`
- First artifact: `grant_submissions/funding_sprint_20260709/SAM_SUBMISSION_AND_TODAY_OPPORTUNITY_PUSH_2026-07-09.md` sha256=`7f4f1a90c08f3c4df1b6f2b6d32b5b863a008a300f304feb807823846cdbf528`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert verifies SAM status, responds to any official DLA or SAM request, and approves any notarized Entity Administrator letter or correction.
- Next human action: Check SAM status and watch for any DLA email; prepare Entity Administrator letter packet if required.
- Claim boundary: Submitted is not Active; no award eligibility, active registration, or CAGE validation is claimed until SAM confirms it.
- Row SHA-256: `b92e17451dbe8770685986d606819aa2090f18335efbf791b4da870be84d541b`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` review_ready=`true`
- `capability_or_technical_narrative` state=`not_required_for_registration_watch` review_ready=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` review_ready=`true`
- `eligibility_account_and_signer_authority` state=`human_authority_required` review_ready=`true`
- `cost_price_or_budget_basis` state=`not_required_for_registration_watch` review_ready=`true`
- `cyber_export_and_protected_data_boundary` state=`watch_only` review_ready=`true`
- `ip_disclosure_and_counsel_boundary` state=`watch_only` review_ready=`true`
- `human_final_action_authority` state=`blocked_until_human_approval` review_ready=`true`

Assembly blockers:
- SAM.gov submission is not the same as Active status.
- External IRS/CAGE/DLA or SAM validation must clear before eligibility language is promoted.

### 2. lanl_vision_licensing_followup

- Name: LANL VISION licensing opportunity follow-up
- Channel: `federal_lab_tech_transfer`
- Status: `OUTBOUND_SENT_RESPONSE_PENDING`
- Legacy intake status: `WAITING_POC_RETURN`
- State source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json`
- Readiness mode: `LAB_POC_FOLLOWUP_READY_HUMAN_SEND_REQUIRED`
- Package status: `FOLLOWUP_PACKET_READY_HUMAN_SEND_REQUIRED`
- Urgency: `URGENT_5D`
- Action due: `2026-07-13`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`9cdcad79bb7bf3041ce817f832d8cbfaf58f6076d30211f8d5d4e6d192d9de9f`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert approves any lab POC reply, NDA, licensing discussion, export-control response, or disclosure packet.
- Next human action: Prepare concise licensing-fit note and technical questions for the named LANL POC return window.
- Claim boundary: This is a POC routing response only; no LANL license, partnership, endorsement, or technical validation is claimed.
- Row SHA-256: `3561eab433065d460f224f67fee910e4e05b3f532b8134a18159fae6c7552a4d`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` review_ready=`true`
- `capability_or_technical_narrative` state=`primary_artifact_ready` review_ready=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` review_ready=`true`
- `eligibility_account_and_signer_authority` state=`human_followup_authority_required` review_ready=`true`
- `cost_price_or_budget_basis` state=`not_required_for_initial_followup` review_ready=`true`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` review_ready=`true`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` review_ready=`true`
- `human_final_action_authority` state=`blocked_until_human_approval` review_ready=`true`

Assembly blockers:
- No lab license, partnership, or technology-transfer relationship is claimed.
- Human approves any follow-up content and disclosure boundary.

### 3. uspto_georgia_patents_route

- Name: USPTO / Georgia PATENTS pro bono routing
- Channel: `ip_readiness`
- Status: `OUTBOUND_SENT_INTAKE_RESPONSE_PENDING`
- Legacy intake status: `PRO_BONO_ROUTE_IDENTIFIED_HUMAN_ACTION_REQUIRED`
- State source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json#related:georgia_patents_pro_bono_intake`
- Readiness mode: `IP_PACKET_READY_COUNSEL_REQUIRED`
- Package status: `COUNSEL_PACKET_READY_LEGAL_ACTION_BLOCKED`
- Urgency: `IMMEDIATE_24H`
- Action due: `2026-07-10`
- First artifact: `grant_submissions/funding_sprint_20260709/IP_COUNSEL_DILIGENCE_PACKET_2026-07-09.md` sha256=`e9efbb7e405cc0dc8d283f991e353df8ff78f69864bde2aab0159839f8ecd306`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Licensed patent counsel and Robert decide any filing, continuation, PCT, disclosure, or claim strategy action.
- Next human action: Prepare Georgia PATENTS intake packet and counsel questions.
- Claim boundary: This is not legal advice and does not assert patentability, ownership, deadline sufficiency, or filing entitlement.
- Row SHA-256: `dfa4ffd398a9427e9bf99df2961db62096f901284b6219d4511c5dfae5ff9fe7`

Components:
- `official_source_and_instructions` state=`counsel_or_official_record_required` review_ready=`true`
- `capability_or_technical_narrative` state=`invention_family_summary_ready` review_ready=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` review_ready=`true`
- `eligibility_account_and_signer_authority` state=`inventor_and_assignment_facts_required` review_ready=`true`
- `cost_price_or_budget_basis` state=`not_required_for_counsel_packet` review_ready=`true`
- `cyber_export_and_protected_data_boundary` state=`not_primary_gate` review_ready=`true`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` review_ready=`true`
- `human_final_action_authority` state=`blocked_until_human_approval` review_ready=`true`

Assembly blockers:
- Licensed counsel must verify status, support, disclosure limits, and exact wording before IP claim expansion.

### 3. darpa_dice_full_submission

- Name: DARPA DICE full proposal sprint
- Channel: `federal_baa`
- Status: `FULL_PROPOSAL_SPRINT`
- Legacy intake status: `FULL_PROPOSAL_SPRINT`
- State source: `legacy_intake_baseline`
- Readiness mode: `FEDERAL_DRAFT_READY_SUBMISSION_BLOCKED`
- Package status: `ASSEMBLED_FOR_REVIEW_FINAL_ACTION_BLOCKED`
- Urgency: `URGENT_5D`
- Action due: `2026-07-12`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`9cdcad79bb7bf3041ce817f832d8cbfaf58f6076d30211f8d5d4e6d192d9de9f`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert verifies the controlling BAA instructions, submission account authority, budget, representations, and final package.
- Next human action: Build full-proposal compliance matrix and confirm controlling BAA instructions.
- Claim boundary: Abstract receipt is not award selection and not permission to skip BAA instructions.
- Row SHA-256: `9e68964cfc341021abd7e8d4863342b0a078eb2da44df356babf76cc27d16b8d`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` review_ready=`true`
- `capability_or_technical_narrative` state=`primary_artifact_ready` review_ready=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` review_ready=`true`
- `eligibility_account_and_signer_authority` state=`sam_portal_and_signer_authority_required` review_ready=`true`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` review_ready=`true`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` review_ready=`true`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` review_ready=`true`
- `human_final_action_authority` state=`blocked_until_human_approval` review_ready=`true`

Assembly blockers:
- Official BAA/RFI instructions, attachment limits, and submission channel must be checked at action time.
- Cost, team, compliance, and upload preview remain human-gated.

### 4. fhwa_tsmo_data_initiative

- Name: FHWA TSMO Data Initiative
- Channel: `federal_contract`
- Status: `QUALIFIED_RESPONSE_LEAD_REFERRAL_ACKNOWLEDGED_FIT_CHECK_PENDING`
- Legacy intake status: `PHASE_I_TECH_VOLUME`
- State source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json#related:fhwa_tsmo_qualified_partner_outreach`
- Readiness mode: `FEDERAL_DRAFT_READY_SUBMISSION_BLOCKED`
- Package status: `ASSEMBLED_FOR_REVIEW_FINAL_ACTION_BLOCKED`
- Urgency: `ROLLING_OR_EVENT_GATED`
- Action due: `None`
- First artifact: `grant_submissions/funding_sprint_20260709/FHWA_TSMO_PHASE1_TECHNICAL_CAPABILITY_OUTLINE_2026-07-09.md` sha256=`f6d090ccc82b6564449476be4c348b21f92554ffad9abe90dbb863744ebfa046`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert verifies SAM access, solicitation attachments, pricing, reps/certs, and authorized representative status before submission.
- Next human action: Monitor the referred response lead for scheduling or a specific question and do not reuse the rejected address. If no response arrives by July 21, send at most one short scheduling follow-up. Before any teaming or proposal claim, verify written role, documentable corporate experience, conflicts, references, facilities, data rights, and schedule.
- Claim boundary: Prepared capability material only; no FHWA field result, safety benefit, or deployment claim.
- Row SHA-256: `8e6d50d96d3e4c7d1ea19e2ea06451a89432ee46fef4451f8fe79c0d03b435e7`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` review_ready=`true`
- `capability_or_technical_narrative` state=`primary_artifact_ready` review_ready=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` review_ready=`true`
- `eligibility_account_and_signer_authority` state=`sam_portal_and_signer_authority_required` review_ready=`true`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` review_ready=`true`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` review_ready=`true`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` review_ready=`true`
- `human_final_action_authority` state=`blocked_until_human_approval` review_ready=`true`

Assembly blockers:
- Official BAA/RFI instructions, attachment limits, and submission channel must be checked at action time.
- Cost, team, compliance, and upload preview remain human-gated.

### 5. nasa_data_center_rfi

- Name: NASA Data Center Infrastructure RFI
- Channel: `federal_rfi`
- Status: `SENT_VERIFIED_RESPONSE_PENDING`
- Legacy intake status: `RFI_RESPONSE_PREP`
- State source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json`
- Readiness mode: `RFI_DRAFT_READY_SEND_BLOCKED`
- Package status: `ASSEMBLED_FOR_REVIEW_FINAL_ACTION_BLOCKED`
- Urgency: `ROLLING_OR_EVENT_GATED`
- Action due: `None`
- First artifact: `grant_submissions/funding_sprint_20260709/NASA_DATA_CENTER_RFI_RESPONSE_OUTLINE_2026-07-09.md` sha256=`bcfdd40dfafc7ca0e7822679dba9d2504c2196b5701704d0ba3d46c5ce9448f6`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert verifies official RFI instructions, contact address, page limits, and final send approval.
- Next human action: Retain the SENT receipt and attachment hash; do not resend before the deadline.
- Claim boundary: RFI response only; no NASA partnership, contract, or infrastructure result is represented.
- Row SHA-256: `31e8ff7079f8c3ada3e6c8d1cc1cc49cee257ff983626d2ee72318666b2c5f5e`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` review_ready=`true`
- `capability_or_technical_narrative` state=`primary_artifact_ready` review_ready=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` review_ready=`true`
- `eligibility_account_and_signer_authority` state=`sam_portal_and_signer_authority_required` review_ready=`true`
- `cost_price_or_budget_basis` state=`not_required_for_initial_response` review_ready=`true`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` review_ready=`true`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` review_ready=`true`
- `human_final_action_authority` state=`blocked_until_human_approval` review_ready=`true`

Assembly blockers:
- Official RFI send route, page limits, and attachment rules must be verified.
- Human must approve response wording before send.

### 6. dla_missionweave_sbir

- Name: DLA MissionWeave DSIP SBIR
- Channel: `federal_sbir`
- Status: `PRIVATE_DSIP_FACTS_CAPTURED_GATES_OPEN`
- Legacy intake status: `DSIP_PACKAGE_PREP`
- State source: `grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json`
- Readiness mode: `SBIR_DRAFT_READY_PORTAL_BLOCKED`
- Package status: `ASSEMBLED_FOR_REVIEW_FINAL_ACTION_BLOCKED`
- Urgency: `ROLLING_OR_EVENT_GATED`
- Action due: `None`
- First artifact: `grant_submissions/funding_sprint_20260709/DSIP_MISSIONWEAVE_FAST_SUBMISSION_PLAN_2026-07-09.md` sha256=`cf0d3fd466ecfd8396d17f1c4787a7fa2898f49ee5f81ed377df05aa161029c4`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert controls DSIP or SBIR portal login, Firm PIN, cost approval, certifications, and final submit.
- Next human action: Resolve the 37 open gates out of 50, review the complete portal preview, and retain the human-only final-submit boundary.
- Claim boundary: No DLA integration, procurement, or certified readiness claim.
- Row SHA-256: `3ee0614a94cfa9413821deba52c5248f8bc451bcdf07668f87efeb4c6e478a30`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` review_ready=`true`
- `capability_or_technical_narrative` state=`primary_artifact_ready` review_ready=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` review_ready=`true`
- `eligibility_account_and_signer_authority` state=`dsip_or_sbir_authority_required` review_ready=`true`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` review_ready=`true`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` review_ready=`true`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` review_ready=`true`
- `human_final_action_authority` state=`blocked_until_human_approval` review_ready=`true`

Assembly blockers:
- DSIP firm linkage, Firm PIN, topic workspace, forms, cost volume, and certifications remain human-gated.
- No DSIP submit or certification action is authorized by local files.

### 7. nsf_project_pitch

- Name: NSF SBIR/STTR Project Pitch
- Channel: `federal_sbir`
- Status: `PITCH_READY_HUMAN_CHECK`
- Legacy intake status: `PITCH_READY_HUMAN_CHECK`
- State source: `legacy_intake_baseline`
- Readiness mode: `ROLLING_GATE_READY_RULE_CHECK_REQUIRED`
- Package status: `ASSEMBLED_FOR_REVIEW_FINAL_ACTION_BLOCKED`
- Urgency: `ROLLING_OR_EVENT_GATED`
- Action due: `None`
- First artifact: `grant_submissions/funding_sprint_20260709/NSF_PROJECT_PITCH_DRAFT_2026-07-09.md` sha256=`baa66ab948fdc1bb57e898d8a6e4e0bf776c65ff4c6722ef658720c148f40e6f`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert verifies account status, platform-specific rules, one-pending-pitch limits, and final content before submit.
- Next human action: Check the one-pending-pitch rule before any Project Pitch submit.
- Claim boundary: No NSF invitation or full-proposal eligibility is represented unless NSF issues it.
- Row SHA-256: `9e682652ee706ae53f99910ef119c877a500942d07cd9635bc69986b316f8624`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` review_ready=`true`
- `capability_or_technical_narrative` state=`primary_artifact_ready` review_ready=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` review_ready=`true`
- `eligibility_account_and_signer_authority` state=`dsip_or_sbir_authority_required` review_ready=`true`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` review_ready=`true`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` review_ready=`true`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` review_ready=`true`
- `human_final_action_authority` state=`blocked_until_human_approval` review_ready=`true`

Assembly blockers:
- NSF account, pending-pitch status, invitation state, and one-pending-pitch rule must be checked.
- No Research.gov or NSF final action is authorized by local files.

### 8. epa_r10_icpoes_route

- Name: EPA Region 10 ICP-OES RFI route
- Channel: `federal_market_research`
- Status: `ROUTE_ONLY_LOW_FIT`
- Legacy intake status: `ROUTE_ONLY_LOW_FIT`
- State source: `legacy_intake_baseline`
- Readiness mode: `ROUTING_SENT_WAIT_FOR_RESPONSE`
- Package status: `WAIT_FOR_RESPONSE`
- Urgency: `ACTIVE_14D`
- Action due: `2026-07-21`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`9cdcad79bb7bf3041ce817f832d8cbfaf58f6076d30211f8d5d4e6d192d9de9f`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert approves any further agency contact after a routing response.
- Next human action: Wait for routing response; do not prepare a prime bid.
- Claim boundary: No instrument supply, OEM, reseller, or lab-services qualification claim.
- Row SHA-256: `cb73a1937206d27b02b6a6301d04e457c6d903df3106f0de4324d3bd0221c3c0`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` review_ready=`true`
- `capability_or_technical_narrative` state=`primary_artifact_ready` review_ready=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` review_ready=`true`
- `eligibility_account_and_signer_authority` state=`human_routing_authority_required` review_ready=`true`
- `cost_price_or_budget_basis` state=`not_required_for_routing_watch` review_ready=`true`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` review_ready=`true`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` review_ready=`true`
- `human_final_action_authority` state=`blocked_until_human_approval` review_ready=`true`

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
- Urgency: `PARKED_UNLESS_PARTNER`
- Action due: `2026-07-21`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`9cdcad79bb7bf3041ce817f832d8cbfaf58f6076d30211f8d5d4e6d192d9de9f`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Qualified partner and Robert approve any partner-led response.
- Next human action: Find qualified partner before any response draft.
- Claim boundary: No testing lab, contaminant monitoring, or regulated lab-services claim.
- Row SHA-256: `ea7ba288a1bbeb4e9df12ee16558b80a2886985df27b147254dadf2c2e8e1444`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` review_ready=`true`
- `capability_or_technical_narrative` state=`primary_artifact_ready` review_ready=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` review_ready=`true`
- `eligibility_account_and_signer_authority` state=`partner_authority_required` review_ready=`true`
- `cost_price_or_budget_basis` state=`not_required_until_partner_or_sources_sought_response` review_ready=`true`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` review_ready=`true`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` review_ready=`true`
- `human_final_action_authority` state=`blocked_until_human_approval` review_ready=`true`

Assembly blockers:
- Qualified prime, jurisdictional owner, lab, testbed, or domain partner is required before any solo package is promoted.

### 10. fhwa_infrastructure_baa_call3

- Name: FHWA Infrastructure R&D BAA Call 3.0
- Channel: `federal_baa`
- Status: `SCOUT_TOPIC_MATCH`
- Legacy intake status: `SCOUT_TOPIC_MATCH`
- State source: `legacy_intake_baseline`
- Readiness mode: `TOPIC_SCOUT_READY_SELECTION_REQUIRED`
- Package status: `SCOUT_READY_NOT_ASSEMBLED`
- Urgency: `WATCHLIST`
- Action due: `2026-07-24`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`9cdcad79bb7bf3041ce817f832d8cbfaf58f6076d30211f8d5d4e6d192d9de9f`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert approves topic selection after official attachments and topic fit are reviewed.
- Next human action: Review official attachments and score topic fit before drafting.
- Claim boundary: No claim that LumenCore fits all BAA topics.
- Row SHA-256: `1f37abab9d40dab00641a252fc89407ed9edf8cbf8b74e149ef0e8a6a0a99989`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` review_ready=`true`
- `capability_or_technical_narrative` state=`primary_artifact_ready` review_ready=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` review_ready=`true`
- `eligibility_account_and_signer_authority` state=`sam_portal_and_signer_authority_required` review_ready=`true`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` review_ready=`true`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` review_ready=`true`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` review_ready=`true`
- `human_final_action_authority` state=`blocked_until_human_approval` review_ready=`true`

Assembly blockers:
- Topic fit and official package requirements must be selected before drafting becomes submission assembly.

### 11. hhs_ai_power_user_pilot

- Name: HHS AI Power User Advanced Models and Features Pilot
- Channel: `federal_contract`
- Status: `DO_NOT_PRIME_SOLO`
- Legacy intake status: `DO_NOT_PRIME_SOLO`
- State source: `legacy_intake_baseline`
- Readiness mode: `PARKED_NO_SOLO_ACTION`
- Package status: `PARTNER_OR_NO_SOLO_BLOCKED`
- Urgency: `PARKED_UNLESS_PARTNER`
- Action due: `2026-07-14`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`9cdcad79bb7bf3041ce817f832d8cbfaf58f6076d30211f8d5d4e6d192d9de9f`
- Review-ready components: `8/8`
- Can prepare internally: `false`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Qualified compliant platform or prime partner must lead before this lane is reopened.
- Next human action: Park as non-solo lane unless a qualified platform or prime partner leads.
- Claim boundary: No FedRAMP, ATO, HHS pilot, or government production-access claim.
- Row SHA-256: `db5460b5fee41a7715d923003ee77bcd9a0b57ee29e556480e173c65210721aa`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` review_ready=`true`
- `capability_or_technical_narrative` state=`primary_artifact_ready` review_ready=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` review_ready=`true`
- `eligibility_account_and_signer_authority` state=`sam_portal_and_signer_authority_required` review_ready=`true`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` review_ready=`true`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` review_ready=`true`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` review_ready=`true`
- `human_final_action_authority` state=`blocked_until_human_approval` review_ready=`true`

Assembly blockers:
- This lane should not be pursued solo without a qualified partner or lead organization.

### 12. csosa_public_safety_analytics

- Name: CSOSA Public Safety Data Analytics Platform
- Channel: `federal_contract`
- Status: `DO_NOT_PRIME_SOLO`
- Legacy intake status: `DO_NOT_PRIME_SOLO`
- State source: `legacy_intake_baseline`
- Readiness mode: `PARKED_NO_SOLO_ACTION`
- Package status: `PARTNER_OR_NO_SOLO_BLOCKED`
- Urgency: `PARKED_UNLESS_PARTNER`
- Action due: `2026-07-14`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`9cdcad79bb7bf3041ce817f832d8cbfaf58f6076d30211f8d5d4e6d192d9de9f`
- Review-ready components: `8/8`
- Can prepare internally: `false`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Qualified compliant platform or prime partner must lead before this lane is reopened.
- Next human action: Park as non-solo lane unless a qualified platform or prime partner leads.
- Claim boundary: No public-safety deployment, law-enforcement feed integration, or FedRAMP authorization claim.
- Row SHA-256: `5473a65c33ffe803d8735495db782308c78e8b60f24b6ad6f46e341bc5dabd8c`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` review_ready=`true`
- `capability_or_technical_narrative` state=`primary_artifact_ready` review_ready=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` review_ready=`true`
- `eligibility_account_and_signer_authority` state=`sam_portal_and_signer_authority_required` review_ready=`true`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` review_ready=`true`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` review_ready=`true`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` review_ready=`true`
- `human_final_action_authority` state=`blocked_until_human_approval` review_ready=`true`

Assembly blockers:
- This lane should not be pursued solo without a qualified partner or lead organization.

### 13. defense_energy_consortium

- Name: Defense Energy Consortium CMO
- Channel: `federal_contract`
- Status: `PARTNER_INTRO_ONLY`
- Legacy intake status: `PARTNER_INTRO_ONLY`
- State source: `legacy_intake_baseline`
- Readiness mode: `INTRO_MATERIAL_READY_NO_SOLO_PROPOSAL`
- Package status: `PARTNER_OR_NO_SOLO_BLOCKED`
- Urgency: `PARKED_UNLESS_PARTNER`
- Action due: `2026-07-30`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`9cdcad79bb7bf3041ce817f832d8cbfaf58f6076d30211f8d5d4e6d192d9de9f`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert approves any strategic partner or investor introduction before outreach.
- Next human action: Use as strategic-intro material, not a solo proposal.
- Claim boundary: No consortium management, energy project financing, or installation-performance claim.
- Row SHA-256: `f4da07a8857f45213263642a39dafd1e4c18b749f0bae8e475fad47e1135715d`

Components:
- `official_source_and_instructions` state=`source_identified_human_recheck_required` review_ready=`true`
- `capability_or_technical_narrative` state=`primary_artifact_ready` review_ready=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` review_ready=`true`
- `eligibility_account_and_signer_authority` state=`sam_portal_and_signer_authority_required` review_ready=`true`
- `cost_price_or_budget_basis` state=`cost_or_price_review_required` review_ready=`true`
- `cyber_export_and_protected_data_boundary` state=`fci_cui_export_cyber_check_required` review_ready=`true`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` review_ready=`true`
- `human_final_action_authority` state=`blocked_until_human_approval` review_ready=`true`

Assembly blockers:
- Only intro material is ready; no solo proposal, pricing, or certification should be sent.

### 15. patent_deadline_counsel

- Name: Patent counsel / IP deadline defense
- Channel: `ip_readiness`
- Status: `OUTBOUND_SENT_INTAKE_RESPONSE_PENDING`
- Legacy intake status: `PRO_BONO_ROUTE_IDENTIFIED_HUMAN_ACTION_REQUIRED`
- State source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json#related:georgia_patents_pro_bono_intake`
- Readiness mode: `IP_PACKET_READY_COUNSEL_REQUIRED`
- Package status: `COUNSEL_PACKET_READY_LEGAL_ACTION_BLOCKED`
- Urgency: `WATCHLIST`
- Action due: `2026-07-25`
- First artifact: `grant_submissions/funding_sprint_20260709/IP_PATENT_CLAIM_BOUNDARY_REGISTER_2026-07-09.md` sha256=`274d6212cdbd25c2a624375cf845ba9f3339c7ca9b111adfefe5034bf9f74cfb`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Licensed patent counsel and Robert decide any filing, continuation, PCT, disclosure, or claim strategy action.
- Next human action: Monitor counsel replies and prepare filed-materials packet for licensed review.
- Claim boundary: This ledger is not legal advice and does not assert patentability, ownership, or filing sufficiency.
- Row SHA-256: `04a28a9f819158631f035c33352c439c79592af225de681e1ead9d2d83ddfed7`

Components:
- `official_source_and_instructions` state=`counsel_or_official_record_required` review_ready=`true`
- `capability_or_technical_narrative` state=`invention_family_summary_ready` review_ready=`true`
- `evidence_annex_and_proof_boundary` state=`hashable_artifacts_claim_bounded` review_ready=`true`
- `eligibility_account_and_signer_authority` state=`inventor_and_assignment_facts_required` review_ready=`true`
- `cost_price_or_budget_basis` state=`not_required_for_counsel_packet` review_ready=`true`
- `cyber_export_and_protected_data_boundary` state=`not_primary_gate` review_ready=`true`
- `ip_disclosure_and_counsel_boundary` state=`counsel_boundary_required` review_ready=`true`
- `human_final_action_authority` state=`blocked_until_human_approval` review_ready=`true`

Assembly blockers:
- Licensed counsel must verify status, support, disclosure limits, and exact wording before IP claim expansion.
