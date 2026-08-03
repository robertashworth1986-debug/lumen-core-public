from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

MULTI_ASSET_PACK = OUT_OPS / "multi_asset_frozen_delta_pack_latest.json"
LIVE_BREADTH_PANEL = OUT_OPS / "live_breadth_value_panel_latest.json"
KEY_GATE = OUT_OPS / "live_breadth_key_gate_latest.json"

OUT_JSON = OUT_OPS / "dollar_claim_gate_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "dollar_claim_gate.json"
OUT_MD = DOCS / "DOLLAR_CLAIM_GATE_2026-06-21.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def as_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def money(value: float) -> str:
    return f"${value:,.2f}"


def lane_gate(row: dict[str, Any]) -> dict[str, Any]:
    hourly = as_float(row.get("estimated_hourly_value_usd"))
    annual = as_float(row.get("estimated_annual_value_usd"))
    baseline = as_float(row.get("baseline_loss_rate_usd_per_hour"))
    gain = as_float(row.get("optimization_gain_pct"))
    measured = as_bool(row.get("measured_source")) and as_bool(row.get("primary_live_evidence"))
    generated = bool(str(row.get("generated_utc") or "").strip())
    baseline_protocol_locked = as_bool(row.get("baseline_protocol_locked"))
    buyer_approved_economic_conversion = as_bool(row.get("buyer_approved_economic_conversion"))
    economic_conversion_source = str(row.get("economic_conversion_source") or "").strip()
    prospective_or_heldout_validation_passed = as_bool(row.get("prospective_or_heldout_validation_passed"))
    uncertainty_bounds_complete = as_bool(row.get("uncertainty_bounds_complete"))
    source = str(row.get("source") or "").strip()
    sector = str(row.get("sector") or "").strip()
    is_tradingish = any(token in (sector + " " + source).lower() for token in ("market", "kraken", "alpaca", "trading", "crypto", "odds"))

    missing: list[str] = []
    if not measured:
        missing.append("live_measured_source")
    if hourly <= 0 or annual <= 0:
        missing.append("positive_estimated_value")
    if baseline <= 0:
        missing.append("baseline_cost_or_loss_rate")
    if gain <= 0:
        missing.append("measured_delta_or_gain")
    if not generated:
        missing.append("generated_timestamp")
    if not baseline_protocol_locked:
        missing.append("baseline_protocol_locked")
    if not buyer_approved_economic_conversion:
        missing.append("buyer_approved_economic_conversion")
    if not economic_conversion_source:
        missing.append("economic_conversion_source")
    if not prospective_or_heldout_validation_passed:
        missing.append("prospective_or_heldout_validation_passed")
    if not uncertainty_bounds_complete:
        missing.append("uncertainty_bounds_complete")

    if missing:
        status = "blocked_context_only"
        allowed_language = (
            "Use only as a test target. The input projection is suppressed and must not be presented as avoided cost, "
            "savings, ROI, revenue, contract value, or government value."
        )
    else:
        status = "estimated_value_signal"
        allowed_language = (
            "Allowed: bounded estimated value signal under stated assumptions. Do not say realized savings, guaranteed ROI, "
            "field validation, customer savings, trading profit, or government value unless separately proven."
        )

    if status == "estimated_value_signal" and is_tradingish:
        allowed_language = (
            "Allowed: paper/read-only estimated value signal for benchmarking. Do not present as trading profit, wagering edge, "
            "investment advice, or live execution performance."
        )

    if status == "estimated_value_signal" and hourly >= 10_000:
        claim_band = "large_estimated_signal"
    elif status == "estimated_value_signal":
        claim_band = "bounded_estimated_signal"
    else:
        claim_band = "not_claimable"

    return {
        "source": source,
        "sector": sector,
        "constraint": str(row.get("constraint") or "default"),
        "status": status,
        "claim_band": claim_band,
        "estimated_hourly_value_usd": round(hourly, 4) if status == "estimated_value_signal" else 0.0,
        "estimated_daily_value_usd": (
            round(as_float(row.get("estimated_daily_value_usd")), 4) if status == "estimated_value_signal" else 0.0
        ),
        "estimated_annual_value_usd": round(annual, 4) if status == "estimated_value_signal" else 0.0,
        "baseline_loss_rate_usd_per_hour": round(baseline, 4) if status == "estimated_value_signal" else 0.0,
        "optimization_gain_pct": round(gain, 4) if status == "estimated_value_signal" else 0.0,
        "input_projection_present": hourly > 0 or annual > 0,
        "input_projection_suppressed": status != "estimated_value_signal",
        "baseline_protocol_locked": baseline_protocol_locked,
        "buyer_approved_economic_conversion": buyer_approved_economic_conversion,
        "economic_conversion_source": economic_conversion_source if status == "estimated_value_signal" else "",
        "prospective_or_heldout_validation_passed": prospective_or_heldout_validation_passed,
        "uncertainty_bounds_complete": uncertainty_bounds_complete,
        "missing_for_stronger_claim": missing,
        "allowed_language": allowed_language,
        "blocked_language": [
            "guaranteed savings",
            "realized savings",
            "government will save",
            "customer ROI proven",
            "field validated",
            "trading profit proven",
            "worth X dollars by itself",
        ],
        "evidence_ref": row.get("evidence_source", "multi_asset_frozen_delta_pack"),
        "generated_utc": row.get("generated_utc", ""),
        "primary_live_evidence": measured,
    }


