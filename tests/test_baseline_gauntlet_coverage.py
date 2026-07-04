from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_baseline_gauntlet_coverage_reports_current_locked_replay_truth() -> None:
    script = ROOT / "code" / "ops" / "BUILD_BASELINE_GAUNTLET_COVERAGE.py"
    subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True, capture_output=True, text=True, timeout=120)

    payload_path = ROOT / "dashboard" / "data" / "baseline_gauntlet_coverage.json"
    doc_path = ROOT / "docs" / "BASELINE_GAUNTLET_COVERAGE_2026-07-03.md"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    rows = {row["id"]: row for row in payload["baseline_rows"]}

    assert payload["schema"] == "baseline_gauntlet_coverage_v1"
    assert payload["summary"]["requested_baselines"] == 29
    assert payload["summary"]["executed_in_locked_replay"] >= 15
    assert payload["summary"]["replay_proxy_ready_from_metric_audit"] >= 2
    assert payload["summary"]["locked_replay_baseline_comparisons"] >= 1900
    assert payload["summary"]["field_validation_claim_allowed"] is False
    assert payload["summary"]["real_dollar_savings_claim_allowed"] is False

    for baseline_id in [
        "holt_winters_ets",
        "extended_kalman_filter",
        "unscented_kalman_filter",
        "particle_filter",
        "gaussian_process_regression",
        "xgboost",
        "lightgbm",
        "random_forest_regression",
    ]:
        assert rows[baseline_id]["status"] == "EXECUTED_IN_LOCKED_REPLAY"
        assert rows[baseline_id]["baseline_comparison_count"] > 0

    for baseline_id in ["model_predictive_control", "dijkstra", "a_star"]:
        assert rows[baseline_id]["status"] == "REGISTERED_BASELINE_NOT_ADAPTER_EXECUTED"
        assert rows[baseline_id]["baseline_comparison_count"] == 0

    for baseline_id in [
        "lstm",
        "tcn",
        "small_transformer_forecast",
        "dc_power_flow",
        "opf",
        "ieee_39_bus",
        "ieee_118_bus",
        "ieee_300_bus",
    ]:
        assert rows[baseline_id]["status"] == "IMPLEMENTATION_NEEDED"

    assert rows["kuramoto_order_parameter"]["status"] == "REPLAY_PROXY_READY_FROM_ACCEPTED_METRIC_AUDIT"
    assert rows["kuramoto_phase_bound_stress"]["status"] == "REPLAY_PROXY_READY_FROM_ACCEPTED_METRIC_AUDIT"
    assert rows["kuramoto_critical_coupling"]["status"] == "EXTERNAL_TOPOLOGY_REQUIRED"

    rendered = doc_path.read_text(encoding="utf-8")
    assert "MPC, Dijkstra, and A* are registered" in rendered
    assert "accepted-metric replay proxies" in rendered
    assert "does not authorize field-validation" in rendered
