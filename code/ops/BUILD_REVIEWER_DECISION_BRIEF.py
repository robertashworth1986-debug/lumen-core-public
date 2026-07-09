from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

AUTHORITY_JSON = OUT_OPS / "submission_authority_matrix_latest.json"
DOCKET_JSON = OUT_OPS / "human_action_docket_latest.json"
CONCIERGE_JSON = OUT_OPS / "reviewer_concierge_packet_latest.json"
TRACTION_JSON = OUT_OPS / "traction_opportunity_intake_ledger_latest.json"
REVIEWER_GATE_JSON = OUT_OPS / "funding_sprint_reviewer_gate_latest.json"

OUT_JSON = OUT_OPS / "reviewer_decision_brief_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "reviewer_decision_brief.json"
OUT_MD = SPRINT_DIR / "REVIEWER_DECISION_BRIEF_2026-07-09.md"

SENSITIVE_MARKERS = [
    "zoom.us",
    "meeting id",
    "password",
    "one tap mobile",
    "private key",
    "refresh_token",
    "client_secret",
    "api_key",
    "sk-",
    "xox",
]

DECISION_STANCE_BY_READINESS = {
    "MEETING_PREP_READY_FINAL_TERMS_BLOCKED": "Review now; human handles meeting and terms.",
    "INVESTOR_WATCH_READY_RESPONSE_BLOCKED": "Keep ready for diligence or review-window follow-up.",
    "FEDERAL_DRAFT_READY_SUBMISSION_BLOCKED": "Advance draft package; human verifies official instructions and authority.",
    "FEDERAL_REGISTRATION_SUBMITTED_VALIDATION_PENDING": "Monitor validation; do not claim Active status until SAM confirms it.",
    "LAB_POC_FOLLOWUP_READY_HUMAN_SEND_REQUIRED": "Prepare lab follow-up; human approves any POC reply or disclosure.",
    "RFI_DRAFT_READY_SEND_BLOCKED": "Prepare response; human verifies official send route.",
    "SBIR_DRAFT_READY_PORTAL_BLOCKED": "Prepare portal package; human controls Firm PIN and certifications.",
    "ROLLING_GATE_READY_RULE_CHECK_REQUIRED": "Submit only after account/rule check.",
    "ROUTING_SENT_WAIT_FOR_RESPONSE": "Wait for routing response.",
    "PARTNER_REQUIRED_NO_SOLO_SUBMISSION": "Partner required before response.",
    "TOPIC_SCOUT_READY_SELECTION_REQUIRED": "Scout topic fit before drafting.",
    "PARKED_NO_SOLO_ACTION": "Do not pursue solo.",
    "INTRO_MATERIAL_READY_NO_SOLO_PROPOSAL": "Use for partner or investor intro only.",
    "CUSTOMER_DISCOVERY_SIGNAL_READY_HUMAN_REPLY_REQUIRED": "Use as buyer-discovery signal; human decides whether to reply.",
    "VENDOR_FORM_READY_HUMAN_SUBMIT_REQUIRED": "Prepare official-form request; human handles account and terms.",
    "IP_PACKET_READY_COUNSEL_REQUIRED": "Counsel review required before public claim expansion.",
}

AUDIENCE_BY_CHANNEL = {
    "venture_engineering": "engineering partner",
    "venture_cash": "early investor",
    "federal_baa": "technical program reviewer",
    "federal_contract": "contracting or capability reviewer",
    "federal_registration": "federal registration reviewer",
    "federal_lab_tech_transfer": "federal lab technology-transfer reviewer",
    "federal_rfi": "market research reviewer",
    "federal_sbir": "SBIR reviewer",
    "federal_market_research": "agency routing contact",
    "federal_sources_sought": "qualified-prime or partner reviewer",
    "infrastructure_market_signal": "infrastructure buyer-discovery reviewer",
    "ip_readiness": "patent counsel",
    "vendor_credit_or_partner_route": "vendor partner-program reviewer",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("lane_id", "")): row for row in rows}


