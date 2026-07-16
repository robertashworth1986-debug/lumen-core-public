"""Fail-closed facade for the historical live executor.

The complete implementation is preserved byte-for-byte in
``live_executor_legacy.py``. This module remains the canonical import and
script path, but every Kraken AddOrder request is evaluated before nonce
creation, signing, credential use, or network I/O.

Current promotion stage: live market data with no live orders.
"""

from __future__ import annotations

import atexit
import os
import sys
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import live_executor_legacy as _legacy
from order_safety_gate import ADD_ORDER_PATH, ORDER_POLICY, evaluate_order_request


ORDER_SAFETY_POLICY = ORDER_POLICY
_ORIGINAL_KRAKEN_PRIVATE = _legacy.KrakenClient._private


def _guarded_kraken_private(
    self: Any,
    endpoint: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Block non-validate AddOrder before the legacy private transport runs."""

    decision = evaluate_order_request(endpoint, data)
    if not decision.allowed:
        return {
            "error": ["ELUMEN:Order safety gate blocked live AddOrder"],
            "order_safety": decision.as_dict(),
        }
    return _ORIGINAL_KRAKEN_PRIVATE(self, endpoint, data)


# Legacy methods resolve KrakenClient._private dynamically. Rebinding the class
# method therefore protects send_order and every other AddOrder caller in the
# preserved executor without changing the 10,000-line implementation.
_legacy.KrakenClient._private = _guarded_kraken_private

from live_executor_legacy import *  # noqa: E402,F401,F403

# Make the protected class explicit for tools that inspect module attributes.
KrakenClient = _legacy.KrakenClient
RobustLiveExecutor = _legacy.RobustLiveExecutor


def main() -> int:
    duplicate_child, root_pid = _legacy._is_duplicate_child_executor()
    if duplicate_child:
        _legacy._write_live_heartbeat(
            {
                "status": "blocked",
                "reason": "duplicate_child_executor",
                "root_pid": int(root_pid),
                "pid": int(os.getpid()),
                "order_safety_policy": ORDER_SAFETY_POLICY,
            }
        )
        print(
            f"duplicate child live_executor detected "
            f"(root_pid={root_pid}, pid={os.getpid()})"
        )
        return 0

    os.environ["LUMA_LIVE_EXECUTOR_ROOT_PID"] = str(os.getpid())

    if not _legacy._acquire_executor_lock():
        return 0
    atexit.register(_legacy._release_executor_lock)

    api_keys = _legacy.load_api_keys()
    executor = _legacy.RobustLiveExecutor(api_keys)
    _legacy._write_live_heartbeat(
        {
            "status": "starting",
            "reason": "live_data_no_orders",
            "order_safety_policy": ORDER_SAFETY_POLICY,
            "add_order_mode": "validate_only_fail_closed",
        }
    )
    try:
        executor.run_institutional_execution_loop()
    finally:
        _legacy._release_executor_lock()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
