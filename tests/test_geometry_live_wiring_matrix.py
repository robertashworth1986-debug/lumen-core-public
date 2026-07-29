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

    assert matrix["schema"] == "geometry_live_wiring_matrix_v3"
    assert matrix["summary"]["lane_count"] == 12
    assert matrix["summary"]["family_count"] == 140
    assert matrix["summary"]["implementation_present_count"] == 35
    assert matrix["summary"]["frozen_generated_executed_count"] == 30
    assert matrix["summary"]["source_conditioned_replay_count"] == 4
    assert matrix["summary"]["field_validated_family_count"] == 0
    assert matrix["summary"]["estimated_annual_value_surface_usd"] == 0.0
    assert matrix["summary"]["claimable_annual_value_usd"] == 0.0
    assert (
        matrix["summary"]["context_only_estimated_annual_value_surface_usd"] > 0.0
    )
    assert matrix["summary"]["eia_status"] == "MEASURED"
    assert matrix["summary"]["eia_rows"] > 0
    assert "EIA" in matrix["summary"]["measured_source_names"]
    assert matrix["summary"]["ready_for_live_geometry_claim"] is False
    assert matrix["summary"]["ready_for_real_dollar_claim"] is False
    assert matrix["summary"]["kraken_live_execution_allowed"] is False
    assert matrix["summary"]["lanes_ready_for_direct_source_replay_build"] == 3
    assert (
        matrix["summary"]["lanes_ready_for_source_conditioned_simulation_build"]
        >= 4
    )
    assert matrix["summary"]["qualified_direct_source_links"] >= 10

    lanes = {row["lane"] for row in matrix["matrix"]}
    assert lanes == set(module.LANE_SOURCE_PLAN)

    by_lane = {row["lane"]: row for row in matrix["matrix"]}
    mission = by_lane["mission_network_routing"]
    assert mission["implementation_present_count"] == 4
    assert mission["frozen_generated_executed_count"] == 4
    assert mission["lane_ready_for_live_replay_build"] is False
    assert mission["lane_ready_for_direct_source_replay_build"] is False
    assert mission["lane_ready_for_source_conditioned_simulation_build"] is True
    assert not mission["direct_measured_replay_sources"]
    assert {
        row["source"]
        for row in mission["source_conditioned_synthetic_stress_sources"]
    } == {"GRANTS_GOV"}
    assert mission["measured_sources"]
    assert any(
        "source-conditioned replay" in item for item in mission["claim_blockers"]
    )


def test_critical_infrastructure_lanes_use_eia_but_keep_blockers():
    module = load_module()
    matrix = module.build_matrix()
    by_lane = {row["lane"]: row for row in matrix["matrix"]}

    branching = by_lane["branching_transport"]
    assert branching["proof_value_champion"]["family"] == "crack_propagation_paths"
    assert any(row["source"] == "EIA" and row["measured"] for row in branching["measured_sources"])
    assert any(row["source"] == "NREL" for row in branching["blocked_sources"])
    assert branching["ready_for_live_geometry_claim"] is False
    assert branching["lane_ready_for_direct_source_replay_build"] is False
    assert branching["lane_ready_for_source_conditioned_simulation_build"] is True
    assert {
        row["source"]
        for row in branching["source_conditioned_synthetic_stress_sources"]
    } >= {"EIA", "NWS_PUBLIC", "OPEN_METEO_PUBLIC"}
    assert any("no field validation" in item for item in branching["claim_blockers"])

    thermal = by_lane["thermal_ventilation"]
    assert thermal["generated_champion"]["family"] == "thermal_plume_convection"
    assert any(row["source"] == "EIA" and row["measured"] for row in thermal["measured_sources"])
    assert any(row["source"] == "NOAA_NCEI" and row["measured"] for row in thermal["measured_sources"])
    assert any(row["source"] == "NREL" for row in thermal["blocked_sources"])
    assert thermal["lane_ready_for_direct_source_replay_build"] is False
    assert thermal["lane_ready_for_source_conditioned_simulation_build"] is True


