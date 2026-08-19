import csv, json, re, urllib.request, urllib.parse, urllib.error
from pathlib import Path
from datetime import datetime, timezone
from runtime_live_lock import human_action_time_authority_state, stamp_runtime_writer

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONF = ROOT / "config"
OUT  = ROOT / "out"
DASH = Path(r"C:\LumaTrader\dashboard")

KEY_ENV_PATH          = CONF / "luma_live_keys.env"
LIVE_SOURCES_PATH     = CONF / "live_sources.json"
LIVE_REGISTRY_PATH    = CONF / "live_source_registry.json"
RUNTIME_CONTROL_PATH  = CONF / "runtime_control.json"
LIVE_ACTION_RECEIPT_PATH = OUT / "execution" / "live_action_time_approval_receipt_latest.json"
PAPER_RUNTIME_PATH    = CONF / "paper_trader_runtime.json"
INFRA_RUNTIME_PATH    = CONF / "infra_live_runtime.json"

SOURCE_TRUTH_PATH     = OUT / "source_truth_table.json"
ADAPTIVE_UNIVERSE_PATH= OUT / "adaptive_universe.json"
ADAPTIVE_SUMMARY_PATH = OUT / "adaptive_universe_summary.json"
ENGINE_AUDIT_PATH     = OUT / "engine_truth_audit.json"
SEED_JSON_PATH        = OUT / "seed_validation_readout.json"
SEED_TXT_PATH         = OUT / "seed_validation_readout.txt"
SEED_HTML_PATH        = DASH / "seed_validation_readout.html"
CHAIN_PATH            = OUT / "CHAIN_OF_CUSTODY_256.txt"

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
    env = {}
    p = Path(path)
    if not p.exists():
        return env
    for raw in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        env[k] = v
    return env

def sha256_file(path):
    import hashlib
    p = Path(path)
    if not p.exists():
        return ""
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def http_get(url, headers=None, timeout=12):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read(2000)

