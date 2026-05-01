from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List

from xinfit import XinFitEngine, sample_karmuk_cases

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
DASHBOARD = ROOT.parent.parent / "dashboard"
SUMMARY_FILE = OUTPUT / "karmuk_summary.json"
DASH_FILE = DASHBOARD / "karmuk_dashboard.html"


def render_row(item: Dict[str, any]) -> str:
    return f"""
    <tr>
        <td>{item['case_id']}</td>
        <td>{item['title']}</td>
        <td>{item['status']}</td>
        <td>{item['category']}</td>
        <td>{item['case_strength']:.4f}</td>
        <td>{item['karmuk_sum']:.4f}</td>
        <td>{item['burst_energy']:.4f}</td>
        <td>{item['constancy']:.4f}</td>
        <td>{item['evidence_count']}</td>
    </tr>
    """


def build_dashboard(summary: Dict[str, any]) -> str:
    rows = "".join(render_row(item) for item in summary['case_rankings'])
    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>LumaTrader Karmuk Dashboard</title>
  <style>
    body {{ margin:0; font-family: Inter, system-ui, sans-serif; background: #03101c; color: #e8f7ff; }}
    header {{ padding: 26px 28px; background: linear-gradient(180deg, #071728 0%, #04101c 100%); border-bottom: 1px solid rgba(119, 231, 255, 0.12); }}
    header h1 {{ margin:0; font-size:2.3rem; color:#7dfcfa; }}
    header p {{ margin:10px 0 0; color:#90b6cc; max-width: 920px; }}
    .container {{ padding:22px 28px; max-width: 1420px; margin:auto; }}
    .grid {{ display:grid; gap:18px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); margin-top:24px; }}
    .card {{ background: rgba(12, 24, 38, 0.92); border: 1px solid rgba(125, 252, 250, 0.1); border-radius:18px; padding:22px; }}
    .card h2 {{ margin:0 0 12px; font-size:1.05rem; color:#c3f5ff; }}
    .metric {{ font-size:2rem; font-weight:700; margin-top:8px; }}
    .small {{ color:#97b9cd; margin-top:10px; display:block; }}
    table {{ width:100%; border-collapse: collapse; margin-top:18px; }}
    th, td {{ padding:14px 12px; border-bottom:1px solid rgba(255,255,255,0.08); text-align:left; font-size:0.95rem; }}
    th {{ color:#9ecfff; text-transform:uppercase; letter-spacing:0.07em; font-size:0.78rem; }}
    tr:hover {{ background: rgba(125,252,250,0.08); }}
    .pill {{ display:inline-flex; align-items:center; gap:8px; padding:8px 14px; border-radius:999px; background: rgba(9, 22, 35, 0.95); border:1px solid rgba(125,252,250,0.14); color:#b2e8ff; margin-right:10px; margin-bottom:10px; }}
    .pill span {{ width:10px; height:10px; border-radius:999px; display:inline-block; background:#7dfcfa; }}
    canvas {{ width:100% !important; height: 320px !important; margin-top:18px; }}
  </style>
</head>
<body>
<header>
  <h1>LumaTrader Karmuk Dashboard</h1>
  <p>Rolling karma-engine proof with multi-fractile burst metrics, Monte Carlo karma search, and compound good karma sums.</p>
</header>
<div class="container">
  <div class="grid">
    <div class="card"><h2>Case count</h2><div class="metric">{summary['case_count']}</div><span class="small">Total cases being processed by XinFit.</span></div>
    <div class="card"><h2>Overall Karmuk</h2><div class="metric">{summary['overall_karmuk']:.4f}</div><span class="small">Summed karma points across all cases.</span></div>
    <div class="card"><h2>Monte Carlo Burst Value</h2><div class="metric">{summary['monte_carlo']['best_value']:.4f}</div><span class="small">Best karma search configuration found over {summary['monte_carlo']['runs']} runs.</span></div>
    <div class="card"><h2>Rolling Mean</h2><div class="metric">{summary['rolling_karma']['rolling_mean']:.4f}</div><span class="small">Rolling karma mean over the last {summary['rolling_karma']['history_length']} checkpoints.</span></div>
  </div>
  <div class="card"><h2>Fractal Karmuk Moments</h2>
    <div class="pill"><span></span>Median {summary['karmuk_moments']['q50']:.4f}</div>
    <div class="pill"><span></span>Q75 {summary['karmuk_moments']['q75']:.4f}</div>
    <div class="pill"><span></span>Q90 {summary['karmuk_moments']['q90']:.4f}</div>
    <div class="pill"><span></span>Q99 {summary['karmuk_moments']['q99']:.4f}</div>
  </div>
  <div class="card"><h2>Top Case Karmuk Burst</h2><table><thead><tr><th>Case</th><th>Status</th><th>Strength</th><th>Karmuk Sum</th><th>Burst Energy</th><th>Constancy</th><th>Evidence</th></tr></thead><tbody>
    {''.join(render_row(item) for item in summary['case_rankings'][:8])}
  </tbody></table></div>
  <div class="card">
    <h2>XinFit Philosophy</h2>
    <p class="small">This engine uses harmonic aggregation and rolling Monte Carlo to maximize good karma across evidence cases. Karmuk sums are the multi-scale moments of strength, and the burst engine captures extreme fractile allocations.</p>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
const summary = {json.dumps(summary)};
const labels = summary.case_rankings.map(c => c.case_id);
const values = summary.case_rankings.map(c => c.case_strength);
const ctx = document.createElement('canvas');
ctx.id = 'karmukChart';
document.querySelector('.container').insertBefore(ctx, document.querySelector('.container').children[2]);
new Chart(ctx, {{
  type: 'line',
  data: {{
    labels,
    datasets: [{{
      label: 'Case Strength',
      data: values,
      borderColor: '#7dfcfa',
      backgroundColor: 'rgba(125,252,250,0.2)',
      tension: 0.25,
      pointRadius: 4,
      pointHoverRadius: 6,
    }}]
  }},
  options: {{
    scales: {{
      y: {{ beginAtZero: true, max: 1.0 }}
    }},
    plugins: {{ legend: {{ display: false }} }}
  }}
}});
</script>
</body>
</html>
"""


def main() -> None:
    cases = sample_karmuk_cases()
    engine = XinFitEngine(cases=cases, runs=1200, history_length=50)
    summary = engine.build_summary()
    SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    DASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    DASH_FILE.write_text(build_dashboard(summary), encoding='utf-8')
    print(f'Karmuk dashboard generated at {DASH_FILE}')


if __name__ == '__main__':
    main()
