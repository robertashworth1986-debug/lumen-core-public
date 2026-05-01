yesaimport json, html
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT  = ROOT / "out"
DASH = Path(r"C:\LumaTrader\dashboard")
DASH.mkdir(parents=True, exist_ok=True)

summary_path     = OUT / "full_beast_summary.json"
registry_path    = OUT / "full_beast_registry.json"
leaderboard_path = OUT / "full_beast_leaderboard.csv"
proof_path       = OUT / "full_beast_proof.json"
scan_path        = OUT / "full_beast_dataset_scan.csv"

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

def fnum(x, nd=2):
    try:
        return f"{float(x):,.{nd}f}"
    except Exception:
        return "0.00"

def fint(x):
    try:
        return f"{int(float(x)):,}"
    except Exception:
        return "0"

def fpct(x, nd=2):
    try:
        return f"{float(x):,.{nd}f}%"
    except Exception:
        return "0.00%"

summary  = read_json(summary_path, {})
registry = read_json(registry_path, {})
proof    = read_json(proof_path, {})
lb       = read_csv(leaderboard_path)
scan     = read_csv(scan_path)

# -------------------------------------------------
# Normalize leaderboard
# -------------------------------------------------
if not lb.empty:
    num_cols = [
        "test_sharpe","test_vs_baseline","test_max_dd",
        "test_cagr","test_calmar","test_win_rate",
        "institutional_score"
    ]
    for c in num_cols:
        if c in lb.columns:
            lb[c] = pd.to_numeric(lb[c], errors="coerce")

    for c in ["test_sharpe","test_vs_baseline","test_max_dd","test_cagr","test_calmar","test_win_rate"]:
        if c in lb.columns:
            lb[c] = lb[c].fillna(0.0)

    # hard sanity clamps so no absurd investor score explosions
    if "test_sharpe" in lb.columns:
        lb["test_sharpe_clean"] = lb["test_sharpe"].clip(-10, 10)
    else:
        lb["test_sharpe_clean"] = 0.0

    if "test_vs_baseline" in lb.columns:
        lb["test_vs_baseline_clean"] = lb["test_vs_baseline"].clip(-200, 200)
    else:
        lb["test_vs_baseline_clean"] = 0.0

    if "test_max_dd" in lb.columns:
        lb["test_max_dd_clean"] = lb["test_max_dd"].abs().clip(0, 1.0)
    else:
        lb["test_max_dd_clean"] = 0.0

    if "test_cagr" in lb.columns:
        lb["test_cagr_clean"] = lb["test_cagr"].clip(-5, 5)
    else:
        lb["test_cagr_clean"] = 0.0

    if "test_calmar" in lb.columns:
        lb["test_calmar_clean"] = lb["test_calmar"].clip(-20, 20)
    else:
        lb["test_calmar_clean"] = 0.0

    if "test_win_rate" in lb.columns:
        lb["test_win_rate_clean"] = lb["test_win_rate"].clip(0, 1)
    else:
        lb["test_win_rate_clean"] = 0.0

    # credibility definition
    lb["credible"] = (
        (lb["test_sharpe_clean"] > 0) &
        (lb["test_vs_baseline_clean"] > 0) &
        (lb["test_max_dd_clean"] < 0.60)
    )

    # cleaned investor score
    lb["investor_score_clean"] = (
        lb["test_sharpe_clean"] * 4.0
        + lb["test_vs_baseline_clean"] * 0.15
        + lb["test_calmar_clean"] * 1.5
        + lb["test_cagr_clean"] * 2.0
        + lb["test_win_rate_clean"] * 8.0
        - lb["test_max_dd_clean"] * 12.0
    )

    dedupe_cols = [c for c in ["file","flow","algo","strategy","metric_profile"] if c in lb.columns]
    if dedupe_cols:
        lb = lb.sort_values("investor_score_clean", ascending=False)
        lb = lb.drop_duplicates(subset=dedupe_cols, keep="first").reset_index(drop=True)

credible_lb = lb[lb["credible"]].copy() if not lb.empty else pd.DataFrame()
noncredible_lb = lb[~lb["credible"]].copy() if not lb.empty else pd.DataFrame()

