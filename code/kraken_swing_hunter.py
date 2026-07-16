"""Read-only facade for the historical Kraken swing hunter.

The complete autonomous trading loop is preserved in
``kraken_swing_hunter_legacy.py``. Running this canonical module now performs a
single live-data ranking snapshot and exits. Imported legacy functions remain
available, but their private transport blocks every non-validate AddOrder
before nonce creation, signing, or network I/O.
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

import kraken_swing_hunter_legacy as _legacy
from execution.order_safety_gate import ORDER_POLICY, evaluate_order_request


ORDER_SAFETY_POLICY = ORDER_POLICY
ORDER_PROMOTION_STAGE = "live_data_no_orders"
_ORIGINAL_POST = _legacy._post


def _post(endpoint: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    decision = evaluate_order_request(endpoint, data)
    if not decision.allowed:
        return {
            "_error": ["ELUMEN:Order safety gate blocked live AddOrder"],
            "order_safety": decision.as_dict(),
        }
    return _ORIGINAL_POST(endpoint, data)


_legacy._post = _post

from kraken_swing_hunter_legacy import *  # noqa: E402,F401,F403


def main() -> int:
    print("=" * 65)
    print(" KRAKEN SWING HUNTER | LIVE DATA SNAPSHOT | NO ORDERS")
    print("=" * 65)

    balances = _legacy.get_balances()
    total = _legacy.portfolio_usd(balances)
    print(f"[PORTFOLIO] estimated total=${total:.4f}")

    movers = _legacy.scan_top_movers()
    print(f"[SCAN] candidates={len(movers)}")
    for pair, score, price, volume, range_pct, momentum_pct in movers[:5]:
        print(
            f"  {pair:20s} score={score:7.1f} range={range_pct:+6.1f}% "
            f"momentum={momentum_pct:+6.1f}% price=${price:.8f} "
            f"turnover=${volume:.0f}"
        )

    print(
        f"[SAFETY] stage={ORDER_PROMOTION_STAGE} "
        f"policy={ORDER_SAFETY_POLICY}; autonomous trading loop not started"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
