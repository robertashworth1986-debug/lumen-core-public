"""V3 prospective source-native collector with independently verifiable custody.

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
import re
import shutil
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
PROTOCOL_PATH = ROOT / "config" / "time_series_source_native_prospective_protocol_v3.json"
MODEL_PATH = ROOT / "code" / "geometry_time_series_model_routing_benchmark.py"
ANALYSIS_PATH = ROOT / "code" / "time_series_source_native_confirmatory_analysis_v3.py"
DEFAULT_OUT_DIR = ROOT / "out" / "time_series_source_native_prospective_v3"
DEFAULT_OPENSSL_CANDIDATES = (
    Path(r"C:\Program Files\Git\usr\bin\openssl.exe"),
    Path(r"C:\Program Files\Git\mingw64\bin\openssl.exe"),
)
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
SAFE_RESPONSE_HEADERS = (
    "content-type",
    "date",
    "etag",
    "last-modified",
    "content-length",
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
    if protocol.get("schema") != "time_series_source_native_prospective_protocol.v3":
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
    if supersession.get("prior_eligible_observation_count") != 0:
        errors.append("supersession_after_observations_forbidden")
    if supersession.get("prior_prediction_count") != 15:
        errors.append("v2_pilot_prediction_count_not_bound")
    if supersession.get("prior_settlement_count") != 0:
        errors.append("v2_pilot_settlement_count_not_zero")
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

    ingress_contract = protocol.get("production_ingress_contract", {})
    if ingress_contract.get("local_file_ingress_to_production_ledger_allowed") is not False:
        errors.append("test_fixture_production_admission_must_be_disabled")
    ledger_contract = protocol.get("ledger_contract", {})
    if ledger_contract.get("external_anchor_required") is not True:
        errors.append("external_anchor_not_required")
    if ledger_contract.get("semantic_preflight_before_append_required") is not True:
        errors.append("semantic_preflight_not_required")
    if ledger_contract.get("immediate_external_anchor_request_required") is not True:
        errors.append("immediate_anchor_request_not_required")
    if ingress_contract.get("production_cli_mode") != "DIRECT_PROVIDER_ONLY":
        errors.append("production_cli_not_direct_provider_only")
    reconstruction_contract = protocol.get("raw_response_reconstruction_contract", {})
    if reconstruction_contract.get(
        "normalized_observations_must_be_reconstructed_from_retained_raw_responses"
    ) is not True:
        errors.append("raw_response_reconstruction_not_required")
    anchor_contract = protocol.get("external_anchor_contract", {})
    if anchor_contract.get("receipt_standard") != "RFC3161":
        errors.append("rfc3161_anchor_not_bound")
    trust = anchor_contract.get("pinned_trust", {})
    for key in ("root_pem_sha256", "tsa_certificate_file_sha256"):
        value = str(trust.get(key, "")).lower()
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            errors.append(f"anchor_trust_hash_invalid:{key}")
    analysis_contract = protocol.get("analysis_contract", {})
    primary_endpoint = protocol.get("primary_endpoint", {})
    if analysis_contract.get("contrast_count") != 16:
        errors.append("analysis_contrast_count_not_16")
    if primary_endpoint.get("bootstrap_replications") != 20000:
        errors.append("analysis_bootstrap_replications_not_bound")
    if primary_endpoint.get("bootstrap_seed") != 2026072901:
        errors.append("analysis_bootstrap_seed_not_bound")

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


def load_analysis_module(path: Path = ANALYSIS_PATH):
    name = "time_series_source_native_confirmatory_analysis_v3"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load frozen analysis implementation: {path}")
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


def period_id_for_target(
    protocol: dict[str, Any], source_name: str, series_id: str, target_period: str
) -> str | None:
    target = date.fromisoformat(target_period)
    source = source_contract(protocol, source_name)
    series = series_contract(source, series_id)
    monthly_fred = (
        source_name == "FRED" and series["cadence"] == "monthly_release_sequence"
    )
    for key in ("first_confirmatory_period", "independent_replication_period"):
        period = protocol["period_contract"][key]
        if monthly_fred:
            start = date.fromisoformat(period["fred_monthly_first_eligible_observation_month"])
            end = date.fromisoformat(period["fred_monthly_last_eligible_observation_month"])
        else:
            start = date.fromisoformat(period["target_period_start_inclusive"])
            end = date.fromisoformat(period["target_period_end_inclusive"])
        if start <= target <= end:
            return str(period["period_id"])
    return None


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


def parse_retained_provider_response(response: dict[str, Any]) -> dict[str, Any]:
    validate_response_metadata(response)
    response_text = str(response.get("response_text", ""))
    expected = str(response.get("response_sha256", "")).lower()
    observed = hashlib.sha256(response_text.encode("utf-8")).hexdigest()
    if expected != observed:
        raise ValueError("raw provider response hash mismatch")
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError("retained provider response is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("retained provider response is not a JSON object")
    return payload


def response_metadata_payload(response: dict[str, Any]) -> dict[str, Any]:
    headers = response.get("response_headers")
    if not isinstance(headers, dict):
        raise ValueError("retained provider response headers are missing")
    normalized_headers = {
        str(key).lower(): str(value)
        for key, value in headers.items()
        if str(key).lower() in SAFE_RESPONSE_HEADERS and str(value)
    }
    if set(normalized_headers) != {str(key).lower() for key in headers}:
        raise ValueError("retained provider response includes an unapproved header")
    return {
        "http_status": int(response.get("http_status", 0)),
        "response_headers": dict(sorted(normalized_headers.items())),
    }


def validate_response_metadata(response: dict[str, Any]) -> None:
    metadata = response_metadata_payload(response)
    if metadata["http_status"] != 200:
        raise ValueError("retained provider response HTTP status is not 200")
    expected = str(response.get("response_metadata_sha256", "")).lower()
    if expected != canonical_sha256(metadata):
        raise ValueError("retained provider response metadata hash mismatch")


def response_receipt(response: dict[str, Any]) -> dict[str, str]:
    validate_response_metadata(response)
    receipt = {
        "series_id": str(response["series_id"]),
        "response_sha256": str(response["response_sha256"]).lower(),
        "response_metadata_sha256": str(response["response_metadata_sha256"]).lower(),
    }
    if response.get("response_part") is not None:
        receipt["response_part"] = str(response["response_part"])
    return receipt


def expected_safe_request_contracts(
    protocol: dict[str, Any], source_name: str, fetched_at: datetime
) -> list[dict[str, str]]:
    contract = source_contract(protocol, source_name)
    contracts: list[dict[str, str]] = []
    if source_name == "FRED":
        for series in contract["series"]:
            contracts.append(
                {
                    "request_role": "first_available_alfred_vintage",
                    "series_id": series["series_id"],
                    "file_type": "json",
                    "sort_order": "asc",
                    "limit": "1",
                }
            )
            windows = fred_realtime_windows(
                series["alfred_initial_release_start"],
                as_of_date=fetched_at.date() - timedelta(days=1),
                chunk_days=int(contract["request_contract"]["realtime_chunk_days"]),
            )
            for realtime_start, realtime_end in windows:
                contracts.append(
                    {
                        "request_role": "initial_release_observations",
                        "series_id": series["series_id"],
                        "file_type": "json",
                        "output_type": "4",
                        "sort_order": "asc",
                        "observation_start": series["observation_start"],
                        "realtime_start": realtime_start,
                        "realtime_end": realtime_end,
                    }
                )
        return contracts
    for series in contract["series"]:
        contracts.append(
            {
                "symbol": series["series_id"],
                "interval": "1day",
                "outputsize": str(series["history_request_count"]),
                "order": "asc",
                "format": "JSON",
                "adjust": contract["request_contract"]["adjust"],
            }
        )
    return contracts


def rebuild_live_series_from_raw(
    snapshot: dict[str, Any], protocol: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    source_name = str(snapshot["source"])
    contract = source_contract(protocol, source_name)
    raw_responses = [
        row for row in snapshot.get("_raw_source_responses", []) if isinstance(row, dict)
    ]
    if not raw_responses:
        raise ValueError("live provider snapshot has no retained raw responses")
    rebuilt: list[dict[str, Any]] = []
    response_receipts: list[dict[str, str]] = []
    for series in contract["series"]:
        series_id = series["series_id"]
        rows = [row for row in raw_responses if str(row.get("series_id", "")) == series_id]
        if not rows:
            raise ValueError(f"missing raw responses for registered series: {series_id}")
        if source_name == "FRED":
            vintage_rows = [row for row in rows if row.get("response_part") == "vintage_index"]
            observation_rows = [
                row
                for row in rows
                if str(row.get("response_part", "")).startswith("initial_release_")
            ]
            if len(vintage_rows) != 1 or not observation_rows:
                raise ValueError(f"incomplete FRED raw response set: {series_id}")
            vintage_payload = parse_retained_provider_response(vintage_rows[0])
            vintage_dates = vintage_payload.get("vintage_dates")
            if vintage_dates != [series["alfred_initial_release_start"]]:
                raise ValueError(f"FRED raw vintage boundary mismatch: {series_id}")
            observations_by_period: dict[str, dict[str, Any]] = {}
            for row in sorted(observation_rows, key=lambda item: str(item["response_part"])):
                payload = parse_retained_provider_response(row)
                if int(payload.get("output_type", -1)) != 4 or not isinstance(
                    payload.get("observations"), list
                ):
                    raise ValueError(f"FRED retained response contract mismatch: {series_id}")
                for provider_row in payload["observations"]:
                    value = str(provider_row.get("value", "")).strip()
                    if not value or value == ".":
                        continue
                    observation = {
                        "period": str(provider_row["date"]),
                        "value": finite_number(value),
                        "first_vintage_date": str(provider_row["realtime_start"]),
                    }
                    date.fromisoformat(observation["period"])
                    date.fromisoformat(observation["first_vintage_date"])
                    existing = observations_by_period.get(observation["period"])
                    if existing is not None and existing != observation:
                        raise ValueError("FRED retained response chunks disagree")
                    observations_by_period[observation["period"]] = observation
            ordered_rows = [vintage_rows[0], *sorted(observation_rows, key=lambda item: str(item["response_part"]))]
            for row in ordered_rows:
                parse_retained_provider_response(row)
                response_receipts.append(response_receipt(row))
            observations = [
                observations_by_period[period] for period in sorted(observations_by_period)
            ]
        else:
            if len(rows) != 1:
                raise ValueError(f"TWELVE_DATA requires one retained response: {series_id}")
            payload = parse_retained_provider_response(rows[0])
            meta = payload.get("meta")
            if (
                not isinstance(meta, dict)
                or meta.get("symbol") != series_id
                or meta.get("interval") != contract["request_contract"]["interval"]
                or meta.get("exchange_timezone") != contract["exchange_timezone"]
                or not isinstance(payload.get("values"), list)
            ):
                raise ValueError(f"TWELVE_DATA retained response contract mismatch: {series_id}")
            observations = [
                {
                    "period": str(provider_row["datetime"])[:10],
                    "value": finite_number(provider_row["close"]),
                }
                for provider_row in payload["values"]
            ]
            observations.sort(key=lambda item: item["period"])
            response_receipts.append(response_receipt(rows[0]))
        rebuilt.append({"series_id": series_id, "observations": observations})
    return rebuilt, response_receipts


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
    if snapshot.get("schema") != "time_series_source_native_source_snapshot.v3":
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
    if raw_responses:
        validate_raw_source_responses(raw_responses)
    raw_response_hashes = sorted(
        hashlib.sha256(str(row.get("response_text", "")).encode("utf-8")).hexdigest()
        for row in raw_responses
    )
    raw_response_metadata_hashes = sorted(
        str(row.get("response_metadata_sha256", "")).lower() for row in raw_responses
    )
    if any(
        len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
        for value in raw_response_hashes
    ):
        raise ValueError("raw response digest is invalid")
    if len(raw_response_hashes) != len(set(raw_response_hashes)):
        raise ValueError("duplicate raw provider response digest")
    if any(
        len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
        for value in raw_response_metadata_hashes
    ):
        raise ValueError("raw response metadata digest is invalid")
    if custody_mode == "LIVE_PROVIDER_RESPONSE":
        response_series = {str(row.get("series_id", "")) for row in raw_responses}
        if response_series != expected_series:
            raise ValueError("live snapshot raw response coverage does not match registered series")
        rebuilt_series, rebuilt_response_receipts = rebuild_live_series_from_raw(
            snapshot, protocol
        )
        supplied_for_comparison = [
            {"series_id": row["series_id"], "observations": row["observations"]}
            for row in sorted(normalized_series, key=lambda item: item["series_id"])
        ]
        rebuilt_for_comparison = sorted(
            rebuilt_series, key=lambda item: item["series_id"]
        )
        if canonical_sha256(supplied_for_comparison) != canonical_sha256(
            rebuilt_for_comparison
        ):
            raise ValueError(
                "normalized observations do not match retained provider responses"
            )
        expected_requests = expected_safe_request_contracts(
            protocol, source_name, fetched_at
        )
        if str(snapshot.get("request_contract_sha256", "")).lower() != canonical_sha256(
            expected_requests
        ):
            raise ValueError("request contract hash is not reproducible from the protocol")
        if str(snapshot.get("source_response_sha256", "")).lower() != canonical_sha256(
            rebuilt_response_receipts
        ):
            raise ValueError("source response hash is not reproducible from retained responses")
    normalized = {
        "schema": "time_series_source_native_source_snapshot.v3",
        "fetched_at_utc": utc_text(fetched_at),
        "source": source_name,
        "source_contract_id": registered_source["source_contract_id"],
        "custody_mode": custody_mode,
        "request_contract_sha256": str(snapshot.get("request_contract_sha256", "")),
        "source_response_sha256": str(snapshot.get("source_response_sha256", "")),
        "raw_response_sha256s": raw_response_hashes,
        "raw_response_metadata_sha256s": raw_response_metadata_hashes,
        "raw_response_retention_verified": custody_mode == "LIVE_PROVIDER_RESPONSE",
        "parser_artifact_path": protocol["implementation_bindings"]["collector_path"],
        "parser_artifact_sha256": protocol["implementation_bindings"][
            "collector_file_sha256"
        ],
        "series": sorted(normalized_series, key=lambda row: row["series_id"]),
    }
    for field in ("request_contract_sha256", "source_response_sha256"):
        value = normalized[field]
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
            raise ValueError(f"{field} must be a lowercase SHA-256 digest")
        normalized[field] = value.lower()
    normalized["snapshot_sha256"] = canonical_sha256(normalized)
    return normalized


def fetch_json(
    url: str, timeout: int
) -> tuple[dict[str, Any], str, str, dict[str, Any]]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "LumenCore-Prospective-Custody/3.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            http_status = int(response.getcode())
            response_headers = {
                name: str(response.headers.get(name))
                for name in SAFE_RESPONSE_HEADERS
                if response.headers.get(name) is not None
            }
            raw = response.read(20_000_001)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"source request failed: {type(exc).__name__}") from exc
    if len(raw) > 20_000_000:
        raise RuntimeError("source response exceeds frozen size limit")
    if http_status != 200:
        raise RuntimeError(f"source response HTTP status is {http_status}")
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("source response is not a JSON object")
    metadata = {
        "http_status": http_status,
        "response_headers": dict(sorted(response_headers.items())),
    }
    return (
        payload,
        hashlib.sha256(raw).hexdigest(),
        raw.decode("utf-8"),
        metadata,
    )


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
            vintage_payload, vintage_sha, vintage_text, vintage_metadata = fetch_json(
                vintage_url, timeout
            )
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
        vintage_response = {
            "series_id": series["series_id"],
            "response_part": "vintage_index",
            "response_sha256": vintage_sha,
            "response_text": vintage_text,
            **vintage_metadata,
            "response_metadata_sha256": canonical_sha256(vintage_metadata),
        }
        raw_responses.append(vintage_response)
        response_hashes.append(response_receipt(vintage_response))
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
                payload, response_sha, response_text, response_metadata = fetch_json(
                    url, timeout
                )
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
            retained_response = {
                "series_id": series["series_id"],
                "response_part": f"initial_release_{part_index:04d}",
                "response_sha256": response_sha,
                "response_text": response_text,
                **response_metadata,
                "response_metadata_sha256": canonical_sha256(response_metadata),
            }
            raw_responses.append(retained_response)
            response_hashes.append(response_receipt(retained_response))
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
        "schema": "time_series_source_native_source_snapshot.v3",
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
        payload, response_sha, response_text, response_metadata = fetch_json(url, timeout)
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
        retained_response = {
            "series_id": series["series_id"],
            "response_sha256": response_sha,
            "response_text": response_text,
            **response_metadata,
            "response_metadata_sha256": canonical_sha256(response_metadata),
        }
        raw_responses.append(retained_response)
        response_hashes.append(response_receipt(retained_response))
    return {
        "schema": "time_series_source_native_source_snapshot.v3",
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
        "anchor_queries": out_dir / "pending_external_anchor_queries",
        "anchor_receipts": out_dir / "verified_external_anchor_receipts",
        "anchor_evidence": out_dir / "external_anchor_evidence",
        "analysis": out_dir / "confirmatory_analysis_latest.json",
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
    anchor_subject_sha256 = canonical_sha256(subject)
    query_directory = paths["anchor_queries"]
    query_directory.mkdir(parents=True, exist_ok=True)
    query_path = query_directory / f"{anchor_subject_sha256}.tsq"
    if not query_path.exists():
        openssl = find_openssl()
        temporary_query = query_path.with_name(query_path.name + ".tmp")
        query_result = subprocess.run(
            [
                str(openssl),
                "ts",
                "-query",
                "-digest",
                anchor_subject_sha256,
                "-sha256",
                "-cert",
                "-no_nonce",
                "-out",
                str(temporary_query),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if query_result.returncode != 0 or not temporary_query.is_file():
            temporary_query.unlink(missing_ok=True)
            raise RuntimeError("unable to build the local RFC3161 timestamp query")
        temporary_query.replace(query_path)
    payload = {
        "schema": "time_series_source_native_external_anchor_request.v3",
        "created_at_utc": utc_text(created_at),
        **subject,
        "anchor_subject_sha256": anchor_subject_sha256,
        "rfc3161_query_filename": query_path.name,
        "rfc3161_query_sha256": file_sha256(query_path),
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


def load_anchor_requests(
    protocol: dict[str, Any], paths: dict[str, Path]
) -> list[dict[str, Any]]:
    if not paths["anchor_requests"].exists():
        return []
    predictions, _ = load_chain(paths["predictions"])
    requests: list[dict[str, Any]] = []
    for request_path in sorted(paths["anchor_requests"].glob("*.json")):
        request = json.loads(request_path.read_text(encoding="utf-8"))
        if not isinstance(request, dict):
            raise ValueError("external anchor request must be a JSON object")
        validate_anchor_request(request, protocol)
        if request_path.stem != request["anchor_request_sha256"]:
            raise ValueError("external anchor request filename hash mismatch")
        query_path = paths["anchor_queries"] / request["rfc3161_query_filename"]
        if not query_path.is_file() or file_sha256(query_path) != request[
            "rfc3161_query_sha256"
        ]:
            raise ValueError("RFC3161 query hash mismatch")
        verify_rfc3161_query(query_path, request["anchor_subject_sha256"])
        count = int(request["prediction_count"])
        if count > len(predictions) or predictions[count - 1]["record_sha256"] != request[
            "prediction_terminal_sha256"
        ]:
            raise ValueError("external anchor request does not match a prediction prefix")
        requests.append(request)
    return requests


def current_terminal_has_anchor_request(
    protocol: dict[str, Any], paths: dict[str, Path], prediction_terminal: str
) -> bool:
    if prediction_terminal == ZERO_HASH:
        return True
    predictions, _ = load_chain(paths["predictions"])
    return any(
        request["prediction_terminal_sha256"] == prediction_terminal
        and int(request["prediction_count"]) == len(predictions)
        for request in load_anchor_requests(protocol, paths)
    )


def find_openssl(explicit: Path | None = None) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    discovered = shutil.which("openssl")
    if discovered:
        candidates.append(Path(discovered))
    candidates.extend(DEFAULT_OPENSSL_CANDIDATES)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise RuntimeError("OpenSSL is required for RFC3161 receipt verification")


def verify_rfc3161_query(query_path: Path, expected_digest: str) -> None:
    openssl = find_openssl()
    decoded = subprocess.run(
        [str(openssl), "ts", "-query", "-in", str(query_path), "-text"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if decoded.returncode != 0:
        raise ValueError("RFC3161 query decoding failed")
    text = decoded.stdout + decoded.stderr
    if not re.search(r"^Hash Algorithm:\s*sha256\s*$", text, flags=re.MULTILINE):
        raise ValueError("RFC3161 query hash algorithm is not SHA-256")
    match = re.search(
        r"^Message data:\s*$\n(?P<body>.*?)(?=^Policy OID:)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise ValueError("RFC3161 query message imprint is missing")
    chunks: list[str] = []
    for line in match.group("body").splitlines():
        _, separator, right = line.partition("-")
        if not separator:
            continue
        hexadecimal = right.split("   ", 1)[0].replace("-", "").replace(" ", "")
        if hexadecimal:
            chunks.append(hexadecimal)
    observed = "".join(chunks).lower()
    if observed != expected_digest.lower():
        raise ValueError("RFC3161 query message imprint mismatch")


def pinned_anchor_paths(protocol: dict[str, Any]) -> tuple[Path, Path]:
    trust = protocol["external_anchor_contract"]["pinned_trust"]
    root_path = (ROOT / str(trust["root_pem_path"])).resolve()
    tsa_path = (ROOT / str(trust["tsa_certificate_path"])).resolve()
    for path in (root_path, tsa_path):
        try:
            path.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise ValueError("pinned TSA material escapes the repository") from exc
        if not path.is_file():
            raise ValueError(f"pinned TSA material is missing: {path.name}")
    if file_sha256(root_path) != str(trust["root_pem_sha256"]).lower():
        raise ValueError("pinned TSA root hash mismatch")
    if file_sha256(tsa_path) != str(trust["tsa_certificate_file_sha256"]).lower():
        raise ValueError("pinned TSA certificate hash mismatch")
    return root_path, tsa_path


def validate_anchor_request(request: dict[str, Any], protocol: dict[str, Any]) -> None:
    supplied_request_hash = str(request.get("anchor_request_sha256", ""))
    unsigned_request = {
        key: value for key, value in request.items() if key != "anchor_request_sha256"
    }
    if supplied_request_hash != canonical_sha256(unsigned_request):
        raise ValueError("external anchor request hash mismatch")
    subject = {
        "protocol_id": request.get("protocol_id"),
        "protocol_payload_sha256": request.get("protocol_payload_sha256"),
        "prediction_terminal_sha256": request.get("prediction_terminal_sha256"),
        "prediction_count": request.get("prediction_count"),
    }
    if request.get("anchor_subject_sha256") != canonical_sha256(subject):
        raise ValueError("external anchor subject hash mismatch")
    if int(subject["prediction_count"] or 0) < 1:
        raise ValueError("external anchor request covers no predictions")
    terminal = str(subject["prediction_terminal_sha256"] or "").lower()
    if len(terminal) != 64 or any(char not in "0123456789abcdef" for char in terminal):
        raise ValueError("external anchor request terminal hash is invalid")
    if subject["protocol_id"] != protocol["protocol_id"] or subject[
        "protocol_payload_sha256"
    ] != protocol["protocol_payload_sha256"]:
        raise ValueError("external anchor request belongs to another protocol")
    if request.get("rfc3161_query_filename") != (
        f"{request['anchor_subject_sha256']}.tsq"
    ):
        raise ValueError("RFC3161 query filename mismatch")


def parse_rfc3161_time(text: str) -> datetime:
    match = re.search(r"^Time stamp:\s*(.+?)\s*$", text, flags=re.MULTILINE)
    if match is None:
        raise ValueError("RFC3161 response does not expose a signed timestamp")
    value = re.sub(r"\s+", " ", match.group(1).strip())
    for format_string in ("%b %d %H:%M:%S %Y GMT", "%b %d %H:%M:%S.%f %Y GMT"):
        try:
            return datetime.strptime(value, format_string).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError("RFC3161 signed timestamp format is unsupported")


def parse_openssl_certificate_time(text: str, field: str) -> datetime:
    match = re.search(rf"^{re.escape(field)}=(.+?)\s*$", text, flags=re.MULTILINE)
    if match is None:
        raise ValueError(f"TSA certificate does not expose {field}")
    value = re.sub(r"\s+", " ", match.group(1).strip())
    for format_string in ("%b %d %H:%M:%S %Y GMT", "%b  %d %H:%M:%S %Y GMT"):
        try:
            return datetime.strptime(value, format_string).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"TSA certificate {field} format is unsupported")


def run_rfc3161_verification(
    *,
    protocol: dict[str, Any],
    anchor_subject_sha256: str,
    response_path: Path,
    openssl_path: Path | None = None,
) -> tuple[datetime, str]:
    root_path, tsa_path = pinned_anchor_paths(protocol)
    openssl = find_openssl(openssl_path)
    verify_command = [
        str(openssl),
        "ts",
        "-verify",
        "-digest",
        anchor_subject_sha256,
        "-in",
        str(response_path),
        "-CAfile",
        str(root_path),
        "-untrusted",
        str(tsa_path),
    ]
    verification = subprocess.run(
        verify_command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if verification.returncode != 0 or "Verification: OK" not in (
        verification.stdout + verification.stderr
    ):
        raise ValueError("RFC3161 signature or message-imprint verification failed")
    decoded = subprocess.run(
        [str(openssl), "ts", "-reply", "-in", str(response_path), "-text"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if decoded.returncode != 0:
        raise ValueError("RFC3161 response decoding failed")
    tsa_time = parse_rfc3161_time(decoded.stdout + decoded.stderr)
    certificate_dates = subprocess.run(
        [str(openssl), "x509", "-in", str(tsa_path), "-noout", "-dates"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if certificate_dates.returncode != 0:
        raise ValueError("TSA certificate validity decoding failed")
    dates_text = certificate_dates.stdout + certificate_dates.stderr
    not_before = parse_openssl_certificate_time(dates_text, "notBefore")
    not_after = parse_openssl_certificate_time(dates_text, "notAfter")
    if not not_before <= tsa_time <= not_after:
        raise ValueError("TSA certificate does not cover the signed timestamp")
    return tsa_time, file_sha256(openssl)


def ingest_rfc3161_anchor_receipt(
    *,
    protocol: dict[str, Any],
    request_path: Path,
    response_path: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
    openssl_path: Path | None = None,
    verified_at: datetime | None = None,
) -> dict[str, Any]:
    request = json.loads(request_path.read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        raise ValueError("external anchor request must be a JSON object")
    validate_anchor_request(request, protocol)
    paths = output_paths(out_dir)
    query_path = paths["anchor_queries"] / request["rfc3161_query_filename"]
    if not query_path.is_file() or file_sha256(query_path) != request[
        "rfc3161_query_sha256"
    ]:
        raise ValueError("RFC3161 query hash mismatch")
    verify_rfc3161_query(query_path, request["anchor_subject_sha256"])
    if not response_path.is_file() or response_path.stat().st_size == 0:
        raise ValueError("RFC3161 response is missing or empty")
    tsa_time, openssl_sha256 = run_rfc3161_verification(
        protocol=protocol,
        anchor_subject_sha256=request["anchor_subject_sha256"],
        response_path=response_path,
        openssl_path=openssl_path,
    )
    evidence_sha256 = file_sha256(response_path)
    evidence_path = paths["anchor_evidence"] / f"{evidence_sha256}.tsr"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    if evidence_path.exists() and file_sha256(evidence_path) != evidence_sha256:
        raise ValueError("RFC3161 evidence collision")
    if not evidence_path.exists():
        temporary = evidence_path.with_name(evidence_path.name + ".tmp")
        temporary.write_bytes(response_path.read_bytes())
        temporary.replace(evidence_path)
    root_path, tsa_path = pinned_anchor_paths(protocol)
    receipt = {
        "schema": "time_series_source_native_external_anchor_receipt.v3",
        "protocol_id": protocol["protocol_id"],
        "protocol_payload_sha256": protocol["protocol_payload_sha256"],
        "anchor_request_sha256": request["anchor_request_sha256"],
        "anchor_subject_sha256": request["anchor_subject_sha256"],
        "prediction_terminal_sha256": request["prediction_terminal_sha256"],
        "prediction_count": int(request["prediction_count"]),
        "receipt_standard": "RFC3161",
        "tsa_signed_time_utc": utc_text(tsa_time),
        "verified_at_utc": utc_text(verified_at or now_utc()),
        "rfc3161_response_path": evidence_path.relative_to(ROOT).as_posix(),
        "rfc3161_response_sha256": evidence_sha256,
        "pinned_root_path": root_path.relative_to(ROOT).as_posix(),
        "pinned_root_sha256": file_sha256(root_path),
        "pinned_tsa_certificate_path": tsa_path.relative_to(ROOT).as_posix(),
        "pinned_tsa_certificate_sha256": file_sha256(tsa_path),
        "openssl_binary_sha256": openssl_sha256,
        "signature_and_message_imprint_verified": True,
        "local_receipt_is_independent_time_proof": False,
        "external_tsa_receipt_is_independent_time_proof": True,
        "primary_scoring_eligibility_requires_pre_target_time": True,
        "claim_boundary": protocol["claim_boundary"],
    }
    receipt["anchor_receipt_sha256"] = canonical_sha256(receipt)
    receipt_path = paths["anchor_receipts"] / f"{receipt['anchor_receipt_sha256']}.json"
    if receipt_path.exists():
        if json.loads(receipt_path.read_text(encoding="utf-8")) != receipt:
            raise ValueError("content-addressed external anchor receipt collision")
    else:
        write_json_atomic(receipt_path, receipt)
    return {**receipt, "anchor_receipt_path": str(receipt_path)}


def load_verified_anchor_receipts(
    protocol: dict[str, Any], paths: dict[str, Path], *, openssl_path: Path | None = None
) -> list[dict[str, Any]]:
    if not paths["anchor_receipts"].exists():
        return []
    requests = {
        request["anchor_request_sha256"]: request
        for request in load_anchor_requests(protocol, paths)
    }
    verified: list[dict[str, Any]] = []
    for receipt_path in sorted(paths["anchor_receipts"].glob("*.json")):
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict):
            raise ValueError("external anchor receipt must be a JSON object")
        supplied_hash = str(receipt.get("anchor_receipt_sha256", ""))
        unsigned = {
            key: value for key, value in receipt.items() if key != "anchor_receipt_sha256"
        }
        if supplied_hash != canonical_sha256(unsigned) or receipt_path.stem != supplied_hash:
            raise ValueError("external anchor receipt hash mismatch")
        request = requests.get(receipt.get("anchor_request_sha256"))
        if request is None:
            raise ValueError("external anchor receipt has no verified request")
        for field in (
            "protocol_id",
            "protocol_payload_sha256",
            "anchor_subject_sha256",
            "prediction_terminal_sha256",
            "prediction_count",
        ):
            if receipt.get(field) != request.get(field):
                raise ValueError(f"external anchor receipt request mismatch: {field}")
        if receipt.get("signature_and_message_imprint_verified") is not True:
            raise ValueError("external anchor receipt verification flag is false")
        evidence_path = (ROOT / str(receipt["rfc3161_response_path"])).resolve()
        if not evidence_path.is_file() or file_sha256(evidence_path) != receipt[
            "rfc3161_response_sha256"
        ]:
            raise ValueError("RFC3161 evidence hash mismatch")
        root_path, tsa_path = pinned_anchor_paths(protocol)
        if receipt.get("pinned_root_sha256") != file_sha256(root_path):
            raise ValueError("external anchor receipt pinned root changed")
        if receipt.get("pinned_tsa_certificate_sha256") != file_sha256(tsa_path):
            raise ValueError("external anchor receipt pinned TSA certificate changed")
        tsa_time, _ = run_rfc3161_verification(
            protocol=protocol,
            anchor_subject_sha256=receipt["anchor_subject_sha256"],
            response_path=evidence_path,
            openssl_path=openssl_path,
        )
        if utc_text(tsa_time) != receipt["tsa_signed_time_utc"]:
            raise ValueError("RFC3161 signed time changed during verification")
        verified.append(receipt)
    return verified


def validate_raw_source_responses(responses: list[dict[str, Any]]) -> None:
    for response in responses:
        validate_response_metadata(response)
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
        metadata_path = directory / f"{expected}.metadata.json"
        metadata_payload = {
            key: value for key, value in response.items() if key != "response_text"
        }
        if metadata_path.exists():
            existing_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if existing_metadata != metadata_payload:
                raise ValueError("content-addressed raw response metadata collision")
        else:
            write_json_atomic(metadata_path, metadata_payload)
        written.extend((path, metadata_path))
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
                [
                    protocol["protocol_id"],
                    snapshot["source"],
                    series["series_id"],
                    origin_period,
                    str(horizon),
                ]
            )
            if prediction_key in existing_keys:
                continue
            payload = {
                "schema": "time_series_source_native_sealed_prediction.v3",
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
    skipped_outside_period = 0
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
        period_id = period_id_for_target(
            protocol,
            prediction["source"],
            prediction["series_id"],
            observation["period"],
        )
        if period_id is None:
            skipped_outside_period += 1
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
            "schema": "time_series_source_native_settlement.v3",
            "protocol_id": protocol["protocol_id"],
            "protocol_payload_sha256": protocol["protocol_payload_sha256"],
            "prediction_key": prediction["prediction_key"],
            "prediction_record_sha256": prediction["record_sha256"],
            "source": prediction["source"],
            "series_id": prediction["series_id"],
            "origin_period": prediction["origin_period"],
            "horizon": prediction["horizon"],
            "target_period": observation["period"],
            "period_id": period_id,
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
        "outside_frozen_period_skipped_count": skipped_outside_period,
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


def verified_anchor_coverage(
    protocol: dict[str, Any],
    paths: dict[str, Path],
    predictions: list[dict[str, Any]],
    settlements: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], set[str]]:
    receipts = load_verified_anchor_receipts(protocol, paths)
    covered: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        count = int(receipt["prediction_count"])
        if count < 1 or count > len(predictions):
            raise ValueError("external anchor receipt prediction count is out of range")
        if predictions[count - 1]["record_sha256"] != receipt[
            "prediction_terminal_sha256"
        ]:
            raise ValueError("external anchor receipt terminal does not match the chain prefix")
        for prediction in predictions[:count]:
            current = covered.get(prediction["record_sha256"])
            if current is None or parse_utc(receipt["tsa_signed_time_utc"]) < parse_utc(
                current["tsa_signed_time_utc"]
            ):
                covered[prediction["record_sha256"]] = receipt

    eligible_settlement_hashes: set[str] = set()
    for settlement in settlements:
        receipt = covered.get(settlement["prediction_record_sha256"])
        if receipt is None:
            continue
        tsa_time = parse_utc(receipt["tsa_signed_time_utc"])
        if settlement["source"] == "FRED":
            target_boundary = parse_utc(
                settlement["release_order_proof"]["conservative_release_boundary_utc"]
            )
        else:
            source = source_contract(protocol, "TWELVE_DATA")
            exchange_timezone = ZoneInfo(source["exchange_timezone"])
            target_date = date.fromisoformat(settlement["target_period"])
            target_boundary = datetime.combine(
                target_date, time.min, tzinfo=exchange_timezone
            ).astimezone(timezone.utc)
        if tsa_time < target_boundary:
            eligible_settlement_hashes.add(settlement["record_sha256"])
    return receipts, covered, eligible_settlement_hashes


def build_analysis_inputs(
    protocol: dict[str, Any], paths: dict[str, Path]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    predictions, _ = load_chain(paths["predictions"])
    settlements, _ = load_chain(paths["settlements"])
    validate_cross_chain(predictions, settlements)
    receipts, covered, _ = verified_anchor_coverage(
        protocol, paths, predictions, settlements
    )
    verified_settlements = []
    for settlement in settlements:
        row = dict(settlement)
        row["verification"] = {
            "chain_record_verified": True,
            "prediction_reference_verified": True,
            "protocol_binding_verified": (
                row.get("protocol_id") == protocol["protocol_id"]
                and row.get("protocol_payload_sha256")
                == protocol["protocol_payload_sha256"]
            ),
        }
        verified_settlements.append(row)

    period_rows = {
        period["period_id"]: [
            row
            for row in settlements
            if row.get("period_id") == period["period_id"]
        ]
        for period in (
            protocol["period_contract"]["first_confirmatory_period"],
            protocol["period_contract"]["independent_replication_period"],
        )
    }
    periods = []
    for period_id, rows in period_rows.items():
        prediction_hashes = {row["prediction_record_sha256"] for row in rows}
        anchors = []
        for receipt in receipts:
            covered_hashes = sorted(
                prediction_hash
                for prediction_hash in prediction_hashes
                if covered.get(prediction_hash, {}).get("anchor_receipt_sha256")
                == receipt["anchor_receipt_sha256"]
            )
            if not covered_hashes:
                continue
            anchors.append(
                {
                    "anchor_receipt_sha256": receipt["anchor_receipt_sha256"],
                    "anchor_subject_sha256": receipt["anchor_subject_sha256"],
                    "anchored_at_utc": receipt["tsa_signed_time_utc"],
                    "covered_prediction_record_sha256": covered_hashes,
                    "verified": True,
                    "independent": True,
                }
            )
        periods.append({"period_id": period_id, "anchors": anchors})
    anchor_coverage = {
        "schema": "time_series_source_native_anchor_coverage.v3",
        "verification_complete": True,
        "analysis_as_of_utc": utc_text(now_utc()),
        "protocol_id": protocol["protocol_id"],
        "protocol_payload_sha256": protocol["protocol_payload_sha256"],
        "periods": periods,
    }
    anchor_coverage["anchor_coverage_sha256"] = canonical_sha256(anchor_coverage)
    return verified_settlements, anchor_coverage


def run_confirmatory_analysis(
    protocol: dict[str, Any], paths: dict[str, Path]
) -> dict[str, Any]:
    analysis = load_analysis_module()
    settlements, anchor_coverage = build_analysis_inputs(protocol, paths)
    report = analysis.analyze_confirmatory(settlements, anchor_coverage, protocol)
    report["analysis_module_path"] = protocol["implementation_bindings"][
        "analysis_path"
    ]
    report["analysis_module_sha256"] = protocol["implementation_bindings"][
        "analysis_file_sha256"
    ]
    report["anchor_coverage_sha256"] = anchor_coverage["anchor_coverage_sha256"]
    report["report_sha256"] = canonical_sha256(report)
    write_json_atomic(paths["analysis"], report)
    return report


def build_status(protocol: dict[str, Any], paths: dict[str, Path]) -> dict[str, Any]:
    predictions, prediction_terminal = load_chain(paths["predictions"])
    settlements, settlement_terminal = load_chain(paths["settlements"])
    validate_cross_chain(predictions, settlements)
    settled_hashes = {row["prediction_record_sha256"] for row in settlements}
    anchor_receipts, anchored_predictions, eligible_settlement_hashes = (
        verified_anchor_coverage(protocol, paths, predictions, settlements)
    )
    eligible_settlements = [
        row for row in settlements if row["record_sha256"] in eligible_settlement_hashes
    ]
    unique_observations = {
        (row["source"], row["series_id"], row["target_period"])
        for row in eligible_settlements
    }
    terminal_anchor_request_present = current_terminal_has_anchor_request(
        protocol, paths, prediction_terminal
    )
    if predictions and not terminal_anchor_request_present:
        state = "INVALID_MISSING_IMMEDIATE_ANCHOR_REQUEST"
    elif not predictions:
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
                        for row in eligible_settlements
                        if row["source"] == source["source"] and row["series_id"] == series["series_id"]
                    }
                ),
            }
    payload = {
        "schema": "time_series_source_native_prospective_status.v3",
        "generated_at_utc": utc_text(now_utc()),
        "protocol_id": protocol["protocol_id"],
        "protocol_payload_sha256": protocol["protocol_payload_sha256"],
        "protocol_commit": protocol_commit(),
        "state": state,
        "prediction_count": len(predictions),
        "settlement_count": len(settlements),
        "unsettled_prediction_count": len(predictions) - len(settled_hashes),
        "eligible_future_observation_count": len(unique_observations),
        "external_anchor_count": len(anchor_receipts),
        "verified_external_anchor_receipt_count": len(anchor_receipts),
        "pending_external_anchor_request_count": max(
            0,
            (
                len(list(paths["anchor_requests"].glob("*.json")))
                if paths["anchor_requests"].exists()
                else 0
            )
            - len({row["anchor_request_sha256"] for row in anchor_receipts}),
        ),
        "externally_anchored_prediction_count": len(anchored_predictions),
        "primary_scoring_eligible_prediction_count": len(
            {
                row["prediction_record_sha256"] for row in eligible_settlements
            }
        ),
        "prediction_terminal_sha256": prediction_terminal,
        "settlement_terminal_sha256": settlement_terminal,
        "terminal_anchor_request_present": terminal_anchor_request_present,
        "counts_by_series": counts_by_series,
        "sample_gate_ready": False,
        "primary_inference_complete": False,
        "promotion_decision": (
            "INVALID_MISSING_IMMEDIATE_ANCHOR_REQUEST"
            if predictions and not terminal_anchor_request_present
            else "INCONCLUSIVE_WAITING_FOR_NEW_SOURCE_ROWS"
        ),
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
        recovered_prior_terminal_anchor_request = None
        if (
            not dry_run
            and before_predictions
            and not current_terminal_has_anchor_request(
                protocol, paths, before_prediction_terminal
            )
        ):
            recovered_prior_terminal_anchor_request, _ = persist_anchor_request(
                protocol=protocol,
                paths=paths,
                created_at=cycle_time,
            )
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
            "schema": "time_series_source_native_operational_cycle.v3",
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
            "recovered_prior_terminal_anchor_request": (
                recovered_prior_terminal_anchor_request
            ),
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
    cycle_parser.add_argument("--source", choices=("FRED", "TWELVE_DATA"), action="append", default=[])
    cycle_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    cycle_parser.add_argument("--timeout", type=int, default=60)
    cycle_parser.add_argument("--dry-run", action="store_true")
    anchor_parser = subparsers.add_parser(
        "verify-anchor", help="Verify and ingest a pinned RFC3161 timestamp receipt."
    )
    anchor_parser.add_argument("--request", type=Path, required=True)
    anchor_parser.add_argument("--response", type=Path, required=True)
    anchor_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    anchor_parser.add_argument("--openssl", type=Path)
    analysis_parser = subparsers.add_parser(
        "analyze", help="Run the frozen analysis only when all custody and sample gates pass."
    )
    analysis_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
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
    if args.command == "verify-anchor":
        result = ingest_rfc3161_anchor_receipt(
            protocol=protocol,
            request_path=args.request,
            response_path=args.response,
            out_dir=args.out_dir,
            openssl_path=args.openssl,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "analyze":
        result = run_confirmatory_analysis(protocol, output_paths(args.out_dir))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    snapshots: list[dict[str, Any]] = []
    for source in dict.fromkeys(args.source):
        if source == "FRED":
            snapshots.append(fetch_fred_snapshot(protocol, timeout=args.timeout))
        else:
            snapshots.append(fetch_twelve_data_snapshot(protocol, timeout=args.timeout))
    if not snapshots:
        raise SystemExit("cycle requires at least one direct-provider --source")
    result = run_cycle(protocol=protocol, snapshots=snapshots, out_dir=args.out_dir, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
