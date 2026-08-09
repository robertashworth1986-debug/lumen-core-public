from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "repair_public_security_headers.py"
NGINX_CONFIG = ROOT / "code" / "deploy" / "nginx" / "lumatrader.conf"
EVIDENCE_REPAIR_PATH = ROOT / "code" / "ops" / "repair_evidence_route.py"
VPS_WRAPPER = ROOT / "code" / "ops" / "REPAIR_PUBLIC_SECURITY_HEADERS_ON_VPS.sh"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MODULE = load_module(MODULE_PATH, "repair_public_security_headers")
EVIDENCE = load_module(EVIDENCE_REPAIR_PATH, "repair_evidence_route_headers")

PARTIAL = """server {
    listen 80;
    server_name lumen-core.ai;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name lumen-core.ai;
    ssl_certificate /etc/example/fullchain.pem;
    ssl_certificate_key /etc/example/privkey.pem;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location = /nginx-health {
        return 200 '{"status":"ok"}';
        add_header Content-Type application/json;
    }

    location /intel {
        proxy_pass http://intel;
        add_header Access-Control-Allow-Origin "$http_origin" always;
    }

    location /evidence/ {
        root /opt/lumencore/dashboard;
        add_header Cache-Control "no-cache" always;
    }

    location / {
        root /opt/lumencore/dashboard;
    }
}

server {
    listen 443 ssl;
    server_name research.lumen-core.ai;
    ssl_certificate /etc/example/fullchain.pem;
    ssl_certificate_key /etc/example/privkey.pem;
    location / { return 302 https://lumen-core.ai/; }
}
"""


class PublicSecurityHeaderTests(unittest.TestCase):
    def test_repairs_all_https_servers_and_header_bearing_locations(self) -> None:
        result = MODULE.repair_config(PARTIAL)
        self.assertTrue(result.changed)
        self.assertNotIn("X-XSS-Protection", result.repaired)
        MODULE.validate_repaired_config(result.repaired)

        for header in MODULE.PUBLIC_SECURITY_HEADERS:
            # Two HTTPS servers plus three header-bearing locations.
            self.assertEqual(5, result.repaired.count(header), header)

        http_block = result.repaired.split("server {", 2)[1]
        self.assertNotIn("Strict-Transport-Security", http_block)

    def test_repair_is_idempotent(self) -> None:
        first = MODULE.repair_config(PARTIAL)
        second = MODULE.repair_config(first.repaired)
        self.assertFalse(second.changed)
        self.assertEqual(first.repaired, second.repaired)

    def test_refuses_config_without_https_server(self) -> None:
        with self.assertRaises(MODULE.SecurityHeaderRepairError):
            MODULE.repair_config("server { listen 80; return 200; }\n")

    def test_canonical_nginx_config_has_complete_policy(self) -> None:
        text = NGINX_CONFIG.read_text(encoding="utf-8")
        MODULE.validate_repaired_config(text)
        self.assertFalse(MODULE.repair_config(text).changed)
        csp = dict(MODULE.HEADER_VALUES)["Content-Security-Policy"]
        self.assertIn("https://fonts.googleapis.com", csp)
        self.assertIn("https://fonts.gstatic.com", csp)
        self.assertIn("https://cdn.jsdelivr.net", csp)
        self.assertNotIn("http://127.0.0.1", csp)
        self.assertNotIn("*", csp)

    def test_evidence_repair_preserves_same_policy(self) -> None:
        self.assertEqual(
            MODULE.PUBLIC_SECURITY_HEADERS,
            EVIDENCE.PUBLIC_SECURITY_HEADERS,
        )
        proxied = """server {
    listen 443 ssl;
    location /evidence/ { proxy_pass http://gateway; }
}
"""
        repaired = EVIDENCE.repair_config(
            proxied, "/opt/lumencore/dashboard"
        ).repaired
        for header in MODULE.PUBLIC_SECURITY_HEADERS:
            self.assertIn(header, repaired)

    def test_cli_is_inspect_only_until_apply_and_creates_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "lumatrader.conf"
            config.write_text(PARTIAL, encoding="utf-8")

            inspect_code = MODULE.main(["--config", str(config)])
            self.assertEqual(1, inspect_code)
            self.assertEqual(PARTIAL, config.read_text(encoding="utf-8"))

            apply_code = MODULE.main(["--config", str(config), "--apply"])
            self.assertEqual(0, apply_code)
            MODULE.validate_repaired_config(config.read_text(encoding="utf-8"))
            backups = list(Path(tmp).glob("lumatrader.conf.pre-security-header-repair.*"))
            self.assertEqual(1, len(backups))
            self.assertEqual(PARTIAL, backups[0].read_text(encoding="utf-8"))

    def test_vps_wrapper_waits_for_reload_convergence(self) -> None:
        text = VPS_WRAPPER.read_text(encoding="utf-8")
        self.assertIn("verify_with_retry()", text)
        self.assertIn("--noproxy '*'", text)
        self.assertIn('"local ${route}"', text)
        self.assertIn('"public ${route}"', text)
        self.assertIn("did not converge after", text)
        self.assertIn("X-Frame-Options=%q", text)


if __name__ == "__main__":
    unittest.main()
