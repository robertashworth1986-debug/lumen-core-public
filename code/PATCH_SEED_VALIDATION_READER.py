import csv, json, html
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT  = ROOT / "out"
CONF = ROOT / "config"
DASH = Path(r"C:\LumaTrader\dashboard")

TXT  = OUT / "seed_validation_readout.txt"
HTML = DASH / "seed_validation_readout.html"

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
        if v is None or str(v).strip() == "":
            return default
        return float(v)
    except Exception:
        return default

def as_int(v, default=0):
    try:
        if v is None or str(v).strip() == "":
            return default
        return int(float(v))
    except Exception:
        return default

def esc(x):
    return html.escape(str(x))

def money(v):
    return "${:,.2f}".format(as_float(v, 0.0))

def num(v):
    try:
        return "{:,.2f}".format(float(v))
    except Exception:
        return str(v)

# -------- load current artifacts --------
runtime_control      = load_json(CONF / "runtime_control.json", {})
paper_runtime        = load_json(CONF / "paper_trader_runtime.json", {})
infra_runtime        = load_json(CONF / "infra_live_runtime.json", {})
live_sources         = load_json(CONF / "live_sources.json", {})
live_registry        = load_json(CONF / "live_source_registry.json", {})
source_truth         = load_json(OUT  / "source_truth_table.json", {})
stack_truth_report   = load_json(OUT  / "stack_truth_report.json", {})
full_beast_summary   = load_json(OUT  / "full_beast_summary.json", {})
adaptive_champion    = load_json(OUT  / "adaptive_champion.json", {})
execution_runtime    = load_json(OUT  / "execution_runtime.json", {})
execution_status     = load_json(OUT  / "execution_status.json", {})
data_ingest_proof    = load_json(OUT  / "data_ingest_proof.json", {})
sector_matrix_json   = load_json(OUT  / "sector_value_matrix.json", {})

credible_top10_rows  = load_csv_rows(OUT / "credible_top10.csv")
dataset_catalog_rows = load_csv_rows(OUT / "dataset_catalog.csv")
data_scan_rows       = load_csv_rows(OUT / "data_scan_summary.csv")
empty_rows           = load_csv_rows(OUT / "empty_report.csv")
auto_dataset_rows    = load_csv_rows(OUT / "auto_dataset_results.csv")

# -------- resolve registry rows from either source --------
registry_rows = []
if isinstance(source_truth, dict) and isinstance(source_truth.get("sources"), list) and source_truth.get("sources"):
    registry_rows = source_truth.get("sources", [])
elif isinstance(live_registry, dict) and isinstance(live_registry.get("sources"), list):
    registry_rows = live_registry.get("sources", [])

enabled_live_rows = []
for r in registry_rows:
    status  = str(r.get("status", "")).upper()
    enabled = bool(r.get("enabled", True))
    if status == "LIVE_KEY_PRESENT" and enabled:
        enabled_live_rows.append(r)

# -------- sector rollup reading both old/new field names --------
sector_rollup = {}
for r in enabled_live_rows:
    sector = str(r.get("sector", "unknown"))
    rows = as_int(r.get("rows", 0), 0)

    est_hour = (
        as_float(r.get("estimated_hour_value", None), None)
        if r.get("estimated_hour_value", None) is not None else
        as_float(r.get("est_dollar_per_hour", None), None)
        if r.get("est_dollar_per_hour", None) is not None else
        as_float(r.get("est_hour", 0.0), 0.0)
    )
    if est_hour is None:
        est_hour = 0.0

    basis = str(
        r.get("value_basis",
        r.get("basis",
        "MEASURED" if rows > 1 else "ESTIMATED"))
    ).upper()

    d = sector_rollup.setdefault(sector, {
        "live_sources": 0,
        "rows": 0,
        "hour": 0.0,
        "basis": "MEASURED"
    })
    d["live_sources"] += 1
    d["rows"] += rows
    d["hour"] += est_hour
    if basis != "MEASURED":
        d["basis"] = "ESTIMATED"

sector_table = []
for sector, d in sorted(sector_rollup.items(), key=lambda kv: kv[1]["hour"], reverse=True):
    hour = as_float(d["hour"], 0.0)
    sector_table.append({
        "sector": sector,
        "live_sources": as_int(d["live_sources"], 0),
        "rows": as_int(d["rows"], 0),
        "hour": round(hour, 2),
        "day": round(hour * 24, 2),
        "week": round(hour * 24 * 7, 2),
        "month": round(hour * 24 * 30, 2),
        "year": round(hour * 24 * 365, 2),
        "basis": d["basis"]
    })

