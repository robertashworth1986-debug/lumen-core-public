from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LIVE_DOMAIN_SERVICE_CONTRACT.py"


def load_module():
    spec = importlib.util.spec_from_file_location("live_domain_service_contract", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def successful_observation(spec: dict) -> dict:
    status = spec["allowed_statuses"][0]
    json_body = dict(spec.get("expected_json") or {})
    if spec["kind"] == "json" and not json_body:
        json_body = {"status": "degraded"}
    return {
        "status": status,
        "content_type": spec.get("content_type_prefix") or "text/html",
        "location": spec.get("expected_location") or "",
        "body_bytes_observed": 12,
        "body_sha256": "a" * 64,
        "json_body": json_body,
        "json_error": "",
        "error": "",
    }


def test_contract_passes_only_when_every_required_endpoint_matches(monkeypatch) -> None:
    module = load_module()
    monkeypatch.setattr(module, "probe_endpoint", lambda spec, timeout: successful_observation(spec))

    payload = module.build_payload(domain="example.test", check_live=True)

    assert payload["summary"]["contract_pass"] is True
    assert payload["summary"]["passed_endpoint_count"] == 7
    assert payload["summary"]["failed_endpoint_ids"] == []
    assert payload["contract_sha256"] == module.canonical_sha256(payload)


def test_gateway_failure_blocks_contract_and_routes_to_vps_diagnostics(monkeypatch) -> None:
    module = load_module()

    def probe(spec: dict, timeout: int) -> dict:
        observation = successful_observation(spec)
        if spec["id"] == "gateway_health":
            observation.update(
                {
                    "status": 502,
                    "content_type": "text/html",
                    "json_body": {},
                    "error": "HTTP Error 502",
                }
            )
        return observation

    monkeypatch.setattr(module, "probe_endpoint", probe)
    payload = module.build_payload(domain="example.test", check_live=True)

    assert payload["summary"]["contract_pass"] is False
    assert payload["summary"]["failed_endpoint_ids"] == ["gateway_health"]
    assert "luma-gateway" in payload["summary"]["safe_next_action"]
    assert payload["summary"]["performance_claim_allowed"] is False


def test_redirect_and_json_content_contracts_are_exact() -> None:
    module = load_module()
    specs = {row["id"]: row for row in module.endpoint_specs("example.test")}

    redirect = successful_observation(specs["app_redirect"])
    redirect["location"] = "https://example.test/wrong.html"
    redirect_row = module.evaluate(specs["app_redirect"], redirect)
    assert redirect_row["passed"] is False
    assert redirect_row["failures"] == ["location"]

    health = successful_observation(specs["research_health"])
    health["content_type"] = "text/html"
    health_row = module.evaluate(specs["research_health"], health)
    assert health_row["passed"] is False
    assert health_row["failures"] == ["content_type"]


def test_nginx_template_exposes_bounded_subdomain_health_contracts() -> None:
    nginx = (ROOT / "code" / "deploy" / "nginx" / "lumatrader.conf").read_text(
        encoding="utf-8"
    )
    deploy = (ROOT / "code" / "deploy" / "deploy_vps.sh").read_text(encoding="utf-8")

    assert '"surface":"app","mode":"reviewer_safe_redirect"' in nginx
    assert '"surface":"research","mode":"reviewer_safe_redirect"' in nginx
    assert nginx.count("location = /health") == 3
    edge_health = nginx.split("location = /nginx-health", 1)[1].split("}", 1)[0]
    assert "default_type application/json;" in edge_health
    assert "add_header Content-Type" not in edge_health
    assert '"investor_command_room.html"' in deploy
