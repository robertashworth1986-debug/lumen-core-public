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

TRACTION_JSON = OUT_OPS / "traction_opportunity_intake_ledger_latest.json"
REVIEWER_GATE_JSON = OUT_OPS / "funding_sprint_reviewer_gate_latest.json"
OUT_JSON = OUT_OPS / "reviewer_concierge_packet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "reviewer_concierge_packet.json"
OUT_MD = SPRINT_DIR / "REVIEWER_CONCIERGE_PACKET_INDEX_2026-07-09.md"

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

ARTIFACT_MAP: dict[str, list[str]] = {
    "evtit_blackdog_inkind": [
        "grant_submissions/funding_sprint_20260709/EVTIT_TRACTION_FOLLOWUP_PACKET_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md",
        "docs/PLATFORM_PROOF_AND_COMMERCIALIZATION_MAP.md",
        "docs/PROOF_TO_PILOT_CONTROL_ROOM_2026-06-25.md",
        "docs/LIVE_DOMAIN_PROOF_FEED_DEPLOY_BUNDLE_2026-06-27.md",
    ],
    "lvlup_first_check": [
        "grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md",
        "docs/PROOF_TO_REVENUE_ENGINE_2026-06-27.md",
        "docs/BUSINESS_PLAN_AND_LIVE_BREADTH_SEND_PACKET_2026-07-05.md",
    ],
    "darpa_dice_full_submission": [
        "grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md",
        "grant_submissions/DICE_HR001126S0010/DICE_SUBMISSION_READINESS.md",
        "grant_submissions/DICE_HR001126S0010/DICE_HEILMEIER_REVIEWER_MATRIX_2026-06-20.md",
        "grant_submissions/DICE_HR001126S0010/DICE_EVIDENCE_SYNTHESIS_2026-06-20.md",
        "grant_submissions/DICE_HR001126S0010/DICE_REFERENCE_RELEVANCE_MATRIX_2026-06-20.md",
    ],
    "fhwa_tsmo_data_initiative": [
        "grant_submissions/funding_sprint_20260709/FHWA_TSMO_PHASE1_TECHNICAL_CAPABILITY_OUTLINE_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/PROOF_STACK_EDGE_INDEX_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/AGENCY_GOV_PROTOCOL_READINESS_CONTROL_ROOM_2026-07-09.md",
    ],
    "nasa_data_center_rfi": [
        "grant_submissions/funding_sprint_20260709/NASA_DATA_CENTER_RFI_RESPONSE_OUTLINE_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/PROOF_STACK_EDGE_INDEX_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/AGENCY_GOV_PROTOCOL_READINESS_CONTROL_ROOM_2026-07-09.md",
    ],
    "dla_missionweave_sbir": [
        "grant_submissions/funding_sprint_20260709/DSIP_MISSIONWEAVE_FAST_SUBMISSION_PLAN_2026-07-09.md",
        "grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_READINESS.md",
        "docs/MISSIONWEAVE_GENERATED_WORKFLOW_VALIDATION_2026-06-13.md",
    ],
    "nsf_project_pitch": [
        "grant_submissions/funding_sprint_20260709/NSF_PROJECT_PITCH_DRAFT_2026-07-09.md",
        "grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_READINESS.md",
        "grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_PORTAL_FIELDS_2026-06-19.md",
    ],
    "epa_r10_icpoes_route": [
        "grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/FUNDING_ACTION_MATRIX_2026-07-09.md",
    ],
    "epa_ucmr6_partner_only": [
        "grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/FUNDING_ACTION_MATRIX_2026-07-09.md",
    ],
    "fhwa_infrastructure_baa_call3": [
        "grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/FHWA_TSMO_PHASE1_TECHNICAL_CAPABILITY_OUTLINE_2026-07-09.md",
    ],
    "hhs_ai_power_user_pilot": [
        "grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/AGENCY_GOV_PROTOCOL_READINESS_CONTROL_ROOM_2026-07-09.md",
    ],
    "csosa_public_safety_analytics": [
        "grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/AGENCY_GOV_PROTOCOL_READINESS_CONTROL_ROOM_2026-07-09.md",
    ],
    "defense_energy_consortium": [
        "grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md",
        "docs/PROOF_TO_PILOT_CONTROL_ROOM_2026-06-25.md",
    ],
    "openai_api_continuity": [
        "grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md",
        "docs/CURRENT_PROOF_POSTURE_AND_NEXT_TESTS_2026-07-03.md",
    ],
    "patent_deadline_counsel": [
        "grant_submissions/funding_sprint_20260709/IP_PATENT_CLAIM_BOUNDARY_REGISTER_2026-07-09.md",
        "grant_submissions/PATENT_LEGAL_RESCUE_PACKET_2026-06-20.md",
    ],
}

