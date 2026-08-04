from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NGINX_TEMPLATE = ROOT / "code" / "deploy" / "nginx" / "lumatrader.conf"
VPS_DEPLOY = ROOT / "deploy" / "VPS_DEPLOY.sh"
DASHBOARD_PORTAL = ROOT / "dashboard" / "dashboard_portal.html"
DASHBOARD_INDEX = ROOT / "dashboard" / "index.html"
CANONICAL_PUBLIC_WEB_ROOT = "/opt/lumencore/dashboard"


def test_nginx_surfaces_never_publish_a_browsable_output_directory() -> None:
    for path in (NGINX_TEMPLATE, VPS_DEPLOY):
        text = path.read_text(encoding="utf-8")
        assert "autoindex on" not in text, path
        assert "alias /opt/lumencore/out/" not in text, path
        assert "location = /proof/" in text, path
        assert "return 302 /proof_to_pilot.html;" in text, path
        assert "location /proof/" in text, path
        assert "return 404;" in text, path
        assert "location ^~ /out/grants/" in text, path


def test_nginx_root_uses_existing_current_dashboard_entrypoints() -> None:
    text = NGINX_TEMPLATE.read_text(encoding="utf-8")

    assert DASHBOARD_PORTAL.is_file()
    assert DASHBOARD_INDEX.is_file()
    assert "operator_home.html" not in text
    assert "try_files /dashboard_portal.html /index.html =404;" in text
    assert "index dashboard_portal.html index.html mission_control.html;" in text


def test_all_nginx_templates_serve_reviewer_evidence_as_static_files() -> None:
    for path in (NGINX_TEMPLATE, VPS_DEPLOY):
        text = path.read_text(encoding="utf-8")
        start = text.index("location /evidence/ {")
        end = text.index("}", start)
        block = text[start:end]

        assert "alias /opt/lumencore/dashboard/evidence/;" in block, path
        assert "try_files $uri $uri/ =404;" in block, path
        assert "proxy_pass" not in block, path


def test_all_deploy_paths_share_one_canonical_public_web_root() -> None:
    deployment_paths = (
        ROOT / "deploy" / "VPS_DEPLOY.sh",
        ROOT / "code" / "deploy" / "deploy_vps.sh",
        ROOT / ".github" / "workflows" / "deploy.yml",
    )
    for path in deployment_paths:
        text = path.read_text(encoding="utf-8")
        assert CANONICAL_PUBLIC_WEB_ROOT in text, path

    guarded_deploy = deployment_paths[1].read_text(encoding="utf-8")
    assert "CHECK_PUBLIC_REVIEWER_RELEASE.py" in guarded_deploy
    assert "/proof_to_pilot.html" in guarded_deploy
    assert "/data/quant_hub_reviewer_context.json" in guarded_deploy
