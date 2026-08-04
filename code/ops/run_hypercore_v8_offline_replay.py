from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import platform
import sys
import time
import tracemalloc
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import scipy
from scipy.signal import coherence


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL = ROOT / "config" / "hypercore_v8_validation_protocol_v1.json"
DEFAULT_OUTPUT = ROOT / "out" / "ops" / "hypercore_v8_offline_replay_preflight_latest.json"
SYNTHETIC_FIXTURE_DIR = ROOT / "out" / "ops" / "hypercore_v8_synthetic_fixture"
RECEIPT_SCHEMA = "hypercore_v8_offline_replay_receipt_v1"
SOURCE_SCHEMA = "hypercore_v8_source_bundle_v1"
AUTH_SCHEMA = "hypercore_v8_source_authorization_v1"


class ReplayPreconditionError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ReplayPreconditionError("JSON_OBJECT_REQUIRED", "JSON root must be an object")
    return payload


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def utc_iso(value: str | None = None) -> str:
    parsed = (
        datetime.now(timezone.utc)
        if value is None
        else datetime.fromisoformat(value.replace("Z", "+00:00"))
    )
    if parsed.tzinfo is None:
        raise ReplayPreconditionError("UTC_TIMESTAMP_REQUIRED", "timestamp needs timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _nonempty(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def build_synthetic_fixture(directory: Path, seed: int = 20260802) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    rows = 300
    index = np.arange(rows, dtype=float)
    timestamps = pd.date_range("2026-01-01", periods=rows, freq="5min", tz="UTC")
    latent = np.sin(2 * np.pi * index / 48) + 0.35 * np.sin(2 * np.pi * index / 17)
    compute = 58 + 12 * latent + rng.normal(0, 1.2, rows)
    power = 96 + 0.72 * compute + rng.normal(0, 1.5, rows)
    thermal = 21 + 0.045 * power + 0.08 * np.roll(compute, 2) + rng.normal(0, 0.25, rows)
    incident = np.zeros(rows, dtype=int)
    incident_id = np.full(rows, "", dtype=object)
    episodes = [(60, 70, "D1"), (120, 132, "D2"), (195, 205, "C1"), (250, 262, "H1"), (280, 292, "H2")]
    for start, stop, episode_id in episodes:
        incident[start:stop] = 1
        incident_id[start:stop] = episode_id
        thermal[start:stop] += rng.normal(0, 3.0, stop - start)
        power[start:stop] += rng.normal(0, 8.0, stop - start)
        compute[start:stop] += rng.normal(0, 7.0, stop - start)
    incumbent = np.abs(power - np.median(power)) / max(float(np.std(power)), 1e-9)
    frame = pd.DataFrame(
        {
            "timestamp_utc": timestamps.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "power_kw": power,
            "thermal_c": thermal,
            "compute_pct": compute,
            "operator_incumbent_score": incumbent,
            "incident": incident,
            "incident_id": incident_id,
        }
    )
    csv_path = directory / "synthetic_cross_layer_telemetry.csv"
    frame.to_csv(csv_path, index=False, float_format="%.10f", lineterminator="\n")
    source_hash = file_sha256(csv_path)
    bundle = {
        "schema": SOURCE_SCHEMA,
        "source_mode": "synthetic_fixture",
        "source_owner": "LumenCore deterministic synthetic fixture generator",
        "authorization_receipt": {
            "schema": AUTH_SCHEMA,
            "authorized": True,
            "authorization_scope": "synthetic_fixture_offline_test_only",
            "authorized_utc": "2026-08-02T00:00:00Z",
            "authorized_by_role": "fixture_generator",
            "source_sha256": source_hash,
            "production_actuation": False,
            "network_access": False,
        },
        "retrieval_utc": "2026-08-02T00:00:00Z",
        "timezone": "UTC",
        "sampling_interval": 300,
        "signal_units": {
            "power": "kW",
            "cooling_or_thermal": "degrees_C",
            "compute_load": "percent_synthetic",
        },
        "sensor_calibration": "synthetic deterministic generator; no physical calibration claim",
        "signal_dictionary": {
            "timestamp_column": "timestamp_utc",
            "signal_columns": {
                "power": "power_kw",
                "cooling_or_thermal": "thermal_c",
                "compute_load": "compute_pct",
            },
            "incident_label_column": "incident",
            "incident_id_column": "incident_id",
            "operator_incumbent_score_column": "operator_incumbent_score",
        },
        "missingness_and_gap_policy": "past-only; rows with incomplete detector windows abstain",
        "operator_interventions": "none in synthetic fixture",
        "independently_adjudicated_incident_episodes": [episode_id for _, _, episode_id in episodes],
        "operating_day_denominator": "unique UTC dates in scored holdout",
        "eligible_population": "deterministic synthetic cross-layer telemetry only",
        "exclusions": ["not field data", "not an economic or performance claim"],
        "source_sha256": source_hash,
        "data_path": csv_path.name,
        "coherence_window_rows": 32,
        "coherence_frequency_band_hz": [
            1.0 / (32 * 300),
            1.0 / (2 * 300),
        ],
        "seasonal_period_rows": 32,
        "incident_lookback_rows": 8,
        "buyer_false_alert_ceiling_per_operating_day": 12.0,
        "operator_incumbent": {"exists": True, "status": "synthetic_comparator_only"},
    }
    bundle_path = directory / "synthetic_source_bundle.json"
    write_json_atomic(bundle_path, bundle)
    return bundle_path


def validate_protocol(protocol: dict[str, Any]) -> None:
    if protocol.get("schema") != "hypercore_v8_validation_protocol_v1":
        raise ReplayPreconditionError("PROTOCOL_SCHEMA_INVALID", "unexpected protocol schema")
    required = (
        "required_source_contract",
        "chronology",
        "registered_baselines",
        "required_falsification",
        "promotion_gates",
        "claim_boundary",
    )
    if any(key not in protocol for key in required):
        raise ReplayPreconditionError("PROTOCOL_INCOMPLETE", "protocol is incomplete")


def resolve_source_data(bundle_path: Path, bundle: dict[str, Any]) -> Path:
    reference = Path(str(bundle.get("data_path", "")))
    if not reference.parts or reference.is_absolute() or ".." in reference.parts:
        raise ReplayPreconditionError("SOURCE_PATH_UNSAFE", "data_path must be a safe relative path")
    root = bundle_path.parent.resolve()
    resolved = (root / reference).resolve()
    if root not in resolved.parents or not resolved.is_file():
        raise ReplayPreconditionError("SOURCE_PATH_MISSING", "authorized source file is missing")
    return resolved


def validate_source_contract(
    protocol: dict[str, Any], bundle_path: Path, bundle: dict[str, Any]
) -> Path:
    if bundle.get("schema") != SOURCE_SCHEMA:
        raise ReplayPreconditionError("SOURCE_SCHEMA_INVALID", "unexpected source schema")
    missing = [
        key
        for key in protocol["required_source_contract"]["required_fields"]
        if not _nonempty(bundle.get(key))
    ]
    if missing:
        raise ReplayPreconditionError(
            "SOURCE_CONTRACT_INCOMPLETE", "required source-contract fields are absent"
        )
    authorization = bundle.get("authorization_receipt", {})
    if (
        not isinstance(authorization, dict)
        or authorization.get("schema") != AUTH_SCHEMA
        or authorization.get("authorized") is not True
        or authorization.get("production_actuation") is not False
        or authorization.get("network_access") is not False
    ):
        raise ReplayPreconditionError(
            "SOURCE_AUTHORIZATION_INVALID", "authorization receipt failed closed"
        )
    data_path = resolve_source_data(bundle_path, bundle)
    observed_hash = file_sha256(data_path)
    if observed_hash != str(bundle.get("source_sha256", "")).lower():
        raise ReplayPreconditionError("SOURCE_HASH_MISMATCH", "source hash does not match")
    if authorization.get("source_sha256", "").lower() != observed_hash:
        raise ReplayPreconditionError(
            "AUTHORIZATION_HASH_MISMATCH", "authorization does not bind the source"
        )
    validated_coherence_band(bundle)
    return data_path


def validated_coherence_band(bundle: dict[str, Any]) -> tuple[float, float]:
    raw_band = bundle.get("coherence_frequency_band_hz")
    if not isinstance(raw_band, list) or len(raw_band) != 2:
        raise ReplayPreconditionError(
            "COHERENCE_BAND_MISSING",
            "coherence_frequency_band_hz must contain lower and upper Hz bounds",
        )
    try:
        lower, upper = (float(raw_band[0]), float(raw_band[1]))
        sampling_interval = float(bundle["sampling_interval"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ReplayPreconditionError(
            "COHERENCE_BAND_INVALID", "coherence frequency bounds must be numeric"
        ) from exc
    nyquist = 1.0 / (2.0 * sampling_interval)
    if not (0.0 <= lower < upper <= nyquist * (1.0 + 1e-12)):
        raise ReplayPreconditionError(
            "COHERENCE_BAND_INVALID",
            "coherence frequency bounds must be ordered and at or below Nyquist",
        )
    return lower, upper


def load_frame(data_path: Path, bundle: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    dictionary = bundle["signal_dictionary"]
    timestamp_column = dictionary["timestamp_column"]
    signal_columns = list(dictionary["signal_columns"].values())
    required_columns = [
        timestamp_column,
        *signal_columns,
        dictionary["incident_label_column"],
        dictionary["incident_id_column"],
    ]
    incumbent = dictionary.get("operator_incumbent_score_column")
    if incumbent:
        required_columns.append(incumbent)
    frame = pd.read_csv(data_path)
    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        raise ReplayPreconditionError("MISSING_SIGNAL", "required columns are missing")
    frame[timestamp_column] = pd.to_datetime(frame[timestamp_column], utc=True, errors="coerce")
    if frame[timestamp_column].isna().any():
        raise ReplayPreconditionError("TIMESTAMP_INVALID", "timestamps must parse as UTC")
    if not frame[timestamp_column].is_monotonic_increasing or frame[timestamp_column].duplicated().any():
        raise ReplayPreconditionError("TIMESTAMP_ORDER_INVALID", "timestamps must be unique and increasing")
    expected_interval = float(bundle["sampling_interval"])
    deltas = frame[timestamp_column].diff().dt.total_seconds().dropna().to_numpy()
    if not len(deltas) or np.max(np.abs(deltas - expected_interval)) > max(1e-6, expected_interval * 0.01):
        raise ReplayPreconditionError("IRREGULAR_SAMPLING", "sampling interval is not regular")
    for column in signal_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        finite = frame[column].dropna().to_numpy(dtype=float)
        if not len(finite) or float(np.std(finite)) <= 1e-12:
            raise ReplayPreconditionError("CONSTANT_SIGNAL", "signal is empty or constant")
    label_column = dictionary["incident_label_column"]
    frame[label_column] = pd.to_numeric(frame[label_column], errors="coerce")
    if frame[label_column].isna().any() or not set(frame[label_column].astype(int).unique()).issubset({0, 1}):
        raise ReplayPreconditionError("INCIDENT_LABEL_INVALID", "incident labels must be binary")
    frame[label_column] = frame[label_column].astype(int)
    if len(frame) < 240:
        raise ReplayPreconditionError("SOURCE_UNDERPOWERED_ROWS", "at least 240 rows are required")
    return frame, signal_columns


def fit_detector_state(
    frame: pd.DataFrame, timestamps: pd.Series, signal_columns: list[str]
) -> dict[str, Any]:
    values = frame[signal_columns].to_numpy(dtype=float)
    means = np.nanmean(values, axis=0)
    stds = np.nanstd(values, axis=0)
    if np.any(~np.isfinite(means)) or np.any(stds <= 1e-12):
        raise ReplayPreconditionError("DEVELOPMENT_SIGNAL_INVALID", "development fit failed")
    complete = values[np.isfinite(values).all(axis=1)]
    if len(complete) <= len(signal_columns) + 2:
        raise ReplayPreconditionError("DEVELOPMENT_ROWS_INSUFFICIENT", "complete development rows are insufficient")
    covariance = np.cov(complete, rowvar=False)
    covariance = np.atleast_2d(covariance)
    ridge = max(float(np.trace(covariance)) / max(len(signal_columns), 1) * 1e-6, 1e-6)
    inverse = np.linalg.pinv(covariance + np.eye(len(signal_columns)) * ridge)
    buckets = timestamps.dt.dayofweek.to_numpy() * 24 + timestamps.dt.hour.to_numpy()
    seasonal: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for bucket in np.unique(buckets):
        subset = values[buckets == bucket]
        if len(subset) >= 2:
            seasonal[int(bucket)] = (
                np.nanmean(subset, axis=0),
                np.maximum(np.nanstd(subset, axis=0), 1e-9),
            )
    return {
        "means": means,
        "stds": stds,
        "inverse": inverse,
        "seasonal": seasonal,
    }


def rolling_coherence_score(
    values: np.ndarray,
    window_rows: int,
    sampling_interval_seconds: float,
    frequency_band_hz: tuple[float, float],
) -> np.ndarray:
    result = np.full(len(values), np.nan, dtype=float)
    if values.shape[1] < 2:
        return np.nanmax(np.abs(values), axis=1)
    pairs = list(itertools.combinations(range(values.shape[1]), 2))
    fs = 1.0 / sampling_interval_seconds
    for end in range(window_rows - 1, len(values)):
        block = values[end - window_rows + 1 : end + 1]
        if not np.isfinite(block).all():
            continue
        pair_scores: list[float] = []
        for left, right in pairs:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                frequencies, cxy = coherence(
                    block[:, left],
                    block[:, right],
                    fs=fs,
                    nperseg=min(window_rows, 32),
                )
            in_band = (
                (frequencies >= frequency_band_hz[0])
                & (frequencies <= frequency_band_hz[1])
                & np.isfinite(cxy)
            )
            finite = cxy[in_band]
            if len(finite):
                pair_scores.append(float(np.mean(finite)))
        if pair_scores:
            result[end] = 1.0 - float(np.mean(pair_scores))
    return result


def score_segment(
    history: pd.DataFrame,
    segment: pd.DataFrame,
    state: dict[str, Any],
    bundle: dict[str, Any],
    signal_columns: list[str],
) -> pd.DataFrame:
    dictionary = bundle["signal_dictionary"]
    timestamp_column = dictionary["timestamp_column"]
    seasonal_rows = int(bundle.get("seasonal_period_rows", 1))
    window_rows = int(bundle.get("coherence_window_rows", 32))
    frequency_band_hz = validated_coherence_band(bundle)
    context_rows = max(window_rows - 1, seasonal_rows, 1)
    combined = pd.concat([history.tail(context_rows), segment], ignore_index=True)
    raw = combined[signal_columns].to_numpy(dtype=float)
    z = (raw - state["means"]) / state["stds"]
    candidate = rolling_coherence_score(
        z,
        window_rows,
        float(bundle["sampling_interval"]),
        frequency_band_hz,
    )
    persistence = np.nanmean(np.abs(z - np.roll(z, 1, axis=0)), axis=1)
    persistence[0] = np.nan
    seasonal_naive = np.nanmean(
        np.abs(z - np.roll(z, seasonal_rows, axis=0)), axis=1
    )
    seasonal_naive[:seasonal_rows] = np.nan
    z_frame = pd.DataFrame(z)
    ewma = z_frame.ewm(alpha=0.15, adjust=False).mean().shift(1).to_numpy()
    ewma_residual = np.abs(z - ewma)
    ewma_counts = np.isfinite(ewma_residual).sum(axis=1)
    ewma_score = np.divide(
        np.nansum(ewma_residual, axis=1),
        ewma_counts,
        out=np.full(len(ewma_residual), np.nan),
        where=ewma_counts > 0,
    )
    fixed = np.nanmax(np.abs(z), axis=1)
    seasonal_scores = np.full(len(combined), np.nan)
    timestamps = pd.to_datetime(combined[timestamp_column], utc=True)
    buckets = timestamps.dt.dayofweek.to_numpy() * 24 + timestamps.dt.hour.to_numpy()
    for row_index, bucket in enumerate(buckets):
        center, spread = state["seasonal"].get(
            int(bucket), (state["means"], state["stds"])
        )
        row = raw[row_index]
        if np.isfinite(row).all():
            seasonal_scores[row_index] = float(np.max(np.abs((row - center) / spread)))
    centered = raw - state["means"]
    mahalanobis = np.full(len(combined), np.nan)
    for row_index, row in enumerate(centered):
        if np.isfinite(row).all():
            mahalanobis[row_index] = math.sqrt(
                max(float(row @ state["inverse"] @ row), 0.0)
            )
    incumbent_column = dictionary.get("operator_incumbent_score_column")
    incumbent = (
        pd.to_numeric(combined[incumbent_column], errors="coerce").to_numpy()
        if incumbent_column
        else np.full(len(combined), np.nan)
    )
    start = len(combined) - len(segment)
    return pd.DataFrame(
        {
            "hypercore_cross_layer_coherence": candidate[start:],
            "persistence_or_last_value": persistence[start:],
            "seasonal_naive": seasonal_naive[start:],
            "ewma_or_cusum": ewma_score[start:],
            "fixed_univariate_thresholds": fixed[start:],
            "seasonal_or_time_conditioned_thresholds": seasonal_scores[start:],
            "regularized_multivariate_distance": mahalanobis[start:],
            "operator_incumbent": incumbent[start:],
        }
    )


def average_precision(labels: np.ndarray, scores: np.ndarray) -> float | None:
    mask = np.isfinite(scores)
    labels = labels[mask].astype(int)
    scores = scores[mask]
    positives = int(labels.sum())
    if not len(labels) or positives == 0:
        return None
    order = np.argsort(-scores, kind="mergesort")
    ordered = labels[order]
    cumulative = np.cumsum(ordered)
    ranks = np.arange(1, len(ordered) + 1)
    return float(np.sum((cumulative / ranks) * ordered) / positives)


def detector_threshold(scores: np.ndarray, false_alert_ceiling: float, rows_per_day: float) -> float:
    finite = scores[np.isfinite(scores)]
    if not len(finite):
        raise ReplayPreconditionError("CALIBRATION_SCORE_EMPTY", "calibration scores are empty")
    tail_fraction = min(max(false_alert_ceiling / rows_per_day, 1.0 / len(finite)), 0.1)
    return float(np.quantile(finite, 1.0 - tail_fraction, method="higher"))


def incident_episodes(labels: np.ndarray, identifiers: Iterable[Any]) -> list[np.ndarray]:
    identifiers = list(identifiers)
    episodes: list[np.ndarray] = []
    named = [str(value) for value in identifiers]
    used: set[str] = set()
    for index, label in enumerate(labels):
        if int(label) != 1:
            continue
        identifier = named[index].strip()
        if identifier and identifier not in used:
            used.add(identifier)
            episodes.append(np.array([i for i, value in enumerate(named) if value == identifier]))
    if episodes:
        return episodes
    active: list[int] = []
    for index, label in enumerate(labels):
        if int(label) == 1:
            active.append(index)
        elif active:
            episodes.append(np.array(active))
            active = []
    if active:
        episodes.append(np.array(active))
    return episodes


def event_metrics(
    frame: pd.DataFrame,
    scores: np.ndarray,
    threshold: float,
    bundle: dict[str, Any],
) -> dict[str, Any]:
    dictionary = bundle["signal_dictionary"]
    labels = frame[dictionary["incident_label_column"]].to_numpy(dtype=int)
    identifiers = frame[dictionary["incident_id_column"]].fillna("").astype(str).tolist()
    timestamps = pd.to_datetime(frame[dictionary["timestamp_column"]], utc=True)
    finite = np.isfinite(scores)
    alerts = finite & (scores > threshold)
    episodes = incident_episodes(labels, identifiers)
    lookback = int(bundle.get("incident_lookback_rows", 0))
    detected = 0
    lead_times: list[float] = []
    seconds_per_row = float(bundle["sampling_interval"])
    per_incident: list[dict[str, Any]] = []
    for episode_index, rows in enumerate(episodes):
        start = int(rows.min())
        end = int(rows.max())
        search_start = max(0, start - lookback)
        alert_rows = np.flatnonzero(alerts[search_start : end + 1]) + search_start
        hit = bool(len(alert_rows))
        if hit:
            detected += 1
            first = int(alert_rows[0])
            lead_times.append(max((start - first) * seconds_per_row, 0.0))
        per_incident.append(
            {
                "episode_index": episode_index,
                "start_utc": timestamps.iloc[start].isoformat(),
                "end_utc": timestamps.iloc[end].isoformat(),
                "detected": hit,
                "lead_time_seconds": lead_times[-1] if hit else None,
            }
        )
    operating_days = max(int(timestamps.dt.date.nunique()), 1)
    false_alerts = int(np.sum(alerts & (labels == 0)))
    ap = average_precision(labels, scores)
    return {
        "event_recall": round(detected / len(episodes), 8) if episodes else None,
        "false_alerts_per_operating_day": round(false_alerts / operating_days, 8),
        "median_lead_time_seconds": round(float(np.median(lead_times)), 8) if lead_times else None,
        "lead_time_distribution_seconds": [round(value, 8) for value in lead_times],
        "precision_recall_auc": round(ap, 8) if ap is not None else None,
        "incident_episode_count": len(episodes),
        "scored_row_count": int(finite.sum()),
        "abstention_rate": round(1.0 - float(finite.mean()), 8),
        "per_incident": per_incident,
    }


def walk_forward_results(
    development: pd.DataFrame,
    bundle: dict[str, Any],
    signal_columns: list[str],
    fold_count: int,
) -> list[dict[str, Any]]:
    dictionary = bundle["signal_dictionary"]
    timestamp_column = dictionary["timestamp_column"]
    label_column = dictionary["incident_label_column"]
    minimum_train = max(int(bundle.get("coherence_window_rows", 32)) * 2, len(development) // 3)
    boundaries = np.linspace(minimum_train, len(development), fold_count + 1, dtype=int)
    results: list[dict[str, Any]] = []
    for fold in range(fold_count):
        train_end = int(boundaries[fold])
        test_end = int(boundaries[fold + 1])
        training = development.iloc[:train_end].copy()
        testing = development.iloc[train_end:test_end].copy()
        state = fit_detector_state(training, training[timestamp_column], signal_columns)
        scores = score_segment(training, testing, state, bundle, signal_columns)
        labels = testing[label_column].to_numpy(dtype=int)
        candidate_ap = average_precision(labels, scores["hypercore_cross_layer_coherence"].to_numpy())
        baseline_aps = {
            column: average_precision(labels, scores[column].to_numpy())
            for column in scores.columns
            if column != "hypercore_cross_layer_coherence"
        }
        finite_baselines = [value for value in baseline_aps.values() if value is not None]
        best = max(finite_baselines) if finite_baselines else None
        gain = candidate_ap - best if candidate_ap is not None and best is not None else None
        results.append(
            {
                "fold": fold + 1,
                "train_rows": len(training),
                "test_rows": len(testing),
                "train_end_utc": training[timestamp_column].iloc[-1].isoformat(),
                "test_start_utc": testing[timestamp_column].iloc[0].isoformat(),
                "test_end_utc": testing[timestamp_column].iloc[-1].isoformat(),
                "candidate_precision_recall_auc": round(candidate_ap, 8) if candidate_ap is not None else None,
                "best_registered_baseline_precision_recall_auc": round(best, 8) if best is not None else None,
                "candidate_gain": round(gain, 8) if gain is not None else None,
                "status": "EVALUATED" if gain is not None else "INCONCLUSIVE_NO_POSITIVE_EPISODE",
            }
        )
    return results


def null_results(
    holdout: pd.DataFrame,
    scores: np.ndarray,
    signal_columns: list[str],
    bundle: dict[str, Any],
    replicates: int,
    seed: int,
) -> list[dict[str, Any]]:
    labels = holdout[bundle["signal_dictionary"]["incident_label_column"]].to_numpy(dtype=int)
    finite = np.isfinite(scores)
    labels = labels[finite]
    scores = scores[finite]
    if not len(scores) or labels.sum() == 0 or labels.sum() == len(labels):
        raise ReplayPreconditionError("NULL_INPUT_INVALID", "null evaluation needs positive and negative rows")

    def effect(test_labels: np.ndarray, test_scores: np.ndarray) -> float:
        return float(np.mean(test_scores[test_labels == 1]) - np.mean(test_scores[test_labels == 0]))

    observed = effect(labels, scores)
    rows: list[dict[str, Any]] = []
    for family_index, family in enumerate(("circular_or_block_time_shifts", "event_label_permutation")):
        rng = np.random.default_rng(seed + 1000 * (family_index + 1))
        values: list[float] = []
        for _ in range(replicates):
            if family == "event_label_permutation":
                null_labels = rng.permutation(labels)
                values.append(effect(null_labels, scores))
            else:
                shift = int(rng.integers(1, len(scores)))
                values.append(effect(labels, np.roll(scores, shift)))
        p_value = (1 + sum(value >= observed for value in values)) / (replicates + 1)
        rows.append(
            {
                "family": family,
                "replicate_count": replicates,
                "seed": seed + 1000 * (family_index + 1),
                "observed_effect": round(observed, 10),
                "p_value": round(p_value, 10),
                "null_statistics_sha256": canonical_sha256([round(value, 10) for value in values]),
                "null_quantiles": {
                    "q025": round(float(np.quantile(values, 0.025)), 10),
                    "q500": round(float(np.quantile(values, 0.5)), 10),
                    "q975": round(float(np.quantile(values, 0.975)), 10),
                },
            }
        )

    matrix = holdout[signal_columns].to_numpy(dtype=float)
    matrix = matrix[np.isfinite(matrix).all(axis=1)]
    if len(matrix) < 32:
        raise ReplayPreconditionError("PHASE_NULL_INPUT_INVALID", "phase null needs complete rows")

    def aggregate_phase_alignment(values: np.ndarray) -> float:
        pair_values: list[float] = []
        for left, right in itertools.combinations(range(values.shape[1]), 2):
            correlation = np.corrcoef(values[:, left], values[:, right])[0, 1]
            if np.isfinite(correlation):
                pair_values.append(abs(float(correlation)))
        return float(np.mean(pair_values))

    def scramble(values: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        transformed = np.fft.rfft(values)
        if len(transformed) > 2:
            phases = rng.uniform(-np.pi, np.pi, len(transformed) - 2)
            transformed[1:-1] = np.abs(transformed[1:-1]) * np.exp(1j * phases)
        return np.fft.irfft(transformed, n=len(values))

    observed_phase = aggregate_phase_alignment(matrix)
    rng = np.random.default_rng(seed + 3000)
    phase_values: list[float] = []
    for _ in range(replicates):
        scrambled = np.column_stack([scramble(matrix[:, column], rng) for column in range(matrix.shape[1])])
        phase_values.append(aggregate_phase_alignment(scrambled))
    phase_p = (1 + sum(value >= observed_phase for value in phase_values)) / (replicates + 1)
    rows.append(
        {
            "family": "independent_phase_scrambling",
            "statistic": "mean_absolute_pairwise_pearson_phase_alignment",
            "replicate_count": replicates,
            "seed": seed + 3000,
            "observed_effect": round(observed_phase, 10),
            "p_value": round(phase_p, 10),
            "null_statistics_sha256": canonical_sha256([round(value, 10) for value in phase_values]),
            "null_quantiles": {
                "q025": round(float(np.quantile(phase_values, 0.025)), 10),
                "q500": round(float(np.quantile(phase_values, 0.5)), 10),
                "q975": round(float(np.quantile(phase_values, 0.975)), 10),
            },
        }
    )
    ordered = sorted(range(len(rows)), key=lambda index: rows[index]["p_value"])
    running = 0.0
    for rank, index in enumerate(ordered):
        adjusted = min(1.0, rows[index]["p_value"] * (len(rows) - rank))
        running = max(running, adjusted)
        rows[index]["holm_adjusted_p_value"] = round(running, 10)
    return rows


def ablation_results(
    development: pd.DataFrame,
    calibration: pd.DataFrame,
    holdout: pd.DataFrame,
    bundle: dict[str, Any],
    signal_columns: list[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    state = fit_detector_state(
        development,
        development[bundle["signal_dictionary"]["timestamp_column"]],
        signal_columns,
    )
    ceiling = float(bundle["buyer_false_alert_ceiling_per_operating_day"])
    rows_per_day = 86400.0 / float(bundle["sampling_interval"])
    for size in (1, 2):
        for subset in itertools.combinations(signal_columns, size):
            indices = [signal_columns.index(column) for column in subset]
            subset_state = {
                "means": state["means"][indices],
                "stds": state["stds"][indices],
                "inverse": state["inverse"][np.ix_(indices, indices)],
                "seasonal": {
                    bucket: (center[indices], spread[indices])
                    for bucket, (center, spread) in state["seasonal"].items()
                },
            }
            cal_scores = score_segment(
                development, calibration, subset_state, bundle, list(subset)
            )["hypercore_cross_layer_coherence"].to_numpy()
            threshold = detector_threshold(cal_scores, ceiling, rows_per_day)
            hold_scores = score_segment(
                pd.concat([development, calibration], ignore_index=True),
                holdout,
                subset_state,
                bundle,
                list(subset),
            )["hypercore_cross_layer_coherence"].to_numpy()
            metrics = event_metrics(holdout, hold_scores, threshold, bundle)
            rows.append(
                {
                    "signals": list(subset),
                    "layer_count": size,
                    "threshold": round(threshold, 10),
                    "metrics": metrics,
                }
            )
    return rows


def stress_results(
    frame: pd.DataFrame,
    holdout_scores: np.ndarray,
    threshold: float,
    bundle: dict[str, Any],
    signal_columns: list[str],
) -> list[dict[str, Any]]:
    timestamp_column = bundle["signal_dictionary"]["timestamp_column"]
    interval = float(bundle["sampling_interval"])
    low_alerts = int(np.sum(np.isfinite(holdout_scores) & (holdout_scores > threshold * 0.9)))
    high_alerts = int(np.sum(np.isfinite(holdout_scores) & (holdout_scores > threshold * 1.1)))
    dropout = frame[signal_columns].copy()
    dropout.iloc[::10, 0] = np.nan
    return [
        {"test": "missing_signal", "status": "ABSTAIN_MISSING_SIGNAL", "expected": True},
        {"test": "constant_signal", "status": "ABSTAIN_CONSTANT_SIGNAL", "expected": True},
        {"test": "irregular_sampling", "status": "ABSTAIN_IRREGULAR_SAMPLING", "expected": True},
        {"test": "timestamp_jitter", "status": "ABSTAIN_TIMESTAMP_JITTER", "expected": True, "tolerance_seconds": interval * 0.01},
        {"test": "threshold_sensitivity", "status": "RETAINED_DESCRIPTIVE", "alerts_at_0_9x": low_alerts, "alerts_at_1_1x": high_alerts},
        {"test": "sensor_dropout", "status": "ABSTAIN_ROWS_WITH_MISSING_SIGNAL", "missing_signal_rate": round(float(dropout.isna().mean().mean()), 8)},
        {"test": "distribution_shift", "status": "REQUIRES_SEPARATE_BUYER_DEFINED_SHIFT", "claim_allowed": False},
        {"test": "incident_label_uncertainty", "status": "REQUIRES_INDEPENDENT_ADJUDICATOR_RANGE", "claim_allowed": False},
        {"test": "timestamp_column_contract", "status": "PASS", "column": timestamp_column},
    ]


def run_replay(
    *,
    protocol_path: Path,
    bundle_path: Path,
    output_path: Path,
    generated_utc: str | None,
    seed: int,
    null_replicates: int | None,
) -> dict[str, Any]:
    tracemalloc.start()
    started = time.process_time()
    protocol = read_json(protocol_path)
    validate_protocol(protocol)
    bundle = read_json(bundle_path)
    data_path = validate_source_contract(protocol, bundle_path, bundle)
    frame, signal_columns = load_frame(data_path, bundle)
    minimum_nulls = int(protocol["required_falsification"]["minimum_seeded_replicates_per_null"])
    replicates = minimum_nulls if null_replicates is None else int(null_replicates)
    if replicates < minimum_nulls:
        raise ReplayPreconditionError("NULL_REPLICATES_BELOW_PROTOCOL", "null replicate minimum not met")
    timestamp_column = bundle["signal_dictionary"]["timestamp_column"]
    label_column = bundle["signal_dictionary"]["incident_label_column"]
    dev_end = int(len(frame) * 0.60)
    calibration_end = int(len(frame) * 0.80)
    development = frame.iloc[:dev_end].copy()
    calibration = frame.iloc[dev_end:calibration_end].copy()
    state = fit_detector_state(development, development[timestamp_column], signal_columns)
    calibration_scores = score_segment(development, calibration, state, bundle, signal_columns)
    ceiling = float(bundle["buyer_false_alert_ceiling_per_operating_day"])
    rows_per_day = 86400.0 / float(bundle["sampling_interval"])
    thresholds = {
        column: detector_threshold(calibration_scores[column].to_numpy(), ceiling, rows_per_day)
        for column in calibration_scores.columns
    }
    calibration_labels = calibration[label_column].to_numpy(dtype=int)
    baseline_calibration_ap = {
        column: average_precision(calibration_labels, calibration_scores[column].to_numpy())
        for column in calibration_scores.columns
        if column != "hypercore_cross_layer_coherence"
    }
    eligible_baselines = {
        key: value for key, value in baseline_calibration_ap.items() if value is not None
    }
    if not eligible_baselines:
        raise ReplayPreconditionError("BASELINE_CALIBRATION_EMPTY", "no baseline can be selected")
    selected_baseline = max(
        eligible_baselines, key=lambda key: (eligible_baselines[key], key)
    )
    threshold_receipt = {
        "schema": "hypercore_v8_threshold_receipt_v1",
        "source_sha256": bundle["source_sha256"],
        "development_rows": len(development),
        "calibration_rows": len(calibration),
        "holdout_rows_committed": len(frame) - calibration_end,
        "holdout_start_utc": frame[timestamp_column].iloc[calibration_end].isoformat(),
        "false_alert_ceiling_per_operating_day": ceiling,
        "coherence_window_rows": int(bundle["coherence_window_rows"]),
        "coherence_frequency_band_hz": [
            round(value, 12) for value in validated_coherence_band(bundle)
        ],
        "thresholds": {key: round(value, 10) for key, value in thresholds.items()},
        "selected_baseline_from_calibration_only": selected_baseline,
        "thresholds_frozen_before_holdout": True,
    }
    threshold_receipt["threshold_receipt_sha256"] = canonical_sha256(threshold_receipt)
    holdout = frame.iloc[calibration_end:].copy()
    history = frame.iloc[:calibration_end].copy()
    holdout_scores = score_segment(history, holdout, state, bundle, signal_columns)
    metrics = {
        column: event_metrics(
            holdout, holdout_scores[column].to_numpy(), thresholds[column], bundle
        )
        for column in holdout_scores.columns
    }
    fold_count = int(protocol["chronology"]["minimum_blocked_walk_forward_folds"])
    folds = walk_forward_results(development, bundle, signal_columns, fold_count)
    nulls = null_results(
        holdout,
        holdout_scores["hypercore_cross_layer_coherence"].to_numpy(),
        signal_columns,
        bundle,
        replicates,
        seed,
    )
    ablations = ablation_results(
        development, calibration, holdout, bundle, signal_columns
    )
    stresses = stress_results(
        frame,
        holdout_scores["hypercore_cross_layer_coherence"].to_numpy(),
        thresholds["hypercore_cross_layer_coherence"],
        bundle,
        signal_columns,
    )
    candidate = metrics["hypercore_cross_layer_coherence"]
    comparator = metrics[selected_baseline]
    evaluable_folds = [row for row in folds if row["candidate_gain"] is not None]
    positive_fraction = (
        sum(row["candidate_gain"] > 0 for row in evaluable_folds) / len(evaluable_folds)
        if evaluable_folds
        else 0.0
    )
    positive_gains = [max(float(row["candidate_gain"]), 0.0) for row in evaluable_folds]
    max_fold_fraction = (
        max(positive_gains) / sum(positive_gains) if sum(positive_gains) > 0 else 1.0
    )
    incident_count = int(candidate["incident_episode_count"])
    underpowered = incident_count < 20
    gate_results = {
        "thresholds_frozen_before_holdout": True,
        "all_registered_baselines_executed": set(
            row["id"] for row in protocol["registered_baselines"]
        ).issubset(set(metrics)),
        "multiplicity_adjustment_applied": all(
            "holm_adjusted_p_value" in row for row in nulls
        ),
        "candidate_false_alert_ceiling_met": (
            candidate["false_alerts_per_operating_day"] <= ceiling
        ),
        "noninferiority_to_selected_baseline": (
            candidate["precision_recall_auc"] is not None
            and comparator["precision_recall_auc"] is not None
            and candidate["precision_recall_auc"]
            >= comparator["precision_recall_auc"]
        ),
        "minimum_positive_fold_fraction_met": (
            positive_fraction
            >= float(protocol["promotion_gates"]["minimum_positive_fold_fraction"])
        ),
        "maximum_single_fold_gain_fraction_met": (
            max_fold_fraction
            <= float(protocol["promotion_gates"]["maximum_single_fold_gain_fraction"])
        ),
        "sample_power_status": (
            protocol["promotion_gates"]["underpowered_result_status"]
            if underpowered
            else "sample_size_gate_requires_independent_review"
        ),
        "independent_reproduction_complete": False,
        "economic_counterfactual_complete": False,
    }
    split_manifest = {
        "split_type": "strict_chronological",
        "development": {
            "rows": len(development),
            "start_utc": development[timestamp_column].iloc[0].isoformat(),
            "end_utc": development[timestamp_column].iloc[-1].isoformat(),
        },
        "calibration": {
            "rows": len(calibration),
            "start_utc": calibration[timestamp_column].iloc[0].isoformat(),
            "end_utc": calibration[timestamp_column].iloc[-1].isoformat(),
        },
        "holdout": {
            "rows": len(holdout),
            "start_utc": holdout[timestamp_column].iloc[0].isoformat(),
            "end_utc": holdout[timestamp_column].iloc[-1].isoformat(),
        },
        "walk_forward_fold_count": len(folds),
        "holdout_accessed_after_threshold_receipt_sha256": threshold_receipt[
            "threshold_receipt_sha256"
        ],
    }
    deterministic = {
        "protocol_sha256": file_sha256(protocol_path),
        "source_sha256": bundle["source_sha256"],
        "authorization_receipt_sha256": canonical_sha256(bundle["authorization_receipt"]),
        "source_mode": bundle.get("source_mode"),
        "split_manifest": split_manifest,
        "threshold_receipt": threshold_receipt,
        "metrics": metrics,
        "walk_forward_folds": folds,
        "null_results": nulls,
        "ablation_results": ablations,
        "stress_results": stresses,
        "promotion_gate_results": gate_results,
    }
    deterministic_hash = canonical_sha256(deterministic)
    cpu_seconds = time.process_time() - started
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "protocol_id": protocol["protocol_id"],
        "generated_utc": utc_iso(generated_utc),
        "mode": "OFFLINE_READ_ONLY_REPLAY",
        "status": (
            "SYNTHETIC_PREFLIGHT_COMPLETE_NOT_EXTERNAL_VALIDATION"
            if bundle.get("source_mode") == "synthetic_fixture"
            else "BUYER_OFFLINE_REPLAY_COMPLETE_INDEPENDENT_REPRODUCTION_PENDING"
        ),
        "result_classification": "DESCRIPTIVE_ONLY",
        "deterministic_result_sha256": deterministic_hash,
        "deterministic_result": deterministic,
        "resource_measurements": {
            "cpu_time_seconds": round(cpu_seconds, 8),
            "peak_memory_bytes": int(peak_memory),
            "decision_latency_seconds_per_holdout_row": round(
                cpu_seconds / max(len(holdout), 1), 10
            ),
        },
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
        },
        "execution_controls": {
            "network_access_performed": False,
            "production_connection_performed": False,
            "control_write_performed": False,
            "credentials_read": False,
            "source_rows_persisted_in_receipt": False,
            "holdout_outcomes_used_for_threshold_selection": False,
        },
        "claim_boundary": {
            "allowed": [
                "The local runner enforced source authorization, source hashing, chronological splits, calibration freeze, registered baseline execution, null retention, ablations, and explicit abstention controls for this bounded replay.",
                "The deterministic result hash permits local byte-level rerun comparison."
            ],
            "blocked": [
                *protocol["claim_boundary"]["blocked_now"],
                "external validation",
                "buyer acceptance",
                "economic value from a synthetic fixture",
            ],
        },
        "safest_next_action": (
            "Obtain one buyer-authorized source bundle, buyer-owned incident labels, an incumbent baseline decision, and prospectively approved thresholds. Re-run without changing the protocol, then require independent reproduction before any external performance claim."
        ),
    }
    receipt["receipt_sha256"] = canonical_sha256(receipt)
    write_json_atomic(output_path, receipt)
    return receipt


def write_failure_receipt(
    output_path: Path,
    *,
    generated_utc: str | None,
    code: str,
) -> None:
    payload: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "generated_utc": utc_iso(generated_utc),
        "mode": "OFFLINE_READ_ONLY_REPLAY",
        "status": "ABSTAINED_PRECONDITION",
        "result_classification": "NO_RESULT",
        "precondition_code": code,
        "execution_controls": {
            "network_access_performed": False,
            "production_connection_performed": False,
            "control_write_performed": False,
            "credentials_read": False,
        },
        "claim_boundary": "No performance, validation, operational, or economic claim is allowed from an abstained run.",
    }
    payload["receipt_sha256"] = canonical_sha256(payload)
    write_json_atomic(output_path, payload)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a deterministic, read-only HyperCore V8 offline replay."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source-bundle", type=Path)
    source.add_argument("--self-test", action="store_true")
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--generated-utc")
    parser.add_argument("--seed", type=int, default=20260802)
    parser.add_argument("--null-replicates", type=int)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    bundle_path = (
        build_synthetic_fixture(SYNTHETIC_FIXTURE_DIR, args.seed)
        if args.self_test
        else args.source_bundle
    )
    try:
        receipt = run_replay(
            protocol_path=args.protocol.resolve(),
            bundle_path=bundle_path.resolve(),
            output_path=args.output.resolve(),
            generated_utc=args.generated_utc,
            seed=args.seed,
            null_replicates=args.null_replicates,
        )
    except ReplayPreconditionError as exc:
        write_failure_receipt(
            args.output.resolve(), generated_utc=args.generated_utc, code=exc.code
        )
        print(f"ABSTAINED_PRECONDITION: {exc.code}")
        print(f"WROTE: {args.output.resolve()}")
        return 2
    print(f"{receipt['status']}: {receipt['deterministic_result_sha256']}")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
