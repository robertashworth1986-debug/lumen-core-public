from __future__ import annotations

import argparse
import hashlib
import json
import re
import string
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "outreach_response_templates_v1.json"
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
VALID_DEADLINE_POLICIES = {
    "NONE",
    "OPTIONAL",
    "REQUIRED",
}
TEMPLATE_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SUBJECT_CONTROL_RE = re.compile(r"[\x00-\x1F\x7F]")
BODY_CONTROL_RE = re.compile(r"[\x00-\x09\x0B-\x1F\x7F]")
UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
POSITIVE_CLAIM_MARKERS = (
    "guaranteed funding",
    "guaranteed savings",
    "government-approved",
    "independently validated performance",
    "field-proven performance",
    "certified safe",
    "will save",
)
SECRET_FIELD_RE = re.compile(
    r"(?:^|_)(?:password|passwd|passphrase|credential|credentials|secret|"
    r"token|authorization|authorization_header|auth_header|cookie|session_cookie|"
    r"recovery_code|backup_code|otp|mfa_code|2fa_code|"
    r"one_time_code|authentication_code|auth_code|verification_code|"
    r"api_key|apikey|client_secret|secret_key|access_token|refresh_token|"
    r"bearer_token|private_key)(?:$|_)",
    re.IGNORECASE,
)
SECRET_VALUE_PATTERNS = (
    re.compile(
        r"\b(?:authentication|verification|one[-_\s]?time|mfa|2fa|otp)"
        r"(?:[-_\s]?(?:code|passcode))?\s*(?:=|:|is)\s*[\"']?"
        r"(?=[A-Z0-9]{4,12}\b)(?=[A-Z0-9]*\d)[A-Z0-9]+\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:api[-_\s]?key|client[-_\s]?secret|secret[-_\s]?key|"
        r"access[-_\s]?token|refresh[-_\s]?token|bearer[-_\s]?token|"
        r"password|passwd|passphrase)\s*(?:=|:|is)\s*[\"']?\S{4,}",
        re.IGNORECASE,
    ),
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\bhttps?://[^/\s:@]+:[^/\s@]+@", re.IGNORECASE),
    re.compile(
        r"\bauthorization\s*:\s*(?:bearer|basic)\s+[A-Z0-9._~+/=-]{8,}",
        re.IGNORECASE,
    ),
    re.compile(
        r"\beyJ[A-Z0-9_-]{8,}\.[A-Z0-9_-]{8,}\.[A-Z0-9_-]{8,}\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(
        r"\b(?:gh[pousr]_[A-Z0-9]{20,}|sk-(?:proj-)?[A-Z0-9_-]{16,}|"
        r"xox[baprs]-[A-Z0-9-]{10,})\b",
        re.IGNORECASE,
    ),
)


class OutreachRegistryError(ValueError):
    pass


def read_registry(path: Path = CONFIG) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise OutreachRegistryError("REGISTRY_NOT_OBJECT")
    return payload


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


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


