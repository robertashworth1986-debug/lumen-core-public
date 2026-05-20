import csv, json, math, html
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONF = ROOT / "config"
OUT = ROOT / "out"
DASH_ROOT = Path(r"C:\LumaTrader\dashboard")
DASH_STACK = ROOT / "dashboard"

JSON_OUT = OUT / "seed_validation_readout.json"
TXT_OUT  = OUT / "seed_validation_readout.txt"
HTML_OUTS = [
    DASH_ROOT / "seed_validation_readout.html",
    DASH_STACK / "seed_validation_readout.html",
]

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def load_csv_rows(path):
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    tried = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
    for enc in tried:
        try:
            with p.open("r", encoding=enc, newline="") as f:
                for row in csv.DictReader(f):
                    rows.append({k: v for k, v in row.items()})
            return rows
        except Exception:
            rows = []
    return []

def as_float(v, default=0.0):
    try:
        if v is None or v == "":
            return default
        return float(str(v).replace(",", ""))
    except Exception:
        return default

def as_int(v, default=0):
    try:
        if v is None or v == "":
            return default
        return int(float(str(v).replace(",", "")))
    except Exception:
        return default

def money(v):
    try:
        return "${:,.2f}".format(float(v))
    except Exception:
        return "$0.00"

def num(v):
    try:
        fv = float(v)
        if abs(fv) >= 1000:
            return "{:,.0f}".format(fv)
        return "{:,.2f}".format(fv)
    except Exception:
        return str(v)

def esc(x):
    return html.escape(str(x))

runtime_control = load_json(CONF / "runtime_control.json", {})
paper_runtime   = load_json(CONF / "paper_trader_runtime.json", {})
infra_runtime   = load_json(CONF / "infra_live_runtime.json", {})
live_sources    = load_json(CONF / "live_sources.json", {})
live_registry   = load_json(CONF / "live_source_registry.json", {})

execution_status  = load_json(OUT / "execution_status.json", {})
execution_runtime = load_json(OUT / "execution_runtime.json", {})
truth_report      = load_json(OUT / "stack_truth_report.json", {})
adaptive_champion = load_json(OUT / "adaptive_champion.json", {})
full_beast_sum    = load_json(OUT / "full_beast_summary.json", {})
full_beast_reg    = load_json(OUT / "full_beast_registry.json", {})
data_ingest_proof = load_json(OUT / "data_ingest_proof.json", {})
infra_truth       = load_json(OUT / "source_truth_table.json", {})
sector_matrix     = load_json(OUT / "sector_value_matrix.json", {})

cred_rows   = load_csv_rows(OUT / "credible_top10.csv")
empty_rows  = load_csv_rows(OUT / "empty_report.csv")
scan_rows   = load_csv_rows(OUT / "data_scan_summary.csv")
catalog_rows= load_csv_rows(OUT / "dataset_catalog.csv")
auto_rows   = load_csv_rows(OUT / "auto_dataset_results.csv")

registry_rows = live_registry.get("sources", []) if isinstance(live_registry, dict) else []
enabled_registry_rows = [r for r in registry_rows if str(r.get("status","")).upper() == "LIVE_KEY_PRESENT"]

paper_mode = str(runtime_control.get("mode", "unknown")).lower()
allow_live_orders = bool(runtime_control.get("allow_live_orders", False))
paper_enabled = bool(paper_runtime.get("paper_enabled", False))
paper_symbols = paper_runtime.get("symbols", [])
if not isinstance(paper_symbols, list):
    paper_symbols = []

execution_mode = str(execution_runtime.get("runtime_mode", execution_status.get("execution_mode", "unknown"))).lower()
execution_live_enabled = bool(execution_runtime.get("live_enabled", False))
last_pair = str(execution_runtime.get("last_pair", execution_status.get("last_pair", "unknown")))
last_mode = str(execution_runtime.get("last_mode", execution_status.get("note", "unknown")))
position = str(execution_runtime.get("position", "unknown"))

files_scanned = as_int(full_beast_sum.get("files_scanned", truth_report.get("files_scanned", 0)))
usable_files  = as_int(full_beast_sum.get("usable_files", 0))
expected_full_candidates = as_int(full_beast_sum.get("expected_full_candidates", 0))
actual_scored = as_int(full_beast_sum.get("actual_candidates_scored", 0))