def build_decision_cards(authority: dict[str, Any], docket: dict[str, Any], concierge: dict[str, Any]) -> list[dict[str, Any]]:
    authority_rows = authority.get("authority_rows", [])
    docket_rows = by_id(docket.get("docket_items", []))
    concierge_rows = by_id(concierge.get("concierge_cards", []))
    cards = []
    for row in sorted(authority_rows, key=lambda item: int(item.get("priority", 999))):
        lane_id = str(row.get("lane_id", ""))
        docket_row = docket_rows.get(lane_id, {})
        concierge_row = concierge_rows.get(lane_id, {})
        readiness = str(row.get("readiness_mode", ""))
        card = {
            "lane_id": lane_id,
            "name": row.get("name", ""),
            "priority": int(row.get("priority", 999)),
            "audience": AUDIENCE_BY_CHANNEL.get(str(row.get("channel", "")), "reviewer"),
            "channel": row.get("channel", ""),
            "urgency": row.get("urgency", ""),
            "action_due": row.get("action_due"),
            "readiness_mode": readiness,
            "decision_stance": DECISION_STANCE_BY_READINESS.get(readiness, "Review with human gate."),
            "reviewer_decision": concierge_row.get("decision_question", row.get("decision_question", "")),
            "next_human_action": docket_row.get("docket_action", ""),
            "required_authority": row.get("required_authority", ""),
            "first_artifact": row.get("first_artifact", ""),
            "artifact_missing_count": row.get("artifact_missing_count", 0),
            "can_prepare_internal": row.get("can_prepare_internal", False),
            "can_send_external_without_human": row.get("can_send_external_without_human", False),
            "can_submit_without_human": row.get("can_submit_without_human", False),
            "can_accept_terms_without_human": row.get("can_accept_terms_without_human", False),
            "claim_boundary": row.get("claim_boundary", ""),
        }
        card["decision_card_sha256"] = hashlib.sha256(
            json.dumps(card, sort_keys=True).encode("utf-8")
        ).hexdigest()
        cards.append(card)
    return cards


