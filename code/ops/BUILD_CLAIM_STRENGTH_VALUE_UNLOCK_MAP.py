from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

DOLLAR_GATE_JSON = OUT_OPS / "dollar_claim_gate_latest.json"
DOLLAR_GATE_SCRIPT = ROOT / "code" / "ops" / "BUILD_DOLLAR_CLAIM_GATE.py"
CONTROL_ROOM_JSON = OUT_OPS / "proof_to_pilot_control_room_latest.json"
CONTROL_ROOM_SCRIPT = ROOT / "code" / "ops" / "BUILD_PROOF_TO_PILOT_CONTROL_ROOM.py"
OUTREACH_QUEUE_JSON = OUT_OPS / "paid_pilot_outreach_queue_latest.json"
OUTREACH_QUEUE_SCRIPT = ROOT / "code" / "ops" / "BUILD_PAID_PILOT_OUTREACH_QUEUE.py"
ASSET_MAP_JSON = OUT_OPS / "geometry_champion_asset_map_latest.json"

OUT_JSON = OUT_OPS / "claim_strength_value_unlock_map_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "claim_strength_value_unlock_map.json"
OUT_MD = DOCS / "CLAIM_STRENGTH_VALUE_UNLOCK_MAP_2026-06-25.md"

BOUNDARY = (
    "This artifact converts the current proof stack into the strongest defensible claim ladder. It supports "
    "bounded estimated-value language, paid technical evaluation scoping, and buyer-authorized field replay. "
    "It does not authorize realized-savings claims, fixed-dollar frozen-delta pricing, award certainty, "
    "bulk outreach, live trading, or autonomous operational execution."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def money(value: Any) -> str:
    try:
        amount = float(value)
    except Exception:
        amount = 0.0
    return f"${amount:,.2f}"


def load_or_build(path: Path, script: Path, expected_key: str) -> dict[str, Any]:
    payload = read_json(path)
    if payload.get(expected_key):
        return payload

    spec = importlib.util.spec_from_file_location(f"loader_{script.stem.lower()}", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.build_payload()


def repeat_cards(control_room: dict[str, Any]) -> list[dict[str, Any]]:
    cards = control_room.get("top_cards", [])
    return [row for row in cards if isinstance(row, dict)]


def top_queue_rows(queue_payload: dict[str, Any], limit: int = 12) -> list[dict[str, Any]]:
    rows = queue_payload.get("queue", [])
    return [row for row in rows if isinstance(row, dict)][:limit]


def build_claim_ladder(
    dollar_gate: dict[str, Any],
    control_room: dict[str, Any],
    outreach_queue: dict[str, Any],
) -> list[dict[str, Any]]:
    summary = dollar_gate.get("summary", {}) if isinstance(dollar_gate.get("summary"), dict) else {}
    control_summary = control_room.get("summary", {}) if isinstance(control_room.get("summary"), dict) else {}
    queue_summary = outreach_queue.get("summary", {}) if isinstance(outreach_queue.get("summary"), dict) else {}

    return [
        {
            "level": 1,
            "claim_stage": "candidate_context",
            "current_status": "allowed",
            "safe_claim": "Candidate geometry and source lanes are available for controlled testing.",
            "money_language": "No dollar claim.",
            "evidence_basis": "Frozen artifacts, source inventory, and benchmark hypotheses.",
            "blocked_until": [],
        },
        {
            "level": 2,
            "claim_stage": "bounded_estimated_value_signal",
            "current_status": "allowed",
            "safe_claim": (
                "Current live-measured lanes support bounded estimated-value language up to "
                f"{money(summary.get('allowed_estimated_hourly_value_usd'))}/hour and "
                f"{money(summary.get('allowed_estimated_annual_value_usd'))}/year under stated assumptions."
            ),
            "money_language": "Estimated value signal only; not revenue, ROI, or realized savings.",
            "evidence_basis": (
                f"{summary.get('allowed_estimated_value_claims', 0)} measured estimated-value lanes with "
                f"{summary.get('live_measured_source_row_count', 0)} live-measured source rows."
            ),
            "blocked_until": [
                "held-out validation",
                "uncertainty bounds per lane",
                "source-rights review",
                "buyer-approved economic conversion factors",
            ],
        },
        {
            "level": 3,
            "claim_stage": "repeat_window_geometry_candidate",
            "current_status": "allowed",
            "safe_claim": (
                "Two geometry families currently show repeat-window frozen replay strength: "
                "brachistochrone_descent and kuramoto_phase_coupling."
            ),
            "money_language": "Can support technical evaluation value, not customer savings.",
            "evidence_basis": (
                f"{control_summary.get('robust_candidate_count', 0)} robust repeat candidates from the "
                "proof-to-pilot control room."
            ),
            "blocked_until": [
                "pre-registered holdout windows",
                "incumbent baselines under identical constraints",
                "buyer or agency authorized replay data",
            ],
        },
        {
            "level": 4,
            "claim_stage": "paid_pilot_scoping",
            "current_status": "allowed",
            "safe_claim": "The strongest current commercial offer is a paid technical evaluation or buyer-authorized field replay.",
            "money_language": "Paid evaluation can be quoted after fit, scope, rights, and baseline review.",
            "evidence_basis": (
                f"{queue_summary.get('queue_count', 0)} manual outreach rows matched to the two strongest proof cards."
            ),
            "blocked_until": [
                "named buyer problem",
                "data rights",
                "physical/compliance review for outreach",
                "signed scope",
            ],
        },
        {
            "level": 5,
            "claim_stage": "validated_avoided_cost",
            "current_status": "blocked",
            "safe_claim": "Not yet claimable.",
            "money_language": "Avoided-cost claims are blocked.",
            "evidence_basis": "Current evidence is not yet buyer-authorized field validation.",
            "blocked_until": [
                "pre-registered validation plan",
                "buyer-approved holdout data",
                "baseline comparison",
                "uncertainty interval",
                "auditable result artifact",
            ],
        },
        {
            "level": 6,
            "claim_stage": "realized_savings_or_license_value",
            "current_status": "blocked",
            "safe_claim": "Not yet claimable.",
            "money_language": "Do not state realized savings, guaranteed ROI, or fixed frozen-delta value.",
            "evidence_basis": "Requires a completed buyer or agency pilot with accepted economics.",
            "blocked_until": [
                "customer or government accepted result",
                "economic conversion factors",
                "signed result packet or equivalent audit trail",
                "legal/commercial review",
            ],
        },
    ]


def build_geometry_note() -> dict[str, Any]:
    return {
        "question": "Is the Flower of Life a bunch of circles, and are circles waves?",
        "answer": (
            "The Flower of Life is an overlapping equal-radius circle lattice, usually arranged in hexagonal packing. "
            "A circle is not a wave by itself. A circular wavefront is what a wave can look like when energy spreads "
            "evenly from a point source, and circular phase contours are common in resonance, interference, and field propagation."
        ),
        "testable_families": [
            "flower_of_life_hex_circle_lattice",
            "circular_wavefront_interference",
            "phase_ring_resonance",
            "hex_packing_transport",
            "standing_wave_nodal_circles",
        ],
        "claim_boundary": "Use circle/Flower-of-Life geometry as a candidate prior until it beats baselines on frozen replay or live-authorized data.",
    }


def build_money_worth_answer(dollar_gate: dict[str, Any], control_room: dict[str, Any]) -> dict[str, Any]:
    summary = dollar_gate.get("summary", {}) if isinstance(dollar_gate.get("summary"), dict) else {}
    control_summary = control_room.get("summary", {}) if isinstance(control_room.get("summary"), dict) else {}
    return {
        "plain_answer": (
            "Worth money now as a paid technical evaluation or buyer-authorized pilot option, not yet as a fixed-value "
            "asset sale or realized-savings claim."
        ),
        "defensible_value_signal": {
            "estimated_hourly_value_usd": summary.get("allowed_estimated_hourly_value_usd", 0),
            "estimated_annual_value_usd": summary.get("allowed_estimated_annual_value_usd", 0),
            "language": "bounded estimated value signal under stated assumptions",
        },
        "blocked_big_number": {
            "context_only_annual_value_usd": summary.get("blocked_context_only_annual_value_usd", 0),
            "language": "context-only value surface; do not present as real savings or revenue",
        },
        "most_defensible_offers": [
            "paid evidence review",
            "buyer-authorized field replay",
            "grant or contract evidence appendix",
            "technical due-diligence data room",
        ],
        "current_commercial_stage": control_summary.get("current_commercial_stage", "unknown"),
    }


def build_highest_value_unlocks() -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "unlock": "Convert brachistochrone_descent into a buyer-authorized constrained-routing replay.",
            "target_lanes": ["datacenter_cooling_optimization", "utility_grid_analytics", "port_maritime_operations"],
            "why_it_matters": "It maps directly to route/path/constraint problems where small improvements can have measurable operating value.",
            "proof_needed": "20 or more pre-registered holdout windows, incumbent baselines, buyer-approved conversion factors.",
        },
        {
            "priority": 2,
            "unlock": "Convert kuramoto_phase_coupling into a timing/forecast/reliability replay.",
            "target_lanes": ["energy_forecasting", "grid_reliability_analytics", "sensor_fusion_defense"],
            "why_it_matters": "Phase, drift, and timing errors are easier to measure against incumbent baselines than broad platform claims.",
            "proof_needed": "Forecast-error or early-warning metrics, false-positive accounting, held-out periods, uncertainty bounds.",
        },
        {
            "priority": 3,
            "unlock": "Promote one context-only high-value lane into a measured lane.",
            "target_lanes": ["energy", "market_data", "macro", "critical_infrastructure"],
            "why_it_matters": "This is the clean path from impressive context to reviewer-safe value.",
            "proof_needed": "Fresh source pull, file hash, source rights, baseline cost model, measured delta.",
        },
        {
            "priority": 4,
            "unlock": "Attach every strong claim to a dashboard tile and a reproducible artifact hash.",
            "target_lanes": ["grant_dashboard", "proof_to_pilot", "mission_control"],
            "why_it_matters": "Reviewers and buyers need to see the same claim, proof, hash, and blocker status everywhere.",
            "proof_needed": "Dashboard JSON parity, markdown packet, hash manifest, no overclaim flags.",
        },
    ]


