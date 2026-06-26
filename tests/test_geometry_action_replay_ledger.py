from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_ACTION_REPLAY_LEDGER.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geometry_action_replay_ledger", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_action_replay_ledger_builds_from_latest_replays():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "geometry_action_replay_ledger_v1"
    assert summary["lane_count"] >= 4
    assert summary["positive_gate_count"] >= 4
    assert summary["total_validation_scenarios"] >= 400
    assert summary["best_current_family"]
    assert len(summary["ledger_chain_sha256"]) == 64

    assert summary["field_validation_claim_allowed"] is False
    assert summary["medical_validation_claim_allowed"] is False
    assert summary["real_dollar_savings_claim_allowed"] is False
    assert summary["fixed_dollar_delta_sale_claim_allowed"] is False
    assert summary["live_trading_or_autonomous_execution_allowed"] is False


def test_expected_lane_winners_are_preserved_with_boundaries():
    module = load_module()
    payload = module.build_payload()
    rows = {row["lane"]: row for row in payload["replay_rows"]}

    expected = {
        "optimal_curve_transport": "brachistochrone_descent",
        "wave_resonance_timing": "kuramoto_phase_coupling",
        "thermal_ventilation": "thermal_plume_convection",
        "branching_transport": "leaf_veins",
    }
    for lane, family_id in expected.items():
        assert lane in rows
        row = rows[lane]
        assert row["best_geometry"] == family_id
        assert row["gate"] == "candidate_geometry_beats_best_baseline"
        assert row["score_delta_vs_best_baseline"] > 0
        assert row["scenario_count"] >= 100
        assert len(row["row_sha256"]) == 64
        assert row["claim_gates"]["field_validation_claim_allowed"] is False
        assert row["claim_gates"]["medical_validation_claim_allowed"] is False
        assert row["claim_gates"]["real_dollar_savings_claim_allowed"] is False
        assert row["claim_gates"]["live_trading_or_autonomous_execution_allowed"] is False


def test_markdown_and_payload_do_not_overclaim():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    serialized = json.dumps(payload)

    assert "Geometry Action Replay Ledger" in rendered
    assert "Medical validation claim allowed: `false`" in rendered
    assert "not medical, addiction-treatment, field, safety, trading, or real-dollar proof" in rendered

    forbidden = [
        "heroin-like",
        "opioid replacement",
        "medical validation claim allowed: `true`",
        "field validation claim allowed: `true`",
        "guaranteed profit",
        "live_order_placement",
    ]
    for term in forbidden:
        assert term not in serialized.lower()
        assert term not in rendered.lower()
