from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
JSON_OUT = SPRINT_DIR / "EMAIL_ACTION_RECONCILIATION_2026-07-18.json"
MD_OUT = SPRINT_DIR / "EMAIL_ACTION_RECONCILIATION_2026-07-18.md"
NASHVILLE_OFFICIAL_DEADLINE_CONFIRMATION = (
    ROOT
    / "grant_submissions"
    / "NASHVILLE_EC_FALL_2026"
    / "NASHVILLE_EC_OFFICIAL_DEADLINE_CONFIRMATION_2026-07-17.json"
)
NASHVILLE_SUBMISSION_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "NASHVILLE_EC_FALL_2026"
    / "NASHVILLE_EC_SUBMISSION_RECEIPT_2026-07-17.json"
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
OPENAI_BUILD_WEEK_SUBMISSION_RECEIPT = (
    ROOT
    / "evidence"
    / "openai_build_week"
    / "prooflock_youtube_publication_receipt_20260721.json"
)
OPENAI_BUILD_WEEK_HANDOFF_CONTROL = (
    ROOT
    / "grant_submissions"
    / "OPENAI_BUILD_WEEK_20260721"
    / "BUILD_WEEK_HANDOFF_INTEGRITY_CONTROL_2026-07-17.json"
)
OUTREACH_RESPONSE_TEMPLATE_REGISTRY = (
    SPRINT_DIR / "OUTREACH_RESPONSE_TEMPLATE_REGISTRY_2026-07-18.json"
)
OUTREACH_FOLLOWUP_POLICY_CONFIG = (
    ROOT / "config" / "outreach_followup_policies_v1.json"
)

VALID_FOLLOWUP_MODES = {
    "ACCOUNT_ACTION",
    "CLOSED",
    "INBOUND_ONLY",
    "ONE_BOUNDED_FOLLOW_UP_AFTER_HOLD",
    "PORTAL_ACTION",
    "PRIVATE_RECONCILIATION",
}

