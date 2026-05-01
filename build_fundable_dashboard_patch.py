import os, json, html
from pathlib import Path
import pandas as pd

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT  = ROOT / "out"
DASH = Path(r"C:\LumaTrader\dashboard")
DASH.mkdir(parents=True, exist_ok=True)

summary_path    = OUT / "full_beast_summary.json"
registry_path   = OUT / "full_beast_registry.json"
leaderboard_path= OUT / "full_beast_leaderboard.csv"
top10_path      = OUT / "full_beast_top10.csv"
proof_path      = OUT / "full_beast_proof.json"
scan_path       = OUT / "full_beast_dataset_scan.csv"

def read_json(path, default=None):
    if default is None:
        default = {}
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def read_csv(path):
    try:
        if path.exists():
            return pd.read_csv(path)
    except Exception:
        pass
    return pd.DataFrame()

def esc(x):
    return html.escape(str(x))

def fmt_num(x, nd=2):
    try:
      import ast
      # Only try to parse as list if it's a string and looks like a list
      if isinstance(x, str) and x.strip().startswith('[') and x.strip().endswith(']'):
        try:
          arr = ast.literal_eval(x)
          if isinstance(arr, (list, tuple)) and arr:
            x = arr[-1]
        except Exception:
          pass
      elif isinstance(x, (list, tuple)) and x:
        x = x[-1]
      return f"{float(x):,.{nd}f}"
    except Exception:
      return "0.00"

def fmt_int(x):
    try:
        return f"{int(x):,}"
    except Exception:
        return "0"

def fmt_pct(x, nd=2):
    try:
        return f"{float(x):,.{nd}f}%"
    except Exception:
        return "0.00%"

summary = read_json(summary_path, {})
registry = read_json(registry_path, {})
proof = read_json(proof_path, {})

leaderboard = read_csv(leaderboard_path)
top10 = read_csv(top10_path)
scan = read_csv(scan_path)

files_scanned = int(summary.get("files_scanned", 0) or 0)
usable_files = int(summary.get("usable_files", 0) or 0)
flowforms_count = int(summary.get("flowforms_count", len(registry.get("flowforms", []))) or 0)
algos_count = int(summary.get("algos_count", len(registry.get("algos", []))) or 0)
strategies_count = int(summary.get("strategies_count", len(registry.get("strategies", []))) or 0)
metric_profiles_count = int(summary.get("metric_profiles_count", len(registry.get("metric_profiles", []))) or 0)
expected_full_candidates = int(summary.get("expected_full_candidates", 0) or 0)
actual_candidates_scored = int(summary.get("actual_candidates_scored", len(leaderboard)) or 0)

top_flow = summary.get("top_flow", "n/a")
top_algo = summary.get("top_algo", "n/a")
top_strategy = summary.get("top_strategy", "n/a")
top_metric_profile = summary.get("top_metric_profile", "n/a")
top_file = summary.get("top_file", "n/a")
top_test_sharpe = float(summary.get("top_test_sharpe", 0.0) or 0.0)
top_test_vs_baseline = float(summary.get("top_test_vs_baseline", 0.0) or 0.0)
top_institutional_score = float(summary.get("top_institutional_score", 0.0) or 0.0)

completion_pct = 0.0
if expected_full_candidates > 0:
    completion_pct = 100.0 * actual_candidates_scored / expected_full_candidates

def metric_card(title, value, sub=""):
    return f"""
    <div class='card metric'>
      <div class='kicker'>{esc(title)}</div>
      <div class='value'>{esc(value)}</div>
      <div class='sub'>{esc(sub)}</div>
    </div>
    """

def list_block(title, items):
    lis = "".join(f"<li>{esc(x)}</li>" for x in list(items)[:40])
    return f"""
    <div class='card'>
      <div class='section-title'>{esc(title)}</div>
      <ul class='clean-list'>{lis}</ul>
    </div>
    """

def simple_bar(value, vmax, color):
    try:
        value = float(value)
        vmax = float(vmax)
    except Exception:
        value = 0.0
        vmax = 1.0
    width = 0 if vmax <= 0 else max(0, min(100, 100.0 * value / vmax))
    return f"<div class='bar-wrap'><div class='bar-fill' style='width:{width:.2f}%; background:{color};'></div></div>"

