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

SUBMISSION_RECEIPT = SPRINT_DIR / "EXTERNAL_SUBMISSION_RECEIPT_2026-07-13.json"
CDC_RECEIPT = SPRINT_DIR / "CDC_AI_ACQUISITION_RFI_ENGAGEMENT_RECEIPT_2026-07-16.json"
LANL_RECEIPT = SPRINT_DIR / "LANL_VISION_FOLLOWUP_ENGAGEMENT_RECEIPT_2026-07-16.json"
EPRI_TEMPLATE = SPRINT_DIR / "EPRI_OPEN_POWER_AI_MOU_RESPONSE_TEMPLATE_2026-07-16.md"
EPRI_RECEIPT = SPRINT_DIR / "EPRI_OPEN_POWER_AI_MOU_ENGAGEMENT_RECEIPT_2026-07-16.json"
EPRI_SIGNING_STATE = (
    SPRINT_DIR / "EPRI_OPEN_POWER_AI_MOU_SIGNING_STATE_2026-07-23.json"
)
OFFICIAL_INBOUND_STATUS_EVENT_REGISTER = (
    SPRINT_DIR / "OFFICIAL_INBOUND_STATUS_EVENT_REGISTER_2026-07-25.json"
)
GEORGIA_PATENTS_TEMPLATE = (
    SPRINT_DIR / "GEORGIA_PATENTS_PRO_BONO_INTAKE_RESPONSE_2026-07-16.md"
)
GEORGIA_PATENTS_RECEIPT = (
    SPRINT_DIR / "GEORGIA_PATENTS_PRO_BONO_INTAKE_ENGAGEMENT_RECEIPT_2026-07-16.json"
)
PATENT_DEADLINE_CONTROL = (
    SPRINT_DIR / "PATENT_DEADLINE_EVIDENCE_CONTROL_2026-07-16.json"
)
PATENT_PRIVATE_CAPTURE_WORKFLOW = (
    SPRINT_DIR / "PATENT_CENTER_PRIVATE_DOCKET_CAPTURE_WORKFLOW_2026-07-17.md"
)
PATENT_PRACTITIONER_TEMPLATE = (
    SPRINT_DIR / "PATENT_PRACTITIONER_DOCKET_REVIEW_REQUEST_TEMPLATE_2026-07-17.md"
)
NASHVILLE_MANIFEST = (
    ROOT
    / "grant_submissions"
    / "NASHVILLE_EC_FALL_2026"
    / "NASHVILLE_EC_FALL_2026_APPLICATION_MANIFEST_2026-07-16.json"
)
NASHVILLE_FACT_RESOLUTION = (
    ROOT
    / "grant_submissions"
    / "NASHVILLE_EC_FALL_2026"
    / "NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.json"
)
NASHVILLE_PRIVATE_COLLECTOR = (
    ROOT / "code" / "ops" / "CAPTURE_NASHVILLE_EC_PRIVATE_FACTS.py"
)
NASHVILLE_PRIVATE_WORKFLOW = (
    ROOT
    / "grant_submissions"
    / "NASHVILLE_EC_FALL_2026"
    / "NASHVILLE_EC_PRIVATE_FACT_CAPTURE_WORKFLOW_2026-07-17.md"
)
NASHVILLE_PRIVATE_FILL_MAP = (
    ROOT
    / "grant_submissions"
    / "NASHVILLE_EC_FALL_2026"
    / "private"
    / "nashville_ec_portal_fill_map.private.json"
)
NASHVILLE_DEADLINE_RECEIPT = (
    SPRINT_DIR
    / "NASHVILLE_EC_DEADLINE_PRESERVATION_ENGAGEMENT_RECEIPT_2026-07-17.json"
)
NASHVILLE_DEADLINE_RESPONSE_CONTROL = (
    SPRINT_DIR / "NASHVILLE_EC_DEADLINE_PRESERVATION_RESPONSE_CONTROL_2026-07-17.md"
)
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
LAUNCHTN_MANIFEST = (
    ROOT
    / "grant_submissions"
    / "LAUNCHTN_3686_PITCH_2026"
    / "LAUNCHTN_3686_APPLICATION_MANIFEST_2026-07-29.json"
)
LAUNCHTN_DECK = (
    ROOT
    / "grant_submissions"
    / "LAUNCHTN_3686_PITCH_2026"
    / "LUMENCORE_3686_PITCH_DECK_2026-07-29_REVIEW_REQUIRED.pptx"
)
LAUNCHTN_FINANCIAL_MODEL = (
    ROOT
    / "grant_submissions"
    / "LAUNCHTN_3686_PITCH_2026"
    / "LUMENCORE_3686_FINANCIAL_MODEL_2026-07-17.xlsx"
)
LVLUP_DRAFT = ROOT / "docs" / "LVLUP_VENTURES_APPLICATION_DRAFT_2026-07-03.md"
LVLUP_REVIEW_CONFIRMATION = (
    SPRINT_DIR / "LVLUP_INDEPENDENT_REVIEW_CONFIRMATION_2026-07-17.json"
)
SAM_ROTATION_CONTROL = (
    SPRINT_DIR / "SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL_2026-07-16.json"
)
EMAIL_ACTION_RECONCILIATION = (
    SPRINT_DIR / "EMAIL_ACTION_RECONCILIATION_2026-07-18.json"
)
OUTREACH_FOLLOWUP_ACTION_QUEUE = (
    SPRINT_DIR / "OUTREACH_FOLLOWUP_ACTION_QUEUE_2026-07-18.json"
)
ARGOS_PARTNER_OUTREACH_STATUS = (
    SPRINT_DIR / "ARGOS_PARTNER_OUTREACH_STATUS_2026-07-28.json"
)
OUTREACH_DRAFT_QUARANTINE_STATE = (
    SPRINT_DIR / "OUTREACH_DRAFT_QUARANTINE_STATE_2026-07-23.json"
)
STAN_MEETING_INVITE_STATE = (
    SPRINT_DIR / "STAN_HERRING_MEETING_INVITE_STATE_2026-07-27.json"
)
DARPA_SN_26_97_RECEIPT = (
    SPRINT_DIR / "DARPA_SN_26_97_PUBLIC_SUBMISSION_RECEIPT_2026-07-17.json"
)
FHWA_TEAMING_TEMPLATE = (
    SPRINT_DIR / "FHWA_TSMO_QUALIFIED_TEAMING_REQUEST_2026-07-16.md"
)
FHWA_PARTNER_OUTREACH = (
    SPRINT_DIR / "FHWA_TSMO_PARTNER_OUTREACH_CONTROL_2026-07-17.json"
)
FHWA_PARTNER_RESPONSE_CONTROL = (
    SPRINT_DIR / "FHWA_TSMO_PARTNER_RESPONSE_CONTROL_2026-07-17.md"
)

OUT_JSON = OUT_OPS / "external_engagement_response_register_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "external_engagement_response_register.json"
CANONICAL_JSON = SPRINT_DIR / "EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-18.json"
OUT_MD = SPRINT_DIR / "EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-18.md"

PRIVATE_MARKERS = (
    "full legal name:",
    "signatory email:",
    "signatory telephone:",
    "meeting id",
    "passcode",
    "zoom.us",
    "client_secret",
    "refresh_token",
    "api_key",
    "private key",
)

