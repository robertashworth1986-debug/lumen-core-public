from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "repair_public_edge.py"
SPEC = importlib.util.spec_from_file_location("repair_public_edge", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

BASE_CONFIG = """upstream luma_gateway {
    server 127.0.0.1:8787;
}

server {
    listen 80;
    server_name example.invalid;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name example.invalid;

    location = /health {
        proxy_pass http://luma_gateway/health;
    }

    location /api/ {
        proxy_pass http://luma_gateway;
    }
}
"""


def _assert_repair_error(callback: object) -> None:
    try:
        callback()  # type: ignore[operator]
    except MODULE.PublicEdgeRepairError:
        return
    raise AssertionError("expected PublicEdgeRepairError")


def test_inserts_public_map_and_server_guard() -> None:
    result = MODULE.repair_config(BASE_CONFIG)
    assert result.changed is True
    assert MODULE.MAP_BLOCK in result.repaired
    assert MODULE.GUARD_BLOCK in result.repaired
    assert result.repaired.index(MODULE.MAP_BEGIN) < result.repaired.index(
        "server {\n    listen 443 ssl;"
    )
    assert "https://$host$request_uri" not in result.repaired
    assert "https://$server_name$request_uri" in result.repaired
    MODULE.validate_repaired_config(result.repaired)


def test_repair_is_idempotent() -> None:
    first = MODULE.repair_config(BASE_CONFIG)
    second = MODULE.repair_config(first.repaired)
    assert second.changed is False
    assert second.repaired == first.repaired


def test_retires_private_subdomain_redirects() -> None:
    private_redirect = (
        BASE_CONFIG
        + """
server {
    listen 443 ssl;
    server_name research.example.invalid;
    location / {
        return 302 https://example.invalid/quant_lab.html;
    }
}
"""
    )
    result = MODULE.repair_config(private_redirect)
    assert "/quant_lab.html" not in result.repaired
    assert "return 404;" in result.repaired
    MODULE.validate_repaired_config(result.repaired)


def test_refuses_ambiguous_https_servers_and_variable_collisions() -> None:
    duplicate = BASE_CONFIG + BASE_CONFIG
    _assert_repair_error(lambda: MODULE.repair_config(duplicate))
    collision = (
        "$lumencore_public_route_denied\n"
        + BASE_CONFIG
    )
    _assert_repair_error(lambda: MODULE.repair_config(collision))


def test_canonical_nginx_config_satisfies_public_edge_contract() -> None:
    canonical = (
        ROOT / "code" / "deploy" / "nginx" / "lumatrader.conf"
    ).read_text(encoding="utf-8")
    MODULE.validate_repaired_config(canonical)
    assert "autoindex on;" not in canonical
    assert "location = /api/master/booth-brief" in canonical
    assert "location /api/ {\n        return 404;" in canonical
    assert "location /proof/ {\n        return 404;" in canonical
    assert "location /out/ {\n        return 404;" in canonical
    assert "location / {\n        return 404;" in canonical
    assert "location = /dashboard {\n        return 404;" in canonical
    assert "location = /dashboard/ {\n        return 404;" in canonical
    assert "location = /proof_to_pilot.html" in canonical
    assert "https://$host$request_uri" not in canonical
    assert "https://$server_name$request_uri" in canonical
    assert "/investor_command_room.html" not in canonical
    assert "/quant_lab.html" not in canonical


def test_public_map_defaults_to_deny_with_an_exact_read_only_manifest() -> None:
    assert "    default 1;" in MODULE.MAP_BLOCK
    allow_patterns = re.findall(
        r'^[ \t]+"([^"]+)"[ \t]+0;',
        MODULE.MAP_BLOCK,
        flags=re.MULTILINE,
    )
    assert allow_patterns

    def allowed(method: str, path: str) -> bool:
        request = f"{method}:{path}"
        return any(
            re.fullmatch(
                pattern[1:] if pattern.startswith("~") else pattern,
                request,
            )
            for pattern in allow_patterns
        )

    for method in ("GET", "HEAD"):
        for path in (
            "/",
            "/operator_home.html",
            "/assets/lumencore.css",
            "/assets/luma_command_fabric.css",
            "/proof_to_pilot.html",
            "/health",
            "/api/master/booth-brief",
            "/evidence",
            "/evidence/",
            "/evidence/index_bounded.html",
        ):
            assert allowed(method, path), (method, path)

    for method, path in (
        ("POST", "/api/master/booth-brief"),
        ("GET", "/dashboard"),
        ("GET", "/dashboard/"),
        ("GET", "/quant_lab.html"),
        ("GET", "/evidence/index.html"),
        ("GET", "/evidence/private.json"),
        ("GET", "/data/site_health.json"),
        ("GET", "/unknown.html"),
    ):
        assert not allowed(method, path), (method, path)


def test_cli_is_inspect_only_until_apply_and_creates_backup() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        config = Path(temporary) / "lumatrader.conf"
        config.write_text(BASE_CONFIG, encoding="utf-8")

        assert MODULE.main(["--config", str(config)]) == 1
        assert config.read_text(encoding="utf-8") == BASE_CONFIG

        assert MODULE.main(["--config", str(config), "--apply"]) == 0
        MODULE.validate_repaired_config(config.read_text(encoding="utf-8"))
        backups = list(config.parent.glob("lumatrader.conf.pre-public-edge-repair.*"))
        assert len(backups) == 1
        assert backups[0].read_text(encoding="utf-8") == BASE_CONFIG


def test_vps_wrapper_is_inspect_only_with_rollback_and_blocked_route_probes() -> None:
    wrapper = (
        ROOT / "code" / "ops" / "REPAIR_PUBLIC_EDGE_ON_VPS.sh"
    ).read_text(encoding="utf-8")
    assert "Inspect-only" in wrapper
    assert "--apply" in wrapper
    assert "nginx -t" in wrapper
    assert "systemctl reload nginx" in wrapper
    assert "deploy-rollback" in wrapper
    assert "/api/master/approval-queue" in wrapper
    assert "/proof/" in wrapper
    assert "/out/" in wrapper
    assert "/dashboard" in wrapper
    assert "/quant_lab.html" in wrapper
    assert "/evidence/index.html" in wrapper
    assert "edge_allows_backend_route GET /evidence/" in wrapper
