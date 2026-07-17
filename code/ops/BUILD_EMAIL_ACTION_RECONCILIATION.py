from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
JSON_OUT = SPRINT_DIR / "EMAIL_ACTION_RECONCILIATION_2026-07-17.json"
MD_OUT = SPRINT_DIR / "EMAIL_ACTION_RECONCILIATION_2026-07-17.md"
NASHVILLE_OFFICIAL_DEADLINE_CONFIRMATION = (
    ROOT
    / "grant_submissions"
    / "NASHVILLE_EC_FALL_2026"
    / "NASHVILLE_EC_OFFICIAL_DEADLINE_CONFIRMATION_2026-07-17.json"
)
LVLUP_REVIEW_CONFIRMATION = (
    SPRINT_DIR / "LVLUP_INDEPENDENT_REVIEW_CONFIRMATION_2026-07-17.json"
)
DARPA_SN_26_97_RECEIPT = (
    SPRINT_DIR / "DARPA_SN_26_97_PUBLIC_SUBMISSION_RECEIPT_2026-07-17.json"
)
MISSIONWEAVE_ACTION_GATE = (
    ROOT
    / "grant_submissions"
    / "DLA26BZ03_NV011_MissionWeave"
    / "MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json"
)
OPENAI_BUILD_WEEK_READINESS = (
    ROOT
    / "grant_submissions"
    / "OPENAI_BUILD_WEEK_20260721"
    / "OPENAI_BUILD_WEEK_SUBMISSION_READINESS_2026-07-17.json"
)
OPENAI_BUILD_WEEK_HANDOFF_CONTROL = (
    ROOT
    / "grant_submissions"
    / "OPENAI_BUILD_WEEK_20260721"
    / "BUILD_WEEK_HANDOFF_INTEGRITY_CONTROL_2026-07-17.json"
)

AS_OF_DATE = "2026-07-17"


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def artifact_status(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "present": True,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest().upper(),
    }


