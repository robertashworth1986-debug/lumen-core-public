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
    / "LAUNCHTN_3686_APPLICATION_MANIFEST_2026-07-17.json"
)
LAUNCHTN_DECK = (
    ROOT
    / "grant_submissions"
    / "LAUNCHTN_3686_PITCH_2026"
    / "LUMENCORE_3686_PITCH_DECK_2026-07-17.pptx"
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
    if patent_control.get("schema") != "lumencore.patent_deadline_evidence_control.v1":
        raise ValueError("Patent deadline evidence control is missing or stale")
    if launchtn.get("schema") != "lumencore.launchtn_3686_pitch_application.v1":
        raise ValueError("LaunchTN 3686 application manifest is missing or stale")
    if sam_rotation.get("schema") != "lumencore.sam_public_credential_rotation_control.v1":
        raise ValueError("SAM public credential rotation control is missing or stale")
    if email_reconciliation.get("schema") != "lumencore.email_action_reconciliation.v1":
        raise ValueError("Email action reconciliation is missing or stale")
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
    if email_reconciliation.get("status") != (
        "NO_UNANSWERED_DEADLINE_CRITICAL_EMAIL_ACTION"
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
    } - reconciliation_lanes.keys():
        raise ValueError("Email action reconciliation is missing required lane controls")
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
            "lane_id": "nashville_ec_takeoff_fall_2026",
            "organization": "Nashville Entrepreneur Center",
            "state": nashville_submission["status"],
            "deadline": nashville_official_deadline["confirmation"][
                "operational_local_deadline"
            ],
            "decision": "MONITOR_REVIEW_RESULT_NO_DUPLICATE",
            "response_channel": "EMAIL_MONITOR_ONLY",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": True,
            "action_gate": "Wait for the rolling review result through August 3. Reply only if NEC asks a specific question or requests a correction.",
            "response_artifact": rel(NASHVILLE_SUBMISSION_RECEIPT),
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
            "expected_next_steps_by": nashville_submission["confirmation_page"][
                "expected_next_steps_by"
            ],
            "next_action": "Monitor the existing account through August 3. Do not resubmit or reply to the automated confirmation, and do not describe the application as accepted, selected, or funded.",
            "claim_boundary": nashville_submission["claim_boundary"],
        },
        {
            "lane_id": "launchtn_3686_pitch_2026",
            "organization": "Launch Tennessee 3686 Pitch Competition",
            "state": "PORTAL_PACKET_QA_PASSED_HUMAN_FACTS_AND_FOUNDER_APPROVAL_REQUIRED",
            "deadline": launchtn["opportunity"]["application_deadline"],
            "decision": "STAGE_PORTAL_FINAL_PREVIEW_REQUIRED",
            "response_channel": "PORTAL",
            "response_ready": True,
            "send_now": False,
            "do_not_duplicate_send": False,
            "action_gate": "Founder enters the 11 private, legal, employment, Tennessee-eligibility, funding-history, and pricing confirmations; approves the $250,000 illustrative raise and pricing assumptions; verifies both attachment hashes; then reviews the complete live preview before final submission.",
            "response_artifact": rel(LAUNCHTN_MANIFEST),
            "supporting_artifacts": [
                rel(LAUNCHTN_DECK),
                rel(LAUNCHTN_FINANCIAL_MODEL),
            ],
            "attachment_qa_passed_count": launchtn["summary"]["required_attachments_qa_passed"],
            "attachment_required_count": launchtn["summary"]["required_attachment_gates"],
            "next_action": "Keep the portal staged. After founder facts and assumptions are confirmed, attach the hash-verified deck and financial model, inspect the final rendered application, and obtain action-time approval before submitting by August 13 at 11:59 PM CDT.",
            "claim_boundary": launchtn["claim_boundary"],
        },
        {
            "lane_id": "epri_open_power_ai_mou",
            "organization": "EPRI Open Power AI Consortium",
            "state": epri["acknowledgment"]["status"],
            "deadline": None,
            "decision": "MONITOR_FOR_MOU_NO_DUPLICATE",
            "response_channel": "EMAIL_REPLY",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": True,
            "no_send_before": epri["acknowledgment"]["earliest_follow_up_date"],
            "action_gate": "Reply only when EPRI sends the MOU, requests a correction, or asks for additional onboarding information.",
            "response_artifact": rel(EPRI_RECEIPT),
            "supporting_artifacts": [rel(EPRI_TEMPLATE)],
            "latest_mailbox_event": reconciliation_lanes[
                "epri_open_power_ai_mou"
            ]["latest_event_type"],
            "out_of_office_through": reconciliation_lanes[
                "epri_open_power_ai_mou"
            ]["out_of_office_through"],
            "next_action": "Monitor the existing thread for the DocuSign envelope or a clarification request; do not resend identity details.",
            "claim_boundary": epri["claim_boundary"],
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
            "state": lanl["acknowledgment"]["status"],
            "deadline": None,
            "decision": "MONITOR_THEN_ONE_BOUNDED_FOLLOW_UP",
            "response_channel": "EMAIL",
            "response_ready": True,
            "send_now": False,
            "do_not_duplicate_send": True,
            "no_send_before": lanl["acknowledgment"]["earliest_follow_up_date"],
            "action_gate": "No follow-up before 2026-07-23 unless LANL replies first; any NDA, licensing term, export-control question, or disclosure remains human-reviewed.",
            "response_artifact": rel(LANL_RECEIPT),
            "next_action": "Wait for LANL. If no reply by July 23, use the single bounded follow-up template in this register.",
            "follow_up_template": {
                "subject": "Follow-up: LumenCore package for LANL VISION licensing discussion",
                "body": (
                    "Michael and Neil,\n\nI am following up on the bounded LumenCore package sent July 16. "
                    "Would a short Stage 0 diligence session be useful to decide whether a VISION evaluation or "
                    "licensing discussion is warranted? I am not asserting a license, LANL endorsement, field "
                    "validation, or production readiness. I would welcome your preferred next step and any "
                    "confidentiality or data-boundary requirements.\n\nBest regards,\nRobert Ashworth\nLumenCore"
                ),
            },
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
            "action_gate": (
                "No additional outbound message. If Terry replies, read the complete "
                "thread and answer only the specific ask without sending another broad deck."
            ),
            "response_artifact": rel(EMAIL_ACTION_RECONCILIATION),
            "outbound_followup_count": reconciliation_lanes[
                "terry_vynetic_followup"
            ]["outbound_followup_count"],
            "outbound_spacing_seconds": reconciliation_lanes[
                "terry_vynetic_followup"
            ]["outbound_spacing_seconds"],
            "next_action": reconciliation_lanes["terry_vynetic_followup"][
                "next_action"
            ],
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
        "as_of_date": "2026-07-18",
        "status": "CURRENT_RESPONSE_CONTROL_HUMAN_GATED",
        "direct_answer": (
            "Nashville EC's portal displayed a submission confirmation before the operational July 17 close, and the follow-up email says rolling-review next steps are expected by August 3. Monitor without resubmitting or implying selection. "
            "DARPA-SN-26-97 received the formal two-attachment RFI package after inviting an instructions-aligned submission; monitor the thread without claiming deadline compliance or receipt acceptance. "
            "The Cambridge Systematics response lead then confirmed that its FHWA team is already set and will not add partners, so that route is closed with no follow-up. Georgia PATENTS also confirmed that it does not provide the requested already-filed prosecution support, so that route is closed. "
            "No additional email should be sent now. "
            "Complete the overdue SAM account-key action and keep the QA-passed LaunchTN 3686 package staged for "
            "founder facts, assumption approval, and final preview. DARPA, EPRI, CDC, LANL, Terry, NASA, and Army "
            "are monitor-only. LvlUp confirmed that declining its optional paid sponsor track does not affect the separate investment and accelerator review, so monitor that thread without spending or sending a duplicate packet; duplicate sends would reduce credibility."
        ),
        "summary": {
            "record_count": len(records),
            "immediate_human_action_count": sum(
                1
                for row in records
                if row["lane_id"] == "sam_public_credential_rotation"
            ),
            "monitor_only_count": sum(1 for row in records if str(row["decision"]).startswith("MONITOR")),
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
