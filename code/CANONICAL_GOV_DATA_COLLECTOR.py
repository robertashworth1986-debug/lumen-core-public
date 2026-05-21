from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
CONF = ROOT / "config"
SNAP_DIR = OUT / "gov_live_snapshots"
SUMMARY_PATH = OUT / "gov_live_canonical_summary.json"
REGISTRY_PATH = CONF / "live_source_registry.json"

ENV_CANDIDATES = [
    CONF / "luma_live_keys.env",
    ROOT / "code" / "execution" / "config" / "luma_live_keys.env",
    ROOT / ".env.live",
    ROOT / ".env.sports",
]

ENV_ALIASES = {
    "FRED_API_KEY": ["FRED_API_KEY", "FRED_KEY", "FRED_API_KEY_PREMIUM"],
    "EIA_API_KEY": ["EIA_API_KEY", "EIA_KEY", "EIA_API_KEY_PREMIUM"],
    "NOAA_API_TOKEN": ["NOAA_API_TOKEN", "NCDC_NOAA_API_TOKEN", "NOAA_TOKEN", "NOAA_NCEI_TOKEN", "NOAA_NCEI_API_TOKEN"],
    "CENSUS_API_KEY": ["CENSUS_API_KEY", "CENSUS_KEY"],
    "BLS_API_KEY": ["BLS_API_KEY"],
    "NASA_API_KEY": ["NASA_API_KEY"],
    "NREL_API_KEY": ["NREL_API_KEY"],
    "BEA_API_KEY": ["BEA_API_KEY"],
    "EPA_AQS_KEY": ["EPA_AQS_KEY", "AQS_KEY", "EPA_AQS_TOKEN"],
    "EPA_AQS_EMAIL": ["EPA_AQS_EMAIL"],
}

GOV_SOURCES = {
    "FRED",
    "USGS",
    "USGS_WATER",
    "NOAA",
    "NOAA_NCEI",
    "CENSUS",
    "EIA",
    "BLS",
    "NASA",
    "NREL",
    "EPA_AQS",
    "BEA",
}

GOV_SOURCE_HINTS = (
    "NOAA",
    "USGS",
    "EPA",
    "FRED",
    "BLS",
    "CENSUS",
    "EIA",
    "NASA",
    "NREL",
    "BEA",
    "DOE",
    "DOT",
    "USDA",
    "HUD",
    "HHS",
    "CDC",
    "NIST",
    "DOL",
    "VA",
    "SSA",
)

GOV_SECTOR_HINTS = {
    "energy",
    "energy_lab",
    "rates",
    "macro",
    "demographic",
    "labor",
    "weather",
    "water",
    "air_quality",
    "space",
    "public_health",
    "transport",
    "housing",
}

SENSITIVE_QUERY_KEYS = {
    "api_key",
    "apikey",
    "email",
    "key",
    "token",
    "access_token",
    "registrationkey",
    "userid",
    "user_id",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def redact_url(url: str) -> str:
    if not url:
        return url
    try:
        parsed = urllib.parse.urlsplit(url)
        query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        safe_pairs = []
        for key, value in query_pairs:
            if key.strip().lower() in SENSITIVE_QUERY_KEYS:
                safe_pairs.append((key, "REDACTED"))
            else:
                safe_pairs.append((key, value))
        safe_query = urllib.parse.urlencode(safe_pairs, doseq=True)
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, safe_query, parsed.fragment))
    except Exception:
        return url


def redact_text_secrets(text: str) -> str:
    if not text:
        return text
    redacted = text
    patterns = (
        "api_key",
        "apikey",
        "key",
        "token",
        "access_token",
        "registrationkey",
        "userid",
        "user_id",
    )
    for token in patterns:
        redacted = redacted.replace(f"{token}=", f"{token}=REDACTED_")
        redacted = redacted.replace(f"{token.upper()}=", f"{token.upper()}=REDACTED_")
    return redacted


