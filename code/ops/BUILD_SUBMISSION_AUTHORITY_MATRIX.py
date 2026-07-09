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

DOCKET_JSON = OUT_OPS / "human_action_docket_latest.json"
CONCIERGE_JSON = OUT_OPS / "reviewer_concierge_packet_latest.json"
REVIEWER_GATE_JSON = OUT_OPS / "funding_sprint_reviewer_gate_latest.json"
OUT_JSON = OUT_OPS / "submission_authority_matrix_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "submission_authority_matrix.json"
OUT_MD = SPRINT_DIR / "SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md"

NO_FINAL_AUTHORITY = (
    "No lane may be sent, uploaded, certified, filed, priced, accepted, traded, or funded "
    "without the named human authority gate."
)

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

AUTHORITY_BY_ACTION_TYPE: dict[str, dict[str, Any]] = {
    "meeting_prep": {
        "required_authority": "Robert attends the meeting and approves any follow-up, build scope, or equity-for-services discussion.",
        "readiness_mode": "MEETING_PREP_READY_FINAL_TERMS_BLOCKED",
        "can_prepare_internal": True,
        "can_send_external_without_human": False,
        "can_submit_without_human": False,
        "can_accept_terms_without_human": False,
        "pre_action_checks": [
            "Use only the public proof links and sanitized packet artifacts.",
            "Keep valuation, equity, and services terms human-decided.",
            "Do not include meeting access details in public or repo artifacts.",
        ],
    },
    "investor_watch": {
        "required_authority": "Robert approves any investor reply, diligence material, investor terms, or capital commitment.",
        "readiness_mode": "INVESTOR_WATCH_READY_RESPONSE_BLOCKED",
        "can_prepare_internal": True,
        "can_send_external_without_human": False,
        "can_submit_without_human": False,
        "can_accept_terms_without_human": False,
        "pre_action_checks": [
            "Send only requested materials or a measured follow-up after the review window.",
            "Reconfirm no performance, revenue, valuation, or award claim is overstated.",
            "Human reviews any instrument, SAFE, note, equity, or services term.",
        ],
    },
    "federal_baa_build": {
        "required_authority": "Robert verifies the controlling BAA instructions, submission account authority, budget, representations, and final package.",
        "readiness_mode": "FEDERAL_DRAFT_READY_SUBMISSION_BLOCKED",
        "can_prepare_internal": True,
        "can_send_external_without_human": False,
        "can_submit_without_human": False,
        "can_accept_terms_without_human": False,
        "pre_action_checks": [
            "Download or verify the controlling BAA package before final formatting.",
            "Build compliance matrix and attach only reviewed materials.",
            "Human approves budget, reps, certifications, and final upload.",
        ],
    },
    "federal_contract_build": {
        "required_authority": "Robert verifies SAM access, solicitation attachments, pricing, reps/certs, and authorized representative status before submission.",
        "readiness_mode": "FEDERAL_DRAFT_READY_SUBMISSION_BLOCKED",
        "can_prepare_internal": True,
        "can_send_external_without_human": False,
        "can_submit_without_human": False,
        "can_accept_terms_without_human": False,
        "pre_action_checks": [
            "Verify current SAM.gov package, amendments, contacts, due time, and required volumes.",
            "Human approves price, exceptions, representations, and signature authority.",
            "Keep claims bounded to proof-to-pilot evidence and no field deployment claim.",
        ],
    },
    "federal_rfi_build": {
        "required_authority": "Robert verifies official RFI instructions, contact address, page limits, and final send approval.",
        "readiness_mode": "RFI_DRAFT_READY_SEND_BLOCKED",
        "can_prepare_internal": True,
        "can_send_external_without_human": False,
        "can_submit_without_human": False,
        "can_accept_terms_without_human": False,
        "pre_action_checks": [
            "Verify official response instructions and deadline.",
            "Use market-research framing, not award or deployment language.",
            "Human approves final email or portal upload.",
        ],
    },
    "federal_sbir_build": {
        "required_authority": "Robert controls DSIP or SBIR portal login, Firm PIN, cost approval, certifications, and final submit.",
        "readiness_mode": "SBIR_DRAFT_READY_PORTAL_BLOCKED",
        "can_prepare_internal": True,
        "can_send_external_without_human": False,
        "can_submit_without_human": False,
        "can_accept_terms_without_human": False,
        "pre_action_checks": [
            "Human enters Firm PIN and confirms organization authority.",
            "Human approves cost volume, certifications, and upload preview.",
            "No integration or procurement readiness claim without agency evidence.",
        ],
    },
    "rolling_human_check": {
        "required_authority": "Robert verifies account status, platform-specific rules, one-pending-pitch limits, and final content before submit.",
        "readiness_mode": "ROLLING_GATE_READY_RULE_CHECK_REQUIRED",
        "can_prepare_internal": True,
        "can_send_external_without_human": False,
        "can_submit_without_human": False,
        "can_accept_terms_without_human": False,
        "pre_action_checks": [
            "Check whether any related pitch, invitation, or proposal is already pending.",
            "Confirm eligibility and portal account state before pressing submit.",
            "Human approves final text.",
        ],
    },
    "vendor_route": {
        "required_authority": "Robert approves vendor form content, account/billing implications, and any credit or discount terms.",
        "readiness_mode": "VENDOR_FORM_READY_HUMAN_SUBMIT_REQUIRED",
        "can_prepare_internal": True,
        "can_send_external_without_human": False,
        "can_submit_without_human": False,
        "can_accept_terms_without_human": False,
        "pre_action_checks": [
            "Use official vendor route only.",
            "Human reviews billing, account, and program terms.",
            "Do not represent credit approval unless the vendor grants it.",
        ],
    },
    "licensed_counsel_review": {
        "required_authority": "Licensed patent counsel and Robert decide any filing, continuation, PCT, disclosure, or claim strategy action.",
        "readiness_mode": "IP_PACKET_READY_COUNSEL_REQUIRED",
        "can_prepare_internal": True,
        "can_send_external_without_human": False,
        "can_submit_without_human": False,
        "can_accept_terms_without_human": False,
        "pre_action_checks": [
            "Prepare filed materials and claim-boundary packet.",
            "Do not expand public patent, ownership, or freedom-to-operate claims without counsel.",
            "Human and counsel approve any filing or disclosure action.",
        ],
    },
    "agency_routing_watch": {
        "required_authority": "Robert approves any further agency contact after a routing response.",
        "readiness_mode": "ROUTING_SENT_WAIT_FOR_RESPONSE",
        "can_prepare_internal": True,
        "can_send_external_without_human": False,
        "can_submit_without_human": False,
        "can_accept_terms_without_human": False,
        "pre_action_checks": [
            "Do not prepare a hardware or prime quote.",
            "Wait for routing signal or partner path.",
            "Human approves any follow-up message.",
        ],
    },
    "partner_only": {
        "required_authority": "Qualified partner and Robert approve any partner-led response.",
        "readiness_mode": "PARTNER_REQUIRED_NO_SOLO_SUBMISSION",
        "can_prepare_internal": True,
        "can_send_external_without_human": False,
        "can_submit_without_human": False,
        "can_accept_terms_without_human": False,
        "pre_action_checks": [
            "Identify qualified prime or regulated-domain partner first.",
            "Do not claim prime qualifications LumenCore does not hold.",
            "Human approves outreach and role boundary.",
        ],
    },
    "partner_intro_only": {
        "required_authority": "Robert approves any strategic partner or investor introduction before outreach.",
        "readiness_mode": "INTRO_MATERIAL_READY_NO_SOLO_PROPOSAL",
        "can_prepare_internal": True,
        "can_send_external_without_human": False,
        "can_submit_without_human": False,
        "can_accept_terms_without_human": False,
        "pre_action_checks": [
            "Use as partner/investor context, not a solo bid.",
            "Human approves the intro target and positioning.",
            "No project-financing or performance claim unless externally documented.",
        ],
    },
    "park_partner_only": {
        "required_authority": "Qualified compliant platform or prime partner must lead before this lane is reopened.",
        "readiness_mode": "PARKED_NO_SOLO_ACTION",
        "can_prepare_internal": False,
        "can_send_external_without_human": False,
        "can_submit_without_human": False,
        "can_accept_terms_without_human": False,
        "pre_action_checks": [
            "Do not spend proposal time without a qualified partner.",
            "Keep as market intelligence only.",
            "Human approves any partner-specific reactivation.",
        ],
    },
    "topic_fit_check": {
        "required_authority": "Robert approves topic selection after official attachments and topic fit are reviewed.",
        "readiness_mode": "TOPIC_SCOUT_READY_SELECTION_REQUIRED",
        "can_prepare_internal": True,
        "can_send_external_without_human": False,
        "can_submit_without_human": False,
        "can_accept_terms_without_human": False,
        "pre_action_checks": [
            "Download official attachments.",
            "Score topic fit before drafting.",
            "Human approves the selected topic and response plan.",
        ],
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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_payload() -> dict[str, Any]:
    docket = read_json(DOCKET_JSON)
    concierge = read_json(CONCIERGE_JSON)
    gate = read_json(REVIEWER_GATE_JSON)
    docket_items = docket.get("docket_items", [])
    docket_items = docket_items if isinstance(docket_items, list) else []

    rows = []
    for item in sorted(docket_items, key=lambda row: int(row.get("priority", 999))):
        action_type = str(item.get("action_type", "human_review"))
        authority = AUTHORITY_BY_ACTION_TYPE[action_type]
        row = {
            "lane_id": item.get("lane_id", ""),
            "name": item.get("name", ""),
            "priority": int(item.get("priority", 999)),
            "channel": item.get("channel", ""),
            "status": item.get("status", ""),
            "action_type": action_type,
            "urgency": item.get("urgency", ""),
            "action_due": item.get("action_due"),
            "readiness_mode": authority["readiness_mode"],
            "can_prepare_internal": authority["can_prepare_internal"],
            "can_send_external_without_human": authority["can_send_external_without_human"],
            "can_submit_without_human": authority["can_submit_without_human"],
            "can_accept_terms_without_human": authority["can_accept_terms_without_human"],
            "required_authority": authority["required_authority"],
            "pre_action_checks": authority["pre_action_checks"],
            "first_artifact": item.get("first_artifact", ""),
            "artifact_missing_count": item.get("artifact_missing_count", 0),
            "claim_boundary": item.get("claim_boundary", ""),
            "decision_question": item.get("decision_question", ""),
            "authority_stop_rule": NO_FINAL_AUTHORITY,
        }
        row["authority_row_sha256"] = hashlib.sha256(
            json.dumps(row, sort_keys=True).encode("utf-8")
        ).hexdigest()
        rows.append(row)

    readiness_counts: dict[str, int] = {}
    action_type_counts: dict[str, int] = {}
    for row in rows:
        readiness_counts[str(row["readiness_mode"])] = readiness_counts.get(str(row["readiness_mode"]), 0) + 1
        action_type_counts[str(row["action_type"])] = action_type_counts.get(str(row["action_type"]), 0) + 1

    gate_clear = bool(gate.get("reviewer_gate_clear")) and int(gate["summary"]["unsafe_secret_count"]) == 0 and int(gate["summary"]["unsafe_claim_count"]) == 0
    all_artifacts_present = all(int(row["artifact_missing_count"]) == 0 for row in rows)
    all_final_actions_blocked = all(
        not row["can_send_external_without_human"]
        and not row["can_submit_without_human"]
        and not row["can_accept_terms_without_human"]
        for row in rows
    )

    payload = {
        "generated_utc": now_utc(),
        "schema": "submission_authority_matrix_v1",
        "status": "SUBMISSION_AUTHORITY_MATRIX_READY" if gate_clear and all_artifacts_present and all_final_actions_blocked else "SUBMISSION_AUTHORITY_MATRIX_BLOCKED",
        "summary": {
            "lane_count": len(rows),
            "docket_lane_count": int(docket["summary"]["lane_count"]),
            "concierge_lane_count": int(concierge["summary"]["lane_count"]),
            "all_artifacts_present": all_artifacts_present,
            "reviewer_gate_clear": gate_clear,
            "all_final_actions_blocked_without_human": all_final_actions_blocked,
            "internal_prepare_allowed_count": sum(1 for row in rows if row["can_prepare_internal"]),
            "parked_no_solo_count": sum(1 for row in rows if row["readiness_mode"] in {"PARKED_NO_SOLO_ACTION", "PARTNER_REQUIRED_NO_SOLO_SUBMISSION", "INTRO_MATERIAL_READY_NO_SOLO_PROPOSAL"}),
            "unsafe_secret_count": int(gate["summary"]["unsafe_secret_count"]),
            "unsafe_claim_count": int(gate["summary"]["unsafe_claim_count"]),
            "external_send_allowed_without_human": False,
            "final_submission_allowed_without_human": False,
            "live_trading_allowed": False,
            "readiness_counts": dict(sorted(readiness_counts.items())),
            "action_type_counts": dict(sorted(action_type_counts.items())),
        },
        "authority_rows": rows,
        "source_ledgers": {
            "docket": rel(DOCKET_JSON),
            "concierge": rel(CONCIERGE_JSON),
            "reviewer_gate": rel(REVIEWER_GATE_JSON),
        },
        "authority_stop_rule": NO_FINAL_AUTHORITY,
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["authority_matrix_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Submission Authority Matrix - 2026-07-09",
        "",
        "Purpose: make authority, account, counsel, pricing, and final-action responsibility explicit for every live LumenCore lane.",
        "",
        "This matrix is not a submission approval. It separates preparation work from the human authority gates required before anything leaves the system.",
        "",
        "## Gate Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Lanes: `{summary['lane_count']}`",
        f"- All artifacts present: `{str(summary['all_artifacts_present']).lower()}`",
        f"- Reviewer gate clear: `{str(summary['reviewer_gate_clear']).lower()}`",
        f"- All final actions blocked without human: `{str(summary['all_final_actions_blocked_without_human']).lower()}`",
        f"- Internal prepare allowed: `{summary['internal_prepare_allowed_count']}`",
        f"- No-solo or partner-only lanes: `{summary['parked_no_solo_count']}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_secret_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Authority matrix SHA-256: `{payload['authority_matrix_sha256']}`",
        "",
        "## Authority Rows",
        "",
    ]
    for row in payload["authority_rows"]:
        lines.extend(
            [
                f"### {row['priority']}. {row['name']}",
                "",
                f"- Lane ID: `{row['lane_id']}`",
                f"- Channel: `{row['channel']}`",
                f"- Status: `{row['status']}`",
                f"- Action type: `{row['action_type']}`",
                f"- Urgency: `{row['urgency']}`",
                f"- Action due: `{row['action_due']}`",
                f"- Readiness mode: `{row['readiness_mode']}`",
                f"- Can prepare internally: `{str(row['can_prepare_internal']).lower()}`",
                f"- Can send externally without human: `{str(row['can_send_external_without_human']).lower()}`",
                f"- Can submit without human: `{str(row['can_submit_without_human']).lower()}`",
                f"- Can accept terms without human: `{str(row['can_accept_terms_without_human']).lower()}`",
                f"- Required authority: {row['required_authority']}",
                f"- First artifact: `{row['first_artifact']}`",
                f"- Claim boundary: {row['claim_boundary']}",
                f"- Decision question: {row['decision_question']}",
                f"- Row SHA-256: `{row['authority_row_sha256']}`",
                "",
                "Pre-action checks:",
            ]
        )
        for check in row["pre_action_checks"]:
            lines.append(f"- {check}")
        lines.append("")
    lines.extend(["## Authority Stop Rule", "", payload["authority_stop_rule"]])
    return "\n".join(lines) + "\n"


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive public authority markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "lanes": payload["summary"]["lane_count"],
                "all_final_actions_blocked": payload["summary"]["all_final_actions_blocked_without_human"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
