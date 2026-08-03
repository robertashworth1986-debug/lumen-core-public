from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_FUNDING_REVIEWER_ZERO_FRICTION_PACK.py"


def load_module():
    spec = importlib.util.spec_from_file_location("funding_reviewer_zero_friction_pack", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_zero_friction_pack_ties_funding_claims_to_source_ledgers():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "funding_reviewer_zero_friction_pack_v1"
    assert payload["status"] == "FUNDING_REVIEWER_ZERO_FRICTION_PACK_READY_HUMAN_ACTION_REQUIRED"
    assert payload["summary"]["source_ledger_count"] == 10
    assert payload["summary"]["source_ledgers_present"] is True
    assert payload["summary"]["defensible_claim_count"] == 5
    assert payload["summary"]["defensible_claims_ready"] is True
    assert payload["summary"]["decision_route_count"] == 5
    assert payload["summary"]["sam_submit_ready_human_gate_count"] == 4
    assert payload["summary"]["data_room_control_artifact_count"] >= 52
    assert payload["summary"]["reviewer_packaging_gate_clear"] is True
    assert payload["summary"]["submission_argument_gate_clear"] is False
    assert payload["summary"]["unsafe_secret_count"] == 0
    assert payload["summary"]["unsafe_claim_count"] == 0
    assert len(payload["zero_friction_pack_sha256"]) == 64

    for claim in payload["defensible_claims"]:
        assert claim["evidence_present"] is True
        assert claim["claim_allowed_for_review"] is True
        assert claim["boundary"]
        assert len(claim["claim_sha256"]) == 64


def test_zero_friction_pack_blocks_final_actions_and_overclaims():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert summary["all_final_actions_blocked_without_human"] is True
    assert summary["external_send_allowed_without_human"] is False
    assert summary["portal_submission_allowed_without_human"] is False
    assert summary["pricing_allowed_without_human"] is False
    assert summary["legal_or_ip_action_allowed_without_human"] is False
    assert summary["live_trading_allowed"] is False
    assert summary["capital_movement_allowed_without_human"] is False
    assert summary["realized_savings_claim_allowed"] is False
    assert summary["patent_grant_claimed"] is False
    assert summary["legal_advice_claimed"] is False

    assert "Funding Reviewer Zero-Friction Pack" in rendered
    assert "All final actions blocked without human: `true`" in rendered
    assert "Live trading allowed: `false`" in rendered
    assert "zoom.us" not in lowered
    assert "meeting id" not in lowered
    assert "password" not in lowered
    assert "one tap mobile" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
