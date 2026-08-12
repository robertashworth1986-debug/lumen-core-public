from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
EXEC_OUT = OUT / "execution"
DASH = ROOT / "dashboard"

INSTITUTIONAL_TOP10 = EXEC_OUT / "institutional_top10.csv"
INSTITUTIONAL_SUMMARY = EXEC_OUT / "institutional_summary.json"
INVESTOR_GRANT_EVIDENCE = OUT / "investor_and_grant_evidence.json"
FEDERAL_BRIEF = OUT / "federal_brief.json"
TOP_STRATEGY_BASELINE_JSON = EXEC_OUT / "top_system_strategy_baseline.json"
TOP_STRATEGY_BASELINE_MD = EXEC_OUT / "top_system_strategy_baseline.md"
GRANT_PROPOSALS_JSON = OUT / "institutional_grant_proposals.json"
GRANT_PROPOSALS_MD = OUT / "institutional_grant_proposals.md"
GRANT_PROPOSALS_HTML = DASH / "institutional_grant_proposals.html"

PROGRAMS = [
    {
        "name": "DARPA Trust and Resilience R&D",
        "focus": "trusted autonomy, resilient decision systems, and audit-grade evidence chains",
    },
    {
        "name": "NSF AI for Critical Infrastructure",
        "focus": "institutional AI systems that span financial, energy, and supply-chain domains",
    },
    {
        "name": "DOE Grid and Energy Systems Innovation",
        "focus": "physics-aware micro-macro decision engines with stability and risk mitigation",
    },
    {
        "name": "DOD Mission Assurance and Operational Resilience",
        "focus": "real-time signal fusion, execution provenance, and decision lineage for mission-critical assets",
    },
    {
        "name": "NASA Mission Systems AI",
        "focus": "trusted systems engineering with cross-sector evidence and long-term stability",
    },
    {
        "name": "SBIR Phase II: Institutional Quant and Execution",
        "focus": "commercialization of grant-ready algorithmic finance and cross-sector signal infrastructure",
    },
    {
        "name": "NIH Digital Health Infrastructure",
        "focus": "predictive risk systems and audit-ready evidence for health supply-chain resilience",
    },
    {
        "name": "OSTP National Resilience Program",
        "focus": "federally aligned software that prevents trillion-dollar failures",
    },
    {
        "name": "FinTech Innovation Fund",
        "focus": "crypto-grade proof of execution, live trading TXIDs, and capital efficiency monitoring",
    },
    {
        "name": "Strategic Digital Scout and Guardrails Initiative",
        "focus": "universal neighborhood-watch system for industry-scale signal integrity",
    },
]


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_csv(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)
    return rows


def format_money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "$0.00"


def format_pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.2f}%" if abs(float(value)) <= 100 else f"{float(value):.2f}%"
    except Exception:
        return "0.00%"