def _normalized_field_name(value: Any) -> str:
    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", text)
    text = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", text)
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _value_contains_secret(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            if SECRET_FIELD_RE.search(_normalized_field_name(key)):
                return True
            if _value_contains_secret(nested_value):
                return True
        return False
    if isinstance(value, (list, tuple, set)):
        return any(_value_contains_secret(item) for item in value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bool(value)
    if not isinstance(value, str):
        return False
    return any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS)


def secret_or_credential_fields(facts: dict[str, Any]) -> list[str]:
    """Return only blocked top-level field names; never return secret values."""
    blocked: list[str] = []
    for field, value in facts.items():
        normalized = _normalized_field_name(field)
        if SECRET_FIELD_RE.search(normalized) or _value_contains_secret(value):
            blocked.append(str(field))
    return sorted(set(blocked))


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
        deadline_policy = row.get("deadline_policy")
        if deadline_policy not in VALID_DEADLINE_POLICIES:
            raise OutreachRegistryError(f"DEADLINE_POLICY_INVALID:{template_id}")

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
        if deadline_policy == "REQUIRED" and "deadline_iso" not in required:
            raise OutreachRegistryError(
                f"REQUIRED_DEADLINE_FIELD_UNDECLARED:{template_id}"
            )
        if deadline_policy != "REQUIRED" and "deadline_iso" in required:
            raise OutreachRegistryError(f"DEADLINE_POLICY_FIELD_MISMATCH:{template_id}")

        subject = row.get("subject")
        body = row.get("body")
        if not isinstance(subject, str) or not isinstance(body, str):
            raise OutreachRegistryError(f"TEMPLATE_TEXT_INVALID:{template_id}")
        if send_policy != "MONITOR_NO_SEND" and (not subject.strip() or not body.strip()):
            raise OutreachRegistryError(f"REPLY_TEMPLATE_EMPTY:{template_id}")
        if send_policy == "MONITOR_NO_SEND" and (subject.strip() or body.strip()):
            raise OutreachRegistryError(f"MONITOR_TEMPLATE_MUST_BE_EMPTY:{template_id}")
        if SUBJECT_CONTROL_RE.search(subject):
            raise OutreachRegistryError(
                f"TEMPLATE_SUBJECT_CONTROL_CHARACTER:{template_id}"
            )
        if BODY_CONTROL_RE.search(body):
            raise OutreachRegistryError(f"TEMPLATE_BODY_CONTROL_CHARACTER:{template_id}")

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
        if _value_contains_secret(subject + "\n" + body):
            raise OutreachRegistryError(
                f"HARDCODED_TEMPLATE_CREDENTIAL:{template_id}"
            )
        if UUID_RE.search(subject + "\n" + body):
            raise OutreachRegistryError(f"PRIVATE_IDENTIFIER_IN_TEMPLATE:{template_id}")

        _string_list(row.get("inbound_states"), f"INBOUND_STATES_INVALID:{template_id}")
        _string_list(row.get("reply_triggers"), f"REPLY_TRIGGERS_INVALID:{template_id}")
        if not isinstance(row.get("description"), str) or not row["description"].strip():
            raise OutreachRegistryError(f"DESCRIPTION_MISSING:{template_id}")
        if not isinstance(row.get("private_render_only"), bool):
            raise OutreachRegistryError(f"PRIVATE_FLAG_INVALID:{template_id}")

    return payload


def template_by_id(payload: dict[str, Any], template_id: str) -> dict[str, Any]:
    for row in payload["templates"]:
        if row["template_id"] == template_id:
            return row
    raise OutreachRegistryError(f"UNKNOWN_TEMPLATE:{template_id}")


def parse_aware_datetime(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise OutreachRegistryError("DEADLINE_INVALID")
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
        "deadline_policy": row["deadline_policy"],
        "claim_boundary": payload["claim_boundary"],
        "send_performed": False,
        "send_allowed_by_builder": False,
        "action_time_human_review_required": True,
    }


def render_response(
    template_id: str,
    facts: dict[str, Any],
    *,
    already_sent: bool = False,
    inbound_requires_response: bool = True,
    explicit_attachment_request: bool = False,
    current_utc: str | None = None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = validate_registry(registry or read_registry())
    if not isinstance(facts, dict):
        raise OutreachRegistryError("FACTS_NOT_OBJECT")
    row = template_by_id(payload, template_id)
    deadline = {
        "provided": False,
        "urgency": "NOT_PROVIDED",
        "hours_remaining": None,
    }

    blocked_secret_fields = secret_or_credential_fields(facts)
    if blocked_secret_fields:
        result = _base_result(
            payload, row, "BLOCKED_SECRET_OR_CREDENTIAL_FACT", deadline
        )
        result.update(
            {
                "duplicate_send_blocked": False,
                "subject": None,
                "body": None,
                "missing_fields": [],
                "secret_or_credential_fields": blocked_secret_fields,
            }
        )
        return result

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

    deadline_value = facts.get("deadline_iso")
    if row["deadline_policy"] != "NONE" and deadline_value not in (None, ""):
        try:
            deadline = deadline_state(deadline_value, current_utc)
        except OutreachRegistryError as exc:
            deadline = {
                "provided": True,
                "urgency": "INVALID",
                "hours_remaining": None,
                "validation_error": str(exc),
            }
            result = _base_result(payload, row, "BLOCKED_INVALID_DEADLINE", deadline)
            result.update(
                {
                    "duplicate_send_blocked": False,
                    "subject": None,
                    "body": None,
                    "missing_fields": [],
                }
            )
            return result

    required = list(row["required_fields"]) + list(row["routing_fields"])
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

    attachments = facts.get("attachment_files") or []
    if not isinstance(attachments, list) or not all(
        isinstance(item, str) and item.strip() for item in attachments
    ):
        raise OutreachRegistryError("ATTACHMENT_LIST_INVALID")
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
    try:
        subject = row["subject"].format_map(values)
        body = row["body"].format_map(values)
    except KeyError as exc:
        raise OutreachRegistryError(f"UNRESOLVED_PLACEHOLDER:{exc.args[0]}") from exc

    remaining = template_placeholders(subject + "\n" + body)
    if remaining:
        raise OutreachRegistryError(
            f"UNRESOLVED_PLACEHOLDER_AFTER_RENDER:{','.join(sorted(remaining))}"
        )
    if SUBJECT_CONTROL_RE.search(subject):
        result = _base_result(payload, row, "BLOCKED_SUBJECT_CONTROL_CHARACTER", deadline)
        result.update(
            {
                "duplicate_send_blocked": False,
                "subject": None,
                "body": None,
                "missing_fields": [],
            }
        )
        return result
    if BODY_CONTROL_RE.search(body):
        result = _base_result(payload, row, "BLOCKED_BODY_CONTROL_CHARACTER", deadline)
        result.update(
            {
                "duplicate_send_blocked": False,
                "subject": None,
                "body": None,
                "missing_fields": [],
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
        }
    )
    return result


def build_public_payload(
    registry: dict[str, Any] | None = None, generated_utc: str | None = None
) -> dict[str, Any]:
    payload = validate_registry(registry or read_registry())
    policy_counts = Counter(row["send_policy"] for row in payload["templates"])
    private_count = sum(bool(row["private_render_only"]) for row in payload["templates"])
    source_effective_utc = canonical_utc(payload["source_effective_utc"])
    result = {
        "schema": PUBLIC_SCHEMA,
        "generated_utc": canonical_utc(generated_utc or source_effective_utc),
        "source_effective_utc": source_effective_utc,
        "source_schema": payload["schema"],
        "source_config": CONFIG.relative_to(ROOT).as_posix(),
        "source_config_sha256": sha256_bytes(CONFIG.read_bytes()),
        "template_count": len(payload["templates"]),
        "send_policy_counts": dict(sorted(policy_counts.items())),
        "private_render_template_count": private_count,
        "claim_boundary": payload["claim_boundary"],
        "global_rules": payload["global_rules"],
        "templates": payload["templates"],
        "controls": {
            "duplicate_send_fail_closed": True,
            "missing_fact_fail_closed": True,
            "secret_or_credential_fail_closed": True,
            "opaque_binary_fact_fail_closed": True,
            "hardcoded_template_credential_fail_closed": True,
            "past_deadline_fail_closed": True,
            "deadline_policy_fail_closed": True,
            "subject_header_injection_fail_closed": True,
            "body_control_character_fail_closed": True,
            "attachment_requires_explicit_request": True,
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
        "- Secret-or-credential gate: `FAIL_CLOSED`",
        "- Past-deadline gate: `FAIL_CLOSED`",
        "- Deadline-policy gate: `FAIL_CLOSED`",
        "- Subject header-injection gate: `FAIL_CLOSED`",
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
            "## Decision Matrix",
            "",
            "| Template | Send policy | Attachment policy | Deadline policy | Private render |",
            "|---|---|---|---|---:|",
        ]
    )
    for row in payload["templates"]:
        lines.append(
            f"| `{row['template_id']}` | `{row['send_policy']}` | "
            f"`{row['attachment_policy']}` | `{row['deadline_policy']}` | "
            f"`{str(row['private_render_only']).lower()}` |"
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
                f"- Deadline policy: `{row['deadline_policy']}`",
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
            "This registry renders drafts and routing decisions only. It does not access Gmail, transmit a message, certify facts, authorize an attachment, or replace action-time human review.",
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
                "outputs_written": not args.check,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
