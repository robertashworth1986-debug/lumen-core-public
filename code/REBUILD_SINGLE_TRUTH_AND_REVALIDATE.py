import csv, json, math, html, re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE = ROOT / "code"
CONF = ROOT / "config"
OUT  = ROOT / "out"
DASH = Path(r"C:\LumaTrader\dashboard")

for p in [CODE, CONF, OUT, DASH]:
    p.mkdir(parents=True, exist_ok=True)

DATA_ROOTS = [
    ROOT / "data",
    Path(r"C:\LumaTrader\data"),
    Path(r"C:\Users\Novac\iCloudDrive\Data sets"),
    Path(r"C:\Users\Novac\iCloudDrive\Downloads"),
]

BASELINE_DEFAULTS = {
    "energy": 3913.75,
    "market_data": 646.40,
    "crypto_exec": 959.50,
    "broker": 707.00,
    "rates": 934.25,
    "weather": 888.80,
    "energy_lab": 858.50,
    "air_quality": 424.20,
    "macro": 555.50,
    "water": 505.00,
    "labor": 343.40,
    "space": 303.00,
    "demographic": 262.60,
    "internal": 250.00,
    "options": 850.00,
    "volatility": 775.00,
}

REGISTRY_SECTOR_MAP = {
    "eia": "energy",
    "fred": "rates",
    "bea": "macro",
    "census": "demographic",
    "bls": "labor",
    "noaa_ncei": "weather",
    "nasa": "space",
    "nrel": "energy_lab",
    "usgs_water": "water",
    "epa_aqs_key": "air_quality",
    "epa_aqs_email": "air_quality",
    "alpaca": "broker",
    "alpaca_secret": "broker",
    "kraken_key": "crypto_exec",
    "kraken_secret": "crypto_exec",
    "polygon": "market_data",
    "finnhub": "market_data",
    "twelve_data": "market_data",
    "massive": "market_data",
    "webhook": "internal",
    "implied": "options",
    "tradier": "options",
    "cboe": "volatility",
}

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def load_json(path, default=None):
    if default is None:
        default = {}
    path = Path(path)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return default

def save_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2), encoding="utf-8")

def load_csv_rows(path):
    path = Path(path)
    if not path.exists():
        return []
    for enc in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except Exception:
            pass
    return []

def as_float(v, default=0.0):
    try:
        if v is None:
            return default
        s = str(v).strip().replace(",", "")
        if s == "" or s.lower() == "nan":
            return default
        return float(s)
    except Exception:
        return default

def as_int(v, default=0):
    try:
        if v is None:
            return default
        s = str(v).strip().replace(",", "")
        if s == "" or s.lower() == "nan":
            return default
        return int(float(s))
    except Exception:
        return default

def norm(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).strip().lower()).strip("_")

def infer_sector(text):
    t = norm(text)
    if any(k in t for k in ["implied", "iv_", "vol_surface", "option", "options", "oi_", "gamma", "delta", "vega", "theta", "skew"]):
        return "options"
    if any(k in t for k in ["vix", "volatility", "cboe"]):
        return "volatility"
    if any(k in t for k in ["kraken", "xbt", "btc", "eth", "sol", "crypto"]):
        return "crypto_exec"
    if any(k in t for k in ["alpaca", "broker", "order", "execution", "trade"]):
        return "broker"
    if any(k in t for k in ["eia", "iso", "pjm", "ercot", "miso", "caiso", "isne", "nyiso", "930", "generation", "outage", "nuclear", "power", "grid", "energy"]):
        return "energy"
    if any(k in t for k in ["nrel", "renewable", "solar", "wind"]):
        return "energy_lab"
    if any(k in t for k in ["fred", "dgs", "yield", "rate", "cpi", "cpi", "inflation"]):
        return "rates"
    if any(k in t for k in ["bea", "gdp", "macro", "pce"]):
        return "macro"
    if any(k in t for k in ["census", "population", "demographic"]):
        return "demographic"
    if any(k in t for k in ["bls", "unrate", "employment", "labor", "payroll"]):
        return "labor"
    if any(k in t for k in ["noaa", "weather", "climate", "storm", "temp", "precip"]):
        return "weather"
    if any(k in t for k in ["usgs", "water", "hydro", "river", "streamflow"]):
        return "water"
    if any(k in t for k in ["nasa", "space", "orbit", "satellite"]):
        return "space"
    if any(k in t for k in ["aqs", "air_quality", "epa"]):
        return "air_quality"
    if any(k in t for k in ["polygon", "finnhub", "twelve", "massive", "market", "equity", "stock", "etf"]):
        return "market_data"
    return "internal"

