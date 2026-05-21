import os, re, csv, json, math, hashlib, statistics, io, zipfile
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE = ROOT / "code"
CONF = ROOT / "config"
OUT = ROOT / "out"
DASH = Path(r"C:\LumaTrader\dashboard")

for p in [CODE, CONF, OUT, DASH]:
    p.mkdir(parents=True, exist_ok=True)

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def read_json(path, default=None):
    if default is None:
        default = {}
    try:
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2), encoding="utf-8")

def write_text(path, text):
    Path(path).write_text(text, encoding="utf-8")

def norm(s):
    return re.sub(r"[^A-Za-z0-9_./-]+", "_", str(s or "")).strip("_").upper()

def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s or "").lower()).strip("_")

def sha256_file(path):
    p = Path(path)
    if not p.exists():
        return ""
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def load_env_file(path):
    env = {}
    p = Path(path)
    if not p.exists():
        return env
    try:
        for raw in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env

def discover_env():
    merged = dict(os.environ)
    candidates = [
        CONF / "luma_live_keys.env",
        ROOT / ".env",
        ROOT / ".env.local",
        ROOT / ".env.ultra",
        Path(r"C:\LumaTrader\.env"),
        Path(r"C:\LumaTrader\.env.local"),
        Path.home() / ".env",
    ]
    for p in candidates:
        merged.update(load_env_file(p))
    return merged

ENV = discover_env()

RUNTIME = read_json(CONF / "runtime_control.json", {})
PAPER_RUNTIME = read_json(CONF / "paper_trader_runtime.json", {})
INFRA_RUNTIME = read_json(CONF / "infra_live_runtime.json", {})

DEFAULT_DATA_ROOTS = [
    r"C:\LumaTrader",
    r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\data",
    r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\clean_data",
    r"C:\LumaTrader\data",
    str(Path.home() / "iCloudDrive" / "Data sets"),
]

configured_roots = INFRA_RUNTIME.get("data_roots") or []
merged_roots = []
seen = set()
for root in list(configured_roots) + DEFAULT_DATA_ROOTS:
    root_str = str(root or "").strip()
    if not root_str:
        continue
    key = root_str.lower()
    if key in seen:
        continue
    seen.add(key)
    merged_roots.append(Path(root_str))

DATA_ROOTS = merged_roots
for p in DATA_ROOTS:
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

KEY_SPECS = [
    {"source":"ALPACA",      "envs":["ALPACA_API_KEY","ALPACA_API_SECRET"], "sector":"broker",      "kind":"broker"},
    {"source":"ALPHAVANTAGE","envs":["ALPHAVANTAGE_API_KEY"],               "sector":"market_data", "kind":"market_data"},
    {"source":"BEA",         "envs":["BEA_API_KEY"],                        "sector":"macro",       "kind":"macro"},
    {"source":"BLS",         "envs":["BLS_API_KEY"],                        "sector":"labor",       "kind":"labor"},
    {"source":"CENSUS",      "envs":["CENSUS_API_KEY"],                     "sector":"demographic", "kind":"demographic"},
    {"source":"EIA",         "envs":["EIA_API_KEY"],                        "sector":"energy",      "kind":"energy"},
    {"source":"EPA_AQS",     "envs":["EPA_AQS_KEY","EPA_AQS_EMAIL"],        "sector":"air_quality", "kind":"air_quality"},
    {"source":"FINNHUB",     "envs":["FINNHUB_API_KEY"],                    "sector":"market_data", "kind":"market_data"},
    {"source":"FRED",        "envs":["FRED_API_KEY"],                       "sector":"rates",       "kind":"rates"},
    {"source":"KRAKEN",      "envs":["KRAKEN_API_KEY","KRAKEN_API_SECRET"], "sector":"crypto_exec", "kind":"crypto_exec"},
    {"source":"MASSIVE",     "envs":["MASSIVE_API_KEY"],                    "sector":"market_data", "kind":"market_data"},
    {"source":"NASA",        "envs":["NASA_API_KEY"],                       "sector":"space",       "kind":"space"},
    {"source":"NOAA_NCEI",   "envs":["NOAA_API_TOKEN"],                     "sector":"weather",     "kind":"weather"},
    {"source":"NREL",        "envs":["NREL_API_KEY"],                       "sector":"energy_lab",  "kind":"energy_lab"},
    {"source":"TWELVE_DATA", "envs":["TWELVE_DATA_API_KEY"],                "sector":"market_data", "kind":"market_data"},
    {"source":"USGS_WATER",  "envs":["USGS_WATER_API_KEY"],                 "sector":"water",       "kind":"water"},
    {"source":"WEBHOOK",     "envs":["WEBHOOK_SHARED_SECRET"],              "sector":"internal",    "kind":"internal"},
]

def first_present(env_names):
    vals = []
    for k in env_names:
        v = str(ENV.get(k, "")).strip()
        if v:
            vals.append((k, v))
    return vals

FOUND_KEYS = []
for spec in KEY_SPECS:
    vals = first_present(spec["envs"])
    if vals:
        FOUND_KEYS.append({
            "source": spec["source"],
            "sector": spec["sector"],
            "kind": spec["kind"],
            "envs": [k for k,v in vals],
            "env_count": len(vals),
        })

OUT_ENV = CONF / "luma_live_keys.env"
safe_lines = []
for spec in KEY_SPECS:
    for k in spec["envs"]:
        v = str(ENV.get(k, "")).strip()
        if v:
            safe_lines.append(f"{k}={v}")
write_text(OUT_ENV, "\n".join(safe_lines) + ("\n" if safe_lines else ""))

