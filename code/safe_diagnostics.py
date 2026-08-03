from __future__ import annotations

import re
import urllib.parse
from typing import Any, Iterable


SENSITIVE_DIAGNOSTIC_FIELDS = {
    "error",
    "exception",
    "note",
    "probe_note",
    "request_url",
    "response_excerpt",
    "url",
}

_PARAM_NAME = (
    r"api[_-]?key|apikey|key|token|access[_-]?token|registrationkey|"
    r"user[_-]?id|userid|email|password|pwd|secret"
)
_QUERY_SECRET = re.compile(
    rf"(?i)(?P<prefix>(?:^|[?&;\s])(?:{_PARAM_NAME})\s*=\s*)"
    r"(?P<value>[^&;\s\"'<>\\]+)"
)
_JSON_SECRET = re.compile(
    rf"(?i)(?P<prefix>[\"']?(?:{_PARAM_NAME})[\"']?\s*:\s*[\"'])"
    r"(?P<value>[^\"']+)(?P<suffix>[\"'])"
)
_HEADER_SECRET = re.compile(
    r"(?i)(?P<prefix>\b(?:authorization|x-api-key|api-key)\s*:\s*"
    r"(?:bearer\s+|basic\s+)?)(?P<value>[^\s,;]+)"
)
_EMAIL_ADDRESS = re.compile(
    r"(?i)(?<![A-Z0-9._%+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}"
)


def _secret_variants(secret_values: Iterable[str] | None) -> set[str]:
    variants: set[str] = set()
    for value in secret_values or ():
        raw = str(value or "").strip()
        if len(raw) < 4:
            continue
        variants.update(
            {
                raw,
                urllib.parse.quote(raw, safe=""),
                urllib.parse.quote_plus(raw, safe=""),
            }
        )
    return {value for value in variants if value}


def sanitize_diagnostic_text(
    text: Any,
    secret_values: Iterable[str] | None = None,
) -> str:
    redacted = str(text or "")
    for value in sorted(_secret_variants(secret_values), key=len, reverse=True):
        redacted = redacted.replace(value, "[REDACTED]")
    redacted = _QUERY_SECRET.sub(
        lambda match: f"{match.group('prefix')}[REDACTED]",
        redacted,
    )
    redacted = _JSON_SECRET.sub(
        lambda match: (
            f"{match.group('prefix')}[REDACTED]{match.group('suffix')}"
        ),
        redacted,
    )
    redacted = _HEADER_SECRET.sub(
        lambda match: f"{match.group('prefix')}[REDACTED]",
        redacted,
    )
    return _EMAIL_ADDRESS.sub("[REDACTED_EMAIL]", redacted)


def sanitize_diagnostic_fields(
    value: Any,
    secret_values: Iterable[str] | None = None,
) -> Any:
    if isinstance(value, list):
        return [
            sanitize_diagnostic_fields(item, secret_values)
            for item in value
        ]
    if not isinstance(value, dict):
        return value
    sanitized: dict[str, Any] = {}
    for key, item in value.items():
        if (
            str(key).strip().lower() in SENSITIVE_DIAGNOSTIC_FIELDS
            and isinstance(item, str)
        ):
            sanitized[key] = sanitize_diagnostic_text(item, secret_values)
        else:
            sanitized[key] = sanitize_diagnostic_fields(item, secret_values)
    return sanitized