def fmt_money(v):
    return "${:,.2f}".format(as_float(v, 0.0))

def fmt_num(v):
    return "{:,.0f}".format(as_float(v, 0.0))

runtime = load_json(CONF / "runtime_control.json", {})
paper_runtime = load_json(CONF / "paper_trader_runtime.json", {})
infra_runtime = load_json(CONF / "infra_live_runtime.json", {})
live_sources_cfg = load_json(CONF / "live_sources.json", {})
live_registry_cfg = load_json(CONF / "live_source_registry.json", {})
truth_report_prev = load_json(OUT / "stack_truth_report.json", {})
source_truth_prev = load_json(OUT / "source_truth_table.json", {})
full_beast_summary = load_json(OUT / "full_beast_summary.json", {})
execution_runtime = load_json(OUT / "execution_runtime.json", {})
execution_status = load_json(OUT / "execution_status.json", {})
adaptive_champion = load_json(OUT / "adaptive_champion.json", {})
data_ingest_proof = load_json(OUT / "data_ingest_proof.json", {})
sector_value_matrix_prev = load_json(OUT / "sector_value_matrix.json", [])
seed_validation_prev = load_json(OUT / "seed_validation_readout.json", {})

dataset_catalog_rows = load_csv_rows(OUT / "dataset_catalog.csv")
scan_rows = load_csv_rows(OUT / "data_scan_summary.csv")
credible_rows = load_csv_rows(OUT / "credible_top10.csv")
empty_rows = load_csv_rows(OUT / "empty_report.csv")
auto_dataset_rows = load_csv_rows(OUT / "auto_dataset_results.csv")

enabled_registry_rows = []

cfg_sources = live_registry_cfg.get("sources", [])
if isinstance(cfg_sources, list):
    for r in cfg_sources:
        if not isinstance(r, dict):
            continue
        status = str(r.get("status", "")).upper()
        enabled = bool(r.get("enabled", False))
        source_name = str(r.get("source", "")).strip()
        sector = str(r.get("sector", "")).strip() or REGISTRY_SECTOR_MAP.get(norm(source_name), infer_sector(source_name))
        rows = as_int(r.get("rows", 0), 0)
        est = as_float(r.get("est_dollar_per_hour", r.get("estimated_hour_value", BASELINE_DEFAULTS.get(sector, 250.0))), BASELINE_DEFAULTS.get(sector, 250.0))
        if enabled and status == "LIVE_KEY_PRESENT":
            enabled_registry_rows.append({
                "source": source_name,
                "sector": sector,
                "status": status,
                "rows": max(rows, 1),
                "enabled": True,
                "last_probe_utc": r.get("last_probe_utc", now_utc()),
                "env": r.get("env", ""),
                "estimated_hour_value": est,
                "value_basis": "MEASURED" if rows > 1 else "ESTIMATED"
            })

if not enabled_registry_rows:
    prev_sources = source_truth_prev.get("sources", [])
    if isinstance(prev_sources, list):
        for r in prev_sources:
            if not isinstance(r, dict):
                continue
            status = str(r.get("status", "")).upper()
            enabled = bool(r.get("enabled", False))
            if enabled and status == "LIVE_KEY_PRESENT":
                sector = str(r.get("sector", "")).strip() or infer_sector(r.get("source", ""))
                rows = as_int(r.get("rows", 0), 0)
                est = as_float(r.get("estimated_hour_value", BASELINE_DEFAULTS.get(sector, 250.0)), BASELINE_DEFAULTS.get(sector, 250.0))
                enabled_registry_rows.append({
                    "source": r.get("source", ""),
                    "sector": sector,
                    "status": status,
                    "rows": max(rows, 1),
                    "enabled": True,
                    "last_probe_utc": r.get("last_probe_utc", now_utc()),
                    "env": r.get("env", ""),
                    "estimated_hour_value": est,
                    "value_basis": "MEASURED" if rows > 1 else "ESTIMATED"
                })

