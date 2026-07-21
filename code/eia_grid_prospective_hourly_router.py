"""Prospective EIA-930 hourly specialist router with pre-interval seals."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import warnings
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Iterator
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "config" / "eia_grid_prospective_hourly_router_protocol_v1.json"
OUT_DIR = ROOT / "out" / "eia_grid_prospective_hourly_router"
SOURCE_CACHE_PATH = OUT_DIR / "source_panel_cache.json"
DESIGN_RESULT_PATH = OUT_DIR / "design_benchmark.json"
PREDICTIONS_PATH = OUT_DIR / "sealed_predictions.jsonl"
SETTLEMENTS_PATH = OUT_DIR / "settlements.jsonl"
RUN_RECEIPTS_PATH = OUT_DIR / "operational_runs.jsonl"
STATUS_PATH = OUT_DIR / "prospective_status_latest.json"
LATEST_CYCLE_PATH = OUT_DIR / "latest_cycle.json"
LOCK_PATH = OUT_DIR / ".prospective_hourly_cycle.lock"
ZERO_HASH = "0" * 64


@lru_cache(maxsize=1)
def load_numpy_runtime() -> Any:
    """Load NumPy only when feature construction or model inference is needed."""
    import numpy as np

    return np


@lru_cache(maxsize=1)
def load_ml_runtime() -> tuple[Any, Any, Any, Any]:
    """Load the optional model stack only when a new forecast must be fit."""
    import lightgbm as lgb
    import xgboost as xgb
    from sklearn.linear_model import Ridge

    np = load_numpy_runtime()
    return lgb, np, xgb, Ridge


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


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
        return None
    return result.stdout.strip() or None


def load_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "eia_grid_prospective_hourly_router_protocol.v1":
        raise ValueError("unexpected hourly-router protocol schema")
    authorities = payload["balancing_authorities"]
    if sorted(authorities) != sorted(payload["authority_timezones"]):
        raise ValueError("authority timezone map is incomplete")
    if sorted(authorities) != sorted(payload["router"]["route_map"]):
        raise ValueError("authority route map is incomplete")
    candidate_ids = {row["id"] for row in payload["candidates"]}
    if any(value not in candidate_ids for value in payload["router"]["route_map"].values()):
        raise ValueError("route map references an undeclared candidate")
    if payload["router"].get("dynamic_override_allowed") is not False:
        raise ValueError("dynamic route overrides must remain disabled")
    if payload["prospective_window"].get("backfilled_predictions_allowed") is not False:
        raise ValueError("backfilled predictions must remain disabled")
    return payload


def read_eia_key() -> str:
    key = os.environ.get("EIA_API_KEY") or os.environ.get("EIA_API_KEY_PREMIUM")
    if not key:
        raise RuntimeError("EIA API key is not configured in the process environment")
    return key


@lru_cache(maxsize=100_000)
def period_end_utc(period: str) -> datetime:
    return datetime.strptime(period, "%Y-%m-%dT%H").replace(tzinfo=timezone.utc)


def period_string(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("period datetime must be timezone-aware")
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H")


@lru_cache(maxsize=1_000_000)
def shift_period(period: str, hours: int) -> str:
    return period_string(period_end_utc(period) + timedelta(hours=hours))


def target_interval_start_utc(period: str) -> datetime:
    return period_end_utc(period) - timedelta(hours=1)


def request_hourly_rows(
    protocol: dict[str, Any], start: str, end: str, timeout: int = 60
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    route = protocol["source"]["api_route"]
    key = read_eia_key()
    page_size = 5000
    offset = 0
    pages: list[dict[str, Any]] = []
    incoming: list[dict[str, Any]] = []
    total = None
    while total is None or offset < total:
        params: list[tuple[str, str]] = [
            ("api_key", key),
            ("frequency", "hourly"),
            ("data[0]", "value"),
            ("facets[type][]", protocol["source"]["actual_type"]),
            ("facets[type][]", protocol["source"]["official_forecast_type"]),
        ]
        params.extend(
            ("facets[respondent][]", respondent)
            for respondent in protocol["balancing_authorities"]
        )
        params.extend(
            [
                ("start", start),
                ("end", end),
                ("sort[0][column]", "period"),
                ("sort[0][direction]", "asc"),
                ("sort[1][column]", "respondent"),
                ("sort[1][direction]", "asc"),
                ("sort[2][column]", "type"),
                ("sort[2][direction]", "asc"),
                ("offset", str(offset)),
                ("length", str(page_size)),
            ]
        )
        request = urllib.request.Request(
            route + "?" + urllib.parse.urlencode(params),
            headers={"User-Agent": "LumenCore-Prospective-Hourly-Router/1.0"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                status = int(response.getcode())
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"EIA hourly request failed with HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"EIA hourly request failed: {type(exc).__name__}") from None
        payload = json.loads(raw.decode("utf-8"))
        response_payload = payload.get("response", {})
        page = response_payload.get("data", []) if isinstance(response_payload, dict) else []
        if total is None:
            total = int(response_payload.get("total", len(page)))
        pages.append(
            {
                "offset": offset,
                "http_status": status,
                "row_count": len(page),
                "response_body_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
        incoming.extend(row for row in page if isinstance(row, dict))
        if not page:
            break
        offset += len(page)

    allowed_authorities = set(protocol["balancing_authorities"])
    allowed_types = {
        protocol["source"]["actual_type"],
        protocol["source"]["official_forecast_type"],
    }
    by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in incoming:
        respondent = str(row.get("respondent"))
        kind = str(row.get("type"))
        period = str(row.get("period"))
        if respondent not in allowed_authorities or kind not in allowed_types:
            continue
        try:
            value = float(row.get("value"))
            period_end_utc(period)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value) or value <= 0.0:
            continue
        normalized = {
            "period": period,
            "respondent": respondent,
            "respondent_name": str(row.get("respondent-name") or respondent),
            "type": kind,
            "type_name": str(row.get("type-name") or kind),
            "value": value,
            "value_units": str(row.get("value-units") or protocol["source"]["native_unit"]),
        }
        identity = (respondent, period, kind)
        existing = by_key.get(identity)
        if existing and existing != normalized:
            raise ValueError(f"conflicting EIA row for {identity}")
        by_key[identity] = normalized
    rows = sorted(by_key.values(), key=lambda row: (row["period"], row["respondent"], row["type"]))
    return rows, {
        "schema": "eia_hourly_source_request_receipt.v1",
        "retrieved_utc": now_utc().isoformat(),
        "route": route,
        "frequency": "hourly",
        "start": start,
        "end": end,
        "respondents": list(protocol["balancing_authorities"]),
        "types": sorted(allowed_types),
        "page_count": len(pages),
        "response_total": int(total or 0),
        "accepted_row_count": len(rows),
        "pages": pages,
        "credential_serialized": False,
    }


def load_source_cache(path: Path = SOURCE_CACHE_PATH) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "eia_grid_hourly_source_cache.v1":
        raise ValueError("unexpected hourly source-cache schema")
    if payload.get("row_chain_sha256") != canonical_sha256(payload.get("rows", [])):
        raise ValueError("hourly source cache failed row-chain verification")
    return payload


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def refresh_source_panel(
    protocol: dict[str, Any], timeout: int = 60, dry_run: bool = False
) -> tuple[dict[str, Any], dict[str, Any]]:
    observed_at = now_utc()
    cache = load_source_cache()
    if cache:
        lookback = int(protocol["source"]["cache_refresh_lookback_hours"])
        start = period_string(observed_at - timedelta(hours=lookback))
        cached_rows = cache["rows"]
    else:
        start = protocol["source"]["history_start_utc"]
        cached_rows = []
    end = period_string(observed_at + timedelta(days=2))
    incoming, receipt = request_hourly_rows(protocol, start, end, timeout)
    by_key = {
        (row["respondent"], row["period"], row["type"]): row for row in cached_rows
    }
    revision_count = 0
    for row in incoming:
        identity = (row["respondent"], row["period"], row["type"])
        if identity in by_key and by_key[identity] != row:
            revision_count += 1
        by_key[identity] = row
    rows = sorted(by_key.values(), key=lambda row: (row["period"], row["respondent"], row["type"]))
    panel = {
        "schema": "eia_grid_hourly_source_cache.v1",
        "generated_utc": observed_at.isoformat(),
        "source_receipt_sha256": canonical_sha256(receipt),
        "refresh_start": start,
        "refresh_end": end,
        "revision_count": revision_count,
        "row_count": len(rows),
        "row_chain_sha256": canonical_sha256(rows),
        "rows": rows,
    }
    if not dry_run:
        write_json_atomic(SOURCE_CACHE_PATH, panel)
    return panel, receipt


def series_by_authority(
    panel: dict[str, Any], protocol: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    output = {
        respondent: {
            "actual": {},
            "official": {},
            "actual_index": {},
            "official_index": {},
            "name": respondent,
        }
        for respondent in protocol["balancing_authorities"]
    }
    for row in panel["rows"]:
        respondent = row["respondent"]
        if respondent not in output:
            continue
        output[respondent]["name"] = row.get("respondent_name") or respondent
        index = int(period_end_utc(row["period"]).timestamp() // 3600)
        if row["type"] == protocol["source"]["actual_type"]:
            output[respondent]["actual"][row["period"]] = float(row["value"])
            output[respondent]["actual_index"][index] = float(row["value"])
        elif row["type"] == protocol["source"]["official_forecast_type"]:
            output[respondent]["official"][row["period"]] = float(row["value"])
            output[respondent]["official_index"][index] = float(row["value"])
    return output


def target_scale(actual: dict[int, float], target: int) -> float:
    values = []
    for offset in range(24, 192):
        first = target - offset
        second = target - offset - 168
        if first in actual and second in actual:
            values.append(abs(actual[first] - actual[second]))
    positive = [value for value in values if value > 0.0 and math.isfinite(value)]
    return max(float(median(positive)), 1.0) if positive else 1.0


def build_feature_row(
    series: dict[str, dict[str, Any]],
    protocol: dict[str, Any],
    respondent: str,
    target: str,
    require_actual: bool,
) -> dict[str, Any]:
    bundle = series[respondent]
    actual: dict[str, float] = bundle["actual"]
    official: dict[str, float] = bundle["official"]
    actual_index: dict[int, float] = bundle["actual_index"]
    official_index: dict[int, float] = bundle["official_index"]
    if target not in official:
        raise ValueError("target official forecast is unavailable")
    if require_actual and target not in actual:
        raise ValueError("target actual is unavailable")
    if not require_actual and target in actual:
        raise ValueError("target actual is already present")

    target_index = int(period_end_utc(target).timestamp() // 3600)
    lag_offsets = [24, 48, 72, 168, 336]
    lag_indices = {offset: target_index - offset for offset in lag_offsets}
    if any(index not in actual_index for index in lag_indices.values()):
        raise ValueError("required actual lag is unavailable")
    if any(index not in official_index for index in lag_indices.values()):
        raise ValueError("required official-forecast lag is unavailable")

    recent_indices = [target_index - offset for offset in range(24, 48)]
    weekly_indices = [target_index - offset for offset in range(168, 336)]
    if any(index not in actual_index or index not in official_index for index in recent_indices):
        raise ValueError("recent residual window is incomplete")
    if any(index not in actual_index or index not in official_index for index in weekly_indices):
        raise ValueError("weekly residual window is incomplete")
    np = load_numpy_runtime()
    recent_residuals = np.asarray(
        [actual_index[index] - official_index[index] for index in recent_indices],
        dtype=float,
    )
    weekly_residuals = np.asarray(
        [actual_index[index] - official_index[index] for index in weekly_indices],
        dtype=float,
    )
    scale = target_scale(actual_index, target_index)
    target_official = official[target]
    p24 = actual_index[lag_indices[24]]
    p48 = actual_index[lag_indices[48]]
    p72 = actual_index[lag_indices[72]]
    p168 = actual_index[lag_indices[168]]
    p336 = actual_index[lag_indices[336]]
    end = period_end_utc(target)
    local_start = (end - timedelta(hours=1)).astimezone(
        ZoneInfo(protocol["authority_timezones"][respondent])
    )
    hour_angle = 2.0 * math.pi * local_start.hour / 24.0
    weekday_angle = 2.0 * math.pi * local_start.weekday() / 7.0
    year_angle = 2.0 * math.pi * (local_start.timetuple().tm_yday - 1) / 365.25
    features = [
        (target_official - p24) / scale,
        (target_official - p168) / scale,
        (p24 - p168) / scale,
        (p24 - p48) / scale,
        (p48 - p72) / scale,
        (p168 - p336) / scale,
        (actual_index[lag_indices[24]] - official_index[lag_indices[24]]) / scale,
        (actual_index[lag_indices[48]] - official_index[lag_indices[48]]) / scale,
        (actual_index[lag_indices[168]] - official_index[lag_indices[168]]) / scale,
        float(np.mean(recent_residuals)) / scale,
        float(np.std(recent_residuals)) / scale,
        float(np.mean(weekly_residuals)) / scale,
        float(np.std(weekly_residuals)) / scale,
        math.sin(hour_angle),
        math.cos(hour_angle),
        math.sin(weekday_angle),
        math.cos(weekday_angle),
        math.sin(year_angle),
        math.cos(year_angle),
    ]
    authority_order = sorted(protocol["balancing_authorities"])
    features.extend(1.0 if respondent == value else 0.0 for value in authority_order)
    if not all(math.isfinite(float(value)) for value in features):
        raise ValueError("nonfinite target feature")
    row = {
        "respondent": respondent,
        "respondent_name": bundle["name"],
        "target_period_end_utc": target,
        "target_interval_start_utc": target_interval_start_utc(target).isoformat(),
        "utc_day": target[:10],
        "official_mwh": target_official,
        "seasonal_24_mwh": p24,
        "seasonal_168_mwh": p168,
        "bias_corrected_official_mwh": max(
            0.0, target_official + float(np.mean(recent_residuals))
        ),
        "scale_mwh": scale,
        "features": features,
    }
    if require_actual:
        row["actual_mwh"] = actual[target]
        row["target_residual_scaled"] = (actual[target] - target_official) / scale
    return row


def build_training_rows(
    panel: dict[str, Any],
    protocol: dict[str, Any],
    start: str,
    end: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    series = series_by_authority(panel, protocol)
    rows: list[dict[str, Any]] = []
    skipped: dict[str, int] = {}
    for respondent in protocol["balancing_authorities"]:
        targets = sorted(
            period
            for period in series[respondent]["actual"]
            if start <= period <= end and period in series[respondent]["official"]
        )
        for target in targets:
            try:
                rows.append(
                    build_feature_row(series, protocol, respondent, target, require_actual=True)
                )
            except ValueError as exc:
                reason = str(exc)
                skipped[reason] = skipped.get(reason, 0) + 1
    rows.sort(key=lambda row: (row["target_period_end_utc"], row["respondent"]))
    return rows, {
        "row_count": len(rows),
        "row_chain_sha256": canonical_sha256(rows),
        "skipped": skipped,
    }


def fit_models(
    rows: list[dict[str, Any]], protocol: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, float]]:
    if not rows:
        raise ValueError("no complete hourly training rows")
    lgb, np, xgb, Ridge = load_ml_runtime()
    matrix = np.asarray([row["features"] for row in rows], dtype=float)
    target = np.asarray([row["target_residual_scaled"] for row in rows], dtype=float)
    contract = protocol["model_contract"]
    models: dict[str, Any] = {
        "ridge_residual": Ridge(alpha=float(contract["ridge"]["alpha"])),
        "xgboost_residual": xgb.XGBRegressor(**contract["xgboost"]),
        "lightgbm_residual": lgb.LGBMRegressor(**contract["lightgbm"]),
    }
    durations: dict[str, float] = {}
    for name, model in models.items():
        started = time.perf_counter()
        model.fit(matrix, target)
        durations[name] = round((time.perf_counter() - started) * 1000.0, 3)
    return models, durations


def candidate_predictions(
    rows: list[dict[str, Any]], models: dict[str, Any]
) -> list[dict[str, float]]:
    if not rows:
        return []
    _, np, _, _ = load_ml_runtime()
    matrix = np.asarray([row["features"] for row in rows], dtype=float)
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="X does not have valid feature names",
            category=UserWarning,
        )
        model_predictions = {
            name: np.asarray(model.predict(matrix), dtype=float)
            for name, model in models.items()
        }
    output: list[dict[str, float]] = []
    for index, row in enumerate(rows):
        values = {
            "eia_official": float(row["official_mwh"]),
            "seasonal_naive_24": float(row["seasonal_24_mwh"]),
            "seasonal_naive_168": float(row["seasonal_168_mwh"]),
            "bias_corrected_official": float(row["bias_corrected_official_mwh"]),
        }
        for name, predictions in model_predictions.items():
            values[name] = max(
                0.0,
                float(row["official_mwh"])
                + float(predictions[index]) * float(row["scale_mwh"]),
            )
        output.append(values)
    return output


def design_benchmark(
    protocol: dict[str, Any], timeout: int = 60, dry_run: bool = False
) -> dict[str, Any]:
    panel, source_receipt = refresh_source_panel(protocol, timeout=timeout, dry_run=dry_run)
    design = protocol["historical_design"]
    all_rows, diagnostics = build_training_rows(
        panel,
        protocol,
        design["training_start_period_end_utc"],
        design["validation_end_period_end_utc"],
    )
    training = [
        row
        for row in all_rows
        if row["target_period_end_utc"] <= design["training_end_period_end_utc"]
    ]
    validation = [
        row
        for row in all_rows
        if design["validation_start_period_end_utc"]
        <= row["target_period_end_utc"]
        <= design["validation_end_period_end_utc"]
    ]
    models, durations = fit_models(training, protocol)
    predictions = candidate_predictions(validation, models)
    candidate_ids = [row["id"] for row in protocol["candidates"]]
    authority_metrics: list[dict[str, Any]] = []
    route_map: dict[str, str] = {}
    for respondent in protocol["balancing_authorities"]:
        indices = [
            index for index, row in enumerate(validation) if row["respondent"] == respondent
        ]
        metrics: dict[str, Any] = {}
        for candidate in candidate_ids:
            absolute = [
                abs(float(validation[index]["actual_mwh"]) - predictions[index][candidate])
                for index in indices
            ]
            scaled = [
                value / float(validation[index]["scale_mwh"])
                for value, index in zip(absolute, indices)
            ]
            metrics[candidate] = {
                "mean_absolute_error_mwh": mean(absolute) if absolute else None,
                "mean_scaled_absolute_error": mean(scaled) if scaled else None,
            }
        winner = min(
            candidate_ids,
            key=lambda name: (
                float(metrics[name]["mean_scaled_absolute_error"]),
                name,
            ),
        )
        route_map[respondent] = winner
        authority_metrics.append(
            {
                "respondent": respondent,
                "validation_row_count": len(indices),
                "candidate_metrics": metrics,
                "selected_candidate": winner,
            }
        )
    result = {
        "schema": "eia_grid_hourly_router_design_benchmark.v1",
        "generated_utc": now_utc().isoformat(),
        "protocol_path": PROTOCOL_PATH.relative_to(ROOT).as_posix(),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "source_panel_row_count": panel["row_count"],
        "source_panel_row_chain_sha256": panel["row_chain_sha256"],
        "source_receipt_sha256": canonical_sha256(source_receipt),
        "training_row_count": len(training),
        "validation_row_count": len(validation),
        "feature_diagnostics": diagnostics,
        "fit_duration_ms": durations,
        "authority_metrics": authority_metrics,
        "selected_route_map": route_map,
        "route_map_matches_protocol": route_map == protocol["router"]["route_map"],
        "claim_boundary": protocol["historical_design"]["claim_rule"],
    }
    if not dry_run:
        write_json_atomic(DESIGN_RESULT_PATH, result)
    return result


def load_chain(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.exists():
        return [], ZERO_HASH
    records: list[dict[str, Any]] = []
    previous = ZERO_HASH
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            observed = record.get("record_sha256")
            unsigned = {key: value for key, value in record.items() if key != "record_sha256"}
            if record.get("prior_record_chain_sha256") != previous:
                raise ValueError(f"broken prior hash at {path.name}:{line_number}")
            if observed != canonical_sha256(unsigned):
                raise ValueError(f"record hash mismatch at {path.name}:{line_number}")
            records.append(record)
            previous = str(observed)
    return records, previous


def append_chain_record(path: Path, record: dict[str, Any], previous: str) -> dict[str, Any]:
    output = dict(record)
    output["prior_record_chain_sha256"] = previous
    output["record_sha256"] = canonical_sha256(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(output, sort_keys=True, separators=(",", ":")) + "\n")
    return output


def eligible_target_scan(
    series: dict[str, dict[str, Any]],
    protocol: dict[str, Any],
    sealed_at: datetime,
) -> tuple[list[tuple[str, str]], dict[str, int], dict[str, dict[str, Any]]]:
    first_allowed = protocol["prospective_window"]["first_allowed_period_end_utc"]
    selected: list[tuple[str, str]] = []
    skipped: dict[str, int] = {}
    authority_diagnostics = {
        authority: {
            "eligible_target_count": 0,
            "pending_target_count": 0,
            "eligible_target_already_sealed_count": 0,
            "feature_ready_count": 0,
            "sealed_record_count": 0,
            "feature_blockers": {},
            "skipped": {},
        }
        for authority in protocol["balancing_authorities"]
    }
    for respondent in protocol["balancing_authorities"]:
        actual = series[respondent]["actual"]
        for target in sorted(series[respondent]["official"]):
            if target < first_allowed:
                continue
            if target in actual:
                reason = "target_actual_already_present"
                skipped[reason] = skipped.get(reason, 0) + 1
                authority_skipped = authority_diagnostics[respondent]["skipped"]
                authority_skipped[reason] = authority_skipped.get(reason, 0) + 1
                continue
            if sealed_at >= target_interval_start_utc(target):
                reason = "target_interval_already_started"
                skipped[reason] = skipped.get(reason, 0) + 1
                authority_skipped = authority_diagnostics[respondent]["skipped"]
                authority_skipped[reason] = authority_skipped.get(reason, 0) + 1
                continue
            selected.append((respondent, target))
            authority_diagnostics[respondent]["eligible_target_count"] += 1
    return selected, skipped, authority_diagnostics


def eligible_targets(
    series: dict[str, dict[str, Any]],
    protocol: dict[str, Any],
    sealed_at: datetime,
) -> tuple[list[tuple[str, str]], dict[str, int]]:
    selected, skipped, _ = eligible_target_scan(series, protocol, sealed_at)
    return selected, skipped


def seal_from_panel(
    protocol: dict[str, Any],
    panel: dict[str, Any],
    source_receipt: dict[str, Any],
    sealed_at: datetime,
    dry_run: bool,
) -> dict[str, Any]:
    series = series_by_authority(panel, protocol)
    targets, skipped, authority_diagnostics = eligible_target_scan(
        series, protocol, sealed_at
    )
    existing, previous = load_chain(PREDICTIONS_PATH)
    existing_keys = {
        (row["respondent"], row["target_period_end_utc"]) for row in existing
    }
    pending: list[tuple[str, str]] = []
    for respondent, target in targets:
        if (respondent, target) in existing_keys:
            authority_diagnostics[respondent][
                "eligible_target_already_sealed_count"
            ] += 1
            continue
        authority_diagnostics[respondent]["pending_target_count"] += 1
        pending.append((respondent, target))
    forecast_rows: list[dict[str, Any]] = []
    for respondent, target in pending:
        try:
            forecast_rows.append(
                build_feature_row(series, protocol, respondent, target, require_actual=False)
            )
            authority_diagnostics[respondent]["feature_ready_count"] += 1
        except ValueError as exc:
            reason = str(exc)
            skipped[reason] = skipped.get(reason, 0) + 1
            authority_skipped = authority_diagnostics[respondent]["skipped"]
            authority_skipped[reason] = authority_skipped.get(reason, 0) + 1
            feature_blockers = authority_diagnostics[respondent]["feature_blockers"]
            feature_blockers[reason] = feature_blockers.get(reason, 0) + 1
    if forecast_rows:
        latest_training_end = max(
            period
            for respondent in protocol["balancing_authorities"]
            for period in series[respondent]["actual"]
            if period_end_utc(period) <= sealed_at
        )
        training_rows, training_diagnostics = build_training_rows(
            panel,
            protocol,
            protocol["historical_design"]["training_start_period_end_utc"],
            latest_training_end,
        )
        models, fit_durations = fit_models(training_rows, protocol)
        predictions = candidate_predictions(forecast_rows, models)
    else:
        training_rows = []
        training_diagnostics = {"row_count": 0, "row_chain_sha256": canonical_sha256([])}
        fit_durations = {}
        predictions = []

    sealed_records: list[dict[str, Any]] = []
    protocol_hash = file_sha256(PROTOCOL_PATH)
    commit = protocol_commit()
    source_receipt_hash = canonical_sha256(source_receipt)
    for row, candidate_values in zip(forecast_rows, predictions):
        respondent = row["respondent"]
        target = row["target_period_end_utc"]
        selected = protocol["router"]["route_map"][respondent]
        record = {
            "schema": "eia_grid_prospective_hourly_router_prediction.v1",
            "respondent": respondent,
            "respondent_name": row["respondent_name"],
            "target_period_end_utc": target,
            "target_interval_start_utc": row["target_interval_start_utc"],
            "sealed_utc": sealed_at.isoformat(),
            "seal_lead_seconds": (
                target_interval_start_utc(target) - sealed_at
            ).total_seconds(),
            "source_receipt_sha256": source_receipt_hash,
            "source_panel_row_chain_sha256": panel["row_chain_sha256"],
            "protocol_sha256": protocol_hash,
            "protocol_commit": commit,
            "candidate_predictions_mwh": candidate_values,
            "selected_candidate": selected,
            "router_prediction_mwh": candidate_values[selected],
            "route_reason_code": protocol["router"]["route_reason_code"],
            "official_forecast_mwh": row["official_mwh"],
            "scale_mwh": row["scale_mwh"],
            "feature_count": len(row["features"]),
            "feature_sha256": canonical_sha256(row["features"]),
            "training_row_count": len(training_rows),
            "training_rows_sha256": training_diagnostics["row_chain_sha256"],
            "fit_duration_ms": fit_durations,
            "target_actual_present_at_seal": False,
            "backfilled": False,
            "claim_boundary": protocol["claim_boundary"],
        }
        if dry_run:
            preview = dict(record)
            preview["prior_record_chain_sha256"] = previous
            preview["record_sha256"] = canonical_sha256(preview)
            sealed = preview
        else:
            sealed = append_chain_record(PREDICTIONS_PATH, record, previous)
        previous = sealed["record_sha256"]
        sealed_records.append(sealed)
        authority_diagnostics[respondent]["sealed_record_count"] += 1
    return {
        "schema": "eia_grid_prospective_hourly_router_seal_run.v1",
        "run_utc": sealed_at.isoformat(),
        "dry_run": dry_run,
        "eligible_target_count": len(targets),
        "pending_target_count": len(pending),
        "sealed_record_count": len(sealed_records),
        "sealed_records": sealed_records,
        "skipped": skipped,
        "authority_diagnostics": authority_diagnostics,
        "existing_prediction_count": len(existing),
    }


def settle_from_panel(
    protocol: dict[str, Any],
    panel: dict[str, Any],
    source_receipt: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    predictions, _ = load_chain(PREDICTIONS_PATH)
    existing, previous = load_chain(SETTLEMENTS_PATH)
    existing_keys = {
        (row["respondent"], row["target_period_end_utc"], row["prediction_record_sha256"])
        for row in existing
    }
    series = series_by_authority(panel, protocol)
    output: list[dict[str, Any]] = []
    receipt_hash = canonical_sha256(source_receipt)
    for prediction in predictions:
        key = (
            prediction["respondent"],
            prediction["target_period_end_utc"],
            prediction["record_sha256"],
        )
        if key in existing_keys:
            continue
        actual = series[prediction["respondent"]]["actual"].get(
            prediction["target_period_end_utc"]
        )
        if actual is None:
            continue
        scale = float(prediction["scale_mwh"])
        candidate_metrics = {}
        for candidate, value in prediction["candidate_predictions_mwh"].items():
            absolute_error = abs(float(actual) - float(value))
            candidate_metrics[candidate] = {
                "absolute_error_mwh": absolute_error,
                "scaled_absolute_error": absolute_error / scale,
            }
        selected = prediction["selected_candidate"]
        oracle = min(
            candidate_metrics,
            key=lambda name: (
                candidate_metrics[name]["scaled_absolute_error"],
                name,
            ),
        )
        record = {
            "schema": "eia_grid_prospective_hourly_router_settlement.v1",
            "settled_utc": now_utc().isoformat(),
            "respondent": prediction["respondent"],
            "target_period_end_utc": prediction["target_period_end_utc"],
            "prediction_record_sha256": prediction["record_sha256"],
            "actual_mwh": float(actual),
            "source_receipt_sha256": receipt_hash,
            "candidate_metrics": candidate_metrics,
            "selected_candidate": selected,
            "router_scaled_absolute_error": candidate_metrics[selected][
                "scaled_absolute_error"
            ],
            "oracle_candidate": oracle,
            "oracle_scaled_absolute_error": candidate_metrics[oracle][
                "scaled_absolute_error"
            ],
            "router_regret_to_oracle": candidate_metrics[selected][
                "scaled_absolute_error"
            ]
            - candidate_metrics[oracle]["scaled_absolute_error"],
            "route_hit": selected == oracle,
            "claim_boundary": protocol["claim_boundary"],
        }
        if dry_run:
            preview = dict(record)
            preview["prior_record_chain_sha256"] = previous
            preview["record_sha256"] = canonical_sha256(preview)
            settled = preview
        else:
            settled = append_chain_record(SETTLEMENTS_PATH, record, previous)
        previous = settled["record_sha256"]
        output.append(settled)
    return {
        "schema": "eia_grid_prospective_hourly_router_settlement_run.v1",
        "run_utc": now_utc().isoformat(),
        "dry_run": dry_run,
        "sealed_prediction_count": len(predictions),
        "prior_settlement_count": len(existing),
        "settled_record_count": len(output),
        "settlements": output,
    }


def build_status(
    protocol: dict[str, Any],
    predictions: list[dict[str, Any]],
    settlements: list[dict[str, Any]],
    source_readiness_by_authority: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    authorities = protocol["balancing_authorities"]
    prediction_periods = {
        authority: {
            row["target_period_end_utc"]
            for row in predictions
            if row["respondent"] == authority
        }
        for authority in authorities
    }
    settled_periods = {
        authority: {
            row["target_period_end_utc"]
            for row in settlements
            if row["respondent"] == authority
        }
        for authority in authorities
    }
    common = sorted(set.intersection(*(settled_periods[a] for a in authorities)))
    settled_authority_count_by_period = {
        period: sum(period in settled_periods[authority] for authority in authorities)
        for period in sorted(set().union(*(settled_periods[a] for a in authorities)))
    }
    authority_coverage = {
        authority: {
            "prediction_count": len(prediction_periods[authority]),
            "settlement_count": len(settled_periods[authority]),
            "unsettled_prediction_count": len(
                prediction_periods[authority] - settled_periods[authority]
            ),
            "first_prediction_period": (
                min(prediction_periods[authority])
                if prediction_periods[authority]
                else None
            ),
            "latest_prediction_period": (
                max(prediction_periods[authority])
                if prediction_periods[authority]
                else None
            ),
            "first_settled_period": (
                min(settled_periods[authority]) if settled_periods[authority] else None
            ),
            "latest_settled_period": (
                max(settled_periods[authority]) if settled_periods[authority] else None
            ),
        }
        for authority in authorities
    }
    authorities_with_predictions = [
        authority for authority in authorities if prediction_periods[authority]
    ]
    authorities_with_settlements = [
        authority for authority in authorities if settled_periods[authority]
    ]
    candidates = [row["id"] for row in protocol["candidates"]]
    candidate_scores = {
        candidate: [
            float(row["candidate_metrics"][candidate]["scaled_absolute_error"])
            for row in settlements
        ]
        for candidate in candidates
    }
    candidate_means = {
        candidate: mean(values) if values else None
        for candidate, values in candidate_scores.items()
    }
    available = {key: value for key, value in candidate_means.items() if value is not None}
    best_fixed = min(available, key=lambda key: (available[key], key)) if available else None
    router_scores = [float(row["router_scaled_absolute_error"]) for row in settlements]
    windows = protocol["prospective_window"]
    common_count = len(common)
    return {
        "schema": "eia_grid_prospective_hourly_router_status.v1",
        "generated_utc": now_utc().isoformat(),
        "state": (
            "WAITING_FOR_FIRST_ELIGIBLE_HOUR"
            if not predictions
            else "SEALED_AWAITING_ACTUALS"
            if not settlements
            else "PROSPECTIVE_COLLECTION_ACTIVE"
        ),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "protocol_commit": protocol_commit(),
        "prediction_count": len(predictions),
        "settlement_count": len(settlements),
        "common_settled_hour_count": common_count,
        "first_common_settled_period": common[0] if common else None,
        "latest_common_settled_period": common[-1] if common else None,
        "authority_coverage": {
            "required_authority_count": len(authorities),
            "authorities_with_predictions": authorities_with_predictions,
            "authorities_without_predictions": [
                authority
                for authority in authorities
                if authority not in authorities_with_predictions
            ],
            "authorities_with_settlements": authorities_with_settlements,
            "authorities_without_settlements": [
                authority
                for authority in authorities
                if authority not in authorities_with_settlements
            ],
            "max_authorities_settled_on_same_period": max(
                settled_authority_count_by_period.values(), default=0
            ),
            "by_authority": authority_coverage,
        },
        "latest_seal_source_readiness_by_authority": (
            source_readiness_by_authority or {}
        ),
        "router_mean_scaled_absolute_error": mean(router_scores) if router_scores else None,
        "fixed_candidate_mean_scaled_absolute_error": candidate_means,
        "current_best_fixed_candidate": best_fixed,
        "router_skill_vs_current_best_fixed": (
            available[best_fixed] - mean(router_scores)
            if best_fixed and router_scores
            else None
        ),
        "sample_gates": {
            "preliminary_ready": common_count
            >= int(windows["preliminary_gate_common_hours_per_authority"]),
            "confirmatory_ready": common_count
            >= int(windows["confirmatory_gate_common_hours_per_authority"]),
            "durability_ready": common_count
            >= int(windows["durability_gate_common_hours_per_authority"]),
            "note": "Sample readiness does not mean a scientific promotion gate passed.",
        },
        "promotion_evaluation_complete": False,
        "claim_boundary": protocol["claim_boundary"],
    }


@contextmanager
def cycle_lock(path: Path = LOCK_PATH) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"prospective hourly cycle already locked: {path}") from exc
    try:
        os.write(
            descriptor,
            json.dumps({"pid": os.getpid(), "created_utc": now_utc().isoformat()}).encode(
                "utf-8"
            ),
        )
        os.close(descriptor)
        descriptor = -1
        yield
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        path.unlink(missing_ok=True)


def run_cycle(timeout: int = 60, dry_run: bool = False) -> dict[str, Any]:
    with cycle_lock():
        protocol = load_protocol()
        panel, receipt = refresh_source_panel(protocol, timeout=timeout, dry_run=dry_run)
        seal = seal_from_panel(protocol, panel, receipt, now_utc(), dry_run)
        settle = settle_from_panel(protocol, panel, receipt, dry_run)
        predictions, prediction_terminal = load_chain(PREDICTIONS_PATH)
        settlements, settlement_terminal = load_chain(SETTLEMENTS_PATH)
        prediction_hashes = {row["record_sha256"] for row in predictions}
        if any(
            row["prediction_record_sha256"] not in prediction_hashes for row in settlements
        ):
            raise ValueError("settlement references a prediction outside the verified chain")
        status = build_status(
            protocol,
            predictions,
            settlements,
            seal["authority_diagnostics"],
        )
        receipt_payload = {
            "schema": "eia_grid_prospective_hourly_router_operational_run.v1",
            "run_utc": now_utc().isoformat(),
            "dry_run": dry_run,
            "protocol_sha256": status["protocol_sha256"],
            "protocol_commit": status["protocol_commit"],
            "source_panel_row_count": panel["row_count"],
            "source_panel_row_chain_sha256": panel["row_chain_sha256"],
            "source_receipt_sha256": canonical_sha256(receipt),
            "sealed_record_count": seal["sealed_record_count"],
            "settled_record_count": settle["settled_record_count"],
            "prediction_count": len(predictions),
            "prediction_terminal_sha256": prediction_terminal,
            "settlement_count": len(settlements),
            "settlement_terminal_sha256": settlement_terminal,
            "status_sha256": canonical_sha256(status),
            "claim_boundary": protocol["claim_boundary"],
        }
        operational = None
        if not dry_run:
            _, previous = load_chain(RUN_RECEIPTS_PATH)
            operational = append_chain_record(RUN_RECEIPTS_PATH, receipt_payload, previous)
            status["operational_receipt_sha256"] = operational["record_sha256"]
            write_json_atomic(STATUS_PATH, status)
        result = {
            "schema": "eia_grid_prospective_hourly_router_cycle.v1",
            "dry_run": dry_run,
            "seal": seal,
            "settle": settle,
            "status": status,
            "operational_receipt": operational,
        }
        if not dry_run:
            write_json_atomic(LATEST_CYCLE_PATH, result)
        return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--design-benchmark", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    protocol = load_protocol()
    if args.design_benchmark:
        result = design_benchmark(protocol, timeout=args.timeout, dry_run=args.dry_run)
    else:
        result = run_cycle(timeout=args.timeout, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