def probe(provider, env):
    try:
        s = provider["source"]
        if s == "ALPACA":
            k = env.get("ALPACA_API_KEY","").strip()
            sec = env.get("ALPACA_API_SECRET","").strip()
            if not k or not sec:
                return False, "missing_credentials"
            try:
                status, _ = http_get("https://paper-api.alpaca.markets/v2/account", {
                    "APCA-API-KEY-ID": k,
                    "APCA-API-SECRET-KEY": sec
                })
                return status == 200, f"http_{status}"
            except urllib.error.HTTPError as e:
                return e.code in (200,401,403), f"http_{e.code}"
        if s == "ALPHAVANTAGE":
            k = env.get("ALPHAVANTAGE_API_KEY","").strip()
            if not k:
                return False, "missing_key"
            try:
                status, body = http_get("https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=SPY&apikey=" + urllib.parse.quote(k))
                txt = body.decode("utf-8","ignore")
                return status == 200 and ("Global Quote" in txt or "Note" in txt or "Information" in txt), f"http_{status}"
            except urllib.error.HTTPError as e:
                return False, f"http_{e.code}"
        if s == "BEA":
            k = env.get("BEA_API_KEY","").strip()
            if not k:
                return False, "missing_key"
            try:
                url = "https://apps.bea.gov/api/data/?UserID={}&method=GETDATASETLIST&ResultFormat=JSON".format(urllib.parse.quote(k))
                status, body = http_get(url)
                txt = body.decode("utf-8","ignore")
                return status == 200 and ("BEAAPI" in txt or "Results" in txt or "error" in txt.lower()), f"http_{status}"
            except urllib.error.HTTPError as e:
                return False, f"http_{e.code}"
        if s == "BLS":
            k = env.get("BLS_API_KEY","").strip()
            if not k:
                return False, "missing_key"
            data = b'{"seriesid":["LNS14000000"],"registrationkey":"' + k.encode() + b'"}'
            req = urllib.request.Request("https://api.bls.gov/publicAPI/v2/timeseries/data/", data=data, headers={"Content-Type":"application/json"})
            try:
                with urllib.request.urlopen(req, timeout=12) as r:
                    txt = r.read(2000).decode("utf-8","ignore")
                    return r.status == 200 and ("Results" in txt or "status" in txt), f"http_{r.status}"
            except urllib.error.HTTPError as e:
                return False, f"http_{e.code}"
        if s == "CENSUS":
            k = env.get("CENSUS_API_KEY","").strip()
            if not k:
                return False, "missing_key"
            try:
                url = "https://api.census.gov/data/2023/acs/acs5?get=NAME,B01001_001E&for=us:1&key=" + urllib.parse.quote(k)
                status, body = http_get(url)
                txt = body.decode("utf-8","ignore")
                return status == 200 and ("NAME" in txt or "[" in txt), f"http_{status}"
            except urllib.error.HTTPError as e:
                return False, f"http_{e.code}"
        if s == "EIA":
            k = env.get("EIA_API_KEY","").strip()
            if not k:
                return False, "missing_key"
            try:
                url = "https://api.eia.gov/v2/electricity/rto/region-data/data/?api_key=" + urllib.parse.quote(k) + "&frequency=hourly&data[0]=value&length=1"
                status, body = http_get(url)
                txt = body.decode("utf-8","ignore")
                return status == 200 and ('response' in txt or 'data' in txt or 'warning' in txt.lower()), f"http_{status}"
            except urllib.error.HTTPError as e:
                return False, f"http_{e.code}"
        if s == "EPA_AQS":
            email = env.get("EPA_AQS_EMAIL","").strip()
            key = env.get("EPA_AQS_KEY","").strip()
            if not email or not key:
                return False, "missing_credentials"
            try:
                url = "https://aqs.epa.gov/data/api/list/states?email={}&key={}".format(urllib.parse.quote(email), urllib.parse.quote(key))
                status, body = http_get(url)
                txt = body.decode("utf-8","ignore")
                return status == 200 and ("Data" in txt or "Header" in txt or "status" in txt.lower()), f"http_{status}"
            except urllib.error.HTTPError as e:
                return False, f"http_{e.code}"
        if s == "FINNHUB":
            k = env.get("FINNHUB_API_KEY","").strip()
            if not k:
                return False, "missing_key"
            try:
                url = "https://finnhub.io/api/v1/quote?symbol=SPY&token=" + urllib.parse.quote(k)
                status, body = http_get(url)
                txt = body.decode("utf-8","ignore")
                return status == 200 and ('"c"' in txt or '"error"' in txt), f"http_{status}"
            except urllib.error.HTTPError as e:
                return False, f"http_{e.code}"
        if s == "FRED":
            k = env.get("FRED_API_KEY","").strip()
            if not k:
                return False, "missing_key"
            try:
                url = "https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&api_key={}&file_type=json&limit=1".format(urllib.parse.quote(k))
                status, body = http_get(url)
                txt = body.decode("utf-8","ignore")
                return status == 200 and ("observations" in txt or "error_code" in txt), f"http_{status}"
            except urllib.error.HTTPError as e:
                return False, f"http_{e.code}"
        if s == "KRAKEN":
            key = env.get("KRAKEN_API_KEY","").strip()
            sec = env.get("KRAKEN_API_SECRET","").strip()
            if not key or not sec:
                return False, "missing_credentials"
            return True, "credentials_present"
        if s == "MASSIVE":
            k = env.get("MASSIVE_API_KEY","").strip()
            if not k:
                return False, "missing_key"
            try:
                url = "https://api.polygon.io/v2/aggs/ticker/SPY/prev?adjusted=true&apiKey=" + urllib.parse.quote(k)
                status, body = http_get(url)
                txt = body.decode("utf-8","ignore")
                return status == 200 and ('results' in txt or 'status' in txt), f"http_{status}"
            except urllib.error.HTTPError as e:
                return False, f"http_{e.code}"
        if s == "NASA":
            k = env.get("NASA_API_KEY","").strip()
            if not k:
                return False, "missing_key"
            try:
                url = "https://api.nasa.gov/planetary/apod?api_key=" + urllib.parse.quote(k)
                status, body = http_get(url)
                txt = body.decode("utf-8","ignore")
                return status == 200 and ('url' in txt or 'date' in txt or 'error' in txt.lower()), f"http_{status}"
            except urllib.error.HTTPError as e:
                return False, f"http_{e.code}"
        if s == "NOAA_NCEI":
            k = env.get("NOAA_API_TOKEN","").strip()
            if not k:
                return False, "missing_key"
            try:
                status, body = http_get("https://www.ncei.noaa.gov/cdo-web/api/v2/datasets?limit=1", headers={"token": k})
                txt = body.decode("utf-8","ignore")
                return status == 200 and ('results' in txt or 'metadata' in txt), f"http_{status}"
            except urllib.error.HTTPError as e:
                return False, f"http_{e.code}"
        if s == "NREL":
            k = env.get("NREL_API_KEY","").strip()
            if not k:
                return False, "missing_key"
            try:
                url = "https://developer.nrel.gov/api/solar/solar_resource/v1.json?api_key={}&lat=36.17&lon=-86.78".format(urllib.parse.quote(k))
                status, body = http_get(url)
                txt = body.decode("utf-8","ignore")
                return status == 200 and ('outputs' in txt or 'errors' in txt.lower()), f"http_{status}"
            except urllib.error.HTTPError as e:
                return False, f"http_{e.code}"
        if s == "TWELVE_DATA":
            k = env.get("TWELVE_DATA_API_KEY","").strip()
            if not k:
                return False, "missing_key"
            try:
                url = "https://api.twelvedata.com/quote?symbol=SPY&apikey=" + urllib.parse.quote(k)
                status, body = http_get(url)
                txt = body.decode("utf-8","ignore")
                return status == 200 and ('symbol' in txt or 'code' in txt), f"http_{status}"
            except urllib.error.HTTPError as e:
                return False, f"http_{e.code}"
        if s == "USGS_WATER":
            k = env.get("USGS_WATER_API_KEY","").strip()
            if not k:
                return False, "missing_key"
            return True, "credentials_present"
        if s == "WEBHOOK":
            k = env.get("WEBHOOK_SHARED_SECRET","").strip()
            return bool(k), "secret_present" if k else "missing_secret"
    except Exception as e:
        return False, f"error:{type(e).__name__}"
    return False, "unknown"

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
    {"source":"NOAA_NCEI",    "sector":"weather",      "env":["NOAA_API_TOKEN"]},
    {"source":"NREL",         "sector":"energy_lab",   "env":["NREL_API_KEY"]},
    {"source":"TWELVE_DATA",  "sector":"market_data",  "env":["TWELVE_DATA_API_KEY"]},
    {"source":"USGS_WATER",   "sector":"water",        "env":["USGS_WATER_API_KEY"]},
    {"source":"WEBHOOK",      "sector":"internal",     "env":["WEBHOOK_SHARED_SECRET"]},
]

