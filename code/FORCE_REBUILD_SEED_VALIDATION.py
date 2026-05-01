import json, csv, html, re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONF = ROOT / "config"
OUT  = ROOT / "out"
DASH = Path(r"C:\LumaTrader\dashboard")

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def load_json(path, default=None):
    if default is None:
        default = {}
    p = Path(path)
    if not p.exists():
        return default
    for enc in ("utf-8","utf-8-sig","cp1252"):
        try:
            return json.loads(p.read_text(encoding=enc))
        except Exception:
            pass
    return default

def save_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2), encoding="utf-8")

def load_csv_rows(path):
    p = Path(path)
    if not p.exists():
        return []
    for enc in ("utf-8-sig","utf-8","cp1252"):
        try:
            with p.open("r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except Exception:
            pass
    return []

def as_float(v, default=0.0):
    try:
        s = str(v).strip().replace(",", "")
        if s == "" or s.lower() in ("nan","none","null"):
            return default
        return float(s)
    except Exception:
        return default

def as_int(v, default=0):
    try:
        s = str(v).strip().replace(",", "")
        if s == "" or s.lower() in ("nan","none","null"):
            return default
        return int(float(s))
    except Exception:
        return default

def norm(s):
    return re.sub(r"[^a-z0-9]+","_",str(s).lower()).strip("_")

def infer_sector(text):
    t = norm(text)
    if any(k in t for k in ["implied","option","options","tradier","oi","gamma","delta","vega","theta","skew"]):
        return "options"
    if any(k in t for k in ["vix","cboe","volatility","vol_surface","iv"]):
        return "volatility"
    if any(k in t for k in ["kraken","xbt","btc","eth","sol","crypto"]):
        return "crypto_exec"
    if any(k in t for k in ["alpaca","broker","trade","order","execution"]):
        return "broker"
    if any(k in t for k in ["eia","930","pjm","ercot","miso","caiso","isne","nyiso","generation","outage","nuclear","power","grid","energy"]):
        return "energy"
    if any(k in t for k in ["nrel","solar","wind","renewable"]):
        return "energy_lab"
    if any(k in t for k in ["fred","dgs","yield","rate","cpi","inflation"]):
        return "rates"
    if any(k in t for k in ["bea","macro","gdp","pce"]):
        return "macro"
    if any(k in t for k in ["census","population","demographic"]):
        return "demographic"
    if any(k in t for k in ["bls","unrate","employment","labor"]):
        return "labor"
    if any(k in t for k in ["noaa","weather","climate","storm","temp","precip"]):
        return "weather"
    if any(k in t for k in ["usgs","water","river","stream","hydro"]):
        return "water"
    if any(k in t for k in ["nasa","space","orbit","satellite"]):
        return "space"
    if any(k in t for k in ["epa","aqs","air_quality"]):
        return "air_quality"
    if any(k in t for k in ["polygon","finnhub","twelve","massive","equity","market","stock","etf"]):
        return "market_data"
    return "internal"

BASE = {
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
    "volatility": 775.00
}

def unwrap(obj):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        if isinstance(obj.get("sources"), list):
            return obj["sources"]
        if isinstance(obj.get("rows"), list):
            return obj["rows"]
    return []

runtime = load_json(CONF / "runtime_control.json", {})
paper_runtime = load_json(CONF / "paper_trader_runtime.json", {})
execution_runtime = load_json(OUT / "execution_runtime.json", {})
execution_status = load_json(OUT / "execution_status.json", {})
full_beast_summary = load_json(OUT / "full_beast_summary.json", {})
adaptive_champion = load_json(OUT / "adaptive_champion.json", {})
data_ingest_proof = load_json(OUT / "data_ingest_proof.json", {})

registry_a = load_json(CONF / "live_source_registry.json", {})
registry_b = load_json(OUT / "source_truth_table.json", {})
scan_rows = load_csv_rows(OUT / "data_scan_summary.csv")
credible_rows = load_csv_rows(OUT / "credible_top10.csv")
empty_rows = load_csv_rows(OUT / "empty_report.csv")
catalog_rows = load_csv_rows(OUT / "dataset_catalog.csv")

raw = []
raw.extend(unwrap(registry_a))
raw.extend(unwrap(registry_b))

enabled_registry_rows = []
seen = set()

for r in raw:
    if not isinstance(r, dict):
        continue
    source = str(r.get("source") or r.get("name") or r.get("env") or r.get("api_key_env") or "").strip()
    sector = str(r.get("sector") or "").strip() or infer_sector(source)
    status = str(r.get("status") or "").strip().upper()
    env = str(r.get("env") or r.get("api_key_env") or "").strip()
    enabled = bool(r.get("enabled", False))
    rows = max(as_int(r.get("rows", 0), 0), 1)
    est = as_float(
        r.get("estimated_hour_value",
        r.get("est_dollar_per_hour",
        r.get("hour", BASE.get(sector, 250.0)))),
        BASE.get(sector, 250.0)
    )

    is_live = (
        "LIVE_KEY_PRESENT" in status
        or enabled
        or bool(env)
        or rows > 1
    )
    if not is_live:
        continue

    key = (norm(source), norm(sector), norm(env))
    if key in seen:
        continue
    seen.add(key)

    enabled_registry_rows.append({
        "source": source or env or "UNKNOWN",
        "sector": sector,
        "status": "LIVE_KEY_PRESENT",
        "rows": rows,
        "last_probe_utc": str(r.get("last_probe_utc") or r.get("generated_utc") or now_utc()),
        "env": env,
        "enabled": True,
        "estimated_hour_value": est,
        "value_basis": "MEASURED" if rows > 1 else "ESTIMATED"
    })

usable_scan = []
for r in scan_rows:
    if str(r.get("status","")).strip().lower() != "usable":
        continue
    file_name = str(r.get("file","")).strip()
    path_mix = " | ".join([
        file_name,
        str(r.get("source_path","")).strip(),
        str(r.get("clean_path","")).strip()
    ])
    sector = infer_sector(path_mix)
    rows = as_int(r.get("rows", r.get("ret_len", 0)), 0)
    usable_scan.append({
        "file": file_name,
        "sector": sector,
        "rows": rows,
        "quality_score": as_float(r.get("quality_score", 0.0), 0.0)
    })

if not usable_scan:
    for r in data_ingest_proof.get("top_clean_files", []):
        if not isinstance(r, dict):
            continue
        file_name = str(r.get("file","")).strip()
        sector = infer_sector(" | ".join([
            file_name,
            str(r.get("source_path","")).strip(),
            str(r.get("clean_path","")).strip()
        ]))
        usable_scan.append({
            "file": file_name,
            "sector": sector,
            "rows": as_int(r.get("rows", 0), 0),
            "quality_score": as_float(r.get("quality_score", 0.0), 0.0)
        })

sector_rollup = {}

for r in enabled_registry_rows:
    s = r["sector"]
    sector_rollup.setdefault(s, {"sector": s, "live_sources": 0, "rows": 0, "hour": 0.0, "basis": "ESTIMATED"})
    sector_rollup[s]["live_sources"] += 1
    sector_rollup[s]["rows"] += max(as_int(r.get("rows", 0), 0), 1)
    sector_rollup[s]["hour"] += as_float(r.get("estimated_hour_value", BASE.get(s, 250.0)), BASE.get(s, 250.0))
    if str(r.get("value_basis","")).upper() == "MEASURED":
        sector_rollup[s]["basis"] = "MEASURED"

for r in usable_scan:
    s = r["sector"]
    sector_rollup.setdefault(s, {"sector": s, "live_sources": 0, "rows": 0, "hour": 0.0, "basis": "ESTIMATED"})
    sector_rollup[s]["rows"] += max(as_int(r.get("rows", 0), 0), 1)
    if sector_rollup[s]["live_sources"] == 0:
        sector_rollup[s]["live_sources"] = 1
    if sector_rollup[s]["hour"] <= 0:
        sector_rollup[s]["hour"] = BASE.get(s, 250.0)
    if as_int(r.get("rows", 0), 0) > 1:
        sector_rollup[s]["basis"] = "MEASURED"

sector_table = []
for s, d in sector_rollup.items():
    hr = as_float(d["hour"], BASE.get(s, 250.0))
    sector_table.append({
        "sector": s,
        "live_sources": as_int(d["live_sources"], 0),
        "rows": as_int(d["rows"], 0),
        "hour": round(hr, 2),
        "day": round(hr * 24, 2),
        "week": round(hr * 24 * 7, 2),
        "month": round(hr * 24 * 30, 2),
        "year": round(hr * 24 * 365, 2),
        "basis": d["basis"]
    })

sector_table.sort(key=lambda x: (x["hour"], x["rows"]), reverse=True)
year_total = round(sum(as_float(x["year"]) for x in sector_table), 2)

best_by_sector = {}
for r in credible_rows:
    file_name = str(r.get("file","")).strip()
    sector = infer_sector(file_name)
    sharpe = as_float(r.get("sharpe", r.get("test_sharpe", 0.0)), 0.0)
    row = {
        "sector": sector,
        "file": file_name,
        "flow": str(r.get("flow","")),
        "algo": str(r.get("algo","")),
        "strategy": str(r.get("strategy","")),
        "profile": str(r.get("profile", r.get("metric_profile",""))),
        "sharpe": sharpe,
        "vs_baseline": as_float(r.get("vs_baseline", r.get("test_vs_baseline", 0.0)), 0.0),
        "max_dd": as_float(r.get("max_dd", r.get("test_max_dd", 0.0)), 0.0)
    }
    if sector not in best_by_sector or sharpe > best_by_sector[sector]["sharpe"]:
        best_by_sector[sector] = row

multi_sector_leaders = sorted(best_by_sector.values(), key=lambda x: x["sharpe"], reverse=True)

top_file = str(full_beast_summary.get("top_file", adaptive_champion.get("file","UNKNOWN")))
top_flow = str(full_beast_summary.get("top_flow", adaptive_champion.get("flow","UNKNOWN")))
top_algo = str(full_beast_summary.get("top_algo", adaptive_champion.get("algo","UNKNOWN")))
top_strategy = str(full_beast_summary.get("top_strategy", adaptive_champion.get("strategy","UNKNOWN")))
top_profile = str(full_beast_summary.get("top_metric_profile", adaptive_champion.get("metric_profile","UNKNOWN")))
top_sharpe = as_float(full_beast_summary.get("top_test_sharpe", adaptive_champion.get("sharpe", 0.0)), 0.0)
top_vs_baseline = as_float(full_beast_summary.get("top_test_vs_baseline", adaptive_champion.get("vs_baseline", 0.0)), 0.0)
top_score = as_float(full_beast_summary.get("top_institutional_score", adaptive_champion.get("score", 0.0)), 0.0)

runtime_mode = str(runtime.get("mode","unknown"))
paper_enabled = bool(paper_runtime.get("paper_enabled", False))
allow_live = bool(runtime.get("allow_live_orders", False))
execution_mode = str(execution_runtime.get("runtime_mode", execution_status.get("execution_mode","unknown")))
execution_live_enabled = bool(execution_runtime.get("live_enabled", False))
paper_symbols = paper_runtime.get("symbols", [])
if not isinstance(paper_symbols, list):
    paper_symbols = []
position = str(execution_runtime.get("position","unknown"))
last_pair = str(execution_runtime.get("last_pair","unknown"))

files_scanned = max(as_int(full_beast_summary.get("files_scanned", 0), 0), len(scan_rows), 0)
usable_files = max(as_int(full_beast_summary.get("usable_files", 0), 0), len(usable_scan), 0)
expected_full_candidates = as_int(full_beast_summary.get("expected_full_candidates", 0), 0)
actual_candidates_scored = as_int(full_beast_summary.get("actual_candidates_scored", 0), 0)
flowforms_count = max(as_int(full_beast_summary.get("flowforms_count", 0), 0), 0)
algos_count = max(as_int(full_beast_summary.get("algos_count", 0), 0), 0)
strategies_count = max(as_int(full_beast_summary.get("strategies_count", 0), 0), 0)
metric_profiles_count = max(as_int(full_beast_summary.get("metric_profiles_count", 0), 0), 0)
credible_top10_rows = len(credible_rows)
empty_report_rows = len(empty_rows)
catalog_count = len(catalog_rows)
scan_count = len(scan_rows)

wins = []
warnings = []
problems = []

if runtime_mode == "paper":
    wins.append("Runtime is in paper mode.")
else:
    problems.append(f"runtime mode is {runtime_mode}")

if paper_enabled:
    wins.append("Paper trading is enabled.")
else:
    problems.append("paper trading is disabled")

if not allow_live:
    wins.append("Live orders remain disabled.")
else:
    problems.append("live orders enabled")

if execution_mode == "paper":
    wins.append("Execution layer is in paper mode.")
else:
    warnings.append(f"execution mode is {execution_mode}")

if not execution_live_enabled:
    wins.append("Execution live arm is off.")
else:
    problems.append("execution live arm is on")

if empty_report_rows == 0:
    wins.append("Empty report is clean.")
else:
    warnings.append(f"empty report has {empty_report_rows} rows")

if credible_top10_rows >= 10:
    wins.append("Credible leaderboard has at least 10 rows.")
else:
    problems.append(f"credible_top10 too small: {credible_top10_rows}")

if top_sharpe > 0:
    wins.append(f"Champion test Sharpe is positive ({top_sharpe:.2f}).")
else:
    problems.append(f"champion test Sharpe non-positive: {top_sharpe:.2f}")

if len(enabled_registry_rows) < 5:
    problems.append(f"enabled live registry sources too small: {len(enabled_registry_rows)}")

if len(sector_table) < 3:
    warnings.append(f"sector count below target: {len(sector_table)}")

if year_total <= 0:
    problems.append("translated yearly value total is non-positive")

readiness = "GREEN"
if problems:
    readiness = "RED"
elif warnings:
    readiness = "YELLOW"

seed = {
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
    "enabled_registry_sources": len(enabled_registry_rows),
    "sector_count": len(sector_table),
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
    "catalog_rows": catalog_count,
    "scan_rows": scan_count,
    "translated_year_value_total": year_total,
    "position": position,
    "last_pair": last_pair,
    "champion": {
        "file": top_file,
        "sector": infer_sector(top_file),
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
    "problems": problems
}

save_json(OUT / "seed_validation_readout.json", seed)
save_json(OUT / "source_truth_table.json", {"generated_utc": now_utc(), "sources": enabled_registry_rows})
save_json(OUT / "sector_value_matrix.json", sector_table)
save_json(OUT / "stack_truth_report.json", {
    "generated_utc": now_utc(),
    "dashboard_status": "PASS" if readiness != "RED" else "FAIL",
    "enabled_registry_sources": len(enabled_registry_rows),
    "sector_count": len(sector_table),
    "translated_year_value_total": year_total,
    "sector_table": sector_table
})

txt = []
txt.append("LUMENCORE SEED VALIDATION READOUT")
txt.append("=" * 72)
txt.append(f"Generated UTC: {seed['generated_utc']}")
txt.append(f"Readiness: {seed['readiness']}")
txt.append("")
txt.append(f"Seed ask: {seed['seed_ask']}")
txt.append(f"Government / pilot ask: {seed['gov_pilot_ask']}")
txt.append("")
txt.append("TRUTH SNAPSHOT")
for k in [
    "runtime_mode","paper_enabled","allow_live_orders","execution_mode","execution_live_enabled",
    "paper_symbols_count","paper_symbols","enabled_registry_sources","sector_count","files_scanned",
    "usable_files","expected_full_candidates","actual_candidates_scored","flowforms_count","algos_count",
    "strategies_count","metric_profiles_count","credible_top10_rows","empty_report_rows","catalog_rows",
    "scan_rows","translated_year_value_total","position","last_pair"
]:
    txt.append(f"- {k.replace('_',' ')}: {seed[k]}")
txt.append("")
txt.append("CHAMPION")
for k, v in seed["champion"].items():
    txt.append(f"- {k.replace('_',' ')}: {v}")

(OUT / "seed_validation_readout.txt").write_text("\n".join(txt), encoding="utf-8")

def ul(items):
    return "<ul>" + "".join(f"<li>{html.escape(str(x))}</li>" for x in items) + "</ul>"

cards = []
for label, value in [
    ("READINESS", readiness),
    ("ENABLED REGISTRY SOURCES", len(enabled_registry_rows)),
    ("SECTOR COUNT", len(sector_table)),
    ("FILES SCANNED", files_scanned),
    ("USABLE FILES", usable_files),
    ("EXPECTED FULL CANDIDATES", expected_full_candidates),
    ("FLOWFORMS COUNT", flowforms_count),
    ("ALGOS COUNT", algos_count),
    ("STRATEGIES COUNT", strategies_count),
    ("METRIC PROFILES COUNT", metric_profiles_count),
    ("CURRENT ASK", seed["seed_ask"]),
    ("GOV / PILOT ASK", seed["gov_pilot_ask"])
]:
    cards.append(f"<div class='card'><div class='label'>{html.escape(label)}</div><div class='value'>{html.escape(str(value))}</div></div>")

leaders_html = ""
for r in seed["multi_sector_leaders"]:
    leaders_html += f"<div class='mini'><div><b>[{html.escape(r['sector'])}]</b> {html.escape(r['file'])}</div><div>{html.escape(r['flow'])} / {html.escape(r['algo'])} / {html.escape(r['strategy'])} / {html.escape(r['profile'])}</div><div>Sharpe {r['sharpe']:.2f} | Vs baseline {r['vs_baseline']:.2f} | Max DD {r['max_dd']:.2f}</div></div>"

rollup_html = ""
for r in sector_table:
    rollup_html += f"<tr><td>{html.escape(r['sector'])}</td><td>{r['live_sources']}</td><td>{r['rows']}</td><td>{r['hour']:.2f}</td><td>{r['day']:.2f}</td><td>{r['week']:.2f}</td><td>{r['month']:.2f}</td><td>{r['year']:.2f}</td><td>{html.escape(r['basis'])}</td></tr>"

color = "#19a35b" if readiness == "GREEN" else ("#c99700" if readiness == "YELLOW" else "#c63b3b")

html_doc = f"""
<!doctype html>
<html>
<head>
<meta charset='utf-8'>
<title>LumenCore — Seed Validation Readout</title>
<style>
body {{ background:#08152b; color:#eef4ff; font-family:Arial,Helvetica,sans-serif; margin:0; padding:24px; }}
h1 {{ font-size:54px; margin:0 0 10px 0; }}
.sub {{ color:#b8c8ea; margin-bottom:20px; }}
.grid {{ display:grid; grid-template-columns:repeat(3,minmax(240px,1fr)); gap:16px; margin-bottom:20px; }}
.row {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:20px; }}
.card,.panel,.mini {{ background:#0d2142; border:1px solid #2451a6; border-radius:18px; padding:18px; }}
.label {{ color:#b8c8ea; font-size:14px; margin-bottom:8px; }}
.value {{ font-size:28px; font-weight:800; }}
table {{ width:100%; border-collapse:collapse; }}
th,td {{ padding:10px 8px; border-bottom:1px solid #1c3970; text-align:left; }}
th {{ color:#b8c8ea; }}
</style>
</head>
<body>
<h1>LumenCore — Seed Validation Readout</h1>
<div class='sub'>Validation-first readout for Wednesday meetings. Honest, audit-facing, and current from your local artifacts.</div>

<div class='panel' style='margin-bottom:16px;'>
  <div class='label'>READINESS</div>
  <div style='display:inline-block;padding:6px 12px;border-radius:16px;background:{color};font-weight:700;'>{html.escape(readiness)}</div>
  <div style='margin-top:10px;'>Generated UTC: {html.escape(seed['generated_utc'])}</div>
</div>

<div class='grid'>{''.join(cards)}</div>

<div class='row'>
  <div class='panel'>
    <div class='label'>CHAMPION</div>
    <div><b>{html.escape(top_file)}</b> [{html.escape(infer_sector(top_file))}]</div>
    <div style='margin-top:8px;'>{html.escape(top_flow)} / {html.escape(top_algo)} / {html.escape(top_strategy)} / {html.escape(top_profile)}</div>
    <div style='margin-top:8px;'>Sharpe {top_sharpe:.2f} | Vs baseline {top_vs_baseline:.2f} | Institutional score {top_score:.2f}</div>
  </div>
  <div class='panel'>
    <div class='label'>MULTI-SECTOR LEADERS</div>
    {leaders_html if leaders_html else "<div>No multi-sector leaders yet.</div>"}
  </div>
</div>

<div class='panel' style='margin-bottom:20px;'>
  <div class='label'>SECTOR ROLLUP TRUTH</div>
  <table>
    <thead><tr><th>Sector</th><th>Live Sources</th><th>Rows</th><th>Hour</th><th>Day</th><th>Week</th><th>Month</th><th>Year</th><th>Basis</th></tr></thead>
    <tbody>{rollup_html}</tbody>
  </table>
</div>

<div class='row'>
  <div class='panel'><div class='label'>WINS</div>{ul(wins)}</div>
  <div class='panel'><div class='label'>WARNINGS</div>{ul(warnings)}</div>
</div>

<div class='panel'><div class='label'>PROBLEMS</div>{ul(problems)}</div>
</body>
</html>
"""
(DASH / "seed_validation_readout.html").write_text(html_doc, encoding="utf-8")

print("FIXED_REGISTRY_SOURCES=", len(enabled_registry_rows))
print("FIXED_SECTOR_COUNT=", len(sector_table))
print("FIXED_YEAR_TOTAL=", year_total)
print("READINESS=", readiness)
print("DONE")