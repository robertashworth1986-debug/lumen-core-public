from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_FIELD_VALIDATION_CONTROL_ROOM.py"


def load_module():
    spec = importlib.util.spec_from_file_location("field_validation_control_room", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_field_validation_control_room_promotes_strongest_current_asset():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "field_validation_control_room_v1"
    assert summary["strongest_current_family"] == "kuramoto_phase_coupling"
    assert summary["strongest_current_lane"] == "wave_resonance_timing"
    assert summary["strongest_current_status"] == "ready_to_request_field_replay_not_yet_field_validated"
    assert summary["kuramoto_holdout_wins_vs_kalman"] == 24
    assert summary["kuramoto_holdout_count"] == 24
    assert summary["kuramoto_estimated_rows_replayed"] >= 2_000_000
    assert summary["kuramoto_source_system_count"] >= 4
    assert summary["best_buyer_pilot_family"] == "brachistochrone_descent"
    assert len(payload["control_room_sha256"]) == 64


def test_field_validation_control_room_keeps_claim_gates_closed():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    ladder = {row["stage"]: row for row in payload["proof_bridge"]["claim_ladder"]}

    assert summary["manual_outreach_ready"] is True
    assert summary["bulk_email_allowed"] is False
    assert summary["external_validation_unlock_packet_ready"] is True
    assert summary["external_approval_received"] is False
    assert summary["grid_rf_pll_protocols_ready"] is True
    assert summary["broader_measured_provider_count"] >= 4
    assert summary["manifest_unique_source_count"] >= 4
    assert summary["field_validation_claim_allowed"] is False
    assert summary["real_dollar_savings_claim_allowed"] is False
    assert summary["fixed_dollar_delta_claim_allowed"] is False
    assert summary["live_trading_or_autonomous_execution_allowed"] is False

    assert ladder["internal_live_replay"]["status"] == "passed"
    assert ladder["buyer_authorized_field_replay_request"]["status"] == "ready"
    assert ladder["field_validation"]["status"] == "blocked_until_external_owner_replay"
    assert ladder["field_validation"]["claim_allowed"] is False
    assert ladder["real_dollar_claim"]["status"] == "blocked_until_buyer_approved_economics"
    assert ladder["real_dollar_claim"]["claim_allowed"] is False
    assert ladder["live_execution_or_trading"]["claim_allowed"] is False


def test_field_validation_control_room_wires_top_assets_and_buyer_tracks():
    module = load_module()
    payload = module.build_payload()
    top_rows = payload["top_assets"]["top_family_asset_rankings"]
    buyer_tracks = {row["family_id"]: row for row in payload["buyer_tracks"]}

    assert len(top_rows) == 5
    assert top_rows[0]["family"] == "kuramoto_phase_coupling"
    assert top_rows[0]["asset_score"] > top_rows[1]["asset_score"]
    assert top_rows[0]["manual_outreach_allowed"] is True

    assert "kuramoto_phase_coupling" in buyer_tracks
    assert "brachistochrone_descent" in buyer_tracks
    assert "Resonance Timing" in buyer_tracks["kuramoto_phase_coupling"]["pilot_name"]
    assert "Constrained Transport" in buyer_tracks["brachistochrone_descent"]["pilot_name"]
    assert len(buyer_tracks["kuramoto_phase_coupling"]["priority_buyer_titles"]) >= 4


def test_field_validation_control_room_markdown_is_reviewer_safe():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Field Validation Control Room" in rendered
    assert "Internal wins vs Kalman: `24/24`" in rendered
    assert "Field-validation claim allowed: `false`" in rendered
    assert "External Validation Unlock" in rendered
    assert "Grid/RF/PLL Validation Tracks" in rendered
    assert "held_out_operational_data" in rendered
    assert "economic_conversion_factor" in rendered
    assert "This supports a field-replay request" in rendered
    assert "does not establish field validation or a realized-dollar claim" in rendered
    assert "Next 10 Actions" in rendered
    assert "fixed dollar value per frozen delta" in lowered
    assert "guaranteed trading or institutional profit" in lowered
