"""Prospective all-authority EIA-930 direct-demand router with atomic panels."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
import warnings
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterator
from zoneinfo import ZoneInfo

import lightgbm as lgb
import numpy as np
import xgboost as xgb
from sklearn.linear_model import Ridge


ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = Path(__file__).resolve().parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import eia_grid_prospective_hourly_router as shared  # noqa: E402


PROTOCOL_PATH = ROOT / "config" / "eia_grid_all_authority_direct_hourly_protocol_v2.json"
V1_PROTOCOL_PATH = ROOT / "config" / "eia_grid_prospective_hourly_router_protocol_v1.json"
V1_CODE_PATH = ROOT / "code" / "eia_grid_prospective_hourly_router.py"
V1_SOURCE_CACHE_PATH = ROOT / "out" / "eia_grid_prospective_hourly_router" / "source_panel_cache.json"
OUT_DIR = ROOT / "out" / "eia_grid_all_authority_direct_hourly_router"
SOURCE_CACHE_PATH = OUT_DIR / "source_panel_cache.json"
DESIGN_RESULT_PATH = OUT_DIR / "design_benchmark.json"
DESIGN_EVIDENCE_PATH = (
    ROOT
    / "evidence"
    / "external_validation"
    / "eia_grid_all_authority_direct_hourly_design_benchmark_20260716.json"
)
PREDICTIONS_PATH = OUT_DIR / "sealed_prediction_panels.jsonl"
SETTLEMENTS_PATH = OUT_DIR / "settlement_panels.jsonl"
RUN_RECEIPTS_PATH = OUT_DIR / "operational_runs.jsonl"
STATUS_PATH = OUT_DIR / "prospective_status_latest.json"
LATEST_CYCLE_PATH = OUT_DIR / "latest_cycle.json"
LOCK_PATH = OUT_DIR / ".all_authority_direct_hourly_cycle.lock"
ZERO_HASH = "0" * 64


now_utc = shared.now_utc
canonical_sha256 = shared.canonical_sha256
file_sha256 = shared.file_sha256
period_end_utc = shared.period_end_utc
period_string = shared.period_string
shift_period = shared.shift_period
target_interval_start_utc = shared.target_interval_start_utc
write_json_atomic = shared.write_json_atomic
append_chain_record = shared.append_chain_record
load_chain = shared.load_chain


def git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def protocol_commit() -> str | None:
    return shared.protocol_commit(PROTOCOL_PATH)


def git_path_is_clean(path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    try:
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative],
            cwd=ROOT,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if tracked.returncode != 0:
        return False
    for args in (["git", "diff", "--quiet", "--", relative], ["git", "diff", "--cached", "--quiet", "--", relative]):
        try:
            result = subprocess.run(args, cwd=ROOT, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return False
        if result.returncode != 0:
            return False
    return True


def load_protocol(
    path: Path = PROTOCOL_PATH, *, allow_design_pending: bool = False
) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "eia_grid_all_authority_direct_hourly_protocol.v2":
        raise ValueError("unexpected all-authority protocol schema")
    authorities = payload["balancing_authorities"]
    if len(authorities) != 8 or len(set(authorities)) != 8:
        raise ValueError("protocol must declare exactly eight unique authorities")
    if sorted(authorities) != sorted(payload["authority_timezones"]):
        raise ValueError("authority timezone map is incomplete")
    if payload["feature_contract"].get("target_official_forecast_may_be_used") is not False:
        raise ValueError("target official forecast must remain excluded")
    if payload["feature_contract"].get("target_actual_may_be_used") is not False:
        raise ValueError("target actual must remain excluded from forecast features")
    if payload["prediction_seal"].get("require_one_common_target_for_all_authorities") is not True:
        raise ValueError("one common target is required")
    if payload["prediction_seal"].get("require_atomic_all_authority_panel_record") is not True:
        raise ValueError("atomic all-authority panel records are required")
    if payload["prospective_window"].get("backfilled_predictions_allowed") is not False:
        raise ValueError("backfilled predictions must remain disabled")
    if payload["router"].get("dynamic_override_allowed") is not False:
        raise ValueError("dynamic route overrides must remain disabled")
    if payload["model_contract"].get("prospective_weight_update_allowed") is not False:
        raise ValueError("prospective model-weight updates must remain disabled")
    candidate_ids = {row["id"] for row in payload["candidates"]}
    routes = payload["router"].get("route_map", {})
    if allow_design_pending and payload.get("status") == "design_pending_historical_route_freeze":
        if routes:
            raise ValueError("design-pending protocol must not contain a partial route map")
        return payload
    if payload.get("status") != "design_frozen_before_prospective_collection":
        raise ValueError("protocol is not frozen for prospective collection")
    if sorted(routes) != sorted(authorities):
        raise ValueError("authority route map is incomplete")
    if any(candidate not in candidate_ids for candidate in routes.values()):
        raise ValueError("route map references an undeclared candidate")
    design = payload["historical_design"]
    if not design.get("result_sha256"):
        raise ValueError("historical design result is not bound")
    design_path = ROOT / design["result_path"]
    if not design_path.exists() or file_sha256(design_path) != design["result_sha256"]:
        raise ValueError("historical design result hash does not match")
    design_result = json.loads(design_path.read_text(encoding="utf-8"))
    if design_result.get("selected_route_map") != routes:
        raise ValueError("frozen route map does not match the historical design result")
    if not payload["prospective_window"].get("first_allowed_period_end_utc"):
        raise ValueError("first prospective target is not frozen")
    return payload


def load_source_cache(path: Path = SOURCE_CACHE_PATH) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    allowed = {"eia_grid_all_authority_source_cache.v2", "eia_grid_hourly_source_cache.v1"}
    if payload.get("schema") not in allowed:
        raise ValueError("unexpected EIA source-cache schema")
    if payload.get("row_chain_sha256") != canonical_sha256(payload.get("rows", [])):
        raise ValueError("EIA source cache failed row-chain verification")
    return payload


def refresh_source_panel(
    protocol: dict[str, Any],
    *,
    timeout: int = 60,
    dry_run: bool = False,
    observed_at: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    observed = (observed_at or now_utc()).astimezone(timezone.utc)
    cache = load_source_cache()
    seeded_from_v1 = False
    if cache is None and V1_SOURCE_CACHE_PATH.exists():
        cache = load_source_cache(V1_SOURCE_CACHE_PATH)
        seeded_from_v1 = cache is not None
    if cache:
        lookback = int(protocol["source"]["cache_refresh_lookback_hours"])
        start = period_string(observed - timedelta(hours=lookback))
        cached_rows = cache["rows"]
    else:
        start = protocol["source"]["history_start_utc"]
        cached_rows = []
    end = period_string(observed + timedelta(days=2))
    incoming, receipt = shared.request_hourly_rows(protocol, start, end, timeout)
    by_key = {
        (row["respondent"], row["period"], row["type"]): row for row in cached_rows
    }
    revision_count = 0
    for row in incoming:
        identity = (row["respondent"], row["period"], row["type"])
        if identity in by_key and by_key[identity] != row:
            revision_count += 1
        by_key[identity] = row
    rows = sorted(
        by_key.values(), key=lambda row: (row["period"], row["respondent"], row["type"])
    )
    panel = {
        "schema": "eia_grid_all_authority_source_cache.v2",
        "generated_utc": observed.isoformat(),
        "source_receipt_sha256": canonical_sha256(receipt),
        "seeded_from_v1_cache": seeded_from_v1,
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
        authority: {
            "actual": {},
            "actual_index": {},
            "official": {},
            "name": authority,
        }
        for authority in protocol["balancing_authorities"]
    }
    for row in panel["rows"]:
        authority = row["respondent"]
        if authority not in output:
            continue
        output[authority]["name"] = row.get("respondent_name") or authority
        index = int(period_end_utc(row["period"]).timestamp() // 3600)
        if row["type"] == protocol["source"]["actual_type"]:
            output[authority]["actual"][row["period"]] = float(row["value"])
            output[authority]["actual_index"][index] = float(row["value"])
        elif row["type"] == protocol["source"]["official_forecast_type"]:
            output[authority]["official"][row["period"]] = float(row["value"])
    return output


def _inclusive_offsets(bounds: list[int]) -> range:
    if len(bounds) != 2 or int(bounds[0]) > int(bounds[1]):
        raise ValueError("invalid feature-window offsets")
    return range(int(bounds[0]), int(bounds[1]) + 1)


def lag_only_level_scale(actual: dict[int, float], target_index: int, protocol: dict[str, Any]) -> float:
    offsets = _inclusive_offsets(protocol["feature_contract"]["level_scale_window_offsets"])
    values = [actual[target_index - offset] for offset in offsets if target_index - offset in actual]
    if len(values) != len(offsets):
        raise ValueError("level-scale history is incomplete")
    positive = [value for value in values if value > 0.0 and math.isfinite(value)]
    if len(positive) != len(values):
        raise ValueError("level-scale history contains invalid demand")
    return max(float(median(positive)), 1.0)


def lag_only_error_scale(actual: dict[int, float], target_index: int, protocol: dict[str, Any]) -> float:
    offsets = _inclusive_offsets(protocol["feature_contract"]["error_scale_window_offsets"])
    values = []
    for offset in offsets:
        current = target_index - offset
        prior = current - 1
        if current not in actual or prior not in actual:
            raise ValueError("error-scale history is incomplete")
        values.append(abs(actual[current] - actual[prior]))
    positive = [value for value in values if value > 0.0 and math.isfinite(value)]
    return max(float(median(positive)), 1.0) if positive else 1.0


def build_feature_row(
    series: dict[str, dict[str, Any]],
    protocol: dict[str, Any],
    authority: str,
    target: str,
    *,
    require_actual: bool,
) -> dict[str, Any]:
    bundle = series[authority]
    actual: dict[str, float] = bundle["actual"]
    actual_index: dict[int, float] = bundle["actual_index"]
    if require_actual and target not in actual:
        raise ValueError("target actual is unavailable")
    if not require_actual and target in actual:
        raise ValueError("target actual is already present")

    target_index = int(period_end_utc(target).timestamp() // 3600)
    lag_offsets = [int(value) for value in protocol["feature_contract"]["actual_lag_hours"]]
    lag_indices = {offset: target_index - offset for offset in lag_offsets}
    if any(index not in actual_index for index in lag_indices.values()):
        raise ValueError("required actual lag is unavailable")

    recent_offsets = _inclusive_offsets(
        protocol["feature_contract"]["recent_actual_window_offsets"]
    )
    weekly_offsets = _inclusive_offsets(
        protocol["feature_contract"]["weekly_actual_window_offsets"]
    )
    recent = [actual_index[target_index - offset] for offset in recent_offsets if target_index - offset in actual_index]
    weekly = [actual_index[target_index - offset] for offset in weekly_offsets if target_index - offset in actual_index]
    if len(recent) != len(recent_offsets):
        raise ValueError("recent actual window is incomplete")
    if len(weekly) != len(weekly_offsets):
        raise ValueError("weekly actual window is incomplete")

    level = lag_only_level_scale(actual_index, target_index, protocol)
    error = lag_only_error_scale(actual_index, target_index, protocol)
    p24 = actual_index[lag_indices[24]]
    p48 = actual_index[lag_indices[48]]
    p72 = actual_index[lag_indices[72]]
    p168 = actual_index[lag_indices[168]]
    p336 = actual_index[lag_indices[336]]
    end = period_end_utc(target)
    local_start = (end - timedelta(hours=1)).astimezone(
        ZoneInfo(protocol["authority_timezones"][authority])
    )
    hour_angle = 2.0 * math.pi * local_start.hour / 24.0
    weekday_angle = 2.0 * math.pi * local_start.weekday() / 7.0
    year_angle = 2.0 * math.pi * (local_start.timetuple().tm_yday - 1) / 365.25
    features = [
        p24 / level,
        p48 / level,
        p72 / level,
        p168 / level,
        p336 / level,
        (p24 - p48) / error,
        (p24 - p168) / error,
        (p48 - p72) / error,
        (p168 - p336) / error,
        float(np.mean(recent)) / level,
        float(np.std(recent)) / error,
        float(np.min(recent)) / level,
        float(np.max(recent)) / level,
        float(np.mean(weekly)) / level,
        float(np.std(weekly)) / error,
        float(np.min(weekly)) / level,
        float(np.max(weekly)) / level,
        math.sin(hour_angle),
        math.cos(hour_angle),
        math.sin(weekday_angle),
        math.cos(weekday_angle),
        math.sin(year_angle),
        math.cos(year_angle),
    ]
    authority_order = sorted(protocol["balancing_authorities"])
    features.extend(1.0 if authority == value else 0.0 for value in authority_order)
    if not all(math.isfinite(float(value)) for value in features):
        raise ValueError("nonfinite target feature")
    row = {
        "respondent": authority,
        "respondent_name": bundle["name"],
        "target_period_end_utc": target,
        "target_interval_start_utc": target_interval_start_utc(target).isoformat(),
        "utc_day": target[:10],
        "seasonal_24_mwh": p24,
        "seasonal_168_mwh": p168,
        "seasonal_blend_24_168_mwh": (p24 + p168) / 2.0,
        "level_scale_mwh": level,
        "error_scale_mwh": error,
        "features": features,
    }
    if require_actual:
        row["actual_mwh"] = actual[target]
        row["target_level_scaled"] = actual[target] / level
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
    for authority in protocol["balancing_authorities"]:
        targets = sorted(period for period in series[authority]["actual"] if start <= period <= end)
        for target in targets:
            try:
                rows.append(
                    build_feature_row(
                        series, protocol, authority, target, require_actual=True
                    )
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
        raise ValueError("no complete direct-demand training rows")
    matrix = np.asarray([row["features"] for row in rows], dtype=float)
    target = np.asarray([row["target_level_scaled"] for row in rows], dtype=float)
    contract = protocol["model_contract"]
    models: dict[str, Any] = {
        "ridge_direct": Ridge(alpha=float(contract["ridge"]["alpha"])),
        "xgboost_direct": xgb.XGBRegressor(**contract["xgboost"]),
        "lightgbm_direct": lgb.LGBMRegressor(**contract["lightgbm"]),
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
            "seasonal_naive_24": float(row["seasonal_24_mwh"]),
            "seasonal_naive_168": float(row["seasonal_168_mwh"]),
            "seasonal_blend_24_168": float(row["seasonal_blend_24_168_mwh"]),
        }
        for name, predictions in model_predictions.items():
            values[name] = max(
                0.0,
                float(predictions[index]) * float(row["level_scale_mwh"]),
            )
        output.append(values)
    return output


def design_benchmark(
    protocol: dict[str, Any], *, timeout: int = 60, dry_run: bool = False
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
        row for row in all_rows if row["target_period_end_utc"] <= design["training_end_period_end_utc"]
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
    route_map: dict[str, str] = {}
    authority_metrics: list[dict[str, Any]] = []
    for authority in protocol["balancing_authorities"]:
        indices = [index for index, row in enumerate(validation) if row["respondent"] == authority]
        if not indices:
            raise ValueError(f"no validation rows for {authority}")
        metrics: dict[str, Any] = {}
        for candidate in candidate_ids:
            absolute = [
                abs(float(validation[index]["actual_mwh"]) - predictions[index][candidate])
                for index in indices
            ]
            scaled = [
                value / float(validation[index]["error_scale_mwh"])
                for value, index in zip(absolute, indices)
            ]
            metrics[candidate] = {
                "mean_absolute_error_mwh": mean(absolute),
                "mean_scaled_absolute_error": mean(scaled),
            }
        winner = min(
            candidate_ids,
            key=lambda name: (float(metrics[name]["mean_scaled_absolute_error"]), name),
        )
        route_map[authority] = winner
        authority_metrics.append(
            {
                "respondent": authority,
                "validation_row_count": len(indices),
                "candidate_metrics": metrics,
                "selected_candidate": winner,
            }
        )
    result = {
        "schema": "eia_grid_all_authority_direct_hourly_design_benchmark.v2",
        "generated_utc": now_utc().isoformat(),
        "design_input_protocol_path": PROTOCOL_PATH.relative_to(ROOT).as_posix(),
        "design_input_protocol_sha256": file_sha256(PROTOCOL_PATH),
        "v1_protocol_sha256": file_sha256(V1_PROTOCOL_PATH),
        "v1_code_sha256": file_sha256(V1_CODE_PATH),
        "source_panel_row_count": panel["row_count"],
        "source_panel_row_chain_sha256": panel["row_chain_sha256"],
        "source_receipt_sha256": canonical_sha256(source_receipt),
        "training_row_count": len(training),
        "validation_row_count": len(validation),
        "feature_diagnostics": diagnostics,
        "fit_duration_ms": durations,
        "authority_metrics": authority_metrics,
        "selected_route_map": route_map,
        "candidate_ids": candidate_ids,
        "claim_boundary": design["claim_rule"],
    }
    if not dry_run:
        write_json_atomic(DESIGN_RESULT_PATH, result)
        write_json_atomic(DESIGN_EVIDENCE_PATH, result)
    return result


def next_common_target(sealed_at: datetime, protocol: dict[str, Any]) -> str:
    observed = sealed_at.astimezone(timezone.utc)
    minimum_lead = int(protocol["prediction_seal"]["minimum_target_interval_lead_hours"])
    required_start = observed + timedelta(hours=minimum_lead)
    target_start = required_start.replace(minute=0, second=0, microsecond=0)
    if required_start > target_start:
        target_start += timedelta(hours=1)
    target = period_string(target_start + timedelta(hours=1))
    first_allowed = protocol["prospective_window"].get("first_allowed_period_end_utc")
    if first_allowed and target < first_allowed:
        target = first_allowed
    final_target = protocol["prospective_window"].get("target_end_period_end_utc")
    if final_target and target > final_target:
        raise ValueError("prospective target window has ended")
    if sealed_at >= target_interval_start_utc(target):
        raise ValueError("target interval already started")
    if target_interval_start_utc(target) - sealed_at < timedelta(hours=minimum_lead):
        raise ValueError("target does not satisfy the minimum seal lead")
    return target


def prepare_common_forecast_rows(
    series: dict[str, dict[str, Any]],
    protocol: dict[str, Any],
    target: str,
    sealed_at: datetime,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if sealed_at >= target_interval_start_utc(target):
        return [], {"panel": "target interval already started"}
    rows: list[dict[str, Any]] = []
    failures: dict[str, str] = {}
    for authority in protocol["balancing_authorities"]:
        try:
            rows.append(
                build_feature_row(
                    series, protocol, authority, target, require_actual=False
                )
            )
        except ValueError as exc:
            failures[authority] = str(exc)
    if failures:
        return [], failures
    if len(rows) != len(protocol["balancing_authorities"]):
        return [], {"panel": "authority count mismatch"}
    if {row["target_period_end_utc"] for row in rows} != {target}:
        return [], {"panel": "common target mismatch"}
    return rows, {}


def seal_from_panel(
    protocol: dict[str, Any],
    panel: dict[str, Any],
    source_receipt: dict[str, Any],
    sealed_at: datetime,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    target = next_common_target(sealed_at, protocol)
    existing, previous = load_chain(PREDICTIONS_PATH)
    if any(row["target_period_end_utc"] == target for row in existing):
        return {
            "schema": "eia_grid_all_authority_direct_hourly_seal_run.v2",
            "run_utc": sealed_at.isoformat(),
            "dry_run": dry_run,
            "target_period_end_utc": target,
            "sealed_panel_count": 0,
            "sealed_authority_count": 0,
            "failures": {"panel": "common target already sealed"},
        }
    series = series_by_authority(panel, protocol)
    forecast_rows, failures = prepare_common_forecast_rows(
        series, protocol, target, sealed_at
    )
    if failures:
        return {
            "schema": "eia_grid_all_authority_direct_hourly_seal_run.v2",
            "run_utc": sealed_at.isoformat(),
            "dry_run": dry_run,
            "target_period_end_utc": target,
            "sealed_panel_count": 0,
            "sealed_authority_count": 0,
            "failures": failures,
        }
    design = protocol["historical_design"]
    training_rows, diagnostics = build_training_rows(
        panel,
        protocol,
        design["prospective_refit_start_period_end_utc"],
        design["prospective_refit_end_period_end_utc"],
    )
    models, durations = fit_models(training_rows, protocol)
    candidate_values = candidate_predictions(forecast_rows, models)
    authority_predictions = []
    for row, predictions in zip(forecast_rows, candidate_values):
        authority = row["respondent"]
        selected = protocol["router"]["route_map"][authority]
        authority_predictions.append(
            {
                "respondent": authority,
                "respondent_name": row["respondent_name"],
                "candidate_predictions_mwh": predictions,
                "selected_candidate": selected,
                "router_prediction_mwh": predictions[selected],
                "level_scale_mwh": row["level_scale_mwh"],
                "error_scale_mwh": row["error_scale_mwh"],
                "feature_count": len(row["features"]),
                "feature_sha256": canonical_sha256(row["features"]),
                "target_actual_present_at_seal": False,
            }
        )
    record = {
        "schema": "eia_grid_all_authority_direct_hourly_prediction_panel.v2",
        "target_period_end_utc": target,
        "target_interval_start_utc": target_interval_start_utc(target).isoformat(),
        "sealed_utc": sealed_at.isoformat(),
        "seal_lead_seconds": (
            target_interval_start_utc(target) - sealed_at
        ).total_seconds(),
        "authority_count": len(authority_predictions),
        "authorities": [row["respondent"] for row in authority_predictions],
        "authority_predictions": authority_predictions,
        "source_receipt_sha256": canonical_sha256(source_receipt),
        "source_panel_row_chain_sha256": panel["row_chain_sha256"],
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "protocol_commit": protocol_commit(),
        "runtime_commit": git_commit(),
        "route_reason_code": protocol["router"]["route_reason_code"],
        "training_row_count": len(training_rows),
        "training_rows_sha256": diagnostics["row_chain_sha256"],
        "fit_duration_ms": durations,
        "target_official_forecast_used": False,
        "target_actual_present_at_seal": False,
        "backfilled": False,
        "claim_boundary": protocol["claim_boundary"],
    }
    if dry_run:
        sealed = dict(record)
        sealed["prior_record_chain_sha256"] = previous
        sealed["record_sha256"] = canonical_sha256(sealed)
    else:
        sealed = append_chain_record(PREDICTIONS_PATH, record, previous)
    return {
        "schema": "eia_grid_all_authority_direct_hourly_seal_run.v2",
        "run_utc": sealed_at.isoformat(),
        "dry_run": dry_run,
        "target_period_end_utc": target,
        "sealed_panel_count": 1,
        "sealed_authority_count": len(authority_predictions),
        "failures": {},
        "sealed_panel": sealed,
    }


def settle_from_panel(
    protocol: dict[str, Any],
    panel: dict[str, Any],
    source_receipt: dict[str, Any],
    *,
    dry_run: bool,
) -> dict[str, Any]:
    predictions, _ = load_chain(PREDICTIONS_PATH)
    existing, previous = load_chain(SETTLEMENTS_PATH)
    settled_targets = {row["target_period_end_utc"] for row in existing}
    series = series_by_authority(panel, protocol)
    output: list[dict[str, Any]] = []
    waiting: dict[str, list[str]] = {}
    for prediction in predictions:
        target = prediction["target_period_end_utc"]
        if target in settled_targets:
            continue
        missing = [
            authority
            for authority in protocol["balancing_authorities"]
            if target not in series[authority]["actual"]
        ]
        if missing:
            waiting[target] = missing
            continue
        authority_metrics = []
        for forecast in prediction["authority_predictions"]:
            authority = forecast["respondent"]
            actual = float(series[authority]["actual"][target])
            error_scale = float(forecast["error_scale_mwh"])
            candidate_metrics: dict[str, Any] = {}
            for candidate, value in forecast["candidate_predictions_mwh"].items():
                absolute = abs(actual - float(value))
                candidate_metrics[candidate] = {
                    "absolute_error_mwh": absolute,
                    "scaled_absolute_error": absolute / error_scale,
                    "absolute_percentage_error": absolute / max(abs(actual), 1.0),
                }
            selected = forecast["selected_candidate"]
            router = candidate_metrics[selected]
            oracle = min(
                candidate_metrics,
                key=lambda name: (candidate_metrics[name]["scaled_absolute_error"], name),
            )
            authority_metrics.append(
                {
                    "respondent": authority,
                    "actual_mwh": actual,
                    "selected_candidate": selected,
                    "router_prediction_mwh": forecast["router_prediction_mwh"],
                    "router_absolute_error_mwh": router["absolute_error_mwh"],
                    "router_scaled_absolute_error": router["scaled_absolute_error"],
                    "candidate_metrics": candidate_metrics,
                    "oracle_candidate": oracle,
                    "router_regret_to_oracle": (
                        router["scaled_absolute_error"]
                        - candidate_metrics[oracle]["scaled_absolute_error"]
                    ),
                }
            )
        record = {
            "schema": "eia_grid_all_authority_direct_hourly_settlement_panel.v2",
            "target_period_end_utc": target,
            "settled_utc": now_utc().isoformat(),
            "authority_count": len(authority_metrics),
            "authority_metrics": authority_metrics,
            "prediction_panel_record_sha256": prediction["record_sha256"],
            "source_receipt_sha256": canonical_sha256(source_receipt),
            "source_panel_row_chain_sha256": panel["row_chain_sha256"],
            "protocol_sha256": prediction["protocol_sha256"],
            "protocol_commit": prediction["protocol_commit"],
            "claim_boundary": protocol["claim_boundary"],
        }
        if dry_run:
            settled = dict(record)
            settled["prior_record_chain_sha256"] = previous
            settled["record_sha256"] = canonical_sha256(settled)
        else:
            settled = append_chain_record(SETTLEMENTS_PATH, record, previous)
        previous = settled["record_sha256"]
        output.append(settled)
    return {
        "schema": "eia_grid_all_authority_direct_hourly_settlement_run.v2",
        "run_utc": now_utc().isoformat(),
        "dry_run": dry_run,
        "sealed_panel_count": len(predictions),
        "prior_settlement_panel_count": len(existing),
        "settled_panel_count": len(output),
        "waiting_for_authorities": waiting,
        "settlement_panels": output,
    }


def build_status(
    protocol: dict[str, Any],
    predictions: list[dict[str, Any]],
    settlements: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_ids = [row["id"] for row in protocol["candidates"]]
    router_scores = [
        float(metric["router_scaled_absolute_error"])
        for panel in settlements
        for metric in panel["authority_metrics"]
    ]
    candidate_scores = {
        candidate: [
            float(metric["candidate_metrics"][candidate]["scaled_absolute_error"])
            for panel in settlements
            for metric in panel["authority_metrics"]
        ]
        for candidate in candidate_ids
    }
    candidate_means = {
        candidate: mean(values) if values else None
        for candidate, values in candidate_scores.items()
    }
    available = {key: value for key, value in candidate_means.items() if value is not None}
    best_fixed = min(available, key=lambda key: (available[key], key)) if available else None
    common_count = len(settlements)
    windows = protocol["prospective_window"]
    release = protocol["external_release_gate"]
    complete_prediction_panels = all(
        panel.get("authority_count") == len(protocol["balancing_authorities"])
        and sorted(panel.get("authorities", [])) == sorted(protocol["balancing_authorities"])
        for panel in predictions
    )
    complete_settlement_panels = all(
        panel.get("authority_count") == len(protocol["balancing_authorities"])
        for panel in settlements
    )
    return {
        "schema": "eia_grid_all_authority_direct_hourly_status.v2",
        "generated_utc": now_utc().isoformat(),
        "state": (
            "WAITING_FOR_FIRST_COMPLETE_PANEL"
            if not predictions
            else "COMPLETE_PANELS_AWAITING_ACTUALS"
            if not settlements
            else "PROSPECTIVE_COLLECTION_ACTIVE"
        ),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "protocol_commit": protocol_commit(),
        "runtime_commit": git_commit(),
        "prediction_panel_count": len(predictions),
        "sealed_authority_prediction_count": len(predictions) * 8,
        "settlement_panel_count": len(settlements),
        "settled_authority_prediction_count": len(settlements) * 8,
        "common_settled_hour_count": common_count,
        "first_common_settled_period": settlements[0]["target_period_end_utc"] if settlements else None,
        "latest_common_settled_period": settlements[-1]["target_period_end_utc"] if settlements else None,
        "all_prediction_panels_complete": complete_prediction_panels,
        "all_settlement_panels_complete": complete_settlement_panels,
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
        "external_release_ready": (
            complete_prediction_panels
            and complete_settlement_panels
            and common_count >= int(release["evidence_packet_minimum_common_hours"])
        ),
        "performance_claim_ready": False,
        "promotion_evaluation_complete": False,
        "claim_boundary": protocol["claim_boundary"],
    }


@contextmanager
def cycle_lock(path: Path = LOCK_PATH) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"all-authority cycle already locked: {path}") from exc
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


def run_cycle(*, timeout: int = 60, dry_run: bool = False) -> dict[str, Any]:
    with cycle_lock():
        protocol = load_protocol()
        if not dry_run:
            for path in (PROTOCOL_PATH, Path(__file__).resolve()):
                if not git_path_is_clean(path):
                    raise RuntimeError(f"prospective source is not committed and clean: {path}")
        panel, receipt = refresh_source_panel(protocol, timeout=timeout, dry_run=dry_run)
        sealed_at = now_utc()
        seal = seal_from_panel(
            protocol, panel, receipt, sealed_at, dry_run=dry_run
        )
        settle = settle_from_panel(protocol, panel, receipt, dry_run=dry_run)
        predictions, prediction_terminal = load_chain(PREDICTIONS_PATH)
        settlements, settlement_terminal = load_chain(SETTLEMENTS_PATH)
        prediction_hashes = {row["record_sha256"] for row in predictions}
        if any(
            row["prediction_panel_record_sha256"] not in prediction_hashes
            for row in settlements
        ):
            raise ValueError("settlement references a prediction outside the verified chain")
        status = build_status(protocol, predictions, settlements)
        receipt_payload = {
            "schema": "eia_grid_all_authority_direct_hourly_operational_run.v2",
            "run_utc": now_utc().isoformat(),
            "dry_run": dry_run,
            "protocol_sha256": status["protocol_sha256"],
            "protocol_commit": status["protocol_commit"],
            "runtime_commit": status["runtime_commit"],
            "source_panel_row_count": panel["row_count"],
            "source_panel_row_chain_sha256": panel["row_chain_sha256"],
            "source_receipt_sha256": canonical_sha256(receipt),
            "sealed_panel_count": seal["sealed_panel_count"],
            "sealed_authority_count": seal["sealed_authority_count"],
            "settled_panel_count": settle["settled_panel_count"],
            "prediction_panel_count": len(predictions),
            "prediction_terminal_sha256": prediction_terminal,
            "settlement_panel_count": len(settlements),
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
            "schema": "eia_grid_all_authority_direct_hourly_cycle.v2",
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
    if args.design_benchmark:
        protocol = load_protocol(allow_design_pending=True)
        result = design_benchmark(protocol, timeout=args.timeout, dry_run=args.dry_run)
    else:
        result = run_cycle(timeout=args.timeout, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
