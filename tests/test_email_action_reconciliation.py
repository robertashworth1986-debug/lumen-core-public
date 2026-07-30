import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_EMAIL_ACTION_RECONCILIATION.py"
JSON_OUT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "EMAIL_ACTION_RECONCILIATION_2026-07-18.json"
)
MISSIONWEAVE_GATE = (
    ROOT
    / "grant_submissions"
    / "DLA26BZ03_NV011_MissionWeave"
    / "MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json"
)
OUTREACH_DRAFT_QUARANTINE_STATE = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "OUTREACH_DRAFT_QUARANTINE_STATE_2026-07-23.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("email_action_reconciliation", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_reconciliation_is_deterministic_and_no_send():
    module = load_module()
    expected = module.build_payload()
    actual = json.loads(JSON_OUT.read_text(encoding="utf-8"))

    module.validate_payload(actual)
    assert actual == expected
    assert actual["status"] == "NO_UNANSWERED_DEADLINE_CRITICAL_EMAIL_ACTION"
    assert actual["summary"]["lane_count"] == 28
    assert actual["summary"]["email_reply_required_count"] == 0
    assert actual["summary"]["send_now_count"] == 0
    assert actual["summary"]["deadline_action_required_count"] == 0
    assert actual["summary"]["duplicate_outbound_risk_count"] == 27
    assert actual["summary"]["monitor_no_send_template_count"] == 27
    assert actual["summary"]["follow_up_mode_counts"] == {
        "ACCOUNT_ACTION": 4,
        "CLOSED": 4,
        "INBOUND_ONLY": 11,
        "ONE_BOUNDED_FOLLOW_UP_AFTER_HOLD": 2,
        "ONE_BOUNDED_INITIAL_OUTREACH_BEFORE_DEADLINE": 1,
        "PORTAL_ACTION": 5,
        "PRIVATE_RECONCILIATION": 1,
    }
    assert actual["summary"]["human_account_action_count"] == 10
    assert actual["summary"]["external_send_allowed_without_human"] is False
    assert actual["summary"]["conflicting_gmail_draft_count"] == 1
    assert actual["summary"]["conflicting_gmail_draft_lane_count"] == 1
    assert all(lane["send_now"] is False for lane in actual["lanes"])


