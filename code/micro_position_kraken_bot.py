"""Read-only facade for the historical micro-position Kraken bot.

The complete duplicated legacy implementation is preserved in
``micro_position_kraken_bot_legacy.py``. The canonical script now produces a
single portfolio snapshot and exits. Both historical private transports are
patched so AddOrder is rejected before nonce creation, signing, or network
I/O.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


_CODE_DIR = Path(__file__).resolve().parent
_EXECUTION_DIR = _CODE_DIR / "execution"
for _path in (_CODE_DIR, _EXECUTION_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import micro_position_kraken_bot_legacy as _legacy
from execution.order_safety_gate import ORDER_POLICY, evaluate_order_request


ORDER_SAFETY_POLICY = ORDER_POLICY
ORDER_PROMOTION_STAGE = "live_data_no_orders"
_ORIGINAL_POST = _legacy._post
_ORIGINAL_KRAKEN_REQUEST = _legacy._kraken_request


def _blocked_payload(error_key: str, decision: Any) -> dict[str, Any]:
    return {
        error_key: ["ELUMEN:Order safety gate blocked live AddOrder"],
        "order_safety": decision.as_dict(),
    }


def _post(endpoint: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    decision = evaluate_order_request(endpoint, data)
    if not decision.allowed:
        return _blocked_payload("_error", decision)
    return _ORIGINAL_POST(endpoint, data)


def _kraken_request(
    endpoint: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = evaluate_order_request(endpoint, data)
    if not decision.allowed:
        return _blocked_payload("error", decision)
    return _ORIGINAL_KRAKEN_REQUEST(endpoint, data)


_legacy._post = _post
_legacy._kraken_request = _kraken_request

from micro_position_kraken_bot_legacy import *  # noqa: E402,F401,F403


def main() -> int:
    print("=" * 70)
    print("KRAKEN MICRO BOT | LIVE DATA SNAPSHOT | NO ORDERS")
    print("=" * 70)

    portfolio = _legacy.value_portfolio()
    if portfolio:
        total = float(portfolio.get("_total_usd", 0.0) or 0.0)
        print(f"[PORTFOLIO] estimated total=${total:.4f}")
    else:
        balance = _legacy.get_balance()
        total = float(balance.get("ZUSD", 0.0) or 0.0)
        print(f"[BALANCE] USD=${total:.4f}")

    print(
        f"[SAFETY] stage={ORDER_PROMOTION_STAGE} "
        f"policy={ORDER_SAFETY_POLICY}; trading loops not started"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
