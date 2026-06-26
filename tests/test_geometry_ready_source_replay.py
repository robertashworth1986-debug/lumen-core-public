from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_READY_SOURCE_REPLAY.py"
FRONTIER_SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_LIVE_SYSTEMS_FRONTIER.py"
MANIFEST_SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_LIVE_SOURCE_MANIFEST.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def ensure_inputs_exist() -> None:
    frontier = load_module(FRONTIER_SCRIPT, "geometry_live_systems_frontier_for_ready_replay_test")
    frontier.main()
    manifest = load_module(MANIFEST_SCRIPT, "geometry_live_source_manifest_for_ready_replay_test")
    manifest.main()


def test_ready_source_replay_runs_core_geometry_lanes_and_keeps_gates_closed():
    ensure_inputs_exist()
    module = load_module(SCRIPT, "geometry_ready_source_replay")
    payload = module.build_payload(max_routes=6, sample_limit=750)
    summary = payload["summary"]
    lanes = {row["lane"] for row in payload["ready_source_replay_results"]}
    gates = payload["claim_gates"]

    assert payload["schema"] == "geometry_ready_source_replay_v1"
    assert summary["routes_replayed"] >= 4
    assert summary["lanes_replayed"] >= 4
    assert summary["source_files_replayed"] >= 3
    assert summary["estimated_rows_replayed"] > 0
    assert summary["numeric_samples_read"] > 0
    assert summary["candidate_win_count"] >= 1
    assert len(summary["replay_chain_sha256"]) == 64

    assert "optimal_curve_transport" in lanes
    assert "wave_resonance_timing" in lanes
    assert "thermal_ventilation" in lanes
    assert "branching_transport" in lanes

    assert gates["field_validation_claim_allowed"] is False
    assert gates["real_dollar_savings_claim_allowed"] is False
    assert gates["fixed_dollar_delta_sale_claim_allowed"] is False
    assert gates["live_trading_or_autonomous_execution_allowed"] is False
    assert gates["medical_or_addiction_treatment_claim_allowed"] is False
    assert gates["buyer_authorized_field_pilot_required"] is True


def test_ready_source_replay_has_candidate_baseline_deltas_and_safe_markdown():
    ensure_inputs_exist()
    module = load_module(SCRIPT, "geometry_ready_source_replay")
    payload = module.build_payload(max_routes=6, sample_limit=750)
    rendered = module.render_markdown(payload)
    dumped = json.dumps(payload).lower()

    by_lane = {row["lane"]: row for row in payload["lane_scoreboard"]}
    assert by_lane["wave_resonance_timing"]["candidate_family"] == "kuramoto_phase_coupling"
    assert by_lane["wave_resonance_timing"]["baseline_family"] == "kalman_filter"
    assert by_lane["optimal_curve_transport"]["candidate_family"] == "brachistochrone_descent"
    assert by_lane["thermal_ventilation"]["candidate_family"] == "thermal_plume_convection"
    assert by_lane["branching_transport"]["candidate_family"] == "leaf_veins"

    for result in payload["ready_source_replay_results"]:
        assert result["adapter_status"] == "live_context_replay_ran"
        assert result["candidate_delta_vs_named_baseline"] is not None
        assert len(result["route_sha256"]) == 64
        assert result["claim_gates"]["real_dollar_savings_claim_allowed"] is False

    assert "This is source-conditioned replay evidence, not field validation." in rendered
    assert "Next 10 Actions" in rendered
    assert "guaranteed" not in dumped
    assert "live_order_placement" not in dumped
    assert "heroin-like" not in dumped