score_max = 1.0
sh_max = 1.0
vsb_max = 1.0
dd_max = 1.0
if not leaderboard.empty:
    if "institutional_score" in leaderboard.columns:
        s = pd.to_numeric(leaderboard["institutional_score"], errors="coerce").dropna()
        if len(s): score_max = max(float(s.max()), 1.0)
    if "test_sharpe" in leaderboard.columns:
        s = pd.to_numeric(leaderboard["test_sharpe"], errors="coerce").dropna()
        if len(s): sh_max = max(float(s.abs().max()), 1.0)
    if "test_vs_baseline" in leaderboard.columns:
        s = pd.to_numeric(leaderboard["test_vs_baseline"], errors="coerce").dropna()
        if len(s): vsb_max = max(float(s.abs().max()), 1.0)
    if "test_max_dd" in leaderboard.columns:
        s = pd.to_numeric(leaderboard["test_max_dd"], errors="coerce").dropna()
        if len(s): dd_max = max(float(s.abs().max()), 1.0)

leader_cards = ""
if not top10.empty:
    for _, row in top10.head(5).iterrows():
        filev = Path(str(row.get("file",""))).name
        flow = row.get("flow","")
        algo = row.get("algo","")
        strat = row.get("strategy","")
        prof = row.get("metric_profile","")
        score = float(pd.to_numeric(pd.Series([row.get("institutional_score",0)]), errors="coerce").fillna(0.0).iloc[0])
        sh = float(pd.to_numeric(pd.Series([row.get("test_sharpe",0)]), errors="coerce").fillna(0.0).iloc[0])
        vsb = float(pd.to_numeric(pd.Series([row.get("test_vs_baseline",0)]), errors="coerce").fillna(0.0).iloc[0])
        dd = abs(float(pd.to_numeric(pd.Series([row.get("test_max_dd",0)]), errors="coerce").fillna(0.0).iloc[0]))
        leader_cards += f"""
        <div class='card leader'>
          <div class='leader-title'>{esc(filev)}</div>
          <div class='leader-sub'>{esc(flow)} / {esc(algo)} / {esc(strat)} / {esc(prof)}</div>
          <div class='mini-metric'>Score: {fmt_num(score)}</div>
          {simple_bar(score, score_max, "linear-gradient(90deg,#7c3aed,#22d3ee)")}
          <div class='mini-metric'>Sharpe: {fmt_num(sh)}</div>
          {simple_bar(abs(sh), sh_max, "linear-gradient(90deg,#22c55e,#86efac)")}
          <div class='mini-metric'>Vs Baseline: {fmt_num(vsb)}</div>
          {simple_bar(abs(vsb), vsb_max, "linear-gradient(90deg,#f59e0b,#fde68a)")}
          <div class='mini-metric'>Abs Drawdown: {fmt_num(dd)}</div>
          {simple_bar(dd, dd_max, "linear-gradient(90deg,#ef4444,#fca5a5)")}
        </div>
        """

top_rows_html = ""
if not top10.empty:
    wanted = [c for c in ["file","flow","algo","strategy","metric_profile","test_sharpe","test_vs_baseline","test_max_dd","institutional_score"] if c in top10.columns]
    for _, row in top10[wanted].head(10).iterrows():
        top_rows_html += f"""
        <tr>
          <td>{esc(Path(str(row.get('file',''))).name)}</td>
          <td>{esc(row.get('flow',''))}</td>
          <td>{esc(row.get('algo',''))}</td>
          <td>{esc(row.get('strategy',''))}</td>
          <td>{esc(row.get('metric_profile',''))}</td>
          <td>{fmt_num(row.get('test_sharpe',0))}</td>
          <td>{fmt_num(row.get('test_vs_baseline',0))}</td>
          <td>{fmt_num(row.get('test_max_dd',0))}</td>
          <td>{fmt_num(row.get('institutional_score',0))}</td>
        </tr>
        """

scan_html = ""
if not scan.empty:
    wanted = [c for c in ["file","status","value_col","time_col","ret_len"] if c in scan.columns]
    for _, row in scan[wanted].head(25).iterrows():
        scan_html += f"""
        <tr>
          <td>{esc(Path(str(row.get('file',''))).name)}</td>
          <td>{esc(row.get('status',''))}</td>
          <td>{esc(row.get('value_col',''))}</td>
          <td>{esc(row.get('time_col',''))}</td>
          <td>{esc(row.get('ret_len',''))}</td>
        </tr>
        """

