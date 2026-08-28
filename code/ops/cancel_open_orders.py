#!/usr/bin/env python3
"""Inert compatibility facade for the retired automatic order-cancellation tool.

The former script loaded live credentials and performed an account mutation as
an import-time side effect. That behavior is prohibited in the current
``live_data_no_orders`` promotion stage. Emergency cancellation requires a
separately reviewed, interactive, receipt-backed workflow.
"""

from __future__ import annotations

import json
from typing import Any


POLICY = "VENUE_MUTATION_BLOCKED"
PROMOTION_STAGE = "live_data_no_orders"


def build_inert_status() -> dict[str, Any]:
    """Return blocked status without loading credentials or touching a network."""

    return {
        "status": "blocked",
        "policy": POLICY,
        "promotion_stage": PROMOTION_STAGE,
        "credentials_loaded": False,
        "network_access": False,
        "open_orders_loaded": False,
        "mutation_authorized": False,
        "reason": (
            "Automatic venue mutation is retired. Use a separately reviewed "
            "interactive emergency workflow."
        ),
    }


def main() -> int:
    print(json.dumps(build_inert_status(), sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
