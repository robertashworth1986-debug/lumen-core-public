from pathlib import Path
import json
import pandas as pd

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out" / "execution"
DASH = ROOT / "dashboard"

DASH.mkdir(parents=True, exist_ok=True)

leaderboard_path = OUT / "institutional_leaderboard.csv"
top10_path = OUT / "institutional_top10.csv"
summary_path = OUT / "institutional_summary.json"
selection_path = OUT / "institutional_live_selection.json"
evidence_path = OUT / "institutional_evidence.json"
equity_path = OUT / "validation_equity_curve.csv"
dash_path = DASH / "validation_front_end.html"


def read_csv_safe(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin1"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            pass
    return pd.DataFrame()


def read_json_safe(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def esc(x) -> str:
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


leader = read_csv_safe(leaderboard_path)
top10 = read_csv_safe(top10_path)
summary = read_json_safe(summary_path)
selection = read_json_safe(selection_path)
evidence = read_json_safe(evidence_path)

if top10.empty and not leader.empty:
    top10 = leader.head(10).copy()

num_cols = [
    "train_sharpe", "test_sharpe", "train_max_dd", "test_max_dd", "train_cagr", "test_cagr",
    "train_calmar", "test_calmar", "test_win_rate", "test_expectancy", "test_vol", "test_final",
    "baseline_final", "test_vs_baseline", "stability", "institutional_score"
]
for df in (leader, top10):
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

best = {}
if not top10.empty:
    best = top10.iloc[0].to_dict()
elif not leader.empty:
    best = leader.iloc[0].to_dict()
elif selection:
    best = selection.copy()

best_flow = best.get("flow", selection.get("flow", ""))
best_strategy = best.get("strategy", selection.get("strategy", ""))
best_sharpe = float(best.get("test_sharpe", summary.get("top_test_sharpe", 0.0)) or 0.0)
best_vs = float(best.get("test_vs_baseline", summary.get("top_test_vs_baseline", 0.0)) or 0.0)
best_inst = float(best.get("institutional_score", summary.get("top_institutional_score", 0.0)) or 0.0)
best_file = best.get("file", summary.get("top_file", ""))

curve_rows = []
if not top10.empty:
    for i, (_, r) in enumerate(top10.head(10).iterrows(), start=1):
        strategy_final = float(r.get("test_final", 0.0) or 0.0)
        baseline_final = float(r.get("baseline_final", 0.0) or 0.0)
        curve_rows.append({
            "rank": i,
            "flow": r.get("flow", ""),
            "strategy": r.get("strategy", ""),
            "strategy_final": strategy_final,
            "baseline_final": baseline_final,
            "spread": strategy_final - baseline_final,
        })

curve_df = pd.DataFrame(curve_rows)
curve_df.to_csv(equity_path, index=False)

candidate_count = int(len(leader)) if not leader.empty else 0
avg_top10_sharpe = float(top10["test_sharpe"].dropna().mean()) if ("test_sharpe" in top10.columns and not top10.empty) else best_sharpe
avg_top10_vs = float(top10["test_vs_baseline"].dropna().mean()) if ("test_vs_baseline" in top10.columns and not top10.empty) else best_vs

wf_sharpe = float((((evidence.get("walk_forward") or {}).get("wf_sharpe")) or 0.0))
mc_mean = float((((evidence.get("monte_carlo") or {}).get("mc_sharpe_mean")) or 0.0))
mc_p05 = float((((evidence.get("monte_carlo") or {}).get("mc_sharpe_p05")) or 0.0))
p_gt_1 = float((((evidence.get("monte_carlo") or {}).get("p_sharpe_gt_1")) or 0.0))

PASS_WF_SHARPE = 1.20
PASS_MC_P_GT_1 = 0.80
PASS_MC_P05 = 0.25

validation_pass = (
    wf_sharpe >= PASS_WF_SHARPE
    and p_gt_1 >= PASS_MC_P_GT_1
    and mc_p05 >= PASS_MC_P05
)
badge_text = "PASS" if validation_pass else "FAIL"
badge_class = "pass" if validation_pass else "fail"

top10_view = top10.copy()
keep_cols = [c for c in [
    "flow", "strategy", "test_sharpe", "test_max_dd", "test_win_rate", "test_expectancy",
    "test_final", "baseline_final", "test_vs_baseline", "institutional_score", "file"
] if c in top10_view.columns]
if keep_cols:
    top10_view = top10_view[keep_cols]

top10_html = "<p>No top 10 rows found.</p>" if top10_view.empty else top10_view.to_html(index=False, border=0, classes="tbl")
curve_html = "<p>No curve rows found.</p>" if curve_df.empty else curve_df.to_html(index=False, border=0, classes="tbl")

proof_candidates = [
    summary_path,
    selection_path,
    evidence_path,
    leaderboard_path,
    top10_path,
    equity_path,
]
proof_items = [f"<li>{esc(str(p))}</li>" for p in proof_candidates if p.exists()]
proof_html = "<ul>" + "".join(proof_items) + "</ul>"

champion_payload = {
    "flow": best_flow,
    "strategy": best_strategy,
    "test_sharpe": best_sharpe,
    "test_vs_baseline": best_vs,
    "institutional_score": best_inst,
    "file": best_file,
    "selection": selection,
}

html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>LumenCore Validation Front End</title>
<style>
body {{
  margin: 0;
  padding: 24px;
  background: #0b1120;
  color: #eef4ff;
  font-family: Arial, sans-serif;
}}
h1,h2,h3 {{ margin: 0 0 12px 0; }}
p {{ line-height: 1.45; }}
.grid {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}}
.card {{
  background: #111b31;
  border: 1px solid #24385d;
  border-radius: 12px;
  padding: 14px;
}}
.label {{
  color: #8fa6cd;
  font-size: 12px;
  text-transform: uppercase;
  margin-bottom: 8px;
}}
.val {{
  font-size: 26px;
  font-weight: 700;
}}
.section {{
  background: #111b31;
  border: 1px solid #24385d;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 18px;
}}
.tbl {{
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}}
.tbl th, .tbl td {{
  border-bottom: 1px solid #25395f;
  padding: 8px 6px;
  text-align: left;
}}
.small {{ color: #9cb0d1; }}
.hero {{
  display:grid;
  grid-template-columns: 1.2fr 1fr;
  gap:18px;
  margin-bottom:18px;
}}
pre {{
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  color: #dbe7ff;
}}
</style>
</head>
<body>

<h1>LumenCore Validation Front End</h1>
<p class="small">Validation view for institutional flow + strategy ranking.</p>

<div class="grid">
  <div class="card"><div class="label">Best Flow</div><div class="val">{esc(best_flow)}</div></div>
  <div class="card"><div class="label">Best Strategy</div><div class="val">{esc(best_strategy)}</div></div>
  <div class="card"><div class="label">Best Sharpe</div><div class="val">{best_sharpe:.6f}</div></div>
  <div class="card"><div class="label">Vs Baseline</div><div class="val">{best_vs:.6f}</div></div>
  <div class="card"><div class="label">Institutional Score</div><div class="val">{best_inst:.3f}</div></div>
  <div class="card"><div class="label">Candidates</div><div class="val">{candidate_count}</div></div>
  <div class="card"><div class="label">Avg Top10 Sharpe</div><div class="val">{avg_top10_sharpe:.6f}</div></div>
  <div class="card"><div class="label">Avg Top10 Vs Baseline</div><div class="val">{avg_top10_vs:.6f}</div></div>
</div>

<div class="grid">
  <div class="card"><div class="label">Walk-Forward Sharpe</div><div class="val">{wf_sharpe:.6f}</div></div>
  <div class="card"><div class="label">MC Sharpe Mean</div><div class="val">{mc_mean:.6f}</div></div>
  <div class="card"><div class="label">MC Sharpe P05</div><div class="val">{mc_p05:.6f}</div></div>
  <div class="card"><div class="label">P(Sharpe > 1)</div><div class="val">{p_gt_1:.3f}</div></div>
</div>

<div class="hero">
  <div class="section">
    <h2>Validation summary</h2>
    <p>The current best configuration is <b>{esc(best_flow)}</b> with <b>{esc(best_strategy)}</b>.</p>
    <p>Best test Sharpe is <b>{best_sharpe:.6f}</b> and improvement versus baseline is <b>{best_vs:.6f}</b>.</p>
    <p>Evidence metrics are shown separately for Monte Carlo and walk-forward validation when available.</p>
    <p><b>Gate:</b> {badge_text} |
     WF Sharpe ≥ {PASS_WF_SHARPE:.2f},
     P(Sharpe &gt; 1) ≥ {PASS_MC_P_GT_1:.2f},
     MC P05 ≥ {PASS_MC_P05:.2f}</p>
  </div>

  <div class="section">
    <h2>Champion payload</h2>
    <pre>{esc(json.dumps(champion_payload, indent=2))}</pre>
  </div>
</div>

<div class="section">
  <h2>Before / after comparison proxy</h2>
  {curve_html}
</div>

<div class="section">
  <h2>Top 10 leaderboard</h2>
  {top10_html}
</div>

<div class="section">
  <h2>Proof files</h2>
  {proof_html}
</div>

</body>
</html>
"""

dash_path.write_text(html, encoding="utf-8")
print(dash_path)