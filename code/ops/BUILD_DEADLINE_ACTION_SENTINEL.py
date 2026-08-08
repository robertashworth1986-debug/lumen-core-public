from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "deadline_action_sentinel_v1.json"
DEFAULT_JSON = (
    ROOT
    / "evidence"
    / "opportunity"
    / "deadline_action_sentinel_latest.json"
)
DEFAULT_MARKDOWN = ROOT / "docs" / "DEADLINE_ACTION_SENTINEL.md"

REQUIRED_FALSE_CONTROLS = {
    "autonomous_email_send_allowed",
    "autonomous_portal_action_allowed",
    "autonomous_agreement_acceptance_allowed",
    "autonomous_payment_allowed",
    "autonomous_signature_allowed",
    "autonomous_certification_allowed",
    "authenticated_portal_session_use_allowed",
}
REQUIRED_TRUE_CONTROLS = {
    "read_only_builder",
    "action_time_human_approval_required",
    "unknown_deadline_time_fail_closed",
    "duplicate_recheck_required_before_external_send",
}
REQUIRED_PROHIBITED_ACTIONS = {
    "SEND_EMAIL",
    "OPEN_AUTHENTICATED_PORTAL",
    "CHANGE_PORTAL_ANSWER",
    "UPLOAD_FILE",
    "ACCEPT_AGREEMENT",
    "SIGN",
    "CERTIFY",
    "SUBMIT",
    "PAY",
}
PRIVATE_FIELD_KEYS = {
    "account_number",
    "access_code",
    "discount_code",
    "ein",
    "message_id",
    "password",
    "recipient_email",
    "sender_email",
    "source_message_id",
    "tax_id",
    "thread_id",
    "token",
}
SHA256_HEX_LENGTH = 64
ARGOS_STATUS_SCHEMA = "lumencore.argos_partner_outreach_status.v1"
ARGOS_SENT_ONCE_STATUS = "SENT_ONCE_POST_SEND_VERIFIED_WAITING_FOR_REPLY"
ARGOS_GOVERNMENT_STATUS_SCHEMA = "lumencore.argos_government_response_status.v1"
ARGOS_GOVERNMENT_SENT_ONCE_STATUS = (
    "SENT_ONCE_AUTOMATIC_MAILBOX_ACK_WAITING_FOR_SUBSTANTIVE_REPLY"
)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=True) + "\n"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_repository_file(path_value: Any, label: str) -> tuple[Path, Path]:
    relative_path = Path(str(path_value or ""))
    if not relative_path.as_posix() or relative_path.is_absolute():
        raise ValueError(f"{label} must be a relative repository path")
    source_path = (ROOT / relative_path).resolve()
    try:
        source_path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside the worktree") from exc
    if not source_path.is_file():
        raise ValueError(f"{label} does not exist: {relative_path.as_posix()}")
    return relative_path, source_path


