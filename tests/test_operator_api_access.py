from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import tempfile
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
            "/out",
            "/out/execution/live_executor_heartbeat.json",
            "/proof/execution/live_executor_heartbeat.json",
            "/INSTITUTIONAL_STACK_V2/out/execution/live_executor_heartbeat.json",
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

    def test_proxy_root_path_matching_requires_exact_segment_boundary(self) -> None:
        cases = (
            ("/gateway", "/gateway/api/private", 503),
            ("/gateway", "/api/private", 503),
            ("/gate", "/gateway/api/private", 204),
            ("/gateway", "/gateway/health", 200),
            ("/gate", "/gateway/health", 204),
            ("/gateway", "/gateway/api/public/status", 200),
            ("/gate", "/gateway/api/public/status", 204),
        )
        for root_path, path, expected in cases:
            with self.subTest(root_path=root_path, path=path):
                app = _ProbeApp()
                middleware = OperatorApiAccessMiddleware(app, token_provider=lambda: ())
                scope = {**_scope(path), "root_path": root_path}
                self.assertEqual(_status(_invoke(middleware, scope)), expected)
                self.assertEqual(scope["path"], path)
                self.assertEqual(len(app.calls), 1 if expected == 204 else 0)

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

    def test_non_ascii_credentials_fail_closed_for_http_and_websocket(self) -> None:
        app = _ProbeApp()
        middleware = OperatorApiAccessMiddleware(
            app,
            token_provider=lambda: ("synthetic-review-token-1234567890123456",),
        )
        for scope_type, path in (
            ("http", "/api/operator/health"), ("websocket", "/ws/live")
        ):
            for header_name, prefix in (
                (b"authorization", b"Bearer "), (b"x-luma-operator-token", b"")
            ):
                for token in (b"\xff", "synthetic-\u2603-token".encode("utf-8")):
                    with self.subTest(scope_type=scope_type, header=header_name, token=token):
                        messages = _invoke(
                            middleware,
                            _scope(
                                path,
                                scope_type=scope_type,
                                headers=[(header_name, prefix + token)],
                            ),
                        )
                        if scope_type == "http":
                            self.assertEqual(_status(messages), 401)
                        else:
                            self.assertEqual(
                                messages, [{"type": "websocket.close", "code": 4401}]
                            )
        self.assertEqual(app.calls, [])

    def test_unrepresentable_configured_token_cannot_break_valid_token_access(self) -> None:
        secret = "synthetic-review-token-1234567890123456"
        app = _ProbeApp()
        middleware = OperatorApiAccessMiddleware(
            app,
            token_provider=lambda: ("\u2603" * 32, secret),
        )
        for scope_type, path in (
            ("http", "/api/operator/health"), ("websocket", "/ws/live")
        ):
            for token in ("synthetic-invalid", secret):
                with self.subTest(scope_type=scope_type, valid=token == secret):
                    messages = _invoke(
                        middleware,
                        _scope(
                            path,
                            scope_type=scope_type,
                            headers=[
                                (b"authorization", f"Bearer {token}".encode("ascii"))
                            ],
                        ),
                    )
                    if scope_type == "http":
                        self.assertEqual(_status(messages), 204 if token == secret else 401)
                    else:
                        self.assertEqual(
                            messages,
                            [{"type": "websocket.accept"}]
                            if token == secret
                            else [{"type": "websocket.close", "code": 4401}],
                        )
        self.assertEqual(len(app.calls), 2)

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

        for path in ("/ws", "/ws/live", "/ws/future-feed"):
            with self.subTest(path=path, credential="missing"):
                blocked = _invoke(
                    middleware,
                    _scope(path, scope_type="websocket"),
                )
                self.assertEqual(
                    blocked,
                    [{"type": "websocket.close", "code": 4401}],
                )
            with self.subTest(path=path, credential="valid"):
                allowed = _invoke(
                    middleware,
                    _scope(
                        path,
                        scope_type="websocket",
                        headers=[
                            (
                                b"authorization",
                                b"Bearer socket-secret-0000000000000000000",
                            )
                        ],
                    ),
                )
                self.assertEqual(allowed, [{"type": "websocket.accept"}])

        self.assertEqual(len(app.calls), 3)

    def test_websocket_root_matching_does_not_overblock_nearby_paths(self) -> None:
        app = _ProbeApp()
        middleware = OperatorApiAccessMiddleware(app, token_provider=lambda: ())

        for path in ("/wss", "/ws-live", "/websocket"):
            with self.subTest(path=path):
                allowed = _invoke(
                    middleware,
                    _scope(path, scope_type="websocket"),
                )
                self.assertEqual(allowed, [{"type": "websocket.accept"}])

        self.assertEqual(len(app.calls), 3)

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


