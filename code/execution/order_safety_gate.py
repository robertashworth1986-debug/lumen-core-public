from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping


ADD_ORDER_PATH = "/0/private/AddOrder"
CANCEL_ALL_AFTER_PATH = "/0/private/CancelAllOrdersAfter"
READ_ONLY_PRIVATE_PATHS = frozenset(
    {
        "/0/private/Balance",
        "/0/private/OpenOrders",
        "/0/private/QueryOrders",
        "/0/private/TradesHistory",
        "/0/private/TradeBalance",
    }
)
ORDER_POLICY = "private_endpoint_allowlist_fail_closed"
MANUAL_LIQUIDATION_SCOPE = "manual_emergency_liquidation_to_usd"
MANUAL_AUTHORIZATION_MAX_AGE_SECONDS = 300.0


class OrderSafetyError(RuntimeError):
    """Raised before credentials or network I/O when a private request is unsafe."""


@dataclass(frozen=True)
class EmergencyMutationAuthorization:
    """Short-lived, receipt-backed capability for one reviewed emergency scope."""

    scope: str
    authorization_sha256: str
    authorized_utc: str
    expires_utc: str


@dataclass(frozen=True)
class OrderSafetyDecision:
    allowed: bool
    policy: str
    mode: str
    reason: str
    url_path: str
    payload_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _payload_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _is_validate_only(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return False


def _parse_utc(value: Any) -> datetime:
    raw = str(value or "").strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise OrderSafetyError("manual emergency authorization timestamp is invalid") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def build_manual_emergency_authorization(
    record: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> EmergencyMutationAuthorization:
    """Verify a fresh interactive liquidation receipt and mint a narrow capability."""

    required_true = (
        "authorized",
        "execute",
        "interactive_terminal",
        "command_line_confirmation",
        "interactive_confirmation",
    )
    missing = [name for name in required_true if record.get(name) is not True]
    if missing:
        raise OrderSafetyError(
            "manual emergency authorization is incomplete: " + ",".join(missing)
        )

    scope = str(record.get("scope", "") or "").strip()
    if scope != MANUAL_LIQUIDATION_SCOPE:
        raise OrderSafetyError("manual emergency authorization scope is not approved")

    reason = str(record.get("reason", "") or "").strip()
    if len(reason) < 8:
        raise OrderSafetyError("manual emergency authorization reason is incomplete")

    authorized_utc = str(record.get("authorized_utc", "") or "").strip()
    authorized_at = _parse_utc(authorized_utc)
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    age_seconds = (reference.astimezone(timezone.utc) - authorized_at).total_seconds()
    if age_seconds < -30.0 or age_seconds > MANUAL_AUTHORIZATION_MAX_AGE_SECONDS:
        raise OrderSafetyError("manual emergency authorization is stale or future-dated")

    material = {
        "authorized_utc": authorized_utc,
        "scope": scope,
        "reason": reason,
        "interactive_terminal": True,
        "command_line_confirmation": True,
        "interactive_confirmation": True,
    }
    expected_digest = hashlib.sha256(
        json.dumps(
            material,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    supplied_digest = str(record.get("authorization_sha256", "") or "").strip().lower()
    if supplied_digest != expected_digest:
        raise OrderSafetyError("manual emergency authorization receipt digest is invalid")

    return EmergencyMutationAuthorization(
        scope=scope,
        authorization_sha256=supplied_digest,
        authorized_utc=authorized_utc,
        expires_utc=(
            authorized_at + timedelta(seconds=MANUAL_AUTHORIZATION_MAX_AGE_SECONDS)
        ).isoformat(),
    )


def _manual_liquidation_request_allowed(
    url_path: str,
    payload: Mapping[str, Any],
    authorization: EmergencyMutationAuthorization | None,
) -> bool:
    if authorization is None or authorization.scope != MANUAL_LIQUIDATION_SCOPE:
        return False
    try:
        if datetime.now(timezone.utc) > _parse_utc(authorization.expires_utc):
            return False
    except OrderSafetyError:
        return False
    if url_path == ADD_ORDER_PATH:
        return (
            str(payload.get("type", "") or "").strip().lower() == "sell"
            and str(payload.get("ordertype", "") or "").strip().lower() == "market"
            and not str(payload.get("leverage", "") or "").strip()
        )
    if url_path == CANCEL_ALL_AFTER_PATH:
        try:
            timeout_seconds = int(payload.get("timeout", 0) or 0)
        except (TypeError, ValueError):
            return False
        return 1 <= timeout_seconds <= 300
    return False


def evaluate_order_request(
    url_path: str,
    payload: Mapping[str, Any] | None,
    *,
    emergency_authorization: EmergencyMutationAuthorization | None = None,
) -> OrderSafetyDecision:
    safe_payload: Mapping[str, Any] = payload if isinstance(payload, Mapping) else {}
    payload_sha256 = _payload_hash(safe_payload)

    if url_path in READ_ONLY_PRIVATE_PATHS:
        return OrderSafetyDecision(
            allowed=True,
            policy=ORDER_POLICY,
            mode="read_only_private_call",
            reason="request is on the explicit read-only private endpoint allowlist",
            url_path=str(url_path),
            payload_sha256=payload_sha256,
        )

    if url_path == ADD_ORDER_PATH and _is_validate_only(safe_payload.get("validate")):
        return OrderSafetyDecision(
            allowed=True,
            policy=ORDER_POLICY,
            mode="validate_only",
            reason="Kraken validate flag is explicitly true",
            url_path=str(url_path),
            payload_sha256=payload_sha256,
        )

    if _manual_liquidation_request_allowed(
        url_path,
        safe_payload,
        emergency_authorization,
    ):
        return OrderSafetyDecision(
            allowed=True,
            policy=ORDER_POLICY,
            mode="manual_emergency_liquidation",
            reason="fresh reviewed emergency receipt permits this scoped mutation",
            url_path=str(url_path),
            payload_sha256=payload_sha256,
        )

    return OrderSafetyDecision(
        allowed=False,
        policy=ORDER_POLICY,
        mode=("blocked_live_order" if url_path == ADD_ORDER_PATH else "blocked_private_mutation"),
        reason=(
            "AddOrder is blocked unless validate is explicitly true or a reviewed "
            "manual liquidation receipt permits a market sell"
            if url_path == ADD_ORDER_PATH
            else "private endpoint is not on the read-only allowlist and has no reviewed emergency exception"
        ),
        url_path=str(url_path),
        payload_sha256=payload_sha256,
    )


def require_order_request_allowed(
    url_path: str,
    payload: Mapping[str, Any] | None,
    *,
    emergency_authorization: EmergencyMutationAuthorization | None = None,
) -> OrderSafetyDecision:
    decision = evaluate_order_request(
        url_path,
        payload,
        emergency_authorization=emergency_authorization,
    )
    if not decision.allowed:
        raise OrderSafetyError(
            f"Order safety gate blocked {decision.url_path}: {decision.reason}; "
            f"payload_sha256={decision.payload_sha256}"
        )
    return decision
