from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_TOP_GEOMETRY_LIVE_REPLAY_RESULTS.py"


def load_module():
    spec = importlib.util.spec_from_file_location("top_geometry_live_replay_results", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_top_geometry_live_replay_runs_four_adapters_and_keeps_claim_gate_closed():
    module = load_module()
    payload = module.build_results()

    assert payload["schema"] == "top_geometry_live_replay_results_v1"
    assert payload["summary"]["replay_card_count"] == 5
    assert payload["summary"]["adapter_replay_count"] == 4
    assert payload["summary"]["source_context_only_count"] == 1
    assert payload["summary"]["candidate_beats_named_baseline_count"] == 3
    assert payload["summary"]["total_live_context_rows_evaluated"] > 100
    assert payload["summary"]["unique_snapshot_sha256_count"] >= 10
    assert payload["summary"]["strict_rolling_champion_count"] == 0
    assert payload["summary"]["triple_source_candidate_replay_count"] == 2
    assert payload["summary"]["single_run_candidate_replay_count"] == 1
    assert payload["summary"]["ready_for_live_geometry_claim"] is False
    assert payload["summary"]["ready_for_real_dollar_claim"] is False
    assert payload["summary"]["field_validation"] is False
    assert payload["summary"]["kraken_live_execution_allowed"] is False
    assert payload["inputs"]["geometry_live_breadth_proof_queue"].endswith(
        "geometry_live_breadth_proof_queue_latest.json"
    )


def test_top_geometry_live_replay_records_candidate_deltas_and_best_geometry():
    module = load_module()
    payload = module.build_results()
    by_lane = {card["lane"]: card for card in payload["replay_cards"]}

    optimal = by_lane["optimal_curve_transport"]
    assert optimal["candidate_family_id"] == "brachistochrone_descent"
    assert optimal["named_baseline"] == "minimum_jerk_curve"
    assert optimal["candidate_beats_named_baseline"] is True
    assert optimal["candidate_score_delta_vs_named_baseline"] > 0
    assert optimal["best_geometry_family_id"] == "brachistochrone_descent"
    assert optimal["rolling_gate_status"] == "triple_source_candidate"
    assert optimal["evidence_status"] == "triple_source_live_candidate_needs_repeat_run"
    assert optimal["top_next_run_rank"] == 1

    wave = by_lane["wave_resonance_timing"]
    assert wave["candidate_family_id"] == "kuramoto_phase_coupling"
    assert wave["candidate_beats_named_baseline"] is True
    assert wave["best_geometry_family_id"] == "kuramoto_phase_coupling"
    assert wave["rolling_gate_status"] == "triple_source_candidate"
    assert wave["top_next_run_rank"] == 2

    branching = by_lane["branching_transport"]
    assert branching["candidate_family_id"] == "leaf_veins"
    assert branching["candidate_beats_named_baseline"] is False
    assert branching["candidate_score_delta_vs_named_baseline"] < 0
    assert branching["best_geometry_family_id"]
    assert branching["rolling_gate_status"] == "not_promoted"

    thermal = by_lane["thermal_ventilation"]
    assert thermal["candidate_family_id"] == "thermal_plume_convection"
    assert thermal["candidate_beats_named_baseline"] is True
    assert thermal["best_geometry_family_id"] == "thermal_plume_convection"
    assert thermal["rolling_gate_status"] == "single_run_candidate"
    assert thermal["top_next_run_rank"] == 3

    time_series = by_lane["time_series_model_routing"]
    assert time_series["adapter_status"] == "source_context_only_no_lane_adapter"
    assert time_series["candidate_score_delta_vs_named_baseline"] is None
    assert time_series["rolling_gate_status"] == "not_promoted"


def test_top_geometry_live_replay_markdown_is_reviewer_safe():
    module = load_module()
    payload = module.build_results()
    rendered = module.render_markdown(payload)

    assert "Top Geometry Live Replay Results" in rendered
    assert "Live-context replay only" in rendered
    assert "not field validation" in rendered
    assert "not a real-dollar claim" in rendered
    assert "not permission for live trading" in rendered
    assert "Triple-source candidate replays: `2`" in rendered
    assert "`triple_source_candidate`" in rendered
    assert "`single_run_candidate`" in rendered
    assert "Ready for live geometry claim: `false`" in rendered
    assert "Ready for real-dollar claim: `false`" in rendered
    assert "guaranteed funding" not in rendered.lower()
    assert "guaranteed profit" not in rendered.lower()