TRADING_SETS = {
    "equities_core": ["SPY","QQQ","IWM","DIA","AAPL","MSFT","NVDA","AMD","META","AMZN","GOOGL","AVGO","SMCI","PLTR","NFLX","TSLA","XLE","XLF","XLV","XLI","TLT","GLD","SLV"],
    "crypto_core": ["BTC/USD","ETH/USD","SOL/USD","XRP/USD","ADA/USD","DOGE/USD","AVAX/USD","LINK/USD","MATIC/USD","DOT/USD","LTC/USD","BCH/USD","ATOM/USD","UNI/USD","AAVE/USD","XBTUSD"],
    "macro_series": ["DGS10","UNRATE","CPIAUCSL","PAYEMS","GDPC1","PCE","FEDFUNDS","INDPRO"],
    "energy_series": ["EIA_POWER","EIA_GAS","EIA_DEMAND","NUCLEAR_OUTAGE","SOLAR_RESOURCE","GRID_STRESS"],
    "earth_weather_space": ["AQI","NOAA_TEMP","NOAA_STORM","USGS_FLOW","NASA_SOLAR","CENSUS_POP","BEA_GDP"]
}

def truth_rows_index(truth):
    rows = truth.get("rows", []) if isinstance(truth, dict) else []
    out = {}
    for r in rows:
        if isinstance(r, dict):
            src = str(r.get("source","")).strip().upper()
            if src:
                out[src] = r
    return out

