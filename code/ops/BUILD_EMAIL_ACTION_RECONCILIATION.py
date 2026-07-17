from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
JSON_OUT = SPRINT_DIR / "EMAIL_ACTION_RECONCILIATION_2026-07-17.json"
MD_OUT = SPRINT_DIR / "EMAIL_ACTION_RECONCILIATION_2026-07-17.md"

AS_OF_DATE = "2026-07-17"


def build_payload() -> dict[str, Any]:
    lanes = [
        {
            "lane_id": "epri_open_power_ai_mou",
            "organization": "EPRI Open Power AI Consortium",
            "latest_event_type": "AUTOMATIC_OUT_OF_OFFICE",
            "latest_event_utc": "2026-07-17T03:51:16Z",
            "state": "MOU_ROUTING_SENT_OUT_OF_OFFICE_RECEIVED",
            "out_of_office_through": "2026-07-20",
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": "2026-07-23",
            "next_action": (
                "Wait for the MOU, a correction request, or an onboarding question; "
                "do not resend identity details."
            ),
        },
        {
            "lane_id": "georgia_patents_pro_bono_intake",
            "organization": "Georgia PATENTS",
            "latest_event_type": "OUTBOUND_INTAKE_SENT",
            "latest_event_utc": "2026-07-17T04:27:26Z",
            "state": "OUTBOUND_SENT_INTAKE_RESPONSE_PENDING",
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": "2026-07-24",
            "next_action": (
                "Wait for intake instructions; do not disclose unpublished patent "
                "materials through ordinary email."
            ),
        },
        {
            "lane_id": "lanl_vision_licensing_followup",
            "organization": "Los Alamos National Laboratory",
            "latest_event_type": "OUTBOUND_PACKAGE_SENT",
            "latest_event_utc": "2026-07-16T18:50:16Z",
            "state": "PACKAGE_SENT_RESPONSE_PENDING",
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": "2026-07-23",
            "next_action": (
                "Wait for LANL; use the single bounded follow-up only on or after "
                "July 23 if no reply arrives."
            ),
        },
        {
            "lane_id": "cdc_ai_acquisition_rfi",
            "organization": "Centers for Disease Control and Prevention",
            "latest_event_type": "AGENCY_RECEIPT_CONFIRMED",
            "latest_event_utc": "2026-07-16T13:34:05Z",
            "state": "RECEIPT_CONFIRMED_FOLLOW_UP_PENDING",
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "next_action": (
                "Monitor for a CDC clarification, replacement request, or scheduling "
                "message; do not resend the response."
            ),
        },
        {
            "lane_id": "lvlup_optional_paid_event",
            "organization": "LvlUp Ventures / Power of the Pitch Week",
            "latest_event_type": "OPTIONAL_SPONSOR_TERMS_CLARIFIED",
            "latest_event_utc": "2026-07-16T13:31:23Z",
            "state": "OPTIONAL_PAID_EVENT_NO_REQUIRED_REPLY_OR_SPEND",
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "next_action": (
                "No reply or purchase; reconsider only if a relevant no-fee route or "
                "written non-pay-to-play selection terms arrive."
            ),
        },
        {
            "lane_id": "terry_vynetic_followup",
            "organization": "Terry Anderton / Vynetic",
            "latest_event_type": "TWO_NEAR_DUPLICATE_OUTBOUND_FOLLOWUPS",
            "latest_event_utc": "2026-07-16T16:58:56Z",
            "state": "OUTBOUND_FOLLOWUPS_SENT_NO_INBOUND_REPLY",
            "outbound_followup_count": 2,
            "outbound_spacing_seconds": 10,
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "next_action": (
                "Send nothing further unless Terry replies with a specific ask; then "
                "answer only that ask in the existing thread."
            ),
        },
        {
            "lane_id": "nsf_project_pitch",
            "organization": "U.S. National Science Foundation",
            "latest_event_type": "MAILBOX_INVITATION_SEARCH",
            "latest_event_utc": None,
            "state": "NO_OFFICIAL_PROJECT_PITCH_INVITATION_VERIFIED",
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "next_action": (
                "Use the rolling Project Pitch portal route; do not represent the July "
                "27 full-proposal deadline as reachable without an invitation."
            ),
        },
        {
            "lane_id": "nasa_data_center_rfi",
            "organization": "NASA",
            "latest_event_type": "SENT_RECEIPT_RECONCILIATION",
            "latest_event_utc": "2026-07-13T21:27:12Z",
            "state": "SENT_VERIFIED_RESPONSE_PENDING",
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "next_action": "Monitor for an agency clarification or replacement request.",
        },
        {
            "lane_id": "army_aidp_draft_cfs_feedback",
            "organization": "U.S. Army",
            "latest_event_type": "SENT_RECEIPT_RECONCILIATION",
            "latest_event_utc": "2026-07-13T21:27:05Z",
            "state": "SENT_VERIFIED_RESPONSE_PENDING",
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "next_action": "Monitor for agency feedback; do not duplicate-send.",
        },
        {
            "lane_id": "sam_public_credential_rotation",
            "organization": "SAM.gov account credential control",
            "latest_event_type": "OFFICIAL_ROTATION_REMINDER",
            "latest_event_utc": "2026-07-16T08:07:36Z",
            "state": "ACCOUNT_ACTION_REQUIRED_NO_EMAIL_REPLY",
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "next_action": (
                "Complete the authenticated account rotation and hidden local install; "
                "do not reply to renewal solicitations or publish the credential."
            ),
        },
    ]
    return {
        "schema": "lumencore.email_action_reconciliation.v1",
        "as_of_date": AS_OF_DATE,
        "status": "NO_NEW_DEADLINE_CRITICAL_EMAIL_ACTION",
        "evidence_method": (
            "Connected Gmail metadata and relevant-thread reconciliation against sent "
            "receipts and the canonical response register."
        ),
        "search_scope": [
            "Funding, grant, contract, SBIR/STTR, DSIP, NSF, SAM.gov, and Research.gov",
            "Patent routing and Georgia PATENTS",
            "LANL VISION and licensing follow-up",
            "EPRI Open Power AI Consortium onboarding",
            "CDC, NASA, Army, LvlUp, Terry Anderton, and Vynetic",
        ],
        "summary": {
            "lane_count": len(lanes),
            "email_reply_required_count": sum(
                1 for lane in lanes if lane["email_reply_required"]
            ),
            "send_now_count": sum(1 for lane in lanes if lane["send_now"]),
            "duplicate_outbound_risk_count": 1,
            "out_of_office_count": 1,
            "human_account_action_count": 1,
            "external_send_allowed_without_human": False,
        },
        "lanes": lanes,
        "excluded_message_classes": [
            "Personal finance and payment notices",
            "Account-security and password-reset notices",
            "Newsletters, social notifications, and job-alert bulk mail",
        ],
        "claim_boundary": (
            "This dated mailbox reconciliation records only the messages observable at "
            "the check. It does not prove that no later message exists, portal state, "
            "eligibility, submission, acceptance, award, validation, or authorization "
            "to disclose private account or patent information."
        ),
    }


