from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "code" / "ops" / "repair_evidence_route.py"
SPEC = importlib.util.spec_from_file_location("repair_evidence_route", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

PROXIED = """server {
    listen 443 ssl;

    location /evidence/ {
        proxy_pass http://luma_gateway;
        proxy_set_header Host $host;
    }

    location / {
        root /opt/lumencore/dashboard;
    }
}
"""

STATIC = """server {
    listen 443 ssl;

    location = /evidence {
        return 301 /evidence/;
    }

    location /evidence/ {
        root /opt/lumencore/dashboard;
        index index.html;
        try_files $uri $uri/ =404;
        add_header Cache-Control "no-cache" always;
    }

    location / {
        root /opt/lumencore/dashboard;
    }
}
"""


class RepairEvidenceRouteTests(unittest.TestCase):
    def test_replaces_gateway_proxy_with_static_contract(self) -> None:
        result = MODULE.repair_config(PROXIED)
        self.assertTrue(result.changed)
        self.assertIn("location = /evidence", result.repaired)
        self.assertIn("root /opt/lumencore/dashboard;", result.repaired)
        self.assertNotIn("proxy_pass http://luma_gateway", result.repaired)
        self.assertIn("location / {", result.repaired)
        MODULE.validate_repaired_config(result.repaired)

    def test_static_contract_is_idempotent(self) -> None:
        result = MODULE.repair_config(STATIC)
        self.assertFalse(result.changed)
        self.assertEqual(STATIC, result.repaired)

    def test_refuses_missing_location(self) -> None:
        with self.assertRaises(MODULE.RouteRepairError):
            MODULE.repair_config("server { location / { return 200; } }\n")

    def test_refuses_duplicate_locations(self) -> None:
        duplicated = PROXIED + PROXIED
        with self.assertRaises(MODULE.RouteRepairError):
            MODULE.repair_config(duplicated)

    def test_cli_requires_explicit_apply_and_creates_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "lumatrader.conf"
            dashboard = root / "dashboard"
            index = dashboard / "evidence" / "index.html"
            index.parent.mkdir(parents=True)
            index.write_text("bounded evidence\n", encoding="utf-8")
            config.write_text(PROXIED, encoding="utf-8")

            check_code = MODULE.main([
                "--config", str(config),
                "--document-root", str(dashboard),
            ])
            self.assertEqual(1, check_code)
            self.assertEqual(PROXIED, config.read_text(encoding="utf-8"))

            apply_code = MODULE.main([
                "--config", str(config),
                "--document-root", str(dashboard),
                "--apply",
            ])
            self.assertEqual(0, apply_code)
            MODULE.validate_repaired_config(config.read_text(encoding="utf-8"))
            backups = list(root.glob("lumatrader.conf.bak.*"))
            self.assertEqual(1, len(backups))
            self.assertEqual(PROXIED, backups[0].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