def test_duplicate_and_out_of_office_gates_are_explicit():
    module = load_module()
    lanes = {lane["lane_id"]: lane for lane in module.build_payload()["lanes"]}

    terry = lanes["terry_vynetic_followup"]
    assert terry["outbound_followup_count"] == 2
    assert terry["outbound_spacing_seconds"] == 10
    assert terry["conflicting_gmail_draft_count"] == 1
    assert terry["draft_quarantine_status"] == "QUARANTINED_NOT_SENDABLE"
    assert terry["quarantined_draft_conflict_type"] == (
        "PROACTIVE_FOLLOWUP_LIMIT_EXHAUSTED"
    )
    assert "Do not send or revive this draft" in terry["next_action"]

    nashville = lanes["nashville_ec_takeoff_fall_2026"]
    assert nashville["conflicting_gmail_draft_count"] == 0
    assert nashville["draft_quarantine_status"] is None
    assert nashville["follow_up_policy"]["mode"] == "ACCOUNT_ACTION"
    assert nashville["account_action_required"] is True
    assert "participation agreement" in nashville["next_action"]
    assert nashville["latest_event_type"] == (
        "UPDATED_PAYMENT_AND_INFO_SESSION_ROUTES_RECEIVED"
    )
    assert nashville["latest_event_utc"] == "2026-07-29T02:49:17Z"
    assert nashville["onboarding_deadline_reconfirmed"] is True
    assert nashville["optional_info_sessions_offered"] is True
    assert nashville["optional_info_session_count"] == 3
    assert nashville["optional_info_session_timezone_explicit"] is False
    assert nashville["optional_info_session_selected"] is False
    assert nashville["info_session_attendance_required"] is False

    epri = lanes["epri_open_power_ai_mou"]
    assert epri["latest_event_type"] == (
        "CANONICAL_LOGO_PAIR_SENT_ONCE_POST_SEND_VERIFIED"
    )
    assert epri["state"] == "LOGO_PAIR_SENT_ONCE_POST_SEND_VERIFIED_DO_NOT_RESEND"
    assert epri["latest_event_utc"] == "2026-07-29T19:45:31Z"
    assert epri["all_parties_completed"] is True
    assert epri["completed_document_attached"] is True
    assert epri["completed_document_private_custody_required"] is True
    assert epri["onboarding_obligations_reviewed"] is False
    assert epri["user_reported_signing_complete"] is True
    assert epri["onboarding_request_observed"] is True
    assert epri["onboarding_response_sent"] is True
    assert epri["mrc_invite_observed"] is True
    assert epri["primary_contact_sent"] is True
    assert epri["work_group_representatives_sent"] is True
    assert epri["logo_permission_sent"] is True
    assert epri["canonical_logo_files_sent"] is True
    assert epri["logo_response_post_send_verified"] is True
    assert epri["logo_response_matching_sent_count"] == 1
    assert epri["requested_asset_template_id"] == "REQUESTED_ASSET_DELIVERY_REPLY"
    assert epri["no_send_before"] is None
    assert "Do not resend the logo pair." in epri["next_action"]

    argos = lanes["argos_emi_teaming_inquiry"]
    assert argos["state"] == "SENT_ONCE_POST_SEND_VERIFIED_WAITING_FOR_REPLY"
    assert argos["latest_event_type"] == "SENT_ONCE_POST_SEND_VERIFIED"
    assert argos["current_draft_count"] == 0
    assert argos["matching_sent_count"] == 1
    assert argos["matching_inbound_count"] == 0
    assert argos["prior_approval_binding_expired"] is True
    assert argos["deadline_action_required"] is False
    assert argos["do_not_duplicate_send"] is True
    assert argos["response_template_id"] == "NO_DUPLICATE_MONITOR"
    assert argos["attachment_count"] == 0
    assert argos["government_response_state"] == (
        "SENT_ONCE_POST_SEND_VERIFIED_NO_DUPLICATE"
    )
    assert argos["government_response_sent"] is True
    assert argos["government_sent_utc"] == "2026-07-29T01:52:18Z"
    assert argos["government_sent_before_deadline"] is True
    assert argos["government_attachment_count"] == 1
    assert argos["government_post_send_automatic_reply_observed"] is True
    assert argos["government_automatic_reply_requires_resend"] is False
    assert argos["send_now"] is False

    pathway = lanes["pathway_working_capital_inquiry"]
    assert pathway["latest_event_type"] == "OFFICIAL_FINANCING_PORTAL_ROUTE_RECEIVED"
    assert pathway["state"] == (
        "OFFICIAL_PORTAL_ROUTE_PROVIDED_FOUNDER_REVIEW_REQUIRED"
    )
    assert pathway["portal_action_required"] is True
    assert pathway["eligibility_verified"] is False
    assert pathway["application_submitted"] is False
    assert pathway["follow_up_policy"]["mode"] == "PORTAL_ACTION"
    assert pathway["send_now"] is False

    dice = lanes["darpa_dice_abstract_status"]
    assert dice["latest_event_type"] == "OFFICIAL_FULL_PROPOSAL_DISCOURAGED"
    assert dice["state"] == "FULL_PROPOSAL_DISCOURAGED_ROUTE_CLOSED"
    assert dice["full_proposal_encouraged"] is False
    assert dice["reply_requested"] is False
    assert dice["follow_up_policy"]["mode"] == "CLOSED"
    assert dice["send_now"] is False

    dhs = lanes["dhs_rfi_correction"]
    assert dhs["latest_event_type"] == (
        "CORRECTED_RESPONSE_SENT_AFTER_OFFICIAL_REQUEST"
    )
    assert dhs["state"] == (
        "CORRECTION_REQUEST_RECEIVED_CORRECTED_RESPONSE_SENT_MONITOR_ONLY"
    )
    assert dhs["correction_request_received"] is True
    assert dhs["corrected_response_sent"] is True
    assert dhs["further_reply_requested"] is False
    assert dhs["follow_up_policy"]["mode"] == "INBOUND_ONLY"
    assert dhs["send_now"] is False

    fhwa = lanes["fhwa_tsmo_qualified_partner_outreach"]
    assert fhwa["latest_event_type"] == "RESPONSE_LEAD_TEAM_SET_DECLINE_RECEIVED"
    assert fhwa["latest_event_utc"] == "2026-07-17T16:28:25Z"
    assert fhwa["state"] == "RESPONSE_LEAD_DECLINED_ADDITIONAL_PARTNER_TEAM_SET"
    assert fhwa["delivery_failure_count"] == 1
    assert fhwa["replacement_send_count"] == 1
    assert fhwa["confirmed_delivery_count"] == 1
    assert fhwa["inbound_response_count"] == 2
    assert fhwa["qualified_response_lead_referral_count"] == 1
    assert fhwa["threaded_acknowledgment_send_count"] == 1
    assert fhwa["fit_check_confirmed_count"] == 0
    assert fhwa["team_set_decline_count"] == 1
    assert fhwa["do_not_duplicate_send"] is True
    assert fhwa["no_send_before"] is None
    assert fhwa["send_now"] is False
    assert "Close this route" in fhwa["next_action"]

    georgia = lanes["georgia_patents_pro_bono_intake"]
    assert georgia["latest_event_type"] == "SERVICE_SCOPE_DECLINE_RECEIVED"
    assert georgia["state"] == "SERVICE_NOT_OFFERED_FOR_ALREADY_FILED_APPLICATION"
    assert georgia["no_send_before"] is None

    uspto = lanes["uspto_document_services_copy_route"]
    assert uspto["latest_event_type"] == "OFFICIAL_COPY_PORTAL_ROUTE_PROVIDED"
    assert uspto["state"] == "OFFICIAL_COPY_PORTAL_ROUTE_PROVIDED_SCOPE_UNCONFIRMED"
    assert uspto["portal_action_required"] is True
    assert uspto["missing_fact_count"] == 5
    assert uspto["do_not_duplicate_send"] is True
    assert uspto["send_now"] is False
    assert uspto["follow_up_policy"]["mode"] == "PORTAL_ACTION"

    nccu = lanes["nccu_ip_clinic_intake"]
    assert nccu["latest_event_type"] == "SERVICE_AVAILABILITY_DECLINE_RECEIVED"
    assert nccu["state"] == (
        "SERVICE_UNAVAILABLE_SUMMER_AND_UPCOMING_DEADLINE_ROUTE_CLOSED"
    )
    assert nccu["do_not_duplicate_send"] is True
    assert nccu["send_now"] is False
    assert nccu["follow_up_policy"]["mode"] == "CLOSED"

    darpa = lanes["darpa_sn_26_97_low_resource_computing_rfi"]
    assert darpa["state"] == "FORMAL_RFI_PACKAGE_SENT_AGENCY_RECEIPT_PENDING"
    assert darpa["attachment_count"] == 2
    assert darpa["deadline_time_compliance_claimed"] is False

    missionweave = lanes["missionweave_dsip_proposal"]
    missionweave_gate = json.loads(MISSIONWEAVE_GATE.read_text(encoding="utf-8"))
    assert missionweave["deadline_utc"] == "2026-07-22T16:00:00Z"
    assert missionweave["open_gate_count"] == missionweave_gate["gate_summary"][
        "open_gate_count"
    ]
    assert missionweave["latest_event_type"] == (
        "OFFICIAL_DSIP_NON_SUBMISSION_CONFIRMED"
    )
    assert missionweave["latest_event_utc"] == "2026-07-28T17:36:13Z"
    assert missionweave["state"] == (
        "OFFICIAL_DLA_CONFIRMED_PROPOSAL_IN_PROGRESS_NOT_SUBMITTED"
    )
    assert missionweave["component_poc_included_on_original_message"] is True
    assert missionweave["component_reply_observed"] is True
    assert missionweave["support_redirect_received"] is True
    assert missionweave["official_status_route_provided"] is True
    assert missionweave["portal_status_observed"] is True
    assert missionweave["portal_status"] == "IN_PROGRESS"
    assert missionweave["formally_submitted"] is False
    assert missionweave["submission_receipt_observed"] is False
    assert missionweave["deadline_elapsed"] is True
    assert missionweave["portal_action_required"] is False
    assert missionweave["no_send_before"] is None
    assert missionweave["follow_up_policy"]["eligible_template_id"] == (
        "COMPONENT_INSTRUCTION_ESCALATION"
    )
    assert missionweave["follow_up_policy"]["max_proactive_sends"] == 1

    build_week = lanes["openai_build_week_prooflock"]
    assert build_week["deadline_utc"] == "2026-07-22T00:00:00Z"
    assert build_week["state"] == "PROJECT_CORE_VERIFIED_EXTERNAL_SUBMISSION_FIELDS_OPEN"

    build_week_handoff = lanes["openai_build_week_internal_handoff"]
    assert build_week_handoff["state"] == (
        "REFERENCED_HANDOFF_UNAVAILABLE_EXECUTION_SCOPE_BOUNDED"
    )
    assert build_week_handoff["latest_event_type"] == (
        "SELF_SENT_HANDOFF_REFERENCE_WITHOUT_ATTACHMENT"
    )
    assert build_week_handoff["embedded_rule_count"] == 10
    assert build_week_handoff["full_handoff_body_available"] is False
    assert build_week_handoff["do_not_duplicate_send"] is True
    assert "do not invent" in build_week_handoff["next_action"]
    assert build_week_handoff["follow_up_policy"]["mode"] == (
        "PRIVATE_RECONCILIATION"
    )

    nashville = lanes["nashville_ec_takeoff_fall_2026"]
    assert nashville["latest_event_type"] == (
        "UPDATED_PAYMENT_AND_INFO_SESSION_ROUTES_RECEIVED"
    )
    assert nashville["latest_event_utc"] == "2026-07-29T02:49:17Z"
    assert nashville["state"] == (
        "COHORT_SELECTED_ONBOARDING_AND_PARTICIPATION_AGREEMENT_DUE"
    )
    assert nashville["prior_portal_submission_verified"] is True
    assert nashville["cohort_selected"] is True
    assert nashville["financial_assistance_amount_usd"] == 375
    assert nashville["full_program_investment_usd"] == 500
    assert nashville["discount_code_omitted"] is True
    assert nashville["thank_you_and_acceptance_sent"] is True
    assert nashville["onboarding_form_completed"] is False
    assert nashville["participation_agreement_accepted"] is False
    assert nashville["deposit_submitted"] is False
    assert (
        nashville["onboarding_form_and_participation_agreement_date"]
        == "2026-07-31"
    )
    assert nashville["deposit_date"] == "2026-08-14"
    assert nashville["deadline_time_and_timezone_explicit"] is False
    assert nashville["do_not_duplicate_send"] is True
    assert nashville["send_now"] is False
    assert "Do not accept the agreement" in nashville["next_action"]
    assert "make a payment" in nashville["next_action"]
    assert "send another acceptance email automatically" in nashville["next_action"]
    assert nashville["follow_up_policy"]["mode"] == "ACCOUNT_ACTION"

    tsa = lanes["tsa_industry_portal_capability"]
    assert tsa["state"] == "OFFICIAL_INDUSTRY_PORTAL_ROUTE_PROVIDED"
    assert tsa["official_industry_portal_route_provided"] is True
    assert tsa["acknowledgment_sent"] is True
    assert tsa["portal_submission_completed"] is False
    assert tsa["portal_action_required"] is True
    assert tsa["follow_up_policy"]["mode"] == "PORTAL_ACTION"

    amps = lanes["dla_amps_application_access"]
    assert amps["state"] == "ACCOUNT_CREATED_EXACT_ROLE_NOT_YET_VERIFIED"
    assert amps["account_created"] is True
    assert amps["account_identifier_omitted"] is True
    assert amps["exact_application_verified"] is False
    assert amps["exact_role_verified"] is False
    assert amps["role_request_submitted"] is False
    assert amps["follow_up_policy"]["mode"] == "ACCOUNT_ACTION"

    login = lanes["login_gov_new_device_signin"]
    assert login["state"] == "NEW_DEVICE_SIGNIN_REQUIRES_USER_RECOGNITION"
    assert login["new_device_signin_reported"] is True
    assert login["recognized_by_user"] is False
    assert login["security_link_and_token_omitted"] is True
    assert login["follow_up_policy"]["mode"] == "ACCOUNT_ACTION"

    nasa = lanes["nasa_data_center_rfi"]
    assert nasa["state"] == "FIRM_FIXED_PRICE_QUOTATION_SENT_RESPONSE_PENDING"
    assert nasa["quotation_sent"] is True
    assert nasa["compliance_verified"] is False
    assert nasa["agency_reply_received"] is False
    assert nasa["do_not_duplicate_send"] is True

    lanl = lanes["lanl_vision_licensing_followup"]
    assert lanl["follow_up_policy"] == {
        "lane_id": "lanl_vision_licensing_followup",
        "mode": "ONE_BOUNDED_FOLLOW_UP_AFTER_HOLD",
        "eligible_template_id": "BOUNDED_REVIEW_FOLLOWUP",
        "not_before_utc": "2026-07-23T14:00:00Z",
        "max_proactive_sends": 1,
        "rationale": (
            "One bounded review follow-up may be drafted after the hold only "
            "if a fresh mailbox check confirms no reply."
        ),
    }

    lvlup = lanes["lvlup_optional_paid_event"]
    assert lvlup["latest_event_type"] == (
        "INDEPENDENT_REVIEW_CONTINUATION_CONFIRMED"
    )
    assert lvlup["latest_event_utc"] == "2026-07-17T15:58:03Z"
    assert lvlup["state"] == (
        "WRITTEN_NO_SPONSOR_SPEND_INDEPENDENT_REVIEW_CONFIRMED"
    )
    assert lvlup["written_independent_review_confirmation"] is True
    assert lvlup["paid_sponsor_purchase_required_for_separate_review"] is False
    assert lvlup["do_not_duplicate_send"] is True
    assert lvlup["send_now"] is False

    lvlup_intro = lanes["lvlup_warm_investor_intro"]
    assert lvlup_intro["latest_event_type"] == (
        "BOUNDED_WARM_INTRO_FOLLOWUP_SENT"
    )
    assert lvlup_intro["state"] == "OUTBOUND_FOLLOWUP_SENT_MONITOR_ONLY"
    assert lvlup_intro["do_not_duplicate_send"] is True
    assert lvlup_intro["follow_up_policy"]["mode"] == "INBOUND_ONLY"

    lvlup_status = lanes["lvlup_application_review_status"]
    assert lvlup_status["latest_event_type"] == (
        "OFFICIAL_APPLICATION_REVIEW_STATUS_RECEIVED"
    )
    assert lvlup_status["latest_event_utc"] == "2026-07-23T20:48:10Z"
    assert lvlup_status["state"] == (
        "APPLICATION_ACTIVE_COMMITTEE_REVIEW_NO_ADDITIONAL_MATERIALS"
    )
    assert lvlup_status["email_reply_required"] is False
    assert lvlup_status["send_now"] is False
    assert lvlup_status["do_not_duplicate_send"] is True
    assert lvlup_status["follow_up_policy"]["mode"] == "INBOUND_ONLY"

    third_sphere = lanes["third_sphere_seedstrap_direct_review"]
    assert third_sphere["latest_event_type"] == (
        "INITIAL_PUBLIC_SAFE_REVIEW_REQUEST_SENT"
    )
    assert third_sphere["state"] == (
        "INITIAL_PUBLIC_SAFE_REVIEW_REQUEST_SENT_MONITOR_ONLY"
    )
    assert third_sphere["do_not_duplicate_send"] is True
    assert third_sphere["follow_up_policy"]["mode"] == "INBOUND_ONLY"

    source_evidence = module.build_payload()["source_evidence"]
    assert source_evidence["nashville_official_deadline_confirmation"]["present"] is True
    assert source_evidence["nashville_submission_receipt"]["present"] is True
    assert source_evidence["epri_open_power_ai_mou_signing_state"][
        "present"
    ] is True
    assert source_evidence["epri_opai_logo_response_send_status"]["present"] is True
    assert source_evidence["lvlup_independent_review_confirmation"]["present"] is True
    assert source_evidence["lvlup_outreach_send_state"]["present"] is True
    assert source_evidence["lvlup_application_review_status_response_state"][
        "present"
    ] is True
    assert source_evidence["third_sphere_seedstrap_outreach_send_state"][
        "present"
    ] is True
    assert source_evidence["darpa_sn_26_97_public_submission_receipt"]["present"] is True
    assert source_evidence["missionweave_dsip_action_gate"]["present"] is True
    assert source_evidence["dla_dsip_official_non_submission_receipt"][
        "present"
    ] is True
    assert source_evidence["openai_build_week_readiness"]["present"] is True
    assert source_evidence["openai_build_week_handoff_integrity_control"][
        "present"
    ] is True
    assert source_evidence["outreach_response_template_registry"]["present"] is True
    assert source_evidence["outreach_followup_policy_config"]["present"] is True
    assert source_evidence["nccu_patent_clinic_route_closure"]["present"] is True
    assert source_evidence["uspto_document_services_routing_response"][
        "present"
    ] is True
    assert source_evidence["outreach_draft_quarantine_state"]["present"] is True
    assert source_evidence["official_inbound_status_event_register"][
        "present"
    ] is True
    assert len(source_evidence["nashville_official_deadline_confirmation"]["sha256"]) == 64
    assert len(source_evidence["lvlup_independent_review_confirmation"]["sha256"]) == 64

    assert all(
        lane["response_template_id"] == "NO_DUPLICATE_MONITOR"
        for lane in lanes.values()
        if lane["do_not_duplicate_send"]
    )


