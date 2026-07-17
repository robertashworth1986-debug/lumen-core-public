from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_FHWA_TSMO_PARTNER_OUTREACH_CONTROL.py"


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

    assert payload["status"] == "OUTBOUND_SENT_PARTNER_CONFIRMATION_PENDING"
    assert payload["target"]["public_professional_route_verified"] is True
    assert len(payload["target"]["qualification_basis"]) == 3
    assert payload["pre_send_gates"]["prior_recipient_or_organization_mailbox_matches"] == 0
    assert payload["pre_send_gates"]["attachment_count"] == 0
    assert payload["pre_send_gates"]["patent_sensitive_material_included"] is False
    assert payload["pre_send_gates"]["partner_relationship_claimed"] is False
    assert control["state"] == "CONTACTED_NOT_CONFIRMED"
    assert control["qualified_partner_evidence_present"] is False
    assert control["send_now"] is False
    assert control["do_not_duplicate_send"] is True
    assert control["no_follow_up_before"] == "2026-07-23"


def test_public_receipt_uses_hashes_and_contains_no_recipient_mailbox():
    module = load_module()
    payload = module.build_payload()
    rendered = json.dumps(payload)

    assert re.fullmatch(r"[0-9a-f]{64}", payload["outbound"]["message_id_sha256"])
    assert re.fullmatch(r"[0-9a-f]{64}", payload["outbound"]["body_sha256"])
    assert "@camsys.com" not in rendered.lower()
    assert "client_secret" not in rendered.lower()
    assert "api_key" not in rendered.lower()
    assert "meeting id" not in rendered.lower()
    assert "passcode" not in rendered.lower()


def test_claim_boundary_does_not_convert_send_into_validation():
    module = load_module()
    payload = module.build_payload()
    boundary = payload["claim_boundary"].lower()

    assert "do not establish receipt" in boundary
    assert "teaming relationship" in boundary
    assert "independent validation" in boundary
    assert "award" in boundary