translated_year_total = round(sum(x["year"] for x in sector_table), 2)

# -------- champion resolution from best available source --------
champ = {}
if full_beast_summary:
    champ["file"] = full_beast_summary.get("top_file", adaptive_champion.get("file", "UNKNOWN"))
    champ["flow"] = full_beast_summary.get("top_flow", adaptive_champion.get("flow", "UNKNOWN"))
    champ["algo"] = full_beast_summary.get("top_algo", adaptive_champion.get("algo", "UNKNOWN"))
    champ["strategy"] = full_beast_summary.get("top_strategy", adaptive_champion.get("strategy", "UNKNOWN"))
    champ["metric_profile"] = full_beast_summary.get("top_metric_profile", adaptive_champion.get("metric_profile", adaptive_champion.get("profile", "UNKNOWN")))
    champ["test_sharpe"] = as_float(full_beast_summary.get("top_test_sharpe", adaptive_champion.get("sharpe", 0.0)), 0.0)
    champ["vs_baseline"] = as_float(full_beast_summary.get("top_test_vs_baseline", adaptive_champion.get("vs_baseline", 0.0)), 0.0)
    champ["institutional_score"] = full_beast_summary.get("top_institutional_score", adaptive_champion.get("score", 0.0))
else:
    champ["file"] = adaptive_champion.get("file", "UNKNOWN")
    champ["flow"] = adaptive_champion.get("flow", "UNKNOWN")
    champ["algo"] = adaptive_champion.get("algo", "UNKNOWN")
    champ["strategy"] = adaptive_champion.get("strategy", "UNKNOWN")
    champ["metric_profile"] = adaptive_champion.get("metric_profile", adaptive_champion.get("profile", "UNKNOWN"))
    champ["test_sharpe"] = as_float(adaptive_champion.get("sharpe", 0.0), 0.0)
    champ["vs_baseline"] = as_float(adaptive_champion.get("vs_baseline", 0.0), 0.0)
    champ["institutional_score"] = adaptive_champion.get("score", 0.0)

# -------- counts --------
files_scanned = max(
    as_int(full_beast_summary.get("files_scanned", 0), 0),
    len({r.get("file","") for r in dataset_catalog_rows if r.get("file","")}),
    len(auto_dataset_rows)
)

usable_files = max(
    as_int(full_beast_summary.get("usable_files", 0), 0),
    len([r for r in data_ingest_proof.get("top_clean_files", []) if r]),
    len([r for r in auto_dataset_rows if r.get("file")])
)

flowforms_count = max(
    as_int(full_beast_summary.get("flowforms_count", 0), 0),
    0
)
algos_count = max(
    as_int(full_beast_summary.get("algos_count", 0), 0),
    0
)
strategies_count = max(
    as_int(full_beast_summary.get("strategies_count", 0), 0),
    0
)
metric_profiles_count = max(
    as_int(full_beast_summary.get("metric_profiles_count", 0), 0),
    0
)

expected_candidates = max(
    as_int(full_beast_summary.get("expected_full_candidates", 0), 0),
    0
)
actual_candidates = max(
    as_int(full_beast_summary.get("actual_candidates_scored", 0), 0),
    0
)

paper_symbols = paper_runtime.get("symbols", [])
paper_symbols_count = len(paper_symbols)
paper_enabled = bool(paper_runtime.get("paper_enabled", False))
runtime_mode = str(runtime_control.get("mode", "unknown"))
allow_live_orders = bool(runtime_control.get("allow_live_orders", False))
execution_mode = str(execution_runtime.get("runtime_mode", execution_status.get("execution_mode", "unknown")))
execution_live_enabled = bool(execution_runtime.get("live_enabled", False))
position = str(execution_runtime.get("position", "unknown"))
last_pair = str(execution_runtime.get("last_pair", execution_runtime.get("symbol", "unknown")))

enabled_registry_sources = len(enabled_live_rows)
sector_count = len(sector_table)

credible_top10_rows_count = len(credible_top10_rows)
empty_report_rows = len(empty_rows)
catalog_rows = len(dataset_catalog_rows)
scan_rows = len(data_scan_rows)

# -------- readiness --------
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

if champ["test_sharpe"] > 0:
    wins.append(f"Champion test Sharpe is positive ({num(champ['test_sharpe'])}).")
