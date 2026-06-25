from __future__ import annotations

import csv
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

CONTROL_ROOM_JSON = OUT_OPS / "proof_to_pilot_control_room_latest.json"
CONTROL_ROOM_SCRIPT = ROOT / "code" / "ops" / "BUILD_PROOF_TO_PILOT_CONTROL_ROOM.py"

OUT_JSON = OUT_OPS / "paid_pilot_outreach_queue_latest.json"
OUT_CSV = OUT_OPS / "paid_pilot_outreach_queue_latest.csv"
DASHBOARD_JSON = DASHBOARD_DATA / "paid_pilot_outreach_queue.json"
OUT_MD = DOCS / "PAID_PILOT_OUTREACH_QUEUE_2026-06-25.md"

BOUNDARY = (
    "This queue is a manual paid-pilot outreach worklist. It helps select reviewed buyer or agency technical "
    "contacts and match each contact to the strongest current proof card. It does not authorize bulk email, "
    "contact scraping, fixed-dollar frozen-delta claims, field-validation claims, realized-savings claims, "
    "live trading, or autonomous operational execution."
)

NO_SEND_PHRASES = [
    "guaranteed savings",
    "field validated",
    "$10k per frozen delta",
    "government-ready proof of dollar value",
    "guaranteed trading edge",
    "award-ready",
    "undeniable",
    "this will make you money",
]

COMMON_QUALIFIERS = [
    "Can review technical evidence or route it to a technical reviewer.",
    "Has authority over analytics, reliability, optimization, innovation, or R&D pilots.",
    "Can discuss buyer-approved data fields without exposing private data.",
    "Can identify incumbent baselines and measurable outcomes.",
    "Can support at least 20 pre-registered holdout windows before replay.",
]

COMMERCIAL_OFFER_TIERS = [
    {
        "tier": "technical_fit_call",
        "price_posture": "no_quote_until_fit",
        "deliverable": "20-minute fit call to decide whether a paid evidence review is worth scoping.",
        "claim_boundary": "No savings or field-validation claim.",
    },
    {
        "tier": "paid_evidence_review",
        "price_posture": "quote_after_scope; typical small paid review target 5000-15000 USD",
        "deliverable": "Review 5-10 curated frozen proof packets, hashes, baselines, gates, and failure modes.",
        "claim_boundary": "Evidence review only; not a procurement-grade field pilot.",
    },
    {
        "tier": "buyer_authorized_field_replay",
        "price_posture": "quote_after_data_rights_baselines_and_holdouts",
        "deliverable": "Replay candidate and incumbent baselines on buyer-approved holdout windows.",
        "claim_boundary": "Economic language only if buyer-provided conversion factors and results support it.",
    },
]