def parse_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def build_top_strategy_baseline() -> Dict[str, Any]:
    top10 = load_csv(INSTITUTIONAL_TOP10)
    summary = load_json(INSTITUTIONAL_SUMMARY, {}) or {}
    evidence = load_json(INVESTOR_GRANT_EVIDENCE, {}) or {}
    federal = load_json(FEDERAL_BRIEF, {}) or {}

    strategies: List[Dict[str, Any]] = []
    for idx, row in enumerate(top10[:10], start=1):
        strategies.append({
            "rank": idx,
            "flow": row.get("flow", ""),
            "strategy": row.get("strategy", ""),
            "algo": row.get("algo", ""),
            "test_sharpe": parse_float(row.get("test_sharpe")),
            "test_sortino": parse_float(row.get("test_sortino")),
            "test_max_dd": parse_float(row.get("test_max_dd")),
            "test_cagr": parse_float(row.get("test_cagr")),
            "test_vs_baseline": parse_float(row.get("test_vs_baseline")),
            "stability": parse_float(row.get("stability")),
            "institutional_score": parse_float(row.get("institutional_score")),
            "source_file": row.get("file", ""),
        })

    baseline = {
        "generated_utc": utc_iso(),
        "top_strategy": summary.get("top_strategy", "unknown"),
        "top_flow": summary.get("top_flow", "unknown"),
        "top_algo": summary.get("top_algo", "unknown"),
        "top_test_sharpe": parse_float(summary.get("top_test_sharpe")),
        "top_test_vs_baseline": parse_float(summary.get("top_test_vs_baseline")),
        "top_institutional_score": parse_float(summary.get("top_institutional_score")),
        "files_scanned": int(summary.get("files_scanned", 0)),
        "total_candidates": int(summary.get("total_candidates", 0)),
        "top_wf_sharpe_mean": parse_float(summary.get("top_wf_sharpe_mean")),
        "top_wf_stability": parse_float(summary.get("top_wf_stability")),
        "strategy_count": len(strategies),
    }

    context = {
        "generated_utc": utc_iso(),
        "baseline": baseline,
        "top_strategies": strategies,
        "grant_evidence": {
            "project_alignment": federal.get("program_alignment", []),
            "validation_scope": "local_evidence_bundle_pending_independent_review",
            "proof_files": [str(p) for p in evidence.get("proof_files", [])] if isinstance(evidence.get("proof_files"), list) else [],
            "federal_brief": str(FEDERAL_BRIEF) if FEDERAL_BRIEF.exists() else "",
        },
    }

    TOP_STRATEGY_BASELINE_JSON.parent.mkdir(parents=True, exist_ok=True)
    TOP_STRATEGY_BASELINE_JSON.write_text(json.dumps(context, indent=2), encoding="utf-8")
    return context


