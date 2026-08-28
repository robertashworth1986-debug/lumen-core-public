from __future__ import annotations

import asyncio
import json
import os
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

try:
    import httpx
except ImportError:  # pragma: no cover - integration test is skipped
    httpx = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from operator_api_access import (  # noqa: E402
    OperatorApiAccessMiddleware,
    PUBLIC_HEALTH_PATH,
    PUBLIC_STATUS_PATH,
    expected_operator_tokens,
    install_operator_api_access,
    presented_operator_token,
    public_health_payload,
    public_status_payload,
)


class _ProbeApp:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def __call__(self, scope, receive, send) -> None:
        self.calls.append(scope)
        if scope["type"] == "http":
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b"", "more_body": False})
        else:
            await send({"type": "websocket.accept"})


def _scope(
    path: str,
    *,
    method: str = "GET",
    scope_type: str = "http",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> dict[str, Any]:
    return {
        "type": scope_type,
        "path": path,
        "method": method,
        "headers": headers or [],
    }


def _invoke(middleware: OperatorApiAccessMiddleware, scope: dict[str, Any]):
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    asyncio.run(middleware(scope, receive, send))
    return sent


def _status(messages: list[dict[str, Any]]) -> int | None:
    for message in messages:
        if message.get("type") == "http.response.start":
            return int(message["status"])
    return None


def _body(messages: list[dict[str, Any]]) -> bytes:
    return b"".join(message.get("body", b"") for message in messages)


class OperatorApiAccessTests(unittest.TestCase):
    def test_tokens_are_split_deduplicated_and_never_defaulted(self) -> None:
        self.assertEqual(expected_operator_tokens({}), ())
        self.assertEqual(
            expected_operator_tokens(
                {
                    "LUMA_OPERATOR_API_TOKEN": "a" * 32,
                    "LUMA_OPERATOR_API_TOKENS": f"{'b' * 32}, {'a' * 32}\n{'c' * 32},short",
                }
            ),
            ("a" * 32, "b" * 32, "c" * 32),
        )

    def test_sensitive_gets_fail_closed_without_runtime_token(self) -> None:
        for path in (
            "/api/kraken/balance",
            "/api/master/approval-queue",
            "/api/funding/approval-queue",
            "/api/grants",
            "/api/snapshot",
            "/api/operator/health",
            "/metrics",
            "/metrics/",
            "/openapi.json",
            "/docs",
            "/docs/oauth2-redirect",
            "/redoc",
        ):
            with self.subTest(path=path):
                app = _ProbeApp()
                middleware = OperatorApiAccessMiddleware(app, token_provider=lambda: ())
                messages = _invoke(middleware, _scope(path))
                self.assertEqual(_status(messages), 503)
                self.assertEqual(app.calls, [])
                self.assertNotIn(b"alpha", b"".join(m.get("body", b"") for m in messages))

    def test_runtime_introspection_requires_valid_operator_token(self) -> None:
        secret = "introspection-secret-000000000000000"
        app = _ProbeApp()
        middleware = OperatorApiAccessMiddleware(
            app,
            token_provider=lambda: (secret,),
        )

        for path in (
            "/metrics",
            "/metrics/",
            "/openapi.json",
            "/docs",
            "/docs/oauth2-redirect",
            "/redoc",
        ):
            with self.subTest(path=path, credential="missing"):
                self.assertEqual(_status(_invoke(middleware, _scope(path))), 401)
            with self.subTest(path=path, credential="valid"):
                allowed = _invoke(
                    middleware,
                    _scope(
                        path,
                        headers=[(b"authorization", f"Bearer {secret}".encode())],
                    ),
                )
                self.assertEqual(_status(allowed), 204)

        self.assertEqual(len(app.calls), 6)

    def test_introspection_root_matching_does_not_overblock_nearby_paths(self) -> None:
        app = _ProbeApp()
        middleware = OperatorApiAccessMiddleware(app, token_provider=lambda: ())

        for path in (
            "/documentation",
            "/metrics-export",
            "/openapi.jsonld",
            "/redocument",
        ):
            with self.subTest(path=path):
                self.assertEqual(_status(_invoke(middleware, _scope(path))), 204)

        self.assertEqual(len(app.calls), 4)

    def test_sensitive_get_requires_valid_bearer_or_operator_header(self) -> None:
        app = _ProbeApp()
        middleware = OperatorApiAccessMiddleware(
            app,
            token_provider=lambda: ("correct-horse-battery-staple-0001",),
        )

        missing = _invoke(middleware, _scope("/api/kraken/balance"))
        invalid = _invoke(
            middleware,
            _scope(
                "/api/kraken/balance",
                headers=[(b"authorization", b"Bearer wrong")],
            ),
        )
        valid_bearer = _invoke(
            middleware,
            _scope(
                "/api/kraken/balance",
                headers=[
                    (b"authorization", b"Bearer correct-horse-battery-staple-0001")
                ],
            ),
        )
        valid_header = _invoke(
            middleware,
            _scope(
                "/api/master/approval-queue",
                headers=[
                    (b"x-luma-operator-token", b"correct-horse-battery-staple-0001")
                ],
            ),
        )

        self.assertEqual(_status(missing), 401)
        self.assertEqual(_status(invalid), 401)
        self.assertEqual(_status(valid_bearer), 204)
        self.assertEqual(_status(valid_header), 204)
        self.assertEqual(len(app.calls), 2)

    def test_conflicting_credentials_are_rejected(self) -> None:
        scope = _scope(
            "/api/kraken/balance",
            headers=[
                (b"authorization", b"Bearer first"),
                (b"x-luma-operator-token", b"second"),
            ],
        )
        self.assertEqual(presented_operator_token(scope), "")

    def test_public_status_and_health_are_minimal_liveness_only(self) -> None:
        app = _ProbeApp()
        middleware = OperatorApiAccessMiddleware(app, token_provider=lambda: ())
        public = _invoke(middleware, _scope(PUBLIC_STATUS_PATH))
        public_head = _invoke(
            middleware,
            _scope(PUBLIC_STATUS_PATH, method="HEAD"),
        )
        health = _invoke(middleware, _scope(PUBLIC_HEALTH_PATH))
        health_head = _invoke(
            middleware,
            _scope(PUBLIC_HEALTH_PATH, method="HEAD"),
        )
        public_post = _invoke(middleware, _scope(PUBLIC_STATUS_PATH, method="POST"))
        public_prefix_smuggle = _invoke(
            middleware,
            _scope(f"{PUBLIC_STATUS_PATH}/extra"),
        )

        self.assertEqual(_status(public), 200)
        self.assertEqual(_status(public_head), 200)
        self.assertEqual(_body(public_head), b"")
        self.assertEqual(_status(health), 200)
        self.assertEqual(_status(health_head), 200)
        self.assertEqual(_body(health_head), b"")
        self.assertEqual(_status(public_post), 503)
        self.assertEqual(_status(public_prefix_smuggle), 503)
        self.assertEqual(len(app.calls), 0)
        self.assertEqual(
            _body(public),
            b'{"status":"ok","service":"luma-experience-gateway",'
            b'"access_boundary":"operator_api_v1","public_surface":"minimal"}',
        )
        self.assertEqual(public_status_payload()["public_surface"], "minimal")
        health_payload = json.loads(_body(health))
        self.assertEqual(health_payload["status"], "ok")
        self.assertEqual(health_payload["service"], "luma-experience-gateway")
        self.assertEqual(health_payload["access_boundary"], "operator_api_v1")
        self.assertEqual(health_payload["public_surface"], "minimal")
        self.assertRegex(
            health_payload["generated_utc"],
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
        )
        self.assertEqual(set(public_health_payload()), set(health_payload))

    def test_preflight_passes_but_does_not_bypass_actual_request_auth(self) -> None:
        app = _ProbeApp()
        middleware = OperatorApiAccessMiddleware(app, token_provider=lambda: ())
        preflight = _invoke(
            middleware,
            _scope("/api/kraken/balance", method="OPTIONS"),
        )
        actual = _invoke(middleware, _scope("/api/kraken/balance"))
        self.assertEqual(_status(preflight), 204)
        self.assertEqual(_status(actual), 503)
        self.assertEqual(len(app.calls), 1)

    def test_live_websocket_is_operator_only(self) -> None:
        app = _ProbeApp()
        middleware = OperatorApiAccessMiddleware(
            app,
            token_provider=lambda: ("socket-secret-0000000000000000000",),
        )
        blocked = _invoke(
            middleware,
            _scope("/ws/live", scope_type="websocket"),
        )
        allowed = _invoke(
            middleware,
            _scope(
                "/ws/live",
                scope_type="websocket",
                headers=[
                    (b"authorization", b"Bearer socket-secret-0000000000000000000")
                ],
            ),
        )
        self.assertEqual(blocked, [{"type": "websocket.close", "code": 4401}])
        self.assertEqual(allowed, [{"type": "websocket.accept"}])
        self.assertEqual(len(app.calls), 1)

    def test_query_string_and_legacy_header_do_not_carry_operator_secrets(self) -> None:
        secret = "query-secret-00000000000000000000"
        app = _ProbeApp()
        middleware = OperatorApiAccessMiddleware(
            app,
            token_provider=lambda: (secret,),
        )
        query_scope = _scope("/api/kraken/balance")
        query_scope["query_string"] = f"token={secret}".encode("ascii")
        query_attempt = _invoke(middleware, query_scope)
        legacy_header_attempt = _invoke(
            middleware,
            _scope(
                "/api/kraken/balance",
                headers=[(b"x-luma-token", secret.encode("ascii"))],
            ),
        )
        unconfigured_websocket = _invoke(
            OperatorApiAccessMiddleware(app, token_provider=lambda: ()),
            _scope("/ws/live", scope_type="websocket"),
        )

        self.assertEqual(_status(query_attempt), 401)
        self.assertEqual(_status(legacy_header_attempt), 401)
        self.assertEqual(
            unconfigured_websocket,
            [{"type": "websocket.close", "code": 1013}],
        )
        self.assertEqual(app.calls, [])

    def test_install_registers_one_outer_middleware(self) -> None:
        class FakeFastAPI:
            def __init__(self) -> None:
                self.middleware: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

            def add_middleware(self, *args: Any, **kwargs: Any) -> None:
                self.middleware.append((args, kwargs))

        app = FakeFastAPI()
        install_operator_api_access(app)
        install_operator_api_access(app)
        self.assertEqual(len(app.middleware), 1)
        self.assertIs(app.middleware[0][0][0], OperatorApiAccessMiddleware)


@unittest.skipIf(httpx is None, "httpx is required for the real gateway probe")
class RealGatewayAccessIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_gateway_enforces_outer_boundary_before_legacy_routes(self) -> None:
        import luma_experience_gateway as gateway

        assert httpx is not None
        transport = httpx.ASGITransport(app=gateway.app)
        with mock.patch.dict(
            os.environ,
            {
                "LUMA_OPERATOR_API_TOKEN": "",
                "LUMA_OPERATOR_API_TOKENS": "",
            },
            clear=False,
        ):
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://gateway-test",
            ) as client:
                public = await client.get(PUBLIC_STATUS_PATH)
                health = await client.get(PUBLIC_HEALTH_PATH)
                operator_health = await client.get("/api/operator/health")
                balance = await client.get("/api/kraken/balance")
                approval_queue = await client.get("/api/master/approval-queue")
                metrics = await client.get("/metrics")
                openapi = await client.get("/openapi.json")
                docs = await client.get("/docs")
                redoc = await client.get("/redoc")

        self.assertEqual(public.status_code, 200)
        self.assertEqual(public.json(), public_status_payload())
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["public_surface"], "minimal")
        self.assertNotIn("services", health.json())
        self.assertNotIn("supervisor_pid", health.json())
        self.assertEqual(operator_health.status_code, 503)
        self.assertEqual(balance.status_code, 503)
        self.assertEqual(approval_queue.status_code, 503)
        self.assertEqual(metrics.status_code, 503)
        self.assertEqual(openapi.status_code, 503)
        self.assertEqual(docs.status_code, 503)
        self.assertEqual(redoc.status_code, 503)

    async def test_real_gateway_accepts_valid_runtime_bearer(self) -> None:
        import luma_experience_gateway as gateway

        assert httpx is not None
        secret = "integration-secret-00000000000000000"
        transport = httpx.ASGITransport(app=gateway.app)
        with mock.patch.dict(
            os.environ,
            {
                "LUMA_OPERATOR_API_TOKEN": secret,
                "LUMA_OPERATOR_API_TOKENS": "",
            },
            clear=False,
        ):
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://gateway-test",
            ) as client:
                missing = await client.get("/api/not-a-route")
                valid = await client.get(
                    "/api/not-a-route",
                    headers={"Authorization": f"Bearer {secret}"},
                )
                detailed_health = await client.get(
                    "/api/operator/health",
                    headers={"Authorization": f"Bearer {secret}"},
                )

        self.assertEqual(missing.status_code, 401)
        self.assertEqual(valid.status_code, 404)
        self.assertEqual(detailed_health.status_code, 200)
        self.assertIn("artifacts", detailed_health.json())


if __name__ == "__main__":
    unittest.main()
