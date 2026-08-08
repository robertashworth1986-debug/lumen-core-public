"""Fail-closed access boundary for the Luma operator gateway.

The legacy gateway contains both reviewer-safe and operator-sensitive routes.
This middleware keeps that distinction explicit: one minimal status route is
public, while every other API route and live WebSocket requires a runtime
operator token.
"""

from __future__ import annotations

import hmac
import json
import os
import re
from collections.abc import Awaitable, Callable, Iterable, Mapping
from typing import Any


ASGIApp = Callable[
    [
        dict[str, Any],
        Callable[..., Awaitable[Any]],
        Callable[..., Awaitable[Any]],
    ],
    Awaitable[None],
]
TokenProvider = Callable[[], tuple[str, ...]]

OPERATOR_TOKEN_ENV_NAMES = (
    "LUMA_OPERATOR_API_TOKEN",
    "LUMA_OPERATOR_API_TOKENS",
)
PUBLIC_STATUS_PATH = "/api/public/status"
PUBLIC_API_READ_PATHS = frozenset({PUBLIC_STATUS_PATH})
PROTECTED_WEBSOCKET_PATHS = frozenset({"/ws", "/ws/live"})
MIN_OPERATOR_TOKEN_CHARS = 32
_TOKEN_SPLIT_RE = re.compile(r"[\r\n,]+")


def _split_tokens(raw: str | None) -> list[str]:
    if not raw:
        return []
    tokens = [token.strip() for token in _TOKEN_SPLIT_RE.split(raw)]
    return [token for token in tokens if len(token) >= MIN_OPERATOR_TOKEN_CHARS]


def expected_operator_tokens(
    environ: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Load deduplicated operator tokens without logging or persisting them."""

    source = os.environ if environ is None else environ
    tokens: list[str] = []
    seen: set[str] = set()
    for name in OPERATOR_TOKEN_ENV_NAMES:
        for token in _split_tokens(source.get(name)):
            if token not in seen:
                seen.add(token)
                tokens.append(token)
    return tuple(tokens)


def _headers(scope: Mapping[str, Any]) -> dict[str, list[str]]:
    parsed: dict[str, list[str]] = {}
    for raw_name, raw_value in scope.get("headers", []):
        name = bytes(raw_name).decode("latin-1").lower()
        value = bytes(raw_value).decode("latin-1").strip()
        parsed.setdefault(name, []).append(value)
    return parsed


def _bearer_token(value: str) -> str:
    parts = value.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return ""
    return parts[1].strip()


def presented_operator_token(scope: Mapping[str, Any]) -> str:
    """Return one unambiguous token from supported request headers."""

    headers = _headers(scope)
    candidates: list[str] = []
    for value in headers.get("authorization", []):
        token = _bearer_token(value)
        if token:
            candidates.append(token)
    for value in headers.get("x-luma-operator-token", []):
        token = value.strip()
        if token:
            candidates.append(token)

    unique: list[str] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique[0] if len(unique) == 1 else ""


def token_is_authorized(provided: str, expected: Iterable[str]) -> bool:
    if not provided:
        return False
    return any(hmac.compare_digest(provided, token) for token in expected)


def is_public_api_read(scope: Mapping[str, Any]) -> bool:
    method = str(scope.get("method", "")).upper()
    path = str(scope.get("path", ""))
    return method in {"GET", "HEAD"} and path in PUBLIC_API_READ_PATHS


def is_operator_http_path(path: str) -> bool:
    return path == "/api" or path.startswith("/api/")


async def _http_error(send: Callable[..., Awaitable[Any]], status: int) -> None:
    detail = (
        "operator API access unavailable"
        if status == 503
        else "operator API authentication required"
    )
    body = json.dumps({"detail": detail}, separators=(",", ":")).encode("utf-8")
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
        (b"cache-control", b"no-store"),
        (b"pragma", b"no-cache"),
    ]
    if status == 401:
        headers.append((b"www-authenticate", b"Bearer"))
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body, "more_body": False})


async def _public_status_response(
    send: Callable[..., Awaitable[Any]],
    *,
    head_only: bool,
) -> None:
    body = json.dumps(public_status_payload(), separators=(",", ":")).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
                (b"cache-control", b"no-store"),
            ],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": b"" if head_only else body,
            "more_body": False,
        }
    )


class OperatorApiAccessMiddleware:
    """Require runtime authentication for operator HTTP and WebSocket routes."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        token_provider: TokenProvider = expected_operator_tokens,
    ) -> None:
        self.app = app
        self.token_provider = token_provider

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[..., Awaitable[Any]],
        send: Callable[..., Awaitable[Any]],
    ) -> None:
        scope_type = str(scope.get("type", ""))
        path = str(scope.get("path", ""))

        if scope_type == "http":
            method = str(scope.get("method", "")).upper()
            if is_public_api_read(scope):
                await _public_status_response(send, head_only=method == "HEAD")
                return
            if not is_operator_http_path(path) or method == "OPTIONS":
                await self.app(scope, receive, send)
                return
        elif scope_type == "websocket":
            if path not in PROTECTED_WEBSOCKET_PATHS:
                await self.app(scope, receive, send)
                return
        else:
            await self.app(scope, receive, send)
            return

        expected = self.token_provider()
        if not expected:
            if scope_type == "http":
                await _http_error(send, 503)
            else:
                await send({"type": "websocket.close", "code": 1013})
            return

        provided = presented_operator_token(scope)
        if not token_is_authorized(provided, expected):
            if scope_type == "http":
                await _http_error(send, 401)
            else:
                await send({"type": "websocket.close", "code": 4401})
            return

        await self.app(scope, receive, send)


def public_status_payload() -> dict[str, str]:
    """Minimal public liveness payload; never reveal configuration state."""

    return {
        "status": "ok",
        "service": "luma-experience-gateway",
        "access_boundary": "operator_api_v1",
        "public_surface": "minimal",
    }


def install_operator_api_access(app: Any) -> None:
    """Install the access middleware ahead of legacy routes and static mounts."""

    marker = "_luma_operator_api_access_installed"
    if bool(getattr(app, marker, False)):
        return
    app.add_middleware(OperatorApiAccessMiddleware)
    setattr(app, marker, True)
