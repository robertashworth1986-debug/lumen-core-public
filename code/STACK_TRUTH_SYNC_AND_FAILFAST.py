import csv, json, math, html
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
CONF = ROOT / "config"
DASH = Path(r"C:\LumaTrader\dashboard")

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        if Path(path).exists():
            return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def load_csv_rows(path):
    rows = []
    p = Path(path)
    if not p.exists():
        return rows
    try:
        with p.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                rows.append({k: v for k, v in row.items()})
    except Exception:
        return []
    return rows

def as_float(v, default=0.0):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default

def fmt_money(v):
    try:
        return "${:,.2f}".format(float(v))
    except Exception:
        return "$0.00"

def fmt_num(v):
    try:
        return "{:,.0f}".format(float(v))
    except Exception:
        return "0"

def esc(s):
    return html.escape(str(s))

def status_chip(text, good=True):
    cls = "good" if good else "bad"
    return f'<span class="chip {cls}">{esc(text)}</span>'

runtime = load_json(CONF / "runtime_control.json", {})
paper_runtime = load_json(CONF / "paper_trader_runtime.json", {})
infra_runtime = load_json(CONF / "infra_live_runtime.json", {})
live_sources = load_json(CONF / "live_sources.json", {})
live_registry = load_json(CONF / "live_source_registry.json", {})
truth_report = load_json(OUT / "stack_truth_report.json", {})

full_beast_summary = load_json(OUT / "full_beast_summary.json", {})
full_beast_registry = load_json(OUT / "full_beast_registry.json", {})
execution_runtime = load_json(OUT / "execution_runtime.json", {})
execution_status = load_json(OUT / "execution_status.json", {})
adaptive_champion = load_json(OUT / "adaptive_champion.json", {})
data_ingest_proof = load_json(OUT / "data_ingest_proof.json", {})

auto_dataset_rows = load_csv_rows(OUT / "auto_dataset_results.csv")
empty_rows = load_csv_rows(OUT / "empty_report.csv")
catalog_rows = load_csv_rows(OUT / "dataset_catalog.csv")
scan_rows = load_csv_rows(OUT / "data_scan_summary.csv")
leader_rows = load_csv_rows(OUT / "credible_top10.csv")
inst_rows = load_json(OUT / "sector_value_matrix.json", {})  # harmless if absent / wrong type

registry_rows = live_registry.get("sources", [])
enabled_registry_rows = [r for r in registry_rows if str(r.get("status","")).upper() == "LIVE_KEY_PRESENT"]

full_flowforms = full_beast_summary.get("flowforms_count", len(full_beast_registry.get("flowforms", [])))
full_algos = full_beast_summary.get("algos_count", len(full_beast_registry.get("algorithms", [])))
full_strategies = full_beast_summary.get("strategies_count", len(full_beast_registry.get("strategies", [])))
full_profiles = full_beast_summary.get("metric_profiles_count", len(full_beast_registry.get("metric_profiles", [])))
usable_files = full_beast_summary.get("usable_files", 0)
files_scanned = full_beast_summary.get("files_scanned", 0)
expected_candidates = full_beast_summary.get("expected_full_candidates", 0)
actual_candidates = full_beast_summary.get("actual_candidates_scored", 0)
top_file = full_beast_summary.get("top_file", adaptive_champion.get("file", "UNKNOWN"))
top_flow = full_beast_summary.get("top_flow", adaptive_champion.get("flow", "UNKNOWN"))
top_algo = full_beast_summary.get("top_algo", adaptive_champion.get("algo", "UNKNOWN"))
top_strategy = full_beast_summary.get("top_strategy", adaptive_champion.get("strategy", "UNKNOWN"))
top_profile = full_beast_summary.get("top_metric_profile", adaptive_champion.get("metric_profile", "UNKNOWN"))
top_sharpe = as_float(full_beast_summary.get("top_test_sharpe", adaptive_champion.get("sharpe", 0.0)))
top_vs_baseline = as_float(full_beast_summary.get("top_test_vs_baseline", adaptive_champion.get("vs_baseline", 0.0)))
top_score = full_beast_summary.get("top_institutional_score", adaptive_champion.get("score", 0.0))