def build_grant_proposals(context: Dict[str, Any]) -> Dict[str, Any]:
    baseline = context.get("baseline", {})
    strategies = context.get("top_strategies", [])
    proof = context.get("grant_evidence", {})
    proposals: List[Dict[str, Any]] = []

    top_strategy = strategies[0] if strategies else {}
    summary_lines = [
        f"Top strategy: {baseline.get('top_flow')} / {baseline.get('top_strategy')} / {baseline.get('top_algo')}",
        f"Top test Sharpe: {baseline.get('top_test_sharpe'):.4f}",
        f"Top test vs baseline: {baseline.get('top_test_vs_baseline'):.4f}",
        f"Top institutional score: {baseline.get('top_institutional_score'):.4f}",
        f"Live strategic candidates analysed: {baseline.get('total_candidates')}",
        f"Provenance: {proof.get('validation_scope', 'local evidence pending independent review')}",
    ]

    for idx, program in enumerate(PROGRAMS, start=1):
        narrative = [
            f"Program: {program['name']}",
            f"Focus: {program['focus']}",
            "", 
            "Problem:",
            "- Modern institutions need a single cross-sector intelligence system that can detect drift, preserve evidence, and produce auditable proof for trillion-dollar decisions.",
            "", 
            "Solution:",
            f"- LumenCore's unified strategy baseline ranks the top 10 institutional strategies across root engines and encodes them as a live baseline for grant-backed systems.",
            f"- The current top strategy is {baseline.get('top_flow')} / {baseline.get('top_strategy')} / {baseline.get('top_algo')} with Sharpe {baseline.get('top_test_sharpe'):.4f} and institutional score {baseline.get('top_institutional_score'):.4f}.",
            f"- The project produces hash-verifiable proof files and federal-brief evidence aligned to {', '.join(proof.get('project_alignment', [])) or 'federal resilience programs' }.",
            "", 
            "Impact:",
            f"- Baseline analysis currently covers {baseline.get('total_candidates')} candidate systems and identifies the top 10 highest-value strategies.",
            "- This system is designed to surface the most consequential leads with stability-aware, physics-respecting scoring and to prevent silent drift.",
            "", 
            "Deliverables:",
            "- Top-system strategy baseline report and ranked leaderboard",
            "- Grant-ready proof pack with SHA-256 chain-of-custody for every major artifact",
            "- A deployable evidence dashboard and federal brief for reviewers",
            "- A set of 10 grant proposals with tailored descriptions and value alignment",
        ]
        proposals.append({
            "proposal_id": f"GRANT-{idx:02d}",
            "program": program["name"],
            "focus": program["focus"],
            "generated_utc": utc_iso(),
            "headline": f"Institutional strategy baseline for {program['name']}",
            "summary": "\n".join(summary_lines),
            "narrative": "\n".join(narrative),
            "top_strategy": {
                "flow": top_strategy.get("flow", ""),
                "strategy": top_strategy.get("strategy", ""),
                "algo": top_strategy.get("algo", ""),
                "test_sharpe": top_strategy.get("test_sharpe", 0.0),
                "institutional_score": top_strategy.get("institutional_score", 0.0),
            },
            "proof_files": proof.get("proof_files", []),
        })

    payload = {
        "generated_utc": utc_iso(),
        "baseline": baseline,
        "top_strategies": strategies,
        "grant_proposals": proposals,
    }
    GRANT_PROPOSALS_JSON.parent.mkdir(parents=True, exist_ok=True)
    GRANT_PROPOSALS_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def render_markdown(context: Dict[str, Any], proposals: Dict[str, Any]) -> str:
    baseline = context.get("baseline", {})
    strategies = context.get("top_strategies", [])
    lines: List[str] = [
        "# Top System Strategy Baseline",
        "",
        f"Generated UTC: {context.get('generated_utc', '')}",
        "",
        "## Baseline Summary",
        f"- Top Flow: {baseline.get('top_flow', '')}",
        f"- Top Strategy: {baseline.get('top_strategy', '')}",
        f"- Top Algo: {baseline.get('top_algo', '')}",
        f"- Top Test Sharpe: {baseline.get('top_test_sharpe', 0.0):.4f}",
        f"- Top vs Baseline: {baseline.get('top_test_vs_baseline', 0.0):.4f}",
        f"- Institutional Score: {baseline.get('top_institutional_score', 0.0):.4f}",
        f"- Candidates Scanned: {baseline.get('total_candidates', 0)}",
        "",
        "## Top 10 Strategy Rank",
    ]
    for strategy in strategies:
        lines.extend([
            f"### {strategy['rank']}. {strategy['flow']} / {strategy['strategy']} / {strategy['algo']}",
            f"- Test Sharpe: {strategy['test_sharpe']:.4f}",
            f"- Test Sortino: {strategy['test_sortino']:.4f}",
            f"- Test Max DD: {strategy['test_max_dd']:.4f}",
            f"- Test CAGR: {strategy['test_cagr']:.4f}",
            f"- Trend vs Baseline: {strategy['test_vs_baseline']:.4f}",
            f"- Stability: {strategy['stability']:.4f}",
            f"- Institutional Score: {strategy['institutional_score']:.4f}",
            f"- Source File: {strategy['source_file']}",
            "",
        ])

    lines.extend([
        "## Grant Proposals",
        "",
    ])
    for proposal in proposals.get("grant_proposals", [])[:10]:
        lines.extend([
            f"### {proposal['proposal_id']} — {proposal['program']}",
            f"Summary: {proposal['summary']}",
            "",
        ])

    return "\n".join(lines)


