"""Fail-closed facade for the Luma Experience Gateway.

The full FastAPI implementation is preserved in
``luma_experience_gateway_legacy.py``. This facade keeps the same ``app``
object and routes while enforcing validate-only behavior at the final signed
Kraken AddOrder boundary.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


_CODE_DIR = Path(__file__).resolve().parent
_EXECUTION_DIR = _CODE_DIR / "execution"
for _path in (_CODE_DIR, _EXECUTION_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from execution.order_safety_gate import (
    ADD_ORDER_PATH,
    ORDER_POLICY,
    evaluate_order_request,
)
from operator_api_access import install_operator_api_access


ORDER_SAFETY_POLICY = ORDER_POLICY
_SERVING_PROFILE = os.getenv("LUMA_GATEWAY_SERVING_PROFILE", "operator").strip().lower()
if _SERVING_PROFILE not in {"operator", "minimal"}:
    raise ValueError("LUMA_GATEWAY_SERVING_PROFILE must be operator or minimal")
_legacy = None
_ORIGINAL_KRAKEN_ADD_ORDER = None
if _SERVING_PROFILE == "operator":
    import luma_experience_gateway_legacy as _legacy

    _ORIGINAL_KRAKEN_ADD_ORDER = getattr(
        _legacy._kraken_add_order, "_lumencore_original_adapter", _legacy._kraken_add_order
    )


def _kraken_add_order(payload: dict[str, Any]) -> dict[str, Any]:
    """Reject live AddOrder payloads before key loading, signing, or I/O."""

    decision = evaluate_order_request(ADD_ORDER_PATH, payload)
    if not decision.allowed:
        return {
            "error": ["ELUMEN:Order safety gate blocked live AddOrder"],
            "order_safety": decision.as_dict(),
        }
    if _ORIGINAL_KRAKEN_ADD_ORDER is None:
        return {"error": ["ELUMEN:Minimal reviewer profile has no order adapter"]}
    return _ORIGINAL_KRAKEN_ADD_ORDER(payload)


if _legacy is not None:
    # Approval routes retain the legacy module as their globals mapping.
    # Keep repeated facade imports/reloads from wrapping this function itself.
    _kraken_add_order._lumencore_original_adapter = _ORIGINAL_KRAKEN_ADD_ORDER
    _legacy._kraken_add_order = _kraken_add_order
    from luma_experience_gateway_legacy import *  # noqa: E402,F401,F403

    app = _legacy.app
else:
    from fastapi import FastAPI, HTTPException

    # Explicit review-only profile: no legacy imports, worker tasks, files,
    # providers, trading adapters or optional operator-feature graph.
    app = FastAPI(title="Luma Gateway Minimal Reviewer Profile", version="1.0.0")

    @app.get("/")
    def minimal_profile():
        return {"profile": "minimal", "operational_readiness": "HOLD"}

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def unavailable_operator_component(path: str):
        raise HTTPException(status_code=503, detail="operator components remain HOLD in minimal reviewer profile")

if hasattr(app, "add_middleware"):
    install_operator_api_access(app)

if _legacy is not None and hasattr(app, "add_api_route"):
    from operator_feed_reads import install_private_feed_routes

    install_private_feed_routes(app, _legacy.ROOT)


def _operator_health() -> dict[str, Any]:
    """Retain detailed legacy health behind the operator API boundary."""

    if _legacy is None:
        return {
            "profile": "minimal",
            "operational_readiness": "HOLD",
            "optional_components": "not_loaded",
            "background_workers": "not_started",
        }
    return {**_legacy.health(), "optional_components": dict(_legacy.GATEWAY_OPTIONAL_COMPONENTS)}


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
        host=os.getenv("LUMA_GATEWAY_HOST", "127.0.0.1" if _SERVING_PROFILE == "minimal" else "0.0.0.0"),
        port=int(os.getenv("LUMA_GATEWAY_PORT", "8787")),
        reload=False,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