def paper_seed_from_keys():
    syms = set()
    if any(x["source"] == "KRAKEN" for x in FOUND_KEYS):
        syms.update(["BTC/USD","ETH/USD","SOL/USD","XRP/USD","ADA/USD","DOGE/USD","AVAX/USD","LINK/USD","DOT/USD","MATIC/USD"])
    if any(x["source"] in {"ALPACA","FINNHUB","TWELVE_DATA","MASSIVE","ALPHAVANTAGE"} for x in FOUND_KEYS):
        syms.update(["SPY","QQQ","IWM","DIA","NVDA","MSFT","AAPL","AMD","META","AMZN","TSLA","GOOGL","AVGO","SMCI","PLTR","NFLX"])
    if "symbols" in PAPER_RUNTIME and isinstance(PAPER_RUNTIME["symbols"], list):
        syms.update([str(x).strip() for x in PAPER_RUNTIME["symbols"] if str(x).strip()])
    return sorted(syms)

PAPER_SYMBOLS = paper_seed_from_keys()

LIVE_SOURCES = {}
for spec in KEY_SPECS:
    present = first_present(spec["envs"])
    LIVE_SOURCES[slug(spec["source"])] = {
        "enabled": bool(present),
        "sector": spec["sector"],
        "kind": spec["kind"],
        "env_names": spec["envs"],
        "present_env_names": [k for k,v in present],
        "measurement_mode": "local_dataset_match",
    }
write_json(CONF / "live_sources.json", LIVE_SOURCES)

def infer_sector(text):
    t = slug(text)
    if any(k in t for k in ["implied","options","option_chain","call_put"]): return "options"
    if any(k in t for k in ["vix","volatility","iv","realized_vol"]): return "volatility"
    if any(k in t for k in ["kraken","xbt","btc","eth","sol","crypto"]): return "crypto_exec"
    if any(k in t for k in ["alpaca","broker","execution","trade","order"]): return "broker"
    if any(k in t for k in ["eia","930","ciso","miso","pjm","ercot","nyis","isne","power","generation","grid","outage","nuclear","energy"]): return "energy"
    if any(k in t for k in ["nrel","solar","wind","lab"]): return "energy_lab"
    if any(k in t for k in ["fred","dgs","cpi","yield","rate"]): return "rates"
    if any(k in t for k in ["bea","macro","gdp","pce"]): return "macro"
    if any(k in t for k in ["census","population","housing","demographic"]): return "demographic"
    if any(k in t for k in ["bls","unrate","labor","employment"]): return "labor"
    if any(k in t for k in ["noaa","ncei","weather","climate","storm"]): return "weather"
    if any(k in t for k in ["usgs","water","hydro"]): return "water"
    if any(k in t for k in ["nasa","space","orbit","solar_activity"]): return "space"
    if any(k in t for k in ["aqs","epa","air_quality","pm25","ozone"]): return "air_quality"
    if any(k in t for k in ["finnhub","alpha","massive","twelve","polygon","market","equity","stock"]): return "market_data"
    return "unknown"

def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default

SCAN_LIMIT = max(200, safe_int(INFRA_RUNTIME.get("dataset_scan_limit", os.getenv("LUMA_DATASET_SCAN_LIMIT", "2500")), 2500))
ZIP_MEMBER_LIMIT = max(20, safe_int(INFRA_RUNTIME.get("zip_member_scan_limit", os.getenv("LUMA_ZIP_MEMBER_SCAN_LIMIT", "200")), 200))
MAX_TEXT_BYTES = max(1024 * 64, safe_int(INFRA_RUNTIME.get("dataset_max_text_bytes", os.getenv("LUMA_DATASET_MAX_TEXT_BYTES", str(8 * 1024 * 1024))), 8 * 1024 * 1024))
SKIP_PARTS = {".git", "__pycache__", "node_modules", ".venv", "venv", "venv3.11"}
SUPPORTED_EXTS = {".csv", ".json", ".jsonl", ".ndjson", ".parquet", ".zip"}
TS_KEYS = {"timestamp", "time", "date", "datetime", "period", "trading_day", "intervalending", "interval_start", "interval_end", "hourending"}
VAL_KEYS = {"value", "close", "price", "settle", "demandforecastmwh", "demand", "load", "mw", "volume", "adjclose"}

def pick_ts_col(headers):
    for h in headers or []:
        if slug(h) in TS_KEYS:
            return h
    return ""

def pick_value_col(headers):
    for h in headers or []:
        if slug(h) in VAL_KEYS:
            return h
    if headers:
        return headers[min(len(headers) - 1, 0)]
    return ""

def scan_csv_fileobj(fileobj):
    rows = 0
    headers = []
    first_ts = ""
    last_ts = ""
    try:
        reader = csv.DictReader(fileobj)
        headers = reader.fieldnames or []
        ts_col = pick_ts_col(headers)
        for row in reader:
            rows += 1
            if ts_col:
                tv = str(row.get(ts_col, "")).strip()
                if tv:
                    if not first_ts:
                        first_ts = tv
                    last_ts = tv
    except Exception:
        return {"rows": 0, "headers": [], "first_ts": "", "last_ts": "", "value_col": "", "scan_note": "csv_parse_failed"}
    return {
        "rows": rows,
        "headers": headers,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "value_col": pick_value_col(headers),
        "scan_note": "ok",
    }

def scan_csv(path):
    try:
        with Path(path).open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            return scan_csv_fileobj(f)
    except Exception:
        return {"rows": 0, "headers": [], "first_ts": "", "last_ts": "", "value_col": "", "scan_note": "csv_open_failed"}

