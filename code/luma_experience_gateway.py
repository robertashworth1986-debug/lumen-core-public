"""Fail-closed facade for the Luma Experience Gateway.

The full FastAPI implementation is preserved in
``luma_experience_gateway_legacy.py``. This facade keeps the same ``app``
object and routes while enforcing validate-only behavior at the final signed
Kraken AddOrder boundary.
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

import luma_experience_gateway_legacy as _legacy
from execution.order_safety_gate import (
    ADD_ORDER_PATH,
    ORDER_POLICY,
    evaluate_order_request,
)
from operator_api_access import install_operator_api_access


ORDER_SAFETY_POLICY = ORDER_POLICY
_ORIGINAL_KRAKEN_ADD_ORDER = _legacy._kraken_add_order


def _kraken_add_order(payload: dict[str, Any]) -> dict[str, Any]:
    """Reject live AddOrder payloads before key loading, signing, or I/O."""

    decision = evaluate_order_request(ADD_ORDER_PATH, payload)
    if not decision.allowed:
        return {
            "error": ["ELUMEN:Order safety gate blocked live AddOrder"],
            "order_safety": decision.as_dict(),
        }
    return _ORIGINAL_KRAKEN_ADD_ORDER(payload)


# Approval route functions retain the legacy module as their globals mapping,
# so patch that mapping before exposing the public FastAPI app.
_legacy._kraken_add_order = _kraken_add_order

from luma_experience_gateway_legacy import *  # noqa: E402,F401,F403

app = _legacy.app
if hasattr(app, "add_middleware"):
    install_operator_api_access(app)


def _operator_health() -> dict[str, Any]:
    """Retain detailed legacy health behind the operator API boundary."""

    return _legacy.health()


if hasattr(app, "add_api_route") and not any(
    getattr(route, "path", "") == "/api/operator/health"
    for route in getattr(app, "routes", ())
):
    app.add_api_route(
        "/api/operator/health",
        _operator_health,
        methods=["GET"],
        include_in_schema=False,
    )
    # The legacy app ends with a catch-all static mount. Move this protected
    # route ahead of that mount so it cannot be shadowed as a static 404.
    app.router.routes.insert(0, app.router.routes.pop())


def main() -> int:
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8787,
        reload=False,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