def test_third_sphere_send_receipt_is_hash_bound_and_tamper_evident():
    module = load_module()
    state = module.read_json(module.THIRD_SPHERE_OUTREACH_SEND_STATE)
    receipt = module.validate_third_sphere_outreach_send_state(state)

    hash_fields = (
        "recipient_route_sha256",
        "subject_sha256",
        "body_sha256",
        "gmail_message_id_sha256",
        "gmail_thread_id_sha256",
        "sent_message_receipt_sha256",
    )
    assert all(module.is_sha256(receipt[field]) for field in hash_fields)
    assert receipt["attachment_count"] == 0
    assert receipt["cc_count"] == 0
    assert receipt["bcc_count"] == 0
    serialized = json.dumps(state, sort_keys=True).lower()
    assert '"recipient_email"' not in serialized
    assert '"message_id"' not in serialized
    assert '"thread_id"' not in serialized
    assert '"subject"' not in serialized
    assert '"body"' not in serialized

    for field in hash_fields:
        tampered = copy.deepcopy(state)
        tampered["receipt"][field] = "F" * 64
        with pytest.raises(ValueError, match="missing or stale"):
            module.validate_third_sphere_outreach_send_state(tampered)

    tampered_count = copy.deepcopy(state)
    tampered_count["receipt"]["attachment_count"] = 1
    with pytest.raises(ValueError, match="missing or stale"):
        module.validate_third_sphere_outreach_send_state(tampered_count)