best = credible_lb.sort_values("investor_score_clean", ascending=False).head(1) if not credible_lb.empty else pd.DataFrame()
worst = lb.sort_values("investor_score_clean", ascending=True).head(1) if not lb.empty else pd.DataFrame()
top10_clean = credible_lb.sort_values("investor_score_clean", ascending=False).head(10) if not credible_lb.empty else pd.DataFrame()

clean_csv = OUT / "credible_top10.csv"
try:
    top10_clean.to_csv(clean_csv, index=False)
except Exception:
    pass

def row_to_dict(df):
    if df is None or df.empty:
        return {}
    return df.iloc[0].to_dict()

best_row = row_to_dict(best)
worst_row = row_to_dict(worst)

files_scanned = int(summary.get("files_scanned", 0) or 0)
usable_files = int(summary.get("usable_files", 0) or 0)
expected_full_candidates = int(summary.get("expected_full_candidates", 0) or 0)
actual_scored = len(lb)
credible_count = len(credible_lb)
noncredible_count = len(noncredible_lb)

completion_pct = 0.0
if expected_full_candidates > 0:
    completion_pct = 100.0 * actual_scored / expected_full_candidates

credible_pct = 0.0
if actual_scored > 0:
    credible_pct = 100.0 * credible_count / actual_scored

flowforms = registry.get("flowforms", [])
algos = registry.get("algos", [])
strategies = registry.get("strategies", [])
metric_profiles = registry.get("metric_profiles", [])

usable_count = 0
skipped_count = 0
if not scan.empty and "status" in scan.columns:
    s = scan["status"].astype(str).str.lower()
    usable_count = int((s == "usable").sum())
    skipped_count = int((s == "skipped").sum())

proof_html = ""
for k, v in proof.items():
    proof_html += f"<tr><td>{esc(k)}</td><td class='mono'>{esc(v)}</td></tr>"

def metric_card(title, value, sub=""):
    return f"""
    <div class="card metric">
      <div class="kicker">{esc(title)}</div>
      <div class="value">{esc(value)}</div>
      <div class="sub">{esc(sub)}</div>
    </div>
    """

def simple_bar(value, vmax, color):
    try:
        value = abs(float(value))
        vmax = max(abs(float(vmax)), 1e-9)
        width = max(0, min(100, 100.0 * value / vmax))
    except Exception:
        width = 0
    return f"<div class='bar-wrap'><div class='bar-fill' style='width:{width:.2f}%; background:{color};'></div></div>"

def leader_card(row):
    if not row:
        return "<div class='card'>No row available.</div>"
    filev = Path(str(row.get("file","n/a"))).name
    flow = row.get("flow","n/a")
    algo = row.get("algo","n/a")
    strategy = row.get("strategy","n/a")
    profile = row.get("metric_profile","n/a")
    score = row.get("investor_score_clean",0)
    sh = row.get("test_sharpe_clean", row.get("test_sharpe",0))
    vsb = row.get("test_vs_baseline_clean", row.get("test_vs_baseline",0))
    dd = row.get("test_max_dd_clean", abs(float(row.get("test_max_dd",0) or 0)))
    return f"""
    <div class="card leader">
      <div class="leader-title">{esc(filev)}</div>
      <div class="leader-sub">{esc(flow)} / {esc(algo)} / {esc(strategy)} / {esc(profile)}</div>
      <div class="mini-metric">Investor score: {fnum(score)}</div>
      {simple_bar(score, 50, "linear-gradient(90deg,#7c3aed,#22d3ee)")}
      <div class="mini-metric">Sharpe: {fnum(sh)}</div>
      {simple_bar(sh, 5, "linear-gradient(90deg,#22c55e,#86efac)")}
      <div class="mini-metric">Vs Baseline: {fnum(vsb)}</div>
      {simple_bar(vsb, 50, "linear-gradient(90deg,#f59e0b,#fde68a)")}
      <div class="mini-metric">Abs Drawdown: {fnum(dd)}</div>
      {simple_bar(dd, 1.0, "linear-gradient(90deg,#ef4444,#fca5a5)")}
    </div>
    """

