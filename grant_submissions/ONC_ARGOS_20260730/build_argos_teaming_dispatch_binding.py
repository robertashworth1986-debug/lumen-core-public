from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ARGOS_DIR = Path(__file__).resolve().parent
ROOT = ARGOS_DIR.parents[1]
SOURCE_GATE = ARGOS_DIR / "ARGOS_EMI_TEAMING_DISPATCH_GATE_2026-07-27.json"
REGISTRY = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "OUTREACH_RESPONSE_TEMPLATE_REGISTRY_2026-07-18.json"
)
DEFAULT_JSON = (
    ARGOS_DIR / "ARGOS_EMI_TEAMING_DISPATCH_BINDING_2026-07-27.json"
)
DEFAULT_MARKDOWN = (
    ARGOS_DIR / "ARGOS_EMI_TEAMING_DISPATCH_BINDING_2026-07-27.md"
)

SOURCE_SCHEMA = "lumencore.argos_partner_dispatch_gate.v1"
OUTPUT_SCHEMA = "lumencore.initial_outreach_dispatch_binding.v1"
BINDING_SCHEMA = "lumencore.initial_outreach_dispatch_binding_core.v1"
MAILBOX_RECHECK_MAX_AGE_SECONDS = 15 * 60
DRAFT_READBACK_MAX_AGE_SECONDS = 15 * 60
APPROVAL_WINDOW_SECONDS = 5 * 60
MAX_SUBJECT_CHARS = 200
MAX_BODY_CHARS = 5000
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
REQUIRED_TEMPLATE_CONTROLS = {
    "EXPLICIT_QUALIFICATION_BOUNDARY",
    "FRESH_DUPLICATE_RECHECK_BEFORE_SEND",
    "NO_ATTACHMENTS",
    "OFFICIAL_OPPORTUNITY_URL",
    "OFFICIAL_TIMEZONE_AWARE_DEADLINE",
    "SINGLE_USE_ACTION_TIME_APPROVAL",
    "VERIFIED_PUBLIC_PARTNER_ROUTE",
    "WRITTEN_PARTNER_AUTHORITY_REQUIRED",
}
FORBIDDEN_PROMOTION_PHRASES = (
    "agency approved",
    "certified safe",
    "field-proven performance",
    "guaranteed funding",
    "guaranteed savings",
    "government-approved",
    "independently validated performance",
    "will save",
)
REQUIRED_BODY_MARKERS = (
    "Duplicate-send check:",
    "No attachment is included.",
    "No pricing, binding commitment, or unsupported credential use is requested.",
    "We do not claim current FHIR/ONC or HHS ATO prior performance.",
)


