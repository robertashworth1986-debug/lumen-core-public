"""Preregistered residual mixture-of-experts benchmark on frozen EIA data.

The benchmark keeps EIA's official day-ahead forecast as the incumbent and
tests whether fixed residual learners, conservative ensembles, or an abstaining
router can improve it on an untouched holdout. It produces public-data
software evidence in MWh, not field, savings, reliability, or trading proof.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import subprocess
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

import numpy as np
from lightgbm import LGBMRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "config" / "eia_grid_residual_moe_protocol_v1.json"
PROTOCOL_PROVENANCE_PATH = ROOT / "config" / "reviewer_protocol_provenance_v1.json"
OUT_DIR = ROOT / "out" / "eia_grid_residual_moe"
OUT_JSON = OUT_DIR / "eia_grid_residual_moe_benchmark_latest.json"
OUT_ROWS = OUT_DIR / "eia_grid_residual_moe_rows_latest.csv"
OUT_MANIFEST = OUT_DIR / "eia_grid_residual_moe_manifest_latest.json"
DASHBOARD_JSON = ROOT / "dashboard" / "data" / "eia_grid_residual_moe_benchmark.json"
OUT_MD = ROOT / "docs" / f"EIA_GRID_RESIDUAL_MOE_BENCHMARK_{date.today().isoformat()}.md"

CANDIDATE_IDS = [
    "ridge_residual",
    "xgboost_residual",
    "lightgbm_residual",
    "median_residual_ensemble",
    "half_median_residual_ensemble",
    "agreement_gated_residual_moe",
    "official_ar_blend_75_25",
]
BASELINE_IDS = [
    "eia_day_ahead_forecast",
    "autoregressive_ridge_p14",
    "seasonal_naive_7",
    "official_ar_equal_blend",
    "direct_xgboost_stack",
    "direct_lightgbm_stack",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "eia_grid_residual_moe_protocol.v1":
        raise ValueError("unexpected EIA residual MoE protocol schema")
    if [row["id"] for row in payload["candidate_models"]] != CANDIDATE_IDS:
        raise ValueError("candidate registry differs from the frozen implementation contract")
    if [row["id"] for row in payload["baselines"]] != BASELINE_IDS:
        raise ValueError("baseline registry differs from the frozen implementation contract")
    return payload


def protocol_commit(path: Path = PROTOCOL_PATH) -> str | None:
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", str(path.relative_to(ROOT))],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        value = ""
    else:
        value = result.stdout.strip()
    if value:
        return value
    try:
        relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
        provenance = json.loads(PROTOCOL_PROVENANCE_PATH.read_text(encoding="utf-8"))
        row = next(item for item in provenance["entries"] if item["path"] == relative)
        commit = str(row["last_touch_commit"])
        if file_sha256(path) != row["sha256"]:
            return None
        if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
            return None
        return commit
    except (OSError, ValueError, KeyError, StopIteration, json.JSONDecodeError):
        return None


def load_panel(protocol: dict[str, Any]) -> dict[str, Any]:
    contract = protocol["frozen_panel"]
    path = ROOT / contract["path"]
    observed_hash = file_sha256(path)
    if observed_hash.lower() != str(contract["file_sha256"]).lower():
        raise ValueError("frozen EIA panel file SHA-256 does not match the protocol")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "eia_grid_validation_panel.v1":
        raise ValueError("unexpected frozen EIA panel schema")
    if payload.get("row_chain_sha256") != contract["row_chain_sha256"]:
        raise ValueError("frozen EIA panel row-chain hash does not match the protocol")
    if int(payload["quality"]["row_count"]) != int(contract["row_count"]):
        raise ValueError("frozen EIA panel row count does not match the protocol")
    return payload


def stable_scale(values: np.ndarray) -> tuple[float, float]:
    center = float(np.median(values))
    mad = float(np.median(np.abs(values - center)))
    scale = max(mad * 1.4826, float(np.std(values)), abs(center) * 1e-9, 1e-9)
    return center, scale


def seasonal_mase_scale(history: list[float], season: int = 7) -> float:
    if len(history) <= season:
        return max(abs(mean(history)) * 1e-9, 1e-9)
    differences = [
        abs(history[index] - history[index - season])
        for index in range(season, len(history))
    ]
    return max(mean(differences), abs(mean(history)) * 1e-9, 1e-9)


def forecast_autoregressive_ridge(
    history: list[float], lag: int = 14, ridge: float = 1.0
) -> float:
    y = np.asarray(history[-730:], dtype=float)
    if y.size <= lag + 4:
        return float(y[-1])
    center, scale = stable_scale(y)
    z = (y - center) / scale
    x_rows = [z[index - lag : index] for index in range(lag, z.size)]
    targets = z[lag:]
    design = np.column_stack([np.ones(len(x_rows)), np.asarray(x_rows)])
    penalty = np.eye(design.shape[1]) * ridge
    penalty[0, 0] = 0.0
    coefficients = np.linalg.solve(design.T @ design + penalty, design.T @ targets)
    return center + scale * float(np.r_[1.0, z[-lag:]] @ coefficients)


def direction(value: float, tolerance: float = 1e-9) -> int:
    if value > tolerance:
        return 1
    if value < -tolerance:
        return -1
    return 0


def panel_series(panel: dict[str, Any]) -> dict[str, dict[str, Any]]:
    authorities: dict[str, dict[str, Any]] = {}
    for row in panel["rows"]:
        respondent = row["respondent"]
        if respondent not in authorities:
            authorities[respondent] = {
                "authority": {
                    "respondent": respondent,
                    "respondent_name": row.get("respondent_name") or respondent,
                    "timezone": row.get("timezone"),
                },
                "actual": {},
                "official": {},
            }
    for row in panel["rows"]:
        respondent = row["respondent"]
        if respondent not in authorities:
            continue
        if row["type"] == "D":
            authorities[respondent]["actual"][row["period"]] = float(row["value"])
        elif row["type"] == "DF":
            authorities[respondent]["official"][row["period"]] = float(row["value"])
    return authorities


def split_for_target(target: str, protocol: dict[str, Any]) -> str | None:
    split = protocol["splits"]
    if split["training_start"] <= target <= split["training_end"]:
        return "training"
    if split["development_start"] <= target <= split["development_end"]:
        return "development"
    if split["holdout_start"] <= target <= split["holdout_end"]:
        return "holdout"
    return None


def lag_date(target: date, days: int) -> str:
    return (target - timedelta(days=days)).isoformat()


def build_feature_rows(
    panel: dict[str, Any], protocol: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    series = panel_series(panel)
    authority_ids = sorted(series)
    minimum_history = int(protocol["splits"]["minimum_history_days"])
    maximum_history = int(protocol["splits"]["maximum_history_days"])
    rows: list[dict[str, Any]] = []
    skip_reasons: Counter[str] = Counter()

    for respondent in authority_ids:
        bundle = series[respondent]
        actual: dict[str, float] = bundle["actual"]
        official: dict[str, float] = bundle["official"]
        actual_dates = sorted(actual)
        targets = sorted(set(actual) & set(official))
        for target in targets:
            split_name = split_for_target(target, protocol)
            if split_name is None:
                continue
            target_day = date.fromisoformat(target)
            required_dates = [lag_date(target_day, offset) for offset in range(1, 30)]
            if any(value not in actual for value in required_dates):
                skip_reasons["actual_lag_gap"] += 1
                continue
            if any(value not in official for value in required_dates[:28]):
                skip_reasons["official_lag_gap"] += 1
                continue
            history_dates = [value for value in actual_dates if value < target][-maximum_history:]
            if len(history_dates) < minimum_history:
                skip_reasons["insufficient_history"] += 1
                continue

            history = [actual[value] for value in history_dates]
            scale = seasonal_mase_scale(history)
            center = float(np.median(np.asarray(history, dtype=float)))
            try:
                ar_forecast = forecast_autoregressive_ridge(history)
            except (ValueError, np.linalg.LinAlgError, FloatingPointError):
                skip_reasons["ar_failure"] += 1
                continue

            previous = required_dates[0]
            seasonal = required_dates[6]
            official_value = official[target]
            residuals_28 = np.asarray(
                [actual[value] - official[value] for value in required_dates[:28]],
                dtype=float,
            )
            actual_29 = np.asarray([actual[value] for value in required_dates], dtype=float)
            day_of_week_angle = 2.0 * math.pi * target_day.weekday() / 7.0
            day_of_year_angle = 2.0 * math.pi * (target_day.timetuple().tm_yday - 1) / 365.25
            features = [
                (official_value - ar_forecast) / scale,
                (official_value - actual[seasonal]) / scale,
                (official_value - actual[previous]) / scale,
                (ar_forecast - actual[seasonal]) / scale,
                (official_value - center) / scale,
                (actual[required_dates[0]] - official[required_dates[0]]) / scale,
                (actual[required_dates[6]] - official[required_dates[6]]) / scale,
                (actual[required_dates[13]] - official[required_dates[13]]) / scale,
                float(np.mean(residuals_28[:7])) / scale,
                float(np.mean(residuals_28)) / scale,
                float(np.std(residuals_28)) / scale,
                (actual[required_dates[0]] - actual[required_dates[1]]) / scale,
                (actual[required_dates[0]] - actual[required_dates[7]]) / scale,
                float(np.std(np.diff(actual_29))) / scale,
                math.sin(day_of_week_angle),
                math.cos(day_of_week_angle),
                math.sin(day_of_year_angle),
                math.cos(day_of_year_angle),
            ]
            features.extend(1.0 if respondent == value else 0.0 for value in authority_ids)
            if not all(math.isfinite(float(value)) for value in features):
                skip_reasons["nonfinite_feature"] += 1
                continue

            actual_value = actual[target]
            rows.append(
                {
                    "split": split_name,
                    "respondent": respondent,
                    "respondent_name": str(
                        bundle["authority"].get("respondent_name")
                        or bundle["authority"].get("name")
                        or respondent
                    ),
                    "target_date": target,
                    "calendar_month": target[:7],
                    "actual_mwh": actual_value,
                    "official_mwh": official_value,
                    "ar_mwh": ar_forecast,
                    "seasonal_mwh": actual[seasonal],
                    "last_mwh": actual[previous],
                    "history_center_mwh": center,
                    "seasonal_scale_mwh": scale,
                    "features": features,
                    "residual_target_scaled": (actual_value - official_value) / scale,
                    "direct_target_scaled": (actual_value - center) / scale,
                }
            )

    diagnostics = {
        "feature_row_count": len(rows),
        "feature_count": len(rows[0]["features"]) if rows else 0,
        "authority_order": authority_ids,
        "rows_by_split": dict(Counter(row["split"] for row in rows)),
        "rows_by_authority": dict(Counter(row["respondent"] for row in rows)),
        "skip_reasons": dict(sorted(skip_reasons.items())),
        "feature_contract_sha256": canonical_sha256(protocol["feature_contract"]),
    }
    return rows, diagnostics


def make_models() -> dict[str, Any]:
    residual_ridge = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    residual_xgb = XGBRegressor(
        objective="reg:squarederror",
        n_estimators=300,
        max_depth=3,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=10.0,
        random_state=20260713,
        n_jobs=4,
        tree_method="hist",
        verbosity=0,
    )
    residual_lgbm = LGBMRegressor(
        n_estimators=300,
        num_leaves=15,
        learning_rate=0.03,
        min_child_samples=40,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=10.0,
        random_state=20260713,
        n_jobs=4,
        deterministic=True,
        force_col_wise=True,
        verbosity=-1,
    )
    direct_xgb = XGBRegressor(
        objective="reg:squarederror",
        n_estimators=300,
        max_depth=3,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=10.0,
        random_state=20260713,
        n_jobs=4,
        tree_method="hist",
        verbosity=0,
    )
    direct_lgbm = LGBMRegressor(
        n_estimators=300,
        num_leaves=15,
        learning_rate=0.03,
        min_child_samples=40,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=10.0,
        random_state=20260713,
        n_jobs=4,
        deterministic=True,
        force_col_wise=True,
        verbosity=-1,
    )
    return {
        "ridge_residual": residual_ridge,
        "xgboost_residual": residual_xgb,
        "lightgbm_residual": residual_lgbm,
        "direct_xgboost_stack": direct_xgb,
        "direct_lightgbm_stack": direct_lgbm,
    }


def fit_models(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, float]]:
    if not rows:
        raise ValueError("cannot fit models without rows")
    x = np.asarray([row["features"] for row in rows], dtype=float)
    residual_target = np.asarray([row["residual_target_scaled"] for row in rows], dtype=float)
    direct_target = np.asarray([row["direct_target_scaled"] for row in rows], dtype=float)
    models = make_models()
    durations: dict[str, float] = {}
    for model_id in ["ridge_residual", "xgboost_residual", "lightgbm_residual"]:
        started = time.perf_counter()
        models[model_id].fit(x, residual_target)
        durations[model_id] = (time.perf_counter() - started) * 1000.0
    for model_id in ["direct_xgboost_stack", "direct_lightgbm_stack"]:
        started = time.perf_counter()
        models[model_id].fit(x, direct_target)
        durations[model_id] = (time.perf_counter() - started) * 1000.0
    return models, durations


def component_predictions(
    rows: list[dict[str, Any]], models: dict[str, Any]
) -> dict[str, np.ndarray]:
    x = np.asarray([row["features"] for row in rows], dtype=float)
    return {
        model_id: np.asarray(models[model_id].predict(x), dtype=float)
        for model_id in models
    }


def candidate_prediction_map(
    row: dict[str, Any], residual_components: dict[str, float]
) -> dict[str, tuple[float, bool]]:
    ridge = float(residual_components["ridge_residual"])
    xgb = float(residual_components["xgboost_residual"])
    lgbm = float(residual_components["lightgbm_residual"])
    component_values = [ridge, xgb, lgbm]
    median_correction = float(np.median(np.asarray(component_values, dtype=float)))
    spread = max(component_values) - min(component_values)
    gated = spread <= 0.75 and abs(median_correction) <= 1.5

    correction_map = {
        "ridge_residual": (ridge, False),
        "xgboost_residual": (xgb, False),
        "lightgbm_residual": (lgbm, False),
        "median_residual_ensemble": (median_correction, False),
        "half_median_residual_ensemble": (0.5 * median_correction, False),
        "agreement_gated_residual_moe": (median_correction if gated else 0.0, not gated),
    }
    predictions = {
        strategy: (
            float(row["official_mwh"])
            + float(row["seasonal_scale_mwh"]) * max(-2.5, min(2.5, correction)),
            abstained,
        )
        for strategy, (correction, abstained) in correction_map.items()
    }
    predictions["official_ar_blend_75_25"] = (
        0.75 * float(row["official_mwh"]) + 0.25 * float(row["ar_mwh"]),
        False,
    )
    return predictions


def baseline_prediction_map(
    row: dict[str, Any], direct_components: dict[str, float]
) -> dict[str, float]:
    return {
        "eia_day_ahead_forecast": float(row["official_mwh"]),
        "autoregressive_ridge_p14": float(row["ar_mwh"]),
        "seasonal_naive_7": float(row["seasonal_mwh"]),
        "official_ar_equal_blend": 0.5 * float(row["official_mwh"])
        + 0.5 * float(row["ar_mwh"]),
        "direct_xgboost_stack": float(row["history_center_mwh"])
        + float(row["seasonal_scale_mwh"])
        * float(direct_components["direct_xgboost_stack"]),
        "direct_lightgbm_stack": float(row["history_center_mwh"])
        + float(row["seasonal_scale_mwh"])
        * float(direct_components["direct_lightgbm_stack"]),
    }


def metric_row(
    source: dict[str, Any], strategy: str, kind: str, predicted: float, abstained: bool
) -> dict[str, Any]:
    actual = float(source["actual_mwh"])
    last = float(source["last_mwh"])
    absolute_error = abs(actual - predicted)
    return {
        "split": source["split"],
        "respondent": source["respondent"],
        "respondent_name": source["respondent_name"],
        "target_date": source["target_date"],
        "calendar_month": source["calendar_month"],
        "strategy": strategy,
        "kind": kind,
        "actual_mwh": actual,
        "predicted_mwh": float(predicted),
        "absolute_error_mwh": absolute_error,
        "absolute_percentage_error": absolute_error / max(abs(actual), 1e-9),
        "seasonal_mase_7": absolute_error / float(source["seasonal_scale_mwh"]),
        "directional_accuracy": float(
            direction(predicted - last) == direction(actual - last)
        ),
        "abstained_to_official": bool(abstained),
    }


def predict_candidates(
    rows: list[dict[str, Any]], models: dict[str, Any], selected_only: str | None = None
) -> list[dict[str, Any]]:
    predictions = component_predictions(rows, models)
    output: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        residuals = {
            key: float(predictions[key][index])
            for key in ["ridge_residual", "xgboost_residual", "lightgbm_residual"]
        }
        candidate_map = candidate_prediction_map(row, residuals)
        strategies = [selected_only] if selected_only else CANDIDATE_IDS
        for strategy in strategies:
            if strategy is None:
                continue
            predicted, abstained = candidate_map[strategy]
            output.append(metric_row(row, strategy, "residual_candidate", predicted, abstained))
    return output


def predict_baselines(
    rows: list[dict[str, Any]], models: dict[str, Any]
) -> list[dict[str, Any]]:
    predictions = component_predictions(rows, models)
    output: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        direct = {
            key: float(predictions[key][index])
            for key in ["direct_xgboost_stack", "direct_lightgbm_stack"]
        }
        for strategy, predicted in baseline_prediction_map(row, direct).items():
            output.append(metric_row(row, strategy, "baseline", predicted, False))
    return output


def aggregate_strategy(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["strategy"]].append(row)
    result: list[dict[str, Any]] = []
    for strategy, items in grouped.items():
        result.append(
            {
                "strategy": strategy,
                "kind": items[0]["kind"],
                "row_count": len(items),
                "authority_count": len({row["respondent"] for row in items}),
                "mean_seasonal_mase_7": mean(float(row["seasonal_mase_7"]) for row in items),
                "median_seasonal_mase_7": median(
                    float(row["seasonal_mase_7"]) for row in items
                ),
                "mean_absolute_error_mwh": mean(
                    float(row["absolute_error_mwh"]) for row in items
                ),
                "mean_absolute_percentage_error": mean(
                    float(row["absolute_percentage_error"]) for row in items
                ),
                "mean_directional_accuracy": mean(
                    float(row["directional_accuracy"]) for row in items
                ),
                "abstention_rate": mean(
                    float(bool(row["abstained_to_official"])) for row in items
                ),
            }
        )
    result.sort(
        key=lambda row: (
            float(row["mean_seasonal_mase_7"]),
            float(row["mean_absolute_error_mwh"]),
            str(row["strategy"]),
        )
    )
    for rank, row in enumerate(result, start=1):
        row["rank"] = rank
    return result


def select_candidate(leaderboard: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [row for row in leaderboard if row["strategy"] in CANDIDATE_IDS]
    if not candidates:
        raise ValueError("development leaderboard contains no candidate")
    return min(
        candidates,
        key=lambda row: (
            float(row["mean_seasonal_mase_7"]),
            float(row["mean_absolute_error_mwh"]),
            str(row["strategy"]),
        ),
    )


def percentile(values: list[float], proportion: float) -> float:
    ordered = sorted(values)
    position = proportion * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    weight = position - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def exact_two_sided_sign_test(deltas: list[float]) -> float | None:
    nonzero = [value for value in deltas if abs(value) > 1e-12]
    count = len(nonzero)
    if count == 0:
        return None
    wins = sum(1 for value in nonzero if value > 0)
    lower = min(wins, count - wins)
    cumulative = sum(math.comb(count, index) for index in range(lower + 1)) / (2**count)
    return min(1.0, 2.0 * cumulative)


def authority_cluster_bootstrap(
    authority_month_deltas: dict[str, list[float]],
    draws: int = 10000,
    seed: int = 20260713,
) -> list[float]:
    authorities = sorted(authority_month_deltas)
    if not authorities:
        return []
    rng = random.Random(seed)
    draw_means: list[float] = []
    for _ in range(draws):
        sampled = [rng.choice(authorities) for _ in authorities]
        values = [
            value for authority in sampled for value in authority_month_deltas[authority]
        ]
        draw_means.append(mean(values))
    return [percentile(draw_means, 0.025), percentile(draw_means, 0.975)]


def apply_holm(comparisons: list[dict[str, Any]]) -> None:
    tests = [
        (index, float(row["raw_two_sided_sign_test_p_value"]))
        for index, row in enumerate(comparisons)
        if row["raw_two_sided_sign_test_p_value"] is not None
    ]
    tests.sort(key=lambda item: item[1])
    running = 0.0
    for rank, (index, raw_p) in enumerate(tests):
        adjusted = min(1.0, raw_p * (len(tests) - rank))
        running = max(running, adjusted)
        comparisons[index]["holm_adjusted_p_value"] = running


def build_comparisons(
    holdout_rows: list[dict[str, Any]], selected_candidate: str, protocol: dict[str, Any]
) -> list[dict[str, Any]]:
    index = {
        (row["respondent"], row["target_date"], row["strategy"]): row
        for row in holdout_rows
    }
    comparisons: list[dict[str, Any]] = []
    for baseline in BASELINE_IDS:
        monthly_values: dict[tuple[str, str], list[float]] = defaultdict(list)
        for (respondent, target, strategy), candidate_row in index.items():
            if strategy != selected_candidate:
                continue
            baseline_row = index.get((respondent, target, baseline))
            if baseline_row is None:
                continue
            delta = float(baseline_row["seasonal_mase_7"]) - float(
                candidate_row["seasonal_mase_7"]
            )
            monthly_values[(respondent, target[:7])].append(delta)
        month_deltas = {key: mean(values) for key, values in monthly_values.items()}
        authority_months: dict[str, list[float]] = defaultdict(list)
        for (respondent, _month), value in month_deltas.items():
            authority_months[respondent].append(value)
        authority_means = {
            respondent: mean(values) for respondent, values in authority_months.items()
        }
        deltas = list(month_deltas.values())
        comparisons.append(
            {
                "baseline": baseline,
                "paired_authority_month_count": len(deltas),
                "mean_skill_delta": mean(deltas) if deltas else None,
                "median_skill_delta": median(deltas) if deltas else None,
                "cluster_bootstrap_mean_skill_ci95": authority_cluster_bootstrap(
                    authority_months
                ),
                "month_win_count": sum(1 for value in deltas if value > 0),
                "month_loss_count": sum(1 for value in deltas if value < 0),
                "month_tie_count": sum(1 for value in deltas if abs(value) <= 1e-12),
                "month_win_rate": sum(1 for value in deltas if value > 0)
                / max(sum(1 for value in deltas if abs(value) > 1e-12), 1),
                "authority_mean_skill": authority_means,
                "authority_mean_win_count": sum(
                    1 for value in authority_means.values() if value > 0
                ),
                "worst_authority_mean_skill": min(authority_means.values())
                if authority_means
                else None,
                "raw_two_sided_sign_test_p_value": exact_two_sided_sign_test(deltas),
                "holm_adjusted_p_value": None,
                "passes_comparison_gate": False,
            }
        )
    apply_holm(comparisons)
    gate = protocol["promotion_gate"]
    for comparison in comparisons:
        interval = comparison["cluster_bootstrap_mean_skill_ci95"]
        comparison["passes_comparison_gate"] = bool(
            comparison["mean_skill_delta"] is not None
            and comparison["mean_skill_delta"] > 0
            and interval
            and interval[0] > 0
            and comparison["holm_adjusted_p_value"] is not None
            and comparison["holm_adjusted_p_value"]
            <= float(gate["require_holm_adjusted_p_at_most"])
            and comparison["authority_mean_win_count"]
            >= int(gate["required_authority_mean_wins"])
            and comparison["month_win_rate"] >= float(gate["required_month_win_rate"])
            and comparison["worst_authority_mean_skill"]
            >= -float(gate["maximum_single_authority_mase_regression"])
        )
    return comparisons


def component_error_correlation(
    development_rows: list[dict[str, Any]], models: dict[str, Any]
) -> dict[str, dict[str, float]]:
    candidate_rows = predict_candidates(development_rows, models)
    by_strategy: dict[str, list[float]] = defaultdict(list)
    for row in candidate_rows:
        by_strategy[row["strategy"]].append(
            float(row["actual_mwh"]) - float(row["predicted_mwh"])
        )
    result: dict[str, dict[str, float]] = {}
    for left in CANDIDATE_IDS:
        result[left] = {}
        for right in CANDIDATE_IDS:
            left_values = np.asarray(by_strategy[left], dtype=float)
            right_values = np.asarray(by_strategy[right], dtype=float)
            if left_values.size < 2 or float(np.std(left_values)) == 0 or float(np.std(right_values)) == 0:
                correlation = 1.0 if left == right else 0.0
            else:
                correlation = float(np.corrcoef(left_values, right_values)[0, 1])
            result[left][right] = correlation
    return result


def run_benchmark(
    panel: dict[str, Any], protocol: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    feature_rows, diagnostics = build_feature_rows(panel, protocol)
    training = [row for row in feature_rows if row["split"] == "training"]
    development = [row for row in feature_rows if row["split"] == "development"]
    holdout = [row for row in feature_rows if row["split"] == "holdout"]
    if not training or not development or not holdout:
        raise ValueError("one or more frozen benchmark splits are empty")

    selection_models, selection_fit_ms = fit_models(training)
    development_prediction_rows = predict_candidates(development, selection_models)
    development_leaderboard = aggregate_strategy(development_prediction_rows)
    selected = select_candidate(development_leaderboard)
    selected_id = str(selected["strategy"])
    correlations = component_error_correlation(development, selection_models)

    final_models, final_fit_ms = fit_models(training + development)
    selected_holdout_rows = predict_candidates(holdout, final_models, selected_only=selected_id)
    baseline_holdout_rows = predict_baselines(holdout, final_models)
    holdout_rows = selected_holdout_rows + baseline_holdout_rows
    holdout_leaderboard = aggregate_strategy(holdout_rows)
    comparisons = build_comparisons(holdout_rows, selected_id, protocol)

    holdout_days: dict[str, set[str]] = defaultdict(set)
    for row in selected_holdout_rows:
        holdout_days[row["respondent"]].add(row["target_date"])
    day_counts = {key: len(value) for key, value in sorted(holdout_days.items())}
    gate = protocol["promotion_gate"]
    coverage_pass = bool(
        len(day_counts) >= int(gate["minimum_balancing_authorities"])
        and min(day_counts.values(), default=0)
        >= int(gate["minimum_common_holdout_days_per_authority"])
        and min(
            (row["paired_authority_month_count"] for row in comparisons), default=0
        )
        >= int(gate["minimum_paired_authority_months"])
    )
    comparison_pass = bool(
        comparisons and all(row["passes_comparison_gate"] for row in comparisons)
    )
    promotion_pass = coverage_pass and comparison_pass

    report = {
        "schema": "eia_grid_residual_moe_benchmark.v1",
        "generated_utc": now_utc(),
        "protocol": {
            "path": str(PROTOCOL_PATH.relative_to(ROOT)).replace("\\", "/"),
            "sha256": file_sha256(PROTOCOL_PATH),
            "git_commit": protocol_commit(),
        },
        "frozen_panel": {
            "path": protocol["frozen_panel"]["path"],
            "sha256": file_sha256(ROOT / protocol["frozen_panel"]["path"]),
            "row_chain_sha256": panel["row_chain_sha256"],
            "row_count": panel["quality"]["row_count"],
        },
        "feature_diagnostics": diagnostics,
        "fit_runtime_ms": {
            "selection_fit": selection_fit_ms,
            "final_refit": final_fit_ms,
        },
        "development_leaderboard": development_leaderboard,
        "development_candidate_error_correlation": correlations,
        "selection": {
            "selected_candidate": selected_id,
            "development_rank": selected["rank"],
            "development_mean_seasonal_mase_7": selected["mean_seasonal_mase_7"],
            "rule": protocol["selection"]["rule"],
            "holdout_used_for_selection": False,
            "post_selection_substitution": False,
        },
        "holdout_leaderboard": holdout_leaderboard,
        "holdout_coverage": {
            "authority_count": len(day_counts),
            "common_holdout_days_by_authority": day_counts,
            "minimum_common_holdout_days": min(day_counts.values(), default=0),
        },
        "baseline_comparisons": comparisons,
        "promotion_gate": {
            "coverage_pass": coverage_pass,
            "all_baseline_comparisons_pass": comparison_pass,
            "protocol_grade_internal_champion": promotion_pass,
            "external_replication_complete": False,
            "field_validation_complete": False,
            "allowed_claim": (
                "Preregistered public-data internal benchmark win in this EIA lane only."
                if promotion_pass
                else "No protocol-grade internal champion; retain the incumbent and report the result."
            ),
        },
        "claim_boundary": protocol["claim_boundary"],
    }
    report["artifact_chain_sha256"] = canonical_sha256(
        {
            "protocol": report["protocol"],
            "panel": report["frozen_panel"],
            "features": report["feature_diagnostics"],
            "selection": report["selection"],
            "holdout": report["holdout_leaderboard"],
            "comparisons": report["baseline_comparisons"],
            "promotion": report["promotion_gate"],
        }
    )
    return report, development_prediction_rows + holdout_rows


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "split",
        "respondent",
        "respondent_name",
        "target_date",
        "calendar_month",
        "strategy",
        "kind",
        "actual_mwh",
        "predicted_mwh",
        "absolute_error_mwh",
        "absolute_percentage_error",
        "seasonal_mase_7",
        "directional_accuracy",
        "abstained_to_official",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row[field] for field in fields} for row in rows)


def render_markdown(report: dict[str, Any]) -> str:
    selected = report["selection"]["selected_candidate"]
    promotion = report["promotion_gate"]
    lines = [
        "# EIA Grid Residual Mixture-of-Experts Benchmark",
        "",
        f"Generated UTC: `{report['generated_utc']}`",
        "",
        "## Verdict",
        "",
        f"- Selected on development only: `{selected}`",
        f"- Protocol-grade internal champion: `{str(promotion['protocol_grade_internal_champion']).lower()}`",
        f"- Allowed claim: {promotion['allowed_claim']}",
        f"- External replication complete: `{str(promotion['external_replication_complete']).lower()}`",
        f"- Field validation complete: `{str(promotion['field_validation_complete']).lower()}`",
        "",
        "This test asks whether residual correction can improve a strong incumbent. It does not assume that a new geometry or machine-learning model should replace the official forecast. The router is allowed to abstain to the incumbent when its component models disagree.",
        "",
        "## Frozen Evidence",
        "",
        f"- Protocol commit: `{report['protocol']['git_commit']}`",
        f"- Protocol SHA-256: `{report['protocol']['sha256']}`",
        f"- Frozen panel SHA-256: `{report['frozen_panel']['sha256']}`",
        f"- Frozen panel row-chain SHA-256: `{report['frozen_panel']['row_chain_sha256']}`",
        f"- Official EIA panel rows: `{report['frozen_panel']['row_count']}`",
        f"- Feature rows: `{report['feature_diagnostics']['feature_row_count']}`",
        f"- Feature contract SHA-256: `{report['feature_diagnostics']['feature_contract_sha256']}`",
        f"- Artifact chain SHA-256: `{report['artifact_chain_sha256']}`",
        "",
        "## Development Selection",
        "",
        "| Rank | Candidate | Mean MASE | Mean absolute error MWh | Abstention rate |",
        "| ---: | --- | ---: | ---: | ---: |",
    ]
    for row in report["development_leaderboard"]:
        lines.append(
            f"| {row['rank']} | `{row['strategy']}` | {row['mean_seasonal_mase_7']:.6f} | "
            f"{row['mean_absolute_error_mwh']:.3f} | {row['abstention_rate']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Untouched Holdout",
            "",
            "| Rank | Strategy | Kind | Mean MASE | Mean absolute error MWh | Direction accuracy |",
            "| ---: | --- | --- | ---: | ---: | ---: |",
        ]
    )
    for row in report["holdout_leaderboard"]:
        lines.append(
            f"| {row['rank']} | `{row['strategy']}` | `{row['kind']}` | "
            f"{row['mean_seasonal_mase_7']:.6f} | {row['mean_absolute_error_mwh']:.3f} | "
            f"{row['mean_directional_accuracy']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Selected Candidate Versus Baselines",
            "",
            "Positive skill means baseline MASE minus selected-candidate MASE is positive.",
            "",
            "| Baseline | Mean skill | CI95 | Month win rate | Authority wins | Holm p | Pass |",
            "| --- | ---: | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in report["baseline_comparisons"]:
        interval = row["cluster_bootstrap_mean_skill_ci95"]
        interval_text = f"[{interval[0]:.6f}, {interval[1]:.6f}]" if interval else "n/a"
        p_value = row["holm_adjusted_p_value"]
        p_text = f"{p_value:.6g}" if p_value is not None else "n/a"
        lines.append(
            f"| `{row['baseline']}` | {row['mean_skill_delta']:.6f} | {interval_text} | "
            f"{row['month_win_rate']:.3f} | {row['authority_mean_win_count']} | {p_text} | "
            f"`{str(row['passes_comparison_gate']).lower()}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- A win must survive every predeclared baseline and every robustness gate. Beating only seasonal naive or only one tree model is not enough.",
            "- A loss is retained as evidence that the incumbent should remain in this lane.",
            "- Development error correlations are stored in the JSON report so ensemble value can be distinguished from redundant model voting.",
            "",
            "## Claim Boundary",
            "",
            report["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARD_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DASHBOARD_JSON.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    write_rows(OUT_ROWS, rows)
    manifest = {
        "schema": "eia_grid_residual_moe_manifest.v1",
        "generated_utc": now_utc(),
        "artifact_chain_sha256": report["artifact_chain_sha256"],
        "files": {
            str(path.relative_to(ROOT)).replace("\\", "/"): {
                "bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
            for path in [OUT_JSON, OUT_ROWS, OUT_MD, DASHBOARD_JSON]
        },
        "claim_boundary": report["claim_boundary"],
    }
    OUT_MANIFEST.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--protocol", type=Path, default=PROTOCOL_PATH, help="Frozen protocol JSON."
    )
    args = parser.parse_args()
    protocol = load_protocol(args.protocol)
    panel = load_panel(protocol)
    report, rows = run_benchmark(panel, protocol)
    manifest = write_outputs(report, rows)
    print(
        json.dumps(
            {
                "selected_candidate": report["selection"]["selected_candidate"],
                "protocol_grade_internal_champion": report["promotion_gate"][
                    "protocol_grade_internal_champion"
                ],
                "artifact_chain_sha256": report["artifact_chain_sha256"],
                "manifest_sha256": canonical_sha256(manifest),
                "report": str(OUT_MD),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