def normalized_sha256(value: Any, label: str) -> str:
    normalized = str(value or "").strip().upper()
    if len(normalized) != SHA256_HEX_LENGTH:
        raise ValueError(f"{label} must be a SHA-256 hex digest")
    try:
        int(normalized, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be a SHA-256 hex digest") from exc
    return normalized


def parse_aware_datetime(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid ISO 8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must include an explicit timezone offset")
    return parsed.astimezone(timezone.utc)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def parse_date(value: str, label: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid YYYY-MM-DD date") from exc


def resolve_field(payload: dict[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"source field not found: {dotted_path}")
        current = current[part]
    return current


def assert_no_private_fields(value: Any, path: str = "config") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key.lower() in PRIVATE_FIELD_KEYS:
                raise ValueError(f"private field is not permitted in sentinel data: {path}.{key}")
            assert_no_private_fields(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            assert_no_private_fields(nested, f"{path}[{index}]")


def argos_outreach_status_receipt(
    binding: dict[str, Any],
    deadline: dict[str, Any],
    gate_relative_path: Path,
    gate_path: Path,
    gate: dict[str, Any],
) -> dict[str, Any]:
    status_relative_path, status_path = resolve_repository_file(
        binding.get("outreach_status_path"),
        "outreach_status_path",
    )
    status = read_json(status_path)
    assert_no_private_fields(status, "outreach_status")
    if status.get("schema") != ARGOS_STATUS_SCHEMA:
        raise ValueError("unexpected Argos outreach status schema")
    if status.get("lane_id") != binding.get("required_lane_id"):
        raise ValueError("Argos outreach status lane changed")
    required_outreach_status = binding.get("required_outreach_status")
    if required_outreach_status != ARGOS_SENT_ONCE_STATUS:
        raise ValueError("Argos required outreach status is not the sent-once state")
    if status.get("status") != required_outreach_status:
        raise ValueError("Argos outreach status is not the required sent-once state")

    recorded_utc = parse_aware_datetime(
        str(status.get("recorded_utc", "")),
        "outreach_status.recorded_utc",
    )
    opportunity = status.get("opportunity")
    mailbox = status.get("mailbox_observation")
    prior_binding = status.get("prior_binding")
    source_control = status.get("source_control")
    controls = status.get("controls")
    submission_opportunity = gate.get("opportunity")
    submission_partner_search = gate.get("partner_search")
    submission_send_gate = gate.get("send_gate")
    required_objects = {
        "outreach_status.opportunity": opportunity,
        "outreach_status.mailbox_observation": mailbox,
        "outreach_status.prior_binding": prior_binding,
        "outreach_status.source_control": source_control,
        "outreach_status.controls": controls,
        "submission_gate.opportunity": submission_opportunity,
        "submission_gate.partner_search": submission_partner_search,
        "submission_gate.send_gate": submission_send_gate,
    }
    for label, value in required_objects.items():
        if not isinstance(value, dict):
            raise ValueError(f"{label} must be an object")

    dispatch_relative_path, dispatch_path = resolve_repository_file(
        source_control.get("public_dispatch_gate_path"),
        "outreach_status.source_control.public_dispatch_gate_path",
    )
    dispatch_gate = read_json(dispatch_path)
    assert_no_private_fields(dispatch_gate, "dispatch_gate")
    dispatch_opportunity = dispatch_gate.get("opportunity")
    dispatch_selection = dispatch_gate.get("template_selection")
    dispatch_message = dispatch_gate.get("message")
    dispatch_controls = dispatch_gate.get("controls")
    for label, value in {
        "dispatch_gate.opportunity": dispatch_opportunity,
        "dispatch_gate.template_selection": dispatch_selection,
        "dispatch_gate.message": dispatch_message,
        "dispatch_gate.controls": dispatch_controls,
    }.items():
        if not isinstance(value, dict):
            raise ValueError(f"{label} must be an object")

    configured_deadline = parse_aware_datetime(
        str(deadline.get("iso_utc", "")),
        "deadline.iso_utc",
    )
    status_deadline = parse_aware_datetime(
        str(opportunity.get("government_deadline_utc", "")),
        "outreach_status.government_deadline_utc",
    )
    submission_deadline = parse_aware_datetime(
        str(submission_opportunity.get("deadline_utc", "")),
        "submission_gate.deadline_utc",
    )
    dispatch_deadline = parse_aware_datetime(
        str(dispatch_opportunity.get("government_deadline_utc", "")),
        "dispatch_gate.government_deadline_utc",
    )
    partner_target = parse_aware_datetime(
        str(opportunity.get("partner_interest_target_utc", "")),
        "outreach_status.partner_interest_target_utc",
    )
    submission_partner_target = parse_aware_datetime(
        str(submission_partner_search.get("primary_partner_interest_target_utc", "")),
        "submission_gate.primary_partner_interest_target_utc",
    )
    dispatch_partner_target = parse_aware_datetime(
        str(dispatch_opportunity.get("partner_interest_target_utc", "")),
        "dispatch_gate.partner_interest_target_utc",
    )
    if not (
        configured_deadline
        == status_deadline
        == submission_deadline
        == dispatch_deadline
        and partner_target
        == submission_partner_target
        == dispatch_partner_target
    ):
        raise ValueError("Argos deadline or partner target changed across sources")
    if not recorded_utc < status_deadline:
        raise ValueError("Argos sent-once status cannot be recorded after the deadline")
    if not partner_target < status_deadline:
        raise ValueError("Argos partner target must precede the Government deadline")

    if mailbox.get("full_mailbox_search_completed") is not True:
        raise ValueError("Argos full-mailbox duplicate search is not recorded")
    expected_counts = {
        "matching_current_draft_count": 0,
        "matching_sent_count": 1,
        "matching_inbound_count": 0,
        "attachment_count": 0,
        "cc_count": 0,
        "bcc_count": 0,
    }
    for field, expected in expected_counts.items():
        value = mailbox.get(field)
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value != expected
        ):
            raise ValueError(f"Argos mailbox count changed: {field}")
    if mailbox.get("current_draft_only") is not False:
        raise ValueError("Argos sent-once receipt cannot remain draft-only")
    for field in (
        "sent_copy_present",
        "gmail_identifiers_omitted",
        "message_body_omitted",
    ):
        if mailbox.get(field) is not True:
            raise ValueError(f"Argos privacy or sent-copy control failed: {field}")
    checked_utc = parse_aware_datetime(
        str(mailbox.get("checked_utc", "")),
        "outreach_status.mailbox_observation.checked_utc",
    )
    sent_utc = parse_aware_datetime(
        str(mailbox.get("sent_utc", "")),
        "outreach_status.mailbox_observation.sent_utc",
    )
    if checked_utc != recorded_utc:
        raise ValueError("Argos mailbox check time must match the status record time")
    if not sent_utc <= checked_utc < status_deadline:
        raise ValueError("Argos sent-copy chronology is invalid")

    subject = str(dispatch_message.get("subject", ""))
    subject_sha256 = hashlib.sha256(subject.encode("utf-8")).hexdigest().upper()
    body_relative_path, body_path = resolve_repository_file(
        dispatch_message.get("body_path"),
        "dispatch_gate.message.body_path",
    )
    body_sha256 = sha256(body_path).upper()
    declared_gate_body_sha256 = normalized_sha256(
        dispatch_message.get("body_sha256"),
        "dispatch_gate.message.body_sha256",
    )
    observed_subject_sha256 = normalized_sha256(
        mailbox.get("subject_sha256"),
        "outreach_status.mailbox_observation.subject_sha256",
    )
    observed_body_sha256 = normalized_sha256(
        mailbox.get("body_sha256"),
        "outreach_status.mailbox_observation.body_sha256",
    )
    if subject_sha256 != observed_subject_sha256:
        raise ValueError("Argos sent subject hash no longer matches the dispatch gate")
    if not body_sha256 == declared_gate_body_sha256 == observed_body_sha256:
        raise ValueError("Argos sent body hash no longer matches the committed source")
    for field in ("attachment_count", "cc_count", "bcc_count"):
        if dispatch_message.get(field) != 0:
            raise ValueError(f"Argos dispatch gate must retain zero {field}")

    selected_template_id = str(source_control.get("selected_template_id", ""))
    if (
        not selected_template_id
        or selected_template_id != dispatch_selection.get("template_id")
    ):
        raise ValueError("Argos selected template changed across sources")
    declared_gate_path = str(source_control.get("public_dispatch_gate_path", ""))
    if declared_gate_path != dispatch_relative_path.as_posix():
        raise ValueError("Argos status points to a different dispatch gate")
    declared_gate_sha256 = normalized_sha256(
        source_control.get("public_dispatch_gate_sha256"),
        "outreach_status.source_control.public_dispatch_gate_sha256",
    )
    if declared_gate_sha256 != sha256(dispatch_path).upper():
        raise ValueError("Argos dispatch gate SHA-256 changed")

    binding_relative_path, binding_path = resolve_repository_file(
        dispatch_controls.get("dispatch_binding_path"),
        "dispatch_gate.controls.dispatch_binding_path",
    )
    binding_payload = read_json(binding_path)
    binding_core = binding_payload.get("dispatch_binding")
    if not isinstance(binding_core, dict):
        raise ValueError("Argos dispatch binding core must be an object")
    observed_binding_sha256 = normalized_sha256(
        prior_binding.get("observed_action_time_binding_sha256"),
        "outreach_status.prior_binding.observed_action_time_binding_sha256",
    )
    historical_binding_sha256 = normalized_sha256(
        binding_core.get("binding_sha256"),
        "dispatch_binding.binding_sha256",
    )
    declared_historical_binding_sha256 = normalized_sha256(
        prior_binding.get("historical_snapshot_binding_sha256"),
        "outreach_status.prior_binding.historical_snapshot_binding_sha256",
    )
    if declared_historical_binding_sha256 != historical_binding_sha256:
        raise ValueError(
            "Argos status no longer matches the historical binding snapshot"
        )
    binding_matches = observed_binding_sha256 == historical_binding_sha256
    expected_binding_status = (
        "MATCHED_TO_HISTORICAL_SNAPSHOT"
        if binding_matches
        else "MISMATCH_RETAINED_AS_UNRECONCILED_PUBLIC_AUDIT_GAP"
    )
    if prior_binding.get("binding_match_status") != expected_binding_status:
        raise ValueError("Argos binding-match status is inconsistent")
    if (
        prior_binding.get("public_authorization_chain_reconciled")
        is not binding_matches
    ):
        raise ValueError(
            "Argos public authorization-chain reconciliation is inconsistent"
        )
    if prior_binding.get("sent_content_source_bound_by_post_send_hashes") is not True:
        raise ValueError("Argos sent content must remain source-bound")
    prior_binding_expires = parse_aware_datetime(
        str(prior_binding.get("expires_utc", "")),
        "outreach_status.prior_binding.expires_utc",
    )
    binding_expires = parse_aware_datetime(
        str(binding_core.get("approval_window_expires_utc", "")),
        "dispatch_binding.approval_window_expires_utc",
    )
    if prior_binding_expires != binding_expires:
        raise ValueError("Argos prior binding expiry changed")
    if not prior_binding_expires < sent_utc <= recorded_utc:
        raise ValueError("Argos prior binding is not expired at record time")
    if prior_binding.get("expired_at_record_time") is not True:
        raise ValueError("Argos status must mark the prior binding expired")
    if prior_binding.get("prior_approval_reusable") is not False:
        raise ValueError("Argos prior approval must remain nonreusable")
    if controls.get("public_action_time_binding_reconciled") is not binding_matches:
        raise ValueError(
            "Argos outreach control disagrees with binding reconciliation"
        )

    required_true_controls = {
        "fresh_full_mailbox_recheck_completed_before_send",
        "fresh_draft_readback_completed_before_send",
        "action_time_human_approval_received",
        "private_human_unlock_required",
        "final_send_performed",
        "post_send_sent_copy_verified",
        "duplicate_send_prohibited",
        "partner_name_use_requires_written_authority",
    }
    for field in required_true_controls:
        if controls.get(field) is not True:
            raise ValueError(f"Argos outreach control must remain true: {field}")
    for field in ("builder_can_send_email", "draft_creation_authorizes_send"):
        if controls.get(field) is not False:
            raise ValueError(f"Argos outreach control must remain false: {field}")
    if dispatch_controls.get("builder_can_send") is not False:
        raise ValueError("Argos dispatch builder must remain unable to send")
    if submission_send_gate.get("decision") != "BLOCK_SEND":
        raise ValueError("Argos Government response send gate must remain blocked")

    return {
        "path": status_relative_path.as_posix(),
        "sha256": sha256(status_path),
        "recorded_utc": format_utc(recorded_utc),
        "observed_state": ARGOS_SENT_ONCE_STATUS,
        "partner_interest_target_utc": format_utc(partner_target),
        "mailbox_checked_utc": format_utc(checked_utc),
        "sent_utc": format_utc(sent_utc),
        "mailbox_state": {
            "current_draft_count": 0,
            "sent_count": 1,
            "inbound_count": 0,
            "attachment_count": 0,
            "cc_count": 0,
            "bcc_count": 0,
        },
        "subject_sha256": subject_sha256,
        "body_path": body_relative_path.as_posix(),
        "body_sha256": body_sha256,
        "selected_template_id": selected_template_id,
        "prior_binding": {
            "historical_snapshot_path": binding_relative_path.as_posix(),
            "historical_snapshot_binding_sha256": historical_binding_sha256,
            "observed_action_time_binding_sha256": observed_binding_sha256,
            "binding_match_status": expected_binding_status,
            "public_authorization_chain_reconciled": binding_matches,
            "sent_content_source_bound_by_post_send_hashes": True,
            "expires_utc": format_utc(prior_binding_expires),
            "expired_at_record_time": True,
            "prior_approval_reusable": False,
        },
    }


def argos_government_response_status_receipt(
    binding: dict[str, Any],
    deadline: dict[str, Any],
) -> dict[str, Any]:
    status_relative_path, status_path = resolve_repository_file(
        binding.get("government_response_status_path"),
        "government_response_status_path",
    )
    status = read_json(status_path)
    assert_no_private_fields(status, "government_response_status")
    if status.get("schema") != ARGOS_GOVERNMENT_STATUS_SCHEMA:
        raise ValueError("unexpected Argos Government response status schema")
    if status.get("lane_id") != binding.get("required_government_lane_id"):
        raise ValueError("Argos Government response lane changed")
    required_status = binding.get("required_government_response_status")
    if required_status != ARGOS_GOVERNMENT_SENT_ONCE_STATUS:
        raise ValueError(
            "Argos required Government response status is not the sent-once state"
        )
    if status.get("status") != required_status:
        raise ValueError(
            "Argos Government response status is not the required sent-once state"
        )

    opportunity = status.get("opportunity")
    mailbox = status.get("mailbox_observation")
    source_binding = status.get("source_and_attachment_binding")
    controls = status.get("controls")
    for label, value in {
        "government_response_status.opportunity": opportunity,
        "government_response_status.mailbox_observation": mailbox,
        "government_response_status.source_and_attachment_binding": source_binding,
        "government_response_status.controls": controls,
    }.items():
        if not isinstance(value, dict):
            raise ValueError(f"{label} must be an object")

    configured_deadline = parse_aware_datetime(
        str(deadline.get("iso_utc", "")),
        "deadline.iso_utc",
    )
    status_deadline = parse_aware_datetime(
        str(opportunity.get("government_deadline_utc", "")),
        "government_response_status.government_deadline_utc",
    )
    if configured_deadline != status_deadline:
        raise ValueError("Argos Government response deadline changed")

    recorded_utc = parse_aware_datetime(
        str(status.get("recorded_utc", "")),
        "government_response_status.recorded_utc",
    )
    sent_utc = parse_aware_datetime(
        str(mailbox.get("sent_utc", "")),
        "government_response_status.mailbox_observation.sent_utc",
    )
    acknowledged_utc = parse_aware_datetime(
        str(mailbox.get("automatic_acknowledgment_utc", "")),
        "government_response_status.mailbox_observation."
        "automatic_acknowledgment_utc",
    )
    source_rechecked_utc = parse_aware_datetime(
        str(source_binding.get("official_source_rechecked_utc", "")),
        "government_response_status.source_and_attachment_binding."
        "official_source_rechecked_utc",
    )
    if not source_rechecked_utc < sent_utc < acknowledged_utc == recorded_utc:
        raise ValueError("Argos Government response chronology is invalid")
    if sent_utc >= configured_deadline:
        raise ValueError("Argos Government response was not timely")

    expected_counts = {
        "sent_count": 1,
        "automatic_acknowledgment_count": 1,
        "formal_receipt_count": 0,
        "substantive_inbound_count": 0,
        "attachment_count": 1,
        "cc_count": 0,
        "bcc_count": 0,
    }
    for field, expected in expected_counts.items():
        value = mailbox.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value != expected:
            raise ValueError(
                f"Argos Government response mailbox count changed: {field}"
            )
    for field in (
        "gmail_identifiers_omitted",
        "recipient_address_omitted",
        "message_body_omitted",
    ):
        if mailbox.get(field) is not True:
            raise ValueError(
                f"Argos Government response privacy control failed: {field}"
            )

    required_attachment_filename = str(
        binding.get("required_government_attachment_filename", "")
    )
    required_attachment_size = binding.get(
        "required_government_attachment_size_bytes"
    )
    required_attachment_sha256 = normalized_sha256(
        binding.get("required_government_attachment_sha256"),
        "required_government_attachment_sha256",
    )
    if source_binding.get("attachment_filename") != required_attachment_filename:
        raise ValueError("Argos Government response attachment filename changed")
    if source_binding.get("attachment_size_bytes") != required_attachment_size:
        raise ValueError("Argos Government response attachment size changed")
    source_receipt_relative_path, source_receipt_path = resolve_repository_file(
        binding.get("required_official_source_receipt_path"),
        "required_official_source_receipt_path",
    )
    required_source_receipt_sha256 = normalized_sha256(
        binding.get("required_official_source_receipt_sha256"),
        "required_official_source_receipt_sha256",
    )
    observed_source_receipt_sha256 = sha256(source_receipt_path).upper()
    if observed_source_receipt_sha256 != required_source_receipt_sha256:
        raise ValueError("Argos official source receipt SHA-256 changed")
    source_receipt_sha256 = normalized_sha256(
        source_binding.get("official_source_receipt_sha256"),
        "government_response_status.official_source_receipt_sha256",
    )
    if source_receipt_sha256 != observed_source_receipt_sha256:
        raise ValueError(
            "Argos Government response source receipt SHA-256 changed"
        )
    attachment_sha256 = normalized_sha256(
        source_binding.get("attachment_sha256"),
        "government_response_status.attachment_sha256",
    )
    if attachment_sha256 != required_attachment_sha256:
        raise ValueError("Argos Government response attachment SHA-256 changed")

    required_true_controls = {
        "duplicate_send_prohibited",
        "new_campaign_key_prohibited",
    }
    required_false_controls = {
        "automatic_acknowledgment_is_formal_receipt",
        "automatic_acknowledgment_is_substantive_review",
        "automatic_acknowledgment_authorizes_follow_up",
        "formal_receipt_confirmed",
        "agency_review_confirmed",
        "selection_award_funding_or_validation_confirmed",
        "action_time_provenance_reconciled",
        "sent_event_cryptographically_anchored_at_action_time",
    }
    for field in required_true_controls:
        if controls.get(field) is not True:
            raise ValueError(
                f"Argos Government response control must remain true: {field}"
            )
    for field in required_false_controls:
        if controls.get(field) is not False:
            raise ValueError(
                f"Argos Government response control must remain false: {field}"
            )

    return {
        "path": status_relative_path.as_posix(),
        "sha256": sha256(status_path),
        "recorded_utc": format_utc(recorded_utc),
        "observed_state": ARGOS_GOVERNMENT_SENT_ONCE_STATUS,
        "sent_utc": format_utc(sent_utc),
        "automatic_acknowledgment_utc": format_utc(acknowledged_utc),
        "mailbox_state": dict(expected_counts),
        "official_source_rechecked_utc": format_utc(source_rechecked_utc),
        "official_source_receipt_path": source_receipt_relative_path.as_posix(),
        "official_source_receipt_sha256": source_receipt_sha256,
        "attachment_filename": required_attachment_filename,
        "attachment_size_bytes": required_attachment_size,
        "attachment_sha256": attachment_sha256,
        "duplicate_send_prohibited": True,
        "automatic_acknowledgment_is_formal_receipt": False,
        "automatic_acknowledgment_is_substantive_review": False,
        "automatic_acknowledgment_authorizes_follow_up": False,
        "action_time_provenance_reconciled": False,
        "sent_event_cryptographically_anchored_at_action_time": False,
    }


def source_receipt(binding: dict[str, Any], deadline: dict[str, Any]) -> dict[str, Any]:
    kind = str(binding.get("kind", "")).strip()
    repository_gate_kinds = {
        "REPOSITORY_GATE",
        "REPOSITORY_DATE_GATE",
        "REPOSITORY_GATE_WITH_OUTREACH_STATUS",
    }
    exact_gate_kinds = {
        "REPOSITORY_GATE",
        "REPOSITORY_GATE_WITH_OUTREACH_STATUS",
    }
    if kind in repository_gate_kinds:
        relative_path, source_path = resolve_repository_file(
            binding.get("path"),
            "repository source path",
        )
        source = read_json(source_path)
        deadline_field = str(binding.get("deadline_field", "")).strip()
        status_field = str(binding.get("status_field", "")).strip()
        observed_deadline = str(resolve_field(source, deadline_field))
        observed_status = str(resolve_field(source, status_field))
        required_status = str(binding.get("required_status", "")).strip()

        if kind in exact_gate_kinds:
            if deadline.get("precision") != "EXACT":
                raise ValueError("repository deadline binding requires EXACT precision")
            if parse_aware_datetime(
                observed_deadline, deadline_field
            ) != parse_aware_datetime(
                str(deadline.get("iso_utc", "")), "deadline.iso_utc"
            ):
                raise ValueError("configured deadline does not match the repository gate")
        else:
            if deadline.get("precision") != "DATE_ONLY":
                raise ValueError(
                    "repository date binding requires DATE_ONLY precision"
                )
            if parse_date(observed_deadline, deadline_field) != parse_date(
                str(deadline.get("date", "")), "deadline.date"
            ):
                raise ValueError("configured date does not match the repository gate")
        if observed_status != required_status:
            raise ValueError(
                "repository gate status changed: "
                f"expected {required_status}, observed {observed_status}"
            )

        receipt = {
            "kind": kind,
            "path": relative_path.as_posix(),
            "sha256": sha256(source_path),
            "bound_deadline_field": deadline_field,
            "observed_status": observed_status,
        }
        if kind == "REPOSITORY_GATE_WITH_OUTREACH_STATUS":
            receipt["outreach_status"] = argos_outreach_status_receipt(
                binding,
                deadline,
                relative_path,
                source_path,
                source,
            )
            receipt["government_response_status"] = (
                argos_government_response_status_receipt(binding, deadline)
            )
        return receipt

    if kind == "PRIVATE_OFFICIAL_INBOUND_STATUS_EVENT":
        if binding.get("private_source_excluded") is not True:
            raise ValueError("private source metadata must remain excluded")
        if binding.get("identifiers_excluded") is not True:
            raise ValueError("private source identifiers must remain excluded")
        return {
            "kind": kind,
            "private_source_excluded": True,
            "identifiers_excluded": True,
        }

    raise ValueError(f"unsupported source binding kind: {kind}")


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema") != "lumencore.deadline_action_sentinel_config.v1":
        raise ValueError("unexpected deadline sentinel config schema")
    assert_no_private_fields(config)

    controls = config.get("controls")
    if not isinstance(controls, dict):
        raise ValueError("controls must be an object")
    for key in sorted(REQUIRED_FALSE_CONTROLS):
        if controls.get(key) is not False:
            raise ValueError(f"control must remain false: {key}")
    for key in sorted(REQUIRED_TRUE_CONTROLS):
        if controls.get(key) is not True:
            raise ValueError(f"control must remain true: {key}")

    prohibited = config.get("prohibited_actions")
    if not isinstance(prohibited, list):
        raise ValueError("prohibited_actions must be a list")
    missing = REQUIRED_PROHIBITED_ACTIONS.difference(str(value) for value in prohibited)
    if missing:
        raise ValueError(f"missing prohibited actions: {sorted(missing)}")

    alert_window = config.get("alert_window_hours")
    if not isinstance(alert_window, int) or alert_window <= 0:
        raise ValueError("alert_window_hours must be a positive integer")

    lanes = config.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        raise ValueError("lanes must be a non-empty list")
    ids: set[str] = set()
    for lane in lanes:
        if not isinstance(lane, dict):
            raise ValueError("each lane must be an object")
        lane_id = str(lane.get("id", "")).strip()
        if not lane_id or lane_id in ids:
            raise ValueError(f"lane id must be present and unique: {lane_id}")
        ids.add(lane_id)
        completion_evidence_present = lane.get("completion_evidence_present")
        if not isinstance(completion_evidence_present, bool):
            raise ValueError(
                f"{lane_id} completion_evidence_present must be boolean"
            )
        if completion_evidence_present:
            parse_aware_datetime(
                str(lane.get("completion_evidence_recorded_utc", "")),
                f"{lane_id}.completion_evidence_recorded_utc",
            )
        elif "completion_evidence_recorded_utc" in lane:
            raise ValueError(
                f"{lane_id} cannot record completion evidence while incomplete"
            )
        blockers = lane.get("blockers")
        if not isinstance(blockers, list) or not blockers:
            raise ValueError(f"{lane_id} must retain at least one blocker")

        deadline = lane.get("deadline")
        if not isinstance(deadline, dict):
            raise ValueError(f"{lane_id} deadline must be an object")
        precision = deadline.get("precision")
        if precision == "EXACT":
            parse_aware_datetime(str(deadline.get("iso_utc", "")), f"{lane_id}.iso_utc")
            if deadline.get("cutoff_time_known") is not True:
                raise ValueError(f"{lane_id} exact deadline must have a known cutoff")
            if deadline.get("timezone_known") is not True:
                raise ValueError(f"{lane_id} exact deadline must have a known timezone")
            if not str(deadline.get("timezone", "")).strip():
                raise ValueError(f"{lane_id} exact deadline must name its timezone")
        elif precision == "DATE_ONLY":
            parse_date(str(deadline.get("date", "")), f"{lane_id}.date")
            if deadline.get("cutoff_time_known") is not False:
                raise ValueError(f"{lane_id} date-only cutoff must remain unknown")
            if deadline.get("timezone_known") is not False:
                raise ValueError(f"{lane_id} date-only timezone must remain unknown")
            for forbidden in ("iso_utc", "local_display", "timezone"):
                if forbidden in deadline:
                    raise ValueError(
                        f"{lane_id} date-only deadline cannot contain {forbidden}"
                    )
        else:
            raise ValueError(f"{lane_id} has unsupported deadline precision: {precision}")

        binding = lane.get("source_binding")
        if not isinstance(binding, dict):
            raise ValueError(f"{lane_id} source_binding must be an object")
        source_receipt(binding, deadline)


def urgency_for(seconds_until: int, alert_window_hours: int) -> str:
    if seconds_until <= 0:
        return "PAST"
    hours_until = seconds_until / 3600
    if hours_until <= 8:
        return "WITHIN_8_HOURS"
    if hours_until <= 24:
        return "WITHIN_24_HOURS"
    if hours_until <= 72:
        return "WITHIN_72_HOURS"
    if hours_until <= alert_window_hours:
        return "WITHIN_ALERT_WINDOW"
    return "LATER"


def evaluate_lane(
    lane: dict[str, Any], as_of_utc: datetime, alert_window_hours: int
) -> dict[str, Any]:
    deadline = lane["deadline"]
    blockers = [str(value) for value in lane["blockers"]]
    precision = deadline["precision"]
    receipt = source_receipt(lane["source_binding"], deadline)
    government_response_status = receipt.get("government_response_status")
    if isinstance(government_response_status, dict):
        government_recorded_utc = parse_aware_datetime(
            str(government_response_status["recorded_utc"]),
            "government_response_status.recorded_utc",
        )
        if government_recorded_utc > as_of_utc:
            receipt = dict(receipt)
            receipt.pop("government_response_status")

    completion_recorded_utc: datetime | None = None
    completion_evidence_present = False
    if lane["completion_evidence_present"]:
        completion_recorded_utc = parse_aware_datetime(
            str(lane["completion_evidence_recorded_utc"]),
            "completion_evidence_recorded_utc",
        )
        completion_evidence_present = completion_recorded_utc <= as_of_utc

    result: dict[str, Any] = {
        "id": str(lane["id"]),
        "title": str(lane["title"]),
        "visibility": str(lane["visibility"]),
        "external_action_type": str(lane["external_action_type"]),
        "completion_evidence_present": completion_evidence_present,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "requires_human_attention": not completion_evidence_present,
        "external_action_authorized": False,
        "send_now": False,
        "external_action_executed": False,
        "safest_next_action": str(lane["safest_next_action"]),
        "source_receipt": receipt,
    }
    if completion_recorded_utc is not None:
        result["completion_evidence_recorded_utc"] = format_utc(
            completion_recorded_utc
        )

    if precision == "EXACT":
        deadline_utc = parse_aware_datetime(str(deadline["iso_utc"]), "deadline.iso_utc")
        seconds_until = int((deadline_utc - as_of_utc).total_seconds())
        if seconds_until <= 0:
            state = "PAST_DEADLINE_NO_EXTERNAL_ACTION_AUTHORIZED"
        elif isinstance(receipt.get("government_response_status"), dict):
            state = "GOVERNMENT_RESPONSE_SENT_ONCE_WAITING_FOR_SUBSTANTIVE_REPLY"
        elif receipt["kind"] == "REPOSITORY_GATE_WITH_OUTREACH_STATUS":
            state = "PARTNER_OUTREACH_SENT_ONCE_GOVERNMENT_RESPONSE_DUE"
        elif seconds_until <= alert_window_hours * 3600:
            state = "BLOCKED_HUMAN_ACTION_DUE"
        else:
            state = "BLOCKED_MONITOR"
        result.update(
            {
                "state": state,
                "urgency": urgency_for(seconds_until, alert_window_hours),
                "deadline": {
                    "precision": "EXACT",
                    "iso_utc": format_utc(deadline_utc),
                    "local_display": str(deadline["local_display"]),
                    "timezone": str(deadline["timezone"]),
                    "cutoff_time_known": True,
                    "timezone_known": True,
                    "exact_countdown_available": True,
                    "deadline_passed": seconds_until <= 0,
                    "seconds_until_deadline": seconds_until,
                    "hours_until_deadline": round(seconds_until / 3600, 2),
                },
            }
        )
        if completion_evidence_present:
            result["state"] = (
                "COMPLETION_EVIDENCE_RECORDED_NO_EXTERNAL_ACTION_REQUIRED"
            )
            result["urgency"] = "COMPLETED"
        outreach_status = receipt.get("outreach_status")
        if isinstance(outreach_status, dict):
            recorded_utc = parse_aware_datetime(
                str(outreach_status["recorded_utc"]),
                "outreach_status.recorded_utc",
            )
            if recorded_utc > as_of_utc:
                raise ValueError(
                    "Argos outreach status cannot be used before its record time"
                )
            partner_target = parse_aware_datetime(
                str(outreach_status["partner_interest_target_utc"]),
                "outreach_status.partner_interest_target_utc",
            )
            target_seconds_until = int((partner_target - as_of_utc).total_seconds())
            if target_seconds_until < 0:
                target_state = "PARTNER_TARGET_PASSED_WAITING_FOR_REPLY"
            else:
                target_state = "PARTNER_INQUIRY_SENT_WAITING_FOR_REPLY"
            result["outreach_status"] = {
                "observed_state": str(outreach_status["observed_state"]),
                "recorded_utc": str(outreach_status["recorded_utc"]),
                "current_state_as_of_evaluation": (
                    "OFFICIAL_DEADLINE_PASSED_NO_SEND"
                    if seconds_until <= 0
                    else target_state
                ),
                "partner_interest_target_utc": format_utc(partner_target),
                "seconds_until_partner_target": target_seconds_until,
                "mailbox_state_as_of_record": dict(
                    outreach_status["mailbox_state"]
                ),
                "selected_template_id": str(
                    outreach_status["selected_template_id"]
                ),
                "subject_sha256": str(outreach_status["subject_sha256"]),
                "body_sha256": str(outreach_status["body_sha256"]),
                "prior_binding_expired": True,
                "prior_approval_reusable": False,
                "binding_match_status": str(
                    outreach_status["prior_binding"]["binding_match_status"]
                ),
                "public_authorization_chain_reconciled": bool(
                    outreach_status["prior_binding"][
                        "public_authorization_chain_reconciled"
                    ]
                ),
                "sent_content_source_bound_by_post_send_hashes": bool(
                    outreach_status["prior_binding"][
                        "sent_content_source_bound_by_post_send_hashes"
                    ]
                ),
                "fresh_recheck_required": False,
                "new_exact_approval_required": False,
                "duplicate_send_prohibited": True,
                "government_response_action_time_gates_required": not isinstance(
                    receipt.get("government_response_status"), dict
                ),
            }
        government_response_status = receipt.get("government_response_status")
        if isinstance(government_response_status, dict):
            recorded_utc = parse_aware_datetime(
                str(government_response_status["recorded_utc"]),
                "government_response_status.recorded_utc",
            )
            result["government_response_status"] = {
                "observed_state": str(
                    government_response_status["observed_state"]
                ),
                "recorded_utc": str(government_response_status["recorded_utc"]),
                "sent_utc": str(government_response_status["sent_utc"]),
                "automatic_acknowledgment_utc": str(
                    government_response_status["automatic_acknowledgment_utc"]
                ),
                "mailbox_state_as_of_record": dict(
                    government_response_status["mailbox_state"]
                ),
                "official_source_rechecked_utc": str(
                    government_response_status["official_source_rechecked_utc"]
                ),
                "official_source_receipt_path": str(
                    government_response_status[
                        "official_source_receipt_path"
                    ]
                ),
                "official_source_receipt_sha256": str(
                    government_response_status[
                        "official_source_receipt_sha256"
                    ]
                ),
                "attachment_filename": str(
                    government_response_status["attachment_filename"]
                ),
                "attachment_size_bytes": int(
                    government_response_status["attachment_size_bytes"]
                ),
                "attachment_sha256": str(
                    government_response_status["attachment_sha256"]
                ),
                "duplicate_send_prohibited": True,
                "automatic_acknowledgment_is_formal_receipt": False,
                "automatic_acknowledgment_is_substantive_review": False,
                "automatic_acknowledgment_authorizes_follow_up": False,
                "action_time_provenance_reconciled": False,
                "sent_event_cryptographically_anchored_at_action_time": False,
            }
        return result

    deadline_date = parse_date(str(deadline["date"]), "deadline.date")
    if as_of_utc.date() < deadline_date:
        state = "HUMAN_DATE_ONLY_ACTION_OPEN"
        relation = "FUTURE_BY_UTC_CALENDAR_DATE"
    elif as_of_utc.date() == deadline_date:
        state = "HUMAN_DATE_ONLY_ACTION_DUE_DATE_UNKNOWN_CUTOFF"
        relation = "SAME_UTC_CALENDAR_DATE"
    else:
        state = "HUMAN_DATE_ONLY_RECONCILIATION_REQUIRED"
        relation = "AFTER_DATE_BY_UTC_CALENDAR_ONLY"
    result.update(
        {
            "state": state,
            "urgency": "UNKNOWN_EXACT_CUTOFF_FAIL_CLOSED",
            "deadline": {
                "precision": "DATE_ONLY",
                "date": deadline_date.isoformat(),
                "cutoff_time_known": False,
                "timezone_known": False,
                "exact_countdown_available": False,
                "deadline_passed": None,
                "calendar_relation": relation,
            },
        }
    )
    if completion_evidence_present:
        result["state"] = "COMPLETION_EVIDENCE_RECORDED_NO_EXTERNAL_ACTION_REQUIRED"
        result["urgency"] = "COMPLETED"
    return result


def lane_sort_key(lane: dict[str, Any]) -> tuple[str, str]:
    deadline = lane["deadline"]
    if deadline["precision"] == "EXACT":
        return str(deadline["iso_utc"]), str(lane["id"])
    return f"{deadline['date']}T23:59:59Z", str(lane["id"])


def build_sentinel(config_path: Path, as_of_utc: datetime) -> dict[str, Any]:
    if as_of_utc.tzinfo is None or as_of_utc.utcoffset() is None:
        raise ValueError("as_of_utc must be timezone-aware")
    as_of_utc = as_of_utc.astimezone(timezone.utc).replace(microsecond=0)
    config = read_json(config_path)
    validate_config(config)

    alert_window_hours = int(config["alert_window_hours"])
    evaluated = [
        evaluate_lane(lane, as_of_utc, alert_window_hours)
        for lane in sorted(config["lanes"], key=lane_sort_key)
    ]
    states = Counter(str(lane["state"]) for lane in evaluated)
    posture = (
        "HUMAN_ACTION_REQUIRED_FAIL_CLOSED"
        if any(lane["requires_human_attention"] for lane in evaluated)
        else "MONITOR_FAIL_CLOSED"
    )

    payload: dict[str, Any] = {
        "schema": "lumencore.deadline_action_sentinel.v1",
        "evaluated_utc": format_utc(as_of_utc),
        "posture": posture,
        "controls": dict(config["controls"]),
        "prohibited_actions": list(config["prohibited_actions"]),
        "alert_window_hours": alert_window_hours,
        "summary": {
            "lane_count": len(evaluated),
            "human_attention_count": sum(
                1 for lane in evaluated if lane["requires_human_attention"]
            ),
            "exact_deadline_count": sum(
                1 for lane in evaluated if lane["deadline"]["precision"] == "EXACT"
            ),
            "date_only_deadline_count": sum(
                1
                for lane in evaluated
                if lane["deadline"]["precision"] == "DATE_ONLY"
            ),
            "autonomous_external_action_count": 0,
            "external_actions_executed_count": 0,
            "state_counts": dict(sorted(states.items())),
        },
        "lanes": evaluated,
        "claim_boundaries": [
            "This sentinel is a read-only deadline and blocker view.",
            (
                "A warning is not authority to send, open a signed-in portal, "
                "upload, accept terms, sign, certify, submit, or pay."
            ),
            (
                "Date-only milestones never receive an invented cutoff time, "
                "timezone, exact countdown, or definitive overdue label."
            ),
            "Drafted, sent, submitted, accepted, and paid remain distinct evidence states.",
        ],
    }
    assert_no_private_fields(payload, "output")
    return payload


def deadline_display(lane: dict[str, Any]) -> str:
    deadline = lane["deadline"]
    if deadline["precision"] == "EXACT":
        return str(deadline["local_display"])
    return f"{deadline['date']} (time and timezone unverified)"


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Deadline Action Sentinel",
        "",
        f"Evaluated UTC: `{payload['evaluated_utc']}`",
        f"Posture: `{payload['posture']}`",
        "",
        "## Control Boundary",
        "",
        "- Read-only builder: `true`",
        (
            "- Autonomous email, portal, agreement, signature, certification, "
            "submission, and payment actions: `false`"
        ),
        "- Exact action-time human approval required: `true`",
        "- Unknown deadline time or timezone: `FAIL_CLOSED`",
        "- External actions executed by this build: `0`",
        "",
        "## Current Lanes",
        "",
        "| Priority | Lane | Deadline | State | Blockers | Safest next action |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for priority, lane in enumerate(payload["lanes"], start=1):
        action = str(lane["safest_next_action"]).replace("|", "/")
        lines.append(
            f"| {priority} | {lane['title']} | {deadline_display(lane)} | "
            f"`{lane['state']}` | {lane['blocker_count']} | {action} |"
        )

    lines.extend(
        [
            "",
            "## Source Custody",
            "",
        ]
    )
    for lane in payload["lanes"]:
        receipt = lane["source_receipt"]
        if receipt["kind"] in {
            "REPOSITORY_GATE",
            "REPOSITORY_DATE_GATE",
            "REPOSITORY_GATE_WITH_OUTREACH_STATUS",
        }:
            lines.append(
                f"- `{lane['id']}`: `{receipt['path']}` at SHA-256 "
                f"`{receipt['sha256']}`; observed gate `{receipt['observed_status']}`."
            )
            outreach_status = receipt.get("outreach_status")
            if isinstance(outreach_status, dict):
                mailbox = outreach_status["mailbox_state"]
                lines.append(
                    f"  Outreach receipt: `{outreach_status['path']}` at SHA-256 "
                    f"`{outreach_status['sha256']}`; observed "
                    f"`{outreach_status['observed_state']}` at "
                    f"`{outreach_status['recorded_utc']}` with "
                    f"{mailbox['current_draft_count']} draft, "
                    f"{mailbox['sent_count']} sent, and "
                    f"{mailbox['inbound_count']} inbound; prior approval expired "
                    "and is not reusable."
                )
        else:
            lines.append(
                f"- `{lane['id']}`: private official-event metadata only; source "
                "content and identifiers intentionally excluded."
            )

    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
        ]
    )
    lines.extend(f"- {boundary}" for boundary in payload["claim_boundaries"])
    lines.append("")
    return "\n".join(lines)


def resolve_cli_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def write_outputs(
    payload: dict[str, Any], json_output: Path, markdown_output: Path
) -> None:
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(canonical_json(payload), encoding="utf-8", newline="\n")
    markdown_output.write_text(render_markdown(payload), encoding="utf-8", newline="\n")


def check_outputs(
    payload: dict[str, Any], json_output: Path, markdown_output: Path
) -> None:
    expected = {
        json_output: canonical_json(payload),
        markdown_output: render_markdown(payload),
    }
    for path, content in expected.items():
        if not path.is_file():
            raise ValueError(f"expected output is missing: {path}")
        if path.read_text(encoding="utf-8") != content:
            raise ValueError(f"output is stale: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a fail-closed, read-only deadline action sentinel."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON))
    parser.add_argument("--markdown-output", default=str(DEFAULT_MARKDOWN))
    parser.add_argument("--as-of-utc")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = resolve_cli_path(args.config)
    json_output = resolve_cli_path(args.json_output)
    markdown_output = resolve_cli_path(args.markdown_output)

    as_of_text = args.as_of_utc
    if args.check and not as_of_text:
        if not json_output.is_file():
            raise ValueError("--check requires an existing JSON output or --as-of-utc")
        as_of_text = str(read_json(json_output).get("evaluated_utc", ""))
    as_of_utc = (
        parse_aware_datetime(as_of_text, "--as-of-utc")
        if as_of_text
        else datetime.now(timezone.utc)
    )
    payload = build_sentinel(config_path, as_of_utc)

    if args.check:
        check_outputs(payload, json_output, markdown_output)
        status = "CURRENT"
    else:
        write_outputs(payload, json_output, markdown_output)
        status = "WRITTEN"

    print(
        json.dumps(
            {
                "status": status,
                "posture": payload["posture"],
                "evaluated_utc": payload["evaluated_utc"],
                "lane_count": payload["summary"]["lane_count"],
                "external_actions_executed_count": 0,
                "json_output": str(json_output),
                "markdown_output": str(markdown_output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