usable_scan_rows = []
for r in scan_rows:
    file_name = str(r.get("file", "")).strip()
    source_path = str(r.get("source_path", "")).strip()
    clean_path = str(r.get("clean_path", "")).strip()
    status = str(r.get("status", "")).strip().lower()
    rows = as_int(r.get("rows", r.get("ret_len", 0)), 0)
    if status != "usable":
        continue
    sector = infer_sector(" | ".join([file_name, source_path, clean_path]))
    usable_scan_rows.append({
        "file": file_name,
        "source_path": source_path,
        "clean_path": clean_path,
        "sector": sector,
        "rows": rows,
        "value_col": r.get("value_col", ""),
        "time_col": r.get("time_col", ""),
        "quality_score": as_float(r.get("quality_score", 0.0), 0.0),
        "value_basis": "MEASURED" if rows > 1 else "ESTIMATED",
    })

if not usable_scan_rows:
    top_clean = data_ingest_proof.get("top_clean_files", [])
    if isinstance(top_clean, list):
        for r in top_clean:
            if not isinstance(r, dict):
                continue
            file_name = str(r.get("file", "")).strip()
            clean_path = str(r.get("clean_path", "")).strip()
            source_path = str(r.get("source_path", "")).strip()
            rows = as_int(r.get("rows", 0), 0)
            sector = infer_sector(" | ".join([file_name, source_path, clean_path]))
            usable_scan_rows.append({
                "file": file_name,
                "source_path": source_path,
                "clean_path": clean_path,
                "sector": sector,
                "rows": rows,
                "value_col": r.get("value_col", ""),
                "time_col": r.get("time_col", ""),
                "quality_score": as_float(r.get("quality_score", 0.0), 0.0),
                "value_basis": "MEASURED" if rows > 1 else "ESTIMATED",
            })

baseline_rates = dict(BASELINE_DEFAULTS)
infra_base = infra_runtime.get("baseline_loss_rates", {})
if isinstance(infra_base, dict):
    for k, v in infra_base.items():
        nk = norm(k)
        if "power" in nk or "grid" in nk:
            baseline_rates["energy"] = as_float(v, baseline_rates["energy"])
        elif "market" in nk:
            baseline_rates["market_data"] = as_float(v, baseline_rates["market_data"])
        elif "weather" in nk or "climate" in nk:
            baseline_rates["weather"] = as_float(v, baseline_rates["weather"])
        elif "water" in nk or "hydro" in nk:
            baseline_rates["water"] = as_float(v, baseline_rates["water"])
        elif "space" in nk:
            baseline_rates["space"] = as_float(v, baseline_rates["space"])
        elif "labor" in nk:
            baseline_rates["labor"] = as_float(v, baseline_rates["labor"])
        elif "economic" in nk or "macro" in nk:
            baseline_rates["macro"] = as_float(v, baseline_rates["macro"])
        elif "data_center" in nk or "telecom" in nk:
            baseline_rates["market_data"] = max(baseline_rates["market_data"], as_float(v, baseline_rates["market_data"]))

sector_rollup = {}

for r in enabled_registry_rows:
    s = r["sector"]
    sector_rollup.setdefault(s, {"sector": s, "live_sources": 0, "rows": 0, "hour": 0.0, "basis": "ESTIMATED"})
    sector_rollup[s]["live_sources"] += 1
    sector_rollup[s]["rows"] += max(as_int(r.get("rows", 0), 0), 1)
    sector_rollup[s]["hour"] += as_float(r.get("estimated_hour_value", baseline_rates.get(s, 250.0)), baseline_rates.get(s, 250.0))
    if str(r.get("value_basis", "ESTIMATED")).upper() == "MEASURED":
        sector_rollup[s]["basis"] = "MEASURED"

for r in usable_scan_rows:
    s = r["sector"]
    sector_rollup.setdefault(s, {"sector": s, "live_sources": 0, "rows": 0, "hour": 0.0, "basis": "ESTIMATED"})
    add_rows = max(as_int(r.get("rows", 0), 0), 1)
    sector_rollup[s]["rows"] += add_rows
    if sector_rollup[s]["live_sources"] == 0:
        sector_rollup[s]["live_sources"] = 1
    if sector_rollup[s]["hour"] <= 0:
        sector_rollup[s]["hour"] = baseline_rates.get(s, 250.0)
    if add_rows > 1:
        sector_rollup[s]["basis"] = "MEASURED"

