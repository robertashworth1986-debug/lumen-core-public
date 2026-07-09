from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_REVIEWER_INVESTOR_FAST_LANE_ROUTER.py"


def load_module():
    spec = importlib.util.spec_from_file_location("reviewer_investor_fast_lane_router", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_fast_lane_router_builds_human_gated_routes():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "reviewer_investor_fast_lane_router_v1"
    assert payload["status"] == "FAST_LANE_ROUTER_READY_HUMAN_SHARE_REQUIRED"
    assert summary["route_count"] == 8
    assert summary["missing_artifact_count"] == 0
    assert summary["decision_lane_count"] == 19
    assert summary["traction_lane_count"] == 19
    assert summary["qa_count"] >= 13
    assert summary["ip_invention_family_count"] == 6
    assert summary["reviewer_gate_clear"] is True
    assert summary["key_firewall_ready"] is True
    assert summary["ip_boundary_ready"] is True
    assert summary["agency_protocol_ready"] is True
    assert summary["all_final_actions_blocked_without_human"] is True
    assert summary["external_send_allowed_without_human"] is False
    assert summary["final_submission_allowed_without_human"] is False
    assert summary["legal_filing_allowed_without_human"] is False
    assert summary["social_posting_allowed_without_human"] is False
    assert summary["ad_spend_allowed_without_human"] is False
    assert summary["live_trading_allowed"] is False
    assert summary["capital_movement_allowed"] is False
    assert summary["unsafe_secret_count"] == 0
    assert summary["unsafe_claim_count"] == 0
    assert len(payload["fast_lane_router_sha256"]) == 64


def test_fast_lane_routes_cover_core_diligence_surfaces():
    module = load_module()
    payload = module.build_payload()
    routes = {route["route_id"]: route for route in payload["routes"]}

    for route_id in [
        "five_minute_reviewer_start",
        "agency_submission_protocol",
        "ip_patent_claim_boundary",
        "live_source_and_key_governance",
        "traction_deadline_action",
        "autonomous_quant_safety",
        "commercialization_customer_roi",
        "investor_profile_and_terms",
    ]:
        assert route_id in routes

    for route in payload["routes"]:
        assert route["answer"]
        assert route["funding_use"]
        assert route["claim_boundary"]
        assert route["human_gate"]
        assert route["external_send_allowed_without_human"] is False
        assert route["final_action_allowed_without_human"] is False
        assert route["missing_artifact_count"] == 0
        assert len(route["route_sha256"]) == 64
        for artifact in route["artifact_status"]:
            assert artifact["present"] is True
            assert artifact["bytes"] > 0
            assert len(artifact["sha256"]) == 64


def test_rendered_fast_lane_router_is_public_safe():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Reviewer Investor Fast-Lane Router" in rendered
    assert "All final actions blocked without human: `true`" in rendered
    assert "Final submission without human: `false`" in rendered
    assert "Live trading allowed: `false`" in rendered
    assert "Capital movement allowed: `false`" in rendered
    assert "five_minute_reviewer_start" in rendered
    assert "ip_patent_claim_boundary" in rendered
    assert "live_source_and_key_governance" in rendered
    assert "zoom.us" not in lowered
    assert "meeting id" not in lowered
    assert "password" not in lowered
    assert "one tap mobile" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
