from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

CONCIERGE_JSON = OUT_OPS / "reviewer_concierge_packet_latest.json"
TRACTION_JSON = OUT_OPS / "traction_opportunity_intake_ledger_latest.json"
REVIEWER_GATE_JSON = OUT_OPS / "funding_sprint_reviewer_gate_latest.json"
OUT_JSON = OUT_OPS / "human_action_docket_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "human_action_docket.json"
OUT_MD = SPRINT_DIR / "HUMAN_ACTION_DOCKET_2026-07-09.md"

CURRENT_DATE = date(2026, 7, 9)
NO_FINAL_ACTION = "Human approval is required before any send, upload, filing, certification, pricing, term acceptance, calendar edit, trading, or capital movement."

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

ACTION_OVERRIDES: dict[str, dict[str, Any]] = {
    "sam_registration_external_validation_watch": {
        "docket_action": "Check SAM status and watch for any DLA email; prepare Entity Administrator letter packet if required.",
        "action_due": "2026-07-13",
        "time_basis": "SAM confirmation says IRS validation can take two business days and DLA CAGE validation averages two business days after routing.",
        "action_type": "federal_registration_watch",
    },
    "lanl_vision_licensing_followup": {
        "docket_action": "Prepare concise licensing-fit note and technical questions for the named LANL POC return window.",
        "action_due": "2026-07-13",
        "time_basis": "LANL response says the main POC is out until next week.",
        "action_type": "lab_poc_followup",
    },
    "uspto_georgia_patents_route": {
        "docket_action": "Prepare Georgia PATENTS intake packet and counsel questions.",
        "action_due": "2026-07-10",
        "time_basis": "USPTO Pro Bono routed Tennessee inventors to Georgia PATENTS; patent timing must be verified by counsel.",
        "action_type": "licensed_counsel_review",
    },
    "protecnium_its_infrastructure_signal": {
        "docket_action": "Use as customer-discovery context for infrastructure/ITS buyers; reply only if Robert wants partner or market discovery.",
        "action_due": None,
        "time_basis": "LinkedIn InMail is a market signal, not a funding deadline.",
        "action_type": "customer_discovery_watch",
    },
    "evtit_blackdog_inkind": {
        "docket_action": "Prepare call packet and proof walkthrough.",
        "action_due": "2026-07-09",
        "time_basis": "Gmail invite received; exact event time is intentionally excluded from the public docket.",
        "action_type": "meeting_prep",
    },
    "lvlup_first_check": {
        "docket_action": "Hold investor brief and walkthrough ready; follow up only if reviewer asks or the under-one-week window passes.",
        "action_due": "2026-07-16",
        "time_basis": "Submitted July 9, 2026; one-week review watch window.",
        "action_type": "investor_watch",
    },
    "darpa_dice_full_submission": {
        "docket_action": "Build full-proposal compliance matrix and confirm controlling BAA instructions.",
        "action_due": "2026-07-12",
        "time_basis": "Internal sprint target so full proposal work does not wait for a last-minute gate.",
        "action_type": "federal_baa_build",
    },
    "nsf_project_pitch": {
        "docket_action": "Check the one-pending-pitch rule before any Project Pitch submit.",
        "action_due": None,
        "time_basis": "Rolling invitation gate; no artificial deadline assigned.",
        "action_type": "rolling_human_check",
    },
    "openai_api_continuity": {
        "docket_action": "Submit or refresh official API-continuity request if API availability is still a blocker.",
        "action_due": "2026-07-10",
        "time_basis": "Operational continuity support action; no public program deadline found.",
        "action_type": "vendor_route",
    },
    "openai_build_week_prooflock": {
        "docket_action": "Confirm model/session provenance, deploy the public demo, record the public video, and populate the Devpost draft without final submission.",
        "action_due": "2026-07-21",
        "time_basis": "Official final submission deadline is July 21, 2026 at 5:00 p.m. Pacific / 7:00 p.m. Central.",
        "action_type": "developer_challenge_build",
    },
    "patent_deadline_counsel": {
        "docket_action": "Monitor counsel replies and prepare filed-materials packet for licensed review.",
        "action_due": "2026-07-25",
        "time_basis": "Dossier email states a July 25, 2025 filing date; counsel must verify any actual legal deadline.",
        "action_type": "licensed_counsel_review",
    },
}