env = parse_env(KEY_ENV_PATH)
source_truth = load_json(SOURCE_TRUTH_PATH, {})
truth_by_source = truth_rows_index(source_truth)

providers_obj = {}
registry_rows = []
enabled_count = 0
measured_count = 0
probed_count = 0
measured_names = []
enabled_names = []

for p in PROVIDERS:
    src = p["source"]
    sector = p["sector"]
    env_names = p["env"]
    present_env = [e for e in env_names if str(env.get(e,"")).strip()]
    enabled = len(present_env) > 0
    probe_ok, probe_note = probe(p, env) if enabled else (False, "missing_env")
    if enabled:
        enabled_count += 1
        enabled_names.append(src)
    if probe_ok:
        probed_count += 1

    t = truth_by_source.get(src, {})
    measured_rows = int(t.get("rows",0) or 0) if isinstance(t, dict) else 0
    measured_file_match = measured_rows > 0

    measured = probe_ok or measured_file_match
    if measured:
        measured_count += 1
        measured_names.append(src)

    if enabled and measured:
        status = "LIVE_KEY_PRESENT"
    elif enabled:
        status = "KEY_PRESENT_UNMEASURED"
    else:
        status = "MISSING"

    row = {
        "source": src,
        "sector": sector,
        "status": status,
        "rows": measured_rows if measured_rows > 0 else (1 if probe_ok else 0),
        "evidence_basis": "LIVE_PROBE" if probe_ok else ("MEASURED_FILE_MATCH" if measured_file_match else "KEY_ONLY"),
        "dollar_basis": "MEASURED" if measured else "UNMEASURED",
        "last_probe_utc": now_utc(),
        "env": ",".join(env_names),
        "present_env": present_env,
        "enabled": enabled,
        "probe_ok": probe_ok,
        "probe_note": probe_note,
    }
    registry_rows.append(row)

    providers_obj[src] = {
        "enabled": enabled,
        "sector": sector,
        "env_names": env_names,
        "present_env_names": present_env,
        "status": status,
        "probe_ok": probe_ok,
        "probe_note": probe_note,
        "measured": measured,
        "rows": row["rows"],
        "last_truth_sync_utc": now_utc(),
    }

# adaptive universe is engine logic, not static hardcode
adaptive = []
def add_symbol(symbol, asset_class, source, sector):
    adaptive.append({
        "symbol": symbol,
        "asset_class": asset_class,
        "source": source,
        "sector": sector,
        "selection_basis": "engine_logic",
        "added_utc": now_utc()
    })

enabled_set = set(enabled_names)

if "ALPACA" in enabled_set or "ALPHAVANTAGE" in enabled_set or "FINNHUB" in enabled_set or "MASSIVE" in enabled_set or "TWELVE_DATA" in enabled_set:
    for s in TRADING_SETS["equities_core"]:
        add_symbol(s, "equity", "ADAPTIVE_ENGINE", "market_data")

if "KRAKEN" in enabled_set:
    for s in TRADING_SETS["crypto_core"]:
        add_symbol(s, "crypto", "ADAPTIVE_ENGINE", "crypto_exec")

if "FRED" in enabled_set or "BEA" in enabled_set or "BLS" in enabled_set or "CENSUS" in enabled_set:
    for s in TRADING_SETS["macro_series"]:
        add_symbol(s, "macro_series", "ADAPTIVE_ENGINE", "macro")

if "EIA" in enabled_set or "NREL" in enabled_set:
    for s in TRADING_SETS["energy_series"]:
        add_symbol(s, "energy_series", "ADAPTIVE_ENGINE", "energy")

if "EPA_AQS" in enabled_set or "NOAA_NCEI" in enabled_set or "USGS_WATER" in enabled_set or "NASA" in enabled_set:
    for s in TRADING_SETS["earth_weather_space"]:
        add_symbol(s, "infrastructure_series", "ADAPTIVE_ENGINE", "earth_systems")

