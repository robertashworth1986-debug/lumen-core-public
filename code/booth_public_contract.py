from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any


PUBLIC_BOOTH_SCHEMA = "lumencore.public_booth_contract.v2"
PUBLIC_BOOTH_CLAIM_BOUNDARY = (
    "This public Level 3 summary contains bounded aggregate counts only. "
    "It omits identities, operational events, internal paths, credentials, "
    "valuation proxies, and application identifiers. It is not evidence of "
    "profit, realized savings, field validation, Level 5 independent "
    "validation, or authority for live execution."
)
MAX_PUBLIC_COUNT = 1_000_000_000

_TRANSACTION_IDENTIFIER = re.compile(
    r"\b[A-Z][A-Z0-9]{5,}-[A-Z0-9]{5,}-[A-Z0-9]{5,}\b",
    re.IGNORECASE,
)
_TAX_IDENTIFIER = re.compile(r"\b\d{2}-\d{7}\b")
_PRIVATE_APPLICATION_IDENTIFIER = re.compile(r"\b\d{2}/\d{3},\d{3}\b")
_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")
_EMAIL_ADDRESS = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _safe_nonnegative_int(value: Any) -> int:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError, OverflowError):
        return 0
    return min(MAX_PUBLIC_COUNT, max(0, parsed))


def _safe_bool(value: Any) -> bool:
    return value if isinstance(value, bool) else False


def _safe_utc_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return ""
    return (
        parsed.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def public_booth_projection(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build the fixed public contract from a small aggregate allowlist."""

    source = _mapping(payload)
    indexing = _mapping(source.get("indexing"))
    catalog = _mapping(source.get("catalog"))

    return {
        "schema": PUBLIC_BOOTH_SCHEMA,
        "generated_utc": _safe_utc_timestamp(source.get("generated_utc")),
        "brand": {
            "company_system": "LumenCore",
        },
        "indexing": {
            "files_indexed": _safe_nonnegative_int(
                indexing.get("files_indexed")
            ),
            "roots_present": _safe_nonnegative_int(
                indexing.get("roots_present")
            ),
            "roots_total": _safe_nonnegative_int(
                indexing.get("roots_total")
            ),
            "scan_capped": _safe_bool(indexing.get("scan_capped")),
        },
        "catalog": {
            "engine_count": _safe_nonnegative_int(
                catalog.get("engine_count")
            ),
            "assets_source_rows": _safe_nonnegative_int(
                catalog.get("assets_source_rows")
            ),
        },
        "supported_maturity_level": 3,
        "details_redacted": True,
        "public_claim_allowed": False,
        "profit_claim_allowed": False,
        "live_execution_authority": False,
        "level_5_attained": False,
        "claim_boundary": PUBLIC_BOOTH_CLAIM_BOUNDARY,
    }


def _is_absolute_local_path(value: str) -> bool:
    text = str(value or "").strip()
    return bool(
        _WINDOWS_ABSOLUTE_PATH.match(text)
        or text.startswith("\\\\")
        or text.startswith("//")
        or text.startswith("/")
    )


def public_booth_contains_forbidden_value(payload: Any) -> bool:
    """Detect private identifiers or local paths in a projected payload."""

    if isinstance(payload, Mapping):
        return any(
            public_booth_contains_forbidden_value(value)
            for value in payload.values()
        )
    if isinstance(payload, (list, tuple)):
        return any(
            public_booth_contains_forbidden_value(value)
            for value in payload
        )
    if not isinstance(payload, str):
        return False
    return bool(
        _is_absolute_local_path(payload)
        or _TRANSACTION_IDENTIFIER.search(payload)
        or _TAX_IDENTIFIER.search(payload)
        or _PRIVATE_APPLICATION_IDENTIFIER.search(payload)
        or _EMAIL_ADDRESS.search(payload)
    )
