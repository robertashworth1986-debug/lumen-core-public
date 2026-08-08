from __future__ import annotations

import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"


class PublicDiscoveryTests(unittest.TestCase):
    def test_robots_exposes_only_bounded_review_routes(self):
        text = (DASHBOARD / "robots.txt").read_text(encoding="utf-8")
        for route in (
            "Allow: /opportunity_sprint.html",
            "Allow: /proof_to_pilot.html",
            "Allow: /evidence/",
            "Allow: /external_review.html",
            "Allow: /build_week/prooflock_console/",
        ):
            self.assertIn(route, text)
        for route in (
            "Disallow: /api/",
            "Disallow: /auth/",
            "Disallow: /data/",
            "Disallow: /mission_control.html",
            "Disallow: /grants.html",
            "Disallow: /kraken_execution_dashboard.html",
        ):
            self.assertIn(route, text)
        self.assertIn("Sitemap: https://lumen-core.ai/sitemap.xml", text)

    def test_sitemap_contains_only_current_bounded_public_routes(self):
        root = ET.parse(DASHBOARD / "sitemap.xml").getroot()
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = [node.text for node in root.findall("sm:url/sm:loc", namespace)]
        self.assertEqual(
            locations,
            [
                "https://lumen-core.ai/",
                "https://lumen-core.ai/opportunity_sprint.html",
                "https://lumen-core.ai/proof_to_pilot.html",
                "https://lumen-core.ai/evidence/",
                "https://lumen-core.ai/external_review.html",
                "https://lumen-core.ai/build_week/prooflock_console/",
            ],
        )
        serialized = (DASHBOARD / "sitemap.xml").read_text(encoding="utf-8")
        self.assertNotIn("mission_control", serialized)
        self.assertNotIn("grants.html", serialized)

    def test_webmanifest_is_strict_and_bounded(self):
        path = DASHBOARD / "manifest.json"
        pairs_seen: list[str] = []

        def strict_object(pairs):
            result = {}
            for key, value in pairs:
                self.assertNotIn(key, result)
                pairs_seen.append(key)
                result[key] = value
            return result

        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)
        self.assertTrue(pairs_seen)
        self.assertEqual(payload["start_url"], "/")
        self.assertEqual(payload["scope"], "/")
        self.assertEqual(payload["icons"][0]["src"], "/assets/lumencore-mark.svg")
        self.assertNotIn("screenshots", payload)
        self.assertEqual(
            payload,
            json.loads((DASHBOARD / "site.webmanifest").read_text(encoding="utf-8")),
            "legacy .webmanifest and canonical JSON manifest must not drift",
        )

    def test_indexed_pages_declare_canonical_routes_and_public_mark(self):
        pages = {
            "operator_home.html": "https://lumen-core.ai/",
            "opportunity_sprint.html": "https://lumen-core.ai/opportunity_sprint.html",
            "proof_to_pilot.html": "https://lumen-core.ai/proof_to_pilot.html",
            "external_review.html": "https://lumen-core.ai/external_review.html",
            "evidence/index_bounded.html": "https://lumen-core.ai/evidence/",
        }
        for relative, canonical in pages.items():
            with self.subTest(page=relative):
                text = (DASHBOARD / relative).read_text(encoding="utf-8")
                self.assertIn('name="robots" content="index,follow,max-image-preview:large"', text)
                self.assertIn(f'rel="canonical" href="{canonical}"', text)
                self.assertIn('rel="icon" href="/assets/lumencore-mark.svg"', text)
                self.assertIn('rel="manifest" href="/manifest.json"', text)

    def test_public_mark_is_accessible_svg_without_script(self):
        text = (DASHBOARD / "assets" / "lumencore-mark.svg").read_text(encoding="utf-8")
        root = ET.fromstring(text)
        self.assertTrue(root.tag.endswith("svg"))
        self.assertNotIn("<script", text.casefold())
        self.assertIn("LumenCore mark", text)

    def test_deploy_gate_requires_canonical_manifest_and_safe_mime_type(self):
        workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("dashboard/manifest.json", workflow)
        self.assertIn("https://lumen-core.ai/manifest.json", workflow)
        self.assertIn('[[ "$MANIFEST_TYPE" == application/json*', workflow)
        self.assertIn("application/manifest+json*", workflow)


if __name__ == "__main__":
    unittest.main()