else:
    problems.append("champion test Sharpe is non-positive")

if champ["vs_baseline"] <= 0:
    warnings.append(f"champion vs baseline is {num(champ['vs_baseline'])}")
else:
    wins.append(f"Champion beats baseline by {num(champ['vs_baseline'])}")

if enabled_registry_sources < 5:
    problems.append(f"enabled live registry sources too small: {enabled_registry_sources}")
elif enabled_registry_sources < 10:
    warnings.append(f"enabled live registry rows below target: {enabled_registry_sources}")
else:
    wins.append(f"Registry live source count is {enabled_registry_sources}")

if sector_count <= 0:
    problems.append("sector rollup is empty")
elif sector_count < 5:
    warnings.append(f"sector count below target: {sector_count}")
else:
    wins.append(f"Sector rollup spans {sector_count} sectors")

if translated_year_total <= 0:
    problems.append("translated yearly value total is non-positive")
else:
    wins.append(f"Translated yearly value total is {money(translated_year_total)}")

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

seed_ask = "$250k–$750k"
gov_ask = "$50k–$200k"
if readiness == "YELLOW":
    seed_ask = "$500k–$1.2M"
    gov_ask = "$100k–$300k"
elif readiness == "GREEN":
    seed_ask = "$1.0M–$2.5M"
    gov_ask = "$250k–$750k"

# -------- write text --------
txt_lines = []
txt_lines.append("LUMENCORE SEED VALIDATION READOUT")
txt_lines.append("=" * 78)
txt_lines.append(f"Generated UTC: {now_utc()}")
txt_lines.append(f"Readiness: {readiness}")
txt_lines.append("")
txt_lines.append("CURRENT ASK")
txt_lines.append(f"Seed ask: {seed_ask}")
txt_lines.append(f"Government / pilot ask: {gov_ask}")
txt_lines.append("")
txt_lines.append("TRUTH SNAPSHOT")
for k, v in [
    ("runtime mode", runtime_mode),
    ("paper enabled", paper_enabled),
    ("allow live orders", allow_live_orders),
    ("execution mode", execution_mode),
    ("execution live enabled", execution_live_enabled),
    ("paper symbols count", paper_symbols_count),
    ("paper symbols", paper_symbols),
    ("enabled registry sources", enabled_registry_sources),
    ("sector count", sector_count),
    ("files scanned", files_scanned),
    ("usable files", usable_files),
    ("expected full candidates", expected_candidates),
    ("actual candidates scored", actual_candidates),
    ("flowforms count", flowforms_count),
    ("algos count", algos_count),
    ("strategies count", strategies_count),
    ("metric profiles count", metric_profiles_count),
    ("credible_top10 rows", credible_top10_rows_count),
    ("empty report rows", empty_report_rows),
    ("catalog rows", catalog_rows),
    ("scan rows", scan_rows),
    ("translated yearly value total", translated_year_total),
    ("position", position),
    ("last pair", last_pair),
]:
    txt_lines.append(f"- {k}: {v}")

txt_lines.append("")
txt_lines.append("CHAMPION")
for k, v in champ.items():
    txt_lines.append(f"- {k}: {v}")

txt_lines.append("")
txt_lines.append("SECTOR ROLLUP TRUTH")
for r in sector_table:
    txt_lines.append(
        f"- {r['sector']}: sources={r['live_sources']} rows={r['rows']} "
        f"hour={r['hour']} day={r['day']} week={r['week']} month={r['month']} year={r['year']} basis={r['basis']}"
    )

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

TXT.write_text("\n".join(txt_lines), encoding="utf-8")

# -------- write html --------
def box(title, value, sub=""):
    return f"""
    <div class="card stat">
      <div class="label">{esc(title)}</div>
      <div class="value">{esc(value)}</div>
      <div class="sub">{esc(sub)}</div>
    </div>
    """

def list_block(title, items):
    inner = "".join(f"<li>{esc(x)}</li>" for x in items) if items else "<li>none</li>"
    return f"""
    <div class="card">
      <div class="section-title">{esc(title)}</div>
      <ul>{inner}</ul>
    </div>
    """

