from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_CHAMPIONSHIP_BRIDGE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geometry_championship_bridge", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_bridge_ranks_lane_champions_without_performance_claims():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "geometry_championship_bridge_v1"
    assert payload["summary"]["family_count"] >= 75
    assert payload["summary"]["natural_logic_family_count"] >= 50
    assert payload["summary"]["benchmark_hypothesis_family_count"] >= 50
    assert payload["summary"]["performance_results_generated"] is False
    assert payload["summary"]["performance_champion"] is None
    assert payload["proof_build_champion"]["evidence_status"] == "candidate_champion_only_not_performance_claim"
    assert len(payload["lane_champion_rankings"]) == payload["summary"]["lane_count"]


def test_bridge_keeps_brachistochrone_and_market_geometry_in_queue():
    module = load_module()
    payload = module.build_payload()
    family_ids = {row["family_id"] for row in payload["top_family_benchmark_queue"]}
    lane_ids = {row["lane"]: row for row in payload["lane_champion_rankings"]}

    assert "brachistochrone_descent" in family_ids
    assert "market_signal_geometry" in lane_ids
    assert lane_ids["market_signal_geometry"]["candidate_champion_id"] == "order_book_liquidity_contours"
    assert lane_ids["market_signal_geometry"]["live_execution_allowed"] is False


def test_bridge_exposes_branching_benchmark_without_promoting_global_winner():
    module = load_module()
    payload = module.build_payload()
    benchmark = payload["branching_transport_benchmark"]

    assert payload["summary"]["branching_transport_benchmark_generated"] is True
    assert benchmark["lane"] == "branching_transport"
    assert benchmark["claim_gate"]["lane_specific_generated_benchmark"] is True
    assert benchmark["claim_gate"]["global_geometry_champion"] is False
    assert benchmark["claim_gate"]["field_validation"] is False
    assert benchmark["claim_gate"]["real_dollar_claim"] is False
    assert benchmark["live_execution_allowed"] is False
    assert payload["summary"]["branching_transport_field_validation"] is False


def test_bridge_exposes_thermal_benchmark_and_generated_champion_without_dollar_claims():
    module = load_module()
    payload = module.build_payload()
    benchmark = payload["thermal_ventilation_benchmark"]
    generated = payload["generated_lane_benchmarks"]

    assert payload["summary"]["thermal_ventilation_benchmark_generated"] is True
    assert benchmark["lane"] == "thermal_ventilation"
    assert benchmark["claim_gate"]["lane_specific_generated_benchmark"] is True
    assert benchmark["claim_gate"]["cfd_validation"] is False
    assert benchmark["claim_gate"]["datacenter_validation"] is False
    assert benchmark["claim_gate"]["field_validation"] is False
    assert benchmark["claim_gate"]["real_dollar_claim"] is False
    assert benchmark["live_execution_allowed"] is False
    assert payload["summary"]["thermal_ventilation_field_validation"] is False

    lanes = {row["lane"]: row for row in generated}
    assert {"branching_transport", "thermal_ventilation", "optimal_curve_transport", "wave_resonance_timing"}.issubset(lanes)
    assert all(row["live_execution_allowed"] is False for row in generated)
    assert all(row["real_dollar_claim"] is False for row in generated)


def test_bridge_exposes_optimal_curve_benchmark_and_brachistochrone_champion():
    module = load_module()
    payload = module.build_payload()
    benchmark = payload["optimal_curve_transport_benchmark"]

    assert payload["summary"]["optimal_curve_transport_benchmark_generated"] is True
    assert benchmark["lane"] == "optimal_curve_transport"
    assert benchmark["claim_gate"]["lane_specific_generated_benchmark"] is True
    assert benchmark["claim_gate"]["robotics_validation"] is False
    assert benchmark["claim_gate"]["cabling_validation"] is False
    assert benchmark["claim_gate"]["field_validation"] is False
    assert benchmark["claim_gate"]["trading_signal"] is False
    assert benchmark["claim_gate"]["real_dollar_claim"] is False
    assert benchmark["live_execution_allowed"] is False
    assert payload["summary"]["optimal_curve_transport_field_validation"] is False
    assert payload["summary"]["optimal_curve_transport_best_geometry"] == "brachistochrone_descent"
    assert payload["summary"]["generated_champion_lane"] == "optimal_curve_transport"
    assert payload["summary"]["generated_champion_strategy"] == "brachistochrone_descent"
    assert payload["generated_champion_of_champions"]["best_geometry"] == "brachistochrone_descent"


