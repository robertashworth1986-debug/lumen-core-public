import importlib.util
import json
from pathlib import Path


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
    assert actual["status"] == "DEADLINE_BEARING_PORTAL_ACTION_OPEN_NO_EMAIL_SEND"
    assert actual["summary"]["lane_count"] == 17
    assert actual["summary"]["email_reply_required_count"] == 0
    assert actual["summary"]["send_now_count"] == 0
    assert actual["summary"]["duplicate_outbound_risk_count"] == 16
    assert actual["summary"]["monitor_no_send_template_count"] == 16
    assert actual["summary"]["follow_up_mode_counts"] == {
        "ACCOUNT_ACTION": 1,
        "CLOSED": 2,
        "INBOUND_ONLY": 8,
        "ONE_BOUNDED_FOLLOW_UP_AFTER_HOLD": 2,
        "PORTAL_ACTION": 3,
        "PRIVATE_RECONCILIATION": 1,
    }
    assert actual["summary"]["human_account_action_count"] == 4
    assert actual["summary"]["deadline_bearing_portal_action_count"] == 2
    assert actual["summary"]["external_send_allowed_without_human"] is False
    assert all(lane["send_now"] is False for lane in actual["lanes"])


def test_duplicate_and_out_of_office_gates_are_explicit():
    module = load_module()
    lanes = {lane["lane_id"]: lane for lane in module.build_payload()["lanes"]}

    terry = lanes["terry_vynetic_followup"]
    assert terry["outbound_followup_count"] == 2
    assert terry["outbound_spacing_seconds"] == 10
    assert "Send nothing further" in terry["next_action"]

    epri = lanes["epri_open_power_ai_mou"]
    assert epri["latest_event_type"] == "AUTOMATIC_OUT_OF_OFFICE"
    assert epri["out_of_office_through"] == "2026-07-20"
    assert epri["no_send_before"] == "2026-07-23"

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
        "DSIP_SUPPORT_REDIRECTED_TO_DLA_COMPONENT_POC"
    )
    assert missionweave["latest_event_utc"] == "2026-07-18T15:35:55Z"
    assert missionweave["component_poc_included_on_original_message"] is True
    assert missionweave["component_reply_observed"] is False
    assert missionweave["support_redirect_received"] is True
    assert missionweave["no_send_before"] == "2026-07-20T17:00:00Z"
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
    assert nashville["latest_event_type"] == "PORTAL_SUBMISSION_CONFIRMED"
    assert nashville["latest_event_utc"] == "2026-07-18T04:54:52.709214Z"
    assert nashville["state"] == "PORTAL_SUBMISSION_CONFIRMED"
    assert nashville["operational_local_deadline"] == "2026-07-17T23:59:00-05:00"
    assert nashville["operational_utc_deadline"] == "2026-07-18T04:59:00Z"
    assert nashville["deadline_timezone_explicit_in_message"] is False
    assert nashville["portal_submission_verified"] is True
    assert nashville["expected_next_steps_by"] == "2026-08-03"
    assert nashville["do_not_duplicate_send"] is True
    assert nashville["send_now"] is False
    assert "do not resubmit" in nashville["next_action"]
    assert nashville["follow_up_policy"]["mode"] == "INBOUND_ONLY"

    financial_aid = lanes["nashville_ec_financial_aid_form"]
    assert financial_aid["latest_event_type"] == (
        "FINANCIAL_AID_FORM_REQUEST_RECEIVED"
    )
    assert financial_aid["latest_event_utc"] == "2026-07-20T19:52:03Z"
    assert financial_aid["state"] == (
        "FINANCIAL_AID_FORM_REQUEST_RECEIVED_ACTION_OPEN"
    )
    assert financial_aid["deadline_date"] == "2026-07-22"
    assert financial_aid["deadline_time_status"] == "NOT_STATED_IN_MESSAGE"
    assert financial_aid["deadline_timezone_status"] == "NOT_STATED_IN_MESSAGE"
    assert financial_aid["financial_aid_form_action_required"] is True
    assert financial_aid["initial_application_resubmission_required"] is False
    assert financial_aid["final_form_submit_human_gated"] is True
    assert financial_aid["email_reply_required"] is False
    assert financial_aid["do_not_duplicate_send"] is True
    assert financial_aid["send_now"] is False
    assert financial_aid["follow_up_policy"]["mode"] == "PORTAL_ACTION"
    assert "Do not resubmit" in financial_aid["next_action"]

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

    source_evidence = module.build_payload()["source_evidence"]
    assert source_evidence["nashville_official_deadline_confirmation"]["present"] is True
    assert source_evidence["nashville_submission_receipt"]["present"] is True
    assert source_evidence["nashville_financial_aid_action"]["present"] is True
    assert source_evidence["lvlup_independent_review_confirmation"]["present"] is True
    assert source_evidence["darpa_sn_26_97_public_submission_receipt"]["present"] is True
    assert source_evidence["missionweave_dsip_action_gate"]["present"] is True
    assert source_evidence["openai_build_week_readiness"]["present"] is True
    assert source_evidence["openai_build_week_handoff_integrity_control"][
        "present"
    ] is True
    assert source_evidence["outreach_response_template_registry"]["present"] is True
    assert source_evidence["outreach_followup_policy_config"]["present"] is True
    assert len(source_evidence["nashville_official_deadline_confirmation"]["sha256"]) == 64
    assert len(source_evidence["lvlup_independent_review_confirmation"]["sha256"]) == 64

    assert all(
        lane["response_template_id"] == "NO_DUPLICATE_MONITOR"
        for lane in lanes.values()
        if lane["do_not_duplicate_send"]
    )


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
