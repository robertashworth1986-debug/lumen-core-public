from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_CHAMPION_ASSET_MAP.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geometry_champion_asset_map", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_asset_map_ranks_full_registry_and_natural_path_target():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    registry = payload["registry_summary"]

    assert payload["schema"] == "geometry_champion_asset_map_v1"
    assert summary["family_count"] >= 140
    assert summary["ranked_asset_count"] == summary["family_count"]
    assert summary["lane_count"] >= 12
    assert summary["natural_path_family_count"] >= 50
    assert summary["natural_path_target_met"] is True
    assert registry["natural_path_family_count"] == summary["natural_path_family_count"]
    assert registry["benchmark_design_ready_count"] >= 100
    assert registry["missing_natural_logic"] == []
    assert len(summary["asset_chain_sha256"]) == 64


def test_asset_map_preserves_claim_gates_and_safe_boundaries():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert summary["ready_for_live_geometry_claim"] is False
    assert summary["ready_for_real_dollar_claim"] is False
    assert summary["field_validation"] is False
    assert summary["kraken_live_execution_allowed"] is False
    assert summary["mass_email_allowed"] is False

    text = json.dumps(payload).lower()
    assert "field validated" in text
    assert "guaranteed profit" in text
    assert "live_order_placement" not in text
    assert ("api" + "_key") not in text
    assert ("sec" + "ret") not in text

    for row in payload["ranked_assets"][:25]:
        assert row["claim_gate"]["ready_for_real_dollar_claim"] is False
        assert row["claim_gate"]["field_validation"] is False


def test_nearest_valuable_proofs_include_repeat_candidates_and_adapter_targets():
    module = load_module()
    payload = module.build_payload()
    nearest = payload["nearest_valuable_proofs"]
    rolling_ids = {row["family_id"] for row in nearest["rolling_champions"]}
    repeat_ids = {row["family_id"] for row in nearest["closest_repeat_candidates"]}
    adapter_ids = {row["family_id"] for row in nearest["highest_value_adapter_targets"]}
    single_ids = {row["family_id"] for row in nearest["single_run_candidates"]}
    all_ids = {row["family_id"] for row in payload["ranked_assets"]}

    assert "brachistochrone_descent" in rolling_ids
    assert "kuramoto_phase_coupling" in rolling_ids
    assert "leaf_veins" in rolling_ids
    assert "phase_locked_residual_corrector" not in all_ids
    assert "thermal_plume_convection" in rolling_ids or "thermal_plume_convection" in single_ids
    assert "crack_propagation_paths" in adapter_ids

    top_actions = {row["family_id"]: row for row in payload["top_validation_sequence"]}
    assert "brachistochrone_descent" in top_actions
    assert "buyer-authorized pilot scoping" in top_actions["brachistochrone_descent"]["action"]
    assert "kuramoto_phase_coupling" in top_actions
    assert "phase_locked_residual_corrector" not in top_actions


def test_rendered_asset_map_is_useful_and_does_not_overclaim():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)

    assert "Geometry Champion Asset Map" in rendered
    assert "Families ranked: `140`" in rendered
    assert "Families with natural logic:" in rendered
    assert "Ready for real-dollar claim: `false`" in rendered
    assert "Mass email allowed: `false`" in rendered
    assert "`brachistochrone_descent`" in rendered
    assert "`kuramoto_phase_coupling`" in rendered
    assert "`crack_propagation_paths`" in rendered
    assert "fixed-dollar packet value" in rendered
