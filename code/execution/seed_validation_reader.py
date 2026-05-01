import csv, json, html
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT  = ROOT / "out"
CONF = ROOT / "config"
DASH = Path(r"C:\LumaTrader\dashboard")

TXT_PATH  = OUT / "seed_validation_readout.txt"
JSON_PATH = OUT / "seed_validation_readout.json"
HTML_PATH = DASH / "seed_validation_readout.html"

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def load_json(path, default=None):
    if default is None:
        default = {}
    p = Path(path)
    if not p.exists():
        return default
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return json.loads(p.read_text(encoding=enc))
        except Exception:
            pass
    return default

def load_csv_rows(path):
    p = Path(path)
    if not p.exists():
        return []
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            with p.open("r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except Exception:
            pass
    return []

def as_float(v, default=0.0):
    try:
        if v is None:
            return default
        s = str(v).strip()
        if s == "":
            return default
        return float(s)
    except Exception:
        return default

def as_int(v, default=0):
    try:
        if v is None:
            return default
        s = str(v).strip()
        if s == "":
            return default
        return int(float(s))
    except Exception:
        return default

def esc(x):
    return html.escape(str(x))

def money(v):
    return "${:,.2f}".format(as_float(v, 0.0))

def fmt(v):
    try:
        return "{:,.2f}".format(float(v))
    except Exception:
        return str(v)

def resolve_rows(blob):
    if isinstance(blob, list):
        return blob
    if isinstance(blob, dict):
        if isinstance(blob.get("sources"), list):
            return blob.get("sources", [])
        if isinstance(blob.get("rows"), list):
            return blob.get("rows", [])
    return []

def truthy_enabled(v):
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s in ("1", "true", "yes", "on")

def norm_status(v):
    return str(v or "").strip().upper()

def pick_hour_value(row):
    for key in (
        "estimated_hour_value",
        "est_dollar_per_hour",
        "est_hour",
        "hour_value",
        "estimated_value_per_hour",
    ):
        if key in row:
            return as_float(row.get(key), 0.0)
    return 0.0

def pick_basis(row):
    for key in ("value_basis", "basis", "dollar_basis", "evidence_basis"):
        if key in row and str(row.get(key)).strip():
            return str(row.get(key)).strip().upper()
    rows = as_int(row.get("rows", 0), 0)
    return "MEASURED" if rows > 1 else "ESTIMATED"

def merge_registry_rows(*sources):
    merged = {}
    for src in sources:
        for row in resolve_rows(src):
            if not isinstance(row, dict):
                continue
            source_name = str(row.get("source", "")).strip()
            env_name    = str(row.get("env", "")).strip()
            sector      = str(row.get("sector", "")).strip()
            key = (source_name, env_name, sector)
            prev = merged.get(key, {})
            new_row = dict(prev)
            new_row.update(row)
            merged[key] = new_row
    return list(merged.values())

runtime_control    = load_json(CONF / "runtime_control.json", {})
paper_runtime      = load_json(CONF / "paper_trader_runtime.json", {})
infra_runtime      = load_json(CONF / "infra_live_runtime.json", {})
live_sources       = load_json(CONF / "live_sources.json", {})
live_registry      = load_json(CONF / "live_source_registry.json", {})
source_truth       = load_json(OUT / "source_truth_table.json", {})
stack_truth        = load_json(OUT / "stack_truth_report.json", {})
full_beast_summary = load_json(OUT / "full_beast_summary.json", {})
adaptive_champion  = load_json(OUT / "adaptive_champion.json", {})
execution_runtime  = load_json(OUT / "execution_runtime.json", {})
execution_status   = load_json(OUT / "execution_status.json", {})
data_ingest_proof  = load_json(OUT / "data_ingest_proof.json", {})

credible_top10_rows = load_csv_rows(OUT / "credible_top10.csv")
dataset_catalog_rows = load_csv_rows(OUT / "dataset_catalog.csv")
data_scan_rows = load_csv_rows(OUT / "data_scan_summary.csv")
empty_rows = load_csv_rows(OUT / "empty_report.csv")
auto_dataset_rows = load_csv_rows(OUT / "auto_dataset_results.csv")

raw_registry_rows = merge_registry_rows(live_registry, source_truth)

enabled_live_rows = []
for row in raw_registry_rows:
    status = norm_status(row.get("status"))
    enabled = truthy_enabled(row.get("enabled", True))
    if status == "LIVE_KEY_PRESENT" and enabled:
        enabled_live_rows.append(row)

sector_rollup = {}
for row in enabled_live_rows:
    sector = str(row.get("sector", "unknown")).strip() or "unknown"
    rows = as_int(row.get("rows", 0), 0)
    hour_val = pick_hour_value(row)
    basis = pick_basis(row)

    if sector not in sector_rollup:
        sector_rollup[sector] = {
            "sector": sector,
            "live_sources": 0,
            "rows": 0,
            "hour": 0.0,
            "basis": "MEASURED"
        }

    sector_rollup[sector]["live_sources"] += 1
    sector_rollup[sector]["rows"] += rows
    sector_rollup[sector]["hour"] += hour_val

    if basis != "MEASURED":
        sector_rollup[sector]["basis"] = "ESTIMATED"

sector_table = []
for sector, d in sorted(sector_rollup.items(), key=lambda kv: kv[1]["hour"], reverse=True):
    hr = round(as_float(d["hour"], 0.0), 2)
    sector_table.append({
        "sector": sector,
        "live_sources": as_int(d["live_sources"], 0),
        "rows": as_int(d["rows"], 0),
        "hour": hr,
        "day": round(hr * 24, 2),
        "week": round(hr * 24 * 7, 2),
        "month": round(hr * 24 * 30, 2),
        "year": round(hr * 24 * 365, 2),
        "basis": d["basis"]
    })

translated_year_total = round(sum(r["year"] for r in sector_table), 2)

files_scanned = max(
    as_int(full_beast_summary.get("files_scanned", 0), 0),
    len({str(r.get("file", "")).strip() for r in dataset_catalog_rows if str(r.get("file", "")).strip()}),
    len({str(r.get("file", "")).strip() for r in auto_dataset_rows if str(r.get("file", "")).strip()})
)

usable_files = max(
    as_int(full_beast_summary.get("usable_files", 0), 0),
    len([r for r in data_ingest_proof.get("top_clean_files", []) if r]),
    len([r for r in auto_dataset_rows if str(r.get("file", "")).strip()])
)

flowforms_count = max(as_int(full_beast_summary.get("flowforms_count", 0), 0), 0)
algos_count = max(as_int(full_beast_summary.get("algos_count", 0), 0), 0)
strategies_count = max(as_int(full_beast_summary.get("strategies_count", 0), 0), 0)
metric_profiles_count = max(as_int(full_beast_summary.get("metric_profiles_count", 0), 0), 0)
expected_candidates = max(as_int(full_beast_summary.get("expected_full_candidates", 0), 0), 0)
actual_candidates = max(as_int(full_beast_summary.get("actual_candidates_scored", 0), 0), 0)

paper_symbols = paper_runtime.get("symbols", [])
paper_symbols_count = len(paper_symbols)
paper_enabled = truthy_enabled(paper_runtime.get("paper_enabled", False))
runtime_mode = str(runtime_control.get("mode", "unknown"))
allow_live_orders = truthy_enabled(runtime_control.get("allow_live_orders", False))
execution_mode = str(execution_runtime.get("runtime_mode", execution_status.get("execution_mode", "unknown")))
execution_live_enabled = truthy_enabled(execution_runtime.get("live_enabled", False))
position = str(execution_runtime.get("position", "unknown"))
last_pair = str(execution_runtime.get("last_pair", execution_runtime.get("symbol", "unknown")))

enabled_registry_sources = len(enabled_live_rows)
sector_count = len(sector_table)
credible_top10_rows_count = len(credible_top10_rows)
empty_report_rows = len(empty_rows)
catalog_rows = len(dataset_catalog_rows)
scan_rows = len(data_scan_rows)

champ_file = full_beast_summary.get("top_file", adaptive_champion.get("file", "UNKNOWN"))
champ_flow = full_beast_summary.get("top_flow", adaptive_champion.get("flow", "UNKNOWN"))
champ_algo = full_beast_summary.get("top_algo", adaptive_champion.get("algo", "UNKNOWN"))
champ_strategy = full_beast_summary.get("top_strategy", adaptive_champion.get("strategy", "UNKNOWN"))
champ_profile = full_beast_summary.get(
    "top_metric_profile",
    adaptive_champion.get("metric_profile", adaptive_champion.get("profile", "UNKNOWN"))
)
champ_sharpe = as_float(full_beast_summary.get("top_test_sharpe", adaptive_champion.get("sharpe", 0.0)), 0.0)
champ_vs_baseline = as_float(full_beast_summary.get("top_test_vs_baseline", adaptive_champion.get("vs_baseline", 0.0)), 0.0)
champ_score = full_beast_summary.get("top_institutional_score", adaptive_champion.get("score", 0.0))

wins = []
warnings = []
problems = []

if runtime_mode == "paper":
    wins.append("Runtime is in paper mode.")
else:
    problems.append(f"runtime mode is {runtime_mode}, expected paper")

if paper_enabled:
    wins.append("Paper trading is enabled.")
else:
    problems.append("paper trading is not enabled")

if not allow_live_orders:
    wins.append("Live orders remain disabled.")
else:
    problems.append("allow_live_orders is true")

if execution_mode in ("paper", "shadow"):
    wins.append(f"Execution layer is in {execution_mode} mode.")
else:
    warnings.append(f"execution mode is {execution_mode}")

if not execution_live_enabled:
    wins.append("Execution live arm is off.")
else:
    warnings.append("execution live is enabled")

if empty_report_rows == 0:
    wins.append("Empty report is clean.")
else:
    warnings.append(f"empty report has {empty_report_rows} rows")

if credible_top10_rows_count >= 10:
    wins.append("Credible leaderboard exists with at least 10 rows.")
else:
    problems.append("credible leaderboard is too small")

if champ_sharpe > 0:
    wins.append(f"Champion test Sharpe is positive ({fmt(champ_sharpe)}).")
else:
    problems.append("champion test Sharpe is non-positive")

if champ_vs_baseline > 0:
    wins.append(f"Champion beats baseline by {fmt(champ_vs_baseline)}.")
else:
    warnings.append(f"champion vs baseline is {fmt(champ_vs_baseline)}")

if enabled_registry_sources <= 0:
    problems.append("enabled live registry sources are zero")
elif enabled_registry_sources < 5:
    warnings.append(f"enabled live registry sources still small: {enabled_registry_sources}")
else:
    wins.append(f"Enabled live registry sources: {enabled_registry_sources}")

if sector_count <= 0:
    problems.append("sector rollup is empty")
elif sector_count < 3:
    warnings.append(f"sector count still small: {sector_count}")
else:
    wins.append(f"Sector rollup spans {sector_count} sectors")

if translated_year_total > 0:
    wins.append(f"Translated yearly value total is {money(translated_year_total)}")
else:
    problems.append("translated yearly value total is non-positive")

if files_scanned < 10:
    problems.append(f"files scanned too small: {files_scanned}")
if usable_files < 5:
    problems.append(f"usable files too small: {usable_files}")
if actual_candidates <= 0:
    problems.append("actual candidates scored is zero")

if problems:
    readiness = "RED"
elif warnings:
    readiness = "YELLOW"
else:
    readiness = "GREEN"

if readiness == "GREEN":
    seed_ask = "$1.0M–$2.5M"
    gov_ask = "$250k–$750k"
elif readiness == "YELLOW":
    seed_ask = "$500k–$1.2M"
    gov_ask = "$100k–$300k"
else:
    seed_ask = "$250k–$750k"
    gov_ask = "$50k–$200k"

txt_lines = [
    "LUMENCORE SEED VALIDATION READOUT",
    "=" * 78,
    f"Generated UTC: {now_utc()}",
    f"Readiness: {readiness}",
    "",
    "CURRENT ASK",
    f"Seed ask: {seed_ask}",
    f"Government / pilot ask: {gov_ask}",
    "",
    "TRUTH SNAPSHOT",
    f"- runtime mode: {runtime_mode}",
    f"- paper enabled: {paper_enabled}",
    f"- allow live orders: {allow_live_orders}",
    f"- execution mode: {execution_mode}",
    f"- execution live enabled: {execution_live_enabled}",
    f"- paper symbols count: {paper_symbols_count}",
    f"- paper symbols: {paper_symbols}",
    f"- enabled registry sources: {enabled_registry_sources}",
    f"- sector count: {sector_count}",
    f"- files scanned: {files_scanned}",
    f"- usable files: {usable_files}",
    f"- expected full candidates: {expected_candidates}",
    f"- actual candidates scored: {actual_candidates}",
    f"- flowforms count: {flowforms_count}",
    f"- algos count: {algos_count}",
    f"- strategies count: {strategies_count}",
    f"- metric profiles count: {metric_profiles_count}",
    f"- credible_top10 rows: {credible_top10_rows_count}",
    f"- empty report rows: {empty_report_rows}",
    f"- catalog rows: {catalog_rows}",
    f"- scan rows: {scan_rows}",
    f"- translated yearly value total: {translated_year_total}",
    f"- position: {position}",
    f"- last pair: {last_pair}",
    "",
    "CHAMPION",
    f"- file: {champ_file}",
    f"- flow: {champ_flow}",
    f"- algo: {champ_algo}",
    f"- strategy: {champ_strategy}",
    f"- metric_profile: {champ_profile}",
    f"- test_sharpe: {champ_sharpe}",
    f"- vs_baseline: {champ_vs_baseline}",
    f"- institutional_score: {champ_score}",
    "",
    "SECTOR ROLLUP TRUTH",
]

for r in sector_table:
    txt_lines.append(
        f"- {r['sector']}: sources={r['live_sources']} rows={r['rows']} hour={r['hour']} day={r['day']} week={r['week']} month={r['month']} year={r['year']} basis={r['basis']}"
    )

txt_lines.extend(["", "WINS"])
for x in wins:
    txt_lines.append(f"- {x}")

txt_lines.extend(["", "WARNINGS"])
for x in warnings:
    txt_lines.append(f"- {x}")

txt_lines.extend(["", "PROBLEMS"])
for x in problems:
    txt_lines.append(f"- {x}")

TXT_PATH.write_text("\n".join(txt_lines), encoding="utf-8")

def stat_card(label, value, sub=""):
    return f'''
    <div class="card">
      <div class="label">{esc(label)}</div>
      <div class="value">{esc(value)}</div>
      <div class="sub">{esc(sub)}</div>
    </div>
    '''

leader_cards = []
seen_sectors = set()
for row in credible_top10_rows:
    sector = str(row.get("sector", "")).strip() or "unknown"
    if sector in seen_sectors:
        continue
    seen_sectors.add(sector)
    leader_cards.append(f'''
      <div class="mini-card">
        <div class="mini-title">[{esc(sector)}] {esc(row.get("file", "UNKNOWN"))}</div>
        <div>{esc(row.get("flow", "?"))} / {esc(row.get("algo", "?"))} / {esc(row.get("strategy", "?"))} / {esc(row.get("profile", "?"))}</div>
        <div>Sharpe: {esc(fmt(row.get("sharpe", 0)))}</div>
        <div>Vs Baseline: {esc(fmt(row.get("vs_baseline", 0)))}</div>
        <div>Max DD: {esc(fmt(row.get("max_dd", 0)))}</div>
      </div>
    ''')

if not leader_cards:
    leader_cards.append('<div class="mini-card">No credible multi-sector leaders yet.</div>')

sector_rows_html = ""
for r in sector_table:
    sector_rows_html += f"""
    <tr>
      <td>{esc(r['sector'])}</td>
      <td>{esc(r['live_sources'])}</td>
      <td>{esc(r['rows'])}</td>
      <td>{esc(money(r['hour']))}</td>
      <td>{esc(money(r['day']))}</td>
      <td>{esc(money(r['week']))}</td>
      <td>{esc(money(r['month']))}</td>
      <td>{esc(money(r['year']))}</td>
      <td>{esc(r['basis'])}</td>
    </tr>
    """

if not sector_rows_html:
    sector_rows_html = '<tr><td colspan="9">No sector truth rows yet.</td></tr>'

def bullets(items):
    if not items:
        return "<li>none</li>"
    return "".join(f"<li>{esc(x)}</li>" for x in items)

readiness_class = readiness.lower()

html_doc = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>LumenCore — Seed Validation Readout</title>
<style>
body {{
  margin:0; padding:24px; background:#071225; color:#eaf2ff;
  font-family:Arial, Helvetica, sans-serif;
}}
h1 {{ margin:0 0 8px 0; font-size:28px; }}
.subtitle {{ color:#b7c7ea; margin-bottom:18px; }}
.grid {{
  display:grid; grid-template-columns:repeat(4, minmax(220px,1fr)); gap:14px;
}}
.card {{
  background:#0d1d3a; border:1px solid #244a93; border-radius:16px; padding:16px;
}}
.label {{
  font-size:12px; color:#9eb7ea; text-transform:uppercase;
}}
.value {{
  font-size:22px; font-weight:700; margin-top:8px;
}}
.sub {{
  font-size:12px; color:#9eb7ea; margin-top:4px;
}}
.big {{ grid-column:span 4; }}
.third {{ grid-column:span 1; }}
.section-title {{ font-size:20px; font-weight:700; margin-bottom:10px; }}
.readiness {{
  display:inline-block; padding:8px 14px; border-radius:999px; font-weight:800;
}}
.readiness.red {{ background:#5c1820; color:#ffd7dc; }}
.readiness.yellow {{ background:#5f4e11; color:#fff1b8; }}
.readiness.green {{ background:#153f25; color:#d9ffe7; }}
.mini-grid {{
  display:grid; grid-template-columns:repeat(3, minmax(240px,1fr)); gap:12px;
}}
.mini-card {{
  background:#102247; border:1px solid #2951a3; border-radius:12px; padding:12px;
}}
.mini-title {{ font-weight:700; margin-bottom:6px; }}
table {{
  width:100%; border-collapse:collapse; font-size:14px;
}}
th, td {{
  border-bottom:1px solid #1e3870; text-align:left; padding:10px 8px;
}}
th {{ color:#9eb7ea; }}
ul {{ margin:8px 0 0 20px; }}
</style>
</head>
<body>
  <h1>LumenCore — Seed Validation Readout</h1>
  <div class="subtitle">Validation-first readout for Wednesday meetings. Honest, audit-facing, and current from your local artifacts.</div>

  <div class="grid">
    <div class="card">
      <div class="label">Readiness</div>
      <div class="value"><span class="readiness {readiness_class}">{esc(readiness)}</span></div>
    </div>
    {stat_card("Enabled Registry Sources", enabled_registry_sources, "live truth rows")}
    {stat_card("Sector Count", sector_count, "multi-sector rollup")}
    {stat_card("Translated Year Value Total", money(translated_year_total), "current rollup")}
    {stat_card("Files Scanned", files_scanned, "catalog breadth")}
    {stat_card("Usable Files", usable_files, "clean/scorable")}
    {stat_card("Expected Full Candidates", expected_candidates, "search universe")}
    {stat_card("Actual Candidates Scored", actual_candidates, "completed")}
    {stat_card("Flowforms Count", flowforms_count, "registered")}
    {stat_card("Algos Count", algos_count, "registered")}
    {stat_card("Strategies Count", strategies_count, "registered")}
    {stat_card("Metric Profiles Count", metric_profiles_count, "registered")}
    {stat_card("Current Ask", seed_ask, "seed validation capital")}
    {stat_card("Gov / Pilot Ask", gov_ask, "paid pilot/evaluation capital")}
    {stat_card("Paper Symbols Count", paper_symbols_count, "paper universe")}
    {stat_card("Last Pair", last_pair, "execution memory")}

    <div class="card big">
      <div class="section-title">Champion</div>
      <div class="grid">
        {stat_card("File", champ_file)}
        {stat_card("Flow", champ_flow)}
        {stat_card("Algo", champ_algo)}
        {stat_card("Strategy", champ_strategy)}
        {stat_card("Metric Profile", champ_profile)}
        {stat_card("Test Sharpe", fmt(champ_sharpe))}
        {stat_card("Vs Baseline", fmt(champ_vs_baseline))}
        {stat_card("Institutional Score", fmt(champ_score))}
      </div>
    </div>

    <div class="card big">
      <div class="section-title">Multi-Sector Leaders</div>
      <div class="mini-grid">
        {''.join(leader_cards)}
      </div>
    </div>

    <div class="card big">
      <div class="section-title">Sector Rollup Truth</div>
      <table>
        <thead>
          <tr>
            <th>Sector</th><th>Live Sources</th><th>Rows</th><th>Hour</th><th>Day</th><th>Week</th><th>Month</th><th>Year</th><th>Basis</th>
          </tr>
        </thead>
        <tbody>
          {sector_rows_html}
        </tbody>
      </table>
    </div>

    <div class="card third">
      <div class="section-title">Wins</div>
      <ul>{bullets(wins)}</ul>
    </div>
    <div class="card third">
      <div class="section-title">Warnings</div>
      <ul>{bullets(warnings)}</ul>
    </div>
    <div class="card third">
      <div class="section-title">Problems</div>
      <ul>{bullets(problems)}</ul>
    </div>
  </div>
</body>
</html>
"""

HTML_PATH.write_text(html_doc, encoding="utf-8")

seed_validation_json = {
    "generated_utc": now_utc(),
    "readiness": readiness,
    "enabled_registry_sources": enabled_registry_sources,
    "sector_count": sector_count,
    "translated_year_value_total": translated_year_total,
    "files_scanned": files_scanned,
    "usable_files": usable_files,
    "expected_full_candidates": expected_candidates,
    "actual_candidates_scored": actual_candidates,
    "flowforms_count": flowforms_count,
    "algos_count": algos_count,
    "strategies_count": strategies_count,
    "metric_profiles_count": metric_profiles_count,
    "paper_symbols_count": paper_symbols_count,
    "paper_symbols": paper_symbols,
    "champion": {
        "file": champ_file,
        "flow": champ_flow,
        "algo": champ_algo,
        "strategy": champ_strategy,
        "metric_profile": champ_profile,
        "test_sharpe": champ_sharpe,
        "vs_baseline": champ_vs_baseline,
        "institutional_score": champ_score
    },
    "sector_rollup_truth": sector_table,
    "wins": wins,
    "warnings": warnings,
    "problems": problems
}
JSON_PATH.write_text(json.dumps(seed_validation_json, indent=2), encoding="utf-8")

print("")
print("REBUILD COMPLETE")
print("TXT :", TXT_PATH)
print("JSON:", JSON_PATH)
print("HTML:", HTML_PATH)
print("READINESS:", readiness)
print("ENABLED REGISTRY SOURCES:", enabled_registry_sources)
print("SECTOR COUNT:", sector_count)
print("YEAR VALUE TOTAL:", translated_year_total)