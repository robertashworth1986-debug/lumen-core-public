from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_FHWA_TSMO_PARTNER_OUTREACH_CONTROL.py"
RESPONSE_CONTROL = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "FHWA_TSMO_PARTNER_RESPONSE_CONTROL_2026-07-17.md"
)
MIRROR_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "FHWA_TSMO_ROUTE_CORRECTION_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
)
MIRROR_RECEIPT_COPY = Path(
    "E:/LumaProofVault/SUBMISSIONS/FHWA_TSMO_ROUTE_CORRECTION_20260717/"
    "grant_submissions/funding_sprint_20260709/"
    "FHWA_TSMO_ROUTE_CORRECTION_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("fhwa_tsmo_partner_outreach", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_sent_outreach_is_qualified_bounded_and_not_a_partner_claim():
    module = load_module()
    payload = module.build_payload()
    control = payload["response_control"]

    assert payload["schema"] == "lumencore.fhwa_tsmo_partner_outreach_control.v2"
    assert payload["status"] == (
        "BOUNCE_RECONCILED_REPLACEMENT_SENT_RESPONSE_PENDING"
    )
    assert payload["target"]["active_public_professional_route_verified"] is True
    assert len(payload["target"]["qualification_basis"]) == 3
    gates = payload["replacement_pre_send_gates"]
    assert gates["original_delivery_failure_verified"] is True
    assert gates["prior_active_recipient_mailbox_matches"] == 0
    assert gates["attachment_count"] == 0
    assert gates["patent_sensitive_material_included"] is False
    assert gates["partner_relationship_claimed"] is False
    assert control["state"] == "REPLACEMENT_ROUTE_CONTACTED_NOT_CONFIRMED"
    assert control["qualified_partner_evidence_present"] is False
    assert control["send_now"] is False
    assert control["do_not_duplicate_send"] is True
    assert control["no_follow_up_before"] == "2026-07-23"


def test_public_receipt_uses_hashes_and_contains_no_recipient_mailbox():
    module = load_module()
    payload = module.build_payload()
    rendered = json.dumps(payload)

    assert len(payload["outbound_history"]) == 2
    for attempt in payload["outbound_history"]:
        assert re.fullmatch(r"[0-9a-f]{64}", attempt["message_id_sha256"])
        assert re.fullmatch(r"[0-9a-f]{64}", attempt["body_sha256"])
    assert "@camsys.com" not in rendered.lower()
    assert "client_secret" not in rendered.lower()
    assert "api_key" not in rendered.lower()
    assert "meeting id" not in rendered.lower()
    assert "passcode" not in rendered.lower()


def test_claim_boundary_does_not_convert_send_into_validation():
    module = load_module()
    payload = module.build_payload()
    boundary = payload["claim_boundary"].lower()

    assert "do not establish delivery or receipt" in boundary
    assert "teaming relationship" in boundary
    assert "independent validation" in boundary
    assert "award" in boundary


def test_bounce_and_replacement_are_reconciled_without_false_delivery_claim():
    module = load_module()
    payload = module.build_payload()
    attempts = payload["outbound_history"]
    delivery = payload["delivery_reconciliation"]

    assert attempts[0]["status"] == "DELIVERY_REJECTED_550_INVALID_RECIPIENT"
    assert attempts[0]["smtp_status_code"] == 550
    assert attempts[0]["delivery_confirmed"] is False
    assert attempts[1]["status"] == (
        "SENT_NO_IMMEDIATE_REJECTION_RESPONSE_PENDING"
    )
    assert attempts[1]["immediate_delivery_rejection_observed"] is False
    assert attempts[1]["delivery_confirmed"] is False
    assert delivery == {
        "attempt_count": 2,
        "delivery_failure_count": 1,
        "replacement_send_count": 1,
        "confirmed_delivery_count": 0,
        "response_count": 0,
        "active_attempt_index": 2,
        "stale_route_reuse_allowed": False,
    }
    assert "do not reuse the rejected address" in payload["response_control"][
        "next_action"
    ]


def test_response_templates_cover_six_bounded_inbound_branches():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_response_templates(payload)
    lowered = rendered.lower()

    assert payload["response_templates"]["branch_count"] == 6
    assert payload["response_templates"]["autonomous_send_allowed"] is False
    assert "## Interested Or Correct Owner" in rendered
    assert "## Referral Provided" in rendered
    assert "## More Information Requested" in rendered
    assert "## Not Pursuing Or Decline" in rendered
    assert "## NDA Or Confidential Information Requested" in rendered
    assert "## One Follow-Up If No Response" in rendered
    assert "Do not send before: `2026-07-23`" in rendered
    assert "do not reuse the rejected address" in lowered
    assert "not representing that a teaming relationship exists" in lowered
    assert "do not claim delivery" in lowered
    assert "@camsys.com" not in lowered

    module.write_outputs(payload)
    assert RESPONSE_CONTROL.read_text(encoding="utf-8") == rendered


def test_route_correction_snapshot_remains_immutable_on_e_drive() -> None:
    receipt = json.loads(MIRROR_RECEIPT.read_text(encoding="utf-8"))

    assert receipt["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 29
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["browser_navigation_performed"] is False
    assert receipt["private_founder_values_mirrored"] is False

    for artifact in receipt["artifacts"]:
        relative = Path(artifact["source"])
        destination = Path(artifact["destination"])
        assert relative.is_absolute() is False
        assert ".." not in relative.parts
        assert destination.is_file(), artifact["destination"]
        assert destination.stat().st_size == artifact["bytes"]
        destination_hash = hashlib.sha256(destination.read_bytes()).hexdigest().upper()
        assert destination_hash == artifact["sha256"]
        assert artifact["copy_sha256_matched"] is True

    assert MIRROR_RECEIPT_COPY.is_file()
    assert hashlib.sha256(MIRROR_RECEIPT.read_bytes()).hexdigest() == hashlib.sha256(
        MIRROR_RECEIPT_COPY.read_bytes()
    ).hexdigest()
    assert "does not prove" in receipt["claim_boundary"]
