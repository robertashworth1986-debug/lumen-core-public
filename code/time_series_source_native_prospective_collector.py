"""Prospective source-native forecast collector with pre-release custody.

The collector seals the frozen candidate and all registered baselines against a
content-addressed source snapshot before a future target exists. Later cycles
settle only predictions whose source-specific release-order proof passes. It
does not tune, rank, promote, trade, or make performance claims.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "config" / "time_series_source_native_prospective_protocol_v2.json"
MODEL_PATH = ROOT / "code" / "geometry_time_series_model_routing_benchmark.py"
DEFAULT_OUT_DIR = ROOT / "out" / "time_series_source_native_prospective"
ZERO_HASH = "0" * 64
EXPECTED_BASELINES = (
    "naive_last",
    "drift",
    "moving_average",
    "exponential_smoothing",
    "linear_trend",
    "seasonal_naive_source_period",
    "damped_holt_ets",
    "autoregressive_ridge_source_lag",
)
FORBIDDEN_METADATA_TOKENS = (
    "api_key",
    "apikey",
    "credential",
    "oauth",
    "password",
    "secret",
    "token",
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protocol_commit(path: Path = PROTOCOL_PATH, root: Path = ROOT) -> str | None:
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", str(path.relative_to(root))],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    return result.stdout.strip() or None


def validate_protocol(protocol: dict[str, Any], root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    if protocol.get("schema") != "time_series_source_native_prospective_protocol.v2":
        errors.append("protocol_schema_invalid")
    if protocol.get("status") != "FROZEN_AWAITING_FIRST_SEAL":
        errors.append("protocol_not_frozen_waiting")
    unsigned = {key: value for key, value in protocol.items() if key != "protocol_payload_sha256"}
    if protocol.get("protocol_payload_sha256") != canonical_sha256(unsigned):
        errors.append("protocol_payload_sha256_mismatch")
    if tuple(protocol.get("registered_baselines", [])) != EXPECTED_BASELINES:
        errors.append("registered_baselines_changed_or_reordered")
    if protocol.get("forecast_contract", {}).get("horizons") != [1, 3, 5]:
        errors.append("forecast_horizons_not_bound")
    if protocol.get("forecast_contract", {}).get("prediction_decimal_places") != 10:
        errors.append("prediction_precision_not_bound")
    supersession = protocol.get("supersession", {})
    if supersession.get("prior_eligible_future_observation_count") != 0:
        errors.append("supersession_after_observations_forbidden")
    if supersession.get("outcome_dependent_change") is not False:
        errors.append("supersession_must_be_outcome_independent")
    if protocol.get("freeze", {}).get("outcome_dependent_changes_allowed") is not False:
        errors.append("outcome_dependent_changes_must_be_disabled")

    sources = protocol.get("sources")
    if not isinstance(sources, list) or {row.get("source") for row in sources if isinstance(row, dict)} != {
        "FRED",
        "TWELVE_DATA",
    }:
        errors.append("source_contract_invalid")
    else:
        for source in sources:
            source_name = source.get("source")
            request_contract = source.get("request_contract", {})
            polling_contract = source.get("polling_contract", {})
            if request_contract.get("credential_serialization_allowed") is not False:
                errors.append(f"credential_serialization_must_be_disabled:{source_name}")
            if polling_contract.get("raw_response_retention_required") is not True:
                errors.append(f"raw_response_retention_not_required:{source_name}")
            if source_name == "FRED" and request_contract.get("output_type") != 4:
                errors.append("fred_initial_release_output_type_not_bound")
            if source_name == "FRED" and request_contract.get("realtime_chunk_days") != 1460:
                errors.append("fred_realtime_chunk_not_bound")
            if source_name == "FRED" and not source.get("vintage_dates_endpoint"):
                errors.append("fred_vintage_index_endpoint_not_bound")
            if source_name == "TWELVE_DATA":
                if request_contract.get("adjust") != "splits":
                    errors.append("twelve_data_adjustment_policy_not_bound")
                if polling_contract.get("not_before_exchange_local_time") != "18:00:00":
                    errors.append("twelve_data_post_close_boundary_not_bound")
                if polling_contract.get("same_session_first_seen_required") is not True:
                    errors.append("twelve_data_first_seen_rule_not_bound")
            for series in source.get("series", []):
                if series.get("horizons") != [1, 3, 5]:
                    errors.append(f"series_horizons_not_bound:{source.get('source')}:{series.get('series_id')}")
                if int(series.get("minimum_history_count", 0)) < 24:
                    errors.append(f"series_history_gate_too_small:{source.get('source')}:{series.get('series_id')}")
                if source_name == "FRED":
                    try:
                        date.fromisoformat(str(series.get("alfred_initial_release_start", "")))
                    except ValueError:
                        errors.append(
                            f"fred_alfred_start_not_bound:{series.get('series_id')}"
                        )

    vintage_contract = protocol.get("vintage_contract", {})
    if vintage_contract.get("test_fixture_admission_to_production_ledger_allowed") is not False:
        errors.append("test_fixture_production_admission_must_be_disabled")
    ledger_contract = protocol.get("ledger_contract", {})
    if ledger_contract.get("external_anchor_required") is not True:
        errors.append("external_anchor_not_required")
    if ledger_contract.get("semantic_preflight_before_append_required") is not True:
        errors.append("semantic_preflight_not_required")
    if ledger_contract.get("immediate_external_anchor_request_required") is not True:
        errors.append("immediate_anchor_request_not_required")

    artifacts = protocol.get("frozen_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("frozen_artifacts_missing")
    else:
        for artifact in artifacts:
            relative = str(artifact.get("path", "")) if isinstance(artifact, dict) else ""
            expected = str(artifact.get("sha256", "")).lower() if isinstance(artifact, dict) else ""
            path = root / relative
            if not relative or not path.is_file():
                errors.append(f"frozen_artifact_missing:{relative}")
            elif file_sha256(path) != expected:
                errors.append(f"frozen_artifact_hash_mismatch:{relative}")
    return errors


def load_protocol(path: Path = PROTOCOL_PATH, root: Path = ROOT) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("protocol must be a JSON object")
    errors = validate_protocol(payload, root=root)
    if errors:
        raise ValueError("invalid prospective protocol: " + ", ".join(errors))
    return payload


def load_model_module(path: Path = MODEL_PATH):
    name = "time_series_source_native_frozen_model"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load frozen model implementation: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def source_contract(protocol: dict[str, Any], source: str) -> dict[str, Any]:
    for row in protocol["sources"]:
        if row["source"] == source:
            return row
    raise ValueError(f"source is not registered: {source}")


def series_contract(source: dict[str, Any], series_id: str) -> dict[str, Any]:
    for row in source["series"]:
        if row["series_id"] == series_id:
            return row
    raise ValueError(f"series is not registered for {source['source']}: {series_id}")


def ensure_no_secret_metadata(value: Any, path: str = "snapshot") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower()
            if any(token in normalized for token in FORBIDDEN_METADATA_TOKENS):
                raise ValueError(f"forbidden credential-like metadata field: {path}.{key}")
            ensure_no_secret_metadata(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            ensure_no_secret_metadata(child, f"{path}[{index}]")


def finite_number(value: Any) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("observation value must be finite")
    return number


def runtime_fingerprint(model: Any) -> dict[str, str]:
    return {
        "python_version": platform.python_version(),
        "numpy_version": str(model.np.__version__),
        "operating_system": platform.system(),
        "machine": platform.machine(),
    }


def ensure_custody_admitted(
    snapshot: dict[str, Any], *, allow_test_fixture: bool
) -> None:
    custody_mode = snapshot["custody_mode"]
    if custody_mode == "LIVE_PROVIDER_RESPONSE":
        if snapshot["raw_response_retention_verified"] is not True:
            raise ValueError("live provider snapshot is missing retained raw responses")
        return
    if custody_mode == "TEST_FIXTURE" and allow_test_fixture:
        return
    raise ValueError("non-live snapshot cannot enter the production custody ledger")


def origin_completeness_proof(
    *,
    snapshot: dict[str, Any],
    source: dict[str, Any],
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    fetched_at = parse_utc(snapshot["fetched_at_utc"])
    latest = observations[-1]
    if snapshot["source"] == "FRED":
        first_vintage_date = date.fromisoformat(latest["first_vintage_date"])
        passed = first_vintage_date <= fetched_at.date()
        return {
            "method": "latest_origin_first_vintage_not_after_fetch_date",
            "fetched_at_utc": utc_text(fetched_at),
            "origin_period": latest["period"],
            "origin_first_vintage_date": first_vintage_date.isoformat(),
            "passed": passed,
        }
    exchange_timezone = ZoneInfo(source["exchange_timezone"])
    fetched_local = fetched_at.astimezone(exchange_timezone)
    origin_date = date.fromisoformat(latest["period"])
    not_before = time.fromisoformat(
        source["polling_contract"]["not_before_exchange_local_time"]
    )
    prior_session = origin_date < fetched_local.date()
    same_session_after_close = (
        origin_date == fetched_local.date()
        and fetched_local.time().replace(tzinfo=None) >= not_before
    )
    passed = prior_session or same_session_after_close
    return {
        "method": "prior_session_or_same_session_after_close_buffer",
        "fetched_at_utc": utc_text(fetched_at),
        "exchange_timezone": source["exchange_timezone"],
        "fetched_exchange_local": fetched_local.isoformat(),
        "origin_period": latest["period"],
        "not_before_exchange_local_time": not_before.isoformat(),
        "prior_session": prior_session,
        "same_session_after_close": same_session_after_close,
        "passed": passed,
    }


def normalize_snapshot(snapshot: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
    if snapshot.get("schema") != "time_series_source_native_source_snapshot.v2":
        raise ValueError("unexpected source snapshot schema")
    safe_snapshot = {
        key: value for key, value in snapshot.items() if key != "_raw_source_responses"
    }
    ensure_no_secret_metadata(safe_snapshot)
    fetched_at = parse_utc(str(snapshot.get("fetched_at_utc", "")))
    source_name = str(snapshot.get("source", ""))
    registered_source = source_contract(protocol, source_name)
    normalized_series: list[dict[str, Any]] = []
    seen_series: set[str] = set()
    for supplied in snapshot.get("series", []):
        if not isinstance(supplied, dict):
            raise ValueError("snapshot series entry must be an object")
        series_id = str(supplied.get("series_id", ""))
        if series_id in seen_series:
            raise ValueError(f"duplicate snapshot series: {series_id}")
        seen_series.add(series_id)
        contract = series_contract(registered_source, series_id)
        observations: list[dict[str, Any]] = []
        seen_periods: set[str] = set()
        for supplied_observation in supplied.get("observations", []):
            period = str(supplied_observation.get("period", ""))
            date.fromisoformat(period)
            if period in seen_periods:
                raise ValueError(f"duplicate observation period: {source_name}:{series_id}:{period}")
            seen_periods.add(period)
            row = {
                "period": period,
                "value": finite_number(supplied_observation.get("value")),
            }
            if source_name == "FRED":
                vintage = str(supplied_observation.get("first_vintage_date", ""))
                date.fromisoformat(vintage)
                row["first_vintage_date"] = vintage
            observations.append(row)
        observations.sort(key=lambda row: row["period"])
        if len(observations) < int(contract["minimum_history_count"]):
            raise ValueError(f"insufficient history: {source_name}:{series_id}")
        normalized_series.append(
            {
                "series_id": series_id,
                "cadence": contract["cadence"],
                "observations": observations,
            }
        )
    expected_series = {row["series_id"] for row in registered_source["series"]}
    if seen_series != expected_series:
        raise ValueError(
            f"snapshot series coverage mismatch for {source_name}: "
            f"expected {sorted(expected_series)}, observed {sorted(seen_series)}"
        )
    custody_mode = str(snapshot.get("custody_mode", "TEST_FIXTURE"))
    if custody_mode not in {"LIVE_PROVIDER_RESPONSE", "TEST_FIXTURE"}:
        raise ValueError("snapshot custody_mode is invalid")
    raw_responses = [
        row
        for row in snapshot.get("_raw_source_responses", [])
        if isinstance(row, dict)
    ]
    raw_response_hashes = sorted(
        str(row.get("response_sha256", "")).lower()
        for row in raw_responses
    )
    if any(
        len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
        for value in raw_response_hashes
    ):
        raise ValueError("raw response digest is invalid")
    if len(raw_response_hashes) != len(set(raw_response_hashes)):
        raise ValueError("duplicate raw provider response digest")
    if custody_mode == "LIVE_PROVIDER_RESPONSE":
        response_series = {str(row.get("series_id", "")) for row in raw_responses}
        if response_series != expected_series:
            raise ValueError("live snapshot raw response coverage does not match registered series")
    normalized = {
        "schema": "time_series_source_native_source_snapshot.v2",
        "fetched_at_utc": utc_text(fetched_at),
        "source": source_name,
        "source_contract_id": registered_source["source_contract_id"],
        "custody_mode": custody_mode,
        "request_contract_sha256": str(snapshot.get("request_contract_sha256", "")),
        "source_response_sha256": str(snapshot.get("source_response_sha256", "")),
        "raw_response_sha256s": raw_response_hashes,
        "raw_response_retention_verified": custody_mode == "LIVE_PROVIDER_RESPONSE",
        "series": sorted(normalized_series, key=lambda row: row["series_id"]),
    }
    for field in ("request_contract_sha256", "source_response_sha256"):
        value = normalized[field]
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
            raise ValueError(f"{field} must be a lowercase SHA-256 digest")
        normalized[field] = value.lower()
    normalized["snapshot_sha256"] = canonical_sha256(normalized)
    return normalized


def fetch_json(url: str, timeout: int) -> tuple[dict[str, Any], str, str]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "LumenCore-Prospective-Custody/2.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(20_000_001)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"source request failed: {type(exc).__name__}") from exc
    if len(raw) > 20_000_000:
        raise RuntimeError("source response exceeds frozen size limit")
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("source response is not a JSON object")
    return payload, hashlib.sha256(raw).hexdigest(), raw.decode("utf-8")


def read_environment_key(names: Iterable[str]) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise RuntimeError("required source API key is not available in the process environment")


def fred_realtime_windows(
    observation_start: str,
    *,
    as_of_date: date,
    chunk_days: int,
) -> list[tuple[str, str]]:
    if chunk_days < 1 or chunk_days > 2000:
        raise ValueError("FRED real-time chunk size is outside the provider limit")
    cursor = date.fromisoformat(observation_start)
    if cursor > as_of_date:
        raise ValueError("FRED observation start is after the collection date")
    windows: list[tuple[str, str]] = []
    while cursor <= as_of_date:
        end = min(cursor + timedelta(days=chunk_days - 1), as_of_date)
        terminal = end >= as_of_date
        windows.append(
            (
                cursor.isoformat(),
                "9999-12-31" if terminal else end.isoformat(),
            )
        )
        if terminal:
            break
        cursor = end + timedelta(days=1)
    return windows


def fetch_fred_snapshot(protocol: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    contract = source_contract(protocol, "FRED")
    key = read_environment_key(contract["credential_environment_names"])
    fetched_at = now_utc()
    series_rows: list[dict[str, Any]] = []
    response_hashes: list[dict[str, str]] = []
    raw_responses: list[dict[str, str]] = []
    safe_contracts: list[dict[str, str]] = []
    for series in contract["series"]:
        observations_by_period: dict[str, dict[str, Any]] = {}
        vintage_params = {
            "request_role": "first_available_alfred_vintage",
            "series_id": series["series_id"],
            "file_type": "json",
            "sort_order": "asc",
            "limit": "1",
        }
        safe_contracts.append(vintage_params)
        vintage_request_params = dict(vintage_params)
        vintage_request_params.pop("request_role")
        vintage_request_params["api_key"] = key
        vintage_url = contract["vintage_dates_endpoint"] + "?" + urllib.parse.urlencode(
            vintage_request_params
        )
        try:
            vintage_payload, vintage_sha, vintage_text = fetch_json(vintage_url, timeout)
        except RuntimeError as exc:
            raise RuntimeError(
                f"FRED vintage index request failed for {series['series_id']}"
            ) from exc
        if key in vintage_text:
            raise RuntimeError("FRED vintage index unexpectedly echoed credential material")
        vintage_dates = vintage_payload.get("vintage_dates")
        if not isinstance(vintage_dates, list) or len(vintage_dates) != 1:
            raise RuntimeError("FRED vintage index response is invalid")
        observed_alfred_start = str(vintage_dates[0])
        if observed_alfred_start != series["alfred_initial_release_start"]:
            raise RuntimeError("FRED first available ALFRED vintage changed")
        response_hashes.append(
            {
                "series_id": series["series_id"],
                "response_part": "vintage_index",
                "response_sha256": vintage_sha,
            }
        )
        raw_responses.append(
            {
                "series_id": series["series_id"],
                "response_part": "vintage_index",
                "response_sha256": vintage_sha,
                "response_text": vintage_text,
            }
        )
        windows = fred_realtime_windows(
            series["alfred_initial_release_start"],
            as_of_date=fetched_at.date() - timedelta(days=1),
            chunk_days=int(contract["request_contract"]["realtime_chunk_days"]),
        )
        for part_index, (realtime_start, realtime_end) in enumerate(windows, start=1):
            params = {
                "request_role": "initial_release_observations",
                "series_id": series["series_id"],
                "file_type": "json",
                "output_type": "4",
                "sort_order": "asc",
                "observation_start": series["observation_start"],
                "realtime_start": realtime_start,
                "realtime_end": realtime_end,
            }
            safe_contracts.append(params)
            request_params = dict(params)
            request_params.pop("request_role")
            request_params["api_key"] = key
            url = contract["endpoint"] + "?" + urllib.parse.urlencode(request_params)
            try:
                payload, response_sha, response_text = fetch_json(url, timeout)
            except RuntimeError as exc:
                raise RuntimeError(
                    f"FRED request failed for {series['series_id']} response part {part_index}"
                ) from exc
            if key in response_text:
                raise RuntimeError("FRED response unexpectedly echoed credential material")
            if "error_code" in payload or not isinstance(payload.get("observations"), list):
                raise RuntimeError("FRED returned an invalid observation response")
            if int(payload.get("output_type", -1)) != 4:
                raise RuntimeError("FRED response output type does not match the frozen contract")
            for row in payload["observations"]:
                value = str(row.get("value", "")).strip()
                if not value or value == ".":
                    continue
                observation = {
                    "period": str(row["date"]),
                    "value": finite_number(value),
                    "first_vintage_date": str(row["realtime_start"]),
                }
                existing = observations_by_period.get(observation["period"])
                if existing is not None and existing != observation:
                    raise RuntimeError("FRED initial-release chunks disagree on an observation")
                observations_by_period[observation["period"]] = observation
            response_hashes.append(
                {
                    "series_id": series["series_id"],
                    "response_part": f"initial_release_{part_index:04d}",
                    "response_sha256": response_sha,
                }
            )
            raw_responses.append(
                {
                    "series_id": series["series_id"],
                    "response_part": f"initial_release_{part_index:04d}",
                    "response_sha256": response_sha,
                    "response_text": response_text,
                }
            )
        series_rows.append(
            {
                "series_id": series["series_id"],
                "observations": [
                    observations_by_period[period]
                    for period in sorted(observations_by_period)
                ],
            }
        )
    return {
        "schema": "time_series_source_native_source_snapshot.v2",
        "fetched_at_utc": utc_text(fetched_at),
        "source": "FRED",
        "custody_mode": "LIVE_PROVIDER_RESPONSE",
        "request_contract_sha256": canonical_sha256(safe_contracts),
        "source_response_sha256": canonical_sha256(response_hashes),
        "series": series_rows,
        "_raw_source_responses": raw_responses,
    }


def fetch_twelve_data_snapshot(protocol: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    contract = source_contract(protocol, "TWELVE_DATA")
    key = read_environment_key(contract["credential_environment_names"])
    fetched_at = now_utc()
    supplied_series: list[dict[str, Any]] = []
    response_hashes: list[dict[str, str]] = []
    raw_responses: list[dict[str, str]] = []
    safe_contracts: list[dict[str, str]] = []
    for series in contract["series"]:
        params = {
            "symbol": series["series_id"],
            "interval": "1day",
            "outputsize": str(series["history_request_count"]),
            "order": "asc",
            "format": "JSON",
            "adjust": contract["request_contract"]["adjust"],
        }
        safe_contracts.append(params)
        request_params = dict(params)
        request_params["apikey"] = key
        url = contract["endpoint"] + "?" + urllib.parse.urlencode(request_params)
        payload, response_sha, response_text = fetch_json(url, timeout)
        if key in response_text:
            raise RuntimeError("TWELVE_DATA response unexpectedly echoed credential material")
        if payload.get("status") == "error":
            raise RuntimeError("TWELVE_DATA returned an error response")
        meta = payload.get("meta", {})
        if not isinstance(meta, dict) or meta.get("symbol") != series["series_id"]:
            raise RuntimeError("TWELVE_DATA symbol metadata mismatch")
        if meta.get("interval") != contract["request_contract"]["interval"]:
            raise RuntimeError("TWELVE_DATA interval metadata mismatch")
        if meta.get("exchange_timezone") != contract["exchange_timezone"]:
            raise RuntimeError("TWELVE_DATA exchange timezone metadata mismatch")
        if not isinstance(payload.get("values"), list):
            raise RuntimeError("TWELVE_DATA returned an invalid time-series response")
        observations = [
            {
                "period": str(row["datetime"])[:10],
                "value": finite_number(row["close"]),
            }
            for row in payload.get("values", [])
        ]
        supplied_series.append({"series_id": series["series_id"], "observations": observations})
        response_hashes.append({"series_id": series["series_id"], "response_sha256": response_sha})
        raw_responses.append(
            {
                "series_id": series["series_id"],
                "response_sha256": response_sha,
                "response_text": response_text,
            }
        )
    return {
        "schema": "time_series_source_native_source_snapshot.v2",
        "fetched_at_utc": utc_text(fetched_at),
        "source": "TWELVE_DATA",
        "custody_mode": "LIVE_PROVIDER_RESPONSE",
        "request_contract_sha256": canonical_sha256(safe_contracts),
        "source_response_sha256": canonical_sha256(response_hashes),
        "series": supplied_series,
        "_raw_source_responses": raw_responses,
    }


def load_chain(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.exists():
        return [], ZERO_HASH
    records: list[dict[str, Any]] = []
    prior = ZERO_HASH
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("prior_record_sha256") != prior:
            raise ValueError(f"chain prior hash mismatch at line {line_number}: {path}")
        supplied_hash = record.get("record_sha256")
        unsigned = {key: value for key, value in record.items() if key != "record_sha256"}
        observed_hash = canonical_sha256(unsigned)
        if supplied_hash != observed_hash:
            raise ValueError(f"chain record hash mismatch at line {line_number}: {path}")
        records.append(record)
        prior = supplied_hash
    return records, prior


def append_chain_record(path: Path, payload: dict[str, Any], prior: str) -> dict[str, Any]:
    if "record_sha256" in payload or "prior_record_sha256" in payload:
        raise ValueError("chain metadata is assigned by append_chain_record")
    record = dict(payload)
    record["prior_record_sha256"] = prior
    record["record_sha256"] = canonical_sha256(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return record


def output_paths(out_dir: Path) -> dict[str, Path]:
    return {
        "snapshots": out_dir / "source_snapshots",
        "raw_responses": out_dir / "raw_source_responses",
        "predictions": out_dir / "sealed_predictions.jsonl",
        "settlements": out_dir / "settlements.jsonl",
        "runs": out_dir / "operational_runs.jsonl",
        "anchor_requests": out_dir / "pending_external_anchor_requests",
        "status": out_dir / "prospective_status_latest.json",
        "latest_cycle": out_dir / "latest_cycle.json",
        "lock": out_dir / ".prospective_cycle.lock",
    }


@contextmanager
def cycle_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"prospective cycle already locked: {path}") from exc
    try:
        payload = canonical_json_bytes({"created_at_utc": utc_text(now_utc()), "pid": os.getpid()})
        os.write(descriptor, payload)
        os.close(descriptor)
        descriptor = -1
        yield
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        path.unlink(missing_ok=True)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def persist_snapshot(snapshot: dict[str, Any], directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{snapshot['snapshot_sha256']}.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != snapshot:
            raise ValueError("content-addressed snapshot collision")
        return path
    write_json_atomic(path, snapshot)
    return path


def persist_anchor_request(
    *,
    protocol: dict[str, Any],
    paths: dict[str, Path],
    created_at: datetime,
) -> tuple[dict[str, Any], Path]:
    predictions, prediction_terminal = load_chain(paths["predictions"])
    subject = {
        "protocol_id": protocol["protocol_id"],
        "protocol_payload_sha256": protocol["protocol_payload_sha256"],
        "prediction_terminal_sha256": prediction_terminal,
        "prediction_count": len(predictions),
    }
    payload = {
        "schema": "time_series_source_native_external_anchor_request.v2",
        "created_at_utc": utc_text(created_at),
        **subject,
        "anchor_subject_sha256": canonical_sha256(subject),
        "requested_anchor_property": (
            "independently verifiable timestamp no later than the external receipt time"
        ),
        "external_anchor_state": "PENDING_INDEPENDENT_TIMESTAMP",
        "local_request_is_independent_time_proof": False,
        "primary_scoring_eligible": False,
        "claim_boundary": protocol["claim_boundary"],
    }
    payload["anchor_request_sha256"] = canonical_sha256(payload)
    directory = paths["anchor_requests"]
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{payload['anchor_request_sha256']}.json"
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != payload:
            raise ValueError("content-addressed anchor request collision")
    else:
        write_json_atomic(path, payload)
    return payload, path


def validate_raw_source_responses(responses: list[dict[str, Any]]) -> None:
    for response in responses:
        response_text = str(response.get("response_text", ""))
        expected = str(response.get("response_sha256", "")).lower()
        observed = hashlib.sha256(response_text.encode("utf-8")).hexdigest()
        if expected != observed:
            raise ValueError("raw provider response hash mismatch")


def persist_raw_source_responses(
    responses: list[dict[str, Any]], directory: Path
) -> list[Path]:
    validate_raw_source_responses(responses)
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for response in responses:
        response_text = str(response.get("response_text", ""))
        expected = str(response.get("response_sha256", "")).lower()
        path = directory / f"{expected}.json"
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("content-addressed raw response collision")
        if not path.exists():
            temporary = path.with_name(path.name + ".tmp")
            temporary.write_text(response_text, encoding="utf-8", newline="")
            temporary.replace(path)
        written.append(path)
    return written


def forecast_predictions(
    *,
    model: Any,
    protocol: dict[str, Any],
    source: dict[str, Any],
    series: dict[str, Any],
    history: list[float],
    horizon: int,
) -> dict[str, float]:
    contract = series_contract(source, series["series_id"])
    parameters = {
        "cadence": contract["cadence"],
        "seasonal_period": int(contract["seasonal_period"]),
        "autoregressive_lag": int(contract["autoregressive_lag"]),
    }
    strategies = {strategy.name: strategy for strategy in model.STRATEGIES}
    names = [protocol["candidate"]["registered_family_id"], *protocol["registered_baselines"]]
    missing = [name for name in names if name not in strategies]
    if missing:
        raise ValueError(f"frozen strategy implementation missing: {missing}")
    predictions: dict[str, float] = {}
    decimal_places = int(protocol["forecast_contract"]["prediction_decimal_places"])
    for name in names:
        value = float(model.forecast_strategy(strategies[name], history, horizon, parameters))
        if not math.isfinite(value):
            raise ValueError(f"non-finite forecast: {name}")
        predictions[name] = round(value, decimal_places)
    return predictions


def seal_snapshot(
    *,
    protocol: dict[str, Any],
    snapshot: dict[str, Any],
    predictions_path: Path,
    sealed_at: datetime,
    model: Any,
    dry_run: bool = False,
    allow_test_fixture: bool = False,
) -> dict[str, Any]:
    ensure_custody_admitted(snapshot, allow_test_fixture=allow_test_fixture)
    if parse_utc(snapshot["fetched_at_utc"]) > sealed_at.astimezone(timezone.utc):
        raise ValueError("snapshot fetch time is after seal time")
    if sealed_at.astimezone(timezone.utc) <= parse_utc(protocol["freeze"]["freeze_utc"]):
        raise ValueError("seal must occur after protocol freeze")
    existing, terminal = load_chain(predictions_path)
    existing_keys = {row["prediction_key"] for row in existing}
    source = source_contract(protocol, snapshot["source"])
    new_records: list[dict[str, Any]] = []
    for series in snapshot["series"]:
        observations = series["observations"]
        completeness = origin_completeness_proof(
            snapshot=snapshot,
            source=source,
            observations=observations,
        )
        if not completeness["passed"]:
            raise ValueError(
                f"source origin is not complete at seal: {snapshot['source']}:{series['series_id']}"
            )
        history = [float(row["value"]) for row in observations]
        origin_period = observations[-1]["period"]
        contract = series_contract(source, series["series_id"])
        execution_parameters = {
            "cadence": contract["cadence"],
            "seasonal_period": int(contract["seasonal_period"]),
            "autoregressive_lag": int(contract["autoregressive_lag"]),
            "prediction_decimal_places": int(
                protocol["forecast_contract"]["prediction_decimal_places"]
            ),
        }
        for horizon in contract["horizons"]:
            prediction_key = "|".join(
                [snapshot["source"], series["series_id"], origin_period, str(horizon)]
            )
            if prediction_key in existing_keys:
                continue
            payload = {
                "schema": "time_series_source_native_sealed_prediction.v2",
                "protocol_id": protocol["protocol_id"],
                "protocol_payload_sha256": protocol["protocol_payload_sha256"],
                "protocol_commit": protocol_commit(),
                "prediction_key": prediction_key,
                "source": snapshot["source"],
                "series_id": series["series_id"],
                "cadence": contract["cadence"],
                "origin_period": origin_period,
                "target_definition": "hth_new_source_observation_strictly_after_origin",
                "target_ordinal_after_origin": int(horizon),
                "horizon": int(horizon),
                "sealed_at_utc": utc_text(sealed_at),
                "source_snapshot_sha256": snapshot["snapshot_sha256"],
                "source_snapshot_fetched_at_utc": snapshot["fetched_at_utc"],
                "source_snapshot_custody_mode": snapshot["custody_mode"],
                "origin_completeness_proof": completeness,
                "raw_response_retention_verified": snapshot[
                    "raw_response_retention_verified"
                ],
                "history_count": len(history),
                "history_sha256": canonical_sha256(
                    [{"period": row["period"], "value": row["value"]} for row in observations]
                ),
                "candidate_family_id": protocol["candidate"]["registered_family_id"],
                "candidate_estimator_id": protocol["candidate"]["scientific_estimator_id"],
                "model_file_sha256": protocol["implementation_bindings"][
                    "model_file_sha256"
                ],
                "collector_file_sha256": protocol["implementation_bindings"][
                    "collector_file_sha256"
                ],
                "execution_parameters": execution_parameters,
                "runtime_fingerprint": runtime_fingerprint(model),
                "predictions": forecast_predictions(
                    model=model,
                    protocol=protocol,
                    source=source,
                    series=series,
                    history=history,
                    horizon=int(horizon),
                ),
                "actual_known_at_seal": False,
                "local_chain_seal_status": protocol["ledger_contract"][
                    "local_seal_without_external_anchor_state"
                ],
                "external_anchor_required": True,
                "external_anchor_receipt_sha256": None,
                "primary_scoring_eligible": False,
                "promotion_claim_allowed": False,
                "claim_boundary": protocol["claim_boundary"],
            }
            if dry_run:
                preview = dict(payload)
                preview["prior_record_sha256"] = terminal
                preview["record_sha256"] = canonical_sha256(preview)
                record = preview
            else:
                record = append_chain_record(predictions_path, payload, terminal)
            terminal = record["record_sha256"]
            existing_keys.add(prediction_key)
            new_records.append(record)
    return {
        "sealed_record_count": len(new_records),
        "sealed_prediction_keys": [row["prediction_key"] for row in new_records],
        "prediction_terminal_sha256": terminal,
    }


def release_order_proof(
    prediction: dict[str, Any],
    observation: dict[str, Any],
    source: dict[str, Any],
    *,
    actual_observed_at_utc: str,
) -> dict[str, Any]:
    sealed_at = parse_utc(prediction["sealed_at_utc"])
    observed_at = parse_utc(actual_observed_at_utc)
    if prediction["source"] == "FRED":
        vintage_date = date.fromisoformat(observation["first_vintage_date"])
        conservative_release_boundary = datetime.combine(vintage_date, time.min, tzinfo=timezone.utc)
        passed = sealed_at < conservative_release_boundary
        return {
            "method": "seal_before_first_vintage_date_utc_boundary",
            "sealed_at_utc": utc_text(sealed_at),
            "first_vintage_date": vintage_date.isoformat(),
            "conservative_release_boundary_utc": utc_text(conservative_release_boundary),
            "actual_observed_at_utc": utc_text(observed_at),
            "passed": passed,
        }
    exchange_timezone = ZoneInfo(source["exchange_timezone"])
    target_date = date.fromisoformat(observation["period"])
    sealed_local_date = sealed_at.astimezone(exchange_timezone).date()
    observed_local = observed_at.astimezone(exchange_timezone)
    not_before = time.fromisoformat(
        source["polling_contract"]["not_before_exchange_local_time"]
    )
    prediction_precedes_target = sealed_local_date < target_date
    first_seen_same_session = observed_local.date() == target_date
    observed_after_close_buffer = observed_local.time().replace(tzinfo=None) >= not_before
    passed = (
        prediction_precedes_target
        and first_seen_same_session
        and observed_after_close_buffer
    )
    return {
        "method": "pre_target_seal_and_same_session_post_close_first_seen",
        "sealed_at_utc": utc_text(sealed_at),
        "actual_observed_at_utc": utc_text(observed_at),
        "exchange_timezone": source["exchange_timezone"],
        "sealed_exchange_local_date": sealed_local_date.isoformat(),
        "target_session_date": target_date.isoformat(),
        "observed_exchange_local": observed_local.isoformat(),
        "not_before_exchange_local_time": not_before.isoformat(),
        "prediction_precedes_target": prediction_precedes_target,
        "first_seen_same_session": first_seen_same_session,
        "observed_after_close_buffer": observed_after_close_buffer,
        "passed": passed,
    }


def settle_snapshot(
    *,
    protocol: dict[str, Any],
    snapshot: dict[str, Any],
    predictions_path: Path,
    settlements_path: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    predictions, _ = load_chain(predictions_path)
    settlements, terminal = load_chain(settlements_path)
    settled_prediction_hashes = {row["prediction_record_sha256"] for row in settlements}
    source = source_contract(protocol, snapshot["source"])
    observations_by_series = {
        row["series_id"]: row["observations"] for row in snapshot["series"]
    }
    new_records: list[dict[str, Any]] = []
    skipped_late = 0
    for prediction in predictions:
        if prediction["source"] != snapshot["source"]:
            continue
        if prediction["record_sha256"] in settled_prediction_hashes:
            continue
        future = [
            row
            for row in observations_by_series[prediction["series_id"]]
            if row["period"] > prediction["origin_period"]
        ]
        horizon = int(prediction["target_ordinal_after_origin"])
        if len(future) < horizon:
            continue
        observation = future[horizon - 1]
        ordering = release_order_proof(
            prediction,
            observation,
            source,
            actual_observed_at_utc=snapshot["fetched_at_utc"],
        )
        if not ordering["passed"]:
            skipped_late += 1
            continue
        actual = float(observation["value"])
        metrics = {
            name: {
                "prediction": float(value),
                "absolute_error": round(abs(actual - float(value)), 10),
            }
            for name, value in prediction["predictions"].items()
        }
        payload = {
            "schema": "time_series_source_native_settlement.v2",
            "protocol_id": protocol["protocol_id"],
            "protocol_payload_sha256": protocol["protocol_payload_sha256"],
            "prediction_key": prediction["prediction_key"],
            "prediction_record_sha256": prediction["record_sha256"],
            "source": prediction["source"],
            "series_id": prediction["series_id"],
            "origin_period": prediction["origin_period"],
            "horizon": prediction["horizon"],
            "target_period": observation["period"],
            "actual": actual,
            "actual_source_snapshot_sha256": snapshot["snapshot_sha256"],
            "actual_observed_at_utc": snapshot["fetched_at_utc"],
            "release_order_proof": ordering,
            "strategy_metrics": metrics,
            "primary_inference_run": False,
            "external_anchor_verified": False,
            "primary_scoring_eligible": False,
            "promotion_claim_allowed": False,
            "claim_boundary": protocol["claim_boundary"],
        }
        if prediction["source"] == "FRED":
            payload["first_vintage_date"] = observation["first_vintage_date"]
        if dry_run:
            preview = dict(payload)
            preview["prior_record_sha256"] = terminal
            preview["record_sha256"] = canonical_sha256(preview)
            record = preview
        else:
            record = append_chain_record(settlements_path, payload, terminal)
        terminal = record["record_sha256"]
        settled_prediction_hashes.add(prediction["record_sha256"])
        new_records.append(record)
    return {
        "settled_record_count": len(new_records),
        "settled_prediction_keys": [row["prediction_key"] for row in new_records],
        "late_or_unproven_release_order_skipped_count": skipped_late,
        "settlement_terminal_sha256": terminal,
    }


def validate_cross_chain(predictions: list[dict[str, Any]], settlements: list[dict[str, Any]]) -> None:
    prediction_keys = [row["prediction_key"] for row in predictions]
    if len(prediction_keys) != len(set(prediction_keys)):
        raise ValueError("duplicate prediction key detected")
    prediction_hashes = {row["record_sha256"] for row in predictions}
    settlement_refs = [row["prediction_record_sha256"] for row in settlements]
    if len(settlement_refs) != len(set(settlement_refs)):
        raise ValueError("duplicate settlement detected")
    if any(reference not in prediction_hashes for reference in settlement_refs):
        raise ValueError("settlement references a prediction outside the verified chain")


def build_status(protocol: dict[str, Any], paths: dict[str, Path]) -> dict[str, Any]:
    predictions, prediction_terminal = load_chain(paths["predictions"])
    settlements, settlement_terminal = load_chain(paths["settlements"])
    validate_cross_chain(predictions, settlements)
    settled_hashes = {row["prediction_record_sha256"] for row in settlements}
    unique_observations = {
        (row["source"], row["series_id"], row["target_period"]) for row in settlements
    }
    if not predictions:
        state = "WAITING_FOR_FIRST_SEAL"
    elif not settlements:
        state = "SEALED_AWAITING_FUTURE_OBSERVATIONS"
    else:
        state = "PROSPECTIVE_COLLECTION_ACTIVE"
    counts_by_series: dict[str, dict[str, int]] = {}
    for source in protocol["sources"]:
        for series in source["series"]:
            key = f"{source['source']}:{series['series_id']}"
            counts_by_series[key] = {
                "prediction_count": sum(
                    row["source"] == source["source"] and row["series_id"] == series["series_id"]
                    for row in predictions
                ),
                "settlement_count": sum(
                    row["source"] == source["source"] and row["series_id"] == series["series_id"]
                    for row in settlements
                ),
                "unique_target_period_count": len(
                    {
                        row["target_period"]
                        for row in settlements
                        if row["source"] == source["source"] and row["series_id"] == series["series_id"]
                    }
                ),
            }
    payload = {
        "schema": "time_series_source_native_prospective_status.v2",
        "generated_at_utc": utc_text(now_utc()),
        "protocol_id": protocol["protocol_id"],
        "protocol_payload_sha256": protocol["protocol_payload_sha256"],
        "protocol_commit": protocol_commit(),
        "state": state,
        "prediction_count": len(predictions),
        "settlement_count": len(settlements),
        "unsettled_prediction_count": len(predictions) - len(settled_hashes),
        "eligible_future_observation_count": len(unique_observations),
        "external_anchor_count": 0,
        "pending_external_anchor_request_count": len(
            list(paths["anchor_requests"].glob("*.json"))
        )
        if paths["anchor_requests"].exists()
        else 0,
        "primary_scoring_eligible_prediction_count": 0,
        "prediction_terminal_sha256": prediction_terminal,
        "settlement_terminal_sha256": settlement_terminal,
        "counts_by_series": counts_by_series,
        "sample_gate_ready": False,
        "primary_inference_complete": False,
        "promotion_decision": "INCONCLUSIVE_WAITING_FOR_NEW_SOURCE_ROWS",
        "performance_claim_allowed": False,
        "trading_alpha_claim_allowed": False,
        "field_validation_claim_allowed": False,
        "real_dollar_claim_allowed": False,
        "claim_boundary": protocol["claim_boundary"],
    }
    payload["status_sha256"] = canonical_sha256(payload)
    return payload


def run_cycle(
    *,
    protocol: dict[str, Any],
    snapshots: list[dict[str, Any]],
    out_dir: Path = DEFAULT_OUT_DIR,
    sealed_at: datetime | None = None,
    dry_run: bool = False,
    model: Any | None = None,
    allow_test_fixture: bool = False,
) -> dict[str, Any]:
    paths = output_paths(out_dir)
    model = model or load_model_module()
    cycle_time = sealed_at or now_utc()
    lock_context = cycle_lock(paths["lock"]) if not dry_run else _null_lock()
    with lock_context:
        before_predictions, before_prediction_terminal = load_chain(paths["predictions"])
        before_settlements, before_settlement_terminal = load_chain(paths["settlements"])
        validate_cross_chain(before_predictions, before_settlements)
        prepared: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for supplied in snapshots:
            snapshot = normalize_snapshot(supplied, protocol)
            ensure_custody_admitted(snapshot, allow_test_fixture=allow_test_fixture)
            raw_responses = [
                row
                for row in supplied.get("_raw_source_responses", [])
                if isinstance(row, dict)
            ]
            validate_raw_source_responses(raw_responses)
            settle_snapshot(
                protocol=protocol,
                snapshot=snapshot,
                predictions_path=paths["predictions"],
                settlements_path=paths["settlements"],
                dry_run=True,
            )
            seal_snapshot(
                protocol=protocol,
                snapshot=snapshot,
                predictions_path=paths["predictions"],
                sealed_at=cycle_time,
                model=model,
                dry_run=True,
                allow_test_fixture=allow_test_fixture,
            )
            prepared.append((supplied, snapshot))
        source_results = []
        for supplied, snapshot in prepared:
            snapshot_path = None
            raw_response_paths: list[Path] = []
            if not dry_run:
                raw_response_paths = persist_raw_source_responses(
                    [
                        row
                        for row in supplied.get("_raw_source_responses", [])
                        if isinstance(row, dict)
                    ],
                    paths["raw_responses"],
                )
                snapshot_path = persist_snapshot(snapshot, paths["snapshots"])
            settlement = settle_snapshot(
                protocol=protocol,
                snapshot=snapshot,
                predictions_path=paths["predictions"],
                settlements_path=paths["settlements"],
                dry_run=dry_run,
            )
            seal = seal_snapshot(
                protocol=protocol,
                snapshot=snapshot,
                predictions_path=paths["predictions"],
                sealed_at=cycle_time,
                model=model,
                dry_run=dry_run,
                allow_test_fixture=allow_test_fixture,
            )
            source_results.append(
                {
                    "source": snapshot["source"],
                    "snapshot_sha256": snapshot["snapshot_sha256"],
                    "snapshot_path": str(snapshot_path) if snapshot_path else None,
                    "raw_response_paths": [str(path) for path in raw_response_paths],
                    "settlement": settlement,
                    "seal": seal,
                }
            )
        after_predictions, after_prediction_terminal = load_chain(paths["predictions"])
        after_settlements, after_settlement_terminal = load_chain(paths["settlements"])
        anchor_request = None
        anchor_request_path = None
        if not dry_run and after_prediction_terminal != before_prediction_terminal:
            anchor_request, anchor_request_path = persist_anchor_request(
                protocol=protocol,
                paths=paths,
                created_at=cycle_time,
            )
        status = build_status(protocol, paths) if not dry_run else {
            "state": "DRY_RUN_NO_CUSTODY_MUTATION",
            "performance_claim_allowed": False,
        }
        receipt_payload = {
            "schema": "time_series_source_native_operational_cycle.v2",
            "run_at_utc": utc_text(cycle_time),
            "dry_run": dry_run,
            "protocol_id": protocol["protocol_id"],
            "protocol_payload_sha256": protocol["protocol_payload_sha256"],
            "before": {
                "prediction_count": len(before_predictions),
                "prediction_terminal_sha256": before_prediction_terminal,
                "settlement_count": len(before_settlements),
                "settlement_terminal_sha256": before_settlement_terminal,
            },
            "sources": source_results,
            "external_anchor_request": anchor_request,
            "external_anchor_request_path": (
                str(anchor_request_path) if anchor_request_path else None
            ),
            "after": {
                "prediction_count": len(after_predictions),
                "prediction_terminal_sha256": after_prediction_terminal,
                "settlement_count": len(after_settlements),
                "settlement_terminal_sha256": after_settlement_terminal,
            },
            "performance_claim_allowed": False,
            "claim_boundary": protocol["claim_boundary"],
        }
        operational_record = None
        if not dry_run:
            _, run_terminal = load_chain(paths["runs"])
            operational_record = append_chain_record(paths["runs"], receipt_payload, run_terminal)
            status["operational_record_sha256"] = operational_record["record_sha256"]
            write_json_atomic(paths["status"], status)
            write_json_atomic(
                paths["latest_cycle"],
                {"cycle": receipt_payload, "operational_record": operational_record, "status": status},
            )
        return {
            "cycle": receipt_payload,
            "operational_record": operational_record,
            "status": status,
        }


@contextmanager
def _null_lock() -> Iterator[None]:
    yield


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify", help="Verify the frozen protocol and artifact hashes.")
    status_parser = subparsers.add_parser("status", help="Verify chains and report collection state.")
    status_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    cycle_parser = subparsers.add_parser("cycle", help="Settle prior seals and append new seals.")
    cycle_parser.add_argument("--snapshot", type=Path, action="append", default=[])
    cycle_parser.add_argument("--source", choices=("FRED", "TWELVE_DATA"), action="append", default=[])
    cycle_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    cycle_parser.add_argument("--timeout", type=int, default=60)
    cycle_parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    protocol = load_protocol()
    if args.command == "verify":
        print(
            json.dumps(
                {
                    "protocol_id": protocol["protocol_id"],
                    "protocol_payload_sha256": protocol["protocol_payload_sha256"],
                    "verification_passed": True,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "status":
        print(json.dumps(build_status(protocol, output_paths(args.out_dir)), indent=2, sort_keys=True))
        return 0
    snapshots = [json.loads(path.read_text(encoding="utf-8")) for path in args.snapshot]
    for source in dict.fromkeys(args.source):
        if source == "FRED":
            snapshots.append(fetch_fred_snapshot(protocol, timeout=args.timeout))
        else:
            snapshots.append(fetch_twelve_data_snapshot(protocol, timeout=args.timeout))
    if not snapshots:
        raise SystemExit("cycle requires at least one --snapshot or --source")
    result = run_cycle(protocol=protocol, snapshots=snapshots, out_dir=args.out_dir, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
