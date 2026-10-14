from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping


ADD_ORDER_PATH = "/0/private/AddOrder"
ORDER_POLICY = "validate_only_fail_closed"
# This boundary is intentionally closed to new private endpoints. Checking only
# AddOrder let batch, edit/amend and normalized path variants reach the signed
# transport. Reads required by account/reconciliation tooling remain available;
# all private mutations except exact validate-only AddOrder fail before I/O.
READ_ONLY_PRIVATE_PATHS = frozenset({
    "/0/private/Balance",
    "/0/private/BalanceEx",
    "/0/private/TradeBalance",
    "/0/private/OpenOrders",
    "/0/private/ClosedOrders",
    "/0/private/QueryOrders",
    "/0/private/TradesHistory",
    "/0/private/QueryTrades",
    "/0/private/OpenPositions",
    "/0/private/Ledgers",
    "/0/private/QueryLedgers",
    "/0/private/TradeVolume",
})


class OrderSafetyError(RuntimeError):
    """Raised before credentials or network I/O when an order request is unsafe."""


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


def evaluate_order_request(
    url_path: str,
    payload: Mapping[str, Any] | None,
) -> OrderSafetyDecision:
    safe_payload: Mapping[str, Any] = payload if isinstance(payload, Mapping) else {}
    payload_sha256 = _payload_hash(safe_payload)

    if isinstance(url_path, str) and url_path in READ_ONLY_PRIVATE_PATHS:
        return OrderSafetyDecision(
            allowed=True,
            policy=ORDER_POLICY,
            mode="non_order_private_call",
            reason="request is an explicitly allowed read-only private call",
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

    return OrderSafetyDecision(
        allowed=False,
        policy=ORDER_POLICY,
        mode=(
            "blocked_live_order"
            if url_path == ADD_ORDER_PATH
            else "blocked_private_side_effect"
        ),
        reason=(
            "AddOrder is blocked unless validate is explicitly true"
            if url_path == ADD_ORDER_PATH
            else "private endpoint is not on the read-only allowlist; "
            "mutations and unknown routes are blocked"
        ),
        url_path=str(url_path),
        payload_sha256=payload_sha256,
    )


def require_order_request_allowed(
    url_path: str,
    payload: Mapping[str, Any] | None,
) -> OrderSafetyDecision:
    decision = evaluate_order_request(url_path, payload)
    if not decision.allowed:
        raise OrderSafetyError(
            f"Order safety gate blocked {decision.url_path}: {decision.reason}; "
            f"payload_sha256={decision.payload_sha256}"
        )
    return decision
