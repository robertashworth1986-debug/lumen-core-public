from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"


def _load_facade() -> Any:
    legacy = types.ModuleType("luma_experience_gateway_legacy")

    async def legacy_app(
        scope: dict[str, Any],
        receive: Any,
        send: Any,
    ) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            }
        )
        await send({"type": "http.response.body", "body": b"legacy"})

    legacy.app = legacy_app
    legacy.health = lambda: {
        "generated_utc": "2026-07-27T23:00:00Z",
        "status": "ok",
        "all_healthy": True,
        "supervisor_pid": 12345,
        "services": {"private": {"running": True}},
    }
    legacy._kraken_add_order = lambda payload: {"result": dict(payload)}

    execution = types.ModuleType("execution")
    order_gate = types.ModuleType("execution.order_safety_gate")

    class Decision:
        allowed = False

        @staticmethod
        def as_dict() -> dict[str, Any]:
            return {"allowed": False}

    order_gate.ADD_ORDER_PATH = "/synthetic"
    order_gate.ORDER_POLICY = {"mode": "blocked"}
    order_gate.evaluate_order_request = lambda path, payload: Decision()

    saved = {
        name: sys.modules.get(name)
        for name in (
            "luma_experience_gateway_legacy",
            "execution",
            "execution.order_safety_gate",
        )
    }
    sys.modules["luma_experience_gateway_legacy"] = legacy
    sys.modules["execution"] = execution
    sys.modules["execution.order_safety_gate"] = order_gate
    try:
        path = CODE / "luma_experience_gateway.py"
        spec = importlib.util.spec_from_file_location(
            "gateway_allowlist_test",
            path,
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for name, value in saved.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


async def _invoke(
    application: Any,
    *,
    scope_type: str = "http",
    method: str = "GET",
    path: str = "/",
) -> list[dict[str, Any]]:
    messages = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    await application(
        {"type": scope_type, "method": method, "path": path},
        receive,
        send,
    )
    return messages


def test_public_request_allowlist_is_exact_and_read_only() -> None:
    module = _load_facade()
    assert module.PUBLIC_GATEWAY_PATHS == {
        "/health",
        "/api/master/booth-brief",
    }
    for path in module.PUBLIC_GATEWAY_PATHS:
        assert module.public_gateway_request_allowed("GET", path) is True
        assert module.public_gateway_request_allowed("HEAD", path) is True
        assert module.public_gateway_request_allowed("POST", path) is False
    assert module.public_gateway_request_allowed("GET", "/health/") is False
    assert module.public_gateway_request_allowed("GET", "/api/") is False


def test_public_boundary_denies_mutations_unknown_paths_and_websockets() -> None:
    module = _load_facade()
    application = module.PublicGatewayAllowlistApp(
        module.legacy_app,
        operator_routes_enabled=False,
    )
    for method, path in (
        ("POST", "/api/master/booth-brief"),
        ("GET", "/api/master/approval-queue"),
        ("GET", "/out/private.json"),
        ("GET", "/"),
    ):
        messages = asyncio.run(
            _invoke(application, method=method, path=path)
        )
        assert messages[0]["status"] == 404
        assert messages[1]["body"] == b'{"detail":"not found"}'

    messages = asyncio.run(
        _invoke(application, scope_type="websocket", path="/ws/live")
    )
    assert messages == [{"type": "websocket.close", "code": 1008}]


def test_allowed_routes_reach_inner_app_and_operator_mode_is_explicit() -> None:
    module = _load_facade()
    public_app = module.PublicGatewayAllowlistApp(
        module.legacy_app,
        operator_routes_enabled=False,
    )
    for path in sorted(module.PUBLIC_GATEWAY_PATHS):
        messages = asyncio.run(_invoke(public_app, path=path))
        assert messages[0]["status"] == 200
        assert messages[1]["body"] == b"legacy"

    operator_app = module.PublicGatewayAllowlistApp(
        module.legacy_app,
        operator_routes_enabled=True,
    )
    messages = asyncio.run(
        _invoke(operator_app, method="POST", path="/api/internal")
    )
    assert messages[0]["status"] == 200


def test_public_health_projection_omits_runtime_topology() -> None:
    module = _load_facade()
    payload = module.public_health_projection(
        {
            "generated_utc": "2026-07-27T23:00:00+00:00",
            "status": "ok",
            "all_healthy": True,
            "supervisor_pid": 12345,
            "services": {"private": {"running": True}},
            "artifacts": {"private": {"age_sec": 1}},
        }
    )
    assert set(payload) == {
        "schema",
        "generated_utc",
        "status",
        "all_healthy",
        "claim_boundary",
    }
    assert payload["schema"] == "lumencore.public_gateway_health.v1"
    assert payload["generated_utc"] == "2026-07-27T23:00:00Z"
    assert payload["status"] == "ok"
    assert payload["all_healthy"] is True

    application = module.PublicGatewayAllowlistApp(
        module.legacy_app,
        operator_routes_enabled=False,
        health_provider=module._legacy.health,
    )
    messages = asyncio.run(_invoke(application, path="/health"))
    assert messages[0]["status"] == 200
    body = messages[1]["body"].decode("utf-8")
    assert "supervisor_pid" not in body
    assert "services" not in body
    assert "artifacts" not in body
