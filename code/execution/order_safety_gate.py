from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping


ADD_ORDER_PATH = "/0/private/AddOrder"
ORDER_POLICY = "validate_only_fail_closed"


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

    if url_path != ADD_ORDER_PATH:
        return OrderSafetyDecision(
            allowed=True,
            policy=ORDER_POLICY,
            mode="non_order_private_call",
            reason="request is not an AddOrder submission",
            url_path=str(url_path),
            payload_sha256=payload_sha256,
        )

    if _is_validate_only(safe_payload.get("validate")):
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
        mode="blocked_live_order",
        reason="AddOrder is blocked unless validate is explicitly true",
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
