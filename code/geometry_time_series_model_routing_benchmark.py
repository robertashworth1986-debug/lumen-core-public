"""Measured-source walk-forward benchmark for time-series model routing.

The benchmark uses frozen public-source snapshots and evaluates every strategy
on the same expanding-window forecast origins. It is software replay evidence,
not a trading system, operational forecast, field validation, or dollar proof.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any, Callable

import numpy as np


EVIDENCE_BOUNDARY = (
    "Frozen measured-source walk-forward software benchmark only. Models use "
    "past values at each forecast origin and are compared on identical future "
    "observations. Results do not establish operational forecasting, field "
    "validation, trading edge, realized savings, or real-dollar performance."
)

CANDIDATE_ESTIMATOR_ID = "hurst_conditioned_multiscale_increment_heuristic_v1"

MIN_SERIES_LENGTH = 24
MAX_ORIGINS_PER_SERIES = 48
FORECAST_HORIZONS = (1, 3, 5)

GROUP_FIELDS = (
    "series_id",
    "symbol",
    "pair",
    "ticker",
    "respondent",
    "station",
    "dataset_id",
    "dataset",
    "name",
)
TIME_FIELDS = (
    "timestamp",
    "time",
    "datetime",
    "date",
    "period_start",
    "observation_date",
    "period",
)
VALUE_FIELD_HINTS = (
    "value",
    "close",
    "price",
    "rate",
    "temperature",
    "measurement",
    "estimate",
    "observation",
    "index",
    "count",
    "volume",
)
EXCLUDED_VALUE_TOKENS = (
    "time",
    "date",
    "year",
    "month",
    "period",
    "status",
    "code",
    "latitude",
    "longitude",
    "coverage",
)

SOURCE_EXTRACTION_RULES: dict[str, dict[str, Any]] = {
    "EIA_GRID_VALIDATION": {
        "group_fields": ("respondent", "type", "timezone"),
        "value_field": "value",
        "filters": {"type": {"D"}},
        "scope": "actual demand only; official day-ahead forecasts are reserved for the paired EIA wave benchmark",
    },
}

ForecastFn = Callable[[list[float], int], float]

SOURCE_BASELINE_DEFAULTS: dict[str, dict[str, Any]] = {
    "EIA_GRID_VALIDATION": {
        "cadence": "daily",
        "seasonal_period": 7,
        "autoregressive_lag": 14,
    },
    "FRED": {
        "cadence": "mixed",
        "seasonal_period": 5,
        "autoregressive_lag": 5,
        "series_overrides": {
            "CPIAUCSL": {
                "cadence": "monthly",
                "seasonal_period": 12,
                "autoregressive_lag": 12,
            },
            "UNRATE": {
                "cadence": "monthly",
                "seasonal_period": 12,
                "autoregressive_lag": 12,
            },
        },
    },
    "BLS": {
        "cadence": "monthly",
        "seasonal_period": 12,
        "autoregressive_lag": 12,
    },
    "KRAKEN_PUBLIC": {
        "cadence": "hourly",
        "seasonal_period": 24,
        "autoregressive_lag": 24,
    },
    "TWELVE_DATA": {
        "cadence": "business_daily",
        "seasonal_period": 5,
        "autoregressive_lag": 5,
    },
    "ALPHAVANTAGE": {
        "cadence": "business_daily",
        "seasonal_period": 5,
        "autoregressive_lag": 5,
    },
}


@dataclass(frozen=True)
class StrategySpec:
    name: str
    kind: str
    family_id: str
    description: str
    forecast: ForecastFn


def as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if not isinstance(value, str):
        return None
    text = value.strip().replace(",", "")
    if not text or text.lower() in {".", "na", "n/a", "null", "none", "-"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def normalized_field_name(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")


def choose_group_field(rows: list[dict[str, Any]]) -> str | None:
    for field in GROUP_FIELDS:
        values = {str(row.get(field, "")).strip() for row in rows if str(row.get(field, "")).strip()}
        if values:
            return field
    return None


def choose_value_field(rows: list[dict[str, Any]]) -> str | None:
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)

    numeric_counts = {
        field: sum(1 for row in rows if as_float(row.get(field)) is not None)
        for field in fields
    }
    candidates = [field for field in fields if numeric_counts[field] >= 2]
    if not candidates:
        return None

    for hint in VALUE_FIELD_HINTS:
        exact = [field for field in candidates if normalized_field_name(field) == hint]
        if exact:
            return max(exact, key=lambda field: numeric_counts[field])
        partial = [field for field in candidates if hint in normalized_field_name(field)]
        if partial:
            return max(partial, key=lambda field: numeric_counts[field])

    filtered = [
        field
        for field in candidates
        if not any(token in normalized_field_name(field) for token in EXCLUDED_VALUE_TOKENS)
        and not normalized_field_name(field).endswith("id")
    ]
    return max(filtered or candidates, key=lambda field: numeric_counts[field])


def row_time_key(row: dict[str, Any], index: int) -> tuple[str, int]:
    year = str(row.get("year", "")).strip()
    period = str(row.get("period", "")).strip().upper().removeprefix("M")
    if year:
        return (f"{year}-{period.zfill(2)}", index)
    for field in TIME_FIELDS:
        value = row.get(field)
        if value is not None and str(value).strip():
            if isinstance(value, (int, float)):
                return (f"{float(value):030.9f}", index)
            return (str(value).strip(), index)
    return (f"{index:012d}", index)


def extract_series(snapshot: dict[str, Any], source: str) -> list[dict[str, Any]]:
    rows = snapshot.get("rows", [])
    if not isinstance(rows, list):
        return []
    clean_rows = [row for row in rows if isinstance(row, dict)]
    if not clean_rows:
        return []

    rule = SOURCE_EXTRACTION_RULES.get(source.upper(), {})
    filters = rule.get("filters", {}) if isinstance(rule.get("filters"), dict) else {}
    clean_rows = [
        row
        for row in clean_rows
        if all(
            str(row.get(field, "")).strip() in {str(value) for value in allowed}
            for field, allowed in filters.items()
        )
    ]
    if not clean_rows:
        return []

    configured_group_fields = tuple(str(field) for field in rule.get("group_fields", ()))
    fallback_group_field = choose_group_field(clean_rows)
    group_fields = (
        configured_group_fields
        if configured_group_fields
        else ((fallback_group_field,) if fallback_group_field else ())
    )
    value_field = str(rule.get("value_field", "")) or choose_value_field(clean_rows)
    if not value_field:
        return []

    grouped: dict[str, list[tuple[tuple[str, int], float]]] = {}
    group_quality: dict[str, dict[str, int]] = {}
    for index, row in enumerate(clean_rows):
        group = (
            "|".join(str(row.get(field, "")).strip() for field in group_fields)
            if group_fields
            else source
        )
        group = group or source
        quality = group_quality.setdefault(
            group,
            {"raw_row_count": 0, "missing_value_count": 0},
        )
        quality["raw_row_count"] += 1
        value = as_float(row.get(value_field))
        if value is None:
            quality["missing_value_count"] += 1
            continue
        grouped.setdefault(group, []).append((row_time_key(row, index), value))

    extracted: list[dict[str, Any]] = []
    for group, items in sorted(grouped.items()):
        items.sort(key=lambda item: item[0])
        time_keys = [time_key[0] for time_key, _ in items]
        duplicate_time_count = len(time_keys) - len(set(time_keys))
        values = [value for _, value in items]
        quality = group_quality[group]
        raw_row_count = quality["raw_row_count"]
        missing_value_count = quality["missing_value_count"]
        valid_fraction = len(values) / raw_row_count if raw_row_count else 0.0
        extracted.append(
            {
                "source": source,
                "series_id": group,
                "group_field": "|".join(group_fields) if group_fields else "source",
                "group_fields": list(group_fields),
                "value_field": value_field,
                "source_extraction_scope": rule.get("scope", "generic measured series"),
                "row_count": len(values),
                "raw_row_count": raw_row_count,
                "first_time_key": time_keys[0] if time_keys else "",
                "last_time_key": time_keys[-1] if time_keys else "",
                "duplicate_time_count": duplicate_time_count,
                "missing_value_count": missing_value_count,
                "valid_value_fraction": round(valid_fraction, 6),
                "calendar_compression_present": missing_value_count > 0,
                "chronology_quality_pass": duplicate_time_count == 0,
                "prospective_confirmation_eligible": (
                    duplicate_time_count == 0 and missing_value_count == 0
                ),
                "values": values,
            }
        )
    return extracted


def forecast_naive_last(history: list[float], horizon: int) -> float:
    return history[-1]


def forecast_drift(history: list[float], horizon: int) -> float:
    if len(history) < 2:
        return history[-1]
    slope = (history[-1] - history[0]) / (len(history) - 1)
    return history[-1] + horizon * slope


def forecast_moving_average(history: list[float], horizon: int) -> float:
    window = history[-min(8, len(history)) :]
    return mean(window)


def forecast_exponential_smoothing(history: list[float], horizon: int) -> float:
    level = history[0]
    alpha = 0.30
    for value in history[1:]:
        level = alpha * value + (1.0 - alpha) * level
    return level


def forecast_seasonal_naive(
    history: list[float], horizon: int, seasonal_period: int
) -> float:
    period = max(1, int(seasonal_period))
    if len(history) < period:
        return forecast_naive_last(history, horizon)
    offset = (horizon - 1) % period
    return history[-period + offset]


def damped_holt_state(
    history: list[float], alpha: float, beta: float, phi: float
) -> tuple[float, float, float]:
    if len(history) < 2:
        return history[-1], 0.0, 0.0
    initial_differences = [
        current - previous
        for previous, current in zip(history[:7], history[1:7])
    ]
    level = history[0]
    trend = median(initial_differences) if initial_differences else 0.0
    absolute_errors: list[float] = []
    for value in history[1:]:
        one_step = level + phi * trend
        absolute_errors.append(abs(value - one_step))
        previous_level = level
        level = alpha * value + (1.0 - alpha) * one_step
        trend = (
            beta * (level - previous_level)
            + (1.0 - beta) * phi * trend
        )
    return level, trend, mean(absolute_errors) if absolute_errors else 0.0


def forecast_damped_holt_ets(history: list[float], horizon: int) -> float:
    if len(history) < 6:
        return forecast_drift(history, horizon)
    best: tuple[float, float, float, float, float] | None = None
    for alpha in (0.2, 0.5, 0.8):
        for beta in (0.1, 0.3, 0.6):
            for phi in (0.80, 0.90, 0.98):
                level, trend, error = damped_holt_state(
                    history, alpha, beta, phi
                )
                candidate = (error, alpha, beta, phi, level)
                if best is None or candidate[:4] < best[:4]:
                    best = candidate
                    best_trend = trend
    if best is None:
        return forecast_drift(history, horizon)
    _, _, _, phi, level = best
    damped_steps = sum(phi**step for step in range(1, horizon + 1))
    return level + damped_steps * best_trend


def forecast_autoregressive_ridge(
    history: list[float], horizon: int, requested_lag: int
) -> float:
    maximum_lag = max(1, (len(history) - 4) // 2)
    lag = min(max(1, int(requested_lag)), maximum_lag)
    if len(history) < 2 * lag + 4:
        return forecast_drift(history, horizon)

    values = np.asarray(history, dtype=float)
    features = np.asarray(
        [values[index - lag : index][::-1] for index in range(lag, len(values))],
        dtype=float,
    )
    targets = values[lag:]
    center = features.mean(axis=0)
    scale = features.std(axis=0)
    scale[scale < 1e-12] = 1.0
    standardized = (features - center) / scale
    design = np.column_stack([np.ones(len(standardized)), standardized])
    penalty = np.eye(design.shape[1], dtype=float)
    penalty[0, 0] = 0.0
    regularization = 1.0
    try:
        coefficients = np.linalg.solve(
            design.T @ design + regularization * penalty,
            design.T @ targets,
        )
    except np.linalg.LinAlgError:
        coefficients = np.linalg.pinv(
            design.T @ design + regularization * penalty
        ) @ design.T @ targets

    recursive = values.tolist()
    prediction = recursive[-1]
    for _ in range(horizon):
        recent = np.asarray(recursive[-lag:][::-1], dtype=float)
        row = np.concatenate(
            [np.asarray([1.0]), (recent - center) / scale]
        )
        prediction = float(row @ coefficients)
        if not math.isfinite(prediction):
            return forecast_drift(history, horizon)
        recursive.append(prediction)
    return prediction


def linear_slope(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    x_mean = (len(values) - 1) / 2.0
    y_mean = mean(values)
    denominator = sum((index - x_mean) ** 2 for index in range(len(values)))
    if denominator <= 0:
        return 0.0
    return sum((index - x_mean) * (value - y_mean) for index, value in enumerate(values)) / denominator


def forecast_linear_trend(history: list[float], horizon: int) -> float:
    window = history[-min(20, len(history)) :]
    return window[-1] + horizon * linear_slope(window)


def variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    center = mean(values)
    return sum((value - center) ** 2 for value in values) / len(values)


def estimate_hurst(history: list[float]) -> float:
    points: list[tuple[float, float]] = []
    for lag in (1, 2, 4, 8):
        if len(history) <= lag + 4:
            continue
        increments = [history[index] - history[index - lag] for index in range(lag, len(history))]
        increment_variance = variance(increments)
        if increment_variance > 0:
            points.append((math.log(float(lag)), math.log(increment_variance)))
    if len(points) < 2:
        return 0.5
    x_mean = mean(point[0] for point in points)
    y_mean = mean(point[1] for point in points)
    denominator = sum((x - x_mean) ** 2 for x, _ in points)
    if denominator <= 0:
        return 0.5
    slope = sum((x - x_mean) * (y - y_mean) for x, y in points) / denominator
    return max(0.05, min(0.95, slope / 2.0))


def forecast_fractal_brownian_surface(history: list[float], horizon: int) -> float:
    hurst = estimate_hurst(history)
    slopes: list[tuple[float, float]] = []
    for lag in (1, 2, 4, 8):
        if len(history) <= lag:
            continue
        slope = (history[-1] - history[-1 - lag]) / lag
        weight = lag ** (hurst - 0.5)
        slopes.append((slope, weight))
    if not slopes:
        return history[-1]
    weighted_slope = sum(slope * weight for slope, weight in slopes) / sum(weight for _, weight in slopes)
    persistence = max(-0.50, min(1.0, 2.0 * hurst - 0.50))
    return history[-1] + horizon * weighted_slope * persistence


STRATEGIES: tuple[StrategySpec, ...] = (
    StrategySpec("naive_last", "baseline", "naive_last", "Last-observation baseline.", forecast_naive_last),
    StrategySpec("drift", "baseline", "drift", "Full-history drift baseline.", forecast_drift),
    StrategySpec("moving_average", "baseline", "moving_average", "Eight-observation mean baseline.", forecast_moving_average),
    StrategySpec(
        "exponential_smoothing",
        "baseline",
        "exponential_smoothing",
        "Fixed-alpha level baseline.",
        forecast_exponential_smoothing,
    ),
    StrategySpec("linear_trend", "baseline", "linear_trend", "Local linear-trend baseline.", forecast_linear_trend),
    StrategySpec(
        "seasonal_naive_source_period",
        "baseline",
        "seasonal_naive_source_period",
        "Cadence-specific seasonal-naive baseline.",
        forecast_naive_last,
    ),
    StrategySpec(
        "damped_holt_ets",
        "baseline",
        "damped_holt_ets",
        "Training-window-selected damped Holt/ETS baseline.",
        forecast_damped_holt_ets,
    ),
    StrategySpec(
        "autoregressive_ridge_source_lag",
        "baseline",
        "autoregressive_ridge_source_lag",
        "Source-lag ridge autoregression fitted inside each training window.",
        forecast_naive_last,
    ),
    StrategySpec(
        "fractal_brownian_surface",
        "geometry_family",
        "fractal_brownian_surface",
        "Hurst-conditioned multiscale increment analogue.",
        forecast_fractal_brownian_surface,
    ),
)


def source_baseline_parameters(series: dict[str, Any]) -> dict[str, Any]:
    source = str(series.get("source", "")).upper()
    parameters = dict(SOURCE_BASELINE_DEFAULTS.get(source, {}))
    overrides = parameters.pop("series_overrides", {})
    supplied = series.get("source_specific_baseline_parameters", {})
    if isinstance(supplied, dict):
        supplied_overrides = supplied.get("series_overrides", {})
        parameters.update(
            {
                key: value
                for key, value in supplied.items()
                if key != "series_overrides"
            }
        )
        if isinstance(supplied_overrides, dict):
            overrides = {**overrides, **supplied_overrides}
    series_override = (
        overrides.get(str(series.get("series_id", "")), {})
        if isinstance(overrides, dict)
        else {}
    )
    if isinstance(series_override, dict):
        parameters.update(series_override)
    return parameters


def forecast_strategy(
    spec: StrategySpec,
    history: list[float],
    horizon: int,
    parameters: dict[str, Any],
) -> float:
    if spec.name == "seasonal_naive_source_period":
        return forecast_seasonal_naive(
            history,
            horizon,
            int(parameters.get("seasonal_period", 1)),
        )
    if spec.name == "autoregressive_ridge_source_lag":
        return forecast_autoregressive_ridge(
            history,
            horizon,
            int(parameters.get("autoregressive_lag", 1)),
        )
    return spec.forecast(history, horizon)


def forecast_origins(length: int, initial_train: int) -> list[int]:
    origins = list(range(initial_train, length))
    if len(origins) <= MAX_ORIGINS_PER_SERIES:
        return origins
    selected: list[int] = []
    for index in range(MAX_ORIGINS_PER_SERIES):
        position = round(index * (len(origins) - 1) / (MAX_ORIGINS_PER_SERIES - 1))
        origin = origins[position]
        if not selected or origin != selected[-1]:
            selected.append(origin)
    return selected


def mase_scale(history: list[float]) -> float:
    differences = [abs(current - previous) for previous, current in zip(history, history[1:])]
    level_floor = max(abs(mean(history)) * 1e-9, 1e-12)
    return max(mean(differences) if differences else 0.0, level_floor)


def direction(value: float, tolerance: float = 1e-12) -> int:
    if value > tolerance:
        return 1
    if value < -tolerance:
        return -1
    return 0


def evaluate_series(
    series: dict[str, Any],
    baseline_names: set[str] | None = None,
) -> list[dict[str, Any]]:
    values = [float(value) for value in series.get("values", [])]
    if len(values) < MIN_SERIES_LENGTH:
        return []
    initial_train = max(20, len(values) // 2)
    parameters = source_baseline_parameters(series)
    selected_strategies = [
        spec
        for spec in STRATEGIES
        if spec.kind != "baseline"
        or baseline_names is None
        or spec.name in baseline_names
    ]
    rows: list[dict[str, Any]] = []
    for origin in forecast_origins(len(values), initial_train):
        history = values[:origin]
        scale = mase_scale(history)
        for horizon in FORECAST_HORIZONS:
            target_index = origin + horizon - 1
            if target_index >= len(values):
                continue
            actual = values[target_index]
            last = history[-1]
            evaluation_unit = f"{series['source']}|{series['series_id']}|{origin}|{horizon}"
            for spec in selected_strategies:
                predicted = float(
                    forecast_strategy(spec, history, horizon, parameters)
                )
                absolute_error = abs(actual - predicted)
                mase = absolute_error / scale
                directional_accuracy = float(direction(predicted - last) == direction(actual - last))
                rows.append(
                    {
                        "split": "frozen_measured_walk_forward",
                        "source": series["source"],
                        "series_id": series["series_id"],
                        "value_field": series["value_field"],
                        "origin": origin,
                        "horizon": horizon,
                        "evaluation_unit": evaluation_unit,
                        "strategy": spec.name,
                        "kind": spec.kind,
                        "family_id": spec.family_id,
                        "estimator_id": (
                            CANDIDATE_ESTIMATOR_ID
                            if spec.family_id == "fractal_brownian_surface"
                            else spec.family_id
                        ),
                        "source_baseline_parameters": (
                            parameters if spec.kind == "baseline" else {}
                        ),
                        "prospective_confirmation_eligible": bool(
                            series.get("prospective_confirmation_eligible")
                        ),
                        "actual": round(actual, 10),
                        "predicted": round(predicted, 10),
                        "absolute_error": round(absolute_error, 10),
                        "mase": round(mase, 10),
                        "directional_accuracy": directional_accuracy,
                        "score": round(1.0 / (1.0 + mase), 10),
                    }
                )
    return rows


def evaluate_live_sources(
    source_refs: list[dict[str, Any]], root: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    accepted_series: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    verified_hash_modes: set[str] = set()
    executed_baselines_by_source: dict[str, list[str]] = {}
    available_baselines = {
        spec.name for spec in STRATEGIES if spec.kind == "baseline"
    }
    for source_ref in source_refs:
        source = str(source_ref.get("source", "UNKNOWN")).upper()
        compatibility_mode = str(source_ref.get("compatibility_mode", ""))
        if compatibility_mode and compatibility_mode != "direct_measured_replay":
            skipped.append(
                {
                    "source": source,
                    "reason": "source_not_authorized_for_direct_measured_replay",
                    "compatibility_mode": compatibility_mode,
                }
            )
            continue
        if (
            "direct_performance_input_allowed" in source_ref
            and not bool(source_ref.get("direct_performance_input_allowed"))
        ):
            skipped.append(
                {
                    "source": source,
                    "reason": "direct_performance_input_not_allowed",
                    "compatibility_mode": compatibility_mode or "unspecified",
                }
            )
            continue
        relative_path = str(source_ref.get("snapshot_json", ""))
        path = root / relative_path
        if not relative_path or not path.exists():
            skipped.append({"source": source, "reason": "snapshot_missing", "snapshot_json": relative_path})
            continue
        expected_snapshot_sha256 = str(
            source_ref.get("snapshot_sha256", "")
        ).strip().lower()
        if expected_snapshot_sha256:
            if (
                len(expected_snapshot_sha256) != 64
                or any(
                    character not in "0123456789abcdef"
                    for character in expected_snapshot_sha256
                )
            ):
                skipped.append(
                    {
                        "source": source,
                        "reason": "snapshot_hash_invalid",
                        "snapshot_json": relative_path,
                    }
                )
                continue
        try:
            snapshot_bytes = path.read_bytes()
            snapshot = json.loads(snapshot_bytes.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            skipped.append({"source": source, "reason": "snapshot_unreadable", "snapshot_json": relative_path})
            continue
        if expected_snapshot_sha256:
            embedded_snapshot_sha256 = str(
                snapshot.get("sha256", "") if isinstance(snapshot, dict) else ""
            ).strip().lower()
            if embedded_snapshot_sha256:
                hash_mode = "canonical_unsigned_payload"
                unsigned_snapshot = {
                    key: value
                    for key, value in snapshot.items()
                    if key != "sha256"
                } if isinstance(snapshot, dict) else {}
                observed_snapshot_sha256 = hashlib.sha256(
                    json.dumps(
                        unsigned_snapshot,
                        sort_keys=True,
                        separators=(",", ":"),
                        default=str,
                    ).encode("utf-8")
                ).hexdigest()
                hash_matches = (
                    embedded_snapshot_sha256 == expected_snapshot_sha256
                    and observed_snapshot_sha256 == expected_snapshot_sha256
                )
            else:
                hash_mode = "file_bytes"
                observed_snapshot_sha256 = hashlib.sha256(snapshot_bytes).hexdigest()
                hash_matches = observed_snapshot_sha256 == expected_snapshot_sha256
            if not hash_matches:
                skipped.append(
                    {
                        "source": source,
                        "reason": "snapshot_hash_mismatch",
                        "snapshot_json": relative_path,
                        "hash_mode": hash_mode,
                        "expected_snapshot_sha256": expected_snapshot_sha256,
                        "embedded_snapshot_sha256": embedded_snapshot_sha256,
                        "observed_snapshot_sha256": observed_snapshot_sha256,
                    }
                )
                continue
            verified_hash_modes.add(hash_mode)
        extracted = extract_series(snapshot if isinstance(snapshot, dict) else {}, source)
        qualifying = [
            series
            for series in extracted
            if int(series["row_count"]) >= MIN_SERIES_LENGTH
            and bool(series.get("chronology_quality_pass"))
        ]
        if not qualifying:
            skipped.append(
                {
                    "source": source,
                    "reason": "no_qualified_chronological_series",
                    "minimum_length": MIN_SERIES_LENGTH,
                    "longest_series": max((int(series["row_count"]) for series in extracted), default=0),
                    "duplicate_time_series_count": sum(
                        not bool(series.get("chronology_quality_pass"))
                        for series in extracted
                    ),
                }
            )
            continue
        registered_baselines = source_ref.get("source_specific_baselines")
        baseline_names = (
            {
                str(name)
                for name in registered_baselines
                if str(name)
            }
            if isinstance(registered_baselines, list)
            else None
        )
        missing_baselines = sorted(
            (baseline_names or set()) - available_baselines
        )
        if missing_baselines:
            skipped.append(
                {
                    "source": source,
                    "reason": "registered_baseline_implementation_missing",
                    "snapshot_json": relative_path,
                    "missing_baselines": missing_baselines,
                }
            )
            continue
        executed_baselines_by_source[source] = sorted(
            baseline_names if baseline_names is not None else available_baselines
        )
        for series in qualifying:
            series["source_specific_baseline_parameters"] = source_ref.get(
                "source_specific_baseline_parameters", {}
            )
            accepted_series.append({key: value for key, value in series.items() if key != "values"})
            rows.extend(evaluate_series(series, baseline_names))

    summary = {
        "source_ref_count": len(source_refs),
        "accepted_source_count": len({series["source"] for series in accepted_series}),
        "accepted_series_count": len(accepted_series),
        "skipped_source_count": len(skipped),
        "minimum_series_length": MIN_SERIES_LENGTH,
        "forecast_horizons": list(FORECAST_HORIZONS),
        "max_origins_per_series": MAX_ORIGINS_PER_SERIES,
        "evaluation_row_count": len(rows),
        "accepted_series": accepted_series,
        "skipped_sources": skipped,
        "snapshot_hash_control": (
            "registered snapshots from providers are bound to their embedded digest and "
            "recomputed canonical unsigned payload; registered snapshots without an "
            "embedded digest are bound to exact file bytes before acceptance"
        ),
        "verified_snapshot_hash_modes": sorted(verified_hash_modes),
        "executed_source_specific_baselines": executed_baselines_by_source,
        "leakage_control": "expanding history ends immediately before each forecast origin",
        "claim_boundary": EVIDENCE_BOUNDARY,
    }
    return rows, summary


def aggregate(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["strategy"]), []).append(row)
    result: dict[str, dict[str, Any]] = {}
    for strategy, items in grouped.items():
        first = items[0]
        result[strategy] = {
            "strategy": strategy,
            "kind": first["kind"],
            "family_id": first["family_id"],
            "estimator_id": first.get("estimator_id", first["family_id"]),
            "scenario_count": len(items),
            "source_count": len({str(item["source"]) for item in items}),
            "series_count": len({(str(item["source"]), str(item["series_id"])) for item in items}),
            "mean_score": round(mean(float(item["score"]) for item in items), 6),
            "median_score": round(median(float(item["score"]) for item in items), 6),
            "mean_mase": round(mean(float(item["mase"]) for item in items), 6),
            "median_mase": round(median(float(item["mase"]) for item in items), 6),
            "mean_directional_accuracy": round(
                mean(float(item["directional_accuracy"]) for item in items), 6
            ),
        }
    return result


def ranked_aggregate(aggregated: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = list(aggregated.values())
    rows.sort(
        key=lambda row: (
            -float(row["mean_score"]),
            float(row["mean_mase"]),
            -float(row["mean_directional_accuracy"]),
            str(row["strategy"]),
        )
    )
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def score_against_baseline(ranked: list[dict[str, Any]]) -> dict[str, Any]:
    baselines = [row for row in ranked if row["kind"] == "baseline"]
    geometries = [row for row in ranked if row["kind"] == "geometry_family"]
    best_baseline = baselines[0] if baselines else None
    best_geometry = geometries[0] if geometries else None
    if not best_baseline or not best_geometry:
        return {"gate": "missing_baseline_or_geometry"}
    score_delta = float(best_geometry["mean_score"]) - float(best_baseline["mean_score"])
    mase_delta = float(best_geometry["mean_mase"]) - float(best_baseline["mean_mase"])
    return {
        "gate": "candidate_geometry_beats_best_baseline" if score_delta > 0 else "baseline_still_leads",
        "best_geometry": best_geometry,
        "best_baseline": best_baseline,
        "score_delta_vs_best_baseline": round(score_delta, 6),
        "mase_delta_vs_best_baseline": round(mase_delta, 6),
        "claim_language": EVIDENCE_BOUNDARY,
    }
