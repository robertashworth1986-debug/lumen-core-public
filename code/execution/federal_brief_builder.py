from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"

EVIDENCE_FILE = OUT / "investor_and_grant_evidence.json"
PREDICTIONS_FILE = OUT / "cross_sector_failure_predictions.jsonl"
CHAIN_FILE = OUT / "infra_chain_of_custody_sha256.json"
INFRA_AUDIT_FILE = OUT / "infra_audit_ledger.jsonl"
ALPACA_EVIDENCE_FILE = OUT / "investor_evidence_report.json"

FEDERAL_BRIEF_JSON = OUT / "federal_brief.json"
FEDERAL_BRIEF_MD = OUT / "federal_brief.md"


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_jsonl(path: Path, limit: int = 5000) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in lines[-max(1, int(limit)):]:
            try:
                payload = json.loads(line)
                if isinstance(payload, dict):
                    rows.append(payload)
            except Exception:
                continue
    except Exception:
        return []
    return rows


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def build_federal_brief() -> Dict[str, Any]:
    evidence = load_json(EVIDENCE_FILE, {})
    chain = load_json(CHAIN_FILE, {})
    alpaca = load_json(ALPACA_EVIDENCE_FILE, {})
    predictions = load_jsonl(PREDICTIONS_FILE, limit=10000)
    audit_events = load_jsonl(INFRA_AUDIT_FILE, limit=300)

    ranked = sorted(
        predictions,
        key=lambda row: _to_float(row.get("projected_failure_cost_usd", 0.0), 0.0),
        reverse=True,
    )
    top_risks = ranked[:5]

    projected = _to_float(evidence.get("projected_failure_cost_usd", 0.0), 0.0)
    avoided = _to_float(evidence.get("estimated_avoided_cost_usd", 0.0), 0.0)
    residual = _to_float(evidence.get("estimated_residual_cost_usd", 0.0), 0.0)
    prevented_pct = (avoided / projected * 100.0) if projected > 0 else 0.0

    summary = {
        "generated_utc": utc_iso(),
        "mission": "cross_sector_failure_prevention_and_cost_avoidance",
        "validation_scope": "local_evidence_bundle_pending_independent_review",
        "program_alignment": list(evidence.get("program_alignment", [])),
        "portfolio": {
            "sector_count": int(evidence.get("sector_count", len({str(r.get('sector', '')) for r in predictions}))),
            "prediction_count": int(len(predictions)),
            "audit_event_count": int(len(audit_events)),
        },
        "financial_impact": {
            "projected_failure_cost_usd": round(projected, 2),
            "estimated_avoided_cost_usd": round(avoided, 2),
            "estimated_residual_cost_usd": round(residual, 2),
            "prevented_pct": round(prevented_pct, 4),
        },
        "top_risks": [
            {
                "sector": str(item.get("sector", "")),
                "stream": str(item.get("stream", "")),
                "constraint": str(item.get("constraint", "")),
                "predicted_failure_utc": str(item.get("predicted_failure_utc", "")),
                "projected_failure_cost_usd": round(_to_float(item.get("projected_failure_cost_usd", 0.0), 0.0), 2),
                "avoided_cost_usd": round(_to_float(item.get("avoided_cost_usd", 0.0), 0.0), 2),
                "confidence": round(_to_float(item.get("confidence", 0.0), 0.0), 4),
            }
            for item in top_risks
        ],
        "alpaca_evidence": {
            "mode": str(alpaca.get("evidence_mode", "unknown")),
            "fills_count": int((alpaca.get("fills") or {}).get("count", 0) if isinstance(alpaca.get("fills"), dict) else 0),
            "equity_usd": _to_float((alpaca.get("capital") or {}).get("latest_equity_usd", 0.0), 0.0) if isinstance(alpaca.get("capital"), dict) else 0.0,
            "win_rate_pct": _to_float((alpaca.get("equity_path") or {}).get("win_rate_pct", 0.0), 0.0) if isinstance(alpaca.get("equity_path"), dict) else 0.0,
            "sharpe_proxy": _to_float((alpaca.get("equity_path") or {}).get("sharpe_proxy", 0.0), 0.0) if isinstance(alpaca.get("equity_path"), dict) else 0.0,
        },
        "chain_of_custody": {
            "hash_file_count": int(len(chain.get("files", []))) if isinstance(chain, dict) else 0,
            "chain_generated_utc": str(chain.get("generated_utc", "")) if isinstance(chain, dict) else "",
        },
        "files": {
            "evidence": str(EVIDENCE_FILE),
            "predictions": str(PREDICTIONS_FILE),
            "chain": str(CHAIN_FILE),
            "alpaca_evidence": str(ALPACA_EVIDENCE_FILE),
        },
    }

    FEDERAL_BRIEF_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def render_markdown(brief: Dict[str, Any]) -> str:
    fi = brief.get("financial_impact", {}) if isinstance(brief, dict) else {}
    top = brief.get("top_risks", []) if isinstance(brief, dict) else []
    lines = [
        "# Federal Brief — LumenCore Cross-Sector Intelligence",
        "",
        f"Generated UTC: {brief.get('generated_utc', '')}",
        f"Validation Scope: {brief.get('validation_scope', '')}",
        f"Program Alignment: {', '.join(brief.get('program_alignment', []))}",
        "",
        "## Financial Impact",
        f"- Projected failure cost: ${fi.get('projected_failure_cost_usd', 0.0):,.2f}",
        f"- Estimated avoided cost: ${fi.get('estimated_avoided_cost_usd', 0.0):,.2f}",
        f"- Residual cost: ${fi.get('estimated_residual_cost_usd', 0.0):,.2f}",
        f"- Prevented percentage: {fi.get('prevented_pct', 0.0):.4f}%",
        "",
        "## Top Risk Signals",
    ]
    if not top:
        lines.append("- No prediction signals found.")
    else:
        for item in top:
            lines.append(
                f"- {item.get('sector','')} / {item.get('constraint','')} | "
                f"Predicted failure: {item.get('predicted_failure_utc','')} | "
                f"Projected: ${item.get('projected_failure_cost_usd',0.0):,.2f} | "
                f"Avoided: ${item.get('avoided_cost_usd',0.0):,.2f} | "
                f"Confidence: {item.get('confidence',0.0):.4f}"
            )

    alp = brief.get("alpaca_evidence", {}) if isinstance(brief, dict) else {}
    lines.extend(
        [
            "",
            "## Financial Engine Evidence",
            f"- Mode: {alp.get('mode', 'unknown')}",
            f"- Fills: {alp.get('fills_count', 0)}",
            f"- Equity: ${alp.get('equity_usd', 0.0):,.2f}",
            f"- Win rate: {alp.get('win_rate_pct', 0.0):.4f}%",
            f"- Sharpe proxy: {alp.get('sharpe_proxy', 0.0):.6f}",
        ]
    )

    return "\n".join(lines)


def run() -> Dict[str, Any]:
    brief = build_federal_brief()
    FEDERAL_BRIEF_MD.write_text(render_markdown(brief), encoding="utf-8")
    return brief


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