def sanitize_check_row(row: dict) -> dict:
    cleaned = dict(row)
    if "url" in cleaned:
        cleaned["url"] = redact_url(str(cleaned.get("url", "")))
    if "error" in cleaned:
        cleaned["error"] = redact_text_secrets(str(cleaned.get("error", "")))
    return cleaned


def load_env() -> dict:
    env = {k: v for k, v in os.environ.items() if isinstance(v, str) and v.strip()}
    for path in ENV_CANDIDATES:
        if path.exists():
            for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    for canonical, aliases in ENV_ALIASES.items():
        for alias in aliases:
            value = (env.get(alias) or "").strip()
            if value:
                env[canonical] = value
                break
    return env


def http_get_json(url: str, headers: dict | None = None, timeout: int = 25):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "LumenCore/CanonicalCollector"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", errors="ignore")
        return r.getcode(), json.loads(raw)


def fetch_fred(env: dict) -> dict:
    key = env.get("FRED_API_KEY", "")
    if not key:
        return {"source": "FRED", "ok": False, "rows": 0, "note": "missing FRED_API_KEY"}
    params = {
        "series_id": "UNRATE",
        "api_key": key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 240,
    }
    url = "https://api.stlouisfed.org/fred/series/observations?" + urllib.parse.urlencode(params)
    try:
        code, data = http_get_json(url)
        rows = len(data.get("observations", []))
        snap = SNAP_DIR / f"fred_unrate_{int(time.time())}.json"
        snap.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return {"source": "FRED", "ok": code == 200, "rows": rows, "snapshot": str(snap), "url": url}
    except Exception as e:
        return {"source": "FRED", "ok": False, "rows": 0, "error": str(e), "url": url}


def fetch_usgs() -> dict:
    url = (
        "https://waterservices.usgs.gov/nwis/iv/?format=json&sites=01646500"
        "&parameterCd=00060,00065&period=P7D"
    )
    try:
        code, data = http_get_json(url)
        series = data.get("value", {}).get("timeSeries", [])
        rows = 0
        for s in series:
            rows += len(s.get("values", [{}])[0].get("value", []))
        snap = SNAP_DIR / f"usgs_iv_{int(time.time())}.json"
        snap.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return {"source": "USGS", "ok": code == 200, "rows": rows, "snapshot": str(snap), "url": url}
    except Exception as e:
        return {"source": "USGS", "ok": False, "rows": 0, "error": str(e), "url": url}


def fetch_noaa(env: dict) -> dict:
    token = env.get("NOAA_API_TOKEN") or env.get("NCDC_NOAA_API_TOKEN")
    if not token:
        return {"source": "NOAA", "ok": False, "rows": 0, "note": "missing NOAA token"}
    # Lightweight live probe endpoint to reduce timeout risk while remaining measured.
    url = "https://www.ncei.noaa.gov/cdo-web/api/v2/datasets?limit=10"
    headers = {"token": token}
    try:
        code, data = http_get_json(url, headers=headers)
        rows = len(data.get("results", []))
        snap = SNAP_DIR / f"noaa_datasets_{int(time.time())}.json"
        snap.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return {"source": "NOAA", "ok": code == 200, "rows": rows, "snapshot": str(snap), "url": url}
    except Exception as e:
        return {"source": "NOAA", "ok": False, "rows": 0, "error": str(e), "url": url}


