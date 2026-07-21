from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
import os
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "eia_grid_wave_champion_benchmark.py"
PROTOCOL = ROOT / "config" / "eia_grid_wave_champion_protocol_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("eia_grid_wave_champion_benchmark", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def synthetic_protocol(module):
    protocol = module.load_protocol()
    protocol = copy.deepcopy(protocol)
    protocol["panel"]["balancing_authorities"] = [
        {"respondent": "TEST", "name": "Test Authority", "timezone": "Central"}
    ]
    protocol["panel"]["start_date"] = "2024-01-01"
    protocol["panel"]["end_date"] = "2024-10-31"
    protocol["split"].update(
        {
            "minimum_history_days": 60,
            "development_start": "2024-03-15",
            "development_end": "2024-07-31",
            "holdout_start": "2024-08-01",
            "holdout_end": "2024-10-31",
            "development_origin_stride_days": 14,
            "holdout_origin_stride_days": 7,
        }
    )
    return protocol


def synthetic_panel(module, protocol, *, holdout_multiplier: float = 1.0):
    rows = []
    start = date.fromisoformat(protocol["panel"]["start_date"])
    end = date.fromisoformat(protocol["panel"]["end_date"])
    holdout_start = date.fromisoformat(protocol["split"]["holdout_start"])
    current = start
    index = 0
    while current <= end:
        value = 1000.0 + 80.0 * math.sin(2.0 * math.pi * index / 7.0) + 0.5 * index
        if current >= holdout_start:
            value *= holdout_multiplier
        for kind, forecast in (("D", value), ("DF", value * 1.01)):
            rows.append(
                {
                    "period": current.isoformat(),
                    "respondent": "TEST",
                    "respondent_name": "Test Authority",
                    "timezone": "Central",
                    "type": kind,
                    "type_name": "Demand" if kind == "D" else "Day-ahead demand forecast",
                    "value": forecast,
                    "value_units": "megawatthours",
                }
            )
        current += timedelta(days=1)
        index += 1
    return {
        "schema": "eia_grid_validation_panel.v1",
        "protocol": {
            "path": "config/eia_grid_wave_champion_protocol_v1.json",
            "sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
            "frozen_commit": "test",
            "protocol_id": protocol["protocol_id"],
        },
        "quality": {"row_count": len(rows)},
        "row_chain_sha256": module.canonical_sha256(rows),
        "rows": rows,
    }


def test_protocol_was_frozen_before_the_benchmark_and_declares_strong_baselines():
    module = load_module()
    protocol = module.load_protocol()

    assert protocol["schema"] == "eia_grid_wave_champion_protocol.v1"
    assert protocol["split"]["development_end"] < protocol["split"]["holdout_start"]
    assert len(protocol["panel"]["balancing_authorities"]) == 8
    assert {row["id"] for row in protocol["baselines"]} == {
        "eia_day_ahead_forecast",
        "seasonal_naive_7",
        "naive_last",
        "kalman_local_linear_trend",
        "autoregressive_ridge_p14",
        "fft_extrapolation_top5",
    }
    assert "kuramoto_phase_coupling" in {row["id"] for row in protocol["wave_candidates"]}
    assert protocol["selection"]["no_post_selection_substitution"] is True
    assert module.protocol_commit() == "5b4ddbaef438e8f1d7c7d294a451d59280175b35"


def test_actual_forecasters_are_finite_and_development_selection_ignores_holdout_values():
    module = load_module()
    history = [1000.0 + 100.0 * math.sin(2.0 * math.pi * index / 7.0) for index in range(180)]
    forecasts = {
        strategy: float(forecaster(history))
        for strategy, forecaster in module.ALGORITHM_FORECASTERS.items()
    }

    assert all(math.isfinite(value) for value in forecasts.values())
    assert forecasts["kuramoto_phase_coupling"] != forecasts["lissajous_phase_paths"]

    protocol = synthetic_protocol(module)
    original_rows, _ = module.evaluate_panel(synthetic_panel(module, protocol), protocol)
    altered_rows, _ = module.evaluate_panel(
        synthetic_panel(module, protocol, holdout_multiplier=100.0), protocol
    )
    original_selection = module.select_candidate(module.aggregate_strategy(original_rows, "development"))
    altered_selection = module.select_candidate(module.aggregate_strategy(altered_rows, "development"))

    assert original_selection["strategy"] == altered_selection["strategy"]
    assert original_selection["mean_seasonal_mase_7"] == altered_selection["mean_seasonal_mase_7"]


def test_global_comparison_gate_requires_every_predeclared_baseline():
    module = load_module()
    protocol = module.load_protocol()
    selected = "lissajous_phase_paths"
    rows = []
    for authority_index, authority in enumerate(protocol["panel"]["balancing_authorities"]):
        for month in range(1, 7):
            target = f"2026-{month:02d}-15"
            rows.append(
                {
                    "split": "holdout",
                    "respondent": authority["respondent"],
                    "target_date": target,
                    "strategy": selected,
                    "seasonal_mase_7": 0.50 + authority_index * 0.001,
                }
            )
            for baseline in protocol["baselines"]:
                rows.append(
                    {
                        "split": "holdout",
                        "respondent": authority["respondent"],
                        "target_date": target,
                        "strategy": baseline["id"],
                        "seasonal_mase_7": 1.00 + authority_index * 0.001,
                    }
                )

    comparisons = module.build_comparisons(rows, selected, protocol)

    assert len(comparisons) == 6
    assert all(row["paired_authority_month_count"] == 48 for row in comparisons)
    assert all(row["authority_mean_win_count"] == 8 for row in comparisons)
    assert all(row["passes_comparison_gate"] is True for row in comparisons)
    assert module.exact_two_sided_sign_test([1.0] * 5) == 0.0625


def test_frozen_eia_panel_and_result_manifests_are_hash_valid_and_claim_safe():
    module = load_module()
    panel = module.load_panel()
    report = json.loads(module.OUT_JSON.read_text(encoding="utf-8"))
    manifest = json.loads(module.OUT_MANIFEST.read_text(encoding="utf-8"))

    assert panel["quality"]["authority_count"] == 8
    assert panel["quality"]["row_count"] > 14000
    assert panel["quality"]["duplicate_conflict_count"] == 0
    assert panel["source"]["credential_serialized"] is False
    rendered_panel = json.dumps(panel)
    configured_key = os.environ.get("EIA_API_KEY") or os.environ.get("EIA_API_KEY_PREMIUM")
    if configured_key:
        assert configured_key not in rendered_panel

    assert report["selection"]["holdout_used_for_selection"] is False
    assert report["selection"]["post_selection_substitution"] is False
    assert report["promotion_gate"]["external_replication_complete"] is False
    assert report["promotion_gate"]["field_validation_complete"] is False
    assert report["promotion_gate"]["realized_savings_claim_allowed"] is False
    assert report["promotion_gate"]["unbeatable_claim_allowed"] is False
    assert report["promotion_gate"]["trading_execution_allowed"] is False
    assert len(report["baseline_comparisons"]) == 6

    assert manifest["schema"] == "eia_grid_wave_champion_manifest.v1"
    for artifact in manifest["artifacts"]:
        path = ROOT / artifact["path"]
        assert path.exists()
        assert path.stat().st_size == artifact["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
    assert manifest["artifact_chain_sha256"] == module.canonical_sha256(manifest["artifacts"])
