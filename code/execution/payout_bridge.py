#!/usr/bin/env python3
"""Inert compatibility facade for the retired automatic payout dispatcher.

The former implementation could load destinations and send payout intents to
an external service. Capital dispatch is prohibited in the current
``live_data_no_orders`` promotion stage. This module performs no credential
loading, destination lookup, file mutation, or network I/O.
"""

from __future__ import annotations

import json
from typing import Any


POLICY = "CAPITAL_DISPATCH_BLOCKED"
PROMOTION_STAGE = "live_data_no_orders"


def build_inert_status() -> dict[str, Any]:
    """Return blocked status without reading an intent, destination, or secret."""

    return {
        "status": "blocked",
        "policy": POLICY,
        "promotion_stage": PROMOTION_STAGE,
        "credentials_loaded": False,
        "network_access": False,
        "destination_loaded": False,
        "payout_intents_loaded": False,
        "transfer_authorized": False,
        "reason": (
            "Automatic capital dispatch is retired. A separately reviewed, "
            "human-confirmed custody workflow is required."
        ),
    }


def main() -> int:
    print(json.dumps(build_inert_status(), sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