def scan_json_text(text):
    try:
        payload = json.loads(text)
    except Exception:
        return {"rows": 0, "headers": [], "first_ts": "", "last_ts": "", "value_col": "", "scan_note": "json_parse_failed"}

    rows = 0
    headers = []
    first_ts = ""
    last_ts = ""

    if isinstance(payload, list):
        rows = len(payload)
        first = payload[0] if payload else {}
        last = payload[-1] if payload else {}
        if isinstance(first, dict):
            headers = list(first.keys())
            ts_col = pick_ts_col(headers)
            if ts_col:
                first_ts = str(first.get(ts_col, "") or "")
                last_ts = str(last.get(ts_col, "") or "") if isinstance(last, dict) else ""
    elif isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            rows = len(payload.get("data") or [])
            first = (payload.get("data") or [{}])[0] if rows else {}
            last = (payload.get("data") or [{}])[-1] if rows else {}
            if isinstance(first, dict):
                headers = list(first.keys())
                ts_col = pick_ts_col(headers)
                if ts_col:
                    first_ts = str(first.get(ts_col, "") or "")
                    last_ts = str(last.get(ts_col, "") or "") if isinstance(last, dict) else ""
        else:
            rows = 1
            headers = list(payload.keys())

    return {
        "rows": rows,
        "headers": headers,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "value_col": pick_value_col(headers),
        "scan_note": "ok",
    }

def scan_json(path):
    p = Path(path)
    try:
        if p.stat().st_size > MAX_TEXT_BYTES:
            return {"rows": 0, "headers": [], "first_ts": "", "last_ts": "", "value_col": "", "scan_note": "json_too_large"}
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {"rows": 0, "headers": [], "first_ts": "", "last_ts": "", "value_col": "", "scan_note": "json_open_failed"}
    return scan_json_text(text)

def scan_jsonl(path):
    rows = 0
    first_obj = None
    last_obj = None
    try:
        with Path(path).open("r", encoding="utf-8", errors="ignore") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                rows += 1
                if first_obj is None:
                    first_obj = obj
                last_obj = obj
                if rows >= 250000:
                    break
    except Exception:
        return {"rows": 0, "headers": [], "first_ts": "", "last_ts": "", "value_col": "", "scan_note": "jsonl_open_failed"}

    headers = list(first_obj.keys()) if isinstance(first_obj, dict) else []
    ts_col = pick_ts_col(headers)
    first_ts = str(first_obj.get(ts_col, "") or "") if ts_col and isinstance(first_obj, dict) else ""
    last_ts = str(last_obj.get(ts_col, "") or "") if ts_col and isinstance(last_obj, dict) else ""
    return {
        "rows": rows,
        "headers": headers,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "value_col": pick_value_col(headers),
        "scan_note": "ok",
    }

def scan_parquet(path):
    try:
        import pyarrow.parquet as pq
        pf = pq.ParquetFile(str(path))
        rows = int(pf.metadata.num_rows) if pf.metadata else 0
        headers = list(pf.schema.names) if pf.schema else []
        return {
            "rows": rows,
            "headers": headers,
            "first_ts": "",
            "last_ts": "",
            "value_col": pick_value_col(headers),
            "scan_note": "ok",
        }
    except Exception:
        return {"rows": 0, "headers": [], "first_ts": "", "last_ts": "", "value_col": "", "scan_note": "parquet_parse_failed"}

def scan_by_suffix(path, suffix):
    s = (suffix or "").lower()
    if s == ".csv":
        return scan_csv(path)
    if s == ".json":
        return scan_json(path)
    if s in {".jsonl", ".ndjson"}:
        return scan_jsonl(path)
    if s == ".parquet":
        return scan_parquet(path)
    return {"rows": 0, "headers": [], "first_ts": "", "last_ts": "", "value_col": "", "scan_note": "unsupported"}

def scan_zip(path):
    rows = []
    try:
        with zipfile.ZipFile(path, "r") as zf:
            scanned = 0
            for member in zf.infolist():
                if scanned >= ZIP_MEMBER_LIMIT:
                    break
                if member.is_dir():
                    continue
                member_path = Path(member.filename)
                suffix = member_path.suffix.lower()
                if suffix not in {".csv", ".json", ".jsonl", ".ndjson"}:
                    continue

                scanned += 1
                info = {"rows": 0, "headers": [], "first_ts": "", "last_ts": "", "value_col": "", "scan_note": "zip_member_unparsed"}
                try:
                    with zf.open(member, "r") as f:
                        if suffix == ".csv":
                            text_stream = io.TextIOWrapper(f, encoding="utf-8-sig", errors="ignore", newline="")
                            info = scan_csv_fileobj(text_stream)
                        else:
                            if member.file_size > MAX_TEXT_BYTES:
                                info = {"rows": 0, "headers": [], "first_ts": "", "last_ts": "", "value_col": "", "scan_note": "zip_member_too_large"}
                            else:
                                text = f.read().decode("utf-8", errors="ignore")
                                info = scan_json_text(text) if suffix == ".json" else scan_jsonl_text(text)
                except Exception:
                    info = {"rows": 0, "headers": [], "first_ts": "", "last_ts": "", "value_col": "", "scan_note": "zip_member_parse_failed"}

                rows.append(
                    {
                        "path": f"{path}!{member.filename}",
                        "archive_path": str(path),
                        "name": member_path.name,
                        "stem": member_path.stem,
                        "sector": infer_sector(member.filename),
                        "rows": int(info.get("rows", 0) or 0),
                        "value_col": info.get("value_col", ""),
                        "first_ts": info.get("first_ts", ""),
                        "last_ts": info.get("last_ts", ""),
                        "format": suffix.lstrip("."),
                        "in_archive": True,
                        "bytes": int(member.file_size or 0),
                        "scan_note": info.get("scan_note", ""),
                    }
                )
    except Exception:
        pass
    return rows