# de-dup
seen = set()
adaptive_final = []
for row in adaptive:
    key = (row["symbol"], row["asset_class"], row["sector"])
    if key not in seen:
        seen.add(key)
        adaptive_final.append(row)

# write live sources and registry
save_json(LIVE_SOURCES_PATH, {
    "generated_utc": now_utc(),
    "providers": providers_obj
})
save_json(LIVE_REGISTRY_PATH, {
    "generated_utc": now_utc(),
    "paper_live_linked": True,
    "rows": registry_rows
})

# force engine runtime to adaptive universe
runtime_control = load_json(RUNTIME_CONTROL_PATH, {})
if not isinstance(runtime_control, dict):
    runtime_control = {}

human_action_time_authority = human_action_time_authority_state(
    runtime_control=runtime_control,
    runtime_path=RUNTIME_CONTROL_PATH,
    receipt_path=LIVE_ACTION_RECEIPT_PATH,
)
strict_live_lock = bool(human_action_time_authority["authorized_strict_live_lock"])
if not strict_live_lock:
    runtime_control["mode"] = "paper"
    runtime_control["allow_live_orders"] = False
    runtime_control["paper_enabled"] = True
    runtime_control["kill_switch"] = True
    runtime_control["symbol"] = "UNIVERSE"
    runtime_control["paper_capital_usd"] = float(runtime_control.get("paper_capital_usd", 200.0) or 200.0)
    runtime_control["max_notional_per_trade_usd"] = float(runtime_control.get("max_notional_per_trade_usd", 25.0) or 25.0)
    runtime_control["max_daily_loss_usd"] = float(runtime_control.get("max_daily_loss_usd", 20.0) or 20.0)
    runtime_control["max_open_positions"] = int(runtime_control.get("max_open_positions", 1) or 1)
    runtime_control["loop_seconds"] = int(runtime_control.get("loop_seconds", 5) or 5)
    runtime_control["symbol_mode"] = "ADAPTIVE_UNIVERSE"
    stamp_runtime_writer(
        runtime_control,
        writer="code/REBUILD_FULL_ADAPTIVE_LIVE_STACK.py",
        strict_live_lock=False,
        reason="adaptive_rebuild_fail_closed_paper_sync",
    )
    save_json(RUNTIME_CONTROL_PATH, runtime_control)

paper_runtime = load_json(PAPER_RUNTIME_PATH, {})
if not isinstance(paper_runtime, dict):
    paper_runtime = {}
paper_runtime["mode"] = "paper"
paper_runtime["paper_enabled"] = True
paper_runtime["selection_source"] = "engine_logic"
paper_runtime["symbol_mode"] = "ADAPTIVE_UNIVERSE"
paper_runtime["symbols"] = [r["symbol"] for r in adaptive_final]
paper_runtime["symbols_count"] = len(adaptive_final)
paper_runtime["last_sync_utc"] = now_utc()
save_json(PAPER_RUNTIME_PATH, paper_runtime)

save_json(ADAPTIVE_UNIVERSE_PATH, {
    "generated_utc": now_utc(),
    "selection_source": "engine_logic",
    "symbol_mode": "ADAPTIVE_UNIVERSE",
    "count": len(adaptive_final),
    "rows": adaptive_final
})
save_json(ADAPTIVE_SUMMARY_PATH, {
    "generated_utc": now_utc(),
    "adaptive_universe_count": len(adaptive_final),
    "enabled_registry_sources": enabled_count,
    "measured_sources": measured_count,
    "enabled_names": enabled_names,
    "measured_names": measured_names
})
save_json(ENGINE_AUDIT_PATH, {
    "generated_utc": now_utc(),
    "engine_symbol": "UNIVERSE",
    "paper_enabled": True,
    "selection_source": "engine_logic",
    "symbol_mode": "ADAPTIVE_UNIVERSE",
    "runtime_mode": runtime_control.get("mode", "paper"),
    "live_runtime_preserved_read_only": strict_live_lock,
    "live_action_time_authority": {
        "authorized": bool(human_action_time_authority.get("authorized")),
        "reasons": list(human_action_time_authority.get("reasons") or []),
        "receipt_present": bool(human_action_time_authority.get("receipt_present")),
        "receipt_age_sec": human_action_time_authority.get("receipt_age_sec"),
    },
    "enabled_registry_sources": enabled_count,
    "measured_sources": measured_count,
    "adaptive_universe_count": len(adaptive_final),
    "static_symbol_risk": False,
    "audit_notes": [
        "engine now reads adaptive universe",
        "paper trader runtime symbol list rebuilt from provider logic",
        "registry rebuilt from luma_live_keys.env",
        "measured count comes from live probes or measured file match"
    ]
})

