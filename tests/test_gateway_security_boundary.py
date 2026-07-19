from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import luma_experience_gateway as gateway  # noqa: E402


def test_default_cors_origins_are_explicit(monkeypatch) -> None:
    monkeypatch.delenv("LUMA_CORS_ORIGINS", raising=False)
    origins = gateway._cors_origins()
    assert "*" not in origins
    assert "https://lumen-core.ai" in origins
    assert "http://127.0.0.1:8787" in origins


def test_configured_wildcard_origin_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("LUMA_CORS_ORIGINS", "*, https://review.example.test/")
    assert gateway._cors_origins() == ["https://review.example.test"]


def test_operator_mutations_require_human_unlock() -> None:
    for path in [
        "/api/master/approval/decide",
        "/api/master/remediation/trigger",
        "/api/grants/nsf-seed-fund/approve",
        "/api/opportunities/email/dispatch/run",
        "/api/opportunities/linkedin/optimize",
        "/api/sells/lock_in",
        "/api/buys/autobuy/run",
        "/api/scanner/smart/config",
        "/api/kraken/sampler/fast",
        "/api/spike-hunter/scan",
        "/api/ml/trigger",
        "/api/nodered/ingest",
    ]:
        assert gateway._requires_human_unlock(path, "POST") is True
        assert gateway._requires_human_unlock(path, "GET") is False


def test_human_unlock_bearer_check_is_exact() -> None:
    assert gateway._human_unlock_bearer_authorized("token", "Bearer token") is True
    assert gateway._human_unlock_bearer_authorized("token", "bearer token") is True
    assert gateway._human_unlock_bearer_authorized("token", "Basic token") is False
    assert gateway._human_unlock_bearer_authorized("token", "Bearer wrong") is False
    assert gateway._human_unlock_bearer_authorized("", "Bearer token") is False


def test_private_grant_artifact_tree_is_shadowed_before_static_mount() -> None:
    route_paths = [getattr(route, "path", "") for route in gateway.app.routes]
    block_index = route_paths.index("/out/grants/{artifact_path:path}")
    static_index = route_paths.index("/out")

    assert "/out/grants" in route_paths
    assert block_index < static_index
    assert gateway.block_private_grant_artifacts("any/submission_packet.json").status_code == 404


def test_nginx_templates_block_private_grant_artifacts() -> None:
    templates = [
        ROOT / "code" / "deploy" / "nginx" / "lumatrader.conf",
        ROOT / "deploy" / "VPS_DEPLOY.sh",
    ]
    for template in templates:
        text = template.read_text(encoding="utf-8")
        assert "location ^~ /out/grants/" in text
        assert text.index("location ^~ /out/grants/") < text.index("location /out/")
