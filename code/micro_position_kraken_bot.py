#!/usr/bin/env python3
"""Quarantined legacy live Kraken scalper.

This file formerly loaded local exchange credentials and placed unattended
orders. It is intentionally retired from executable use. Preserve it only as
a named boundary so legacy launchers fail closed rather than trading.
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
