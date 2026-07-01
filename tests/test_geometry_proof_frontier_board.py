from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_PROOF_FRONTIER_BOARD.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geometry_proof_frontier_board", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_frontier_counts_registry_and_separates_champion_types():
    module = load_module()
    board = module.build_board()

    assert board["schema"] == "geometry_proof_frontier_board_v1"
    health = board["registry_health"]
    assert health["family_count"] >= 75
    assert health["lane_count"] == 12
    assert health["natural_logic_family_count"] >= 50
    assert health["benchmark_hypothesis_family_count"] >= 50
    assert health["cross_lane_ranking_allowed"] is False
    assert "No geometry is sacred" in health["core_rule"]

    champions = board["champion_board"]
    assert champions["generated_benchmark_champion"]["family"] == "brachistochrone_descent"
    assert champions["generated_benchmark_champion"]["lane"] == "optimal_curve_transport"
    assert champions["generated_benchmark_champion"]["status"] == "generated_lane_champion_not_live_claim"
    assert champions["proof_value_champion"]["family"] == "crack_propagation_paths"
    assert champions["proof_value_champion"]["status"] == "highest_funding_and_proof_priority_not_performance_winner"
    assert champions["live_proof_champion"]["name"] == "DICE live-breadth replay"
    assert "never conflated" in champions["boundary"]


def test_frontier_ranks_generated_winners_and_live_wiring_queue():
    module = load_module()
    board = module.build_board()
    generated = board["generated_benchmark_frontier"]
    by_lane = {row["lane"]: row for row in generated}

    assert generated[0]["lane"] == "optimal_curve_transport"
    assert generated[0]["best_geometry"] == "brachistochrone_descent"
    assert generated[0]["frontier_score"] > by_lane["wave_resonance_timing"]["frontier_score"]
    assert by_lane["wave_resonance_timing"]["best_geometry"] == "kuramoto_phase_coupling"
    assert by_lane["thermal_ventilation"]["best_geometry"] == "thermal_plume_convection"
    assert by_lane["branching_transport"]["best_geometry"] == "leaf_veins"
    assert set(by_lane) == {
        "optimal_curve_transport",
        "wave_resonance_timing",
        "thermal_ventilation",
        "branching_transport",
    }

    for row in generated:
        assert row["target_assets"]
        assert row["first_adapter"]
        assert row["ready_for_live_claim"] is False
        assert row["ready_for_real_dollar_claim"] is False
        assert row["kraken_live_execution_allowed"] is False
        assert row["evidence_status"] == "generated_software_benchmark_only"


def test_frontier_promotes_live_proof_without_field_or_profit_claims():
    module = load_module()
    board = module.build_board()
    live = board["current_live_proof_champions"]
    gate = board["promotion_gate"]
    rendered = module.render_markdown(board)

    assert live[0]["name"] == "DICE live-breadth replay"
    assert live[0]["source_count"] == 6
    assert live[0]["scenario_count"] == 14
    assert live[0]["ready_for_submit"] is False
    assert "not_field_validation" in live[0]["claim_status"]
    assert any(row["name"] == "HarborSentinel public AIS controlled-injection" for row in live)

    assert gate["ready_for_live_geometry_claim"] is False
    assert gate["ready_for_real_dollar_claim"] is False
    assert gate["kraken_live_execution_allowed"] is False
    assert gate["live_breadth_backed_generated_lanes"] == 0
    assert gate["synthetic_only_generated_lanes"] == 4
    assert any("frozen raw input manifest" in item for item in gate["requirements"])
    assert any("identical baselines" in item for item in gate["requirements"])

    assert "Champion-Of-Champions" in rendered
    assert "Live Assets" in rendered
    assert "Ready for live geometry claim: `false`" in rendered
    assert "Kraken live execution allowed: `false`" in rendered
    assert "Guaranteed funding" not in rendered
    assert "live_order_placement" not in json.dumps(board)