sector_table = []
for s, d in sector_rollup.items():
    hr = as_float(d.get("hour", baseline_rates.get(s, 250.0)), baseline_rates.get(s, 250.0))
    sector_table.append({
        "sector": s,
        "live_sources": as_int(d.get("live_sources", 0), 0),
        "rows": as_int(d.get("rows", 0), 0),
        "hour": round(hr, 2),
        "day": round(hr * 24, 2),
        "week": round(hr * 24 * 7, 2),
        "month": round(hr * 24 * 30, 2),
        "year": round(hr * 24 * 365, 2),
        "basis": "MEASURED" if str(d.get("basis", "ESTIMATED")).upper() == "MEASURED" else "ESTIMATED",
    })

sector_table = sorted(sector_table, key=lambda x: (as_float(x["hour"]), as_int(x["rows"])), reverse=True)
translated_year_value_total = round(sum(as_float(r["year"]) for r in sector_table), 2)

top_file = str(full_beast_summary.get("top_file", adaptive_champion.get("file", "UNKNOWN")))
top_flow = str(full_beast_summary.get("top_flow", adaptive_champion.get("flow", "UNKNOWN")))
top_algo = str(full_beast_summary.get("top_algo", adaptive_champion.get("algo", "UNKNOWN")))
top_strategy = str(full_beast_summary.get("top_strategy", adaptive_champion.get("strategy", "UNKNOWN")))
top_profile = str(full_beast_summary.get("top_metric_profile", adaptive_champion.get("metric_profile", "UNKNOWN")))
top_sharpe = as_float(full_beast_summary.get("top_test_sharpe", adaptive_champion.get("sharpe", 0.0)), 0.0)
top_vs_baseline = as_float(full_beast_summary.get("top_test_vs_baseline", adaptive_champion.get("vs_baseline", 0.0)), 0.0)
top_score = as_float(full_beast_summary.get("top_institutional_score", adaptive_champion.get("score", 0.0)), 0.0)
top_sector = infer_sector(top_file)

paper_enabled = bool(paper_runtime.get("paper_enabled", False))
runtime_mode = str(runtime.get("mode", "unknown"))
allow_live = bool(runtime.get("allow_live_orders", False))
execution_mode = str(execution_runtime.get("runtime_mode", execution_status.get("execution_mode", "unknown")))
execution_live_enabled = bool(execution_runtime.get("live_enabled", False))
paper_symbols = paper_runtime.get("symbols", [])
if not isinstance(paper_symbols, list):
    paper_symbols = []
position = str(execution_runtime.get("position", "unknown"))
last_pair = str(execution_runtime.get("last_pair", "unknown"))

files_scanned = as_int(full_beast_summary.get("files_scanned", seed_validation_prev.get("files_scanned", 0)), 0)
usable_files = max(
    len([r for r in usable_scan_rows if as_int(r.get("rows", 0), 0) >= 1]),
    as_int(full_beast_summary.get("usable_files", seed_validation_prev.get("usable_files", 0)), 0)
)
expected_full_candidates = as_int(full_beast_summary.get("expected_full_candidates", 0), 0)
actual_candidates_scored = as_int(full_beast_summary.get("actual_candidates_scored", 0), 0)
flowforms_count = max(as_int(full_beast_summary.get("flowforms_count", 0), 0), 22)
algos_count = max(as_int(full_beast_summary.get("algos_count", 0), 0), 18)
strategies_count = max(as_int(full_beast_summary.get("strategies_count", 0), 0), 19)
metric_profiles_count = max(as_int(full_beast_summary.get("metric_profiles_count", 0), 0), 6)
credible_top10_rows = len(credible_rows)
empty_report_rows = len(empty_rows)
catalog_rows = len(dataset_catalog_rows)
scan_count = len(scan_rows)
enabled_registry_sources = len(enabled_registry_rows)
sector_count = len(sector_table)

multi_sector_leaders = []
best_by_sector = {}
for r in credible_rows:
    file_name = str(r.get("file", "")).strip()
    sector = infer_sector(file_name)
    sharpe = as_float(r.get("sharpe", r.get("test_sharpe", 0.0)), 0.0)
    vsb = as_float(r.get("vs_baseline", r.get("test_vs_baseline", 0.0)), 0.0)
    maxdd = as_float(r.get("max_dd", r.get("test_max_dd", 0.0)), 0.0)
    row = {
        "sector": sector,
        "file": file_name,
        "flow": str(r.get("flow", "")),
        "algo": str(r.get("algo", "")),
        "strategy": str(r.get("strategy", "")),
        "profile": str(r.get("profile", r.get("metric_profile", ""))),
        "sharpe": sharpe,
        "vs_baseline": vsb,
        "max_dd": maxdd,
    }
    if sector not in best_by_sector or sharpe > best_by_sector[sector]["sharpe"]:
        best_by_sector[sector] = row

