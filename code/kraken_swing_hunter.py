#!/usr/bin/env python3
"""Quarantined legacy live Kraken swing hunter.

The previous implementation could load credentials, inspect balances, and
place unattended orders. It is deliberately retired from executable use so
old autopilot launchers stop safely instead of trading.
"""

from __future__ import annotations

import json


SAFE_SPINE = (
    "code/execution/live_runtime_guard.py",
    "code/execution/order_router.py",
    "code/execution/risk_kernel.py",
    "code/ops/BUILD_TRADING_STACK_SAFETY_AUDIT.py",
)


def main() -> int:
    print(
        json.dumps(
            {
                "status": "QUARANTINED_LEGACY_LIVE_BOT",
                "action": "no credentials, balances, market data, or orders were accessed",
                "next_path": "use the paper/replay safe spine and its separate human approval gates",
                "safe_spine": SAFE_SPINE,
            },
            indent=2,
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