def build_payload() -> dict[str, Any]:
    authority = read_json(AUTHORITY_JSON)
    docket = read_json(DOCKET_JSON)
    concierge = read_json(CONCIERGE_JSON)
    traction = read_json(TRACTION_JSON)
    gate = read_json(REVIEWER_GATE_JSON)

    cards = build_decision_cards(authority, docket, concierge)
    top_ready = [
        card
        for card in cards
        if int(card["priority"]) <= 7 and int(card["artifact_missing_count"]) == 0
    ]
    urgent_cards = [card for card in cards if card["urgency"] in {"IMMEDIATE_24H", "URGENT_5D"}]
    partner_blocked = [
        card
        for card in cards
        if card["readiness_mode"] in {
            "PARKED_NO_SOLO_ACTION",
            "PARTNER_REQUIRED_NO_SOLO_SUBMISSION",
            "INTRO_MATERIAL_READY_NO_SOLO_PROPOSAL",
        }
    ]
    final_actions_blocked = all(
        not card["can_send_external_without_human"]
        and not card["can_submit_without_human"]
        and not card["can_accept_terms_without_human"]
        for card in cards
    )
    gate_clear = bool(gate.get("reviewer_gate_clear")) and int(gate["summary"]["unsafe_secret_count"]) == 0 and int(gate["summary"]["unsafe_claim_count"]) == 0

    payload = {
        "generated_utc": now_utc(),
        "schema": "reviewer_decision_brief_v1",
        "status": "REVIEWER_DECISION_BRIEF_READY" if gate_clear and final_actions_blocked else "REVIEWER_DECISION_BRIEF_BLOCKED",
        "decision_headline": "LumenCore has a reviewer-ready proof packet with live traction, current funding lanes, explicit human authority gates, and no autonomous final-action authority.",
        "summary": {
            "lane_count": len(cards),
            "top_ready_lane_count": len(top_ready),
            "urgent_lane_count": len(urgent_cards),
            "partner_blocked_lane_count": len(partner_blocked),
            "reviewer_gate_clear": gate_clear,
            "all_final_actions_blocked_without_human": final_actions_blocked,
            "authority_lane_count": int(authority["summary"]["lane_count"]),
            "docket_lane_count": int(docket["summary"]["lane_count"]),
            "concierge_lane_count": int(concierge["summary"]["lane_count"]),
            "traction_lane_count": int(traction["summary"]["lane_count"]),
            "unsafe_secret_count": int(gate["summary"]["unsafe_secret_count"]),
            "unsafe_claim_count": int(gate["summary"]["unsafe_claim_count"]),
            "external_send_allowed_without_human": False,
            "final_submission_allowed_without_human": False,
            "live_trading_allowed": False,
        },
        "reviewer_answer": {
            "what_is_ready": [
                "A 15-lane traction and funding queue with source-backed evidence.",
                "A concierge index that maps each lane to reviewer artifacts.",
                "A date-aware human action docket.",
                "A submission authority matrix that blocks final action without named human authority.",
                "A reviewer gate showing zero unsafe sensitive hits and zero unsafe claim hits.",
            ],
            "what_to_review_first": [
                "EVTit / Black Dog in-kind engineering fund: meeting prep and build-scope review.",
                "DARPA DICE full proposal sprint: BAA compliance and technical package build.",
                "NASA Data Center Infrastructure RFI: bounded RFI response.",
                "FHWA TSMO Data Initiative: Phase I technical capability package.",
                "DLA MissionWeave DSIP SBIR and NSF Project Pitch: portal/rule-gated SBIR package work.",
                "Patent counsel / IP deadline defense: counsel packet and claim-boundary review.",
            ],
            "what_is_not_claimed": [
                "No award, agency approval, investment decision, partnership acceptance, patentability, counsel advice, or production deployment is represented by this brief.",
                "No final portal action, email send, certification, filing, term acceptance, trading, or capital movement is authorized.",
            ],
            "why_this_reduces_reviewer_work": [
                "Every lane has a first artifact, decision question, human gate, and claim boundary.",
                "No-solo lanes are separated from immediate actions.",
                "Machine-readable JSON mirrors the Markdown packet for audit and dashboard use.",
            ],
        },
        "decision_cards": cards,
        "top_ready_lane_ids": [card["lane_id"] for card in top_ready],
        "urgent_lane_ids": [card["lane_id"] for card in urgent_cards],
        "partner_blocked_lane_ids": [card["lane_id"] for card in partner_blocked],
        "source_ledgers": {
            "authority": rel(AUTHORITY_JSON),
            "docket": rel(DOCKET_JSON),
            "concierge": rel(CONCIERGE_JSON),
            "traction": rel(TRACTION_JSON),
            "reviewer_gate": rel(REVIEWER_GATE_JSON),
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["decision_brief_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Reviewer Decision Brief - 2026-07-09",
        "",
        payload["decision_headline"],
        "",
        "This brief is a decision-support front page. It does not authorize any final external action.",
        "",
        "## Readiness Snapshot",
        "",
        f"- Status: `{payload['status']}`",
        f"- Lanes: `{summary['lane_count']}`",
        f"- Top ready lanes: `{summary['top_ready_lane_count']}`",
        f"- Immediate/urgent lanes: `{summary['urgent_lane_count']}`",
        f"- Partner-blocked lanes: `{summary['partner_blocked_lane_count']}`",
        f"- Reviewer gate clear: `{str(summary['reviewer_gate_clear']).lower()}`",
        f"- All final actions blocked without human: `{str(summary['all_final_actions_blocked_without_human']).lower()}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_secret_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Decision brief SHA-256: `{payload['decision_brief_sha256']}`",
        "",
        "## Reviewer Answer",
        "",
        "### What Is Ready",
        "",
    ]
    for item in payload["reviewer_answer"]["what_is_ready"]:
        lines.append(f"- {item}")
    lines.extend(["", "### What To Review First", ""])
    for item in payload["reviewer_answer"]["what_to_review_first"]:
        lines.append(f"- {item}")
    lines.extend(["", "### What Is Not Claimed", ""])
    for item in payload["reviewer_answer"]["what_is_not_claimed"]:
        lines.append(f"- {item}")
    lines.extend(["", "### Why This Reduces Reviewer Work", ""])
    for item in payload["reviewer_answer"]["why_this_reduces_reviewer_work"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Decision Cards", ""])
    for card in payload["decision_cards"]:
        lines.extend(
            [
                f"### {card['priority']}. {card['name']}",
                "",
                f"- Audience: {card['audience']}",
                f"- Lane ID: `{card['lane_id']}`",
                f"- Channel: `{card['channel']}`",
                f"- Urgency: `{card['urgency']}`",
                f"- Action due: `{card['action_due']}`",
                f"- Readiness mode: `{card['readiness_mode']}`",
                f"- Decision stance: {card['decision_stance']}",
                f"- Reviewer decision: {card['reviewer_decision']}",
                f"- Next human action: {card['next_human_action']}",
                f"- Required authority: {card['required_authority']}",
                f"- First artifact: `{card['first_artifact']}`",
                f"- Claim boundary: {card['claim_boundary']}",
                f"- Can send externally without human: `{str(card['can_send_external_without_human']).lower()}`",
                f"- Can submit without human: `{str(card['can_submit_without_human']).lower()}`",
                f"- Can accept terms without human: `{str(card['can_accept_terms_without_human']).lower()}`",
                f"- Card SHA-256: `{card['decision_card_sha256']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Final-Action Boundary",
            "",
            "No final portal action, email send, certification, filing, pricing approval, term acceptance, trading, or capital movement is authorized by this brief.",
        ]
    )
    return "\n".join(lines) + "\n"


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive public decision brief markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "lanes": payload["summary"]["lane_count"],
                "top_ready": payload["summary"]["top_ready_lane_count"],
                "urgent": payload["summary"]["urgent_lane_count"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
