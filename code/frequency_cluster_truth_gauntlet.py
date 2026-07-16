from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "config" / "frequency_cluster_truth_gauntlet_protocol_v1.json"
DEFAULT_OUT = ROOT / "out" / "frequency_cluster_truth_gauntlet"
KRAKEN_BASE_URL = "https://api.kraken.com"

EVIDENCE_BOUNDARY = (
    "Official-source Kraken market data and an internally hash-sealed benchmark do not constitute "
    "independent validation, Kraken endorsement, a trading recommendation, guaranteed alpha, "
    "realized savings, or authorization to place orders."
)


@dataclass(frozen=True)
class PairSeries:
    pair: str
    source_file: Path
    timestamps: np.ndarray
    closes: np.ndarray
    highs: np.ndarray
    lows: np.ndarray
    volumes: np.ndarray
    returns_bps: np.ndarray
    target: np.ndarray
    quality: dict[str, Any]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    os.replace(temporary, path)


def compute_run_identity(input_dir: Path, protocol_path: Path) -> dict[str, Any]:
    input_hashes = {
        path.name: sha256_file(path)
        for path in sorted(input_dir.glob("kraken_*m.csv"), key=lambda item: item.name.lower())
    }
    payload = {
        "protocol_sha256": sha256_file(protocol_path),
        "normalized_input_sha256": input_hashes,
    }
    return {
        **payload,
        "run_identity_sha256": sha256_payload(payload),
        "input_file_count": len(input_hashes),
    }


def find_prior_scored_run(
    out_root: Path,
    current_run_dir: Path,
    run_identity_sha256: str,
    protocol_path: Path,
) -> Path | None:
    for candidate in sorted(out_root.glob("frequency_cluster_truth_gauntlet_*")):
        if candidate == current_run_dir or not candidate.is_dir():
            continue
        summary_path = candidate / "summary.json"
        input_dir = candidate / "inputs"
        if not summary_path.exists() or not input_dir.exists():
            continue
        try:
            summary = read_json(summary_path)
            candidate_identity = str(summary.get("run_identity_sha256") or "")
            if not candidate_identity:
                candidate_identity = str(
                    compute_run_identity(input_dir, protocol_path)["run_identity_sha256"]
                )
        except Exception:
            continue
        if candidate_identity != run_identity_sha256:
            continue
        if isinstance(summary.get("aggregate"), dict) and summary.get("pair_results"):
            return candidate
    return None


