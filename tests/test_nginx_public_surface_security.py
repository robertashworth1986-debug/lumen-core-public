from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NGINX_TEMPLATE = ROOT / "code" / "deploy" / "nginx" / "lumatrader.conf"
VPS_DEPLOY = ROOT / "deploy" / "VPS_DEPLOY.sh"
DASHBOARD_PORTAL = ROOT / "dashboard" / "dashboard_portal.html"
DASHBOARD_INDEX = ROOT / "dashboard" / "index.html"


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
