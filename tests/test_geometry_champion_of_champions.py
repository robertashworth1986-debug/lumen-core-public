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
    assert board["summary"]["ranked_family_count"] == 140
    assert board["summary"]["benchmark_specified_family_count"] == board["summary"]["ranked_family_count"]
    assert board["summary"]["benchmark_specified_family_gap_count"] == 0
    assert board["summary"]["benchmark_specified_family_missing"] == []
    assert board["summary"]["ready_for_field_validation_claim"] is False
    assert board["summary"]["ready_for_real_dollar_claim"] is False
    assert board["summary"]["kraken_live_execution_allowed"] is False
    assert board["summary"]["live_measured_sources"] >= 18
    assert board["summary"]["live_total_measured_rows"] >= 418
    assert board["summary"]["strict_rolling_champion_count"] >= 4
    assert board["summary"]["robust_repeat_candidate_count"] >= 1
    assert board["summary"]["triple_source_candidate_count"] >= 1
    assert board["summary"]["bounded_estimated_value_claim_allowed"] is True
    assert board["summary"]["paid_pilot_scoping_allowed"] is True
    assert board["summary"]["vault_packet_ready"] is True
    assert board["summary"]["kuramoto_holdout_count"] >= 20
    assert board["summary"]["kuramoto_holdout_wins_vs_kalman"] >= 20
    assert board["summary"]["kuramoto_holdout_estimated_rows_replayed"] >= 2_000_000
    assert board["summary"]["kuramoto_holdout_source_system_count"] >= 4
    assert board["summary"]["kuramoto_ready_for_buyer_authorized_field_replay_request"] is True
    assert "field validation" in board["summary"]["claim_boundary"]
    assert board["current_truth_gates"]["field_validation_claim_allowed"] is False
    assert board["current_truth_gates"]["real_dollar_savings_claim_allowed"] is False
    assert board["current_truth_gates"]["live_trading_or_autonomous_execution_allowed"] is False
    assert board["current_truth_gates"]["all_families_have_benchmark_specs"] is True


def test_all_ranked_families_have_benchmark_specs():
    module = load_module()
    board = module.build_board()
    required = {
        "natural_logic",
        "benchmark_hypothesis",
        "first_test",
        "promotion_metric",
        "failure_mode",
    }

    missing = {
        row["family"]: sorted(field for field in required if not str(row.get(field, "")).strip())
        for row in board["family_asset_rankings"]
        if any(not str(row.get(field, "")).strip() for field in required)
    }

    assert missing == {}
    families = {row["family"]: row for row in board["family_asset_rankings"]}
    assert families["mycelium_network"]["first_test"] == "mycelium_resilient_routing_v1"
    assert families["toroidal_fields"]["first_test"] == "toroidal_field_control_v1"
    assert families["frobenius_stability"]["first_test"] == "frobenius_stability_gate_v1"


def test_operational_priority_keeps_lane_rank_bounded_and_family_rank_current():
    module = load_module()
    board = module.build_board()

    top_lane = board["lane_rankings"][0]
    top_family = board["family_asset_rankings"][0]

    assert top_lane["lane"] == "time_series_model_routing"
    assert top_lane["claim_stage"] == "live_replay_ready_not_field_validated"
    assert top_lane["measured_source_count"] >= 8
    assert top_lane["ready_for_live_geometry_claim"] is False
    assert top_lane["ready_for_real_dollar_claim"] is False
    assert top_family["family"] == "kuramoto_phase_coupling"
    assert top_family["rolling_gate_status"] == "rolling_champion"
    assert top_family["ready_for_buyer_authorized_field_replay_request"] is True
    assert top_family["holdout_gate_status"] == "internal_20_holdout_gate_passed"
    assert top_family["paid_pilot_ready"] is True


def test_known_champions_are_ranked_but_still_bounded():
    module = load_module()
    board = module.build_board()
    families = {row["family"]: row for row in board["family_asset_rankings"]}

    assert families["beast_algo_echo_stack"]["evidence_status"] == "proof_value_candidate_not_performance_claim"
    assert families["brachistochrone_descent"]["evidence_status"] == "rolling_champion_repeat_live_context_not_field_validated"
    assert families["kuramoto_phase_coupling"]["evidence_status"] == "expanded_source_conditioned_holdout_winner_not_field_validated"
    assert families["thermal_plume_convection"]["evidence_status"] == "rolling_champion_repeat_live_context_not_field_validated"
    assert families["leaf_veins"]["evidence_status"] == "triple_source_live_candidate_needs_repeat_run"
    assert families["crack_propagation_paths"]["evidence_status"] == "proof_value_candidate_not_performance_claim"
    assert families["brachistochrone_descent"]["rolling_gate_status"] == "rolling_champion"
    assert families["kuramoto_phase_coupling"]["rolling_gate_status"] == "rolling_champion"
    assert families["thermal_plume_convection"]["rolling_gate_status"] == "rolling_champion"
    assert families["leaf_veins"]["rolling_gate_status"] == "triple_source_candidate"
    assert families["brachistochrone_descent"]["claim_stage"] == "rolling_champion_not_field_validated"
    assert families["kuramoto_phase_coupling"]["claim_stage"] == "buyer_authorized_field_replay_request_ready_not_field_validated"
    assert families["kuramoto_phase_coupling"]["kuramoto_holdout_evidence"]["wins_vs_kalman"] >= 20
    assert families["kuramoto_phase_coupling"]["kuramoto_holdout_evidence"]["field_validation_claim_allowed"] is False

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


def test_champion_of_champions_surfaces_truth_gated_money_proxy():
    module = load_module()
    board = module.build_board()
    current = board["champion_of_champions"]["strongest_current"]
    money_proxy = board["champion_of_champions"]["strongest_money_proxy"]

    assert current["family"] == "kuramoto_phase_coupling"
    assert current["ready_for_buyer_authorized_field_replay_request"] is True
    assert current["ready_for_real_dollar_claim"] is False
    assert money_proxy["family_id"] == "phase_locked_residual_corrector"
    assert money_proxy["status"] == "rolling_champion"
    assert money_proxy["ready_for_real_dollar_claim"] is False


def test_markdown_lists_validation_requirements_and_no_overclaim_terms():
    module = load_module()
    board = module.build_board()
    rendered = module.render_markdown(board)

    assert "Geometry Champion Of Champions" in rendered
    assert "Field Validation Requirements" in rendered
    assert "Ready for field-validation claim: `false`" in rendered
    assert "Strict rolling champions: `4`" in rendered
    assert "Bounded estimated value claim allowed: `true`" in rendered
    assert "Strongest current candidate: `kuramoto_phase_coupling`" in rendered
    assert "Kuramoto Holdout Read" in rendered
    assert "not field validation" in rendered
    assert "Triple-source candidates" in rendered
    assert "guaranteed funding" not in rendered.lower()
    assert "guaranteed profit" not in rendered.lower()
