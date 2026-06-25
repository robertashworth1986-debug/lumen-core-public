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

FIELD_PROTOCOL_JSON = OUT_OPS / "geometry_field_validation_protocol_latest.json"
FIELD_PROTOCOL_SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_FIELD_VALIDATION_PROTOCOL.py"

OUT_JSON = OUT_OPS / "field_validation_buyer_pilot_packet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "field_validation_buyer_pilot_packet.json"
OUT_MD = DOCS / "FIELD_VALIDATION_BUYER_PILOT_PACKET_2026-06-25.md"

BOUNDARY = (
    "This packet is for targeted manual buyer outreach and paid pilot scoping. It does not authorize bulk email, "
    "fixed-dollar frozen-delta claims, realized-savings claims, field-validation claims, live trading, or autonomous "
    "operational execution."
)

LANE_BUYER_PERSONAS: dict[str, dict[str, Any]] = {
    "optimal_curve_transport": {
        "priority_titles": [
            "Director of Grid Analytics",
            "Infrastructure Optimization Lead",
            "Port Operations Analytics Lead",
            "Datacenter Cooling Optimization Lead",
            "R&D Program Manager for Critical Infrastructure",
        ],
        "buyer_pain": "constraint-heavy routing, dispatch, airflow, or recovery decisions where small path-quality changes can reduce time, exposure, energy, or operator burden",
        "pilot_question": "Can the brachistochrone-style candidate beat incumbent route/path baselines on pre-registered buyer holdout windows without violating constraints?",
        "technical_hook": "6/6 positive frozen replay windows, minimum 5 sources per replay window, positive lower 95% margin.",
    },
    "wave_resonance_timing": {
        "priority_titles": [
            "Energy Forecasting Lead",
            "Grid Reliability Analytics Lead",
            "Sensor Fusion Program Manager",
            "Industrial Process Stability Lead",
            "R&D Program Manager for Cyber-Physical Systems",
        ],
        "buyer_pain": "oscillatory or cyclic systems where earlier timing, lower phase error, or better drift detection can reduce missed events and manual review",
        "pilot_question": "Can the Kuramoto-style candidate beat incumbent timing/forecast baselines on pre-registered buyer holdout windows?",
        "technical_hook": "6/6 positive frozen replay windows, minimum 4 sources per replay window, positive lower 95% margin.",
    },
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


def load_field_protocol_payload() -> dict[str, Any]:
    payload = read_json(FIELD_PROTOCOL_JSON)
    if payload.get("protocols"):
        return payload

    spec = importlib.util.spec_from_file_location("geometry_field_validation_protocol_for_buyer_packet", FIELD_PROTOCOL_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.build_payload()


def data_room_artifacts() -> list[str]:
    return [
        "docs/GEOMETRY_CHAMPION_ASSET_MAP_2026-06-25.md",
        "docs/GEOMETRY_REPEAT_PROOF_VALIDATION_2026-06-25.md",
        "docs/GEOMETRY_REPEAT_UNCERTAINTY_REPORT_2026-06-25.md",
        "docs/GEOMETRY_FIELD_VALIDATION_PROTOCOL_2026-06-25.md",
        "docs/FROZEN_DELTA_BUYER_OUTREACH_PACKET_2026-06-25.md",
    ]


def make_email(protocol: dict[str, Any], persona: dict[str, Any]) -> dict[str, str]:
    family = str(protocol.get("family_id", ""))
    lane = str(protocol.get("lane", ""))
    pilot = str(protocol.get("pilot_name", ""))
    evidence = protocol.get("evidence_summary", {})
    subject = f"Paid pilot scoping: {pilot}"
    body = f"""Hello [Name],

I am Robert Ashworth, inventor of the LumenCore/NovaCore frozen evidence framework. I am reaching out because your team works near {persona['buyer_pain']}.

The current evidence is not a field-validation or savings claim. It is a narrower pilot-scoping signal:
- Candidate: {family}
- Lane: {lane}
- Repeat-window evidence: {evidence.get('win_count')}/{evidence.get('window_count')} positive frozen replay windows
- Lower 95% score-margin estimate: {evidence.get('normal_t_lower_95_delta')}
- Current technical question: {persona['pilot_question']}

I am looking for one paid technical evaluation or buyer-authorized pilot where we replay the candidate against your incumbent baselines on pre-registered holdout windows. The output would be a claim-bounded evidence report: what improved, what failed, what cannot yet be claimed, and what would be required for a procurement-grade validation.

Would you be open to a 20-minute technical fit call this week?

Best,
Robert Ashworth
[Organization / LumenCore]
[Website or proof portal link]
[Physical mailing address]

To stop further outreach, reply "remove."
"""
    follow_up = f"""Hello [Name],

Following up once on the LumenCore/NovaCore pilot-scoping request.

The short version: we have repeat-window frozen replay evidence for {family}, but the next real milestone is buyer-authorized field data. I am not asking you to accept a savings claim; I am asking whether your team would review a bounded pilot plan and decide if the evidence is worth testing on your holdout windows.

If you are not the right technical contact, who owns {pilot.lower()} or related analytics pilots on your team?

Best,
Robert Ashworth
"""
    return {
        "subject": subject,
        "first_email": body,
        "follow_up_email": follow_up,
    }


def make_packet(protocol: dict[str, Any]) -> dict[str, Any]:
    lane = str(protocol.get("lane", ""))
    persona = LANE_BUYER_PERSONAS.get(
        lane,
        {
            "priority_titles": ["Technical Evaluation Lead", "Innovation Program Manager"],
            "buyer_pain": "complex operational optimization problems",
            "pilot_question": "Can the candidate beat named baselines on pre-registered holdout data?",
            "technical_hook": "repeat-window candidate evidence with blocked commercial claims",
        },
    )
    email = make_email(protocol, persona)
    packet = {
        "family_id": protocol.get("family_id", ""),
        "lane": lane,
        "pilot_name": protocol.get("pilot_name", ""),
        "evidence_stage": protocol.get("evidence_stage", ""),
        "evidence_strength_score": protocol.get("evidence_strength_score", 0),
        "priority_buyer_titles": persona["priority_titles"],
        "buyer_pain": persona["buyer_pain"],
        "pilot_question": persona["pilot_question"],
        "technical_hook": persona["technical_hook"],
        "paid_offer": {
            "offer_type": "paid technical evaluation or buyer-authorized pilot scoping",
            "pricing_status": "quote_after_fit_call_and_data_scope",
            "safe_positioning": "paid evaluation of a repeat-window candidate, not sale of guaranteed-value frozen deltas",
        },
        "deliverables": [
            "buyer-specific data checklist",
            "pre-registered holdout and baseline plan",
            "candidate replay against incumbent and named baselines",
            "uncertainty and failure-mode report",
            "claim-boundary memo separating proven evidence from unproven commercial claims",
            "pilot result artifact with hashable chain references",
        ],
        "data_room_artifacts": data_room_artifacts(),
        "buyer_data_checklist": protocol.get("field_data_required", []),
        "baseline_controls": protocol.get("baseline_controls", []),
        "primary_kpis": protocol.get("primary_kpis", []),
        "acceptance_gate": protocol.get("acceptance_gate", {}),
        "pre_call_questions": [
            "What operational decision or forecast would you want this to improve?",
            "What incumbent baseline does your team trust today?",
            "Can you provide at least 20 pre-registered holdout windows?",
            "Which measured outcome would make the pilot worth continuing?",
            "Which guardrail failure would stop the pilot immediately?",
            "Who can approve use of field data and economic conversion factors?",
        ],
        "sow_outline": [
            "Scope the buyer decision lane and incumbent baselines.",
            "Define permitted data fields, privacy boundaries, and holdout windows.",
            "Run baseline and candidate replay under identical constraints.",
            "Report win rate, lower-bound margin, failure cases, and guardrail results.",
            "Only discuss economic impact if buyer-provided conversion factors support it.",
        ],
        "email": email,
        "claim_gate": {
            "send_manually_to_reviewed_contacts": True,
            "bulk_email_allowed": False,
            "fixed_dollar_delta_claim_allowed": False,
            "field_validation_claim_allowed": False,
            "realized_savings_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
        },
        "no_send_phrases": [
            "guaranteed savings",
            "field validated",
            "$10k per frozen delta",
            "guaranteed trading edge",
            "bulk government-ready assets",
        ],
    }
    packet["packet_sha256"] = stable_sha256(packet)
    return packet


def build_payload() -> dict[str, Any]:
    protocol_payload = load_field_protocol_payload()
    protocols = [
        row
        for row in protocol_payload.get("protocols", [])
        if isinstance(row, dict) and row.get("evidence_stage") == "ready_for_buyer_authorized_pilot_scoping"
    ]
    packets = [make_packet(protocol) for protocol in protocols]
    summary = {
        "packet_count": len(packets),
        "manual_outreach_ready_count": sum(1 for packet in packets if packet["claim_gate"]["send_manually_to_reviewed_contacts"]),
        "bulk_email_allowed": False,
        "fixed_dollar_delta_claim_allowed": False,
        "field_validation_claim_allowed": False,
        "realized_savings_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
        "top_packet_family_id": packets[0]["family_id"] if packets else "",
        "packet_chain_sha256": stable_sha256(packets),
    }
    return {
        "schema": "field_validation_buyer_pilot_packet_v1",
        "generated_utc": now_utc(),
        "evidence_boundary": BOUNDARY,
        "inputs": {
            "geometry_field_validation_protocol": str(FIELD_PROTOCOL_JSON.relative_to(ROOT)),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
        },
        "field_protocol_summary": protocol_payload.get("summary", {}),
        "summary": summary,
        "packets": packets,
        "claim_controls": {
            "allowed": [
                "manual reviewed outreach",
                "paid evaluation offer",
                "buyer-authorized pilot scoping",
                "field-data request",
            ],
            "blocked": [
                "bulk email",
                "fixed-dollar frozen-delta claim",
                "field validation already proven",
                "realized savings",
                "live trading or autonomous operational execution",
            ],
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Field Validation Buyer Pilot Packet",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## Summary",
        "",
        f"- Buyer pilot packets: `{summary['packet_count']}`",
        f"- Manual outreach ready: `{summary['manual_outreach_ready_count']}`",
        f"- Bulk email allowed: `{str(summary['bulk_email_allowed']).lower()}`",
        f"- Fixed-dollar delta claim allowed: `{str(summary['fixed_dollar_delta_claim_allowed']).lower()}`",
        f"- Field-validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
        f"- Packet chain SHA-256: `{summary['packet_chain_sha256']}`",
        "",
        "## Packets",
        "",
    ]
    for packet in payload["packets"]:
        lines.extend(
            [
                f"### `{packet['family_id']}`",
                "",
                f"- Pilot: {packet['pilot_name']}",
                f"- Lane: `{packet['lane']}`",
                f"- Evidence stage: `{packet['evidence_stage']}`",
                f"- Evidence strength score: `{packet['evidence_strength_score']}`",
                f"- Buyer pain: {packet['buyer_pain']}",
                f"- Pilot question: {packet['pilot_question']}",
                f"- Paid offer: {packet['paid_offer']['offer_type']}",
                f"- Pricing status: `{packet['paid_offer']['pricing_status']}`",
                "- Priority buyer titles:",
            ]
        )
        for title in packet["priority_buyer_titles"]:
            lines.append(f"  - {title}")
        lines.append("- Deliverables:")
        for item in packet["deliverables"]:
            lines.append(f"  - {item}")
        lines.append("- Pre-call questions:")
        for question in packet["pre_call_questions"]:
            lines.append(f"  - {question}")
        lines.extend(
            [
                "",
                "Email subject:",
                "",
                f"```text\n{packet['email']['subject']}\n```",
                "",
                "First email:",
                "",
                f"```text\n{packet['email']['first_email'].rstrip()}\n```",
                "",
            ]
        )
    lines.extend(
        [
            "## Claim Boundary",
            "",
            "- Send manually only to reviewed contacts.",
            "- Do not run bulk outreach from this packet.",
            "- Do not claim fixed-dollar value per frozen delta.",
            "- Do not claim field validation or realized savings until a buyer-authorized pilot produces that evidence.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "packet_count": payload["summary"]["packet_count"],
                "manual_outreach_ready_count": payload["summary"]["manual_outreach_ready_count"],
                "json": payload["outputs"]["json"],
                "markdown": payload["outputs"]["markdown"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