def build_payload() -> dict[str, Any]:
    pack = read_json(MULTI_ASSET_PACK)
    panel = read_json(LIVE_BREADTH_PANEL)
    key_gate = read_json(KEY_GATE)

    live_rows = pack.get("live_measured_top_lanes", []) if isinstance(pack.get("live_measured_top_lanes"), list) else []
    context_rows = pack.get("context_only_lanes", []) if isinstance(pack.get("context_only_lanes"), list) else []

    evaluated_live = [lane_gate(row) for row in live_rows if isinstance(row, dict)]
    evaluated_context = [lane_gate(row) for row in context_rows if isinstance(row, dict)]
    allowed = [row for row in evaluated_live if row["status"] == "estimated_value_signal"]
    blocked = [row for row in evaluated_live + evaluated_context if row["status"] != "estimated_value_signal"]
    large = [row for row in allowed if row["claim_band"] == "large_estimated_signal"]

    allowed_hourly = sum(as_float(row.get("estimated_hourly_value_usd")) for row in allowed)
    allowed_annual = sum(as_float(row.get("estimated_annual_value_usd")) for row in allowed)
    panel_headline = panel.get("headline", {}) if isinstance(panel.get("headline"), dict) else {}
    key_summary = key_gate.get("summary", {}) if isinstance(key_gate.get("summary"), dict) else {}

    return {
        "generated_utc": now_utc(),
        "schema": "dollar_claim_gate_v2",
        "purpose": "Tell the system when dollar language is allowed, what language is safe, and what is still blocked.",
        "summary": {
            "allowed_estimated_value_claims": len(allowed),
            "large_estimated_signal_claims": len(large),
            "blocked_context_only_claims": len(blocked),
            "allowed_estimated_hourly_value_usd": round(allowed_hourly, 2),
            "allowed_estimated_annual_value_usd": round(allowed_annual, 2),
            "blocked_context_only_annual_value_usd": 0.0,
            "suppressed_input_projection_count": sum(
                1 for row in evaluated_live + evaluated_context if row.get("input_projection_suppressed")
            ),
            "panel_primary_evidence_mode": panel_headline.get("primary_evidence_mode", ""),
            "live_measured_source_row_count": panel_headline.get("live_measured_source_row_count", 0),
            "context_only_estimated_annual_value_usd": 0.0,
            "key_gate_configured_providers": key_summary.get("configured_providers", 0),
            "proof_vault_note": "A terabyte of frozen deltas is storage capacity and provenance leverage, not a dollar claim by itself.",
        },
        "claim_levels": [
            {
                "level": "context_value",
                "when_allowed": "You have a frozen artifact, source metadata, and hypothesis, but no measured delta against a baseline.",
                "safe_phrase": "This is a candidate value surface for testing.",
            },
            {
                "level": "estimated_value_signal",
                "when_allowed": (
                    "Live or authorized representative data, a locked buyer baseline, a buyer-approved economic "
                    "conversion source, held-out or prospective validation, uncertainty bounds, and a timestamped frozen run."
                ),
                "safe_phrase": "This run produced an estimated avoided-cost signal of X under stated assumptions.",
            },
            {
                "level": "validated_avoided_cost",
                "when_allowed": "Pre-registered baseline, held-out validation, uncertainty bounds, multiple-comparison control, and source rights.",
                "safe_phrase": "On frozen validation data, the method reduced the measured cost proxy by X with Y uncertainty.",
            },
            {
                "level": "realized_customer_or_government_savings",
                "when_allowed": "Authorized pilot/customer/government data confirms actual operational savings or loss reduction.",
                "safe_phrase": "In the authorized pilot, measured avoided cost was X over Y period.",
            },
        ],
        "allowed_claim_language": (
            [
                (
                    "Current fully gated lanes support bounded estimated value language up to "
                    f"{money(allowed_hourly)} per hour / {money(allowed_annual)} per year under stated assumptions."
                ),
                "Use estimated, bounded, source-backed, and under-assumptions language.",
                "Separate fully gated lanes from blocked test targets in every dashboard and submission.",
            ]
            if allowed
            else [
                "No current lane clears the dollar-projection gate.",
                "Describe current value only as a buyer-measured pilot hypothesis, without a dollar amount.",
                "Preserve input projections as suppressed test targets until every required gate is evidenced.",
            ]
        ),
        "blocked_claim_language": [
            "Do not publish or aggregate suppressed input projections as a product, contract, savings, or valuation claim.",
            "Do not say guaranteed funding, guaranteed savings, government value, customer ROI, or realized trading profit.",
            "Do not say a terabyte of frozen deltas is worth a fixed amount without reviewed source rights, validated deltas, and buyer relevance.",
        ],
        "next_actions_to_unlock_larger_claims": [
            "For each high-value context-only lane, attach a public/authorized source registry row and mark it measured only after fresh probe or file-hash evidence.",
            "Add uncertainty intervals and a paired baseline comparison for every lane promoted above estimated-value language.",
            "Obtain a named buyer or system owner approval for the baseline and economic conversion before publishing dollars.",
            "Promote government/agency language only when the delta maps to a mission metric such as downtime, response time, false positives, missed detections, energy waste, or review burden.",
            "Keep market/sports lanes as calibration and paper/replay tests unless real-money results are separately audited and legally reviewable.",
            "Use the plugged-in terabyte drive as a proof vault: raw snapshots, manifests, hashes, rendered packets, and reproducible run directories.",
        ],
        "estimated_value_lanes": allowed,
        "context_only_or_blocked_lanes": blocked[:50],
        "inputs": {
            "multi_asset_pack": str(MULTI_ASSET_PACK),
            "live_breadth_panel": str(LIVE_BREADTH_PANEL),
            "key_gate": str(KEY_GATE),
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Dollar Claim Gate",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Answer",
        "",
        (
            "Dollar projections are blocked unless a lane has a locked buyer baseline, buyer-approved economic conversion, "
            "held-out or prospective validation, uncertainty bounds, and source/legal review."
        ),
        "",
        "## Current Gate",
        "",
        f"- Allowed estimated-value lanes: {summary['allowed_estimated_value_claims']}",
        f"- Large estimated-value lanes: {summary['large_estimated_signal_claims']}",
        f"- Blocked/context-only lanes: {summary['blocked_context_only_claims']}",
        f"- Allowed estimated value: {money(summary['allowed_estimated_hourly_value_usd'])}/hour; {money(summary['allowed_estimated_annual_value_usd'])}/year",
        f"- Suppressed input projections: {summary['suppressed_input_projection_count']}",
        f"- Proof vault note: {summary['proof_vault_note']}",
        "",
        "## Claim Levels",
        "",
        "| Level | When Allowed | Safe Phrase |",
        "|---|---|---|",
    ]
    for row in payload["claim_levels"]:
        lines.append(f"| {row['level']} | {row['when_allowed']} | {row['safe_phrase']} |")
    lines.extend(["", "## Allowed Language", ""])
    lines.extend(f"- {item}" for item in payload["allowed_claim_language"])
    lines.extend(["", "## Blocked Language", ""])
    lines.extend(f"- {item}" for item in payload["blocked_claim_language"])
    lines.extend(["", "## Estimated-Value Lanes", ""])
    lines.extend(["| Source | Sector | Status | Hourly | Annual | Allowed Language |", "|---|---|---|---:|---:|---|"])
    for row in payload["estimated_value_lanes"][:20]:
        lines.append(
            f"| {row['source']} | {row['sector']} | {row['status']} | "
            f"{money(as_float(row['estimated_hourly_value_usd']))} | {money(as_float(row['estimated_annual_value_usd']))} | "
            f"{row['allowed_language']} |"
        )
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {item}" for item in payload["next_actions_to_unlock_larger_claims"])
    return "\n".join(lines)


def write_outputs(payload: dict[str, Any]) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    DASHBOARD_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    payload = build_payload()
    write_outputs(payload)
    print(
        json.dumps(
            {
                "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                "allowed_estimated_annual_value_usd": payload["summary"]["allowed_estimated_annual_value_usd"],
                "blocked_context_only_annual_value_usd": payload["summary"]["blocked_context_only_annual_value_usd"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