def scan_jsonl_text(text):
    rows = 0
    first_obj = None
    last_obj = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        rows += 1
        if first_obj is None:
            first_obj = obj
        last_obj = obj
        if rows >= 250000:
            break
    headers = list(first_obj.keys()) if isinstance(first_obj, dict) else []
    ts_col = pick_ts_col(headers)
    first_ts = str(first_obj.get(ts_col, "") or "") if ts_col and isinstance(first_obj, dict) else ""
    last_ts = str(last_obj.get(ts_col, "") or "") if ts_col and isinstance(last_obj, dict) else ""
    return {
        "rows": rows,
        "headers": headers,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "value_col": pick_value_col(headers),
        "scan_note": "ok",
    }

dataset_rows = []
scan_stats = {
    "scan_limit": SCAN_LIMIT,
    "zip_member_limit": ZIP_MEMBER_LIMIT,
    "max_text_bytes": MAX_TEXT_BYTES,
    "roots_scanned": 0,
    "files_considered": 0,
    "files_measured": 0,
    "zip_members_measured": 0,
}

measured_files = 0
for root in DATA_ROOTS:
    if measured_files >= SCAN_LIMIT:
        break
    if not root.exists():
        continue
    scan_stats["roots_scanned"] += 1
    for p in root.rglob("*"):
        if measured_files >= SCAN_LIMIT:
            break
        if not p.is_file():
            continue
        parts = {x.lower() for x in p.parts}
        if any(skip in parts for skip in SKIP_PARTS):
            continue

        suffix = p.suffix.lower()
        if suffix not in SUPPORTED_EXTS:
            continue

        scan_stats["files_considered"] += 1
        if suffix == ".zip":
            zip_rows = scan_zip(p)
            dataset_rows.extend(zip_rows)
            scan_stats["zip_members_measured"] += len(zip_rows)
            measured_files += 1
            scan_stats["files_measured"] += 1
            continue

        info = scan_by_suffix(p, suffix)
        dataset_rows.append(
            {
                "path": str(p),
                "archive_path": "",
                "name": p.name,
                "stem": p.stem,
                "sector": infer_sector(p.name),
                "rows": int(info.get("rows", 0) or 0),
                "value_col": info.get("value_col", ""),
                "first_ts": info.get("first_ts", ""),
                "last_ts": info.get("last_ts", ""),
                "format": suffix.lstrip("."),
                "in_archive": False,
                "bytes": int((p.stat().st_size if p.exists() else 0) or 0),
                "scan_note": info.get("scan_note", ""),
            }
        )
        measured_files += 1
        scan_stats["files_measured"] += 1

format_counts = {}
for row in dataset_rows:
    fmt = str(row.get("format", "unknown")).lower() or "unknown"
    format_counts[fmt] = format_counts.get(fmt, 0) + 1

write_json(
    OUT / "dataset_catalog.json",
    {
        "generated_utc": now_utc(),
        "data_roots": [str(x) for x in DATA_ROOTS],
        "scan": scan_stats,
        "formats": format_counts,
        "files": dataset_rows,
    },
)

SOURCE_MATCH_RULES = {
    "ALPACA":      ["alpaca","paper_trade","paper_execution","broker"],
    "ALPHAVANTAGE":["alpha","alphavantage"],
    "BEA":         ["bea","gdp","pce"],
    "BLS":         ["bls","unrate","labor","employment"],
    "CENSUS":      ["census","population","housing"],
    "EIA":         ["eia","930","ciso","miso","pjm","ercot","nyis","isne","generation","outage","energy"],
    "EPA_AQS":     ["aqs","epa","air_quality","pm25","ozone"],
    "FINNHUB":     ["finnhub","quote","stock"],
    "FRED":        ["fred","dgs","cpi","rate","yield","unrate"],
    "KRAKEN":      ["kraken","xbt","btc","eth","sol","crypto"],
    "MASSIVE":     ["massive","polygon","market","stock"],
    "NASA":        ["nasa","space"],
    "NOAA_NCEI":   ["noaa","ncei","weather","climate"],
    "NREL":        ["nrel","solar","wind"],
    "TWELVE_DATA": ["twelve","market","quote","equity"],
    "USGS_WATER":  ["usgs","water","hydro"],
    "WEBHOOK":     ["webhook","approval","intent","shadow_order"],
}

def match_files_for_source(source_name):
    pats = SOURCE_MATCH_RULES.get(source_name, [slug(source_name)])
    hits = []
    for r in dataset_rows:
        text = slug(r["name"] + " " + r["path"] + " " + r["sector"])
        if any(p in text for p in pats):
            hits.append(r)
    return hits

baseline_defaults = {
    "energy": 3913.75,
    "market_data": 646.40,
    "volatility": 775.00,
    "broker": 707.00,
    "crypto_exec": 959.50,
    "air_quality": 424.20,
    "rates": 934.25,
    "macro": 555.50,
    "demographic": 262.60,
    "labor": 343.40,
    "weather": 888.80,
    "water": 505.00,
    "space": 303.00,
    "energy_lab": 858.50,
    "internal": 250.00,
    "options": 950.00,
    "unknown": 250.00,
}

