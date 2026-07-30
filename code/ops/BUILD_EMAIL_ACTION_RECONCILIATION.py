from __future__ import annotations

import hashlib
import json
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
EPRI_MOU_SIGNING_STATE = (
    SPRINT_DIR / "EPRI_OPEN_POWER_AI_MOU_SIGNING_STATE_2026-07-23.json"
)
EPRI_LOGO_RESPONSE_SEND_STATUS = (
    SPRINT_DIR / "EPRI_OPAI_LOGO_RESPONSE_SEND_STATUS_2026-07-29.json"
)
LVLUP_REVIEW_CONFIRMATION = (
    SPRINT_DIR / "LVLUP_INDEPENDENT_REVIEW_CONFIRMATION_2026-07-17.json"
)
LVLUP_OUTREACH_SEND_STATE = (
    SPRINT_DIR / "LVLUP_OUTREACH_SEND_STATE_2026-07-23.json"
)
LVLUP_APPLICATION_REVIEW_STATUS_RESPONSE_STATE = (
    SPRINT_DIR
    / "LVLUP_APPLICATION_REVIEW_STATUS_RESPONSE_STATE_2026-07-23.json"
)
THIRD_SPHERE_OUTREACH_SEND_STATE = (
    SPRINT_DIR / "THIRD_SPHERE_SEEDSTRAP_OUTREACH_SEND_STATE_2026-07-23.json"
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
DLA_DSIP_NON_SUBMISSION_RECEIPT = (
    SPRINT_DIR / "DLA_DSIP_OFFICIAL_NON_SUBMISSION_RECEIPT_2026-07-28.json"
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
OUTREACH_RESPONSE_TEMPLATE_REGISTRY = (
    SPRINT_DIR / "OUTREACH_RESPONSE_TEMPLATE_REGISTRY_2026-07-18.json"
)
OUTREACH_FOLLOWUP_POLICY_CONFIG = (
    ROOT / "config" / "outreach_followup_policies_v1.json"
)
NCCU_PATENT_CLINIC_ROUTE_CLOSURE = (
    SPRINT_DIR / "NCCU_PATENT_CLINIC_ROUTE_CLOSURE_STATE_2026-07-22.json"
)
USPTO_DOCUMENT_SERVICES_ROUTING_RESPONSE = (
    SPRINT_DIR / "USPTO_DOCUMENT_SERVICES_ROUTING_RESPONSE_STATE_2026-07-23.json"
)
OUTREACH_DRAFT_QUARANTINE_STATE = (
    SPRINT_DIR / "OUTREACH_DRAFT_QUARANTINE_STATE_2026-07-23.json"
)
OFFICIAL_INBOUND_STATUS_EVENT_REGISTER = (
    SPRINT_DIR / "OFFICIAL_INBOUND_STATUS_EVENT_REGISTER_2026-07-25.json"
)
ARGOS_PARTNER_OUTREACH_STATUS = (
    SPRINT_DIR / "ARGOS_PARTNER_OUTREACH_STATUS_2026-07-28.json"
)
ARGOS_GOVERNMENT_SUBMISSION_STATUS = (
    SPRINT_DIR / "ARGOS_GOVERNMENT_SUBMISSION_STATUS_2026-07-28.json"
)

VALID_FOLLOWUP_MODES = {
    "ACCOUNT_ACTION",
    "CLOSED",
    "INBOUND_ONLY",
    "ONE_BOUNDED_INITIAL_OUTREACH_BEFORE_DEADLINE",
    "ONE_BOUNDED_FOLLOW_UP_AFTER_HOLD",
    "PORTAL_ACTION",
    "PRIVATE_RECONCILIATION",
}

AS_OF_DATE = "2026-07-29"


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


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789ABCDEF" for char in value)
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def validate_epri_logo_response_send_status(
    receipt: dict[str, Any],
) -> dict[str, Any]:
    authorization = receipt.get("authorization", {})
    mailbox = receipt.get("mailbox_observation", {})
    dispatch = receipt.get("dispatch", {})
    controls = receipt.get("controls", {})
    attachments = dispatch.get("attachments", [])
    expected_filenames = {
        "lumencore_logo_on_dark_1024.png",
        "lumencore_logo_on_light_1024.png",
    }
    if (
        receipt.get("schema")
        != "lumencore.epri_opai_logo_response_send_status.v1"
        or receipt.get("lane_id") != "epri_open_power_ai_mou"
        or receipt.get("status") != "SENT_ONCE_POST_SEND_VERIFIED_NO_DUPLICATE"
        or authorization.get("fresh_full_thread_read_completed") is not True
        or authorization.get("exact_permitted_use_boundary_confirmed") is not True
        or authorization.get("fresh_duplicate_check_completed") is not True
        or mailbox.get("matching_logo_attachment_sent_count_before_send") != 0
        or mailbox.get("matching_epri_attachment_sent_count_before_send") != 0
        or mailbox.get("post_send_sent_copy_verified") is not True
        or mailbox.get("matching_logo_attachment_sent_count_after_send") != 1
        or mailbox.get("gmail_identifiers_omitted") is not True
        or mailbox.get("recipient_addresses_omitted") is not True
        or mailbox.get("message_body_omitted") is not True
        or dispatch.get("attachment_count") != 2
        or dispatch.get("bcc_count") != 0
        or len(attachments) != 2
        or {row.get("filename") for row in attachments} != expected_filenames
        or any(not is_sha256(row.get("sha256")) for row in attachments)
        or controls.get("single_send_only") is not True
        or controls.get("duplicate_send_prohibited") is not True
        or controls.get("external_action_performed") is not True
        or controls.get("additional_attachments_sent") is not False
        or not isinstance(receipt.get("next_action"), str)
        or not receipt["next_action"].startswith("Do not resend the logo pair.")
    ):
        raise ValueError("EPRI logo-response send status is missing or unsafe")
    return receipt


def validate_dla_dsip_non_submission_receipt(
    receipt: dict[str, Any],
) -> dict[str, Any]:
    source = receipt.get("source", {})
    evidence = receipt.get("evidence", {})
    action = receipt.get("action", {})
    controls = receipt.get("controls", {})
    if (
        receipt.get("schema")
        != "lumencore.dla_dsip_official_non_submission_receipt.v1"
        or receipt.get("status")
        != "OFFICIAL_DLA_CONFIRMED_PROPOSAL_IN_PROGRESS_NOT_SUBMITTED"
        or receipt.get("lane_id") != "missionweave_dsip_proposal"
        or receipt.get("topic") != "DLA26BZ03-NV011"
        or receipt.get("as_of_utc") != source.get("received_utc")
        or source.get("subject_sha256")
        != sha256_text(str(source.get("subject") or ""))
        or source.get("sender_address_omitted") is not True
        or source.get("recipient_identifiers_omitted") is not True
        or source.get("message_body_omitted") is not True
        or source.get("private_mail_identifiers_omitted") is not True
        or source.get("signature_and_contact_details_omitted") is not True
        or source.get("full_thread_read") is not True
        or source.get("thread_truncated") is not False
        or evidence.get("official_dla_response") is not True
        or evidence.get("official_portal_status_observed") is not True
        or evidence.get("portal_status") != "IN_PROGRESS"
        or evidence.get("portal_snapshot_reported") is not True
        or evidence.get("portal_snapshot_omitted") is not True
        or evidence.get("formally_submitted") is not False
        or evidence.get("submission_receipt_observed") is not False
        or evidence.get("deadline_elapsed") is not True
        or evidence.get("founder_portal_recheck_required") is not False
        or action.get("missing_facts") != []
        or action.get("deadline") is not None
        or action.get("email_reply_required") is not False
        or action.get("portal_action_required") is not False
        or action.get("send_now") is not False
        or action.get("do_not_duplicate_send") is not True
        or action.get("selected_template_id") != "NO_DUPLICATE_MONITOR"
        or action.get("duplicate_send_decision")
        != "CLOSE_NOT_SUBMITTED_DO_NOT_RESEND"
        or controls.get("builder_can_send_email") is not False
        or controls.get("builder_can_access_authenticated_portal") is not False
        or controls.get("builder_can_change_portal_state") is not False
        or controls.get("credentials_omitted") is not True
        or controls.get("private_identifiers_omitted") is not True
        or controls.get("legal_or_compliance_claim_created") is not False
        or controls.get("submission_claim_allowed") is not False
    ):
        raise ValueError(
            "DLA DSIP official non-submission receipt is missing or unsafe"
        )
    return receipt


def validate_argos_partner_outreach_status(
    state: dict[str, Any],
) -> dict[str, Any]:
    opportunity = state.get("opportunity", {})
    route = state.get("recipient_route", {})
    mailbox = state.get("mailbox_observation", {})
    prior_binding = state.get("prior_binding", {})
    source_control = state.get("source_control", {})
    controls = state.get("controls", {})
    if (
        state.get("schema") != "lumencore.argos_partner_outreach_status.v1"
        or state.get("lane_id") != "argos_emi_teaming_inquiry"
        or opportunity.get("government_deadline_utc") != "2026-07-30T21:00:00Z"
        or opportunity.get("government_deadline_timezone") != "America/New_York"
        or opportunity.get("partner_interest_target_utc") != "2026-07-28T17:00:00Z"
        or route.get("public_route_verified") is not True
        or route.get("address_omitted") is not True
        or mailbox.get("full_mailbox_search_completed") is not True
        or mailbox.get("matching_inbound_count") != 0
        or mailbox.get("gmail_identifiers_omitted") is not True
        or mailbox.get("message_body_omitted") is not True
        or mailbox.get("attachment_count") != 0
        or mailbox.get("cc_count") != 0
        or mailbox.get("bcc_count") != 0
        or not is_sha256(mailbox.get("subject_sha256"))
        or not is_sha256(mailbox.get("body_sha256"))
        or not is_sha256(prior_binding.get("binding_sha256"))
        or prior_binding.get("expired_at_record_time") is not True
        or prior_binding.get("prior_approval_reusable") is not False
        or source_control.get("selected_template_id")
        != "INITIAL_PARTNER_TEAMING_INQUIRY"
        or controls.get("builder_can_send_email") is not False
        or controls.get("draft_creation_authorizes_send") is not False
        or controls.get("private_human_unlock_required") is not True
        or controls.get("duplicate_send_prohibited") is not True
        or controls.get("partner_name_use_requires_written_authority") is not True
    ):
        raise ValueError("Argos partner-outreach state is missing or unsafe")
    status = state.get("status")
    if status == "DRAFT_ONLY_APPROVAL_EXPIRED_DEADLINE_OPEN":
        if (
            mailbox.get("matching_current_draft_count") != 1
            or mailbox.get("matching_sent_count") != 0
            or mailbox.get("current_draft_only") is not True
            or controls.get("fresh_full_mailbox_recheck_required") is not True
            or controls.get("fresh_draft_readback_required") is not True
            or controls.get("new_five_minute_exact_approval_required") is not True
        ):
            raise ValueError("Argos draft-only state is missing or unsafe")
    elif status == "SENT_ONCE_POST_SEND_VERIFIED_WAITING_FOR_REPLY":
        if (
            mailbox.get("matching_current_draft_count") != 0
            or mailbox.get("matching_sent_count") != 1
            or mailbox.get("current_draft_only") is not False
            or mailbox.get("sent_copy_present") is not True
            or mailbox.get("sent_utc") != state.get("recorded_utc")
            or controls.get("fresh_full_mailbox_recheck_completed_before_send")
            is not True
            or controls.get("fresh_draft_readback_completed_before_send") is not True
            or controls.get("action_time_human_approval_received") is not True
            or controls.get("final_send_performed") is not True
            or controls.get("post_send_sent_copy_verified") is not True
        ):
            raise ValueError("Argos post-send state is missing or unsafe")
    else:
        raise ValueError("Argos partner-outreach state is unknown")
    if str(prior_binding.get("expires_utc") or "") >= str(
        state.get("recorded_utc") or ""
    ):
        raise ValueError("Argos prior approval binding is not expired")
    return state


def validate_argos_government_submission_status(
    state: dict[str, Any],
) -> dict[str, Any]:
    opportunity = state.get("opportunity", {})
    authorization = state.get("authorization", {})
    mailbox = state.get("mailbox_observation", {})
    dispatch = state.get("dispatch", {})
    controls = state.get("controls", {})
    if (
        state.get("schema")
        != "lumencore.argos_government_submission_status.v1"
        or state.get("notice_id") != "ONC-ARGOS-SSN-2026-OS351107"
        or state.get("status") != "SENT_ONCE_POST_SEND_VERIFIED_NO_DUPLICATE"
        or opportunity.get("official_notice_active_at_send") is not True
        or opportunity.get("government_deadline_utc")
        != "2026-07-30T21:00:00Z"
        or not is_sha256(opportunity.get("official_source_receipt_sha256"))
        or authorization.get("exact_action_time_phrase_received") is not True
        or not is_sha256(authorization.get("approval_phrase_sha256"))
        or authorization.get("sent_within_binding_window") is not True
        or mailbox.get("full_mailbox_duplicate_search_completed_before_send")
        is not True
        or mailbox.get("matching_sent_count_before_send") != 0
        or mailbox.get("matching_sent_count_after_send") != 1
        or mailbox.get("matching_current_draft_count_after_send") != 0
        or mailbox.get("post_send_sent_copy_verified") is not True
        or mailbox.get("post_send_automatic_reply_observed") is not True
        or mailbox.get("gmail_identifiers_omitted") is not True
        or mailbox.get("message_body_omitted") is not True
        or any(
            not is_sha256(dispatch.get(field))
            for field in (
                "recipient_route_sha256",
                "subject_sha256",
                "body_sha256",
                "attachment_sha256",
            )
        )
        or dispatch.get("attachment_count") != 1
        or dispatch.get("attachment_bytes") != 730579
        or dispatch.get("cc_count") != 0
        or dispatch.get("bcc_count") != 0
        or controls.get("single_send_only") is not True
        or controls.get("duplicate_send_prohibited") is not True
        or controls.get("sent_copy_verified") is not True
        or controls.get("automatic_reply_is_not_a_request_to_resend")
        is not True
        or controls.get("private_cover_values_omitted") is not True
        or controls.get("public_repository_link_included") is not False
        or controls.get("external_action_performed") is not True
    ):
        raise ValueError(
            "Argos Government submission status is missing or unsafe"
        )
    if not (
        str(authorization.get("binding_generated_utc") or "")
        <= str(mailbox.get("sent_utc") or "")
        <= str(authorization.get("binding_expires_utc") or "")
    ):
        raise ValueError("Argos Government send fell outside its approval binding")
    if str(mailbox.get("sent_utc") or "") >= str(
        opportunity.get("government_deadline_utc") or ""
    ):
        raise ValueError("Argos Government send missed the official deadline")
    return state


def validate_lvlup_application_review_status_response(
    response_state: dict[str, Any],
) -> dict[str, Any]:
    source = response_state.get("source", {})
    evidence = response_state.get("evidence", {})
    action = response_state.get("action", {})
    if (
        response_state.get("schema")
        != "lumencore.lvlup_application_review_status_response_state.v1"
        or response_state.get("status")
        != "APPLICATION_ACTIVE_COMMITTEE_REVIEW_NO_ADDITIONAL_MATERIALS"
        or response_state.get("lane_id") != "lvlup_application_review_status"
        or response_state.get("as_of_utc") != source.get("received_utc")
        or source.get("sender_address_omitted") is not True
        or source.get("message_body_omitted") is not True
        or source.get("full_thread_read") is not True
        or source.get("thread_truncated") is not False
        or source.get("subject_sha256")
        != sha256_text(str(source.get("subject") or ""))
        or not is_sha256(source.get("gmail_message_id_sha256"))
        or not is_sha256(source.get("gmail_thread_id_sha256"))
        or evidence.get("application_active") is not True
        or evidence.get("application_remains_under_review") is not True
        or evidence.get("investment_committee_review_reported") is not True
        or evidence.get("additional_materials_requested") is not False
        or evidence.get("decision_or_timing_commitment_observed") is not False
        or action.get("deadline") is not None
        or action.get("email_reply_required") is not False
        or action.get("send_now") is not False
        or action.get("selected_template_id") != "NO_DUPLICATE_MONITOR"
        or action.get("duplicate_send_decision")
        != "BLOCK_FURTHER_PROACTIVE_STATUS_EMAIL"
    ):
        raise ValueError(
            "LvlUp application-review status response is missing or stale"
        )
    return action


def validate_third_sphere_outreach_send_state(
    outreach_state: dict[str, Any],
) -> dict[str, Any]:
    receipt = outreach_state.get("receipt", {})
    hash_fields = (
        "recipient_route_sha256",
        "subject_sha256",
        "body_sha256",
        "gmail_message_id_sha256",
        "gmail_thread_id_sha256",
        "sent_message_receipt_sha256",
    )
    count_fields = ("attachment_count", "cc_count", "bcc_count")
    canonical = "|".join(
        [
            str(receipt.get("lane_id") or ""),
            str(receipt.get("template_id") or ""),
            str(receipt.get("sent_utc") or ""),
            str(receipt.get("recipient_route_sha256") or ""),
            str(receipt.get("subject_sha256") or ""),
            str(receipt.get("body_sha256") or ""),
            str(receipt.get("gmail_message_id_sha256") or ""),
            str(receipt.get("gmail_thread_id_sha256") or ""),
            str(receipt.get("attachment_count")),
            str(receipt.get("cc_count")),
            str(receipt.get("bcc_count")),
        ]
    )
    controls = outreach_state.get("controls", {})
    if (
        outreach_state.get("schema")
        != "lumencore.third_sphere_seedstrap_outreach_send_state.v1"
        or outreach_state.get("status")
        != "INITIAL_PUBLIC_SAFE_REVIEW_REQUEST_SENT_MONITOR_ONLY"
        or controls.get("do_not_repeat_without_substantive_inbound") is not True
        or controls.get("private_message_and_thread_identifiers_omitted")
        is not True
        or controls.get("recipient_address_omitted") is not True
        or controls.get("subject_and_body_omitted") is not True
        or receipt.get("delivery_state") != "SENT"
        or receipt.get("lane_id") != "third_sphere_seedstrap_direct_review"
        or receipt.get("template_id") != "DIRECT_INVESTOR_REVIEW_REQUEST"
        or receipt.get("sent_utc") != outreach_state.get("as_of_utc")
        or any(not is_sha256(receipt.get(field)) for field in hash_fields)
        or any(receipt.get(field) != 0 for field in count_fields)
        or controls.get("attachment_count") != receipt.get("attachment_count")
        or controls.get("cc_count") != receipt.get("cc_count")
        or receipt.get("sent_message_receipt_sha256") != sha256_text(canonical)
    ):
        raise ValueError("Third Sphere outreach send state is missing or stale")
    return receipt


def validate_outreach_draft_quarantine_state(
    quarantine_state: dict[str, Any],
) -> list[dict[str, Any]]:
    controls = quarantine_state.get("controls", {})
    drafts = quarantine_state.get("drafts", [])
    expected_conflicts = {
        "terry_vynetic_followup": "PROACTIVE_FOLLOWUP_LIMIT_EXHAUSTED",
    }
    required_draft_fields = {
        "conflict_type",
        "detected_utc",
        "draft_body_omitted",
        "draft_label_confirmed",
        "gmail_draft_deleted",
        "gmail_draft_id_sha256",
        "gmail_thread_id_sha256",
        "lane_id",
        "meeting_details_omitted",
        "recipient_route_omitted",
        "safest_next_action",
        "selected_template_id",
        "send_now",
        "subject_sha256",
    }
    if (
        quarantine_state.get("schema")
        != "lumencore.outreach_draft_quarantine_state.v1"
        or quarantine_state.get("status")
        != "CONFLICTING_GMAIL_DRAFTS_QUARANTINED_NO_SEND"
        or quarantine_state.get("draft_count") != len(drafts)
        or quarantine_state.get("lane_count") != len(expected_conflicts)
        or len(drafts) != len(expected_conflicts)
        or controls.get("conflicting_drafts_fail_closed") is not True
        or controls.get("draft_deletion_performed") is not False
        or controls.get("meeting_credentials_omitted") is not True
        or controls.get("message_bodies_omitted") is not True
        or controls.get("raw_draft_ids_omitted") is not True
        or controls.get("raw_thread_ids_omitted") is not True
        or controls.get("recipient_routes_omitted") is not True
    ):
        raise ValueError("Outreach draft quarantine state is missing or unsafe")
    lane_ids = [row.get("lane_id") for row in drafts]
    if set(lane_ids) != set(expected_conflicts) or len(lane_ids) != len(
        set(lane_ids)
    ):
        raise ValueError("Outreach draft quarantine lane coverage is invalid")
    for row in drafts:
        if (
            set(row) != required_draft_fields
            or row.get("conflict_type")
            != expected_conflicts.get(row.get("lane_id"))
            or row.get("draft_body_omitted") is not True
            or row.get("draft_label_confirmed") is not True
            or row.get("gmail_draft_deleted") is not False
            or row.get("meeting_details_omitted") is not True
            or row.get("recipient_route_omitted") is not True
            or row.get("selected_template_id") != "NO_DUPLICATE_MONITOR"
            or row.get("send_now") is not False
            or not isinstance(row.get("detected_utc"), str)
            or not row["detected_utc"].endswith("Z")
            or not isinstance(row.get("safest_next_action"), str)
            or not row["safest_next_action"].strip()
            or any(
                not is_sha256(row.get(field))
                for field in (
                    "gmail_draft_id_sha256",
                    "gmail_thread_id_sha256",
                    "subject_sha256",
                )
            )
        ):
            raise ValueError("Outreach draft quarantine entry is missing or unsafe")
    if len({row["gmail_draft_id_sha256"] for row in drafts}) != len(drafts):
        raise ValueError("Outreach draft quarantine contains a duplicate draft")
    return drafts


def validate_official_inbound_status_event_register(
    register: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    expected = {
        "epri_open_power_ai_mou": (
            "ONBOARDING_RESPONSE_SENT_MRC_INVITE_RECEIVED_LOGO_FILES_PENDING",
            "REQUESTED_ASSET_DELIVERY_REPLY",
            "DO_NOT_REPEAT_CONTACT_WORKGROUP_OR_PERMISSION_FACTS",
        ),
        "pathway_working_capital_inquiry": (
            "OFFICIAL_PORTAL_ROUTE_PROVIDED_FOUNDER_REVIEW_REQUIRED",
            "NO_DUPLICATE_MONITOR",
            "DO_NOT_REPLY_TO_REPEAT_THE_INQUIRY",
        ),
        "darpa_dice_abstract_status": (
            "FULL_PROPOSAL_DISCOURAGED_ROUTE_CLOSED",
            "NO_DUPLICATE_MONITOR",
            "CLOSE_WITHOUT_REPLY_OR_FULL_PROPOSAL",
        ),
        "dhs_rfi_correction": (
            "CORRECTION_REQUEST_RECEIVED_CORRECTED_RESPONSE_SENT_MONITOR_ONLY",
            "NO_DUPLICATE_MONITOR",
            "DO_NOT_REPEAT_THE_CORRECTED_RESPONSE",
        ),
        "nashville_ec_takeoff_fall_2026": (
            "COHORT_SELECTED_ONBOARDING_AND_PARTICIPATION_AGREEMENT_DUE",
            "NO_DUPLICATE_MONITOR",
            "THANK_YOU_ALREADY_SENT_DO_NOT_REPEAT",
        ),
        "tsa_industry_portal_capability": (
            "OFFICIAL_INDUSTRY_PORTAL_ROUTE_PROVIDED",
            "NO_DUPLICATE_MONITOR",
            "DO_NOT_REPEAT_EMAIL_OUTREACH_USE_PORTAL",
        ),
        "dla_amps_application_access": (
            "ACCOUNT_CREATED_EXACT_ROLE_NOT_YET_VERIFIED",
            "NO_DUPLICATE_MONITOR",
            "DO_NOT_REQUEST_AN_UNKNOWN_ROLE",
        ),
        "login_gov_new_device_signin": (
            "NEW_DEVICE_SIGNIN_REQUIRES_USER_RECOGNITION",
            "NO_DUPLICATE_MONITOR",
            "NO_EMAIL_REPLY_VERIFY_ACCOUNT_DIRECTLY",
        ),
        "dla_dsip_topic_status": (
            "OFFICIAL_DLA_CONFIRMED_PROPOSAL_IN_PROGRESS_NOT_SUBMITTED",
            "NO_DUPLICATE_MONITOR",
            "CLOSE_NOT_SUBMITTED_DO_NOT_RESEND",
        ),
        "epri_open_power_ai_mou_completed": (
            "MOU_COMPLETED_BY_ALL_PARTIES_PRIVATE_CUSTODY_REQUIRED",
            "NO_DUPLICATE_MONITOR",
            "DO_NOT_SEND_A_COMPLETION_REPLY_UNLESS_EPRI_REQUESTS_ONE",
        ),
        "nashville_ec_accelerator_info_sessions": (
            "UPDATED_PAYMENT_ROUTE_AND_OPTIONAL_INFO_SESSIONS_AVAILABLE",
            "NO_DUPLICATE_MONITOR",
            "DO_NOT_REPLY_OR_TREAT_OPTIONAL_SESSION_AS_REQUIRED",
        ),
        "argos_government_automatic_reply": (
            "AUTOMATIC_OUT_OF_OFFICE_REPLY_OBSERVED_DELIVERY_ONLY_NO_DUPLICATE",
            "NO_DUPLICATE_MONITOR",
            "DO_NOT_REPLY_TO_THE_AUTOMATIC_MESSAGE_OR_RESEND_THE_ARGOS_PACKET",
        ),
    }
    controls = register.get("controls", {})
    events = register.get("events", [])
    if (
        register.get("schema")
        != "lumencore.official_inbound_status_event_register.v1"
        or register.get("status") != "TWELVE_OFFICIAL_EVENTS_RECONCILED_NO_SEND"
        or register.get("event_count") != len(events)
        or len(events) != len(expected)
        or controls.get("action_time_human_review_required") is not True
        or controls.get("builder_can_send_email") is not False
        or controls.get("message_bodies_omitted") is not True
        or controls.get("meeting_credentials_omitted") is not True
        or controls.get("private_mail_identifiers_omitted") is not True
        or controls.get("recipient_and_sender_addresses_omitted") is not True
        or controls.get("patent_sensitive_contents_omitted") is not True
        or controls.get("assessment_and_project_contents_omitted") is not True
    ):
        raise ValueError("Official inbound status event register is missing or unsafe")
    by_lane = {row.get("lane_id"): row for row in events}
    if set(by_lane) != set(expected) or len(by_lane) != len(events):
        raise ValueError("Official inbound status event coverage is invalid")
    for lane_id, row in by_lane.items():
        source = row.get("source", {})
        action = row.get("action", {})
        status, template_id, duplicate_decision = expected[lane_id]
        if (
            row.get("status") != status
            or source.get("subject_sha256")
            != sha256_text(str(source.get("subject") or ""))
            or source.get("sender_address_omitted") is not True
            or source.get("message_body_omitted") is not True
            or source.get("private_mail_identifiers_omitted") is not True
            or source.get("full_thread_read") is not True
            or source.get("thread_truncated") is not False
            or not isinstance(source.get("received_utc"), str)
            or not source["received_utc"].endswith("Z")
            or action.get("email_reply_required") is not False
            or action.get("send_now") is not False
            or action.get("selected_template_id") != template_id
            or action.get("duplicate_send_decision") != duplicate_decision
            or not isinstance(action.get("key_ask"), str)
            or not action["key_ask"].strip()
            or not isinstance(action.get("missing_facts"), list)
            or not isinstance(action.get("safest_next_action"), str)
            or not action["safest_next_action"].strip()
        ):
            raise ValueError(
                f"Official inbound status event is missing or stale: {lane_id}"
            )
        deadline = action.get("deadline")
        if lane_id == "nashville_ec_takeoff_fall_2026":
            if deadline != {
                "onboarding_form_and_participation_agreement_date": "2026-07-31",
                "deposit_date": "2026-08-14",
                "time_and_timezone_explicit": False,
            }:
                raise ValueError("Nashville onboarding deadlines are missing or stale")
        elif lane_id == "nashville_ec_accelerator_info_sessions":
            if deadline != {
                "onboarding_form_date": "2026-07-31",
                "time_and_timezone_explicit": False,
            }:
                raise ValueError(
                    "Nashville information-session deadline is missing or stale"
                )
        elif deadline is not None:
            raise ValueError(
                f"Unexpected official-event deadline present: {lane_id}"
            )
    epri = by_lane["epri_open_power_ai_mou"]
    epri_evidence = epri["evidence"]
    if (
        epri_evidence.get("primary_contact_requested") is not True
        or epri_evidence.get("work_group_representatives_requested") is not True
        or epri_evidence.get("logo_permission_requested") is not True
        or epri_evidence.get("light_and_dark_png_logos_requested") is not True
        or epri_evidence.get("primary_contact_sent") is not True
        or epri_evidence.get("work_group_representatives_sent") is not True
        or epri_evidence.get("logo_permission_sent") is not True
        or epri_evidence.get("logo_files_sent") is not False
        or epri_evidence.get("meeting_credentials_omitted") is not True
        or not str(epri_evidence.get("onboarding_response_sent_utc") or "").endswith(
            "Z"
        )
        or not str(epri_evidence.get("mrc_invite_received_utc") or "").endswith("Z")
    ):
        raise ValueError("EPRI onboarding event is missing or stale")
    if by_lane["pathway_working_capital_inquiry"]["evidence"].get(
        "application_submitted"
    ) is not False:
        raise ValueError("Pathway portal state is missing or stale")
    if by_lane["darpa_dice_abstract_status"]["evidence"].get(
        "full_proposal_encouraged"
    ) is not False:
        raise ValueError("DARPA DICE closure state is missing or stale")
    if by_lane["dhs_rfi_correction"]["evidence"].get(
        "corrected_response_sent"
    ) is not True:
        raise ValueError("DHS correction state is missing or stale")
    nashville_evidence = by_lane["nashville_ec_takeoff_fall_2026"]["evidence"]
    if (
        nashville_evidence.get("cohort_selected") is not True
        or nashville_evidence.get("financial_assistance_reported") is not True
        or nashville_evidence.get("financial_assistance_amount_usd") != 375
        or nashville_evidence.get("full_program_investment_usd") != 500
        or nashville_evidence.get("discount_code_omitted") is not True
        or not str(
            nashville_evidence.get("thank_you_and_acceptance_sent_utc") or ""
        ).endswith("Z")
        or nashville_evidence.get("onboarding_form_completed") is not False
        or nashville_evidence.get("participation_agreement_accepted") is not False
        or nashville_evidence.get("deposit_submitted") is not False
    ):
        raise ValueError("Nashville cohort onboarding event is missing or stale")
    tsa_evidence = by_lane["tsa_industry_portal_capability"]["evidence"]
    if (
        tsa_evidence.get("official_industry_portal_route_provided") is not True
        or tsa_evidence.get("capability_meeting_request_must_use_portal") is not True
        or not str(tsa_evidence.get("acknowledgment_sent_utc") or "").endswith("Z")
        or tsa_evidence.get("portal_submission_completed") is not False
    ):
        raise ValueError("TSA Industry Portal event is missing or stale")
    amps_evidence = by_lane["dla_amps_application_access"]["evidence"]
    if (
        amps_evidence.get("account_created") is not True
        or amps_evidence.get("account_identifier_omitted") is not True
        or amps_evidence.get("exact_application_verified") is not False
        or amps_evidence.get("exact_role_verified") is not False
        or amps_evidence.get("role_request_submitted") is not False
    ):
        raise ValueError("DLA AMPS access event is missing or stale")
    login_evidence = by_lane["login_gov_new_device_signin"]["evidence"]
    if (
        login_evidence.get("new_device_signin_reported") is not True
        or login_evidence.get("recognized_by_user") is not False
        or login_evidence.get("email_security_link_and_token_omitted") is not True
        or not str(login_evidence.get("signin_local_timestamp") or "").endswith(
            "-04:00"
        )
    ):
        raise ValueError("Login.gov security event is missing or stale")
    dsip_evidence = by_lane["dla_dsip_topic_status"]["evidence"]
    if (
        dsip_evidence.get("official_status_route_provided") is not True
        or dsip_evidence.get("past_proposals_tab_named") is not True
        or dsip_evidence.get("official_portal_status_observed") is not True
        or dsip_evidence.get("portal_status") != "IN_PROGRESS"
        or dsip_evidence.get("portal_snapshot_reported") is not True
        or dsip_evidence.get("portal_snapshot_omitted") is not True
        or dsip_evidence.get("formally_submitted") is not False
        or dsip_evidence.get("submission_receipt_observed") is not False
        or dsip_evidence.get("deadline_elapsed") is not True
        or dsip_evidence.get("founder_portal_recheck_required") is not False
    ):
        raise ValueError("DLA DSIP status event is missing or stale")
    epri_completion_evidence = by_lane[
        "epri_open_power_ai_mou_completed"
    ]["evidence"]
    if (
        epri_completion_evidence.get("all_parties_completed") is not True
        or epri_completion_evidence.get("completed_document_attached") is not True
        or epri_completion_evidence.get("document_contents_omitted") is not True
        or epri_completion_evidence.get("private_signing_identifiers_omitted")
        is not True
        or epri_completion_evidence.get("onboarding_obligations_reviewed")
        is not False
    ):
        raise ValueError("EPRI completion event is missing or stale")
    nashville_info_evidence = by_lane[
        "nashville_ec_accelerator_info_sessions"
    ]["evidence"]
    if (
        nashville_info_evidence.get("fall_cohort_preparation_confirmed")
        is not True
        or nashville_info_evidence.get("prior_payment_link_invalidated")
        is not True
        or nashville_info_evidence.get("updated_takeoff_payment_route_provided")
        is not True
        or nashville_info_evidence.get("payment_link_omitted") is not True
        or nashville_info_evidence.get("deposit_deadline_date")
        != "2026-08-14"
        or nashville_info_evidence.get("deposit_deadline_time_explicit")
        is not False
        or nashville_info_evidence.get("optional_info_sessions_offered")
        is not True
        or nashville_info_evidence.get("session_count") != 3
        or nashville_info_evidence.get("session_times_present") is not True
        or nashville_info_evidence.get("session_timezone_explicit") is not False
        or nashville_info_evidence.get("session_links_omitted") is not True
        or nashville_info_evidence.get("attendance_required") is not False
        or nashville_info_evidence.get("onboarding_deadline_date")
        != "2026-07-31"
        or nashville_info_evidence.get("onboarding_deadline_time_explicit")
        is not False
        or nashville_info_evidence.get("onboarding_form_submitted") is not False
    ):
        raise ValueError("Nashville information-session event is missing or stale")
    argos_auto_reply = by_lane["argos_government_automatic_reply"]["evidence"]
    if (
        argos_auto_reply.get("automatic_reply") is not True
        or argos_auto_reply.get("delivery_evidence_only") is not True
        or argos_auto_reply.get("substantive_acknowledgment") is not False
        or argos_auto_reply.get("acceptance_or_award") is not False
        or argos_auto_reply.get("emails_not_forwarded_while_away") is not True
        or argos_auto_reply.get("out_of_office_end_date") != "2026-07-29"
        or argos_auto_reply.get("out_of_office_end_time_explicit") is not False
    ):
        raise ValueError("Argos automatic-reply event is missing or stale")
    return by_lane


def build_payload() -> dict[str, Any]:
    nashville = read_json(NASHVILLE_OFFICIAL_DEADLINE_CONFIRMATION)
    nashville_submission = read_json(NASHVILLE_SUBMISSION_RECEIPT)
    epri_signing = read_json(EPRI_MOU_SIGNING_STATE)
    epri_logo_send = validate_epri_logo_response_send_status(
        read_json(EPRI_LOGO_RESPONSE_SEND_STATUS)
    )
    lvlup = read_json(LVLUP_REVIEW_CONFIRMATION)
    lvlup_outreach = read_json(LVLUP_OUTREACH_SEND_STATE)
    lvlup_application_response = read_json(
        LVLUP_APPLICATION_REVIEW_STATUS_RESPONSE_STATE
    )
    third_sphere_outreach = read_json(THIRD_SPHERE_OUTREACH_SEND_STATE)
    darpa = read_json(DARPA_SN_26_97_RECEIPT)
    missionweave = read_json(MISSIONWEAVE_ACTION_GATE)
    dla_dsip_non_submission = validate_dla_dsip_non_submission_receipt(
        read_json(DLA_DSIP_NON_SUBMISSION_RECEIPT)
    )
    build_week = read_json(OPENAI_BUILD_WEEK_READINESS)
    build_week_handoff = read_json(OPENAI_BUILD_WEEK_HANDOFF_CONTROL)
    response_registry = read_json(OUTREACH_RESPONSE_TEMPLATE_REGISTRY)
    followup_config = read_json(OUTREACH_FOLLOWUP_POLICY_CONFIG)
    nccu_closure = read_json(NCCU_PATENT_CLINIC_ROUTE_CLOSURE)
    uspto_routing = read_json(USPTO_DOCUMENT_SERVICES_ROUTING_RESPONSE)
    draft_quarantine = read_json(OUTREACH_DRAFT_QUARANTINE_STATE)
    official_events = read_json(OFFICIAL_INBOUND_STATUS_EVENT_REGISTER)
    argos_state = validate_argos_partner_outreach_status(
        read_json(ARGOS_PARTNER_OUTREACH_STATUS)
    )
    argos_government = validate_argos_government_submission_status(
        read_json(ARGOS_GOVERNMENT_SUBMISSION_STATUS)
    )
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
        epri_signing.get("schema")
        != "lumencore.epri_open_power_ai_mou_signing_state.v1"
        or epri_signing.get("status")
        != "USER_SIGNATURE_REPORTED_COMPLETION_CONFIRMATION_PENDING"
        or epri_signing.get("evidence", {}).get("user_reported_signing_complete")
        is not True
        or epri_signing.get("evidence", {}).get(
            "post_sign_finish_screen_observed"
        )
        is not True
        or epri_signing.get("controls", {}).get("do_not_duplicate_signature")
        is not True
    ):
        raise ValueError("EPRI MOU signing state is missing or stale")
    if (
        lvlup.get("schema")
        != "lumencore.lvlup_independent_review_confirmation.v1"
        or lvlup.get("status")
        != "WRITTEN_NO_SPONSOR_SPEND_INDEPENDENT_REVIEW_CONFIRMED"
    ):
        raise ValueError("LvlUp independent-review confirmation is missing or stale")
    if (
        lvlup_outreach.get("schema") != "lumencore.lvlup_outreach_send_state.v1"
        or lvlup_outreach.get("status")
        != "TWO_BOUNDED_FOLLOWUPS_SENT_MONITOR_ONLY"
        or lvlup_outreach.get("controls", {}).get(
            "do_not_repeat_without_substantive_inbound"
        )
        is not True
        or len(lvlup_outreach.get("receipts", [])) != 2
    ):
        raise ValueError("LvlUp outreach send state is missing or stale")
    expected_lvlup_receipts = {
        (
            "lvlup_warm_investor_intro",
            "WARM_INVESTOR_INTRO_REQUEST",
        ),
        (
            "lvlup_application_review_status",
            "FUNDING_REVIEW_STATUS_CHECK",
        ),
    }
    actual_lvlup_receipts = {
        (row.get("lane_id"), row.get("template_id"))
        for row in lvlup_outreach.get("receipts", [])
        if row.get("delivery_state") == "SENT"
    }
    if actual_lvlup_receipts != expected_lvlup_receipts:
        raise ValueError("LvlUp outreach receipts are incomplete or mismatched")
    lvlup_application_action = (
        validate_lvlup_application_review_status_response(
            lvlup_application_response
        )
    )
    third_sphere_receipt = validate_third_sphere_outreach_send_state(
        third_sphere_outreach
    )
    quarantined_drafts = validate_outreach_draft_quarantine_state(
        draft_quarantine
    )
    official_events_by_lane = validate_official_inbound_status_event_register(
        official_events
    )
    dsip_event = official_events_by_lane["dla_dsip_topic_status"]
    if (
        dsip_event.get("status") != dla_dsip_non_submission.get("status")
        or dsip_event.get("source", {}).get("received_utc")
        != dla_dsip_non_submission.get("source", {}).get("received_utc")
        or dsip_event.get("source", {}).get("subject_sha256")
        != dla_dsip_non_submission.get("source", {}).get("subject_sha256")
        or dsip_event.get("evidence", {}).get("portal_status")
        != dla_dsip_non_submission.get("evidence", {}).get("portal_status")
        or dsip_event.get("evidence", {}).get("formally_submitted")
        != dla_dsip_non_submission.get("evidence", {}).get("formally_submitted")
        or dsip_event.get("action", {}).get("duplicate_send_decision")
        != dla_dsip_non_submission.get("action", {}).get(
            "duplicate_send_decision"
        )
    ):
        raise ValueError("DLA DSIP official status sources disagree")
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
    if (
        response_registry.get("schema")
        != "lumencore.outreach_response_template_registry.v1"
        or response_registry.get("controls", {}).get("builder_can_send_email") is not False
        or response_registry.get("controls", {}).get("duplicate_send_fail_closed") is not True
    ):
        raise ValueError("Outreach response template registry is missing or unsafe")
    if (
        nccu_closure.get("schema")
        != "lumencore.patent_clinic_route_closure_state.v1"
        or nccu_closure.get("state")
        != "SERVICE_UNAVAILABLE_SUMMER_AND_UPCOMING_DEADLINE_ROUTE_CLOSED"
        or nccu_closure.get("send_now") is not False
        or nccu_closure.get("duplicate_send_decision") != "CLOSE_WITHOUT_REPLY"
    ):
        raise ValueError("NCCU patent-clinic closure state is missing or stale")
    if (
        uspto_routing.get("schema")
        != "lumencore.uspto_document_services_routing_response_state.v1"
        or uspto_routing.get("state")
        != "OFFICIAL_COPY_PORTAL_ROUTE_PROVIDED_SCOPE_UNCONFIRMED"
        or uspto_routing.get("send_now") is not False
        or uspto_routing.get("duplicate_send_decision")
        != "DO_NOT_REPLY_OR_REPEAT_THE_EMAIL_REQUEST"
    ):
        raise ValueError("USPTO document-services routing state is missing or stale")
    response_template_ids = {
        row.get("template_id") for row in response_registry.get("templates", [])
    }
    if "NO_DUPLICATE_MONITOR" not in response_template_ids:
        raise ValueError("No-duplicate response template is unavailable")
    if "INITIAL_PARTNER_TEAMING_INQUIRY" not in response_template_ids:
        raise ValueError("Initial partner-teaming response template is unavailable")
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

    epri_event = official_events_by_lane["epri_open_power_ai_mou"]
    epri_completion_event = official_events_by_lane[
        "epri_open_power_ai_mou_completed"
    ]
    pathway_event = official_events_by_lane["pathway_working_capital_inquiry"]
    dice_event = official_events_by_lane["darpa_dice_abstract_status"]
    dhs_event = official_events_by_lane["dhs_rfi_correction"]
    nashville_event = official_events_by_lane[
        "nashville_ec_takeoff_fall_2026"
    ]
    tsa_event = official_events_by_lane["tsa_industry_portal_capability"]
    amps_event = official_events_by_lane["dla_amps_application_access"]
    login_event = official_events_by_lane["login_gov_new_device_signin"]
    dsip_status_event = official_events_by_lane["dla_dsip_topic_status"]
    nashville_info_event = official_events_by_lane[
        "nashville_ec_accelerator_info_sessions"
    ]

    lanes = [
        {
            "lane_id": "argos_emi_teaming_inquiry",
            "organization": argos_state["recipient_route"]["organization"],
            "latest_event_type": (
                "SENT_ONCE_POST_SEND_VERIFIED"
                if argos_state["status"]
                == "SENT_ONCE_POST_SEND_VERIFIED_WAITING_FOR_REPLY"
                else "CURRENT_DRAFT_ONLY_APPROVAL_BINDING_EXPIRED"
            ),
            "latest_event_utc": argos_state["recorded_utc"],
            "state": argos_state["status"],
            "government_deadline_utc": argos_state["opportunity"][
                "government_deadline_utc"
            ],
            "government_deadline_timezone": argos_state["opportunity"][
                "government_deadline_timezone"
            ],
            "partner_interest_target_utc": argos_state["opportunity"][
                "partner_interest_target_utc"
            ],
            "current_draft_count": argos_state["mailbox_observation"][
                "matching_current_draft_count"
            ],
            "matching_sent_count": argos_state["mailbox_observation"][
                "matching_sent_count"
            ],
            "matching_inbound_count": argos_state["mailbox_observation"][
                "matching_inbound_count"
            ],
            "prior_approval_binding_expired": argos_state["prior_binding"][
                "expired_at_record_time"
            ],
            "attachment_count": argos_state["mailbox_observation"][
                "attachment_count"
            ],
            "government_response_state": argos_government["status"],
            "government_response_sent": True,
            "government_sent_utc": argos_government["mailbox_observation"][
                "sent_utc"
            ],
            "government_sent_before_deadline": True,
            "government_attachment_count": argos_government["dispatch"][
                "attachment_count"
            ],
            "government_post_send_automatic_reply_observed": (
                argos_government["mailbox_observation"][
                    "post_send_automatic_reply_observed"
                ]
            ),
            "government_automatic_reply_requires_resend": False,
            "deadline_action_required": (
                argos_state["status"]
                == "DRAFT_ONLY_APPROVAL_EXPIRED_DEADLINE_OPEN"
            ),
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": (
                argos_state["status"]
                == "SENT_ONCE_POST_SEND_VERIFIED_WAITING_FOR_REPLY"
            ),
            "duplicate_send_prohibited": True,
            "next_action": (
                "Do not resend either the EMI teaming inquiry or the Government "
                "response. The Government response was sent once before the July 30 "
                "deadline and its sent copy was verified. Treat the out-of-office "
                "notice as informational only; monitor for a substantive reply."
            ),
        },
        {
            "lane_id": "nashville_ec_takeoff_fall_2026",
            "organization": "Nashville Entrepreneur Center",
            "latest_event_type": "UPDATED_PAYMENT_AND_INFO_SESSION_ROUTES_RECEIVED",
            "latest_event_utc": nashville_info_event["source"]["received_utc"],
            "state": nashville_event["status"],
            "prior_portal_submission_verified": True,
            "cohort_selected": True,
            "financial_assistance_reported": True,
            "financial_assistance_amount_usd": nashville_event["evidence"][
                "financial_assistance_amount_usd"
            ],
            "full_program_investment_usd": nashville_event["evidence"][
                "full_program_investment_usd"
            ],
            "discount_code_omitted": True,
            "thank_you_and_acceptance_sent": True,
            "onboarding_form_completed": False,
            "participation_agreement_accepted": False,
            "deposit_submitted": False,
            "onboarding_deadline_reconfirmed": True,
            "optional_info_sessions_offered": True,
            "optional_info_session_count": nashville_info_event["evidence"][
                "session_count"
            ],
            "optional_info_session_timezone_explicit": nashville_info_event[
                "evidence"
            ]["session_timezone_explicit"],
            "optional_info_session_selected": False,
            "info_session_attendance_required": False,
            "onboarding_form_and_participation_agreement_date": nashville_event[
                "action"
            ]["deadline"]["onboarding_form_and_participation_agreement_date"],
            "deposit_date": nashville_event["action"]["deadline"]["deposit_date"],
            "deadline_time_and_timezone_explicit": nashville_event["action"][
                "deadline"
            ]["time_and_timezone_explicit"],
            "account_action_required": True,
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": (
                "Review and complete the official onboarding form and participation "
                "agreement by July 31. Preserve the corrected TakeOff payment route for "
                "founder-controlled payment by August 14. An information session is "
                "optional; verify its timezone and calendar conflicts before saving one. "
                "Do not accept the agreement, make a payment, or send another acceptance "
                "email automatically."
            ),
        },
        {
            "lane_id": "tsa_industry_portal_capability",
            "organization": "Transportation Security Administration",
            "latest_event_type": "OFFICIAL_INDUSTRY_PORTAL_ROUTE_RECEIVED",
            "latest_event_utc": tsa_event["source"]["received_utc"],
            "state": tsa_event["status"],
            "official_industry_portal_route_provided": True,
            "acknowledgment_sent": True,
            "portal_submission_completed": False,
            "portal_action_required": True,
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": tsa_event["action"]["safest_next_action"],
        },
        {
            "lane_id": "dla_amps_application_access",
            "organization": "Defense Logistics Agency",
            "latest_event_type": "AMPS_ACCOUNT_CREATED_ROLE_REQUEST_NOT_VERIFIED",
            "latest_event_utc": amps_event["source"]["received_utc"],
            "state": amps_event["status"],
            "account_created": True,
            "account_identifier_omitted": True,
            "exact_application_verified": False,
            "exact_role_verified": False,
            "role_request_submitted": False,
            "account_action_required": True,
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": amps_event["action"]["safest_next_action"],
        },
        {
            "lane_id": "login_gov_new_device_signin",
            "organization": "Login.gov",
            "latest_event_type": "NEW_DEVICE_SIGNIN_SECURITY_NOTICE",
            "latest_event_utc": login_event["source"]["received_utc"],
            "state": login_event["status"],
            "new_device_signin_reported": True,
            "recognized_by_user": False,
            "security_link_and_token_omitted": True,
            "account_action_required": True,
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": login_event["action"]["safest_next_action"],
        },
        {
            "lane_id": "epri_open_power_ai_mou",
            "organization": "EPRI Open Power AI Consortium",
            "latest_event_type": "CANONICAL_LOGO_PAIR_SENT_ONCE_POST_SEND_VERIFIED",
            "latest_event_utc": epri_logo_send["mailbox_observation"]["sent_utc"],
            "state": "LOGO_PAIR_SENT_ONCE_POST_SEND_VERIFIED_DO_NOT_RESEND",
            "user_reported_signing_complete": True,
            "post_sign_finish_screen_observed": True,
            "all_parties_completed": True,
            "completed_document_attached": True,
            "completed_document_private_custody_required": True,
            "onboarding_obligations_reviewed": False,
            "onboarding_request_observed": True,
            "onboarding_response_sent": True,
            "mrc_invite_observed": True,
            "primary_contact_sent": True,
            "work_group_representatives_sent": True,
            "logo_permission_sent": True,
            "canonical_logo_files_sent": True,
            "logo_response_post_send_verified": True,
            "logo_response_matching_sent_count": 1,
            "requested_asset_template_id": epri_event["action"][
                "selected_template_id"
            ],
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": (
                epri_logo_send["next_action"]
                + " Keep the completed agreement in private custody and review its "
                "obligations without exposing signing links or private identifiers."
            ),
        },
        {
            "lane_id": "pathway_working_capital_inquiry",
            "organization": "Pathway Lending",
            "latest_event_type": "OFFICIAL_FINANCING_PORTAL_ROUTE_RECEIVED",
            "latest_event_utc": pathway_event["source"]["received_utc"],
            "state": pathway_event["status"],
            "portal_action_required": True,
            "eligibility_verified": False,
            "application_submitted": False,
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": pathway_event["action"]["safest_next_action"],
        },
        {
            "lane_id": "darpa_dice_abstract_status",
            "organization": "DARPA DICE Program",
            "latest_event_type": "OFFICIAL_FULL_PROPOSAL_DISCOURAGED",
            "latest_event_utc": dice_event["source"]["received_utc"],
            "state": dice_event["status"],
            "full_proposal_encouraged": False,
            "reply_requested": False,
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": dice_event["action"]["safest_next_action"],
        },
        {
            "lane_id": "dhs_rfi_correction",
            "organization": "U.S. Department of Homeland Security",
            "latest_event_type": "CORRECTED_RESPONSE_SENT_AFTER_OFFICIAL_REQUEST",
            "latest_event_utc": dhs_event["source"]["received_utc"],
            "state": dhs_event["status"],
            "correction_request_received": True,
            "corrected_response_sent": True,
            "further_reply_requested": False,
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": dhs_event["action"]["safest_next_action"],
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
            "lane_id": "uspto_document_services_copy_route",
            "organization": "USPTO Document Services",
            "latest_event_type": "OFFICIAL_COPY_PORTAL_ROUTE_PROVIDED",
            "latest_event_utc": uspto_routing["official_response_received_utc"],
            "state": uspto_routing["state"],
            "portal_action_required": True,
            "missing_fact_count": len(uspto_routing["missing_facts"]),
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": uspto_routing["next_action"],
        },
        {
            "lane_id": "nccu_ip_clinic_intake",
            "organization": "North Carolina Central University IP Clinic",
            "latest_event_type": "SERVICE_AVAILABILITY_DECLINE_RECEIVED",
            "latest_event_utc": nccu_closure["official_response_received_utc"],
            "state": nccu_closure["state"],
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": nccu_closure["next_action"],
        },
        {
            "lane_id": "lanl_vision_licensing_followup",
            "organization": "Los Alamos National Laboratory",
            "latest_event_type": "SINGLE_BOUNDED_FOLLOWUP_SENT",
            "latest_event_utc": "2026-07-27T13:49:21Z",
            "state": "BOUNDED_FOLLOWUP_SENT_RESPONSE_PENDING_INBOUND_ONLY",
            "follow_up_allowance_consumed": True,
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": (
                "Monitor the existing LANL thread for an inbound reply. The single "
                "bounded follow-up allowance is consumed; do not send again."
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
            "latest_event_type": "OFFICIAL_DSIP_NON_SUBMISSION_CONFIRMED",
            "latest_event_utc": dsip_status_event["source"]["received_utc"],
            "state": dsip_status_event["status"],
            "deadline_utc": missionweave["deadline"]["expected_utc"],
            "open_gate_count": missionweave["gate_summary"]["open_gate_count"],
            "component_poc_included_on_original_message": True,
            "component_reply_observed": True,
            "support_redirect_received": True,
            "official_status_route_provided": True,
            "portal_status_observed": True,
            "portal_status": "IN_PROGRESS",
            "formally_submitted": False,
            "submission_receipt_observed": False,
            "deadline_elapsed": True,
            "portal_action_required": False,
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": dsip_status_event["action"]["safest_next_action"],
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
            "lane_id": "lvlup_warm_investor_intro",
            "organization": "LvlUp Ventures",
            "latest_event_type": "BOUNDED_WARM_INTRO_FOLLOWUP_SENT",
            "latest_event_utc": lvlup_outreach["receipts"][0]["sent_utc"],
            "state": "OUTBOUND_FOLLOWUP_SENT_MONITOR_ONLY",
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": (
                "Monitor the existing thread for a substantive introduction or "
                "question. Do not send another proactive introduction follow-up."
            ),
        },
        {
            "lane_id": "lvlup_application_review_status",
            "organization": "LvlUp Ventures",
            "latest_event_type": "OFFICIAL_APPLICATION_REVIEW_STATUS_RECEIVED",
            "latest_event_utc": lvlup_application_response["as_of_utc"],
            "state": lvlup_application_response["status"],
            "email_reply_required": lvlup_application_action[
                "email_reply_required"
            ],
            "send_now": lvlup_application_action["send_now"],
            "no_send_before": lvlup_application_action["deadline"],
            "do_not_duplicate_send": True,
            "next_action": lvlup_application_action["safest_next_action"],
        },
        {
            "lane_id": "third_sphere_seedstrap_direct_review",
            "organization": "Third Sphere",
            "latest_event_type": "INITIAL_PUBLIC_SAFE_REVIEW_REQUEST_SENT",
            "latest_event_utc": third_sphere_receipt["sent_utc"],
            "state": third_sphere_outreach["status"],
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": third_sphere_outreach["next_action"],
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
            "latest_event_type": "FIRM_FIXED_PRICE_QUOTATION_SENT",
            "latest_event_utc": "2026-07-24T18:13:34Z",
            "state": "FIRM_FIXED_PRICE_QUOTATION_SENT_RESPONSE_PENDING",
            "quotation_sent": True,
            "compliance_verified": False,
            "agency_reply_received": False,
            "email_reply_required": False,
            "send_now": False,
            "no_send_before": None,
            "do_not_duplicate_send": True,
            "next_action": (
                "Monitor the existing thread for an agency clarification or replacement "
                "request. Do not resend the quotation or claim compliance, acceptance, "
                "selection, or award."
            ),
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
        if followup_policy["mode"] in {
            "ONE_BOUNDED_FOLLOW_UP_AFTER_HOLD",
            "ONE_BOUNDED_INITIAL_OUTREACH_BEFORE_DEADLINE",
        }:
            if (
                not followup_policy.get("not_before_utc")
                or followup_policy.get("max_proactive_sends") != 1
                or not eligible_template_id
            ):
                raise ValueError("Bounded proactive-outreach policy is incomplete")
            if followup_policy["mode"] == "ONE_BOUNDED_INITIAL_OUTREACH_BEFORE_DEADLINE":
                if (
                    not followup_policy.get("deadline_utc")
                    or not followup_policy.get("partner_interest_target_utc")
                    or followup_policy["not_before_utc"]
                    >= followup_policy["deadline_utc"]
                    or followup_policy["partner_interest_target_utc"]
                    >= followup_policy["deadline_utc"]
                ):
                    raise ValueError(
                        "Deadline-bound initial-outreach policy is incomplete"
                    )
        elif (
            followup_policy.get("not_before_utc") is not None
            or followup_policy.get("max_proactive_sends") != 0
            or eligible_template_id is not None
        ):
            raise ValueError("Non-proactive follow-up policy contains send authority")
        lane["follow_up_policy"] = followup_policy
        lane["response_template_id"] = (
            "NO_DUPLICATE_MONITOR"
            if lane["do_not_duplicate_send"]
            else (
                eligible_template_id
                if followup_policy["mode"]
                == "ONE_BOUNDED_INITIAL_OUTREACH_BEFORE_DEADLINE"
                else None
            )
        )
    quarantined_by_lane = {
        row["lane_id"]: row for row in quarantined_drafts
    }
    if set(quarantined_by_lane) - lane_ids:
        raise ValueError("Draft quarantine references an unknown outreach lane")
    for lane in lanes:
        conflict = quarantined_by_lane.get(lane["lane_id"])
        lane["conflicting_gmail_draft_count"] = 1 if conflict else 0
        lane["draft_quarantine_status"] = (
            "QUARANTINED_NOT_SENDABLE" if conflict else None
        )
        if conflict:
            lane["quarantined_draft_conflict_type"] = conflict[
                "conflict_type"
            ]
            lane["quarantined_draft_observed_utc"] = conflict[
                "detected_utc"
            ]
            lane["send_now"] = False
            lane["email_reply_required"] = False
            lane["do_not_duplicate_send"] = True
            lane["response_template_id"] = "NO_DUPLICATE_MONITOR"
            lane["next_action"] = conflict["safest_next_action"]
    deadline_action_required_count = sum(
        1 for lane in lanes if lane.get("deadline_action_required") is True
    )
    return {
        "schema": "lumencore.email_action_reconciliation.v1",
        "as_of_date": AS_OF_DATE,
        "status": (
            "DEADLINE_ACTION_DUE_HUMAN_REVIEW"
            if deadline_action_required_count
            else "NO_UNANSWERED_DEADLINE_CRITICAL_EMAIL_ACTION"
        ),
        "evidence_method": (
            "Connected Gmail metadata and relevant-thread reconciliation against sent "
            "receipts and the canonical response register."
        ),
        "search_scope": [
            "Funding, grant, contract, SBIR/STTR, DSIP, NSF, SAM.gov, and Research.gov",
            "Patent routing and Georgia PATENTS",
            "USPTO Document Services copy-route response and NCCU IP Clinic closure",
            "LANL VISION and licensing follow-up",
            "EPRI Open Power AI Consortium onboarding",
            "Pathway Lending working-capital portal routing",
            "DARPA DICE abstract status",
            "DHS RFI correction request and corrected-response state",
            "TSA Industry Portal capability routing",
            "DLA AMPS account creation and application-role verification",
            "Login.gov new-device sign-in security notice",
            "FHWA TSMO qualified-partner outreach",
            "Nashville EC Fall 2026 TakeOff deadline-support query",
            "Nashville EC Fall 2026 TakeOff portal-submission confirmation",
            "Nashville EC cohort selection, onboarding, agreement, and deposit dates",
            "DARPA-SN-26-97 formal RFI response and agency-thread state",
            "MissionWeave DSIP and OpenAI Build Week portal deadlines",
            "OpenAI Build Week self-sent handoff attachment integrity",
            "HHS Project Argos partner-outreach draft, duplicate, and deadline state",
            "CDC, NASA, Army, LvlUp, Terry Anderton, and Vynetic",
        ],
        "summary": {
            "lane_count": len(lanes),
            "email_reply_required_count": sum(
                1 for lane in lanes if lane["email_reply_required"]
            ),
            "send_now_count": sum(1 for lane in lanes if lane["send_now"]),
            "deadline_action_required_count": deadline_action_required_count,
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
            "out_of_office_count": 0,
            "human_account_action_count": sum(
                1
                for lane in lanes
                if lane["follow_up_policy"]["mode"]
                in {"ACCOUNT_ACTION", "PORTAL_ACTION", "PRIVATE_RECONCILIATION"}
            ),
            "external_send_allowed_without_human": False,
            "conflicting_gmail_draft_count": len(quarantined_drafts),
            "conflicting_gmail_draft_lane_count": len(quarantined_by_lane),
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
            "epri_open_power_ai_mou_signing_state": artifact_status(
                EPRI_MOU_SIGNING_STATE
            ),
            "epri_opai_logo_response_send_status": artifact_status(
                EPRI_LOGO_RESPONSE_SEND_STATUS
            ),
            "lvlup_independent_review_confirmation": artifact_status(
                LVLUP_REVIEW_CONFIRMATION
            ),
            "lvlup_outreach_send_state": artifact_status(
                LVLUP_OUTREACH_SEND_STATE
            ),
            "lvlup_application_review_status_response_state": artifact_status(
                LVLUP_APPLICATION_REVIEW_STATUS_RESPONSE_STATE
            ),
            "third_sphere_seedstrap_outreach_send_state": artifact_status(
                THIRD_SPHERE_OUTREACH_SEND_STATE
            ),
            "darpa_sn_26_97_public_submission_receipt": artifact_status(
                DARPA_SN_26_97_RECEIPT
            ),
            "missionweave_dsip_action_gate": artifact_status(
                MISSIONWEAVE_ACTION_GATE
            ),
            "dla_dsip_official_non_submission_receipt": artifact_status(
                DLA_DSIP_NON_SUBMISSION_RECEIPT
            ),
            "openai_build_week_readiness": artifact_status(
                OPENAI_BUILD_WEEK_READINESS
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
            "nccu_patent_clinic_route_closure": artifact_status(
                NCCU_PATENT_CLINIC_ROUTE_CLOSURE
            ),
            "uspto_document_services_routing_response": artifact_status(
                USPTO_DOCUMENT_SERVICES_ROUTING_RESPONSE
            ),
            "outreach_draft_quarantine_state": artifact_status(
                OUTREACH_DRAFT_QUARANTINE_STATE
            ),
            "official_inbound_status_event_register": artifact_status(
                OFFICIAL_INBOUND_STATUS_EVENT_REGISTER
            ),
            "argos_partner_outreach_status": artifact_status(
                ARGOS_PARTNER_OUTREACH_STATUS
            ),
            "argos_government_submission_status": artifact_status(
                ARGOS_GOVERNMENT_SUBMISSION_STATUS
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
    deadline_action_count = payload["summary"].get(
        "deadline_action_required_count"
    )
    expected_status = (
        "DEADLINE_ACTION_DUE_HUMAN_REVIEW"
        if deadline_action_count
        else "NO_UNANSWERED_DEADLINE_CRITICAL_EMAIL_ACTION"
    )
    if payload.get("status") != expected_status:
        raise ValueError("Deadline action reconciliation is incomplete")
    if payload["summary"]["email_reply_required_count"] != 0:
        raise ValueError("A reply-required lane needs separate action review")
    if payload["summary"]["send_now_count"] != 0:
        raise ValueError("A send-now lane needs separate action review")
    quarantined = [
        lane
        for lane in payload["lanes"]
        if lane.get("conflicting_gmail_draft_count")
    ]
    if (
        payload["summary"]["conflicting_gmail_draft_count"] != len(quarantined)
        or payload["summary"]["conflicting_gmail_draft_lane_count"]
        != len(quarantined)
        or any(
            lane.get("draft_quarantine_status") != "QUARANTINED_NOT_SENDABLE"
            or lane.get("send_now") is not False
            or lane.get("email_reply_required") is not False
            or lane.get("response_template_id") != "NO_DUPLICATE_MONITOR"
            for lane in quarantined
        )
    ):
        raise ValueError("Conflicting Gmail draft quarantine is incomplete")
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
    argos = next(
        lane
        for lane in payload["lanes"]
        if lane["lane_id"] == "argos_emi_teaming_inquiry"
    )
    if (
        argos["matching_inbound_count"] != 0
        or argos["prior_approval_binding_expired"] is not True
        or argos["follow_up_policy"]["mode"]
        != "ONE_BOUNDED_INITIAL_OUTREACH_BEFORE_DEADLINE"
        or argos["send_now"] is not False
        or argos["duplicate_send_prohibited"] is not True
    ):
        raise ValueError("Argos deadline control is incomplete")
    if argos["state"] == "DRAFT_ONLY_APPROVAL_EXPIRED_DEADLINE_OPEN":
        if (
            argos["current_draft_count"] != 1
            or argos["matching_sent_count"] != 0
            or argos["deadline_action_required"] is not True
            or argos["do_not_duplicate_send"] is not False
            or argos["response_template_id"]
            != "INITIAL_PARTNER_TEAMING_INQUIRY"
        ):
            raise ValueError("Argos draft-only deadline control is incomplete")
    elif argos["state"] == "SENT_ONCE_POST_SEND_VERIFIED_WAITING_FOR_REPLY":
        if (
            argos["current_draft_count"] != 0
            or argos["matching_sent_count"] != 1
            or argos["deadline_action_required"] is not False
            or argos["do_not_duplicate_send"] is not True
            or argos["response_template_id"] != "NO_DUPLICATE_MONITOR"
        ):
            raise ValueError("Argos post-send duplicate control is incomplete")
    else:
        raise ValueError("Argos state is unknown")
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
    missionweave = next(
        lane
        for lane in payload["lanes"]
        if lane["lane_id"] == "missionweave_dsip_proposal"
    )
    if (
        missionweave["state"]
        != "OFFICIAL_DLA_CONFIRMED_PROPOSAL_IN_PROGRESS_NOT_SUBMITTED"
        or missionweave["latest_event_type"]
        != "OFFICIAL_DSIP_NON_SUBMISSION_CONFIRMED"
        or missionweave["official_status_route_provided"] is not True
        or missionweave["component_reply_observed"] is not True
        or missionweave["portal_status_observed"] is not True
        or missionweave["portal_status"] != "IN_PROGRESS"
        or missionweave["formally_submitted"] is not False
        or missionweave["submission_receipt_observed"] is not False
        or missionweave["deadline_elapsed"] is not True
        or missionweave["portal_action_required"] is not False
        or missionweave["email_reply_required"] is not False
        or missionweave["send_now"] is not False
        or missionweave["do_not_duplicate_send"] is not True
    ):
        raise ValueError("MissionWeave DSIP status routing is incomplete")
    epri = next(
        lane for lane in payload["lanes"] if lane["lane_id"] == "epri_open_power_ai_mou"
    )
    if (
        epri["state"]
        != "LOGO_PAIR_SENT_ONCE_POST_SEND_VERIFIED_DO_NOT_RESEND"
        or epri["latest_event_type"]
        != "CANONICAL_LOGO_PAIR_SENT_ONCE_POST_SEND_VERIFIED"
        or epri["all_parties_completed"] is not True
        or epri["completed_document_attached"] is not True
        or epri["completed_document_private_custody_required"] is not True
        or epri["onboarding_obligations_reviewed"] is not False
        or epri["onboarding_response_sent"] is not True
        or epri["mrc_invite_observed"] is not True
        or epri["canonical_logo_files_sent"] is not True
        or epri["logo_response_post_send_verified"] is not True
        or epri["logo_response_matching_sent_count"] != 1
        or epri["requested_asset_template_id"] != "REQUESTED_ASSET_DELIVERY_REPLY"
        or epri["do_not_duplicate_send"] is not True
    ):
        raise ValueError("EPRI onboarding and requested-asset control is incomplete")
    pathway = next(
        lane
        for lane in payload["lanes"]
        if lane["lane_id"] == "pathway_working_capital_inquiry"
    )
    if (
        pathway["state"]
        != "OFFICIAL_PORTAL_ROUTE_PROVIDED_FOUNDER_REVIEW_REQUIRED"
        or pathway["portal_action_required"] is not True
        or pathway["eligibility_verified"] is not False
        or pathway["application_submitted"] is not False
        or pathway["do_not_duplicate_send"] is not True
    ):
        raise ValueError("Pathway financing portal control is incomplete")
    dice = next(
        lane
        for lane in payload["lanes"]
        if lane["lane_id"] == "darpa_dice_abstract_status"
    )
    if (
        dice["state"] != "FULL_PROPOSAL_DISCOURAGED_ROUTE_CLOSED"
        or dice["full_proposal_encouraged"] is not False
        or dice["reply_requested"] is not False
        or dice["do_not_duplicate_send"] is not True
    ):
        raise ValueError("DARPA DICE closure control is incomplete")
    dhs = next(
        lane for lane in payload["lanes"] if lane["lane_id"] == "dhs_rfi_correction"
    )
    if (
        dhs["state"]
        != "CORRECTION_REQUEST_RECEIVED_CORRECTED_RESPONSE_SENT_MONITOR_ONLY"
        or dhs["correction_request_received"] is not True
        or dhs["corrected_response_sent"] is not True
        or dhs["further_reply_requested"] is not False
        or dhs["do_not_duplicate_send"] is not True
    ):
        raise ValueError("DHS correction duplicate-send control is incomplete")
    nashville = next(
        lane
        for lane in payload["lanes"]
        if lane["lane_id"] == "nashville_ec_takeoff_fall_2026"
    )
    if (
        nashville["state"]
        != "COHORT_SELECTED_ONBOARDING_AND_PARTICIPATION_AGREEMENT_DUE"
        or nashville["prior_portal_submission_verified"] is not True
        or nashville["cohort_selected"] is not True
        or nashville["financial_assistance_amount_usd"] != 375
        or nashville["full_program_investment_usd"] != 500
        or nashville["discount_code_omitted"] is not True
        or nashville["thank_you_and_acceptance_sent"] is not True
        or nashville["onboarding_form_completed"] is not False
        or nashville["participation_agreement_accepted"] is not False
        or nashville["deposit_submitted"] is not False
        or nashville["onboarding_deadline_reconfirmed"] is not True
        or nashville["optional_info_sessions_offered"] is not True
        or nashville["optional_info_session_count"] != 3
        or nashville["optional_info_session_timezone_explicit"] is not False
        or nashville["optional_info_session_selected"] is not False
        or nashville["info_session_attendance_required"] is not False
        or nashville["onboarding_form_and_participation_agreement_date"]
        != "2026-07-31"
        or nashville["deposit_date"] != "2026-08-14"
        or nashville["deadline_time_and_timezone_explicit"] is not False
        or nashville["account_action_required"] is not True
        or nashville["do_not_duplicate_send"] is not True
    ):
        raise ValueError("Nashville EC onboarding control is incomplete")
    tsa = next(
        lane
        for lane in payload["lanes"]
        if lane["lane_id"] == "tsa_industry_portal_capability"
    )
    if (
        tsa["state"] != "OFFICIAL_INDUSTRY_PORTAL_ROUTE_PROVIDED"
        or tsa["official_industry_portal_route_provided"] is not True
        or tsa["acknowledgment_sent"] is not True
        or tsa["portal_submission_completed"] is not False
        or tsa["portal_action_required"] is not True
        or tsa["do_not_duplicate_send"] is not True
    ):
        raise ValueError("TSA Industry Portal control is incomplete")
    amps = next(
        lane
        for lane in payload["lanes"]
        if lane["lane_id"] == "dla_amps_application_access"
    )
    if (
        amps["state"] != "ACCOUNT_CREATED_EXACT_ROLE_NOT_YET_VERIFIED"
        or amps["account_created"] is not True
        or amps["account_identifier_omitted"] is not True
        or amps["exact_application_verified"] is not False
        or amps["exact_role_verified"] is not False
        or amps["role_request_submitted"] is not False
        or amps["account_action_required"] is not True
    ):
        raise ValueError("DLA AMPS role-request control is incomplete")
    login = next(
        lane
        for lane in payload["lanes"]
        if lane["lane_id"] == "login_gov_new_device_signin"
    )
    if (
        login["state"] != "NEW_DEVICE_SIGNIN_REQUIRES_USER_RECOGNITION"
        or login["new_device_signin_reported"] is not True
        or login["recognized_by_user"] is not False
        or login["security_link_and_token_omitted"] is not True
        or login["account_action_required"] is not True
    ):
        raise ValueError("Login.gov security control is incomplete")
    nasa = next(
        lane
        for lane in payload["lanes"]
        if lane["lane_id"] == "nasa_data_center_rfi"
    )
    if (
        nasa["state"] != "FIRM_FIXED_PRICE_QUOTATION_SENT_RESPONSE_PENDING"
        or nasa["quotation_sent"] is not True
        or nasa["compliance_verified"] is not False
        or nasa["agency_reply_received"] is not False
        or nasa["do_not_duplicate_send"] is not True
    ):
        raise ValueError("NASA quotation duplicate-send control is incomplete")
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
        f"- Conflicting Gmail drafts quarantined: `{summary['conflicting_gmail_draft_count']}`",
        f"- Lanes with conflicting drafts: `{summary['conflicting_gmail_draft_lane_count']}`",
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