@unittest.skipIf(httpx is None, "httpx is required for the static-output probe")
class MountedOperatorAccessIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_mounted_private_http_routes_and_outputs_keep_auth_boundary(self) -> None:
        from starlette.applications import Starlette
        from starlette.responses import Response
        from starlette.routing import Mount, Route
        from starlette.staticfiles import StaticFiles

        token = "synthetic-mounted-operator-token-0000"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "fixture.txt").write_text("synthetic private output", encoding="utf-8")
            for tokens in ((), (token,)):
                for nested in (False, True):
                    calls: list[str] = []

                    async def private(request):
                        calls.append(request.url.path)
                        return Response("synthetic private API")

                    inner = Starlette(routes=[
                        Route("/api/private", private),
                        Route("/docs", private),
                        Mount("/out", app=StaticFiles(directory=str(output))),
                    ])
                    inner.add_middleware(
                        OperatorApiAccessMiddleware,
                        token_provider=lambda tokens=tokens: tokens,
                    )
                    outer = Starlette(routes=[Mount("/gateway", app=inner)])
                    if nested:
                        outer = Starlette(routes=[Mount("/parent", app=outer)])
                    prefix = "/parent/gateway" if nested else "/gateway"
                    async with httpx.AsyncClient(
                        transport=httpx.ASGITransport(app=outer), base_url="http://test"
                    ) as client:
                        for route in ("/api/private", "/docs", "/out/fixture.txt"):
                            with self.subTest(route=route, configured=bool(tokens), nested=nested):
                                missing = await client.get(prefix + route)
                                invalid = await client.get(
                                    prefix + route, headers={"Authorization": "Bearer invalid"}
                                )
                                self.assertEqual(missing.status_code, 401 if tokens else 503)
                                self.assertEqual(invalid.status_code, 401 if tokens else 503)
                                self.assertNotIn("synthetic private", missing.text)
                        self.assertEqual(calls, [])
                        for route in (PUBLIC_HEALTH_PATH, PUBLIC_STATUS_PATH):
                            public = await client.get(prefix + route)
                            public_head = await client.head(prefix + route)
                            self.assertEqual(public.status_code, 200)
                            self.assertEqual(public.json()["public_surface"], "minimal")
                            self.assertEqual(public_head.status_code, 200)
                            self.assertEqual(public_head.content, b"")
                        if tokens:
                            for route in ("/api/private", "/docs", "/out/fixture.txt"):
                                allowed = await client.get(
                                    prefix + route,
                                    headers={"Authorization": f"Bearer {token}"},
                                )
                                self.assertEqual(allowed.status_code, 200)
                                self.assertIn("synthetic private", allowed.text)
                            self.assertEqual(len(calls), 2)

    async def test_mounted_websocket_cannot_reach_handler_without_auth(self) -> None:
        from starlette.applications import Starlette
        from starlette.routing import Mount, WebSocketRoute

        token = "synthetic-mounted-operator-token-0000"
        for tokens in ((), (token,)):
            calls: list[bool] = []

            async def private_socket(websocket):
                calls.append(True)
                await websocket.accept()
                await websocket.close()

            inner = Starlette(routes=[WebSocketRoute("/ws/live", private_socket)])
            inner.add_middleware(
                OperatorApiAccessMiddleware,
                token_provider=lambda tokens=tokens: tokens,
            )
            outer = Starlette(routes=[Mount("/gateway", app=inner)])

            async def invoke(headers):
                messages = []
                scope = {
                    **_scope("/gateway/ws/live", scope_type="websocket", headers=headers),
                    "root_path": "", "scheme": "ws", "query_string": b"",
                    "subprotocols": [], "client": ("test", 1234), "server": ("test", 80),
                    "asgi": {"version": "3.0", "spec_version": "2.3"},
                }

                async def receive():
                    return {"type": "websocket.connect"}

                async def send(message):
                    messages.append(message)

                await outer(scope, receive, send)
                return messages

            for headers in ([], [(b"authorization", b"Bearer invalid")]):
                self.assertEqual(
                    await invoke(headers),
                    [{"type": "websocket.close", "code": 4401 if tokens else 1013}],
                )
            self.assertEqual(calls, [])
            if tokens:
                allowed = await invoke([(b"authorization", f"Bearer {token}".encode("ascii"))])
                self.assertEqual(allowed[0]["type"], "websocket.accept")
                self.assertEqual(calls, [True])


