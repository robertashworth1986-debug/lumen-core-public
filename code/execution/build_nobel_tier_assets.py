from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
DASH = ROOT / "dashboard"
BUNDLE = OUT / "INSTITUTIONAL_REVIEW_BUNDLE"
ROOT_PARENT = ROOT.parent

FEDERAL_BRIEF = OUT / "federal_brief.json"
OPT_REPORT = OUT / "cross_sector_optimization_report.json"
GRANT_EVIDENCE = OUT / "investor_and_grant_evidence.json"
CHAIN_FILE = OUT / "infra_chain_of_custody_sha256.json"
ALPACA_EVIDENCE = OUT / "investor_evidence_report.json"
INVESTOR_BRIEF = ROOT / "INVESTOR_BRIEF.md"

NOBEL_DASHBOARD = DASH / "nobel_tier_command_center.html"
SLIDES_JSON = BUNDLE / "nobel_tier_slides.json"
SLIDES_MD = BUNDLE / "nobel_tier_powerpoint_slides.md"
EXEC_SUMMARY_JSON = BUNDLE / "nobel_tier_executive_summary.json"


def _latest_patent_tracker() -> Path | None:
    ops_dir = ROOT_PARENT / "out" / "ops"
    if not ops_dir.exists():
        return None
    candidates = sorted(ops_dir.glob("patent_filing_tracker_*.json"))
    if not candidates:
        return None
    return candidates[-1]


def extract_valuation_bands() -> list[str]:
    if not INVESTOR_BRIEF.exists():
        return []
    try:
        lines = INVESTOR_BRIEF.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []

    in_section = False
    out: list[str] = []
    for line in lines:
        text = line.strip()
        if text.lower().startswith("### valuation positioning bands"):
            in_section = True
            continue
        if in_section and text.startswith("### "):
            break
        if in_section and text.startswith("- "):
            out.append(text[2:].strip())
    return out[:8]


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "$0.00"


def pct(value: Any) -> str:
    try:
        return f"{float(value):.4f}%"
    except Exception:
        return "0.0000%"