def test_lvlup_application_status_response_is_privacy_safe_and_no_send():
    module = load_module()
    state = module.read_json(
        module.LVLUP_APPLICATION_REVIEW_STATUS_RESPONSE_STATE
    )
    action = module.validate_lvlup_application_review_status_response(state)

    assert state["source"]["received_utc"] == "2026-07-23T20:48:10Z"
    assert state["source"]["sender"] == "Ana Rivera / LvlUp Ventures"
    assert state["evidence"]["application_active"] is True
    assert state["evidence"]["application_remains_under_review"] is True
    assert state["evidence"]["additional_materials_requested"] is False
    assert action["deadline"] is None
    assert action["email_reply_required"] is False
    assert action["send_now"] is False
    assert action["selected_template_id"] == "NO_DUPLICATE_MONITOR"
    serialized = json.dumps(state, sort_keys=True).lower()
    assert "@lvlup." not in serialized
    assert '"message_id"' not in serialized
    assert '"thread_id"' not in serialized
    assert '"body"' not in serialized

    tampered = copy.deepcopy(state)
    tampered["evidence"]["additional_materials_requested"] = True
    with pytest.raises(ValueError, match="missing or stale"):
        module.validate_lvlup_application_review_status_response(tampered)


def test_conflicting_gmail_drafts_are_hash_only_and_fail_closed():
    module = load_module()
    state = module.read_json(OUTREACH_DRAFT_QUARANTINE_STATE)
    drafts = module.validate_outreach_draft_quarantine_state(state)

    assert len(drafts) == 1
    assert {row["lane_id"] for row in drafts} == {"terry_vynetic_followup"}
    assert all(row["send_now"] is False for row in drafts)
    assert all(row["gmail_draft_deleted"] is False for row in drafts)
    assert all(
        module.is_sha256(row[field])
        for row in drafts
        for field in (
            "gmail_draft_id_sha256",
            "gmail_thread_id_sha256",
            "subject_sha256",
        )
    )
    serialized = json.dumps(state, sort_keys=True).lower()
    assert "@gmail." not in serialized
    assert "@vynetic." not in serialized
    assert "@ec.co" not in serialized
    assert "meeting id" not in serialized
    assert "passcode" not in serialized
    assert "zoom.us" not in serialized
    assert '"subject"' not in serialized
    assert '"body"' not in serialized

    tampered = copy.deepcopy(state)
    tampered["drafts"][0]["send_now"] = True
    with pytest.raises(ValueError, match="missing or unsafe"):
        module.validate_outreach_draft_quarantine_state(tampered)