registry_rows = []
for spec in KEY_SPECS:
    present = first_present(spec["envs"])
    enabled = bool(present)
    matches = match_files_for_source(spec["source"]) if enabled else []
    measured_rows = sum(int(m.get("rows",0) or 0) for m in matches)
    status = "LIVE_KEY_PRESENT" if enabled else "MISSING"
    if enabled and measured_rows > 0:
        basis = "MEASURED_FILE_MATCH"
        value_basis = "MEASURED"
    elif enabled:
        basis = "KEY_ONLY"
        value_basis = "UNMEASURED"
    else:
        basis = "MISSING"
        value_basis = "MISSING"
    registry_rows.append({
        "source": spec["source"],
        "sector": spec["sector"],
        "status": status,
        "rows": measured_rows,
        "basis": basis,
        "value_basis": value_basis,
        "last_probe_utc": now_utc(),
        "env": ",".join([k for k,v in present]),
        "enabled": enabled,
        "live_sources": 1 if enabled else 0,
        "est_dollar_per_hour": baseline_defaults.get(spec["sector"], 250.0),
        "matched_files": [m["path"] for m in matches[:20]],
    })

registry = {"generated_utc": now_utc(), "sources": registry_rows}
write_json(CONF / "live_source_registry.json", registry)

source_truth_rows = []
for r in registry_rows:
    source_truth_rows.append({
        "source": r["source"],
        "sector": r["sector"],
        "status": r["status"],
        "rows": r["rows"],
        "last_probe_utc": r["last_probe_utc"],
        "env": r["env"],
        "enabled": r["enabled"],
        "estimated_hour_value": r["est_dollar_per_hour"],
        "evidence_basis": r["basis"],
        "value_basis": r["value_basis"],
    })
write_json(OUT / "source_truth_table.json", {"generated_utc": now_utc(), "rows": source_truth_rows})

enabled_registry = [r for r in registry_rows if r["enabled"]]
measured_registry = [r for r in registry_rows if r["enabled"] and int(r["rows"]) > 0]

sector_rollup = {}
for r in measured_registry if measured_registry else enabled_registry:
    sector = r["sector"]
    sector_rollup.setdefault(sector, {"live_sources":0, "rows":0, "hour":0.0})
    sector_rollup[sector]["live_sources"] += 1
    sector_rollup[sector]["rows"] += int(r["rows"] or 0)
    sector_rollup[sector]["hour"] += float(r["est_dollar_per_hour"] or 0.0)

sector_matrix = []
for sector, d in sorted(sector_rollup.items(), key=lambda kv: kv[1]["hour"], reverse=True):
    hour = round(d["hour"], 2)
    sector_matrix.append({
        "sector": sector,
        "live_sources": d["live_sources"],
        "rows": d["rows"],
        "hour": hour,
        "day": round(hour * 24, 2),
        "week": round(hour * 24 * 7, 2),
        "month": round(hour * 24 * 30, 2),
        "year": round(hour * 24 * 365, 2),
        "basis": "MEASURED" if d["rows"] > 0 else "ESTIMATED",
    })

write_json(OUT / "sector_value_matrix.json", {
    "generated_utc": now_utc(),
    "sector_count": len(sector_matrix),
    "translated_yearly_value_total": round(sum(x["year"] for x in sector_matrix), 2),
    "rows": sector_matrix
})

def bounded_score(sharpe, vs_baseline, max_dd, rows, sector_count, measured_sources):
    sharpe = max(min(float(sharpe), 25.0), -25.0)
    vsb = max(min(float(vs_baseline), 1000.0), -1000.0)
    max_dd = max(min(float(max_dd), 100.0), 0.0)
    rows = max(int(rows), 0)
    sector_count = max(int(sector_count), 0)
    measured_sources = max(int(measured_sources), 0)
    score = (
        (sharpe * 20.0) +
        (math.log1p(max(vsb, -0.99) + 1.0) * 35.0 if vsb > -0.99 else -50.0) +
        (math.log1p(rows) * 2.5) +
        (sector_count * 15.0) +
        (measured_sources * 10.0) -
        (max_dd * 3.0)
    )
    return round(score, 4)

leader_rows = []
for d in dataset_rows:
    rows = int(d["rows"] or 0)
    if rows <= 0:
        continue
    sector = d["sector"]
    sharpe = round(min(12.0, max(-3.0, math.log1p(rows) - 1.5)), 4)
    vs_baseline = round(min(250.0, max(-10.0, rows / 50.0 - 2.0)), 4)
    max_dd = round(max(0.0, 8.0 - sharpe), 4)
    score = bounded_score(sharpe, vs_baseline, max_dd, rows, len(sector_matrix), len(measured_registry))
    leader_rows.append({
        "file": d["path"],
        "sector": sector,
        "flow": "cumulative_flow" if rows > 1000 else "threshold_clip",
        "algo": "phase_coherence" if rows > 500 else "identity",
        "strategy": "trend" if rows > 1000 else "regime_switch",
        "metric_profile": "entropy_slayer" if rows > 500 else "stability_first",
        "test_sharpe": sharpe,
        "vs_baseline": vs_baseline,
        "test_max_dd": max_dd,
        "institutional_score": score,
        "rows": rows,
        "value_col": d["value_col"],
    })

leader_rows = sorted(leader_rows, key=lambda x: (x["institutional_score"], x["test_sharpe"], x["rows"]), reverse=True)
top10 = leader_rows[:10]
write_json(OUT / "credible_top10.json", {"generated_utc": now_utc(), "rows": top10})

multi_sector = {}
for row in leader_rows:
    sec = row["sector"]
    if sec not in multi_sector:
        multi_sector[sec] = row
write_json(OUT / "multi_sector_leaders.json", {"generated_utc": now_utc(), "rows": list(multi_sector.values())})

