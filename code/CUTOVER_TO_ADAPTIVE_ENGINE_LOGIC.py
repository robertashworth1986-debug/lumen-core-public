import json, re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONF = ROOT / "config"
OUT  = ROOT / "out"

RUNTIME_CONTROL = CONF / "runtime_control.json"
PAPER_RUNTIME   = CONF / "paper_trader_runtime.json"
LIVE_REGISTRY   = CONF / "live_source_registry.json"
LIVE_SOURCES    = CONF / "live_sources.json"
SOURCE_TRUTH    = OUT  / "source_truth_table.json"

ADAPTIVE_UNIVERSE = OUT / "adaptive_universe.json"
UNIVERSE_AUDIT    = OUT / "adaptive_universe_audit.json"
ENGINE_AUDIT      = OUT / "engine_truth_audit.json"

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

def norm(x):
    return re.sub(r"[^a-z0-9]+", "_", str(x).lower()).strip("_")

def source_to_candidates(source, sector):
    s = norm(source)
    sec = norm(sector)
    out = []

    if s == "alpaca" or sec == "broker":
        out += ["SPY","QQQ","IWM","DIA","AAPL","MSFT","NVDA","AMD","META","AMZN","GOOGL","AVGO","SMCI","PLTR","NFLX","TSLA"]
    if s == "finnhub" or s == "massive" or s == "twelve_data" or sec == "market_data":
        out += ["SPY","QQQ","IWM","DIA","AAPL","MSFT","NVDA","AMD","META","AMZN","GOOGL","AVGO","SMCI","PLTR","NFLX","TSLA"]
    if s == "kraken" or sec == "crypto_exec":
        out += ["XBTUSD","ETHUSD","SOLUSD","XRPUSD","ADAUSD","AVAXUSD","DOGEUSD","LINKUSD","MATICUSD","DOTUSD"]
    if s == "fred" or sec == "rates":
        out += ["DGS10","DGS2","UNRATE","CPIAUCSL"]
    if s == "eia" or sec == "energy":
        out += ["EIA_POWER_GRID","EIA_NUCLEAR_OUTAGE","EIA_ISO_LOAD","EIA_GAS_POWER"]
    if s == "bls" or sec == "labor":
        out += ["BLS_UNRATE","BLS_PAYROLLS","BLS_CPI_CORE"]
    if s == "bea" or sec == "macro":
        out += ["BEA_GDP","BEA_PCE","BEA_INCOME"]
    if s == "census" or sec == "demographic":
        out += ["CENSUS_POP","CENSUS_HOUSING","CENSUS_INCOME"]
    if s == "nasa" or sec == "space":
        out += ["NASA_SOLAR","NASA_SPACE_WEATHER"]
    if s == "noaa_ncei" or sec == "weather":
        out += ["NOAA_TEMP","NOAA_STORMS","NOAA_PRECIP"]
    if s == "nrel" or sec == "energy_lab":
        out += ["NREL_SOLAR","NREL_WIND","NREL_GRID"]
    if s == "usgs_water" or sec == "water":
        out += ["USGS_STREAMFLOW","USGS_WATER_LEVEL","USGS_DROUGHT"]
    if s == "epa_aqs" or sec == "air_quality":
        out += ["EPA_PM25","EPA_OZONE","EPA_AQI"]

    dedup = []
    seen = set()
    for item in out:
        if item not in seen:
            seen.add(item)
            dedup.append(item)
    return dedup

runtime = load_json(RUNTIME_CONTROL, {})
paper   = load_json(PAPER_RUNTIME, {})
registry = load_json(LIVE_REGISTRY, {})
live_sources = load_json(LIVE_SOURCES, {})
truth = load_json(SOURCE_TRUTH, {})

rows = registry.get("rows", []) if isinstance(registry, dict) else []
truth_rows = truth.get("rows", []) if isinstance(truth, dict) else []

# Build adaptive universe only from enabled/measured/key-present sources
universe = []
sector_rollup = {}
enabled_sources = []
measured_sources = []