STATUS_ACTION_TYPES: dict[str, str] = {
    "DO_NOT_PRIME_SOLO": "park_partner_only",
    "PARTNER_ONLY": "partner_only",
    "PARTNER_INTRO_ONLY": "partner_intro_only",
    "ROUTE_ONLY_LOW_FIT": "agency_routing_watch",
    "SCOUT_TOPIC_MATCH": "topic_fit_check",
    "PHASE_I_TECH_VOLUME": "federal_contract_build",
    "RFI_RESPONSE_PREP": "federal_rfi_build",
    "DSIP_PACKAGE_PREP": "federal_sbir_build",
    "FULL_PROPOSAL_SPRINT": "federal_baa_build",
    "PITCH_READY_HUMAN_CHECK": "rolling_human_check",
    "HUMAN_FORM_READY": "vendor_route",
    "PRO_BONO_ROUTE_IDENTIFIED_HUMAN_ACTION_REQUIRED": "licensed_counsel_review",
    "PROJECT_CORE_VERIFIED_EXTERNAL_SUBMISSION_FIELDS_OPEN": "developer_challenge_build",
    "URGENT_COUNSEL_WATCH": "licensed_counsel_review",
    "SUBMITTED_EXTERNAL_VALIDATION_PENDING": "federal_registration_watch",
    "WAITING_POC_RETURN": "lab_poc_followup",
    "CUSTOMER_DISCOVERY_SIGNAL_ONLY": "customer_discovery_watch",
    "WAITING_REVIEW": "investor_watch",
    "LIVE_MEETING_PREP": "meeting_prep",
}