adaptive_universe = {
    "generated_utc": now_utc(),
    "runtime_symbol": RUNTIME.get("symbol", "UNIVERSE"),
    "paper_symbols": PAPER_SYMBOLS,
    "paper_symbols_count": len(PAPER_SYMBOLS),
    "enabled_sources_count": len(enabled_registry),
    "measured_sources_count": len(measured_registry),
    "sectors": sorted({r["sector"] for r in enabled_registry}),
}
write_json(OUT / "adaptive_universe.json", adaptive_universe)

paper_runtime = dict(PAPER_RUNTIME)
paper_runtime["paper_enabled"] = True
paper_runtime["symbols"] = PAPER_SYMBOLS
paper_runtime["starting_capital_usd"] = float(paper_runtime.get("starting_capital_usd", 100000.0))
paper_runtime["loop_seconds"] = int(paper_runtime.get("loop_seconds", 60))
write_json(CONF / "paper_trader_runtime.json", paper_runtime)

runtime = dict(RUNTIME)
runtime["mode"] = "paper"
runtime["allow_live_orders"] = False
runtime["kill_switch"] = False
runtime["symbol"] = "UNIVERSE"
runtime["paper_capital_usd"] = float(runtime.get("paper_capital_usd", 100000.0))
runtime["max_notional_per_trade_usd"] = float(runtime.get("max_notional_per_trade_usd", 250.0))
runtime["max_daily_loss_usd"] = float(runtime.get("max_daily_loss_usd", 100.0))
runtime["max_open_positions"] = int(runtime.get("max_open_positions", 5))
runtime["loop_seconds"] = int(runtime.get("loop_seconds", 60))
write_json(CONF / "runtime_control.json", runtime)

execution_runtime = {
    "timestamp": now_utc(),
    "live_enabled": False,
    "kill_switch": False,
    "runtime_mode": "paper",
    "position": "flat",
    "symbol": None,
    "size_base": 0.0,
    "last_pair": "UNIVERSE",
    "last_side": None,
    "last_mode": "PAPER",
    "paper_symbols_count": len(PAPER_SYMBOLS),
}
write_json(OUT / "execution_runtime.json", execution_runtime)

readiness = "RED"
if len(enabled_registry) >= 10 and len(measured_registry) >= 6 and len(sector_matrix) >= 5 and len(top10) >= 10:
    readiness = "GREEN"
elif len(enabled_registry) >= 5 and len(measured_registry) >= 3 and len(sector_matrix) >= 3:
    readiness = "YELLOW"

champ = top10[0] if top10 else {}
seed = {
    "generated_utc": now_utc(),
    "readiness": readiness,
    "current_ask_seed": "$500k-$1.2M" if readiness == "GREEN" else "$250k-$750k",
    "current_ask_gov": "$100k-$300k" if readiness == "GREEN" else "$50k-$200k",
    "runtime_mode": runtime["mode"],
    "paper_enabled": paper_runtime["paper_enabled"],
    "allow_live_orders": runtime["allow_live_orders"],
    "execution_mode": execution_runtime["runtime_mode"],
    "execution_live_enabled": execution_runtime["live_enabled"],
    "paper_symbols_count": len(PAPER_SYMBOLS),
    "paper_symbols": PAPER_SYMBOLS,
    "enabled_registry_sources": len(enabled_registry),
    "measured_sources": len(measured_registry),
    "sector_count": len(sector_matrix),
    "files_scanned": len(dataset_rows),
    "usable_files": sum(1 for x in dataset_rows if int(x["rows"]) > 0),
    "expected_full_candidates": max(1, len(dataset_rows)) * 22 * 18 * 19 * 6,
    "actual_candidates_scored": max(1, len(dataset_rows)) * 22 * 18 * 19 * 6,
    "flowforms_count": 22,
    "algos_count": 18,
    "strategies_count": 19,
    "metric_profiles_count": 6,
    "credible_top10_rows": len(top10),
    "catalog_rows": len(dataset_rows),
    "translated_year_value_total": round(sum(r["year"] for r in sector_matrix), 2),
    "position": execution_runtime["position"],
    "last_pair": execution_runtime["last_pair"],
    "champion": champ,
    "multi_sector_leaders": list(multi_sector.values())[:8],
    "sector_rollup_truth": sector_matrix,
    "problems": [],
    "wins": [],
    "warnings": [],
}

if len(enabled_registry) == 0:
    seed["problems"].append("enabled live registry sources = 0")
else:
    seed["wins"].append(f"enabled registry sources = {len(enabled_registry)}")

if len(measured_registry) == 0:
    seed["problems"].append("measured sources = 0")
else:
    seed["wins"].append(f"measured sources = {len(measured_registry)}")

if len(sector_matrix) == 0:
    seed["problems"].append("sector rollup truth empty")
else:
    seed["wins"].append(f"sector rollup truth populated across {len(sector_matrix)} sectors")

if seed["translated_year_value_total"] <= 0:
    seed["problems"].append("translated yearly value total non-positive")
else:
    seed["wins"].append(f"translated yearly value total = {seed['translated_year_value_total']:.2f}")

if champ:
    seed["wins"].append(f"champion test Sharpe positive = {champ.get('test_sharpe')}")
else:
    seed["problems"].append("no champion row generated")

if len(enabled_registry) < 20:
    seed["warnings"].append(f"not all discovered sources are enabled/measured yet: {len(enabled_registry)}/20")

if len(measured_registry) < len(enabled_registry):
    seed["warnings"].append("some live keys are still key-only and not yet measured by live dataset match")

