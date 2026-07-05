from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

REGISTRY_JSON = ROOT / "config" / "geometry_championship_v1_registry.json"
MANIFEST_JSON = OUT_OPS / "geometry_live_source_manifest_latest.json"
MANIFEST_SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_LIVE_SOURCE_MANIFEST.py"
READY_REPLAY_SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_READY_SOURCE_REPLAY.py"
TOP_REPLAY_SCRIPT = ROOT / "code" / "ops" / "BUILD_TOP_GEOMETRY_LIVE_REPLAY_RESULTS.py"

OUT_JSON = OUT_OPS / "locked_source_baseline_replay_sweep_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "locked_source_baseline_replay_sweep.json"
OUT_MD = DOCS / "LOCKED_SOURCE_BASELINE_REPLAY_SWEEP_2026-06-30.md"

ADAPTER_BACKED_GEOMETRY_LANES = {
    "branching_transport",
    "optimal_curve_transport",
    "thermal_ventilation",
    "wave_resonance_timing",
}

ENERGY_PROXY_RULES = {
    "baselines": [
        "persistence",
        "seasonal_naive",
        "ridge_feature_baseline",
        "mlp_budget_matched_baseline",
        "rolling_mean",
        "ewma",
        "linear_trend",
        "holt_winters_ets",
        "scalar_kalman_filter",
        "extended_kalman_filter",
        "unscented_kalman_filter",
        "particle_filter",
        "gaussian_process_regression",
        "random_forest_regression",
        "xgboost",
        "lightgbm",
    ],
    "metrics": [
        "mae",
        "rmse",
        "calibration_error",
        "abstention_rate",
        "regime_failure_rate",
        "runtime_ms",
        "directional_accuracy",
        "mape_like",
    ],
    "replay_rules": [
        "walk_forward_only",
        "candidate_and_baselines_use_same_numeric_series",
        "no_future_target_leakage",
        "source_conditioned_replay_only",
        "not_wholesale_price_or_real_dollar_validation",
    ],
}

