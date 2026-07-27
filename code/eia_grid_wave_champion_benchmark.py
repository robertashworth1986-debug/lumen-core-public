"""Protocol-frozen EIA grid-demand wave champion benchmark.

This module collects read-only EIA-930 daily actual demand and official
day-ahead forecasts, selects one implemented wave candidate on development
dates, and evaluates it once on the fixed 2026 holdout. It produces public-
data software evidence in native MWh, not field, savings, or reliability proof.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Callable

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "config" / "eia_grid_wave_champion_protocol_v1.json"
PROTOCOL_PROVENANCE_PATH = ROOT / "config" / "reviewer_protocol_provenance_v1.json"
PANEL_DIR = ROOT / "data" / "live_measured" / "eia_grid_validation"
PANEL_LATEST = PANEL_DIR / "eia_grid_validation_panel_latest.json"
OUT_DIR = ROOT / "out" / "eia_grid_wave_champion"
OUT_JSON = OUT_DIR / "eia_grid_wave_champion_benchmark_latest.json"
OUT_ROWS = OUT_DIR / "eia_grid_wave_champion_rows_latest.csv"
OUT_MANIFEST = OUT_DIR / "eia_grid_wave_champion_manifest_latest.json"
DASHBOARD_JSON = ROOT / "dashboard" / "data" / "eia_grid_wave_champion_benchmark.json"
OUT_MD = ROOT / "docs" / f"EIA_GRID_WAVE_CHAMPION_BENCHMARK_{date.today().isoformat()}.md"

EIA_ROUTE = "https://api.eia.gov/v2/electricity/rto/daily-region-data/data/"
STRATEGY_KIND = {
    "eia_day_ahead_forecast": "official_baseline",
    "seasonal_naive_7": "algorithmic_baseline",
    "naive_last": "algorithmic_baseline",
    "kalman_local_linear_trend": "algorithmic_baseline",
    "autoregressive_ridge_p14": "algorithmic_baseline",
    "fft_extrapolation_top5": "algorithmic_baseline",
    "lissajous_phase_paths": "wave_candidate",
    "kuramoto_phase_coupling": "wave_candidate",
    "firefly_synchronization": "wave_candidate",
    "chladni_nodal_patterns": "wave_candidate",
}
CLAIM_BOUNDARY = (
    "Measured public EIA-930 software forecast benchmark in native MWh only. "
    "It does not establish field control, grid reliability improvement, "
    "realized savings, procurement acceptance, safety, external validation, "
    "trading edge, or an unbeatable claim."
)

ForecastFn = Callable[[list[float]], float]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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
    if payload.get("schema") != "eia_grid_wave_champion_protocol.v1":
        raise ValueError("unexpected EIA grid protocol schema")
    return payload


def protocol_commit(path: Path = PROTOCOL_PATH) -> str | None:
    try:
        relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return None
    if PROTOCOL_PROVENANCE_PATH.is_file():
        try:
            provenance = json.loads(
                PROTOCOL_PROVENANCE_PATH.read_text(encoding="utf-8")
            )
            row = next(
                item for item in provenance["entries"] if item["path"] == relative
            )
            commit = str(row["last_touch_commit"])
            portable_text = (
                path.read_text(encoding="utf-8")
                .replace("\r\n", "\n")
                .replace("\r", "\n")
            )
        except (OSError, KeyError, StopIteration, json.JSONDecodeError):
            return None
        if hashlib.sha256(portable_text.encode("utf-8")).hexdigest() != row["sha256"]:
            return None
        if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
            return None
        return commit
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", relative],
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
    return value or None


def read_eia_key() -> str:
    key = os.environ.get("EIA_API_KEY") or os.environ.get("EIA_API_KEY_PREMIUM")
    if not key:
        raise RuntimeError("EIA API key is not configured in the process environment")
    return key


def request_eia_rows(
    protocol: dict[str, Any], authority: dict[str, str], timeout: int = 45
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    key = read_eia_key()
    panel = protocol["panel"]
    params = [
        ("api_key", key),
        ("frequency", "daily"),
        ("data[0]", "value"),
        ("facets[type][]", protocol["source"]["actual_type"]),
        ("facets[type][]", protocol["source"]["official_forecast_type"]),
        ("facets[respondent][]", authority["respondent"]),
        ("facets[timezone][]", authority["timezone"]),
        ("start", panel["start_date"]),
        ("end", panel["end_date"]),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "asc"),
        ("offset", "0"),
        ("length", "5000"),
    ]
    url = EIA_ROUTE + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "LumenCore-EIA-Grid-Validation/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status = int(response.getcode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"EIA request failed for {authority['respondent']} with HTTP {exc.code}"
        ) from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(
            f"EIA request failed for {authority['respondent']}: {type(exc).__name__}"
        ) from None

    payload = json.loads(raw.decode("utf-8"))
    response_payload = payload.get("response", {}) if isinstance(payload, dict) else {}
    incoming = response_payload.get("data", []) if isinstance(response_payload, dict) else []
    rows: list[dict[str, Any]] = []
    allowed_types = {
        protocol["source"]["actual_type"],
        protocol["source"]["official_forecast_type"],
    }
    for row in incoming:
        if not isinstance(row, dict):
            continue
        if row.get("respondent") != authority["respondent"]:
            continue
        if row.get("timezone") != authority["timezone"]:
            continue
        if row.get("type") not in allowed_types:
            continue
        try:
            value = float(row.get("value"))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value):
            continue
        rows.append(
            {
                "period": str(row.get("period")),
                "respondent": str(row.get("respondent")),
                "respondent_name": str(row.get("respondent-name") or authority["name"]),
                "timezone": str(row.get("timezone")),
                "type": str(row.get("type")),
                "type_name": str(row.get("type-name")),
                "value": value,
                "value_units": str(row.get("value-units") or protocol["source"]["value_units"]),
            }
        )
    rows.sort(key=lambda row: (row["respondent"], row["period"], row["type"]))
    receipt = {
        "respondent": authority["respondent"],
        "timezone": authority["timezone"],
        "http_status": status,
        "response_total": int(response_payload.get("total", len(incoming))),
        "accepted_row_count": len(rows),
        "response_body_sha256": hashlib.sha256(raw).hexdigest(),
        "request": {
            "route": EIA_ROUTE,
            "frequency": "daily",
            "types": sorted(allowed_types),
            "respondent": authority["respondent"],
            "timezone": authority["timezone"],
            "start": panel["start_date"],
            "end": panel["end_date"],
            "credential_serialized": False,
        },
    }
    return rows, receipt


def deduplicate_panel_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    conflicts: list[dict[str, Any]] = []
    for row in rows:
        key = (row["respondent"], row["timezone"], row["type"], row["period"])
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = row
            continue
        if not math.isclose(float(existing["value"]), float(row["value"]), rel_tol=1e-12, abs_tol=1e-9):
            conflicts.append(
                {
                    "respondent": key[0],
                    "timezone": key[1],
                    "type": key[2],
                    "period": key[3],
                    "first_value": existing["value"],
                    "second_value": row["value"],
                }
            )
    deduplicated = sorted(by_key.values(), key=lambda row: (row["respondent"], row["period"], row["type"]))
    return deduplicated, conflicts


def panel_quality(rows: list[dict[str, Any]], protocol: dict[str, Any]) -> dict[str, Any]:
    actual_type = protocol["source"]["actual_type"]
    forecast_type = protocol["source"]["official_forecast_type"]
    by_authority: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in rows:
        by_authority[row["respondent"]][row["type"]].add(row["period"])
    authority_rows = []
    for authority in protocol["panel"]["balancing_authorities"]:
        respondent = authority["respondent"]
        actual_dates = by_authority[respondent][actual_type]
        forecast_dates = by_authority[respondent][forecast_type]
        common = actual_dates & forecast_dates
        authority_rows.append(
            {
                "respondent": respondent,
                "actual_day_count": len(actual_dates),
                "official_forecast_day_count": len(forecast_dates),
                "common_day_count": len(common),
                "first_common_day": min(common) if common else None,
                "last_common_day": max(common) if common else None,
            }
        )
    return {
        "row_count": len(rows),
        "authority_count": len(by_authority),
        "actual_row_count": sum(1 for row in rows if row["type"] == actual_type),
        "official_forecast_row_count": sum(1 for row in rows if row["type"] == forecast_type),
        "nonpositive_value_count": sum(1 for row in rows if float(row["value"]) <= 0),
        "authorities": authority_rows,
    }


def collect_panel(protocol: dict[str, Any], timeout: int = 45) -> dict[str, Any]:
    all_rows: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    for authority in protocol["panel"]["balancing_authorities"]:
        rows, receipt = request_eia_rows(protocol, authority, timeout=timeout)
        all_rows.extend(rows)
        receipts.append(receipt)
    rows, conflicts = deduplicate_panel_rows(all_rows)
    quality = panel_quality(rows, protocol)
    quality["duplicate_conflict_count"] = len(conflicts)
    quality["duplicate_conflicts"] = conflicts
    return {
        "schema": "eia_grid_validation_panel.v1",
        "generated_utc": now_utc(),
        "protocol": {
            "path": str(PROTOCOL_PATH.relative_to(ROOT)).replace("\\", "/"),
            "sha256": file_sha256(PROTOCOL_PATH),
            "frozen_commit": protocol_commit(),
            "protocol_id": protocol["protocol_id"],
        },
        "source": {
            "publisher": protocol["source"]["publisher"],
            "product": protocol["source"]["product"],
            "route": EIA_ROUTE,
            "documentation": protocol["source"]["documentation"],
            "credential_serialized": False,
        },
        "request_receipts": receipts,
        "quality": quality,
        "row_chain_sha256": canonical_sha256(rows),
        "rows": rows,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def write_panel(panel: dict[str, Any]) -> tuple[Path, Path]:
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    stamped = PANEL_DIR / f"eia_grid_validation_panel_{now_tag()}.json"
    text = json.dumps(panel, indent=2, sort_keys=True) + "\n"
    stamped.write_text(text, encoding="utf-8")
    PANEL_LATEST.write_text(text, encoding="utf-8")
    return stamped, PANEL_LATEST


def load_panel(path: Path = PANEL_LATEST) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "eia_grid_validation_panel.v1":
        raise ValueError("unexpected EIA grid panel schema")
    if canonical_sha256(payload.get("rows", [])) != payload.get("row_chain_sha256"):
        raise ValueError("EIA grid panel row-chain hash mismatch")
    return payload


def stable_scale(values: np.ndarray) -> tuple[float, float]:
    center = float(np.median(values))
    mad = float(np.median(np.abs(values - center)))
    scale = max(mad * 1.4826, float(np.std(values)), abs(center) * 1e-9, 1e-9)
    return center, scale


def forecast_naive_last(history: list[float]) -> float:
    return float(history[-1])


def forecast_kalman_local_linear(history: list[float]) -> float:
    y = np.asarray(history, dtype=float)
    if y.size < 3:
        return float(y[-1])
    differences = np.diff(y)
    diff_variance = max(float(np.var(differences)), abs(float(np.mean(y))) * 1e-9, 1e-6)
    state = np.array([y[0], float(np.median(differences[: min(14, differences.size)]))])
    covariance = np.diag([diff_variance, diff_variance * 0.1])
    transition = np.array([[1.0, 1.0], [0.0, 1.0]])
    observation = np.array([[1.0, 0.0]])
    process_noise = np.diag([0.01 * diff_variance, 0.001 * diff_variance])
    observation_noise = 0.50 * diff_variance
    identity = np.eye(2)
    for value in y[1:]:
        state = transition @ state
        covariance = transition @ covariance @ transition.T + process_noise
        innovation = float(value - (observation @ state)[0])
        innovation_variance = float((observation @ covariance @ observation.T)[0, 0] + observation_noise)
        gain = (covariance @ observation.T)[:, 0] / max(innovation_variance, 1e-12)
        state = state + gain * innovation
        covariance = (identity - np.outer(gain, observation[0])) @ covariance
    return float((transition @ state)[0])


def forecast_autoregressive_ridge(history: list[float], lag: int = 14, ridge: float = 1.0) -> float:
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
    prediction = float(np.r_[1.0, z[-lag:]] @ coefficients)
    return center + scale * prediction


def forecast_fft(history: list[float], top_modes: int = 5) -> float:
    y = np.asarray(history[-730:], dtype=float)
    if y.size < 16:
        return float(y[-1])
    t = np.arange(y.size, dtype=float)
    slope, intercept = np.polyfit(t, y, 1)
    residual = y - (intercept + slope * t)
    spectrum = np.fft.rfft(residual)
    if spectrum.size <= 1:
        return float(intercept + slope * y.size)
    candidates = np.arange(1, spectrum.size)
    selected = candidates[np.argsort(np.abs(spectrum[1:]))[-top_modes:]]
    future_residual = 0.0
    for index in selected:
        coefficient = spectrum[index] / y.size
        future_residual += 2.0 * float(
            np.real(coefficient * np.exp(2j * np.pi * index * y.size / y.size))
        )
    return float(intercept + slope * y.size + future_residual)


def harmonic_design(
    length: int, periods: tuple[float, ...], *, interactions: bool = False
) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(length, dtype=float)
    future_t = float(length)
    trend = (t - (length - 1) / 2.0) / max(length, 1)
    future_trend = (future_t - (length - 1) / 2.0) / max(length, 1)
    columns = [np.ones(length), trend]
    future = [1.0, future_trend]
    sines: list[np.ndarray] = []
    cosines: list[np.ndarray] = []
    for period in periods:
        angle = 2.0 * np.pi * t / period
        future_angle = 2.0 * np.pi * future_t / period
        sine = np.sin(angle)
        cosine = np.cos(angle)
        sines.append(sine)
        cosines.append(cosine)
        columns.extend([sine, cosine])
        future.extend([math.sin(future_angle), math.cos(future_angle)])
    if interactions:
        for left in range(len(periods)):
            for right in range(left + 1, len(periods)):
                columns.extend([sines[left] * sines[right], cosines[left] * cosines[right]])
                left_angle = 2.0 * np.pi * future_t / periods[left]
                right_angle = 2.0 * np.pi * future_t / periods[right]
                future.extend(
                    [
                        math.sin(left_angle) * math.sin(right_angle),
                        math.cos(left_angle) * math.cos(right_angle),
                    ]
                )
    return np.column_stack(columns), np.asarray(future, dtype=float)


def ridge_fit(design: np.ndarray, target: np.ndarray, ridge: float) -> np.ndarray:
    penalty = np.eye(design.shape[1]) * ridge
    penalty[0, 0] = 0.0
    return np.linalg.solve(design.T @ design + penalty, design.T @ target)


def forecast_harmonic(
    history: list[float], periods: tuple[float, ...], ridge: float, *, interactions: bool = False
) -> float:
    y = np.asarray(history[-730:], dtype=float)
    center, scale = stable_scale(y)
    z = (y - center) / scale
    design, future = harmonic_design(y.size, periods, interactions=interactions)
    coefficients = ridge_fit(design, z, ridge)
    return center + scale * float(future @ coefficients)


def fitted_seasonal_oscillators(
    history: list[float], periods: tuple[float, ...], ridge: float = 0.0001
) -> tuple[float, float, np.ndarray, np.ndarray, np.ndarray, float, float]:
    y = np.asarray(history[-730:], dtype=float)
    center, scale = stable_scale(y)
    z = (y - center) / scale
    design, _ = harmonic_design(y.size, periods)
    coefficients = ridge_fit(design, z, ridge)
    future_trend = (y.size - (y.size - 1) / 2.0) / max(y.size, 1)
    trend_value = float(coefficients[0] + coefficients[1] * future_trend)
    amplitudes = []
    phases = []
    frequencies = []
    current_t = y.size - 1
    for index, period in enumerate(periods):
        sine_coefficient = float(coefficients[2 + 2 * index])
        cosine_coefficient = float(coefficients[3 + 2 * index])
        amplitude = math.hypot(sine_coefficient, cosine_coefficient)
        phase_offset = math.atan2(sine_coefficient, cosine_coefficient)
        omega = 2.0 * math.pi / period
        amplitudes.append(amplitude)
        phases.append(omega * current_t - phase_offset)
        frequencies.append(omega)
    return (
        center,
        scale,
        np.asarray(amplitudes),
        np.asarray(phases),
        np.asarray(frequencies),
        trend_value,
        float(y.size),
    )


def forecast_kuramoto(history: list[float], coupling: float = 0.01) -> float:
    periods = (7.0, 30.4375, 365.25)
    center, scale, amplitudes, phases, frequencies, trend_value, _ = fitted_seasonal_oscillators(
        history, periods
    )
    count = len(phases)
    derivatives = np.empty(count)
    for index in range(count):
        coupling_term = sum(math.sin(phases[j] - phases[index]) for j in range(count))
        derivatives[index] = frequencies[index] + coupling * coupling_term / count
    future_phases = phases + derivatives
    prediction = trend_value + float(np.sum(amplitudes * np.cos(future_phases)))
    return center + scale * prediction


def forecast_firefly(history: list[float], beta: float = 0.02) -> float:
    periods = (7.0, 30.4375, 365.25)
    center, scale, amplitudes, phases, frequencies, trend_value, _ = fitted_seasonal_oscillators(
        history, periods
    )
    leader = int(np.argmax(amplitudes))
    future_phases = phases + frequencies
    for index in range(len(phases)):
        if index != leader:
            future_phases[index] += beta * math.sin(phases[leader] - phases[index])
    prediction = trend_value + float(np.sum(amplitudes * np.cos(future_phases)))
    return center + scale * prediction


ALGORITHM_FORECASTERS: dict[str, ForecastFn] = {
    "naive_last": forecast_naive_last,
    "kalman_local_linear_trend": forecast_kalman_local_linear,
    "autoregressive_ridge_p14": forecast_autoregressive_ridge,
    "fft_extrapolation_top5": forecast_fft,
    "lissajous_phase_paths": lambda history: forecast_harmonic(
        history, (7.0, 30.4375, 365.25), 0.0001
    ),
    "kuramoto_phase_coupling": forecast_kuramoto,
    "firefly_synchronization": forecast_firefly,
    "chladni_nodal_patterns": lambda history: forecast_harmonic(
        history, (7.0, 14.0, 30.4375, 365.25), 0.001, interactions=True
    ),
}


def seasonal_mase_scale(history: list[float], season: int = 7) -> float:
    if len(history) <= season:
        return max(abs(mean(history)) * 1e-9, 1e-9)
    differences = [abs(history[index] - history[index - season]) for index in range(season, len(history))]
    return max(mean(differences), abs(mean(history)) * 1e-9, 1e-9)


def direction(value: float, tolerance: float = 1e-9) -> int:
    if value > tolerance:
        return 1
    if value < -tolerance:
        return -1
    return 0


def panel_series(panel: dict[str, Any], protocol: dict[str, Any]) -> dict[str, dict[str, Any]]:
    actual_type = protocol["source"]["actual_type"]
    forecast_type = protocol["source"]["official_forecast_type"]
    series: dict[str, dict[str, Any]] = {}
    for authority in protocol["panel"]["balancing_authorities"]:
        series[authority["respondent"]] = {
            "authority": authority,
            "actual": {},
            "official": {},
        }
    for row in panel["rows"]:
        respondent = row["respondent"]
        if respondent not in series:
            continue
        if row["type"] == actual_type:
            series[respondent]["actual"][row["period"]] = float(row["value"])
        elif row["type"] == forecast_type:
            series[respondent]["official"][row["period"]] = float(row["value"])
    return series


def target_split(target: str, protocol: dict[str, Any]) -> str | None:
    split = protocol["split"]
    if split["development_start"] <= target <= split["development_end"]:
        origin = date.fromisoformat(target)
        start = date.fromisoformat(split["development_start"])
        if (origin - start).days % int(split["development_origin_stride_days"]) == 0:
            return "development"
        return None
    if split["holdout_start"] <= target <= split["holdout_end"]:
        origin = date.fromisoformat(target)
        start = date.fromisoformat(split["holdout_start"])
        if (origin - start).days % int(split["holdout_origin_stride_days"]) == 0:
            return "holdout"
    return None


def evaluate_panel(panel: dict[str, Any], protocol: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    maximum_history = int(protocol["execution_controls"]["maximum_history_days"])
    minimum_history = int(protocol["split"]["minimum_history_days"])
    series = panel_series(panel, protocol)
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    strategy_ids = [row["id"] for row in protocol["baselines"]] + [
        row["id"] for row in protocol["wave_candidates"]
    ]

    for respondent, bundle in series.items():
        actual: dict[str, float] = bundle["actual"]
        official: dict[str, float] = bundle["official"]
        actual_dates = sorted(actual)
        common_dates = sorted(set(actual) & set(official))
        for target in common_dates:
            split_name = target_split(target, protocol)
            if split_name is None:
                continue
            target_date = date.fromisoformat(target)
            previous = (target_date - timedelta(days=1)).isoformat()
            seasonal = (target_date - timedelta(days=7)).isoformat()
            if previous not in actual or seasonal not in actual:
                skipped.append({"respondent": respondent, "target": target, "reason": "history_gap"})
                continue
            history_dates = [value for value in actual_dates if value < target]
            if len(history_dates) < minimum_history:
                skipped.append({"respondent": respondent, "target": target, "reason": "insufficient_history"})
                continue
            history_dates = history_dates[-maximum_history:]
            history = [actual[value] for value in history_dates]
            scale = seasonal_mase_scale(history)
            target_value = actual[target]
            last_value = actual[previous]
            predictions: dict[str, tuple[float, float]] = {
                "eia_day_ahead_forecast": (official[target], 0.0),
                "seasonal_naive_7": (actual[seasonal], 0.0),
            }
            failed = False
            for strategy, forecaster in ALGORITHM_FORECASTERS.items():
                start = time.perf_counter()
                try:
                    predicted = float(forecaster(history))
                except (ValueError, np.linalg.LinAlgError, FloatingPointError, OverflowError):
                    failed = True
                    skipped.append(
                        {
                            "respondent": respondent,
                            "target": target,
                            "reason": "strategy_failure",
                            "strategy": strategy,
                        }
                    )
                    break
                runtime_ms = (time.perf_counter() - start) * 1000.0
                if not math.isfinite(predicted):
                    failed = True
                    skipped.append(
                        {
                            "respondent": respondent,
                            "target": target,
                            "reason": "nonfinite_prediction",
                            "strategy": strategy,
                        }
                    )
                    break
                predictions[strategy] = (predicted, runtime_ms)
            if failed or set(predictions) != set(strategy_ids):
                continue

            for strategy in strategy_ids:
                predicted, runtime_ms = predictions[strategy]
                absolute_error = abs(target_value - predicted)
                rows.append(
                    {
                        "split": split_name,
                        "respondent": respondent,
                        "respondent_name": bundle["authority"]["name"],
                        "timezone": bundle["authority"]["timezone"],
                        "target_date": target,
                        "calendar_month": target[:7],
                        "strategy": strategy,
                        "kind": STRATEGY_KIND[strategy],
                        "actual_mwh": target_value,
                        "predicted_mwh": predicted,
                        "absolute_error_mwh": absolute_error,
                        "absolute_percentage_error": absolute_error / max(abs(target_value), 1e-9),
                        "seasonal_mase_7": absolute_error / scale,
                        "directional_accuracy": float(
                            direction(predicted - last_value) == direction(target_value - last_value)
                        ),
                        "runtime_ms": runtime_ms,
                    }
                )

    summary = {
        "evaluation_row_count": len(rows),
        "development_row_count": sum(1 for row in rows if row["split"] == "development"),
        "holdout_row_count": sum(1 for row in rows if row["split"] == "holdout"),
        "strategy_count": len(strategy_ids),
        "authority_count": len({row["respondent"] for row in rows}),
        "skipped_target_count": len(skipped),
        "skipped_targets": skipped,
        "leakage_control": protocol["split"]["rolling_rule"],
    }
    return rows, summary


def aggregate_strategy(rows: list[dict[str, Any]], split_name: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["split"] == split_name:
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
                "median_seasonal_mase_7": median(float(row["seasonal_mase_7"]) for row in items),
                "mean_absolute_error_mwh": mean(float(row["absolute_error_mwh"]) for row in items),
                "mean_absolute_percentage_error": mean(
                    float(row["absolute_percentage_error"]) for row in items
                ),
                "mean_directional_accuracy": mean(float(row["directional_accuracy"]) for row in items),
                "mean_runtime_ms": mean(float(row["runtime_ms"]) for row in items),
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


def select_candidate(development: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [row for row in development if row["kind"] == "wave_candidate"]
    if not candidates:
        raise ValueError("development rows contain no wave candidate")
    return min(
        candidates,
        key=lambda row: (
            float(row["mean_seasonal_mase_7"]),
            float(row["mean_absolute_error_mwh"]),
            str(row["strategy"]),
        ),
    )


def exact_two_sided_sign_test(deltas: list[float]) -> float | None:
    nonzero = [value for value in deltas if abs(value) > 1e-12]
    count = len(nonzero)
    if count == 0:
        return None
    wins = sum(1 for value in nonzero if value > 0)
    lower = min(wins, count - wins)
    cumulative = sum(math.comb(count, index) for index in range(lower + 1)) / (2**count)
    return min(1.0, 2.0 * cumulative)


def percentile(values: list[float], proportion: float) -> float:
    if not values:
        raise ValueError("cannot take percentile of empty values")
    ordered = sorted(values)
    position = proportion * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    weight = position - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def authority_cluster_bootstrap(
    authority_month_deltas: dict[str, list[float]], draws: int = 10000, seed: int = 20260713
) -> list[float]:
    authorities = sorted(authority_month_deltas)
    if not authorities:
        return []
    rng = random.Random(seed)
    results: list[float] = []
    for _ in range(draws):
        sampled = [rng.choice(authorities) for _ in authorities]
        values = [value for authority in sampled for value in authority_month_deltas[authority]]
        results.append(mean(values))
    return [percentile(results, 0.025), percentile(results, 0.975)]


def build_comparisons(
    rows: list[dict[str, Any]], selected_candidate: str, protocol: dict[str, Any]
) -> list[dict[str, Any]]:
    holdout = [row for row in rows if row["split"] == "holdout"]
    index = {
        (row["respondent"], row["target_date"], row["strategy"]): row
        for row in holdout
    }
    baselines = [row["id"] for row in protocol["baselines"]]
    comparisons: list[dict[str, Any]] = []
    for baseline in baselines:
        monthly_values: dict[tuple[str, str], list[float]] = defaultdict(list)
        for key, candidate_row in index.items():
            respondent, target, strategy = key
            if strategy != selected_candidate:
                continue
            baseline_row = index.get((respondent, target, baseline))
            if baseline_row is None:
                continue
            delta = float(baseline_row["seasonal_mase_7"]) - float(
                candidate_row["seasonal_mase_7"]
            )
            monthly_values[(respondent, target[:7])].append(delta)
        month_deltas = {
            key: mean(values) for key, values in monthly_values.items() if values
        }
        authority_months: dict[str, list[float]] = defaultdict(list)
        for (respondent, _month), value in month_deltas.items():
            authority_months[respondent].append(value)
        authority_means = {
            respondent: mean(values) for respondent, values in authority_months.items()
        }
        deltas = list(month_deltas.values())
        interval = authority_cluster_bootstrap(authority_months)
        comparisons.append(
            {
                "baseline": baseline,
                "paired_authority_month_count": len(deltas),
                "mean_skill_delta": mean(deltas) if deltas else None,
                "median_skill_delta": median(deltas) if deltas else None,
                "cluster_bootstrap_mean_skill_ci95": interval,
                "month_win_count": sum(1 for value in deltas if value > 0),
                "month_loss_count": sum(1 for value in deltas if value < 0),
                "month_tie_count": sum(1 for value in deltas if abs(value) <= 1e-12),
                "month_win_rate": (
                    sum(1 for value in deltas if value > 0)
                    / max(sum(1 for value in deltas if abs(value) > 1e-12), 1)
                ),
                "authority_mean_skill": authority_means,
                "authority_mean_win_count": sum(1 for value in authority_means.values() if value > 0),
                "worst_authority_mean_skill": min(authority_means.values()) if authority_means else None,
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


def holdout_coverage(rows: list[dict[str, Any]], protocol: dict[str, Any]) -> dict[str, Any]:
    strategies = [row["id"] for row in protocol["baselines"]] + [
        row["id"] for row in protocol["wave_candidates"]
    ]
    holdout = [row for row in rows if row["split"] == "holdout"]
    by_authority: dict[str, set[str]] = defaultdict(set)
    for row in holdout:
        if row["strategy"] == strategies[0]:
            by_authority[row["respondent"]].add(row["target_date"])
    counts = {authority: len(days) for authority, days in sorted(by_authority.items())}
    return {
        "authority_count": len(counts),
        "common_holdout_day_count_by_authority": counts,
        "minimum_common_holdout_days": min(counts.values()) if counts else 0,
        "all_strategy_count": len(strategies),
    }


def run_benchmark(panel: dict[str, Any], protocol: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows, evaluation = evaluate_panel(panel, protocol)
    development = aggregate_strategy(rows, "development")
    holdout = aggregate_strategy(rows, "holdout")
    selected = select_candidate(development)
    selected_id = str(selected["strategy"])
    comparisons = build_comparisons(rows, selected_id, protocol)
    coverage = holdout_coverage(rows, protocol)
    gate = protocol["promotion_gate"]
    minimum_months = min(
        (row["paired_authority_month_count"] for row in comparisons), default=0
    )
    coverage_pass = bool(
        coverage["authority_count"] >= int(gate["minimum_balancing_authorities"])
        and coverage["minimum_common_holdout_days"]
        >= int(gate["minimum_common_holdout_days_per_authority"])
        and minimum_months >= int(gate["minimum_paired_authority_months"])
    )
    comparison_pass = bool(comparisons and all(row["passes_comparison_gate"] for row in comparisons))
    promotion_pass = coverage_pass and comparison_pass
    report = {
        "schema": "eia_grid_wave_champion_benchmark.v1",
        "generated_utc": now_utc(),
        "protocol": panel["protocol"],
        "panel": {
            "path": str(PANEL_LATEST.relative_to(ROOT)).replace("\\", "/"),
            "sha256": file_sha256(PANEL_LATEST) if PANEL_LATEST.exists() else None,
            "row_chain_sha256": panel["row_chain_sha256"],
            "quality": panel["quality"],
        },
        "evaluation": evaluation,
        "development_leaderboard": development,
        "selection": {
            "selected_wave_candidate": selected_id,
            "development_rank": selected["rank"],
            "development_mean_seasonal_mase_7": selected["mean_seasonal_mase_7"],
            "rule": protocol["selection"]["rule"],
            "holdout_used_for_selection": False,
            "post_selection_substitution": False,
        },
        "holdout_leaderboard": holdout,
        "holdout_coverage": coverage,
        "baseline_comparisons": comparisons,
        "promotion_gate": {
            "coverage_pass": coverage_pass,
            "all_baseline_comparisons_pass": comparison_pass,
            "protocol_grade_internal_champion": promotion_pass,
            "external_replication_complete": False,
            "field_validation_complete": False,
            "realized_savings_claim_allowed": False,
            "unbeatable_claim_allowed": False,
            "trading_execution_allowed": False,
        },
        "synthetic_predecessor_boundary": "The prior coefficient-driven wave benchmark is synthetic scenario software and is not evidence that an implemented Kuramoto model beats Kalman on measured grid demand.",
        "claim_boundary": CLAIM_BOUNDARY,
    }
    return report, rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "split",
        "respondent",
        "respondent_name",
        "timezone",
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
        "runtime_ms",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def render_markdown(report: dict[str, Any]) -> str:
    selection = report["selection"]
    gate = report["promotion_gate"]
    lines = [
        "# EIA Grid Wave Champion Benchmark",
        "",
        f"Generated UTC: `{report['generated_utc']}`",
        "",
        "## Decision",
        "",
        f"Development-selected wave candidate: `{selection['selected_wave_candidate']}`.",
        f"Protocol-grade internal champion: `{str(gate['protocol_grade_internal_champion']).lower()}`.",
        "",
        "The candidate identity was selected on development dates only. The fixed 2026 holdout was not used for selection or substitution.",
        "",
        "## Protocol Receipt",
        "",
        f"- Protocol id: `{report['protocol']['protocol_id']}`",
        f"- Protocol SHA-256: `{report['protocol']['sha256']}`",
        f"- Protocol frozen commit: `{report['protocol']['frozen_commit']}`",
        f"- Panel row-chain SHA-256: `{report['panel']['row_chain_sha256']}`",
        f"- Authorities: `{report['holdout_coverage']['authority_count']}`",
        f"- Minimum common holdout days per authority: `{report['holdout_coverage']['minimum_common_holdout_days']}`",
        "",
        "## Development Leaderboard",
        "",
        "| Rank | Strategy | Kind | Mean seasonal MASE | Mean absolute error MWh |",
        "|---:|---|---|---:|---:|",
    ]
    for row in report["development_leaderboard"]:
        lines.append(
            f"| {row['rank']} | `{row['strategy']}` | `{row['kind']}` | "
            f"{row['mean_seasonal_mase_7']:.6f} | {row['mean_absolute_error_mwh']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Untouched Holdout Leaderboard",
            "",
            "| Rank | Strategy | Kind | Mean seasonal MASE | Mean absolute error MWh | Direction accuracy |",
            "|---:|---|---|---:|---:|---:|",
        ]
    )
    for row in report["holdout_leaderboard"]:
        lines.append(
            f"| {row['rank']} | `{row['strategy']}` | `{row['kind']}` | "
            f"{row['mean_seasonal_mase_7']:.6f} | {row['mean_absolute_error_mwh']:.3f} | "
            f"{row['mean_directional_accuracy']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Baseline Gauntlet",
            "",
            "Positive skill means the baseline seasonal-MASE minus candidate seasonal-MASE is positive.",
            "",
            "| Baseline | Mean skill | Cluster CI95 | Holm p | Authority wins | Month win rate | Pass |",
            "|---|---:|---|---:|---:|---:|---|",
        ]
    )
    for row in report["baseline_comparisons"]:
        interval = row["cluster_bootstrap_mean_skill_ci95"]
        lines.append(
            f"| `{row['baseline']}` | {row['mean_skill_delta']:.6f} | "
            f"[{interval[0]:.6f}, {interval[1]:.6f}] | "
            f"{row['holm_adjusted_p_value']:.6g} | {row['authority_mean_win_count']}/8 | "
            f"{row['month_win_rate']:.4f} | `{str(row['passes_comparison_gate']).lower()}` |"
        )
    lines.extend(
        [
            "",
            "## Gate",
            "",
            f"- Coverage pass: `{str(gate['coverage_pass']).lower()}`",
            f"- Every baseline comparison pass: `{str(gate['all_baseline_comparisons_pass']).lower()}`",
            f"- External replication complete: `{str(gate['external_replication_complete']).lower()}`",
            f"- Realized-savings claim allowed: `{str(gate['realized_savings_claim_allowed']).lower()}`",
            f"- Unbeatable claim allowed: `{str(gate['unbeatable_claim_allowed']).lower()}`",
            "",
            "## Boundary",
            "",
            report["synthetic_predecessor_boundary"],
            "",
            f"> {report['claim_boundary']}",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    write_json(OUT_JSON, report)
    write_json(DASHBOARD_JSON, report)
    write_rows(OUT_ROWS, rows)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    artifacts = []
    for path in (PROTOCOL_PATH, PANEL_LATEST, OUT_JSON, OUT_ROWS, DASHBOARD_JSON, OUT_MD):
        artifacts.append(
            {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
        )
    manifest = {
        "schema": "eia_grid_wave_champion_manifest.v1",
        "generated_utc": now_utc(),
        "artifacts": artifacts,
        "artifact_chain_sha256": canonical_sha256(artifacts),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    write_json(OUT_MANIFEST, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--refresh", action="store_true", help="Collect a fresh official EIA panel.")
    mode.add_argument("--skip-network", action="store_true", help="Reuse the frozen latest panel.")
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()

    protocol = load_protocol()
    if args.refresh:
        panel = collect_panel(protocol, timeout=args.timeout)
        stamped, _latest = write_panel(panel)
        panel_path = stamped
    else:
        if not PANEL_LATEST.exists():
            raise SystemExit("No frozen EIA grid panel exists; run once with --refresh")
        panel = load_panel(PANEL_LATEST)
        panel_path = PANEL_LATEST

    if panel["protocol"]["sha256"] != file_sha256(PROTOCOL_PATH):
        raise SystemExit("Frozen panel protocol hash does not match the current protocol")
    report, rows = run_benchmark(panel, protocol)
    manifest = write_outputs(report, rows)
    print(
        json.dumps(
            {
                "status": "EIA_GRID_WAVE_CHAMPION_BENCHMARK_READY",
                "mode": "fresh_official_eia_pull" if args.refresh else "reuse_frozen_panel",
                "panel_path": str(panel_path.relative_to(ROOT)).replace("\\", "/"),
                "panel_rows": panel["quality"]["row_count"],
                "evaluation_rows": len(rows),
                "selected_wave_candidate": report["selection"]["selected_wave_candidate"],
                "protocol_grade_internal_champion": report["promotion_gate"][
                    "protocol_grade_internal_champion"
                ],
                "artifact_chain_sha256": manifest["artifact_chain_sha256"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
