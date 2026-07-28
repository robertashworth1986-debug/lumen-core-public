from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import string
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "outreach_response_templates_v1.json"
CLAIM_EVIDENCE_TEMPLATE = (
    ROOT / "config" / "outreach_claim_evidence_receipt_template_v1.json"
)
ACTION_TIME_MAILBOX_RECEIPT_TEMPLATE = (
    ROOT / "config" / "outreach_action_time_mailbox_receipt_template_v1.json"
)
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
OUT_JSON = SPRINT_DIR / "OUTREACH_RESPONSE_TEMPLATE_REGISTRY_2026-07-18.json"
OUT_MD = SPRINT_DIR / "OUTREACH_RESPONSE_TEMPLATE_REGISTRY_2026-07-18.md"
LATEST_JSON = OUT_OPS / "outreach_response_template_registry_latest.json"

SCHEMA = "lumencore.outreach_response_templates.v1"
PUBLIC_SCHEMA = "lumencore.outreach_response_template_registry.v1"
VALID_SEND_POLICIES = {
    "MONITOR_NO_SEND",
    "REPLY_AFTER_FACT_REVIEW",
    "HUMAN_ACTION_DUE",
}
VALID_ATTACHMENT_POLICIES = {
    "NONE",
    "EXPLICIT_REQUEST_ONLY",
}
TEMPLATE_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SENDABLE_IDENTITY_FIELDS = {
    "recipient_name",
    "sender_name",
    "sender_title",
    "organization_name",
}
MAX_RENDERED_SUBJECT_CHARS = 200
MAX_RENDERED_BODY_CHARS = 5000
POSITIVE_CLAIM_MARKERS = (
    "guaranteed funding",
    "guaranteed savings",
    "government-approved",
    "independently validated performance",
    "field-proven performance",
    "certified safe",
    "will save",
)
CLAIM_EVIDENCE_RECEIPT_SCHEMA = (
    "lumencore.outreach_claim_evidence_receipt.v1"
)
DISPATCH_BINDING_SCHEMA = "lumencore.outreach_dispatch_binding.v1"
ACTION_TIME_MAILBOX_RECEIPT_SCHEMA = (
    "lumencore.outreach_action_time_mailbox_receipt.v1"
)
ACTION_TIME_AUTHORIZATION_SCHEMA = (
    "lumencore.outreach_action_time_authorization.v1"
)
ACTION_TIME_APPROVAL_BINDING_SCHEMA = (
    "lumencore.outreach_action_time_approval_binding.v1"
)
ACTION_TIME_MAILBOX_MAX_AGE_SECONDS = 15 * 60
ACTION_TIME_APPROVAL_WINDOW_SECONDS = 5 * 60
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
CLAIM_EVIDENCE_RECEIPT_FIELDS = {
    "claim_allowed",
    "fact_field",
    "fact_value_sha256",
    "receipt_sha256",
    "review_basis",
    "reviewed_utc",
    "risk_codes",
    "schema",
    "source_artifacts",
}
CLAIM_RISK_PATTERNS = {
    "UNSUPPORTED_GUARANTEE": re.compile(r"\bguarantee(?:d|s)?\b", re.IGNORECASE),
    "UNSUPPORTED_SUPERLATIVE": re.compile(
        r"(?:\bbest[- ]in[- ]class\b|\bworld(?:'s)?[- ]best\b|"
        r"\bunbeatable\b|#\s*1\b|\bsuperior to all\b)",
        re.IGNORECASE,
    ),
    "UNSUPPORTED_EXTERNAL_VALIDATION": re.compile(
        r"\b(?:independently|externally)\s+"
        r"(?:reproduced|validated|verified)\b",
        re.IGNORECASE,
    ),
    "UNSUPPORTED_FIELD_PERFORMANCE": re.compile(
        r"\b(?:field|production)[- ](?:proven|validated)\b|"
        r"\bdeployed in production\b",
        re.IGNORECASE,
    ),
    "UNSUPPORTED_ECONOMIC_OUTCOME": re.compile(
        r"\b(?:realized|validated|proven)\s+(?:annual\s+)?savings\b|"
        r"\bwill save\b|\bsaved\s+\$|"
        r"\$[\d,.]+\s*(?:million|billion|m|b)?\s+"
        r"(?:in\s+)?(?:annual\s+)?(?:savings|value)\b",
        re.IGNORECASE,
    ),
    "UNSUPPORTED_AGENCY_ACCEPTANCE": re.compile(
        r"\b(?:government|federal|agency)[- ](?:approved|accepted)\b|"
        r"\baccepted by (?:darpa|dod|doe|nasa|nsf|epri|lanl)\b",
        re.IGNORECASE,
    ),
    "UNSUPPORTED_AWARD_OR_CONTRACT": re.compile(
        r"\b(?:won|received|awarded)\s+(?:an?\s+)?"
        r"(?:grant|contract|award)\b",
        re.IGNORECASE,
    ),
    "UNSUPPORTED_CUSTOMER_TRACTION": re.compile(
        r"\b(?:paying customer|customer revenue|commercial deployment)\b",
        re.IGNORECASE,
    ),
    "UNSUPPORTED_BASELINE_SUPERIORITY": re.compile(
        r"\b(?:outperforms?|beats?)\s+"
        r"(?:all|every|the incumbent|the baseline)\b",
        re.IGNORECASE,
    ),
}
ACTION_TIME_MAILBOX_RECEIPT_FIELDS = {
    "attachment_count",
    "attachment_set_sha256",
    "bcc_count",
    "body_sha256",
    "cc_count",
    "checked_utc",
    "current_draft_only",
    "draft_present",
    "draft_readback_checked_utc",
    "draft_sent",
    "full_mailbox_search_completed",
    "identifiers_omitted",
    "matching_current_draft_count",
    "matching_received_after_draft_count",
    "matching_sent_count",
    "message_body_omitted",
    "recipient_route_sha256",
    "schema",
    "search_scope",
    "source_message_id_sha256",
    "subject_sha256",
}
NEGATION_WINDOW_RE = re.compile(
    r"\b(?:no|not|never|without|unverified|unproven)\b",
    re.IGNORECASE,
)


class OutreachRegistryError(ValueError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise OutreachRegistryError(f"DUPLICATE_JSON_KEY:{key}")
        result[key] = value
    return result


def read_registry(path: Path = CONFIG) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )
    if not isinstance(payload, dict):
        raise OutreachRegistryError("REGISTRY_NOT_OBJECT")
    return payload


def validate_action_time_mailbox_receipt_template(
    path: Path = ACTION_TIME_MAILBOX_RECEIPT_TEMPLATE,
) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )
    if not isinstance(payload, dict):
        raise OutreachRegistryError(
            "ACTION_TIME_MAILBOX_RECEIPT_TEMPLATE_NOT_OBJECT"
        )
    if set(payload) != ACTION_TIME_MAILBOX_RECEIPT_FIELDS:
        raise OutreachRegistryError(
            "ACTION_TIME_MAILBOX_RECEIPT_TEMPLATE_FIELDS_INVALID"
        )
    if payload.get("schema") != ACTION_TIME_MAILBOX_RECEIPT_SCHEMA:
        raise OutreachRegistryError(
            "ACTION_TIME_MAILBOX_RECEIPT_TEMPLATE_SCHEMA_INVALID"
        )
    expected_non_authorizing_values = {
        "attachment_count": 0,
        "attachment_set_sha256": None,
        "bcc_count": 0,
        "body_sha256": None,
        "cc_count": 0,
        "checked_utc": None,
        "current_draft_only": False,
        "draft_present": False,
        "draft_readback_checked_utc": None,
        "draft_sent": False,
        "full_mailbox_search_completed": False,
        "identifiers_omitted": True,
        "matching_current_draft_count": 0,
        "matching_received_after_draft_count": 0,
        "matching_sent_count": 0,
        "message_body_omitted": True,
        "recipient_route_sha256": None,
        "search_scope": "ALL_MAIL_BOUND_ROUTE_THREAD_SUBJECT_BODY",
        "source_message_id_sha256": None,
        "subject_sha256": None,
    }
    for field, expected in expected_non_authorizing_values.items():
        if payload.get(field) != expected:
            raise OutreachRegistryError(
                "ACTION_TIME_MAILBOX_RECEIPT_TEMPLATE_MUST_NOT_AUTHORIZE:"
                f"{field}"
            )
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
            bounded, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )


def _normalize_attachment_files(raw_attachments: Any) -> list[str]:
    attachments = raw_attachments or []
    if not isinstance(attachments, list) or not all(
        isinstance(item, str) and item.strip() for item in attachments
    ):
        raise OutreachRegistryError("ATTACHMENT_LIST_INVALID")
    normalized = [item.strip() for item in attachments]
    names = [item.casefold() for item in normalized]
    if len(names) != len(set(names)):
        raise OutreachRegistryError("DUPLICATE_ATTACHMENT_NAME")
    return normalized


def _attachment_binding(
    attachments: list[str],
    attachment_sha256s: dict[str, str] | None,
) -> tuple[list[dict[str, str | None]], str, bool]:
    supplied: Any = {} if attachment_sha256s is None else attachment_sha256s
    if not isinstance(supplied, dict) or not all(
        isinstance(name, str) and name.strip() and isinstance(digest, str)
        for name, digest in supplied.items()
    ):
        raise OutreachRegistryError("ATTACHMENT_SHA256_MAP_INVALID")

    normalized_supplied: dict[str, str] = {}
    for name, digest in supplied.items():
        normalized_name = name.strip().casefold()
        if normalized_name in normalized_supplied:
            raise OutreachRegistryError("DUPLICATE_ATTACHMENT_HASH_NAME")
        if not SHA256_RE.fullmatch(digest.strip()):
            raise OutreachRegistryError("ATTACHMENT_SHA256_INVALID")
        normalized_supplied[normalized_name] = digest.strip().upper()

    attachment_names = {name.casefold() for name in attachments}
    if normalized_supplied and set(normalized_supplied) != attachment_names:
        raise OutreachRegistryError("ATTACHMENT_HASH_SET_MISMATCH")

    hashes_bound = not attachments or set(normalized_supplied) == attachment_names
    entries = sorted(
        (
            {
                "name_sha256": sha256_bytes(name.casefold().encode("utf-8")),
                "content_sha256": normalized_supplied.get(name.casefold()),
            }
            for name in attachments
        ),
        key=lambda item: item["name_sha256"],
    )
    attachment_set_sha256 = canonical_object_sha256({"attachments": entries})
    return entries, attachment_set_sha256, hashes_bound


def _dispatch_binding(
    *,
    payload: dict[str, Any],
    row: dict[str, Any],
    facts: dict[str, Any],
    subject: str,
    body: str,
    rendered_deadline_iso: str | None,
    attachment_entries: list[dict[str, str | None]],
    attachment_set_sha256: str,
    attachment_content_hashes_bound: bool,
    evidence_receipt_sha256s: dict[str, str],
    already_sent: bool,
    inbound_requires_response: bool,
    explicit_attachment_request: bool,
) -> dict[str, Any]:
    recipient_route = str(facts["recipient_email"]).strip().casefold()
    source_message_id = str(facts.get("source_message_id") or "").strip()
    core = {
        "schema": DISPATCH_BINDING_SCHEMA,
        "template_id": row["template_id"],
        "registry_source_config_sha256": canonical_object_sha256(payload),
        "recipient_route_sha256": sha256_bytes(recipient_route.encode("utf-8")),
        "source_message_id_sha256": (
            sha256_bytes(source_message_id.encode("utf-8"))
            if source_message_id
            else None
        ),
        "subject_sha256": sha256_bytes(subject.encode("utf-8")),
        "body_sha256": sha256_bytes(body.encode("utf-8")),
        "deadline_utc": rendered_deadline_iso,
        "send_policy": row["send_policy"],
        "attachment_policy": row["attachment_policy"],
        "attachment_count": len(attachment_entries),
        "attachment_entries": attachment_entries,
        "attachment_set_sha256": attachment_set_sha256,
        "attachment_content_hashes_bound": attachment_content_hashes_bound,
        "claim_evidence_receipt_sha256s": dict(
            sorted(evidence_receipt_sha256s.items())
        ),
        "duplicate_send_state": {
            "already_sent": already_sent,
            "inbound_requires_response": inbound_requires_response,
        },
        "explicit_attachment_request": explicit_attachment_request,
    }
    return {**core, "binding_sha256": canonical_object_sha256(core)}


def _rooted_artifact(path_value: Any) -> Path:
    if not isinstance(path_value, str) or not path_value.strip():
        raise OutreachRegistryError("CLAIM_EVIDENCE_PATH_INVALID")
    path = Path(path_value)
    if path.is_absolute():
        raise OutreachRegistryError("CLAIM_EVIDENCE_PATH_MUST_BE_RELATIVE")
    resolved = (ROOT / path).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise OutreachRegistryError("CLAIM_EVIDENCE_PATH_OUTSIDE_ROOT") from exc
    if not resolved.is_file():
        raise OutreachRegistryError("CLAIM_EVIDENCE_FILE_MISSING")
    return resolved


def _assertion_is_negated(text: str, match_start: int) -> bool:
    window = text[max(0, match_start - 40) : match_start]
    boundary = max(window.rfind("."), window.rfind(";"), window.rfind("\n"))
    if boundary >= 0:
        window = window[boundary + 1 :]
    return bool(NEGATION_WINDOW_RE.search(window))


def claim_fact_risks(facts: dict[str, Any]) -> dict[str, list[str]]:
    risks: dict[str, list[str]] = {}
    for field, raw_value in facts.items():
        if field in {"attachment_files"} or field.endswith("_email"):
            continue
        if not isinstance(raw_value, str) or not raw_value.strip():
            continue
        codes = []
        for code, pattern in CLAIM_RISK_PATTERNS.items():
            matches = [
                match
                for match in pattern.finditer(raw_value)
                if not _assertion_is_negated(raw_value, match.start())
            ]
            if matches:
                codes.append(code)
        if codes:
            risks[field] = sorted(codes)
    return dict(sorted(risks.items()))


def validate_claim_evidence_receipt(
    receipt_path: str,
    *,
    fact_field: str,
    fact_value: str,
    risk_codes: list[str],
) -> str:
    path = _rooted_artifact(receipt_path)
    try:
        receipt = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise OutreachRegistryError("CLAIM_EVIDENCE_RECEIPT_INVALID_JSON") from exc
    if not isinstance(receipt, dict):
        raise OutreachRegistryError("CLAIM_EVIDENCE_RECEIPT_NOT_OBJECT")
    if set(receipt) != CLAIM_EVIDENCE_RECEIPT_FIELDS:
        raise OutreachRegistryError("CLAIM_EVIDENCE_RECEIPT_FIELDS_INVALID")
    if receipt.get("schema") != CLAIM_EVIDENCE_RECEIPT_SCHEMA:
        raise OutreachRegistryError("CLAIM_EVIDENCE_RECEIPT_SCHEMA_INVALID")
    if receipt.get("claim_allowed") is not True:
        raise OutreachRegistryError("CLAIM_EVIDENCE_NOT_APPROVED")
    if receipt.get("fact_field") != fact_field:
        raise OutreachRegistryError("CLAIM_EVIDENCE_FIELD_MISMATCH")
    expected_value_sha = sha256_bytes(fact_value.strip().encode("utf-8"))
    if receipt.get("fact_value_sha256") != expected_value_sha:
        raise OutreachRegistryError("CLAIM_EVIDENCE_VALUE_MISMATCH")
    if sorted(receipt.get("risk_codes") or []) != sorted(risk_codes):
        raise OutreachRegistryError("CLAIM_EVIDENCE_RISK_MISMATCH")
    if not isinstance(receipt.get("review_basis"), str) or not receipt[
        "review_basis"
    ].strip():
        raise OutreachRegistryError("CLAIM_EVIDENCE_REVIEW_BASIS_MISSING")
    try:
        parse_aware_datetime(str(receipt.get("reviewed_utc") or ""))
    except OutreachRegistryError as exc:
        raise OutreachRegistryError(
            "CLAIM_EVIDENCE_REVIEWED_UTC_INVALID"
        ) from exc

    sources = receipt.get("source_artifacts")
    if not isinstance(sources, list) or not sources:
        raise OutreachRegistryError("CLAIM_EVIDENCE_SOURCES_MISSING")
    for source in sources:
        if not isinstance(source, dict) or set(source) != {"path", "sha256"}:
            raise OutreachRegistryError("CLAIM_EVIDENCE_SOURCE_INVALID")
        source_path = _rooted_artifact(source["path"])
        if source_path == path:
            raise OutreachRegistryError("CLAIM_EVIDENCE_SOURCE_IS_RECEIPT")
        if sha256_bytes(source_path.read_bytes()) != source["sha256"]:
            raise OutreachRegistryError("CLAIM_EVIDENCE_SOURCE_HASH_MISMATCH")

    expected_receipt_sha = canonical_object_sha256(
        receipt, omit={"receipt_sha256"}
    )
    if receipt.get("receipt_sha256") != expected_receipt_sha:
        raise OutreachRegistryError("CLAIM_EVIDENCE_RECEIPT_HASH_MISMATCH")
    return expected_receipt_sha


