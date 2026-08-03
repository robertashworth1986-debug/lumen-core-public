from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

TOP5_PROOF = OUT_OPS / "top5_live_proof_submission_board_latest.json"
DOLLAR_GATE = OUT_OPS / "dollar_claim_gate_latest.json"
LIVE_BREADTH = OUT_OPS / "live_breadth_value_panel_latest.json"
PARITY_AUDIT = OUT_OPS / "luma_context_dashboard_parity_audit_latest.json"
GEOMETRY_FRONTIER = OUT_OPS / "geometry_proof_frontier_board_latest.json"
CROSS_SECTOR_BENCHMARK = OUT_OPS / "kuramoto_cross_sector_benchmark_latest.json"

OUT_JSON = OUT_OPS / "live_proof_value_meter_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "live_proof_value_meter.json"
OUT_MD = DOCS / "LIVE_PROOF_VALUE_METER_2026-06-22.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def money(value: Any) -> str:
    return f"${as_float(value):,.2f}"


def pct_value(pool_usd: float, pct: float) -> float:
    return pool_usd * (pct / 100.0)


def top_rows(rows: list[dict[str, Any]], key: str, limit: int = 5) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: as_float(row.get(key)), reverse=True)[:limit]


def compact_lane(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": str(row.get("source") or ""),
        "sector": str(row.get("sector") or ""),
        "constraint": str(row.get("constraint") or "default"),
        "status": str(row.get("status") or ""),
        "claim_band": str(row.get("claim_band") or ""),
        "estimated_hourly_value_usd": round(as_float(row.get("estimated_hourly_value_usd")), 2),
        "estimated_annual_value_usd": round(as_float(row.get("estimated_annual_value_usd")), 2),
        "baseline_loss_rate_usd_per_hour": round(as_float(row.get("baseline_loss_rate_usd_per_hour")), 2),
        "optimization_gain_pct": round(as_float(row.get("optimization_gain_pct")), 4),
        "primary_live_evidence": bool(row.get("primary_live_evidence")),
        "missing_for_stronger_claim": row.get("missing_for_stronger_claim", [])
        if isinstance(row.get("missing_for_stronger_claim"), list)
        else [],
        "allowed_language": str(row.get("allowed_language") or ""),
    }


def build_sector_capture_math() -> list[dict[str, Any]]:
    pools = [1_000_000_000.0, 10_000_000_000.0, 100_000_000_000.0]
    capture_pcts = [0.01, 0.1, 1.0]
    rows: list[dict[str, Any]] = []
    for pool in pools:
        rows.append(
            {
                "sector_or_loss_pool_usd": pool,
                "capture_examples": [
                    {
                        "improvement_or_capture_pct": pct,
                        "gross_value_usd": round(pct_value(pool, pct), 2),
                    }
                    for pct in capture_pcts
                ],
            }
        )
    return rows