LANE_TARGETS: dict[str, list[dict[str, Any]]] = {
    "optimal_curve_transport": [
        {
            "target_segment": "utility_grid_analytics",
            "buyer_role": "Director of Grid Analytics",
            "organization_search_phrase": "utility grid analytics innovation reliability pilot",
            "pain": "constraint-heavy routing, dispatch, restoration, and reliability decisions",
            "measured_outcome": "recovery time, dispatch quality, outage exposure, operator review burden",
            "fit_score": 96,
        },
        {
            "target_segment": "datacenter_cooling_optimization",
            "buyer_role": "Datacenter Cooling Optimization Lead",
            "organization_search_phrase": "datacenter cooling optimization airflow reliability analytics",
            "pain": "airflow routing and thermal constraint management under cost and uptime pressure",
            "measured_outcome": "energy use, hot-spot exposure, cooling response time, thermal guardrail violations",
            "fit_score": 93,
        },
        {
            "target_segment": "port_maritime_operations",
            "buyer_role": "Port Operations Analytics Lead",
            "organization_search_phrase": "port operations analytics maritime anomaly routing pilot",
            "pain": "vessel, asset, and response routing under traffic, timing, and safety constraints",
            "measured_outcome": "route quality, response time, false-review burden, constraint violations",
            "fit_score": 91,
        },
        {
            "target_segment": "critical_infrastructure_resilience",
            "buyer_role": "R&D Program Manager for Critical Infrastructure",
            "organization_search_phrase": "critical infrastructure resilience optimization pilot program manager",
            "pain": "resilience routing and recovery planning where small decision-quality gains matter",
            "measured_outcome": "time-to-recover, exposure reduction, baseline score delta, guardrail failure rate",
            "fit_score": 89,
        },
        {
            "target_segment": "defense_cyber_physical_logistics",
            "buyer_role": "Cyber-Physical Systems Program Manager",
            "organization_search_phrase": "defense cyber physical systems routing optimization pilot",
            "pain": "mission route, sensor, or response choices under changing constraints",
            "measured_outcome": "constraint violation rate, decision latency, baseline score delta, review burden",
            "fit_score": 87,
        },
        {
            "target_segment": "industrial_maintenance_routing",
            "buyer_role": "Infrastructure Optimization Lead",
            "organization_search_phrase": "industrial maintenance routing optimization analytics pilot",
            "pain": "maintenance and inspection path planning across assets with time and risk constraints",
            "measured_outcome": "coverage, time, exposure, energy, repeatability against incumbent path plans",
            "fit_score": 84,
        },
    ],
    "wave_resonance_timing": [
        {
            "target_segment": "energy_forecasting",
            "buyer_role": "Energy Forecasting Lead",
            "organization_search_phrase": "energy forecasting grid load timing anomaly pilot",
            "pain": "cyclic load, generation, price, or anomaly timing where phase error matters",
            "measured_outcome": "forecast error, lead time, drift detection latency, missed-event rate",
            "fit_score": 95,
        },
        {
            "target_segment": "grid_reliability_analytics",
            "buyer_role": "Grid Reliability Analytics Lead",
            "organization_search_phrase": "grid reliability analytics oscillation drift detection pilot",
            "pain": "oscillatory system drift and early warning across measured operating signals",
            "measured_outcome": "early warning lead time, false positives, missed events, phase error",
            "fit_score": 92,
        },
        {
            "target_segment": "sensor_fusion_defense",
            "buyer_role": "Sensor Fusion Program Manager",
            "organization_search_phrase": "sensor fusion timing drift anomaly detection defense pilot",
            "pain": "multi-sensor timing, drift, and cyclic-event alignment under noisy conditions",
            "measured_outcome": "timing error, drift detection, event alignment, operator review burden",
            "fit_score": 90,
        },
        {
            "target_segment": "industrial_process_stability",
            "buyer_role": "Industrial Process Stability Lead",
            "organization_search_phrase": "industrial process stability oscillation timing analytics pilot",
            "pain": "process oscillations, resonance, and instability that cause manual intervention",
            "measured_outcome": "phase error, intervention count, stability alarms, false positives",
            "fit_score": 88,
        },
        {
            "target_segment": "national_lab_validation",
            "buyer_role": "Technology Transfer or Validation Program Manager",
            "organization_search_phrase": "national lab validation signal processing cyber physical systems",
            "pain": "independent validation of reproducible phase/timing benchmark evidence",
            "measured_outcome": "repeatability, baseline score delta, holdout performance, uncertainty report",
            "fit_score": 85,
        },
        {
            "target_segment": "infrastructure_risk_analytics",
            "buyer_role": "Operational Risk Analytics Lead",
            "organization_search_phrase": "infrastructure risk analytics early warning drift detection pilot",
            "pain": "early warning, risk timing, and anomaly triage before operational losses grow",
            "measured_outcome": "lead time, review burden, false positives, missed-event rate",
            "fit_score": 83,
        },
    ],
}


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


