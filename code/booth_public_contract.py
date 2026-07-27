from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from typing import Any


PUBLIC_BOOTH_CLAIM_BOUNDARY = (
    "This public Level 3 booth summary contains bounded aggregate metadata only. "
    "Per-event execution details, internal paths, and valuation proxies are redacted. "
    "It is not evidence of profit, realized savings, field validation, Level 5 independent "
    "validation, or authority for live execution."
)

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

_PRIVATE_PROFILE_KEYS = {
    "address",
    "application_number",
    "email",
    "ein",
    "patent_center_reference",
    "phone",
    "ssn",
    "tax_id",
    "tin",
    "uspto_non_provisional_application",
}
_PRIVATE_ANYWHERE_KEYS = _PRIVATE_PROFILE_KEYS | {
    "access_token",
    "api_key",
    "credential",
    "credentials",
    "meeting_password",
    "otp",
    "passcode",
    "passwd",
    "password",
    "pin",
    "private_key",
    "refresh_token",
    "secret",
    "ssh_key",
    "token",
}
_PRIVATE_KEY_SUFFIXES = (
    "_access_token",
    "_api_key",
    "_credential",
    "_credentials",
    "_password",
    "_private_key",
    "_refresh_token",
    "_secret",
)

_LEGACY_TRADE_KEYS = (
    "timestamp",
    "txid",
    "symbol",
    "pair",
    "side",
    "status",
    "size_usd",
)
_LEGACY_GRANT_KEYS = (
    "master_valuation_generated_utc",
    "master_valuation_proxy_usd",
    "valuation_increment_usd",
    "ip_entry_sha256",
    "event_id",
    "explainer_generated_utc",
    "explainer_entry_sha256",
    "public_truth_status",
    "public_truth_generated_utc",
    "public_truth_chain_entry_sha256",
)
_LEGACY_ARTIFACT_KEYS = (
    "universe_map_json",
    "nobel_engine_catalog_json",
    "live_trade_ledger_jsonl",
    "live_executor_heartbeat_json",
    "premium_mirror_latest_json",
    "master_valuation_latest_json",
    "luma_explainer_quantified_latest_json",
    "public_truth_latest_json",
)


def _is_absolute_local_path(value: str) -> bool:
    text = str(value or "").strip()
    return bool(
        _WINDOWS_ABSOLUTE_PATH.match(text)
        or text.startswith("\\\\")
        or text.startswith("//")
        or text.startswith("/")
    )


def _is_private_key(value: Any) -> bool:
    key = str(value or "").strip().casefold()
    return key in _PRIVATE_ANYWHERE_KEYS or key.endswith(_PRIVATE_KEY_SUFFIXES)


def _redact_forbidden_strings(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "" if _is_private_key(key) else _redact_forbidden_strings(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_forbidden_strings(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_forbidden_strings(item) for item in value)
    if isinstance(value, str) and (
        _is_absolute_local_path(value)
        or _TRANSACTION_IDENTIFIER.search(value)
        or _TAX_IDENTIFIER.search(value)
        or _PRIVATE_APPLICATION_IDENTIFIER.search(value)
        or _EMAIL_ADDRESS.search(value)
    ):
        return ""
    return value


def _safe_nonnegative_int(value: Any, default: int = 0) -> int:
    try:
        return max(0, int(float(value)))
    except (TypeError, ValueError):
        return max(0, int(default))


def _redacted_trade() -> dict[str, Any]:
    trade = {key: "" for key in _LEGACY_TRADE_KEYS}
    trade["size_usd"] = None
    trade["details_redacted"] = True
    trade["public_claim_allowed"] = False
    return trade


def _redacted_grant_container(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, Mapping) else {}
    keys = list(dict.fromkeys((*_LEGACY_GRANT_KEYS, *(str(key) for key in source))))
    redacted: dict[str, Any] = {}
    for key in keys:
        redacted[key] = None if key.endswith("_usd") else ""
    redacted["details_redacted"] = True
    redacted["public_claim_allowed"] = False
    return redacted


def _redacted_artifact_container(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, Mapping) else {}
    keys = list(dict.fromkeys((*_LEGACY_ARTIFACT_KEYS, *(str(key) for key in source))))
    redacted = {key: "" for key in keys}
    redacted["details_redacted"] = True
    redacted["public_claim_allowed"] = False
    return redacted


def public_booth_projection(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return the stable public booth contract without operational detail values."""

    source = payload if isinstance(payload, Mapping) else {}
    public = _redact_forbidden_strings(copy.deepcopy(dict(source)))

    founder_source = public.get("founder_profile")
    if not isinstance(founder_source, Mapping):
        founder_source = {}
    public["founder_profile"] = {
        str(key): value
        for key, value in founder_source.items()
        if str(key).strip().casefold() not in _PRIVATE_PROFILE_KEYS
    }
    public["founder_profile"]["private_identifiers_embedded"] = False

    live_source = public.get("live_execution")
    if not isinstance(live_source, Mapping):
        live_source = {}
    heartbeat_source = live_source.get("heartbeat")
    if not isinstance(heartbeat_source, Mapping):
        heartbeat_source = {}
    raw_recent = live_source.get("recent_trades")
    fallback_count = len(raw_recent) if isinstance(raw_recent, list) else 0

    public["live_execution"] = {
        "heartbeat": {
            "status": str(heartbeat_source.get("status", "unknown") or "unknown"),
            "reason": "",
            "symbol": "",
            "universe_candidate_count": _safe_nonnegative_int(
                heartbeat_source.get("universe_candidate_count", 0)
            ),
            "timestamp_utc": str(heartbeat_source.get("timestamp_utc", "") or ""),
            "details_redacted": True,
            "public_claim_allowed": False,
        },
        "latest_trade": _redacted_trade(),
        "recent_trade_count": _safe_nonnegative_int(
            live_source.get("recent_trade_count", fallback_count),
            fallback_count,
        ),
        "recent_trades": [],
        "details_redacted": True,
        "public_claim_allowed": False,
        "profit_claim_allowed": False,
        "live_execution_authority": False,
    }

    mirror = public.get("premium_mirror")
    if not isinstance(mirror, dict):
        mirror = {}
    mirror["destination_root"] = ""
    mirror["details_redacted"] = True
    public["premium_mirror"] = mirror

    public["autonomous_grant_win"] = _redacted_grant_container(
        public.get("autonomous_grant_win")
    )
    public["artifacts"] = _redacted_artifact_container(public.get("artifacts"))
    public["artifact_paths"] = _redacted_artifact_container(public.get("artifact_paths"))

    public["supported_maturity_level"] = 3
    public["details_redacted"] = True
    public["public_claim_allowed"] = False
    public["profit_claim_allowed"] = False
    public["live_execution_authority"] = False
    public["level_5_attained"] = False
    public["claim_boundary"] = PUBLIC_BOOTH_CLAIM_BOUNDARY
    return public


def public_booth_contains_forbidden_value(payload: Any) -> bool:
    """Return True when a projected payload still contains an operational ID or local path."""

    if isinstance(payload, Mapping):
        return any(public_booth_contains_forbidden_value(value) for value in payload.values())
    if isinstance(payload, (list, tuple)):
        return any(public_booth_contains_forbidden_value(value) for value in payload)
    if not isinstance(payload, str):
        return False
    return bool(
        _is_absolute_local_path(payload)
        or _TRANSACTION_IDENTIFIER.search(payload)
        or _TAX_IDENTIFIER.search(payload)
        or _PRIVATE_APPLICATION_IDENTIFIER.search(payload)
        or _EMAIL_ADDRESS.search(payload)
    )
