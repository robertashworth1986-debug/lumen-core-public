"""Prospective, append-only EIA hybrid specialist router.

Predictions count only when they are sealed before target-local midnight and
before EIA actual demand is present. Historical data through 2026-07-12 was
used to design the frozen authority route map, so only later targets can test
the routing hypothesis.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, time as clock_time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "config" / "eia_grid_prospective_hybrid_router_protocol_v1.json"
RESIDUAL_PROTOCOL_PATH = ROOT / "config" / "eia_grid_residual_moe_protocol_v1.json"
RESIDUAL_MODULE_PATH = ROOT / "code" / "eia_grid_residual_moe_benchmark.py"
OUT_DIR = ROOT / "out" / "eia_grid_prospective_hybrid_router"
PREDICTIONS_PATH = OUT_DIR / "sealed_predictions.jsonl"
SETTLEMENTS_PATH = OUT_DIR / "settlements.jsonl"
LATEST_RUN_PATH = OUT_DIR / "latest_run.json"
EIA_ROUTE = "https://api.eia.gov/v2/electricity/rto/daily-region-data/data/"
ZERO_HASH = "0" * 64

EIA_FACET_TIMEZONES = {
    "CISO": "Pacific",
    "ERCO": "Central",
    "ISNE": "Eastern",
    "MISO": "Central",
    "NYIS": "Eastern",
    "PJM": "Eastern",
    "SWPP": "Central",
    "TVA": "Central",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    if payload.get("schema") != "eia_grid_prospective_hybrid_router_protocol.v1":
        raise ValueError("unexpected prospective hybrid-router protocol schema")
    authorities = payload["balancing_authorities"]
    if sorted(authorities) != sorted(payload["router"]["route_map"]):
        raise ValueError("route map does not cover the frozen authority registry")
    if sorted(authorities) != sorted(payload["authority_timezones"]):
        raise ValueError("timezone map does not cover the frozen authority registry")
    if sorted(authorities) != sorted(EIA_FACET_TIMEZONES):
        raise ValueError("EIA facet timezone registry differs from the protocol")
    if payload["router"].get("dynamic_override_allowed") is not False:
        raise ValueError("v1 router must not permit dynamic overrides")
    return payload


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


def load_residual_module():
    spec = importlib.util.spec_from_file_location("eia_grid_residual_moe", RESIDUAL_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load residual benchmark module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_eia_key() -> str:
    key = os.environ.get("EIA_API_KEY") or os.environ.get("EIA_API_KEY_PREMIUM")
    if not key:
        raise RuntimeError("EIA API key is not configured in the process environment")
    return key


def request_eia_rows(
    protocol: dict[str, Any], respondent: str, start: str, end: str, timeout: int = 45
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    key = read_eia_key()
    facet_timezone = EIA_FACET_TIMEZONES[respondent]
    params = [
        ("api_key", key),
        ("frequency", "daily"),
        ("data[0]", "value"),
        ("facets[type][]", protocol["source"]["actual_type"]),
        ("facets[type][]", protocol["source"]["official_forecast_type"]),
        ("facets[respondent][]", respondent),
        ("facets[timezone][]", facet_timezone),
        ("start", start),
        ("end", end),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "asc"),
        ("offset", "0"),
        ("length", "5000"),
    ]
    request = urllib.request.Request(
        EIA_ROUTE + "?" + urllib.parse.urlencode(params),
        headers={"User-Agent": "LumenCore-Prospective-Hybrid-Router/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status = int(response.getcode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"EIA request failed for {respondent} with HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(
            f"EIA request failed for {respondent}: {type(exc).__name__}"
        ) from None

    payload = json.loads(raw.decode("utf-8"))
    response_payload = payload.get("response", {}) if isinstance(payload, dict) else {}
    incoming = response_payload.get("data", []) if isinstance(response_payload, dict) else []
    allowed_types = {
        protocol["source"]["actual_type"],
        protocol["source"]["official_forecast_type"],
    }
    rows: list[dict[str, Any]] = []
    for row in incoming:
        if not isinstance(row, dict):
            continue
        if row.get("respondent") != respondent or row.get("timezone") != facet_timezone:
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
                "respondent": respondent,
                "respondent_name": str(row.get("respondent-name") or respondent),
                "timezone": facet_timezone,
                "type": str(row.get("type")),
                "type_name": str(row.get("type-name") or row.get("type")),
                "value": value,
                "value_units": str(row.get("value-units") or protocol["source"]["native_unit"]),
            }
        )
    rows.sort(key=lambda row: (row["respondent"], row["period"], row["type"]))
    return rows, {
        "respondent": respondent,
        "http_status": status,
        "accepted_row_count": len(rows),
        "response_total": int(response_payload.get("total", len(incoming))),
        "response_body_sha256": hashlib.sha256(raw).hexdigest(),
        "request": {
            "route": EIA_ROUTE,
            "respondent": respondent,
            "timezone": facet_timezone,
            "start": start,
            "end": end,
            "types": sorted(allowed_types),
            "credential_serialized": False,
        },
    }


def collect_panel(
    protocol: dict[str, Any], start: str, end: str, timeout: int = 45
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    receipts: dict[str, dict[str, Any]] = {}
    for respondent in protocol["balancing_authorities"]:
        authority_rows, receipt = request_eia_rows(protocol, respondent, start, end, timeout)
        rows.extend(authority_rows)
        receipts[respondent] = receipt

    by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    conflicts: list[dict[str, Any]] = []
    for row in rows:
        key = (row["respondent"], row["timezone"], row["type"], row["period"])
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = row
        elif not math.isclose(
            float(existing["value"]), float(row["value"]), rel_tol=1e-12, abs_tol=1e-9
        ):
            conflicts.append({"key": key, "first": existing["value"], "second": row["value"]})
    if conflicts:
        raise ValueError(f"EIA duplicate-value conflicts: {len(conflicts)}")
    deduplicated = sorted(
        by_key.values(), key=lambda row: (row["respondent"], row["period"], row["type"])
    )
    return (
        {
            "schema": "eia_grid_validation_panel.v1",
            "generated_utc": now_utc(),
            "rows": deduplicated,
            "row_chain_sha256": canonical_sha256(deduplicated),
            "quality": {
                "row_count": len(deduplicated),
                "authority_count": len({row["respondent"] for row in deduplicated}),
                "duplicate_conflict_count": 0,
            },
            "requests": [receipts[key]["request"] for key in sorted(receipts)],
        },
        receipts,
    )


def target_local_midnight_utc(
    protocol: dict[str, Any], respondent: str, target_date: str
) -> datetime:
    zone = ZoneInfo(protocol["authority_timezones"][respondent])
    local_midnight = datetime.combine(date.fromisoformat(target_date), clock_time.min, tzinfo=zone)
    return local_midnight.astimezone(timezone.utc)


def seal_eligibility(
    protocol: dict[str, Any], respondent: str, target_date: str, sealed_at: datetime
) -> tuple[bool, str]:
    first_allowed = date.fromisoformat(protocol["prospective_window"]["first_allowed_target_date"])
    target = date.fromisoformat(target_date)
    if target < first_allowed:
        return False, "before_first_allowed_target"
    if sealed_at.tzinfo is None:
        raise ValueError("sealed_at must be timezone-aware")
    if sealed_at.astimezone(timezone.utc) >= target_local_midnight_utc(
        protocol, respondent, target_date
    ):
        return False, "after_target_local_midnight"
    return True, "eligible"


def series_by_authority(panel: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
    output = {
        respondent: {"actual": {}, "official": {}, "name": respondent}
        for respondent in protocol["balancing_authorities"]
    }
    for row in panel["rows"]:
        respondent = row["respondent"]
        if respondent not in output:
            continue
        output[respondent]["name"] = row.get("respondent_name") or respondent
        if row["type"] == protocol["source"]["actual_type"]:
            output[respondent]["actual"][row["period"]] = float(row["value"])
        elif row["type"] == protocol["source"]["official_forecast_type"]:
            output[respondent]["official"][row["period"]] = float(row["value"])
    return output


def latest_eligible_targets(
    panel: dict[str, Any], protocol: dict[str, Any], sealed_at: datetime
) -> tuple[dict[str, str], dict[str, str]]:
    series = series_by_authority(panel, protocol)
    selected: dict[str, str] = {}
    skipped: dict[str, str] = {}
    for respondent in protocol["balancing_authorities"]:
        actual = series[respondent]["actual"]
        official = series[respondent]["official"]
        reasons: Counter[str] = Counter()
        for target in sorted(official, reverse=True):
            if target in actual:
                reasons["actual_already_present"] += 1
                continue
            eligible, reason = seal_eligibility(protocol, respondent, target, sealed_at)
            if not eligible:
                reasons[reason] += 1
                continue
            selected[respondent] = target
            break
        if respondent not in selected:
            skipped[respondent] = reasons.most_common(1)[0][0] if reasons else "no_official_forecast"
    return selected, skipped


def make_training_protocol(target_date: str) -> dict[str, Any]:
    protocol = json.loads(RESIDUAL_PROTOCOL_PATH.read_text(encoding="utf-8"))
    previous = (date.fromisoformat(target_date) - timedelta(days=1)).isoformat()
    protocol = copy.deepcopy(protocol)
    protocol["splits"].update(
        {
            "training_start": "2024-04-01",
            "training_end": previous,
            "development_start": "2099-01-01",
            "development_end": "2099-01-01",
            "holdout_start": "2099-01-02",
            "holdout_end": "2099-01-02",
        }
    )
    return protocol


def build_forecast_feature(
    panel: dict[str, Any], protocol: dict[str, Any], target_date: str, respondent: str
) -> dict[str, Any]:
    residual = load_residual_module()
    series = series_by_authority(panel, protocol)
    bundle = series[respondent]
    actual: dict[str, float] = bundle["actual"]
    official: dict[str, float] = bundle["official"]
    if target_date in actual:
        raise ValueError("target actual is already present")
    if target_date not in official:
        raise ValueError("target official forecast is unavailable")

    target_day = date.fromisoformat(target_date)
    required_dates = [residual.lag_date(target_day, offset) for offset in range(1, 30)]
    if any(value not in actual for value in required_dates):
        raise ValueError("required actual lag is unavailable")
    if any(value not in official for value in required_dates[:28]):
        raise ValueError("required official-forecast lag is unavailable")

    residual_protocol = json.loads(RESIDUAL_PROTOCOL_PATH.read_text(encoding="utf-8"))
    maximum_history = int(residual_protocol["splits"]["maximum_history_days"])
    minimum_history = int(residual_protocol["splits"]["minimum_history_days"])
    history_dates = [value for value in sorted(actual) if value < target_date][-maximum_history:]
    if len(history_dates) < minimum_history:
        raise ValueError("insufficient pre-target history")
    history = [actual[value] for value in history_dates]
    scale = residual.seasonal_mase_scale(history)
    center = float(np.median(np.asarray(history, dtype=float)))
    ar_forecast = residual.forecast_autoregressive_ridge(history)
    previous = required_dates[0]
    seasonal = required_dates[6]
    official_value = official[target_date]
    residuals_28 = np.asarray(
        [actual[value] - official[value] for value in required_dates[:28]], dtype=float
    )
    actual_29 = np.asarray([actual[value] for value in required_dates], dtype=float)
    day_of_week_angle = 2.0 * math.pi * target_day.weekday() / 7.0
    day_of_year_angle = 2.0 * math.pi * (target_day.timetuple().tm_yday - 1) / 365.25
    features = [
        (official_value - ar_forecast) / scale,
        (official_value - actual[seasonal]) / scale,
        (official_value - actual[previous]) / scale,
        (ar_forecast - actual[seasonal]) / scale,
        (official_value - center) / scale,
        (actual[required_dates[0]] - official[required_dates[0]]) / scale,
        (actual[required_dates[6]] - official[required_dates[6]]) / scale,
        (actual[required_dates[13]] - official[required_dates[13]]) / scale,
        float(np.mean(residuals_28[:7])) / scale,
        float(np.mean(residuals_28)) / scale,
        float(np.std(residuals_28)) / scale,
        (actual[required_dates[0]] - actual[required_dates[1]]) / scale,
        (actual[required_dates[0]] - actual[required_dates[7]]) / scale,
        float(np.std(np.diff(actual_29))) / scale,
        math.sin(day_of_week_angle),
        math.cos(day_of_week_angle),
        math.sin(day_of_year_angle),
        math.cos(day_of_year_angle),
    ]
    authority_order = sorted(protocol["balancing_authorities"])
    features.extend(1.0 if respondent == value else 0.0 for value in authority_order)
    if not all(math.isfinite(float(value)) for value in features):
        raise ValueError("nonfinite target feature")
    return {
        "respondent": respondent,
        "respondent_name": bundle["name"],
        "target_date": target_date,
        "calendar_month": target_date[:7],
        "official_mwh": official_value,
        "ar_mwh": ar_forecast,
        "seasonal_mwh": actual[seasonal],
        "last_mwh": actual[previous],
        "history_center_mwh": center,
        "seasonal_scale_mwh": scale,
        "features": features,
    }


def specialist_predictions(
    forecast_rows: list[dict[str, Any]], training_rows: list[dict[str, Any]]
) -> tuple[dict[tuple[str, str], dict[str, float]], dict[str, float]]:
    residual = load_residual_module()
    models, fit_durations = residual.fit_models(training_rows)
    components = residual.component_predictions(forecast_rows, models)
    output: dict[tuple[str, str], dict[str, float]] = {}
    for index, row in enumerate(forecast_rows):
        residual_map = residual.candidate_prediction_map(
            row,
            {
                "ridge_residual": float(components["ridge_residual"][index]),
                "xgboost_residual": float(components["xgboost_residual"][index]),
                "lightgbm_residual": float(components["lightgbm_residual"][index]),
            },
        )
        baseline_map = residual.baseline_prediction_map(
            row,
            {
                "direct_xgboost_stack": float(components["direct_xgboost_stack"][index]),
                "direct_lightgbm_stack": float(components["direct_lightgbm_stack"][index]),
            },
        )
        output[(row["respondent"], row["target_date"])] = {
            "xgboost_residual": float(residual_map["xgboost_residual"][0]),
            "direct_lightgbm_stack": float(baseline_map["direct_lightgbm_stack"]),
            "autoregressive_ridge_p14": float(baseline_map["autoregressive_ridge_p14"]),
            "eia_day_ahead_forecast": float(baseline_map["eia_day_ahead_forecast"]),
        }
    return output, fit_durations


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
            expected = canonical_sha256(unsigned)
            if observed != expected:
                raise ValueError(f"record hash mismatch at {path.name}:{line_number}")
            records.append(record)
            previous = observed
    return records, previous


def append_chain_record(path: Path, record: dict[str, Any], previous: str) -> dict[str, Any]:
    output = dict(record)
    output["prior_record_chain_sha256"] = previous
    output["record_sha256"] = canonical_sha256(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(output, sort_keys=True, separators=(",", ":")) + "\n")
    return output


def seal_latest(
    protocol: dict[str, Any], timeout: int = 45, dry_run: bool = False
) -> dict[str, Any]:
    sealed_at = datetime.now(timezone.utc)
    end = (sealed_at.date() + timedelta(days=2)).isoformat()
    panel, receipts = collect_panel(protocol, "2024-01-01", end, timeout)
    targets, skipped = latest_eligible_targets(panel, protocol, sealed_at)
    existing, previous = load_chain(PREDICTIONS_PATH)
    existing_keys = {(row["respondent"], row["target_date"]) for row in existing}
    sealed_records: list[dict[str, Any]] = []

    for target_date in sorted(set(targets.values())):
        respondents = [key for key, value in targets.items() if value == target_date]
        pending = [key for key in respondents if (key, target_date) not in existing_keys]
        if not pending:
            for respondent in respondents:
                skipped[respondent] = "already_sealed"
            continue
        training_protocol = make_training_protocol(target_date)
        residual = load_residual_module()
        training_rows, diagnostics = residual.build_feature_rows(panel, training_protocol)
        forecast_rows: list[dict[str, Any]] = []
        for respondent in pending:
            try:
                forecast_rows.append(
                    build_forecast_feature(panel, protocol, target_date, respondent)
                )
            except ValueError as exc:
                skipped[respondent] = str(exc)
        if not forecast_rows:
            continue
        predictions, fit_durations = specialist_predictions(forecast_rows, training_rows)
        for row in forecast_rows:
            respondent = row["respondent"]
            values = predictions[(respondent, target_date)]
            selected = protocol["router"]["route_map"][respondent]
            record = {
                "schema": "eia_grid_prospective_hybrid_router_prediction.v1",
                "target_date": target_date,
                "respondent": respondent,
                "respondent_name": row["respondent_name"],
                "sealed_utc": sealed_at.isoformat(),
                "target_local_midnight_utc": target_local_midnight_utc(
                    protocol, respondent, target_date
                ).isoformat(),
                "source_response_sha256": receipts[respondent]["response_body_sha256"],
                "source_panel_row_chain_sha256": panel["row_chain_sha256"],
                "protocol_sha256": file_sha256(PROTOCOL_PATH),
                "protocol_commit": protocol_commit(),
                "specialist_predictions_mwh": values,
                "selected_specialist": selected,
                "router_prediction_mwh": values[selected],
                "route_reason_code": protocol["router"]["route_reason_code"],
                "seasonal_scale_mwh": row["seasonal_scale_mwh"],
                "last_actual_mwh": row["last_mwh"],
                "official_forecast_mwh": row["official_mwh"],
                "feature_sha256": canonical_sha256(row["features"]),
                "feature_count": len(row["features"]),
                "training_row_count": len(training_rows),
                "training_end": training_protocol["splits"]["training_end"],
                "training_diagnostics_sha256": canonical_sha256(diagnostics),
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

    result = {
        "schema": "eia_grid_prospective_hybrid_router_run.v1",
        "run_utc": sealed_at.isoformat(),
        "dry_run": dry_run,
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "protocol_commit": protocol_commit(),
        "source_panel_row_count": panel["quality"]["row_count"],
        "source_panel_row_chain_sha256": panel["row_chain_sha256"],
        "sealed_record_count": len(sealed_records),
        "sealed_records": sealed_records,
        "skipped": skipped,
        "existing_prediction_count": len(existing),
    }
    if not dry_run:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        LATEST_RUN_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def settle(protocol: dict[str, Any], timeout: int = 45, dry_run: bool = False) -> dict[str, Any]:
    predictions, _ = load_chain(PREDICTIONS_PATH)
    existing_settlements, previous = load_chain(SETTLEMENTS_PATH)
    settled_keys = {
        (row["respondent"], row["target_date"], row["prediction_record_sha256"])
        for row in existing_settlements
    }
    if not predictions:
        return {"settled_record_count": 0, "reason": "no_sealed_predictions"}
    end = datetime.now(timezone.utc).date().isoformat()
    panel, receipts = collect_panel(protocol, "2024-01-01", end, timeout)
    series = series_by_authority(panel, protocol)
    output: list[dict[str, Any]] = []
    for prediction in predictions:
        key = (
            prediction["respondent"],
            prediction["target_date"],
            prediction["record_sha256"],
        )
        if key in settled_keys:
            continue
        actual = series[prediction["respondent"]]["actual"].get(prediction["target_date"])
        if actual is None:
            continue
        scale = float(prediction["seasonal_scale_mwh"])
        specialist_metrics = {}
        for specialist, value in prediction["specialist_predictions_mwh"].items():
            error = abs(float(actual) - float(value))
            specialist_metrics[specialist] = {
                "absolute_error_mwh": error,
                "seasonal_mase_7": error / scale,
            }
        selected = prediction["selected_specialist"]
        oracle = min(
            specialist_metrics,
            key=lambda name: (
                specialist_metrics[name]["seasonal_mase_7"],
                name,
            ),
        )
        settlement = {
            "schema": "eia_grid_prospective_hybrid_router_settlement.v1",
            "settled_utc": now_utc(),
            "target_date": prediction["target_date"],
            "respondent": prediction["respondent"],
            "prediction_record_sha256": prediction["record_sha256"],
            "actual_mwh": float(actual),
            "source_response_sha256": receipts[prediction["respondent"]][
                "response_body_sha256"
            ],
            "specialist_metrics": specialist_metrics,
            "selected_specialist": selected,
            "router_seasonal_mase_7": specialist_metrics[selected]["seasonal_mase_7"],
            "oracle_specialist": oracle,
            "oracle_seasonal_mase_7": specialist_metrics[oracle]["seasonal_mase_7"],
            "router_regret_to_oracle": specialist_metrics[selected]["seasonal_mase_7"]
            - specialist_metrics[oracle]["seasonal_mase_7"],
            "route_hit": selected == oracle,
            "claim_boundary": protocol["claim_boundary"],
        }
        if dry_run:
            preview = dict(settlement)
            preview["prior_record_chain_sha256"] = previous
            preview["record_sha256"] = canonical_sha256(preview)
            settled = preview
        else:
            settled = append_chain_record(SETTLEMENTS_PATH, settlement, previous)
            previous = settled["record_sha256"]
        output.append(settled)
    return {
        "schema": "eia_grid_prospective_hybrid_router_settlement_run.v1",
        "run_utc": now_utc(),
        "dry_run": dry_run,
        "sealed_prediction_count": len(predictions),
        "prior_settlement_count": len(existing_settlements),
        "settled_record_count": len(output),
        "settlements": output,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal-latest", action="store_true")
    parser.add_argument("--settle", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=45)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.seal_latest and not args.settle:
        args.seal_latest = True
    protocol = load_protocol()
    outputs = []
    if args.seal_latest:
        outputs.append(seal_latest(protocol, timeout=args.timeout, dry_run=args.dry_run))
    if args.settle:
        outputs.append(settle(protocol, timeout=args.timeout, dry_run=args.dry_run))
    print(json.dumps(outputs[0] if len(outputs) == 1 else outputs, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