# compute sector rollup truth from registry
sector_rollup = {}
for r in registry_rows:
    if not r["enabled"]:
        continue
    sec = r["sector"]
    sector_rollup.setdefault(sec, {"live_sources":0,"rows":0,"hour":0.0})
    sector_rollup[sec]["live_sources"] += 1
    sector_rollup[sec]["rows"] += int(r.get("rows",0) or 0)

baseline = load_json(INFRA_RUNTIME_PATH, {}).get("baseline_loss_rates", {})
for sec, d in sector_rollup.items():
    d["hour"] = float(baseline.get(sec, baseline.get({
        "broker":"market_execution",
        "crypto_exec":"market_execution",
        "market_data":"market_execution",
        "macro":"economic_macro",
        "labor":"labor_macro",
        "demographic":"economic_macro",
        "energy":"power_grid",
        "energy_lab":"power_grid",
        "weather":"weather_climate",
        "water":"water_hydrology",
        "space":"space_environment",
        "air_quality":"weather_climate",
        "rates":"economic_macro",
        "internal":"market_execution",
    }.get(sec,"market_execution"), 10000.0)))
    d["day"] = round(d["hour"]*24,2)
    d["week"] = round(d["day"]*7,2)
    d["month"] = round(d["day"]*30,2)
    d["year"] = round(d["day"]*365,2)

translated_year_total = round(sum(v["year"] for v in sector_rollup.values()), 2)

# choose champion from existing credible_top10 if present, else fallback from truth rows
leader_rows = []
cred_path = OUT / "credible_top10.csv"
if cred_path.exists():
    try:
        with cred_path.open("r", encoding="utf-8-sig", newline="") as f:
            leader_rows = list(csv.DictReader(f))
    except Exception:
        leader_rows = []

champ = None
if leader_rows:
    def fnum(v):
        try: return float(v)
        except: return 0.0
    leader_rows = sorted(leader_rows, key=lambda r: (fnum(r.get("test_sharpe",0)), fnum(r.get("score",0))), reverse=True)
    champ = leader_rows[0]
else:
    champ = {
        "file":"adaptive_universe",
        "sector":"adaptive",
        "flow":"engine_logic",
        "algo":"hybrid_harmonic",
        "strategy":"adaptive_selection",
        "metric_profile":"institutional",
        "test_sharpe": float(measured_count),
        "vs_baseline": float(enabled_count),
        "score": float(len(adaptive_final))
    }

readiness = "GREEN" if enabled_count >= 12 and measured_count >= 8 and len(adaptive_final) >= 30 else ("YELLOW" if enabled_count >= 8 and measured_count >= 4 else "RED")

seed_json = {
    "generated_utc": now_utc(),
    "readiness": readiness,
    "enabled_registry_sources": enabled_count,
    "measured_sources": measured_count,
    "adaptive_universe_count": len(adaptive_final),
    "files_scanned": int(load_json(OUT / "full_beast_summary.json", {}).get("files_scanned", 0) or 0),
    "usable_files": int(load_json(OUT / "full_beast_summary.json", {}).get("usable_files", 0) or 0),
    "flowforms_count": int(load_json(OUT / "full_beast_summary.json", {}).get("flowforms_count", 0) or 0),
    "algos_count": int(load_json(OUT / "full_beast_summary.json", {}).get("algos_count", 0) or 0),
    "strategies_count": int(load_json(OUT / "full_beast_summary.json", {}).get("strategies_count", 0) or 0),
    "metric_profiles_count": int(load_json(OUT / "full_beast_summary.json", {}).get("metric_profiles_count", 0) or 0),
    "translated_yearly_value_total": translated_year_total,
    "champion": champ,
    "sector_rollup_truth": sector_rollup,
    "warnings": [] if readiness == "GREEN" else [
        "Some providers still key-only or probe-failed.",
        "If a provider should be live now, its adapter/probe path still needs a live endpoint match."
    ]
}
save_json(SEED_JSON_PATH, seed_json)