def audit_run_identities(out_root: Path, protocol_path: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for candidate in sorted(out_root.glob("frequency_cluster_truth_gauntlet_*")):
        summary_path = candidate / "summary.json"
        input_dir = candidate / "inputs"
        if not candidate.is_dir() or not summary_path.exists() or not input_dir.exists():
            continue
        try:
            summary = read_json(summary_path)
            identity = str(summary.get("run_identity_sha256") or "")
            if not identity:
                identity = str(compute_run_identity(input_dir, protocol_path)["run_identity_sha256"])
        except Exception as exc:
            rows.append({"run_dir": str(candidate), "error": str(exc)})
            continue
        rows.append(
            {
                "run_dir": str(candidate),
                "run_name": candidate.name,
                "run_identity_sha256": identity,
                "decision": summary.get("decision"),
                "evidence_receipt_sha256": summary.get("evidence_receipt_sha256"),
                "contains_scored_holdout": bool(
                    isinstance(summary.get("aggregate"), dict) and summary.get("pair_results")
                ),
            }
        )

    groups: list[dict[str, Any]] = []
    identities = sorted({row.get("run_identity_sha256") for row in rows if row.get("run_identity_sha256")})
    for identity in identities:
        members = [row for row in rows if row.get("run_identity_sha256") == identity]
        scored = [row for row in members if row.get("contains_scored_holdout")]
        primary = scored[0] if scored else members[0]
        groups.append(
            {
                "run_identity_sha256": identity,
                "primary_run": primary.get("run_dir"),
                "member_count": len(members),
                "scored_run_count": len(scored),
                "duplicate_scored_runs": [row.get("run_dir") for row in scored[1:]],
                "duplicate_runs_are_independent_confirmations": False,
                "evidence_receipts_match": len(
                    {
                        row.get("evidence_receipt_sha256")
                        for row in scored
                        if row.get("evidence_receipt_sha256")
                    }
                )
                <= 1,
                "members": members,
            }
        )
    audit = {
        "schema": "frequency_cluster_run_identity_audit_v1",
        "generated_utc": now_utc(),
        "protocol_sha256": sha256_file(protocol_path),
        "run_count": len(rows),
        "identity_group_count": len(groups),
        "groups": groups,
        "truth_boundary": (
            "Repeated scoring of the same protocol and identical normalized source files is a "
            "duplicate computation, not independent replication or additional evidence."
        ),
    }
    write_json(out_root / "run_identity_audit.json", audit)
    return audit


def validate_protocol(protocol: dict[str, Any]) -> dict[str, Any]:
    if protocol.get("schema") != "frequency_cluster_truth_gauntlet_protocol_v1":
        raise ValueError("unexpected frequency-cluster protocol schema")
    if protocol.get("execution_authorized") is not False:
        raise ValueError("execution must remain disabled")
    if protocol.get("capital_at_risk_allowed") is not False:
        raise ValueError("capital-at-risk actions must remain disabled")
    if protocol.get("holdout_used_for_selection") is not False:
        raise ValueError("holdout selection must remain disabled")
    if protocol.get("null_and_adverse_results_retained") is not True:
        raise ValueError("null and adverse result retention must remain enabled")

    split = protocol.get("splits") or {}
    split_sum = sum(
        float(split.get(key) or 0.0)
        for key in ("discovery_fraction", "calibration_fraction", "holdout_fraction")
    )
    if not math.isclose(split_sum, 1.0, abs_tol=1e-12):
        raise ValueError("split fractions must sum to one")
    if split.get("chronological") is not True:
        raise ValueError("chronological splitting is required")

    data = protocol.get("data") or {}
    pairs = [str(value) for value in data.get("fixed_pair_universe") or []]
    if len(pairs) < int(data.get("minimum_eligible_pairs") or 0):
        raise ValueError("fixed pair universe is smaller than the minimum eligible cohort")
    if len(pairs) != len(set(pairs)):
        raise ValueError("fixed pair universe contains duplicates")

    discovery = protocol.get("frequency_discovery") or {}
    periods = [float(value) for value in discovery.get("candidate_periods_days") or []]
    if not periods or min(periods) <= 1.0 or periods != sorted(set(periods)):
        raise ValueError("candidate periods must be sorted, unique, and greater than one day")
    if int(discovery.get("maximum_selected_periods") or 0) < 1:
        raise ValueError("at least one selected period is required")

    variants = (protocol.get("models") or {}).get("candidate_variants") or []
    names: list[str] = []
    for row in variants:
        names.append(str(row.get("name") or ""))
        total = sum(float(row.get(key) or 0.0) for key in ("harmonic", "ewma", "weekday"))
        if not math.isclose(total, 1.0, abs_tol=1e-12):
            raise ValueError(f"candidate weights must sum to one: {row.get('name')}")
        if float(row.get("harmonic") or 0.0) <= 0.0:
            raise ValueError(f"candidate must contain a frequency component: {row.get('name')}")
    if not names or len(names) != len(set(names)) or any(not name for name in names):
        raise ValueError("candidate variant names must be non-empty and unique")

    inference = protocol.get("inference") or {}
    if str(inference.get("pair_family_correction")) != "holm":
        raise ValueError("this protocol requires Holm family correction")
    if int(inference.get("time_block_days") or 0) < 2:
        raise ValueError("time-block bootstrap must preserve multi-day dependence")

    shadow = protocol.get("directional_shadow_lane") or {}
    if shadow.get("orders_allowed") is not False or shadow.get("live_execution_allowed") is not False:
        raise ValueError("directional shadow lane must not authorize orders")
    if shadow.get("promotion_allowed") is not False:
        raise ValueError("directional shadow lane must remain non-promotional")

    return {
        "valid": True,
        "pair_count": len(pairs),
        "candidate_period_count": len(periods),
        "candidate_variant_count": len(variants),
        "holdout_selection_disabled": True,
        "execution_disabled": True,
        "adverse_result_retention_enabled": True,
    }


def kraken_get(
    session: requests.Session,
    path: str,
    params: dict[str, Any] | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    response = session.get(f"{KRAKEN_BASE_URL}{path}", params=params, timeout=timeout_seconds)
    response.raise_for_status()
    payload = response.json()
    errors = payload.get("error") or []
    if errors:
        raise RuntimeError(f"Kraken {path} error: {errors}")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"Kraken {path} returned a non-object result")
    return result


def safe_pair_name(pair: str) -> str:
    return pair.replace("/", "_").replace("-", "_")


def fetch_kraken_inputs(
    protocol: dict[str, Any],
    input_dir: Path,
    timeout_seconds: float,
    pause_seconds: float,
) -> dict[str, Any]:
    data = protocol["data"]
    interval_minutes = int(data["interval_minutes"])
    interval_seconds = interval_minutes * 60
    session = requests.Session()
    session.headers.update({"User-Agent": "LumenCoreFrequencyTruthGauntlet/1.0"})
    pair_payload = kraken_get(
        session,
        str(data["asset_pairs_path"]),
        None,
        timeout_seconds,
    )

    by_wsname: dict[str, tuple[str, dict[str, Any]]] = {}
    for pair_id, metadata in pair_payload.items():
        if not isinstance(metadata, dict) or str(metadata.get("status") or "") != "online":
            continue
        wsname = str(metadata.get("wsname") or "").upper()
        if wsname:
            by_wsname[wsname] = (str(pair_id), metadata)

    aliases = {"BTC/USD": "XBT/USD", "DOGE/USD": "XDG/USD"}
    retrieved_epoch = int(datetime.now(timezone.utc).timestamp())
    selected_metadata: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    input_dir.mkdir(parents=True, exist_ok=True)

    for configured_pair in data["fixed_pair_universe"]:
        requested = aliases.get(str(configured_pair).upper(), str(configured_pair).upper())
        mapping = by_wsname.get(requested)
        if mapping is None:
            errors.append({"pair": configured_pair, "error": "fixed_pair_not_available_online"})
            continue
        pair_id, metadata = mapping
        try:
            result = kraken_get(
                session,
                str(data["ohlc_path"]),
                {"pair": pair_id, "interval": interval_minutes},
                timeout_seconds,
            )
            rows: list[list[Any]] = []
            for key, value in result.items():
                if key != "last" and isinstance(value, list):
                    rows = value
                    break
            normalized: list[dict[str, Any]] = []
            for row in rows:
                if not isinstance(row, list) or len(row) < 8:
                    continue
                timestamp = int(float(row[0]))
                if bool(data["exclude_current_incomplete_candle"]):
                    if timestamp + interval_seconds > retrieved_epoch:
                        continue
                normalized.append(
                    {
                        "timestamp_utc": timestamp,
                        "time_utc": datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(),
                        "open": row[1],
                        "high": row[2],
                        "low": row[3],
                        "close": row[4],
                        "vwap": row[5],
                        "volume": row[6],
                        "trade_count": row[7],
                    }
                )
            normalized.sort(key=lambda item: int(item["timestamp_utc"]))
            path = input_dir / f"kraken_{safe_pair_name(requested)}_{interval_minutes}m.csv"
            write_csv(
                path,
                normalized,
                [
                    "timestamp_utc",
                    "time_utc",
                    "open",
                    "high",
                    "low",
                    "close",
                    "vwap",
                    "volume",
                    "trade_count",
                ],
            )
            selected_metadata.append(
                {
                    "configured_pair": configured_pair,
                    "resolved_pair": requested,
                    "pair_id": pair_id,
                    "altname": metadata.get("altname"),
                    "wsname": metadata.get("wsname"),
                    "base": metadata.get("base"),
                    "quote": metadata.get("quote"),
                }
            )
            receipts.append(
                {
                    "pair": requested,
                    "pair_id": pair_id,
                    "rows": len(normalized),
                    "first_utc": normalized[0]["time_utc"] if normalized else None,
                    "last_utc": normalized[-1]["time_utc"] if normalized else None,
                    "source_file": str(path),
                    "source_file_sha256": sha256_file(path),
                    "request_path": str(data["ohlc_path"]),
                    "request_interval_minutes": interval_minutes,
                }
            )
        except Exception as exc:
            errors.append({"pair": requested, "pair_id": pair_id, "error": str(exc)})
        if pause_seconds > 0:
            time.sleep(pause_seconds)

    receipt = {
        "schema": "kraken_frequency_gauntlet_retrieval_receipt_v1",
        "retrieved_utc": datetime.fromtimestamp(retrieved_epoch, tz=timezone.utc).isoformat(),
        "provider": "Kraken",
        "base_url": KRAKEN_BASE_URL,
        "public_endpoints_only": True,
        "authentication_used": False,
        "interval_minutes": interval_minutes,
        "incomplete_candle_excluded": bool(data["exclude_current_incomplete_candle"]),
        "selected_pair_metadata": selected_metadata,
        "pair_receipts": receipts,
        "errors": errors,
    }
    write_json(input_dir / "retrieval_receipt.json", receipt)
    return receipt


def load_pair_series(path: Path, pair: str, protocol: dict[str, Any]) -> PairSeries:
    timestamps: list[int] = []
    closes: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    volumes: list[float] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                timestamp = int(float(row.get("timestamp_utc") or 0))
                close = float(row.get("close") or 0.0)
                high = float(row.get("high") or 0.0)
                low = float(row.get("low") or 0.0)
                volume = float(row.get("volume") or 0.0)
            except Exception:
                continue
            if timestamp <= 0 or min(close, high, low) <= 0.0 or high < low:
                continue
            timestamps.append(timestamp)
            closes.append(close)
            highs.append(high)
            lows.append(low)
            volumes.append(max(0.0, volume))

    if len(timestamps) < 3:
        raise ValueError("insufficient valid OHLC rows")
    order = np.argsort(np.asarray(timestamps, dtype=np.int64))
    ts = np.asarray(timestamps, dtype=np.int64)[order]
    close_values = np.asarray(closes, dtype=float)[order]
    high_values = np.asarray(highs, dtype=float)[order]
    low_values = np.asarray(lows, dtype=float)[order]
    volume_values = np.asarray(volumes, dtype=float)[order]
    unique_mask = np.concatenate(([True], np.diff(ts) > 0))
    ts = ts[unique_mask]
    close_values = close_values[unique_mask]
    high_values = high_values[unique_mask]
    low_values = low_values[unique_mask]
    volume_values = volume_values[unique_mask]

    returns_bps = np.diff(np.log(close_values)) * 10000.0
    target = np.log1p(np.abs(returns_bps))
    interval_seconds = int(protocol["data"]["interval_minutes"]) * 60
    expected_rows = max(1, int(round((int(ts[-1]) - int(ts[0])) / interval_seconds)) + 1)
    missing_fraction = max(0.0, 1.0 - (len(ts) / expected_rows))
    nonzero_volume_fraction = float(np.mean(volume_values > 0.0))
    nonzero_return_fraction = float(np.mean(np.abs(returns_bps) > 1e-12))
    maximum_return_bps = float(np.max(np.abs(returns_bps)))
    gates = protocol["data"]["quality_gates"]
    checks = {
        "minimum_returns": len(returns_bps) >= int(protocol["data"]["minimum_returns_per_pair"]),
        "missing_interval_fraction": missing_fraction <= float(gates["maximum_missing_interval_fraction"]),
        "nonzero_volume_fraction": nonzero_volume_fraction >= float(gates["minimum_nonzero_volume_fraction"]),
        "nonzero_return_fraction": nonzero_return_fraction >= float(gates["minimum_nonzero_return_fraction"]),
        "maximum_single_return": maximum_return_bps <= float(gates["maximum_single_return_bps"]),
    }
    quality = {
        "rows": len(ts),
        "returns": len(returns_bps),
        "first_utc": datetime.fromtimestamp(int(ts[0]), tz=timezone.utc).isoformat(),
        "last_utc": datetime.fromtimestamp(int(ts[-1]), tz=timezone.utc).isoformat(),
        "missing_interval_fraction": missing_fraction,
        "nonzero_volume_fraction": nonzero_volume_fraction,
        "nonzero_return_fraction": nonzero_return_fraction,
        "maximum_absolute_return_bps": maximum_return_bps,
        "checks": checks,
        "pass": all(checks.values()),
    }
    return PairSeries(
        pair=pair,
        source_file=path,
        timestamps=ts[1:],
        closes=close_values[1:],
        highs=high_values[1:],
        lows=low_values[1:],
        volumes=volume_values[1:],
        returns_bps=returns_bps,
        target=target,
        quality=quality,
    )


def load_inputs(input_dir: Path, protocol: dict[str, Any]) -> tuple[list[PairSeries], list[dict[str, Any]]]:
    eligible: list[PairSeries] = []
    rejected: list[dict[str, Any]] = []
    interval = int(protocol["data"]["interval_minutes"])
    for pair in protocol["data"]["fixed_pair_universe"]:
        path = input_dir / f"kraken_{safe_pair_name(str(pair).upper())}_{interval}m.csv"
        if not path.exists():
            rejected.append({"pair": pair, "reason": "source_file_missing", "path": str(path)})
            continue
        try:
            series = load_pair_series(path, str(pair).upper(), protocol)
        except Exception as exc:
            rejected.append({"pair": pair, "reason": "source_parse_failed", "error": str(exc)})
            continue
        if series.quality["pass"]:
            eligible.append(series)
        else:
            rejected.append({"pair": pair, "reason": "quality_gate_failed", "quality": series.quality})
    return eligible, rejected


def split_counts(length: int, protocol: dict[str, Any]) -> tuple[int, int, int]:
    split = protocol["splits"]
    discovery = int(math.floor(length * float(split["discovery_fraction"])))
    calibration = int(math.floor(length * float(split["calibration_fraction"])))
    holdout = length - discovery - calibration
    if min(discovery, calibration, holdout) < 2:
        raise ValueError("split produced an insufficient segment")
    return discovery, calibration, holdout


def harmonic_design(day_index: np.ndarray, periods: Iterable[float]) -> np.ndarray:
    columns = [np.ones(len(day_index), dtype=float)]
    days = np.asarray(day_index, dtype=float)
    for period in periods:
        phase = (2.0 * math.pi * days) / float(period)
        columns.append(np.sin(phase))
        columns.append(np.cos(phase))
    return np.column_stack(columns)


def fit_harmonic_predict(
    train_day_index: np.ndarray,
    train_target: np.ndarray,
    predict_day_index: np.ndarray,
    periods: Iterable[float],
) -> np.ndarray:
    train_design = harmonic_design(train_day_index, periods)
    predict_design = harmonic_design(predict_day_index, periods)
    coefficients = np.linalg.lstsq(train_design, train_target, rcond=None)[0]
    return np.maximum(0.0, predict_design @ coefficients)


def partial_r2(day_index: np.ndarray, target: np.ndarray, period: float) -> float:
    if len(target) < 4:
        return 0.0
    baseline_error = float(np.sum((target - float(np.mean(target))) ** 2))
    if baseline_error <= 1e-18:
        return 0.0
    design = harmonic_design(day_index, [period])
    fitted = design @ np.linalg.lstsq(design, target, rcond=None)[0]
    residual_error = float(np.sum((target - fitted) ** 2))
    return max(0.0, 1.0 - residual_error / baseline_error)


def discover_frequency_clusters(
    series_rows: list[PairSeries],
    protocol: dict[str, Any],
) -> tuple[list[float], list[dict[str, Any]]]:
    discovery = protocol["frequency_discovery"]
    candidate_periods = [float(value) for value in discovery["candidate_periods_days"]]
    per_period: list[dict[str, Any]] = []
    pair_scores: dict[str, dict[float, float]] = {}
    for series in series_rows:
        discovery_count, _, _ = split_counts(len(series.target), protocol)
        days = series.timestamps[:discovery_count].astype(float) / 86400.0
        target = series.target[:discovery_count]
        scores: dict[float, float] = {}
        for period in candidate_periods:
            cycles = discovery_count / period
            if cycles < float(discovery["minimum_discovery_cycles"]):
                continue
            scores[period] = partial_r2(days, target, period)
        pair_scores[series.pair] = scores

    top_by_pair = {
        pair: {
            period
            for period, _score in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:3]
        }
        for pair, scores in pair_scores.items()
    }
    for period in candidate_periods:
        values = [scores[period] for scores in pair_scores.values() if period in scores]
        if not values:
            continue
        per_period.append(
            {
                "period_days": period,
                "pair_count": len(values),
                "median_partial_r2": float(np.median(values)),
                "mean_partial_r2": float(np.mean(values)),
                "top3_pair_count": sum(period in periods for periods in top_by_pair.values()),
                "top3_pair_fraction": sum(period in periods for periods in top_by_pair.values())
                / max(1, len(top_by_pair)),
            }
        )
    per_period.sort(key=lambda row: (row["median_partial_r2"], row["mean_partial_r2"]), reverse=True)

    selected: list[float] = []
    minimum_ratio = float(discovery["minimum_period_ratio_separation"])
    for row in per_period:
        period = float(row["period_days"])
        if all(max(period / prior, prior / period) >= minimum_ratio for prior in selected):
            selected.append(period)
        if len(selected) >= int(discovery["maximum_selected_periods"]):
            break
    for rank, row in enumerate(per_period, start=1):
        row["development_rank"] = rank
        row["selected"] = float(row["period_days"]) in selected
    return selected, per_period