leader_cards = []
seen_sectors = set()
for row in credible_top10_rows:
    sector = str(row.get("sector","")).strip() or "unknown"
    if sector in seen_sectors:
        continue
    seen_sectors.add(sector)
    leader_cards.append(f"""
    <div class="mini-card">
      <div class="mini-title">[{esc(sector)}] {esc(row.get('file','UNKNOWN'))}</div>
      <div>{esc(row.get('flow','?'))} / {esc(row.get('algo','?'))} / {esc(row.get('strategy','?'))} / {esc(row.get('profile','?'))}</div>
      <div>Sharpe: {esc(num(row.get('sharpe',0)))}</div>
      <div>Vs Baseline: {esc(num(row.get('vs_baseline',0)))}</div>
      <div>Max DD: {esc(num(row.get('max_dd',0)))}</div>
    </div>
    """)
if not leader_cards:
    leader_cards.append('<div class="mini-card">No credible multi-sector leaders yet.</div>')

sector_rows_html = "".join(f"""
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
""" for r in sector_table) or '<tr><td colspan="9">No sector truth rows yet.</td></tr>'

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
  box-shadow:0 0 0 1px rgba(60,120,255,.08) inset;
}}
.stat .label {{ font-size:12px; color:#9eb7ea; text-transform:uppercase; }}
.stat .value {{ font-size:22px; font-weight:700; margin-top:8px; }}
.stat .sub {{ font-size:12px; color:#9eb7ea; margin-top:4px; }}
.section-title {{ font-size:20px; font-weight:700; margin-bottom:8px; }}
.big {{
  grid-column: span 4;
}}
.half {{
  grid-column: span 2;
}}
.readiness {{
  font-size:20px; font-weight:800; padding:8px 14px; border-radius:999px; display:inline-block;
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
code {{ color:#a8d2ff; }}
</style>
</head>
<body>
  <h1>LumenCore — Seed Validation Readout</h1>
  <div class="subtitle">Validation-first readout for Wednesday meetings. Honest, audit-facing, and current from your local artifacts.</div>

  <div class="grid">
    <div class="card stat">
      <div class="label">Readiness</div>
      <div class="value"><span class="readiness {readiness_class}">{readiness}</span></div>
    </div>
    {box("Enabled Registry Sources", enabled_registry_sources, "live truth rows")}
    {box("Sector Count", sector_count, "multi-sector rollup")}
    {box("Files Scanned", files_scanned, "catalog breadth")}
    {box("Usable Files", usable_files, "clean / scorable")}
    {box("Expected Full Candidates", expected_candidates, "search universe")}
    {box("Actual Candidates Scored", actual_candidates, "completed")}
    {box("Flowforms Count", flowforms_count, "registered")}
    {box("Algos Count", algos_count, "registered")}
    {box("Strategies Count", strategies_count, "registered")}
    {box("Metric Profiles Count", metric_profiles_count, "registered")}
    {box("Current Ask", seed_ask, "seed validation capital")}
    {box("Gov / Pilot Ask", gov_ask, "paid pilot / evaluation capital")}

    <div class="card big">
      <div class="section-title">Champion</div>
      <div class="grid">
        {box("File", champ.get("file","UNKNOWN"))}
        {box("Flow", champ.get("flow","UNKNOWN"))}
        {box("Algo", champ.get("algo","UNKNOWN"))}
        {box("Strategy", champ.get("strategy","UNKNOWN"))}
        {box("Metric Profile", champ.get("metric_profile","UNKNOWN"))}
        {box("Test Sharpe", num(champ.get("test_sharpe",0)))}
        {box("Vs Baseline", num(champ.get("vs_baseline",0)))}
        {box("Institutional Score", num(champ.get("institutional_score",0)))}
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

    {list_block("Wins", wins)}
    {list_block("Warnings", warnings)}
    {list_block("Problems", problems)}
  </div>
</body>
</html>
"""
HTML.write_text(html_doc, encoding="utf-8")

seed_validation_json = {{
    "generated_utc": now_utc(),
    "readiness": readiness,
    "enabled_registry_sources": enabled_registry_sources,
    "sector_count": sector_count,
    "translated_year_value_total": translated_year_total,
    "champion": champ,
    "wins": wins,
    "warnings": warnings,
    "problems": problems
}}
(OUT / "seed_validation_readout.json").write_text(json.dumps(seed_validation_json, indent=2), encoding="utf-8")

print("")
print("REBUILD COMPLETE")
print("TXT :", TXT)
print("HTML:", HTML)
print("READINESS:", readiness)
print("ENABLED REGISTRY SOURCES:", enabled_registry_sources)
print("SECTOR COUNT:", sector_count)
print("YEAR VALUE TOTAL:", translated_year_total)