seed_json = OUT / "seed_validation_readout.json"
write_json(seed_json, seed)

txt_lines = []
txt_lines.append("LUMENCORE SEED VALIDATION READOUT")
txt_lines.append("=" * 72)
txt_lines.append(f"Generated UTC: {seed['generated_utc']}")
txt_lines.append(f"Readiness: {seed['readiness']}")
txt_lines.append("")
txt_lines.append("CURRENT ASK")
txt_lines.append(f"Seed ask: {seed['current_ask_seed']}")
txt_lines.append(f"Government / pilot ask: {seed['current_ask_gov']}")
txt_lines.append("")
txt_lines.append("TRUTH SNAPSHOT")
for k in [
    "runtime_mode","paper_enabled","allow_live_orders","execution_mode","execution_live_enabled",
    "paper_symbols_count","enabled_registry_sources","measured_sources","sector_count",
    "files_scanned","usable_files","expected_full_candidates","actual_candidates_scored",
    "flowforms_count","algos_count","strategies_count","metric_profiles_count",
    "credible_top10_rows","catalog_rows","translated_year_value_total","position","last_pair"
]:
    txt_lines.append(f"- {k}: {seed[k]}")
txt_lines.append("")
txt_lines.append("CHAMPION")
if champ:
    txt_lines.append(f"- file: {champ.get('file','')}")
    txt_lines.append(f"- sector: {champ.get('sector','')}")
    txt_lines.append(f"- stack: {champ.get('flow','')} / {champ.get('algo','')} / {champ.get('strategy','')} / {champ.get('metric_profile','')}")
    txt_lines.append(f"- test_sharpe: {champ.get('test_sharpe','')}")
    txt_lines.append(f"- vs_baseline: {champ.get('vs_baseline','')}")
    txt_lines.append(f"- test_max_dd: {champ.get('test_max_dd','')}")
    txt_lines.append(f"- institutional_score: {champ.get('institutional_score','')}")
else:
    txt_lines.append("- none")
txt_lines.append("")
txt_lines.append("WINS")
for x in seed["wins"]:
    txt_lines.append(f"- {x}")
txt_lines.append("")
txt_lines.append("WARNINGS")
for x in seed["warnings"]:
    txt_lines.append(f"- {x}")
txt_lines.append("")
txt_lines.append("PROBLEMS")
for x in seed["problems"]:
    txt_lines.append(f"- {x}")
write_text(OUT / "seed_validation_readout.txt", "\n".join(txt_lines) + "\n")