flowforms_count = as_int(full_beast_sum.get("flowforms_count", len(full_beast_reg.get("flowforms", []))))
algos_count = as_int(full_beast_sum.get("algos_count", len(full_beast_reg.get("algorithms", []))))
strategies_count = as_int(full_beast_sum.get("strategies_count", len(full_beast_reg.get("strategies", []))))
metric_profiles_count = as_int(full_beast_sum.get("metric_profiles_count", len(full_beast_reg.get("metric_profiles", []))))

champ_file = full_beast_sum.get("top_file", adaptive_champion.get("file", "UNKNOWN"))
champ_flow = full_beast_sum.get("top_flow", adaptive_champion.get("flow", "UNKNOWN"))
champ_algo = full_beast_sum.get("top_algo", adaptive_champion.get("algo", "UNKNOWN"))
champ_strategy = full_beast_sum.get("top_strategy", adaptive_champion.get("strategy", "UNKNOWN"))
champ_profile = full_beast_sum.get("top_metric_profile", adaptive_champion.get("metric_profile", "UNKNOWN"))
champ_sharpe = as_float(full_beast_sum.get("top_test_sharpe", adaptive_champion.get("sharpe", 0.0)))
champ_vs_baseline = as_float(full_beast_sum.get("top_test_vs_baseline", adaptive_champion.get("vs_baseline", 0.0)))
champ_score = as_float(full_beast_sum.get("top_institutional_score", adaptive_champion.get("score", 0.0)))

ingest_top_clean = data_ingest_proof.get("top_clean_files", [])
ingest_clean_count = len(ingest_top_clean) if isinstance(ingest_top_clean, list) else 0

sector_rows = []
if isinstance(infra_truth, dict) and isinstance(infra_truth.get("rows"), list):
    sector_rows = infra_truth.get("rows", [])
elif isinstance(sector_matrix, dict) and isinstance(sector_matrix.get("sector_table"), list):
    sector_rows = sector_matrix.get("sector_table", [])

measured_sector_rows = []
for r in sector_rows:
    basis = str(r.get("basis", r.get("evidence_basis", "ESTIMATED"))).upper()
    rows = as_int(r.get("rows", 0))
    if basis == "MEASURED" or rows > 1:
        measured_sector_rows.append(r)

year_value_total = 0.0
for r in sector_rows:
    year_value_total += as_float(r.get("year", 0.0))

problems = []
warnings = []
wins = []

if paper_mode != "paper":
    problems.append(f"runtime_control.mode is {paper_mode}, expected paper")
if not paper_enabled:
    problems.append("paper_trader_runtime.paper_enabled is false")
if allow_live_orders:
    problems.append("runtime_control.allow_live_orders is true")
if execution_mode not in ("paper", "shadow"):
    warnings.append(f"execution runtime mode is {execution_mode}")
if execution_live_enabled:
    problems.append("execution_runtime.live_enabled is true")
if len(enabled_registry_rows) < 5:
    problems.append(f"enabled live registry rows too small: {len(enabled_registry_rows)}")
if files_scanned < 25:
    warnings.append(f"files_scanned still small: {files_scanned}")
if usable_files < 10:
    problems.append(f"usable_files too small: {usable_files}")
if actual_scored < 10000:
    problems.append(f"actual_candidates_scored too small: {actual_scored}")
if flowforms_count < 20:
    problems.append(f"flowforms_count too small: {flowforms_count}")
if algos_count < 10:
    problems.append(f"algos_count too small: {algos_count}")
if strategies_count < 10:
    problems.append(f"strategies_count too small: {strategies_count}")
if metric_profiles_count < 6:
    problems.append(f"metric_profiles_count too small: {metric_profiles_count}")
if len(scan_rows) == 0:
    problems.append("data_scan_summary.csv missing or empty")
if len(catalog_rows) == 0:
    problems.append("dataset_catalog.csv missing or empty")
if len(cred_rows) == 0:
    problems.append("credible_top10.csv missing or empty")
if len(empty_rows) > 0:
    warnings.append(f"empty_report.csv has {len(empty_rows)} row(s)")
