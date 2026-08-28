#!/usr/bin/env python3
"""Inert compatibility facade for the retired Kraken withdrawal utility.

The historical implementation loaded credentials, inspected balances, and
could submit a capital transfer automatically. That behavior is prohibited in
the current ``live_data_no_orders`` promotion stage. This module deliberately
does not import an exchange SDK, load credentials, read a destination address,
perform network I/O, or expose an execution switch.
"""

from __future__ import annotations

import json
from typing import Any


POLICY = "CAPITAL_TRANSFER_BLOCKED"
PROMOTION_STAGE = "live_data_no_orders"


def build_inert_status() -> dict[str, Any]:
    """Return the fail-closed status without touching credentials or a network."""

    return {
        "status": "blocked",
        "policy": POLICY,
        "promotion_stage": PROMOTION_STAGE,
        "credentials_loaded": False,
        "network_access": False,
        "destination_address_loaded": False,
        "withdrawal_authorized": False,
        "reason": (
            "Automated capital transfer is retired. A separately reviewed, "
            "human-confirmed custody workflow is required."
        ),
    }


def main() -> int:
    print(json.dumps(build_inert_status(), sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