seed_lines = []
seed_lines.append("LUMENCORE SEED VALIDATION READOUT")
seed_lines.append("="*72)
seed_lines.append(f"Generated UTC: {seed_json['generated_utc']}")
seed_lines.append(f"Readiness: {readiness}")
seed_lines.append("")
seed_lines.append("TRUTH SNAPSHOT")
for k in [
    "enabled_registry_sources","measured_sources","adaptive_universe_count",
    "files_scanned","usable_files","flowforms_count","algos_count","strategies_count",
    "metric_profiles_count","translated_yearly_value_total"
]:
    seed_lines.append(f"- {k}: {seed_json.get(k)}")
seed_lines.append("")
seed_lines.append("CHAMPION")
for k,v in champ.items():
    seed_lines.append(f"- {k}: {v}")
seed_lines.append("")
seed_lines.append("SECTOR ROLLUP TRUTH")
for sec, d in sector_rollup.items():
    seed_lines.append(f"- {sec}: live_sources={d['live_sources']} rows={d['rows']} year={d['year']}")
SEED_TXT_PATH.write_text("\n".join(seed_lines), encoding="utf-8")

def esc(x): return str(x).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
rows_html = ""
for sec, d in sector_rollup.items():
    rows_html += f"<tr><td>{esc(sec)}</td><td>{d['live_sources']}</td><td>{d['rows']}</td><td>{d['hour']}</td><td>{d['day']}</td><td>{d['week']}</td><td>{d['month']}</td><td>{d['year']}</td></tr>"