def build_dashboard_html(
    federal: Dict[str, Any],
    opt: Dict[str, Any],
    evidence: Dict[str, Any],
    chain: Dict[str, Any],
    alpaca: Dict[str, Any],
    patent: Dict[str, Any],
    valuation_bands: List[str],
) -> str:
    impact = federal.get("financial_impact", {}) if isinstance(federal, dict) else {}
    top_risks = federal.get("top_risks", []) if isinstance(federal, dict) else []
    recommended = opt.get("recommended", {}) if isinstance(opt, dict) else {}
    chain_files = chain.get("files", []) if isinstance(chain, dict) else []
    app_anchor = patent.get("application_anchor", {}) if isinstance(patent, dict) else {}
    patent_files = patent.get("evidence_files", []) if isinstance(patent, dict) else []

    rows = []
    for idx, risk in enumerate(top_risks[:8], start=1):
        rows.append(
            f"<tr>"
            f"<td>{idx}</td>"
            f"<td>{risk.get('sector','')}</td>"
            f"<td>{risk.get('constraint','')}</td>"
            f"<td>{risk.get('predicted_failure_utc','')}</td>"
            f"<td>{money(risk.get('projected_failure_cost_usd',0.0))}</td>"
            f"<td>{money(risk.get('avoided_cost_usd',0.0))}</td>"
            f"<td>{float(risk.get('confidence',0.0) or 0.0):.4f}</td>"
            f"</tr>"
        )

    hash_rows = []
    for item in chain_files[:12]:
        path = str(item.get("path", ""))
        digest = str(item.get("sha256", ""))
        hash_rows.append(
            f"<tr><td>{path}</td><td class='mono'>{digest}</td></tr>"
        )

    patent_rows = []
    for item in patent_files[:8]:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", ""))
        digest = str(item.get("sha256", ""))
        patent_rows.append(f"<tr><td>{path}</td><td class='mono'>{digest}</td></tr>")

    valuation_html = "".join(f"<li>{v}</li>" for v in valuation_bands)

    return f"""<!doctype html>
<html>
<head>
<meta charset='utf-8' />
<meta name='viewport' content='width=device-width, initial-scale=1' />
<title>LumenCore Nobel-Tier Command Center</title>
<style>
:root {{ --bg:#050913; --panel:#0f1a2e; --line:#21395f; --txt:#e8f2ff; --muted:#95afd1; --good:#74f0b6; --cyan:#48d7ff; --gold:#ffd166; --mono:Consolas, monospace; }}
body {{ margin:0; padding:24px; background:radial-gradient(circle at 10% 0%, #14305a 0%, transparent 30%), var(--bg); color:var(--txt); font-family:Segoe UI, Arial, sans-serif; }}
.wrap {{ max-width:1600px; margin:0 auto; }}
h1 {{ margin:0 0 6px; font-size:40px; }}
.sub {{ color:var(--muted); margin-bottom:16px; }}
.grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:16px; }}
.card {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:14px; }}
.k {{ color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.09em; }}
.v {{ font-size:30px; margin-top:8px; color:var(--good); }}
.v2 {{ font-size:22px; margin-top:8px; color:var(--cyan); }}
.table {{ width:100%; border-collapse:collapse; background:var(--panel); border:1px solid var(--line); border-radius:14px; overflow:hidden; }}
th, td {{ padding:10px; border-bottom:1px solid var(--line); text-align:left; font-size:12px; }}
th {{ color:var(--muted); font-size:10px; text-transform:uppercase; letter-spacing:.1em; }}
.mono {{ font-family:var(--mono); font-size:11px; word-break:break-all; }}
.section {{ margin-top:16px; }}
</style>
</head>
<body>
<div class='wrap'>
  <h1>LumenCore Nobel-Tier Command Center</h1>
  <div class='sub'>Cross-sector failure intelligence, optimized prevention economics, and hash-verifiable chain-of-custody evidence.</div>

  <div class='grid'>
    <div class='card'><div class='k'>Projected Failure Cost</div><div class='v'>{money(impact.get('projected_failure_cost_usd',0.0))}</div></div>
    <div class='card'><div class='k'>Estimated Avoided Cost</div><div class='v'>{money(impact.get('estimated_avoided_cost_usd',0.0))}</div></div>
    <div class='card'><div class='k'>Residual Cost</div><div class='v'>{money(impact.get('estimated_residual_cost_usd',0.0))}</div></div>
    <div class='card'><div class='k'>Prevention Rate</div><div class='v'>{pct(impact.get('prevented_pct',0.0))}</div></div>
  </div>

  <div class='grid'>
    <div class='card'><div class='k'>Optimization Sims Run</div><div class='v2'>{int(opt.get('sims_run',0) or 0)}</div></div>
    <div class='card'><div class='k'>Best Detection Efficiency</div><div class='v2'>{float(recommended.get('lumen_detection_efficiency',0.0) or 0.0):.6f}</div></div>
    <div class='card'><div class='k'>Best Mitigation Multiplier</div><div class='v2'>{float(recommended.get('mitigation_multiplier',0.0) or 0.0):.6f}</div></div>
    <div class='card'><div class='k'>Hash-Proven Files</div><div class='v2'>{len(chain_files)}</div></div>
  </div>

  <div class='section'>
    <h3>Top Risk Signal Queue</h3>
    <table class='table'>
      <thead><tr><th>#</th><th>Sector</th><th>Constraint</th><th>Predicted Failure UTC</th><th>Projected Cost</th><th>Avoided</th><th>Confidence</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>

  <div class='section'>
        <h3>Patent Anchor and Valuation Positioning</h3>
        <table class='table'>
            <thead><tr><th>Field</th><th>Value</th></tr></thead>
            <tbody>
                <tr><td>USPTO Application</td><td>{app_anchor.get('uspto_application','')}</td></tr>
                <tr><td>Patent Center Reference</td><td>{app_anchor.get('patent_center_reference','')}</td></tr>
                <tr><td>Confirmation Number</td><td>{app_anchor.get('confirmation_number','')}</td></tr>
                <tr><td>Receipt Timestamp</td><td>{app_anchor.get('receipt_timestamp_et','')}</td></tr>
                <tr><td>Title</td><td>{app_anchor.get('title','')}</td></tr>
            </tbody>
        </table>
        <div class='card' style='margin-top:12px;'>
            <div class='k'>Valuation Positioning Bands</div>
            <ul>{valuation_html}</ul>
        </div>
    </div>

    <div class='section'>
    <h3>Chain of Custody (SHA-256)</h3>
    <table class='table'>
      <thead><tr><th>Artifact</th><th>SHA-256</th></tr></thead>
      <tbody>{''.join(hash_rows)}</tbody>
    </table>
  </div>

    <div class='section'>
        <h3>Patent Evidence File Hashes</h3>
        <table class='table'>
            <thead><tr><th>Artifact</th><th>SHA-256</th></tr></thead>
            <tbody>{''.join(patent_rows)}</tbody>
        </table>
    </div>
</div>
</body>
</html>"""