def test_champions_and_market_lane_are_bounded():
    module = load_module()
    matrix = module.build_matrix()
    by_lane = {row["lane"]: row for row in matrix["matrix"]}

    optimal = by_lane["optimal_curve_transport"]
    assert optimal["generated_champion"]["family"] == "brachistochrone_descent"
    assert optimal["generated_champion"]["score_delta_vs_best_baseline"] > 0
    assert optimal["lane_ready_for_live_replay_build"] is False
    assert optimal["lane_ready_for_direct_source_replay_build"] is False
    assert not optimal["direct_measured_replay_sources"]

    wave = by_lane["wave_resonance_timing"]
    assert wave["generated_champion"]["family"] == "kuramoto_phase_coupling"
    assert any(row["source"] == "EIA" and row["measured"] for row in wave["measured_sources"])
    assert any(
        row["source"] == "EIA_GRID_VALIDATION" and row["measured"]
        for row in wave["measured_sources"]
    )
    assert wave["lane_ready_for_direct_source_replay_build"] is True
    assert {
        row["source"] for row in wave["direct_measured_replay_sources"]
    } == {"EIA_GRID_VALIDATION"}

    market = by_lane["market_signal_geometry"]
    assert market["implementation_present_count"] == 4
    assert market["lane_ready_for_direct_source_replay_build"] is True
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
    assert matrix["summary"]["top_live_replay_ready_count"] == 2
    assert matrix["summary"]["top_live_replay_measured_source_count"] >= 10
    assert len(source_map) == 5

    by_lane = {row["lane"]: row for row in source_map}
    optimal = by_lane["optimal_curve_transport"]
    assert optimal["candidate_family_id"] == "brachistochrone_descent"
    assert optimal["score_delta_vs_best_baseline"] > 0
    assert {row["source"] for row in optimal["fresh_measured_sources"]} >= {"EIA", "FRED", "KRAKEN_PUBLIC"}
    assert optimal["direct_measured_replay_sources"] == []
    assert optimal["lane_ready_for_direct_source_replay_build"] is False
    assert optimal["ready_for_live_geometry_claim"] is False
    assert optimal["ready_for_real_dollar_claim"] is False

    wave = by_lane["wave_resonance_timing"]
    assert wave["candidate_family_id"] == "kuramoto_phase_coupling"
    assert {row["source"] for row in wave["fresh_measured_sources"]} >= {"EIA", "FRED", "NOAA_NCEI", "NASA"}
    assert {
        row["source"] for row in wave["direct_measured_replay_sources"]
    } == {"EIA_GRID_VALIDATION"}
    assert not any(row["source"] == "NASA" for row in wave["fresh_blocked_sources"])
    assert "Direct measured replay" in wave["claim_boundary"]


def test_markdown_exposes_top_live_replay_source_map_without_overclaiming():
    module = load_module()
    matrix = module.build_matrix()
    rendered = module.render_markdown(matrix)

    assert "Top Live Replay Source Map" in rendered
    assert "brachistochrone_descent" in rendered
    assert "kuramoto_phase_coupling" in rendered
    assert "Neither is a live performance claim" in rendered
    assert "Ready for live geometry claim: `false`" in rendered
    assert "Ready for real-dollar claim: `false`" in rendered


def test_source_specific_baselines_require_semantic_compatibility():
    module = load_module()
    matrix = module.build_matrix()
    by_lane = {row["lane"]: row for row in matrix["matrix"]}

    time_series = by_lane["time_series_model_routing"]
    direct = {
        row["source"]: row for row in time_series["direct_measured_replay_sources"]
    }
    assert direct["FRED"]["source_specific_baselines"] == module.TIME_SERIES_BASELINES
    assert len(direct["FRED"]["source_specific_baselines"]) == 8
    assert direct["FRED"]["source_specific_baseline_parameters"][
        "series_overrides"
    ]["CPIAUCSL"]["seasonal_period"] == 12
    assert direct["KRAKEN_PUBLIC"]["source_specific_baseline_parameters"][
        "seasonal_period"
    ] == 24
    assert (
        direct["EIA_GRID_VALIDATION"]["direct_performance_input_allowed"] is True
    )
    assert direct["EIA_GRID_VALIDATION"]["measurement_shape"]["pass"] is True
    assert (
        direct["EIA_GRID_VALIDATION"]["measurement_shape"][
            "longest_series_length"
        ]
        >= 365
    )
    eia_context = next(
        row
        for row in time_series["context_only_measured_sources"]
        if row["source"] == "EIA"
    )
    assert eia_context["direct_performance_input_allowed"] is False
    assert time_series["lane_ready_for_direct_source_replay_build"] is True

    multi_agent = by_lane["multi_agent_coordination"]
    assert multi_agent["lane_ready_for_direct_source_replay_build"] is False
    assert multi_agent["lane_ready_for_source_conditioned_simulation_build"] is True
    assert all(
        row["source_conditioning_only"]
        for row in multi_agent[
            "source_conditioned_synthetic_stress_sources"
        ]
    )
    assert any(
        "per-agent trajectories" in item
        for item in multi_agent["missing_direct_observations"]
    )
