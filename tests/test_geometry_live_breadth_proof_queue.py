from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_LIVE_BREADTH_PROOF_QUEUE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geometry_live_breadth_proof_queue", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_queue_ranks_every_family_and_keeps_claim_gates_closed():
    module = load_module()
    queue = module.build_queue()

    assert queue["schema"] == "geometry_live_breadth_proof_queue_v1"
    assert queue["registry_health"]["family_count"] >= 75
    assert queue["registry_health"]["lane_count"] == 12
    assert queue["promotion_gate"]["families_ranked"] >= 75
    assert len(queue["family_queue"]) == queue["promotion_gate"]["families_ranked"]
    assert queue["promotion_gate"]["ready_for_live_geometry_claim"] is False
    assert queue["promotion_gate"]["ready_for_real_dollar_claim"] is False
    assert queue["promotion_gate"]["kraken_live_execution_allowed"] is False
    assert queue["promotion_gate"]["strict_rolling_champion_count"] == 0
    assert queue["promotion_gate"]["triple_source_candidate_count"] >= 3
    assert queue["promotion_gate"]["single_run_candidate_count"] >= 1
    assert "one-off win" in queue["promotion_gate"]["rolling_gate_boundary"]
    live_meter = json.loads(
        (ROOT / "out" / "ops" / "live_proof_value_meter_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert queue["valuation_posture"]["safe_estimated_annual_value_usd"] == live_meter[
        "value_gate"
    ]["allowed_estimated_annual_value_usd"]
    assert queue["valuation_posture"]["safe_estimated_annual_value_usd"] > 0
    assert "not company valuation" in queue["valuation_posture"]["boundary"]


def test_queue_preserves_champion_categories_without_overclaiming():
    module = load_module()
    queue = module.build_queue()
    champions = queue["champions"]
    top_ids = {row["family_id"] for row in queue["family_queue"][:20]}

    assert champions["generated_champion"]["family_id"] == "brachistochrone_descent"
    assert champions["generated_champion"]["status"] == "generated_lane_champion_not_live_claim"
    assert champions["proof_value_champion"]["family_id"] == "crack_propagation_paths"
    assert champions["proof_value_champion"]["status"] == "highest_funding_and_proof_priority_not_performance_winner"
    assert champions["fastest_live_breadth_adapter"]["status"] == "best_next_adapter_candidate_not_live_geometry_claim"
    assert champions["market_paper_champion"]["status"] == "paper_only_no_profit_claim"
    assert champions["strict_rolling_champion"]["status"] == "none"
    assert {row["family_id"] for row in champions["triple_source_candidates"]} >= {
        "brachistochrone_descent",
        "kuramoto_phase_coupling",
        "phase_locked_residual_corrector",
    }
    assert "not interchangeable" in champions["boundary"]
    assert {"brachistochrone_descent", "kuramoto_phase_coupling", "thermal_plume_convection"} & top_ids


def test_each_family_has_lane_contract_assets_and_boundary():
    module = load_module()
    queue = module.build_queue()

    for row in queue["family_queue"]:
        assert row["family_id"]
        assert row["lane"]
        assert row["baselines"], row["family_id"]
        assert row["metrics"], row["family_id"]
        assert row["target_assets"], row["family_id"]
        assert row["target_live_sources"], row["family_id"]
        assert row["next_adapter"], row["family_id"]
        assert row["claim_boundary"], row["family_id"]
        assert row["rolling_gate_status"], row["family_id"]
        assert row["ready_for_real_dollar_claim"] is False
        assert row["kraken_live_execution_allowed"] is False

    market_rows = [row for row in queue["family_queue"] if row["lane"] == "market_signal_geometry"]
    assert market_rows
    for row in market_rows:
        assert row["market_safety"] == "paper_only_no_profit_claim"
        assert "not trading profit" in row["claim_boundary"]


def test_top_next_runs_are_live_breadth_replay_work_orders():
    module = load_module()
    queue = module.build_queue()
    runs = queue["top_next_runs"]
    rendered = module.render_markdown(queue)

    assert len(runs) >= 5
    assert runs[0]["family_id"] == "brachistochrone_descent"
    assert any(run["family_id"] == "kuramoto_phase_coupling" for run in runs)
    assert any(run["lane"] == "thermal_ventilation" for run in runs)
    for run in runs:
        assert run["run_name"].endswith("live_breadth_replay_v1")
        assert run["baselines"]
        assert run["metrics"]
        assert run["rolling_gate_status"]
        assert run["claim_gate"]["ready_for_live_geometry_claim"] is False
        assert run["claim_gate"]["kraken_live_execution_allowed"] is False

    assert "Geometry Live-Breadth Proof Queue" in rendered
    assert "Strict Rolling Gate" in rendered
    assert "Ready for live geometry claim: `false`" in rendered
    assert "guaranteed" not in rendered.lower()
    assert "live_order_placement" not in json.dumps(queue)