def ewma_predictions(train_target: np.ndarray, test_target: np.ndarray, half_life: float) -> np.ndarray:
    alpha = 1.0 - math.exp(math.log(0.5) / half_life)
    previous = float(train_target[-1])
    predictions: list[float] = []
    for observed in test_target:
        predictions.append(previous)
        previous = alpha * float(observed) + (1.0 - alpha) * previous
    return np.asarray(predictions, dtype=float)


def weekday_predictions(
    train_day_index: np.ndarray,
    train_target: np.ndarray,
    test_day_index: np.ndarray,
) -> np.ndarray:
    train_weekdays = np.mod(train_day_index.astype(np.int64) + 3, 7)
    test_weekdays = np.mod(test_day_index.astype(np.int64) + 3, 7)
    global_median = float(np.median(train_target))
    medians = {
        weekday: float(np.median(train_target[train_weekdays == weekday]))
        for weekday in range(7)
        if np.any(train_weekdays == weekday)
    }
    return np.asarray([medians.get(int(value), global_median) for value in test_weekdays])


def moving_block_indices(
    length: int,
    block_size: int,
    repetitions: int,
    rng: np.random.Generator,
) -> Iterable[np.ndarray]:
    effective_block = min(max(1, block_size), length)
    maximum_start = max(1, length - effective_block + 1)
    for _ in range(repetitions):
        indexes: list[int] = []
        while len(indexes) < length:
            start = int(rng.integers(0, maximum_start))
            indexes.extend(range(start, start + effective_block))
        yield np.asarray(indexes[:length], dtype=np.int64)