def validate_payload(payload: dict[str, Any]) -> None:
    if payload["schema"] != "lumencore.email_action_reconciliation.v1":
        raise ValueError("Email reconciliation schema is invalid")
    if payload["summary"]["email_reply_required_count"] != 0:
        raise ValueError("A reply-required lane needs separate action review")
    if payload["summary"]["send_now_count"] != 0:
        raise ValueError("A send-now lane needs separate action review")
    if any(lane["send_now"] for lane in payload["lanes"]):
        raise ValueError("The no-send reconciliation contains a send-now lane")
    terry = next(
        lane for lane in payload["lanes"] if lane["lane_id"] == "terry_vynetic_followup"
    )
    if terry["outbound_followup_count"] != 2:
        raise ValueError("Terry duplicate-send guard is incomplete")


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Email Action Reconciliation",
        "",
        f"As of: {payload['as_of_date']}",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Control Line",
        "",
        f"- Reconciled lanes: `{summary['lane_count']}`",
        f"- Reply required now: `{summary['email_reply_required_count']}`",
        f"- Send now: `{summary['send_now_count']}`",
        f"- Duplicate-outbound risks: `{summary['duplicate_outbound_risk_count']}`",
        f"- Human account actions: `{summary['human_account_action_count']}`",
        "- Browser navigation performed: `false`",
        "",
        "## Reconciled Lanes",
        "",
        "| Lane | State | Reply now | Next action |",
        "|---|---|---:|---|",
    ]
    for lane in payload["lanes"]:
        lines.append(
            f"| {lane['organization']} | `{lane['state']}` | "
            f"`{str(lane['email_reply_required']).lower()}` | {lane['next_action']} |"
        )
    lines.extend(
        [
            "",
            "## Excluded Message Classes",
            "",
            *[f"- {item}" for item in payload["excluded_message_classes"]],
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    validate_payload(payload)
    SPRINT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    MD_OUT.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "lane_count": payload["summary"]["lane_count"],
                "send_now_count": payload["summary"]["send_now_count"],
                "json": JSON_OUT.relative_to(ROOT).as_posix(),
                "markdown": MD_OUT.relative_to(ROOT).as_posix(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
