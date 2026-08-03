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


def test_field_validation_control_room_has_no_performance_champion():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "field_validation_control_room_v2"
    assert summary["internal_performance_champion_present"] is False
    assert summary["strongest_current_family"] == ""
    assert summary["strongest_current_lane"] == ""
    assert summary["strongest_current_status"] == "no_current_performance_champion"
    assert summary["next_asset_build_priority_family"] == "beast_algo_echo_stack"
    assert summary["kuramoto_holdout_wins_vs_kalman"] == 482
    assert summary["kuramoto_holdout_count"] == 1525
    assert summary["kuramoto_mean_delta_vs_kalman"] == -0.508191
    assert summary["direct_all_baseline_global_holm_positive_count"] == 0
    assert summary["best_buyer_pilot_family"] == ""
    assert len(payload["control_room_sha256"]) == 64


def test_field_validation_control_room_keeps_claim_gates_closed():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    ladder = {row["stage"]: row for row in payload["proof_bridge"]["claim_ladder"]}

    assert summary["manual_outreach_ready"] is False
    assert summary["bulk_email_allowed"] is False
    assert summary["external_validation_unlock_packet_ready"] is False
    assert summary["external_approval_received"] is False
    assert summary["grid_rf_pll_protocols_ready"] is True
    assert summary["broader_measured_provider_count"] == 24
    assert summary["broader_measured_row_count"] == 17081
    assert summary["field_validation_claim_allowed"] is False
    assert summary["real_dollar_savings_claim_allowed"] is False
    assert summary["fixed_dollar_delta_claim_allowed"] is False
    assert summary["live_trading_or_autonomous_execution_allowed"] is False
    assert summary["paid_protocol_review_scoping_ready"] is True

    assert ladder["direct_measured_replay"]["status"] == "completed_nonpromotion"
    assert (
        ladder["source_specific_candidate_promotion"]["status"]
        == "blocked_all_baseline_gate_failed"
    )
    assert (
        ladder["buyer_authorized_field_replay_request"]["status"]
        == "blocked_no_promoted_candidate"
    )
    assert (
        ladder["field_validation"]["status"]
        == "blocked_until_external_owner_protocol_and_accepted_result"
    )
    assert ladder["field_validation"]["claim_allowed"] is False
    assert (
        ladder["real_dollar_claim"]["status"]
        == "blocked_until_accepted_economics"
    )
    assert ladder["real_dollar_claim"]["claim_allowed"] is False
    assert ladder["live_execution_or_trading"]["claim_allowed"] is False


def test_field_validation_control_room_separates_build_priority_and_buyer_tracks():
    module = load_module()
    payload = module.build_payload()
    top_rows = payload["top_assets"]["top_family_asset_rankings"]
    buyer_tracks = {row["family_id"]: row for row in payload["buyer_tracks"]}

    assert len(top_rows) == 5
    assert top_rows[0]["family"] == "beast_algo_echo_stack"
    assert top_rows[0]["manual_outreach_allowed"] is False
    assert top_rows[0]["paid_pilot_ready"] is False

    assert "kuramoto_phase_coupling" in buyer_tracks
    assert "brachistochrone_descent" in buyer_tracks
    assert "Negative-Result" in buyer_tracks["kuramoto_phase_coupling"][
        "protocol_review_name"
    ]
    assert "Protocol Review" in buyer_tracks["brachistochrone_descent"][
        "protocol_review_name"
    ]
    assert buyer_tracks["kuramoto_phase_coupling"]["send_allowed"] is False
    assert buyer_tracks["brachistochrone_descent"]["send_allowed"] is False


def test_field_validation_control_room_markdown_is_reviewer_safe():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Field Validation Control Room" in rendered
    assert "Internal performance champion present: `false`" in rendered
    assert "Kuramoto measured wins vs Kalman: `482/1525`" in rendered
    assert "Kuramoto mean skill delta: `-0.508191`" in rendered
    assert "Direct all-baseline global promotions: `0`" in rendered
    assert "Manual outreach ready: `false`" in rendered
    assert "Paid protocol-review scoping ready: `true`" in rendered
    assert "Field-validation claim allowed: `false`" in rendered
    assert "External Validation Unlock" in rendered
    assert "Grid/RF/PLL Validation Tracks" in rendered
    assert "held_out_operational_data" in rendered
    assert "economic_conversion_factor" in rendered
    assert "blocked_no_promoted_candidate" in lowered
    assert "field performance or savings" in lowered
    assert "Next 10 Actions" in rendered
    assert "Current performance champion: `none`" in rendered
    assert "24/24" not in rendered
