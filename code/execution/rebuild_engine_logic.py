import os, re, json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONF = ROOT / "config"
OUT  = ROOT / "out"

ENV_FILE              = CONF / "luma_live_keys.env"
LIVE_SOURCES_FILE     = CONF / "live_sources.json"
LIVE_REGISTRY_FILE    = CONF / "live_source_registry.json"
RUNTIME_CONTROL_FILE  = CONF / "runtime_control.json"
PAPER_RUNTIME_FILE    = CONF / "paper_trader_runtime.json"
AUDIT_FILE            = OUT / "engine_truth_audit.json"

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

def parse_env_file(path):
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
        if k:
            out[k] = v
    return out

def merged_env():
    out = {}
    out.update(parse_env_file(ENV_FILE))
    for k, v in os.environ.items():
        if k not in out and v:
            out[k] = v
    return out

CANONICAL = [
    {"source":"ALPACA",      "envs":["ALPACA_API_KEY","ALPACA_API_SECRET"],       "sector":"broker"},
    {"source":"ALPHAVANTAGE","envs":["ALPHAVANTAGE_API_KEY"],                      "sector":"market_data"},
    {"source":"BEA",         "envs":["BEA_API_KEY"],                               "sector":"macro"},
    {"source":"BLS",         "envs":["BLS_API_KEY"],                               "sector":"labor"},
    {"source":"CENSUS",      "envs":["CENSUS_API_KEY"],                            "sector":"demographic"},
    {"source":"EIA",         "envs":["EIA_API_KEY"],                               "sector":"energy"},
    {"source":"EPA_AQS",     "envs":["EPA_AQS_KEY","EPA_AQS_EMAIL"],               "sector":"air_quality"},
    {"source":"FINNHUB",     "envs":["FINNHUB_API_KEY"],                           "sector":"market_data"},
    {"source":"FRED",        "envs":["FRED_API_KEY"],                              "sector":"rates"},
    {"source":"KRAKEN",      "envs":["KRAKEN_API_KEY","KRAKEN_API_SECRET"],        "sector":"crypto_exec"},
    {"source":"MASSIVE",     "envs":["MASSIVE_API_KEY"],                           "sector":"market_data"},
    {"source":"NASA",        "envs":["NASA_API_KEY"],                              "sector":"space"},
    {"source":"NOAA_NCEI",   "envs":["NOAA_API_TOKEN"],                            "sector":"weather"},
    {"source":"NREL",        "envs":["NREL_API_KEY"],                              "sector":"energy_lab"},
    {"source":"TWELVE_DATA", "envs":["TWELVE_DATA_API_KEY"],                       "sector":"market_data"},
    {"source":"USGS_WATER",  "envs":["USGS_WATER_API_KEY"],                        "sector":"water"},
    {"source":"WEBHOOK",     "envs":["WEBHOOK_SHARED_SECRET"],                     "sector":"internal"},
]

def has_all(env, env_names):
    return all(env.get(k) for k in env_names)

def found_any(env, env_names):
    return any(env.get(k) for k in env_names)

def infer_measured_rows(source_name, sector):
    source_truth = load_json(OUT / "source_truth_table.json", {})
    rows = source_truth.get("rows", []) if isinstance(source_truth, dict) else []
    total = 0
    evidence = "KEY_ONLY"
    dollar_basis = "UNMEASURED"

    for r in rows:
        if not isinstance(r, dict):
            continue
        s = str(r.get("source","")).upper()
        sec = str(r.get("sector","")).lower()
        if s == source_name.upper() or sec == sector.lower():
            rr = int(r.get("rows", 0) or 0)
            if rr > 0:
                total += rr
                evidence = "MEASURED_FILE_MATCH"
                dollar_basis = "MEASURED"

    return total, evidence, dollar_basis

def build_live_sources(env):
    out = {}
    for item in CANONICAL:
        source = item["source"]
        envs   = item["envs"]
        sector = item["sector"]
        present = found_any(env, envs)
        complete = has_all(env, envs)
        rows, evidence, dollar_basis = infer_measured_rows(source, sector)

        out[source] = {
            "enabled": bool(present),
            "complete_keyset": bool(complete),
            "sector": sector,
            "envs": envs,
            "rows": rows,
            "evidence_basis": evidence,
            "dollar_basis": dollar_basis,
            "last_truth_sync_utc": now_utc()
        }
    return out