def template_placeholders(text: str) -> set[str]:
    names: set[str] = set()
    for _, field_name, _, _ in string.Formatter().parse(text):
        if field_name:
            if any(token in field_name for token in (".", "[", "]")):
                raise OutreachRegistryError(
                    f"UNSAFE_PLACEHOLDER_EXPRESSION:{field_name}"
                )
            names.add(field_name)
    return names


def _string_list(value: Any, code: str) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise OutreachRegistryError(code)
    return value


def deadline_control_required(row: dict[str, Any]) -> bool:
    return any(
        field in {"deadline_iso", "deadline_local"}
        or field.endswith("_deadline_local")
        for field in row["required_fields"]
    )


def template_quality_profile(row: dict[str, Any]) -> dict[str, Any]:
    template_id = str(row["template_id"])
    required_list = list(row["required_fields"])
    routing_list = list(row["routing_fields"])
    sensitive_list = list(row["sensitive_fields"])
    default_fields = set(row["optional_defaults"])
    required = set(required_list)
    routing = set(routing_list)
    sensitive = set(sensitive_list)
    placeholders = template_placeholders(row["subject"] + "\n" + row["body"])
    sendable = row["send_policy"] != "MONITOR_NO_SEND"
    deadline_required = deadline_control_required(row)
    url_fields = sorted(field for field in required if field.endswith("_url"))

    checks = {
        "field_lists_have_no_duplicates": all(
            len(values) == len(set(values))
            for values in (required_list, routing_list, sensitive_list)
        ),
        "field_declarations_are_disjoint": not (
            required.intersection(routing)
            or required.intersection(default_fields)
            or routing.intersection(default_fields)
        ),
        "all_required_fields_are_rendered": not (required - placeholders),
        "all_routing_fields_are_sensitive": routing.issubset(sensitive),
        "nonrouting_sensitive_fields_force_private_render": (
            not (sensitive - routing) or row["private_render_only"] is True
        ),
        "sendable_identity_fields_are_required": (
            not sendable or SENDABLE_IDENTITY_FIELDS.issubset(required)
        ),
        "sendable_recipient_route_is_required": (
            not sendable or "recipient_email" in routing
        ),
        "sendable_template_has_greeting_and_signature": (
            not sendable
            or (
                row["body"].startswith("Hello {recipient_name},")
                and "{sender_name}" in row["body"]
                and "{sender_title}" in row["body"]
                and "{organization_name}" in row["body"]
            )
        ),
        "monitor_template_is_content_free": (
            sendable
            or (
                not row["subject"]
                and not row["body"]
                and not required
                and not routing
                and not sensitive
                and not default_fields
                and row["attachment_policy"] == "NONE"
            )
        ),
        "template_subject_is_single_line": (
            "\r" not in row["subject"] and "\n" not in row["subject"]
        ),
        "template_text_is_within_render_limits": (
            len(row["subject"]) <= MAX_RENDERED_SUBJECT_CHARS
            and len(row["body"]) <= MAX_RENDERED_BODY_CHARS
        ),
        "known_deadline_uses_single_structured_value": (
            not deadline_required
            or (
                "deadline_iso" in required
                and "deadline_iso" in placeholders
                and not any(
                    field == "deadline_local"
                    or field.endswith("_deadline_local")
                    for field in required
                )
            )
        ),
    }
    failures = sorted(name for name, passed in checks.items() if not passed)
    return {
        "template_id": template_id,
        "status": "PASS" if not failures else "FAIL",
        "checks": checks,
        "failed_checks": failures,
        "deadline_iso_control_required": deadline_required,
        "https_public_url_fields": url_fields,
    }


def is_public_https_url(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip() or any(
        char.isspace() for char in value
    ):
        return False
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return False
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or port not in (None, 443)
    ):
        return False
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".local"):
        return False
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return True
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
    )


