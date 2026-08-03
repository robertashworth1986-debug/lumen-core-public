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

    assert board["schema"] == "geometry_champion_of_champions_v3"
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
    assert board["summary"]["strict_rolling_champion_count"] == 0
    assert board["summary"]["internal_performance_champion_count"] == 0
    assert board["summary"]["robust_repeat_candidate_count"] == 0
    assert board["summary"]["triple_source_rolling_champion_count"] == 0
    assert board["summary"]["implementation_present_count"] == 31
    assert board["summary"]["frozen_generated_executed_count"] == 30
    assert board["summary"]["source_conditioned_replay_family_count"] == 4
    assert board["summary"]["qualified_direct_source_link_count"] == 10
    assert board["summary"]["qualified_conditioning_source_link_count"] == 12
    assert board["summary"]["context_only_measured_source_link_count"] == 46
    assert board["summary"]["direct_source_replay_build_ready_lane_count"] == 2
    assert board["summary"]["adapter_replay_count"] == 4
    assert board["summary"]["direct_measured_replay_count"] == 2
    assert board["summary"]["conditioned_synthetic_replay_count"] == 2
    assert (
        board["summary"]["direct_all_baseline_global_holm_positive_count"] == 0
    )
    assert board["summary"]["legacy_ready_rows_excluded"] >= 300
    assert board["summary"]["numeric_fallback_profile_count"] == 0
    assert board["summary"]["field_validated_family_count"] == 0
    assert board["summary"]["bounded_estimated_value_claim_allowed"] is False
    assert board["summary"]["safe_estimated_hourly_value_usd"] == 0
    assert board["summary"]["safe_estimated_annual_value_usd"] == 0
    assert board["summary"]["paid_pilot_scoping_allowed"] is True
    assert board["summary"]["vault_packet_ready"] is True
    assert board["summary"]["kuramoto_holdout_count"] >= 1_500
    assert (
        board["summary"]["kuramoto_holdout_wins_vs_kalman"]
        < board["summary"]["kuramoto_holdout_count"] / 2
    )
    assert board["summary"]["kuramoto_holdout_mean_delta_vs_kalman"] < 0
    assert board["summary"]["kuramoto_holdout_estimated_rows_replayed"] >= 15_000
    assert board["summary"]["kuramoto_holdout_source_system_count"] == 1
    assert (
        board["summary"][
            "kuramoto_ready_for_buyer_authorized_field_replay_request"
        ]
        is False
    )
    assert board["summary"]["paid_pilot_ready_count"] == 0
    assert board["summary"]["legacy_pilot_card_excluded_count"] >= 2
    assert "field validation" in board["summary"]["claim_boundary"]
    assert board["current_truth_gates"]["field_validation_claim_allowed"] is False
    assert board["current_truth_gates"]["real_dollar_savings_claim_allowed"] is False
    assert board["current_truth_gates"]["live_trading_or_autonomous_execution_allowed"] is False
    assert board["current_truth_gates"]["all_families_have_benchmark_specs"] is True
    assert board["protocol_field_receipt"]["self_hash_valid"] is True
    assert board["summary"]["reviewer_packet_is_external_validation"] is False


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
    assert (
        top_lane["claim_stage"]
        == "direct_source_replay_build_ready_not_field_validated"
    )
    assert top_lane["measured_source_count"] >= 8
    assert top_lane["direct_source_count"] >= 6
    assert top_lane["ready_for_direct_source_replay_build"] is True
    assert top_lane["ready_for_live_geometry_claim"] is False
    assert top_lane["ready_for_real_dollar_claim"] is False
    assert top_family["family"] == "beast_algo_echo_stack"
    assert (
        top_family["evidence_status"]
        == "proof_value_candidate_not_performance_claim"
    )
    assert top_family["rolling_gate_status"] == "not_in_rolling_gate"
    assert top_family["paid_pilot_ready"] is False
    assert top_family["manual_outreach_allowed"] is False


def test_known_candidates_are_ranked_but_still_bounded():
    module = load_module()
    board = module.build_board()
    families = {row["family"]: row for row in board["family_asset_rankings"]}

    assert families["beast_algo_echo_stack"]["evidence_status"] == "proof_value_candidate_not_performance_claim"
    assert families["brachistochrone_descent"]["evidence_status"] == "generated_software_benchmark_only_needs_live_replay"
    assert families["kuramoto_phase_coupling"]["evidence_status"] == "direct_measured_eia_nonpromotion_result"
    assert families["thermal_plume_convection"]["evidence_status"] == "generated_software_benchmark_only_needs_live_replay"
    assert families["leaf_veins"]["evidence_status"] == "generated_software_benchmark_only_needs_live_replay"
    assert families["crack_propagation_paths"]["evidence_status"] == "proof_value_candidate_not_performance_claim"
    assert families["brachistochrone_descent"]["rolling_gate_status"] == "not_promoted"
    assert families["kuramoto_phase_coupling"]["rolling_gate_status"] == "not_promoted"
    assert families["thermal_plume_convection"]["rolling_gate_status"] == "not_promoted"
    assert families["leaf_veins"]["rolling_gate_status"] == "not_promoted"
    assert families["brachistochrone_descent"]["legacy_pilot_card_excluded"] is True
    assert families["brachistochrone_descent"]["paid_pilot_ready"] is False
    assert families["kuramoto_phase_coupling"]["claim_stage"] == "direct_measured_source_specific_baseline_gate_failed"
    assert families["kuramoto_phase_coupling"]["holdout_gate_status"] == "source_specific_all_baseline_gate_failed"
    assert families["kuramoto_phase_coupling"]["ready_for_buyer_authorized_field_replay_request"] is False
    assert families["kuramoto_phase_coupling"]["kuramoto_holdout_evidence"]["wins_vs_kalman"] < families["kuramoto_phase_coupling"]["kuramoto_holdout_evidence"]["holdout_count"] / 2
    assert families["kuramoto_phase_coupling"]["kuramoto_holdout_evidence"]["mean_delta_vs_kalman"] < 0
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
    section = board["champion_of_champions"]
    current = section["strongest_current"]
    asset_priority = section["next_asset_build_priority"]
    money_proxy = board["champion_of_champions"]["strongest_money_proxy"]

    assert section["internal_performance_champion_present"] is False
    assert current == {}
    assert asset_priority["family"] == "beast_algo_echo_stack"
    assert asset_priority["paid_pilot_ready"] is False
    assert money_proxy["family_id"] == "phase_locked_residual_corrector"
    assert money_proxy["status"] == "not_promoted"
    assert money_proxy["ready_for_real_dollar_claim"] is False


def test_markdown_lists_validation_requirements_and_no_overclaim_terms():
    module = load_module()
    board = module.build_board()
    rendered = module.render_markdown(board)

    assert "Geometry Champion Of Champions" in rendered
    assert "Field Validation Requirements" in rendered
    assert "Ready for field-validation claim: `false`" in rendered
    assert "Strict rolling champions: `0`" in rendered
    assert "Internal performance champions: `0`" in rendered
    assert "Bounded estimated value claim allowed: `false`" in rendered
    assert "Safe estimated value signal: `$0/hour`, `$0/year`" in rendered
    assert "Current performance champion: `none`" in rendered
    assert "Next asset-build priority: `beast_algo_echo_stack`" in rendered
    assert "Kuramoto Holdout Read" in rendered
    assert "does not establish field validation" in rendered
    assert "Triple-source rolling champions" in rendered
    assert "Triple-source candidates" in rendered
    assert "guaranteed funding" not in rendered.lower()
    assert "guaranteed profit" not in rendered.lower()
