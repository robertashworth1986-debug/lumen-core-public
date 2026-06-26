from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_LIVE_SYSTEMS_FRONTIER.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geometry_live_systems_frontier", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_frontier_ranks_registry_and_detects_local_live_systems():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "geometry_live_systems_frontier_v1"
    assert summary["registered_family_count"] >= 140
    assert summary["ranked_family_count"] == summary["registered_family_count"]
    assert summary["lane_count"] == 12
    assert summary["local_file_inventory_count"] > 0
    assert summary["live_system_count"] > 0
    assert summary["local_estimated_rows"] >= 0

    systems = {row["system"] for row in payload["top_live_systems"]}
    assert "energy_grid" in systems or "market_data" in systems
    assert any(row["candidate_lanes"] for row in payload["top_live_systems"])


def test_frontier_keeps_top_geometries_and_actions_visible():
    module = load_module()
    payload = module.build_payload()
    ranked = {row["family_id"]: row for row in payload["all_family_rankings"]}
    actions = payload["top_10_next_actions"]

    for family_id in [
        "brachistochrone_descent",
        "kuramoto_phase_coupling",
        "thermal_plume_convection",
        "leaf_veins",
    ]:
        assert family_id in ranked
        assert ranked[family_id]["frontier_score"] > 0

    assert len(actions) == 10
    assert actions[0]["family_id"] == "brachistochrone_descent"
    assert actions[1]["family_id"] == "kuramoto_phase_coupling"
    assert any(action["lane"] == "cross_stack" for action in actions)
    assert all("field validation" in action["claim_boundary"] for action in actions)


def test_frontier_claim_gates_close_unsafe_claims():
    module = load_module()
    payload = module.build_payload()
    gates = payload["claim_gates"]
    rendered = module.render_markdown(payload)
    dumped = json.dumps(payload).lower()

    assert gates["field_validation_claim_allowed"] is False
    assert gates["real_dollar_savings_claim_allowed"] is False
    assert gates["fixed_dollar_delta_sale_claim_allowed"] is False
    assert gates["live_trading_or_autonomous_execution_allowed"] is False
    assert gates["medical_or_addiction_treatment_claim_allowed"] is False
    assert gates["mass_email_allowed"] is False

    assert "Medical/addiction-treatment claim allowed: `false`" in rendered
    assert "drug-like effect" in rendered
    assert "fixed-dollar" in rendered
    assert "live_order_placement" not in dumped
    assert "heroin-like" not in dumped
