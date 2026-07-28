"""Fail-closed facade for the Luma Experience Gateway.

The full FastAPI implementation is preserved in
``luma_experience_gateway_legacy.py``. This facade keeps the same ``app``
object and routes while enforcing validate-only behavior at the final signed
Kraken AddOrder boundary.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable


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


ORDER_SAFETY_POLICY = ORDER_POLICY
_ORIGINAL_KRAKEN_ADD_ORDER = _legacy._kraken_add_order
PUBLIC_GATEWAY_METHODS = frozenset({"GET", "HEAD"})
PUBLIC_GATEWAY_PATHS = frozenset(
    {
        "/health",
        "/api/master/booth-brief",
    }
)
PUBLIC_HEALTH_SCHEMA = "lumencore.public_gateway_health.v1"
PUBLIC_HEALTH_CLAIM_BOUNDARY = (
    "This is a current, bounded process-health signal. It does not disclose "
    "service topology and does not prove uptime, performance, security, "
    "savings, validation, eligibility, or award."
)


def public_gateway_request_allowed(
    method: str,
    path: str,
    *,
    operator_routes_enabled: bool = False,
) -> bool:
    if operator_routes_enabled:
        return True
    return (
        str(method).upper() in PUBLIC_GATEWAY_METHODS
        and str(path) in PUBLIC_GATEWAY_PATHS
    )


def _safe_utc_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return ""
    return (
        parsed.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def public_health_projection(payload: Any) -> dict[str, Any]:
    source = payload if isinstance(payload, dict) else {}
    all_healthy = source.get("all_healthy") is True
    status = "ok" if source.get("status") == "ok" and all_healthy else "degraded"
    return {
        "schema": PUBLIC_HEALTH_SCHEMA,
        "generated_utc": _safe_utc_timestamp(source.get("generated_utc")),
        "status": status,
        "all_healthy": status == "ok",
        "claim_boundary": PUBLIC_HEALTH_CLAIM_BOUNDARY,
    }


class PublicGatewayAllowlistApp:
    """ASGI boundary that defaults the legacy gateway to two public GET routes."""

    def __init__(
        self,
        inner: Callable[..., Awaitable[None]],
        *,
        operator_routes_enabled: bool | None = None,
        health_provider: Callable[[], Any] | None = None,
    ) -> None:
        self.inner = inner
        self.health_provider = health_provider
        self.operator_routes_enabled = (
            os.environ.get("LUMENCORE_GATEWAY_OPERATOR_ROUTES") == "1"
            if operator_routes_enabled is None
            else operator_routes_enabled
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[..., Awaitable[dict[str, Any]]],
        send: Callable[..., Awaitable[None]],
    ) -> None:
        scope_type = str(scope.get("type", ""))
        if scope_type == "lifespan" or self.operator_routes_enabled:
            await self.inner(scope, receive, send)
            return

        if scope_type == "http" and public_gateway_request_allowed(
            str(scope.get("method", "")),
            str(scope.get("path", "")),
        ):
            if (
                str(scope.get("path", "")) == "/health"
                and self.health_provider is not None
            ):
                try:
                    payload = public_health_projection(self.health_provider())
                    status = 200
                except Exception:
                    payload = public_health_projection({})
                    status = 503
                body = json.dumps(
                    payload,
                    ensure_ascii=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                await send(
                    {
                        "type": "http.response.start",
                        "status": status,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"cache-control", b"no-store"),
                            (
                                b"content-length",
                                str(len(body)).encode("ascii"),
                            ),
                        ],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": (
                            b""
                            if str(scope.get("method", "")).upper() == "HEAD"
                            else body
                        ),
                    }
                )
                return
            await self.inner(scope, receive, send)
            return

        if scope_type == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return

        body = json.dumps(
            {"detail": "not found"},
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 404,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"cache-control", b"no-store"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


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

legacy_app = _legacy.app
app = PublicGatewayAllowlistApp(
    legacy_app,
    health_provider=getattr(_legacy, "health", None),
)


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
