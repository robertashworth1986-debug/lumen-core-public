from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable, Iterable


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
OUT = ROOT / "out"
OUT_OPS = OUT / "ops"
DATA_ROOT = ROOT / "data" / "live_measured"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

ENV_FILES = [
    CONFIG / "luma_live_keys.env",
    ROOT / ".env.live",
    ROOT / ".env.sports",
]

REGISTRY_JSON = CONFIG / "live_source_registry.json"
LIVE_SOURCES_JSON = CONFIG / "live_sources.json"
SOURCE_TRUTH_JSON = OUT / "source_truth_table.json"
OUT_JSON = OUT_OPS / "live_source_measurement_maximizer_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "live_source_measurement_maximizer.json"
OUT_MD = DOCS / "LIVE_SOURCE_MEASUREMENT_MAXIMIZER_2026-06-22.md"
ORCHESTRATOR_POLICY_JSON = CONFIG / "live_source_orchestrator_policy_v1.json"

MAX_HTTP_RESPONSE_BYTES = 2_000_000
POLICY_SCHEMA = "live_source_orchestrator_policy.v1"
RECEIPT_SCHEMA = "live_source_provider_receipt.v1"
ORCHESTRATOR_SCHEMA = "live_source_orchestrator_run.v1"
ORCHESTRATOR_STATE_SCHEMA = "live_source_orchestrator_state.v1"
SNAPSHOT_SCHEMA = "live_source_snapshot.v1"
REGISTRY_ROWS_SCHEMA = "live_source_registry.rows.v1"
REGISTRY_CANONICAL_SCHEMA = "live_source_registry.canonical.v1"
REGISTRY_LEGACY_ROWS_SCHEMA = "live_source_registry.legacy_rows.v0"
REGISTRY_LEGACY_SOURCES_SCHEMA = "live_source_registry.legacy_sources.v0"
REGISTRY_LEGACY_MIRRORED_SCHEMA = "live_source_registry.legacy_mirrored.v0"
SAFE_PROVIDER_ID = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")
SAFE_NAMESPACE = re.compile(r"^live-source/[A-Za-z0-9_.-]+/[a-z0-9_-]+/(cpu|gpu)$")
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
QC_STATES = {
    "PASS",
    "DRY_RUN",
    "EMPTY",
    "UNCONFIGURED",
    "HTTP_REJECTED",
    "RETRYABLE_HTTP",
    "TIMEOUT",
    "MALFORMED_JSON",
    "OVERSIZED_JSON",
    "ADAPTER_ERROR",
    "TRANSPORT_ERROR",
    "CHILD_EXIT",
    "INVALID_RECEIPT",
    "RATE_LIMITED",
}
CIRCUIT_STATES = {"CLOSED", "OPEN", "HALF_OPEN"}

CHILD_ENV_PASSTHROUGH = {
    "APPDATA",
    "COMSPEC",
    "HOME",
    "LANG",
    "LC_ALL",
    "LOCALAPPDATA",
    "NO_PROXY",
    "PATH",
    "PATHEXT",
    "PROGRAMDATA",
    "PYTHONHOME",
    "PYTHONPATH",
    "REQUESTS_CA_BUNDLE",
    "SSL_CERT_FILE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "USERPROFILE",
    "WINDIR",
}


class MalformedJSONError(ValueError):
    pass


class OversizedJSONError(ValueError):
    pass


class ReceiptValidationError(ValueError):
    pass


class PolicyValidationError(ValueError):
    pass


class RegistrySchemaError(ValueError):
    pass