def build_payload() -> dict[str, Any]:
    dollar_gate = load_or_build(DOLLAR_GATE_JSON, DOLLAR_GATE_SCRIPT, "summary")
    control_room = load_or_build(CONTROL_ROOM_JSON, CONTROL_ROOM_SCRIPT, "summary")
    outreach_queue = load_or_build(OUTREACH_QUEUE_JSON, OUTREACH_QUEUE_SCRIPT, "summary")
    asset_map = read_json(ASSET_MAP_JSON)

    dollar_summary = dollar_gate.get("summary", {}) if isinstance(dollar_gate.get("summary"), dict) else {}
    control_summary = control_room.get("summary", {}) if isinstance(control_room.get("summary"), dict) else {}
    queue_summary = outreach_queue.get("summary", {}) if isinstance(outreach_queue.get("summary"), dict) else {}
    cards = repeat_cards(control_room)
    queue_rows = top_queue_rows(outreach_queue)

    gates = {
        "bounded_estimated_value_claim_allowed": True,
        "paid_evaluation_offer_allowed": bool(control_summary.get("paid_evaluation_offer_allowed")),
        "buyer_authorized_pilot_scoping_ready": bool(control_summary.get("buyer_authorized_pilot_scoping_ready")),
        "manual_reviewed_outreach_allowed": bool(control_summary.get("manual_reviewed_outreach_allowed")),
        "field_validation_claim_allowed": False,
        "realized_savings_claim_allowed": False,
        "fixed_dollar_delta_claim_allowed": False,
        "bulk_email_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
    }
    payload = {
        "schema": "claim_strength_value_unlock_map_v1",
        "generated_utc": now_utc(),
        "boundary": BOUNDARY,
        "summary": {
            "strongest_current_claim": "bounded_estimated_value_signal_and_paid_pilot_scoping",
            "safe_estimated_hourly_value_usd": dollar_summary.get("allowed_estimated_hourly_value_usd", 0),
            "safe_estimated_annual_value_usd": dollar_summary.get("allowed_estimated_annual_value_usd", 0),
            "blocked_context_annual_value_usd": dollar_summary.get("blocked_context_only_annual_value_usd", 0),
            "measured_estimated_value_lane_count": dollar_summary.get("allowed_estimated_value_claims", 0),
            "live_measured_source_row_count": dollar_summary.get("live_measured_source_row_count", 0),
            "geometry_family_count": control_summary.get("family_count", 0),
            "natural_path_family_count": control_summary.get("natural_path_family_count", 0),
            "robust_repeat_candidate_count": control_summary.get("robust_candidate_count", 0),
            "manual_paid_pilot_outreach_rows": queue_summary.get("queue_count", 0),
            "current_commercial_stage": control_summary.get("current_commercial_stage", "unknown"),
            **gates,
        },
        "money_worth_answer": build_money_worth_answer(dollar_gate, control_room),
        "claim_ladder": build_claim_ladder(dollar_gate, control_room, outreach_queue),
        "current_repeat_candidates": [
            {
                "family_id": row.get("family_id", ""),
                "lane": row.get("lane", ""),
                "pilot_name": row.get("pilot_name", ""),
                "evidence_stage": row.get("evidence_stage", ""),
                "repeat_window_evidence": row.get("repeat_window_evidence", {}),
                "claim_gate": row.get("claim_gate", {}),
            }
            for row in cards
        ],
        "paid_pilot_outreach_preview": [
            {
                "rank": row.get("rank"),
                "family_id": row.get("family_id", ""),
                "target_segment": row.get("target_segment", ""),
                "buyer_role": row.get("buyer_role", ""),
                "fit_score": row.get("fit_score", 0),
                "primary_ask": row.get("primary_ask", ""),
                "send_now_allowed": row.get("send_now_allowed", False),
            }
            for row in queue_rows
        ],
        "highest_value_unlocks": build_highest_value_unlocks(),
        "flower_of_life_circle_wave_note": build_geometry_note(),
        "must_not_say": [
            "guaranteed savings",
            "field validated",
            "realized customer savings",
            "fixed dollar value per frozen delta",
            "guaranteed grant award",
            "guaranteed alpha or profit",
            "live trading performance",
            "government owes this value",
        ],
        "inputs": {
            "dollar_claim_gate": str(DOLLAR_GATE_JSON.relative_to(ROOT)),
            "proof_to_pilot_control_room": str(CONTROL_ROOM_JSON.relative_to(ROOT)),
            "paid_pilot_outreach_queue": str(OUTREACH_QUEUE_JSON.relative_to(ROOT)),
            "geometry_champion_asset_map": str(ASSET_MAP_JSON.relative_to(ROOT)),
        },
        "asset_map_summary": asset_map.get("summary", {}) if isinstance(asset_map.get("summary"), dict) else {},
    }
    payload["claim_strength_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "money_worth_answer": payload["money_worth_answer"],
            "claim_ladder": payload["claim_ladder"],
            "current_repeat_candidates": payload["current_repeat_candidates"],
            "highest_value_unlocks": payload["highest_value_unlocks"],
            "flower_of_life_circle_wave_note": payload["flower_of_life_circle_wave_note"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    money_answer = payload["money_worth_answer"]
    geometry_note = payload["flower_of_life_circle_wave_note"]
    lines = [
        "# Claim Strength And Value Unlock Map",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["boundary"],
        "",
        "## Direct Answer",
        "",
        money_answer["plain_answer"],
        "",
        f"- Strongest current claim: `{summary['strongest_current_claim']}`",
        f"- Safe estimated value signal: `{money(summary['safe_estimated_hourly_value_usd'])}/hour` and `{money(summary['safe_estimated_annual_value_usd'])}/year` under stated assumptions",
        f"- Blocked context-only value surface: `{money(summary['blocked_context_annual_value_usd'])}/year`",
        f"- Robust repeat candidates: `{summary['robust_repeat_candidate_count']}`",
        f"- Manual paid-pilot outreach rows: `{summary['manual_paid_pilot_outreach_rows']}`",
        "",
        "## Claim Gates",
        "",
        f"- Bounded estimated-value claim allowed: `{str(summary['bounded_estimated_value_claim_allowed']).lower()}`",
        f"- Paid evaluation offer allowed: `{str(summary['paid_evaluation_offer_allowed']).lower()}`",
        f"- Buyer-authorized pilot scoping ready: `{str(summary['buyer_authorized_pilot_scoping_ready']).lower()}`",
        f"- Field-validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
        f"- Realized-savings claim allowed: `{str(summary['realized_savings_claim_allowed']).lower()}`",
        f"- Fixed-dollar delta claim allowed: `{str(summary['fixed_dollar_delta_claim_allowed']).lower()}`",
        f"- Bulk email allowed: `{str(summary['bulk_email_allowed']).lower()}`",
        f"- Live trading or autonomous execution allowed: `{str(summary['live_trading_or_autonomous_execution_allowed']).lower()}`",
        "",
        "## Claim Ladder",
        "",
        "| Level | Stage | Status | Safe Claim | Money Language |",
        "|---:|---|---|---|---|",
    ]
    for row in payload["claim_ladder"]:
        lines.append(
            f"| {row['level']} | {row['claim_stage']} | {row['current_status']} | "
            f"{row['safe_claim']} | {row['money_language']} |"
        )

    lines.extend(["", "## Current Repeat Candidates", ""])
    lines.extend(["| Family | Lane | Windows | Lower 95 Delta | Sign-Test P | Claim Boundary |", "|---|---|---:|---:|---:|---|"])
    for row in payload["current_repeat_candidates"]:
        evidence = row.get("repeat_window_evidence", {}) or {}
        gate = row.get("claim_gate", {}) or {}
        boundary = (
            "paid evaluation allowed; field validation blocked"
            if gate.get("paid_evaluation_offer_allowed") and not gate.get("field_validation_claim_allowed")
            else "claim-gated"
        )
        lines.append(
            f"| `{row.get('family_id', '')}` | `{row.get('lane', '')}` | "
            f"{evidence.get('wins', 0)}/{evidence.get('windows', 0)} | "
            f"{evidence.get('lower_95_delta', '')} | {evidence.get('sign_test_p', '')} | {boundary} |"
        )

    lines.extend(["", "## Highest-Value Unlocks", ""])
    for row in payload["highest_value_unlocks"]:
        lines.append(f"- P{row['priority']}: {row['unlock']} Proof needed: {row['proof_needed']}")

    lines.extend(
        [
            "",
            "## Flower Of Life / Circles / Waves",
            "",
            geometry_note["answer"],
            "",
            "Candidate geometries to test:",
        ]
    )
    lines.extend(f"- `{item}`" for item in geometry_note["testable_families"])
    lines.extend(["", f"Claim boundary: {geometry_note['claim_boundary']}"])

    lines.extend(["", "## Must Not Say", ""])
    lines.extend(f"- {item}" for item in payload["must_not_say"])
    lines.extend(["", f"Claim-strength hash: `{payload['claim_strength_sha256']}`"])
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