REVIEWER_PACKS = {
    "venture_engineering": {
        "audience": "engineering-for-equity reviewer",
        "best_first_read": "Live proof stack, build scope, validation workflow, and productization gaps.",
        "decision_question": "Can an in-kind engineering team accelerate proof portal, replay runner, manifest, and pilot onboarding?",
    },
    "venture_cash": {
        "audience": "early-check investor",
        "best_first_read": "Traction ledger, proof-to-revenue engine, and clean proof-to-pilot public link.",
        "decision_question": "Is a small first check useful enough to preserve execution velocity and unlock pilots?",
    },
    "federal_baa": {
        "audience": "BAA technical evaluator",
        "best_first_read": "Heilmeier matrix, evidence synthesis, compliance matrix, and human-gated submission controls.",
        "decision_question": "Does the proposal map a credible research objective to a bounded validation method?",
    },
    "federal_contract": {
        "audience": "contracting or technical capability reviewer",
        "best_first_read": "Capability outline, source provenance, risk boundaries, and agency protocol controls.",
        "decision_question": "Can LumenCore contribute a bounded evidence workflow without overstating operational deployment?",
    },
    "federal_rfi": {
        "audience": "market research reviewer",
        "best_first_read": "RFI response outline and source-backed concept map.",
        "decision_question": "Does the response provide useful market intelligence without claiming award readiness?",
    },
    "federal_sbir": {
        "audience": "SBIR reviewer",
        "best_first_read": "Phase I technical plan, innovation boundary, commercialization path, and proof-to-pilot evidence.",
        "decision_question": "Is the Phase I work scoped to produce independently reviewable technical evidence?",
    },
    "federal_market_research": {
        "audience": "agency routing contact",
        "best_first_read": "Boundary-safe routing note and partner-only decision record.",
        "decision_question": "Should LumenCore be routed to a data QA or validation need instead of a hardware buy?",
    },
    "federal_sources_sought": {
        "audience": "sources-sought reviewer",
        "best_first_read": "Partner-only filter and qualification boundary.",
        "decision_question": "Is there a qualified prime or lab partner before any response is drafted?",
    },
    "ip_readiness": {
        "audience": "patent counsel or IP reviewer",
        "best_first_read": "Claim-boundary register and legal rescue packet.",
        "decision_question": "What filing or claim action must licensed counsel verify before public expansion?",
    },
    "vendor_credit_or_partner_route": {
        "audience": "vendor credit or partner-program reviewer",
        "best_first_read": "Proof-stack continuity case and API continuity request.",
        "decision_question": "Can a temporary credit or startup route preserve grant/proof-factory continuity?",
    },
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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def artifact_rows(paths: list[str]) -> list[dict[str, Any]]:
    rows = []
    for item in paths:
        path = ROOT / item
        row = {
            "path": item,
            "present": path.exists(),
            "bytes": path.stat().st_size if path.exists() else 0,
            "sha256": sha256_file(path) if path.exists() else "",
        }
        rows.append(row)
    return rows


def build_payload() -> dict[str, Any]:
    traction = read_json(TRACTION_JSON)
    gate = read_json(REVIEWER_GATE_JSON)
    lanes = traction.get("lanes", [])
    if not isinstance(lanes, list):
        lanes = []

    concierge_cards = []
    for lane in sorted(lanes, key=lambda row: int(row.get("priority", 999))):
        lane_id = str(lane.get("lane_id", ""))
        channel = str(lane.get("channel", "unknown"))
        artifacts = artifact_rows(ARTIFACT_MAP.get(lane_id, []))
        present_count = sum(1 for item in artifacts if item["present"])
        pack = REVIEWER_PACKS.get(channel, {})
        card = {
            "lane_id": lane_id,
            "name": lane.get("name", ""),
            "priority": int(lane.get("priority", 999)),
            "channel": channel,
            "status": lane.get("status", ""),
            "fit_score": lane.get("fit_score", 0),
            "audience": pack.get("audience", "reviewer"),
            "best_first_read": pack.get("best_first_read", "Review the traction ledger and source artifacts."),
            "decision_question": pack.get("decision_question", "Decide whether to continue this lane."),
            "deadline_or_gate": lane.get("deadline_or_gate", ""),
            "reviewer_action": lane.get("reviewer_action", ""),
            "human_gate": lane.get("human_gate", ""),
            "claim_boundary": lane.get("claim_boundary", ""),
            "artifact_count": len(artifacts),
            "artifact_present_count": present_count,
            "artifact_missing_count": len(artifacts) - present_count,
            "artifacts": artifacts,
            "source_refs": lane.get("source_refs", []),
        }
        card["concierge_card_sha256"] = hashlib.sha256(
            json.dumps(card, sort_keys=True).encode("utf-8")
        ).hexdigest()
        concierge_cards.append(card)

    missing_artifacts = [
        {"lane_id": card["lane_id"], "path": item["path"]}
        for card in concierge_cards
        for item in card["artifacts"]
        if not item["present"]
    ]
    top_cards = [card for card in concierge_cards if card["priority"] <= 7]
    top_cards_complete = all(card["artifact_missing_count"] == 0 for card in top_cards)
    gate_clear = bool(gate.get("reviewer_gate_clear")) and int(gate["summary"]["unsafe_secret_count"]) == 0 and int(gate["summary"]["unsafe_claim_count"]) == 0

    payload = {
        "generated_utc": now_utc(),
        "schema": "reviewer_concierge_packet_v1",
        "status": "REVIEWER_CONCIERGE_READY_HUMAN_ACTION_REQUIRED" if gate_clear else "REVIEWER_CONCIERGE_BLOCKED_BY_GATE",
        "summary": {
            "lane_count": len(concierge_cards),
            "top_priority_count": len(top_cards),
            "top_priority_artifacts_complete": top_cards_complete,
            "missing_artifact_count": len(missing_artifacts),
            "reviewer_gate_clear": gate_clear,
            "unsafe_secret_count": int(gate["summary"]["unsafe_secret_count"]),
            "unsafe_claim_count": int(gate["summary"]["unsafe_claim_count"]),
            "human_action_required": True,
            "external_send_allowed_without_human": False,
            "final_submission_allowed_without_human": False,
        },
        "source_ledgers": {
            "traction_ledger": rel(TRACTION_JSON),
            "reviewer_gate": rel(REVIEWER_GATE_JSON),
        },
        "concierge_cards": concierge_cards,
        "missing_artifacts": missing_artifacts,
        "reviewer_route": [
            "Start with the priority queue.",
            "Open only the artifact rows for the lane being reviewed.",
            "Check the claim boundary before reusing text externally.",
            "Use the human gate as the stop condition before any send, upload, filing, or commitment.",
        ],
        "public_packet_rules": {
            "exclude_meeting_access_details": True,
            "exclude_credentials": True,
            "exclude_personal_financial_data": True,
            "exclude_unreviewed_archives": True,
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["concierge_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return payload


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Reviewer Concierge Packet Index - 2026-07-09",
        "",
        "Purpose: give a reviewer, investor, agency contact, partner, or counsel a one-stop index into the LumenCore proof stack without exposing meeting access details or unreviewed materials.",
        "",
        "This index is a navigation and decision-support artifact. It does not authorize sending, submitting, filing, certifying, accepting terms, trading, or moving capital.",
        "",
        "## Gate Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Lanes indexed: `{summary['lane_count']}`",
        f"- Top priority lanes: `{summary['top_priority_count']}`",
        f"- Top priority artifacts complete: `{str(summary['top_priority_artifacts_complete']).lower()}`",
        f"- Missing artifact references: `{summary['missing_artifact_count']}`",
        f"- Reviewer gate clear: `{str(summary['reviewer_gate_clear']).lower()}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_secret_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Concierge SHA-256: `{payload['concierge_sha256']}`",
        "",
        "## Reviewer Route",
        "",
    ]
    for item in payload["reviewer_route"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Priority Concierge Cards", ""])
    for card in payload["concierge_cards"]:
        lines.extend(
            [
                f"### {card['priority']}. {card['name']}",
                "",
                f"- Lane ID: `{card['lane_id']}`",
                f"- Audience: {card['audience']}",
                f"- Channel: `{card['channel']}`",
                f"- Status: `{card['status']}`",
                f"- Fit score: `{card['fit_score']}`",
                f"- Gate: {card['deadline_or_gate']}",
                f"- Best first read: {card['best_first_read']}",
                f"- Decision question: {card['decision_question']}",
                f"- Reviewer action: {card['reviewer_action']}",
                f"- Human gate: {card['human_gate']}",
                f"- Claim boundary: {card['claim_boundary']}",
                f"- Artifacts present: `{card['artifact_present_count']}/{card['artifact_count']}`",
                f"- Card SHA-256: `{card['concierge_card_sha256']}`",
                "",
                "Artifacts:",
            ]
        )
        for artifact in card["artifacts"]:
            state = "present" if artifact["present"] else "missing"
            lines.append(f"- `{state}` `{artifact['path']}` sha256=`{artifact['sha256']}`")
        lines.extend(["", "Source refs:"])
        for ref in card["source_refs"]:
            lines.append(f"- `{ref}`")
        lines.append("")
    lines.extend(["## Packet Rules", ""])
    for key, value in payload["public_packet_rules"].items():
        lines.append(f"- {key}: `{str(value).lower()}`")
    lines.extend(
        [
            "",
            "## Human Stop Rule",
            "",
            "A clear concierge packet means the materials are organized for review. It is not a substitute for human approval, legal review, portal authority, signature authority, counsel review, or investor-term acceptance.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive public concierge markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "lanes": payload["summary"]["lane_count"],
                "missing_artifacts": payload["summary"]["missing_artifact_count"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