REGISTER_BOUNDARY = (
    "This register records bounded communication and portal-preparation states. It does not prove "
    "evaluation, selection, endorsement, independent validation, a pilot, funding, an award, a "
    "contract, deployment, realized savings, or technical performance."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def artifact_status(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "present": path.is_file(),
        "bytes": path.stat().st_size if path.is_file() else 0,
        "sha256": sha256_file(path) if path.is_file() else None,
    }


def submission_by_notice(receipt: dict[str, Any], notice_id: str) -> dict[str, Any]:
    for row in receipt.get("submissions", []):
        if isinstance(row, dict) and row.get("notice_id") == notice_id:
            return row
    raise ValueError(f"Missing verified submission receipt for {notice_id}")


def verify_attachment(receipt_row: dict[str, Any]) -> dict[str, Any]:
    attachment = receipt_row.get("attachment")
    if isinstance(attachment, dict):
        path_value = attachment.get("path")
        expected_hash = attachment.get("sha256")
        expected_bytes = attachment.get("bytes")
    else:
        path_value = attachment
        expected_hash = receipt_row.get("attachment_sha256")
        expected_bytes = receipt_row.get("attachment_bytes")

    path = ROOT / str(path_value)
    actual_hash = sha256_file(path)
    actual_bytes = path.stat().st_size
    return {
        "path": rel(path),
        "present": True,
        "expected_sha256": str(expected_hash).upper(),
        "actual_sha256": actual_hash,
        "sha256_match": actual_hash == str(expected_hash).upper(),
        "expected_bytes": int(expected_bytes),
        "actual_bytes": actual_bytes,
        "bytes_match": actual_bytes == int(expected_bytes),
    }


def verify_qa_attachment(attachment: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / str(attachment["path"])
    expected_hash = str(attachment["expected_sha256"]).upper()
    expected_bytes = int(attachment["bytes"])
    actual_hash = sha256_file(path)
    actual_bytes = path.stat().st_size
    return {
        "path": rel(path),
        "present": True,
        "expected_sha256": expected_hash,
        "actual_sha256": actual_hash,
        "sha256_match": actual_hash == expected_hash,
        "expected_bytes": expected_bytes,
        "actual_bytes": actual_bytes,
        "bytes_match": actual_bytes == expected_bytes,
        "qa_status": attachment["status"],
        "founder_approval_required": attachment["founder_approval_required"],
    }


def lane_hash(row: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_payload(generated_utc: str | None = None) -> dict[str, Any]:
    submissions = read_json(SUBMISSION_RECEIPT)
    cdc = read_json(CDC_RECEIPT)
    lanl = read_json(LANL_RECEIPT)
    epri = read_json(EPRI_RECEIPT)
    epri_signing = read_json(EPRI_SIGNING_STATE)
    official_events = read_json(OFFICIAL_INBOUND_STATUS_EVENT_REGISTER)
    georgia_patents = read_json(GEORGIA_PATENTS_RECEIPT)
    patent_control = read_json(PATENT_DEADLINE_CONTROL)
    nashville = read_json(NASHVILLE_MANIFEST)
    nashville_resolution = read_json(NASHVILLE_FACT_RESOLUTION)
    nashville_deadline = read_json(NASHVILLE_DEADLINE_RECEIPT)
    nashville_official_deadline = read_json(NASHVILLE_OFFICIAL_DEADLINE_CONFIRMATION)
    nashville_submission = read_json(NASHVILLE_SUBMISSION_RECEIPT)
    launchtn = read_json(LAUNCHTN_MANIFEST)
    lvlup_review = read_json(LVLUP_REVIEW_CONFIRMATION)
    sam_rotation = read_json(SAM_ROTATION_CONTROL)
    email_reconciliation = read_json(EMAIL_ACTION_RECONCILIATION)
    followup_queue = read_json(OUTREACH_FOLLOWUP_ACTION_QUEUE)
    stan_meeting = read_json(STAN_MEETING_INVITE_STATE)
    darpa_sn_26_97 = read_json(DARPA_SN_26_97_RECEIPT)
    fhwa_outreach = read_json(FHWA_PARTNER_OUTREACH)

    if nashville_resolution.get("status") != "SIX_FOUNDER_CONFIRMATIONS_REQUIRED":
        raise ValueError("Nashville EC human-fact resolution is missing or stale")
    if (
        nashville_deadline.get("schema") != "lumencore.external_engagement_receipt.v1"
        or nashville_deadline.get("acknowledgment", {}).get("status")
        != "DEADLINE_PRESERVATION_QUERY_SENT_RESPONSE_PENDING"
    ):
        raise ValueError("Nashville EC deadline-preservation receipt is missing or stale")
    if (
        nashville_official_deadline.get("schema")
        != "lumencore.nashville_ec_official_deadline_confirmation.v1"
        or nashville_official_deadline.get("status")
        != "OFFICIAL_SUPPORT_CONFIRMED_CLOSE_TIME_APPLICATION_NOT_SUBMITTED"
    ):
        raise ValueError("Nashville EC official deadline confirmation is missing or stale")
    if (
        nashville_submission.get("schema")
        != "lumencore.nashville_ec_submission_receipt.v1"
        or nashville_submission.get("status") != "PORTAL_SUBMISSION_CONFIRMED"
    ):
        raise ValueError("Nashville EC submission receipt is missing or stale")
    if (
        lvlup_review.get("schema")
        != "lumencore.lvlup_independent_review_confirmation.v1"
        or lvlup_review.get("status")
        != "WRITTEN_NO_SPONSOR_SPEND_INDEPENDENT_REVIEW_CONFIRMED"
    ):
        raise ValueError("LvlUp independent-review confirmation is missing or stale")
    if (
        epri_signing.get("schema")
        != "lumencore.epri_open_power_ai_mou_signing_state.v1"
        or epri_signing.get("status")
        != "USER_SIGNATURE_REPORTED_COMPLETION_CONFIRMATION_PENDING"
        or epri_signing.get("evidence", {}).get("user_reported_signing_complete")
        is not True
        or epri_signing.get("controls", {}).get("do_not_duplicate_signature")
        is not True
    ):
        raise ValueError("EPRI MOU signing state is missing or stale")
    official_events_by_lane = {
        row.get("lane_id"): row for row in official_events.get("events", [])
    }
    epri_onboarding = official_events_by_lane.get("epri_open_power_ai_mou", {})
    epri_source = epri_onboarding.get("source", {})
    epri_action = epri_onboarding.get("action", {})
    nashville_onboarding = official_events_by_lane.get(
        "nashville_ec_takeoff_fall_2026", {}
    )
    nashville_action = nashville_onboarding.get("action", {})
    nashville_info = official_events_by_lane.get(
        "nashville_ec_accelerator_info_sessions", {}
    )
    nashville_info_action = nashville_info.get("action", {})
    dsip_status = official_events_by_lane.get("dla_dsip_topic_status", {})
    dsip_action = dsip_status.get("action", {})
    argos_auto_reply = official_events_by_lane.get(
        "argos_government_automatic_reply", {}
    )
    argos_auto_reply_action = argos_auto_reply.get("action", {})
    event_count = official_events.get("event_count")
    if (
        official_events.get("schema")
        != "lumencore.official_inbound_status_event_register.v1"
        or official_events.get("status")
        != "TWELVE_OFFICIAL_EVENTS_RECONCILED_NO_SEND"
        or event_count != 12
        or len(official_events.get("events", [])) != event_count
        or len(official_events_by_lane) != event_count
        or official_events.get("controls", {}).get("builder_can_send_email")
        is not False
        or epri_onboarding.get("status")
        != "ONBOARDING_RESPONSE_SENT_MRC_INVITE_RECEIVED_LOGO_FILES_PENDING"
        or epri_source.get("subject_sha256")
        != hashlib.sha256(
            str(epri_source.get("subject") or "").encode("utf-8")
        ).hexdigest().upper()
        or epri_action.get("selected_template_id")
        != "REQUESTED_ASSET_DELIVERY_REPLY"
        or epri_action.get("send_now") is not False
        or nashville_onboarding.get("status")
        != "COHORT_SELECTED_ONBOARDING_AND_PARTICIPATION_AGREEMENT_DUE"
        or nashville_action.get("deadline")
        != {
            "onboarding_form_and_participation_agreement_date": "2026-07-31",
            "deposit_date": "2026-08-14",
            "time_and_timezone_explicit": False,
        }
        or nashville_action.get("email_reply_required") is not False
            or nashville_action.get("send_now") is not False
            or nashville_info.get("status")
            != "UPDATED_PAYMENT_ROUTE_AND_OPTIONAL_INFO_SESSIONS_AVAILABLE"
            or nashville_info.get("evidence", {}).get(
                "prior_payment_link_invalidated"
            )
            is not True
            or nashville_info.get("evidence", {}).get(
                "updated_takeoff_payment_route_provided"
            )
            is not True
            or nashville_info.get("evidence", {}).get("payment_link_omitted")
            is not True
            or nashville_info.get("evidence", {}).get("session_count") != 3
        or nashville_info.get("evidence", {}).get(
            "session_timezone_explicit"
        )
        is not False
        or nashville_info.get("evidence", {}).get("attendance_required")
        is not False
        or nashville_info_action.get("deadline")
        != {
            "onboarding_form_date": "2026-07-31",
            "time_and_timezone_explicit": False,
        }
        or nashville_info_action.get("email_reply_required") is not False
        or nashville_info_action.get("send_now") is not False
        or dsip_status.get("status")
        != "OFFICIAL_DLA_CONFIRMED_PROPOSAL_IN_PROGRESS_NOT_SUBMITTED"
        or dsip_status.get("evidence", {}).get(
            "official_portal_status_observed"
        )
        is not True
        or dsip_status.get("evidence", {}).get("portal_status")
        != "IN_PROGRESS"
        or dsip_status.get("evidence", {}).get("formally_submitted") is not False
        or dsip_status.get("evidence", {}).get(
            "submission_receipt_observed"
        )
        is not False
        or dsip_status.get("evidence", {}).get(
            "founder_portal_recheck_required"
        )
        is not False
        or dsip_action.get("selected_template_id") != "NO_DUPLICATE_MONITOR"
        or dsip_action.get("duplicate_send_decision")
        != "CLOSE_NOT_SUBMITTED_DO_NOT_RESEND"
        or dsip_action.get("email_reply_required") is not False
        or dsip_action.get("send_now") is not False
        or argos_auto_reply.get("status")
        != "AUTOMATIC_OUT_OF_OFFICE_REPLY_OBSERVED_DELIVERY_ONLY_NO_DUPLICATE"
        or argos_auto_reply.get("evidence", {}).get("delivery_evidence_only")
        is not True
        or argos_auto_reply.get("evidence", {}).get(
            "substantive_acknowledgment"
        )
        is not False
        or argos_auto_reply.get("evidence", {}).get("acceptance_or_award")
        is not False
        or argos_auto_reply_action.get("selected_template_id")
        != "NO_DUPLICATE_MONITOR"
        or argos_auto_reply_action.get("duplicate_send_decision")
        != "DO_NOT_REPLY_TO_THE_AUTOMATIC_MESSAGE_OR_RESEND_THE_ARGOS_PACKET"
        or argos_auto_reply_action.get("email_reply_required") is not False
        or argos_auto_reply_action.get("send_now") is not False
    ):
        raise ValueError("Official inbound event register is missing or stale")
    if patent_control.get("schema") != "lumencore.patent_deadline_evidence_control.v1":
        raise ValueError("Patent deadline evidence control is missing or stale")
    if launchtn.get("schema") != "lumencore.launchtn_3686_pitch_application.v2":
        raise ValueError("LaunchTN 3686 application manifest is missing or stale")
    if sam_rotation.get("schema") != "lumencore.sam_public_credential_rotation_control.v1":
        raise ValueError("SAM public credential rotation control is missing or stale")
    if email_reconciliation.get("schema") != "lumencore.email_action_reconciliation.v1":
        raise ValueError("Email action reconciliation is missing or stale")
    if (
        followup_queue.get("schema")
        != "lumencore.outreach_followup_action_queue.v1"
        or followup_queue.get("controls", {}).get("builder_can_send_email") is not False
        or followup_queue.get("controls", {}).get("final_send_performed") is not False
    ):
        raise ValueError("Outreach follow-up action queue is missing or unsafe")
    stan_source = stan_meeting.get("source", {})
    stan_action = stan_meeting.get("action", {})
    stan_controls = stan_meeting.get("controls", {})
    if (
        stan_meeting.get("schema")
        != "lumencore.external_reviewer_meeting_invite_state.v1"
        or stan_meeting.get("status")
        != "MEETING_CONFIRMED_INVITE_ACCEPTED_PREP_REQUIRED"
        or stan_meeting.get("lane_id")
        != "stan_herring_product_validation_meeting"
        or stan_source.get("subject_sha256")
        != hashlib.sha256(
            str(stan_source.get("subject") or "").encode("utf-8")
        ).hexdigest().upper()
        or stan_meeting.get("meeting", {}).get("calendar_invite_created")
        is not True
        or stan_meeting.get("meeting", {}).get("guest_response_status")
        != "accepted"
        or stan_meeting.get("meeting", {}).get("meeting_credentials_omitted")
        is not True
        or stan_action.get("email_reply_required") is not False
        or stan_action.get("send_now") is not False
        or stan_action.get("create_another_invite") is not False
        or stan_controls.get("builder_can_send_email") is not False
        or stan_controls.get("builder_can_create_calendar_event") is not False
        or stan_controls.get("duplicate_invite_prohibited") is not True
    ):
        raise ValueError("External reviewer meeting invite state is missing or unsafe")
    if (
        darpa_sn_26_97.get("schema")
        != "lumencore.darpa_sn_26_97_public_submission_receipt.v1"
        or darpa_sn_26_97.get("status")
        != "FORMAL_RFI_PACKAGE_SENT_AGENCY_RECEIPT_PENDING"
    ):
        raise ValueError("DARPA-SN-26-97 public submission receipt is missing or stale")
    if (
        fhwa_outreach.get("schema")
        != "lumencore.fhwa_tsmo_partner_outreach_control.v3"
        or fhwa_outreach.get("status")
        != "RESPONSE_LEAD_DECLINED_ADDITIONAL_PARTNER_TEAM_SET"
    ):
        raise ValueError("FHWA partner outreach control is missing or stale")
    reconciliation_status = email_reconciliation.get("status")
    reconciliation_summary = email_reconciliation.get("summary", {})
    allowed_reconciliation_statuses = {
        "NO_UNANSWERED_DEADLINE_CRITICAL_EMAIL_ACTION",
        "DEADLINE_ACTION_DUE_HUMAN_REVIEW",
    }
    deadline_action_count = int(
        reconciliation_summary.get("deadline_action_required_count", 0)
    )
    if (
        reconciliation_status not in allowed_reconciliation_statuses
        or reconciliation_summary.get("send_now_count") != 0
        or (
            reconciliation_status == "DEADLINE_ACTION_DUE_HUMAN_REVIEW"
            and deadline_action_count < 1
        )
        or (
            reconciliation_status
            == "NO_UNANSWERED_DEADLINE_CRITICAL_EMAIL_ACTION"
            and deadline_action_count != 0
        )
    ):
        raise ValueError("Email action reconciliation requires a fresh action review")
    reconciliation_lanes = {
        row["lane_id"]: row for row in email_reconciliation.get("lanes", [])
    }
    if {
        "nashville_ec_takeoff_fall_2026",
        "epri_open_power_ai_mou",
        "georgia_patents_pro_bono_intake",
        "darpa_sn_26_97_low_resource_computing_rfi",
        "terry_vynetic_followup",
        "fhwa_tsmo_qualified_partner_outreach",
        "argos_emi_teaming_inquiry",
    } - reconciliation_lanes.keys():
        raise ValueError("Email action reconciliation is missing required lane controls")
    followup_actions = {
        row["lane_id"]: row for row in followup_queue.get("actions", [])
    }
    required_followup_actions = {
        "lanl_vision_licensing_followup",
        "nashville_ec_takeoff_fall_2026",
        "terry_vynetic_followup",
        "argos_emi_teaming_inquiry",
    }
    if required_followup_actions - followup_actions.keys():
        raise ValueError("Outreach follow-up queue is missing required lanes")
    quarantined_followup_actions = [
        row
        for row in followup_actions.values()
        if row.get("conflicting_gmail_draft_count", 0) > 0
    ]
    if (
        followup_queue.get("summary", {}).get(
            "conflicting_gmail_draft_count"
        )
        != sum(
            row["conflicting_gmail_draft_count"]
            for row in quarantined_followup_actions
        )
        or followup_queue.get("summary", {}).get(
            "conflicting_gmail_draft_lane_count"
        )
        != len(quarantined_followup_actions)
        or any(
            row.get("draft_quarantine_status")
            != "QUARANTINED_NOT_SENDABLE"
            or row.get("send_now") is not False
            for row in quarantined_followup_actions
        )
    ):
        raise ValueError("Outreach follow-up queue draft quarantine is incomplete")
    lanl_followup = followup_actions["lanl_vision_licensing_followup"]
    nashville_followup = followup_actions[
        "nashville_ec_takeoff_fall_2026"
    ]
    terry_followup = followup_actions["terry_vynetic_followup"]
    argos_followup = followup_actions["argos_emi_teaming_inquiry"]
    if (
        lanl_followup.get("send_now") is not False
        or lanl_followup.get("action_time_human_review_required") is not True
        or lanl_followup.get("action_state")
        not in {
            "HELD_NO_SEND",
            "RECHECK_MAILBOX_BEFORE_DRAFT",
            "FOLLOWUP_LIMIT_REACHED_NO_SEND",
        }
    ):
        raise ValueError("LANL follow-up queue state is not fail-closed")
        if (
            argos_followup.get("send_now") is not False
            or argos_followup.get("action_time_human_review_required") is not True
            or argos_followup.get("inbox_recheck_required") is not False
            or argos_followup.get("action_state")
            != "INITIAL_OUTREACH_LIMIT_REACHED_NO_SEND"
            or argos_followup.get("eligible_template_id")
            != "INITIAL_PARTNER_TEAMING_INQUIRY"
            or argos_followup.get("recorded_proactive_send_count") != 1
        ):
            raise ValueError("Argos post-send outreach state is not fail-closed")
    fhwa_delivery = fhwa_outreach["delivery_reconciliation"]
    fhwa_active_outbound = next(
        row
        for row in fhwa_outreach["outbound_history"]
        if row["attempt_index"] == fhwa_delivery["active_attempt_index"]
    )
    if (
        fhwa_delivery["delivery_failure_count"] != 1
        or fhwa_delivery["replacement_send_count"] != 1
        or fhwa_delivery["threaded_acknowledgment_send_count"] != 1
        or fhwa_delivery["confirmed_delivery_count"] != 1
        or fhwa_delivery["response_count"] != 2
        or fhwa_delivery["qualified_response_lead_referral_count"] != 1
        or fhwa_delivery["fit_check_confirmed_count"] != 0
        or fhwa_delivery["team_set_decline_count"] != 1
        or fhwa_active_outbound["status"]
        != "THREADED_REFERRAL_ACKNOWLEDGMENT_SENT_FIT_CHECK_PENDING"
    ):
        raise ValueError("FHWA delivery reconciliation is incomplete")

    nasa = submission_by_notice(submissions, "80TECH26RFI0020")
    army = submission_by_notice(submissions, "ACCAPGAIDPRFI4")

    records: list[dict[str, Any]] = [
        {
            "lane_id": stan_meeting["lane_id"],
            "organization": "External technical adviser prospect",
            "state": stan_meeting["status"],
            "deadline": stan_meeting["meeting"]["start"],
            "decision": "HUMAN_MEETING_PREP",
            "response_channel": "CALENDAR",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": True,
            "action_gate": stan_action["safest_next_action"],
            "response_artifact": rel(STAN_MEETING_INVITE_STATE),
            "calendar_invite_created": True,
            "guest_response_status": stan_meeting["meeting"][
                "guest_response_status"
            ],
            "meeting_credentials_omitted": True,
            "next_action": stan_action["safest_next_action"],
            "claim_boundary": stan_meeting["claim_boundary"],
        },
        {
            "lane_id": "argos_emi_teaming_inquiry",
            "organization": argos_followup["organization"],
            "state": reconciliation_lanes["argos_emi_teaming_inquiry"]["state"],
            "deadline": argos_followup["deadline_utc"],
            "decision": (
                "MONITOR_EXISTING_THREAD_NO_RESEND"
                if argos_followup["action_state"]
                == "INITIAL_OUTREACH_LIMIT_REACHED_NO_SEND"
                else "HUMAN_DEADLINE_ACTION_REVIEW"
            ),
            "response_channel": "EMAIL",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": reconciliation_lanes[
                "argos_emi_teaming_inquiry"
            ]["do_not_duplicate_send"],
            "no_send_before": argos_followup["not_before_utc"],
            "queue_action_state": argos_followup["action_state"],
            "inbox_recheck_required": argos_followup["inbox_recheck_required"],
            "current_draft_count": reconciliation_lanes[
                "argos_emi_teaming_inquiry"
            ]["current_draft_count"],
            "matching_sent_count": reconciliation_lanes[
                "argos_emi_teaming_inquiry"
            ]["matching_sent_count"],
            "matching_inbound_count": reconciliation_lanes[
                "argos_emi_teaming_inquiry"
            ]["matching_inbound_count"],
            "prior_approval_binding_expired": reconciliation_lanes[
                "argos_emi_teaming_inquiry"
            ]["prior_approval_binding_expired"],
            "attachment_count": 0,
            "selected_template_id": argos_followup[
                "current_response_template_id"
            ],
            "eligible_template_id": argos_followup["eligible_template_id"],
            "partner_interest_target_utc": argos_followup[
                "partner_interest_target_utc"
            ],
            "government_deadline_timezone": reconciliation_lanes[
                "argos_emi_teaming_inquiry"
            ]["government_deadline_timezone"],
            "action_gate": reconciliation_lanes[
                "argos_emi_teaming_inquiry"
            ]["next_action"],
            "response_artifact": rel(ARGOS_PARTNER_OUTREACH_STATUS),
            "next_action": argos_followup["next_action"],
            "claim_boundary": (
                "The recorded mailbox and queue state establishes only that one bounded "
                "partner inquiry was sent once and the proactive allowance is exhausted. "
                "It does not prove delivery, recipient review, partner interest, teaming "
                "authority, Government submission, award, funding, validation, or agency "
                "acceptance."
            ),
        },
        {
            "lane_id": "nashville_ec_takeoff_fall_2026",
            "organization": "Nashville Entrepreneur Center",
            "state": nashville_onboarding["status"],
            "deadline": nashville_action["deadline"][
                "onboarding_form_and_participation_agreement_date"
            ],
            "decision": "HUMAN_ACCOUNT_ACTION_BEFORE_ONBOARDING_DEADLINE",
            "response_channel": "OFFICIAL_ONBOARDING_ROUTE",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": True,
            "conflicting_gmail_draft_count": nashville_followup.get(
                "conflicting_gmail_draft_count", 0
            ),
            "draft_quarantine_status": nashville_followup.get(
                "draft_quarantine_status"
            ),
            "quarantined_draft_conflict_type": nashville_followup.get(
                "quarantined_draft_conflict_type"
            ),
            "action_gate": nashville_followup["next_action"],
            "response_artifact": rel(OFFICIAL_INBOUND_STATUS_EVENT_REGISTER),
            "supporting_artifacts": [
                rel(NASHVILLE_MANIFEST),
                rel(NASHVILLE_FACT_RESOLUTION),
                rel(NASHVILLE_PRIVATE_COLLECTOR),
                rel(NASHVILLE_PRIVATE_WORKFLOW),
                rel(NASHVILLE_DEADLINE_RECEIPT),
                rel(NASHVILLE_DEADLINE_RESPONSE_CONTROL),
                rel(NASHVILLE_OFFICIAL_DEADLINE_CONFIRMATION),
                rel(NASHVILLE_SUBMISSION_RECEIPT),
            ],
            "deadline_support_sent_utc": nashville_deadline["submission"]["sent_utc"],
            "deadline_support_email_is_application": False,
            "official_close_time_confirmed": True,
            "deadline_timezone_explicit_in_message": nashville_official_deadline[
                "confirmation"
            ]["timezone_explicit_in_message"],
            "operational_timezone": nashville_official_deadline["confirmation"][
                "operational_timezone"
            ],
            "private_fill_map_present": NASHVILLE_PRIVATE_FILL_MAP.is_file(),
            "private_fact_values_read_or_published": False,
            "portal_submission_verified": True,
            "cohort_selected": True,
            "financial_assistance_reported": True,
            "financial_assistance_amount_usd": nashville_onboarding["evidence"][
                "financial_assistance_amount_usd"
            ],
            "full_program_investment_usd": nashville_onboarding["evidence"][
                "full_program_investment_usd"
            ],
            "thank_you_and_acceptance_sent": True,
            "onboarding_form_completed": False,
            "participation_agreement_accepted": False,
            "deposit_submitted": False,
            "deposit_date": nashville_action["deadline"]["deposit_date"],
            "deadline_time_and_timezone_explicit": nashville_action["deadline"][
                "time_and_timezone_explicit"
            ],
            "onboarding_deadline_reconfirmed": True,
            "prior_payment_link_invalidated": nashville_info["evidence"][
                "prior_payment_link_invalidated"
            ],
            "updated_takeoff_payment_route_provided": nashville_info[
                "evidence"
            ]["updated_takeoff_payment_route_provided"],
            "payment_link_omitted": nashville_info["evidence"][
                "payment_link_omitted"
            ],
            "optional_info_sessions_offered": True,
            "optional_info_session_count": nashville_info["evidence"][
                "session_count"
            ],
            "optional_info_session_timezone_explicit": nashville_info[
                "evidence"
            ]["session_timezone_explicit"],
            "optional_info_session_selected": False,
            "info_session_attendance_required": False,
            "next_action": nashville_followup["next_action"],
            "claim_boundary": official_events["claim_boundary"],
        },
        {
            "lane_id": "launchtn_3686_pitch_2026",
            "organization": "Launch Tennessee 3686 Pitch Competition",
            "state": "NO_SAFE_UPLOAD_SET_PORTAL_FACTS_AND_ATTACHMENT_GATES_OPEN",
            "deadline": launchtn["opportunity"]["application_deadline"],
            "decision": "BUILD_ATTACHMENTS_RECHECK_PORTAL_THEN_STAGE_PREVIEW",
            "response_channel": "PORTAL",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": False,
            "action_gate": "Founder verifies legal, employment, Tennessee-eligibility, and funding-history facts; approves or replaces every financial assumption; reviews the venue-specific deck, live portal schema, terms, and complete preview before submission.",
            "response_artifact": rel(LAUNCHTN_MANIFEST),
            "supporting_artifacts": [
                rel(LAUNCHTN_DECK),
                rel(LAUNCHTN_FINANCIAL_MODEL),
            ],
            "attachment_qa_passed_count": launchtn["summary"]["required_attachments_qa_passed"],
            "attachment_structural_qa_passed_count": launchtn["summary"][
                "required_attachments_structural_qa_passed"
            ],
            "attachment_required_count": launchtn["summary"]["required_attachment_gates"],
            "safe_upload_set": launchtn["safe_upload_set"],
            "next_action": "Build and inspect the LaunchTN-specific deck, approve or replace every financial assumption, recheck the live form and file limits, then stop at the complete final preview for action-time approval before August 13 at 11:59 PM CDT.",
            "claim_boundary": launchtn["claim_boundary"],
        },
        {
            "lane_id": "epri_open_power_ai_mou",
            "organization": "EPRI Open Power AI Consortium",
            "state": reconciliation_lanes["epri_open_power_ai_mou"]["state"],
            "deadline": None,
            "decision": "PRIVATE_CUSTODY_REVIEW_REQUESTED_ASSET_PENDING_NO_REPLY",
            "response_channel": "EMAIL_REPLY",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": True,
            "no_send_before": None,
            "action_gate": "Verify both canonical PNG logo files, the attachment inventory, and the permitted-use boundary before one private action-time review. Do not repeat the onboarding facts or expose meeting details.",
            "response_artifact": rel(OFFICIAL_INBOUND_STATUS_EVENT_REGISTER),
            "supporting_artifacts": [
                rel(EPRI_SIGNING_STATE),
                rel(EPRI_RECEIPT),
                rel(EPRI_TEMPLATE),
            ],
            "latest_mailbox_event": reconciliation_lanes[
                "epri_open_power_ai_mou"
            ]["latest_event_type"],
            "user_reported_signing_complete": reconciliation_lanes[
                "epri_open_power_ai_mou"
            ]["user_reported_signing_complete"],
            "onboarding_request_observed": reconciliation_lanes[
                "epri_open_power_ai_mou"
            ]["onboarding_request_observed"],
            "onboarding_response_sent": reconciliation_lanes[
                "epri_open_power_ai_mou"
            ]["onboarding_response_sent"],
            "mrc_invite_observed": reconciliation_lanes[
                "epri_open_power_ai_mou"
            ]["mrc_invite_observed"],
            "canonical_logo_files_sent": reconciliation_lanes[
                "epri_open_power_ai_mou"
            ]["canonical_logo_files_sent"],
            "all_parties_completed": reconciliation_lanes[
                "epri_open_power_ai_mou"
            ]["all_parties_completed"],
            "completed_document_attached": reconciliation_lanes[
                "epri_open_power_ai_mou"
            ]["completed_document_attached"],
            "completed_document_private_custody_required": reconciliation_lanes[
                "epri_open_power_ai_mou"
            ]["completed_document_private_custody_required"],
            "onboarding_obligations_reviewed": reconciliation_lanes[
                "epri_open_power_ai_mou"
            ]["onboarding_obligations_reviewed"],
            "requested_asset_template_id": reconciliation_lanes[
                "epri_open_power_ai_mou"
            ]["requested_asset_template_id"],
            "next_action": reconciliation_lanes["epri_open_power_ai_mou"][
                "next_action"
            ],
            "claim_boundary": official_events["claim_boundary"],
        },
        {
            "lane_id": "georgia_patents_pro_bono_intake",
            "organization": "Georgia PATENTS",
            "state": reconciliation_lanes["georgia_patents_pro_bono_intake"][
                "state"
            ],
            "deadline": None,
            "decision": "CLOSE_SERVICE_SCOPE_NO_GO_NO_DUPLICATE",
            "response_channel": "EMAIL",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": True,
            "no_send_before": None,
            "action_gate": "Do not reply or submit the intake for this already-filed application. Continue only through USPTO Pro Se procedural support or a verified practitioner channel.",
            "response_artifact": rel(GEORGIA_PATENTS_RECEIPT),
            "supporting_artifacts": [
                rel(GEORGIA_PATENTS_TEMPLATE),
                rel(PATENT_PRIVATE_CAPTURE_WORKFLOW),
                rel(PATENT_PRACTITIONER_TEMPLATE),
            ],
            "required_docket_role_count": patent_control["public_evidence_summary"]["required_docket_role_count"],
            "captured_required_docket_role_count": patent_control["public_evidence_summary"]["captured_required_docket_role_count"],
            "docket_capture_complete": patent_control["public_evidence_summary"]["docket_capture_complete"],
            "next_action": reconciliation_lanes["georgia_patents_pro_bono_intake"][
                "next_action"
            ],
            "claim_boundary": georgia_patents["claim_boundary"],
        },
        {
            "lane_id": "lvlup_optional_paid_event",
            "organization": "LvlUp Ventures / Power of the Pitch Week",
            "state": lvlup_review["status"],
            "deadline": None,
            "decision": "MONITOR_INDEPENDENT_REVIEW_NO_DUPLICATE",
            "response_channel": "EMAIL",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": True,
            "action_gate": "Reply only if LvlUp's Investment Committee requests additional information. No sponsor purchase, unsolicited duplicate packet, valuation disclosure, or reuse of the July 3 draft without a fresh claim review and explicit founder approval.",
            "response_artifact": rel(LVLUP_REVIEW_CONFIRMATION),
            "supporting_artifacts": [rel(LVLUP_DRAFT)],
            "written_independent_review_confirmation": True,
            "paid_sponsor_purchase_required_for_separate_review": False,
            "next_action": lvlup_review["required_next_action"],
            "claim_boundary": lvlup_review["claim_boundary"],
        },
        {
            "lane_id": "sam_public_credential_rotation",
            "organization": "SAM.gov account credential control",
            "state": sam_rotation["status"],
            "deadline": sam_rotation["deadline"]["date_local"],
            "decision": "HUMAN_ACCOUNT_ACTION_REQUIRED_NO_EMAIL_REPLY",
            "response_channel": "ACCOUNT_ACTION",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": True,
            "action_gate": "Founder completes the official SAM.gov one-time-password flow, supplies the replacement key only through the hidden local installer prompt, and authorizes the final account confirmation. No secret may enter this register.",
            "response_artifact": rel(SAM_ROTATION_CONTROL),
            "supporting_artifacts": [sam_rotation["private_installer"]["path"]],
            "next_action": "Rotate the public API key inside the authenticated SAM.gov account, run the guarded installer, and rerun the verifier until the private fingerprint changes and an authenticated probe is observable.",
            "claim_boundary": sam_rotation["claim_boundary"],
        },
        {
            "lane_id": "cdc_ai_acquisition_rfi",
            "organization": "Centers for Disease Control and Prevention",
            "state": cdc["acknowledgment"]["status"],
            "deadline": "2026-07-30T21:00:00Z",
            "decision": "MONITOR_NO_REPLY_REQUIRED",
            "response_channel": "EMAIL",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": True,
            "action_gate": "Reply only if CDC asks for clarification, replacement material, or scheduling.",
            "response_artifact": rel(CDC_RECEIPT),
            "next_action": "Preserve the acknowledgment and monitor the existing thread; do not resend the response.",
            "claim_boundary": cdc["claim_boundary"],
        },
        {
            "lane_id": "lanl_vision_licensing_followup",
            "organization": "Los Alamos National Laboratory",
            "state": lanl_followup["source_state"],
            "deadline": None,
            "decision": (
                f"{lanl_followup['action_state']}_NO_SEND"
                if not str(lanl_followup["action_state"]).endswith("_NO_SEND")
                else lanl_followup["action_state"]
            ),
            "response_channel": "EMAIL",
            "response_ready": bool(lanl_followup["draft_rendered"]),
            "send_now": lanl_followup["send_now"],
            "do_not_duplicate_send": True,
            "no_send_before": lanl_followup["not_before_utc"],
            "queue_action_state": lanl_followup["action_state"],
            "inbox_recheck_required": lanl_followup["inbox_recheck_required"],
            "draft_rendered": lanl_followup["draft_rendered"],
            "eligible_template_id": lanl_followup["eligible_template_id"],
            "current_response_template_id": lanl_followup[
                "current_response_template_id"
            ],
            "recorded_proactive_send_count": lanl_followup[
                "recorded_proactive_send_count"
            ],
            "max_proactive_sends": lanl_followup["max_proactive_sends"],
            "action_gate": (
                f"{lanl_followup['next_action']} Any NDA, licensing term, "
                "export-control question, disclosure, or final dispatch remains "
                "action-time human-reviewed."
            ),
            "response_artifact": rel(OUTREACH_FOLLOWUP_ACTION_QUEUE),
            "next_action": lanl_followup["next_action"],
            "claim_boundary": lanl["claim_boundary"],
        },
        {
            "lane_id": "terry_vynetic_followup",
            "organization": "Terry Anderton / Vynetic",
            "state": reconciliation_lanes["terry_vynetic_followup"]["state"],
            "deadline": None,
            "decision": "MONITOR_NO_FURTHER_FOLLOWUP",
            "response_channel": "EMAIL_REPLY_ONLY_IF_INBOUND",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": True,
            "conflicting_gmail_draft_count": terry_followup[
                "conflicting_gmail_draft_count"
            ],
            "draft_quarantine_status": terry_followup[
                "draft_quarantine_status"
            ],
            "quarantined_draft_conflict_type": terry_followup[
                "quarantined_draft_conflict_type"
            ],
            "action_gate": terry_followup["next_action"],
            "response_artifact": rel(EMAIL_ACTION_RECONCILIATION),
            "outbound_followup_count": reconciliation_lanes[
                "terry_vynetic_followup"
            ]["outbound_followup_count"],
            "outbound_spacing_seconds": reconciliation_lanes[
                "terry_vynetic_followup"
            ]["outbound_spacing_seconds"],
            "next_action": terry_followup["next_action"],
            "claim_boundary": (
                "The mailbox record proves only that two near-duplicate follow-ups were "
                "sent and no inbound reply was observed at reconciliation time. It does "
                "not prove interest, rejection, selection, funding, or validation."
            ),
        },
        {
            "lane_id": "darpa_sn_26_97_low_resource_computing_rfi",
            "organization": "DARPA Multi X Office",
            "state": darpa_sn_26_97["status"],
            "deadline": darpa_sn_26_97["opportunity"]["deadline_date"],
            "decision": "MONITOR_FORMAL_PACKAGE_NO_DUPLICATE",
            "response_channel": "EMAIL_REPLY_ONLY_IF_INBOUND",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": True,
            "no_send_before": None,
            "action_gate": (
                "Reply only to a specific DARPA clarification, replacement request, or workshop "
                "invitation. Do not resend, expand claims, or disclose controlled information."
            ),
            "response_artifact": rel(DARPA_SN_26_97_RECEIPT),
            "attachment_count": len(darpa_sn_26_97["attachments"]),
            "formal_package_sent_utc": darpa_sn_26_97[
                "thread_reconciliation"
            ]["formal_package_sent_utc"],
            "timely_submission_claimed": False,
            "next_action": darpa_sn_26_97["send_control"]["next_action"],
            "claim_boundary": darpa_sn_26_97["claim_boundary"],
        },
        {
            "lane_id": "fhwa_tsmo_qualified_partner_outreach",
            "organization": fhwa_outreach["target"]["organization"],
            "state": fhwa_outreach["status"],
            "deadline": fhwa_outreach["opportunity"]["phase_i_deadline"],
            "decision": "CLOSE_NO_GO_TEAM_SET_NO_DUPLICATE",
            "response_channel": "EMAIL",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": True,
            "no_send_before": fhwa_outreach["response_control"][
                "no_follow_up_before"
            ],
            "action_gate": (
                "Close this route. Do not claim a partner, cite corporate experience, draft a "
                "joint submission, or send another follow-up."
            ),
            "response_artifact": rel(FHWA_PARTNER_OUTREACH),
            "supporting_artifacts": [
                rel(FHWA_TEAMING_TEMPLATE),
                rel(FHWA_PARTNER_RESPONSE_CONTROL),
                rel(EMAIL_ACTION_RECONCILIATION),
            ],
            "message_id_sha256": fhwa_active_outbound["message_id_sha256"],
            "delivery_failure_count": fhwa_delivery["delivery_failure_count"],
            "replacement_send_count": fhwa_delivery["replacement_send_count"],
            "threaded_acknowledgment_send_count": fhwa_delivery[
                "threaded_acknowledgment_send_count"
            ],
            "confirmed_delivery_count": fhwa_delivery["confirmed_delivery_count"],
            "inbound_response_count": fhwa_delivery["response_count"],
            "qualified_response_lead_referral_count": fhwa_delivery[
                "qualified_response_lead_referral_count"
            ],
            "fit_check_confirmed_count": fhwa_delivery[
                "fit_check_confirmed_count"
            ],
            "team_set_decline_count": fhwa_delivery["team_set_decline_count"],
            "last_outbound_status": fhwa_active_outbound["status"],
            "active_route_status": fhwa_outreach["response_control"]["state"],
            "qualified_partner_evidence_present": fhwa_outreach[
                "response_control"
            ]["qualified_partner_evidence_present"],
            "next_action": fhwa_outreach["response_control"]["next_action"],
            "claim_boundary": fhwa_outreach["claim_boundary"],
        },
        {
            "lane_id": "nasa_data_center_rfi",
            "organization": "NASA",
            "state": "SENT_VERIFIED_RESPONSE_PENDING",
            "deadline": "2026-07-17T21:00:00Z",
            "decision": "MONITOR_NO_DUPLICATE",
            "response_channel": "EMAIL",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": True,
            "action_gate": "Respond only to an agency clarification or replacement request.",
            "response_artifact": rel(SUBMISSION_RECEIPT),
            "next_action": "Retain the SENT receipt and attachment hash; do not resend before the deadline.",
            "claim_boundary": nasa["claim_boundary"],
        },
        {
            "lane_id": "army_aidp_draft_cfs_feedback",
            "organization": "U.S. Army",
            "state": "SENT_VERIFIED_RESPONSE_PENDING",
            "deadline": None,
            "decision": "MONITOR_NO_DUPLICATE",
            "response_channel": "EMAIL",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": True,
            "action_gate": "Respond only to an agency clarification or replacement request.",
            "response_artifact": rel(SUBMISSION_RECEIPT),
            "next_action": "Retain the SENT receipt and attachment hash; monitor for agency feedback.",
            "claim_boundary": army["claim_boundary"],
        },
    ]

    for row in records:
        row["record_sha256"] = lane_hash(row)

    launchtn_attachments = {
        row["id"]: row for row in launchtn["required_attachments"]
    }
    attachment_checks = {
        "army": verify_attachment(army),
        "nasa": verify_attachment(nasa),
        "cdc": verify_attachment(cdc["submission"]),
        "lanl": verify_attachment(lanl["submission"]),
        "launchtn_pitch_deck": verify_qa_attachment(
            launchtn_attachments["launchtn_pitch_deck"]
        ),
        "launchtn_financial_model": verify_qa_attachment(
            launchtn_attachments["launchtn_financial_model"]
        ),
    }
    all_attachment_checks_pass = all(
        check["sha256_match"] and check["bytes_match"]
        for check in attachment_checks.values()
    )
    if not all_attachment_checks_pass:
        raise ValueError("One or more engagement receipt attachments failed integrity verification")

    payload: dict[str, Any] = {
        "schema": "lumencore.external_engagement_response_register.v1",
        "generated_utc": generated_utc or now_utc(),
        "as_of_date": "2026-07-28",
        "status": "CURRENT_RESPONSE_CONTROL_HUMAN_GATED",
        "direct_answer": (
            "An external technical adviser prospect confirmed the July 28 product-and-validation meeting time, and the calendar invitation was accepted. Prepare the evidence-first brief and do not create a duplicate event. "
            "Nashville EC selected LumenCore for the Fall 2026 TakeOff cohort. The official onboarding form and participation agreement are due July 31, with a separate deposit date of August 14; both remain founder-reviewed account actions, and no duplicate acceptance email is needed. Four optional information sessions were offered, but the email did not state a timezone, so verify the official calendar event before saving one. "
            "DARPA-SN-26-97 received the formal two-attachment RFI package after inviting an instructions-aligned submission; monitor the thread without claiming deadline compliance or receipt acceptance. "
            "The Cambridge Systematics response lead then confirmed that its FHWA team is already set and will not add partners, so that route is closed with no follow-up. Georgia PATENTS also confirmed that it does not provide the requested already-filed prosecution support, so that route is closed. "
            "No additional email should be sent now. The LANL bounded follow-up is already recorded in the sealed ledger, so its proactive allowance is exhausted and the existing thread is monitor-only. "
            "EPRI confirmed that all parties completed the consortium MOU and attached the "
            "completed document. Archive it privately, hash it, and review any onboarding "
            "obligations without replying or exposing signing details. The separately requested "
            "logo files remain pending canonical-asset and permitted-use review. "
            "Complete the overdue SAM account-key action and keep the LaunchTN 3686 lane fail-closed while "
            "the venue deck, financial assumptions, founder facts, portal schema, and final preview remain open. DARPA, EPRI, CDC, Terry, NASA, and Army "
            "are monitor-only. LvlUp confirmed that declining its optional paid sponsor track does not affect the separate investment and accelerator review, so monitor that thread without spending or sending a duplicate packet; duplicate sends would reduce credibility."
        ),
        "summary": {
            "record_count": len(records),
            "immediate_human_action_count": sum(
                1
                for row in records
                if str(row["decision"]).startswith("HUMAN_")
            ),
            "monitor_only_count": sum(1 for row in records if str(row["decision"]).startswith("MONITOR")),
            "mailbox_recheck_due_count": sum(
                1
                for row in records
                if row.get("queue_action_state")
                in {
                    "RECHECK_MAILBOX_BEFORE_DRAFT",
                    "DEADLINE_ACTION_DUE_MAILBOX_RECHECK",
                }
            ),
            "conflicting_gmail_draft_count": sum(
                row.get("conflicting_gmail_draft_count", 0)
                for row in records
            ),
            "conflicting_gmail_draft_lane_count": sum(
                1
                for row in records
                if row.get("conflicting_gmail_draft_count", 0) > 0
            ),
            "do_not_duplicate_send_count": sum(1 for row in records if row["do_not_duplicate_send"]),
            "verified_attachment_count": len(attachment_checks),
            "all_attachment_checks_pass": all_attachment_checks_pass,
            "autonomous_external_send_allowed": False,
            "autonomous_final_portal_submission_allowed": False,
            "email_action_reconciliation_status": email_reconciliation["status"],
        },
        "records": records,
        "attachment_checks": attachment_checks,
        "inbox_risk_filters": [
            {
                "pattern": "Paid third-party SAM renewal solicitation",
                "decision": "DO_NOT_TREAT_AS_OFFICIAL_SAM_NOTICE",
                "safe_action": "Verify registration status and renewal tasks only inside SAM.gov or through an official .gov notice.",
            },
            {
                "pattern": "Paid sponsor activation presented near a venture review",
                "decision": "DO_NOT_TREAT_AS_REQUIRED_FOR_FUND_REVIEW",
                "safe_action": "Keep sponsor purchases separate from investment or accelerator evaluation unless written terms prove otherwise.",
            },
            {
                "pattern": "Patent intake without a confidentiality relationship",
                "decision": "PROCEDURAL_FACTS_ONLY",
                "safe_action": "Do not send unpublished specifications, claims, drawings, application identifiers, or private Patent Center records until a reviewed confidential channel exists.",
            },
        ],
        "source_artifacts": {
            "external_submission_receipt": artifact_status(SUBMISSION_RECEIPT),
            "cdc_engagement_receipt": artifact_status(CDC_RECEIPT),
            "lanl_engagement_receipt": artifact_status(LANL_RECEIPT),
            "epri_response_template": artifact_status(EPRI_TEMPLATE),
            "epri_engagement_receipt": artifact_status(EPRI_RECEIPT),
            "epri_mou_signing_state": artifact_status(EPRI_SIGNING_STATE),
            "official_inbound_status_event_register": artifact_status(
                OFFICIAL_INBOUND_STATUS_EVENT_REGISTER
            ),
            "georgia_patents_response_template": artifact_status(GEORGIA_PATENTS_TEMPLATE),
            "georgia_patents_engagement_receipt": artifact_status(GEORGIA_PATENTS_RECEIPT),
            "patent_deadline_control": artifact_status(PATENT_DEADLINE_CONTROL),
            "patent_private_capture_workflow": artifact_status(PATENT_PRIVATE_CAPTURE_WORKFLOW),
            "patent_practitioner_request_template": artifact_status(PATENT_PRACTITIONER_TEMPLATE),
            "nashville_application_manifest": artifact_status(NASHVILLE_MANIFEST),
            "nashville_human_fact_resolution": artifact_status(NASHVILLE_FACT_RESOLUTION),
            "nashville_private_collector": artifact_status(NASHVILLE_PRIVATE_COLLECTOR),
            "nashville_private_workflow": artifact_status(NASHVILLE_PRIVATE_WORKFLOW),
            "nashville_deadline_preservation_receipt": artifact_status(
                NASHVILLE_DEADLINE_RECEIPT
            ),
            "nashville_deadline_response_control": artifact_status(
                NASHVILLE_DEADLINE_RESPONSE_CONTROL
            ),
            "nashville_official_deadline_confirmation": artifact_status(
                NASHVILLE_OFFICIAL_DEADLINE_CONFIRMATION
            ),
            "nashville_submission_receipt": artifact_status(
                NASHVILLE_SUBMISSION_RECEIPT
            ),
            "nashville_private_fill_map": {
                "path": rel(NASHVILLE_PRIVATE_FILL_MAP),
                "present": NASHVILLE_PRIVATE_FILL_MAP.is_file(),
                "bytes": 0,
                "sha256": None,
                "private_values_read_or_published": False,
                "sha256_published": False,
            },
            "launchtn_application_manifest": artifact_status(LAUNCHTN_MANIFEST),
            "launchtn_pitch_deck": artifact_status(LAUNCHTN_DECK),
            "launchtn_financial_model": artifact_status(LAUNCHTN_FINANCIAL_MODEL),
            "lvlup_historical_application_draft": artifact_status(LVLUP_DRAFT),
            "lvlup_independent_review_confirmation": artifact_status(
                LVLUP_REVIEW_CONFIRMATION
            ),
            "sam_public_credential_rotation_control": artifact_status(
                SAM_ROTATION_CONTROL
            ),
            "email_action_reconciliation": artifact_status(
                EMAIL_ACTION_RECONCILIATION
            ),
            "outreach_followup_action_queue": artifact_status(
                OUTREACH_FOLLOWUP_ACTION_QUEUE
            ),
            "argos_partner_outreach_status": artifact_status(
                ARGOS_PARTNER_OUTREACH_STATUS
            ),
            "stan_meeting_invite_state": artifact_status(
                STAN_MEETING_INVITE_STATE
            ),
            "outreach_draft_quarantine_state": artifact_status(
                OUTREACH_DRAFT_QUARANTINE_STATE
            ),
            "darpa_sn_26_97_public_submission_receipt": artifact_status(
                DARPA_SN_26_97_RECEIPT
            ),
            "fhwa_teaming_template": artifact_status(FHWA_TEAMING_TEMPLATE),
            "fhwa_partner_outreach_control": artifact_status(
                FHWA_PARTNER_OUTREACH
            ),
            "fhwa_partner_response_control": artifact_status(
                FHWA_PARTNER_RESPONSE_CONTROL
            ),
        },
        "claim_boundary": REGISTER_BOUNDARY,
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "canonical_json": rel(CANONICAL_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["register_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        f"# External Engagement Response Register - {payload['as_of_date']}",
        "",
        payload["direct_answer"],
        "",
        "## Control Summary",
        "",
        f"- Status: `{payload['status']}`",
        f"- Engagement records: `{summary['record_count']}`",
        f"- Immediate human actions: `{summary['immediate_human_action_count']}`",
        f"- Monitor-only lanes: `{summary['monitor_only_count']}`",
        f"- Mailbox rechecks due: `{summary['mailbox_recheck_due_count']}`",
        f"- Conflicting Gmail drafts: `{summary['conflicting_gmail_draft_count']}`",
        f"- Quarantined draft lanes: `{summary['conflicting_gmail_draft_lane_count']}`",
        f"- Do-not-duplicate lanes: `{summary['do_not_duplicate_send_count']}`",
        f"- Verified attachments: `{summary['verified_attachment_count']}`",
        f"- All attachment checks pass: `{str(summary['all_attachment_checks_pass']).lower()}`",
        f"- Autonomous external send allowed: `{str(summary['autonomous_external_send_allowed']).lower()}`",
        f"- Autonomous final portal submit allowed: `{str(summary['autonomous_final_portal_submission_allowed']).lower()}`",
        f"- Register SHA-256: `{payload['register_sha256']}`",
        "",
        "## Response Queue",
        "",
        "| Organization | State | Decision | Deadline / Hold | Duplicate Send |",
        "|---|---|---|---|---:|",
    ]
    for row in payload["records"]:
        deadline = row.get("deadline") or row.get("no_send_before") or "None"
        lines.append(
            f"| {row['organization']} | `{row['state']}` | `{row['decision']}` | {deadline} | "
            f"`{str(row['do_not_duplicate_send']).lower()}` |"
        )

    for row in payload["records"]:
        lines.extend(
            [
                "",
                f"### {row['organization']}",
                "",
                f"- Lane: `{row['lane_id']}`",
                f"- State: `{row['state']}`",
                f"- Decision: `{row['decision']}`",
                f"- Response channel: `{row['response_channel']}`",
                f"- Response ready: `{str(row['response_ready']).lower()}`",
                f"- Send now: `{str(row['send_now']).lower()}`",
                f"- Action gate: {row['action_gate']}",
                f"- Next action: {row['next_action']}",
                f"- Response artifact: `{row['response_artifact']}`",
                f"- Claim boundary: {row['claim_boundary']}",
                f"- Record SHA-256: `{row['record_sha256']}`",
            ]
        )
        template = row.get("follow_up_template")
        if isinstance(template, dict):
            lines.extend(
                [
                    "",
                    f"**Held follow-up subject:** {template['subject']}",
                    "",
                    "```text",
                    template["body"],
                    "```",
                ]
            )

    lines.extend(["", "## Inbox Risk Filters", ""])
    for row in payload["inbox_risk_filters"]:
        lines.extend(
            [
                f"- **{row['pattern']}**: `{row['decision']}`",
                f"  Safe action: {row['safe_action']}",
            ]
        )

    lines.extend(["", "## Source Integrity", ""])
    for key, row in payload["source_artifacts"].items():
        lines.append(
            f"- `{key}`: present=`{str(row['present']).lower()}` bytes=`{row['bytes']}` sha256=`{row['sha256']}` path=`{row['path']}`"
        )
    lines.extend(["", "## Claim Boundary", "", payload["claim_boundary"], ""])
    return "\n".join(lines)


def ensure_public_safe(text: str) -> None:
    lowered = text.lower()
    hits = sorted(marker for marker in PRIVATE_MARKERS if marker in lowered)
    if hits:
        raise ValueError(f"Public response register contains prohibited private markers: {hits}")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    ensure_public_safe(json.dumps(payload, sort_keys=True))
    ensure_public_safe(markdown)
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_json(CANONICAL_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "records": payload["summary"]["record_count"],
                "immediate_human_actions": payload["summary"]["immediate_human_action_count"],
                "do_not_duplicate": payload["summary"]["do_not_duplicate_send_count"],
                "all_attachment_checks_pass": payload["summary"]["all_attachment_checks_pass"],
                "json": rel(OUT_JSON),
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
