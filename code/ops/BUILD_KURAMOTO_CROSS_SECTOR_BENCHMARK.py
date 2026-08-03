"""Build a claim-safe, actual-data Kuramoto cross-sector benchmark.

The runner admits only explicitly configured local public-data snapshots. It
uses rolling one-step origins, identical history for every strategy, paired
loss deltas, deterministic block bootstrap intervals, and Holm correction.
Retrospective results remain exploratory until a prospective external replay.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import random
import time
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Callable

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = Path(__file__).resolve()
PROTOCOL_PATH = ROOT / "config" / "kuramoto_cross_sector_benchmark_protocol_v1.json"
EIA_RUNNER_PATH = ROOT / "code" / "eia_grid_wave_champion_benchmark.py"
LIVE_MANIFEST_PATH = ROOT / "out" / "ops" / "geometry_live_source_manifest_latest.json"
EXTERNAL_PROTOCOL_TEMPLATE_PATH = (
    ROOT / "config" / "kuramoto_sector_external_evaluator_protocol_template_v1.json"
)
EXTERNAL_RESULT_TEMPLATE_PATH = (
    ROOT
    / "config"
    / "kuramoto_sector_external_evaluator_result_receipt_template_v1.json"
)
OUT_DIR = ROOT / "out" / "ops"
OUT_JSON = OUT_DIR / "kuramoto_cross_sector_benchmark_latest.json"
OUT_ROWS = OUT_DIR / "kuramoto_cross_sector_benchmark_rows_latest.csv"
OUT_MANIFEST = OUT_DIR / "kuramoto_cross_sector_benchmark_manifest_latest.json"
OUT_MD = ROOT / "docs" / f"KURAMOTO_CROSS_SECTOR_BENCHMARK_{date.today().isoformat()}.md"

SCHEMA = "lumencore.kuramoto_cross_sector_benchmark.v1"
CLAIM_BOUNDARY = (
    "Retrospective local-snapshot software evidence plus a separately frozen EIA "
    "public-data benchmark. It does not establish cross-sector efficiency, field "
    "performance, realized savings, safety, procurement acceptance, external "
    "validation, trading edge, or an unbeatable claim."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object in {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    payload = read_json(path)
    if payload.get("schema") != "lumencore.kuramoto_cross_sector_benchmark_protocol.v1":
        raise ValueError("unexpected Kuramoto cross-sector protocol schema")
    ids = [str(row.get("id")) for row in payload.get("baselines", [])]
    if len(ids) != len(set(ids)) or not ids:
        raise ValueError("baseline ids must be nonempty and unique")
    source_ids = [str(row.get("id")) for row in payload.get("retrospective_sources", [])]
    if len(source_ids) != len(set(source_ids)) or not source_ids:
        raise ValueError("retrospective source ids must be nonempty and unique")
    return payload


def load_eia_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "eia_grid_wave_champion_for_cross_sector", EIA_RUNNER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load EIA benchmark module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_timestamp(value: str, *, year_override: int | None = None) -> datetime:
    raw = value.strip()
    if not raw:
        raise ValueError("blank timestamp")
    parsed: datetime | None = None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        pass
    if parsed is None:
        for pattern in ("%b %Y", "%m/%d/%Y", "%Y%m%dT%H", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(raw, pattern)
                break
            except ValueError:
                continue
    if parsed is None:
        raise ValueError(f"unsupported timestamp: {raw}")
    if year_override is not None:
        parsed = parsed.replace(year=int(year_override))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def load_source_series(
    source: dict[str, Any], protocol: dict[str, Any]
) -> tuple[list[datetime], list[float], dict[str, Any]]:
    path = ROOT / str(source["path"])
    if not path.exists() or not path.is_file():
        raise ValueError(f"source file missing: {source['path']}")
    if source.get("format") != "csv":
        raise ValueError(f"unsupported source format for {source['id']}")

    parsed: list[tuple[datetime, float]] = []
    empty_rows = 0
    invalid_rows = 0
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        for _ in range(int(source.get("skip_rows", 0))):
            next(handle, None)
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"missing CSV header for {source['id']}")
        required = {str(source["date_column"]), str(source["value_column"])}
        if not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"missing configured columns for {source['id']}: {sorted(required - set(reader.fieldnames))}"
            )
        for row in reader:
            date_raw = str(row.get(str(source["date_column"])) or "").strip()
            value_raw = str(row.get(str(source["value_column"])) or "").strip()
            if not date_raw and not value_raw:
                empty_rows += 1
                continue
            if not date_raw or not value_raw:
                invalid_rows += 1
                continue
            try:
                timestamp = parse_timestamp(
                    date_raw,
                    year_override=(
                        int(source["date_year_override"])
                        if source.get("date_year_override") is not None
                        else None
                    ),
                )
                value = float(value_raw.replace(",", ""))
            except (TypeError, ValueError):
                invalid_rows += 1
                continue
            if not math.isfinite(value):
                invalid_rows += 1
                continue
            parsed.append((timestamp, value))

    parsed.sort(key=lambda item: item[0])
    timestamp_counts: dict[datetime, int] = defaultdict(int)
    for timestamp, _value in parsed:
        timestamp_counts[timestamp] += 1
    duplicate_count = sum(count - 1 for count in timestamp_counts.values() if count > 1)
    if duplicate_count and protocol["source_admission"]["reject_duplicate_timestamps"]:
        raise ValueError(f"duplicate timestamps in {source['id']}: {duplicate_count}")
    if invalid_rows and protocol["source_admission"]["reject_nonfinite_values"]:
        raise ValueError(f"invalid or nonfinite rows in {source['id']}: {invalid_rows}")

    dates = [row[0] for row in parsed]
    values = [row[1] for row in parsed]
    minimum_rows = max(
        int(protocol["source_admission"]["minimum_numeric_rows"]),
        int(source["minimum_history"]) + int(protocol["promotion_gate"]["minimum_evaluation_points"]),
    )
    if len(values) < minimum_rows:
        raise ValueError(
            f"insufficient admitted rows for {source['id']}: {len(values)} < {minimum_rows}"
        )
    if any(left >= right for left, right in zip(dates, dates[1:])):
        raise ValueError(f"timestamps are not strictly increasing for {source['id']}")

    receipt = {
        "source_id": source["id"],
        "sector": source["sector"],
        "publisher": source["publisher"],
        "source_url": source["source_url"],
        "path": rel(path),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
        "accepted_numeric_rows": len(values),
        "empty_row_count": empty_rows,
        "invalid_row_count": invalid_rows,
        "duplicate_timestamp_count": duplicate_count,
        "first_timestamp": dates[0].isoformat(),
        "last_timestamp": dates[-1].isoformat(),
        "cadence": source["cadence"],
        "native_unit": source["native_unit"],
        "read_only": True,
        "credential_serialized": False,
    }
    return dates, values, receipt


def forecast_seasonal_naive(history: list[float], season: int) -> float:
    return float(history[-season]) if len(history) >= season else float(history[-1])


def forecast_rolling_mean(history: list[float], season: int) -> float:
    window = history[-max(1, min(season, len(history))) :]
    return float(mean(window))


def forecast_ewma(history: list[float], alpha: float = 0.2) -> float:
    level = float(history[0])
    for value in history[1:]:
        level = alpha * float(value) + (1.0 - alpha) * level
    return level


def forecast_linear_trend(history: list[float], season: int) -> float:
    y = np.asarray(history[-max(8, min(len(history), season * 2)) :], dtype=float)
    if y.size < 3:
        return float(y[-1])
    x = np.arange(y.size, dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    return float(intercept + slope * y.size)


def forecast_kuramoto_generic(
    history: list[float],
    periods: tuple[float, ...],
    *,
    coupling: float,
    ridge: float,
    eia: Any,
) -> float:
    (
        center,
        scale,
        amplitudes,
        phases,
        frequencies,
        trend_value,
        _length,
    ) = eia.fitted_seasonal_oscillators(history, periods, ridge=ridge)
    count = len(phases)
    derivatives = np.empty(count)
    for index in range(count):
        coupling_term = sum(math.sin(phases[j] - phases[index]) for j in range(count))
        derivatives[index] = frequencies[index] + coupling * coupling_term / count
    future_phases = phases + derivatives
    prediction = trend_value + float(np.sum(amplitudes * np.cos(future_phases)))
    return center + scale * prediction


def seasonal_mase_scale(history: list[float], season: int) -> float:
    if len(history) <= season:
        return max(abs(mean(history)) * 1e-9, 1e-9)
    deltas = [
        abs(history[index] - history[index - season])
        for index in range(season, len(history))
    ]
    return max(mean(deltas), abs(mean(history)) * 1e-9, 1e-9)


def direction(value: float, tolerance: float = 1e-12) -> int:
    if value > tolerance:
        return 1
    if value < -tolerance:
        return -1
    return 0


def build_forecasters(
    source: dict[str, Any], protocol: dict[str, Any], eia: Any
) -> dict[str, Callable[[list[float]], float]]:
    season = int(source["seasonal_lag"])
    periods = tuple(float(value) for value in source["oscillator_periods"])
    candidate = protocol["candidate"]
    lag = max(2, min(14, season))
    forecasters: dict[str, Callable[[list[float]], float]] = {
        "naive_last": eia.forecast_naive_last,
        "seasonal_naive": lambda history: forecast_seasonal_naive(history, season),
        "rolling_mean_season": lambda history: forecast_rolling_mean(history, season),
        "ewma_0_2": forecast_ewma,
        "linear_trend": lambda history: forecast_linear_trend(history, season),
        "kalman_local_linear_trend": eia.forecast_kalman_local_linear,
        "autoregressive_ridge": lambda history: eia.forecast_autoregressive_ridge(
            history, lag=lag, ridge=1.0
        ),
        "fft_extrapolation_top5": eia.forecast_fft,
        "uncoupled_harmonic": lambda history: forecast_kuramoto_generic(
            history,
            periods,
            coupling=0.0,
            ridge=float(candidate["ridge"]),
            eia=eia,
        ),
        str(candidate["id"]): lambda history: forecast_kuramoto_generic(
            history,
            periods,
            coupling=float(candidate["coupling"]),
            ridge=float(candidate["ridge"]),
            eia=eia,
        ),
    }
    expected = {str(row["id"]) for row in protocol["baselines"]} | {str(candidate["id"])}
    if set(forecasters) != expected:
        raise ValueError("forecaster implementation set does not match the frozen protocol")
    return forecasters


def evaluate_source(
    source: dict[str, Any],
    dates: list[datetime],
    values: list[float],
    protocol: dict[str, Any],
    eia: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    forecasters = build_forecasters(source, protocol, eia)
    candidate_id = str(protocol["candidate"]["id"])
    minimum_history = int(source["minimum_history"])
    maximum_history = int(source["maximum_history"])
    evaluation_points = int(source["evaluation_points"])
    stride = int(source["origin_stride"])
    season = int(source["seasonal_lag"])
    start_index = max(minimum_history, len(values) - evaluation_points)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for index in range(start_index, len(values), stride):
        history = values[max(0, index - maximum_history) : index]
        if len(history) < minimum_history or len(history) <= season:
            continue
        target = float(values[index])
        previous = float(history[-1])
        mase_scale = seasonal_mase_scale(history, season)
        predictions: dict[str, tuple[float, float]] = {}
        for strategy, forecaster in forecasters.items():
            started = time.perf_counter()
            try:
                predicted = float(forecaster(history))
            except (ValueError, np.linalg.LinAlgError, FloatingPointError, OverflowError) as exc:
                failures.append(
                    {
                        "timestamp": dates[index].isoformat(),
                        "strategy": strategy,
                        "failure": type(exc).__name__,
                    }
                )
                predictions = {}
                break
            runtime_ms = (time.perf_counter() - started) * 1000.0
            if not math.isfinite(predicted):
                failures.append(
                    {
                        "timestamp": dates[index].isoformat(),
                        "strategy": strategy,
                        "failure": "nonfinite_prediction",
                    }
                )
                predictions = {}
                break
            predictions[strategy] = (predicted, runtime_ms)
        if set(predictions) != set(forecasters):
            continue
        for strategy, (predicted, runtime_ms) in predictions.items():
            error = abs(target - predicted)
            rows.append(
                {
                    "source_id": source["id"],
                    "sector": source["sector"],
                    "target_timestamp": dates[index].isoformat(),
                    "strategy": strategy,
                    "kind": "candidate" if strategy == candidate_id else "baseline",
                    "actual": target,
                    "predicted": predicted,
                    "absolute_error": error,
                    "squared_error": (target - predicted) ** 2,
                    "seasonal_mase": error / mase_scale,
                    "directional_accuracy": float(
                        direction(predicted - previous) == direction(target - previous)
                    ),
                    "runtime_ms": runtime_ms,
                }
            )

    origin_count = len({row["target_timestamp"] for row in rows})
    summary = {
        "requested_evaluation_points": evaluation_points,
        "evaluation_origin_count": origin_count,
        "strategy_count": len(forecasters),
        "forecast_row_count": len(rows),
        "failed_origin_count": len({row["timestamp"] for row in failures}),
        "failures": failures,
        "first_evaluation_timestamp": min(
            (row["target_timestamp"] for row in rows), default=None
        ),
        "last_evaluation_timestamp": max(
            (row["target_timestamp"] for row in rows), default=None
        ),
        "history_only_at_each_origin": True,
        "retrospective_not_untouched": True,
    }
    return rows, summary


def strategy_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["strategy"])].append(row)
    metrics: list[dict[str, Any]] = []
    for strategy, items in grouped.items():
        metrics.append(
            {
                "strategy": strategy,
                "kind": items[0]["kind"],
                "row_count": len(items),
                "mean_absolute_error": mean(float(row["absolute_error"]) for row in items),
                "median_absolute_error": median(float(row["absolute_error"]) for row in items),
                "root_mean_squared_error": math.sqrt(
                    mean(float(row["squared_error"]) for row in items)
                ),
                "mean_seasonal_mase": mean(float(row["seasonal_mase"]) for row in items),
                "mean_directional_accuracy": mean(
                    float(row["directional_accuracy"]) for row in items
                ),
                "mean_runtime_ms": mean(float(row["runtime_ms"]) for row in items),
            }
        )
    metrics.sort(
        key=lambda row: (
            float(row["mean_absolute_error"]),
            float(row["root_mean_squared_error"]),
            str(row["strategy"]),
        )
    )
    for rank, row in enumerate(metrics, start=1):
        row["rank"] = rank
    return metrics


def exact_two_sided_sign_test(values: list[float]) -> float | None:
    nonzero = [value for value in values if abs(value) > 1e-12]
    count = len(nonzero)
    if count == 0:
        return None
    wins = sum(1 for value in nonzero if value > 0)
    lower = min(wins, count - wins)
    cumulative = sum(math.comb(count, index) for index in range(lower + 1)) / (2**count)
    return min(1.0, 2.0 * cumulative)


def percentile(values: list[float], proportion: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("cannot compute percentile of empty sequence")
    position = proportion * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return float(ordered[lower])
    weight = position - lower
    return float(ordered[lower] * (1.0 - weight) + ordered[upper] * weight)


def nonoverlapping_block_means(values: list[float], block_length: int) -> list[float]:
    return [
        mean(values[index : index + block_length])
        for index in range(0, len(values), block_length)
        if values[index : index + block_length]
    ]


def deterministic_block_bootstrap(
    values: list[float],
    *,
    block_length: int,
    draws: int,
    seed: int,
) -> dict[str, Any]:
    blocks = nonoverlapping_block_means(values, block_length)
    if not blocks:
        return {
            "block_length": block_length,
            "block_count": 0,
            "draws": draws,
            "ci95_lower": None,
            "ci95_upper": None,
        }
    rng = random.Random(seed)
    distribution = [
        mean(rng.choice(blocks) for _ in range(len(blocks))) for _ in range(draws)
    ]
    return {
        "block_length": block_length,
        "block_count": len(blocks),
        "draws": draws,
        "ci95_lower": percentile(distribution, 0.025),
        "ci95_upper": percentile(distribution, 0.975),
    }


def holm_adjust(rows: list[dict[str, Any]]) -> None:
    candidates = [
        (index, float(row["sign_test_p_value"]))
        for index, row in enumerate(rows)
        if row.get("sign_test_p_value") is not None
    ]
    candidates.sort(key=lambda item: item[1])
    running = 0.0
    count = len(candidates)
    for rank, (index, p_value) in enumerate(candidates):
        adjusted = min(1.0, p_value * (count - rank))
        running = max(running, adjusted)
        rows[index]["holm_adjusted_p_value"] = running
    for row in rows:
        row.setdefault("holm_adjusted_p_value", None)


def build_source_comparisons(
    rows: list[dict[str, Any]],
    source: dict[str, Any],
    protocol: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidate_id = str(protocol["candidate"]["id"])
    by_strategy: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_strategy[str(row["strategy"])][str(row["target_timestamp"])] = row
    candidate_rows = by_strategy[candidate_id]
    metrics = strategy_metrics(rows)
    metric_map = {str(row["strategy"]): row for row in metrics}
    season = int(source["seasonal_lag"])
    origin_count = len(candidate_rows)
    block_length = max(2, min(season, int(math.floor(math.sqrt(max(origin_count, 1))))))
    comparisons: list[dict[str, Any]] = []

    for baseline in protocol["baselines"]:
        baseline_id = str(baseline["id"])
        common = sorted(set(candidate_rows) & set(by_strategy[baseline_id]))
        deltas = [
            float(by_strategy[baseline_id][target]["absolute_error"])
            - float(candidate_rows[target]["absolute_error"])
            for target in common
        ]
        baseline_mae = float(metric_map[baseline_id]["mean_absolute_error"])
        candidate_mae = float(metric_map[candidate_id]["mean_absolute_error"])
        bootstrap = deterministic_block_bootstrap(
            deltas,
            block_length=block_length,
            draws=int(protocol["evaluation"]["bootstrap_draws"]),
            seed=int(protocol["evaluation"]["bootstrap_seed"])
            + int(hashlib.sha256(f"{source['id']}|{baseline_id}".encode()).hexdigest()[:8], 16),
        )
        blocks = nonoverlapping_block_means(deltas, block_length)
        comparison = {
            "baseline": baseline_id,
            "paired_origin_count": len(common),
            "candidate_mean_absolute_error": candidate_mae,
            "baseline_mean_absolute_error": baseline_mae,
            "mean_absolute_error_delta": mean(deltas) if deltas else None,
            "relative_mae_improvement_percent": (
                100.0 * (baseline_mae - candidate_mae) / baseline_mae
                if baseline_mae > 0
                else None
            ),
            "candidate_beats_baseline_on_mean": bool(
                deltas and mean(deltas) > 0
            ),
            "paired_block_count": len(blocks),
            "sign_test_p_value": exact_two_sided_sign_test(blocks),
            "block_bootstrap": bootstrap,
        }
        comparisons.append(comparison)

    holm_adjust(comparisons)
    threshold = float(protocol["promotion_gate"]["require_holm_adjusted_p_at_most"])
    for row in comparisons:
        lower = row["block_bootstrap"].get("ci95_lower")
        adjusted = row.get("holm_adjusted_p_value")
        row["passes_comparison_gate"] = bool(
            row["candidate_beats_baseline_on_mean"]
            and lower is not None
            and float(lower) > 0
            and adjusted is not None
            and float(adjusted) <= threshold
        )
    return comparisons, metrics


def summarize_source(
    source: dict[str, Any],
    receipt: dict[str, Any],
    evaluation: dict[str, Any],
    comparisons: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
    protocol: dict[str, Any],
) -> dict[str, Any]:
    candidate_id = str(protocol["candidate"]["id"])
    candidate = next(row for row in metrics if row["strategy"] == candidate_id)
    baselines = [row for row in metrics if row["kind"] == "baseline"]
    best_baseline = min(
        baselines,
        key=lambda row: (
            float(row["mean_absolute_error"]),
            float(row["root_mean_squared_error"]),
            str(row["strategy"]),
        ),
    )
    best_comparison = next(
        row for row in comparisons if row["baseline"] == best_baseline["strategy"]
    )
    beats_every_mean = all(row["candidate_beats_baseline_on_mean"] for row in comparisons)
    every_comparison_pass = all(row["passes_comparison_gate"] for row in comparisons)
    minimum_points_pass = (
        int(evaluation["evaluation_origin_count"])
        >= int(protocol["promotion_gate"]["minimum_evaluation_points"])
    )
    retrospective_signal = bool(
        minimum_points_pass
        and beats_every_mean
        and every_comparison_pass
        and best_comparison["passes_comparison_gate"]
    )
    return {
        "source_id": source["id"],
        "sector": source["sector"],
        "native_unit": source["native_unit"],
        "cadence": source["cadence"],
        "source_sha256": receipt["sha256"],
        "evaluation": evaluation,
        "candidate": candidate,
        "best_baseline": best_baseline,
        "candidate_rank": candidate["rank"],
        "strategy_count": len(metrics),
        "comparisons": comparisons,
        "beats_every_baseline_on_mean": beats_every_mean,
        "every_comparison_gate_pass": every_comparison_pass,
        "best_baseline_comparison_pass": best_comparison["passes_comparison_gate"],
        "relative_mae_improvement_vs_best_percent": best_comparison[
            "relative_mae_improvement_percent"
        ],
        "retrospective_signal": retrospective_signal,
        "prospective_holdout_complete": False,
        "external_replication_complete": False,
        "sector_efficiency_claim_allowed": False,
        "status": (
            "RETROSPECTIVE_SIGNAL_ONLY_PROSPECTIVE_EXTERNAL_REPLAY_REQUIRED"
            if retrospective_signal
            else "NO_KURAMOTO_GAIN_PROVEN_ON_THIS_SOURCE"
        ),
    }


def anchor_eia_result(anchor: dict[str, Any], eia: Any) -> dict[str, Any]:
    protocol_path = ROOT / str(anchor["protocol_path"])
    panel_path = ROOT / str(anchor["panel_path"])
    result_path = ROOT / str(anchor["result_path"])
    if not protocol_path.exists() or not panel_path.exists() or not result_path.exists():
        raise ValueError(f"anchored benchmark files missing for {anchor['id']}")
    report = read_json(result_path)
    if report.get("schema") != "eia_grid_wave_champion_benchmark.v1":
        raise ValueError("unexpected anchored EIA result schema")
    protocol_sha = file_sha256(protocol_path)
    if report.get("protocol", {}).get("sha256") != protocol_sha:
        raise ValueError("anchored EIA protocol hash mismatch")
    panel = eia.load_panel(panel_path)
    if report.get("panel", {}).get("row_chain_sha256") != panel.get("row_chain_sha256"):
        raise ValueError("anchored EIA panel hash mismatch")

    candidate_id = str(anchor["required_candidate_id"])
    leaderboard = report.get("holdout_leaderboard", [])
    candidate = next(
        (row for row in leaderboard if row.get("strategy") == candidate_id), None
    )
    if candidate is None:
        raise ValueError("anchored EIA result lacks required Kuramoto candidate")
    baselines = [
        row
        for row in leaderboard
        if row.get("kind") in {"algorithmic_baseline", "official_baseline"}
    ]
    best_baseline = min(
        baselines,
        key=lambda row: (
            float(row["mean_absolute_error_mwh"]),
            float(row["mean_seasonal_mase_7"]),
            str(row["strategy"]),
        ),
    )
    candidate_mae = float(candidate["mean_absolute_error_mwh"])
    baseline_mae = float(best_baseline["mean_absolute_error_mwh"])
    improvement = 100.0 * (baseline_mae - candidate_mae) / baseline_mae
    selected_id = str(report.get("selection", {}).get("selected_wave_candidate"))
    return {
        "anchor_id": anchor["id"],
        "sector": anchor["sector"],
        "evidence_class": anchor["evidence_class"],
        "generated_utc": report.get("generated_utc"),
        "protocol_path": anchor["protocol_path"],
        "protocol_sha256": protocol_sha,
        "protocol_frozen_commit": report.get("protocol", {}).get("frozen_commit"),
        "panel_path": anchor["panel_path"],
        "panel_row_chain_sha256": panel.get("row_chain_sha256"),
        "result_path": anchor["result_path"],
        "result_sha256": file_sha256(result_path),
        "authority_count": report.get("panel", {}).get("authority_count"),
        "candidate": candidate,
        "best_baseline": best_baseline,
        "strategy_count": len(leaderboard),
        "candidate_selected_on_development": selected_id == candidate_id,
        "development_selected_wave_candidate": selected_id,
        "relative_mae_improvement_vs_best_percent": improvement,
        "candidate_beats_best_baseline_on_mean": improvement > 0,
        "prospective_holdout_complete": True,
        "external_replication_complete": bool(
            report.get("promotion_gate", {}).get("external_replication_complete")
        ),
        "sector_efficiency_claim_allowed": False,
        "status": (
            "POSITIVE_INTERNAL_EIA_SIGNAL_EXTERNAL_REPLICATION_REQUIRED"
            if improvement > 0
            else "NEGATIVE_KURAMOTO_EVIDENCE"
        ),
        "claim_boundary": report.get("claim_boundary"),
    }


def live_breadth_admission_audit(
    protocol: dict[str, Any], receipts: list[dict[str, Any]]
) -> dict[str, Any]:
    configured_paths = {str(row["path"]).replace("\\", "/") for row in receipts}
    if not LIVE_MANIFEST_PATH.exists():
        return {
            "manifest_present": False,
            "admitted_source_count": len(receipts),
            "manifest_rows_admitted_by_path_count": 0,
            "excluded_system_row_counts": {},
            "manifest_consistency_pass": False,
        }
    manifest = read_json(LIVE_MANIFEST_PATH)
    rows = manifest.get("manifest_rows", [])
    if not isinstance(rows, list):
        rows = []
    excluded = set(protocol["source_admission"]["excluded_live_breadth_systems_until_repaired"])
    counts: dict[str, int] = defaultdict(int)
    admitted_matches = 0
    for row in rows:
        system = str(row.get("system") or "")
        if system in excluded:
            counts[system] += 1
        source_path = str(row.get("source_path") or "").replace("\\", "/")
        normalized = source_path
        if source_path.startswith(str(ROOT).replace("\\", "/")):
            normalized = source_path[len(str(ROOT).replace("\\", "/")) :].lstrip("/")
        if normalized in configured_paths:
            admitted_matches += 1
    declared_count = int(manifest.get("summary", {}).get("manifest_row_count", len(rows)) or 0)
    discovered_count = int(
        manifest.get("summary", {}).get("discovered_manifest_row_count", declared_count)
        or 0
    )
    return {
        "manifest_present": True,
        "manifest_path": rel(LIVE_MANIFEST_PATH),
        "manifest_sha256": file_sha256(LIVE_MANIFEST_PATH),
        "manifest_schema": manifest.get("schema"),
        "materialized_manifest_row_count": len(rows),
        "declared_manifest_row_count": declared_count,
        "discovered_manifest_row_count": discovered_count,
        "manifest_rows_truncated": bool(
            manifest.get("summary", {}).get(
                "manifest_rows_truncated", discovered_count > declared_count
            )
        ),
        "manifest_rows_omitted_count": int(
            manifest.get("summary", {}).get(
                "manifest_rows_omitted_count", max(0, discovered_count - declared_count)
            )
            or 0
        ),
        "declared_materialized_count_match": declared_count == len(rows),
        "admitted_source_count": len(receipts),
        "manifest_rows_admitted_by_path_count": admitted_matches,
        "excluded_system_row_counts": dict(sorted(counts.items())),
        "explicit_allowlist_only": True,
        "manifest_consistency_pass": declared_count == len(rows),
        "claim_boundary": (
            "The live-breadth manifest is discovery inventory only. Only explicit protocol "
            "sources with a valid univariate time-series contract enter this benchmark."
        ),
    }


def rank_sectors(
    source_results: list[dict[str, Any]],
    anchors: list[dict[str, Any]],
    protocol: dict[str, Any],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in source_results:
        grouped[str(row["sector"])].append(
            {
                "id": row["source_id"],
                "improvement": float(row["relative_mae_improvement_vs_best_percent"]),
                "positive": float(row["relative_mae_improvement_vs_best_percent"]) > 0,
                "strong": bool(row["retrospective_signal"]),
                "prospective": False,
                "external": False,
            }
        )
    for row in anchors:
        grouped[str(row["sector"])].append(
            {
                "id": row["anchor_id"],
                "improvement": float(row["relative_mae_improvement_vs_best_percent"]),
                "positive": bool(row["candidate_beats_best_baseline_on_mean"]),
                "strong": False,
                "prospective": bool(row["prospective_holdout_complete"]),
                "external": bool(row["external_replication_complete"]),
            }
        )

    required_sources = int(
        protocol["promotion_gate"]["minimum_source_wins_for_sector_signal"]
    )
    ranked: list[dict[str, Any]] = []
    for sector, items in grouped.items():
        positive = sum(1 for row in items if row["positive"])
        strong = sum(1 for row in items if row["strong"])
        external = sum(1 for row in items if row["external"])
        mean_improvement = mean(row["improvement"] for row in items)
        proven = bool(strong >= required_sources and external >= 1)
        ranked.append(
            {
                "sector": sector,
                "source_count": len(items),
                "positive_mean_vs_best_baseline_count": positive,
                "retrospective_strong_signal_count": strong,
                "prospective_source_count": sum(1 for row in items if row["prospective"]),
                "external_replication_count": external,
                "mean_relative_mae_improvement_vs_best_percent": mean_improvement,
                "best_source_relative_improvement_percent": max(
                    row["improvement"] for row in items
                ),
                "sector_gain_proven": proven,
                "status": (
                    "SECTOR_GAIN_PROVEN"
                    if proven
                    else "EXPLORATORY_SIGNAL_NOT_PROVEN"
                    if positive
                    else "NO_SECTOR_GAIN_PROVEN"
                ),
                "source_ids": [row["id"] for row in items],
            }
        )
    ranked.sort(
        key=lambda row: (
            -int(row["sector_gain_proven"]),
            -int(row["retrospective_strong_signal_count"]),
            -int(row["positive_mean_vs_best_baseline_count"]),
            -float(row["mean_relative_mae_improvement_vs_best_percent"]),
            str(row["sector"]),
        )
    )
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
    return ranked


def stable_evidence_core(payload: dict[str, Any]) -> dict[str, Any]:
    source_core = []
    for row in payload["source_results"]:
        source_core.append(
            {
                "source_id": row["source_id"],
                "source_sha256": row["source_sha256"],
                "candidate_rank": row["candidate_rank"],
                "candidate_mae": row["candidate"]["mean_absolute_error"],
                "best_baseline": row["best_baseline"]["strategy"],
                "best_baseline_mae": row["best_baseline"]["mean_absolute_error"],
                "improvement": row["relative_mae_improvement_vs_best_percent"],
                "comparisons": [
                    {
                        "baseline": item["baseline"],
                        "mean_delta": item["mean_absolute_error_delta"],
                        "improvement": item["relative_mae_improvement_percent"],
                        "ci95_lower": item["block_bootstrap"]["ci95_lower"],
                        "ci95_upper": item["block_bootstrap"]["ci95_upper"],
                        "holm_p": item["holm_adjusted_p_value"],
                        "pass": item["passes_comparison_gate"],
                    }
                    for item in row["comparisons"]
                ],
                "status": row["status"],
            }
        )
    anchor_core = [
        {
            "anchor_id": row["anchor_id"],
            "protocol_sha256": row["protocol_sha256"],
            "panel_row_chain_sha256": row["panel_row_chain_sha256"],
            "result_sha256": row["result_sha256"],
            "candidate_rank": row["candidate"]["rank"],
            "best_baseline": row["best_baseline"]["strategy"],
            "improvement": row["relative_mae_improvement_vs_best_percent"],
            "status": row["status"],
        }
        for row in payload["anchored_results"]
    ]
    return {
        "implementation": payload["implementation"],
        "protocol_sha256": payload["protocol"]["sha256"],
        "source_core": source_core,
        "anchor_core": anchor_core,
        "sector_ranking": payload["sector_ranking"],
        "gates": payload["gates"],
    }


def build_payload(protocol: dict[str, Any], *, generated_utc: str | None = None) -> tuple[
    dict[str, Any], list[dict[str, Any]]
]:
    eia = load_eia_module()
    source_receipts: list[dict[str, Any]] = []
    source_results: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []
    source_failures: list[dict[str, str]] = []

    for source in protocol["retrospective_sources"]:
        try:
            dates, values, receipt = load_source_series(source, protocol)
            rows, evaluation = evaluate_source(source, dates, values, protocol, eia)
            comparisons, metrics = build_source_comparisons(rows, source, protocol)
            result = summarize_source(
                source, receipt, evaluation, comparisons, metrics, protocol
            )
        except (OSError, ValueError, KeyError) as exc:
            source_failures.append(
                {
                    "source_id": str(source.get("id")),
                    "failure": type(exc).__name__,
                    "message": str(exc),
                }
            )
            continue
        source_receipts.append(receipt)
        source_results.append(result)
        all_rows.extend(rows)

    maximum_origins = int(
        protocol["execution_controls"]["maximum_total_forecast_origins"]
    )
    total_origins = sum(
        int(row["evaluation"]["evaluation_origin_count"]) for row in source_results
    )
    if total_origins > maximum_origins:
        raise ValueError(
            f"forecast origin budget exceeded: {total_origins} > {maximum_origins}"
        )

    anchored_results = [
        anchor_eia_result(anchor, eia) for anchor in protocol["anchored_benchmarks"]
    ]
    sector_ranking = rank_sectors(source_results, anchored_results, protocol)
    proven = [row for row in sector_ranking if row["sector_gain_proven"]]
    positive = [
        row for row in sector_ranking if row["positive_mean_vs_best_baseline_count"] > 0
    ]
    breadth = live_breadth_admission_audit(protocol, source_receipts)
    gates = {
        "configured_source_count": len(protocol["retrospective_sources"]),
        "admitted_source_count": len(source_receipts),
        "source_failure_count": len(source_failures),
        "anchored_benchmark_count": len(anchored_results),
        "total_evaluation_origin_count": total_origins,
        "protocol_matched_strategy_count": len(protocol["baselines"]) + 1,
        "sector_count": len(sector_ranking),
        "positive_exploratory_sector_count": len(positive),
        "sector_gain_proven_count": len(proven),
        "prospective_cross_sector_holdout_complete": False,
        "external_cross_sector_replication_complete": False,
        "cross_sector_efficiency_claim_allowed": False,
        "realized_savings_claim_allowed": False,
        "dollar_projection_from_forecast_error_allowed": False,
        "trading_execution_allowed": False,
    }
    status = (
        "BLOCKED_SOURCE_ADMISSION_FAILURE"
        if source_failures
        else "NO_CROSS_SECTOR_EFFICIENCY_GAIN_PROVEN"
    )
    if not source_failures and positive:
        status = "EXPLORATORY_SECTOR_SIGNAL_PROSPECTIVE_VALIDATION_REQUIRED"
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_utc": generated_utc or now_utc(),
        "status": status,
        "protocol": {
            "id": protocol["protocol_id"],
            "path": rel(PROTOCOL_PATH),
            "sha256": file_sha256(PROTOCOL_PATH),
            "frozen_date_utc": protocol["frozen_date_utc"],
            "freeze_method": "local_sha256_before_execution_not_independent_registration",
        },
        "implementation": {
            "runner_path": rel(RUNNER_PATH),
            "runner_sha256": file_sha256(RUNNER_PATH),
            "eia_runner_path": rel(EIA_RUNNER_PATH),
            "eia_runner_sha256": file_sha256(EIA_RUNNER_PATH),
        },
        "candidate": protocol["candidate"],
        "baseline_scope": protocol["baseline_scope"],
        "baselines": protocol["baselines"],
        "source_receipts": source_receipts,
        "source_failures": source_failures,
        "source_results": source_results,
        "anchored_results": anchored_results,
        "live_breadth_admission_audit": breadth,
        "sector_ranking": sector_ranking,
        "economic_sensitivity": protocol["economic_translation"],
        "gates": gates,
        "highest_observed_exploratory_sector": positive[0]["sector"] if positive else None,
        "highest_proven_efficiency_sector": proven[0]["sector"] if proven else None,
        "safest_next_action": (
            "Freeze a future, never-before-scored window for the highest positive exploratory "
            "sector, obtain an independent evaluator or data-owner signoff, and use a buyer-"
            "approved native-unit cost rule before any dollar statement."
            if positive
            else "Do not market a Kuramoto efficiency gain. Preserve the negative results and "
            "test a future never-before-scored window only after the sector, incumbent baseline, "
            "native metric, and economic conversion are approved by an external owner."
        ),
        "claim_boundary": protocol["claim_boundary"],
    }
    payload["evidence_chain_sha256"] = canonical_sha256(stable_evidence_core(payload))
    return payload, all_rows


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Kuramoto Cross-Sector Benchmark",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        f"Status: `{payload['status']}`",
        f"Evidence chain SHA-256: `{payload['evidence_chain_sha256']}`",
        "",
        "## Decision",
        "",
        (
            f"Highest proven efficiency sector: `{payload['highest_proven_efficiency_sector']}`."
            if payload["highest_proven_efficiency_sector"]
            else "No sector-level Kuramoto efficiency gain is proven."
        ),
        (
            f"Highest positive exploratory sector: `{payload['highest_observed_exploratory_sector']}`."
            if payload["highest_observed_exploratory_sector"]
            else "No positive exploratory sector survived comparison with its best protocol baseline."
        ),
        "",
        "The old coefficient-driven 24/24 result is not used as real-data performance evidence. "
        "The separately frozen EIA benchmark is retained, including its negative result.",
        "",
        "## Coverage",
        "",
        f"- Explicit retrospective sources admitted: `{payload['gates']['admitted_source_count']}` / `{payload['gates']['configured_source_count']}`",
        f"- Anchored protocol-frozen benchmarks: `{payload['gates']['anchored_benchmark_count']}`",
        f"- Rolling evaluation origins: `{payload['gates']['total_evaluation_origin_count']}`",
        f"- Protocol-matched strategies per retrospective source: `{payload['gates']['protocol_matched_strategy_count']}`",
        f"- Sector gains proven: `{payload['gates']['sector_gain_proven_count']}`",
        f"- External cross-sector replication complete: `{str(payload['gates']['external_cross_sector_replication_complete']).lower()}`",
        "",
        "## Sector Ranking",
        "",
        "| Rank | Sector | Sources | Positive vs best | Strong retrospective | Mean improvement vs best | Status |",
        "| ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in payload["sector_ranking"]:
        lines.append(
            f"| {row['rank']} | `{row['sector']}` | {row['source_count']} | "
            f"{row['positive_mean_vs_best_baseline_count']} | "
            f"{row['retrospective_strong_signal_count']} | "
            f"{row['mean_relative_mae_improvement_vs_best_percent']:.4f}% | "
            f"`{row['status']}` |"
        )

    lines.extend(
        [
            "",
            "## Source Results",
            "",
            "| Source | Sector | Candidate rank | Best baseline | MAE improvement vs best | Status |",
            "| --- | --- | ---: | --- | ---: | --- |",
        ]
    )
    for row in payload["source_results"]:
        lines.append(
            f"| `{row['source_id']}` | `{row['sector']}` | {row['candidate_rank']} / "
            f"{row['strategy_count']} | `{row['best_baseline']['strategy']}` | "
            f"{row['relative_mae_improvement_vs_best_percent']:.4f}% | `{row['status']}` |"
        )
    for row in payload["anchored_results"]:
        lines.append(
            f"| `{row['anchor_id']}` | `{row['sector']}` | {row['candidate']['rank']} / "
            f"{row['strategy_count']} | `{row['best_baseline']['strategy']}` | "
            f"{row['relative_mae_improvement_vs_best_percent']:.4f}% | `{row['status']}` |"
        )

    sensitivity = payload["economic_sensitivity"]
    lines.extend(
        [
            "",
            "## Dollar Sensitivity",
            "",
            "These values are arithmetic sensitivity only, not LumenCore-attributable savings.",
            "",
            "| Improvement | Sensitivity on a $1B annual value stream |",
            "| ---: | ---: |",
        ]
    )
    for row in sensitivity["sensitivity_only"]:
        lines.append(
            f"| {float(row['improvement_percent']):g}% | ${int(row['reference_value_usd_per_year']):,}/year |"
        )
    lines.extend(
        [
            "",
            f"Required conversion: `{sensitivity['required_formula']}`",
            "",
            "## Live-Breadth Admission",
            "",
            f"- Manifest present: `{str(payload['live_breadth_admission_audit']['manifest_present']).lower()}`",
            f"- Manifest count internally consistent: `{str(payload['live_breadth_admission_audit'].get('manifest_consistency_pass', False)).lower()}`",
            f"- Discovered routes: `{payload['live_breadth_admission_audit'].get('discovered_manifest_row_count', 0)}`",
            f"- Materialized routes: `{payload['live_breadth_admission_audit'].get('materialized_manifest_row_count', 0)}`",
            f"- Omitted routes disclosed: `{payload['live_breadth_admission_audit'].get('manifest_rows_omitted_count', 0)}`",
            "- Discovery-manifest membership is not benchmark admission.",
            "- Thin, unrelated, duplicated, and contract-free source systems remain excluded.",
            "",
            "## Next Proof Step",
            "",
            payload["safest_next_action"],
            "",
            "## Boundary",
            "",
            f"> {payload['claim_boundary']}",
            "",
        ]
    )
    return "\n".join(lines)


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "source_id",
        "sector",
        "target_timestamp",
        "strategy",
        "kind",
        "actual",
        "predicted",
        "absolute_error",
        "squared_error",
        "seasonal_mase",
        "directional_accuracy",
        "runtime_ms",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(payload: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUT_JSON, payload)
    write_rows(OUT_ROWS, rows)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    artifact_roles: dict[Path, set[str]] = defaultdict(set)

    def include(path: Path, role: str) -> None:
        if path.exists() and path.is_file():
            artifact_roles[path.resolve()].add(role)

    include(RUNNER_PATH, "cross_sector_runner")
    include(PROTOCOL_PATH, "cross_sector_protocol")
    include(EIA_RUNNER_PATH, "anchored_eia_runner")
    include(LIVE_MANIFEST_PATH, "live_breadth_discovery_manifest")
    include(EXTERNAL_PROTOCOL_TEMPLATE_PATH, "external_evaluator_protocol_template")
    include(EXTERNAL_RESULT_TEMPLATE_PATH, "external_evaluator_result_template")
    for receipt in payload["source_receipts"]:
        include(ROOT / str(receipt["path"]), "measured_source_snapshot")
    for anchor in payload["anchored_results"]:
        include(ROOT / str(anchor["protocol_path"]), "anchored_eia_protocol")
        include(ROOT / str(anchor["panel_path"]), "anchored_eia_panel")
        include(ROOT / str(anchor["result_path"]), "anchored_eia_result")
    include(OUT_JSON, "benchmark_receipt")
    include(OUT_ROWS, "paired_forecast_rows")
    include(OUT_MD, "reviewer_report")

    artifacts = []
    for path in sorted(artifact_roles, key=lambda item: rel(item)):
        artifacts.append(
            {
                "path": rel(path),
                "bytes": path.stat().st_size,
                "sha256": file_sha256(path),
                "roles": sorted(artifact_roles[path]),
            }
        )
    manifest = {
        "schema": "lumencore.kuramoto_cross_sector_benchmark_manifest.v1",
        "generated_utc": payload["generated_utc"],
        "evidence_chain_sha256": payload["evidence_chain_sha256"],
        "artifacts": artifacts,
        "artifact_chain_sha256": canonical_sha256(artifacts),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    write_json(OUT_MANIFEST, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Recompute stable evidence and compare with the latest receipt without writing.",
    )
    args = parser.parse_args()
    protocol = load_protocol()
    existing = read_json(OUT_JSON) if args.check and OUT_JSON.exists() else None
    payload, rows = build_payload(
        protocol,
        generated_utc=existing.get("generated_utc") if existing else None,
    )
    if args.check:
        if existing is None:
            raise SystemExit("no existing cross-sector benchmark receipt to check")
        if payload["evidence_chain_sha256"] != existing.get("evidence_chain_sha256"):
            raise SystemExit(
                "cross-sector benchmark evidence drift: "
                f"{existing.get('evidence_chain_sha256')} != {payload['evidence_chain_sha256']}"
            )
        print(
            json.dumps(
                {
                    "status": "KURAMOTO_CROSS_SECTOR_CHECK_PASS",
                    "evidence_chain_sha256": payload["evidence_chain_sha256"],
                    "source_count": len(payload["source_results"]),
                    "sector_gain_proven_count": payload["gates"][
                        "sector_gain_proven_count"
                    ],
                },
                indent=2,
            )
        )
        return 0

    manifest = write_outputs(payload, rows)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "source_count": len(payload["source_results"]),
                "anchor_count": len(payload["anchored_results"]),
                "evaluation_origins": payload["gates"]["total_evaluation_origin_count"],
                "highest_observed_exploratory_sector": payload[
                    "highest_observed_exploratory_sector"
                ],
                "highest_proven_efficiency_sector": payload[
                    "highest_proven_efficiency_sector"
                ],
                "evidence_chain_sha256": payload["evidence_chain_sha256"],
                "artifact_chain_sha256": manifest["artifact_chain_sha256"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