def build_slide_pack(
    federal: Dict[str, Any],
    opt: Dict[str, Any],
    evidence: Dict[str, Any],
    chain: Dict[str, Any],
    alpaca: Dict[str, Any],
    patent: Dict[str, Any],
    valuation_bands: List[str],
) -> Dict[str, Any]:
    impact = federal.get("financial_impact", {}) if isinstance(federal, dict) else {}
    recommended = opt.get("recommended", {}) if isinstance(opt, dict) else {}
    top_risks = federal.get("top_risks", []) if isinstance(federal, dict) else []
    app_anchor = patent.get("application_anchor", {}) if isinstance(patent, dict) else {}

    slides = [
        {
            "slide": 1,
            "title": "LumenCore Command Authority",
            "bullets": [
                "Cross-sector failure intelligence with immutable evidence chain",
                f"Projected risk currently monitored: {money(impact.get('projected_failure_cost_usd',0.0))}",
                f"Estimated avoided impact: {money(impact.get('estimated_avoided_cost_usd',0.0))}",
                f"Prevention rate: {pct(impact.get('prevented_pct',0.0))}",
            ],
        },
        {
            "slide": 2,
            "title": "Optimization Engine (Compute-Efficient)",
            "bullets": [
                f"Bounded simulations executed: {int(opt.get('sims_run',0) or 0)}",
                f"Best detection efficiency: {float(recommended.get('lumen_detection_efficiency',0.0) or 0.0):.6f}",
                f"Best mitigation multiplier: {float(recommended.get('mitigation_multiplier',0.0) or 0.0):.6f}",
                f"Residual risk under best parameters: {money(recommended.get('residual_cost_usd',0.0))}",
            ],
        },
        {
            "slide": 3,
            "title": "Top Predicted Risk Events",
            "bullets": [
                f"{r.get('sector','')} / {r.get('constraint','')} | failure ETA {r.get('predicted_failure_utc','')} | projected {money(r.get('projected_failure_cost_usd',0.0))}"
                for r in top_risks[:5]
            ] or ["No risk events available"],
        },
        {
            "slide": 4,
            "title": "Patent and Valuation Anchors",
            "bullets": [
                f"USPTO application: {app_anchor.get('uspto_application','')}",
                f"Patent Center reference: {app_anchor.get('patent_center_reference','')}",
                f"Confirmation number: {app_anchor.get('confirmation_number','')}",
                f"Receipt timestamp: {app_anchor.get('receipt_timestamp_et','')}",
            ] + valuation_bands[:4],
        },
        {
            "slide": 5,
            "title": "Integrity and Chain of Custody",
            "bullets": [
                f"SHA-256 hashed artifacts: {len((chain.get('files',[]) if isinstance(chain,dict) else []))}",
                "Append-only JSONL ledgers for deltas, predictions, and audit cycles",
                "Atomic writes for report snapshots and governance artifacts",
                "Federal brief generated with traceable source files and timestamps",
            ],
        },
        {
            "slide": 6,
            "title": "Deployment Track",
            "bullets": [
                "24/7 federal brief daemon active with heartbeat and run ledger",
                "Cross-sector + financial evidence unified for institutional review",
                "Scale path: add live sector feeds and policy attestation bundles",
                "Target outcome: measurable resilience gains at national-scale sectors",
            ],
        },
    ]

    return {
        "generated_utc": utc_iso(),
        "deck_name": "Nobel Tier Command Deck",
        "slide_count": len(slides),
        "slides": slides,
        "source_files": {
            "federal_brief": str(FEDERAL_BRIEF),
            "optimization": str(OPT_REPORT),
            "grant_evidence": str(GRANT_EVIDENCE),
            "chain": str(CHAIN_FILE),
            "alpaca": str(ALPACA_EVIDENCE),
        },
    }