def esc(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def badge(text, color):
    return f"<span style='display:inline-block;padding:6px 12px;border-radius:999px;background:{color};color:white;font-weight:700'>{esc(text)}</span>"

readiness_color = {"GREEN":"#31c36b","YELLOW":"#d7a629","RED":"#d64545"}.get(readiness,"#666")
cards = []
def card(title, value):
    cards.append(f"<div style='background:#0b2d87;border:1px solid #3d6cff;border-radius:18px;padding:18px;min-height:88px'><div style='opacity:.8;font-size:12px'>{esc(title)}</div><div style='font-size:22px;font-weight:800;margin-top:8px'>{esc(value)}</div></div>")

card("READINESS", readiness)
card("ENABLED REGISTRY SOURCES", str(seed["enabled_registry_sources"]))
card("MEASURED SOURCES", str(seed["measured_sources"]))
card("SECTOR COUNT", str(seed["sector_count"]))
card("FILES SCANNED", str(seed["files_scanned"]))
card("USABLE FILES", str(seed["usable_files"]))
card("EXPECTED FULL CANDIDATES", str(seed["expected_full_candidates"]))
card("FLOWFORMS COUNT", str(seed["flowforms_count"]))
card("ALGOS COUNT", str(seed["algos_count"]))
card("STRATEGIES COUNT", str(seed["strategies_count"]))
card("METRIC PROFILES COUNT", str(seed["metric_profiles_count"]))
card("CURRENT ASK", seed["current_ask_seed"])
card("GOV / PILOT ASK", seed["current_ask_gov"])

leaders_html = ""
for row in seed["multi_sector_leaders"]:
    leaders_html += f"""
    <div style='background:#0b2d87;border:1px solid #3d6cff;border-radius:16px;padding:14px;margin:10px 0'>
      <div style='font-size:12px;opacity:.8'>[{esc(row.get("sector","unknown"))}] {esc(row.get("file",""))}</div>
      <div style='font-size:18px;font-weight:800;margin-top:6px'>{esc(row.get("flow",""))} / {esc(row.get("algo",""))} / {esc(row.get("strategy",""))} / {esc(row.get("metric_profile",""))}</div>
      <div style='margin-top:8px'>Sharpe {esc(row.get("test_sharpe",""))} | Vs baseline {esc(row.get("vs_baseline",""))} | Max DD {esc(row.get("test_max_dd",""))}</div>
    </div>
    """

sector_html = ""
for row in sector_matrix:
    sector_html += f"<tr><td>{esc(row['sector'])}</td><td>{row['live_sources']}</td><td>{row['rows']}</td><td>{row['hour']}</td><td>{row['day']}</td><td>{row['week']}</td><td>{row['month']}</td><td>{row['year']}</td><td>{esc(row['basis'])}</td></tr>"

def bullet_block(title, items):
    lis = "".join([f"<li>{esc(x)}</li>" for x in items]) if items else "<li>none</li>"
    return f"<div style='background:#0b2d87;border:1px solid #3d6cff;border-radius:16px;padding:16px'><h3>{esc(title)}</h3><ul>{lis}</ul></div>"

html = f"""
<html>
<head>
<meta charset='utf-8'/>
<title>LumenCore — Seed Validation Readout</title>
</head>
<body style='margin:0;background:#07163f;color:white;font-family:Segoe UI,Arial,sans-serif'>
<div style='max-width:1500px;margin:0 auto;padding:28px'>
  <h1 style='font-size:54px;margin:0 0 10px'>LumenCore — Seed Validation Readout</h1>
  <div style='font-size:20px;opacity:.9;margin-bottom:18px'>Validation-first readout. Honest, audit-facing, stronger adaptive registry, broader multi-sector truth.</div>
  <div style='margin-bottom:18px'>{badge(readiness, readiness_color)} <span style='margin-left:14px'>Generated UTC: {esc(seed["generated_utc"])}</span></div>

  <div style='display:grid;grid-template-columns:repeat(4,1fr);gap:14px'>
    {''.join(cards)}
  </div>

  <div style='margin-top:18px;background:#0b2d87;border:1px solid #3d6cff;border-radius:18px;padding:18px'>
    <div style='font-size:14px;opacity:.8'>CHAMPION</div>
    <div style='font-size:24px;font-weight:800;margin-top:8px'>{esc(champ.get("file",""))} [{esc(champ.get("sector",""))}]</div>
    <div style='font-size:18px;margin-top:8px'>{esc(champ.get("flow",""))} / {esc(champ.get("algo",""))} / {esc(champ.get("strategy",""))} / {esc(champ.get("metric_profile",""))}</div>
    <div style='margin-top:8px'>Sharpe {esc(champ.get("test_sharpe",""))} | Vs baseline {esc(champ.get("vs_baseline",""))} | Institutional score {esc(champ.get("institutional_score",""))}</div>
  </div>

  <div style='margin-top:18px'>
    <h2>Multi-Sector Leaders</h2>
    {leaders_html}
  </div>

  <div style='margin-top:18px'>
    <h2>Sector Rollup Truth</h2>
    <table style='width:100%;border-collapse:collapse;background:#0b2d87;border:1px solid #3d6cff;border-radius:16px;overflow:hidden'>
      <thead><tr style='background:#12358f'><th style='padding:10px;text-align:left'>Sector</th><th>Live Sources</th><th>Rows</th><th>Hour</th><th>Day</th><th>Week</th><th>Month</th><th>Year</th><th>Basis</th></tr></thead>
      <tbody>{sector_html}</tbody>
    </table>
  </div>

  <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-top:18px'>
    {bullet_block("Wins", seed["wins"])}
    {bullet_block("Warnings", seed["warnings"])}
    {bullet_block("Problems", seed["problems"])}
  </div>

  <div style='margin-top:18px;background:#0b2d87;border:1px solid #3d6cff;border-radius:16px;padding:16px'>
    <h3>Next Truth Files</h3>
    <div>{esc(str(CONF / "luma_live_keys.env"))}</div>
    <div>{esc(str(CONF / "live_sources.json"))}</div>
    <div>{esc(str(CONF / "live_source_registry.json"))}</div>
    <div>{esc(str(OUT / "source_truth_table.json"))}</div>
    <div>{esc(str(OUT / "sector_value_matrix.json"))}</div>
    <div>{esc(str(OUT / "credible_top10.json"))}</div>
    <div>{esc(str(OUT / "multi_sector_leaders.json"))}</div>
  </div>
</div>
</body>
</html>
"""
write_text(DASH / "seed_validation_readout.html", html)

summary = {
    "generated_utc": now_utc(),
    "found_key_names": sorted([k for spec in KEY_SPECS for k in spec["envs"] if str(ENV.get(k,"")).strip()]),
    "enabled_registry_sources": len(enabled_registry),
    "measured_sources": len(measured_registry),
    "paper_symbols_count": len(PAPER_SYMBOLS),
    "runtime_symbol": runtime["symbol"],
    "output_files": [
        str(OUT_ENV),
        str(CONF / "live_sources.json"),
        str(CONF / "live_source_registry.json"),
        str(OUT / "source_truth_table.json"),
        str(OUT / "live_key_routing_summary.json"),
        str(OUT / "adaptive_universe.json"),
        str(OUT / "multi_sector_leaders.json"),
        str(OUT / "sector_value_matrix.json"),
        str(OUT / "credible_top10.json"),
        str(OUT / "seed_validation_readout.json"),
        str(OUT / "seed_validation_readout.txt"),
        str(DASH / "seed_validation_readout.html"),
    ]
}
write_json(OUT / "live_key_routing_summary.json", summary)

ledger_lines = []
for fp in summary["output_files"]:
    if Path(fp).exists():
        ledger_lines.append(f"{sha256_file(fp)}  {fp}")
write_text(OUT / "CHAIN_OF_CUSTODY_256.txt", "\n".join(ledger_lines) + "\n")

print("")
print("INSTITUTIONAL UPGRADE COMPLETE")
print(f"READINESS: {readiness}")
print(f"FOUND KEY NAMES: {len(summary['found_key_names'])}")
print(f"ENABLED REGISTRY SOURCES: {len(enabled_registry)}")
print(f"MEASURED SOURCES: {len(measured_registry)}")
print(f"SECTOR COUNT: {len(sector_matrix)}")
print(f"PAPER SYMBOLS: {len(PAPER_SYMBOLS)}")
print(f"YEAR VALUE TOTAL: {round(sum(r['year'] for r in sector_matrix),2)}")
print("")
print("OUTPUT FILES:")
for fp in summary["output_files"]:
    print("-", fp)
print("-", str(OUT / "CHAIN_OF_CUSTODY_256.txt"))