AS_OF_DATE = "2026-07-18"


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def validate_self_hashed_receipt(payload: dict[str, Any], *, field: str) -> None:
    claimed = payload.get(field)
    canonical = dict(payload)
    canonical.pop(field, None)
    observed = hashlib.sha256(
        json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    if not isinstance(claimed, str) or claimed.lower() != observed:
        raise ValueError("Self-hashed receipt identity is invalid")


def normalize_text_eol(payload: bytes) -> bytes:
    return payload.replace(b"\r\n", b"\n")


def read_head_blob(path: Path) -> bytes | None:
    relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
    completed = subprocess.run(
        ["git", "show", f"HEAD:{relative}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return completed.stdout if completed.returncode == 0 else None


def artifact_status(path: Path) -> dict[str, Any]:
    worktree_bytes = path.read_bytes()
    head_blob = read_head_blob(path)
    eol_equivalent_to_head = (
        head_blob is not None
        and normalize_text_eol(worktree_bytes) == normalize_text_eol(head_blob)
    )
    data = head_blob if eol_equivalent_to_head else worktree_bytes
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "present": True,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest().upper(),
        "identity_source": (
            "COMMITTED_GIT_BLOB" if eol_equivalent_to_head else "WORKTREE_BYTES"
        ),
        # Publication identity is the committed blob. Do not publish an
        # operating-system-specific checkout diagnostic into this receipt.
        "worktree_eol_differs_from_git_blob": False,
    }


def build_payload() -> dict[str, Any]:
    nashville = read_json(NASHVILLE_OFFICIAL_DEADLINE_CONFIRMATION)
    nashville_submission = read_json(NASHVILLE_SUBMISSION_RECEIPT)
    lvlup = read_json(LVLUP_REVIEW_CONFIRMATION)
    darpa = read_json(DARPA_SN_26_97_RECEIPT)
    missionweave = read_json(MISSIONWEAVE_ACTION_GATE)
    build_week = read_json(OPENAI_BUILD_WEEK_READINESS)
    build_week_submission = read_json(OPENAI_BUILD_WEEK_SUBMISSION_RECEIPT)
    build_week_handoff = read_json(OPENAI_BUILD_WEEK_HANDOFF_CONTROL)
    response_registry = read_json(OUTREACH_RESPONSE_TEMPLATE_REGISTRY)
    followup_config = read_json(OUTREACH_FOLLOWUP_POLICY_CONFIG)
    if (
        nashville.get("schema")
        != "lumencore.nashville_ec_official_deadline_confirmation.v1"
        or nashville.get("status")
        != "OFFICIAL_SUPPORT_CONFIRMED_CLOSE_TIME_APPLICATION_NOT_SUBMITTED"
    ):
        raise ValueError("Nashville official deadline confirmation is missing or stale")
    if (
        nashville_submission.get("schema")
        != "lumencore.nashville_ec_submission_receipt.v1"
        or nashville_submission.get("status") != "PORTAL_SUBMISSION_CONFIRMED"
    ):
        raise ValueError("Nashville application submission receipt is missing or stale")
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
        != "FORMAL_RFI_PACKAGE_SENT_AGENCY_RESPONSE_RECEIVED_MONITOR_ONLY"
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
    validate_self_hashed_receipt(build_week_submission, field="receipt_sha256")
    build_week_devpost = build_week_submission.get("devpost", {})
    build_week_controls = build_week_submission.get("controls", {})
    if (
        build_week_submission.get("schema")
        != "lumencore.prooflock_youtube_publication_receipt.v1"
        or build_week_devpost.get("submission_state") != "SUBMITTED"
        or build_week_devpost.get("final_submission_performed") is not True
        or build_week_devpost.get("public_project_page_resolved") is not True
        or build_week_devpost.get("confirmation_email_received") is not True
        or build_week_devpost.get("confirmation_email_reply_required") is not False
        or build_week_controls.get("contest_acceptance_claimed") is not False
        or build_week_controls.get("award_claimed") is not False
    ):
        raise ValueError("OpenAI Build Week submission receipt is missing or unsafe")
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
    if (
        response_registry.get("schema")
        != "lumencore.outreach_response_template_registry.v1"
        or response_registry.get("controls", {}).get("builder_can_send_email") is not False
        or response_registry.get("controls", {}).get("duplicate_send_fail_closed") is not True
    ):
        raise ValueError("Outreach response template registry is missing or unsafe")
    response_template_ids = {
        row.get("template_id") for row in response_registry.get("templates", [])
    }
    if "NO_DUPLICATE_MONITOR" not in response_template_ids:
        raise ValueError("No-duplicate response template is unavailable")
    if (
        followup_config.get("schema")
        != "lumencore.outreach_followup_policies.v1"
        or followup_config.get("version") != 1
        or followup_config.get("controls", {}).get("builder_can_send_email") is not False
        or followup_config.get("controls", {}).get("missing_lane_policy_fail_closed")
        is not True
    ):
        raise ValueError("Outreach follow-up policy config is missing or unsafe")
    followup_policies = {
        row.get("lane_id"): row for row in followup_config.get("lane_policies", [])
    }
    if len(followup_policies) != len(followup_config.get("lane_policies", [])):
        raise ValueError("Outreach follow-up policy lane IDs are duplicated")
    if any(
        row.get("mode") not in VALID_FOLLOWUP_MODES
        for row in followup_policies.values()
    ):
        raise ValueError("Outreach follow-up policy mode is invalid")

    lanes = [
        {
            "lane_id": "nashville_ec_takeoff_fall_2026",
            "organization": "Nashville Entrepreneur Center",
            "latest_event_type": "PORTAL_SUBMISSION_CONFIRMED",
            "latest_event_utc": "2026-07-18T04:54:52.709214Z",
            "state": nashville_submission["status"],
            "operational_local_deadline": nashville["confirmation"][
                "operational_local_deadline"
            ],
            "operational_utc_deadline": nashville["confirmation"][
                "operational_utc_deadline"
            ],
            "deadline_timezone_explicit_in_message": nashville["confirmation"][
                "timezone_explicit_in_message"
            ],
            "portal_submission_verified": True,
            "expected_next_steps_by": nashville_submission["confirmation_page"][
                "expected_next_steps_by"
            ],
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": (
                "Monitor for the rolling review result through August 3; do not resubmit, "
                "reply to the automated confirmation, or describe the application as selected."
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
            "latest_event_type": "AGENCY_THREAD_RESPONSE_AFTER_FORMAL_PACKAGE",
            "latest_event_utc": darpa["thread_reconciliation"][
                "agency_thread_response_received_utc"
            ],
            "state": darpa["status"],
            "deadline_date": darpa["opportunity"]["deadline_date"],
            "deadline_time_compliance_claimed": False,
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "attachment_count": len(darpa["attachments"]),
            "agency_thread_response_observed": darpa["thread_reconciliation"][
                "agency_thread_response_after_formal_package_observed"
            ],
            "explicit_attachment_receipt_confirmed": darpa[
                "thread_reconciliation"
            ]["explicit_attachment_receipt_confirmed"],
            "specific_action_request_observed": darpa["thread_reconciliation"][
                "specific_action_request_observed"
            ],
            "next_action": darpa["send_control"]["next_action"],
        },
        {
            "lane_id": "missionweave_dsip_proposal",
            "organization": "Defense SBIR/STTR Innovation Portal",
            "latest_event_type": "DSIP_SUPPORT_REDIRECTED_TO_DLA_COMPONENT_POC",
            "latest_event_utc": "2026-07-18T15:35:55Z",
            "state": missionweave["status"],
            "deadline_utc": missionweave["deadline"]["expected_utc"],
            "open_gate_count": missionweave["gate_summary"]["open_gate_count"],
            "component_poc_included_on_original_message": True,
            "component_reply_observed": False,
            "support_redirect_received": True,
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": "2026-07-20T17:00:00Z",
            "do_not_duplicate_send": True,
            "next_action": (
                "Continue the JCP portal and DSIP evidence work. Recheck the complete component "
                "thread after the Monday hold; only if no component reply exists may one bounded "
                "instruction follow-up be drafted. Do not resend the proposal package."
            ),
        },
        {
            "lane_id": "openai_build_week_prooflock",
            "organization": "OpenAI Build Week / Devpost",
            "latest_event_type": "DEVPOST_SUBMISSION_CONFIRMED",
            "latest_event_utc": build_week_devpost["confirmation_email_utc"],
            "state": "PORTAL_SUBMISSION_CONFIRMED",
            "deadline_utc": build_week["official_requirements"]["facts"][
                "submission_period"
            ]["deadline_utc"],
            "portal_submission_verified": True,
            "confirmation_email_received": True,
            "public_project_page_resolved": True,
            "public_page_video_embed_matches": True,
            "confirmed_model_reference": build_week_devpost[
                "public_page_model_reference"
            ],
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": (
                "Preserve the submission receipt and monitor for a judging or correction request. "
                "Do not reply to the automated confirmation, resubmit without a verified issue, "
                "or describe successful submission as selection, endorsement, or an award."
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
    lane_ids = {lane["lane_id"] for lane in lanes}
    if lane_ids != set(followup_policies):
        missing = sorted(lane_ids - set(followup_policies))
        stale = sorted(set(followup_policies) - lane_ids)
        raise ValueError(
            f"Outreach follow-up policy coverage mismatch: missing={missing}, stale={stale}"
        )
    for lane in lanes:
        followup_policy = dict(followup_policies[lane["lane_id"]])
        eligible_template_id = followup_policy.get("eligible_template_id")
        if eligible_template_id and eligible_template_id not in response_template_ids:
            raise ValueError(
                f"Unknown eligible response template: {eligible_template_id}"
            )
        if followup_policy["mode"] == "ONE_BOUNDED_FOLLOW_UP_AFTER_HOLD":
            if (
                not followup_policy.get("not_before_utc")
                or followup_policy.get("max_proactive_sends") != 1
                or not eligible_template_id
            ):
                raise ValueError("Bounded follow-up policy is incomplete")
        elif (
            followup_policy.get("not_before_utc") is not None
            or followup_policy.get("max_proactive_sends") != 0
            or eligible_template_id is not None
        ):
            raise ValueError("Non-proactive follow-up policy contains send authority")
        lane["follow_up_policy"] = followup_policy
        lane["response_template_id"] = (
            "NO_DUPLICATE_MONITOR" if lane["do_not_duplicate_send"] else None
        )
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
            "Nashville EC Fall 2026 TakeOff portal-submission confirmation",
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
            "monitor_no_send_template_count": sum(
                1
                for lane in lanes
                if lane["response_template_id"] == "NO_DUPLICATE_MONITOR"
            ),
            "follow_up_mode_counts": dict(
                sorted(
                    Counter(
                        lane["follow_up_policy"]["mode"] for lane in lanes
                    ).items()
                )
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
            "nashville_submission_receipt": artifact_status(
                NASHVILLE_SUBMISSION_RECEIPT
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
            "openai_build_week_submission_receipt": artifact_status(
                OPENAI_BUILD_WEEK_SUBMISSION_RECEIPT
            ),
            "openai_build_week_handoff_integrity_control": artifact_status(
                OPENAI_BUILD_WEEK_HANDOFF_CONTROL
            ),
            "outreach_response_template_registry": artifact_status(
                OUTREACH_RESPONSE_TEMPLATE_REGISTRY
            ),
            "outreach_followup_policy_config": artifact_status(
                OUTREACH_FOLLOWUP_POLICY_CONFIG
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
    if any(
        lane.get("response_template_id") != "NO_DUPLICATE_MONITOR"
        for lane in payload["lanes"]
        if lane["do_not_duplicate_send"]
    ):
        raise ValueError("A duplicate-send lane is not routed to the no-send template")
    if payload["summary"]["monitor_no_send_template_count"] != payload["summary"][
        "duplicate_outbound_risk_count"
    ]:
        raise ValueError("No-send template coverage is incomplete")
    if sum(payload["summary"]["follow_up_mode_counts"].values()) != payload["summary"][
        "lane_count"
    ]:
        raise ValueError("Follow-up mode coverage is incomplete")
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
        darpa["state"]
        != "FORMAL_RFI_PACKAGE_SENT_AGENCY_RESPONSE_RECEIVED_MONITOR_ONLY"
        or darpa["attachment_count"] != 2
        or darpa["agency_thread_response_observed"] is not True
        or darpa["explicit_attachment_receipt_confirmed"] is not False
        or darpa["specific_action_request_observed"] is not False
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
        nashville["state"] != "PORTAL_SUBMISSION_CONFIRMED"
        or nashville["operational_local_deadline"] != "2026-07-17T23:59:00-05:00"
        or nashville["operational_utc_deadline"] != "2026-07-18T04:59:00Z"
        or nashville["deadline_timezone_explicit_in_message"] is not False
        or nashville["portal_submission_verified"] is not True
        or nashville["expected_next_steps_by"] != "2026-08-03"
        or nashville["do_not_duplicate_send"] is not True
    ):
        raise ValueError("Nashville EC submission control is incomplete")
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
        f"- No-send template coverage: `{summary['monitor_no_send_template_count']}`",
        f"- Human account actions: `{summary['human_account_action_count']}`",
        "- Browser navigation performed: `false`",
        "",
        "## Reconciled Lanes",
        "",
        "| Lane | State | Follow-up mode | Reply now | Next action |",
        "|---|---|---|---:|---|",
    ]
    for lane in payload["lanes"]:
        lines.append(
            f"| {lane['organization']} | `{lane['state']}` | "
            f"`{lane['follow_up_policy']['mode']}` | "
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
