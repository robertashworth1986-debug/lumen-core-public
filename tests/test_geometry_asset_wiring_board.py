from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_ASSET_WIRING_BOARD.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geometry_asset_wiring_board", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_asset_wiring_board_builds_reviewer_safe_summary():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "geometry_asset_wiring_board_v1"
    assert summary["proof_card_count"] >= 9
    assert summary["ranked_family_count"] >= 140
    assert summary["registered_family_count"] >= 140
    assert summary["live_measured_sources"] >= 18
    assert summary["live_measured_rows"] >= 418
    assert summary["rolling_champion_count"] >= 3
    assert summary["robust_repeat_candidate_count"] >= 1
    assert summary["triple_source_rolling_champion_count"] >= 1
    assert summary["single_run_candidate_count"] == 0
    assert summary["dashboard_feed_count"] >= 4
    assert summary["grant_packet_feed_count"] >= 3
    assert summary["outreach_feed_count"] >= 3
    assert summary["validation_run_count"] >= 9
    assert summary["candidate_win_count"] >= 3
    assert summary["field_validation_target_count"] >= 9
    assert summary["buyer_authorized_replay_ready_count"] >= 5
    assert summary["external_owner_required_count"] >= 9
    assert len(summary["board_chain_sha256"]) == 64

    assert summary["ready_for_live_geometry_claim"] is False
    assert summary["ready_for_real_dollar_claim"] is False
    assert summary["field_validation"] is False
    assert summary["kraken_live_execution_allowed"] is False
    assert summary["mass_email_allowed"] is False
    assert summary["bounded_estimated_value_claim_allowed"] is False
    assert summary["paid_pilot_scoping_allowed"] is True
    assert summary["vps_domain_live_dashboard_routed"] is False
    assert payload["send_gate"]["send_without_user_review"] is False
    assert len(payload["high_value_wiring_queue"]) >= 20
    assert len(payload["field_validation_target_queue"]) >= 5


def test_key_rows_wire_to_dashboards_grants_outreach_and_blockers():
    module = load_module()
    payload = module.build_payload()
    rows = {row["family_id"]: row for row in payload["wiring_rows"]}

    for family_id in [
        "brachistochrone_descent",
        "kuramoto_phase_coupling",
        "thermal_plume_convection",
        "leaf_veins",
        "crack_propagation_paths",
    ]:
        assert family_id in rows
        row = rows[family_id]
        assert "mission_control" in row["dashboard_targets"]
        assert "grants" in row["dashboard_targets"]
        assert row["grant_targets"]
        assert row["buyer_segments"]
        assert row["buyer_outreach_position"]["send_gate"]["mass_email_allowed"] is False
        assert row["claim_gate"]["ready_for_real_dollar_claim"] is False
        assert row["claim_gate"]["field_validation"] is False
        assert row["field_validation_target"]["field_validation_claim_allowed_now"] is False
        assert row["field_validation_target"]["real_dollar_claim_allowed_now"] is False
        assert row["field_validation_target"]["external_owner_needed"]
        assert row["field_validation_target"]["buyer_data_needed"]
        assert len(row["row_sha256"]) == 64

    brach = rows["brachistochrone_descent"]
    assert brach["readiness_tier"] == "rolling_champion_robust_repeat_pilot_ready"
    assert brach["rolling_gate_status"] == "rolling_champion"
    assert brach["robust_repeat_uncertainty_gate_passed"] is True
    assert brach["paid_pilot_ready"] is True
    assert "buyer-authorized field data" in brach["next_high_value_step"]
    assert any("buyer or agency authorized field data" in item for item in brach["blockers"])
    assert brach["validation_run"]["candidate_beats_named_baseline"] is True
    assert "DARPA/I2O or DICE-style reviewer evidence annex" in brach["grant_targets"]
    assert "Dijkstra" in brach["field_validation_target"]["incumbent_baseline"]
    assert "buyer-authorized" in brach["field_validation_target"]["next_request"]

    kuramoto = rows["kuramoto_phase_coupling"]
    assert kuramoto["readiness_tier"] == "rolling_champion_robust_repeat_pilot_ready"
    assert kuramoto["rolling_gate_status"] == "rolling_champion"
    assert kuramoto["paid_pilot_ready"] is True
    assert "forecast" in kuramoto["dashboard_targets"]
    assert "uncertainty" in json.dumps(kuramoto).lower()
    assert "Kalman" in kuramoto["field_validation_target"]["incumbent_baseline"]
    assert "phase" in kuramoto["field_validation_target"]["candidate_metric"]
    assert kuramoto["field_validation_target"]["minimum_holdouts"] >= 20

    thermal = rows["thermal_plume_convection"]
    assert thermal["readiness_tier"] == "rolling_champion_needs_field_authorized_holdouts"
    assert thermal["rolling_gate_status"] == "rolling_champion"
    assert any("three measured source types" in item for item in thermal["blockers"])
    assert any("DOE" in target for target in thermal["grant_targets"])
    assert "thermal" in thermal["field_validation_target"]["candidate_metric"]
    assert "cooling" in thermal["field_validation_target"]["next_request"]

    leaf = rows["leaf_veins"]
    assert leaf["readiness_tier"] == "rolling_champion_needs_field_authorized_holdouts"
    assert leaf["rolling_gate_status"] == "rolling_champion"
    assert leaf["validation_run"]["candidate_beats_named_baseline"] is True
    assert leaf["validation_run"]["candidate_score_delta_vs_named_baseline"] > 0
    assert "field validation" in leaf["allowed_language"]
    assert leaf["claim_gate"]["ready_for_real_dollar_claim"] is False
    assert "min-cost" in leaf["field_validation_target"]["incumbent_baseline"]

    crack = rows["crack_propagation_paths"]
    assert "proof_value" in crack["readiness_tier"]
    assert any("Infrastructure" in target for target in crack["grant_targets"])

    assert "phase_locked_residual_corrector" not in rows


def test_next_actions_and_markdown_keep_claim_boundaries_visible():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    actions = {item["family_id"]: item for item in payload["top_next_actions"]}

    assert "brachistochrone_descent" in actions
    assert "buyer-authorized pilot scoping" in actions["brachistochrone_descent"]["action"]
    assert "kuramoto_phase_coupling" in actions
    assert "pre-registered holdout windows" in actions["kuramoto_phase_coupling"]["action"]
    assert "thermal_plume_convection" in actions
    assert "crack_propagation_paths" in actions

    assert "Geometry Asset Wiring Board" in rendered
    assert "Rolling champions in wired proof cards: `4`" in rendered
    assert "Triple-source rolling champions" in rendered
    assert "Field-Validation Target Queue" in rendered
    assert "buyer-authorized" in rendered
    assert "High-Value Wiring Queue" in rendered
    assert "Bounded estimated value claim allowed: `false`" in rendered
    assert "Ready for real-dollar claim: `false`" in rendered
    assert "Mass email allowed: `false`" in rendered
    assert "Do not say a packet is worth a fixed dollar amount as fact." in rendered
    assert "guaranteed profit" not in rendered.lower()
    assert "live_order_placement" not in json.dumps(payload)
