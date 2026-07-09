from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_IMMEDIATE_FEDERAL_AI_OPPORTUNITY_RADAR.py"


def load_module():
    spec = importlib.util.spec_from_file_location("immediate_federal_ai_opportunity_radar", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_radar_builds_near_deadline_federal_ai_queue():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "immediate_federal_ai_opportunity_radar_v1"
    assert payload["status"] == "IMMEDIATE_FEDERAL_AI_OPPORTUNITY_RADAR_READY_HUMAN_ACTION_REQUIRED"
    assert payload["summary"]["opportunity_count"] >= 8
    assert payload["summary"]["close_deadline_count"] >= 5
    assert payload["summary"]["recommended_action_count"] >= 3
    assert payload["summary"]["human_action_required"] is True
    assert payload["summary"]["external_send_allowed_without_human"] is False
    assert payload["summary"]["final_submission_allowed_without_human"] is False
    assert len(payload["radar_sha256"]) == 64


def test_radar_keeps_prime_partner_and_no_bid_boundaries_clear():
    module = load_module()
    payload = module.build_payload()
    rows = {row["opportunity_id"]: row for row in payload["opportunities"]}

    assert rows["fhwa_tsmo_data_initiative"]["pursuit_posture"] == "PRIMARY_PHASE_I_TECHNICAL_VOLUME"
    assert rows["air_force_aac_advanced_automation_rfi"]["pursuit_posture"] == "CAPABILITY_RESPONSE_DRAFT"
    assert rows["hhs_ai_power_user_pilot"]["pursuit_posture"] == "PARTNER_OR_NO_BID"
    assert rows["csosa_public_safety_analytics"]["pursuit_posture"] == "NO_PRIME_FEDRAMP_GATE"
    assert rows["va_omega_2_assurance_services"]["data_quality_flags"]

    for row in payload["opportunities"]:
        assert row["human_gate_required"] is True
        assert row["final_submission_allowed_without_human"] is False
        assert row["opportunity_sha256"]
        assert row["primary_blockers"]
        assert row["reuse_evidence"]


def test_rendered_radar_is_public_safe_and_business_translated():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Immediate Federal AI Opportunity Radar" in rendered
    assert "Best immediate action" in rendered
    assert "Terry Feedback Translation" in rendered
    assert "External send without human: `false`" in rendered
    assert "Final submission without human: `false`" in rendered
    assert "FedRAMP, ATO, customer savings, or award status" in rendered
    assert "zoom.us" not in lowered
    assert "password" not in lowered
    assert "meeting id" not in lowered
    assert "one tap mobile" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
