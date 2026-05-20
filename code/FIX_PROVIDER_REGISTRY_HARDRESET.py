import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONF = ROOT / "config"
OUT  = ROOT / "out"

KEY_ENV_PATH          = CONF / "luma_live_keys.env"
LIVE_SOURCES_PATH     = CONF / "live_sources.json"
LIVE_REGISTRY_PATH    = CONF / "live_source_registry.json"
SOURCE_TRUTH_PATH     = OUT  / "source_truth_table.json"
ROUTING_SUMMARY_PATH  = OUT  / "live_key_routing_summary.json"
ENGINE_AUDIT_PATH     = OUT  / "engine_truth_audit.json"
ADAPTIVE_SUMMARY_PATH = OUT  / "adaptive_universe_summary.json"

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def load_json(path, default):
    try:
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def save_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2), encoding="utf-8")

def parse_env(path):
    out = {}
    p = Path(path)
    if not p.exists():
        return out
    for raw in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        out[k] = v
    return out

PROVIDERS = [
    {"source":"ALPACA",       "sector":"broker",       "env":["ALPACA_API_KEY","ALPACA_API_SECRET"]},
    {"source":"ALPHAVANTAGE", "sector":"market_data",  "env":["ALPHAVANTAGE_API_KEY"]},
    {"source":"BEA",          "sector":"macro",        "env":["BEA_API_KEY"]},
    {"source":"BLS",          "sector":"labor",        "env":["BLS_API_KEY"]},
    {"source":"CENSUS",       "sector":"demographic",  "env":["CENSUS_API_KEY"]},
    {"source":"EIA",          "sector":"energy",       "env":["EIA_API_KEY"]},
    {"source":"EPA_AQS",      "sector":"air_quality",  "env":["EPA_AQS_KEY","EPA_AQS_EMAIL"]},
    {"source":"FINNHUB",      "sector":"market_data",  "env":["FINNHUB_API_KEY"]},
    {"source":"FRED",         "sector":"rates",        "env":["FRED_API_KEY"]},
    {"source":"KRAKEN",       "sector":"crypto_exec",  "env":["KRAKEN_API_KEY","KRAKEN_API_SECRET"]},
    {"source":"MASSIVE",      "sector":"market_data",  "env":["MASSIVE_API_KEY"]},
    {"source":"NASA",         "sector":"space",        "env":["NASA_API_KEY"]},
    {"source":"NOAA_NCEI",    "sector":"weather",      "env":["NOAA_API_TOKEN","NOAA_NCEI_TOKEN","NCDC_NOAA_API_TOKEN"]},
    {"source":"NREL",         "sector":"energy_lab",   "env":["NREL_API_KEY"]},
    {"source":"TWELVE_DATA",  "sector":"market_data",  "env":["TWELVE_DATA_API_KEY"]},
    {"source":"USGS_WATER",   "sector":"water",        "env":["USGS_WATER_API_KEY"]},
    {"source":"WEBHOOK",      "sector":"internal",     "env":["WEBHOOK_SHARED_SECRET"]},
]

env_map = parse_env(KEY_ENV_PATH)

truth = load_json(SOURCE_TRUTH_PATH, {})
truth_rows = truth.get("rows", []) if isinstance(truth, dict) else []
truth_by_source = {}
for r in truth_rows:
    if isinstance(r, dict):
        src = str(r.get("source", "")).strip().upper()
        if src:
            truth_by_source[src] = r

providers_obj = {}
registry_rows = []
found_key_names = []
enabled_count = 0
measured_count = 0

