import json
from pathlib import Path
from datetime import datetime, timezone
import os

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONF = ROOT / "config"
OUT = ROOT / "out"

LIVE_SOURCES_PATH = CONF / "live_sources.json"
REGISTRY_PATH = CONF / "live_source_registry.json"
TRUTH_PATH = OUT / "source_truth_table.json"

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def load_json(path, default=None):
    if default is None:
        default = {}
    p = Path(path)
    if not p.exists():
        return default
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return json.loads(p.read_text(encoding=enc))
        except Exception:
            pass
    return default

def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def env_present(name):
    if not name:
        return False
    v = os.getenv(str(name), "")
    return str(v).strip() != ""

def sector_for(name, env_name=""):
    s = (str(name) + " " + str(env_name)).lower()
    if any(x in s for x in ["sam.gov", "sam_gov", "federal contract", "contract opportunity"]):
        return "federal_contracts"
    if any(x in s for x in ["sba", "small business administration", "8(a)", "hubzone", "set-aside", "set aside"]):
        return "federal_small_business"
    if any(x in s for x in ["implied", "iv", "volatility", "options"]):
        return "market_data"
    if any(x in s for x in ["polygon", "finnhub", "twelve", "alpaca", "equity", "stock", "market"]):
        return "market_data"
    if any(x in s for x in ["kraken", "xbt", "btc", "eth", "sol", "crypto"]):
        return "crypto_exec"
    if any(x in s for x in ["eia", "ercot", "pjm", "miso", "ciso", "nyis", "isne", "generation", "outage", "nuclear", "energy", "grid"]):
        return "energy"
    if any(x in s for x in ["nrel", "lab"]):
        return "energy_lab"
    if any(x in s for x in ["fred", "cpi", "inflation", "dgs", "macro", "rates"]):
        return "macro"
    if any(x in s for x in ["bls", "labor", "unrate"]):
        return "labor"
    if any(x in s for x in ["noaa", "weather", "climate"]):
        return "weather"
    if any(x in s for x in ["usgs", "water", "hydro"]):
        return "water"
    if any(x in s for x in ["nasa", "space"]):
        return "space"
    if any(x in s for x in ["census", "demo", "population"]):
        return "demographic"
    if any(x in s for x in ["epa", "aqs", "air"]):
        return "air_quality"
    return "internal"

def default_est_hour(sector):
    table = {
        "federal_contracts": 812.50,
        "federal_small_business": 575.00,
        "energy": 3913.75,
        "market_data": 646.40,
        "crypto_exec": 959.50,
        "energy_lab": 858.50,
        "macro": 555.50,
        "labor": 343.40,
        "weather": 888.80,
        "water": 505.00,
        "space": 303.00,
        "demographic": 262.60,
        "air_quality": 424.20,
        "internal": 250.00
    }
    return table.get(sector, 250.00)

live_sources = load_json(LIVE_SOURCES_PATH, {})
existing_registry = load_json(REGISTRY_PATH, {})
existing_rows = existing_registry.get("sources", [])

existing_by_name = {}
for row in existing_rows:
    existing_by_name[str(row.get("source", "")).lower()] = row

rebuilt = []

if isinstance(live_sources, dict):
    for source_name, spec in live_sources.items():
        if not isinstance(spec, dict):
            continue

        enabled = bool(spec.get("enabled", False))
        env_name = spec.get("api_key_env") or spec.get("env") or spec.get("api_env") or ""
        source_lower = str(source_name).lower()

        # try to preserve older env field if new one missing
        if not env_name and source_lower in existing_by_name:
            env_name = existing_by_name[source_lower].get("env", "")

        sector = spec.get("sector") or sector_for(source_name, env_name)
        present = env_present(env_name)
        status = "LIVE_KEY_PRESENT" if present else "MISSING"

        old = existing_by_name.get(source_lower, {})
        rows = old.get("rows", 1 if present else 0)
        last_probe = now_utc()

        rebuilt.append({
            "source": str(source_name).upper(),
            "sector": sector,
            "status": status,
            "rows": int(rows),
            "est_dollar_per_hour": float(old.get("est_dollar_per_hour", default_est_hour(sector))),
            "last_probe_utc": last_probe,
            "enabled": enabled
        })