class DispatchBindingError(ValueError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DispatchBindingError(f"DUPLICATE_JSON_KEY:{key}")
        result[key] = value
    return result


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise DispatchBindingError(f"INVALID_JSON:{path.name}") from exc
    if not isinstance(payload, dict):
        raise DispatchBindingError(f"JSON_NOT_OBJECT:{path.name}")
    return payload


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical_object_sha256(
    payload: dict[str, Any], *, omit: set[str] | None = None
) -> str:
    bounded = {
        key: value
        for key, value in payload.items()
        if key not in (omit or set())
    }
    return sha256_bytes(
        json.dumps(
            bounded,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def parse_utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise DispatchBindingError(f"{label}_MISSING")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise DispatchBindingError(f"{label}_INVALID") from exc
    if parsed.tzinfo is None:
        raise DispatchBindingError(f"{label}_TIMEZONE_REQUIRED")
    return parsed.astimezone(timezone.utc)


def utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def rooted_file(path_value: Any) -> Path:
    if not isinstance(path_value, str) or not path_value.strip():
        raise DispatchBindingError("BODY_PATH_INVALID")
    path = Path(path_value)
    if path.is_absolute():
        raise DispatchBindingError("BODY_PATH_MUST_BE_RELATIVE")
    resolved = (ROOT / path).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise DispatchBindingError("BODY_PATH_OUTSIDE_ROOT") from exc
    if not resolved.is_file():
        raise DispatchBindingError("BODY_FILE_MISSING")
    return resolved


def is_public_https_url(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = urlsplit(value.strip())
    except ValueError:
        return False
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    hostname = parsed.hostname.strip().rstrip(".")
    if hostname.casefold() == "localhost" or "." not in hostname:
        return False
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return True
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def canonical_template_sha256(template: dict[str, Any]) -> str:
    return canonical_object_sha256(template)


def check_row(
    check_id: str,
    requirement: str,
    passed: bool,
    evidence: str,
) -> dict[str, str]:
    return {
        "check_id": check_id,
        "requirement": requirement,
        "status": "PASS" if passed else "FAIL",
        "evidence": evidence,
    }


def build_payload(
    source_gate: dict[str, Any] | None = None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate = source_gate or read_json(SOURCE_GATE)
    public_registry = registry or read_json(REGISTRY)
    if gate.get("schema") != SOURCE_SCHEMA:
        raise DispatchBindingError("SOURCE_SCHEMA_INVALID")
    if public_registry.get("schema") != (
        "lumencore.outreach_response_template_registry.v1"
    ):
        raise DispatchBindingError("REGISTRY_SCHEMA_INVALID")

    generated = parse_utc(gate.get("generated_utc"), "GENERATED_UTC")
    opportunity = gate.get("opportunity")
    selection = gate.get("template_selection")
    recipient = gate.get("recipient_route")
    message = gate.get("message")
    preflight = gate.get("mailbox_duplicate_preflight")
    duplicate = gate.get("fresh_duplicate_recheck")
    draft = gate.get("gmail_draft_receipt")
    controls = gate.get("controls")
    required_objects = {
        "OPPORTUNITY": opportunity,
        "TEMPLATE_SELECTION": selection,
        "RECIPIENT_ROUTE": recipient,
        "MESSAGE": message,
        "MAILBOX_PREFLIGHT": preflight,
        "DUPLICATE_RECHECK": duplicate,
        "GMAIL_DRAFT_RECEIPT": draft,
        "CONTROLS": controls,
    }
    for label, value in required_objects.items():
        if not isinstance(value, dict):
            raise DispatchBindingError(f"{label}_INVALID")

    government_deadline = parse_utc(
        opportunity.get("government_deadline_utc"),
        "GOVERNMENT_DEADLINE",
    )
    partner_target = parse_utc(
        opportunity.get("partner_interest_target_utc"),
        "PARTNER_INTEREST_TARGET",
    )
    official_notice_url = opportunity.get("official_notice_url")
    body_path = rooted_file(message.get("body_path"))
    body_bytes = body_path.read_bytes()
    try:
        body = body_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DispatchBindingError("BODY_NOT_UTF8") from exc
    subject = str(message.get("subject") or "")
    body_sha256 = sha256_bytes(body_bytes)
    subject_sha256 = sha256_bytes(subject.encode("utf-8"))

    template_id = str(selection.get("template_id") or "")
    templates = public_registry.get("templates")
    if not isinstance(templates, list):
        raise DispatchBindingError("REGISTRY_TEMPLATES_INVALID")
    matching_templates = [
        row
        for row in templates
        if isinstance(row, dict) and row.get("template_id") == template_id
    ]
    template = matching_templates[0] if len(matching_templates) == 1 else None
    expected_template_sha256 = (
        canonical_template_sha256(template) if template is not None else ""
    )
    declared_controls = selection.get("required_controls_preserved")
    declared_control_set = (
        set(declared_controls)
        if isinstance(declared_controls, list)
        and all(isinstance(item, str) for item in declared_controls)
        else set()
    )

    preflight_checked = parse_utc(preflight.get("checked_utc"), "PREFLIGHT_UTC")
    duplicate_checked = parse_utc(
        duplicate.get("checked_utc"),
        "DUPLICATE_RECHECK_UTC",
    )
    draft_created = parse_utc(draft.get("created_utc"), "DRAFT_CREATED_UTC")
    draft_updated = parse_utc(draft.get("updated_utc"), "DRAFT_UPDATED_UTC")
    draft_readback_checked = parse_utc(
        draft.get("readback_checked_utc"),
        "DRAFT_READBACK_CHECKED_UTC",
    )
    duplicate_age = (generated - duplicate_checked).total_seconds()
    draft_readback_age = (
        generated - draft_readback_checked
    ).total_seconds()

    matching_message_count = duplicate.get("matching_message_count")
    matching_current_draft_count = duplicate.get(
        "matching_current_draft_count"
    )
    matching_sent_or_received_count = duplicate.get(
        "matching_sent_or_received_count"
    )
    duplicate_counts_are_integers = all(
        isinstance(value, int) and not isinstance(value, bool) and value >= 0
        for value in (
            matching_message_count,
            matching_current_draft_count,
            matching_sent_or_received_count,
        )
    )
    duplicate_counts_hold = (
        duplicate_counts_are_integers
        and matching_message_count
        == matching_current_draft_count + matching_sent_or_received_count
        and matching_current_draft_count == 1
        and matching_sent_or_received_count == 0
    )

    route_fields_present = all(
        isinstance(recipient.get(field), str) and recipient[field].strip()
        for field in (
            "organization",
            "named_addressee",
            "route_type",
            "official_contact_source",
            "official_partnership_source",
        )
    )
    route_urls_public = all(
        is_public_https_url(recipient.get(field))
        for field in (
            "official_contact_source",
            "official_partnership_source",
        )
    )
    normalized_body = " ".join(body.split())
    body_markers_present = all(
        " ".join(marker.split()) in normalized_body
        for marker in REQUIRED_BODY_MARKERS
    )
    body_claim_boundaries_hold = not any(
        marker in normalized_body.casefold()
        for marker in FORBIDDEN_PROMOTION_PHRASES
    )
    body_content_safe = (
        bool(body.strip())
        and len(body) <= MAX_BODY_CHARS
        and CONTROL_CHAR_RE.search(body) is None
        and body_markers_present
        and body_claim_boundaries_hold
        and isinstance(official_notice_url, str)
        and is_public_https_url(official_notice_url)
        and official_notice_url in body
    )
    subject_safe = (
        bool(subject.strip())
        and len(subject) <= MAX_SUBJECT_CHARS
        and "\r" not in subject
        and "\n" not in subject
        and CONTROL_CHAR_RE.search(subject) is None
    )

    registry_current = bool(
        template
        and selection.get("registry_source_config_sha256")
        == public_registry.get("source_config_sha256")
        and selection.get("template_canonical_sha256")
        == expected_template_sha256
        and selection.get("relationship")
        == "OPPORTUNITY_SPECIFIC_SPECIALIZATION"
        and selection.get("exact_template_render_used") is False
        and selection.get("message_body_independently_hash_bound") is True
        and declared_control_set == REQUIRED_TEMPLATE_CONTROLS
        and template.get("send_policy") == "HUMAN_ACTION_DUE"
        and template.get("attachment_policy") == "NONE"
    )
    body_custody_holds = (
        SHA256_RE.fullmatch(str(message.get("body_sha256") or "")) is not None
        and str(message["body_sha256"]).upper() == body_sha256
        and message.get("body_bytes") == len(body_bytes)
    )
    deadline_order_holds = generated < partner_target < government_deadline
    route_holds = bool(
        route_fields_present
        and route_urls_public
        and recipient.get("public_route_verified") is True
        and recipient.get("recipient_address_stored_in_public_gate") is False
    )
    preflight_holds = bool(
        preflight_checked
        <= draft_created
        <= draft_updated
        <= draft_readback_checked
        <= generated
        and preflight.get("matching_messages_before_draft") == 0
        and preflight.get("decision") == "NO_DUPLICATE_FOUND"
    )
    duplicate_holds = bool(
        0 <= duplicate_age <= MAILBOX_RECHECK_MAX_AGE_SECONDS
        and duplicate_checked >= draft_created
        and duplicate_counts_hold
        and duplicate.get("decision") == "NO_DUPLICATE_ONLY_CURRENT_DRAFT"
    )
    draft_holds = bool(
        0 <= draft_readback_age <= DRAFT_READBACK_MAX_AGE_SECONDS
        and draft.get("draft_present") is True
        and draft.get("subject_matches") is True
        and draft.get("body_matches_source_after_newline_normalization") is True
        and draft.get("recipient_route_matches") is True
        and draft.get("attachment_count") == 0
        and draft.get("cc_count") == 0
        and draft.get("bcc_count") == 0
        and draft.get("gmail_identifiers_stored_in_public_gate") is False
        and draft.get("sent") is False
    )
    zero_attachment_holds = all(
        message.get(field) == 0
        for field in ("attachment_count", "cc_count", "bcc_count")
    )
    message_declarations_hold = bool(
        message.get("official_notice_link_present") is True
        and message.get("duplicate_disclosure_present") is True
        and zero_attachment_holds
    )
    control_holds = bool(
        controls.get("draft_creation_authorizes_send") is False
        and controls.get("single_use_action_time_approval_required") is True
        and controls.get("fresh_duplicate_recheck_required_before_send") is True
        and controls.get(
            "final_subject_body_recipient_and_attachment_set_must_match"
        )
        is True
        and controls.get(
            "partner_name_use_in_government_response_requires_written_authorization"
        )
        is True
        and controls.get("approval_binding_required") is True
        and controls.get("approval_window_seconds") == APPROVAL_WINDOW_SECONDS
        and controls.get("dispatch_binding_path")
        == DEFAULT_JSON.relative_to(ROOT).as_posix()
        and controls.get("builder_can_send") is False
    )

    checks = [
        check_row(
            "REGISTRY_BINDING",
            "The selected teaming template and registry hashes are current.",
            registry_current,
            (
                f"template_id={template_id}; "
                f"template_matches={len(matching_templates)}"
            ),
        ),
        check_row(
            "PUBLIC_RECIPIENT_ROUTE",
            "The named organization route is public, verified, and address-redacted.",
            route_holds,
            (
                f"organization={recipient.get('organization')}; "
                f"public_route_verified={recipient.get('public_route_verified')}"
            ),
        ),
        check_row(
            "SUBJECT_SAFETY",
            "The exact subject is nonempty, bounded, and header-safe.",
            subject_safe,
            f"subject_chars={len(subject)}; subject_sha256={subject_sha256}",
        ),
        check_row(
            "BODY_CUSTODY",
            "The declared body bytes and SHA-256 match the committed source.",
            body_custody_holds,
            f"body_bytes={len(body_bytes)}; body_sha256={body_sha256}",
        ),
        check_row(
            "BODY_BOUNDARIES",
            "The body preserves the notice, qualification, no-attachment, duplicate, and nonbinding controls.",
            body_content_safe,
            (
                f"required_markers_present={body_markers_present}; "
                f"official_notice_present={isinstance(official_notice_url, str) and official_notice_url in body}; "
                f"forbidden_promotion_phrase_count="
                f"{sum(marker in normalized_body.casefold() for marker in FORBIDDEN_PROMOTION_PHRASES)}"
            ),
        ),
        check_row(
            "DEADLINE_ORDER",
            "The snapshot precedes the partner target, which precedes the Government deadline.",
            deadline_order_holds,
            (
                f"generated_utc={utc_iso(generated)}; "
                f"partner_target_utc={utc_iso(partner_target)}; "
                f"government_deadline_utc={utc_iso(government_deadline)}"
            ),
        ),
        check_row(
            "PRE_DRAFT_DUPLICATE_CHECK",
            "The full-mailbox preflight found no pre-existing matching message.",
            preflight_holds,
            (
                f"checked_utc={utc_iso(preflight_checked)}; "
                f"matching_before_draft={preflight.get('matching_messages_before_draft')}"
            ),
        ),
        check_row(
            "FRESH_DUPLICATE_RECHECK",
            "The snapshot has one current draft and no sent or received duplicate.",
            duplicate_holds,
            (
                f"age_seconds={int(duplicate_age)}; "
                f"current_drafts={matching_current_draft_count}; "
                f"sent_or_received={matching_sent_or_received_count}"
            ),
        ),
        check_row(
            "FRESH_DRAFT_READBACK",
            "The current Gmail draft readback matches the exact route, subject, body, and empty attachment set.",
            draft_holds,
            (
                f"age_seconds={int(draft_readback_age)}; "
                f"draft_present={draft.get('draft_present')}; "
                f"sent={draft.get('sent')}"
            ),
        ),
        check_row(
            "ZERO_ATTACHMENT_SET",
            "The message, CC, BCC, and attachment counts are all zero.",
            zero_attachment_holds,
            (
                f"attachments={message.get('attachment_count')}; "
                f"cc={message.get('cc_count')}; bcc={message.get('bcc_count')}"
            ),
        ),
        check_row(
            "MESSAGE_DECLARATIONS",
            "The public gate records the official-link and duplicate disclosures.",
            message_declarations_hold,
            (
                f"official_notice={message.get('official_notice_link_present')}; "
                f"duplicate_disclosure={message.get('duplicate_disclosure_present')}"
            ),
        ),
        check_row(
            "FAIL_CLOSED_CONTROLS",
            "The builder cannot send and the exact approval is binding-scoped and time-limited.",
            control_holds,
            (
                f"builder_can_send={controls.get('builder_can_send')}; "
                f"approval_window_seconds={controls.get('approval_window_seconds')}"
            ),
        ),
    ]
    failed_checks = [
        row["check_id"] for row in checks if row["status"] == "FAIL"
    ]

    route_binding_core = {
        "organization": recipient.get("organization"),
        "named_addressee": recipient.get("named_addressee"),
        "route_type": recipient.get("route_type"),
        "official_contact_source": recipient.get("official_contact_source"),
        "official_partnership_source": recipient.get(
            "official_partnership_source"
        ),
    }
    mailbox_receipt_core = {
        "checked_utc": utc_iso(duplicate_checked),
        "search_scope": duplicate.get("search_scope"),
        "matching_message_count": matching_message_count,
        "matching_current_draft_count": matching_current_draft_count,
        "matching_sent_or_received_count": matching_sent_or_received_count,
        "decision": duplicate.get("decision"),
    }
    draft_receipt_core = {
        "created_utc": utc_iso(draft_created),
        "updated_utc": utc_iso(draft_updated),
        "readback_checked_utc": utc_iso(draft_readback_checked),
        "draft_present": draft.get("draft_present"),
        "subject_matches": draft.get("subject_matches"),
        "body_matches_source_after_newline_normalization": draft.get(
            "body_matches_source_after_newline_normalization"
        ),
        "recipient_route_matches": draft.get("recipient_route_matches"),
        "attachment_count": draft.get("attachment_count"),
        "cc_count": draft.get("cc_count"),
        "bcc_count": draft.get("bcc_count"),
        "sent": draft.get("sent"),
    }
    empty_attachment_set_sha256 = canonical_object_sha256({"attachments": []})
    binding = None
    approval_phrase = None
    approval_expires = generated + timedelta(seconds=APPROVAL_WINDOW_SECONDS)
    if not failed_checks:
        binding_core = {
            "schema": BINDING_SCHEMA,
            "template_id": template_id,
            "registry_source_config_sha256": public_registry.get(
                "source_config_sha256"
            ),
            "template_canonical_sha256": expected_template_sha256,
            "recipient_route_sha256": canonical_object_sha256(route_binding_core),
            "gmail_route_readback_receipt_sha256": canonical_object_sha256(
                draft_receipt_core
            ),
            "subject_sha256": subject_sha256,
            "body_sha256": body_sha256,
            "body_bytes": len(body_bytes),
            "official_notice_url_sha256": sha256_bytes(
                str(official_notice_url).encode("utf-8")
            ),
            "government_deadline_utc": utc_iso(government_deadline),
            "partner_interest_target_utc": utc_iso(partner_target),
            "mailbox_duplicate_receipt_sha256": canonical_object_sha256(
                mailbox_receipt_core
            ),
            "attachment_count": 0,
            "cc_count": 0,
            "bcc_count": 0,
            "attachment_set_sha256": empty_attachment_set_sha256,
            "approval_window_opened_utc": utc_iso(generated),
            "approval_window_expires_utc": utc_iso(approval_expires),
            "single_use": True,
        }
        binding = {
            **binding_core,
            "binding_sha256": canonical_object_sha256(binding_core),
        }
        approval_phrase = (
            "APPROVE ONE ARGOS TEAMING DISPATCH: "
            f"recipient {recipient['organization']} / "
            f"{recipient['named_addressee']}; "
            f"template {template_id}; "
            f"binding SHA-256 {binding['binding_sha256']}; "
            f"subject SHA-256 {subject_sha256}; "
            f"body SHA-256 {body_sha256}; "
            f"attachment set SHA-256 {empty_attachment_set_sha256}; "
            f"expires {utc_iso(approval_expires)}."
        )

    snapshot_ready = not failed_checks
    decision = (
        "VERIFIED_SNAPSHOT_READY_FOR_SINGLE_USE_ACTION_TIME_APPROVAL"
        if snapshot_ready
        else "BLOCKED_DISPATCH_GATE_INTEGRITY"
    )
    return {
        "schema": OUTPUT_SCHEMA,
        "generated_utc": utc_iso(generated),
        "source_gate": SOURCE_GATE.relative_to(ROOT).as_posix(),
        "source_gate_sha256": sha256_bytes(SOURCE_GATE.read_bytes())
        if source_gate is None
        else None,
        "decision": decision,
        "summary": {
            "check_count": len(checks),
            "pass_count": len(checks) - len(failed_checks),
            "fail_count": len(failed_checks),
            "snapshot_ready_for_exact_approval": snapshot_ready,
            "approval_received": False,
            "send_authorized": False,
            "send_performed": False,
            "external_action_performed": False,
        },
        "checks": checks,
        "failed_checks": failed_checks,
        "dispatch_binding": binding,
        "approval_window": {
            "opened_utc": utc_iso(generated),
            "expires_utc": utc_iso(approval_expires),
            "window_seconds": APPROVAL_WINDOW_SECONDS,
            "current_wall_clock_evaluation_required": True,
            "fresh_mailbox_and_draft_readback_required_for_each_new_window": True,
        },
        "exact_action_time_approval_phrase": approval_phrase,
        "controls": {
            "builder_can_send": False,
            "draft_creation_authorizes_send": False,
            "approval_phrase_authorizes_send_without_current_validation": False,
            "single_use_action_time_approval_required": True,
            "recipient_route_must_be_reverified_at_send": True,
            "subject_body_and_empty_attachment_set_must_match": True,
        },
        "claim_boundary": (
            "This artifact validates one historical draft snapshot and derives a "
            "time-limited binding. It does not send email, prove current mailbox "
            "state, authorize partner-name use, certify qualifications, submit a "
            "Government response, prove receipt, or establish selection, award, "
            "funding, field performance, validation, or savings."
        ),
        "safest_next_action": (
            "At action time, repeat the full-mailbox duplicate search and Gmail "
            "draft readback, update the duplicate counts and the separate "
            "readback_checked_utc receipt, rebuild this binding, then accept only "
            "the newly displayed unexpired exact approval phrase. Do not send if "
            "any bound field changes."
        ),
    }


def evaluate_action_time(
    payload: dict[str, Any],
    current_utc: str | None = None,
) -> dict[str, Any]:
    now = (
        parse_utc(current_utc, "CURRENT_UTC")
        if current_utc
        else datetime.now(timezone.utc)
    )
    expires = parse_utc(
        payload["approval_window"]["expires_utc"],
        "APPROVAL_EXPIRES_UTC",
    )
    snapshot_ready = bool(
        payload.get("summary", {}).get("snapshot_ready_for_exact_approval")
    )
    current = snapshot_ready and now <= expires
    return {
        "schema": "lumencore.initial_outreach_action_time_state.v1",
        "evaluated_utc": utc_iso(now),
        "approval_expires_utc": utc_iso(expires),
        "approval_window_current": current,
        "decision": (
            "CURRENT_EXACT_APPROVAL_WINDOW"
            if current
            else "EXPIRED_OR_BLOCKED_REBUILD_REQUIRED"
        ),
        "send_authorized": False,
        "send_performed": False,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Argos EMI Teaming Dispatch Binding",
        "",
        f"- Decision: `{payload['decision']}`",
        f"- Snapshot UTC: `{payload['generated_utc']}`",
        (
            "- Checks: "
            f"`{summary['pass_count']}/{summary['check_count']}` passed; "
            f"`{summary['fail_count']}` failed"
        ),
        "- Send authorized: `false`",
        "- Send performed: `false`",
        (
            "- Approval window: "
            f"`{payload['approval_window']['opened_utc']}` through "
            f"`{payload['approval_window']['expires_utc']}`"
        ),
        "",
        "## Conformance Checks",
        "",
        "| Check | Status | Requirement | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for row in payload["checks"]:
        requirement = row["requirement"].replace("|", r"\|")
        evidence = row["evidence"].replace("|", r"\|")
        lines.append(
            f"| `{row['check_id']}` | `{row['status']}` | "
            f"{requirement} | {evidence} |"
        )
    lines.extend(
        [
            "",
            "## Exact Approval",
            "",
            (
                f"`{payload['exact_action_time_approval_phrase']}`"
                if payload["exact_action_time_approval_phrase"]
                else "`WITHHELD_UNTIL_ALL_CHECKS_PASS`"
            ),
            "",
            "The displayed phrase is single-use and expires at the stated UTC "
            "time. Current mailbox and draft validation remain mandatory.",
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
            "## Safest Next Action",
            "",
            payload["safest_next_action"],
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the fail-closed, time-limited Argos partner-outreach binding."
        )
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--action-time-check", action="store_true")
    parser.add_argument(
        "--current-utc",
        help="Aware timestamp for an explicit action-time expiry check.",
    )
    args = parser.parse_args()

    payload = build_payload()
    expected_json = json_text(payload)
    expected_markdown = render_markdown(payload)
    if args.action_time_check:
        state = evaluate_action_time(payload, args.current_utc)
        print(json.dumps(state, indent=2, sort_keys=True))
        return 0 if state["approval_window_current"] else 3
    if args.check:
        current = (
            DEFAULT_JSON.is_file()
            and DEFAULT_MARKDOWN.is_file()
            and DEFAULT_JSON.read_text(encoding="utf-8") == expected_json
            and DEFAULT_MARKDOWN.read_text(encoding="utf-8")
            == expected_markdown
        )
        print(
            json.dumps(
                {
                    "status": "CURRENT" if current else "STALE",
                    "decision": payload["decision"],
                    "check_count": payload["summary"]["check_count"],
                    "pass_count": payload["summary"]["pass_count"],
                    "fail_count": payload["summary"]["fail_count"],
                    "send_authorized": False,
                    "send_performed": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if current else 1

    write_text(DEFAULT_JSON, expected_json)
    write_text(DEFAULT_MARKDOWN, expected_markdown)
    print(
        json.dumps(
            {
                "status": "BUILT",
                "decision": payload["decision"],
                "check_count": payload["summary"]["check_count"],
                "pass_count": payload["summary"]["pass_count"],
                "fail_count": payload["summary"]["fail_count"],
                "json": DEFAULT_JSON.relative_to(ROOT).as_posix(),
                "markdown": DEFAULT_MARKDOWN.relative_to(ROOT).as_posix(),
                "send_authorized": False,
                "send_performed": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