def build_payload() -> dict[str, Any]:
    nashville = read_json(NASHVILLE_OFFICIAL_DEADLINE_CONFIRMATION)
    lvlup = read_json(LVLUP_REVIEW_CONFIRMATION)
    darpa = read_json(DARPA_SN_26_97_RECEIPT)
    missionweave = read_json(MISSIONWEAVE_ACTION_GATE)
    build_week = read_json(OPENAI_BUILD_WEEK_READINESS)
    build_week_handoff = read_json(OPENAI_BUILD_WEEK_HANDOFF_CONTROL)
    if (
        nashville.get("schema")
        != "lumencore.nashville_ec_official_deadline_confirmation.v1"
        or nashville.get("status")
        != "OFFICIAL_SUPPORT_CONFIRMED_CLOSE_TIME_APPLICATION_NOT_SUBMITTED"
    ):
        raise ValueError("Nashville official deadline confirmation is missing or stale")
    if (
        lvlup.get("schema")
        != "lumencore.lvlup_independent_review_confirmation.v1"
        or lvlup.get("status")
        != "WRITTEN_NO_SPONSOR_SPEND_INDEPENDENT_REVIEW_CONFIRMED"
    ):
        raise ValueError("LvlUp independent-review confirmation is missing or stale")
    if (
        darpa.get("schema")
        != "lumencore.darpa_sn_26_97_public_submission_receipt.v1"
        or darpa.get("status")
        != "FORMAL_RFI_PACKAGE_SENT_AGENCY_RECEIPT_PENDING"
    ):
        raise ValueError("DARPA-SN-26-97 public receipt is missing or stale")
    if (
        missionweave.get("schema") != "lumencore.missionweave_dsip_action_gate.v1"
        or missionweave.get("status") != "PRIVATE_DSIP_FACTS_CAPTURED_GATES_OPEN"
    ):
        raise ValueError("MissionWeave DSIP action gate is missing or stale")
    if (
        build_week.get("schema")
        != "lumencore.openai_build_week_submission_readiness.v1"
        or build_week.get("status")
        != "PROJECT_CORE_VERIFIED_EXTERNAL_SUBMISSION_FIELDS_OPEN"
    ):
        raise ValueError("OpenAI Build Week readiness is missing or stale")
    if (
        build_week_handoff.get("schema")
        != "lumencore.build_week_handoff_integrity_control.v1"
        or build_week_handoff.get("status")
        != "REFERENCED_HANDOFF_UNAVAILABLE_EXECUTION_SCOPE_BOUNDED"
        or build_week_handoff.get("integrity_findings", {}).get(
            "full_handoff_body_available"
        )
        is not False
    ):
        raise ValueError("OpenAI Build Week handoff integrity control is missing or stale")

    lanes = [
        {
            "lane_id": "nashville_ec_takeoff_fall_2026",
            "organization": "Nashville Entrepreneur Center",
            "latest_event_type": "OFFICIAL_DEADLINE_CONFIRMATION_RECEIVED",
            "latest_event_utc": nashville["source"]["received_utc"],
            "state": nashville["status"],
            "operational_local_deadline": nashville["confirmation"][
                "operational_local_deadline"
            ],
            "operational_utc_deadline": nashville["confirmation"][
                "operational_utc_deadline"
            ],
            "deadline_timezone_explicit_in_message": nashville["confirmation"][
                "timezone_explicit_in_message"
            ],
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": (
                "Complete the founder-fact and reviewed portal workflow well before the "
                "confirmed close; do not resend and do not treat the support reply as an application."
            ),
        },
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
            "do_not_duplicate_send": True,
            "next_action": (
                "Wait for the MOU, a correction request, or an onboarding question; "
                "do not resend identity details."
            ),
        },
        {
            "lane_id": "georgia_patents_pro_bono_intake",
            "organization": "Georgia PATENTS",
            "latest_event_type": "SERVICE_SCOPE_DECLINE_RECEIVED",
            "latest_event_utc": "2026-07-17T16:14:15Z",
            "state": "SERVICE_NOT_OFFERED_FOR_ALREADY_FILED_APPLICATION",
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": (
                "Close this pro bono route without a reply. Continue the private Patent Center "
                "docket capture, USPTO Pro Se procedural route, and a verified practitioner "
                "referral without emailing unpublished application material."
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
            "do_not_duplicate_send": True,
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
            "do_not_duplicate_send": True,
            "next_action": (
                "Monitor for a CDC clarification, replacement request, or scheduling "
                "message; do not resend the response."
            ),
        },
        {
            "lane_id": "darpa_sn_26_97_low_resource_computing_rfi",
            "organization": "DARPA Multi X Office",
            "latest_event_type": "FORMAL_TWO_ATTACHMENT_RFI_PACKAGE_SENT",
            "latest_event_utc": darpa["thread_reconciliation"]["formal_package_sent_utc"],
            "state": darpa["status"],
            "deadline_date": darpa["opportunity"]["deadline_date"],
            "deadline_time_compliance_claimed": False,
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "attachment_count": len(darpa["attachments"]),
            "next_action": darpa["send_control"]["next_action"],
        },
        {
            "lane_id": "missionweave_dsip_proposal",
            "organization": "Defense SBIR/STTR Innovation Portal",
            "latest_event_type": "DSIP_PROPOSAL_CREATION_CONFIRMED",
            "latest_event_utc": "2026-07-17T18:12:03Z",
            "state": missionweave["status"],
            "deadline_utc": missionweave["deadline"]["expected_utc"],
            "open_gate_count": missionweave["gate_summary"]["open_gate_count"],
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": (
                "Complete and endorse all DSIP volumes, resolve the live legal/entity, CMMC, "
                "ITAR, cost, support, and authority gates, review the portal preview, and obtain "
                "action-time approval before final submission."
            ),
        },
        {
            "lane_id": "openai_build_week_prooflock",
            "organization": "OpenAI Build Week / Devpost",
            "latest_event_type": "PROJECT_CORE_VERIFIED_SUBMISSION_FIELDS_OPEN",
            "latest_event_utc": build_week["generated_utc"],
            "state": build_week["status"],
            "deadline_utc": build_week["official_requirements"]["facts"][
                "submission_period"
            ]["deadline_utc"],
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": (
                "Confirm model provenance and the /feedback session ID, deploy the public demo, "
                "record the required public video, complete Devpost registration, and obtain "
                "action-time approval before final submission."
            ),
        },
        {
            "lane_id": "openai_build_week_internal_handoff",
            "organization": "OpenAI Build Week internal handoff",
            "latest_event_type": "SELF_SENT_HANDOFF_REFERENCE_WITHOUT_ATTACHMENT",
            "latest_event_utc": build_week_handoff["as_of_utc"],
            "state": build_week_handoff["status"],
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "embedded_rule_count": build_week_handoff["integrity_findings"][
                "embedded_rule_count"
            ],
            "full_handoff_body_available": build_week_handoff["integrity_findings"][
                "full_handoff_body_available"
            ],
            "next_action": (
                "Resend or privately place the exact named handoff, then refresh its integrity "
                "receipt. Until then, preserve the ten embedded rules and do not invent the "
                "missing Evidence Lattice design or completion criteria."
            ),
        },
        {
            "lane_id": "lvlup_optional_paid_event",
            "organization": "LvlUp Ventures / Power of the Pitch Week",
            "latest_event_type": "INDEPENDENT_REVIEW_CONTINUATION_CONFIRMED",
            "latest_event_utc": lvlup["source"]["received_utc"],
            "state": lvlup["status"],
            "written_independent_review_confirmation": True,
            "paid_sponsor_purchase_required_for_separate_review": False,
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": lvlup["required_next_action"],
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
            "do_not_duplicate_send": True,
            "next_action": (
                "Send nothing further unless Terry replies with a specific ask; then "
                "answer only that ask in the existing thread."
            ),
        },
        {
            "lane_id": "fhwa_tsmo_qualified_partner_outreach",
            "organization": "Cambridge Systematics",
            "latest_event_type": "RESPONSE_LEAD_TEAM_SET_DECLINE_RECEIVED",
            "latest_event_utc": "2026-07-17T16:28:25Z",
            "state": "RESPONSE_LEAD_DECLINED_ADDITIONAL_PARTNER_TEAM_SET",
            "delivery_failure_count": 1,
            "replacement_send_count": 1,
            "confirmed_delivery_count": 1,
            "inbound_response_count": 2,
            "qualified_response_lead_referral_count": 1,
            "threaded_acknowledgment_send_count": 1,
            "fit_check_confirmed_count": 0,
            "team_set_decline_count": 1,
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": (
                "Close this route without another reply or follow-up. Do not claim a partner or "
                "use Cambridge Systematics' experience. Reopen only for a future opportunity "
                "initiated by the firm."
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
            "do_not_duplicate_send": False,
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
            "do_not_duplicate_send": True,
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
            "do_not_duplicate_send": True,
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
            "do_not_duplicate_send": True,
            "next_action": (
                "Complete the authenticated account rotation and hidden local install; "
                "do not reply to renewal solicitations or publish the credential."
            ),
        },
    ]
    return {
        "schema": "lumencore.email_action_reconciliation.v1",
        "as_of_date": AS_OF_DATE,
        "status": "NO_UNANSWERED_DEADLINE_CRITICAL_EMAIL_ACTION",
        "evidence_method": (
            "Connected Gmail metadata and relevant-thread reconciliation against sent "
            "receipts and the canonical response register."
        ),
        "search_scope": [
            "Funding, grant, contract, SBIR/STTR, DSIP, NSF, SAM.gov, and Research.gov",
            "Patent routing and Georgia PATENTS",
            "LANL VISION and licensing follow-up",
            "EPRI Open Power AI Consortium onboarding",
            "FHWA TSMO qualified-partner outreach",
            "Nashville EC Fall 2026 TakeOff deadline-support query",
            "DARPA-SN-26-97 formal RFI response and agency-thread state",
            "MissionWeave DSIP and OpenAI Build Week portal deadlines",
            "OpenAI Build Week self-sent handoff attachment integrity",
            "CDC, NASA, Army, LvlUp, Terry Anderton, and Vynetic",
        ],
        "summary": {
            "lane_count": len(lanes),
            "email_reply_required_count": sum(
                1 for lane in lanes if lane["email_reply_required"]
            ),
            "send_now_count": sum(1 for lane in lanes if lane["send_now"]),
            "duplicate_outbound_risk_count": sum(
                1 for lane in lanes if lane["do_not_duplicate_send"]
            ),
            "out_of_office_count": 1,
            "human_account_action_count": 4,
            "external_send_allowed_without_human": False,
        },
        "lanes": lanes,
        "excluded_message_classes": [
            "Personal finance and payment notices",
            "Account-access and recovery notices",
            "Newsletters, social notifications, and job-alert bulk mail",
        ],
        "source_evidence": {
            "nashville_official_deadline_confirmation": artifact_status(
                NASHVILLE_OFFICIAL_DEADLINE_CONFIRMATION
            ),
            "lvlup_independent_review_confirmation": artifact_status(
                LVLUP_REVIEW_CONFIRMATION
            ),
            "darpa_sn_26_97_public_submission_receipt": artifact_status(
                DARPA_SN_26_97_RECEIPT
            ),
            "missionweave_dsip_action_gate": artifact_status(
                MISSIONWEAVE_ACTION_GATE
            ),
            "openai_build_week_readiness": artifact_status(
                OPENAI_BUILD_WEEK_READINESS
            ),
            "openai_build_week_handoff_integrity_control": artifact_status(
                OPENAI_BUILD_WEEK_HANDOFF_CONTROL
            ),
        },
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
    if any(not isinstance(lane.get("do_not_duplicate_send"), bool) for lane in payload["lanes"]):
        raise ValueError("Every lane must declare a duplicate-send decision")
    terry = next(
        lane for lane in payload["lanes"] if lane["lane_id"] == "terry_vynetic_followup"
    )
    if terry["outbound_followup_count"] != 2:
        raise ValueError("Terry duplicate-send guard is incomplete")
    fhwa = next(
        lane
        for lane in payload["lanes"]
        if lane["lane_id"] == "fhwa_tsmo_qualified_partner_outreach"
    )
    if (
        fhwa["state"]
        != "RESPONSE_LEAD_DECLINED_ADDITIONAL_PARTNER_TEAM_SET"
        or fhwa["delivery_failure_count"] != 1
        or fhwa["replacement_send_count"] != 1
        or fhwa["confirmed_delivery_count"] != 1
        or fhwa["inbound_response_count"] != 2
        or fhwa["qualified_response_lead_referral_count"] != 1
        or fhwa["threaded_acknowledgment_send_count"] != 1
        or fhwa["fit_check_confirmed_count"] != 0
        or fhwa["team_set_decline_count"] != 1
        or fhwa["do_not_duplicate_send"] is not True
    ):
        raise ValueError("FHWA bounce/replacement reconciliation is incomplete")
    georgia = next(
        lane
        for lane in payload["lanes"]
        if lane["lane_id"] == "georgia_patents_pro_bono_intake"
    )
    if (
        georgia["state"] != "SERVICE_NOT_OFFERED_FOR_ALREADY_FILED_APPLICATION"
        or georgia["email_reply_required"] is not False
        or georgia["do_not_duplicate_send"] is not True
    ):
        raise ValueError("Georgia PATENTS scope-decline control is incomplete")
    darpa = next(
        lane
        for lane in payload["lanes"]
        if lane["lane_id"] == "darpa_sn_26_97_low_resource_computing_rfi"
    )
    if (
        darpa["state"] != "FORMAL_RFI_PACKAGE_SENT_AGENCY_RECEIPT_PENDING"
        or darpa["attachment_count"] != 2
        or darpa["deadline_time_compliance_claimed"] is not False
        or darpa["do_not_duplicate_send"] is not True
    ):
        raise ValueError("DARPA formal-package control is incomplete")
    nashville = next(
        lane
        for lane in payload["lanes"]
        if lane["lane_id"] == "nashville_ec_takeoff_fall_2026"
    )
    if (
        nashville["state"]
        != "OFFICIAL_SUPPORT_CONFIRMED_CLOSE_TIME_APPLICATION_NOT_SUBMITTED"
        or nashville["operational_local_deadline"] != "2026-07-17T23:59:00-05:00"
        or nashville["operational_utc_deadline"] != "2026-07-18T04:59:00Z"
        or nashville["deadline_timezone_explicit_in_message"] is not False
        or nashville["do_not_duplicate_send"] is not True
    ):
        raise ValueError("Nashville EC confirmed-deadline control is incomplete")
    lvlup = next(
        lane for lane in payload["lanes"] if lane["lane_id"] == "lvlup_optional_paid_event"
    )
    if (
        lvlup["state"]
        != "WRITTEN_NO_SPONSOR_SPEND_INDEPENDENT_REVIEW_CONFIRMED"
        or lvlup["written_independent_review_confirmation"] is not True
        or lvlup["paid_sponsor_purchase_required_for_separate_review"] is not False
        or lvlup["do_not_duplicate_send"] is not True
    ):
        raise ValueError("LvlUp independent-review control is incomplete")


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