top_rows_html = ""
if not top10_clean.empty:
    for _, row in top10_clean.iterrows():
        top_rows_html += f"""
        <tr>
          <td>{esc(Path(str(row.get("file",""))).name)}</td>
          <td>{esc(row.get("flow",""))}</td>
          <td>{esc(row.get("algo",""))}</td>
          <td>{esc(row.get("strategy",""))}</td>
          <td>{esc(row.get("metric_profile",""))}</td>
          <td>{fnum(row.get("test_sharpe_clean", row.get("test_sharpe",0)))}</td>
          <td>{fnum(row.get("test_vs_baseline_clean", row.get("test_vs_baseline",0)))}</td>
          <td>{fnum(row.get("test_max_dd_clean", row.get("test_max_dd",0)))}</td>
          <td>{fnum(row.get("investor_score_clean",0))}</td>
        </tr>
        """

scan_html = ""
if not scan.empty:
    wanted = [c for c in ["file","status","value_col","time_col","ret_len"] if c in scan.columns]
    for _, row in scan[wanted].head(24).iterrows():
        scan_html += f"""
        <tr>
          <td>{esc(Path(str(row.get("file",""))).name)}</td>
          <td>{esc(row.get("status",""))}</td>
          <td>{esc(row.get("value_col",""))}</td>
          <td>{esc(row.get("time_col",""))}</td>
          <td>{esc(row.get("ret_len",""))}</td>
        </tr>
        """

def list_block(title, items):
    lis = "".join(f"<li>{esc(x)}</li>" for x in list(items)[:40])
    return f"""
    <div class="card">
      <div class="section-title">{esc(title)}</div>
      <ul class="clean-list">{lis}</ul>
    </div>
    """

