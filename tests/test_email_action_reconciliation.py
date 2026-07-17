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
    assert actual["status"] == "NO_NEW_DEADLINE_CRITICAL_EMAIL_ACTION"
    assert actual["summary"]["lane_count"] == 12
    assert actual["summary"]["email_reply_required_count"] == 0
    assert actual["summary"]["send_now_count"] == 0
    assert actual["summary"]["duplicate_outbound_risk_count"] == 3
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
        "BOUNCE_RECONCILED_REPLACEMENT_OUTREACH_SENT"
    )
    assert fhwa["latest_event_utc"] == "2026-07-17T12:35:16Z"
    assert fhwa["state"] == (
        "REPLACEMENT_OUTBOUND_SENT_PARTNER_CONFIRMATION_PENDING"
    )
    assert fhwa["delivery_failure_count"] == 1
    assert fhwa["replacement_send_count"] == 1
    assert fhwa["confirmed_delivery_count"] == 0
    assert fhwa["do_not_duplicate_send"] is True
    assert fhwa["no_send_before"] == "2026-07-23"
    assert fhwa["send_now"] is False
    assert "do not reuse the rejected address" in fhwa["next_action"]

    nashville = lanes["nashville_ec_takeoff_fall_2026"]
    assert nashville["latest_event_type"] == "DEADLINE_PRESERVATION_QUERY_SENT"
    assert nashville["latest_event_utc"] == "2026-07-17T12:05:34Z"
    assert nashville["state"] == "DEADLINE_QUERY_SENT_PORTAL_SUBMISSION_STILL_REQUIRED"
    assert nashville["do_not_duplicate_send"] is True
    assert nashville["send_now"] is False
    assert "not treat the email as an application" in nashville["next_action"]


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
