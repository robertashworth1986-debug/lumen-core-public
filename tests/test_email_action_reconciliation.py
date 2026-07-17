import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_EMAIL_ACTION_RECONCILIATION.py"
JSON_OUT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "EMAIL_ACTION_RECONCILIATION_2026-07-17.json"
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
    assert actual["summary"]["lane_count"] == 12
    assert actual["summary"]["email_reply_required_count"] == 0
    assert actual["summary"]["send_now_count"] == 0
    assert actual["summary"]["duplicate_outbound_risk_count"] == 11
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
    assert fhwa["latest_event_type"] == (
        "QUALIFIED_RESPONSE_LEAD_REFERRAL_ACKNOWLEDGED"
    )
    assert fhwa["latest_event_utc"] == "2026-07-17T14:41:54Z"
    assert fhwa["state"] == (
        "QUALIFIED_RESPONSE_LEAD_REFERRAL_ACKNOWLEDGED_FIT_CHECK_PENDING"
    )
    assert fhwa["delivery_failure_count"] == 1
    assert fhwa["replacement_send_count"] == 1
    assert fhwa["confirmed_delivery_count"] == 1
    assert fhwa["inbound_response_count"] == 1
    assert fhwa["qualified_response_lead_referral_count"] == 1
    assert fhwa["threaded_acknowledgment_send_count"] == 1
    assert fhwa["fit_check_confirmed_count"] == 0
    assert fhwa["do_not_duplicate_send"] is True
    assert fhwa["no_send_before"] == "2026-07-21"
    assert fhwa["send_now"] is False
    assert "Monitor the referred response lead" in fhwa["next_action"]

    nashville = lanes["nashville_ec_takeoff_fall_2026"]
    assert nashville["latest_event_type"] == "OFFICIAL_DEADLINE_CONFIRMATION_RECEIVED"
    assert nashville["latest_event_utc"] == "2026-07-17T16:11:48Z"
    assert nashville["state"] == (
        "OFFICIAL_SUPPORT_CONFIRMED_CLOSE_TIME_APPLICATION_NOT_SUBMITTED"
    )
    assert nashville["operational_local_deadline"] == "2026-07-17T23:59:00-05:00"
    assert nashville["operational_utc_deadline"] == "2026-07-18T04:59:00Z"
    assert nashville["deadline_timezone_explicit_in_message"] is False
    assert nashville["do_not_duplicate_send"] is True
    assert nashville["send_now"] is False
    assert "not treat the support reply as an application" in nashville["next_action"]

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
    assert source_evidence["lvlup_independent_review_confirmation"]["present"] is True
    assert len(source_evidence["nashville_official_deadline_confirmation"]["sha256"]) == 64
    assert len(source_evidence["lvlup_independent_review_confirmation"]["sha256"]) == 64


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
