import os, json, re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONF = ROOT / "config"
OUT  = ROOT / "out"

ENV_FILE = CONF / "luma_live_keys.env"
LIVE_SOURCES_JSON = CONF / "live_sources.json"
REGISTRY_JSON = CONF / "live_source_registry.json"
SUMMARY_JSON = OUT / "live_key_routing_summary.json"
SOURCE_TRUTH_JSON = OUT / "source_truth_table.json"
PAPER_RUNTIME_JSON = CONF / "paper_trader_runtime.json"

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def load_json(p, default):
    try:
        if Path(p).exists():
            return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def save_json(p, obj):
    Path(p).write_text(json.dumps(obj, indent=2), encoding="utf-8")


def registry_rows(payload):
    if not isinstance(payload, dict):
        return []
    raw = payload.get("rows")
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    raw = payload.get("sources")
    if isinstance(raw, list):
        normalized = []
        for row in raw:
            if not isinstance(row, dict):
                continue
            normalized.append({
                "source": str(row.get("source", "")).upper(),
                "sector": row.get("sector", "unknown"),
                "status": row.get("status", "MISSING"),
                "rows": int(row.get("rows", 0) or 0),
                "evidence_basis": row.get("evidence_basis", "KEY_ONLY"),
                "dollar_basis": row.get("dollar_basis", "UNMEASURED"),
                "enabled": bool(row.get("enabled", False)),
                "env": row.get("env", ""),
            })
        return normalized
    return []

def parse_env_file(path):
    env = {}
    if not Path(path).exists():
        return env
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env

found = parse_env_file(ENV_FILE)

canonical = {
    "ALPACA": {
        "sector": "broker",
        "env_key": "ALPACA_API_KEY",
        "env_secret": "ALPACA_API_SECRET"
    },
    "ALPHAVANTAGE": {
        "sector": "market_data",
        "env_key": "ALPHAVANTAGE_API_KEY"
    },
    "BEA": {
        "sector": "macro",
        "env_key": "BEA_API_KEY"
    },
    "BLS": {
        "sector": "labor",
        "env_key": "BLS_API_KEY"
    },
    "CENSUS": {
        "sector": "demographic",
        "env_key": "CENSUS_API_KEY"
    },
    "EIA": {
        "sector": "energy",
        "env_key": "EIA_API_KEY"
    },
    "EPA_AQS": {
        "sector": "air_quality",
        "env_key": "EPA_AQS_KEY",
        "env_aux": "EPA_AQS_EMAIL"
    },
    "FINNHUB": {
        "sector": "market_data",
        "env_key": "FINNHUB_API_KEY"
    },
    "FRED": {
        "sector": "rates",
        "env_key": "FRED_API_KEY"
    },
    "KRAKEN": {
        "sector": "crypto_exec",
        "env_key": "KRAKEN_API_KEY",
        "env_secret": "KRAKEN_API_SECRET"
    },
    "MASSIVE": {
        "sector": "market_data",
        "env_key": "MASSIVE_API_KEY"
    },
    "NASA": {
        "sector": "space",
        "env_key": "NASA_API_KEY"
    },
    "NOAA_NCEI": {
        "sector": "weather",
        "env_key": "NOAA_API_TOKEN"
    },
    "NREL": {
        "sector": "energy_lab",
        "env_key": "NREL_API_KEY"
    },
    "TWELVE_DATA": {
        "sector": "market_data",
        "env_key": "TWELVE_DATA_API_KEY"
    },
    "USGS_WATER": {
        "sector": "water",
        "env_key": "USGS_WATER_API_KEY"
    },
    "WEBHOOK": {
        "sector": "internal",
        "env_key": "WEBHOOK_SHARED_SECRET"
    }
}

registry = load_json(REGISTRY_JSON, {})
rows = registry_rows(registry)
old_by_source = {}
for r in rows:
    s = str(r.get("source", "")).strip().upper()
    if s:
        old_by_source[s] = r

new_rows = []
enabled_count = 0
measured_count = 0