@unittest.skipIf(httpx is None, "httpx is required for the static-output probe")
class StaticOutputAccessIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_output_mounts_require_operator_access_before_serving_bytes(self) -> None:
        from starlette.applications import Starlette
        from starlette.routing import Mount
        from starlette.staticfiles import StaticFiles

        assert httpx is not None
        marker = b'{"fixture":"synthetic-private-output"}'
        token = "synthetic-output-operator-token-0000"
        prefixes = ("/out", "/proof", "/INSTITUTIONAL_STACK_V2/out")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output / "execution").mkdir()
            (output / "execution" / "fixture.json").write_bytes(marker)
            inner = Starlette(
                routes=[
                    Mount(prefix, app=StaticFiles(directory=str(output)))
                    for prefix in prefixes
                ]
            )
            for tokens, denied_status in (((), 503), ((token,), 401)):
                app = OperatorApiAccessMiddleware(inner, token_provider=lambda: tokens)
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://synthetic-output-test",
                ) as client:
                    for prefix in prefixes:
                        path = f"{prefix}/execution/fixture.json"
                        with self.subTest(prefix=prefix, tokens_configured=bool(tokens)):
                            missing = await client.get(path)
                            invalid = await client.get(
                                path, headers={"Authorization": "Bearer invalid"}
                            )
                            head = await client.head(path)
                            self.assertEqual(missing.status_code, denied_status)
                            self.assertEqual(invalid.status_code, denied_status)
                            self.assertEqual(head.status_code, denied_status)
                            self.assertNotIn(marker, missing.content)
                            self.assertNotIn(marker, invalid.content)
                            if tokens:
                                allowed = await client.get(
                                    path, headers={"Authorization": f"Bearer {token}"}
                                )
                                self.assertEqual(allowed.status_code, 200)
                                self.assertEqual(allowed.content, marker)
                    encoded = await client.get("/out%2Fexecution%2Ffixture.json")
                    self.assertEqual(encoded.status_code, denied_status)
                    for path in (PUBLIC_HEALTH_PATH, PUBLIC_STATUS_PATH):
                        public = await client.get(path)
                        self.assertEqual(public.status_code, 200)
                        self.assertEqual(public.json()["public_surface"], "minimal")


class DeploymentOutputBoundaryTests(unittest.TestCase):
    def test_proxy_sources_cannot_serve_workspace_output_from_public_alias(self) -> None:
        for relative in (
            "deploy/VPS_DEPLOY.sh",
            "code/deploy/nginx/lumatrader.conf",
        ):
            with self.subTest(path=relative):
                source = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIsNone(
                    re.search(r"\b(?:alias|root)\s+/opt/lumencore/out(?:/|;)", source)
                )
                for location in (r"= /proof", r"\^~ /proof/"):
                    block = re.search(
                        rf"location {location}\s*\{{([^}}]*)\}}", source
                    )
                    self.assertIsNotNone(block)
                    assert block is not None
                    self.assertRegex(block.group(1), r"\breturn\s+404\s*;")


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