for r in rows:
    if not isinstance(r, dict):
        continue
    source = str(r.get("source","")).strip()
    sector = str(r.get("sector","unknown")).strip()
    status = str(r.get("status","")).strip().upper()
    row_count = int(r.get("rows",0) or 0)

    if status in ("LIVE_KEY_PRESENT","KEY_PRESENT_UNMEASURED"):
        enabled_sources.append(source)

        if row_count > 0:
            measured_sources.append(source)

        cands = source_to_candidates(source, sector)
        for sym in cands:
            universe.append({
                "symbol": sym,
                "source": source,
                "sector": sector,
                "status": status,
                "measured_rows": row_count
            })

        sector_rollup.setdefault(sector, {"sources":0,"rows":0})
        sector_rollup[sector]["sources"] += 1
        sector_rollup[sector]["rows"] += row_count

# dedup universe by symbol, keep strongest measured_rows
best = {}
for item in universe:
    sym = item["symbol"]
    if sym not in best or item["measured_rows"] > best[sym]["measured_rows"]:
        best[sym] = item
universe = sorted(best.values(), key=lambda x: (-x["measured_rows"], x["symbol"]))

# Hard cutover away from static basket
paper["paper_enabled"] = True
paper["symbol_mode"] = "ADAPTIVE_UNIVERSE"
paper["selection_source"] = "engine_logic"
paper["adaptive_universe_file"] = str(ADAPTIVE_UNIVERSE)
paper["symbols"] = []
paper["static_symbols"] = []
paper["legacy_symbols"] = []
paper["manual_symbols"] = []
paper["universe_symbols"] = [x["symbol"] for x in universe]
paper["universe_count"] = len(universe)
paper["enabled_sources_count"] = len(enabled_sources)
paper["measured_sources_count"] = len(measured_sources)
paper["last_universe_rebuild_utc"] = now_utc()

runtime["mode"] = "paper"
runtime["allow_live_orders"] = False
runtime["kill_switch"] = False
runtime["symbol"] = "UNIVERSE"

save_json(PAPER_RUNTIME, paper)
save_json(RUNTIME_CONTROL, runtime)

adaptive_payload = {
    "generated_utc": now_utc(),
    "builder": "engine_logic",
    "selection_mode": "adaptive_from_registry",
    "enabled_sources": enabled_sources,
    "measured_sources": measured_sources,
    "sector_rollup": sector_rollup,
    "symbols": universe
}
save_json(ADAPTIVE_UNIVERSE, adaptive_payload)

static_symbol_risk = False
notes = []

if runtime.get("symbol") != "UNIVERSE":
    static_symbol_risk = True
    notes.append(f"runtime_control.symbol={runtime.get('symbol')}")

for field in ["symbols","static_symbols","legacy_symbols","manual_symbols"]:
    vals = paper.get(field, [])
    if isinstance(vals, list) and len(vals) > 0:
        static_symbol_risk = True
        notes.append(f"{field}_count={len(vals)}")

if paper.get("selection_source") != "engine_logic":
    static_symbol_risk = True
    notes.append(f"selection_source={paper.get('selection_source')}")

if paper.get("symbol_mode") != "ADAPTIVE_UNIVERSE":
    static_symbol_risk = True
    notes.append(f"symbol_mode={paper.get('symbol_mode')}")

audit = {
    "generated_utc": now_utc(),
    "engine_symbol": runtime.get("symbol"),
    "paper_enabled": paper.get("paper_enabled"),
    "selection_source": paper.get("selection_source"),
    "symbol_mode": paper.get("symbol_mode"),
    "enabled_registry_sources": len(enabled_sources),
    "measured_sources": len(measured_sources),
    "adaptive_universe_count": len(universe),
    "static_symbol_risk": static_symbol_risk,
    "audit_notes": notes if notes else ["static basket cleared; engine now reads adaptive_universe.json"]
}
save_json(ENGINE_AUDIT, audit)

universe_audit = {
    "generated_utc": now_utc(),
    "enabled_sources": len(enabled_sources),
    "measured_sources": len(measured_sources),
    "sector_count": len(sector_rollup),
    "adaptive_universe_count": len(universe),
    "top_symbols": [x["symbol"] for x in universe[:25]]
}
save_json(UNIVERSE_AUDIT, universe_audit)

print("ADAPTIVE ENGINE CUTOVER COMPLETE")
print("enabled_sources:", len(enabled_sources))
print("measured_sources:", len(measured_sources))
print("adaptive_universe_count:", len(universe))
print("static_symbol_risk:", static_symbol_risk)
print("adaptive_universe_file:", ADAPTIVE_UNIVERSE)
print("engine_audit_file:", ENGINE_AUDIT)
print("universe_audit_file:", UNIVERSE_AUDIT)