if champ_sharpe <= 0:
    problems.append(f"top_test_sharpe not positive: {champ_sharpe}")
if champ_vs_baseline <= 0:
    warnings.append(f"top_test_vs_baseline not positive: {champ_vs_baseline}")
if len(measured_sector_rows) == 0:
    warnings.append("no sector currently qualifies as measured-source evidence")
if year_value_total <= 0:
    problems.append("sector yearly translated value total is non-positive")

if paper_mode == "paper" and paper_enabled and not allow_live_orders:
    wins.append("Paper execution is in paper mode and live orders are disabled.")
if len(enabled_registry_rows) >= 5:
    wins.append(f"Live registry sees {len(enabled_registry_rows)} connected sources.")
if len(scan_rows) > 0 and len(catalog_rows) > 0:
    wins.append("Dataset scan and catalog artifacts exist.")
if champ_sharpe > 0:
    wins.append(f"Top champion currently shows positive test Sharpe ({num(champ_sharpe)}).")
if len(measured_sector_rows) > 0:
    wins.append(f"{len(measured_sector_rows)} sector row(s) currently qualify as measured evidence.")

if len(problems) == 0 and len(warnings) == 0:
    readiness = "GREEN"
elif len(problems) == 0:
    readiness = "YELLOW"
else:
    readiness = "RED"

if readiness == "GREEN":
    investor_ask = {
        "seed_raise_usd_low": 1000000,
        "seed_raise_usd_high": 2500000,
        "gov_pilot_usd_low": 150000,
        "gov_pilot_usd_high": 500000,
        "message": "Raise for pilot deployment, engineering hardening, live ingestion expansion, validation, audit packaging, and first paid pilots."
    }
elif readiness == "YELLOW":
    investor_ask = {
        "seed_raise_usd_low": 500000,
        "seed_raise_usd_high": 1200000,
        "gov_pilot_usd_low": 100000,
        "gov_pilot_usd_high": 300000,
        "message": "Raise for validation completion, live data hardening, audit trail expansion, and conversion of strongest lanes into pilot-ready proofs."
    }
else:
    investor_ask = {
        "seed_raise_usd_low": 250000,
        "seed_raise_usd_high": 750000,
        "gov_pilot_usd_low": 50000,
        "gov_pilot_usd_high": 200000,
        "message": "Ask for validation capital and paid evaluation pilots, not scale capital yet."
    }

one_liner = (
    "We are building an institutional-grade live intelligence and optimization platform that ingests multi-sector data, "
    "tests a large universe of flowforms / algorithms / strategies / metric profiles, ranks the strongest edges, "
    "and produces auditable outputs for infrastructure and market decision support."
)

payload = {
    "generated_utc": now_utc(),
    "readiness": readiness,
    "one_liner": one_liner,
    "wins": wins,
    "warnings": warnings,
    "problems": problems,
    "investor_ask": investor_ask,
    "truth_snapshot": {
        "runtime_mode": paper_mode,
        "paper_enabled": paper_enabled,
        "allow_live_orders": allow_live_orders,
        "execution_mode": execution_mode,
        "execution_live_enabled": execution_live_enabled,
        "paper_symbols_count": len(paper_symbols),
        "paper_symbols": paper_symbols,
        "enabled_registry_sources": len(enabled_registry_rows),
        "files_scanned": files_scanned,
        "usable_files": usable_files,
        "expected_full_candidates": expected_full_candidates,
        "actual_candidates_scored": actual_scored,
        "flowforms_count": flowforms_count,
        "algos_count": algos_count,
        "strategies_count": strategies_count,
        "metric_profiles_count": metric_profiles_count,
        "credible_top10_rows": len(cred_rows),
        "empty_report_rows": len(empty_rows),
        "catalog_rows": len(catalog_rows),
        "scan_rows": len(scan_rows),
        "measured_sector_rows": len(measured_sector_rows),
        "translated_year_value_total": round(year_value_total, 2),
        "last_pair": last_pair,
        "last_mode": last_mode,
        "position": position
    },
    "champion": {
        "file": champ_file,
        "flow": champ_flow,
        "algo": champ_algo,
        "strategy": champ_strategy,
        "metric_profile": champ_profile,
        "test_sharpe": champ_sharpe,
        "vs_baseline": champ_vs_baseline,
        "institutional_score": champ_score
    }
}