def percentile_interval(values: Iterable[float], alpha: float = 0.05) -> list[float]:
    array = np.asarray(list(values), dtype=float)
    if len(array) == 0:
        return [0.0, 0.0]
    bounds = np.quantile(array, [alpha / 2.0, 1.0 - alpha / 2.0])
    return [float(bounds[0]), float(bounds[1])]


def holm_adjust(p_values: list[float]) -> list[float]:
    count = len(p_values)
    if count == 0:
        return []
    order = sorted(range(count), key=lambda index: p_values[index])
    adjusted = [1.0] * count
    running = 0.0
    for rank, index in enumerate(order):
        candidate = min(1.0, (count - rank) * float(p_values[index]))
        running = max(running, candidate)
        adjusted[index] = running
    return adjusted


def variant_lookup(protocol: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["name"]): row for row in protocol["models"]["candidate_variants"]}


def matched_no_frequency(
    weights: dict[str, Any],
    median_prediction: np.ndarray,
    ewma_prediction: np.ndarray,
    weekday_prediction: np.ndarray,
) -> np.ndarray:
    ewma_weight = float(weights["ewma"])
    weekday_weight = float(weights["weekday"])
    nonfrequency_total = ewma_weight + weekday_weight
    if nonfrequency_total <= 1e-15:
        return median_prediction.copy()
    return (
        (ewma_weight / nonfrequency_total) * ewma_prediction
        + (weekday_weight / nonfrequency_total) * weekday_prediction
    )