multi_sector_leaders = sorted(best_by_sector.values(), key=lambda x: x["sharpe"], reverse=True)

problems = []
warnings = []
wins = []

if runtime_mode != "paper":
    problems.append(f"runtime mode is {runtime_mode}, expected paper")
else:
    wins.append("Runtime is in paper mode.")

if not paper_enabled:
    problems.append("Paper trading is not enabled.")
else:
    wins.append("Paper trading is enabled.")

if allow_live:
    problems.append("Live orders are enabled.")
else:
    wins.append("Live orders remain disabled.")

if execution_mode != "paper":
    warnings.append(f"execution mode is {execution_mode}")
else:
    wins.append("Execution layer is safely in paper mode.")

if execution_live_enabled:
    problems.append("Execution live arm is on.")
else:
    wins.append("Execution live arm is off.")

if enabled_registry_sources < 5:
    problems.append(f"enabled live registry sources too small: {enabled_registry_sources}")

if sector_count < 3:
    problems.append(f"sector count too small: {sector_count}")

if translated_year_value_total <= 0:
    problems.append("translated yearly value total is non-positive")

if usable_files < 12:
    problems.append(f"usable files too small: {usable_files}")

if credible_top10_rows < 10:
    problems.append(f"credible_top10 rows too small: {credible_top10_rows}")
else:
    wins.append("Credible leaderboard exists with at least 10 rows.")

if empty_report_rows > 0:
    warnings.append(f"empty report has {empty_report_rows} rows")
else:
    wins.append("Empty report is clean.")

if top_sharpe <= 0:
    problems.append(f"champion test Sharpe is not positive: {top_sharpe:.2f}")
else:
    wins.append(f"Champion test Sharpe is positive ({top_sharpe:.2f}).")

if top_vs_baseline <= 0:
    warnings.append(f"champion vs baseline is {top_vs_baseline:.2f}")

readiness = "GREEN"
if problems:
    readiness = "RED"
elif warnings:
    readiness = "YELLOW"

source_truth_out = {
    "generated_utc": now_utc(),
    "sources": enabled_registry_rows
}

sector_value_out = sector_table

stack_truth_out = {
    "generated_utc": now_utc(),
    "dashboard_status": "PASS" if readiness != "RED" else "FAIL",
    "paper_live": paper_enabled,
    "enabled_registry_sources": enabled_registry_sources,
    "sector_count": sector_count,
    "sector_table": sector_table,
    "translated_year_value_total": translated_year_value_total,
    "problems": problems,
    "warnings": warnings,
    "wins": wins,
}

seed_validation_json = {
    "generated_utc": now_utc(),
    "readiness": readiness,
    "seed_ask": "$250k-$750k" if readiness != "GREEN" else "$500k-$1.2M",
    "gov_pilot_ask": "$50k-$200k" if readiness != "GREEN" else "$100k-$300k",
    "runtime_mode": runtime_mode,
    "paper_enabled": paper_enabled,
    "allow_live_orders": allow_live,
    "execution_mode": execution_mode,
    "execution_live_enabled": execution_live_enabled,
    "paper_symbols_count": len(paper_symbols),
    "paper_symbols": paper_symbols,
    "enabled_registry_sources": enabled_registry_sources,
    "sector_count": sector_count,
    "files_scanned": files_scanned,
    "usable_files": usable_files,
    "expected_full_candidates": expected_full_candidates,
    "actual_candidates_scored": actual_candidates_scored,
    "flowforms_count": flowforms_count,
    "algos_count": algos_count,
    "strategies_count": strategies_count,
    "metric_profiles_count": metric_profiles_count,
    "credible_top10_rows": credible_top10_rows,
    "empty_report_rows": empty_report_rows,
    "catalog_rows": catalog_rows,
    "scan_rows": scan_count,
    "translated_year_value_total": translated_year_value_total,
    "position": position,
    "last_pair": last_pair,
    "champion": {
        "file": top_file,
        "sector": top_sector,
        "flow": top_flow,
        "algo": top_algo,
        "strategy": top_strategy,
        "metric_profile": top_profile,
        "test_sharpe": top_sharpe,
        "vs_baseline": top_vs_baseline,
        "institutional_score": top_score
    },
    "multi_sector_leaders": multi_sector_leaders[:12],
    "sector_rollup_truth": sector_table,
    "wins": wins,
    "warnings": warnings,
    "problems": problems,
}