DOCKET_ACTIONS_BY_TYPE: dict[str, str] = {
    "federal_contract_build": "Convert the current outline into a human-review package with compliance checklist, pricing stop, and source attachment check.",
    "federal_rfi_build": "Prepare a bounded response draft and verify official response instructions before send.",
    "federal_sbir_build": "Prepare technical volume, cost notes, and Firm PIN handoff checklist.",
    "federal_baa_build": "Build compliance matrix, technical narrative, and submission authority checklist.",
    "rolling_human_check": "Verify platform rules before any submit action.",
    "vendor_route": "Prepare official-form language and human billing/terms review.",
    "licensed_counsel_review": "Prepare counsel packet and do not expand public IP claims without licensed review.",
    "federal_registration_watch": "Monitor entity registration validations and respond to official requests only through human-approved channels.",
    "lab_poc_followup": "Prepare a concise tech-transfer follow-up packet for the named lab POC.",
    "customer_discovery_watch": "Use as market-context evidence; do not claim a customer or pilot.",
    "investor_watch": "Keep brief ready and avoid repeated follow-up until the stated review window passes or the reviewer asks.",
    "meeting_prep": "Prepare walkthrough, build-scope menu, proof links, and terms questions.",
    "agency_routing_watch": "Wait for routing response; do not prepare a prime bid.",
    "partner_only": "Find qualified partner before any response draft.",
    "partner_intro_only": "Use as strategic-intro material, not a solo proposal.",
    "park_partner_only": "Park as non-solo lane unless a qualified platform or prime partner leads.",
    "topic_fit_check": "Review official attachments and score topic fit before drafting.",
    "developer_challenge_build": "Complete public demo, video, model/session provenance, registration, and draft fields before human final review.",
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


def parse_first_iso_date(value: str) -> str | None:
    match = re.search(r"\b20\d{2}-\d{2}-\d{2}\b", value or "")
    return match.group(0) if match else None


def days_until(value: str | None) -> int | None:
    if not value:
        return None
    return (date.fromisoformat(value) - CURRENT_DATE).days


def urgency_for(action_due: str | None, action_type: str, status: str) -> str:
    if status in {"DO_NOT_PRIME_SOLO", "PARTNER_ONLY", "PARTNER_INTRO_ONLY"}:
        return "PARKED_UNLESS_PARTNER"
    delta = days_until(action_due)
    if delta is None:
        return "ROLLING_OR_EVENT_GATED"
    if delta < 0:
        return "PAST_DATE_RECHECK"
    if delta <= 1:
        return "IMMEDIATE_24H"
    if delta <= 5:
        return "URGENT_5D"
    if delta <= 14:
        return "ACTIVE_14D"
    return "WATCHLIST"


def first_artifact(card: dict[str, Any]) -> str:
    for artifact in card.get("artifacts", []):
        if artifact.get("present"):
            return str(artifact.get("path", ""))
    return ""


def build_payload() -> dict[str, Any]:
    concierge = read_json(CONCIERGE_JSON)
    traction = read_json(TRACTION_JSON)
    gate = read_json(REVIEWER_GATE_JSON)
    cards = concierge.get("concierge_cards", [])
    cards = cards if isinstance(cards, list) else []

    docket_items = []
    for card in sorted(cards, key=lambda row: int(row.get("priority", 999))):
        lane_id = str(card.get("lane_id", ""))
        status = str(card.get("status", ""))
        action_type = ACTION_OVERRIDES.get(lane_id, {}).get(
            "action_type",
            STATUS_ACTION_TYPES.get(status, "human_review"),
        )
        action_due = ACTION_OVERRIDES.get(lane_id, {}).get(
            "action_due",
            parse_first_iso_date(str(card.get("deadline_or_gate", ""))),
        )
        docket_action = ACTION_OVERRIDES.get(lane_id, {}).get(
            "docket_action",
            DOCKET_ACTIONS_BY_TYPE.get(action_type, str(card.get("reviewer_action", ""))),
        )
        time_basis = ACTION_OVERRIDES.get(lane_id, {}).get(
            "time_basis",
            str(card.get("deadline_or_gate", "")),
        )
        item = {
            "lane_id": lane_id,
            "name": card.get("name", ""),
            "priority": int(card.get("priority", 999)),
            "channel": card.get("channel", ""),
            "status": status,
            "fit_score": card.get("fit_score", 0),
            "action_type": action_type,
            "action_due": action_due,
            "days_until_action_due": days_until(action_due),
            "urgency": urgency_for(action_due, action_type, status),
            "docket_action": docket_action,
            "time_basis": time_basis,
            "first_artifact": first_artifact(card),
            "artifact_present_count": card.get("artifact_present_count", 0),
            "artifact_missing_count": card.get("artifact_missing_count", 0),
            "decision_question": card.get("decision_question", ""),
            "human_gate": card.get("human_gate", ""),
            "claim_boundary": card.get("claim_boundary", ""),
            "no_final_action_rule": NO_FINAL_ACTION,
        }
        item["docket_item_sha256"] = hashlib.sha256(
            json.dumps(item, sort_keys=True).encode("utf-8")
        ).hexdigest()
        docket_items.append(item)

    urgency_counts: dict[str, int] = {}
    action_type_counts: dict[str, int] = {}
    for item in docket_items:
        urgency_counts[item["urgency"]] = urgency_counts.get(item["urgency"], 0) + 1
        action_type_counts[item["action_type"]] = action_type_counts.get(item["action_type"], 0) + 1

    immediate = [
        item
        for item in docket_items
        if item["urgency"] in {"IMMEDIATE_24H", "URGENT_5D"}
        and item["urgency"] != "PARKED_UNLESS_PARTNER"
    ]
    immediate_ids = [item["lane_id"] for item in immediate]
    all_artifacts_present = all(int(item["artifact_missing_count"]) == 0 for item in docket_items)
    gate_clear = bool(gate.get("reviewer_gate_clear")) and int(gate["summary"]["unsafe_secret_count"]) == 0 and int(gate["summary"]["unsafe_claim_count"]) == 0

    payload = {
        "generated_utc": now_utc(),
        "schema": "human_action_docket_v1",
        "current_date": CURRENT_DATE.isoformat(),
        "status": "HUMAN_ACTION_DOCKET_READY" if gate_clear and all_artifacts_present else "HUMAN_ACTION_DOCKET_BLOCKED",
        "summary": {
            "lane_count": len(docket_items),
            "immediate_or_urgent_count": len(immediate),
            "immediate_or_urgent_lane_ids": immediate_ids,
            "all_artifacts_present": all_artifacts_present,
            "reviewer_gate_clear": gate_clear,
            "unsafe_secret_count": int(gate["summary"]["unsafe_secret_count"]),
            "unsafe_claim_count": int(gate["summary"]["unsafe_claim_count"]),
            "traction_lane_count": int(traction["summary"]["lane_count"]),
            "concierge_lane_count": int(concierge["summary"]["lane_count"]),
            "human_action_required": True,
            "external_send_allowed_without_human": False,
            "final_submission_allowed_without_human": False,
            "live_trading_allowed": False,
            "urgency_counts": dict(sorted(urgency_counts.items())),
            "action_type_counts": dict(sorted(action_type_counts.items())),
        },
        "docket_items": sorted(
            docket_items,
            key=lambda item: (
                {
                    "IMMEDIATE_24H": 0,
                    "URGENT_5D": 1,
                    "ACTIVE_14D": 2,
                    "WATCHLIST": 3,
                    "ROLLING_OR_EVENT_GATED": 4,
                    "PARKED_UNLESS_PARTNER": 5,
                    "PAST_DATE_RECHECK": 6,
                }.get(item["urgency"], 9),
                item["days_until_action_due"] if item["days_until_action_due"] is not None else 999,
                int(item["priority"]),
            ),
        ),
        "source_ledgers": {
            "concierge": rel(CONCIERGE_JSON),
            "traction": rel(TRACTION_JSON),
            "reviewer_gate": rel(REVIEWER_GATE_JSON),
        },
        "human_stop_rule": NO_FINAL_ACTION,
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["docket_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Human Action Docket - 2026-07-09",
        "",
        "Purpose: convert the reviewer concierge packet into a date-aware action board that makes the next human moves obvious without authorizing external action.",
        "",
        f"Current date for this docket: `{payload['current_date']}`.",
        "",
        "## Gate Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Lanes: `{summary['lane_count']}`",
        f"- Immediate or urgent lanes: `{summary['immediate_or_urgent_count']}`",
        f"- All artifacts present: `{str(summary['all_artifacts_present']).lower()}`",
        f"- Reviewer gate clear: `{str(summary['reviewer_gate_clear']).lower()}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_secret_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Docket SHA-256: `{payload['docket_sha256']}`",
        "",
        "## Immediate And Urgent Lanes",
        "",
    ]
    urgent = [item for item in payload["docket_items"] if item["urgency"] in {"IMMEDIATE_24H", "URGENT_5D"}]
    for item in urgent:
        lines.extend(
            [
                f"### {item['name']}",
                "",
                f"- Lane ID: `{item['lane_id']}`",
                f"- Urgency: `{item['urgency']}`",
                f"- Action due: `{item['action_due']}`",
                f"- Days until due: `{item['days_until_action_due']}`",
                f"- Action: {item['docket_action']}",
                f"- Time basis: {item['time_basis']}",
                f"- First artifact: `{item['first_artifact']}`",
                f"- Human gate: {item['human_gate']}",
                f"- Claim boundary: {item['claim_boundary']}",
                f"- Item SHA-256: `{item['docket_item_sha256']}`",
                "",
            ]
        )
    lines.extend(["## Full Docket", ""])
    for item in payload["docket_items"]:
        lines.extend(
            [
                f"### {item['priority']}. {item['name']}",
                "",
                f"- Lane ID: `{item['lane_id']}`",
                f"- Channel: `{item['channel']}`",
                f"- Status: `{item['status']}`",
                f"- Action type: `{item['action_type']}`",
                f"- Urgency: `{item['urgency']}`",
                f"- Action due: `{item['action_due']}`",
                f"- Action: {item['docket_action']}",
                f"- First artifact: `{item['first_artifact']}`",
                f"- Decision question: {item['decision_question']}",
                f"- Human gate: {item['human_gate']}",
                f"- Claim boundary: {item['claim_boundary']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Human Stop Rule",
            "",
            payload["human_stop_rule"],
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
        raise SystemExit(f"Refusing to write sensitive public docket markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "lanes": payload["summary"]["lane_count"],
                "immediate_or_urgent": payload["summary"]["immediate_or_urgent_count"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
