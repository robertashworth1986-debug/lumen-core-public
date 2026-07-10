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
- Assembly gate SHA-256: `70a60614ffbd17ba49b9143dc481099367c91f93cfa51bc633d924c7227ea338`

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
- Row SHA-256: `fff8f2b49219b6072bd225cae4ef3c7c4cd150d7848ec9395096e5757e4761d9`

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
- Status: `WAITING_POC_RETURN`
- Readiness mode: `LAB_POC_FOLLOWUP_READY_HUMAN_SEND_REQUIRED`
- Package status: `FOLLOWUP_PACKET_READY_HUMAN_SEND_REQUIRED`
- Urgency: `URGENT_5D`
- Action due: `2026-07-13`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`e6bcabe153e9bccee645a489dd32e69550c078ce6e07c0e600d8e37fc75f6e55`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert approves any lab POC reply, NDA, licensing discussion, export-control response, or disclosure packet.
- Next human action: Prepare concise licensing-fit note and technical questions for the named LANL POC return window.
- Claim boundary: This is a POC routing response only; no LANL license, partnership, endorsement, or technical validation is claimed.
- Row SHA-256: `dad3c03d4f2dbb0437232991813706152db271627545b9cd54b76c253aff5774`

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
- Status: `PRO_BONO_ROUTE_IDENTIFIED_HUMAN_ACTION_REQUIRED`
- Readiness mode: `IP_PACKET_READY_COUNSEL_REQUIRED`
- Package status: `COUNSEL_PACKET_READY_LEGAL_ACTION_BLOCKED`
- Urgency: `IMMEDIATE_24H`
- Action due: `2026-07-10`
- First artifact: `grant_submissions/funding_sprint_20260709/IP_COUNSEL_DILIGENCE_PACKET_2026-07-09.md` sha256=`a3354fec70f9ae12a0bf42c24a2f1699f05ba0d05880afa16264080b1a1860ee`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Licensed patent counsel and Robert decide any filing, continuation, PCT, disclosure, or claim strategy action.
- Next human action: Prepare Georgia PATENTS intake packet and counsel questions.
- Claim boundary: This is not legal advice and does not assert patentability, ownership, deadline sufficiency, or filing entitlement.
- Row SHA-256: `8ce0abfa57e004025e2f821057a5bf2c5a88db9c8580d9d55b4b25b8e1f8b6db`

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
- Readiness mode: `FEDERAL_DRAFT_READY_SUBMISSION_BLOCKED`
- Package status: `ASSEMBLED_FOR_REVIEW_FINAL_ACTION_BLOCKED`
- Urgency: `URGENT_5D`
- Action due: `2026-07-12`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`e6bcabe153e9bccee645a489dd32e69550c078ce6e07c0e600d8e37fc75f6e55`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert verifies the controlling BAA instructions, submission account authority, budget, representations, and final package.
- Next human action: Build full-proposal compliance matrix and confirm controlling BAA instructions.
- Claim boundary: Abstract receipt is not award selection and not permission to skip BAA instructions.
- Row SHA-256: `0e35771a739505864d533c21ecf9508674ec48c149df72679dab8d752b30793b`

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
- Status: `PHASE_I_TECH_VOLUME`
- Readiness mode: `FEDERAL_DRAFT_READY_SUBMISSION_BLOCKED`
- Package status: `ASSEMBLED_FOR_REVIEW_FINAL_ACTION_BLOCKED`
- Urgency: `WATCHLIST`
- Action due: `2026-08-03`
- First artifact: `grant_submissions/funding_sprint_20260709/FHWA_TSMO_PHASE1_TECHNICAL_CAPABILITY_OUTLINE_2026-07-09.md` sha256=`f6d090ccc82b6564449476be4c348b21f92554ffad9abe90dbb863744ebfa046`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert verifies SAM access, solicitation attachments, pricing, reps/certs, and authorized representative status before submission.
- Next human action: Convert the current outline into a human-review package with compliance checklist, pricing stop, and source attachment check.
- Claim boundary: Prepared capability material only; no FHWA field result, safety benefit, or deployment claim.
- Row SHA-256: `aa4199c6af91836b4cccbdc40451dc60ca3522cd1abe8102faf45cd5b7cd9073`

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
- Status: `RFI_RESPONSE_PREP`
- Readiness mode: `RFI_DRAFT_READY_SEND_BLOCKED`
- Package status: `ASSEMBLED_FOR_REVIEW_FINAL_ACTION_BLOCKED`
- Urgency: `ACTIVE_14D`
- Action due: `2026-07-17`
- First artifact: `grant_submissions/funding_sprint_20260709/NASA_DATA_CENTER_RFI_RESPONSE_OUTLINE_2026-07-09.md` sha256=`bcfdd40dfafc7ca0e7822679dba9d2504c2196b5701704d0ba3d46c5ce9448f6`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert verifies official RFI instructions, contact address, page limits, and final send approval.
- Next human action: Prepare a bounded response draft and verify official response instructions before send.
- Claim boundary: RFI response only; no NASA partnership, contract, or infrastructure result is represented.
- Row SHA-256: `ff354396c87764aca4ae3f0968cc2f3215bd5dcadb1d823666427cc12e910231`

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
- Status: `DSIP_PACKAGE_PREP`
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
- Next human action: Prepare technical volume, cost notes, and Firm PIN handoff checklist.
- Claim boundary: No DLA integration, procurement, or certified readiness claim.
- Row SHA-256: `80e6c84f4928f283f8d7a23177d60f964531ddfbe70418e89823c4e21631270b`

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
- Row SHA-256: `e21bd5a7a4e9095ba712b74084984f35ad60bdd232720823d279a76f2369430c`

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
- Readiness mode: `ROUTING_SENT_WAIT_FOR_RESPONSE`
- Package status: `WAIT_FOR_RESPONSE`
- Urgency: `ACTIVE_14D`
- Action due: `2026-07-21`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`e6bcabe153e9bccee645a489dd32e69550c078ce6e07c0e600d8e37fc75f6e55`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert approves any further agency contact after a routing response.
- Next human action: Wait for routing response; do not prepare a prime bid.
- Claim boundary: No instrument supply, OEM, reseller, or lab-services qualification claim.
- Row SHA-256: `33cc48f5664d89455678fe10589460221358862d0b06d372f0610ce348b5762a`

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
- Readiness mode: `PARTNER_REQUIRED_NO_SOLO_SUBMISSION`
- Package status: `PARTNER_OR_NO_SOLO_BLOCKED`
- Urgency: `PARKED_UNLESS_PARTNER`
- Action due: `2026-07-21`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`e6bcabe153e9bccee645a489dd32e69550c078ce6e07c0e600d8e37fc75f6e55`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Qualified partner and Robert approve any partner-led response.
- Next human action: Find qualified partner before any response draft.
- Claim boundary: No testing lab, contaminant monitoring, or regulated lab-services claim.
- Row SHA-256: `8cb6190184f78cc75db67b667c668eab645cef1d3290ce58cb1d5f56a799aafd`

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
- Readiness mode: `TOPIC_SCOUT_READY_SELECTION_REQUIRED`
- Package status: `SCOUT_READY_NOT_ASSEMBLED`
- Urgency: `WATCHLIST`
- Action due: `2026-07-24`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`e6bcabe153e9bccee645a489dd32e69550c078ce6e07c0e600d8e37fc75f6e55`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert approves topic selection after official attachments and topic fit are reviewed.
- Next human action: Review official attachments and score topic fit before drafting.
- Claim boundary: No claim that LumenCore fits all BAA topics.
- Row SHA-256: `9de3e0ae8ad03f06d62f25f8b827df9cc6f729c40ab3ad713606181a66d3787f`

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
- Readiness mode: `PARKED_NO_SOLO_ACTION`
- Package status: `PARTNER_OR_NO_SOLO_BLOCKED`
- Urgency: `PARKED_UNLESS_PARTNER`
- Action due: `2026-07-14`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`e6bcabe153e9bccee645a489dd32e69550c078ce6e07c0e600d8e37fc75f6e55`
- Review-ready components: `8/8`
- Can prepare internally: `false`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Qualified compliant platform or prime partner must lead before this lane is reopened.
- Next human action: Park as non-solo lane unless a qualified platform or prime partner leads.
- Claim boundary: No FedRAMP, ATO, HHS pilot, or government production-access claim.
- Row SHA-256: `e750b5b627a51fd2bfaa88e2bf704514c20af45f2ed05ae16a61de2fe369cae5`

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
- Readiness mode: `PARKED_NO_SOLO_ACTION`
- Package status: `PARTNER_OR_NO_SOLO_BLOCKED`
- Urgency: `PARKED_UNLESS_PARTNER`
- Action due: `2026-07-14`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`e6bcabe153e9bccee645a489dd32e69550c078ce6e07c0e600d8e37fc75f6e55`
- Review-ready components: `8/8`
- Can prepare internally: `false`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Qualified compliant platform or prime partner must lead before this lane is reopened.
- Next human action: Park as non-solo lane unless a qualified platform or prime partner leads.
- Claim boundary: No public-safety deployment, law-enforcement feed integration, or FedRAMP authorization claim.
- Row SHA-256: `3a7b0d825d28da6d0cbe625d4bac20e629ffea703c6ce642720a720192818a95`

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
- Readiness mode: `INTRO_MATERIAL_READY_NO_SOLO_PROPOSAL`
- Package status: `PARTNER_OR_NO_SOLO_BLOCKED`
- Urgency: `PARKED_UNLESS_PARTNER`
- Action due: `2026-07-30`
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md` sha256=`e6bcabe153e9bccee645a489dd32e69550c078ce6e07c0e600d8e37fc75f6e55`
- Review-ready components: `8/8`
- Can prepare internally: `true`
- External send without human: `false`
- Final submission without human: `false`
- Legal/certification action without human: `false`
- Required authority: Robert approves any strategic partner or investor introduction before outreach.
- Next human action: Use as strategic-intro material, not a solo proposal.
- Claim boundary: No consortium management, energy project financing, or installation-performance claim.
- Row SHA-256: `91eed77a9c6537a1e6d766a57cb3c87bb6717b0252b55b90da3fe49548365419`

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
- Status: `PRO_BONO_ROUTE_IDENTIFIED_HUMAN_ACTION_REQUIRED`
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
- Row SHA-256: `8c68c7932bab9a32e707a5fb16aa102c9afad9cdc437d45cc3e196c75558b4dc`

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