def evaluate_pair(
    series: PairSeries,
    periods: list[float],
    protocol: dict[str, Any],
    rng_seed: int,
    fixed_variant: str | None = None,
    run_inference: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    target = series.target
    day_index = series.timestamps.astype(float) / 86400.0
    discovery_count, calibration_count, holdout_count = split_counts(len(target), protocol)
    calibration_end = discovery_count + calibration_count
    discovery_target = target[:discovery_count]
    calibration_target = target[discovery_count:calibration_end]
    holdout_target = target[calibration_end:]

    harmonic_calibration = fit_harmonic_predict(
        day_index[:discovery_count],
        discovery_target,
        day_index[discovery_count:calibration_end],
        periods,
    )
    ewma_calibration = ewma_predictions(
        discovery_target,
        calibration_target,
        float(protocol["models"]["ewma_half_life_days"]),
    )
    weekday_calibration = weekday_predictions(
        day_index[:discovery_count],
        discovery_target,
        day_index[discovery_count:calibration_end],
    )

    variants = variant_lookup(protocol)
    calibration_scores: list[dict[str, Any]] = []
    for name, weights in variants.items():
        prediction = (
            float(weights["harmonic"]) * harmonic_calibration
            + float(weights["ewma"]) * ewma_calibration
            + float(weights["weekday"]) * weekday_calibration
        )
        calibration_scores.append(
            {
                "name": name,
                "mae": float(np.mean(np.abs(calibration_target - prediction))),
            }
        )
    calibration_scores.sort(key=lambda row: (row["mae"], row["name"]))
    selected_variant = fixed_variant or str(calibration_scores[0]["name"])
    if selected_variant not in variants:
        raise ValueError(f"unknown frozen candidate variant: {selected_variant}")
    weights = variants[selected_variant]

    training_target = target[:calibration_end]
    harmonic_holdout = fit_harmonic_predict(
        day_index[:calibration_end],
        training_target,
        day_index[calibration_end:],
        periods,
    )
    ewma_holdout = ewma_predictions(
        training_target,
        holdout_target,
        float(protocol["models"]["ewma_half_life_days"]),
    )
    weekday_holdout = weekday_predictions(
        day_index[:calibration_end],
        training_target,
        day_index[calibration_end:],
    )
    median_holdout = np.repeat(float(np.median(training_target)), holdout_count)
    candidate = (
        float(weights["harmonic"]) * harmonic_holdout
        + float(weights["ewma"]) * ewma_holdout
        + float(weights["weekday"]) * weekday_holdout
    )
    matched = matched_no_frequency(
        weights,
        median_holdout,
        ewma_holdout,
        weekday_holdout,
    )
    baselines = {
        "development_median": median_holdout,
        "online_ewma": ewma_holdout,
        "development_weekday_median": weekday_holdout,
        "matched_no_frequency": matched,
    }
    absolute_candidate_error = np.abs(holdout_target - candidate)
    error_differences = {
        name: np.abs(holdout_target - prediction) - absolute_candidate_error
        for name, prediction in baselines.items()
    }
    baseline_mae = {
        name: float(np.mean(np.abs(holdout_target - prediction)))
        for name, prediction in baselines.items()
    }
    candidate_mae = float(np.mean(absolute_candidate_error))
    pair_effect = min(float(np.mean(values)) for values in error_differences.values())
    strongest_baseline = min(baseline_mae, key=baseline_mae.get)
    strongest_baseline_mae = float(baseline_mae[strongest_baseline])
    improvement_pct = (
        (strongest_baseline_mae - candidate_mae) / strongest_baseline_mae * 100.0
        if strongest_baseline_mae > 0.0
        else 0.0
    )

    inference = protocol["inference"]
    bootstrap_effects: list[float] = []
    if run_inference:
        rng = np.random.default_rng(rng_seed)
        for indexes in moving_block_indices(
            holdout_count,
            int(inference["time_block_days"]),
            int(inference["pair_block_bootstrap_repetitions"]),
            rng,
        ):
            bootstrap_effects.append(
                min(float(np.mean(values[indexes])) for values in error_differences.values())
            )
    effect_ci95 = (
        percentile_interval(bootstrap_effects, float(inference["alpha"]))
        if bootstrap_effects
        else [0.0, 0.0]
    )

    matched_effect = float(
        np.mean(np.abs(holdout_target - matched) - absolute_candidate_error)
    )
    minimum_shift = int(inference["phase_shift_minimum_days"])
    phase_null: list[float] = []
    if run_inference and holdout_count > 2 * minimum_shift:
        for shift in range(minimum_shift, holdout_count - minimum_shift + 1):
            shifted_candidate = (
                float(weights["harmonic"]) * np.roll(harmonic_holdout, shift)
                + float(weights["ewma"]) * ewma_holdout
                + float(weights["weekday"]) * weekday_holdout
            )
            phase_null.append(
                float(
                    np.mean(
                        np.abs(holdout_target - matched)
                        - np.abs(holdout_target - shifted_candidate)
                    )
                )
            )
    phase_p = (
        (1.0 + sum(value >= matched_effect for value in phase_null)) / (1.0 + len(phase_null))
        if phase_null
        else 1.0
    )

    holdout_period_scores = {
        str(period): partial_r2(day_index[calibration_end:], holdout_target, period)
        for period in protocol["frequency_discovery"]["candidate_periods_days"]
        if holdout_count / float(period)
        >= float(protocol["frequency_discovery"]["minimum_discovery_cycles"])
    }
    holdout_top_periods = [
        float(period)
        for period, _score in sorted(
            ((float(period), score) for period, score in holdout_period_scores.items()),
            key=lambda item: item[1],
            reverse=True,
        )[:3]
    ]

    row = {
        "pair": series.pair,
        "source_file": str(series.source_file),
        "source_file_sha256": sha256_file(series.source_file),
        "quality": series.quality,
        "discovery_samples": discovery_count,
        "calibration_samples": calibration_count,
        "holdout_samples": holdout_count,
        "holdout_first_utc": datetime.fromtimestamp(
            int(series.timestamps[calibration_end]), tz=timezone.utc
        ).isoformat(),
        "holdout_last_utc": datetime.fromtimestamp(
            int(series.timestamps[-1]), tz=timezone.utc
        ).isoformat(),
        "selected_variant": selected_variant,
        "calibration_candidate_scores": calibration_scores,
        "candidate_mae": candidate_mae,
        "baseline_mae": baseline_mae,
        "strongest_baseline": strongest_baseline,
        "strongest_baseline_mae": strongest_baseline_mae,
        "worst_baseline_effect": pair_effect,
        "worst_baseline_improvement_pct": improvement_pct,
        "effect_block_bootstrap_ci95": effect_ci95,
        "matched_no_frequency_effect": matched_effect,
        "phase_shift_p_raw": phase_p,
        "phase_shift_null_count": len(phase_null),
        "holdout_top_periods_days": holdout_top_periods,
        "holdout_selected_period_overlap": len(set(periods).intersection(holdout_top_periods)),
    }
    cache = {
        "target": holdout_target,
        "returns_bps": series.returns_bps[calibration_end:],
        "day_index_train": day_index[:calibration_end],
        "day_index_holdout": day_index[calibration_end:],
        "signed_returns_train": series.returns_bps[:calibration_end],
        "harmonic": harmonic_holdout,
        "ewma": ewma_holdout,
        "weekday": weekday_holdout,
        "median": median_holdout,
        "matched": matched,
        "candidate": candidate,
        "baselines": baselines,
        "weights": weights,
        "selected_variant": selected_variant,
    }
    return row, cache


def aggregate_pair_results(
    pair_rows: list[dict[str, Any]],
    protocol: dict[str, Any],
) -> dict[str, Any]:
    raw_p = [float(row["phase_shift_p_raw"]) for row in pair_rows]
    adjusted = holm_adjust(raw_p)
    alpha = float(protocol["inference"]["alpha"])
    threshold = float(protocol["promotion_gate"]["individual_pair_holm_phase_p_must_not_exceed"])
    for row, p_adjusted in zip(pair_rows, adjusted):
        row["phase_shift_p_holm"] = p_adjusted
        row["individual_gate_checks"] = {
            "positive_against_all_named_baselines": float(row["worst_baseline_effect"]) > 0.0,
            "block_bootstrap_ci95_lower_positive": float(row["effect_block_bootstrap_ci95"][0]) > 0.0,
            "holm_phase_p_pass": p_adjusted <= threshold,
        }
        row["individually_promoted"] = all(row["individual_gate_checks"].values())

    effects = np.asarray([float(row["worst_baseline_effect"]) for row in pair_rows])
    pair_improvement_percentages = np.asarray(
        [
            float(
                row.get(
                    "worst_baseline_improvement_pct",
                    float(row["worst_baseline_effect"])
                    / max(1e-18, min(float(value) for value in row["baseline_mae"].values()))
                    * 100.0,
                )
            )
            for row in pair_rows
        ]
    )
    candidate_mae = np.asarray([float(row["candidate_mae"]) for row in pair_rows])
    baseline_names = list(protocol["models"]["named_baselines"])
    baseline_arrays = {
        name: np.asarray([float(row["baseline_mae"][name]) for row in pair_rows])
        for name in baseline_names
    }
    aggregate_baseline_mae = {name: float(np.mean(values)) for name, values in baseline_arrays.items()}
    strongest_baseline = min(aggregate_baseline_mae, key=aggregate_baseline_mae.get)
    strongest_baseline_mae = float(aggregate_baseline_mae[strongest_baseline])
    aggregate_candidate_mae = float(np.mean(candidate_mae))
    aggregate_improvement_pct = (
        (strongest_baseline_mae - aggregate_candidate_mae) / strongest_baseline_mae * 100.0
        if strongest_baseline_mae > 0.0
        else 0.0
    )

    rng = np.random.default_rng(int(protocol["inference"]["bootstrap_seed"]))
    repetitions = int(protocol["inference"]["aggregate_pair_bootstrap_repetitions"])
    bootstrap_effects: list[float] = []
    bootstrap_pair_percentages: list[float] = []
    bootstrap_percentages: list[float] = []
    for _ in range(repetitions):
        indexes = rng.integers(0, len(pair_rows), size=len(pair_rows))
        bootstrap_effects.append(float(np.mean(effects[indexes])))
        bootstrap_pair_percentages.append(
            float(np.mean(pair_improvement_percentages[indexes]))
        )
        candidate_value = float(np.mean(candidate_mae[indexes]))
        baseline_values = {
            name: float(np.mean(values[indexes])) for name, values in baseline_arrays.items()
        }
        strongest = min(baseline_values.values())
        bootstrap_percentages.append(
            (strongest - candidate_value) / strongest * 100.0 if strongest > 0.0 else 0.0
        )

    leave_one_out = []
    for index, row in enumerate(pair_rows):
        kept = np.delete(effects, index)
        leave_one_out.append(
            {"withheld_pair": row["pair"], "mean_effect": float(np.mean(kept))}
        )
    minimum_leave_one_out = min(row["mean_effect"] for row in leave_one_out)
    positive_fraction = float(np.mean(effects > 0.0))
    individually_promoted = [row["pair"] for row in pair_rows if row["individually_promoted"]]
    checks = {
        "aggregate_pair_effect_positive": float(np.mean(effects)) > 0.0,
        "aggregate_bootstrap_ci95_lower_positive": percentile_interval(
            bootstrap_effects, alpha
        )[0]
        > 0.0,
        "minimum_positive_pair_fraction": positive_fraction
        >= float(protocol["promotion_gate"]["minimum_positive_pair_fraction"]),
        "leave_one_pair_out_minimum_positive": minimum_leave_one_out > 0.0,
        "minimum_individually_promoted_pairs": len(individually_promoted)
        >= int(protocol["promotion_gate"]["minimum_individually_promoted_pairs"]),
    }
    return {
        "pair_count": len(pair_rows),
        "aggregate_candidate_mae": aggregate_candidate_mae,
        "aggregate_baseline_mae": aggregate_baseline_mae,
        "strongest_named_baseline": strongest_baseline,
        "strongest_named_baseline_mae": strongest_baseline_mae,
        "aggregate_improvement_pct_vs_strongest_named_baseline": aggregate_improvement_pct,
        "global_baseline_comparison_only_not_promotion_metric": True,
        "aggregate_improvement_pct_pair_bootstrap_ci95": percentile_interval(
            bootstrap_percentages, alpha
        ),
        "mean_pair_worst_baseline_improvement_pct": float(
            np.mean(pair_improvement_percentages)
        ),
        "mean_pair_worst_baseline_improvement_pct_bootstrap_ci95": percentile_interval(
            bootstrap_pair_percentages, alpha
        ),
        "mean_worst_baseline_effect": float(np.mean(effects)),
        "mean_worst_baseline_effect_pair_bootstrap_ci95": percentile_interval(
            bootstrap_effects, alpha
        ),
        "positive_pair_count": int(np.sum(effects > 0.0)),
        "positive_pair_fraction": positive_fraction,
        "individually_promoted_pairs": individually_promoted,
        "leave_one_pair_out": leave_one_out,
        "minimum_leave_one_pair_out_effect": minimum_leave_one_out,
        "gate_checks": checks,
        "gate_pass": all(checks.values()),
    }


def build_stress_ladder(
    series_rows: list[PairSeries],
    pair_rows: list[dict[str, Any]],
    caches: dict[str, dict[str, Any]],
    periods: list[float],
    protocol: dict[str, Any],
) -> dict[str, Any]:
    time_shift_rows: list[dict[str, Any]] = []
    for shift in protocol["stress_ladder"]["harmonic_time_shifts_days"]:
        effects: list[float] = []
        percentages: list[float] = []
        for row in pair_rows:
            cache = caches[row["pair"]]
            weights = cache["weights"]
            candidate = (
                float(weights["harmonic"]) * np.roll(cache["harmonic"], int(shift))
                + float(weights["ewma"]) * cache["ewma"]
                + float(weights["weekday"]) * cache["weekday"]
            )
            candidate_error = np.abs(cache["target"] - candidate)
            baseline_mae = {
                name: float(np.mean(np.abs(cache["target"] - prediction)))
                for name, prediction in cache["baselines"].items()
            }
            candidate_mae = float(np.mean(candidate_error))
            strongest = min(baseline_mae.values())
            effects.append(
                min(
                    float(np.mean(np.abs(cache["target"] - prediction) - candidate_error))
                    for prediction in cache["baselines"].values()
                )
            )
            percentages.append((strongest - candidate_mae) / strongest * 100.0)
        time_shift_rows.append(
            {
                "stress": "harmonic_time_shift_days",
                "value": int(shift),
                "mean_worst_baseline_effect": float(np.mean(effects)),
                "mean_pair_improvement_pct": float(np.mean(percentages)),
                "positive_pair_fraction": float(np.mean(np.asarray(effects) > 0.0)),
                "survives_positive_effect": float(np.mean(effects)) > 0.0,
            }
        )

    detuning_rows: list[dict[str, Any]] = []
    base_variant = {row["pair"]: str(row["selected_variant"]) for row in pair_rows}
    for factor in protocol["stress_ladder"]["frequency_detuning_factors"]:
        adjusted_periods = [float(period) * float(factor) for period in periods]
        effects: list[float] = []
        percentages: list[float] = []
        for index, series in enumerate(series_rows):
            stressed_row, _cache = evaluate_pair(
                series,
                adjusted_periods,
                protocol,
                int(protocol["inference"]["bootstrap_seed"]) + 100000 + index,
                fixed_variant=base_variant[series.pair],
                run_inference=False,
            )
            effects.append(float(stressed_row["worst_baseline_effect"]))
            percentages.append(float(stressed_row["worst_baseline_improvement_pct"]))
        detuning_rows.append(
            {
                "stress": "frequency_detuning_factor",
                "value": float(factor),
                "periods_days": adjusted_periods,
                "mean_worst_baseline_effect": float(np.mean(effects)),
                "mean_pair_improvement_pct": float(np.mean(percentages)),
                "positive_pair_fraction": float(np.mean(np.asarray(effects) > 0.0)),
                "survives_positive_effect": float(np.mean(effects)) > 0.0,
            }
        )

    directional_rows: list[dict[str, Any]] = []
    for cost_bps in protocol["stress_ladder"]["directional_roundtrip_cost_bps"]:
        pair_net_means: list[float] = []
        pair_total_returns: list[float] = []
        pair_sharpes: list[float] = []
        active_fractions: list[float] = []
        for series in series_rows:
            cache = caches[series.pair]
            predicted_returns = fit_harmonic_predict_signed(
                cache["day_index_train"],
                cache["signed_returns_train"],
                cache["day_index_holdout"],
                periods,
            )
            threshold = float(cost_bps)
            positions = np.where(
                np.abs(predicted_returns) > threshold,
                np.sign(predicted_returns),
                0.0,
            )
            previous = np.concatenate(([0.0], positions[:-1]))
            turnover = np.abs(positions - previous)
            one_way_cost = float(cost_bps) / 2.0
            net_bps = positions * cache["returns_bps"] - turnover * one_way_cost
            mean_net = float(np.mean(net_bps))
            volatility = float(np.std(net_bps, ddof=1)) if len(net_bps) > 1 else 0.0
            pair_net_means.append(mean_net)
            pair_total_returns.append(float(np.sum(net_bps) / 100.0))
            pair_sharpes.append(mean_net / volatility * math.sqrt(365.0) if volatility > 0.0 else 0.0)
            active_fractions.append(float(np.mean(positions != 0.0)))
        directional_rows.append(
            {
                "stress": "directional_roundtrip_cost_bps",
                "value": float(cost_bps),
                "equal_pair_mean_net_bps_per_day": float(np.mean(pair_net_means)),
                "equal_pair_mean_total_return_pct": float(np.mean(pair_total_returns)),
                "equal_pair_mean_annualized_sharpe": float(np.mean(pair_sharpes)),
                "mean_active_fraction": float(np.mean(active_fractions)),
                "diagnostic_only": True,
                "orders_authorized": False,
            }
        )

    first_time_shift_failure = next(
        (row for row in time_shift_rows if not row["survives_positive_effect"]), None
    )
    first_detuning_failure = next(
        (row for row in detuning_rows if not row["survives_positive_effect"]), None
    )
    return {
        "time_shift": time_shift_rows,
        "frequency_detuning": detuning_rows,
        "directional_cost": directional_rows,
        "breakpoints": {
            "first_time_shift_nonpositive": first_time_shift_failure,
            "first_detuning_nonpositive": first_detuning_failure,
            "base_effect_failed_before_stress": bool(
                time_shift_rows and not time_shift_rows[0]["survives_positive_effect"]
            ),
        },
    }


def fit_harmonic_predict_signed(
    train_day_index: np.ndarray,
    train_returns_bps: np.ndarray,
    predict_day_index: np.ndarray,
    periods: Iterable[float],
) -> np.ndarray:
    train_design = harmonic_design(train_day_index, periods)
    predict_design = harmonic_design(predict_day_index, periods)
    coefficients = np.linalg.lstsq(train_design, train_returns_bps, rcond=None)[0]
    return predict_design @ coefficients


def flatten_stress(stress: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lane in ("time_shift", "frequency_detuning", "directional_cost"):
        for row in stress.get(lane, []):
            compact = dict(row)
            if isinstance(compact.get("periods_days"), list):
                compact["periods_days"] = ",".join(str(value) for value in compact["periods_days"])
            rows.append(compact)
    return rows


def markdown_report(summary: dict[str, Any]) -> str:
    aggregate = summary.get("aggregate") or {}
    frequency_rows = summary.get("frequency_clusters") or []
    pair_rows = summary.get("pair_results") or []
    directional = ((summary.get("stress_ladder") or {}).get("directional_cost") or [])
    lines = [
        "# Frequency-Cluster Truth Gauntlet",
        "",
        f"Generated UTC: {summary.get('generated_utc')}",
        f"Decision: `{summary.get('decision')}`",
        f"Official-source input: `{str(summary.get('source_authentic')).lower()}`",
        f"Independently validated: `{str(summary.get('independently_validated')).lower()}`",
        f"Execution authorized: `{str(summary.get('execution_authorized')).lower()}`",
        "",
        "## Answer",
        "",
        f"The frequency-enabled candidate changed cohort-average MAE by "
        f"`{aggregate.get('aggregate_improvement_pct_vs_strongest_named_baseline', 0.0):.4f}%` "
        "against one globally strongest named baseline on the untouched holdout. "
        f"The pair-bootstrap 95% interval was "
        f"`[{(aggregate.get('aggregate_improvement_pct_pair_bootstrap_ci95') or [0, 0])[0]:.4f}%, "
        f"{(aggregate.get('aggregate_improvement_pct_pair_bootstrap_ci95') or [0, 0])[1]:.4f}%]`.",
        "",
        "That global comparison is diagnostic, not the promotion metric. The reviewer gate uses "
        "the strongest baseline separately for every pair. On that harder metric, the mean pair "
        f"improvement was `{aggregate.get('mean_pair_worst_baseline_improvement_pct', 0.0):.4f}%` "
        f"with 95% interval "
        f"`[{(aggregate.get('mean_pair_worst_baseline_improvement_pct_bootstrap_ci95') or [0, 0])[0]:.4f}%, "
        f"{(aggregate.get('mean_pair_worst_baseline_improvement_pct_bootstrap_ci95') or [0, 0])[1]:.4f}%]`.",
        "",
        f"Positive pair diagnostics: `{aggregate.get('positive_pair_count', 0)}/{aggregate.get('pair_count', 0)}`. "
        f"Individually promoted after block uncertainty and Holm correction: "
        f"`{len(aggregate.get('individually_promoted_pairs') or [])}`.",
        "",
        "## Promotion Gate",
        "",
    ]
    for name, passed in (aggregate.get("gate_checks") or {}).items():
        lines.append(f"- `{name}`: `{'PASS' if passed else 'FAIL'}`")
    lines.extend(
        [
        "",
        "## Frozen Frequency Clusters",
        "",
        "| Development rank | Period days | Median partial R2 | Top-3 pair fraction | Selected |",
        "|---:|---:|---:|---:|---|",
        ]
    )
    for row in frequency_rows:
        lines.append(
            f"| {row.get('development_rank')} | {row.get('period_days')} | "
            f"{row.get('median_partial_r2', 0.0):.6f} | "
            f"{row.get('top3_pair_fraction', 0.0):.3f} | "
            f"{str(row.get('selected')).lower()} |"
        )

    lines.extend(
        [
            "",
            "## Pair Gate",
            "",
            "| Pair | Variant | Improvement vs strongest baseline | CI95 effect | Raw phase p | Holm p | Promoted |",
            "|---|---|---:|---|---:|---:|---|",
        ]
    )
    for row in sorted(
        pair_rows,
        key=lambda item: float(item.get("worst_baseline_improvement_pct") or 0.0),
        reverse=True,
    ):
        interval = row.get("effect_block_bootstrap_ci95") or [0.0, 0.0]
        lines.append(
            f"| {row.get('pair')} | {row.get('selected_variant')} | "
            f"{row.get('worst_baseline_improvement_pct', 0.0):.4f}% | "
            f"[{interval[0]:.6f}, {interval[1]:.6f}] | "
            f"{row.get('phase_shift_p_raw', 1.0):.6f} | "
            f"{row.get('phase_shift_p_holm', 1.0):.6f} | "
            f"{str(row.get('individually_promoted')).lower()} |"
        )

    lines.extend(["", "## Directional Shadow Cost Ladder", ""])
    lines.append("| Roundtrip cost bps | Mean net bps/day | Mean total return pct | Mean Sharpe | Active fraction |")
    lines.append("|---:|---:|---:|---:|---:|")
    for row in directional:
        lines.append(
            f"| {row.get('value')} | {row.get('equal_pair_mean_net_bps_per_day', 0.0):.6f} | "
            f"{row.get('equal_pair_mean_total_return_pct', 0.0):.6f} | "
            f"{row.get('equal_pair_mean_annualized_sharpe', 0.0):.6f} | "
            f"{row.get('mean_active_fraction', 0.0):.4f} |"
        )
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            f"{EVIDENCE_BOUNDARY}",
            "",
            "The holdout was not used to select periods or candidate variants. Every pair, null, "
            "adverse result, confidence interval, corrected p-value, and first stress failure is retained.",
            "",
        ]
    )
    return "\n".join(lines)