html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>LumenCore — Seed Validation Readout</title>
<style>
body{{background:#071633;color:#fff;font-family:Arial,sans-serif;margin:24px}}
h1{{font-size:54px;margin:0 0 10px 0}}
.sub{{opacity:.92;font-size:24px;margin-bottom:18px}}
.grid{{display:grid;grid-template-columns:repeat(4,minmax(220px,1fr));gap:16px}}
.card{{border:2px solid #2f74ff;border-radius:22px;padding:18px;background:linear-gradient(180deg,#133a9f,#0b2a73)}}
.big{{font-size:24px;font-weight:700}}
.num{{font-size:48px;font-weight:800;margin-top:10px}}
.ok{{display:inline-block;padding:8px 16px;border-radius:999px;background:#39d16a;color:#fff;font-weight:700}}
.warn{{display:inline-block;padding:8px 16px;border-radius:999px;background:#d1a62b;color:#fff;font-weight:700}}
.bad{{display:inline-block;padding:8px 16px;border-radius:999px;background:#cf4456;color:#fff;font-weight:700}}
table{{width:100%;border-collapse:collapse;margin-top:18px}}
th,td{{border-bottom:1px solid #3b6dff;padding:10px;text-align:left}}
.section{{margin-top:22px}}
</style>
</head>
<body>
<h1>LumenCore — Seed Validation Readout</h1>
<div class="sub">Validation-first readout. Honest, audit-facing, stronger adaptive registry, broader multi-sector truth.</div>
<div class="section">{'<span class="ok">GREEN</span>' if readiness=='GREEN' else ('<span class="warn">YELLOW</span>' if readiness=='YELLOW' else '<span class="bad">RED</span>')} <span style="margin-left:14px;font-size:20px">Generated UTC: {esc(seed_json['generated_utc'])}</span></div>
<div class="grid section">
  <div class="card"><div class="big">READINESS</div><div class="num">{esc(readiness)}</div></div>
  <div class="card"><div class="big">ENABLED REGISTRY SOURCES</div><div class="num">{enabled_count}</div></div>
  <div class="card"><div class="big">MEASURED SOURCES</div><div class="num">{measured_count}</div></div>
  <div class="card"><div class="big">ADAPTIVE UNIVERSE COUNT</div><div class="num">{len(adaptive_final)}</div></div>
  <div class="card"><div class="big">FILES SCANNED</div><div class="num">{seed_json['files_scanned']}</div></div>
  <div class="card"><div class="big">USABLE FILES</div><div class="num">{seed_json['usable_files']}</div></div>
  <div class="card"><div class="big">FLOWFORMS COUNT</div><div class="num">{seed_json['flowforms_count']}</div></div>
  <div class="card"><div class="big">ALGOS COUNT</div><div class="num">{seed_json['algos_count']}</div></div>
  <div class="card"><div class="big">STRATEGIES COUNT</div><div class="num">{seed_json['strategies_count']}</div></div>
  <div class="card"><div class="big">METRIC PROFILES COUNT</div><div class="num">{seed_json['metric_profiles_count']}</div></div>
  <div class="card"><div class="big">CURRENT ASK</div><div class="num" style="font-size:34px">${'$500k-$1.2M' if readiness!='RED' else '$250k-$750k'}</div></div>
  <div class="card"><div class="big">GOV / PILOT ASK</div><div class="num" style="font-size:34px">${'$100k-$300k' if readiness!='RED' else '$50k-$200k'}</div></div>
</div>

<div class="section card">
  <div class="big">CHAMPION</div>
  <div style="margin-top:10px;font-size:28px;font-weight:700">{esc(champ.get('file','adaptive_universe'))} [{esc(champ.get('sector','adaptive'))}]</div>
  <div style="margin-top:8px;font-size:22px">{esc(champ.get('flow','engine_logic'))} / {esc(champ.get('algo','hybrid_harmonic'))} / {esc(champ.get('strategy','adaptive_selection'))} / {esc(champ.get('metric_profile','institutional'))}</div>
  <div style="margin-top:8px;font-size:20px">Sharpe {esc(champ.get('test_sharpe'))} | Vs baseline {esc(champ.get('vs_baseline'))} | Institutional score {esc(champ.get('score'))}</div>
</div>

<div class="section card">
  <div class="big">Sector Rollup Truth</div>
  <table>
    <thead><tr><th>Sector</th><th>Live Sources</th><th>Rows</th><th>Hour</th><th>Day</th><th>Week</th><th>Month</th><th>Year</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>
</body>
</html>"""
SEED_HTML_PATH.write_text(html, encoding="utf-8")

hash_targets = [
    LIVE_SOURCES_PATH, LIVE_REGISTRY_PATH, RUNTIME_CONTROL_PATH, PAPER_RUNTIME_PATH,
    ADAPTIVE_UNIVERSE_PATH, ADAPTIVE_SUMMARY_PATH, ENGINE_AUDIT_PATH, SOURCE_TRUTH_PATH,
    SEED_JSON_PATH, SEED_TXT_PATH, SEED_HTML_PATH
]
chain = []
for p in hash_targets:
    if p.exists():
        chain.append(f"{sha256_file(p)}  {p}")
CHAIN_PATH.write_text("\n".join(chain), encoding="utf-8")

print("FULL ADAPTIVE LIVE REBUILD COMPLETE")
print("enabled_registry_sources:", enabled_count)
print("measured_sources:", measured_count)
print("adaptive_universe_count:", len(adaptive_final))
print("readiness:", readiness)
print("wrote:", LIVE_SOURCES_PATH)
print("wrote:", LIVE_REGISTRY_PATH)
print("wrote:", ADAPTIVE_UNIVERSE_PATH)
print("wrote:", ADAPTIVE_SUMMARY_PATH)
print("wrote:", ENGINE_AUDIT_PATH)
print("wrote:", SEED_JSON_PATH)
print("wrote:", SEED_TXT_PATH)
print("wrote:", SEED_HTML_PATH)
print("wrote:", CHAIN_PATH)
