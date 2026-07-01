from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_LIVE_WIRING_MATRIX.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geometry_live_wiring_matrix", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_matrix_covers_registry_lanes_and_fresh_eia():
    module = load_module()
    matrix = module.build_matrix()

    assert matrix["schema"] == "geometry_live_wiring_matrix_v1"
    assert matrix["summary"]["lane_count"] == 12
    assert matrix["summary"]["family_count"] >= 75
    assert matrix["summary"]["eia_status"] == "MEASURED"
    assert matrix["summary"]["eia_rows"] > 0
    assert "EIA" in matrix["summary"]["measured_source_names"]
    assert matrix["summary"]["ready_for_live_geometry_claim"] is False
    assert matrix["summary"]["ready_for_real_dollar_claim"] is False
    assert matrix["summary"]["kraken_live_execution_allowed"] is False

    lanes = {row["lane"] for row in matrix["matrix"]}
    assert lanes == set(module.LANE_SOURCE_PLAN)


def test_critical_infrastructure_lanes_use_eia_but_keep_blockers():
    module = load_module()
    matrix = module.build_matrix()
    by_lane = {row["lane"]: row for row in matrix["matrix"]}

    branching = by_lane["branching_transport"]
    assert branching["proof_value_champion"]["family"] == "crack_propagation_paths"
    assert any(row["source"] == "EIA" and row["measured"] for row in branching["measured_sources"])
    assert any(row["source"] == "NREL" for row in branching["blocked_sources"])
    assert branching["ready_for_live_geometry_claim"] is False
    assert any("no field validation" in item for item in branching["claim_blockers"])

    thermal = by_lane["thermal_ventilation"]
    assert thermal["generated_champion"]["family"] == "thermal_plume_convection"
    assert any(row["source"] == "EIA" and row["measured"] for row in thermal["measured_sources"])
    assert any(row["source"] == "NOAA_NCEI" and row["measured"] for row in thermal["measured_sources"])
    assert any(row["source"] == "NREL" for row in thermal["blocked_sources"])


def test_champions_and_market_lane_are_bounded():
    module = load_module()
    matrix = module.build_matrix()
    by_lane = {row["lane"]: row for row in matrix["matrix"]}

    optimal = by_lane["optimal_curve_transport"]
    assert optimal["generated_champion"]["family"] == "brachistochrone_descent"
    assert optimal["generated_champion"]["score_delta_vs_best_baseline"] > 0
    assert optimal["lane_ready_for_live_replay_build"] is True

    wave = by_lane["wave_resonance_timing"]
    assert wave["generated_champion"]["family"] == "kuramoto_phase_coupling"
    assert any(row["source"] == "EIA" and row["measured"] for row in wave["measured_sources"])

    market = by_lane["market_signal_geometry"]
    assert market["kraken_live_execution_allowed"] is False
    assert market["ready_for_live_geometry_claim"] is False
    assert market["ready_for_real_dollar_claim"] is False
    assert any("paper/replay only" in item for item in market["claim_blockers"])
    assert any(row["source"] == "KRAKEN_PUBLIC" and row["measured"] for row in market["measured_sources"])


def test_markdown_boundaries_do_not_overclaim():
    module = load_module()
    matrix = module.build_matrix()
    rendered = module.render_markdown(matrix)

    assert "Geometry Live Wiring Matrix" in rendered
    assert "EIA status: `MEASURED`" in rendered
    assert "not field validation" in rendered
    assert "not a realized-dollar proof" in rendered
    assert "not permission for live trading" in rendered
    assert "guaranteed funding" not in rendered.lower()
    assert "guaranteed profit" not in rendered.lower()

def test_top_live_replay_source_map_links_generated_champions_to_measured_sources():
    module = load_module()
    matrix = module.build_matrix()
    source_map = matrix["top_live_replay_source_map"]

    assert matrix["summary"]["top_live_replay_source_map_count"] == 5
    assert matrix["summary"]["top_live_replay_ready_count"] >= 4
    assert matrix["summary"]["top_live_replay_measured_source_count"] >= 10
    assert len(source_map) == 5

    by_lane = {row["lane"]: row for row in source_map}
    optimal = by_lane["optimal_curve_transport"]
    assert optimal["candidate_family_id"] == "brachistochrone_descent"
    assert optimal["score_delta_vs_best_baseline"] > 0
    assert {row["source"] for row in optimal["fresh_measured_sources"]} >= {"EIA", "FRED", "KRAKEN_PUBLIC"}
    assert optimal["ready_for_live_geometry_claim"] is False
    assert optimal["ready_for_real_dollar_claim"] is False

    wave = by_lane["wave_resonance_timing"]
    assert wave["candidate_family_id"] == "kuramoto_phase_coupling"
    assert {row["source"] for row in wave["fresh_measured_sources"]} >= {"EIA", "FRED", "NOAA_NCEI", "NASA"}
    assert not any(row["source"] == "NASA" for row in wave["fresh_blocked_sources"])
    assert "requires lane-specific replay" in wave["claim_boundary"]


def test_markdown_exposes_top_live_replay_source_map_without_overclaiming():
    module = load_module()
    matrix = module.build_matrix()
    rendered = module.render_markdown(matrix)

    assert "Top Live Replay Source Map" in rendered
    assert "brachistochrone_descent" in rendered
    assert "kuramoto_phase_coupling" in rendered
    assert "replay-build card, not a live performance claim" in rendered
    assert "Ready for live geometry claim: `false`" in rendered
    assert "Ready for real-dollar claim: `false`" in rendered