def build_manifest(run_dir: Path, protocol_path: Path) -> dict[str, Any]:
    files = [path for path in run_dir.rglob("*") if path.is_file() and path.name != "manifest.sha256.json"]
    entries: list[dict[str, Any]] = []
    terminal = "0" * 64
    for path in sorted(files, key=lambda item: str(item.relative_to(run_dir)).lower()):
        relative = str(path.relative_to(run_dir)).replace("\\", "/")
        digest = sha256_file(path)
        size = path.stat().st_size
        terminal = hashlib.sha256(
            f"{terminal}\n{relative}\n{digest}\n{size}".encode("utf-8")
        ).hexdigest()
        entries.append({"path": relative, "sha256": digest, "bytes": size})
    manifest = {
        "schema": "frequency_cluster_truth_gauntlet_manifest_v1",
        "generated_utc": now_utc(),
        "run_dir": str(run_dir),
        "protocol_source": str(protocol_path),
        "protocol_source_sha256": sha256_file(protocol_path),
        "benchmark_source": str(Path(__file__).resolve()),
        "benchmark_source_sha256": sha256_file(Path(__file__).resolve()),
        "entry_count": len(entries),
        "entries": entries,
        "terminal_chain_sha256": terminal,
    }
    write_json(run_dir / "manifest.sha256.json", manifest)
    return manifest