html_doc = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>LumenCore — Credibility Dashboard</title>
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
.wrap {{ max-width:1650px; margin:0 auto; padding:24px; }}
.hero {{
  border:1px solid var(--line);
  background: linear-gradient(135deg, rgba(12,24,48,.95), rgba(9,21,40,.95));
  border-radius:20px;
  padding:28px;
  box-shadow: 0 0 40px rgba(34,211,238,.08);
}}
.hero h1 {{ margin:0 0 8px 0; font-size:40px; }}
.hero p {{ margin:0; color:var(--muted); }}
.grid4 {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:16px; margin-top:18px; }}
.grid3 {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; margin-top:16px; }}
.grid2 {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; margin-top:16px; }}
.card {{
  background: linear-gradient(180deg, rgba(12,24,48,.92), rgba(8,18,36,.92));
  border:1px solid var(--line); border-radius:18px; padding:18px;
}}
.metric .kicker {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:1px; }}
.metric .value {{ font-size:34px; font-weight:800; margin-top:8px; }}
.metric .sub {{ color:var(--muted); margin-top:8px; font-size:13px; }}
.section-title {{ font-size:22px; font-weight:800; margin-bottom:12px; }}
.leader-title {{ font-size:18px; font-weight:800; }}
.leader-sub {{ color:var(--muted); font-size:12px; margin:6px 0 12px 0; line-height:1.45; }}
.mini-metric {{ font-size:13px; }}
.bar-wrap {{ width:100%; height:10px; background:rgba(255,255,255,.06); border-radius:999px; overflow:hidden; margin:8px 0 12px 0; }}
.bar-fill {{ height:100%; border-radius:999px; }}
.clean-list {{ margin:0; padding-left:18px; columns:2; }}
.clean-list li {{ margin:0 0 8px 0; font-size:13px; }}
table {{ width:100%; border-collapse:collapse; }}
th, td {{ padding:10px 8px; border-bottom:1px solid rgba(255,255,255,.08); text-align:left; font-size:13px; vertical-align:top; }}
th {{ color:#bcd0f4; font-size:12px; text-transform:uppercase; }}
.mono {{ font-family: ui-monospace, Consolas, monospace; font-size:12px; word-break:break-all; }}
.callout {{ line-height:1.6; font-size:16px; }}
.good {{ color:#22c55e; }}
.warn {{ color:#f59e0b; }}
.bad {{ color:#ef4444; }}
.footer {{ margin-top:18px; color:var(--muted); font-size:12px; }}
@media (max-width:1200px) {{ .grid4,.grid3 {{ grid-template-columns:1fr 1fr; }} }}
@media (max-width:800px) {{
  .grid4,.grid3,.grid2 {{ grid-template-columns:1fr; }}
  .clean-list {{ columns:1; }}
  .hero h1 {{ font-size:30px; }}
}}
</style>
</head>
<body>
<div class="wrap">

<div class="hero">
  <h1>⚡ LumenCore — Credibility Dashboard</h1>
  <p>Not just breadth. This one separates credible candidates from junk and surfaces the best positive champion.</p>
  <div class="grid4">
    {metric_card("Files scanned", fint(files_scanned), f"Usable: {fint(usable_files)}")}
    {metric_card("Expected candidates", fint(expected_full_candidates), f"Completion: {fpct(completion_pct)}")}
    {metric_card("Credible candidates", fint(credible_count), f"Credible rate: {fpct(credible_pct)}")}
    {metric_card("Non-credible candidates", fint(noncredible_count), "Need ranking / signal improvement")}
  </div>
</div>

<div class="grid4">
  {metric_card("Flowforms", fint(len(flowforms)), "Active registry")}
  {metric_card("Algorithms", fint(len(algos)), "Active registry")}
  {metric_card("Strategies", fint(len(strategies)), "Active registry")}
  {metric_card("Metric profiles", fint(len(metric_profiles)), "Active registry")}
</div>

<div class="grid3">
  <div class="card">
    <div class="section-title">Best credible champion</div>
    {leader_card(best_row)}
  </div>

  <div class="card">
    <div class="section-title">Worst failure case</div>
    {leader_card(worst_row)}
  </div>

  <div class="card">
    <div class="section-title">Investor readout</div>
    <div class="callout">
      <div><span class="good"><b>Working:</b></span> universe breadth, registry, proof, scan visibility, cleaned ranking, duplicate suppression.</div>
      <div style="margin-top:10px;"><span class="warn"><b>Still needed:</b></span> higher credible-rate, stronger positive champions, and forward-trade audit trail.</div>
      <div style="margin-top:10px;"><span class="bad"><b>Do not pitch yet:</b></span> negative-Sharpe rows as real alpha. Pitch the architecture and validation discipline, not fake certainty.</div>
    </div>
  </div>
</div>

<div class="grid2">
  <div class="card">
    <div class="section-title">Registry coverage</div>
    <div class="grid2" style="margin-top:0;">
      {list_block("Flowforms", flowforms)}
      {list_block("Algorithms", algos)}
      {list_block("Strategies", strategies)}
      {list_block("Metric profiles", metric_profiles)}
    </div>
  </div>

  <div class="card">
    <div class="section-title">Scan health</div>
    <table>
      <tbody>
        <tr><td>Usable files</td><td>{fint(usable_count)}</td></tr>
        <tr><td>Skipped files</td><td>{fint(skipped_count)}</td></tr>
        <tr><td>Scored rows after cleanup</td><td>{fint(actual_scored)}</td></tr>
        <tr><td>Credible rows</td><td>{fint(credible_count)}</td></tr>
      </tbody>
    </table>
    <div class="section-title" style="margin-top:16px;">Proof / integrity</div>
    <table><tbody>{proof_html if proof_html else "<tr><td colspan='2'>No proof file found.</td></tr>"}</tbody></table>
  </div>
</div>

<div class="card">
  <div class="section-title">Top 10 credible leaderboard</div>
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
        <th>Investor Score</th>
      </tr>
    </thead>
    <tbody>
      {top_rows_html if top_rows_html else "<tr><td colspan='9'>No credible rows yet. That is the real truth signal.</td></tr>"}
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
      {scan_html if scan_html else "<tr><td colspan='5'>No scan rows found.</td></tr>"}
    </tbody>
  </table>
</div>

<div class="footer">
  Wrote clean leaderboard to: {esc(str(clean_csv))}
</div>

</div>
</body>
</html>
"""

out_html = DASH / "credibility_dashboard.html"
out_html.write_text(html_doc, encoding="utf-8")
print(str(out_html))