paper_enabled = bool(paper_runtime.get("paper_enabled", False))
paper_symbols = paper_runtime.get("symbols", [])
runtime_mode = str(runtime.get("mode", "unknown"))
allow_live = bool(runtime.get("allow_live_orders", False))
execution_mode = str(execution_runtime.get("runtime_mode", execution_status.get("execution_mode", "unknown")))
live_enabled = bool(execution_runtime.get("live_enabled", False))
last_mode = str(execution_runtime.get("last_mode", "unknown"))
last_pair = str(execution_runtime.get("last_pair", "unknown"))
position = str(execution_runtime.get("position", "unknown"))

quality_files = data_ingest_proof.get("top_clean_files", [])
quality_rows = len(quality_files)
catalog_count = len(catalog_rows)
scan_count = len(scan_rows)
leader_count = len(leader_rows)
empty_count = len(empty_rows)

problems = []
warnings = []

if runtime_mode != "paper":
    problems.append(f"runtime_control.mode is {runtime_mode}, expected paper")
if not paper_enabled:
    problems.append("paper_trader_runtime.paper_enabled is false")
if allow_live:
    problems.append("runtime_control.allow_live_orders is true")
if execution_mode not in ("paper", "shadow"):
    warnings.append(f"execution_runtime.runtime_mode={execution_mode}")
if live_enabled:
    problems.append("execution_runtime.live_enabled is true")
if full_flowforms < 20:
    problems.append(f"flowforms_count too small: {full_flowforms}")
if full_algos < 10:
    problems.append(f"algos_count too small: {full_algos}")
if full_strategies < 10:
    problems.append(f"strategies_count too small: {full_strategies}")
if full_profiles < 6:
    problems.append(f"metric_profiles_count too small: {full_profiles}")
if files_scanned < 25:
    warnings.append(f"files_scanned still small: {files_scanned}")
if usable_files < 10:
    problems.append(f"usable_files too small: {usable_files}")
if actual_candidates < 100000:
    warnings.append(f"actual_candidates_scored still small: {actual_candidates}")
if top_sharpe <= 0:
    problems.append(f"top_test_sharpe not positive: {top_sharpe}")
if empty_count > 0:
    warnings.append(f"empty_report has {empty_count} rows")
if catalog_count == 0:
    problems.append("dataset_catalog.csv is empty or missing")
if scan_count == 0:
    problems.append("data_scan_summary.csv is empty or missing")
if leader_count == 0:
    problems.append("credible_top10.csv is empty or missing")
if len(enabled_registry_rows) < 5:
    problems.append(f"enabled live registry rows too small: {len(enabled_registry_rows)}")

dashboard_status = "PASS" if not problems else "FAIL"

sector_rollup = {}
for r in enabled_registry_rows:
    sector = str(r.get("sector", "unknown"))
    sector_rollup.setdefault(sector, {"live_sources": 0, "rows": 0})
    sector_rollup[sector]["live_sources"] += 1
    sector_rollup[sector]["rows"] += int(r.get("rows", 0) or 0)

baseline_rates = infra_runtime.get("baseline_loss_rates", {})
sector_table = []

for sector, d in sector_rollup.items():
    est_hour = baseline_rates.get(sector, 250.0) * max(1, int(d.get("live_sources", 0)))
    sector_table.append({
        "sector": sector,
        "live_sources": int(d.get("live_sources", 0)),
        "rows": int(d.get("rows", 0)),
        "hour": round(est_hour, 2),
        "day": round(est_hour * 24, 2),
        "week": round(est_hour * 24 * 7, 2),
        "month": round(est_hour * 24 * 30, 2),
        "year": round(est_hour * 24 * 365, 2),
        "basis": "MEASURED" if int(d.get("rows", 0)) > 1 else "ESTIMATED"
    })

sector_table = sorted(sector_table, key=lambda x: x["hour"], reverse=True)

out = {
    "generated_utc": now_utc().format(),
    "dashboard_status": dashboard_status,
    "problems": problems,
    "paper_live": False,
    "enabled_registry_sources": len(enabled_registry_rows),
    "sector_count": len(sector_table),
    "sector_table": sector_table
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)

print("WROTE:", OUT)
print("STATUS:", dashboard_status)
print("SECTORS:", len(sector_table))