def load_control_room_payload() -> dict[str, Any]:
    payload = read_json(CONTROL_ROOM_JSON)
    if payload.get("top_cards"):
        return payload

    spec = importlib.util.spec_from_file_location("proof_to_pilot_control_room_for_queue", CONTROL_ROOM_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.build_payload()


def evidence_line(card: dict[str, Any]) -> str:
    evidence = card.get("repeat_window_evidence", {}) or {}
    return (
        f"{evidence.get('wins')}/{evidence.get('windows')} positive frozen replay windows; "
        f"lower 95 margin {evidence.get('lower_95_delta')}; "
        f"minimum source count {evidence.get('min_source_count')}"
    )


def safe_subject(card: dict[str, Any], target: dict[str, Any]) -> str:
    pilot = str(card.get("pilot_name") or card.get("email_subject") or "Paid pilot scoping")
    segment = str(target["target_segment"]).replace("_", " ")
    return f"Paid pilot scoping: {pilot} for {segment}"


def make_outreach_row(card: dict[str, Any], target: dict[str, Any], rank: int) -> dict[str, Any]:
    family = str(card.get("family_id", ""))
    lane = str(card.get("lane", ""))
    ask = (
        "Ask for a 20-minute technical fit call and permission to scope a paid evidence review or buyer-authorized "
        "field replay using pre-registered holdout windows."
    )
    row = {
        "rank": rank,
        "family_id": family,
        "lane": lane,
        "pilot_name": card.get("pilot_name", ""),
        "target_segment": target["target_segment"],
        "buyer_role": target["buyer_role"],
        "organization_search_phrase": target["organization_search_phrase"],
        "fit_score": target["fit_score"],
        "pain": target["pain"],
        "measured_outcome": target["measured_outcome"],
        "proof_line": evidence_line(card),
        "subject": safe_subject(card, target),
        "primary_ask": ask,
        "allowed_positioning": [
            "repeat-window frozen replay evidence",
            "named-baseline comparison",
            "paid technical evaluation",
            "buyer-approved field-data replay",
            "claim-gated evidence report",
        ],
        "blocked_positioning": NO_SEND_PHRASES,
        "contact_qualifiers": COMMON_QUALIFIERS,
        "data_room_artifacts": card.get("data_room_artifacts", []),
        "manual_review_required": True,
        "send_now_allowed": False,
        "why_not_send_now": "A human must identify and review the exact recipient, organization fit, physical address footer, and opt-out language before sending.",
    }
    row["row_sha256"] = stable_sha256(row)
    return row


def build_queue(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for card in cards:
        lane = str(card.get("lane", ""))
        targets = LANE_TARGETS.get(lane, [])
        for target in targets:
            rows.append(make_outreach_row(card, target, rank=0))
    rows.sort(key=lambda row: (-int(row["fit_score"]), str(row["family_id"]), str(row["target_segment"])))
    for idx, row in enumerate(rows, start=1):
        row["rank"] = idx
        row["row_sha256"] = stable_sha256({k: v for k, v in row.items() if k != "row_sha256"})
    return rows


def build_payload() -> dict[str, Any]:
    control_room = load_control_room_payload()
    cards = [row for row in control_room.get("top_cards", []) if isinstance(row, dict)]
    queue = build_queue(cards)
    ready_cards = [row for row in cards if row.get("commercial_stage") == "manual_paid_pilot_outreach_ready"]
    summary = {
        "queue_count": len(queue),
        "proof_card_count": len(cards),
        "ready_proof_card_count": len(ready_cards),
        "unique_lanes": sorted({str(row.get("lane")) for row in queue}),
        "top_ranked_target": queue[0]["target_segment"] if queue else "",
        "manual_reviewed_outreach_allowed": bool(queue),
        "bulk_email_allowed": False,
        "contact_scraping_allowed": False,
        "send_without_user_review_allowed": False,
        "fixed_dollar_delta_claim_allowed": False,
        "field_validation_claim_allowed": False,
        "realized_savings_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
        "queue_chain_sha256": stable_sha256(queue),
    }
    return {
        "schema": "paid_pilot_outreach_queue_v1",
        "generated_utc": now_utc(),
        "boundary": BOUNDARY,
        "inputs": {
            "proof_to_pilot_control_room": str(CONTROL_ROOM_JSON.relative_to(ROOT)),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)),
            "csv": str(OUT_CSV.relative_to(ROOT)),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
        },
        "summary": summary,
        "commercial_offer_tiers": COMMERCIAL_OFFER_TIERS,
        "send_gate": {
            "manual_reviewed_outreach_allowed": bool(queue),
            "bulk_email_allowed": False,
            "contact_scraping_allowed": False,
            "send_without_user_review_allowed": False,
            "requires_valid_physical_address": True,
            "requires_opt_out_language": True,
            "requires_per_recipient_fit_review": True,
        },
        "queue": queue,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Paid Pilot Outreach Queue",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["boundary"],
        "",
        "## Summary",
        "",
        f"- Queue rows: `{summary['queue_count']}`",
        f"- Proof cards: `{summary['proof_card_count']}`",
        f"- Ready proof cards: `{summary['ready_proof_card_count']}`",
        f"- Unique lanes: `{', '.join(summary['unique_lanes'])}`",
        f"- Top target: `{summary['top_ranked_target']}`",
        f"- Manual reviewed outreach allowed: `{str(summary['manual_reviewed_outreach_allowed']).lower()}`",
        f"- Bulk email allowed: `{str(summary['bulk_email_allowed']).lower()}`",
        f"- Contact scraping allowed: `{str(summary['contact_scraping_allowed']).lower()}`",
        f"- Fixed-dollar delta claim allowed: `{str(summary['fixed_dollar_delta_claim_allowed']).lower()}`",
        f"- Field-validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
        f"- Realized-savings claim allowed: `{str(summary['realized_savings_claim_allowed']).lower()}`",
        f"- Queue chain SHA-256: `{summary['queue_chain_sha256']}`",
        "",
        "## Commercial Offer Tiers",
        "",
    ]
    for tier in payload["commercial_offer_tiers"]:
        lines.extend(
            [
                f"### `{tier['tier']}`",
                "",
                f"- Price posture: {tier['price_posture']}",
                f"- Deliverable: {tier['deliverable']}",
                f"- Claim boundary: {tier['claim_boundary']}",
                "",
            ]
        )
    lines.extend(["## Ranked Queue", ""])
    for row in payload["queue"]:
        lines.extend(
            [
                f"### {row['rank']}. `{row['target_segment']}`",
                "",
                f"- Family: `{row['family_id']}`",
                f"- Lane: `{row['lane']}`",
                f"- Buyer role: {row['buyer_role']}",
                f"- Fit score: `{row['fit_score']}`",
                f"- Search phrase: `{row['organization_search_phrase']}`",
                f"- Pain: {row['pain']}",
                f"- Measured outcome: {row['measured_outcome']}",
                f"- Proof line: {row['proof_line']}",
                f"- Subject: {row['subject']}",
                f"- Primary ask: {row['primary_ask']}",
                f"- Send now allowed: `{str(row['send_now_allowed']).lower()}`",
                f"- Why not send now: {row['why_not_send_now']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Send Gate",
            "",
            "- Send only one reviewed message per reviewed contact.",
            "- Do not scrape contacts or bulk-send.",
            "- Include a valid physical mailing address and an opt-out sentence.",
            "- Do not claim fixed dollar value, field validation, realized savings, guaranteed funding, or guaranteed alpha.",
        ]
    )
    return "\n".join(lines)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "rank",
        "family_id",
        "lane",
        "target_segment",
        "buyer_role",
        "organization_search_phrase",
        "fit_score",
        "pain",
        "measured_outcome",
        "proof_line",
        "subject",
        "primary_ask",
        "manual_review_required",
        "send_now_allowed",
        "row_sha256",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_csv(OUT_CSV, payload["queue"])
    write_text(OUT_MD, render_markdown(payload))
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_CSV}")
    print(f"wrote {DASHBOARD_JSON}")
    print(f"wrote {OUT_MD}")
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