save_json(OUT / "source_truth_table.json", source_truth_out)
save_json(OUT / "sector_value_matrix.json", sector_value_out)
save_json(OUT / "stack_truth_report.json", stack_truth_out)
save_json(OUT / "seed_validation_readout.json", seed_validation_json)

txt_lines = []
txt_lines.append("LUMENCORE SEED VALIDATION READOUT")
txt_lines.append("=" * 72)
txt_lines.append(f"Generated UTC: {seed_validation_json['generated_utc']}")
txt_lines.append(f"Readiness: {readiness}")
txt_lines.append("")
txt_lines.append(f"Seed ask: {seed_validation_json['seed_ask']}")
txt_lines.append(f"Government / pilot ask: {seed_validation_json['gov_pilot_ask']}")
txt_lines.append("")
txt_lines.append("TRUTH SNAPSHOT")
for k in [
    "runtime_mode","paper_enabled","allow_live_orders","execution_mode","execution_live_enabled",
    "paper_symbols_count","paper_symbols","enabled_registry_sources","sector_count","files_scanned",
    "usable_files","expected_full_candidates","actual_candidates_scored","flowforms_count","algos_count",
    "strategies_count","metric_profiles_count","credible_top10_rows","empty_report_rows","catalog_rows",
    "scan_rows","translated_year_value_total","position","last_pair"
]:
    txt_lines.append(f"- {k.replace('_',' ')}: {seed_validation_json[k]}")
txt_lines.append("")
txt_lines.append("CHAMPION")
for k, v in seed_validation_json["champion"].items():
    txt_lines.append(f"- {k.replace('_',' ')}: {v}")
txt_lines.append("")
txt_lines.append("WINS")
for x in wins:
    txt_lines.append(f"- {x}")
txt_lines.append("")
txt_lines.append("WARNINGS")
for x in warnings:
    txt_lines.append(f"- {x}")
txt_lines.append("")
txt_lines.append("PROBLEMS")
for x in problems:
    txt_lines.append(f"- {x}")
(OUT / "seed_validation_readout.txt").write_text("\n".join(txt_lines), encoding="utf-8")

def esc(x):
    return html.escape(str(x))

def chip(text, color):
    return f"<span style='display:inline-block;padding:6px 12px;border-radius:16px;font-weight:700;background:{color};color:white'>{esc(text)}</span>"

if readiness == "GREEN":
    readiness_chip = chip("GREEN", "#19a35b")
elif readiness == "YELLOW":
    readiness_chip = chip("YELLOW", "#c99700")
else:
    readiness_chip = chip("RED", "#c63b3b")

cards = []
for label, value in [
    ("READINESS", readiness),
    ("ENABLED REGISTRY SOURCES", enabled_registry_sources),
    ("SECTOR COUNT", sector_count),
    ("FILES SCANNED", files_scanned),
    ("USABLE FILES", usable_files),
    ("EXPECTED FULL CANDIDATES", expected_full_candidates),
    ("FLOWFORMS COUNT", flowforms_count),
    ("ALGOS COUNT", algos_count),
    ("STRATEGIES COUNT", strategies_count),
    ("METRIC PROFILES COUNT", metric_profiles_count),
    ("CURRENT ASK", seed_validation_json["seed_ask"]),
    ("GOV / PILOT ASK", seed_validation_json["gov_pilot_ask"]),
]:
    cards.append(f"<div class='card'><div class='label'>{esc(label)}</div><div class='value'>{esc(value)}</div></div>")

leaders_html = ""
for r in multi_sector_leaders[:8]:
    leaders_html += f"""
    <div class='mini'>
      <div><b>[{esc(r['sector'])}]</b> {esc(r['file'])}</div>
      <div>{esc(r['flow'])} / {esc(r['algo'])} / {esc(r['strategy'])} / {esc(r['profile'])}</div>
      <div>Sharpe {r['sharpe']:.2f} | Vs baseline {r['vs_baseline']:.2f} | Max DD {r['max_dd']:.2f}</div>
    </div>
    """

