from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_CHAMPION_METRIC_BATTERY.py"


def load_module():
    spec = importlib.util.spec_from_file_location("champion_metric_battery", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_metric_battery_consolidates_champion_without_overclaiming():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "champion_metric_battery_v1"
    assert summary["champion_family"] == "kuramoto_phase_coupling"
    assert summary["named_baseline"] == "kalman_filter"
    assert summary["holdout_count"] >= 20
    assert summary["holdout_wins"] >= 20
    assert summary["estimated_rows_replayed"] >= 1_000_000
    assert summary["metric_category_count"] >= 10
    assert summary["metric_pass_count"] >= 3
    assert summary["metric_ready_to_run_count"] >= 2
    assert summary["metric_blocked_external_count"] >= 3
    assert summary["field_validation_claim_allowed"] is False
    assert summary["real_dollar_savings_claim_allowed"] is False
    assert summary["fixed_frozen_delta_price_claim_allowed"] is False
    assert summary["live_trading_or_autonomous_execution_allowed"] is False
    assert len(payload["metric_battery_sha256"]) == 64


def test_metric_battery_names_real_test_lanes_and_blockers():
    module = load_module()
    payload = module.build_payload()
    lanes = {row["category_id"]: row for row in payload["metric_categories"]}

    assert lanes["source_conditioned_replay"]["status"] == "PASS"
    assert lanes["best_same_run_baseline"]["status"] == "PASS"
    assert lanes["phase_resonance_proxy"]["status"] == "PASS"
    assert lanes["residual_calibration"]["status"] == "READY_TO_RUN_OR_EXPAND"
    assert lanes["source_generalization"]["status"] == "READY_TO_RUN_OR_EXPAND"
    assert lanes["hardware_grid_rf_pll"]["status"].startswith("BLOCKED")
    assert lanes["economic_conversion"]["status"].startswith("BLOCKED")
    assert lanes["buyer_authorized_field_replay"]["status"].startswith("BLOCKED")
    assert "external owner" in lanes["economic_conversion"]["next_action"].lower()
    assert "held-out dataset" in lanes["hardware_grid_rf_pll"]["next_action"].lower()


def test_metric_battery_recommends_high_value_source_families():
    module = load_module()
    payload = module.build_payload()
    families = {row["family"] for row in payload["best_next_source_families"]}

    assert "ISO/RTO grid operations" in families
    assert "utility outage and reliability" in families
    assert "energy market and plant operations" in families
    assert "weather and environmental operations" in families
    assert "maritime and critical infrastructure movement" in families


def test_metric_battery_markdown_is_reviewer_safe():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    dumped = json.dumps(payload).lower()

    assert "Champion Metric Battery" in rendered
    assert "Battery Status" in rendered
    assert "Field-validation claim allowed: `false`" in rendered
    assert "Real-dollar savings claim allowed: `false`" in rendered
    assert "realized savings" in dumped
    assert "guaranteed profit" not in dumped
    assert "guaranteed grant" not in dumped
    assert "money printer" not in dumped