def build_registry(env, live_sources):
    rows = []
    for item in CANONICAL:
        source = item["source"]
        sector = item["sector"]
        envs   = item["envs"]
        info   = live_sources.get(source, {})
        present = found_any(env, envs)
        complete = has_all(env, envs)
        measured = int(info.get("rows", 0) or 0)

        if measured > 0:
            status = "LIVE_KEY_PRESENT"
            enabled = True
        elif present:
            status = "KEY_PRESENT_UNMEASURED"
            enabled = True
        else:
            status = "MISSING"
            enabled = False

        rows.append({
            "source": source,
            "sector": sector,
            "status": status,
            "rows": measured,
            "evidence_basis": info.get("evidence_basis", "KEY_ONLY"),
            "dollar_basis": info.get("dollar_basis", "UNMEASURED"),
            "last_probe_utc": now_utc(),
            "env": ",".join(envs),
            "env_present_count": sum(1 for e in envs if env.get(e)),
            "env_complete": complete,
            "enabled": enabled
        })
    return {
        "generated_utc": now_utc(),
        "paper_live_linked": True,
        "rows": rows
    }

def patch_runtime():
    runtime = load_json(RUNTIME_CONTROL_FILE, {})
    paper   = load_json(PAPER_RUNTIME_FILE, {})

    runtime["mode"] = "paper"
    runtime["allow_live_orders"] = False
    runtime["paper_enabled"] = True
    runtime["kill_switch"] = True
    runtime["symbol"] = "UNIVERSE"

    if "paper_enabled" not in paper:
        paper["paper_enabled"] = True
    else:
        paper["paper_enabled"] = True

    if "symbols" not in paper or not isinstance(paper["symbols"], list):
        paper["symbols"] = []

    paper["symbol_mode"] = "ADAPTIVE_UNIVERSE"
    paper["selection_source"] = "engine_logic"
    paper["loop_seconds"] = int(paper.get("loop_seconds", 5) or 5)

    save_json(RUNTIME_CONTROL_FILE, runtime)
    save_json(PAPER_RUNTIME_FILE, paper)
    return runtime, paper

def audit_static_symbol_risk(runtime, paper):
    static_risk = False
    reasons = []

    sym = str(runtime.get("symbol",""))
    if sym and sym.upper() != "UNIVERSE":
        static_risk = True
        reasons.append(f"runtime_control.symbol={sym}")

    syms = paper.get("symbols", [])
    if isinstance(syms, list) and len(syms) > 0:
        reasons.append(f"paper_trader_runtime.symbols_count={len(syms)}")
    else:
        reasons.append("paper_trader_runtime.symbols_count=0")

    if paper.get("selection_source") != "engine_logic":
        static_risk = True
        reasons.append(f"selection_source={paper.get('selection_source')}")

    return static_risk, reasons

def main():
    env = merged_env()
    live_sources = build_live_sources(env)
    registry = build_registry(env, live_sources)
    runtime, paper = patch_runtime()
    static_risk, reasons = audit_static_symbol_risk(runtime, paper)

    save_json(LIVE_SOURCES_FILE, live_sources)
    save_json(LIVE_REGISTRY_FILE, registry)

    enabled_count  = sum(1 for _,v in live_sources.items() if v.get("enabled"))
    measured_count = sum(1 for _,v in live_sources.items() if int(v.get("rows",0) or 0) > 0)

    audit = {
        "generated_utc": now_utc(),
        "engine_symbol": runtime.get("symbol"),
        "paper_enabled": paper.get("paper_enabled"),
        "selection_source": paper.get("selection_source"),
        "enabled_registry_sources": enabled_count,
        "measured_sources": measured_count,
        "static_symbol_risk": static_risk,
        "audit_notes": reasons
    }
    save_json(AUDIT_FILE, audit)

    print("REBUILT LIVE SOURCE MAP")
    print("ENABLED REGISTRY SOURCES:", enabled_count)
    print("MEASURED SOURCES:", measured_count)
    print("ENGINE SYMBOL:", runtime.get("symbol"))
    print("SELECTION SOURCE:", paper.get("selection_source"))
    print("STATIC SYMBOL RISK:", static_risk)
    print("AUDIT:", str(AUDIT_FILE))

if __name__ == "__main__":
    main()