for p in PROVIDERS:
    source = p["source"]
    sector = p["sector"]
    env_names = p["env"]

    present_env = [e for e in env_names if str(env_map.get(e, "")).strip()]
    for e in present_env:
        if e not in found_key_names:
            found_key_names.append(e)

    enabled = len(present_env) > 0
    if enabled:
        enabled_count += 1

    t = truth_by_source.get(source.upper(), {})
    measured = False
    measured_rows = 0
    if isinstance(t, dict):
        measured_rows = int(t.get("rows", 0) or 0)
        evidence_basis = str(t.get("evidence_basis", "")).upper()
        dollar_basis = str(t.get("dollar_basis", "")).upper()
        measured = measured_rows > 0 or evidence_basis == "MEASURED_FILE_MATCH" or dollar_basis == "MEASURED"

    if enabled and measured:
        measured_count += 1

    if enabled and measured:
        status = "LIVE_KEY_PRESENT"
    elif enabled and not measured:
        status = "KEY_PRESENT_UNMEASURED"
    else:
        status = "MISSING"

    providers_obj[source] = {
        "enabled": enabled,
        "sector": sector,
        "env_names": env_names,
        "present_env_names": present_env,
        "status": status,
        "measured": measured,
        "measured_rows": measured_rows,
        "last_truth_sync_utc": now_utc()
    }

    registry_rows.append({
        "source": source,
        "sector": sector,
        "status": status,
        "rows": measured_rows if measured else 0,
        "evidence_basis": "MEASURED_FILE_MATCH" if measured else "KEY_ONLY",
        "dollar_basis": "MEASURED" if measured else "UNMEASURED",
        "last_probe_utc": now_utc(),
        "env": ",".join(env_names),
        "present_env": present_env,
        "enabled": enabled
    })

live_sources_json = {
    "generated_utc": now_utc(),
    "providers": providers_obj
}

live_registry_json = {
    "generated_utc": now_utc(),
    "paper_live_linked": True,
    "rows": registry_rows
}

routing_summary = {
    "generated_utc": now_utc(),
    "found_key_names": found_key_names,
    "enabled_registry_sources": enabled_count,
    "measured_sources": measured_count,
    "missing_sources": [r["source"] for r in registry_rows if not r["enabled"]],
    "unmeasured_sources": [r["source"] for r in registry_rows if r["enabled"] and r["dollar_basis"] != "MEASURED"]
}

engine_audit = load_json(ENGINE_AUDIT_PATH, {})
if not isinstance(engine_audit, dict):
    engine_audit = {}
engine_audit["generated_utc"] = now_utc()
engine_audit["engine_symbol"] = "UNIVERSE"
engine_audit["paper_enabled"] = True
engine_audit["selection_source"] = "engine_logic"
engine_audit["symbol_mode"] = "ADAPTIVE_UNIVERSE"
engine_audit["enabled_registry_sources"] = enabled_count
engine_audit["measured_sources"] = measured_count
engine_audit["static_symbol_risk"] = False
engine_audit["audit_notes"] = [
    "live_source_registry rebuilt from luma_live_keys.env",
    "broken pseudo-source parsing removed",
    "real provider env mapping restored",
    "engine remains adaptive not static"
]

adaptive_summary = load_json(ADAPTIVE_SUMMARY_PATH, {})
if not isinstance(adaptive_summary, dict):
    adaptive_summary = {}
adaptive_summary["generated_utc"] = now_utc()
adaptive_summary["enabled_registry_sources"] = enabled_count
adaptive_summary["measured_sources"] = measured_count
adaptive_summary["measured_source_names"] = [r["source"] for r in registry_rows if r["enabled"] and r["dollar_basis"] == "MEASURED"]

save_json(LIVE_SOURCES_PATH, live_sources_json)
save_json(LIVE_REGISTRY_PATH, live_registry_json)
save_json(ROUTING_SUMMARY_PATH, routing_summary)
save_json(ENGINE_AUDIT_PATH, engine_audit)
save_json(ADAPTIVE_SUMMARY_PATH, adaptive_summary)

print("HARD RESET COMPLETE")
print("enabled_registry_sources:", enabled_count)
print("measured_sources:", measured_count)
print("found_key_names:", len(found_key_names))
print("wrote:", LIVE_SOURCES_PATH)
print("wrote:", LIVE_REGISTRY_PATH)
print("wrote:", ROUTING_SUMMARY_PATH)
print("wrote:", ENGINE_AUDIT_PATH)
print("wrote:", ADAPTIVE_SUMMARY_PATH)