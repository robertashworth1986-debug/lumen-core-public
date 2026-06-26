from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_LIVE_SOURCE_MANIFEST.py"
FRONTIER_SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_LIVE_SYSTEMS_FRONTIER.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def ensure_frontier_exists() -> None:
    frontier = load_module(FRONTIER_SCRIPT, "geometry_live_systems_frontier_for_manifest")
    frontier.main()


def test_manifest_maps_sources_to_core_geometry_lanes():
    ensure_frontier_exists()
    module = load_module(SCRIPT, "geometry_live_source_manifest")
    payload = module.build_payload()
    summary = payload["summary"]
    by_lane = {row["lane"]: row for row in payload["lane_summary"]}

    assert payload["schema"] == "geometry_live_source_manifest_v1"
    assert summary["manifest_row_count"] > 0
    assert summary["ready_for_benchmark_row_count"] > 0
    assert summary["estimated_rows_mapped"] > 0
    assert summary["unique_source_count"] > 0
    assert summary["unique_source_estimated_rows"] > 0
    assert summary["estimated_rows_mapped"] >= summary["unique_source_estimated_rows"]

    assert by_lane["wave_resonance_timing"]["candidate_family"] == "kuramoto_phase_coupling"
    assert by_lane["wave_resonance_timing"]["baseline_family"] == "kalman_filter"
    assert by_lane["thermal_ventilation"]["candidate_family"] == "thermal_plume_convection"
    assert by_lane["branching_transport"]["candidate_family"] == "leaf_veins"
    assert by_lane["optimal_curve_transport"]["candidate_family"] == "brachistochrone_descent"


def test_manifest_rows_are_benchmark_routes_not_claims():
    ensure_frontier_exists()
    module = load_module(SCRIPT, "geometry_live_source_manifest")
    payload = module.build_payload()
    gates = payload["claim_gates"]
    rendered = module.render_markdown(payload)
    dumped = json.dumps(payload).lower()

    assert gates["field_validation_claim_allowed"] is False
    assert gates["real_dollar_savings_claim_allowed"] is False
    assert gates["live_trading_or_autonomous_execution_allowed"] is False
    assert gates["medical_or_addiction_treatment_claim_allowed"] is False
    assert gates["fixed_dollar_delta_sale_claim_allowed"] is False

    assert "This manifest is a benchmark routing map, not a result." in rendered
    assert "may count the same source once per benchmark lane" in rendered
    assert "Medical/addiction-treatment claim allowed: `false`" in rendered
    assert "live_order_placement" not in dumped
    assert "guaranteed" not in dumped
    assert "heroin-like" not in dumped
