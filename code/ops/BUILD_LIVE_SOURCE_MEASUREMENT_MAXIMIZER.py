from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


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


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


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


def hydrate_env() -> dict[str, str]:
    loaded: dict[str, str] = {}
    for path in ENV_FILES:
        loaded.update(load_env_file(path))
    for key, value in loaded.items():
        if value and not os.environ.get(key):
            os.environ[key] = value
    return loaded


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
    for path in ENV_FILES:
        names.update(load_env_file(path).keys())
    values = []
    for name in names:
        value = os.environ.get(name, "")
        if value and len(value) >= 4:
            values.append(value)
    return values


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


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = 20,
) -> tuple[int | None, Any, str]:
    data = None
    req_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        text = response.read().decode("utf-8", errors="ignore")
        try:
            payload = json.loads(text)
        except Exception:
            payload = None
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
        }
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="ignore")
        except Exception:
            body = str(exc)
        return {
            "source": source,
            "http_status": getattr(exc, "code", None),
            "rows": [],
            "probe_ok": False,
            "probe_note": sanitize_text(f"http_error:{body}", env_names),
        }
    except Exception as exc:
        return {
            "source": source,
            "http_status": None,
            "rows": [],
            "probe_ok": False,
            "probe_note": sanitize_text(f"exception:{type(exc).__name__}:{exc}", env_names),
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
    url = (
        "https://api.sam.gov/opportunities/v2/search?"
        f"limit={max_rows}&postedFrom=01/01/2026&postedTo=06/22/2026&api_key={urllib.parse.quote(key)}"
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
    write_json(json_path, snapshot)
    write_json(latest_path, snapshot)
    write_csv(csv_path, rows if isinstance(rows, list) else [])

    return {
        "snapshot_json": str(json_path.relative_to(ROOT)).replace("\\", "/"),
        "snapshot_latest_json": str(latest_path.relative_to(ROOT)).replace("\\", "/"),
        "snapshot_csv": str(csv_path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": digest,
    }


def registry_row(provider: dict[str, Any], result: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    source = str(provider["source"])
    sector = str(provider["sector"])
    env_names = list(provider.get("env_names", []))
    row_count = len(result.get("rows", []) or [])
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
        "dollar_basis": "MEASURED" if measured else "UNMEASURED",
        "constraint_type": provider.get("constraint_type", ""),
        "money_drain_mode": provider.get("money_drain_mode", ""),
        "formula_basis": "bounded_log_translation_if_measured_else_zero",
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
    old_rows = existing.get("rows", []) if isinstance(existing.get("rows"), list) else []
    merged: dict[str, dict[str, Any]] = {}
    for row in old_rows:
        if isinstance(row, dict) and row.get("source"):
            merged[str(row["source"]).upper()] = dict(row)
    for row in rows:
        merged[str(row["source"]).upper()] = dict(row)
    ordered = sorted(merged.values(), key=lambda item: str(item.get("source", "")))
    return {
        "generated_utc": now_utc(),
        "paper_live_linked": True,
        "rows": ordered,
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
                "value_basis": "MEASURED" if row.get("measured") else "UNMEASURED",
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
        "coverage_pct": round((len(measured) / len(enabled) * 100.0) if enabled else 0.0, 2),
        "measured_source_names": [str(row.get("source")) for row in measured],
        "failed_or_thin_source_names": [str(row.get("source")) for row in failed],
        "by_sector": by_sector,
        "claim_boundary": (
            "This pass proves fresh measured rows and hashes. It does not prove realized savings, "
            "field validation, trading profit, or guaranteed award value."
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
        f"- Estimated annual value surface: ${summary['estimated_annual_value_surface_usd']:,.2f}",
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


def run_measurement(max_rows: int, timeout: int) -> dict[str, Any]:
    hydrate_env()
    tag = now_tag()
    provider_rows = []

    for provider in PROVIDERS:
        env_names = list(provider.get("env_names", []))
        collector = provider["collector"]
        result = safe_request(
            str(provider["source"]),
            env_names,
            lambda provider=provider, collector=collector: collector(max_rows, timeout),
        )
        artifact = snapshot_provider(provider, result, tag=tag)
        provider_rows.append(registry_row(provider, result, artifact))

    registry = merge_registry(read_json(REGISTRY_JSON), provider_rows)
    live_sources = live_sources_from_registry(registry)
    source_truth = source_truth_from_registry(registry)
    summary = build_summary(registry["rows"])

    payload = {
        "generated_utc": now_utc(),
        "schema": "live_source_measurement_maximizer_v1",
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

    write_json(REGISTRY_JSON, registry)
    write_json(LIVE_SOURCES_JSON, live_sources)
    write_json(SOURCE_TRUTH_JSON, source_truth)
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Pull bounded live snapshots from every configured source.")
    parser.add_argument("--max-rows", type=int, default=25)
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    payload = run_measurement(max(1, args.max_rows), max(3, args.timeout))
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "enabled_sources": payload["summary"]["enabled_sources"],
                "measured_sources": payload["summary"]["measured_sources"],
                "failed_or_thin_sources": payload["summary"]["failed_or_thin_sources"],
                "total_measured_rows": payload["summary"]["total_measured_rows"],
                "output": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
