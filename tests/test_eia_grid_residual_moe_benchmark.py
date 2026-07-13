from __future__ import annotations

import copy
import importlib.util
import json
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "eia_grid_residual_moe_benchmark.py"
PROTOCOL_PATH = ROOT / "config" / "eia_grid_residual_moe_protocol_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("eia_residual_moe", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_panel(days: int = 900):
    start = date(2024, 1, 1)
    rows = []
    for index in range(days):
        target = (start + timedelta(days=index)).isoformat()
        actual = 1000.0 + 2.0 * index + 40.0 * ((index % 7) / 6.0)
        official = actual + (12.0 if index % 2 else -8.0)
        rows.extend(
            [
                {
                    "respondent": "TEST",
                    "period": target,
                    "type": "D",
                    "value": actual,
                },
                {
                    "respondent": "TEST",
                    "period": target,
                    "type": "DF",
                    "value": official,
                },
            ]
        )
    return {
        "schema": "eia_grid_validation_panel.v1",
        "requests": [{"respondent": "TEST", "respondent_name": "Test Authority"}],
        "rows": rows,
        "quality": {"row_count": len(rows)},
        "row_chain_sha256": "test",
    }


def synthetic_protocol():
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    protocol["splits"].update(
        {
            "training_start": "2024-04-01",
            "training_end": "2024-12-31",
            "development_start": "2025-01-01",
            "development_end": "2025-06-30",
            "holdout_start": "2025-07-01",
            "holdout_end": "2026-06-18",
        }
    )
    return protocol


def test_protocol_registry_is_locked_to_implementation():
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    assert [row["id"] for row in protocol["candidate_models"]] == module.CANDIDATE_IDS
    assert [row["id"] for row in protocol["baselines"]] == module.BASELINE_IDS
    assert protocol["execution_controls"]["post_holdout_tuning_allowed"] is False


def test_target_actual_does_not_change_target_features():
    module = load_module()
    protocol = synthetic_protocol()
    panel = synthetic_panel()
    original, _ = module.build_feature_rows(panel, protocol)
    target = original[-1]["target_date"]
    altered_panel = copy.deepcopy(panel)
    for row in altered_panel["rows"]:
        if row["period"] == target and row["type"] == "D":
            row["value"] += 50000.0
    altered, _ = module.build_feature_rows(altered_panel, protocol)
    original_row = next(row for row in original if row["target_date"] == target)
    altered_row = next(row for row in altered if row["target_date"] == target)
    assert original_row["features"] == altered_row["features"]
    assert original_row["residual_target_scaled"] != altered_row["residual_target_scaled"]


def test_agreement_gate_abstains_and_correction_clip_holds():
    module = load_module()
    row = {
        "official_mwh": 1000.0,
        "ar_mwh": 900.0,
        "seasonal_scale_mwh": 10.0,
    }
    predictions = module.candidate_prediction_map(
        row,
        {
            "ridge_residual": -10.0,
            "xgboost_residual": 0.0,
            "lightgbm_residual": 10.0,
        },
    )
    gated_value, abstained = predictions["agreement_gated_residual_moe"]
    ridge_value, _ = predictions["ridge_residual"]
    assert gated_value == 1000.0
    assert abstained is True
    assert ridge_value == 975.0


def test_selection_uses_metric_then_error_then_id():
    module = load_module()
    leaderboard = [
        {
            "strategy": "ridge_residual",
            "mean_seasonal_mase_7": 0.5,
            "mean_absolute_error_mwh": 10.0,
        },
        {
            "strategy": "xgboost_residual",
            "mean_seasonal_mase_7": 0.4,
            "mean_absolute_error_mwh": 20.0,
        },
    ]
    assert module.select_candidate(leaderboard)["strategy"] == "xgboost_residual"