proof_html = ""
for k, v in proof.items():
    proof_html += f"<tr><td>{esc(k)}</td><td class='mono'>{esc(v)}</td></tr>"

flowforms = registry.get("flowforms", [])
algos = registry.get("algos", [])
strategies = registry.get("strategies", [])
metric_profiles = registry.get("metric_profiles", [])

html_doc = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>LumenCore Fundable Dashboard</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
:root {{
  --bg:#07111f;
  --panel:#0c1830;
  --line:#21365f;
  --text:#e6eefc;
  --muted:#96a7c7;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0;
  background:
    radial-gradient(circle at 15% 20%, rgba(34,211,238,.12), transparent 35%),
    radial-gradient(circle at 85% 10%, rgba(139,92,246,.10), transparent 30%),
    linear-gradient(180deg, #06101d 0%, #091528 100%);
  color:var(--text);
  font-family: Inter, Segoe UI, Arial, sans-serif;
}}
.wrap {{
  max-width: 1600px;
  margin: 0 auto;
  padding: 24px;
}}
.hero {{
  border:1px solid var(--line);
  background: linear-gradient(135deg, rgba(12,24,48,.95), rgba(9,21,40,.95));
  border-radius:20px;
  padding:28px;
  box-shadow: 0 0 40px rgba(34,211,238,.08);
}}
.hero h1 {{
  margin:0 0 8px 0;
  font-size:42px;
}}
.hero p {{
  margin:0;
  color:var(--muted);
}}
.grid4 {{
  display:grid;
  grid-template-columns: repeat(4, minmax(0,1fr));
  gap:16px;
  margin-top:18px;
}}
.grid2 {{
  display:grid;
  grid-template-columns: repeat(2, minmax(0,1fr));
  gap:16px;
  margin-top:16px;
}}
.card {{
  background: linear-gradient(180deg, rgba(12,24,48,.92), rgba(8,18,36,.92));
  border:1px solid var(--line);
  border-radius:18px;
  padding:18px;
}}
.metric .kicker {{
  color:var(--muted);
  font-size:12px;
  text-transform:uppercase;
  letter-spacing:1px;
}}
.metric .value {{
  font-size:34px;
  font-weight:800;
  margin-top:8px;
}}
.metric .sub {{
  color:var(--muted);
  margin-top:8px;
  font-size:13px;
}}
.section-title {{
  font-size:22px;
  font-weight:800;
  margin-bottom:12px;
}}
.badge {{
  display:inline-block;
  padding:6px 10px;
  border-radius:999px;
  background:rgba(34,211,238,.12);
  border:1px solid rgba(34,211,238,.25);
  color:#9be7f3;
  font-size:12px;
  margin-right:8px;
  margin-bottom:8px;
}}
table {{
  width:100%;
  border-collapse:collapse;
}}
th, td {{
  padding:10px 8px;
  border-bottom:1px solid rgba(255,255,255,.08);
  text-align:left;
  font-size:13px;
  vertical-align:top;
}}
th {{
  color:#bcd0f4;
  font-size:12px;
  text-transform:uppercase;
}}
.bar-wrap {{
  width:100%;
  height:10px;
  background:rgba(255,255,255,.06);
  border-radius:999px;
  overflow:hidden;
  margin:8px 0 12px 0;
}}
.bar-fill {{
  height:100%;
  border-radius:999px;
}}
.leader-title {{
  font-size:18px;
  font-weight:800;
}}
.leader-sub {{
  color:var(--muted);
  font-size:12px;
  margin:6px 0 12px 0;
  line-height:1.45;
}}
.mini-metric {{
  font-size:13px;
}}
.clean-list {{
  margin:0;
  padding-left:18px;
  columns:2;
}}
.clean-list li {{
  margin:0 0 8px 0;
  font-size:13px;
}}
.mono {{
  font-family: ui-monospace, Consolas, monospace;
  font-size:12px;
  word-break:break-all;
}}
.footer {{
  margin-top:18px;
  color:var(--muted);
  font-size:12px;
}}
@media (max-width: 1200px) {{
  .grid4 {{ grid-template-columns: 1fr 1fr; }}
}}
@media (max-width: 800px) {{
  .grid4, .grid2 {{ grid-template-columns: 1fr; }}
  .clean-list {{ columns:1; }}
  .hero h1 {{ font-size:30px; }}
}}
</style>
</head>
<body>
<div class="wrap">

  <div class="hero">
    <h1>⚡ LumenCore — Fundable Dashboard</h1>
    <p>Champion discovery, breadth, proof, and investor-facing validation.</p>

    <div style="margin-top:14px;">
      <span class="badge">Top flow: {esc(top_flow)}</span>
      <span class="badge">Top algo: {esc(top_algo)}</span>
      <span class="badge">Top strategy: {esc(top_strategy)}</span>
      <span class="badge">Profile: {esc(top_metric_profile)}</span>
    </div>

    <div class="grid4">
      {metric_card("Files scanned", fmt_int(files_scanned), f"Usable: {fmt_int(usable_files)}")}
      {metric_card("Expected candidates", fmt_int(expected_full_candidates), "Full search breadth")}
      {metric_card("Actual scored", fmt_int(actual_candidates_scored), f"Completion: {fmt_pct(completion_pct)}")}
      {metric_card("Top institutional score", fmt_num(top_institutional_score), f"Sharpe: {fmt_num(top_test_sharpe)} | Vs baseline: {fmt_num(top_test_vs_baseline)}")}
    </div>
  </div>

  <div class="grid4">
    {metric_card("Flowforms", fmt_int(flowforms_count), "Geometry universe")}
    {metric_card("Algorithms", fmt_int(algos_count), "Transform universe")}
    {metric_card("Strategies", fmt_int(strategies_count), "Decision universe")}
    {metric_card("Metric profiles", fmt_int(metric_profiles_count), "Scoring universe")}
  </div>

  <div class="grid2">
    <div class="card">
      <div class="section-title">Champion block</div>
      <p><b>Top file:</b> {esc(Path(str(top_file)).name if str(top_file) != "n/a" else "n/a")}</p>
      <p><b>Top stack:</b> {esc(top_flow)} / {esc(top_algo)} / {esc(top_strategy)} / {esc(top_metric_profile)}</p>
      <p><b>Test Sharpe:</b> {fmt_num(top_test_sharpe)}</p>
      <p><b>Vs baseline:</b> {fmt_num(top_test_vs_baseline)}</p>
      <p><b>Institutional score:</b> {fmt_num(top_institutional_score)}</p>
    </div>

    <div class="card">
      <div class="section-title">Proof / integrity</div>
      <table>
        <tbody>
          {proof_html if proof_html else "<tr><td colspan='2'>No proof file found.</td></tr>"}
        </tbody>
      </table>
    </div>
  </div>

  <div class="grid2">
    <div class="card">
      <div class="section-title">Top 5 leaders</div>
      {leader_cards if leader_cards else "<div>No top10 file found yet.</div>"}
    </div>

    <div class="card">
      <div class="section-title">Active registry</div>
      <div class="grid2" style="margin-top:0;">
        {list_block("Flowforms", flowforms)}
        {list_block("Algorithms", algos)}
        {list_block("Strategies", strategies)}
        {list_block("Metric profiles", metric_profiles)}
      </div>
    </div>
  </div>

  <div class="card">
    <div class="section-title">Top 10 leaderboard</div>
    <table>
      <thead>
        <tr>
          <th>File</th>
          <th>Flow</th>
          <th>Algo</th>
          <th>Strategy</th>
          <th>Profile</th>
          <th>Sharpe</th>
          <th>Vs Baseline</th>
          <th>Max DD</th>
          <th>Score</th>
        </tr>
      </thead>
      <tbody>
        {top_rows_html if top_rows_html else "<tr><td colspan='9'>No leaderboard rows found.</td></tr>"}
      </tbody>
    </table>
  </div>

  <div class="card">
    <div class="section-title">Dataset scan</div>
    <table>
      <thead>
        <tr>
          <th>File</th>
          <th>Status</th>
          <th>Value Col</th>
          <th>Time Col</th>
          <th>Ret Len</th>
        </tr>
      </thead>
      <tbody>
        {scan_html if scan_html else "<tr><td colspan='5'>No dataset scan found.</td></tr>"}
      </tbody>
    </table>
  </div>

  <div class="footer">
    Source files:
    {esc(str(summary_path))} |
    {esc(str(registry_path))} |
    {esc(str(leaderboard_path))} |
    {esc(str(top10_path))}
  </div>

</div>
</body>
</html>
"""

out_html = DASH / "fundable_dashboard.html"
out_html.write_text(html_doc, encoding="utf-8")
print(str(out_html))