JSON_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

lines = []
lines.append("LUMENCORE SEED VALIDATION READOUT")
lines.append("=" * 72)
lines.append(f"Generated UTC: {payload['generated_utc']}")
lines.append(f"Readiness: {readiness}")
lines.append("")
lines.append("ONE-LINER")
lines.append(one_liner)
lines.append("")
lines.append("CURRENT ASK")
lines.append(f"Seed ask: {money(investor_ask['seed_raise_usd_low'])} to {money(investor_ask['seed_raise_usd_high'])}")
lines.append(f"Government / pilot ask: {money(investor_ask['gov_pilot_usd_low'])} to {money(investor_ask['gov_pilot_usd_high'])}")
lines.append(investor_ask["message"])
lines.append("")
lines.append("TRUTH SNAPSHOT")
for k, v in payload["truth_snapshot"].items():
    lines.append(f"- {k}: {v}")
lines.append("")
lines.append("CHAMPION")
for k, v in payload["champion"].items():
    lines.append(f"- {k}: {v}")
lines.append("")
lines.append("WINS")
if wins:
    for w in wins:
        lines.append(f"+ {w}")
else:
    lines.append("+ none yet")
lines.append("")
lines.append("WARNINGS")
if warnings:
    for w in warnings:
        lines.append(f"! {w}")
else:
    lines.append("! none")
lines.append("")
lines.append("PROBLEMS")
if problems:
    for p in problems:
        lines.append(f"x {p}")
else:
    lines.append("x none")
lines.append("")
lines.append("WHAT TO SAY WEDNESDAY")
if readiness == "GREEN":
    lines.append("We have a working validated paper-mode system with auditable artifacts and positive champion evidence.")
    lines.append("We are asking for capital to harden, expand, and deploy pilots.")
elif readiness == "YELLOW":
    lines.append("We have a working platform with real artifacts, but we are still tightening validation before scale.")
    lines.append("We are asking for validation capital / pilot capital, not hype capital.")
else:
    lines.append("We have real architecture and partial truth artifacts, but not enough verified evidence to claim full institutional readiness.")
    lines.append("We are asking for validation capital and paid pilot access to finish the truth stack.")
lines.append("")
lines.append("FILE OUTPUTS")
lines.append(str(JSON_OUT))
lines.append(str(TXT_OUT))
for html_out in HTML_OUTS:
    lines.append(str(html_out))

TXT_OUT.write_text("\n".join(lines), encoding="utf-8")

def badge(text, cls):
    return f'<span class="badge {cls}">{esc(text)}</span>'

readiness_cls = "green" if readiness == "GREEN" else ("yellow" if readiness == "YELLOW" else "red")

wins_html = "".join(f"<li>{esc(x)}</li>" for x in wins) or "<li>none yet</li>"
warn_html = "".join(f"<li>{esc(x)}</li>" for x in warnings) or "<li>none</li>"
prob_html = "".join(f"<li>{esc(x)}</li>" for x in problems) or "<li>none</li>"

snapshot_cards = []
for k, v in payload["truth_snapshot"].items():
    snapshot_cards.append(f"""
    <div class="card mini">
      <div class="label">{esc(k)}</div>
      <div class="value">{esc(v)}</div>
    </div>
    """)

champ_cards = []
for k, v in payload["champion"].items():
    champ_cards.append(f"""
    <div class="card mini">
      <div class="label">{esc(k)}</div>
      <div class="value">{esc(v)}</div>
    </div>
    """)