SECTOR_WEIGHT = {
    "broker": 10_000.0,
    "market_data": 10_000.0,
    "rates": 50_000.0,
    "macro": 50_000.0,
    "labor": 25_000.0,
    "demographic": 50_000.0,
    "energy": 125_000.0,
    "air_quality": 40_000.0,
    "weather": 40_000.0,
    "water": 35_000.0,
    "space": 15_000.0,
    "energy_lab": 125_000.0,
    "crypto_market": 10_000.0,
    "sports_market": 8_000.0,
    "federal_opportunity": 20_000.0,
    "internal": 5_000.0,
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def atomic_write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        fields: list[str] = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
        with temporary.open("x", encoding="utf-8", newline="") as handle:
            if fields:
                writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def load_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env

    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        text = raw.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            env[key] = value
    return env


def hydrate_selected_env(env_names: Iterable[str]) -> list[str]:
    selected = {str(name) for name in env_names if str(name)}
    loaded_names: list[str] = []
    for path in ENV_FILES:
        values = load_env_file(path)
        for name in sorted(selected):
            value = values.get(name, "")
            if value and not os.environ.get(name):
                os.environ[name] = value
                loaded_names.append(name)
    return loaded_names


def env_first(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "")
        if value.strip():
            return value.strip()
    return ""


def present_env_names(names: list[str]) -> list[str]:
    return [name for name in names if os.environ.get(name)]


def known_secret_values(env_names: list[str] | None = None) -> list[str]:
    names = set(env_names or [])
    values: list[str] = []
    for name in names:
        value = os.environ.get(name, "")
        if value and len(value) >= 4:
            values.append(value)
    return sorted(set(values), key=lambda value: (-len(value), value))


def build_child_environment(provider_id: str) -> dict[str, str]:
    """Pass only runtime essentials and the selected provider's credentials."""
    if provider_id not in PROVIDER_BY_ID:
        raise ValueError("provider id is not recognized")
    provider_env_names = set(PROVIDER_BY_ID[provider_id].get("env_names", []))
    allowed = CHILD_ENV_PASSTHROUGH | provider_env_names
    child_env = {
        name: value
        for name, value in os.environ.items()
        if name.upper() in allowed and isinstance(value, str)
    }
    child_env["CUDA_VISIBLE_DEVICES"] = ""
    return child_env


def sanitize_text(value: Any, env_names: list[str] | None = None) -> str:
    text = str(value or "")
    for secret in known_secret_values(env_names):
        text = text.replace(secret, "[REDACTED]")
    text = re.sub(
        r"(?i)(api[_-]?key|token|secret|password|email|key)=([^&\s\"']+)",
        r"\1=[REDACTED]",
        text,
    )
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[REDACTED_EMAIL]", text)
    return text[:500]


def scrub(obj: Any, env_names: list[str] | None = None) -> Any:
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            key_text = str(key)
            if re.search(r"(?i)(api[_-]?key|token|secret|password|signature|authorization)", key_text):
                out[key_text] = "[REDACTED]"
            else:
                out[key_text] = scrub(value, env_names)
        return out
    if isinstance(obj, list):
        return [scrub(value, env_names) for value in obj]
    if isinstance(obj, str):
        return sanitize_text(obj, env_names)
    return obj


def sha256_payload(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def seal_receipt(payload: dict[str, Any]) -> dict[str, Any]:
    if "receipt_sha256" in payload:
        raise ReceiptValidationError("receipt payload already contains receipt_sha256")
    sealed = dict(payload)
    sealed["receipt_sha256"] = sha256_payload(payload)
    return sealed


def verify_receipt_hash(receipt: dict[str, Any]) -> bool:
    observed = receipt.get("receipt_sha256")
    if not isinstance(observed, str) or not SHA256_HEX.fullmatch(observed):
        return False
    unsigned = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    return observed == sha256_payload(unsigned)


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def parse_retry_after(value: Any, *, reference_utc: datetime | None = None) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return max(0, int(text))
    except ValueError:
        pass
    try:
        retry_at = parsedate_to_datetime(text)
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        reference = reference_utc or datetime.now(timezone.utc)
        return max(0, int((retry_at.astimezone(timezone.utc) - reference).total_seconds()))
    except (TypeError, ValueError, OverflowError):
        return None


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = 20,
    max_response_bytes: int = MAX_HTTP_RESPONSE_BYTES,
) -> tuple[int | None, Any, str]:
    data = None
    req_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read(max_response_bytes + 1)
        if len(raw) > max_response_bytes:
            raise OversizedJSONError("response exceeded the configured byte limit")
        text = raw.decode("utf-8", errors="strict")
        try:
            payload = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MalformedJSONError("response was not valid UTF-8 JSON") from exc
        return response.getcode(), payload, text


def safe_request(
    source: str,
    env_names: list[str],
    fn: Callable[[], tuple[int | None, list[dict[str, Any]], str]],
) -> dict[str, Any]:
    try:
        http_status, rows, note = fn()
        return {
            "source": source,
            "http_status": http_status,
            "rows": rows,
            "probe_ok": bool(rows),
            "probe_note": sanitize_text(note, env_names),
            "error_kind": None,
            "retry_after_seconds": None,
        }
    except urllib.error.HTTPError as exc:
        headers = getattr(exc, "headers", None)
        retry_after = headers.get("Retry-After") if headers is not None else None
        return {
            "source": source,
            "http_status": getattr(exc, "code", None),
            "rows": [],
            "probe_ok": False,
            "probe_note": f"http_error:{getattr(exc, 'code', 'unknown')}",
            "error_kind": "http_error",
            "retry_after_seconds": parse_retry_after(retry_after),
        }
    except OversizedJSONError:
        return {
            "source": source,
            "http_status": None,
            "rows": [],
            "probe_ok": False,
            "probe_note": "exception:OversizedJSONError",
            "error_kind": "oversized_json",
            "retry_after_seconds": None,
        }
    except (MalformedJSONError, UnicodeDecodeError, json.JSONDecodeError):
        return {
            "source": source,
            "http_status": None,
            "rows": [],
            "probe_ok": False,
            "probe_note": "exception:MalformedJSONError",
            "error_kind": "malformed_json",
            "retry_after_seconds": None,
        }
    except (TimeoutError, socket.timeout):
        return {
            "source": source,
            "http_status": None,
            "rows": [],
            "probe_ok": False,
            "probe_note": "exception:TimeoutError",
            "error_kind": "timeout",
            "retry_after_seconds": None,
        }
    except urllib.error.URLError as exc:
        is_timeout = isinstance(getattr(exc, "reason", None), (TimeoutError, socket.timeout))
        kind = "timeout" if is_timeout else "transport_error"
        return {
            "source": source,
            "http_status": None,
            "rows": [],
            "probe_ok": False,
            "probe_note": f"exception:{'TimeoutError' if is_timeout else 'URLError'}",
            "error_kind": kind,
            "retry_after_seconds": None,
        }
    except Exception as exc:
        return {
            "source": source,
            "http_status": None,
            "rows": [],
            "probe_ok": False,
            "probe_note": sanitize_text(f"exception:{type(exc).__name__}", env_names),
            "error_kind": "adapter_error",
            "retry_after_seconds": None,
        }


def latest_items(values: Any, max_rows: int) -> list[dict[str, Any]]:
    if isinstance(values, list):
        cleaned = [row for row in values if isinstance(row, dict)]
        return cleaned[:max_rows]
    return []


def rows_from_kraken_public(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    url = "https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=60"
    code, obj, _ = request_json(url, timeout=timeout)
    result = obj.get("result", {}) if isinstance(obj, dict) else {}
    key = next((k for k in result if k != "last"), "")
    raw_rows = result.get(key, []) if key else []
    rows = []
    for item in raw_rows[-max_rows:]:
        if isinstance(item, list) and len(item) >= 7:
            rows.append(
                {
                    "pair": key,
                    "time": item[0],
                    "open": item[1],
                    "high": item[2],
                    "low": item[3],
                    "close": item[4],
                    "vwap": item[5],
                    "volume": item[6],
                }
            )
    return code, rows, "kraken_public_ohlc"


def rows_from_binance_public(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit={max_rows}"
    code, obj, _ = request_json(url, timeout=timeout)
    rows = []
    if isinstance(obj, list):
        for item in obj[:max_rows]:
            if isinstance(item, list) and len(item) >= 6:
                rows.append(
                    {
                        "symbol": "BTCUSDT",
                        "open_time": item[0],
                        "open": item[1],
                        "high": item[2],
                        "low": item[3],
                        "close": item[4],
                        "volume": item[5],
                    }
                )
    return code, rows, "binance_public_klines"


def rows_from_coingecko_public(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    url = (
        "https://api.coingecko.com/api/v3/coins/markets"
        "?vs_currency=usd&ids=bitcoin,ethereum,solana,ripple,cardano,dogecoin"
        "&order=market_cap_desc&per_page=10&page=1&sparkline=false"
    )
    code, obj, _ = request_json(url, timeout=timeout)
    rows = latest_items(obj, max_rows)
    return code, rows, "coingecko_public_markets"


def rows_from_finnhub(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    key = env_first("FINNHUB_API_KEY")
    if not key:
        return None, [], "missing_env"
    rows = []
    code: int | None = None
    for symbol in ["AAPL", "MSFT", "NVDA", "SPY"][:max_rows]:
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={urllib.parse.quote(key)}"
        code, obj, _ = request_json(url, timeout=timeout)
        if isinstance(obj, dict) and any(obj.get(k) is not None for k in ("c", "h", "l", "o")):
            row = dict(obj)
            row["symbol"] = symbol
            rows.append(row)
    return code, rows, "finnhub_quotes"


def rows_from_twelve(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    key = env_first("TWELVE_DATA_API_KEY")
    if not key:
        return None, [], "missing_env"
    url = (
        "https://api.twelvedata.com/time_series?"
        f"symbol=AAPL&interval=1day&outputsize={max_rows}&apikey={urllib.parse.quote(key)}"
    )
    code, obj, _ = request_json(url, timeout=timeout)
    values = obj.get("values", []) if isinstance(obj, dict) else []
    rows = latest_items(values, max_rows)
    for row in rows:
        row["symbol"] = "AAPL"
    return code, rows, "twelve_data_time_series"


def rows_from_alpha(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    key = env_first("ALPHAVANTAGE_API_KEY")
    if not key:
        return None, [], "missing_env"
    url = (
        "https://www.alphavantage.co/query?"
        f"function=FX_DAILY&from_symbol=EUR&to_symbol=USD&outputsize=compact&apikey={urllib.parse.quote(key)}"
    )
    code, obj, _ = request_json(url, timeout=timeout)
    series = obj.get("Time Series FX (Daily)", {}) if isinstance(obj, dict) else {}
    rows = []
    if isinstance(series, dict):
        for date, values in list(series.items())[:max_rows]:
            if isinstance(values, dict):
                row = {"date": date, "pair": "EURUSD"}
                row.update(values)
                rows.append(row)
    return code, rows, "alphavantage_fx_daily"


def rows_from_massive(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    key = env_first("MASSIVE_API_KEY", "POLYGON_API_KEY")
    if not key:
        return None, [], "missing_env"
    rows = []
    code: int | None = None
    for symbol in ["SPY", "QQQ", "NVDA"][:max_rows]:
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?adjusted=true&apiKey={urllib.parse.quote(key)}"
        code, obj, _ = request_json(url, timeout=timeout)
        values = obj.get("results", []) if isinstance(obj, dict) else []
        for row in latest_items(values, 1):
            row["symbol"] = symbol
            rows.append(row)
    return code, rows, "polygon_prev_aggs"


def rows_from_fred(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    key = env_first("FRED_API_KEY")
    if not key:
        return None, [], "missing_env"
    rows = []
    code: int | None = None
    per_series = max(1, max_rows // 4)
    for series in ["DGS10", "DGS2", "UNRATE", "CPIAUCSL"]:
        url = (
            "https://api.stlouisfed.org/fred/series/observations?"
            f"series_id={series}&api_key={urllib.parse.quote(key)}&file_type=json&limit={per_series}"
        )
        code, obj, _ = request_json(url, timeout=timeout)
        observations = obj.get("observations", []) if isinstance(obj, dict) else []
        for row in latest_items(observations, per_series):
            row["series_id"] = series
            rows.append(row)
    return code, rows[:max_rows], "fred_observations"


def rows_from_eia(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    key = env_first("EIA_API_KEY", "EIA_API_KEY_PREMIUM")
    if not key:
        return None, [], "missing_env"
    url = (
        "https://api.eia.gov/v2/electricity/rto/daily-region-data/data/?"
        f"api_key={urllib.parse.quote(key)}&frequency=daily&data[0]=value&"
        "sort[0][column]=period&sort[0][direction]=desc&"
        f"length={max_rows}"
    )
    code, obj, _ = request_json(url, timeout=timeout)
    response = obj.get("response", {}) if isinstance(obj, dict) else {}
    rows = latest_items(response.get("data", []), max_rows) if isinstance(response, dict) else []
    return code, rows, "eia_daily_region_data"


def rows_from_bls(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    key = env_first("BLS_API_KEY")
    if not key:
        return None, [], "missing_env"
    payload = {
        "seriesid": ["LNS14000000"],
        "startyear": "2024",
        "endyear": "2026",
        "registrationkey": key,
    }
    req = urllib.request.Request(
        "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        code = response.getcode()
        obj = json.loads(response.read().decode("utf-8", errors="ignore"))
    results = obj.get("Results", {}) if isinstance(obj, dict) else {}
    series = results.get("series", []) if isinstance(results, dict) else []
    data = series[0].get("data", []) if series and isinstance(series[0], dict) else []
    rows = latest_items(data, max_rows)
    for row in rows:
        row["series_id"] = "LNS14000000"
    return code, rows, "bls_unemployment_series"


def rows_from_nasa(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    key = env_first("NASA_API_KEY")
    if key:
        try:
            url = f"https://api.nasa.gov/planetary/apod?api_key={urllib.parse.quote(key)}"
            code, obj, _ = request_json(url, timeout=timeout)
            row = obj if isinstance(obj, dict) else {}
            if row:
                return code, [row], "nasa_apod"
        except Exception:
            pass

    # NASA POWER is a durable open fallback for environmental context when APOD is slow.
    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point?"
        "parameters=T2M,WS10M&community=RE&longitude=-86.7816&latitude=36.1627"
        "&start=20260601&end=20260607&format=JSON"
    )
    code, obj, _ = request_json(url, timeout=timeout)
    properties = obj.get("properties", {}) if isinstance(obj, dict) else {}
    parameter = properties.get("parameter", {}) if isinstance(properties, dict) else {}
    rows: list[dict[str, Any]] = []
    for name, series in parameter.items() if isinstance(parameter, dict) else []:
        if not isinstance(series, dict):
            continue
        for period, value in list(series.items())[:max_rows]:
            rows.append({"parameter": name, "period": period, "value": value})
    return code, rows[:max_rows], "nasa_power_daily_point"


def rows_from_noaa(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    key = env_first("NOAA_API_TOKEN", "NOAA_NCEI_TOKEN", "NCDC_NOAA_API_TOKEN")
    if not key:
        return None, [], "missing_env"
    code, obj, _ = request_json(
        f"https://www.ncei.noaa.gov/cdo-web/api/v2/datasets?limit={max_rows}",
        headers={"token": key},
        timeout=timeout,
    )
    rows = latest_items(obj.get("results", []) if isinstance(obj, dict) else [], max_rows)
    return code, rows, "noaa_datasets"


def rows_from_nrel(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    key = env_first("NREL_API_KEY")
    if not key:
        return None, [], "missing_env"
    url = (
        "https://developer.nrel.gov/api/alt-fuel-stations/v1/nearest.json?"
        f"api_key={urllib.parse.quote(key)}&latitude=36.1627&longitude=-86.7816&limit={max_rows}"
    )
    code, obj, _ = request_json(url, timeout=timeout)
    rows = latest_items(obj.get("fuel_stations", []) if isinstance(obj, dict) else [], max_rows)
    return code, rows, "nrel_alt_fuel_stations"


def rows_from_usgs(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    url = "https://waterservices.usgs.gov/nwis/iv/?format=json&sites=01646500&parameterCd=00060"
    code, obj, _ = request_json(url, timeout=timeout)
    value = obj.get("value", {}) if isinstance(obj, dict) else {}
    rows = latest_items(value.get("timeSeries", []) if isinstance(value, dict) else [], max_rows)
    return code, rows, "usgs_water_iv"


def rows_from_census(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    key = env_first("CENSUS_API_KEY")
    if not key:
        return None, [], "missing_env"
    url = f"https://api.census.gov/data/2023/acs/acs1?get=NAME,B01001_001E&for=us:1&key={urllib.parse.quote(key)}"
    code, obj, _ = request_json(url, timeout=timeout)
    rows = []
    if isinstance(obj, list) and len(obj) >= 2:
        headers = obj[0]
        for values in obj[1 : max_rows + 1]:
            if isinstance(headers, list) and isinstance(values, list):
                rows.append(dict(zip(headers, values)))
    return code, rows, "census_acs"


def rows_from_bea(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    key = env_first("BEA_API_KEY")
    if not key:
        return None, [], "missing_env"
    url = f"https://apps.bea.gov/api/data?UserID={urllib.parse.quote(key)}&method=GETDATASETLIST&ResultFormat=json"
    code, obj, _ = request_json(url, timeout=timeout)
    beaapi = obj.get("BEAAPI", {}) if isinstance(obj, dict) else {}
    results = beaapi.get("Results", {}) if isinstance(beaapi, dict) else {}
    rows = latest_items(results.get("Dataset", []) if isinstance(results, dict) else [], max_rows)
    return code, rows, "bea_dataset_list"


def rows_from_epa_aqs(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    key = env_first("EPA_AQS_KEY", "AQS_API_TOKEN")
    email = env_first("EPA_AQS_EMAIL")
    if not (key and email):
        return None, [], "missing_env"
    url = (
        "https://aqs.epa.gov/data/api/list/states?"
        f"email={urllib.parse.quote(email)}&key={urllib.parse.quote(key)}"
    )
    code, obj, _ = request_json(url, timeout=timeout)
    rows = latest_items(obj.get("Data", []) if isinstance(obj, dict) else [], max_rows)
    return code, rows, "epa_aqs_states"


def rows_from_airnow(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    key = env_first("AIRNOW_API_KEY")
    if not key:
        return None, [], "missing_env"
    base = "https://www.airnowapi.org/aq/observation/zipCode/current/"
    query = urllib.parse.urlencode(
        {
            "format": "application/json",
            "zipCode": "37214",
            "distance": "25",
            "API_KEY": key,
        }
    )
    code, obj, _ = request_json(f"{base}?{query}", timeout=timeout)
    rows = latest_items(obj, max_rows)
    for row in rows:
        row["zipCode"] = "37214"
        row["distance_miles"] = 25
        row["source_endpoint"] = "airnow_zip_current"
    return code, rows, "airnow_zip_current"


def rows_from_sports_odds(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    key = env_first("THEODDS_API_KEY", "ODDS_API_KEY", "SPORTS_ODDS_API_KEY")
    if not key:
        return None, [], "missing_env"
    url = f"https://api.the-odds-api.com/v4/sports?apiKey={urllib.parse.quote(key)}"
    code, obj, _ = request_json(url, timeout=timeout)
    rows = latest_items(obj, max_rows)
    return code, rows, "the_odds_api_sports"


def rows_from_sam_gov(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    key = env_first("SAM_API_KEY", "SAM_GOV_API_KEY")
    if not key:
        return None, [], "missing_env"
    today = datetime.now(timezone.utc).strftime("%m/%d/%Y")
    url = (
        "https://api.sam.gov/opportunities/v2/search?"
        f"limit={max_rows}&postedFrom=01/01/2026&postedTo={today}&api_key={urllib.parse.quote(key)}"
    )
    code, obj, _ = request_json(url, timeout=timeout)
    rows = latest_items(obj.get("opportunitiesData", []) if isinstance(obj, dict) else [], max_rows)
    return code, rows, "sam_opportunity_search"


def rows_from_grants_gov(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    body = {
        "rows": max_rows,
        "startRecordNum": 0,
        "keyword": "artificial intelligence",
        "oppStatuses": "posted|forecasted",
        "sortBy": "closeDate|asc",
    }
    code, obj, _ = request_json(
        "https://api.grants.gov/v1/api/search2",
        method="POST",
        body=body,
        timeout=timeout,
    )
    data = obj.get("data", {}) if isinstance(obj, dict) else {}
    rows = latest_items(data.get("oppHits", []) if isinstance(data, dict) else [], max_rows)
    return code, rows, "grants_gov_search2"


def rows_from_webhook(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    secret = env_first("WEBHOOK_SHARED_SECRET")
    if not secret:
        return None, [], "missing_env"
    return None, [{"configured": True, "secret_present": True}], "internal_webhook_secret_present"


def rows_from_nws(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    url = "https://api.weather.gov/gridpoints/OHX/50,57/forecast/hourly"
    code, obj, _ = request_json(
        url,
        headers={"User-Agent": "LumenCore evidence replay contact: robertashworth4444@gmail.com"},
        timeout=timeout,
    )
    properties = obj.get("properties", {}) if isinstance(obj, dict) else {}
    rows = latest_items(properties.get("periods", []) if isinstance(properties, dict) else [], max_rows)
    return code, rows, "nws_hourly_forecast_nashville"


def rows_from_open_meteo(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        "latitude=36.1627&longitude=-86.7816&hourly=temperature_2m,wind_speed_10m,relative_humidity_2m"
        "&forecast_days=2"
    )
    code, obj, _ = request_json(url, timeout=timeout)
    hourly = obj.get("hourly", {}) if isinstance(obj, dict) else {}
    times = hourly.get("time", []) if isinstance(hourly, dict) else []
    rows: list[dict[str, Any]] = []
    for idx, ts in enumerate(times[:max_rows]):
        row = {"time": ts}
        for key, values in hourly.items():
            if key == "time" or not isinstance(values, list) or idx >= len(values):
                continue
            row[key] = values[idx]
        rows.append(row)
    return code, rows, "open_meteo_hourly_forecast"


def rows_from_treasury_fiscal(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    url = (
        "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/avg_interest_rates?"
        f"sort=-record_date&page[size]={max_rows}"
    )
    code, obj, _ = request_json(url, timeout=timeout)
    rows = latest_items(obj.get("data", []) if isinstance(obj, dict) else [], max_rows)
    return code, rows, "treasury_average_interest_rates"


def rows_from_sec_public(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    code, obj, _ = request_json(
        "https://www.sec.gov/files/company_tickers.json",
        headers={"User-Agent": "LumenCore evidence replay contact: robertashworth4444@gmail.com"},
        timeout=timeout,
    )
    rows: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        for value in list(obj.values())[:max_rows]:
            if isinstance(value, dict):
                rows.append(value)
    return code, rows, "sec_company_tickers"


def rows_from_coinbase_public(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    code, obj, _ = request_json("https://api.coinbase.com/v2/exchange-rates?currency=BTC", timeout=timeout)
    data = obj.get("data", {}) if isinstance(obj, dict) else {}
    rates = data.get("rates", {}) if isinstance(data, dict) else {}
    rows = [{"currency": key, "btc_rate": value} for key, value in list(rates.items())[:max_rows]]
    return code, rows, "coinbase_btc_exchange_rates"


def rows_from_world_bank(max_rows: int, timeout: int) -> tuple[int | None, list[dict[str, Any]], str]:
    url = "https://api.worldbank.org/v2/country/USA?format=json"
    code, obj, _ = request_json(url, timeout=timeout)
    rows = latest_items(obj[1] if isinstance(obj, list) and len(obj) > 1 else [], max_rows)
    return code, rows, "world_bank_us_country_metadata"


PROVIDERS: list[dict[str, Any]] = [
    {
        "source": "KRAKEN_PUBLIC",
        "sector": "crypto_market",
        "env_names": [],
        "constraint_type": "public crypto price and liquidity context",
        "money_drain_mode": "stale market context and weak replay calibration",
        "collector": rows_from_kraken_public,
    },
    {
        "source": "BINANCE_PUBLIC",
        "sector": "crypto_market",
        "env_names": [],
        "constraint_type": "public crypto cross-venue market context",
        "money_drain_mode": "venue-specific blind spots and weak market breadth",
        "collector": rows_from_binance_public,
    },
    {
        "source": "COINGECKO_PUBLIC",
        "sector": "crypto_market",
        "env_names": [],
        "constraint_type": "crypto asset breadth and market-cap context",
        "money_drain_mode": "asset universe blind spots",
        "collector": rows_from_coingecko_public,
    },
    {
        "source": "FINNHUB",
        "sector": "market_data",
        "env_names": ["FINNHUB_API_KEY"],
        "constraint_type": "equity price discovery / event latency / symbol coverage",
        "money_drain_mode": "bad entries, bad exits, stale market context",
        "collector": rows_from_finnhub,
    },
    {
        "source": "ALPHAVANTAGE",
        "sector": "market_data",
        "env_names": ["ALPHAVANTAGE_API_KEY"],
        "constraint_type": "market regime context / time series coverage",
        "money_drain_mode": "weak ranking inputs, stale comparative context",
        "collector": rows_from_alpha,
    },
    {
        "source": "TWELVE_DATA",
        "sector": "market_data",
        "env_names": ["TWELVE_DATA_API_KEY"],
        "constraint_type": "cross-asset live price context",
        "money_drain_mode": "low-quality selection and delayed reaction",
        "collector": rows_from_twelve,
    },
    {
        "source": "MASSIVE",
        "sector": "market_data",
        "env_names": ["MASSIVE_API_KEY", "POLYGON_API_KEY"],
        "constraint_type": "broad market event and price context",
        "money_drain_mode": "missed structure, stale inputs",
        "collector": rows_from_massive,
    },
    {
        "source": "FRED",
        "sector": "rates",
        "env_names": ["FRED_API_KEY"],
        "constraint_type": "rates / macro liquidity drift",
        "money_drain_mode": "bad macro positioning and wrong risk posture",
        "collector": rows_from_fred,
    },
    {
        "source": "EIA",
        "sector": "energy",
        "env_names": ["EIA_API_KEY", "EIA_API_KEY_PREMIUM"],
        "constraint_type": "energy throughput / outage / supply drift",
        "money_drain_mode": "energy misread, outage blind spots, capacity drift",
        "collector": rows_from_eia,
    },
    {
        "source": "BLS",
        "sector": "labor",
        "env_names": ["BLS_API_KEY"],
        "constraint_type": "labor pressure / unemployment drift",
        "money_drain_mode": "macro labor blind spots",
        "collector": rows_from_bls,
    },
    {
        "source": "NASA",
        "sector": "space",
        "env_names": ["NASA_API_KEY"],
        "constraint_type": "space-weather / environmental externalities",
        "money_drain_mode": "environmental blind spots affecting operations",
        "collector": rows_from_nasa,
    },
    {
        "source": "NOAA_NCEI",
        "sector": "weather",
        "env_names": ["NOAA_API_TOKEN", "NOAA_NCEI_TOKEN", "NCDC_NOAA_API_TOKEN"],
        "constraint_type": "weather / climate disruption",
        "money_drain_mode": "weather-driven loss, outage, scheduling drift",
        "collector": rows_from_noaa,
    },
    {
        "source": "NWS_PUBLIC",
        "sector": "weather",
        "env_names": [],
        "constraint_type": "near-term public weather forecast stress",
        "money_drain_mode": "weather-driven operational blind spots and poor timing windows",
        "collector": rows_from_nws,
    },
    {
        "source": "OPEN_METEO_PUBLIC",
        "sector": "weather",
        "env_names": [],
        "constraint_type": "open weather forecast comparison lane",
        "money_drain_mode": "single-provider weather dependence and missed cross-checks",
        "collector": rows_from_open_meteo,
    },
    {
        "source": "NREL",
        "sector": "energy_lab",
        "env_names": ["NREL_API_KEY"],
        "constraint_type": "renewables / grid / energy lab context",
        "money_drain_mode": "energy planning blind spots",
        "collector": rows_from_nrel,
    },
    {
        "source": "USGS_WATER",
        "sector": "water",
        "env_names": ["USGS_WATER_API_KEY"],
        "constraint_type": "hydrology / water availability / flow disruption",
        "money_drain_mode": "water-side operational blind spots",
        "collector": rows_from_usgs,
    },
    {
        "source": "CENSUS",
        "sector": "demographic",
        "env_names": ["CENSUS_API_KEY"],
        "constraint_type": "population / regional demand drift",
        "money_drain_mode": "wrong location assumptions and demand misread",
        "collector": rows_from_census,
    },
    {
        "source": "BEA",
        "sector": "macro",
        "env_names": ["BEA_API_KEY"],
        "constraint_type": "GDP / income / macro growth drift",
        "money_drain_mode": "macro misallocation",
        "collector": rows_from_bea,
    },
    {
        "source": "EPA_AQS",
        "sector": "air_quality",
        "env_names": ["EPA_AQS_KEY", "EPA_AQS_EMAIL", "AQS_API_TOKEN"],
        "constraint_type": "air quality / environmental stress",
        "money_drain_mode": "air-quality-related operational degradation",
        "collector": rows_from_epa_aqs,
    },
    {
        "source": "AIRNOW",
        "sector": "air_quality",
        "env_names": ["AIRNOW_API_KEY"],
        "constraint_type": "near-real-time air quality and particle pollution stress",
        "money_drain_mode": "air-quality-driven operational blind spots, public-health timing, and environmental stress drift",
        "collector": rows_from_airnow,
    },
    {
        "source": "THE_ODDS_API",
        "sector": "sports_market",
        "env_names": ["THEODDS_API_KEY", "ODDS_API_KEY", "SPORTS_ODDS_API_KEY"],
        "constraint_type": "sports market calibration and live odds breadth",
        "money_drain_mode": "stale odds context and poor paper-market calibration",
        "collector": rows_from_sports_odds,
    },
    {
        "source": "SAM_GOV",
        "sector": "federal_opportunity",
        "env_names": ["SAM_API_KEY", "SAM_GOV_API_KEY"],
        "constraint_type": "near-term federal opportunity discovery",
        "money_drain_mode": "missed bid windows and late capture",
        "collector": rows_from_sam_gov,
    },
    {
        "source": "GRANTS_GOV",
        "sector": "federal_opportunity",
        "env_names": [],
        "constraint_type": "federal grant opportunity discovery",
        "money_drain_mode": "missed grant windows and weak deadline triage",
        "collector": rows_from_grants_gov,
    },
    {
        "source": "WEBHOOK",
        "sector": "internal",
        "env_names": ["WEBHOOK_SHARED_SECRET"],
        "constraint_type": "signal/event ingress",
        "money_drain_mode": "dropped internal triggers and missed event flow",
        "collector": rows_from_webhook,
    },
    {
        "source": "TREASURY_FISCAL_PUBLIC",
        "sector": "rates",
        "env_names": [],
        "constraint_type": "public federal rate and debt-cost context",
        "money_drain_mode": "rate-pressure blind spots and weak macro conversion assumptions",
        "collector": rows_from_treasury_fiscal,
    },
    {
        "source": "SEC_PUBLIC",
        "sector": "market_data",
        "env_names": [],
        "constraint_type": "public company universe context",
        "money_drain_mode": "weak issuer universe and poor public-market context",
        "collector": rows_from_sec_public,
    },
    {
        "source": "COINBASE_PUBLIC",
        "sector": "crypto_market",
        "env_names": [],
        "constraint_type": "public crypto reference-rate context",
        "money_drain_mode": "single-exchange crypto reference dependence",
        "collector": rows_from_coinbase_public,
    },
    {
        "source": "WORLD_BANK_PUBLIC",
        "sector": "macro",
        "env_names": [],
        "constraint_type": "global macro and economic scale context",
        "money_drain_mode": "weak macro normalization and sector-size context",
        "collector": rows_from_world_bank,
    },
]


def build_provider_catalog() -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for provider in PROVIDERS:
        provider_id = str(provider.get("source") or "")
        if not SAFE_PROVIDER_ID.fullmatch(provider_id):
            raise RuntimeError("provider catalog contains an invalid provider id")
        if provider_id in catalog:
            raise RuntimeError("provider catalog contains a duplicate provider id")
        if not callable(provider.get("collector")):
            raise RuntimeError("provider catalog contains a non-callable collector")
        catalog[provider_id] = provider
    return catalog


PROVIDER_BY_ID = build_provider_catalog()

POLICY_LIMITS = {
    "max_concurrency": (1, 16),
    "child_timeout_seconds": (1, 300),
    "request_timeout_seconds": (1, 120),
    "max_retries": (0, 5),
    "retry_base_seconds": (0, 60),
    "max_retry_delay_seconds": (0, 300),
    "default_rate_limit_seconds": (1, 86_400),
    "circuit_breaker_failures": (1, 20),
    "max_rows": (1, 1_000),
    "max_child_output_bytes": (512, 1_000_000),
}


def _strict_int(value: Any, *, name: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise PolicyValidationError(f"{name} must be an integer in [{low}, {high}]")
    return value


def _safe_runtime_state_path(value: Any) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise PolicyValidationError("state_path must be a forward-slash relative path")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts or relative.parts[0] != "run":
        raise PolicyValidationError("state_path must remain under run/")
    resolved = (ROOT / relative).resolve()
    run_root = (ROOT / "run").resolve()
    if resolved != run_root and run_root not in resolved.parents:
        raise PolicyValidationError("state_path escaped run/")
    return resolved


def load_orchestrator_policy(path: Path = ORCHESTRATOR_POLICY_JSON) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PolicyValidationError("orchestrator policy could not be read") from exc
    if not isinstance(payload, dict):
        raise PolicyValidationError("orchestrator policy must be an object")

    expected_keys = {
        "schema",
        "provider_allowlist",
        "limits",
        "state_path",
        "execution_default",
        "network_default",
        "publish_outputs_default",
    }
    if set(payload) != expected_keys:
        raise PolicyValidationError("orchestrator policy fields do not match the v1 schema")
    if payload.get("schema") != POLICY_SCHEMA:
        raise PolicyValidationError("orchestrator policy schema is unsupported")
    if payload.get("execution_default") != "dry_run":
        raise PolicyValidationError("orchestrator policy must default to dry_run")
    if payload.get("network_default") is not False or payload.get("publish_outputs_default") is not False:
        raise PolicyValidationError("network and output publication must default to false")

    raw_allowlist = payload.get("provider_allowlist")
    if not isinstance(raw_allowlist, list) or not raw_allowlist:
        raise PolicyValidationError("provider_allowlist must be a non-empty list")
    allowlist: list[str] = []
    for value in raw_allowlist:
        if not isinstance(value, str) or not SAFE_PROVIDER_ID.fullmatch(value):
            raise PolicyValidationError("provider_allowlist contains an invalid provider id")
        if value not in PROVIDER_BY_ID:
            raise PolicyValidationError("provider_allowlist contains an unknown provider id")
        if value in allowlist:
            raise PolicyValidationError("provider_allowlist contains a duplicate provider id")
        allowlist.append(value)

    raw_limits = payload.get("limits")
    if not isinstance(raw_limits, dict) or set(raw_limits) != set(POLICY_LIMITS):
        raise PolicyValidationError("policy limits do not match the v1 schema")
    limits = {
        name: _strict_int(raw_limits.get(name), name=name, low=bounds[0], high=bounds[1])
        for name, bounds in POLICY_LIMITS.items()
    }
    if limits["request_timeout_seconds"] >= limits["child_timeout_seconds"]:
        raise PolicyValidationError("request timeout must be lower than child timeout")

    state_path = _safe_runtime_state_path(payload.get("state_path"))
    normalized = dict(payload)
    normalized["provider_allowlist"] = sorted(allowlist)
    normalized["limits"] = limits
    normalized["resolved_state_path"] = state_path
    normalized["policy_sha256"] = sha256_payload(payload)
    return normalized


def normalize_provider_ids(provider_ids: Iterable[str] | None, allowlist: Iterable[str]) -> list[str]:
    allowed = set(allowlist)
    requested = list(allowlist) if provider_ids is None else list(provider_ids)
    if not requested:
        raise ValueError("at least one provider id is required")
    normalized: list[str] = []
    for provider_id in requested:
        if not isinstance(provider_id, str) or not SAFE_PROVIDER_ID.fullmatch(provider_id):
            raise ValueError("provider id is invalid")
        if provider_id not in allowed or provider_id not in PROVIDER_BY_ID:
            raise ValueError("provider id is not allowlisted")
        if provider_id in normalized:
            raise ValueError("provider ids must be unique")
        normalized.append(provider_id)
    return sorted(normalized)


def _registry_rows_by_id(values: Any, *, field: str) -> dict[str, dict[str, Any]]:
    if not isinstance(values, list):
        raise RegistrySchemaError(f"registry {field} must be a list")
    rows: dict[str, dict[str, Any]] = {}
    for value in values:
        if not isinstance(value, dict):
            raise RegistrySchemaError(f"registry {field} contains a non-object row")
        provider_id = str(value.get("source") or "").upper()
        if not SAFE_PROVIDER_ID.fullmatch(provider_id):
            raise RegistrySchemaError(f"registry {field} contains an invalid source id")
        if provider_id in rows:
            raise RegistrySchemaError(f"registry {field} contains a duplicate source id")
        row = dict(value)
        row["source"] = provider_id
        rows[provider_id] = row
    return rows


def migrate_live_source_registry(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise RegistrySchemaError("live source registry must be an object")
    declared_schema = payload.get("schema")
    rows_present = "rows" in payload
    sources_present = "sources" in payload

    if declared_schema in {REGISTRY_ROWS_SCHEMA, REGISTRY_CANONICAL_SCHEMA}:
        if not rows_present or sources_present:
            raise RegistrySchemaError("versioned rows registry has an ambiguous payload shape")
        rows_by_id = _registry_rows_by_id(payload.get("rows"), field="rows")
        source_schema = str(declared_schema)
        migration_required = declared_schema != REGISTRY_CANONICAL_SCHEMA
    elif declared_schema in {
        REGISTRY_LEGACY_ROWS_SCHEMA,
        REGISTRY_LEGACY_SOURCES_SCHEMA,
        REGISTRY_LEGACY_MIRRORED_SCHEMA,
    }:
        if declared_schema == REGISTRY_LEGACY_MIRRORED_SCHEMA:
            rows_by_id = _registry_rows_by_id(payload.get("rows"), field="rows")
            sources_by_id = _registry_rows_by_id(payload.get("sources"), field="sources")
            if sha256_payload(rows_by_id) != sha256_payload(sources_by_id):
                raise RegistrySchemaError("versioned legacy registry rows and sources conflict")
        else:
            field = "sources" if declared_schema == REGISTRY_LEGACY_SOURCES_SCHEMA else "rows"
            rows_by_id = _registry_rows_by_id(payload.get(field), field=field)
        source_schema = str(declared_schema)
        migration_required = True
    elif declared_schema is not None:
        raise RegistrySchemaError("live source registry schema is unsupported")
    elif rows_present and sources_present:
        rows_by_id = _registry_rows_by_id(payload.get("rows"), field="rows")
        sources_by_id = _registry_rows_by_id(payload.get("sources"), field="sources")
        if sha256_payload(rows_by_id) != sha256_payload(sources_by_id):
            raise RegistrySchemaError("unversioned registry rows and sources conflict")
        source_schema = REGISTRY_LEGACY_MIRRORED_SCHEMA
        migration_required = True
    elif rows_present:
        rows_by_id = _registry_rows_by_id(payload.get("rows"), field="rows")
        source_schema = REGISTRY_LEGACY_ROWS_SCHEMA
        migration_required = True
    elif sources_present:
        rows_by_id = _registry_rows_by_id(payload.get("sources"), field="sources")
        source_schema = REGISTRY_LEGACY_SOURCES_SCHEMA
        migration_required = True
    else:
        raise RegistrySchemaError("unversioned registry has no recognized row field")

    return {
        "schema": REGISTRY_CANONICAL_SCHEMA,
        "source_schema": source_schema,
        "source_payload_sha256": sha256_payload(payload),
        "migration_required": migration_required,
        "generated_utc": payload.get("generated_utc"),
        "paper_live_linked": bool(payload.get("paper_live_linked", False)),
        "rows": [rows_by_id[key] for key in sorted(rows_by_id)],
    }


def read_live_source_registry(path: Path = REGISTRY_JSON) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RegistrySchemaError("live source registry could not be read") from exc
    return migrate_live_source_registry(payload)


def registry_boundary_receipt(registry: dict[str, Any], allowlist: Iterable[str]) -> dict[str, Any]:
    known = set(allowlist)
    provider_ids = [str(row["source"]) for row in registry["rows"]]
    return {
        "input_schema": registry["source_schema"],
        "canonical_schema": registry["schema"],
        "migration_required": bool(registry["migration_required"]),
        "source_payload_sha256": registry["source_payload_sha256"],
        "provider_count": len(provider_ids),
        "stale_provider_ids": sorted(provider_id for provider_id in provider_ids if provider_id not in known),
    }


def build_namespace_assignments(provider_ids: Iterable[str], run_id: str) -> dict[str, dict[str, str]]:
    if not SAFE_RUN_ID.fullmatch(run_id):
        raise ValueError("run id is invalid")
    assignments = {
        provider_id: {
            "cpu": f"live-source/{run_id}/{provider_id.lower()}/cpu",
            "gpu": f"live-source/{run_id}/{provider_id.lower()}/gpu",
        }
        for provider_id in provider_ids
    }
    validate_namespace_assignments(assignments)
    return assignments


def validate_namespace_assignments(assignments: dict[str, dict[str, str]]) -> None:
    if not isinstance(assignments, dict) or not assignments:
        raise ValueError("namespace assignments must be a non-empty object")
    seen: set[str] = set()
    for provider_id, namespace in assignments.items():
        if not SAFE_PROVIDER_ID.fullmatch(provider_id):
            raise ValueError("namespace assignment has an invalid provider id")
        if not isinstance(namespace, dict) or set(namespace) != {"cpu", "gpu"}:
            raise ValueError("namespace assignment fields are invalid")
        for kind in ("cpu", "gpu"):
            value = namespace[kind]
            if not isinstance(value, str) or not SAFE_NAMESPACE.fullmatch(value) or not value.endswith(f"/{kind}"):
                raise ValueError("namespace value is invalid")
            if value in seen:
                raise ValueError("CPU/GPU namespaces must be disjoint")
            seen.add(value)


def _validate_artifact(
    artifact: Any,
    *,
    expected_provider_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(artifact, dict):
        raise ReceiptValidationError("published child receipt requires an artifact")
    expected = {
        "snapshot_json",
        "snapshot_latest_json",
        "snapshot_csv",
        "sha256",
        "file_sha256",
    }
    if set(artifact) != expected:
        raise ReceiptValidationError("artifact fields do not match the v1 schema")
    validated: dict[str, Any] = {}
    expected_root = None
    if expected_provider_id is not None:
        if expected_provider_id not in PROVIDER_BY_ID:
            raise ReceiptValidationError("artifact provider is not recognized")
        expected_root = (DATA_ROOT / expected_provider_id.lower()).resolve()
    for key in ("snapshot_json", "snapshot_latest_json", "snapshot_csv"):
        value = artifact.get(key)
        if not isinstance(value, str) or not value or "\\" in value:
            raise ReceiptValidationError("artifact path is invalid")
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise ReceiptValidationError("artifact path escaped the workspace")
        resolved = (ROOT / path).resolve()
        if expected_root is not None and expected_root not in resolved.parents:
            raise ReceiptValidationError("artifact path escaped the provider data directory")
        validated[key] = value
    digest = artifact.get("sha256")
    if not isinstance(digest, str) or not SHA256_HEX.fullmatch(digest):
        raise ReceiptValidationError("artifact hash is invalid")
    validated["sha256"] = digest
    file_hashes = artifact.get("file_sha256")
    expected_hash_keys = {"snapshot_json", "snapshot_latest_json", "snapshot_csv"}
    if not isinstance(file_hashes, dict) or set(file_hashes) != expected_hash_keys:
        raise ReceiptValidationError("artifact file hashes are invalid")
    for key, value in file_hashes.items():
        if not isinstance(value, str) or not SHA256_HEX.fullmatch(value):
            raise ReceiptValidationError("artifact file hash is invalid")
    validated["file_sha256"] = dict(file_hashes)
    return validated


def verify_artifact_files(
    artifact: Any,
    *,
    expected_provider_id: str,
) -> dict[str, Any]:
    validated = _validate_artifact(
        artifact,
        expected_provider_id=expected_provider_id,
    )
    paths = {
        key: (ROOT / validated[key]).resolve()
        for key in ("snapshot_json", "snapshot_latest_json", "snapshot_csv")
    }
    for key, path in paths.items():
        if not path.is_file() or sha256_file(path) != validated["file_sha256"][key]:
            raise ReceiptValidationError("artifact file is missing or hash-mismatched")
    try:
        snapshot = json.loads(paths["snapshot_json"].read_text(encoding="utf-8"))
        latest = json.loads(paths["snapshot_latest_json"].read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptValidationError("artifact snapshot JSON is unreadable") from exc
    if not isinstance(snapshot, dict) or snapshot != latest:
        raise ReceiptValidationError("artifact snapshot and latest JSON differ")
    unsigned = {key: value for key, value in snapshot.items() if key != "sha256"}
    if (
        snapshot.get("schema") != SNAPSHOT_SCHEMA
        or snapshot.get("source") != expected_provider_id
        or snapshot.get("sha256") != validated["sha256"]
        or sha256_payload(unsigned) != validated["sha256"]
    ):
        raise ReceiptValidationError("artifact snapshot payload hash is invalid")
    return validated


def validate_child_receipt(
    receipt: Any,
    *,
    allowlist: Iterable[str],
    expected_provider_id: str | None = None,
    expected_run_id: str | None = None,
    expected_attempt: int | None = None,
    expected_namespace: dict[str, str] | None = None,
    expected_network_allowed: bool | None = None,
    expected_published_outputs: bool | None = None,
    max_rows: int = 1_000,
) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        raise ReceiptValidationError("child receipt must be an object")
    expected_fields = {
        "schema",
        "run_id",
        "provider_id",
        "attempt",
        "namespace",
        "network_allowed",
        "published_outputs",
        "credential_state",
        "qc_state",
        "row_count",
        "http_status",
        "retry_after_seconds",
        "artifact",
        "receipt_sha256",
    }
    if set(receipt) != expected_fields:
        raise ReceiptValidationError("child receipt fields do not match the v1 schema")
    if receipt.get("schema") != RECEIPT_SCHEMA or not verify_receipt_hash(receipt):
        raise ReceiptValidationError("child receipt schema or hash is invalid")

    provider_id = receipt.get("provider_id")
    if not isinstance(provider_id, str) or provider_id not in set(allowlist) or provider_id not in PROVIDER_BY_ID:
        raise ReceiptValidationError("child receipt provider is not allowlisted")
    if expected_provider_id is not None and provider_id != expected_provider_id:
        raise ReceiptValidationError("child receipt provider does not match the launched provider")
    run_id = receipt.get("run_id")
    if not isinstance(run_id, str) or not SAFE_RUN_ID.fullmatch(run_id):
        raise ReceiptValidationError("child receipt run id is invalid")
    if expected_run_id is not None and run_id != expected_run_id:
        raise ReceiptValidationError("child receipt run id does not match")
    attempt = receipt.get("attempt")
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
        raise ReceiptValidationError("child receipt attempt is invalid")
    if expected_attempt is not None and attempt != expected_attempt:
        raise ReceiptValidationError("child receipt attempt does not match")

    namespace = receipt.get("namespace")
    validate_namespace_assignments({provider_id: namespace})
    if expected_namespace is not None and namespace != expected_namespace:
        raise ReceiptValidationError("child receipt namespace does not match")
    if not isinstance(receipt.get("network_allowed"), bool) or not isinstance(receipt.get("published_outputs"), bool):
        raise ReceiptValidationError("child receipt boolean fields are invalid")
    if receipt["published_outputs"] and not receipt["network_allowed"]:
        raise ReceiptValidationError("child cannot publish without network authorization")
    if expected_network_allowed is not None and receipt["network_allowed"] is not expected_network_allowed:
        raise ReceiptValidationError("child receipt network authorization does not match")
    if expected_published_outputs is not None and receipt["published_outputs"] is not expected_published_outputs:
        raise ReceiptValidationError("child receipt publication state does not match")
    if receipt.get("credential_state") not in {"UNKNOWN", "NOT_REQUIRED", "PRESENT", "MISSING"}:
        raise ReceiptValidationError("child receipt credential state is invalid")
    qc_state = receipt.get("qc_state")
    if not isinstance(qc_state, str) or qc_state not in QC_STATES - {"RATE_LIMITED"}:
        raise ReceiptValidationError("child receipt QC state is invalid")
    row_count = receipt.get("row_count")
    if isinstance(row_count, bool) or not isinstance(row_count, int) or not 0 <= row_count <= max_rows:
        raise ReceiptValidationError("child receipt row count is invalid")
    http_status = receipt.get("http_status")
    if http_status is not None and (
        isinstance(http_status, bool) or not isinstance(http_status, int) or not 100 <= http_status <= 599
    ):
        raise ReceiptValidationError("child receipt HTTP status is invalid")
    retry_after = receipt.get("retry_after_seconds")
    if retry_after is not None and (
        isinstance(retry_after, bool) or not isinstance(retry_after, int) or not 0 <= retry_after <= 86_400
    ):
        raise ReceiptValidationError("child receipt retry delay is invalid")
    if receipt["published_outputs"]:
        verify_artifact_files(
            receipt.get("artifact"),
            expected_provider_id=provider_id,
        )
    elif receipt.get("artifact") is not None:
        raise ReceiptValidationError("unpublished child receipt cannot declare an artifact")
    return dict(receipt)


def estimate_value(sector: str, rows: int) -> dict[str, float]:
    if rows <= 0:
        return {"hour": 0.0, "day": 0.0, "week": 0.0, "month": 0.0, "year": 0.0}
    import math

    base = min(max(float(rows), 1.0), 1000.0)
    hour = round(SECTOR_WEIGHT.get(sector, 10_000.0) * math.log(base + 1.0), 2)
    day = round(hour * 24.0, 2)
    return {
        "hour": hour,
        "day": day,
        "week": round(day * 7.0, 2),
        "month": round(day * 30.0, 2),
        "year": round(day * 365.0, 2),
    }


def snapshot_provider(
    provider: dict[str, Any],
    result: dict[str, Any],
    *,
    tag: str,
) -> dict[str, Any]:
    source = str(provider["source"])
    env_names = list(provider.get("env_names", []))
    rows = scrub(result.get("rows", []), env_names)
    snapshot = {
        "schema": SNAPSHOT_SCHEMA,
        "generated_utc": now_utc(),
        "source": source,
        "sector": provider["sector"],
        "rows": rows,
        "row_count": len(rows) if isinstance(rows, list) else 0,
        "http_status": result.get("http_status"),
        "probe_ok": bool(result.get("probe_ok")),
        "probe_note": sanitize_text(result.get("probe_note", ""), env_names),
        "env_names": env_names,
        "present_env_names": present_env_names(env_names),
    }
    digest = sha256_payload(snapshot)
    snapshot["sha256"] = digest

    source_dir = DATA_ROOT / source.lower()
    json_path = source_dir / f"{source.lower()}_{tag}.json"
    latest_path = source_dir / f"{source.lower()}_latest.json"
    csv_path = source_dir / f"{source.lower()}_{tag}.csv"
    atomic_write_json(json_path, snapshot)
    atomic_write_json(latest_path, snapshot)
    atomic_write_csv(csv_path, rows if isinstance(rows, list) else [])

    return {
        "snapshot_json": str(json_path.relative_to(ROOT)).replace("\\", "/"),
        "snapshot_latest_json": str(latest_path.relative_to(ROOT)).replace("\\", "/"),
        "snapshot_csv": str(csv_path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": digest,
        "file_sha256": {
            "snapshot_json": sha256_file(json_path),
            "snapshot_latest_json": sha256_file(latest_path),
            "snapshot_csv": sha256_file(csv_path),
        },
    }


def registry_row(provider: dict[str, Any], result: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    source = str(provider["source"])
    sector = str(provider["sector"])
    env_names = list(provider.get("env_names", []))
    raw_row_count = result.get("row_count")
    row_count = int(raw_row_count) if isinstance(raw_row_count, int) else len(result.get("rows", []) or [])
    enabled = (not env_names) or bool(present_env_names(env_names))
    measured = bool(result.get("probe_ok")) and row_count > 0
    translated = estimate_value(sector, row_count) if measured else estimate_value(sector, 0)
    status = "MEASURED" if measured else ("PROBE_FAILED_OR_THIN" if enabled else "UNCONFIGURED")
    return {
        "source": source,
        "sector": sector,
        "status": status,
        "rows": row_count,
        "probe_ok": bool(result.get("probe_ok")),
        "http_status": result.get("http_status"),
        "evidence_basis": "LIVE_HTTP_SNAPSHOT" if measured else ("KEY_PRESENT_BUT_NO_USABLE_ROWS" if enabled else "NONE"),
        "dollar_basis": (
            "HEURISTIC_TRANSLATION_FROM_MEASURED_ROW_COUNT"
            if measured
            else "UNMEASURED"
        ),
        "constraint_type": provider.get("constraint_type", ""),
        "money_drain_mode": provider.get("money_drain_mode", ""),
        "formula_basis": "bounded_log_heuristic_if_rows_measured_else_zero",
        "translated_value": translated,
        "env_names": env_names,
        "present_env_names": present_env_names(env_names),
        "last_probe_utc": now_utc(),
        "probe_note": sanitize_text(result.get("probe_note", ""), env_names),
        "enabled": enabled,
        "measured": measured,
        "snapshot_json": artifact["snapshot_json"],
        "snapshot_latest_json": artifact["snapshot_latest_json"],
        "snapshot_csv": artifact["snapshot_csv"],
        "snapshot_sha256": artifact["sha256"],
    }


def merge_registry(existing: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    if existing.get("schema") == REGISTRY_CANONICAL_SCHEMA:
        old_rows_by_id = _registry_rows_by_id(existing.get("rows"), field="rows")
        canonical = dict(existing)
        canonical["rows"] = [old_rows_by_id[key] for key in sorted(old_rows_by_id)]
    else:
        canonical = migrate_live_source_registry(existing)
    old_rows = canonical["rows"]
    merged: dict[str, dict[str, Any]] = {}
    for row in old_rows:
        if isinstance(row, dict) and row.get("source"):
            merged[str(row["source"]).upper()] = dict(row)
    for row in rows:
        if not isinstance(row, dict):
            raise RegistrySchemaError("new registry rows must be objects")
        provider_id = str(row.get("source") or "").upper()
        if not SAFE_PROVIDER_ID.fullmatch(provider_id):
            raise RegistrySchemaError("new registry row has an invalid source id")
        copied = dict(row)
        copied["source"] = provider_id
        merged[provider_id] = copied
    ordered = sorted(merged.values(), key=lambda item: str(item.get("source", "")))
    stale_provider_ids = sorted(provider_id for provider_id in merged if provider_id not in PROVIDER_BY_ID)
    return {
        "schema": REGISTRY_ROWS_SCHEMA,
        "generated_utc": now_utc(),
        "paper_live_linked": True,
        "rows": ordered,
        "stale_provider_ids": stale_provider_ids,
        "migration_boundary": {
            "input_schema": canonical.get("source_schema", canonical.get("schema")),
            "canonical_schema": REGISTRY_CANONICAL_SCHEMA,
            "source_payload_sha256": canonical.get("source_payload_sha256", sha256_payload(existing)),
        },
    }


def live_sources_from_registry(registry: dict[str, Any]) -> dict[str, Any]:
    providers: dict[str, Any] = {}
    rows = registry.get("rows", []) if isinstance(registry.get("rows"), list) else []
    for row in rows:
        if not isinstance(row, dict) or not row.get("source"):
            continue
        providers[str(row["source"])] = {
            "enabled": bool(row.get("enabled", False)),
            "sector": row.get("sector", ""),
            "env_names": row.get("env_names", []),
            "present_env_names": row.get("present_env_names", []),
            "status": "LIVE_KEY_PRESENT" if row.get("enabled") else "MISSING",
            "probe_ok": bool(row.get("probe_ok", False)),
            "probe_note": row.get("probe_note", ""),
            "measured": bool(row.get("measured", False)),
            "rows": row.get("rows", 0),
            "http_status": row.get("http_status"),
            "last_truth_sync_utc": row.get("last_probe_utc", ""),
            "snapshot_json": row.get("snapshot_json", ""),
            "snapshot_sha256": row.get("snapshot_sha256", ""),
        }
    return {"generated_utc": now_utc(), "providers": providers}


def source_truth_from_registry(registry: dict[str, Any]) -> dict[str, Any]:
    rows = registry.get("rows", []) if isinstance(registry.get("rows"), list) else []
    truth_rows = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        translated = row.get("translated_value", {}) if isinstance(row.get("translated_value"), dict) else {}
        truth_rows.append(
            {
                "source": row.get("source", ""),
                "sector": row.get("sector", ""),
                "status": row.get("status", ""),
                "rows": row.get("rows", 0),
                "enabled": bool(row.get("enabled", False)),
                "measured": bool(row.get("measured", False)),
                "estimated_hour_value": translated.get("hour", 0.0),
                "value_basis": (
                    "HEURISTIC_FROM_MEASURED_ROW_COUNT"
                    if row.get("measured")
                    else "UNMEASURED"
                ),
                "last_probe_utc": row.get("last_probe_utc", ""),
                "probe_note": row.get("probe_note", ""),
                "snapshot_json": row.get("snapshot_json", ""),
                "snapshot_sha256": row.get("snapshot_sha256", ""),
            }
        )
    return {"generated_utc": now_utc(), "rows": truth_rows}


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    enabled = [row for row in rows if row.get("enabled")]
    measured = [row for row in enabled if row.get("measured")]
    failed = [row for row in enabled if not row.get("measured")]
    total_rows = sum(int(row.get("rows", 0) or 0) for row in measured)
    annual = sum(float((row.get("translated_value") or {}).get("year", 0.0)) for row in measured)
    by_sector: dict[str, dict[str, Any]] = {}
    for row in rows:
        sector = str(row.get("sector") or "unknown")
        item = by_sector.setdefault(sector, {"enabled": 0, "measured": 0, "rows": 0})
        if row.get("enabled"):
            item["enabled"] += 1
        if row.get("measured"):
            item["measured"] += 1
            item["rows"] += int(row.get("rows", 0) or 0)
    return {
        "enabled_sources": len(enabled),
        "measured_sources": len(measured),
        "failed_or_thin_sources": len(failed),
        "total_measured_rows": total_rows,
        "estimated_annual_value_surface_usd": round(annual, 2),
        "estimated_annual_value_surface_basis": (
            "UNVALIDATED_HEURISTIC_NOT_REALIZED_OR_MEASURED_VALUE"
        ),
        "coverage_pct": round((len(measured) / len(enabled) * 100.0) if enabled else 0.0, 2),
        "measured_source_names": [str(row.get("source")) for row in measured],
        "failed_or_thin_source_names": [str(row.get("source")) for row in failed],
        "by_sector": by_sector,
        "claim_boundary": (
            "This pass proves fresh measured row counts and snapshot hashes. Dollar translations "
            "are unvalidated heuristics, not measured economic value, realized savings, field "
            "validation, trading profit, or guaranteed award value."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Live Source Measurement Maximizer",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Summary",
        "",
        f"- Enabled sources: {summary['enabled_sources']}",
        f"- Measured sources: {summary['measured_sources']}",
        f"- Failed/thin sources: {summary['failed_or_thin_sources']}",
        f"- Total measured rows: {summary['total_measured_rows']}",
        f"- Coverage: {summary['coverage_pct']}%",
        f"- Heuristic annual value surface (not measured dollars): "
        f"${summary['estimated_annual_value_surface_usd']:,.2f}",
        f"- Boundary: {summary['claim_boundary']}",
        "",
        "## Measured Sources",
        "",
    ]
    for name in summary["measured_source_names"]:
        lines.append(f"- `{name}`")
    lines.extend(["", "## Failed Or Thin Sources", ""])
    for name in summary["failed_or_thin_source_names"]:
        lines.append(f"- `{name}`")
    lines.extend(
        [
            "",
            "## Provider Rows",
            "",
            "| Source | Sector | Status | Rows | Snapshot | SHA-256 |",
            "|---|---|---|---:|---|---|",
        ]
    )
    for row in payload["provider_rows"]:
        lines.append(
            f"| {row['source']} | {row['sector']} | {row['status']} | {row['rows']} | "
            f"`{row.get('snapshot_json', '')}` | `{row.get('snapshot_sha256', '')}` |"
        )
    return "\n".join(lines)


def classify_provider_result(result: dict[str, Any], *, network_allowed: bool) -> str:
    if not network_allowed:
        return "DRY_RUN"
    rows = result.get("rows") if isinstance(result.get("rows"), list) else []
    if result.get("probe_ok") and rows:
        return "PASS"
    note = str(result.get("probe_note") or "")
    error_kind = str(result.get("error_kind") or "")
    http_status = result.get("http_status")
    if note == "missing_env":
        return "UNCONFIGURED"
    if http_status == 429 or (isinstance(http_status, int) and 500 <= http_status <= 599):
        return "RETRYABLE_HTTP"
    if isinstance(http_status, int) and 400 <= http_status <= 499:
        return "HTTP_REJECTED"
    if error_kind == "timeout":
        return "TIMEOUT"
    if error_kind == "malformed_json":
        return "MALFORMED_JSON"
    if error_kind == "oversized_json":
        return "OVERSIZED_JSON"
    if error_kind == "transport_error":
        return "TRANSPORT_ERROR"
    if error_kind:
        return "ADAPTER_ERROR"
    return "EMPTY"


def build_provider_child_receipt(
    provider_id: str,
    *,
    policy: dict[str, Any],
    run_id: str,
    attempt: int,
    namespace: dict[str, str],
    max_rows: int,
    request_timeout_seconds: int,
    allow_network: bool = False,
    publish_outputs: bool = False,
) -> dict[str, Any]:
    normalize_provider_ids([provider_id], policy["provider_allowlist"])
    validate_namespace_assignments({provider_id: namespace})
    if not SAFE_RUN_ID.fullmatch(run_id):
        raise ValueError("run id is invalid")
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
        raise ValueError("attempt must be a positive integer")
    if publish_outputs and not allow_network:
        raise ValueError("output publication requires network authorization")
    limits = policy["limits"]
    if not 1 <= max_rows <= limits["max_rows"]:
        raise ValueError("max_rows exceeds policy")
    if not 1 <= request_timeout_seconds <= limits["request_timeout_seconds"]:
        raise ValueError("request timeout exceeds policy")

    provider = PROVIDER_BY_ID[provider_id]
    env_names = list(provider.get("env_names", []))
    os.environ["LUMA_CPU_NAMESPACE"] = namespace["cpu"]
    os.environ["LUMA_GPU_NAMESPACE"] = namespace["gpu"]
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

    credential_state = "UNKNOWN"
    if not env_names:
        credential_state = "NOT_REQUIRED"
    if allow_network:
        hydrate_selected_env(env_names)
        credential_state = "PRESENT" if (not env_names or present_env_names(env_names)) else "MISSING"
        collector = provider["collector"]
        result = safe_request(
            provider_id,
            env_names,
            lambda: collector(max_rows, request_timeout_seconds),
        )
        rows = result.get("rows") if isinstance(result.get("rows"), list) else []
        result["rows"] = [row for row in rows if isinstance(row, dict)][:max_rows]
    else:
        result = {
            "source": provider_id,
            "http_status": None,
            "rows": [],
            "probe_ok": False,
            "probe_note": "dry_run",
            "error_kind": None,
            "retry_after_seconds": None,
        }

    qc_state = classify_provider_result(result, network_allowed=allow_network)
    artifact = None
    if publish_outputs:
        artifact = snapshot_provider(provider, result, tag=f"{run_id}_{attempt}")
    retry_after = result.get("retry_after_seconds")
    if isinstance(retry_after, int) and not isinstance(retry_after, bool):
        retry_after = min(max(0, retry_after), 86_400)
    else:
        retry_after = None
    http_status = result.get("http_status")
    if isinstance(http_status, bool) or not isinstance(http_status, int) or not 100 <= http_status <= 599:
        http_status = None
    rows = result.get("rows") if isinstance(result.get("rows"), list) else []
    receipt = seal_receipt(
        {
            "schema": RECEIPT_SCHEMA,
            "run_id": run_id,
            "provider_id": provider_id,
            "attempt": attempt,
            "namespace": dict(namespace),
            "network_allowed": bool(allow_network),
            "published_outputs": bool(publish_outputs),
            "credential_state": credential_state,
            "qc_state": qc_state,
            "row_count": len(rows),
            "http_status": http_status,
            "retry_after_seconds": retry_after,
            "artifact": artifact,
        }
    )
    return validate_child_receipt(
        receipt,
        allowlist=policy["provider_allowlist"],
        expected_provider_id=provider_id,
        expected_run_id=run_id,
        expected_attempt=attempt,
        expected_namespace=namespace,
        expected_network_allowed=allow_network,
        expected_published_outputs=publish_outputs,
        max_rows=max_rows,
    )


def empty_rate_limit_state() -> dict[str, Any]:
    return {"schema": ORCHESTRATOR_STATE_SCHEMA, "providers": {}}


def validate_rate_limit_state(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {"schema", "providers"}:
        raise ValueError("rate-limit state fields are invalid")
    if payload.get("schema") != ORCHESTRATOR_STATE_SCHEMA or not isinstance(payload.get("providers"), dict):
        raise ValueError("rate-limit state schema is invalid")
    for provider_id, entry in payload["providers"].items():
        if not isinstance(provider_id, str) or not SAFE_PROVIDER_ID.fullmatch(provider_id):
            raise ValueError("rate-limit state provider id is invalid")
        if not isinstance(entry, dict) or set(entry) != {
            "circuit_state",
            "consecutive_failures",
            "not_before_utc",
            "last_qc_state",
            "last_http_status",
        }:
            raise ValueError("rate-limit provider state fields are invalid")
        if entry.get("circuit_state") not in CIRCUIT_STATES:
            raise ValueError("rate-limit circuit state is invalid")
        failures = entry.get("consecutive_failures")
        if isinstance(failures, bool) or not isinstance(failures, int) or failures < 0:
            raise ValueError("rate-limit failure count is invalid")
        not_before = entry.get("not_before_utc")
        if not_before is not None and parse_utc(not_before) is None:
            raise ValueError("rate-limit not-before timestamp is invalid")
        if entry.get("last_qc_state") not in QC_STATES:
            raise ValueError("rate-limit last QC state is invalid")
        status = entry.get("last_http_status")
        if status is not None and (
            isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599
        ):
            raise ValueError("rate-limit HTTP status is invalid")
    return payload


def load_rate_limit_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_rate_limit_state()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("rate-limit state could not be read") from exc
    return validate_rate_limit_state(payload)


def provider_is_rate_limited(entry: Any, *, reference_utc: datetime) -> bool:
    if not isinstance(entry, dict):
        return False
    not_before = parse_utc(entry.get("not_before_utc"))
    return bool(not_before and not_before > reference_utc.astimezone(timezone.utc))


def update_rate_limit_state(
    state: dict[str, Any],
    provider_results: Iterable[dict[str, Any]],
    *,
    limits: dict[str, int],
    reference_utc: datetime,
) -> dict[str, Any]:
    updated = {
        "schema": ORCHESTRATOR_STATE_SCHEMA,
        "providers": {key: dict(value) for key, value in state.get("providers", {}).items()},
    }
    for result in provider_results:
        provider_id = result["provider_id"]
        qc_state = result["qc_state"]
        prior = updated["providers"].get(provider_id, {})
        failures = int(prior.get("consecutive_failures", 0) or 0)
        not_before_utc = None
        circuit_state = "CLOSED"

        if qc_state in {"RETRYABLE_HTTP", "TIMEOUT", "TRANSPORT_ERROR", "CHILD_EXIT"}:
            failures += 1
            retry_after = result.get("retry_after_seconds")
            if qc_state == "RETRYABLE_HTTP":
                delay = retry_after if isinstance(retry_after, int) else limits["default_rate_limit_seconds"]
                not_before_utc = (reference_utc + timedelta(seconds=delay)).astimezone(timezone.utc).isoformat()
            if failures >= limits["circuit_breaker_failures"]:
                circuit_state = "OPEN"
                if not_before_utc is None:
                    not_before_utc = (
                        reference_utc + timedelta(seconds=limits["default_rate_limit_seconds"])
                    ).astimezone(timezone.utc).isoformat()
        elif qc_state == "RATE_LIMITED":
            continue
        else:
            failures = 0

        updated["providers"][provider_id] = {
            "circuit_state": circuit_state,
            "consecutive_failures": failures,
            "not_before_utc": not_before_utc,
            "last_qc_state": qc_state,
            "last_http_status": result.get("http_status"),
        }
    return updated


def write_rate_limit_state(path: Path, state: dict[str, Any]) -> None:
    validate_rate_limit_state(state)
    atomic_write_json(path, state)


def build_child_command(
    *,
    provider_id: str,
    policy_path: Path,
    run_id: str,
    attempt: int,
    namespace: dict[str, str],
    max_rows: int,
    request_timeout_seconds: int,
    allow_network: bool,
    publish_outputs: bool,
) -> list[str]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--policy",
        str(policy_path.resolve()),
        "--child-provider",
        provider_id,
        "--run-id",
        run_id,
        "--attempt",
        str(attempt),
        "--cpu-namespace",
        namespace["cpu"],
        "--gpu-namespace",
        namespace["gpu"],
        "--max-rows",
        str(max_rows),
        "--timeout",
        str(request_timeout_seconds),
    ]
    if allow_network:
        command.append("--allow-network")
    if publish_outputs:
        command.append("--publish-outputs")
    if command.count("--child-provider") != 1:
        raise RuntimeError("child command must contain exactly one provider selector")
    return command


def _provider_process_failure(
    provider_id: str,
    namespace: dict[str, str],
    *,
    qc_state: str,
    attempts: int,
) -> dict[str, Any]:
    return {
        "provider_id": provider_id,
        "namespace": dict(namespace),
        "qc_state": qc_state,
        "attempts": attempts,
        "child_receipt_sha256": None,
        "credential_state": "UNKNOWN",
        "row_count": 0,
        "http_status": None,
        "retry_after_seconds": None,
        "artifact": None,
    }


def run_provider_subprocess(
    provider_id: str,
    *,
    policy: dict[str, Any],
    policy_path: Path,
    run_id: str,
    namespace: dict[str, str],
    allow_network: bool,
    publish_outputs: bool,
    runner: Callable[..., Any] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    limits = policy["limits"]
    process_runner = runner or subprocess.run
    for attempt in range(1, limits["max_retries"] + 2):
        command = build_child_command(
            provider_id=provider_id,
            policy_path=policy_path,
            run_id=run_id,
            attempt=attempt,
            namespace=namespace,
            max_rows=limits["max_rows"],
            request_timeout_seconds=limits["request_timeout_seconds"],
            allow_network=allow_network,
            publish_outputs=publish_outputs,
        )
        try:
            completed = process_runner(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=limits["child_timeout_seconds"],
                env=build_child_environment(provider_id),
            )
        except subprocess.TimeoutExpired:
            result = _provider_process_failure(provider_id, namespace, qc_state="TIMEOUT", attempts=attempt)
        except (OSError, subprocess.SubprocessError):
            result = _provider_process_failure(provider_id, namespace, qc_state="CHILD_EXIT", attempts=attempt)
        else:
            if completed.returncode != 0:
                result = _provider_process_failure(provider_id, namespace, qc_state="CHILD_EXIT", attempts=attempt)
            else:
                stdout = completed.stdout if isinstance(completed.stdout, str) else ""
                if len(stdout.encode("utf-8")) > limits["max_child_output_bytes"]:
                    result = _provider_process_failure(
                        provider_id, namespace, qc_state="INVALID_RECEIPT", attempts=attempt
                    )
                else:
                    try:
                        raw_receipt = json.loads(stdout)
                        receipt = validate_child_receipt(
                            raw_receipt,
                            allowlist=policy["provider_allowlist"],
                            expected_provider_id=provider_id,
                            expected_run_id=run_id,
                            expected_attempt=attempt,
                            expected_namespace=namespace,
                            expected_network_allowed=allow_network,
                            expected_published_outputs=publish_outputs,
                            max_rows=limits["max_rows"],
                        )
                    except (json.JSONDecodeError, UnicodeError, ReceiptValidationError, ValueError):
                        result = _provider_process_failure(
                            provider_id, namespace, qc_state="INVALID_RECEIPT", attempts=attempt
                        )
                    else:
                        result = {
                            "provider_id": provider_id,
                            "namespace": dict(namespace),
                            "qc_state": receipt["qc_state"],
                            "attempts": attempt,
                            "child_receipt_sha256": receipt["receipt_sha256"],
                            "credential_state": receipt["credential_state"],
                            "row_count": receipt["row_count"],
                            "http_status": receipt["http_status"],
                            "retry_after_seconds": receipt["retry_after_seconds"],
                            "artifact": receipt["artifact"],
                        }

        retryable = result["qc_state"] in {"RETRYABLE_HTTP", "TIMEOUT", "TRANSPORT_ERROR", "CHILD_EXIT"}
        if retryable and attempt <= limits["max_retries"]:
            requested_delay = result.get("retry_after_seconds")
            if not isinstance(requested_delay, int):
                requested_delay = limits["retry_base_seconds"] * (2 ** (attempt - 1))
            delay = min(requested_delay, limits["max_retry_delay_seconds"])
            if delay > 0:
                sleep_fn(float(delay))
            continue
        return result
    raise RuntimeError("provider retry loop exhausted unexpectedly")


def registry_row_from_provider_result(provider_result: dict[str, Any]) -> dict[str, Any]:
    provider = PROVIDER_BY_ID[provider_result["provider_id"]]
    sector = str(provider["sector"])
    row_count = int(provider_result.get("row_count", 0) or 0)
    qc_state = str(provider_result["qc_state"])
    measured = qc_state == "PASS" and row_count > 0
    credential_state = str(provider_result.get("credential_state") or "UNKNOWN")
    enabled = not provider.get("env_names") or credential_state == "PRESENT"
    artifact = verify_artifact_files(
        provider_result.get("artifact"),
        expected_provider_id=provider_result["provider_id"],
    )
    return {
        "source": provider_result["provider_id"],
        "sector": sector,
        "status": "MEASURED" if measured else ("PROBE_FAILED_OR_THIN" if enabled else "UNCONFIGURED"),
        "rows": row_count,
        "probe_ok": measured,
        "http_status": provider_result.get("http_status"),
        "evidence_basis": "LIVE_HTTP_SNAPSHOT" if measured else ("KEY_PRESENT_BUT_NO_USABLE_ROWS" if enabled else "NONE"),
        "dollar_basis": (
            "HEURISTIC_TRANSLATION_FROM_MEASURED_ROW_COUNT"
            if measured
            else "UNMEASURED"
        ),
        "constraint_type": provider.get("constraint_type", ""),
        "money_drain_mode": provider.get("money_drain_mode", ""),
        "formula_basis": "bounded_log_heuristic_if_rows_measured_else_zero",
        "translated_value": estimate_value(sector, row_count if measured else 0),
        "env_names": list(provider.get("env_names", [])),
        "present_env_names": [],
        "credential_state": credential_state,
        "last_probe_utc": now_utc(),
        "probe_note": f"child_qc:{qc_state}",
        "enabled": enabled,
        "measured": measured,
        "snapshot_json": artifact["snapshot_json"],
        "snapshot_latest_json": artifact["snapshot_latest_json"],
        "snapshot_csv": artifact["snapshot_csv"],
        "snapshot_sha256": artifact["sha256"],
        "child_receipt_sha256": provider_result["child_receipt_sha256"],
    }


def publish_measurement_outputs(
    registry_input: dict[str, Any],
    provider_results: list[dict[str, Any]],
    *,
    run_id: str,
) -> dict[str, Any]:
    provider_rows = [
        registry_row_from_provider_result(result)
        for result in provider_results
        if result.get("child_receipt_sha256") and result.get("artifact") is not None
    ]
    registry = merge_registry(registry_input, provider_rows)
    live_sources = live_sources_from_registry(registry)
    source_truth = source_truth_from_registry(registry)
    summary = build_summary(registry["rows"])
    payload = {
        "generated_utc": now_utc(),
        "schema": "live_source_measurement_maximizer_v1",
        "orchestrator_run_id": run_id,
        "summary": summary,
        "provider_rows": provider_rows,
        "outputs": {
            "registry": str(REGISTRY_JSON.relative_to(ROOT)).replace("\\", "/"),
            "live_sources": str(LIVE_SOURCES_JSON.relative_to(ROOT)).replace("\\", "/"),
            "source_truth_table": str(SOURCE_TRUTH_JSON.relative_to(ROOT)).replace("\\", "/"),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
            "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        },
    }
    atomic_write_json(REGISTRY_JSON, registry)
    atomic_write_json(LIVE_SOURCES_JSON, live_sources)
    atomic_write_json(SOURCE_TRUTH_JSON, source_truth)
    atomic_write_json(OUT_JSON, payload)
    atomic_write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    return payload


def _bounded_policy_overrides(
    policy: dict[str, Any],
    *,
    max_rows: int | None,
    request_timeout_seconds: int | None,
    max_concurrency: int | None,
    max_retries: int | None,
) -> dict[str, Any]:
    normalized = dict(policy)
    limits = dict(policy["limits"])
    overrides = {
        "max_rows": max_rows,
        "request_timeout_seconds": request_timeout_seconds,
        "max_concurrency": max_concurrency,
        "max_retries": max_retries,
    }
    for name, value in overrides.items():
        if value is None:
            continue
        low, _ = POLICY_LIMITS[name]
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= limits[name]:
            raise PolicyValidationError(f"{name} override exceeds the configured policy bound")
        limits[name] = value
    if limits["request_timeout_seconds"] >= limits["child_timeout_seconds"]:
        raise PolicyValidationError("request timeout must remain lower than child timeout")
    normalized["limits"] = limits
    return normalized


def orchestrate_providers(
    provider_ids: Iterable[str] | None = None,
    *,
    policy_path: Path = ORCHESTRATOR_POLICY_JSON,
    registry_path: Path = REGISTRY_JSON,
    state_path: Path | None = None,
    receipt_path: Path | None = None,
    execute: bool = False,
    allow_network: bool = False,
    publish_outputs: bool = False,
    run_id: str | None = None,
    max_rows: int | None = None,
    request_timeout_seconds: int | None = None,
    max_concurrency: int | None = None,
    max_retries: int | None = None,
    runner: Callable[..., Any] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    now_fn: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    if allow_network and not execute:
        raise ValueError("network authorization requires --execute")
    if publish_outputs and (not execute or not allow_network):
        raise ValueError("output publication requires --execute and --allow-network")
    policy = _bounded_policy_overrides(
        load_orchestrator_policy(policy_path),
        max_rows=max_rows,
        request_timeout_seconds=request_timeout_seconds,
        max_concurrency=max_concurrency,
        max_retries=max_retries,
    )
    selected = normalize_provider_ids(provider_ids, policy["provider_allowlist"])
    registry = read_live_source_registry(registry_path)
    boundary = registry_boundary_receipt(registry, policy["provider_allowlist"])
    if run_id is None:
        if execute:
            run_id = f"run-{now_tag()}-{uuid.uuid4().hex[:8]}"
        else:
            dry_seed = {
                "policy_sha256": policy["policy_sha256"],
                "registry_sha256": boundary["source_payload_sha256"],
                "provider_ids": selected,
            }
            run_id = f"dry-{sha256_payload(dry_seed)[:24]}"
    if not SAFE_RUN_ID.fullmatch(run_id):
        raise ValueError("run id is invalid")
    namespaces = build_namespace_assignments(selected, run_id)
    reference_utc = (now_fn or (lambda: datetime.now(timezone.utc)))()
    if reference_utc.tzinfo is None:
        raise ValueError("now_fn must return a timezone-aware datetime")
    reference_utc = reference_utc.astimezone(timezone.utc)

    effective_state_path = state_path or policy["resolved_state_path"]
    state = load_rate_limit_state(effective_state_path) if execute and allow_network else empty_rate_limit_state()
    provider_results: dict[str, dict[str, Any]] = {}
    eligible: list[str] = []
    if not execute:
        for provider_id in selected:
            provider_results[provider_id] = _provider_process_failure(
                provider_id, namespaces[provider_id], qc_state="DRY_RUN", attempts=0
            )
    else:
        for provider_id in selected:
            prior = state["providers"].get(provider_id)
            if allow_network and provider_is_rate_limited(prior, reference_utc=reference_utc):
                skipped = _provider_process_failure(
                    provider_id, namespaces[provider_id], qc_state="RATE_LIMITED", attempts=0
                )
                if isinstance(prior, dict):
                    skipped["http_status"] = prior.get("last_http_status")
                provider_results[provider_id] = skipped
            else:
                eligible.append(provider_id)

        if eligible:
            workers = min(policy["limits"]["max_concurrency"], len(eligible))
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="live-source-parent") as executor:
                futures = {
                    executor.submit(
                        run_provider_subprocess,
                        provider_id,
                        policy=policy,
                        policy_path=policy_path,
                        run_id=run_id,
                        namespace=namespaces[provider_id],
                        allow_network=allow_network,
                        publish_outputs=publish_outputs,
                        runner=runner,
                        sleep_fn=sleep_fn,
                    ): provider_id
                    for provider_id in eligible
                }
                for future in as_completed(futures):
                    provider_id = futures[future]
                    try:
                        provider_results[provider_id] = future.result()
                    except Exception:
                        provider_results[provider_id] = _provider_process_failure(
                            provider_id, namespaces[provider_id], qc_state="CHILD_EXIT", attempts=1
                        )

    ordered_results = [provider_results[provider_id] for provider_id in selected]
    state_persisted = False
    if execute and allow_network:
        updated_state = update_rate_limit_state(
            state,
            ordered_results,
            limits=policy["limits"],
            reference_utc=reference_utc,
        )
        write_rate_limit_state(effective_state_path, updated_state)
        state_persisted = True

    fail_closed_states = {"TIMEOUT", "CHILD_EXIT", "INVALID_RECEIPT"}
    has_fail_closed_result = any(result["qc_state"] in fail_closed_states for result in ordered_results)
    published = False
    if publish_outputs and not has_fail_closed_result:
        publish_measurement_outputs(registry, ordered_results, run_id=run_id)
        published = True

    if not execute:
        status = "DRY_RUN"
    elif has_fail_closed_result:
        status = "FAILED_CLOSED"
    elif any(result["qc_state"] not in {"PASS", "DRY_RUN", "RATE_LIMITED"} for result in ordered_results):
        status = "COMPLETED_WITH_PROVIDER_FAILURES"
    else:
        status = "COMPLETE"
    receipt = seal_receipt(
        {
            "schema": ORCHESTRATOR_SCHEMA,
            "run_id": run_id,
            "status": status,
            "mode": "DRY_RUN" if not execute else ("LIVE" if allow_network else "EXECUTE_NO_NETWORK"),
            "network_allowed": bool(allow_network),
            "publish_outputs_requested": bool(publish_outputs),
            "published_outputs": published,
            "state_persisted": state_persisted,
            "policy": {
                "schema": policy["schema"],
                "sha256": policy["policy_sha256"],
                "limits": dict(policy["limits"]),
            },
            "registry_boundary": boundary,
            "providers": ordered_results,
            "summary": {
                "provider_count": len(ordered_results),
                "launched_child_processes": sum(int(result["attempts"]) for result in ordered_results),
                "valid_child_receipts": sum(bool(result["child_receipt_sha256"]) for result in ordered_results),
                "rate_limited_providers": sum(result["qc_state"] == "RATE_LIMITED" for result in ordered_results),
                "failed_closed_providers": sum(
                    result["qc_state"] in fail_closed_states for result in ordered_results
                ),
            },
        }
    )
    if receipt_path is not None:
        atomic_write_json(receipt_path, receipt)
    return receipt


def run_measurement(
    max_rows: int = 25,
    timeout: int = 20,
    *,
    allow_network: bool = False,
    publish_outputs: bool = False,
) -> dict[str, Any]:
    return orchestrate_providers(
        execute=allow_network,
        allow_network=allow_network,
        publish_outputs=publish_outputs,
        max_rows=max_rows,
        request_timeout_seconds=timeout,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run isolated, bounded live-source provider children.")
    parser.add_argument("--policy", type=Path, default=ORCHESTRATOR_POLICY_JSON)
    parser.add_argument("--registry", type=Path, default=REGISTRY_JSON)
    parser.add_argument("--state-file", type=Path)
    parser.add_argument("--receipt-file", type=Path)
    parser.add_argument("--provider", action="append", dest="providers")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--publish-outputs", action="store_true")
    parser.add_argument("--max-rows", type=int)
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--max-concurrency", type=int)
    parser.add_argument("--max-retries", type=int)
    parser.add_argument("--run-id")
    parser.add_argument("--child-provider", help=argparse.SUPPRESS)
    parser.add_argument("--attempt", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--cpu-namespace", help=argparse.SUPPRESS)
    parser.add_argument("--gpu-namespace", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.child_provider:
            if (
                args.providers
                or args.execute
                or args.registry != REGISTRY_JSON
                or args.state_file
                or args.receipt_file
                or args.max_concurrency is not None
                or args.max_retries is not None
            ):
                raise ValueError("child mode received parent-only arguments")
            policy = _bounded_policy_overrides(
                load_orchestrator_policy(args.policy),
                max_rows=args.max_rows,
                request_timeout_seconds=args.timeout,
                max_concurrency=None,
                max_retries=None,
            )
            if not args.run_id or not args.attempt or not args.cpu_namespace or not args.gpu_namespace:
                raise ValueError("child mode is missing its execution envelope")
            receipt = build_provider_child_receipt(
                args.child_provider,
                policy=policy,
                run_id=args.run_id,
                attempt=args.attempt,
                namespace={"cpu": args.cpu_namespace, "gpu": args.gpu_namespace},
                max_rows=policy["limits"]["max_rows"],
                request_timeout_seconds=policy["limits"]["request_timeout_seconds"],
                allow_network=args.allow_network,
                publish_outputs=args.publish_outputs,
            )
            print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
            return 0

        receipt = orchestrate_providers(
            args.providers,
            policy_path=args.policy,
            registry_path=args.registry,
            state_path=args.state_file,
            receipt_path=args.receipt_file,
            execute=args.execute,
            allow_network=args.allow_network,
            publish_outputs=args.publish_outputs,
            run_id=args.run_id,
            max_rows=args.max_rows,
            request_timeout_seconds=args.timeout,
            max_concurrency=args.max_concurrency,
            max_retries=args.max_retries,
        )
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 1 if receipt["status"] == "FAILED_CLOSED" else 0
    except (PolicyValidationError, RegistrySchemaError, ReceiptValidationError, ValueError, OSError):
        print("live source orchestrator rejected the request", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