def fetch_bls(env: dict) -> dict:
    key = env.get("BLS_API_KEY", "").strip()
    if not key:
        return {"source": "BLS", "ok": False, "rows": 0, "note": "missing BLS_API_KEY"}
    url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
    payload = {
        "seriesid": ["LNS14000000"],
        "startyear": "2024",
        "endyear": "2026",
        "registrationkey": key,
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "LumenCore/CanonicalCollector",
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            data = json.loads(raw)
            series = data.get("Results", {}).get("series", [])
            rows = len(series[0].get("data", [])) if series else 0
            snap = SNAP_DIR / f"bls_unrate_{int(time.time())}.json"
            snap.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return {"source": "BLS", "ok": resp.getcode() == 200, "rows": rows, "snapshot": str(snap), "url": url}
    except Exception as e:
        return {"source": "BLS", "ok": False, "rows": 0, "error": str(e), "url": url}


def fetch_nasa(env: dict) -> dict:
    key = env.get("NASA_API_KEY", "").strip()
    if not key:
        return {"source": "NASA", "ok": False, "rows": 0, "note": "missing NASA_API_KEY"}
    url = "https://api.nasa.gov/planetary/apod?api_key=" + urllib.parse.quote(key)
    try:
        code, data = http_get_json(url)
        rows = 1 if isinstance(data, dict) and data else 0
        snap = SNAP_DIR / f"nasa_apod_{int(time.time())}.json"
        snap.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return {"source": "NASA", "ok": code == 200, "rows": rows, "snapshot": str(snap), "url": url}
    except Exception as e:
        return {"source": "NASA", "ok": False, "rows": 0, "error": str(e), "url": url}


def fetch_nrel(env: dict) -> dict:
    key = env.get("NREL_API_KEY", "").strip()
    if not key:
        return {"source": "NREL", "ok": False, "rows": 0, "note": "missing NREL_API_KEY"}
    url = (
        "https://developer.nrel.gov/api/solar/solar_resource/v1.json?api_key="
        + urllib.parse.quote(key)
        + "&lat=36.17&lon=-86.78"
    )
    try:
        code, data = http_get_json(url)
        outputs = data.get("outputs", {}) if isinstance(data, dict) else {}
        rows = len(outputs.keys()) if isinstance(outputs, dict) else 0
        snap = SNAP_DIR / f"nrel_solar_{int(time.time())}.json"
        snap.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return {"source": "NREL", "ok": code == 200, "rows": rows, "snapshot": str(snap), "url": url}
    except Exception as e:
        return {"source": "NREL", "ok": False, "rows": 0, "error": str(e), "url": url}


def fetch_epa_aqs(env: dict) -> dict:
    key = env.get("EPA_AQS_KEY", "").strip()
    email = env.get("EPA_AQS_EMAIL", "").strip()
    if not key or not email:
        return {"source": "EPA_AQS", "ok": False, "rows": 0, "note": "missing EPA_AQS credentials"}
    url = (
        "https://aqs.epa.gov/data/api/list/states?email="
        + urllib.parse.quote(email)
        + "&key="
        + urllib.parse.quote(key)
    )
    try:
        code, data = http_get_json(url)
        rows = len(data.get("Data", [])) if isinstance(data, dict) else 0
        snap = SNAP_DIR / f"epa_aqs_states_{int(time.time())}.json"
        snap.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return {"source": "EPA_AQS", "ok": code == 200, "rows": rows, "snapshot": str(snap), "url": url}
    except Exception as e:
        return {"source": "EPA_AQS", "ok": False, "rows": 0, "error": str(e), "url": url}


def fetch_bea(env: dict) -> dict:
    key = env.get("BEA_API_KEY", "").strip()
    if not key:
        return {"source": "BEA", "ok": False, "rows": 0, "note": "missing BEA_API_KEY"}
    url = (
        "https://apps.bea.gov/api/data/?UserID="
        + urllib.parse.quote(key)
        + "&method=GETDATASETLIST&ResultFormat=JSON"
    )
    try:
        code, data = http_get_json(url)
        rows = len((data.get("BEAAPI", {}).get("Results", {}).get("Dataset", [])))
        snap = SNAP_DIR / f"bea_dataset_list_{int(time.time())}.json"
        snap.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return {"source": "BEA", "ok": code == 200, "rows": rows, "snapshot": str(snap), "url": url}
    except Exception as e:
        return {"source": "BEA", "ok": False, "rows": 0, "error": str(e), "url": url}


def load_registry_gov_rows() -> list[dict]:
    if not REGISTRY_PATH.exists():
        return []
    try:
        payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        rows = []

    out: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        src = str(row.get("source", "")).upper()
        sector = str(row.get("sector", "")).strip().lower()
        env_blob = str(row.get("env", "")).upper()
        inferred_gov = (
            src in GOV_SOURCES
            or any(hint in src for hint in GOV_SOURCE_HINTS)
            or sector in GOV_SECTOR_HINTS
            or any(hint in env_blob for hint in GOV_SOURCE_HINTS)
        )
        if not inferred_gov:
            continue
        probe_ok = bool(row.get("probe_ok", False))
        measured = bool(row.get("measured", False))
        ok = probe_ok or measured
        out.append(
            {
                "source": src,
                "ok": ok,
                "rows": int(row.get("rows", 0) or 0),
                "probe_ok": probe_ok,
                "measured": measured,
                "probe_note": str(row.get("probe_note", "")),
                "basis": "registry_live_probe",
            }
        )
    return out


def fetch_census(env: dict) -> dict:
    key = env.get("CENSUS_API_KEY", "")
    if not key:
        return {"source": "CENSUS", "ok": False, "rows": 0, "note": "missing CENSUS_API_KEY"}
    url = (
        "https://api.census.gov/data/2023/acs/acs1?get=NAME,B01001_001E&for=state:*&key="
        + urllib.parse.quote(key)
    )
    try:
        code, data = http_get_json(url)
        rows = max(0, len(data) - 1) if isinstance(data, list) else 0
        snap = SNAP_DIR / f"census_acs_{int(time.time())}.json"
        snap.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return {"source": "CENSUS", "ok": code == 200, "rows": rows, "snapshot": str(snap), "url": url}
    except Exception as e:
        return {"source": "CENSUS", "ok": False, "rows": 0, "error": str(e), "url": url}


def fetch_eia(env: dict) -> dict:
    key = env.get("EIA_API_KEY", "")
    if not key:
        return {"source": "EIA", "ok": False, "rows": 0, "note": "missing EIA_API_KEY"}
    url = (
        "https://api.eia.gov/v2/electricity/rto/region-data/data/?"
        "frequency=hourly&data[0]=value&facets[type][]=D&facets[respondent][]=MISO"
        "&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=500"
        f"&api_key={urllib.parse.quote(key)}"
    )
    try:
        code, data = http_get_json(url)
        rows = len(data.get("response", {}).get("data", []))
        snap = SNAP_DIR / f"eia_rto_{int(time.time())}.json"
        snap.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return {"source": "EIA", "ok": code == 200, "rows": rows, "snapshot": str(snap), "url": url}
    except Exception as e:
        return {"source": "EIA", "ok": False, "rows": 0, "error": str(e), "url": url}


def main() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    env = load_env()

    direct_checks = [
        fetch_fred(env),
        fetch_usgs(),
        fetch_noaa(env),
        fetch_census(env),
        fetch_eia(env),
        fetch_bls(env),
        fetch_nasa(env),
        fetch_nrel(env),
        fetch_epa_aqs(env),
        fetch_bea(env),
    ]

    by_source: dict[str, dict] = {str(c.get("source", "")).upper(): c for c in direct_checks}
    for row in load_registry_gov_rows():
        src = str(row.get("source", "")).upper()
        existing = by_source.get(src)
        if existing is None:
            by_source[src] = row
            continue
        # Keep registry row only when direct probe failed and registry has measured/probe evidence.
        if (not bool(existing.get("ok", False))) and bool(row.get("ok", False)):
            by_source[src] = row

    checks = list(by_source.values())

    ok_count = sum(1 for c in checks if c.get("ok"))
    rows = sum(int(c.get("rows", 0) or 0) for c in checks)

    payload = {
        "generated_utc": now_utc(),
        "collector": "canonical_gov_live",
        "sources_ok": ok_count,
        "sources_total": len(checks),
        "rows_total": rows,
        "env_keys_detected": sorted([k for k in env.keys() if k.endswith("_KEY") or k.endswith("_TOKEN")]),
        "checks": [sanitize_check_row(c) for c in checks],
    }
    SUMMARY_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[GOV] wrote {SUMMARY_PATH}")
    print(f"[GOV] sources_ok={ok_count}/{len(checks)} rows_total={rows}")
    return payload


if __name__ == "__main__":
    main()
