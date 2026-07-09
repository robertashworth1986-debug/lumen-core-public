from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_INSTITUTIONAL_TRUST_GATE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("institutional_trust_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_institutional_trust_gate_unifies_readiness_and_keeps_actions_human_gated():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "institutional_trust_gate_v1"
    assert payload["status"] == "INSTITUTIONAL_TRUST_GATE_READY_HUMAN_GATED"
    assert summary["domain_count"] == 6
    assert summary["source_control_count"] >= 12
    assert summary["missing_source_control_count"] == 0
    assert summary["primary_artifact_count"] >= 10
    assert summary["missing_primary_artifact_count"] == 0
    assert summary["sam_registration_submitted"] is True
    assert summary["sam_confirmation_email_received"] is True
    assert summary["unsafe_sensitive_hits"] == 0
    assert summary["unsafe_claim_hits"] == 0
    assert summary["all_final_actions_blocked_without_human"] is True
    assert summary["external_send_allowed_without_human"] is False
    assert summary["final_submission_allowed_without_human"] is False
    assert summary["legal_or_ip_action_allowed_without_human"] is False
    assert summary["order_placement_allowed"] is False
    assert summary["capital_movement_allowed"] is False
    assert summary["live_trading_allowed"] is False
    assert summary["large_fund_ready_now"] is False
    assert len(payload["institutional_trust_gate_sha256"]) == 64


def test_domain_rows_cover_agency_investor_ip_technical_quant_and_custody():
    module = load_module()
    payload = module.build_payload()
    by_id = {row["domain_id"]: row for row in payload["domain_rows"]}

    expected = {
        "agency_and_federal_protocol",
        "investor_and_commercial_diligence",
        "ip_and_patent_defense",
        "technical_and_measured_evidence",
        "autonomous_quant_and_trading_safety",
        "custody_and_reviewer_navigation",
    }
    assert expected == set(by_id)
    assert by_id["agency_and_federal_protocol"]["status"] == "REVIEW_READY_FINAL_PORTAL_ACTIONS_HUMAN_GATED"
    assert by_id["autonomous_quant_and_trading_safety"]["status"] == "PAPER_RESEARCH_READY_LIVE_BLOCKED"
    assert "not investment advice" in by_id["autonomous_quant_and_trading_safety"]["claim_boundary"].lower()
    assert "not legal advice" in by_id["ip_and_patent_defense"]["claim_boundary"].lower()

    for row in payload["domain_rows"]:
        assert 0 <= int(row["trust_score"]) <= 100
        assert row["ready_signals"]
        assert row["remaining_gates"]
        assert row["primary_controls"]
        assert len(row["domain_row_sha256"]) == 64


def test_trust_gate_artifacts_hashes_promotion_ladder_and_safe_markdown():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Institutional Trust Gate" in rendered
    assert "Large-fund ready now: `false`" in rendered
    assert "Order placement allowed: `false`" in rendered
    assert "Capital movement allowed: `false`" in rendered
    assert "No award, acceptance, investment" in rendered
    assert any(item["level"] == "review_ready" and item["current"] is True for item in payload["promotion_ladder"])
    assert all(item["current"] is False for item in payload["promotion_ladder"] if item["level"] != "review_ready")

    for row in payload["primary_artifacts"]:
        assert row["present"] is True
        assert row["bytes"] > 0
        assert len(row["sha256"]) == 64

    for marker in [
        "zoom.us",
        "meeting id",
        "password",
        "one tap mobile",
        "private key",
        "refresh_token",
        "client_secret",
        "api_key",
        "sk-",
    ]:
        assert marker not in lowered