def test_official_inbound_event_register_is_sanitized_and_tamper_evident():
    module = load_module()
    state = module.read_json(module.OFFICIAL_INBOUND_STATUS_EVENT_REGISTER)
    by_lane = module.validate_official_inbound_status_event_register(state)

    assert set(by_lane) == {
        "epri_open_power_ai_mou",
        "pathway_working_capital_inquiry",
        "darpa_dice_abstract_status",
        "dhs_rfi_correction",
        "nashville_ec_takeoff_fall_2026",
        "tsa_industry_portal_capability",
        "dla_amps_application_access",
        "login_gov_new_device_signin",
        "dla_dsip_topic_status",
        "epri_open_power_ai_mou_completed",
        "nashville_ec_accelerator_info_sessions",
        "argos_government_automatic_reply",
    }
    assert all(event["action"]["send_now"] is False for event in by_lane.values())
    assert all(
        event["action"]["email_reply_required"] is False
        for event in by_lane.values()
    )
    assert all(
        module.is_sha256(event["source"]["subject_sha256"])
        for event in by_lane.values()
    )
    nashville = by_lane["nashville_ec_takeoff_fall_2026"]
    assert nashville["evidence"]["discount_code_omitted"] is True
    assert nashville["action"]["deadline"] == {
        "onboarding_form_and_participation_agreement_date": "2026-07-31",
        "deposit_date": "2026-08-14",
        "time_and_timezone_explicit": False,
    }
    assert by_lane["tsa_industry_portal_capability"]["evidence"][
        "portal_submission_completed"
    ] is False
    assert by_lane["dla_amps_application_access"]["evidence"][
        "account_identifier_omitted"
    ] is True
    assert by_lane["login_gov_new_device_signin"]["evidence"][
        "email_security_link_and_token_omitted"
    ] is True
    dsip = by_lane["dla_dsip_topic_status"]
    assert dsip["status"] == (
        "OFFICIAL_DLA_CONFIRMED_PROPOSAL_IN_PROGRESS_NOT_SUBMITTED"
    )
    assert dsip["evidence"]["official_portal_status_observed"] is True
    assert dsip["evidence"]["portal_status"] == "IN_PROGRESS"
    assert dsip["evidence"]["formally_submitted"] is False
    assert dsip["evidence"]["submission_receipt_observed"] is False
    assert dsip["evidence"]["founder_portal_recheck_required"] is False
    assert dsip["action"]["duplicate_send_decision"] == (
        "CLOSE_NOT_SUBMITTED_DO_NOT_RESEND"
    )
    assert by_lane["epri_open_power_ai_mou_completed"]["evidence"][
        "all_parties_completed"
    ] is True
    info_sessions = by_lane["nashville_ec_accelerator_info_sessions"]
    assert info_sessions["status"] == (
        "UPDATED_PAYMENT_ROUTE_AND_OPTIONAL_INFO_SESSIONS_AVAILABLE"
    )
    assert info_sessions["evidence"]["prior_payment_link_invalidated"] is True
    assert info_sessions["evidence"]["updated_takeoff_payment_route_provided"] is True
    assert info_sessions["evidence"]["payment_link_omitted"] is True
    assert info_sessions["evidence"]["deposit_deadline_date"] == "2026-08-14"
    assert info_sessions["evidence"]["session_count"] == 3
    assert info_sessions["evidence"]["session_timezone_explicit"] is False
    assert info_sessions["evidence"]["session_links_omitted"] is True
    assert info_sessions["evidence"]["attendance_required"] is False
    assert info_sessions["action"]["deadline"] == {
        "onboarding_form_date": "2026-07-31",
        "time_and_timezone_explicit": False,
    }
    argos_auto_reply = by_lane["argos_government_automatic_reply"]
    assert argos_auto_reply["evidence"]["delivery_evidence_only"] is True
    assert argos_auto_reply["evidence"]["substantive_acknowledgment"] is False
    assert argos_auto_reply["evidence"]["acceptance_or_award"] is False
    assert argos_auto_reply["action"]["duplicate_send_decision"] == (
        "DO_NOT_REPLY_TO_THE_AUTOMATIC_MESSAGE_OR_RESEND_THE_ARGOS_PACKET"
    )
    serialized = json.dumps(state, sort_keys=True).lower()
    for forbidden in (
        "@gmail.",
        "@epri.",
        "message_id",
        "thread_id",
        "meeting id",
        "passcode",
        "zoom.us",
        "assessment content",
        "project content",
    ):
        assert forbidden not in serialized

    tampered = copy.deepcopy(state)
    tampered["events"][0]["source"]["subject_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="missing or stale"):
        module.validate_official_inbound_status_event_register(tampered)


def test_dla_dsip_non_submission_receipt_is_authoritative_and_private_safe():
    module = load_module()
    state = module.read_json(module.DLA_DSIP_NON_SUBMISSION_RECEIPT)
    receipt = module.validate_dla_dsip_non_submission_receipt(state)

    assert receipt["status"] == (
        "OFFICIAL_DLA_CONFIRMED_PROPOSAL_IN_PROGRESS_NOT_SUBMITTED"
    )
    assert receipt["evidence"]["portal_status"] == "IN_PROGRESS"
    assert receipt["evidence"]["formally_submitted"] is False
    assert receipt["evidence"]["submission_receipt_observed"] is False
    assert receipt["action"]["portal_action_required"] is False
    assert receipt["action"]["send_now"] is False
    assert receipt["action"]["do_not_duplicate_send"] is True
    serialized = json.dumps(receipt, sort_keys=True).lower()
    for forbidden in (
        "@gmail.",
        "@dla.",
        "message_id",
        "thread_id",
        "proposal l26",
        "mobile:",
    ):
        assert forbidden not in serialized

    tampered = copy.deepcopy(receipt)
    tampered["evidence"]["formally_submitted"] = True
    with pytest.raises(ValueError, match="missing or unsafe"):
        module.validate_dla_dsip_non_submission_receipt(tampered)


def test_public_reconciliation_excludes_private_mailbox_data():
    module = load_module()
    rendered = json.dumps(module.build_payload(), sort_keys=True).lower()

    for forbidden in (
        "@gmail.com",
        "message_id",
        "thread_id",
        "meeting id",
        "passcode",
        "zoom.us",
        "client_secret",
        "refresh_token",
        "api_key",
    ):
        assert forbidden not in rendered

    assert "personal finance and payment notices" in rendered
    assert "account-access and recovery notices" in rendered
