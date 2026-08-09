from __future__ import annotations

import csv
import html
import importlib.util
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(
    os.environ.get("LUMA_STACK_ROOT", r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
).expanduser().resolve()
OUT = ROOT / "out"
EXEC_OUT = OUT / "execution"
DASH = Path(
    os.environ.get("LUMA_DASHBOARD_DIR", str(ROOT / "dashboard"))
).expanduser().resolve()

SOURCES = {
    "institutional_summary": EXEC_OUT / "institutional_summary.json",
    "strategy_baseline": EXEC_OUT / "top_system_strategy_baseline.json",
    "grant_proposals": OUT / "institutional_grant_proposals.json",
    "rolling_performance": OUT / "rolling_performance.json",
    "proof_chain": OUT / "unified_dashboard_chain_of_custody_sha256.json",
    "live_ops": DASH / "live_ops_state.json",
    "level2_summary": DASH / "level2_summary.txt",
    "level3_summary": DASH / "level3_truth_summary.txt",
    "level4_summary": DASH / "level4_live_summary.json",
    "master_summary": DASH / "master_summary.txt",
    "watchdog": DASH / "orchestrator_watchdog_status.txt",
    "compliance": DASH / "compliance_mvp_progress.json",
    "trade_log": EXEC_OUT / "trade_log.json",
    "walkforward_results": DASH / "ensemble_walkforward_results.csv",
}

OUTPUT_FILE = DASH / "combined_master_dashboard.html"


def build_premium_combined_dashboard() -> str | None:
  builder_path = ROOT / "code" / "UNIFIED_MASTER_DASHBOARD_BUILDER.py"
  if not builder_path.exists():
    return None
  spec = importlib.util.spec_from_file_location("luma_unified_master_dashboard_builder", builder_path)
  if spec is None or spec.loader is None:
    return None
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  data = module.collect_data()
  return module.render_html(data)


def load_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_text(path: Path, max_lines: int = 20) -> List[str]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return lines[:max_lines]
    except Exception:
        return []


def format_money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return str(value)


def format_pct(value: Any) -> str:
    try:
        val = float(value)
        return f"{val:.1f}%"
    except Exception:
        return str(value)


def count_trade_events(trades: List[Dict[str, Any]]) -> int:
    if not isinstance(trades, list):
        return 0
    return sum(1 for trade in trades if isinstance(trade, dict))


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def bounded_text_status(lines: Any) -> Dict[str, Any]:
    """Project only availability metadata; never publish arbitrary file contents."""
    if not isinstance(lines, list):
        return {"available": False, "line_count": 0}
    return {"available": bool(lines), "line_count": len(lines)}


def safe_dashboard_href(value: Any) -> str:
    """Allow same-directory HTML links only; reject active or external schemes."""
    name = str(value).strip()
    if not name or any(marker in name for marker in (":", "/", "\\")):
        return "#"
    if not re.fullmatch(r"[A-Za-z0-9._ -]+\.html?", name, flags=re.IGNORECASE):
        return "#"
    return name


def render_lines_as_html(lines: List[str], max_chars: int = 180) -> str:
    escaped = []
    for line in lines:
        text = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        escaped.append(text)
    return "\n".join(f"<div>{line}</div>" for line in escaped) if escaped else "<div class='empty'>No data</div>"


def load_csv_summary(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            reader = csv.DictReader(fh)
            rows = []
            for row in reader:
                try:
                    rows.append({
                        "start": int(row.get("start", 0)),
                        "end": int(row.get("end", 0)),
                        "result": float(row.get("result", 0.0)),
                    })
                except Exception:
                    continue
        if not rows:
            return {}
        latest = rows[-1]["result"]
        return {
            "count": len(rows),
            "latest_result": latest,
            "best_result": max(r["result"] for r in rows),
            "worst_result": min(r["result"] for r in rows),
            "latest_window": f"{rows[-1]['start']}–{rows[-1]['end']}",
        }
    except Exception:
        return {}


def find_dashboard_links(directory: Path, exclude: List[str] | None = None) -> List[Path]:
    exclude = exclude or []
    return sorted([p for p in directory.glob("*.html") if p.name not in exclude])


def build_dashboard(context: Dict[str, Any]) -> str:
    timestamp = datetime.now(timezone.utc).isoformat()
    inst = context.get("institutional_summary", {})
    baseline = context.get("strategy_baseline", {}).get("baseline", {})
    grant = context.get("grant_proposals", {})
    rolling = context.get("rolling_performance", {})
    proof = context.get("proof_chain", {})
    live_ops = context.get("live_ops", {})
    watch = context.get("watchdog", [])
    compliance = context.get("compliance", [])
    level2 = context.get("level2_summary", [])
    level3 = context.get("level3_summary", [])
    master = context.get("master_summary", [])
    walkforward = context.get("walkforward_results", {})
    dashboards = context.get("dashboard_links", [])
    trades = context.get("trade_log", [])
    trade_event_count = count_trade_events(trades)

    optimization_gain = float(baseline.get("top_test_vs_baseline", 0.0)) * 100.0
    optimization_badge = "INTERNAL DELTA REPORTED" if optimization_gain else "NO DELTA REPORTED"
    badge_color = "#ffd700"
    source_update_state = "CURRENT FEED REPORTED" if rolling.get("live_now") else "NO CURRENT FEED"
    proof_files = proof.get("files", []) if isinstance(proof.get("files", []), list) else []
    proof_count = len(proof_files)
    proof_chain_latest = proof_files[-1].get("path", "") if proof_files else ""

    grant_count = len(grant.get("grant_proposals", [])) if isinstance(grant.get("grant_proposals", []), list) else 0
    watch_state = "ISSUES REPORTED" if any("ISSUES DETECTED" in str(line) for line in watch) else ("REPORTED CLEAR" if watch else "NOT REPORTED")
    comp_lines = "<br>".join(
        f"{esc(item.get('item', ''))}: {esc(item.get('status', ''))}"
        for item in compliance
        if isinstance(item, dict)
    ) if isinstance(compliance, list) else "No compliance data."
    summary_meta = {
        "level2": bounded_text_status(level2),
        "level3": bounded_text_status(level3),
        "master": bounded_text_status(master),
    }

    top_strategies = baseline.get("top_strategies", []) if isinstance(baseline.get("top_strategies", []), list) else []
    strategy_rows = "".join(
        f"<tr><td>{esc(s.get('rank'))}</td><td>{esc(s.get('flow'))}</td><td>{esc(s.get('strategy'))}</td><td>{esc(s.get('algo'))}</td><td>{float(s.get('test_sharpe', 0.0)):.3f}</td><td>{float(s.get('institutional_score', 0.0)):.2f}</td><td>{float(s.get('stability',0.0)):.3f}</td></tr>"
        for s in top_strategies[:8]
    )

    walkforward_count = int(walkforward.get("count", 0))
    walkforward_latest = float(walkforward.get("latest_result", 0.0))
    walkforward_best = float(walkforward.get("best_result", 0.0))
    walkforward_worst = float(walkforward.get("worst_result", 0.0))
    walkforward_window = walkforward.get("latest_window", "n/a")
    dashboard_links_html = "".join(
        f"<li><a href='{esc(safe_dashboard_href(link))}' target='_blank' rel='noopener noreferrer'>{esc(Path(link).stem.replace('_', ' ').title())}</a></li>"
        for link in dashboards
    ) or "<li>No dashboard pages found.</li>"

    return f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>LumenCore Combined Master Dashboard</title>
<style>
body {{margin:0;padding:24px;background:#03101f;color:#eef7ff;font-family:Segoe UI,Arial,sans-serif;}}
.wrap {{max-width:1600px;margin:0 auto;}}
h1,h2,h3{{margin:0;}}
h1{{font-size:38px;color:#7dfcfa;}}
.sub{{color:#9ebde3;margin:12px 0 24px;}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;}}
.card{{background:rgba(10,20,40,0.96);border:1px solid rgba(125,252,250,0.14);border-radius:18px;padding:20px;box-shadow:0 18px 50px rgba(0,0,0,0.18);}}
.card-title{{font-size:14px;text-transform:uppercase;color:#74f0b6;letter-spacing:0.12em;margin-bottom:14px;}}
.metric{{display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px solid rgba(255,255,255,0.06);}}
.metric:last-child{{border-bottom:none;}}
.metric-label{{color:#9fbad3;}}
.metric-value{{font-size:1.2rem;font-weight:700;}}
.badge{{display:inline-flex;align-items:center;justify-content:center;padding:8px 14px;border-radius:999px;background:{badge_color};color:#04120b;font-weight:800;letter-spacing:0.06em;}}
.small{{color:#a5b8d6;font-size:0.94rem;}}
.table-wrap{{overflow-x:auto;}}
table{{width:100%;border-collapse:collapse;margin-top:14px;}}
th,td{{padding:12px 10px;border-bottom:1px solid rgba(255,255,255,0.08);text-align:left;font-size:0.92rem;}}
th{{color:#8fd9ff;text-transform:uppercase;letter-spacing:0.08em;font-size:0.78rem;}}
.txid{{font-family:Consolas,monospace;background:rgba(125,252,250,0.08);padding:8px 10px;margin-bottom:8px;border-radius:10px;word-break:break-all;}}
.empty{{color:#7288a0;font-style:italic;}}
.code-block{{background:rgba(0,0,0,0.22);padding:14px;border-radius:14px;font-family:Consolas,monospace;font-size:0.86rem;line-height:1.5;white-space:pre-wrap;word-break:break-word;color:#d9ebff;}}
.link-list{{list-style:none;padding:0;margin:0;}}
.link-list li{{margin-bottom:8px;}}
.link-list a{{color:#7dfcfa;text-decoration:none;}}
.footer{{margin-top:24px;text-align:center;color:#7d9bc1;font-size:0.9rem;}}
</style>
</head>
<body>
<div class='wrap'>
<h1>LumenCore Combined Master Dashboard</h1>
<div class='sub'>Unified live, proof, optimization, grant, and audit view for every major command center asset.</div>

<div class='grid'>
  <div class='card'>
    <div class='card-title'>Master Status</div>
    <div class='metric'><span class='metric-label'>Generated UTC</span><span class='metric-value'>{timestamp}</span></div>
    <div class='metric'><span class='metric-label'>Source Update State</span><span class='metric-value'>{source_update_state}</span></div>
    <div class='metric'><span class='metric-label'>Paper Event Records</span><span class='metric-value'>{trade_event_count}</span></div>
    <div class='metric'><span class='metric-label'>Optimization Badge</span><span class='badge'>{optimization_badge}</span></div>
  </div>

  <div class='card'>
    <div class='card-title'>Optimization Baseline</div>
    <div class='metric'><span class='metric-label'>Top Flow</span><span class='metric-value'>{baseline.get('top_flow', 'N/A')}</span></div>
    <div class='metric'><span class='metric-label'>Top Strategy</span><span class='metric-value'>{baseline.get('top_strategy', 'N/A')}</span></div>
    <div class='metric'><span class='metric-label'>Top Algo</span><span class='metric-value'>{baseline.get('top_algo', 'N/A')}</span></div>
    <div class='metric'><span class='metric-label'>Top Sharpe</span><span class='metric-value'>{float(baseline.get('top_test_sharpe', 0.0)):.3f}</span></div>
    <div class='metric'><span class='metric-label'>Total Candidates</span><span class='metric-value'>{int(baseline.get('total_candidates', 0))}</span></div>
    <div class='metric'><span class='metric-label'>Institutional Score</span><span class='metric-value'>{float(baseline.get('top_institutional_score', 0.0)):.2f}</span></div>
  </div>

  <div class='card'>
    <div class='card-title'>Proof and Audit Summary</div>
    <div class='metric'><span class='metric-label'>Proof Chain Files</span><span class='metric-value'>{proof_count}</span></div>
    <div class='metric'><span class='metric-label'>Proof Receipt Status</span><span class='metric-value'>{'PRESENT' if proof_count else 'MISSING'}</span></div>
    <div class='metric'><span class='metric-label'>Latest Proof Artifact</span><span class='metric-value'>{esc(Path(proof_chain_latest).name if proof_chain_latest else 'None')}</span></div>
    <div class='metric'><span class='metric-label'>Grant Proposals</span><span class='metric-value'>{grant_count}</span></div>
    <div class='metric'><span class='metric-label'>Watchdog State</span><span class='metric-value'>{watch_state}</span></div>
  </div>

  <div class='card'>
    <div class='card-title'>Observation Lane (No Orders)</div>
    <div class='metric'><span class='metric-label'>Observed Pair</span><span class='metric-value'>{esc(live_ops.get('live_rows', [{}])[-1].get('top_pair', 'N/A') if live_ops.get('live_rows') else 'N/A')}</span></div>
    <div class='metric'><span class='metric-label'>Observed Strategy</span><span class='metric-value'>{esc(live_ops.get('live_rows', [{}])[-1].get('top_strategy', 'N/A') if live_ops.get('live_rows') else 'N/A')}</span></div>
    <div class='metric'><span class='metric-label'>Paper Action</span><span class='metric-value'>{esc(live_ops.get('live_rows', [{}])[-1].get('top_action', 'N/A') if live_ops.get('live_rows') else 'N/A')}</span></div>
    <div class='metric'><span class='metric-label'>Paper Luma Score</span><span class='metric-value'>{float(live_ops.get('live_rows', [{}])[-1].get('top_luma_score', 0.0) if live_ops.get('live_rows') else 0.0):.3f}</span></div>
    <div class='metric'><span class='metric-label'>Paper Allocation Weight Sum</span><span class='metric-value'>{float(live_ops.get('live_rows', [{}])[-1].get('gross_effective_weight', 0.0) if live_ops.get('live_rows') else 0.0):.3f}</span></div>
  </div>
</div>

<div class='grid'>
  <div class='card'>
    <div class='card-title'>Execution Identifier Boundary</div>
    <div class='code-block'>Raw transaction and order identifiers are excluded from the public dashboard. Paper event count: {trade_event_count}.</div>
  </div>

  <div class='card'>
    <div class='card-title'>Runtime Guard State</div>
    <div class='code-block'>Watchdog: {watch_state}</div>
    <div class='code-block'>Credential state is private and is not inspected or published by this surface.</div>
  </div>

  <div class='card'>
    <div class='card-title'>Compliance / MVP Progress</div>
    <div class='code-block'>{comp_lines}</div>
  </div>

  <div class='card'>
    <div class='card-title'>Baseline Strategy Ranking</div>
    <div class='table-wrap'>
      <table>
        <thead><tr><th>#</th><th>Flow</th><th>Strategy</th><th>Algo</th><th>Sharpe</th><th>Score</th><th>Stab</th></tr></thead>
        <tbody>{strategy_rows}</tbody>
      </table>
    </div>
  </div>
</div>

<div class='grid'>
  <div class='card'>
    <div class='card-title'>Level 2 Summary Receipt</div>
    <div class='code-block'>Available: {summary_meta['level2']['available']} | Lines retained privately: {summary_meta['level2']['line_count']}</div>
  </div>
  <div class='card'>
    <div class='card-title'>Level 3 Summary Receipt</div>
    <div class='code-block'>Available: {summary_meta['level3']['available']} | Lines retained privately: {summary_meta['level3']['line_count']}</div>
  </div>
  <div class='card'>
    <div class='card-title'>Master Summary Receipt</div>
    <div class='code-block'>Available: {summary_meta['master']['available']} | Lines retained privately: {summary_meta['master']['line_count']}</div>
  </div>
</div>

<div class='card'>
  <div class='card-title'>Dashboard Library</div>
  <ul class='link-list'>{dashboard_links_html}</ul>
</div>

<div class='footer'>
  Combined dashboard generated from institutional, live, proof, and grant command center sources.
</div>
</div>
</body>
</html>"""


def run() -> Path:
    DASH.mkdir(parents=True, exist_ok=True)
    context = {}
    for key, path in SOURCES.items():
        if path.suffix.lower() in {".json"}:
            context[key] = load_json(path, {})
        elif path.suffix.lower() == ".csv":
            context[key] = load_csv_summary(path)
        else:
            context[key] = load_text(path, max_lines=20)
    context["trade_log"] = load_json(SOURCES["trade_log"], [])
    context["dashboard_links"] = [str(p.name) for p in find_dashboard_links(DASH, exclude=[OUTPUT_FILE.name])]

    html = build_premium_combined_dashboard() or build_dashboard(context)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    return OUTPUT_FILE


if __name__ == '__main__':
    out_path = run()
    print(f"✅ Combined dashboard written: {out_path}")
