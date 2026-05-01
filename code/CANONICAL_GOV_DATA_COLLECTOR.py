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

ENV_CANDIDATES = [
    CONF / "luma_live_keys.env",
    ROOT / "code" / "execution" / "config" / "luma_live_keys.env",
    ROOT / ".env.live",
    ROOT / ".env.sports",
]

ENV_ALIASES = {
    "FRED_API_KEY": ["FRED_API_KEY", "FRED_KEY"],
    "EIA_API_KEY": ["EIA_API_KEY", "EIA_KEY"],
    "NOAA_API_TOKEN": ["NOAA_API_TOKEN", "NCDC_NOAA_API_TOKEN", "NOAA_TOKEN"],
    "CENSUS_API_KEY": ["CENSUS_API_KEY", "CENSUS_KEY"],
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    url = (
        "https://www.ncei.noaa.gov/cdo-web/api/v2/data?datasetid=GHCND"
        "&locationid=FIPS:37&startdate=2025-01-01&enddate=2025-01-31&limit=200"
    )
    headers = {"token": token}
    try:
        code, data = http_get_json(url, headers=headers)
        rows = len(data.get("results", []))
        snap = SNAP_DIR / f"noaa_ghcnd_{int(time.time())}.json"
        snap.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return {"source": "NOAA", "ok": code == 200, "rows": rows, "snapshot": str(snap), "url": url}
    except Exception as e:
        return {"source": "NOAA", "ok": False, "rows": 0, "error": str(e), "url": url}


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

    checks = [
        fetch_fred(env),
        fetch_usgs(),
        fetch_noaa(env),
        fetch_census(env),
        fetch_eia(env),
    ]

    ok_count = sum(1 for c in checks if c.get("ok"))
    rows = sum(int(c.get("rows", 0) or 0) for c in checks)

    payload = {
        "generated_utc": now_utc(),
        "collector": "canonical_gov_live",
        "sources_ok": ok_count,
        "sources_total": len(checks),
        "rows_total": rows,
        "checks": checks,
    }
    SUMMARY_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[GOV] wrote {SUMMARY_PATH}")
    print(f"[GOV] sources_ok={ok_count}/{len(checks)} rows_total={rows}")
    return payload


if __name__ == "__main__":
    main()