def test_bridge_exposes_wave_resonance_benchmark_for_harmonic_claims():
    module = load_module()
    payload = module.build_payload()
    benchmark = payload["wave_resonance_timing_benchmark"]

    assert payload["summary"]["wave_resonance_timing_benchmark_generated"] is True
    assert benchmark["lane"] == "wave_resonance_timing"
    assert benchmark["claim_gate"]["lane_specific_generated_benchmark"] is True
    assert benchmark["claim_gate"]["grid_validation"] is False
    assert benchmark["claim_gate"]["pll_hardware_validation"] is False
    assert benchmark["claim_gate"]["rf_validation"] is False
    assert benchmark["claim_gate"]["medical_validation"] is False
    assert benchmark["claim_gate"]["field_validation"] is False
    assert benchmark["claim_gate"]["trading_signal"] is False
    assert benchmark["claim_gate"]["real_dollar_claim"] is False
    assert benchmark["live_execution_allowed"] is False
    assert payload["summary"]["wave_resonance_timing_field_validation"] is False
    assert payload["summary"]["wave_resonance_timing_best_geometry"] == "kuramoto_phase_coupling"
    assert payload["summary"]["wave_resonance_timing_best_baseline"] == "kalman_filter"


def test_bridge_live_breadth_gate_blocks_generated_lanes_from_live_claims():
    module = load_module()
    payload = module.build_payload()
    gate = payload["live_breadth_promotion_gate"]

    assert gate["gate"] == "live_breadth_not_yet_mapped_to_geometry_lanes"
    assert gate["live_breadth_artifacts_present"] is True
    assert gate["live_execution_allowed"] is False
    assert gate["ready_for_public_live_claim"] is False
    assert gate["ready_for_commit_push_as_live_benchmark"] is False
    assert "branching_transport" in gate["synthetic_only_lanes"]
    assert "thermal_ventilation" in gate["synthetic_only_lanes"]
    assert "optimal_curve_transport" in gate["synthetic_only_lanes"]
    assert "wave_resonance_timing" in gate["synthetic_only_lanes"]
    assert gate["live_breadth_backed_lanes"] == []
    assert "live data source" in gate["commit_push_boundary"]
    assert "frozen input manifest" in gate["commit_push_boundary"]
    assert "baselines" in gate["commit_push_boundary"]
    assert payload["summary"]["ready_for_commit_push_as_live_benchmark"] is False


def test_bridge_exposes_top_live_replay_wiring_cards():
    module = load_module()
    payload = module.build_payload()
    cards = payload["top_live_replay_wiring_cards"]
    lanes = [card["lane"] for card in cards]

    assert payload["summary"]["top_live_replay_wiring_card_count"] == len(cards)
    assert lanes[:4] == [
        "optimal_curve_transport",
        "wave_resonance_timing",
        "branching_transport",
        "thermal_ventilation",
    ]

    by_lane = {card["lane"]: card for card in cards}
    assert by_lane["optimal_curve_transport"]["candidate_family_id"] == "brachistochrone_descent"
    assert by_lane["optimal_curve_transport"]["runner_script"].endswith("geometry_optimal_curve_transport_benchmark.py")
    assert by_lane["wave_resonance_timing"]["candidate_family_id"] == "kuramoto_phase_coupling"
    assert by_lane["wave_resonance_timing"]["runner_script"].endswith("geometry_wave_resonance_timing_benchmark.py")
    assert by_lane["time_series_model_routing"]["runner_script"].endswith("BUILD_LIVE_BREADTH_REPLAY_BRIDGE.py")
    assert all(card["claim_gate"]["ready_for_public_live_claim"] is False for card in cards)
    assert all(card["claim_gate"]["real_dollar_claim"] is False for card in cards)
    assert all("frozen lane-specific live input manifest" in card["unlock_evidence"] for card in cards)


def test_bridge_writes_dashboard_and_markdown_without_authorizing_kraken(tmp_path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "OUT_JSON", tmp_path / "bridge.json")
    monkeypatch.setattr(module, "DASHBOARD_JSON", tmp_path / "dashboard.json")
    monkeypatch.setattr(module, "OUT_MD", tmp_path / "bridge.md")

    payload = module.build_payload()
    module.write_outputs(payload)

    saved = json.loads((tmp_path / "bridge.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "bridge.md").read_text(encoding="utf-8")

    assert saved["summary"]["kraken_live_execution_allowed"] is False
    assert "Kraken live execution allowed: `false`" in markdown
    assert "Latest Branching Benchmark" in markdown
    assert "Latest Thermal Benchmark" in markdown
    assert "Latest Optimal Curve Benchmark" in markdown
    assert "Latest Wave Resonance Benchmark" in markdown
    assert "Generated Champion-Of-Champions" in markdown
    assert "Live Breadth Promotion Gate" in markdown
    assert "Top Live Replay Wiring Cards" in markdown
    assert "brachistochrone_descent" in markdown
    assert "kuramoto_phase_coupling" in markdown
    assert "Ready for commit/push as live benchmark: `false`" in markdown
    assert "not a global, field, customer, safety, or real-dollar claim" in markdown
    assert "Kraken/live execution authorization: `false`" in markdown
    assert "Candidate champion only" in markdown
    assert "live_order_placement" in json.dumps(saved)
