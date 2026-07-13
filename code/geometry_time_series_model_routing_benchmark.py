"""Measured-source walk-forward benchmark for time-series model routing.

The benchmark uses frozen public-source snapshots and evaluates every strategy
on the same expanding-window forecast origins. It is software replay evidence,
not a trading system, operational forecast, field validation, or dollar proof.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any, Callable


EVIDENCE_BOUNDARY = (
    "Frozen measured-source walk-forward software benchmark only. Models use "
    "past values at each forecast origin and are compared on identical future "
    "observations. Results do not establish operational forecasting, field "
    "validation, trading edge, realized savings, or real-dollar performance."
)

MIN_SERIES_LENGTH = 24
MAX_ORIGINS_PER_SERIES = 48
FORECAST_HORIZONS = (1, 3, 5)

GROUP_FIELDS = (
    "series_id",
    "symbol",
    "pair",
    "ticker",
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

ForecastFn = Callable[[list[float], int], float]


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
    for field in TIME_FIELDS:
        value = row.get(field)
        if value is not None and str(value).strip():
            if isinstance(value, (int, float)):
                return (f"{float(value):030.9f}", index)
            return (str(value).strip(), index)
    year = str(row.get("year", "")).strip()
    period = str(row.get("period", "")).strip().upper().removeprefix("M")
    if year:
        return (f"{year}-{period.zfill(2)}", index)
    return (f"{index:012d}", index)


def extract_series(snapshot: dict[str, Any], source: str) -> list[dict[str, Any]]:
    rows = snapshot.get("rows", [])
    if not isinstance(rows, list):
        return []
    clean_rows = [row for row in rows if isinstance(row, dict)]
    if not clean_rows:
        return []

    group_field = choose_group_field(clean_rows)
    value_field = choose_value_field(clean_rows)
    if not value_field:
        return []

    grouped: dict[str, list[tuple[tuple[str, int], float]]] = {}
    for index, row in enumerate(clean_rows):
        value = as_float(row.get(value_field))
        if value is None:
            continue
        group = str(row.get(group_field, source)).strip() if group_field else source
        grouped.setdefault(group or source, []).append((row_time_key(row, index), value))

    extracted: list[dict[str, Any]] = []
    for group, items in sorted(grouped.items()):
        items.sort(key=lambda item: item[0])
        values = [value for _, value in items]
        extracted.append(
            {
                "source": source,
                "series_id": group,
                "group_field": group_field or "source",
                "value_field": value_field,
                "row_count": len(values),
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
        "fractal_brownian_surface",
        "geometry_family",
        "fractal_brownian_surface",
        "Hurst-conditioned multiscale increment analogue.",
        forecast_fractal_brownian_surface,
    ),
)


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


def evaluate_series(series: dict[str, Any]) -> list[dict[str, Any]]:
    values = [float(value) for value in series.get("values", [])]
    if len(values) < MIN_SERIES_LENGTH:
        return []
    initial_train = max(20, len(values) // 2)
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
            for spec in STRATEGIES:
                predicted = float(spec.forecast(history, horizon))
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
    for source_ref in source_refs:
        source = str(source_ref.get("source", "UNKNOWN")).upper()
        relative_path = str(source_ref.get("snapshot_json", ""))
        path = root / relative_path
        if not relative_path or not path.exists():
            skipped.append({"source": source, "reason": "snapshot_missing", "snapshot_json": relative_path})
            continue
        try:
            snapshot = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            skipped.append({"source": source, "reason": "snapshot_unreadable", "snapshot_json": relative_path})
            continue
        extracted = extract_series(snapshot if isinstance(snapshot, dict) else {}, source)
        qualifying = [series for series in extracted if int(series["row_count"]) >= MIN_SERIES_LENGTH]
        if not qualifying:
            skipped.append(
                {
                    "source": source,
                    "reason": "no_series_meets_minimum_length",
                    "minimum_length": MIN_SERIES_LENGTH,
                    "longest_series": max((int(series["row_count"]) for series in extracted), default=0),
                }
            )
            continue
        for series in qualifying:
            accepted_series.append({key: value for key, value in series.items() if key != "values"})
            rows.extend(evaluate_series(series))

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