def package_rows(top5: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pkg in top5.get("packages", []):
        if not isinstance(pkg, dict):
            continue
        proof = pkg.get("live_proof", {}) if isinstance(pkg.get("live_proof"), dict) else {}
        rows.append(
            {
                "rank": pkg.get("rank"),
                "package": str(pkg.get("package") or ""),
                "portal": str(pkg.get("portal") or ""),
                "opportunity": str(pkg.get("opportunity") or ""),
                "proposal_specific_live_proof": bool(proof.get("proposal_specific_live_proof")),
                "proof_status": str(proof.get("proof_status") or ""),
                "ready_for_final_submit": bool(pkg.get("ready_for_final_submit")),
                "safe_value_language": (
                    "proposal-specific public evidence is present; this does not imply a dollar or savings claim"
                    if proof.get("proposal_specific_live_proof")
                    else "proposal-specific proof is blocked; no value or submission-readiness claim follows"
                ),
                "blocked": str(pkg.get("final_submit_blocker") or ""),
            }
        )
    return rows


def build_payload() -> dict[str, Any]:
    top5 = read_json(TOP5_PROOF)
    dollar = read_json(DOLLAR_GATE)
    live = read_json(LIVE_BREADTH)
    parity = read_json(PARITY_AUDIT)
    geometry = read_json(GEOMETRY_FRONTIER)
    cross_sector = read_json(CROSS_SECTOR_BENCHMARK)

    proof_gate = top5.get("global_live_proof_gate", {}) if isinstance(top5.get("global_live_proof_gate"), dict) else {}
    dollar_summary = dollar.get("summary", {}) if isinstance(dollar.get("summary"), dict) else {}
    live_headline = live.get("headline", {}) if isinstance(live.get("headline"), dict) else {}
    live_domain = parity.get("live_domain_parity", {}) if isinstance(parity.get("live_domain_parity"), dict) else {}
    geometry_gate = geometry.get("promotion_gate", {}) if isinstance(geometry.get("promotion_gate"), dict) else {}
    cross_sector_gates = (
        cross_sector.get("gates", {}) if isinstance(cross_sector.get("gates"), dict) else {}
    )

    allowed_lanes = [
        compact_lane(row)
        for row in dollar.get("estimated_value_lanes", [])
        if isinstance(row, dict)
    ]
    blocked_lanes = [
        compact_lane(row)
        for row in dollar.get("context_only_or_blocked_lanes", [])
        if isinstance(row, dict)
    ]

    allowed_annual = as_float(dollar_summary.get("allowed_estimated_annual_value_usd"))
    allowed_hourly = as_float(dollar_summary.get("allowed_estimated_hourly_value_usd"))
    blocked_annual = as_float(dollar_summary.get("blocked_context_only_annual_value_usd"))
    proof_count = as_int(proof_gate.get("proposal_specific_live_proof_count"))
    proof_total = as_int(proof_gate.get("proposal_specific_live_proof_total"))
    feed_ok = as_int(live_domain.get("feed_ok"))
    feed_total = as_int(live_domain.get("feed_total"))

    safe_claim = {
        "estimated_value_signal_allowed": allowed_annual > 0 and bool(allowed_lanes),
        "validated_avoided_cost_allowed": False,
        "realized_customer_or_government_savings_allowed": False,
        "trading_profit_claim_allowed": False,
        "grant_final_submit_ready": bool(proof_gate.get("ready_for_any_final_submit")),
        "live_domain_data_feed_ready": feed_total > 0 and feed_ok == feed_total,
        "geometry_live_dollar_claim_ready": bool(geometry_gate.get("ready_for_real_dollar_claim")),
        "claim_boundary": (
            "Allowed numbers are bounded estimated value signals under stated assumptions. "
            "They are not realized revenue, guaranteed savings, customer ROI, or government savings."
        ),
    }

    proof_to_value_formula = {
        "sector_math": "For every $1B of relevant loss pool, 0.01% improvement equals $100,000 of gross avoided-cost surface.",
        "generic_formula": "estimated_value = baseline_loss_or_cost_rate * measured_delta_pct * time_window",
        "priceable_formula": "priceable_contract_surface = estimated_value * buyer_relevance * capture_rate * proof_confidence",
        "required_before_pricing": [
            "source rights or public-data basis",
            "frozen manifest and hash",
            "baseline comparison on identical windows",
            "leakage-control statement",
            "uncertainty or holdout plan",
            "buyer/agency mission metric mapping",
        ],
    }

    capture_from_allowed_signal = [
        {
            "capture_rate_pct": pct,
            "illustrative_contract_surface_usd_per_year": round(pct_value(allowed_annual, pct), 2),
            "boundary": "Illustrative pricing surface only; not revenue unless sold, awarded, or piloted.",
        }
        for pct in [0.5, 1.0, 5.0, 10.0]
    ]

    payload = {
        "generated_utc": now_utc(),
        "schema": "live_proof_value_meter_v2",
        "purpose": "Connect live proof, grant readiness, live breadth, and safe economic-value language without inflating claims.",
        "answer": {
            "undeniable_live_proof_now": False,
            "current_state": (
                f"{proof_count}/{proof_total} grant packages have proposal-specific bounded live/public proof. "
                "The system has useful evidence, but not yet an undeniable field-validated proof stack."
            ),
            "what_is_safe_now": (
                (
                    f"A fully gated estimated-value signal up to {money(allowed_hourly)}/hour and "
                    f"{money(allowed_annual)}/year under stated assumptions."
                )
                if allowed_annual > 0 and allowed_lanes
                else (
                    "No dollar projection is currently claimable. Product value must be measured against a "
                    "buyer-approved workflow or operational baseline in a bounded pilot."
                )
            ),
            "what_is_not_safe": (
                "Do not claim guaranteed funding, realized customer savings, government savings, field validation, "
                "trading profit, or fixed value for frozen deltas."
            ),
        },
        "proof_gate": {
            "proposal_specific_live_proof_count": proof_count,
            "proposal_specific_live_proof_total": proof_total,
            "packages_with_live_proof": proof_gate.get("packages_with_live_proof", []),
            "packages_missing_live_proof": proof_gate.get("packages_missing_live_proof", []),
            "ready_for_any_final_submit": bool(proof_gate.get("ready_for_any_final_submit")),
            "rule": str(proof_gate.get("rule") or ""),
        },
        "value_gate": {
            "allowed_estimated_value_claims": as_int(dollar_summary.get("allowed_estimated_value_claims")),
            "allowed_estimated_hourly_value_usd": round(allowed_hourly, 2),
            "allowed_estimated_annual_value_usd": round(allowed_annual, 2),
            "live_breadth_raw_live_measured_annual_value_usd": 0.0,
            "blocked_context_only_annual_value_usd": round(blocked_annual, 2),
            "ungated_input_projections_suppressed": allowed_annual <= 0 or not allowed_lanes,
            "panel_primary_evidence_mode": str(dollar_summary.get("panel_primary_evidence_mode") or live_headline.get("primary_evidence_mode") or ""),
            "live_measured_source_rows": as_int(dollar_summary.get("live_measured_source_row_count") or live_headline.get("live_measured_source_row_count")),
            "safe_claim": safe_claim,
        },
        "sector_capture_math": build_sector_capture_math(),
        "capture_from_allowed_signal": capture_from_allowed_signal,
        "proof_to_value_formula": proof_to_value_formula,
        "evidence_to_contract_workflow": [
            {"stage": "sense", "meaning": "Pull public/authorized live breadth and market/sector signals."},
            {"stage": "freeze", "meaning": "Hash raw rows, inputs, seeds, baselines, and replay windows."},
            {"stage": "beat", "meaning": "Run the method and baselines on the same frozen windows."},
            {"stage": "gate", "meaning": "Promote only lanes that pass source, leakage, baseline, and claim gates."},
            {"stage": "price", "meaning": "Convert measured improvement into avoided-cost or review-burden value under assumptions."},
            {"stage": "fund", "meaning": "Use grant, contract, pilot, or license language tied to the proven metric."},
        ],
        "package_value_readiness": package_rows(top5),
        "top_safe_estimated_value_lanes": top_rows(allowed_lanes, "estimated_annual_value_usd", 8),
        "top_blocked_context_value_lanes": top_rows(blocked_lanes, "estimated_annual_value_usd", 8),
        "dashboard_feed_manifest": {
            "local_ready_feeds": [
                "dashboard/data/live_proof_value_meter.json",
                "dashboard/data/dollar_claim_gate.json",
                "dashboard/data/top5_live_proof_submission_board.json",
                "dashboard/data/geometry_proof_frontier_board.json",
                "dashboard/data/grant_readiness_status.json",
            ],
            "live_domain_feed_ok": feed_ok,
            "live_domain_feed_total": feed_total,
            "live_domain_state": str(live_domain.get("parity_state") or "unknown"),
            "boundary": str(live_domain.get("boundary") or "Live-domain feed deployment must be verified before reviewer-facing live claims."),
        },
        "current_model_benchmark": {
            "status": str(cross_sector.get("status") or "CURRENT_CROSS_SECTOR_BENCHMARK_MISSING"),
            "sector_gain_proven_count": as_int(cross_sector_gates.get("sector_gain_proven_count")),
            "sector_count": as_int(cross_sector_gates.get("sector_count")),
            "cross_sector_efficiency_claim_allowed": bool(
                cross_sector_gates.get("cross_sector_efficiency_claim_allowed")
            ),
            "dollar_projection_from_forecast_error_allowed": bool(
                cross_sector_gates.get("dollar_projection_from_forecast_error_allowed")
            ),
            "boundary": str(cross_sector.get("claim_boundary") or ""),
        },
        "next_actions": [
            "Deploy or route fresh dashboard/data JSON feeds to the live domain so reviewer-facing pages hydrate with the same proof state.",
            "Promote high-value context-only lanes only after public/authorized source rows, hashes, and identical baseline replays exist.",
            "Build proposal-specific proof for NSF Project Pitch, MissionWeave, and NV065 before treating those submissions as evidence-backed.",
            "Map each dollar claim to a mission metric: downtime, review burden, missed detection, energy waste, response time, or constraint violation.",
            "Keep trading and sports data as paper/read-only calibration until a separately audited realized track record exists.",
        ],
        "inputs": {
            "top5_proof": str(TOP5_PROOF),
            "dollar_gate": str(DOLLAR_GATE),
            "live_breadth": str(LIVE_BREADTH),
            "parity_audit": str(PARITY_AUDIT),
            "geometry_frontier": str(GEOMETRY_FRONTIER),
            "cross_sector_benchmark": str(CROSS_SECTOR_BENCHMARK),
        },
    }
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    answer = payload["answer"]
    proof = payload["proof_gate"]
    value = payload["value_gate"]
    safe = value["safe_claim"]
    lines = [
        "# Live Proof Value Meter",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Direct Answer",
        "",
        f"- Undeniable live proof now: `{answer['undeniable_live_proof_now']}`",
        f"- Current state: {answer['current_state']}",
        f"- Safe now: {answer['what_is_safe_now']}",
        f"- Not safe: {answer['what_is_not_safe']}",
        "",
        "## Gates",
        "",
        f"- Grant live proof gate: {proof['proposal_specific_live_proof_count']}/{proof['proposal_specific_live_proof_total']}",
        f"- Any final submit ready: `{proof['ready_for_any_final_submit']}`",
        f"- Estimated value signal allowed: `{safe['estimated_value_signal_allowed']}`",
        f"- Realized savings allowed: `{safe['realized_customer_or_government_savings_allowed']}`",
        f"- Trading profit claim allowed: `{safe['trading_profit_claim_allowed']}`",
        f"- Live domain data feed ready: `{safe['live_domain_data_feed_ready']}`",
        "",
        "## Current Safe Value Signal",
        "",
        f"- Allowed estimated hourly value: {money(value['allowed_estimated_hourly_value_usd'])}",
        f"- Allowed estimated annual value: {money(value['allowed_estimated_annual_value_usd'])}",
        f"- Blocked/context-only annual surface: {money(value['blocked_context_only_annual_value_usd'])}",
        "",
        "## Billion-Dollar Sector Math",
        "",
        "For every $1B relevant loss pool, 0.01% improvement equals $100,000 gross avoided-cost surface. It becomes a real claim only after proof, source rights, and buyer relevance are established.",
        "",
        "## Top Safe Lanes",
        "",
        "| Source | Sector | Hourly | Annual | Boundary |",
        "|---|---|---:|---:|---|",
    ]
    for row in payload["top_safe_estimated_value_lanes"][:8]:
        lines.append(
            f"| {row['source']} | {row['sector']} | {money(row['estimated_hourly_value_usd'])} | "
            f"{money(row['estimated_annual_value_usd'])} | {row['allowed_language']} |"
        )
    lines.extend(["", "## Top Blocked Context Lanes", "", "| Source | Sector | Annual Surface | Missing |", "|---|---|---:|---|"])
    for row in payload["top_blocked_context_value_lanes"][:8]:
        missing = ", ".join(row.get("missing_for_stronger_claim") or [])
        lines.append(f"| {row['source']} | {row['sector']} | {money(row['estimated_annual_value_usd'])} | {missing} |")
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {item}" for item in payload["next_actions"])
    return "\n".join(lines)


def write_outputs(payload: dict[str, Any]) -> None:
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))


def main() -> int:
    payload = build_payload()
    write_outputs(payload)
    print(
        json.dumps(
            {
                "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                "proof_gate": f"{payload['proof_gate']['proposal_specific_live_proof_count']}/{payload['proof_gate']['proposal_specific_live_proof_total']}",
                "allowed_estimated_annual_value_usd": payload["value_gate"]["allowed_estimated_annual_value_usd"],
                "live_domain_state": payload["dashboard_feed_manifest"]["live_domain_state"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