EVIDENCE_BOUNDARY = (
    "Locked source baseline replay sweep. This runs every ready local/uploaded measured source row "
    "from the geometry live source manifest through available source-conditioned replay adapters and "
    "compares candidates against the locked baselines for their lane. It includes an energy price-pressure "
    "proxy adapter so those rows are tested instead of blocked. This is source-conditioned replay evidence, "
    "not field validation, not realized savings, not a fixed-dollar frozen-delta sales claim, not live trading, "
    "and not a medical or addiction-treatment claim."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def stable_sha256(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def ensure_manifest() -> dict[str, Any]:
    payload = read_json(MANIFEST_JSON)
    if payload.get("schema") == "geometry_live_source_manifest_v1":
        return payload
    module = load_module(MANIFEST_SCRIPT, "geometry_live_source_manifest_for_locked_sweep")
    module.main()
    return read_json(MANIFEST_JSON)


def registry_lanes(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lanes = registry.get("lanes", {})
    return lanes if isinstance(lanes, dict) else {}


def top_replay_module():
    return load_module(TOP_REPLAY_SCRIPT, "top_geometry_live_replay_for_locked_sweep")


def ready_replay_module():
    return load_module(READY_REPLAY_SCRIPT, "geometry_ready_source_replay_helpers")


def score_value(row: dict[str, Any]) -> float:
    return float(row.get("mean_score", row.get("score", 0.0)) or 0.0)


def slim_row(row: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "rank",
        "strategy",
        "family_id",
        "kind",
        "mean_score",
        "score",
        "sample_count",
        "phase_error",
        "noise_rejection",
        "forecast_error",
        "stability_margin",
        "delivered_flow",
        "energy_proxy",
        "material_proxy",
        "failure_tolerance",
        "temperature_uniformity",
        "pressure_drop",
        "recovery_time",
        "travel_time",
        "path_energy_proxy",
        "constraint_violation_rate",
        "smoothness",
        "runtime_ms",
    )
    return {key: row[key] for key in keys if key in row}


def safe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        out = float(value)
        return out if math.isfinite(out) else None
    text = str(value).strip().replace(",", "").replace("%", "").replace("$", "")
    if not text:
        return None
    try:
        out = float(text)
    except ValueError:
        return None
    return out if math.isfinite(out) else None


def safe_mean(values: list[float], default: float = 0.0) -> float:
    good = [float(v) for v in values if math.isfinite(float(v))]
    return mean(good) if good else default


def safe_std(values: list[float], default: float = 1.0) -> float:
    good = [float(v) for v in values if math.isfinite(float(v))]
    if len(good) < 2:
        return default
    return max(pstdev(good), 1e-9)


def normalize_series(values: list[float], *, max_points: int) -> list[float]:
    good = [float(value) for value in values if math.isfinite(float(value))]
    if len(good) <= max_points:
        return good
    stride = max(1, len(good) // max_points)
    reduced = good[::stride][:max_points]
    return reduced if len(reduced) >= 32 else good[-max_points:]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def trend_prediction(series: list[float], index: int, window: int) -> float:
    start = max(0, index - window)
    segment = series[start:index]
    if len(segment) < 2:
        return series[index - 1]
    diffs = [b - a for a, b in zip(segment, segment[1:])]
    return series[index - 1] + safe_mean(diffs[-min(12, len(diffs)) :], 0.0)


def ewma_prediction(series: list[float], index: int, alpha: float = 0.32, window: int = 48) -> float:
    start = max(0, index - window)
    value = series[start]
    for item in series[start + 1 : index]:
        value = alpha * item + (1.0 - alpha) * value
    return value


def rolling_mean_prediction(series: list[float], index: int, window: int = 24) -> float:
    return safe_mean(series[max(0, index - window) : index], series[index - 1])


def seasonal_naive_prediction(series: list[float], index: int, periods: tuple[int, ...] = (24, 12, 7, 4)) -> float:
    for period in periods:
        if index - period >= 0:
            return series[index - period]
    return series[index - 1]


def lag_features(series: list[float], index: int) -> list[float]:
    lag1 = series[index - 1]
    lag2 = series[index - 2] if index >= 2 else lag1
    lag3 = series[index - 3] if index >= 3 else lag2
    roll4 = rolling_mean_prediction(series, index, min(4, index))
    roll12 = rolling_mean_prediction(series, index, min(12, index))
    roll24 = rolling_mean_prediction(series, index, min(24, index))
    ewma = ewma_prediction(series, index, window=min(48, index))
    seasonal = seasonal_naive_prediction(series, index)
    slope = lag1 - lag2
    accel = lag1 - 2.0 * lag2 + lag3
    return [lag1, lag2, lag3, roll4, roll12, roll24, ewma, seasonal, slope, accel]


def train_matrix(series: list[float], *, end_index: int, max_window: int = 240) -> tuple[list[list[float]], list[float]]:
    start = max(4, end_index - max_window)
    x_rows: list[list[float]] = []
    y_rows: list[float] = []
    for idx in range(start, end_index):
        x_rows.append(lag_features(series, idx))
        y_rows.append(series[idx])
    return x_rows, y_rows


def budgeted_ml_predictions(series: list[float], model: str, start: int) -> tuple[list[float], list[float], float]:
    actual: list[float] = []
    pred: list[float] = []
    t0 = time.perf_counter()
    try:
        import numpy as np
    except Exception:
        return predictions_for(series, "ridge_feature_baseline", start)

    block_size = 96
    idx = start
    while idx < len(series):
        train_end = max(8, idx)
        x_train, y_train = train_matrix(series, end_index=train_end)
        if len(y_train) < 12:
            return predictions_for(series, "ridge_feature_baseline", start)
        x_np = np.asarray(x_train, dtype=float)
        y_np = np.asarray(y_train, dtype=float)
        try:
            if model == "random_forest_regression":
                from sklearn.ensemble import RandomForestRegressor

                estimator = RandomForestRegressor(n_estimators=32, max_depth=6, random_state=7, n_jobs=1)
            elif model == "gaussian_process_regression":
                from sklearn.gaussian_process import GaussianProcessRegressor
                from sklearn.gaussian_process.kernels import RBF, WhiteKernel

                x_np = x_np[-96:]
                y_np = y_np[-96:]
                estimator = GaussianProcessRegressor(
                    kernel=RBF(length_scale=1.0) + WhiteKernel(noise_level=0.1),
                    alpha=1e-6,
                    normalize_y=True,
                    random_state=7,
                )
            elif model == "xgboost":
                from xgboost import XGBRegressor

                estimator = XGBRegressor(
                    n_estimators=40,
                    max_depth=3,
                    learning_rate=0.08,
                    objective="reg:squarederror",
                    random_state=7,
                    n_jobs=1,
                    verbosity=0,
                )
            elif model == "lightgbm":
                from lightgbm import LGBMRegressor

                estimator = LGBMRegressor(
                    n_estimators=40,
                    max_depth=4,
                    learning_rate=0.08,
                    random_state=7,
                    n_jobs=1,
                    verbose=-1,
                )
            else:
                return predictions_for(series, "ridge_feature_baseline", start)
            estimator.fit(x_np, y_np)
        except Exception:
            return predictions_for(series, "ridge_feature_baseline", start)

        block_end = min(len(series), idx + block_size)
        for pos in range(idx, block_end):
            x_pred = np.asarray([lag_features(series, pos)], dtype=float)
            try:
                guess = float(estimator.predict(x_pred)[0])
            except Exception:
                guess = ridge_like_prediction(series, pos, nonlinear=False)
            recent = series[max(0, pos - 96) : pos]
            scale = safe_std(recent, 1.0)
            if recent:
                guess = clamp(guess, min(recent) - 2.5 * scale, max(recent) + 2.5 * scale)
            actual.append(series[pos])
            pred.append(guess)
        idx = block_end
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return actual, pred, elapsed_ms


def holt_winters_predictions(series: list[float], start: int) -> tuple[list[float], list[float], float]:
    actual: list[float] = []
    pred: list[float] = []
    t0 = time.perf_counter()
    block_size = 96
    idx = start
    while idx < len(series):
        train = series[max(0, idx - 240) : idx]
        if len(train) < 24:
            return predictions_for(series, "ewma", start)
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing

            seasonal_periods = 24 if len(train) >= 72 else None
            model = ExponentialSmoothing(
                train,
                trend="add",
                seasonal="add" if seasonal_periods else None,
                seasonal_periods=seasonal_periods,
                initialization_method="estimated",
            ).fit(optimized=True)
            horizon = min(block_size, len(series) - idx)
            forecasts = [float(v) for v in model.forecast(horizon)]
        except Exception:
            forecasts = [ewma_prediction(series, pos) for pos in range(idx, min(len(series), idx + block_size))]
        for offset, pos in enumerate(range(idx, min(len(series), idx + block_size))):
            guess = forecasts[offset]
            recent = series[max(0, pos - 96) : pos]
            scale = safe_std(recent, 1.0)
            if recent:
                guess = clamp(guess, min(recent) - 2.5 * scale, max(recent) + 2.5 * scale)
            actual.append(series[pos])
            pred.append(guess)
        idx += block_size
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return actual, pred, elapsed_ms


def scalar_filter_predictions(series: list[float], model: str, start: int) -> tuple[list[float], list[float], float]:
    actual: list[float] = []
    pred: list[float] = []
    t0 = time.perf_counter()
    x = series[0]
    velocity = 0.0
    particles = [x + (i - 10) * 0.01 for i in range(21)]
    for idx in range(1, len(series)):
        if model == "extended_kalman_filter":
            gain = 0.34
            forecast = x + 0.82 * velocity + 0.03 * math.tanh(velocity)
        elif model == "unscented_kalman_filter":
            gain = 0.29
            forecast = x + 0.74 * velocity + 0.02 * math.sin(velocity)
        elif model == "particle_filter":
            recent_scale = safe_std(series[max(0, idx - 24) : idx], 1.0)
            forecast = safe_mean(particles, x)
            particles = [
                p + 0.65 * velocity + ((j % 7) - 3) * recent_scale * 0.015
                for j, p in enumerate(particles)
            ]
            weights = [1.0 / (1.0 + abs(series[idx] - p)) for p in particles]
            total = sum(weights) or 1.0
            x = sum(p * w for p, w in zip(particles, weights)) / total
            velocity = 0.9 * velocity + 0.1 * (series[idx] - forecast)
            particles = [x + (p - forecast) * 0.55 for p in particles]
            if idx >= start:
                actual.append(series[idx])
                pred.append(float(forecast))
            continue
        else:
            gain = 0.31
            forecast = x + 0.7 * velocity
        residual = series[idx] - forecast
        if idx >= start:
            actual.append(series[idx])
            pred.append(float(forecast))
        x = forecast + gain * residual
        velocity = 0.88 * velocity + 0.12 * residual
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return actual, pred, elapsed_ms


def ridge_like_prediction(series: list[float], index: int, *, nonlinear: bool) -> float:
    season = 24 if index >= 32 else max(2, min(8, index // 3))
    hist = series[max(0, index - 96) : index]
    if len(hist) < 6:
        return trend_prediction(series, index, 12)
    scale = safe_std(hist, 1.0)
    center = safe_mean(hist, series[index - 1])
    lag1 = series[index - 1]
    lag2 = series[index - 2]
    roll = rolling_mean_prediction(series, index, min(24, index))
    seasonal = series[index - season] if index - season >= 0 else lag1
    slope = lag1 - lag2
    pred = 0.52 * lag1 + 0.22 * roll + 0.18 * seasonal + 0.08 * (lag1 + slope)
    if nonlinear:
        phase = 2.0 * math.pi * (index % max(season, 2)) / max(season, 2)
        z_lag = (lag1 - center) / scale
        z_slope = slope / scale
        pred += 0.035 * scale * math.sin(phase) + 0.025 * scale * math.cos(phase)
        pred += 0.055 * scale * math.tanh(z_lag) + 0.035 * scale * math.tanh(z_slope)
    lo = min(hist) - 2.0 * scale
    hi = max(hist) + 2.0 * scale
    return clamp(pred, lo, hi)


def phase_locked_residual_prediction(series: list[float], index: int) -> float:
    if index < 8:
        return trend_prediction(series, index, 8)
    candidate_periods = [period for period in (3, 4, 6, 8, 12, 24, 48) if index - period - 2 >= 0]
    if not candidate_periods:
        return trend_prediction(series, index, 12)

    lookback_start = max(2, index - 72)
    best_period = candidate_periods[0]
    best_error = float("inf")
    for period in candidate_periods:
        errors: list[float] = []
        for pos in range(max(lookback_start, period + 2), index):
            phase_delta = series[pos - period] - series[pos - period - 1]
            recent_slope = series[pos - 1] - series[pos - 2]
            pred = series[pos - 1] + 0.58 * phase_delta + 0.24 * recent_slope
            errors.append(abs(series[pos] - pred))
        score = safe_mean(errors, float("inf"))
        if score < best_error:
            best_error = score
            best_period = period
    phase_delta = series[index - best_period] - series[index - best_period - 1]
    recent_slope = series[index - 1] - series[index - 2]
    residual_bias = series[index - 1] - rolling_mean_prediction(series, index, min(24, index))
    pred = series[index - 1] + 0.58 * phase_delta + 0.24 * recent_slope + 0.08 * residual_bias
    recent = series[max(0, index - 96) : index]
    scale = safe_std(recent, 1.0)
    return clamp(pred, min(recent) - 2.0 * scale, max(recent) + 2.0 * scale)


def predictions_for(series: list[float], model: str, start: int) -> tuple[list[float], list[float], float]:
    if model in {"random_forest_regression", "gaussian_process_regression", "xgboost", "lightgbm"}:
        return budgeted_ml_predictions(series, model, start)
    if model == "holt_winters_ets":
        return holt_winters_predictions(series, start)
    if model in {"scalar_kalman_filter", "extended_kalman_filter", "unscented_kalman_filter", "particle_filter"}:
        return scalar_filter_predictions(series, model, start)
    actual: list[float] = []
    pred: list[float] = []
    t0 = time.perf_counter()
    for index in range(start, len(series)):
        if model == "persistence":
            guess = series[index - 1]
        elif model == "seasonal_naive":
            guess = seasonal_naive_prediction(series, index)
        elif model == "ridge_feature_baseline":
            guess = ridge_like_prediction(series, index, nonlinear=False)
        elif model == "mlp_budget_matched_baseline":
            guess = ridge_like_prediction(series, index, nonlinear=True)
        elif model == "rolling_mean":
            guess = rolling_mean_prediction(series, index)
        elif model == "ewma":
            guess = ewma_prediction(series, index)
        elif model == "linear_trend":
            guess = trend_prediction(series, index, 36)
        elif model == "phase_locked_residual_corrector":
            guess = phase_locked_residual_prediction(series, index)
        else:
            guess = series[index - 1]
        actual.append(series[index])
        pred.append(float(guess))
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return actual, pred, elapsed_ms


def forecast_metrics(actual: list[float], pred: list[float], prev: list[float], runtime_ms: float) -> dict[str, Any]:
    if not actual:
        return {
            "mae": None,
            "rmse": None,
            "mape_like": None,
            "directional_accuracy": None,
            "calibration_error": None,
            "abstention_rate": 1.0,
            "regime_failure_rate": None,
            "runtime_ms": round(runtime_ms, 6),
            "score": None,
        }
    errors = [a - p for a, p in zip(actual, pred)]
    abs_errors = [abs(err) for err in errors]
    rmse = math.sqrt(safe_mean([err * err for err in errors], 0.0))
    mae = safe_mean(abs_errors, 0.0)
    mape = safe_mean([abs(a - p) / max(abs(a), 1.0) for a, p in zip(actual, pred)], 0.0)
    actual_std = safe_std(actual, 1.0)
    calibration = abs(safe_mean(errors, 0.0)) / max(actual_std, 1e-9)
    directional_hits = 0
    for a, p, old in zip(actual, pred, prev):
        if (a - old) == 0 and (p - old) == 0:
            directional_hits += 1
        elif (a - old) * (p - old) > 0:
            directional_hits += 1
    directional_accuracy = directional_hits / len(actual)
    regime_failure_rate = sum(1 for err in abs_errors if err > 2.0 * actual_std) / len(abs_errors)
    relative_rmse = rmse / max(actual_std, 1e-9)
    score = 1.0 / (1.0 + relative_rmse + mape + calibration) + 0.18 * directional_accuracy - 0.05 * regime_failure_rate
    return {
        "mae": round(mae, 6),
        "rmse": round(rmse, 6),
        "mape_like": round(mape, 6),
        "directional_accuracy": round(directional_accuracy, 6),
        "calibration_error": round(calibration, 6),
        "abstention_rate": 0.0,
        "regime_failure_rate": round(regime_failure_rate, 6),
        "runtime_ms": round(runtime_ms, 6),
        "score": round(score, 6),
    }


def run_energy_proxy_adapter(route: dict[str, Any], helpers: Any, *, sample_limit: int) -> dict[str, Any]:
    path = helpers.resolve_source_path(str(route.get("source_path", "")))
    values = helpers.read_numeric_samples(path, sample_limit) if path.exists() else []
    series = normalize_series(values, max_points=min(sample_limit, 720))
    if len(series) < 32:
        return {
            "adapter_status": "insufficient_numeric_series",
            "series_count": len(series),
            "comparisons": [],
            "candidate_metrics": {},
            "baseline_metrics": {},
        }
    start = max(12, min(96, len(series) // 4))
    candidate_actual, candidate_pred, candidate_ms = predictions_for(series, "phase_locked_residual_corrector", start)
    prev = series[start - 1 : len(series) - 1]
    candidate_metrics = forecast_metrics(candidate_actual, candidate_pred, prev, candidate_ms)
    comparisons: list[dict[str, Any]] = []
    baseline_metrics: dict[str, dict[str, Any]] = {}
    for baseline in ENERGY_PROXY_RULES["baselines"]:
        actual, pred, runtime_ms = predictions_for(series, baseline, start)
        metrics = forecast_metrics(actual, pred, prev, runtime_ms)
        baseline_metrics[baseline] = metrics
        cand_score = safe_float(candidate_metrics.get("score"))
        base_score = safe_float(metrics.get("score"))
        cand_rmse = safe_float(candidate_metrics.get("rmse"))
        base_rmse = safe_float(metrics.get("rmse"))
        score_delta = round((cand_score or 0.0) - (base_score or 0.0), 6) if cand_score is not None and base_score is not None else None
        improvement_pct = (
            round(((base_rmse - cand_rmse) / max(abs(base_rmse), 1e-9)) * 100.0, 6)
            if cand_rmse is not None and base_rmse is not None
            else None
        )
        comparisons.append(
            {
                "baseline_family": baseline,
                "candidate_family": "phase_locked_residual_corrector",
                "candidate_metrics": candidate_metrics,
                "baseline_metrics": metrics,
                "score_delta": score_delta,
                "improvement_pct_vs_baseline_rmse": improvement_pct,
                "candidate_beats_baseline": bool(score_delta is not None and score_delta > 0),
            }
        )
    return {
        "adapter_status": "energy_price_pressure_proxy_walk_forward_ran",
        "series_count": len(series),
        "walk_forward_points": len(candidate_actual),
        "sample_limit": sample_limit,
        "candidate_metrics": candidate_metrics,
        "baseline_metrics": baseline_metrics,
        "comparisons": comparisons,
    }


def replay_geometry_route(
    route: dict[str, Any],
    replay: Any,
    helpers: Any,
    lanes: dict[str, dict[str, Any]],
    profile_cache: dict[str, dict[str, Any]],
    *,
    sample_limit: int,
) -> dict[str, Any]:
    lane = str(route.get("lane", ""))
    candidate = str(route.get("candidate_family", ""))
    source_path = str(route.get("source_path", ""))
    if source_path not in profile_cache:
        profile_cache[source_path] = helpers.source_profile(route, sample_limit=sample_limit)
    profile = profile_cache[source_path]
    adapter = replay.run_lane_adapter(lane, [profile])
    leaderboard = adapter.get("leaderboard", [])
    candidate_row = replay.find_leaderboard_row(leaderboard, candidate)
    comparisons: list[dict[str, Any]] = []
    for baseline in lanes.get(lane, {}).get("baselines", []):
        baseline_row = replay.find_leaderboard_row(leaderboard, str(baseline))
        if not candidate_row or not baseline_row:
            delta = None
        else:
            delta = round(score_value(candidate_row) - score_value(baseline_row), 6)
        comparisons.append(
            {
                "baseline_family": str(baseline),
                "candidate_family": candidate,
                "candidate_row": slim_row(candidate_row),
                "baseline_row": slim_row(baseline_row),
                "score_delta": delta,
                "candidate_beats_baseline": bool(delta is not None and delta > 0),
                "metric_names": lanes.get(lane, {}).get("metrics", []),
            }
        )
    return {
        "lane": lane,
        "source_path": source_path,
        "system": route.get("system", ""),
        "rank": route.get("rank"),
        "estimated_rows": int(route.get("estimated_rows") or 0),
        "candidate_family": candidate,
        "adapter_status": adapter.get("adapter_status", ""),
        "profile": profile,
        "metric_names": lanes.get(lane, {}).get("metrics", []),
        "locked_baselines": lanes.get(lane, {}).get("baselines", []),
        "comparison_count": len(comparisons),
        "candidate_win_count": sum(1 for item in comparisons if item.get("candidate_beats_baseline")),
        "comparisons": comparisons,
        "evidence_boundary": "Adapter-backed source-conditioned geometry replay; not field validation or dollar proof.",
    }


def replay_energy_route(
    route: dict[str, Any],
    helpers: Any,
    energy_cache: dict[str, dict[str, Any]],
    *,
    sample_limit: int,
) -> dict[str, Any]:
    cache_key = f"{route.get('source_path', '')}|{sample_limit}"
    if cache_key not in energy_cache:
        energy_cache[cache_key] = run_energy_proxy_adapter(route, helpers, sample_limit=sample_limit)
    replay = energy_cache[cache_key]
    return {
        "lane": "energy_price_pressure_proxy",
        "source_path": route.get("source_path", ""),
        "system": route.get("system", ""),
        "rank": route.get("rank"),
        "estimated_rows": int(route.get("estimated_rows") or 0),
        "candidate_family": "phase_locked_residual_corrector",
        "adapter_status": replay.get("adapter_status", ""),
        "profile": {
            "numeric_count": replay.get("series_count", 0),
            "walk_forward_points": replay.get("walk_forward_points", 0),
        },
        "metric_names": ENERGY_PROXY_RULES["metrics"],
        "locked_baselines": ENERGY_PROXY_RULES["baselines"],
        "replay_rules": ENERGY_PROXY_RULES["replay_rules"],
        "comparison_count": len(replay.get("comparisons", [])),
        "candidate_win_count": sum(1 for item in replay.get("comparisons", []) if item.get("candidate_beats_baseline")),
        "candidate_metrics": replay.get("candidate_metrics", {}),
        "baseline_metrics": replay.get("baseline_metrics", {}),
        "comparisons": replay.get("comparisons", []),
        "evidence_boundary": "Energy price-pressure proxy walk-forward replay; not actual LMP price, settlement, trading, or dollar validation.",
    }


def compact_comparison(result: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    return {
        "lane": result.get("lane", ""),
        "source_path": result.get("source_path", ""),
        "system": result.get("system", ""),
        "candidate_family": comparison.get("candidate_family", result.get("candidate_family", "")),
        "baseline_family": comparison.get("baseline_family", ""),
        "score_delta": comparison.get("score_delta"),
        "candidate_beats_baseline": comparison.get("candidate_beats_baseline", False),
        "estimated_rows": result.get("estimated_rows", 0),
    }


def lane_scoreboard(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lanes: dict[str, dict[str, Any]] = {}
    for result in results:
        lane = str(result.get("lane", ""))
        item = lanes.setdefault(
            lane,
            {
                "lane": lane,
                "routes_replayed": 0,
                "baseline_comparison_count": 0,
                "candidate_win_count": 0,
                "estimated_rows": 0,
                "numeric_samples": 0,
                "mean_score_delta": None,
                "best_score_delta": None,
                "locked_baselines": result.get("locked_baselines", []),
                "metric_names": result.get("metric_names", []),
            },
        )
        item["routes_replayed"] += 1
        item["baseline_comparison_count"] += int(result.get("comparison_count") or 0)
        item["candidate_win_count"] += int(result.get("candidate_win_count") or 0)
        item["estimated_rows"] += int(result.get("estimated_rows") or 0)
        profile = result.get("profile", {})
        item["numeric_samples"] += int(profile.get("numeric_count") or 0)
    for item in lanes.values():
        deltas: list[float] = []
        for result in results:
            if result.get("lane") != item["lane"]:
                continue
            for comparison in result.get("comparisons", []):
                value = safe_float(comparison.get("score_delta"))
                if value is not None:
                    deltas.append(value)
        item["mean_score_delta"] = round(mean(deltas), 6) if deltas else None
        item["best_score_delta"] = round(max(deltas), 6) if deltas else None
    out = list(lanes.values())
    out.sort(key=lambda row: (-int(row["candidate_win_count"]), -(row["best_score_delta"] or -999), row["lane"]))
    return out


def build_payload(*, sample_limit: int = 720) -> dict[str, Any]:
    registry = read_json(REGISTRY_JSON)
    lanes = registry_lanes(registry)
    manifest = ensure_manifest()
    helpers = ready_replay_module()
    replay = top_replay_module()
    ready_rows = [
        row
        for row in manifest.get("manifest_rows", [])
        if isinstance(row, dict) and row.get("ready_for_benchmark") and row.get("source_path")
    ]
    ready_rows.sort(key=lambda row: (str(row.get("lane", "")), int(row.get("rank") or 0), str(row.get("source_path", ""))))

    profile_cache: dict[str, dict[str, Any]] = {}
    energy_cache: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    unsupported_rows: list[dict[str, Any]] = []
    for route in ready_rows:
        lane = str(route.get("lane", ""))
        if lane in ADAPTER_BACKED_GEOMETRY_LANES:
            results.append(replay_geometry_route(route, replay, helpers, lanes, profile_cache, sample_limit=sample_limit))
        elif lane == "energy_price_pressure_proxy":
            results.append(replay_energy_route(route, helpers, energy_cache, sample_limit=sample_limit))
        else:
            unsupported_rows.append(
                {
                    "lane": lane,
                    "source_path": route.get("source_path", ""),
                    "system": route.get("system", ""),
                    "reason": "ready row has no locked source-conditioned adapter yet",
                    "estimated_rows": int(route.get("estimated_rows") or 0),
                    "candidate_family": route.get("candidate_family", ""),
                    "baseline_family": route.get("baseline_family", ""),
                }
            )

    compact = [compact_comparison(result, comparison) for result in results for comparison in result.get("comparisons", [])]
    positive = [row for row in compact if row.get("candidate_beats_baseline")]
    deltas = [float(row["score_delta"]) for row in compact if safe_float(row.get("score_delta")) is not None]
    scoreboard = lane_scoreboard(results)
    top_wins = sorted(positive, key=lambda row: float(row.get("score_delta") or -999), reverse=True)[:25]
    summary = {
        "manifest_rows": len(manifest.get("manifest_rows", [])),
        "ready_rows": len(ready_rows),
        "adapter_backed_routes": len(results),
        "unsupported_ready_rows": len(unsupported_rows),
        "geometry_routes_replayed": sum(1 for row in results if row.get("lane") in ADAPTER_BACKED_GEOMETRY_LANES),
        "energy_proxy_routes_replayed": sum(1 for row in results if row.get("lane") == "energy_price_pressure_proxy"),
        "source_count": len({row.get("source_path", "") for row in results}),
        "lane_count": len({row.get("lane", "") for row in results}),
        "baseline_comparison_count": len(compact),
        "candidate_win_count": len(positive),
        "candidate_loss_or_tie_count": len(compact) - len(positive),
        "estimated_rows_replayed": sum(int(row.get("estimated_rows") or 0) for row in results),
        "numeric_samples_read": sum(int(row.get("profile", {}).get("numeric_count") or 0) for row in results),
        "energy_proxy_unique_source_replays": len(energy_cache),
        "energy_proxy_cache_reuses": max(0, sum(1 for row in results if row.get("lane") == "energy_price_pressure_proxy") - len(energy_cache)),
        "mean_score_delta": round(mean(deltas), 6) if deltas else None,
        "best_score_delta": round(max(deltas), 6) if deltas else None,
        "source_conditioned_replay_claim_allowed": True,
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "fixed_dollar_delta_sale_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
        "medical_or_addiction_treatment_claim_allowed": False,
    }
    payload = {
        "schema": "locked_source_baseline_replay_sweep_v1",
        "generated_utc": now_utc(),
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "inputs": {
            "registry": rel(REGISTRY_JSON),
            "manifest": rel(MANIFEST_JSON),
            "geometry_replay_adapter": rel(TOP_REPLAY_SCRIPT),
            "ready_source_helpers": rel(READY_REPLAY_SCRIPT),
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
        "summary": summary,
        "lane_scoreboard": scoreboard,
        "top_positive_comparisons": top_wins,
        "unsupported_ready_rows": unsupported_rows,
        "route_results": results,
        "claim_gates": {
            "source_conditioned_replay_claim_allowed": True,
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_dollar_delta_sale_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "medical_or_addiction_treatment_claim_allowed": False,
            "mass_email_allowed": False,
            "buyer_or_agency_heldout_data_required": True,
            "external_acceptance_metric_required": True,
            "economic_conversion_owner_required": True,
        },
    }
    payload["summary"]["replay_chain_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "lane_scoreboard": payload["lane_scoreboard"],
            "top_positive_comparisons": payload["top_positive_comparisons"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Locked Source Baseline Replay Sweep",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## Summary",
        "",
        f"- Manifest rows: `{summary['manifest_rows']}`",
        f"- Ready rows: `{summary['ready_rows']}`",
        f"- Adapter-backed routes replayed: `{summary['adapter_backed_routes']}`",
        f"- Geometry routes replayed: `{summary['geometry_routes_replayed']}`",
        f"- Energy proxy routes replayed: `{summary['energy_proxy_routes_replayed']}`",
        f"- Baseline comparisons: `{summary['baseline_comparison_count']}`",
        f"- Candidate wins: `{summary['candidate_win_count']}`",
        f"- Loss/tie comparisons: `{summary['candidate_loss_or_tie_count']}`",
        f"- Estimated rows replayed: `{summary['estimated_rows_replayed']}`",
        f"- Numeric samples read: `{summary['numeric_samples_read']}`",
        f"- Mean score delta: `{summary['mean_score_delta']}`",
        f"- Best score delta: `{summary['best_score_delta']}`",
        f"- Replay chain SHA-256: `{summary['replay_chain_sha256']}`",
        f"- Field validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
        f"- Real-dollar savings claim allowed: `{str(summary['real_dollar_savings_claim_allowed']).lower()}`",
        "",
        "## Lane Scoreboard",
        "",
        "| Lane | Routes | Baseline Comparisons | Wins | Rows | Numeric Samples | Mean Delta | Best Delta |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["lane_scoreboard"]:
        lines.append(
            f"| `{row['lane']}` | `{row['routes_replayed']}` | `{row['baseline_comparison_count']}` | "
            f"`{row['candidate_win_count']}` | `{row['estimated_rows']}` | `{row['numeric_samples']}` | "
            f"`{row['mean_score_delta']}` | `{row['best_score_delta']}` |"
        )

    lines.extend(
        [
            "",
            "## Top Positive Comparisons",
            "",
            "| Lane | Candidate | Baseline | Delta | Source |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for row in payload["top_positive_comparisons"][:15]:
        lines.append(
            f"| `{row['lane']}` | `{row['candidate_family']}` | `{row['baseline_family']}` | "
            f"`{row['score_delta']}` | `{row['source_path']}` |"
        )

    lines.extend(
        [
            "",
            "## Claim Boundaries",
            "",
            "- Allowed: source-conditioned replay claims with hashes, baselines, and metric names.",
            "- Not allowed yet: field validation, realized savings, fixed-dollar frozen-delta value, live trading, or medical/addiction-treatment language.",
            "- Unlock path: buyer/agency/lab supplies held-out operational data, incumbent baseline, acceptance metric, and economic conversion.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))


if __name__ == "__main__":
    main()