def render_slide_markdown(slide_pack: Dict[str, Any]) -> str:
    lines = [
        "# Nobel Tier PowerPoint Slides (Authoring Pack)",
        "",
        f"Generated UTC: {slide_pack.get('generated_utc','')}",
        "",
        "Use each `## Slide` section as one PowerPoint slide.",
        "",
    ]
    for slide in slide_pack.get("slides", []):
        lines.append(f"## Slide {slide.get('slide', 0)} — {slide.get('title','')}")
        for bullet in slide.get("bullets", []):
            lines.append(f"- {bullet}")
        lines.append("")
    return "\n".join(lines)


def run() -> Dict[str, Any]:
    DASH.mkdir(parents=True, exist_ok=True)
    BUNDLE.mkdir(parents=True, exist_ok=True)

    federal = load_json(FEDERAL_BRIEF, {})
    opt = load_json(OPT_REPORT, {})
    evidence = load_json(GRANT_EVIDENCE, {})
    chain = load_json(CHAIN_FILE, {})
    alpaca = load_json(ALPACA_EVIDENCE, {})
    patent_tracker_path = _latest_patent_tracker()
    patent = load_json(patent_tracker_path, {}) if patent_tracker_path else {}
    valuation_bands = extract_valuation_bands()

    html = build_dashboard_html(federal, opt, evidence, chain, alpaca, patent, valuation_bands)
    NOBEL_DASHBOARD.write_text(html, encoding="utf-8")

    slide_pack = build_slide_pack(federal, opt, evidence, chain, alpaca, patent, valuation_bands)
    SLIDES_JSON.write_text(json.dumps(slide_pack, indent=2), encoding="utf-8")
    SLIDES_MD.write_text(render_slide_markdown(slide_pack), encoding="utf-8")

    app_anchor = patent.get("application_anchor", {}) if isinstance(patent, dict) else {}

    executive = {
        "generated_utc": utc_iso(),
        "dashboard": str(NOBEL_DASHBOARD),
        "slides_json": str(SLIDES_JSON),
        "slides_markdown": str(SLIDES_MD),
        "patent_tracker": str(patent_tracker_path) if patent_tracker_path else "",
        "patent_anchor": {
            "uspto_application": str(app_anchor.get("uspto_application") or ""),
            "patent_center_reference": str(app_anchor.get("patent_center_reference") or ""),
            "confirmation_number": str(app_anchor.get("confirmation_number") or ""),
            "receipt_timestamp_et": str(app_anchor.get("receipt_timestamp_et") or ""),
            "title": str(app_anchor.get("title") or ""),
        },
        "valuation_positioning_bands": valuation_bands,
        "headline": {
            "projected_failure_cost_usd": float((federal.get("financial_impact") or {}).get("projected_failure_cost_usd", 0.0) or 0.0),
            "estimated_avoided_cost_usd": float((federal.get("financial_impact") or {}).get("estimated_avoided_cost_usd", 0.0) or 0.0),
            "prevented_pct": float((federal.get("financial_impact") or {}).get("prevented_pct", 0.0) or 0.0),
            "sims_run": int(opt.get("sims_run", 0) or 0),
        },
    }
    EXEC_SUMMARY_JSON.write_text(json.dumps(executive, indent=2), encoding="utf-8")
    return executive


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
