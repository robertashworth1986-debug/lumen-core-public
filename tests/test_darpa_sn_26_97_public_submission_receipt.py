import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_DARPA_SN_26_97_PUBLIC_SUBMISSION_RECEIPT.py"
OUT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "DARPA_SN_26_97_PUBLIC_SUBMISSION_RECEIPT_2026-07-17.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("darpa_sn_26_97_receipt", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_receipt_is_deterministic_bounded_and_matches_output():
    module = load_module()
    expected = module.build_payload()
    actual = json.loads(OUT.read_text(encoding="utf-8"))

    module.validate_payload(actual)
    assert actual == expected
    assert actual["status"] == (
        "FORMAL_RFI_PACKAGE_SENT_AGENCY_RESPONSE_RECEIVED_MONITOR_ONLY"
    )
    assert actual["thread_reconciliation"]["formal_package_sent_utc"] == (
        "2026-07-17T19:27:49Z"
    )
    thread = actual["thread_reconciliation"]
    assert thread["agency_thread_response_after_formal_package_observed"] is True
    assert thread["agency_thread_response_received_utc"] == "2026-07-21T15:25:21Z"
    assert thread["explicit_attachment_receipt_confirmed"] is False
    assert thread["specific_action_request_observed"] is False
    assert actual["opportunity"]["timely_submission_claimed"] is False
    assert actual["send_control"]["do_not_duplicate_send"] is True
    assert actual["send_control"]["send_now"] is False
    assert len(actual["attachments"]) == 2
    assert all(re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) for row in actual["attachments"])


def test_public_receipt_excludes_private_contact_and_claim_inflation():
    module = load_module()
    rendered = json.dumps(module.build_payload(), sort_keys=True).lower()

    for forbidden in (
        "recipient_email",
        "sender_email",
        "sender_phone",
        "sender_address",
        "meeting id",
        "passcode",
        "api_key",
        "private key",
    ):
        assert forbidden not in rendered

    assert "does not prove delivery acceptance" in rendered
    assert "independent_validation_claimed\": false" in rendered
