"""
Leakage-resistant hybrid forecasting research runner.

This runner is intentionally separate from live execution. It evaluates whether
harmonic or residual-harmonic models add repeatable value beyond strong,
past-only baselines. Every outer test fold is untouched until scoring.

Evidence levels:
  screening  - walk-forward and bootstrap complete, surrogate test omitted
  candidate  - nominal gates pass before multiple-comparison adjustment
  robust     - all gates, including adjusted surrogate p-value, pass

The legacy "brachistochrone" idea is represented only as a square-root recency
weighting ablation. It is not treated as evidence of a physical fastest-path
effect.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler


ROOT = Path(
    os.environ.get("LUMA_ROOT", str(Path(__file__).resolve().parents[1]))
).expanduser().resolve()
MASTER_ROOT = ROOT / "out" / "master_universe_v2"
OUT_ROOT = ROOT / "out" / "hybrid_edge_v7"
LEDGER = OUT_ROOT / "ledger.jsonl"

BASELINE_MODELS = (
    "naive",
    "seasonal_naive",
    "ridge_ar_12",
    "ridge_ar_24",
    "mlp_ar_24",
)
ADVANCED_MODELS = (
    "harmonic_ridge",
    "sqrt_recency_harmonic",
    "ridge_ar_12_harmonic_residual",
    "ridge_ar_24_harmonic_residual",
)
ALL_MODELS = BASELINE_MODELS + ADVANCED_MODELS


@dataclass(frozen=True)
class Fold:
    fold: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int


def utc_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_float(value: Any, default: float = float("nan")) -> float:
    try:
        result = float(value)
    except Exception:
        return default
    return result if math.isfinite(result) else default


def expanding_folds(
    n_obs: int,
    *,
    n_splits: int,
    test_size: int,
    min_train: int,
) -> list[Fold]:
    if n_splits < 1 or test_size < 1:
        raise ValueError("n_splits and test_size must be positive")
    first_test = n_obs - n_splits * test_size
    if first_test < min_train:
        raise ValueError(
            f"need at least {min_train + n_splits * test_size} observations; "
            f"received {n_obs}"
        )
    return [
        Fold(
            fold=index + 1,
            train_start=0,
            train_end=first_test + index * test_size,
            test_start=first_test + index * test_size,
            test_end=first_test + (index + 1) * test_size,
        )
        for index in range(n_splits)
    ]


def _mase_scale(train: np.ndarray) -> float:
    if len(train) < 2:
        return 1.0
    scale = float(np.mean(np.abs(np.diff(train))))
    return scale if math.isfinite(scale) and scale > 1e-12 else 1.0


def _rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(actual - predicted))))


def _mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - predicted)))


def _directional_accuracy(
    actual: np.ndarray,
    predicted: np.ndarray,
    anchor: float,
) -> float:
    actual_direction = np.sign(np.diff(np.concatenate([[anchor], actual])))
    predicted_direction = np.sign(np.diff(np.concatenate([[anchor], predicted])))
    return float(np.mean(actual_direction == predicted_direction))


def _linear_detrend(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(len(values), dtype=float)
    if len(values) < 2:
        trend = np.full(len(values), values[-1] if len(values) else 0.0)
        return values - trend, trend
    slope, intercept = np.polyfit(t, values, 1)
    trend = slope * t + intercept
    return values - trend, trend


def spectral_profile(values: np.ndarray, top_k: int = 3) -> dict[str, Any]:
    values = np.asarray(values, dtype=float)
    residual, _ = _linear_detrend(values)
    residual = residual - float(np.mean(residual))
    if len(residual) < 16 or float(np.std(residual)) <= 1e-12:
        return {
            "frequencies": [],
            "periods": [],
            "concentration": 0.0,
        }
    spectrum = np.fft.rfft(residual)
    power = np.square(np.abs(spectrum))
    frequencies = np.fft.rfftfreq(len(residual), d=1.0)
    valid = np.where(
        (frequencies > 0.0)
        & (frequencies <= 0.5)
        & ((1.0 / np.maximum(frequencies, 1e-12)) >= 2.0)
        & ((1.0 / np.maximum(frequencies, 1e-12)) <= max(4.0, len(values) / 2.0))
    )[0]
    if len(valid) == 0:
        return {
            "frequencies": [],
            "periods": [],
            "concentration": 0.0,
        }
    ranked = valid[np.argsort(power[valid])[::-1]]
    chosen = ranked[: max(1, int(top_k))]
    total = float(np.sum(power[valid])) + 1e-12
    concentration = float(np.sum(power[chosen]) / total)
    selected_frequencies = [float(frequencies[index]) for index in chosen]
    return {
        "frequencies": selected_frequencies,
        "periods": [float(1.0 / frequency) for frequency in selected_frequencies],
        "concentration": concentration,
    }


def phase_stability(values: np.ndarray, windows: int = 4) -> dict[str, float]:
    values = np.asarray(values, dtype=float)
    profile = spectral_profile(values, top_k=1)
    if not profile["frequencies"] or len(values) < 48:
        return {
            "phase_stability": 0.0,
            "spectral_concentration": float(profile["concentration"]),
            "dominant_period": 0.0,
        }
    frequency = float(profile["frequencies"][0])
    window_size = max(24, len(values) // 3)
    starts = np.linspace(
        0,
        max(0, len(values) - window_size),
        num=max(2, windows),
        dtype=int,
    )
    phases: list[float] = []
    for start in sorted(set(int(value) for value in starts)):
        stop = min(len(values), start + window_size)
        segment = values[start:stop]
        if len(segment) < 16:
            continue
        residual, _ = _linear_detrend(segment)
        global_t = np.arange(start, stop, dtype=float)
        coefficient = np.sum(
            residual * np.exp(-2j * np.pi * frequency * global_t)
        )
        if abs(coefficient) > 1e-12:
            phases.append(float(np.angle(coefficient)))
    stability = (
        float(abs(np.mean(np.exp(1j * np.asarray(phases)))))
        if len(phases) >= 2
        else 0.0
    )
    return {
        "phase_stability": stability,
        "spectral_concentration": float(profile["concentration"]),
        "dominant_period": float(profile["periods"][0]),
    }


def forecast_naive(train: np.ndarray, horizon: int) -> np.ndarray:
    return np.full(horizon, float(train[-1]), dtype=float)


def forecast_seasonal_naive(train: np.ndarray, horizon: int) -> np.ndarray:
    profile = spectral_profile(train, top_k=1)
    period = (
        int(round(float(profile["periods"][0])))
        if profile["periods"] and profile["concentration"] >= 0.08
        else 1
    )
    period = max(1, min(period, len(train)))
    return np.asarray(
        [train[len(train) - period + (index % period)] for index in range(horizon)],
        dtype=float,
    )


def _lagged_xy(values: np.ndarray, lag: int) -> tuple[np.ndarray, np.ndarray]:
    if len(values) <= lag + 4:
        raise ValueError(f"insufficient history for lag {lag}")
    x = np.asarray(
        [values[index - lag : index] for index in range(lag, len(values))],
        dtype=float,
    )
    y = np.asarray(values[lag:], dtype=float)
    return x, y


def _fit_ridge_ar(
    train: np.ndarray,
    lag: int,
) -> tuple[Ridge, StandardScaler, StandardScaler, np.ndarray]:
    x, y = _lagged_xy(train, lag)
    x_scaler = StandardScaler().fit(x)
    y_scaler = StandardScaler().fit(y.reshape(-1, 1))
    model = Ridge(alpha=1.0)
    model.fit(
        x_scaler.transform(x),
        y_scaler.transform(y.reshape(-1, 1)).ravel(),
    )
    fitted_scaled = model.predict(x_scaler.transform(x))
    fitted = y_scaler.inverse_transform(fitted_scaled.reshape(-1, 1)).ravel()
    return model, x_scaler, y_scaler, fitted


def _recursive_lag_forecast(
    train: np.ndarray,
    horizon: int,
    lag: int,
    model: Any,
    x_scaler: StandardScaler,
    y_scaler: StandardScaler,
) -> np.ndarray:
    history = list(np.asarray(train, dtype=float))
    predictions: list[float] = []
    for _ in range(horizon):
        row = np.asarray(history[-lag:], dtype=float).reshape(1, -1)
        scaled = model.predict(x_scaler.transform(row))
        predicted = float(
            y_scaler.inverse_transform(np.asarray(scaled).reshape(-1, 1))[0, 0]
        )
        predictions.append(predicted)
        history.append(predicted)
    return np.asarray(predictions, dtype=float)


def forecast_ridge_ar(train: np.ndarray, horizon: int, lag: int) -> np.ndarray:
    model, x_scaler, y_scaler, _ = _fit_ridge_ar(train, lag)
    return _recursive_lag_forecast(
        train,
        horizon,
        lag,
        model,
        x_scaler,
        y_scaler,
    )


def forecast_mlp_ar(
    train: np.ndarray,
    horizon: int,
    lag: int,
    seed: int,
) -> np.ndarray:
    x, y = _lagged_xy(train, lag)
    x_scaler = StandardScaler().fit(x)
    y_scaler = StandardScaler().fit(y.reshape(-1, 1))
    model = MLPRegressor(
        hidden_layer_sizes=(32, 16),
        activation="tanh",
        solver="adam",
        alpha=1e-3,
        learning_rate_init=2e-3,
        max_iter=600,
        early_stopping=len(x) >= 40,
        validation_fraction=0.15,
        n_iter_no_change=25,
        random_state=seed,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(
            x_scaler.transform(x),
            y_scaler.transform(y.reshape(-1, 1)).ravel(),
        )
    return _recursive_lag_forecast(
        train,
        horizon,
        lag,
        model,
        x_scaler,
        y_scaler,
    )


def _harmonic_design(
    indices: np.ndarray,
    scale: float,
    frequencies: Iterable[float],
) -> np.ndarray:
    columns = [indices / max(scale, 1.0)]
    for frequency in frequencies:
        angle = 2.0 * np.pi * float(frequency) * indices
        columns.append(np.sin(angle))
        columns.append(np.cos(angle))
    return np.column_stack(columns)


def forecast_harmonic(
    train: np.ndarray,
    horizon: int,
    *,
    sqrt_recency: bool = False,
    top_k: int = 3,
) -> np.ndarray:
    profile = spectral_profile(train, top_k=top_k)
    frequencies = profile["frequencies"]
    if not frequencies:
        return forecast_naive(train, horizon)
    train_index = np.arange(len(train), dtype=float)
    future_index = np.arange(len(train), len(train) + horizon, dtype=float)
    x_train = _harmonic_design(train_index, len(train), frequencies)
    x_future = _harmonic_design(future_index, len(train), frequencies)
    center = float(np.mean(train))
    scale = float(np.std(train))
    if scale <= 1e-12:
        return np.full(horizon, center, dtype=float)
    target = (train - center) / scale
    sample_weight = None
    if sqrt_recency:
        sample_weight = np.sqrt(
            np.linspace(1.0 / len(train), 1.0, len(train), dtype=float)
        )
    model = Ridge(alpha=1.0)
    model.fit(x_train, target, sample_weight=sample_weight)
    return model.predict(x_future) * scale + center


def forecast_residual_hybrid(
    train: np.ndarray,
    horizon: int,
    *,
    lag: int,
) -> np.ndarray:
    model, x_scaler, y_scaler, fitted = _fit_ridge_ar(train, lag)
    ar_forecast = _recursive_lag_forecast(
        train,
        horizon,
        lag,
        model,
        x_scaler,
        y_scaler,
    )
    residual = np.asarray(train[lag:] - fitted, dtype=float)
    if len(residual) < 36:
        return ar_forecast
    residual_forecast = forecast_harmonic(
        residual,
        horizon,
        sqrt_recency=False,
        top_k=3,
    )
    return ar_forecast + residual_forecast


def forecast_model(
    model_name: str,
    train: np.ndarray,
    horizon: int,
    *,
    seed: int,
) -> np.ndarray:
    if model_name == "naive":
        return forecast_naive(train, horizon)
    if model_name == "seasonal_naive":
        return forecast_seasonal_naive(train, horizon)
    if model_name == "ridge_ar_12":
        return forecast_ridge_ar(train, horizon, lag=12)
    if model_name == "ridge_ar_24":
        return forecast_ridge_ar(train, horizon, lag=24)
    if model_name == "mlp_ar_24":
        return forecast_mlp_ar(train, horizon, lag=24, seed=seed)
    if model_name == "harmonic_ridge":
        return forecast_harmonic(train, horizon, sqrt_recency=False)
    if model_name == "sqrt_recency_harmonic":
        return forecast_harmonic(train, horizon, sqrt_recency=True)
    if model_name == "ridge_ar_12_harmonic_residual":
        return forecast_residual_hybrid(train, horizon, lag=12)
    if model_name == "ridge_ar_24_harmonic_residual":
        return forecast_residual_hybrid(train, horizon, lag=24)
    raise KeyError(f"unknown model: {model_name}")


def inner_model_scores(
    train: np.ndarray,
    *,
    seed: int,
    n_splits: int = 3,
) -> dict[str, dict[str, Any]]:
    test_size = max(8, min(14, (len(train) - 48) // max(1, n_splits)))
    folds = expanding_folds(
        len(train),
        n_splits=n_splits,
        test_size=test_size,
        min_train=48,
    )
    scores: dict[str, dict[str, Any]] = {}
    for model_offset, model_name in enumerate(ALL_MODELS):
        fold_scores: list[float] = []
        failures: list[str] = []
        for fold in folds:
            inner_train = train[fold.train_start : fold.train_end]
            actual = train[fold.test_start : fold.test_end]
            try:
                predicted = forecast_model(
                    model_name,
                    inner_train,
                    len(actual),
                    seed=seed + model_offset * 101 + fold.fold,
                )
                fold_scores.append(_mae(actual, predicted) / _mase_scale(inner_train))
            except Exception as exc:
                fold_scores.append(float("inf"))
                failures.append(f"fold_{fold.fold}:{type(exc).__name__}")
        finite = [value for value in fold_scores if math.isfinite(value)]
        scores[model_name] = {
            "mean_mase": float(np.mean(finite)) if finite else float("inf"),
            "fold_mase": fold_scores,
            "failures": failures,
        }
    return scores


def _candidate_phase_values(
    train: np.ndarray,
    candidate: str,
) -> np.ndarray:
    if "harmonic_residual" not in candidate:
        residual, _ = _linear_detrend(train)
        return residual
    lag = 24 if "_24_" in candidate else 12
    try:
        _, _, _, fitted = _fit_ridge_ar(train, lag)
        return np.asarray(train[lag:] - fitted, dtype=float)
    except Exception:
        residual, _ = _linear_detrend(train)
        return residual


def select_past_only_model(
    train: np.ndarray,
    *,
    seed: int,
    min_inner_gain: float = 0.01,
    phase_stability_min: float = 0.55,
    spectral_concentration_min: float = 0.08,
) -> dict[str, Any]:
    scores = inner_model_scores(train, seed=seed)
    baseline = min(
        BASELINE_MODELS,
        key=lambda name: scores[name]["mean_mase"],
    )
    advanced = min(
        ADVANCED_MODELS,
        key=lambda name: scores[name]["mean_mase"],
    )
    baseline_score = float(scores[baseline]["mean_mase"])
    advanced_score = float(scores[advanced]["mean_mase"])
    relative_gain = (
        (baseline_score - advanced_score) / baseline_score
        if math.isfinite(baseline_score) and baseline_score > 1e-12
        else float("-inf")
    )
    baseline_folds = scores[baseline]["fold_mase"]
    advanced_folds = scores[advanced]["fold_mase"]
    paired = [
        (base, candidate)
        for base, candidate in zip(baseline_folds, advanced_folds)
        if math.isfinite(base) and math.isfinite(candidate)
    ]
    paired_relative_gains = [
        (base - candidate) / base
        for base, candidate in paired
        if base > 1e-12
    ]
    fold_win_rate = (
        sum(candidate < base for base, candidate in paired) / len(paired)
        if paired
        else 0.0
    )
    recent_fold_gain = (
        paired_relative_gains[-1]
        if paired_relative_gains
        else float("-inf")
    )
    median_fold_gain = (
        float(np.median(paired_relative_gains))
        if paired_relative_gains
        else float("-inf")
    )
    phase = phase_stability(_candidate_phase_values(train, advanced))
    phase_gate = (
        phase["phase_stability"] >= phase_stability_min
        and phase["spectral_concentration"] >= spectral_concentration_min
    )
    advanced_allowed = (
        math.isfinite(advanced_score)
        and relative_gain >= min_inner_gain
        and fold_win_rate >= (2.0 / 3.0)
        and recent_fold_gain > 0.0
        and median_fold_gain > 0.0
        and phase_gate
    )
    selected = advanced if advanced_allowed else baseline
    return {
        "baseline_model": baseline,
        "advanced_model": advanced,
        "selected_model": selected,
        "advanced_allowed": advanced_allowed,
        "baseline_inner_mase": baseline_score,
        "advanced_inner_mase": advanced_score,
        "advanced_inner_gain_pct": relative_gain * 100.0,
        "advanced_inner_fold_win_rate": fold_win_rate,
        "advanced_recent_inner_gain_pct": recent_fold_gain * 100.0,
        "advanced_median_inner_gain_pct": median_fold_gain * 100.0,
        **phase,
        "inner_scores": {
            name: {
                "mean_mase": scores[name]["mean_mase"],
                "fold_mase": scores[name]["fold_mase"],
                "failures": scores[name]["failures"],
            }
            for name in ALL_MODELS
        },
    }


def evaluate_series_core(
    values: np.ndarray,
    *,
    n_splits: int,
    test_size: int,
    min_train: int,
    seed: int,
    correction_alpha: float = 0.10,
    correction_clip_scale: float = 0.50,
) -> dict[str, Any]:
    if not 0.0 <= correction_alpha <= 1.0:
        raise ValueError("correction_alpha must be between 0 and 1")
    if correction_clip_scale <= 0.0:
        raise ValueError("correction_clip_scale must be positive")
    folds = expanding_folds(
        len(values),
        n_splits=n_splits,
        test_size=test_size,
        min_train=min_train,
    )
    fold_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    for fold in folds:
        train = values[fold.train_start : fold.train_end]
        actual = values[fold.test_start : fold.test_end]
        selection = select_past_only_model(
            train,
            seed=seed + fold.fold * 1009,
        )
        baseline_model = str(selection["baseline_model"])
        selected_model = str(selection["selected_model"])
        baseline_pred = forecast_model(
            baseline_model,
            train,
            len(actual),
            seed=seed + fold.fold * 2003,
        )
        if selected_model == baseline_model:
            hybrid_pred = baseline_pred.copy()
        else:
            advanced_pred = forecast_model(
                selected_model,
                train,
                len(actual),
                seed=seed + fold.fold * 3001,
            )
            correction_cap = correction_clip_scale * _mase_scale(train)
            bounded_correction = np.clip(
                advanced_pred - baseline_pred,
                -correction_cap,
                correction_cap,
            )
            hybrid_pred = baseline_pred + correction_alpha * bounded_correction
        scale = _mase_scale(train)
        baseline_abs = np.abs(actual - baseline_pred)
        hybrid_abs = np.abs(actual - hybrid_pred)
        improvement = baseline_abs - hybrid_abs
        fold_rows.append(
            {
                "fold": fold.fold,
                "train_end": fold.train_end,
                "test_start": fold.test_start,
                "test_end": fold.test_end,
                "n_train": len(train),
                "n_test": len(actual),
                "baseline_model": baseline_model,
                "advanced_model": selection["advanced_model"],
                "selected_model": selected_model,
                "advanced_allowed": selection["advanced_allowed"],
                "phase_stability": selection["phase_stability"],
                "spectral_concentration": selection["spectral_concentration"],
                "dominant_period": selection["dominant_period"],
                "advanced_inner_gain_pct": selection["advanced_inner_gain_pct"],
                "advanced_inner_fold_win_rate": selection[
                    "advanced_inner_fold_win_rate"
                ],
                "advanced_recent_inner_gain_pct": selection[
                    "advanced_recent_inner_gain_pct"
                ],
                "advanced_median_inner_gain_pct": selection[
                    "advanced_median_inner_gain_pct"
                ],
                "correction_alpha": correction_alpha,
                "correction_clip_scale": correction_clip_scale,
                "baseline_mae": float(np.mean(baseline_abs)),
                "hybrid_mae": float(np.mean(hybrid_abs)),
                "baseline_rmse": _rmse(actual, baseline_pred),
                "hybrid_rmse": _rmse(actual, hybrid_pred),
                "baseline_mase": float(np.mean(baseline_abs) / scale),
                "hybrid_mase": float(np.mean(hybrid_abs) / scale),
                "baseline_directional_accuracy": _directional_accuracy(
                    actual,
                    baseline_pred,
                    float(train[-1]),
                ),
                "hybrid_directional_accuracy": _directional_accuracy(
                    actual,
                    hybrid_pred,
                    float(train[-1]),
                ),
                "mae_gain": float(np.sum(improvement)),
            }
        )
        for offset, (
            actual_value,
            baseline_value,
            hybrid_value,
            point_gain,
        ) in enumerate(
            zip(actual, baseline_pred, hybrid_pred, improvement)
        ):
            prediction_rows.append(
                {
                    "fold": fold.fold,
                    "offset": offset,
                    "index": fold.test_start + offset,
                    "actual": float(actual_value),
                    "baseline_prediction": float(baseline_value),
                    "hybrid_prediction": float(hybrid_value),
                    "baseline_abs_error": float(abs(actual_value - baseline_value)),
                    "hybrid_abs_error": float(abs(actual_value - hybrid_value)),
                    "paired_mae_gain": float(point_gain),
                }
            )
    baseline_errors = np.asarray(
        [row["baseline_abs_error"] for row in prediction_rows],
        dtype=float,
    )
    hybrid_errors = np.asarray(
        [row["hybrid_abs_error"] for row in prediction_rows],
        dtype=float,
    )
    baseline_mae = float(np.mean(baseline_errors))
    hybrid_mae = float(np.mean(hybrid_errors))
    improvement_pct = (
        (baseline_mae - hybrid_mae) / baseline_mae * 100.0
        if baseline_mae > 1e-12
        else 0.0
    )
    positive_fold_rate = (
        sum(float(row["mae_gain"]) > 0.0 for row in fold_rows)
        / max(1, len(fold_rows))
        * 100.0
    )
    positive_gains = [
        max(0.0, float(row["mae_gain"]))
        for row in fold_rows
    ]
    max_fold_contribution = (
        max(positive_gains) / sum(positive_gains) * 100.0
        if sum(positive_gains) > 1e-12
        else 100.0
    )
    return {
        "folds": fold_rows,
        "predictions": prediction_rows,
        "metrics": {
            "n_folds": len(fold_rows),
            "test_observations": len(prediction_rows),
            "baseline_mae": baseline_mae,
            "hybrid_mae": hybrid_mae,
            "mae_improvement_pct": improvement_pct,
            "baseline_rmse": float(
                np.sqrt(np.mean(np.square(baseline_errors)))
            ),
            "hybrid_rmse": float(
                np.sqrt(np.mean(np.square(hybrid_errors)))
            ),
            "positive_fold_rate_pct": positive_fold_rate,
            "max_positive_fold_contribution_pct": max_fold_contribution,
            "advanced_activation_rate_pct": (
                sum(bool(row["advanced_allowed"]) for row in fold_rows)
                / max(1, len(fold_rows))
                * 100.0
            ),
        },
    }


def paired_block_bootstrap(
    prediction_rows: list[dict[str, Any]],
    *,
    samples: int,
    seed: int,
) -> dict[str, float]:
    by_fold: dict[int, np.ndarray] = {}
    for row in prediction_rows:
        by_fold.setdefault(int(row["fold"]), []).append(
            float(row["paired_mae_gain"])
        )
    arrays = {
        fold: np.asarray(values, dtype=float)
        for fold, values in by_fold.items()
    }
    observed = float(
        np.mean(np.concatenate(list(arrays.values())))
    )
    if samples <= 0:
        return {
            "mean_paired_mae_gain": observed,
            "ci95_low": float("nan"),
            "ci95_high": float("nan"),
        }
    rng = np.random.default_rng(seed)
    boot: list[float] = []
    for _ in range(samples):
        sampled_folds: list[np.ndarray] = []
        for values in arrays.values():
            block = max(2, int(round(math.sqrt(len(values)))))
            generated: list[float] = []
            while len(generated) < len(values):
                start = int(rng.integers(0, len(values)))
                for offset in range(block):
                    generated.append(float(values[(start + offset) % len(values)]))
                    if len(generated) >= len(values):
                        break
            sampled_folds.append(np.asarray(generated, dtype=float))
        boot.append(float(np.mean(np.concatenate(sampled_folds))))
    return {
        "mean_paired_mae_gain": observed,
        "ci95_low": float(np.quantile(boot, 0.025)),
        "ci95_high": float(np.quantile(boot, 0.975)),
    }


def iaaft_surrogate(
    values: np.ndarray,
    *,
    rng: np.random.Generator,
    iterations: int = 30,
) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    sorted_values = np.sort(values)
    target_amplitude = np.abs(np.fft.rfft(values - np.mean(values)))
    surrogate = rng.permutation(values)
    for _ in range(max(1, iterations)):
        transformed = np.fft.rfft(surrogate - np.mean(surrogate))
        phases = np.angle(transformed)
        adjusted = np.fft.irfft(
            target_amplitude * np.exp(1j * phases),
            n=len(values),
        )
        ranks = np.argsort(np.argsort(adjusted))
        surrogate = sorted_values[ranks]
    return np.asarray(surrogate, dtype=float)


def surrogate_p_value(
    values: np.ndarray,
    observed_improvement_pct: float,
    *,
    count: int,
    n_splits: int,
    test_size: int,
    min_train: int,
    seed: int,
    correction_alpha: float,
    correction_clip_scale: float,
) -> dict[str, Any]:
    if count <= 0:
        return {
            "count": 0,
            "p_value": None,
            "null_improvement_pct": [],
            "method": "IAAFT_full_nested_rerun",
        }
    rng = np.random.default_rng(seed)
    null_values: list[float] = []
    failures = 0
    for index in range(count):
        surrogate = iaaft_surrogate(values, rng=rng)
        try:
            result = evaluate_series_core(
                surrogate,
                n_splits=n_splits,
                test_size=test_size,
                min_train=min_train,
                seed=seed + 50_000 + index * 997,
                correction_alpha=correction_alpha,
                correction_clip_scale=correction_clip_scale,
            )
            null_values.append(
                float(result["metrics"]["mae_improvement_pct"])
            )
        except Exception:
            failures += 1
    p_value = (
        (1.0 + sum(value >= observed_improvement_pct for value in null_values))
        / (len(null_values) + 1.0)
        if null_values
        else None
    )
    return {
        "count": len(null_values),
        "failures": failures,
        "p_value": p_value,
        "null_improvement_pct": null_values,
        "method": "IAAFT_full_nested_rerun",
    }


def benjamini_hochberg(p_values: list[float | None]) -> list[float | None]:
    valid = [
        (index, float(value))
        for index, value in enumerate(p_values)
        if value is not None and math.isfinite(float(value))
    ]
    adjusted: list[float | None] = [None] * len(p_values)
    if not valid:
        return adjusted
    ranked = sorted(valid, key=lambda item: item[1])
    running = 1.0
    total = len(ranked)
    for reverse_rank in range(total - 1, -1, -1):
        index, value = ranked[reverse_rank]
        rank = reverse_rank + 1
        running = min(running, value * total / rank)
        adjusted[index] = min(1.0, running)
    return adjusted


def evaluate_series(
    values: np.ndarray,
    *,
    n_splits: int,
    test_size: int,
    min_train: int,
    bootstrap_samples: int,
    surrogate_count: int,
    seed: int,
    correction_alpha: float,
    correction_clip_scale: float,
) -> dict[str, Any]:
    core = evaluate_series_core(
        values,
        n_splits=n_splits,
        test_size=test_size,
        min_train=min_train,
        seed=seed,
        correction_alpha=correction_alpha,
        correction_clip_scale=correction_clip_scale,
    )
    bootstrap = paired_block_bootstrap(
        core["predictions"],
        samples=bootstrap_samples,
        seed=seed + 10_000,
    )
    surrogates = surrogate_p_value(
        values,
        float(core["metrics"]["mae_improvement_pct"]),
        count=surrogate_count,
        n_splits=n_splits,
        test_size=test_size,
        min_train=min_train,
        seed=seed + 20_000,
        correction_alpha=correction_alpha,
        correction_clip_scale=correction_clip_scale,
    )
    return {
        **core,
        "bootstrap": bootstrap,
        "surrogate_test": surrogates,
    }


def _dataset_group(name: str) -> str:
    prefixes = (
        "EIA930",
        "EIA_GEN",
        "EIA_",
        "FRED",
        "NOAA",
        "NASA",
        "USGS",
        "COINGECKO",
        "YF_",
        "AV_",
        "OPENAQ",
        "BLS",
    )
    for prefix in prefixes:
        if name.startswith(prefix):
            return prefix
    return name.split("_", 1)[0]


def discover_datasets(
    raw_dir: Path,
    *,
    requested: list[str],
    limit: int,
    offset: int,
    minimum_observations: int,
) -> list[Path]:
    if limit < 1:
        raise ValueError("limit must be positive")
    if offset < 0:
        raise ValueError("offset cannot be negative")
    if requested:
        if offset:
            raise ValueError("offset cannot be combined with explicit datasets")
        paths = [raw_dir / f"{name}.csv" for name in requested]
        missing = [str(path) for path in paths if not path.exists()]
        if missing:
            raise FileNotFoundError("missing requested datasets: " + ", ".join(missing))
        return paths
    groups: dict[str, list[Path]] = {}
    seen_hashes: set[str] = set()
    for path in sorted(raw_dir.glob("*.csv")):
        try:
            frame = pd.read_csv(path, usecols=["value"])
            count = int(frame["value"].notna().sum())
        except Exception:
            continue
        if count < minimum_observations:
            continue
        digest = sha256_file(path)
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        groups.setdefault(_dataset_group(path.stem), []).append(path)
    selected: list[Path] = []
    group_names = sorted(groups)
    cursor = 0
    target_count = offset + limit
    while group_names and len(selected) < target_count:
        group = group_names[cursor % len(group_names)]
        candidates = groups[group]
        if candidates:
            selected.append(candidates.pop(0))
        if not candidates:
            group_names.remove(group)
            cursor = 0
        else:
            cursor += 1
    return selected[offset:target_count]


def load_values(path: Path) -> np.ndarray:
    frame = pd.read_csv(path)
    if "value" not in frame.columns:
        raise ValueError(f"{path} has no value column")
    values = pd.to_numeric(frame["value"], errors="coerce")
    values = values.replace([np.inf, -np.inf], np.nan).dropna()
    return values.to_numpy(dtype=float)


def _dependency_versions() -> dict[str, str]:
    packages = (
        "numpy",
        "pandas",
        "scipy",
        "scikit-learn",
        "statsmodels",
        "xgboost",
        "lightgbm",
    )
    versions: dict[str, str] = {}
    for package in packages:
        try:
            versions[package] = importlib_metadata.version(package)
        except Exception:
            versions[package] = "unavailable"
    return versions


def _git_state() -> dict[str, Any]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        return {
            "commit": commit,
            "dirty": bool(status),
            "modified_paths": status,
        }
    except Exception as exc:
        return {"error": str(exc)}


def _gate_row(row: dict[str, Any]) -> dict[str, Any]:
    p_value = row.get("surrogate_p_value")
    q_value = row.get("surrogate_q_value")
    checks = {
        "five_walk_forward_folds": int(row["n_folds"]) >= 5,
        "hundred_test_observations": int(row["test_observations"]) >= 100,
        "bootstrap_ci_above_zero": float(row["bootstrap_ci95_low"]) > 0.0,
        "positive_effect_70pct_folds": (
            float(row["positive_fold_rate_pct"]) >= 70.0
        ),
        "no_fold_over_40pct_gain": (
            float(row["max_positive_fold_contribution_pct"]) <= 40.0
        ),
        "positive_total_improvement": float(row["mae_improvement_pct"]) > 0.0,
        "surrogate_p_below_005": (
            p_value is not None and float(p_value) < 0.05
        ),
        "bh_q_below_005": (
            q_value is not None and float(q_value) < 0.05
        ),
    }
    if p_value is None:
        evidence_level = "screening"
    elif all(checks.values()):
        evidence_level = "robust"
    elif all(
        value
        for name, value in checks.items()
        if name not in {"bh_q_below_005"}
    ):
        evidence_level = "candidate"
    else:
        evidence_level = "exploratory"
    return {
        "evidence_level": evidence_level,
        "claim_gate_passed": evidence_level == "robust",
        "gate_checks": checks,
    }


def _write_markdown(
    path: Path,
    summary: dict[str, Any],
    dataset_rows: list[dict[str, Any]],
) -> None:
    lines = [
        "# Hybrid Edge V7 Scorecard",
        "",
        f"Run UTC: `{summary['run_utc']}`",
        f"Source benchmark: `{summary['source_run']}`",
        "",
        "## Evidence Boundary",
        "",
        "This is a research benchmark, not live-trading authorization. The "
        "geometry ablation is a recency-weight test, not proof of a physical "
        "brachistochrone, vortex, or non-Euclidean mechanism.",
        "",
        "## Headline",
        "",
        f"- Datasets evaluated: {summary['datasets_evaluated']}",
        f"- Robust claim gates passed: {summary['robust_datasets']}",
        f"- Screening-positive datasets: {summary['positive_improvement_datasets']}",
        f"- Median MAE improvement: {summary['median_mae_improvement_pct']:.3f}%",
        f"- Advanced model activation rate: {summary['advanced_activation_rate_pct']:.1f}%",
        "",
        "## Dataset Results",
        "",
        "| Dataset | MAE gain | CI low | Positive folds | Surrogate p | BH q | Level |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in sorted(
        dataset_rows,
        key=lambda item: float(item["mae_improvement_pct"]),
        reverse=True,
    ):
        p_text = (
            f"{float(row['surrogate_p_value']):.4f}"
            if row["surrogate_p_value"] is not None
            else "not run"
        )
        q_text = (
            f"{float(row['surrogate_q_value']):.4f}"
            if row["surrogate_q_value"] is not None
            else "not run"
        )
        lines.append(
            f"| {row['dataset']} | {row['mae_improvement_pct']:.3f}% | "
            f"{row['bootstrap_ci95_low']:.6g} | "
            f"{row['positive_fold_rate_pct']:.1f}% | {p_text} | {q_text} | "
            f"{row['evidence_level']} |"
        )
    lines.extend(
        [
            "",
            "## Federal Grant Relevance",
            "",
            "The defensible innovation is evidence-gated adaptive forecasting: "
            "advanced residual or harmonic corrections are activated only when "
            "past-only validation and phase-stability diagnostics agree. The same "
            "architecture can route compact maritime pattern-of-life models, "
            "calibrate alert confidence, and abstain when evidence is weak.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_manifest(run_dir: Path, validation: dict[str, Any]) -> Path:
    files: dict[str, dict[str, Any]] = {}
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file() or path.name == "manifest.sha256.json":
            continue
        files[str(path.relative_to(run_dir))] = {
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
    manifest = {
        "generated_utc": utc_iso(),
        "schema": "hybrid_edge_v7_manifest_v1",
        "validation": validation,
        "files": files,
    }
    path = run_dir / "manifest.sha256.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def _append_ledger(entry: dict[str, Any]) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    previous_hash = ""
    if LEDGER.exists():
        lines = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if lines:
            try:
                previous_hash = json.loads(lines[-1]).get("entry_sha256", "")
            except Exception:
                previous_hash = ""
    payload = {**entry, "previous_entry_sha256": previous_hash}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["entry_sha256"] = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    with LEDGER.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def run(args: argparse.Namespace) -> Path:
    source_run = args.run_utc
    if not source_run:
        latest = MASTER_ROOT / "latest.txt"
        if latest.exists():
            source_run = latest.read_text(encoding="utf-8").strip()
        else:
            runs = sorted(path.name for path in MASTER_ROOT.iterdir() if path.is_dir())
            source_run = runs[-1] if runs else ""
    if not source_run:
        raise FileNotFoundError("no master universe run is available")
    raw_dir = MASTER_ROOT / source_run / "raw"
    if not raw_dir.exists():
        raise FileNotFoundError(raw_dir)

    run_tag = args.output_tag or utc_tag()
    run_dir = OUT_ROOT / run_tag
    run_dir.mkdir(parents=True, exist_ok=False)

    minimum_observations = args.min_train + args.folds * args.test_size
    paths = discover_datasets(
        raw_dir,
        requested=args.datasets,
        limit=args.limit,
        offset=args.offset,
        minimum_observations=minimum_observations,
    )
    if not paths:
        raise RuntimeError("no eligible datasets selected")

    config = {
        "run_utc": run_tag,
        "source_run": source_run,
        "datasets": [path.stem for path in paths],
        "dataset_offset": args.offset,
        "folds": args.folds,
        "test_size": args.test_size,
        "min_train": args.min_train,
        "bootstrap_samples": args.bootstrap_samples,
        "surrogate_count": args.surrogates,
        "seed": args.seed,
        "baseline_models": list(BASELINE_MODELS),
        "advanced_models": list(ADVANCED_MODELS),
        "phase_gate": {
            "minimum_inner_gain": 0.01,
            "phase_stability_min": 0.55,
            "spectral_concentration_min": 0.08,
            "inner_fold_win_rate_min": 2.0 / 3.0,
            "recent_inner_fold_gain_gt": 0.0,
            "median_inner_fold_gain_gt": 0.0,
        },
        "correction_governor": {
            "alpha": args.correction_alpha,
            "clip_scale_mase": args.correction_clip_scale,
        },
        "claim_gate": {
            "outer_folds_min": 5,
            "test_observations_min": 100,
            "bootstrap_ci_low_gt": 0.0,
            "surrogate_adjusted_p_lt": 0.05,
            "positive_fold_rate_min": 0.70,
            "max_single_fold_gain_share": 0.40,
        },
        "dependencies": _dependency_versions(),
        "python": sys.version,
        "platform": platform.platform(),
        "git": _git_state(),
    }
    (run_dir / "config.json").write_text(
        json.dumps(config, indent=2),
        encoding="utf-8",
    )

    dataset_rows: list[dict[str, Any]] = []
    fold_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    t0 = time.time()
    for dataset_index, path in enumerate(paths):
        values = load_values(path)
        print(
            f"[hybrid-v7] {dataset_index + 1}/{len(paths)} "
            f"{path.stem} n={len(values)}",
            flush=True,
        )
        result = evaluate_series(
            values,
            n_splits=args.folds,
            test_size=args.test_size,
            min_train=args.min_train,
            bootstrap_samples=args.bootstrap_samples,
            surrogate_count=args.surrogates,
            seed=args.seed + dataset_index * 100_003,
            correction_alpha=args.correction_alpha,
            correction_clip_scale=args.correction_clip_scale,
        )
        metrics = result["metrics"]
        bootstrap = result["bootstrap"]
        surrogate = result["surrogate_test"]
        dataset_rows.append(
            {
                "dataset": path.stem,
                "group": _dataset_group(path.stem),
                "source_path": str(path.relative_to(ROOT)),
                "source_sha256": sha256_file(path),
                "n_obs": len(values),
                **metrics,
                "bootstrap_mean_paired_mae_gain": bootstrap[
                    "mean_paired_mae_gain"
                ],
                "bootstrap_ci95_low": bootstrap["ci95_low"],
                "bootstrap_ci95_high": bootstrap["ci95_high"],
                "surrogate_count": surrogate["count"],
                "surrogate_p_value": surrogate["p_value"],
                "surrogate_method": surrogate["method"],
            }
        )
        for row in result["folds"]:
            fold_rows.append({"dataset": path.stem, **row})
        for row in result["predictions"]:
            prediction_rows.append({"dataset": path.stem, **row})

    q_values = benjamini_hochberg(
        [row["surrogate_p_value"] for row in dataset_rows]
    )
    for row, q_value in zip(dataset_rows, q_values):
        row["surrogate_q_value"] = q_value
        row.update(_gate_row(row))

    dataset_frame = pd.DataFrame(dataset_rows)
    fold_frame = pd.DataFrame(fold_rows)
    prediction_frame = pd.DataFrame(prediction_rows)
    dataset_frame.to_csv(run_dir / "dataset_summary.csv", index=False)
    fold_frame.to_csv(run_dir / "folds.csv", index=False)
    prediction_frame.to_csv(run_dir / "predictions.csv", index=False)

    summary = {
        "run_utc": run_tag,
        "generated_utc": utc_iso(),
        "schema": "hybrid_edge_v7_summary_v1",
        "source_run": source_run,
        "datasets_evaluated": len(dataset_rows),
        "robust_datasets": sum(
            bool(row["claim_gate_passed"]) for row in dataset_rows
        ),
        "positive_improvement_datasets": sum(
            float(row["mae_improvement_pct"]) > 0.0 for row in dataset_rows
        ),
        "median_mae_improvement_pct": float(
            np.median(
                [float(row["mae_improvement_pct"]) for row in dataset_rows]
            )
        ),
        "advanced_activation_rate_pct": float(
            np.mean(
                [float(row["advanced_activation_rate_pct"]) for row in dataset_rows]
            )
        ),
        "elapsed_seconds": round(time.time() - t0, 3),
        "validation": {
            "chronological_outer_walk_forward": True,
            "nested_past_only_selection": True,
            "training_only_transforms": True,
            "paired_moving_block_bootstrap": True,
            "phase_randomized_iaaft_surrogates": args.surrogates > 0,
            "benjamini_hochberg_control": args.surrogates > 0,
            "live_execution_authorized": False,
            "submission_grade_only_if_claim_gate_passed": True,
        },
        "datasets": dataset_rows,
    }
    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_markdown(run_dir / "SCORECARD.md", summary, dataset_rows)
    manifest_path = _write_manifest(run_dir, summary["validation"])
    _append_ledger(
        {
            "run_utc": run_tag,
            "generated_utc": summary["generated_utc"],
            "source_run": source_run,
            "datasets_evaluated": summary["datasets_evaluated"],
            "robust_datasets": summary["robust_datasets"],
            "median_mae_improvement_pct": summary[
                "median_mae_improvement_pct"
            ],
            "manifest_sha256": sha256_file(manifest_path),
            "summary_sha256": sha256_file(summary_path),
        }
    )
    (OUT_ROOT / "latest.txt").write_text(run_tag + "\n", encoding="utf-8")
    return run_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run leakage-resistant hybrid forecasting validation."
    )
    parser.add_argument("--run-utc", default="")
    parser.add_argument("--output-tag", default="")
    parser.add_argument("--datasets", nargs="*", default=[])
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--test-size", type=int, default=20)
    parser.add_argument("--min-train", type=int, default=60)
    parser.add_argument("--bootstrap-samples", type=int, default=400)
    parser.add_argument("--surrogates", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20260613)
    parser.add_argument("--correction-alpha", type=float, default=0.10)
    parser.add_argument("--correction-clip-scale", type=float, default=0.50)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_dir = run(args)
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "datasets_evaluated": summary["datasets_evaluated"],
                "positive_improvement_datasets": summary[
                    "positive_improvement_datasets"
                ],
                "robust_datasets": summary["robust_datasets"],
                "median_mae_improvement_pct": summary[
                    "median_mae_improvement_pct"
                ],
                "elapsed_seconds": summary["elapsed_seconds"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