html_doc = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>LumenCore Seed Validation Readout</title>
<style>
body {{
  margin: 0;
  background: #081224;
  color: #eaf2ff;
  font-family: Arial, Helvetica, sans-serif;
}}
.wrap {{
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}}
h1 {{ margin: 0 0 8px 0; font-size: 38px; }}
.sub {{ color: #9fb7e8; margin-bottom: 18px; }}
.grid {{
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}}
.grid2 {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}}
.card {{
  background: linear-gradient(180deg,#0e1f3d,#0a1730);
  border: 1px solid #284a8a;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 0 0 1px rgba(56,110,198,0.15) inset;
}}
.mini .label {{ color:#9fb7e8; font-size:12px; text-transform:uppercase; }}
.mini .value {{ font-size:20px; font-weight:700; margin-top:6px; word-break:break-word; }}
.badge {{
  display:inline-block; padding:6px 10px; border-radius:999px; font-weight:700; font-size:13px;
}}
.green {{ background:#103b22; color:#72f0a2; border:1px solid #2e8b57; }}
.yellow {{ background:#4b3a08; color:#ffd76a; border:1px solid #a98516; }}
.red {{ background:#4b1212; color:#ff8c8c; border:1px solid #a63b3b; }}
ul {{ margin: 8px 0 0 18px; }}
.section-title {{ font-size:22px; font-weight:700; margin: 24px 0 12px 0; }}
.note {{ color:#c9d7f5; line-height:1.5; }}
.ask {{ font-size:18px; font-weight:700; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>LumenCore — Seed Validation Readout</h1>
  <div class="sub">Validation-first readout for Wednesday meetings. Honest, audit-facing, and current from your local artifacts.</div>

  <div class="card">
    <div style="display:flex; justify-content:space-between; align-items:center; gap:16px; flex-wrap:wrap;">
      <div>
        <div class="section-title" style="margin:0 0 6px 0;">Readiness</div>
        {badge(readiness, readiness_cls)}
      </div>
      <div>
        <div class="label">Generated UTC</div>
        <div class="value">{esc(payload["generated_utc"])}</div>
      </div>
    </div>
    <p class="note" style="margin-top:14px;">{esc(one_liner)}</p>
  </div>

  <div class="section-title">Current ask</div>
  <div class="grid2">
    <div class="card">
      <div class="label">Seed ask</div>
      <div class="ask">{money(investor_ask["seed_raise_usd_low"])} to {money(investor_ask["seed_raise_usd_high"])}</div>
      <p class="note">{esc(investor_ask["message"])}</p>
    </div>
    <div class="card">
      <div class="label">Government / pilot ask</div>
      <div class="ask">{money(investor_ask["gov_pilot_usd_low"])} to {money(investor_ask["gov_pilot_usd_high"])}</div>
      <p class="note">Ask for a paid evaluation, pilot, SBIR-style validation, or technical assessment contract.</p>
    </div>
  </div>

  <div class="section-title">Truth snapshot</div>
  <div class="grid">
    {''.join(snapshot_cards)}
  </div>

  <div class="section-title">Champion</div>
  <div class="grid">
    {''.join(champ_cards)}
  </div>

  <div class="section-title">Validation readout</div>
  <div class="grid2">
    <div class="card"><div class="label">Wins</div><ul>{wins_html}</ul></div>
    <div class="card"><div class="label">Warnings</div><ul>{warn_html}</ul></div>
  </div>

  <div class="section-title">Problems to fix before calling it fully validated</div>
  <div class="card">
    <ul>{prob_html}</ul>
  </div>

  <div class="section-title">Wednesday language</div>
  <div class="card">
    <p class="note">{
      esc("We are not asking you to fund a dream dashboard. We are asking you to fund the completion and pilot deployment of a live, auditable decision-and-optimization platform. The market side is our proving ground. The infrastructure side is the scale opportunity.")
    }</p>
  </div>
</div>
</body>
</html>
"""

for html_out in HTML_OUTS:
    html_out.parent.mkdir(parents=True, exist_ok=True)
    html_out.write_text(html_doc, encoding="utf-8")

print("WROTE:")
print(JSON_OUT)
print(TXT_OUT)
for html_out in HTML_OUTS:
    print(html_out)
print("")
print("READINESS:", readiness)
print("SEED ASK:", money(investor_ask["seed_raise_usd_low"]), "to", money(investor_ask["seed_raise_usd_high"]))
print("GOV / PILOT ASK:", money(investor_ask["gov_pilot_usd_low"]), "to", money(investor_ask["gov_pilot_usd_high"]))
print("")
print("OPEN THESE:")
print(TXT_OUT)
for html_out in HTML_OUTS:
    print(html_out)