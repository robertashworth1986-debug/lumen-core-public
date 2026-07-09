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

OUT_JSON = OUT_OPS / "sam_submission_and_today_opportunity_push_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "sam_submission_and_today_opportunity_push.json"
OUT_MD = SPRINT_DIR / "SAM_SUBMISSION_AND_TODAY_OPPORTUNITY_PUSH_2026-07-09.md"

SENSITIVE_MARKERS = [
    "password",
    "zoom.us",
    "meeting id",
    "one tap mobile",
    "private key",
    "refresh_token",
    "client_secret",
    "api_key",
    "sk-",
    "xox",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_payload() -> dict[str, Any]:
    submitted_pushes = [
        {
            "push_id": "sam_entity_renewal_submission",
            "type": "official_portal_submission",
            "status": "SUBMITTED_CONFIRMATION_RECEIVED",
            "submitted_at_local": "2026-07-09 17:39 America/New_York",
            "entity": "Robert Ashworth",
            "uei": "SQY2XW71ZM51",
            "cage": "14TM8",
            "browser_evidence": "SAM.gov page displayed Entity Registration Submitted and no action required at this time.",
            "email_evidence": {
                "gmail_message_id": "19f48d20c59295b2",
                "subject": (
                    "CONFIRMATION: Registration Submitted for Robert Ashworth / SQY2XW71ZM51 / "
                    "14TM8 in the U.S. Government's System for Award Management (SAM)"
                ),
                "received_local": "2026-07-09 17:39 America/New_York",
            },
            "control_boundary": [
                "Do not disclose OTPs or unmasked banking data.",
                "Monitor SAM status; confirmation is submission, not necessarily active renewal approval.",
            ],
        },
        {
            "push_id": "air_force_aac_rfi_capability_statement",
            "type": "federal_rfi_email_response",
            "status": "SENT",
            "opportunity": "SAF-AQ-RFI-26-0001",
            "recipient": "yvette.coddington@us.af.mil",
            "gmail_sent_id": "19f48d5933c9b5cb",
            "subject": "Response to SAF-AQ-RFI-26-0001 - LumenCore Advanced Automation Capability Statement",
            "attachment": "grant_submissions/funding_sprint_20260709/LUMENCORE_AAC_RFI_RESPONSE_SAF-AQ-RFI-26-0001_2026-07-09.pdf",
            "claim_boundary": [
                "Market research capability statement only.",
                "No award, agency validation, field deployment, certified assurance, FedRAMP/ATO, or realized savings claim.",
            ],
        },
        {
            "push_id": "fhwa_tsmo_capability_intent_note",
            "type": "federal_solicitation_contact_email",
            "status": "SENT_AS_CAPABILITY_NOTE_NOT_FINAL_PROPOSAL",
            "opportunity": "693JJ326R000012",
            "recipient": "Vivian.Riboli@dot.gov",
            "gmail_sent_id": "19f48d653b59eecb",
            "subject": "693JJ326R000012 - LumenCore TSMO Data Initiative capability note and submission-instruction request",
            "attachment": "grant_submissions/funding_sprint_20260709/LUMENCORE_FHWA_TSMO_CAPABILITY_NOTE_693JJ326R000012_2026-07-09.pdf",
            "claim_boundary": [
                "Capability and instruction-request note only.",
                "Not a final proposal, price, signed representation, or contract offer.",
            ],
        },
    ]

    remaining_gates = [
        {
            "gate_id": "fhwa_tsmo_full_proposal",
            "opportunity": "693JJ326R000012",
            "deadline": "2026-08-03",
            "next_action": "Download/verify official SAM attachments, build compliance matrix, complete Phase I technical capability volume.",
            "blocked_until": [
                "Official instructions and amendments are reviewed.",
                "Technical volume is finalized.",
                "Pricing/cost assumptions are approved by Robert.",
                "Final upload/submission screen is inspected.",
            ],
        },
        {
            "gate_id": "dsip_missionweave_phase1",
            "opportunity": "DLA26BZ03-NV011",
            "deadline": "2026-07-22",
            "next_action": "Clear DSIP Firm PIN/registration, then upload technical, commercialization, and cost volumes.",
            "blocked_until": [
                "DSIP Firm PIN and small-business registration are complete.",
                "Submitter authority and certifications are reviewed.",
                "Cost volume and upload preview are approved.",
            ],
        },
        {
            "gate_id": "nsf_seed_fund_pitch_or_invited_proposal",
            "opportunity": "NSF SBIR/STTR",
            "deadline": "depends_on_pitch_invitation_or_current_window",
            "next_action": "Confirm whether a project pitch is pending/invited before any NSF portal submission.",
            "blocked_until": [
                "NSF Project Pitch status is confirmed.",
                "No duplicate or conflicting NSF pitch/proposal is pending.",
                "Company eligibility and PI/Co-PI requirements are checked.",
            ],
        },
    ]

    payload = {
        "schema": "sam_submission_and_today_opportunity_push_v1",
        "generated_utc": now_utc(),
        "status": "SAM_SUBMITTED_AND_TODAY_OPPORTUNITY_PUSH_READY",
        "summary": {
            "sam_registration_submitted": True,
            "sam_confirmation_email_received": True,
            "same_day_external_push_count": 3,
            "same_day_federal_email_push_count": 2,
            "portal_submission_completed_count": 1,
            "remaining_portal_gate_count": len(remaining_gates),
            "air_force_aac_rfi_sent": True,
            "fhwa_tsmo_capability_note_sent": True,
            "external_send_allowed_without_human": False,
            "final_portal_submission_allowed_without_human": False,
            "live_trading_allowed": False,
        },
        "submitted_pushes": submitted_pushes,
        "remaining_gates": remaining_gates,
        "todays_decision": {
            "plain_english": (
                "Today moved the eligibility blocker and two credible federal traction lanes. SAM renewal was submitted. "
                "The Air Force AAC RFI was sent as a bounded capability statement. FHWA TSMO was contacted with a "
                "capability note and instruction request, while the full proposal remains gated by official package review."
            ),
            "what_was_not_done": [
                "No DSIP final submission was made without the Firm PIN and cost volume.",
                "No FHWA final proposal was represented as submitted.",
                "No FedRAMP, ATO, field validation, realized savings, or award status was claimed.",
                "No credentials, OTPs, bank data, or unreviewed raw proof vault were sent.",
            ],
        },
        "outputs": {
            "json": "out/ops/sam_submission_and_today_opportunity_push_latest.json",
            "dashboard_json": "dashboard/data/sam_submission_and_today_opportunity_push.json",
            "markdown": "grant_submissions/funding_sprint_20260709/SAM_SUBMISSION_AND_TODAY_OPPORTUNITY_PUSH_2026-07-09.md",
        },
    }
    payload["today_push_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# SAM Submission And Today Opportunity Push - 2026-07-09",
        "",
        "Purpose: record the SAM renewal submission and the same-day federal opportunity pushes without overstating what was actually submitted.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- SAM registration submitted: `{str(summary['sam_registration_submitted']).lower()}`",
        f"- SAM confirmation email received: `{str(summary['sam_confirmation_email_received']).lower()}`",
        f"- Same-day external pushes: `{summary['same_day_external_push_count']}`",
        f"- Same-day federal email pushes: `{summary['same_day_federal_email_push_count']}`",
        f"- Portal submissions completed: `{summary['portal_submission_completed_count']}`",
        f"- Remaining portal gates: `{summary['remaining_portal_gate_count']}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Final portal submission without human: `{str(summary['final_portal_submission_allowed_without_human']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Today push SHA-256: `{payload['today_push_sha256']}`",
        "",
        "## Submitted / Sent Today",
        "",
    ]
    for push in payload["submitted_pushes"]:
        lines.extend(
            [
                f"### {push['push_id']}",
                "",
                f"- Type: `{push['type']}`",
                f"- Status: `{push['status']}`",
            ]
        )
        for key in ("opportunity", "recipient", "gmail_sent_id", "subject", "attachment", "uei", "cage"):
            if key in push:
                lines.append(f"- {key.replace('_', ' ').title()}: `{push[key]}`")
        if "browser_evidence" in push:
            lines.append(f"- Browser evidence: {push['browser_evidence']}")
        if "email_evidence" in push:
            evidence = push["email_evidence"]
            lines.append(f"- Email evidence message ID: `{evidence['gmail_message_id']}`")
            lines.append(f"- Email evidence subject: {evidence['subject']}")
        if push.get("claim_boundary"):
            lines.append("- Claim boundary:")
            for item in push["claim_boundary"]:
                lines.append(f"  - {item}")
        if push.get("control_boundary"):
            lines.append("- Control boundary:")
            for item in push["control_boundary"]:
                lines.append(f"  - {item}")
        lines.append("")

    lines.extend(["## Remaining Gates", ""])
    for gate in payload["remaining_gates"]:
        lines.extend(
            [
                f"### {gate['gate_id']}",
                "",
                f"- Opportunity: `{gate['opportunity']}`",
                f"- Deadline: `{gate['deadline']}`",
                f"- Next action: {gate['next_action']}",
                "- Blocked until:",
            ]
        )
        for item in gate["blocked_until"]:
            lines.append(f"  - {item}")
        lines.append("")

    decision = payload["todays_decision"]
    lines.extend(["## Today's Decision", "", decision["plain_english"], "", "What was not done:"])
    for item in decision["what_was_not_done"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive public data-room markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "same_day_external_push_count": payload["summary"]["same_day_external_push_count"],
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