def validate_registry(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema") != SCHEMA:
        raise OutreachRegistryError("SCHEMA_MISMATCH")
    if payload.get("version") != 1:
        raise OutreachRegistryError("VERSION_MISMATCH")
    source_effective_utc = payload.get("source_effective_utc")
    if not isinstance(source_effective_utc, str) or not source_effective_utc.strip():
        raise OutreachRegistryError("SOURCE_EFFECTIVE_UTC_MISSING")
    parse_aware_datetime(source_effective_utc)
    if not isinstance(payload.get("claim_boundary"), str) or not payload[
        "claim_boundary"
    ].strip():
        raise OutreachRegistryError("CLAIM_BOUNDARY_MISSING")
    rules = _string_list(payload.get("global_rules"), "GLOBAL_RULES_INVALID")
    if len(rules) < 6:
        raise OutreachRegistryError("GLOBAL_RULES_INCOMPLETE")

    templates = payload.get("templates")
    if not isinstance(templates, list) or len(templates) < 8:
        raise OutreachRegistryError("TEMPLATE_SET_INCOMPLETE")

    seen: set[str] = set()
    for row in templates:
        if not isinstance(row, dict):
            raise OutreachRegistryError("TEMPLATE_NOT_OBJECT")
        template_id = str(row.get("template_id") or "")
        if not TEMPLATE_ID_RE.fullmatch(template_id):
            raise OutreachRegistryError(f"TEMPLATE_ID_INVALID:{template_id}")
        if template_id in seen:
            raise OutreachRegistryError(f"TEMPLATE_ID_DUPLICATE:{template_id}")
        seen.add(template_id)

        send_policy = row.get("send_policy")
        if send_policy not in VALID_SEND_POLICIES:
            raise OutreachRegistryError(f"SEND_POLICY_INVALID:{template_id}")
        if row.get("attachment_policy") not in VALID_ATTACHMENT_POLICIES:
            raise OutreachRegistryError(f"ATTACHMENT_POLICY_INVALID:{template_id}")

        required = set(
            _string_list(row.get("required_fields"), f"REQUIRED_FIELDS_INVALID:{template_id}")
        )
        routing = set(
            _string_list(row.get("routing_fields"), f"ROUTING_FIELDS_INVALID:{template_id}")
        )
        sensitive = set(
            _string_list(row.get("sensitive_fields"), f"SENSITIVE_FIELDS_INVALID:{template_id}")
        )
        defaults = row.get("optional_defaults")
        if not isinstance(defaults, dict):
            raise OutreachRegistryError(f"OPTIONAL_DEFAULTS_INVALID:{template_id}")
        if not sensitive.issubset(required | routing | set(defaults)):
            raise OutreachRegistryError(f"SENSITIVE_FIELD_UNDECLARED:{template_id}")

        subject = row.get("subject")
        body = row.get("body")
        if not isinstance(subject, str) or not isinstance(body, str):
            raise OutreachRegistryError(f"TEMPLATE_TEXT_INVALID:{template_id}")
        if send_policy != "MONITOR_NO_SEND" and (not subject.strip() or not body.strip()):
            raise OutreachRegistryError(f"REPLY_TEMPLATE_EMPTY:{template_id}")
        if send_policy == "MONITOR_NO_SEND" and (subject.strip() or body.strip()):
            raise OutreachRegistryError(f"MONITOR_TEMPLATE_MUST_BE_EMPTY:{template_id}")

        placeholders = template_placeholders(subject + "\n" + body)
        declared = required | routing | set(defaults)
        undeclared = sorted(placeholders - declared)
        if undeclared:
            raise OutreachRegistryError(
                f"PLACEHOLDER_UNDECLARED:{template_id}:{','.join(undeclared)}"
            )

        lowered = (subject + "\n" + body).lower()
        for marker in POSITIVE_CLAIM_MARKERS:
            if marker in lowered:
                raise OutreachRegistryError(
                    f"UNSUPPORTED_POSITIVE_CLAIM:{template_id}:{marker}"
                )
        if UUID_RE.search(subject + "\n" + body):
            raise OutreachRegistryError(f"PRIVATE_IDENTIFIER_IN_TEMPLATE:{template_id}")

        _string_list(row.get("inbound_states"), f"INBOUND_STATES_INVALID:{template_id}")
        _string_list(row.get("reply_triggers"), f"REPLY_TRIGGERS_INVALID:{template_id}")
        if not isinstance(row.get("description"), str) or not row["description"].strip():
            raise OutreachRegistryError(f"DESCRIPTION_MISSING:{template_id}")
        if not isinstance(row.get("private_render_only"), bool):
            raise OutreachRegistryError(f"PRIVATE_FLAG_INVALID:{template_id}")
        quality = template_quality_profile(row)
        if quality["status"] != "PASS":
            raise OutreachRegistryError(
                f"QUALITY_GATE_FAILED:{template_id}:"
                f"{','.join(quality['failed_checks'])}"
            )

    return payload


def template_by_id(payload: dict[str, Any], template_id: str) -> dict[str, Any]:
    for row in payload["templates"]:
        if row["template_id"] == template_id:
            return row
    raise OutreachRegistryError(f"UNKNOWN_TEMPLATE:{template_id}")


def parse_aware_datetime(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise OutreachRegistryError("DEADLINE_INVALID") from exc
    if parsed.tzinfo is None:
        raise OutreachRegistryError("DEADLINE_TIMEZONE_REQUIRED")
    return parsed.astimezone(timezone.utc)


def canonical_utc(value: str) -> str:
    return parse_aware_datetime(value).isoformat().replace("+00:00", "Z")


def deadline_state(deadline_iso: str | None, current_utc: str | None = None) -> dict[str, Any]:
    if not deadline_iso:
        return {"provided": False, "urgency": "NOT_PROVIDED", "hours_remaining": None}
    deadline = parse_aware_datetime(deadline_iso)
    current = parse_aware_datetime(current_utc) if current_utc else datetime.now(timezone.utc)
    hours = (deadline - current).total_seconds() / 3600
    if hours <= 0:
        urgency = "PAST_DUE"
    elif hours <= 24:
        urgency = "CRITICAL_UNDER_24_HOURS"
    elif hours <= 72:
        urgency = "HIGH_UNDER_72_HOURS"
    else:
        urgency = "NORMAL"
    return {
        "provided": True,
        "deadline_utc": deadline.isoformat(),
        "urgency": urgency,
        "hours_remaining": round(hours, 2),
    }


def _base_result(
    payload: dict[str, Any], row: dict[str, Any], status: str, deadline: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema": "lumencore.outreach_response_render.v1",
        "template_id": row["template_id"],
        "status": status,
        "deadline": deadline,
        "claim_boundary": payload["claim_boundary"],
        "send_performed": False,
        "send_allowed_by_builder": False,
        "action_time_human_review_required": True,
        "dispatch_binding": None,
        "exact_action_time_approval_ready": False,
        "exact_action_time_approval_phrase": None,
        "exact_action_time_approval_blockers": ["RENDER_NOT_READY"],
    }


def render_response(
    template_id: str,
    facts: dict[str, Any],
    *,
    already_sent: bool = False,
    inbound_requires_response: bool = True,
    explicit_attachment_request: bool = False,
    claim_evidence_receipts: dict[str, str] | None = None,
    attachment_sha256s: dict[str, str] | None = None,
    current_utc: str | None = None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = validate_registry(registry or read_registry())
    row = template_by_id(payload, template_id)
    deadline = deadline_state(facts.get("deadline_iso"), current_utc)

    if row["send_policy"] == "MONITOR_NO_SEND":
        result = _base_result(payload, row, "MONITOR_NO_SEND", deadline)
        result.update(
            {
                "duplicate_send_blocked": True,
                "subject": None,
                "body": None,
                "missing_fields": [],
            }
        )
        return result

    if already_sent and not inbound_requires_response:
        result = _base_result(payload, row, "MONITOR_NO_DUPLICATE", deadline)
        result.update(
            {
                "duplicate_send_blocked": True,
                "subject": None,
                "body": None,
                "missing_fields": [],
            }
        )
        return result

    required = list(row["required_fields"]) + list(row["routing_fields"])
    if deadline_control_required(row) and "deadline_iso" not in required:
        required.append("deadline_iso")
    missing = sorted(
        field
        for field in required
        if field not in facts or facts[field] is None or str(facts[field]).strip() == ""
    )
    if missing:
        result = _base_result(payload, row, "BLOCKED_MISSING_FACTS", deadline)
        result.update(
            {
                "duplicate_send_blocked": False,
                "subject": None,
                "body": None,
                "missing_fields": missing,
            }
        )
        return result

    invalid_emails = sorted(
        field
        for field in required
        if field.endswith("_email") and not EMAIL_RE.fullmatch(str(facts[field]).strip())
    )
    if invalid_emails:
        result = _base_result(payload, row, "BLOCKED_INVALID_EMAIL", deadline)
        result.update(
            {
                "duplicate_send_blocked": False,
                "subject": None,
                "body": None,
                "missing_fields": [],
                "invalid_email_fields": invalid_emails,
            }
        )
        return result

    invalid_urls = sorted(
        field
        for field in required
        if field.endswith("_url") and not is_public_https_url(facts[field])
    )
    if invalid_urls:
        result = _base_result(payload, row, "BLOCKED_INVALID_PUBLIC_URL", deadline)
        result.update(
            {
                "duplicate_send_blocked": False,
                "subject": None,
                "body": None,
                "missing_fields": [],
                "invalid_url_fields": invalid_urls,
            }
        )
        return result

    fact_risks = claim_fact_risks(facts)
    evidence_receipts = claim_evidence_receipts or {}
    if not isinstance(evidence_receipts, dict) or not all(
        isinstance(field, str) and isinstance(path, str)
        for field, path in evidence_receipts.items()
    ):
        raise OutreachRegistryError("CLAIM_EVIDENCE_RECEIPT_MAP_INVALID")
    invalid_evidence_fields: dict[str, str] = {}
    evidence_receipt_sha256s: dict[str, str] = {}
    for field, risk_codes in fact_risks.items():
        receipt_path = evidence_receipts.get(field)
        if not receipt_path:
            invalid_evidence_fields[field] = "MISSING_EVIDENCE_RECEIPT"
            continue
        try:
            evidence_receipt_sha256s[field] = validate_claim_evidence_receipt(
                receipt_path,
                fact_field=field,
                fact_value=str(facts[field]),
                risk_codes=risk_codes,
            )
        except OutreachRegistryError as exc:
            invalid_evidence_fields[field] = str(exc)
    if invalid_evidence_fields:
        result = _base_result(
            payload, row, "BLOCKED_UNSUPPORTED_CLAIM_FACTS", deadline
        )
        result.update(
            {
                "duplicate_send_blocked": False,
                "subject": None,
                "body": None,
                "missing_fields": [],
                "claim_risk_fields": sorted(fact_risks),
                "claim_risk_codes": sorted(
                    {
                        code
                        for codes in fact_risks.values()
                        for code in codes
                    }
                ),
                "invalid_claim_evidence_fields": invalid_evidence_fields,
            }
        )
        return result

    attachments = _normalize_attachment_files(facts.get("attachment_files"))
    attachment_blocked = bool(attachments) and (
        row["attachment_policy"] == "NONE"
        or (
            row["attachment_policy"] == "EXPLICIT_REQUEST_ONLY"
            and not explicit_attachment_request
        )
    )
    if attachment_blocked:
        result = _base_result(payload, row, "BLOCKED_ATTACHMENT_NOT_AUTHORIZED", deadline)
        result.update(
            {
                "duplicate_send_blocked": False,
                "subject": None,
                "body": None,
                "missing_fields": [],
                "attachment_count": len(attachments),
            }
        )
        return result

    if deadline["urgency"] == "PAST_DUE":
        result = _base_result(payload, row, "BLOCKED_DEADLINE_PASSED", deadline)
        result.update(
            {
                "duplicate_send_blocked": False,
                "subject": None,
                "body": None,
                "missing_fields": [],
            }
        )
        return result

    values = dict(row["optional_defaults"])
    values.update(facts)
    if deadline["provided"]:
        values["deadline_iso"] = canonical_utc(str(facts["deadline_iso"]))
    try:
        subject = row["subject"].format_map(values)
        body = row["body"].format_map(values)
    except KeyError as exc:
        raise OutreachRegistryError(f"UNRESOLVED_PLACEHOLDER:{exc.args[0]}") from exc

    unsafe_reasons: list[str] = []
    if "\r" in subject or "\n" in subject:
        unsafe_reasons.append("SUBJECT_LINE_BREAK")
    if CONTROL_CHAR_RE.search(subject):
        unsafe_reasons.append("SUBJECT_CONTROL_CHARACTER")
    if CONTROL_CHAR_RE.search(body):
        unsafe_reasons.append("BODY_CONTROL_CHARACTER")
    if len(subject) > MAX_RENDERED_SUBJECT_CHARS:
        unsafe_reasons.append("SUBJECT_TOO_LONG")
    if len(body) > MAX_RENDERED_BODY_CHARS:
        unsafe_reasons.append("BODY_TOO_LONG")
    if unsafe_reasons:
        result = _base_result(
            payload, row, "BLOCKED_UNSAFE_RENDERED_CONTENT", deadline
        )
        result.update(
            {
                "duplicate_send_blocked": False,
                "subject": None,
                "body": None,
                "missing_fields": [],
                "unsafe_reasons": sorted(set(unsafe_reasons)),
            }
        )
        return result

    lowered = (subject + "\n" + body).lower()
    for marker in POSITIVE_CLAIM_MARKERS:
        if marker in lowered:
            raise OutreachRegistryError(f"UNSUPPORTED_POSITIVE_CLAIM_RENDER:{marker}")

    sensitive_present = sorted(
        field for field in row["sensitive_fields"] if facts.get(field) not in (None, "")
    )
    private_render = bool(row["private_render_only"] or sensitive_present)
    status = (
        "READY_FOR_PRIVATE_ACTION_TIME_REVIEW"
        if private_render
        else "READY_FOR_ACTION_TIME_REVIEW"
    )
    attachment_entries, attachment_set_sha256, attachment_hashes_bound = (
        _attachment_binding(attachments, attachment_sha256s)
    )
    rendered_deadline_iso = (
        values["deadline_iso"] if deadline["provided"] else None
    )
    dispatch_binding = _dispatch_binding(
        payload=payload,
        row=row,
        facts=facts,
        subject=subject,
        body=body,
        rendered_deadline_iso=rendered_deadline_iso,
        attachment_entries=attachment_entries,
        attachment_set_sha256=attachment_set_sha256,
        attachment_content_hashes_bound=attachment_hashes_bound,
        evidence_receipt_sha256s=evidence_receipt_sha256s,
        already_sent=already_sent,
        inbound_requires_response=inbound_requires_response,
        explicit_attachment_request=explicit_attachment_request,
    )
    draft_binding_complete = attachment_hashes_bound
    exact_approval_ready = False
    exact_approval_phrase = None
    exact_approval_blockers = ["ACTION_TIME_MAILBOX_RECEIPT_REQUIRED"]
    if not attachment_hashes_bound:
        exact_approval_blockers.append("ATTACHMENT_CONTENT_HASHES_REQUIRED")
    exact_approval_blockers.sort()
    result = _base_result(payload, row, status, deadline)
    result.update(
        {
            "duplicate_send_blocked": False,
            "subject": subject,
            "body": body,
            "missing_fields": [],
            "attachment_count": len(attachments),
            "attachment_policy": row["attachment_policy"],
            "private_render": private_render,
            "public_safe": not private_render,
            "sensitive_field_names": sensitive_present,
            "rendered_deadline_iso": rendered_deadline_iso,
            "claim_risk_fields": sorted(fact_risks),
            "claim_evidence_receipt_sha256s": evidence_receipt_sha256s,
            "dispatch_binding": dispatch_binding,
            "draft_binding_complete": draft_binding_complete,
            "exact_action_time_approval_ready": exact_approval_ready,
            "exact_action_time_approval_phrase": exact_approval_phrase,
            "exact_action_time_approval_blockers": exact_approval_blockers,
        }
    )
    return result


def _normalize_optional_sha256(value: Any, code: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value.strip()):
        raise OutreachRegistryError(code)
    return value.strip().upper()


def _normalize_required_sha256(value: Any, code: str) -> str:
    normalized = _normalize_optional_sha256(value, code)
    if normalized is None:
        raise OutreachRegistryError(code)
    return normalized


def _validated_ready_dispatch_binding(
    rendered: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(rendered, dict):
        raise OutreachRegistryError("RENDERED_RESPONSE_INVALID")
    if rendered.get("status") not in {
        "READY_FOR_ACTION_TIME_REVIEW",
        "READY_FOR_PRIVATE_ACTION_TIME_REVIEW",
    }:
        raise OutreachRegistryError("RENDERED_RESPONSE_NOT_READY")
    if rendered.get("send_allowed_by_builder") is not False:
        raise OutreachRegistryError("RENDERED_BUILDER_SEND_CONTROL_INVALID")
    if rendered.get("send_performed") is not False:
        raise OutreachRegistryError("RENDERED_SEND_STATE_INVALID")
    if rendered.get("draft_binding_complete") is not True:
        raise OutreachRegistryError("DRAFT_BINDING_INCOMPLETE")
    binding = rendered.get("dispatch_binding")
    if not isinstance(binding, dict):
        raise OutreachRegistryError("DISPATCH_BINDING_MISSING")
    if binding.get("schema") != DISPATCH_BINDING_SCHEMA:
        raise OutreachRegistryError("DISPATCH_BINDING_SCHEMA_INVALID")
    expected_sha256 = canonical_object_sha256(
        binding,
        omit={"binding_sha256"},
    )
    if binding.get("binding_sha256") != expected_sha256:
        raise OutreachRegistryError("DISPATCH_BINDING_HASH_MISMATCH")
    for field in (
        "binding_sha256",
        "recipient_route_sha256",
        "subject_sha256",
        "body_sha256",
        "attachment_set_sha256",
    ):
        _normalize_required_sha256(
            binding.get(field),
            f"DISPATCH_BINDING_{field.upper()}_INVALID",
        )
    _normalize_optional_sha256(
        binding.get("source_message_id_sha256"),
        "DISPATCH_BINDING_SOURCE_MESSAGE_SHA256_INVALID",
    )
    if binding.get("attachment_content_hashes_bound") is not True:
        raise OutreachRegistryError("ATTACHMENT_CONTENT_HASHES_REQUIRED")
    duplicate_state = binding.get("duplicate_send_state")
    if not isinstance(duplicate_state, dict):
        raise OutreachRegistryError("DISPATCH_DUPLICATE_STATE_INVALID")
    if duplicate_state.get("already_sent") is not False:
        raise OutreachRegistryError("DISPATCH_ALREADY_SENT")
    return binding


def _validate_action_time_mailbox_receipt(
    receipt: dict[str, Any],
    binding: dict[str, Any],
    current: datetime,
) -> tuple[dict[str, Any], str]:
    if not isinstance(receipt, dict):
        raise OutreachRegistryError("ACTION_TIME_MAILBOX_RECEIPT_INVALID")
    if set(receipt) != ACTION_TIME_MAILBOX_RECEIPT_FIELDS:
        raise OutreachRegistryError("ACTION_TIME_MAILBOX_RECEIPT_FIELDS_INVALID")
    if receipt.get("schema") != ACTION_TIME_MAILBOX_RECEIPT_SCHEMA:
        raise OutreachRegistryError("ACTION_TIME_MAILBOX_RECEIPT_SCHEMA_INVALID")
    if receipt.get("search_scope") != "ALL_MAIL_BOUND_ROUTE_THREAD_SUBJECT_BODY":
        raise OutreachRegistryError("ACTION_TIME_MAILBOX_SEARCH_SCOPE_INVALID")

    required_true = {
        "current_draft_only",
        "draft_present",
        "full_mailbox_search_completed",
        "identifiers_omitted",
        "message_body_omitted",
    }
    for field in required_true:
        if receipt.get(field) is not True:
            raise OutreachRegistryError(
                f"ACTION_TIME_MAILBOX_CONTROL_INVALID:{field}"
            )
    if receipt.get("draft_sent") is not False:
        raise OutreachRegistryError("ACTION_TIME_DRAFT_ALREADY_SENT")

    expected_counts = {
        "matching_current_draft_count": 1,
        "matching_sent_count": 0,
        "matching_received_after_draft_count": 0,
        "cc_count": 0,
        "bcc_count": 0,
    }
    for field, expected in expected_counts.items():
        value = receipt.get(field)
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value != expected
        ):
            raise OutreachRegistryError(
                f"ACTION_TIME_MAILBOX_COUNT_INVALID:{field}"
            )
    attachment_count = receipt.get("attachment_count")
    if (
        not isinstance(attachment_count, int)
        or isinstance(attachment_count, bool)
        or attachment_count != binding.get("attachment_count")
    ):
        raise OutreachRegistryError("ACTION_TIME_ATTACHMENT_COUNT_MISMATCH")

    digest_fields = {
        "recipient_route_sha256": "ACTION_TIME_RECIPIENT_ROUTE_MISMATCH",
        "source_message_id_sha256": "ACTION_TIME_SOURCE_MESSAGE_MISMATCH",
        "subject_sha256": "ACTION_TIME_SUBJECT_MISMATCH",
        "body_sha256": "ACTION_TIME_BODY_MISMATCH",
        "attachment_set_sha256": "ACTION_TIME_ATTACHMENT_SET_MISMATCH",
    }
    normalized_receipt = dict(receipt)
    for field, mismatch_code in digest_fields.items():
        observed = _normalize_optional_sha256(
            receipt.get(field),
            f"ACTION_TIME_{field.upper()}_INVALID",
        )
        expected = _normalize_optional_sha256(
            binding.get(field),
            f"DISPATCH_BINDING_{field.upper()}_INVALID",
        )
        if observed != expected:
            raise OutreachRegistryError(mismatch_code)
        normalized_receipt[field] = observed

    checked = parse_aware_datetime(str(receipt.get("checked_utc") or ""))
    readback_checked = parse_aware_datetime(
        str(receipt.get("draft_readback_checked_utc") or "")
    )
    for label, observed in (
        ("MAILBOX_SEARCH", checked),
        ("DRAFT_READBACK", readback_checked),
    ):
        age_seconds = (current - observed).total_seconds()
        if age_seconds < 0:
            raise OutreachRegistryError(
                f"ACTION_TIME_{label}_FROM_FUTURE"
            )
        if age_seconds > ACTION_TIME_MAILBOX_MAX_AGE_SECONDS:
            raise OutreachRegistryError(
                f"ACTION_TIME_{label}_STALE"
            )
    normalized_receipt["checked_utc"] = canonical_utc(
        str(receipt["checked_utc"])
    )
    normalized_receipt["draft_readback_checked_utc"] = canonical_utc(
        str(receipt["draft_readback_checked_utc"])
    )
    return normalized_receipt, canonical_object_sha256(normalized_receipt)


def _action_time_approval_phrase(binding: dict[str, Any]) -> str:
    return (
        "APPROVE ONE OUTREACH DISPATCH: "
        f"template {binding['template_id']}; "
        f"action-time binding SHA-256 {binding['binding_sha256']}; "
        f"draft binding SHA-256 {binding['dispatch_binding_sha256']}; "
        f"subject SHA-256 {binding['subject_sha256']}; "
        f"body SHA-256 {binding['body_sha256']}; "
        f"attachment set SHA-256 {binding['attachment_set_sha256']}; "
        f"expires {binding['approval_window_expires_utc']}."
    )


def build_action_time_authorization(
    rendered: dict[str, Any],
    mailbox_receipt: dict[str, Any],
    *,
    current_utc: str,
) -> dict[str, Any]:
    binding = _validated_ready_dispatch_binding(rendered)
    current = parse_aware_datetime(current_utc)
    deadline_value = binding.get("deadline_utc")
    deadline = (
        parse_aware_datetime(str(deadline_value))
        if deadline_value is not None
        else None
    )
    if deadline is not None and current >= deadline:
        raise OutreachRegistryError("ACTION_TIME_DEADLINE_REACHED")

    normalized_receipt, receipt_sha256 = (
        _validate_action_time_mailbox_receipt(
            mailbox_receipt,
            binding,
            current,
        )
    )
    expires = current + timedelta(
        seconds=ACTION_TIME_APPROVAL_WINDOW_SECONDS
    )
    if deadline is not None:
        expires = min(expires, deadline)
    opened_utc = current.isoformat().replace("+00:00", "Z")
    expires_utc = expires.isoformat().replace("+00:00", "Z")
    core = {
        "schema": ACTION_TIME_APPROVAL_BINDING_SCHEMA,
        "template_id": str(binding["template_id"]),
        "dispatch_binding_sha256": str(binding["binding_sha256"]),
        "mailbox_receipt_sha256": receipt_sha256,
        "recipient_route_sha256": str(binding["recipient_route_sha256"]),
        "source_message_id_sha256": binding.get("source_message_id_sha256"),
        "subject_sha256": str(binding["subject_sha256"]),
        "body_sha256": str(binding["body_sha256"]),
        "attachment_set_sha256": str(binding["attachment_set_sha256"]),
        "approval_window_opened_utc": opened_utc,
        "approval_window_expires_utc": expires_utc,
        "single_use": True,
    }
    approval_binding = {
        **core,
        "binding_sha256": canonical_object_sha256(core),
    }
    phrase = _action_time_approval_phrase(approval_binding)
    return {
        "schema": ACTION_TIME_AUTHORIZATION_SCHEMA,
        "status": "READY_FOR_SINGLE_USE_EXACT_APPROVAL",
        "generated_utc": opened_utc,
        "dispatch_binding": dict(binding),
        "mailbox_receipt": normalized_receipt,
        "mailbox_receipt_sha256": receipt_sha256,
        "approval_binding": approval_binding,
        "exact_action_time_approval_phrase": phrase,
        "approval_received": False,
        "action_time_approval_valid": False,
        "send_authorized": False,
        "send_performed": False,
        "builder_can_send_email": False,
        "controls": {
            "fresh_full_mailbox_search_required": True,
            "fresh_exact_draft_readback_required": True,
            "mailbox_max_age_seconds": ACTION_TIME_MAILBOX_MAX_AGE_SECONDS,
            "approval_window_seconds": int(
                (expires - current).total_seconds()
            ),
            "exact_phrase_required": True,
            "single_use": True,
            "deadline_reached_fail_closed": True,
            "duplicate_send_fail_closed": True,
        },
        "claim_boundary": (
            "This authorization binds one fresh draft snapshot for exact human "
            "approval. It does not send email, prove delivery or receipt, "
            "certify facts, authorize partner-name use, submit a portal action, "
            "or establish selection, award, funding, validation, performance, "
            "or savings."
        ),
    }


def evaluate_action_time_authorization(
    authorization: dict[str, Any],
    *,
    exact_approval_phrase: str,
    current_utc: str,
    dispatch_consumed: bool = False,
) -> dict[str, Any]:
    if not isinstance(authorization, dict) or authorization.get(
        "schema"
    ) != ACTION_TIME_AUTHORIZATION_SCHEMA:
        raise OutreachRegistryError("ACTION_TIME_AUTHORIZATION_INVALID")
    if not isinstance(dispatch_consumed, bool):
        raise OutreachRegistryError("DISPATCH_CONSUMED_STATE_INVALID")
    approval_binding = authorization.get("approval_binding")
    if not isinstance(approval_binding, dict) or approval_binding.get(
        "schema"
    ) != ACTION_TIME_APPROVAL_BINDING_SCHEMA:
        raise OutreachRegistryError("ACTION_TIME_APPROVAL_BINDING_INVALID")
    expected_binding_sha256 = canonical_object_sha256(
        approval_binding,
        omit={"binding_sha256"},
    )
    binding_hash_valid = (
        approval_binding.get("binding_sha256")
        == expected_binding_sha256
    )
    expected_phrase = _action_time_approval_phrase(approval_binding)
    phrase_integrity_valid = (
        authorization.get("exact_action_time_approval_phrase")
        == expected_phrase
    )
    phrase_matches = exact_approval_phrase == expected_phrase
    current = parse_aware_datetime(current_utc)
    opened = parse_aware_datetime(
        str(approval_binding.get("approval_window_opened_utc") or "")
    )
    expires = parse_aware_datetime(
        str(approval_binding.get("approval_window_expires_utc") or "")
    )
    approval_window_seconds = (expires - opened).total_seconds()
    approval_window_bounded = (
        0 < approval_window_seconds <= ACTION_TIME_APPROVAL_WINDOW_SECONDS
    )

    dispatch_binding = authorization.get("dispatch_binding")
    dispatch_binding_hash_valid = False
    dispatch_scope_matches = False
    deadline_bounds_window = True
    if isinstance(dispatch_binding, dict):
        dispatch_binding_hash_valid = (
            dispatch_binding.get("schema") == DISPATCH_BINDING_SCHEMA
            and dispatch_binding.get("binding_sha256")
            == canonical_object_sha256(
                dispatch_binding,
                omit={"binding_sha256"},
            )
        )
        dispatch_scope_matches = all(
            (
                approval_binding.get("template_id")
                == dispatch_binding.get("template_id"),
                approval_binding.get("dispatch_binding_sha256")
                == dispatch_binding.get("binding_sha256"),
                approval_binding.get("recipient_route_sha256")
                == dispatch_binding.get("recipient_route_sha256"),
                approval_binding.get("source_message_id_sha256")
                == dispatch_binding.get("source_message_id_sha256"),
                approval_binding.get("subject_sha256")
                == dispatch_binding.get("subject_sha256"),
                approval_binding.get("body_sha256")
                == dispatch_binding.get("body_sha256"),
                approval_binding.get("attachment_set_sha256")
                == dispatch_binding.get("attachment_set_sha256"),
            )
        )
        deadline_value = dispatch_binding.get("deadline_utc")
        if deadline_value is not None:
            deadline_bounds_window = expires <= parse_aware_datetime(
                str(deadline_value)
            )

    mailbox_receipt_integrity_valid = False
    mailbox_receipt_scope_matches = False
    mailbox_receipt = authorization.get("mailbox_receipt")
    if isinstance(dispatch_binding, dict) and isinstance(
        mailbox_receipt, dict
    ):
        try:
            normalized_receipt, observed_receipt_sha256 = (
                _validate_action_time_mailbox_receipt(
                    mailbox_receipt,
                    dispatch_binding,
                    opened,
                )
            )
        except OutreachRegistryError:
            pass
        else:
            mailbox_receipt_integrity_valid = (
                mailbox_receipt == normalized_receipt
                and authorization.get("mailbox_receipt_sha256")
                == observed_receipt_sha256
                and approval_binding.get("mailbox_receipt_sha256")
                == observed_receipt_sha256
            )
            mailbox_receipt_scope_matches = True

    window_current = opened <= current < expires
    valid = all(
        (
            binding_hash_valid,
            phrase_integrity_valid,
            phrase_matches,
            approval_window_bounded,
            dispatch_binding_hash_valid,
            dispatch_scope_matches,
            deadline_bounds_window,
            mailbox_receipt_integrity_valid,
            mailbox_receipt_scope_matches,
            window_current,
            not dispatch_consumed,
        )
    )
    blockers = []
    if not binding_hash_valid:
        blockers.append("ACTION_TIME_BINDING_HASH_MISMATCH")
    if not phrase_integrity_valid:
        blockers.append("STORED_APPROVAL_PHRASE_TAMPERED")
    if not phrase_matches:
        blockers.append("EXACT_APPROVAL_PHRASE_MISMATCH")
    if not approval_window_bounded:
        blockers.append("APPROVAL_WINDOW_BOUNDS_INVALID")
    if not dispatch_binding_hash_valid:
        blockers.append("DISPATCH_BINDING_HASH_MISMATCH")
    if not dispatch_scope_matches:
        blockers.append("ACTION_TIME_DISPATCH_SCOPE_MISMATCH")
    if not deadline_bounds_window:
        blockers.append("ACTION_TIME_DEADLINE_WINDOW_MISMATCH")
    if not mailbox_receipt_integrity_valid:
        blockers.append("ACTION_TIME_MAILBOX_RECEIPT_HASH_MISMATCH")
    if not mailbox_receipt_scope_matches:
        blockers.append("ACTION_TIME_MAILBOX_SCOPE_MISMATCH")
    if current < opened:
        blockers.append("APPROVAL_WINDOW_NOT_OPEN")
    elif current >= expires:
        blockers.append("APPROVAL_WINDOW_EXPIRED")
    if dispatch_consumed:
        blockers.append("SINGLE_USE_BINDING_ALREADY_CONSUMED")
    return {
        "status": (
            "CURRENT_EXACT_APPROVAL_PRESENT"
            if valid
            else "EXPIRED_OR_BLOCKED_REBUILD_REQUIRED"
        ),
        "evaluated_utc": current.isoformat().replace("+00:00", "Z"),
        "action_time_approval_valid": valid,
        "approval_window_current": window_current,
        "approval_window_bounded": approval_window_bounded,
        "dispatch_binding_integrity_valid": dispatch_binding_hash_valid,
        "dispatch_scope_matches": dispatch_scope_matches,
        "deadline_bounds_window": deadline_bounds_window,
        "mailbox_receipt_integrity_valid": (
            mailbox_receipt_integrity_valid
        ),
        "mailbox_receipt_scope_matches": mailbox_receipt_scope_matches,
        "single_use_binding_consumed": dispatch_consumed,
        "blockers": sorted(blockers),
        "builder_can_send_email": False,
        "send_authorized": valid,
        "send_performed": False,
    }


def build_public_payload(
    registry: dict[str, Any] | None = None, generated_utc: str | None = None
) -> dict[str, Any]:
    payload = validate_registry(registry or read_registry())
    action_time_mailbox_receipt_template = (
        validate_action_time_mailbox_receipt_template()
    )
    policy_counts = Counter(row["send_policy"] for row in payload["templates"])
    private_count = sum(bool(row["private_render_only"]) for row in payload["templates"])
    quality_rows = [
        template_quality_profile(row) for row in payload["templates"]
    ]
    quality_check_count = sum(len(row["checks"]) for row in quality_rows)
    source_effective_utc = canonical_utc(payload["source_effective_utc"])
    result = {
        "schema": PUBLIC_SCHEMA,
        "generated_utc": canonical_utc(generated_utc or source_effective_utc),
        "source_effective_utc": source_effective_utc,
        "source_schema": payload["schema"],
        "source_config": CONFIG.relative_to(ROOT).as_posix(),
        "source_config_sha256": canonical_object_sha256(payload),
        "source_config_hash_basis": "SORTED_COMPACT_JSON_UTF8",
        "template_count": len(payload["templates"]),
        "send_policy_counts": dict(sorted(policy_counts.items())),
        "private_render_template_count": private_count,
        "claim_boundary": payload["claim_boundary"],
        "global_rules": payload["global_rules"],
        "templates": payload["templates"],
        "quality_gate": {
            "status": "PASS",
            "all_templates_pass": all(
                row["status"] == "PASS" for row in quality_rows
            ),
            "template_count": len(quality_rows),
            "check_count": quality_check_count,
            "deadline_control_template_ids": sorted(
                row["template_id"]
                for row in quality_rows
                if row["deadline_iso_control_required"]
            ),
            "https_public_url_field_count": sum(
                len(row["https_public_url_fields"]) for row in quality_rows
            ),
            "template_results": quality_rows,
        },
        "controls": {
            "duplicate_send_fail_closed": True,
            "missing_fact_fail_closed": True,
            "past_deadline_fail_closed": True,
            "attachment_requires_explicit_request": True,
            "unused_required_field_fail_closed": True,
            "overlapping_field_declaration_fail_closed": True,
            "known_deadline_requires_aware_iso_control": True,
            "rendered_deadline_matches_evaluated_deadline": True,
            "public_url_requires_https_without_credentials": True,
            "rendered_subject_header_injection_fail_closed": True,
            "rendered_length_limits_fail_closed": True,
            "rendered_fact_claim_guard_fail_closed": True,
            "high_risk_claim_requires_hash_bound_evidence_receipt": True,
            "claim_evidence_source_artifacts_rehashed": True,
            "claim_evidence_receipt_schema": CLAIM_EVIDENCE_RECEIPT_SCHEMA,
            "claim_evidence_receipt_template": (
                CLAIM_EVIDENCE_TEMPLATE.relative_to(ROOT).as_posix()
            ),
            "duplicate_json_key_fail_closed": True,
            "ready_render_has_dispatch_binding": True,
            "draft_binding_is_not_send_authorization": True,
            "recipient_route_and_source_thread_hash_bound": True,
            "subject_body_deadline_and_attachment_set_hash_bound": True,
            "attachment_content_hash_required_for_exact_approval": True,
            "exact_approval_phrase_is_binding_scoped": True,
            "action_time_mailbox_receipt_required": True,
            "action_time_mailbox_receipt_schema": (
                ACTION_TIME_MAILBOX_RECEIPT_SCHEMA
            ),
            "action_time_mailbox_receipt_template": (
                ACTION_TIME_MAILBOX_RECEIPT_TEMPLATE.relative_to(
                    ROOT
                ).as_posix()
            ),
            "action_time_mailbox_receipt_template_sha256": (
                canonical_object_sha256(
                    action_time_mailbox_receipt_template
                )
            ),
            "action_time_mailbox_max_age_seconds": (
                ACTION_TIME_MAILBOX_MAX_AGE_SECONDS
            ),
            "action_time_approval_window_seconds": (
                ACTION_TIME_APPROVAL_WINDOW_SECONDS
            ),
            "exact_approval_expires": True,
            "single_use_action_time_binding": True,
            "source_config_hash_cross_platform_canonical_json": True,
            "builder_can_send_email": False,
            "action_time_human_review_required": True,
            "unchanged_rebuild_byte_stable": True,
        },
    }
    serialized = json.dumps(result, sort_keys=True)
    if UUID_RE.search(serialized):
        raise OutreachRegistryError("PUBLIC_OUTPUT_CONTAINS_PRIVATE_IDENTIFIER")
    return result


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Outreach Response Template Registry - 2026-07-18",
        "",
        f"- Templates: `{payload['template_count']}`",
        f"- Private-render templates: `{payload['private_render_template_count']}`",
        "- Builder can send email: `false`",
        "- Duplicate-send gate: `FAIL_CLOSED`",
        "- Missing-fact gate: `FAIL_CLOSED`",
        "- Past-deadline gate: `FAIL_CLOSED`",
        "- Inserted-fact claim gate: `FAIL_CLOSED`",
        "- High-risk claim evidence: `EXACT_VALUE_AND_SOURCE_HASH_BOUND`",
        "- Ready-render dispatch scope: `RECIPIENT_THREAD_BODY_DEADLINE_EVIDENCE_HASH_BOUND`",
        "- Attachment content required for exact approval: `true`",
        "- Draft binding is send authorization: `false`",
        "- Action-time mailbox receipt: `REQUIRED`",
        "- Action-time mailbox freshness: `15_MINUTES_MAX`",
        "- Exact approval phrase: `BINDING_SCOPED_SINGLE_USE`",
        "- Exact approval window: `5_MINUTES_MAX`",
        f"- Static quality gate: `{payload['quality_gate']['status']}`",
        f"- Static quality checks: `{payload['quality_gate']['check_count']}`",
        "- Unchanged rebuilds byte-stable: `true`",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Global Rules",
        "",
    ]
    lines.extend(f"- {rule}" for rule in payload["global_rules"])
    lines.extend(
        [
            "",
            "## Quality Gate",
            "",
            f"- All templates pass: `{str(payload['quality_gate']['all_templates_pass']).lower()}`",
            f"- Deadline-control templates: `{', '.join(payload['quality_gate']['deadline_control_template_ids']) or 'none'}`",
            f"- HTTPS public URL fields: `{payload['quality_gate']['https_public_url_field_count']}`",
            "",
            "## Decision Matrix",
            "",
            "| Template | Send policy | Attachment policy | Private render |",
            "|---|---|---|---:|",
        ]
    )
    for row in payload["templates"]:
        lines.append(
            f"| `{row['template_id']}` | `{row['send_policy']}` | "
            f"`{row['attachment_policy']}` | `{str(row['private_render_only']).lower()}` |"
        )
    for row in payload["templates"]:
        lines.extend(
            [
                "",
                f"## {row['template_id']}",
                "",
                row["description"],
                "",
                f"- Inbound states: `{', '.join(row['inbound_states'])}`",
                f"- Reply triggers: `{', '.join(row['reply_triggers'])}`",
                f"- Required fields: `{', '.join(row['required_fields'] + row['routing_fields']) or 'none'}`",
                "",
            ]
        )
        if row["send_policy"] == "MONITOR_NO_SEND":
            lines.append("No message is rendered. Monitor the thread and do not duplicate-send.")
            continue
        lines.extend(
            [
                "```text",
                f"Subject: {row['subject']}",
                "",
                row["body"],
                "```",
            ]
        )
    lines.extend(
        [
            "",
            "## Operating Boundary",
            "",
            "This registry renders drafts, immutable dispatch bindings, action-time authorization records, and routing decisions only. It does not access Gmail, transmit a message, certify facts, authorize an attachment, or replace action-time human review. A ready render receives a binding over the recipient route, source thread, exact subject and body, deadline, evidence receipts, and attachment set, but that draft binding is not send authorization. An exact approval phrase is withheld until every attachment content hash is bound and a fresh full-mailbox search plus exact draft readback confirm one current unsent draft, no matching sent copy, no later inbound response, and no CC or BCC. The resulting exact phrase is hash-bound, single-use, and valid for no more than five minutes or until the deadline, whichever comes first. A binding scopes approval; it is not proof of transmission, receipt, content truth, independent validation, agency acceptance, field performance, savings, an award, or any other real-world outcome.",
            "",
        ]
    )
    return "\n".join(lines)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the bounded outreach response template registry."
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    registry = validate_registry(read_registry())
    payload = build_public_payload(registry)
    markdown = render_markdown(payload)
    if not args.check:
        write_json(OUT_JSON, payload)
        write_text(OUT_MD, markdown)
        write_json(LATEST_JSON, payload)
    print(
        json.dumps(
            {
                "status": "VALID" if args.check else "BUILT",
                "template_count": payload["template_count"],
                "duplicate_send_fail_closed": payload["controls"][
                    "duplicate_send_fail_closed"
                ],
                "builder_can_send_email": payload["controls"][
                    "builder_can_send_email"
                ],
                "quality_gate_status": payload["quality_gate"]["status"],
                "quality_check_count": payload["quality_gate"]["check_count"],
                "outputs_written": not args.check,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
