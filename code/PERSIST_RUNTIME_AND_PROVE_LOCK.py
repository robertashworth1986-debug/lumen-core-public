import os, json, subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONF = ROOT / "config"
OUT  = ROOT / "out"

ENV_FILE = CONF / "luma_live_keys.env"
LIVE_SOURCES = CONF / "live_sources.json"
REGISTRY = CONF / "live_source_registry.json"
SEED = OUT / "seed_validation_readout.json"
AUDIT = OUT / "engine_truth_audit.json"
PROOF = OUT / "PERSISTED_RUNTIME_LOCK_PROOF.json"

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def parse_env(path):
    env = {}
    p = Path(path)
    if not p.exists():
        return env
    for raw in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env

env_map = parse_env(ENV_FILE)

needed = [
    "KRAKEN_API_KEY","KRAKEN_API_SECRET",
    "ALPACA_API_KEY","ALPACA_API_SECRET",
    "FINNHUB_API_KEY","FRED_API_KEY","EIA_API_KEY","BLS_API_KEY","BEA_API_KEY",
    "CENSUS_API_KEY","NASA_API_KEY","NOAA_API_TOKEN","NREL_API_KEY",
    "EPA_AQS_KEY","EPA_AQS_EMAIL","TWELVE_DATA_API_KEY","MASSIVE_API_KEY",
    "USGS_WATER_API_KEY","WEBHOOK_SHARED_SECRET","ALPHAVANTAGE_API_KEY"
]

present = {k: bool(env_map.get(k, "").strip()) for k in needed}

seed = {}
audit = {}
live = {}
registry = {}

for p, target in [
    (SEED, "seed"),
    (AUDIT, "audit"),
    (LIVE_SOURCES, "live"),
    (REGISTRY, "registry")
]:
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    if target == "seed": seed = data
    elif target == "audit": audit = data
    elif target == "live": live = data
    elif target == "registry": registry = data

proof = {
    "generated_utc": now_utc(),
    "env_file": str(ENV_FILE),
    "keys_found_count": sum(1 for v in present.values() if v),
    "keys_present": present,
    "seed_readiness": seed.get("readiness"),
    "enabled_registry_sources": seed.get("enabled_registry_sources"),
    "measured_sources": seed.get("measured_sources"),
    "adaptive_universe_count": seed.get("adaptive_universe_count"),
    "translated_yearly_value_total": seed.get("translated_yearly_value_total"),
    "selection_source": audit.get("selection_source"),
    "symbol_mode": audit.get("symbol_mode"),
    "engine_symbol": audit.get("engine_symbol"),
    "static_symbol_risk": audit.get("static_symbol_risk"),
    "providers_count": len((live.get("providers") or {})),
    "registry_rows_count": len((registry.get("rows") or []))
}

PROOF.write_text(json.dumps(proof, indent=2), encoding="utf-8")
print("LOCK PROOF WRITTEN:", PROOF)
print("keys_found_count:", proof["keys_found_count"])
print("seed_readiness:", proof["seed_readiness"])
print("enabled_registry_sources:", proof["enabled_registry_sources"])
print("measured_sources:", proof["measured_sources"])
print("adaptive_universe_count:", proof["adaptive_universe_count"])
print("static_symbol_risk:", proof["static_symbol_risk"])