from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_CHAMPION_OF_CHAMPIONS.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geometry_champion_of_champions", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_board_ranks_all_lanes_and_families_without_global_winner_claim():
    module = load_module()
    board = module.build_board()

    assert board["schema"] == "geometry_champion_of_champions_v1"
    assert board["global_performance_champion_allowed"] is False
    assert board["summary"]["ranked_lane_count"] == 12
    assert board["summary"]["ranked_family_count"] >= 75
    assert board["summary"]["ready_for_field_validation_claim"] is False
    assert board["summary"]["ready_for_real_dollar_claim"] is False
    assert board["summary"]["kraken_live_execution_allowed"] is False
    assert board["summary"]["strict_rolling_champion_count"] == 0
    assert board["summary"]["triple_source_candidate_count"] >= 3
    assert "field validation" in board["summary"]["claim_boundary"]


def test_operational_priority_prefers_live_wired_time_series_lane():
    module = load_module()
    board = module.build_board()

    top_lane = board["lane_rankings"][0]

    assert top_lane["lane"] == "time_series_model_routing"
    assert top_lane["claim_stage"] == "live_replay_ready_not_field_validated"
    assert top_lane["measured_source_count"] >= 8
    assert top_lane["ready_for_live_geometry_claim"] is False
    assert top_lane["ready_for_real_dollar_claim"] is False


def test_known_champions_are_ranked_but_still_bounded():
    module = load_module()
    board = module.build_board()
    families = {row["family"]: row for row in board["family_asset_rankings"]}

    assert families["beast_algo_echo_stack"]["evidence_status"] == "proof_value_candidate_not_performance_claim"
    assert families["brachistochrone_descent"]["evidence_status"] == "triple_source_live_candidate_needs_repeat_run"
    assert families["kuramoto_phase_coupling"]["evidence_status"] == "triple_source_live_candidate_needs_repeat_run"
    assert families["thermal_plume_convection"]["evidence_status"] == "single_run_candidate_needs_more_sources_or_repeat"
    assert families["crack_propagation_paths"]["evidence_status"] == "proof_value_candidate_not_performance_claim"
    assert families["brachistochrone_descent"]["rolling_gate_status"] == "triple_source_candidate"
    assert families["kuramoto_phase_coupling"]["rolling_gate_status"] == "triple_source_candidate"

    for family in (
        "beast_algo_echo_stack",
        "brachistochrone_descent",
        "kuramoto_phase_coupling",
        "thermal_plume_convection",
        "crack_propagation_paths",
    ):
        assert families[family]["ready_for_field_validation_claim"] is False
        assert families[family]["ready_for_real_dollar_claim"] is False


def test_market_lane_remains_quarantined_from_live_execution_claims():
    module = load_module()
    board = module.build_board()
    lanes = {row["lane"]: row for row in board["lane_rankings"]}

    market = lanes["market_signal_geometry"]

    assert market["kraken_live_execution_allowed"] is False
    assert market["ready_for_live_geometry_claim"] is False
    assert market["ready_for_real_dollar_claim"] is False
    assert market["operational_proof_score"] < lanes["time_series_model_routing"]["operational_proof_score"]


def test_markdown_lists_validation_requirements_and_no_overclaim_terms():
    module = load_module()
    board = module.build_board()
    rendered = module.render_markdown(board)

    assert "Geometry Champion Of Champions" in rendered
    assert "Field Validation Requirements" in rendered
    assert "Ready for field-validation claim: `false`" in rendered
    assert "Triple-source candidates" in rendered
    assert "guaranteed funding" not in rendered.lower()
    assert "guaranteed profit" not in rendered.lower()