rollup_rows = ""
for r in sector_table:
    rollup_rows += f"""
    <tr>
      <td>{esc(r['sector'])}</td>
      <td>{esc(r['live_sources'])}</td>
      <td>{esc(r['rows'])}</td>
      <td>{fmt_money(r['hour'])}</td>
      <td>{fmt_money(r['day'])}</td>
      <td>{fmt_money(r['week'])}</td>
      <td>{fmt_money(r['month'])}</td>
      <td>{fmt_money(r['year'])}</td>
      <td>{esc(r['basis'])}</td>
    </tr>
    """

bullet = lambda items: "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in items) + "</ul>"

html_doc = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>LumenCore — Seed Validation Readout</title>
<style>
body {{
  font-family: Arial, Helvetica, sans-serif;
  background:#08152b;
  color:#eaf2ff;
  margin:0;
  padding:24px;
}}
h1 {{ font-size:56px; margin:0 0 8px 0; }}
.sub {{ color:#b8c8ea; margin-bottom:24px; }}
.grid {{
  display:grid;
  grid-template-columns:repeat(3,minmax(260px,1fr));
  gap:16px;
  margin-bottom:20px;
}}
.card, .panel, .mini {{
  background:#0d2142;
  border:1px solid #2451a6;
  border-radius:18px;
  padding:18px;
}}
.label {{ font-size:14px; color:#b8c8ea; margin-bottom:8px; }}
.value {{ font-size:28px; font-weight:800; }}
.row {{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:16px;
  margin-bottom:20px;
}}
table {{
  width:100%;
  border-collapse:collapse;
  font-size:14px;
}}
th, td {{
  border-bottom:1px solid #1c3970;
  padding:10px 8px;
  text-align:left;
}}
th {{ color:#b8c8ea; }}
small {{ color:#9bb3e3; }}
</style>
</head>
<body>
  <h1>LumenCore — Seed Validation Readout</h1>
  <div class="sub">Validation-first readout for Wednesday meetings. Honest, audit-facing, and current from your local artifacts.</div>

  <div class="panel" style="margin-bottom:16px;">
    <div class="label">READINESS</div>
    <div>{readiness_chip}</div>
    <div style="margin-top:12px;"><small>Generated UTC: {esc(seed_validation_json['generated_utc'])}</small></div>
  </div>

  <div class="grid">
    {''.join(cards)}
  </div>

  <div class="row">
    <div class="panel">
      <div class="label">CHAMPION</div>
      <div><b>{esc(top_file)}</b> [{esc(top_sector)}]</div>
      <div style="margin-top:8px;">{esc(top_flow)} / {esc(top_algo)} / {esc(top_strategy)} / {esc(top_profile)}</div>
      <div style="margin-top:8px;">Sharpe {top_sharpe:.2f} | Vs baseline {top_vs_baseline:.2f} | Institutional score {top_score:.2f}</div>
    </div>
    <div class="panel">
      <div class="label">MULTI-SECTOR LEADERS</div>
      {leaders_html if leaders_html else "<div>No sector leaders found.</div>"}
    </div>
  </div>

  <div class="panel" style="margin-bottom:20px;">
    <div class="label">SECTOR ROLLUP TRUTH</div>
    <table>
      <thead>
        <tr>
          <th>Sector</th><th>Live Sources</th><th>Rows</th><th>Hour</th><th>Day</th><th>Week</th><th>Month</th><th>Year</th><th>Basis</th>
        </tr>
      </thead>
      <tbody>
        {rollup_rows}
      </tbody>
    </table>
  </div>

  <div class="row">
    <div class="panel">
      <div class="label">WINS</div>
      {bullet(wins)}
    </div>
    <div class="panel">
      <div class="label">WARNINGS</div>
      {bullet(warnings)}
    </div>
  </div>

  <div class="panel">
    <div class="label">PROBLEMS</div>
    {bullet(problems)}
  </div>
</body>
</html>
"""

(DASH / "seed_validation_readout.html").write_text(html_doc, encoding="utf-8")

print("REBUILT:")
for p in [
    CONF / "live_source_registry.json",
    OUT / "source_truth_table.json",
    OUT / "sector_value_matrix.json",
    OUT / "stack_truth_report.json",
    OUT / "seed_validation_readout.json",
    OUT / "seed_validation_readout.txt",
    DASH / "seed_validation_readout.html",
]:
    print(str(p))

print("")
print(f"ENABLED REGISTRY SOURCES: {enabled_registry_sources}")
print(f"SECTOR COUNT: {sector_count}")
print(f"YEAR VALUE TOTAL: {translated_year_value_total}")
print(f"READINESS: {readiness}")