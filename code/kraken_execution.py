"""Fail-closed facade for the legacy Kraken execution module.

The historical implementation is preserved byte-for-byte in
``kraken_execution_legacy.py`` for auditability. This facade is the public
import surface. It blocks every Kraken AddOrder request unless the payload is
explicitly validate-only and replaces the legacy validate-only helper with a
side-effect-bounded implementation.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import kraken_execution_legacy as _legacy
from execution.order_safety_gate import (
    ORDER_POLICY,
    OrderSafetyDecision,
    OrderSafetyError,
    require_order_request_allowed,
)
from kraken_execution_legacy import *  # noqa: F401,F403


ORDER_SAFETY_POLICY = ORDER_POLICY
_ORIGINAL_PRIVATE_POST = _legacy._private_post


def _private_post(
    url_path: str,
    payload: Dict[str, Any],
    timeout: int = 20,
    retry_attempt: int = 0,
) -> Dict[str, Any]:
    """Apply the no-live-order gate before keys, nonces, or network I/O."""

    try:
        require_order_request_allowed(url_path, payload)
    except OrderSafetyError as exc:
        raise _legacy.KrakenExecutionError(str(exc)) from exc

    return _ORIGINAL_PRIVATE_POST(
        url_path,
        payload,
        timeout=timeout,
        retry_attempt=retry_attempt,
    )


# Legacy functions resolve globals in the legacy module. Rebinding its private
# transport makes the gate central for every caller that reaches AddOrder.
_legacy._private_post = _private_post


def submit_order_validate_only(
    *,
    controller: str,
    pair: Optional[str] = None,
    side: str = "buy",
    notional_usd: Optional[float] = None,
    volume_base: Optional[float] = None,
    ordertype: str = "market",
    note: str = "",
) -> Dict[str, Any]:
    """Validate an order payload without placing or arming a live order."""

    _legacy.assert_controller(controller)
    flags = _legacy._ensure_flags()
    pair = pair or str(flags.get("default_pair", "XBTUSD"))

    if notional_usd is None and volume_base is None:
        volume_base = float(flags.get("default_volume_base", 0.0004))

    if volume_base is None:
        last_price = _legacy.get_last_price(pair)
        if last_price <= 0:
            raise _legacy.KrakenExecutionError(
                "Could not derive last price for notional sizing"
            )
        volume_base = float(notional_usd) / float(last_price)

    if notional_usd is None:
        last_price = _legacy.get_last_price(pair)
        notional_usd = float(volume_base) * float(last_price)

    _legacy.enforce_risk(
        symbol=pair,
        side=side,
        notional_usd=float(notional_usd),
    )

    payload = _legacy._build_order_payload(
        pair=pair,
        side=side,
        volume_base=float(volume_base),
        ordertype=ordertype,
        validate=True,
        userref=int(time.time()),
    )
    safety_decision: OrderSafetyDecision = require_order_request_allowed(
        _legacy.ADD_ORDER_PATH,
        payload,
    )

    # A validate-only request creates no order, so arming CancelAllOrdersAfter
    # would add an unnecessary private side effect and is intentionally skipped.
    deadman_result = {
        "skipped": True,
        "reason": "validate-only request creates no live order",
    }
    validation_result = _private_post(_legacy.ADD_ORDER_PATH, payload)

    result: Dict[str, Any] = {
        "timestamp": _legacy._now_iso(),
        "mode": "VALIDATE_ONLY",
        "controller": controller,
        "pair": pair,
        "side": side,
        "notional_usd": float(notional_usd),
        "volume_base": float(volume_base),
        "payload": payload,
        "order_safety": safety_decision.as_dict(),
        "deadman_result": deadman_result,
        "validation_result": validation_result,
    }

    ticket = _legacy.queue_approval_ticket(
        controller=controller,
        pair=pair,
        side=side,
        notional_usd=float(notional_usd),
        volume_base=float(volume_base),
        payload=payload,
        note=note or "Validated only; no live order authorized.",
    )
    result["approval_ticket"] = ticket

    _legacy._append_jsonl(_legacy.INTENTS_FILE, result)
    _legacy._append_jsonl(
        _legacy.EVENTS_FILE,
        {"event": "submit_order_validate_only", **result},
    )
    _legacy._write_json(_legacy.LAST_RESULT_FILE, result)
    _legacy._runtime_snapshot(
        last_pair=pair,
        last_side=side,
        last_mode="VALIDATE_ONLY",
        order_safety_policy=ORDER_SAFETY_POLICY,
    )
    return result


# Any code holding a reference to the imported legacy module receives the same
# corrected helper after the facade is imported.
_legacy.submit_order_validate_only = submit_order_validate_only