def pair_csv_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in rows:
        interval = row["effect_block_bootstrap_ci95"]
        compact.append(
            {
                "pair": row["pair"],
                "discovery_samples": row["discovery_samples"],
                "calibration_samples": row["calibration_samples"],
                "holdout_samples": row["holdout_samples"],
                "selected_variant": row["selected_variant"],
                "candidate_mae": row["candidate_mae"],
                "strongest_baseline": row["strongest_baseline"],
                "strongest_baseline_mae": row["strongest_baseline_mae"],
                "worst_baseline_effect": row["worst_baseline_effect"],
                "worst_baseline_improvement_pct": row["worst_baseline_improvement_pct"],
                "effect_ci95_low": interval[0],
                "effect_ci95_high": interval[1],
                "phase_shift_p_raw": row["phase_shift_p_raw"],
                "phase_shift_p_holm": row["phase_shift_p_holm"],
                "individually_promoted": row["individually_promoted"],
                "holdout_selected_period_overlap": row["holdout_selected_period_overlap"],
                "source_file_sha256": row["source_file_sha256"],
            }
        )
    return compact


def run_gauntlet(args: argparse.Namespace) -> dict[str, Any]:
    protocol_path = Path(args.protocol).resolve()
    protocol = read_json(protocol_path)
    protocol_validation = validate_protocol(protocol)
    out_root = Path(args.out_root).resolve()
    run_dir = out_root / f"frequency_cluster_truth_gauntlet_{now_tag()}"
    input_dir = run_dir / "inputs"
    run_dir.mkdir(parents=True, exist_ok=False)

    if args.input_dir:
        source_dir = Path(args.input_dir).resolve()
        if not source_dir.exists():
            raise FileNotFoundError(source_dir)
        shutil.copytree(source_dir, input_dir)
        retrieval_receipt_path = input_dir / "retrieval_receipt.json"
        retrieval_receipt = (
            read_json(retrieval_receipt_path)
            if retrieval_receipt_path.exists()
            else {
                "schema": "offline_fixture_receipt_v1",
                "provider": "offline_fixture",
                "public_endpoints_only": False,
                "authentication_used": False,
            }
        )
    else:
        retrieval_receipt = fetch_kraken_inputs(
            protocol,
            input_dir,
            float(args.timeout_seconds),
            float(args.pause_seconds),
        )

    series_rows, rejected = load_inputs(input_dir, protocol)
    minimum_pairs = int(protocol["data"]["minimum_eligible_pairs"])
    run_identity = compute_run_identity(input_dir, protocol_path)
    source_authentic = (
        str(retrieval_receipt.get("provider")) == "Kraken"
        and retrieval_receipt.get("public_endpoints_only") is True
        and retrieval_receipt.get("authentication_used") is False
    )
    prior_scored_run = find_prior_scored_run(
        out_root,
        run_dir,
        str(run_identity["run_identity_sha256"]),
        protocol_path,
    )
    if prior_scored_run is not None:
        prior_summary = read_json(prior_scored_run / "summary.json")
        summary = {
            "schema": "frequency_cluster_truth_gauntlet_duplicate_guard_v1",
            "generated_utc": now_utc(),
            "decision": "DUPLICATE_SOURCE_SNAPSHOT_NOT_RESCORED",
            "run_identity_sha256": run_identity["run_identity_sha256"],
            "source_authentic": source_authentic,
            "independently_validated": False,
            "execution_authorized": False,
            "holdout_rescored": False,
            "primary_scored_run": str(prior_scored_run),
            "primary_decision": prior_summary.get("decision"),
            "primary_evidence_receipt_sha256": prior_summary.get(
                "evidence_receipt_sha256"
            ),
            "truth_boundary": (
                "Identical protocol and normalized input hashes were already scored. This run "
                "retains the retrieval receipt but does not rescore the holdout and is not an "
                "independent confirmation."
            ),
        }
        write_json(run_dir / "run_identity.json", run_identity)
        write_json(run_dir / "summary.json", summary)
        atomic_write_text(
            run_dir / "report.md",
            "# Duplicate Source Snapshot\n\n"
            f"Decision: `{summary['decision']}`\n\n"
            f"Primary scored run: `{prior_scored_run}`\n\n"
            f"Run identity: `{run_identity['run_identity_sha256']}`\n\n"
            "The holdout was not rescored. This retrieval is not independent confirmation.\n",
        )
        build_manifest(run_dir, protocol_path)
        audit_run_identities(out_root, protocol_path)
        print(
            "FREQUENCY_GAUNTLET "
            f"decision={summary['decision']} identity={run_identity['run_identity_sha256']} "
            f"primary={prior_scored_run}"
        )
        return summary

    if len(series_rows) < minimum_pairs:
        decision = str(protocol["decision_labels"]["insufficient"])
        summary = {
            "schema": "frequency_cluster_truth_gauntlet_summary_v1",
            "generated_utc": now_utc(),
            "decision": decision,
            "source_authentic": source_authentic,
            "independently_validated": False,
            "execution_authorized": False,
            "run_identity_sha256": run_identity["run_identity_sha256"],
            "eligible_pair_count": len(series_rows),
            "minimum_eligible_pairs": minimum_pairs,
            "rejected_pairs": rejected,
            "protocol_validation": protocol_validation,
            "evidence_boundary": EVIDENCE_BOUNDARY,
        }
        write_json(run_dir / "summary.json", summary)
        write_json(run_dir / "run_identity.json", run_identity)
        atomic_write_text(run_dir / "report.md", markdown_report(summary))
        manifest = build_manifest(run_dir, protocol_path)
        audit_run_identities(out_root, protocol_path)
        summary["manifest_terminal_chain_sha256"] = manifest["terminal_chain_sha256"]
        return summary

    selected_periods, frequency_rows = discover_frequency_clusters(series_rows, protocol)
    pair_rows: list[dict[str, Any]] = []
    caches: dict[str, dict[str, Any]] = {}
    seed = int(protocol["inference"]["bootstrap_seed"])
    for index, series in enumerate(series_rows):
        row, cache = evaluate_pair(series, selected_periods, protocol, seed + index)
        pair_rows.append(row)
        caches[series.pair] = cache
    aggregate = aggregate_pair_results(pair_rows, protocol)
    stress = build_stress_ladder(
        series_rows,
        pair_rows,
        caches,
        selected_periods,
        protocol,
    )
    decision = str(
        protocol["decision_labels"]["pass"]
        if aggregate["gate_pass"]
        else protocol["decision_labels"]["fail"]
    )
    summary = {
        "schema": "frequency_cluster_truth_gauntlet_summary_v1",
        "generated_utc": now_utc(),
        "decision": decision,
        "source_authentic": source_authentic,
        "source_authentic_meaning": "Retrieved directly from Kraken public endpoints and hash-sealed locally.",
        "independently_validated": False,
        "independent_validation_status": "NOT_RUN_EXTERNAL_REPRODUCTION_REQUIRED",
        "execution_authorized": False,
        "capital_at_risk_allowed": False,
        "run_identity_sha256": run_identity["run_identity_sha256"],
        "protocol_path": str(protocol_path),
        "protocol_sha256": sha256_file(protocol_path),
        "benchmark_source_sha256": sha256_file(Path(__file__).resolve()),
        "protocol_validation": protocol_validation,
        "eligible_pair_count": len(series_rows),
        "rejected_pairs": rejected,
        "selected_periods_days": selected_periods,
        "frequency_clusters": frequency_rows,
        "pair_results": pair_rows,
        "aggregate": aggregate,
        "stress_ladder": stress,
        "directional_shadow_lane": {
            "status": "DIAGNOSTIC_ONLY_NOT_PROMOTABLE",
            "orders_authorized": False,
            "live_execution_authorized": False,
        },
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "safest_next_action": (
            "Package the frozen protocol, source inputs, and verification script for one external "
            "reviewer; do not run economic action unless a future prospectively sealed result and "
            "independent reproduction both pass."
        ),
    }
    summary["evidence_receipt_sha256"] = sha256_payload(
        {
            "protocol_sha256": summary["protocol_sha256"],
            "benchmark_source_sha256": summary["benchmark_source_sha256"],
            "selected_periods_days": selected_periods,
            "decision": decision,
            "aggregate": aggregate,
            "pair_source_hashes": {
                row["pair"]: row["source_file_sha256"] for row in pair_rows
            },
        }
    )

    write_json(run_dir / "summary.json", summary)
    write_json(run_dir / "run_identity.json", run_identity)
    pair_compact = pair_csv_rows(pair_rows)
    write_csv(run_dir / "pair_results.csv", pair_compact, list(pair_compact[0].keys()))
    write_csv(
        run_dir / "frequency_clusters.csv",
        frequency_rows,
        list(frequency_rows[0].keys()),
    )
    stress_rows = flatten_stress(stress)
    stress_fields = sorted({key for row in stress_rows for key in row})
    write_csv(run_dir / "stress_ladder.csv", stress_rows, stress_fields)
    atomic_write_text(run_dir / "report.md", markdown_report(summary))
    manifest = build_manifest(run_dir, protocol_path)
    audit_run_identities(out_root, protocol_path)

    latest_dir = out_root / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "summary.json",
        "pair_results.csv",
        "frequency_clusters.csv",
        "stress_ladder.csv",
        "report.md",
        "manifest.sha256.json",
    ):
        shutil.copy2(run_dir / name, latest_dir / name)
    write_json(
        out_root / "latest.json",
        {
            "schema": "frequency_cluster_truth_gauntlet_latest_pointer_v1",
            "run_dir": str(run_dir),
            "decision": decision,
            "evidence_receipt_sha256": summary["evidence_receipt_sha256"],
            "manifest_terminal_chain_sha256": manifest["terminal_chain_sha256"],
        },
    )
    print(
        "FREQUENCY_GAUNTLET "
        f"decision={decision} pairs={len(pair_rows)} periods={selected_periods} "
        f"improvement_pct={aggregate['aggregate_improvement_pct_vs_strongest_named_baseline']:.6f} "
        f"promoted_pairs={len(aggregate['individually_promoted_pairs'])} "
        f"receipt={summary['evidence_receipt_sha256']}"
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the source-authentic frequency-cluster truth gauntlet."
    )
    parser.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    parser.add_argument("--out-root", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--input-dir",
        default="",
        help="Optional normalized input directory for offline reproduction. Network retrieval is used when omitted.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--pause-seconds", type=float, default=0.05)
    return parser.parse_args()


def main() -> int:
    run_gauntlet(parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