# hard-add important known lanes if env exists but source entry is missing
known = [
    ("ALPACA", "ALPACA_API_KEY", "market_data"),
    ("POLYGON", "POLYGON_API_KEY", "market_data"),
    ("FINNHUB", "FINNHUB_API_KEY", "market_data"),
    ("TWELVE_DATA", "TWELVE_DATA_API_KEY", "market_data"),
    ("KRAKEN_KEY", "KRAKEN_API_KEY", "crypto_exec"),
    ("EIA", "EIA_API_KEY", "energy"),
    ("FRED", "FRED_API_KEY", "macro"),
    ("NOAA_NCEI", "NOAA_API_TOKEN", "weather"),
    ("USGS_WATER", "USGS_WATER_API_KEY", "water"),
    ("NREL", "NREL_API_KEY", "energy_lab"),
    ("NASA", "NASA_API_KEY", "space"),
    ("BLS", "BLS_API_KEY", "labor"),
    ("CENSUS", "CENSUS_API_KEY", "demographic"),
    ("EPA_AQS_KEY", "EPA_AQS_KEY", "air_quality"),
    ("SAM_GOV", "SAM_GOV_API_KEY", "federal_contracts"),
    ("IMPLIED", "IMPLIED_API_KEY", "market_data"),
    ("IMPLIED_VOL", "IMPLIED_VOL_API_KEY", "market_data"),
    ("TRADIER", "TRADIER_API_KEY", "market_data"),
]

already = {str(x.get("source","")).upper() for x in rebuilt}
for src, env_name, sector in known:
    if src in already:
        continue
    if env_present(env_name):
        rebuilt.append({
            "source": src,
            "sector": sector,
            "status": "LIVE_KEY_PRESENT",
            "rows": 1,
            "est_dollar_per_hour": float(default_est_hour(sector)),
            "last_probe_utc": now_utc(),
            "enabled": True
        })

# if no explicit implied key exists, but one of the option-capable market feeds exists, add IMPLIED lane
already = {str(x.get("source","")).upper() for x in rebuilt}
option_capable_envs = ["POLYGON_API_KEY", "FINNHUB_API_KEY", "TRADIER_API_KEY", "ALPACA_API_KEY"]
if "IMPLIED" not in already and any(env_present(e) for e in option_capable_envs):
    rebuilt.append({
        "source": "IMPLIED",
        "sector": "market_data",
        "status": "LIVE_KEY_PRESENT",
        "rows": 1,
        "est_dollar_per_hour": float(default_est_hour("market_data")),
        "last_probe_utc": now_utc(),
        "enabled": True
    })

# always-on public open-data lanes
already = {str(x.get("source","")).upper() for x in rebuilt}
open_data_known = [
    ("SBA_GOV", "federal_small_business"),
]
for src, sector in open_data_known:
    if src in already:
        continue
    rebuilt.append({
        "source": src,
        "sector": sector,
        "status": "PUBLIC_OPEN_DATA",
        "rows": 0,
        "est_dollar_per_hour": float(default_est_hour(sector)),
        "last_probe_utc": now_utc(),
        "enabled": True
    })

# sort for stability
rebuilt = sorted(rebuilt, key=lambda x: (x["sector"], x["source"]))

registry_obj = {
    "generated_utc": now_utc(),
    "sources": rebuilt
}
save_json(REGISTRY_PATH, registry_obj)

enabled_live = [
    r for r in rebuilt
    if bool(r.get("enabled", True)) and str(r.get("status", "")).upper() == "LIVE_KEY_PRESENT"
]

truth_obj = {
    "generated_utc": now_utc(),
    "paper_live_linked": True,
    "sources": enabled_live
}
save_json(TRUTH_PATH, truth_obj)

print("")
print("REGISTRY REBUILD COMPLETE")
print("LIVE_SOURCES_PATH:", LIVE_SOURCES_PATH)
print("REGISTRY_PATH:", REGISTRY_PATH)
print("TRUTH_PATH:", TRUTH_PATH)
print("TOTAL REGISTRY ROWS:", len(rebuilt))
print("ENABLED + LIVE_KEY_PRESENT:", len(enabled_live))
print("IMPLIED PRESENT:", any(str(r.get('source','')).upper() == 'IMPLIED' for r in rebuilt))
print("")
for r in rebuilt:
    print(f"{r['source']:<16} | enabled={str(r['enabled']):<5} | status={r['status']:<16} | sector={r['sector']:<12}")