for source, meta in canonical.items():
    old = old_by_source.get(source, {})
    env_key = meta.get("env_key")
    env_secret = meta.get("env_secret")
    env_aux = meta.get("env_aux")

    key_present = bool(found.get(env_key))
    secret_present = bool(found.get(env_secret)) if env_secret else True
    aux_present = bool(found.get(env_aux)) if env_aux else True

    fully_present = key_present and secret_present and aux_present

    old_rows = int(old.get("rows", 0) or 0)
    old_evidence = str(old.get("evidence_basis", "KEY_ONLY"))
    old_dollar = str(old.get("dollar_basis", "UNMEASURED"))

    measured = (old_rows > 0) or ("MEASURED" in old_evidence.upper()) or ("MEASURED" in old_dollar.upper())

    if fully_present and measured:
        status = "MEASURED_FILE_MATCH"
        evidence_basis = "MEASURED_FILE_MATCH"
        dollar_basis = "MEASURED"
        enabled = True
    elif fully_present:
        status = "LIVE_KEY_PRESENT"
        evidence_basis = "KEY_ONLY"
        dollar_basis = "UNMEASURED"
        enabled = True
    else:
        status = "MISSING"
        evidence_basis = old_evidence if measured else "KEY_ONLY"
        dollar_basis = old_dollar if measured else "UNMEASURED"
        enabled = False

    row = {
        "source": source,
        "sector": meta["sector"],
        "status": status,
        "rows": old_rows,
        "evidence_basis": evidence_basis,
        "dollar_basis": dollar_basis,
        "last_probe_utc": now_utc(),
        "env": env_key,
        "enabled": enabled
    }

    if env_secret:
        row["secret_env"] = env_secret
    if env_aux:
        row["aux_env"] = env_aux
    row["key_present"] = key_present
    if env_secret:
        row["secret_present"] = secret_present
    if env_aux:
        row["aux_present"] = aux_present

    new_rows.append(row)

    if enabled:
        enabled_count += 1
    if measured:
        measured_count += 1

live_sources = {
    "generated_utc": now_utc(),
    "runtime_symbol": "UNIVERSE",
    "sources": []
}

for r in new_rows:
    item = {
        "source": r["source"],
        "sector": r["sector"],
        "enabled": r["enabled"],
        "status": r["status"],
        "env": r["env"]
    }
    if "secret_env" in r:
        item["secret_env"] = r["secret_env"]
    if "aux_env" in r:
        item["aux_env"] = r["aux_env"]
    live_sources["sources"].append(item)

registry_out = {
    "generated_utc": now_utc(),
    "paper_live_linked": True,
    "rows": new_rows,
    "sources": new_rows,
}

summary = {
    "generated_utc": now_utc(),
    "found_key_names": sorted(found.keys()),
    "enabled_registry_sources": enabled_count,
    "measured_sources": measured_count,
    "missing_sources": [r["source"] for r in new_rows if not r["enabled"]],
    "enabled_sources": [r["source"] for r in new_rows if r["enabled"]],
    "measured_enabled_sources": [r["source"] for r in new_rows if r["enabled"] and r["rows"] > 0],
    "output_files": [
        str(ENV_FILE),
        str(LIVE_SOURCES_JSON),
        str(REGISTRY_JSON),
        str(SUMMARY_JSON),
    ]
}

save_json(LIVE_SOURCES_JSON, live_sources)
save_json(REGISTRY_JSON, registry_out)
save_json(SUMMARY_JSON, summary)
save_json(SOURCE_TRUTH_JSON, {
    "generated_utc": now_utc(),
    "rows": new_rows,
    "sources": new_rows,
})

paper_runtime = load_json(PAPER_RUNTIME_JSON, {})
if isinstance(paper_runtime, dict):
    paper_runtime["enabled_sources_count"] = int(enabled_count)
    paper_runtime["measured_sources_count"] = int(measured_count)
    paper_runtime["last_universe_rebuild_utc"] = now_utc()
    save_json(PAPER_RUNTIME_JSON, paper_runtime)

print("FIXED REGISTRY + LIVE SOURCE MAPPING")
print("ENABLED REGISTRY SOURCES:", enabled_count)
print("MEASURED SOURCES:", measured_count)
print("LIVE_SOURCES_JSON:", LIVE_SOURCES_JSON)
print("REGISTRY_JSON:", REGISTRY_JSON)
print("SUMMARY_JSON:", SUMMARY_JSON)
print("SOURCE_TRUTH_JSON:", SOURCE_TRUTH_JSON)
print("PAPER_RUNTIME_JSON:", PAPER_RUNTIME_JSON)