def render_html(context: Dict[str, Any], proposals: Dict[str, Any]) -> str:
    lines = [
        "<!doctype html>",
        "<html lang=\"en\">",
        "<head>",
        "<meta charset=\"utf-8\">",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
        "<title>Institutional Grant Proposals</title>",
        "<style>",
        "body{margin:0;padding:24px;font-family:Segoe UI,Arial,sans-serif;background:#03111e;color:#eef6ff;}",
        "h1{margin:0 0 12px;font-size:32px;color:#7dfcfa;}",
        "h2{margin:24px 0 8px;color:#a6f7ff;}",
        "h3{margin:18px 0 6px;color:#c8f3ff;}",
        "p,li{line-height:1.5;font-size:14px;color:#d8e8f2;}",
        ".card{background:rgba(8,25,44,0.95);border:1px solid rgba(125,252,250,0.18);border-radius:14px;padding:18px;margin-bottom:16px;}",
        "table{width:100%;border-collapse:collapse;margin-top:12px;}",
        "th,td{padding:10px 8px;border-bottom:1px solid rgba(125,252,250,0.12);}",
        "th{color:#7dfcfa;text-align:left;font-size:12px;}",
        "</style>",
        "</head>",
        "<body>",
        "<div class=\"card\">",
        "<h1>Top System Strategy Baseline</h1>",
        f"<p>Generated UTC: {context.get('generated_utc','')}</p>",
        "</div>",
        "<div class=\"card\">",
        "<h2>Baseline Summary</h2>",
        "<table>",
        "<tbody>",
    ]
    baseline = context.get("baseline", {})
    for label, value in [
        ("Top Flow", baseline.get("top_flow", "")),
        ("Top Strategy", baseline.get("top_strategy", "")),
        ("Top Algo", baseline.get("top_algo", "")),
        ("Top Test Sharpe", f"{baseline.get('top_test_sharpe',0.0):.4f}"),
        ("Top vs Baseline", f"{baseline.get('top_test_vs_baseline',0.0):.4f}"),
        ("Institutional Score", f"{baseline.get('top_institutional_score',0.0):.4f}"),
        ("Candidates Scanned", baseline.get("total_candidates", 0)),
    ]:
        lines.append(f"<tr><th>{label}</th><td>{value}</td></tr>")
    lines.extend([
        "</tbody>",
        "</table>",
        "</div>",
        "<div class=\"card\">",
        "<h2>Top 10 Strategies</h2>",
        "<table>",
        "<thead><tr><th>#</th><th>Flow</th><th>Strategy</th><th>Algo</th><th>Sharpe</th><th>Score</th><th>Stability</th></tr></thead>",
        "<tbody>",
    ])
    for strategy in context.get("top_strategies", []):
        lines.append(
            "<tr>"
            f"<td>{strategy['rank']}</td>"
            f"<td>{strategy['flow']}</td>"
            f"<td>{strategy['strategy']}</td>"
            f"<td>{strategy['algo']}</td>"
            f"<td>{strategy['test_sharpe']:.4f}</td>"
            f"<td>{strategy['institutional_score']:.4f}</td>"
            f"<td>{strategy['stability']:.4f}</td>"
            "</tr>"
        )
    lines.extend([
        "</tbody>",
        "</table>",
        "</div>",
        "<div class=\"card\">",
        "<h2>Grant Proposals</h2>",
    ])
    for proposal in proposals.get("grant_proposals", []):
        lines.extend([
            "<div class=\"card\">",
            f"<h3>{proposal['proposal_id']} — {proposal['program']}</h3>",
            f"<p>{proposal['summary'].replace(chr(10), '<br/>')}</p>",
            "</div>",
        ])
    lines.extend(["</body>", "</html>"])
    return "\n".join(lines)


def run() -> Dict[str, Any]:
    context = build_top_strategy_baseline()
    proposal_payload = build_grant_proposals(context)

    TOP_STRATEGY_BASELINE_MD.parent.mkdir(parents=True, exist_ok=True)
    TOP_STRATEGY_BASELINE_MD.write_text(render_markdown(context, proposal_payload), encoding="utf-8")

    GRANT_PROPOSALS_JSON.parent.mkdir(parents=True, exist_ok=True)
    GRANT_PROPOSALS_HTML.parent.mkdir(parents=True, exist_ok=True)
    GRANT_PROPOSALS_MD.parent.mkdir(parents=True, exist_ok=True)
    GRANT_PROPOSALS_HTML.write_text(render_html(context, proposal_payload), encoding="utf-8")
    GRANT_PROPOSALS_MD.write_text(render_markdown(context, proposal_payload), encoding="utf-8")

    return {
        "baseline_json": str(TOP_STRATEGY_BASELINE_JSON),
        "baseline_md": str(TOP_STRATEGY_BASELINE_MD),
        "grant_json": str(GRANT_PROPOSALS_JSON),
        "grant_md": str(GRANT_PROPOSALS_MD),
        "grant_html": str(GRANT_PROPOSALS_HTML),
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
