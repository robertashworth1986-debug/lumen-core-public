from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from cold_case_engine import HarmonicEvidenceEngine, CaseRecord, EvidenceComponent, sample_cold_case_data

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
DASHBOARD = ROOT.parent.parent / "dashboard"
SUMMARY_FILE = OUTPUT / "cold_case_summary.json"
DASH_FILE = DASHBOARD / "cold_case_dashboard.html"


def render_case_row(case: Dict[str, Any]) -> str:
    return f"""
    <tr>
        <td>{case['case_id']}</td>
        <td>{case['title']}</td>
        <td>{case['status']}</td>
        <td>{case['category']}</td>
        <td>{case['case_strength']:.3f}</td>
        <td>{case['credibility']:.3f}</td>
        <td>{case['stability']:.3f}</td>
        <td>{case['lead_quality']:.3f}</td>
        <td>{case['evidence_count']}</td>
    </tr>
    """


def build_dashboard(summary: Dict[str, Any]) -> str:
    rows = "".join(render_case_row(case) for case in summary["ranked_cases"])
    categories = ", ".join(summary.get("categories", []))
    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>LumaTrader Cold-Case Evidence Dashboard</title>
  <style>
    body {{ margin:0; font-family: Inter, system-ui, sans-serif; background: #051019; color: #eef2ff; }}
    header {{ padding: 24px; background: linear-gradient(180deg, #07202a 0%, #06161f 100%); border-bottom: 1px solid #103147; }}
    header h1 {{ margin:0; font-size:2.2rem; color:#7dfcfa; }}
    header p {{ margin:8px 0 0; color:#92a8bf; }}
    .container {{ padding:24px; max-width: 1400px; margin: auto; }}
    .summary-grid {{ display:grid; gap:18px; grid-template-columns: repeat(auto-fit, minmax(240px,1fr)); margin-top:24px; }}
    .card {{ padding:22px; border-radius:18px; background: rgba(15, 30, 50, 0.92); border: 1px solid rgba(74, 172, 255, 0.12); }}
    .card h2 {{ margin:0 0 12px; font-size:1.05rem; color:#c6f7ff; }}
    .metric {{ font-size: 1.75rem; font-weight:700; margin-top:8px; }}
    .small {{ color:#98aebd; margin-top:10px; display:block; }}
    table {{ width:100%; border-collapse:collapse; margin-top:18px; }}
    th, td {{ padding:14px 12px; text-align:left; border-bottom:1px solid rgba(255,255,255,0.08); font-size:0.95rem; }}
    th {{ color:#94c7ff; text-transform:uppercase; letter-spacing:0.06em; font-size:0.8rem; }}
    tr:hover {{ background: rgba(74, 172, 255, 0.06); }}
    .chart-card {{ margin-top:24px; }}
    canvas {{ width:100% !important; height: 360px !important; }}
    .pill {{ display:inline-flex; align-items:center; gap:8px; padding:8px 12px; border-radius:999px; background:#0F172A; border:1px solid rgba(129, 196, 255, 0.14); color:#b8d8ff; margin-right:8px; margin-bottom:8px; }}
    .pill span {{ width:10px; height:10px; border-radius:999px; display:inline-block; background:#7dfcfa; }}
  </style>
</head>
<body>
<header>
  <h1>LumaTrader Cold-Case Evidence Dashboard</h1>
  <p>Harmonic evidence scoring, rolling stability, and freeze-proof delta tracking for unsolved investigations.</p>
</header>
<div class="container">
  <div class="summary-grid">
    <div class="card"><h2>Cases Tracked</h2><div class="metric">{summary['case_count']}</div><span class="small">Active cold cases ingested by the engine.</span></div>
    <div class="card"><h2>Categories</h2><div class="metric">{categories}</div><span class="small">Evidence domains and case types in the current run.</span></div>
    <div class="card"><h2>Top Case Strength</h2><div class="metric">{summary['ranked_cases'][0]['case_strength'] if summary['ranked_cases'] else 0.0:.3f}</div><span class="small">Harmonic aggregate across evidence quality, confidence, freshness, and stability.</span></div>
    <div class="card"><h2>Stability</h2><div class="metric">{summary['ranked_cases'][0]['stability'] if summary['ranked_cases'] else 0.0:.3f}</div><span class="small">Higher values signal cases with more coherent evidence structure.</span></div>
  </div>

  <div class="card chart-card"><h2>Case Strength Distribution</h2><canvas id="caseStrengthChart"></canvas></div>

  <div class="card"><h2>Top Cold Case Priorities</h2><table><thead><tr><th>Case</th><th>Status</th><th>Category</th><th>Strength</th><th>Credibility</th><th>Stability</th><th>Lead Quality</th><th>Evidence</th></tr></thead><tbody>
    {rows}
  </tbody></table></div>

  <div class="card"><h2>Harmonic Evidence Philosophy</h2>
    <p class="small">This dashboard avoids gradient backprop; it uses harmonic aggregation to reward completeness across evidence dimensions while penalizing missing evidence and weak confidence.</p>
    <div class="pill"><span></span>Harmonic evidence scoring</div>
    <div class="pill"><span></span>Rolling integrity / stability</div>
    <div class="pill"><span></span>Forensic + digital + witness traces</div>
    <div class="pill"><span></span>Case freeze checksum proof</div>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
const data = {json.dumps(summary)};
const labels = data.ranked_cases.map(c => c.case_id);
const values = data.ranked_cases.map(c => c.case_strength);
const ctx = document.getElementById('caseStrengthChart');
new Chart(ctx, {{
    type: 'bar',
    data: {{
        labels,
        datasets: [{{
            label: 'Case Strength',
            data: values,
            backgroundColor: 'rgba(125, 252, 250, 0.35)',
            borderColor: '#7dfcfa',
            borderWidth: 2,
        }}]
    }},
    options: {{
        scales: {{
            y: {{ beginAtZero: true, max: 1.0 }}
        }}
    }}
}});
</script>
</body>
</html>
"""


def load_input_data(path: Path) -> List[CaseRecord]:
    if not path.exists():
        return sample_cold_case_data()

    raw = json.loads(path.read_text(encoding='utf-8'))
    cases: List[CaseRecord] = []
    for record in raw:
        evidence = [EvidenceComponent(**e) for e in record.get('evidence', [])]
        cases.append(CaseRecord(
            case_id=record.get('case_id', 'UNKNOWN'),
            title=record.get('title', 'Untitled'),
            status=record.get('status', 'Unknown'),
            category=record.get('category', 'Unknown'),
            evidence=evidence,
            metadata=record.get('metadata', {}),
        ))
    return cases


def main() -> None:
    cases = load_input_data(OUTPUT / 'cold_case_evidence.json')
    engine = HarmonicEvidenceEngine(cases)
    summary = {
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'case_count': len(cases),
        'ranked_cases': engine.rank_cases(),
        'categories': sorted({case.category for case in cases}),
    }
    SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    DASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    DASH_FILE.write_text(build_dashboard(summary), encoding='utf-8')
    print(f'Cold-case dashboard generated: {DASH_FILE}')


if __name__ == '__main__':
    main()
