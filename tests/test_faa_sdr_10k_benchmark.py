from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "RUN_FAA_SDR_10K_BENCHMARK.py"


def load_module():
    spec = importlib.util.spec_from_file_location("faa_sdr_10k_benchmark", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_deterministic_holdout_selection_is_stable_and_without_replacement():
    module = load_module()
    keys = [f"KEY-{index}" for index in range(20)]

    first = module.deterministic_holdout_indices(keys, target=10, protocol_id="fixture")
    second = module.deterministic_holdout_indices(keys, target=10, protocol_id="fixture")

    assert first == second
    assert len(first) == 10
    assert len(set(first)) == 10


def test_router_plan_uses_group_champion_and_global_fallback():
    module = load_module()
    y = np.array([0, 0, 1, 1, 0, 1])
    makes = pd.Series(["A", "A", "A", "A", "B", "B"])
    model_a = np.array(
        [[0.9, 0.1], [0.8, 0.2], [0.2, 0.8], [0.1, 0.9], [0.7, 0.3], [0.7, 0.3]]
    )
    model_b = np.array(
        [[0.6, 0.4], [0.4, 0.6], [0.6, 0.4], [0.4, 0.6], [0.8, 0.2], [0.2, 0.8]]
    )

    plan = module.router_plan(y, makes, {"model_a": model_a, "model_b": model_b}, minimum_rows=3)
    routed, chosen = module.apply_router(makes, {"model_a": model_a, "model_b": model_b}, plan)

    assert plan["routes"]["A"] == "model_a"
    assert chosen[:4] == ["model_a"] * 4
    assert routed.shape == (6, 2)


def test_paired_bootstrap_detects_identical_predictions_and_holm_is_monotone():
    module = load_module()
    y = np.array([0, 0, 1, 1, 2, 2])
    prediction = np.array([0, 1, 1, 1, 2, 0])

    result = module.paired_macro_f1_bootstrap(y, prediction, prediction, resamples=250, seed=7)
    adjusted = module.holm_adjust({"a": 0.01, "b": 0.03, "c": 0.20})

    assert result["observed_delta"] == 0.0
    assert result["ci95"] == [0.0, 0.0]
    assert adjusted["a"] <= adjusted["b"] <= adjusted["c"]


def test_classification_metrics_are_bounded():
    module = load_module()
    y = np.array([0, 1, 0, 1])
    probabilities = np.array([[0.9, 0.1], [0.1, 0.9], [0.6, 0.4], [0.4, 0.6]])

    metrics = module.classification_metrics(y, probabilities)

    assert metrics["rows"] == 4
    assert metrics["macro_f1"] == 1.0
    assert 0.0 <= metrics["expected_calibration_error"] <= 1.0


def test_prediction_receipt_gzip_is_deterministic(tmp_path):
    module = load_module()
    module.BENCHMARK_VAULT_DIR = tmp_path
    holdout = pd.DataFrame(
        {
            "report_key": ["KEY-1", "KEY-2"],
            "target": ["21", "27"],
            "AircraftMake": ["BOEING", "AIRBUS"],
            "EngineMake": ["RROYCE", "CFM"],
            "EngineModel": ["TRENT", "CFM56"],
        }
    )
    encoder = module.LabelEncoder().fit(["21", "27"])
    probabilities = {"baseline": np.array([[0.8, 0.2], [0.1, 0.9]])}

    first = module.write_prediction_receipt(holdout, encoder, probabilities, ["baseline", "baseline"])
    second = module.write_prediction_receipt(holdout, encoder, probabilities, ["baseline", "baseline"])

    assert first["sha256"] == second["sha256"]
    assert first["bytes"] == second["bytes"]
