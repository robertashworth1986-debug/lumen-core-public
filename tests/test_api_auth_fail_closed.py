from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
import httpx
from fastapi import FastAPI, HTTPException


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import grants_api  # noqa: E402
import opportunities_api  # noqa: E402


AUTH_CASES = (
    (
        opportunities_api,
        (
            "LUMA_OPPORTUNITY_API_TOKEN",
            "LUMA_OPP_API_TOKEN",
            "LUMA_API_TOKEN",
        ),
        "/api/opportunities/queue",
    ),
    (
        grants_api,
        ("LUMA_GRANTS_API_TOKEN", "LUMA_API_TOKEN"),
        "/api/grants",
    ),
)
ALL_AUTH_ENV_NAMES = {
    name for _, env_names, _ in AUTH_CASES for name in env_names
}


def _get(app: FastAPI, route: str, **kwargs) -> httpx.Response:
    async def request() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            return await client.get(route, **kwargs)

    return asyncio.run(request())


def _clear_auth_config(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ALL_AUTH_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def _configure_auth(
    monkeypatch: pytest.MonkeyPatch,
    env_names: tuple[str, ...],
    token: str,
) -> None:
    _clear_auth_config(monkeypatch)
    monkeypatch.setenv(env_names[0], token)


@pytest.mark.parametrize(("module", "env_names", "route"), AUTH_CASES)
def test_helper_denies_when_api_token_config_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    module,
    env_names: tuple[str, ...],
    route: str,
) -> None:
    del env_names, route
    _clear_auth_config(monkeypatch)

    with pytest.raises(HTTPException) as exc_info:
        module._require_api_token(None, None)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "api authentication is not configured"


@pytest.mark.parametrize(("module", "env_names", "route"), AUTH_CASES)
def test_protected_router_denies_when_api_token_config_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    module,
    env_names: tuple[str, ...],
    route: str,
) -> None:
    del env_names
    _clear_auth_config(monkeypatch)
    app = FastAPI()
    app.include_router(module.router)

    response = _get(app, route)

    assert response.status_code == 503
    assert response.json() == {"detail": "api authentication is not configured"}


@pytest.mark.parametrize(("module", "env_names", "route"), AUTH_CASES)
def test_wrong_api_token_is_denied(
    monkeypatch: pytest.MonkeyPatch,
    module,
    env_names: tuple[str, ...],
    route: str,
) -> None:
    del route
    _configure_auth(monkeypatch, env_names, "correct-test-token")

    with pytest.raises(HTTPException) as exc_info:
        module._require_api_token("wrong-test-token", None)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "invalid api token"


@pytest.mark.parametrize(("module", "env_names", "route"), AUTH_CASES)
def test_valid_x_luma_token_header_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
    module,
    env_names: tuple[str, ...],
    route: str,
) -> None:
    del route
    token = "valid-header-test-token"
    _configure_auth(monkeypatch, env_names, token)

    assert module._require_api_token(token, None) is None


@pytest.mark.parametrize(("module", "env_names", "route"), AUTH_CASES)
def test_valid_authorization_bearer_header_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
    module,
    env_names: tuple[str, ...],
    route: str,
) -> None:
    del route
    token = "valid-bearer-test-token"
    _configure_auth(monkeypatch, env_names, token)

    assert module._require_api_token(None, f"Bearer {token}") is None


@pytest.mark.parametrize(("module", "env_names", "route"), AUTH_CASES)
def test_query_string_token_is_not_an_accepted_auth_mechanism(
    monkeypatch: pytest.MonkeyPatch,
    module,
    env_names: tuple[str, ...],
    route: str,
) -> None:
    token = "query-string-test-token"
    _configure_auth(monkeypatch, env_names, token)
    app = FastAPI()
    app.include_router(module.router)

    response = _get(app, route, params={"token": token})

    assert response.status_code == 401
    assert response.json() == {"detail": "missing api token"}


@pytest.mark.parametrize(("module", "env_names", "route"), AUTH_CASES)
def test_router_keeps_app_health_and_docs_public(
    monkeypatch: pytest.MonkeyPatch,
    module,
    env_names: tuple[str, ...],
    route: str,
) -> None:
    del env_names, route
    _clear_auth_config(monkeypatch)
    app = FastAPI()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(module.router)
    assert _get(app, "/health").status_code == 200
    assert _get(app, "/docs").status_code == 200
    assert _get(app, "/openapi.json").status_code == 200
