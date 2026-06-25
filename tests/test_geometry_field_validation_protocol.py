from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_FIELD_VALIDATION_PROTOCOL.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geometry_field_validation_protocol", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_field_validation_protocol_builds_two_pilot_scoping_protocols():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    by_family = {row["family_id"]: row for row in payload["protocols"]}

    assert payload["schema"] == "geometry_field_validation_protocol_v1"
    assert summary["protocol_count"] == 2
    assert summary["ready_for_buyer_authorized_pilot_scoping_count"] == 2
    assert summary["top_family_id"] in {"brachistochrone_descent", "kuramoto_phase_coupling"}
    assert len(summary["protocol_chain_sha256"]) == 64

    assert "brachistochrone_descent" in by_family
    assert "kuramoto_phase_coupling" in by_family
    assert by_family["brachistochrone_descent"]["lane"] == "optimal_curve_transport"
    assert by_family["kuramoto_phase_coupling"]["lane"] == "wave_resonance_timing"

    for protocol in payload["protocols"]:
        assert protocol["evidence_stage"] == "ready_for_buyer_authorized_pilot_scoping"
        assert protocol["evidence_summary"]["win_count"] == 6
        assert protocol["evidence_summary"]["window_count"] == 6
        assert protocol["evidence_summary"]["normal_t_lower_95_delta"] > 0
        assert protocol["evidence_strength_score"] > 100
        assert len(protocol["field_data_required"]) >= 5
        assert len(protocol["baseline_controls"]) >= 5
        assert len(protocol["primary_kpis"]) >= 4
        assert len(protocol["protocol_sha256"]) == 64


def test_field_validation_protocol_acceptance_gate_is_buyer_authorized_and_holdout_based():
    module = load_module()
    payload = module.build_payload()

    for protocol in payload["protocols"]:
        gate = protocol["acceptance_gate"]
        assert gate["minimum_holdout_windows"] >= 20
        assert gate["minimum_independent_source_or_sensor_count"] >= 3
        assert gate["minimum_candidate_win_rate"] >= 0.6
        assert gate["minimum_wilson_lower_95_win_rate"] >= 0.5
        assert gate["minimum_lower_95_delta"] == 0.0
        assert "pre-registered holdout windows" in gate["required_result"]
        assert "buyer-authorized field data" in protocol["commercial_claim_unlock_requires"]
        assert "buyer-approved economic conversion factors" in protocol["commercial_claim_unlock_requires"]
        assert "signed or otherwise traceable pilot result artifact" in protocol["commercial_claim_unlock_requires"]


def test_field_validation_protocol_keeps_commercial_claims_blocked():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    text = json.dumps(payload).lower()

    assert summary["ready_for_field_validation_claim"] is False
    assert summary["ready_for_real_dollar_claim"] is False
    assert summary["ready_for_bulk_sales_claim"] is False
    assert summary["ready_for_live_trading"] is False
    assert "fixed-dollar delta claim" in text
    assert "live_order_placement" not in text
    assert ("api" + "_key") not in text

    for protocol in payload["protocols"]:
        gate = protocol["current_claim_gate"]
        assert gate["ready_for_field_validation_claim"] is False
        assert gate["ready_for_real_dollar_claim"] is False
        assert gate["ready_for_bulk_sales_claim"] is False
        assert gate["ready_for_live_trading"] is False


def test_field_validation_protocol_markdown_is_actionable_and_safe():
    module = load_module()
    rendered = module.render_markdown(module.build_payload())

    assert "Geometry Field Validation Protocol" in rendered
    assert "Pilot-scoping ready: `2`" in rendered
    assert "`brachistochrone_descent`" in rendered
    assert "`kuramoto_phase_coupling`" in rendered
    assert "Buyer data required" in rendered
    assert "Acceptance gate" in rendered
    assert "Ready for real-dollar claim: `false`" in rendered
    assert "Bulk frozen-delta sales claims remain blocked" in rendered
