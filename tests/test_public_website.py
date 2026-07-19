from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"
ENSURE_SPEC = importlib.util.spec_from_file_location(
    "ensure_dashboard_command_fabric",
    ROOT / "code" / "ops" / "ensure_dashboard_command_fabric.py",
)
assert ENSURE_SPEC and ENSURE_SPEC.loader
ENSURE_MODULE = importlib.util.module_from_spec(ENSURE_SPEC)
ENSURE_SPEC.loader.exec_module(ENSURE_MODULE)


class PageInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.start_tags: list[tuple[str, dict[str, str]]] = []
        self.h1_count = 0
        self.main_count = 0
        self.nav_labels: list[str] = []
        self.json_ld: list[str] = []
        self._capture_json_ld = False
        self._json_ld_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        self.start_tags.append((tag, values))
        if tag == "h1":
            self.h1_count += 1
        elif tag == "main":
            self.main_count += 1
        elif tag == "nav":
            self.nav_labels.append(values.get("aria-label", ""))
        elif tag == "script" and values.get("type") == "application/ld+json":
            self._capture_json_ld = True
            self._json_ld_buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture_json_ld:
            self._json_ld_buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._capture_json_ld:
            self.json_ld.append("".join(self._json_ld_buffer).strip())
            self._capture_json_ld = False
            self._json_ld_buffer = []

    def first(self, tag: str, **attrs: str) -> dict[str, str] | None:
        for found_tag, values in self.start_tags:
            if found_tag != tag:
                continue
            if all(values.get(key) == expected for key, expected in attrs.items()):
                return values
        return None


class PublicWebsiteTests(unittest.TestCase):
    PUBLIC_PAGES = (
        "operator_home.html",
        "proof_to_pilot.html",
        "review_sprint.html",
    )
    OPERATOR_PAGES = (
        "mission_control.html",
        "quant_lab.html",
        "kraken_execution_dashboard.html",
        "grants.html",
        "forecast.html",
        "explain.html",
    )

    def inspect(self, name: str) -> tuple[str, PageInspector]:
        text = (DASHBOARD / name).read_text(encoding="utf-8")
        inspector = PageInspector()
        inspector.feed(text)
        return text, inspector

    def test_public_pages_have_semantic_and_search_metadata(self) -> None:
        for name in self.PUBLIC_PAGES:
            with self.subTest(page=name):
                text, page = self.inspect(name)
                self.assertEqual(page.h1_count, 1)
                self.assertEqual(page.main_count, 1)
                self.assertIn("Primary navigation", page.nav_labels)
                self.assertIsNotNone(page.first("meta", name="description"))
                robots = page.first("meta", name="robots")
                self.assertIsNotNone(robots)
                self.assertIn("index", robots["content"])
                self.assertNotIn("noindex", robots["content"])
                canonical = page.first("link", rel="canonical")
                self.assertIsNotNone(canonical)
                self.assertTrue(canonical["href"].startswith("https://lumen-core.ai/"))
                self.assertIsNotNone(
                    page.first("link", rel="stylesheet", href="./assets/public_site.css")
                )
                self.assertIsNotNone(
                    page.first("script", src="./assets/public_site.js")
                )
                self.assertIsNotNone(
                    page.first("script", src="./assets/luma_command_fabric.js")
                )
                self.assertTrue(page.json_ld)
                for payload in page.json_ld:
                    parsed = json.loads(payload)
                    self.assertEqual(parsed["@context"], "https://schema.org")
                self.assertIn("Evidence", text)

    def test_homepage_keeps_bounded_story_and_clear_commercial_path(self) -> None:
        text, _ = self.inspect("operator_home.html")
        self.assertIn("One proof path.", text)
        self.assertIn("One bounded decision.", text)
        self.assertIn("Internal replay evidence is not external validation.", text)
        self.assertIn("Bounded Validation Sprint", text)
        self.assertIn("/proof_to_pilot.html", text)
        self.assertIn("/review_sprint.html", text)
        self.assertIn("robertashworth4444@gmail.com", text)
        self.assertNotIn("One platform. Four products. One truth layer.", text)
        self.assertNotIn("Finish and submit the current NSF Project Pitch.", text)
        self.assertNotIn('href="/evidence/"', text)

    def test_proof_page_states_external_validation_boundary(self) -> None:
        text, _ = self.inspect("proof_to_pilot.html")
        self.assertIn("Internal simulation, replay, benchmark, and hash records are not external validation.", text)
        self.assertIn("independently reproduced", text)
        self.assertIn("external_review", text)
        self.assertIn("No result authorizes live trading or operational control", text)

    def test_sprint_page_is_commercial_but_non_promissory(self) -> None:
        text, _ = self.inspect("review_sprint.html")
        self.assertIn("typically 30-day engagement", text)
        self.assertIn("mutually agreed written scope", text)
        self.assertIn("No guaranteed performance", text)
        self.assertIn("The sprint is designed to reject weak claims", text)
        self.assertNotIn("guaranteed savings", text.lower())
        self.assertNotIn("guaranteed return", text.lower())

    def test_public_support_assets_parse(self) -> None:
        manifest = json.loads((DASHBOARD / "site.webmanifest").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "LumenCore")
        self.assertEqual(manifest["start_url"], "/")
        ET.parse(DASHBOARD / "sitemap.xml")
        ET.parse(DASHBOARD / "assets" / "lumencore-mark.svg")
        robots = (DASHBOARD / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("Sitemap: https://lumen-core.ai/sitemap.xml", robots)
        self.assertIn("Disallow: /grants.html", robots)
        self.assertIn("Allow: /review_sprint.html", robots)

    def test_public_pages_do_not_mount_operator_command_chrome(self) -> None:
        fabric = (DASHBOARD / "assets" / "luma_command_fabric.js").read_text(
            encoding="utf-8"
        )
        for name in self.PUBLIC_PAGES:
            self.assertIn(f'"{name}": true', fabric)
        self.assertIn("var isPublicPage = Boolean(PUBLIC_PAGES[currentFile]);", fabric)
        self.assertIn("if (!isPublicPage) {", fabric)
        self.assertIn("buildRail();", fabric)
        self.assertIn("buildPalette();", fabric)

    def test_canonical_operator_pages_are_not_indexable(self) -> None:
        marker = '<meta name="robots" content="noindex,nofollow,noarchive">'
        for name in self.OPERATOR_PAGES:
            with self.subTest(page=name):
                text = (DASHBOARD / name).read_text(encoding="utf-8")
                self.assertIn(marker, text)

    def test_index_file_is_a_nonindexing_root_fallback(self) -> None:
        text = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        self.assertIn('content="noindex,follow"', text)
        self.assertIn('content="0;url=/"', text)
        self.assertIn('rel="canonical" href="https://lumen-core.ai/"', text)

    def test_operator_pages_receive_noindex_and_public_pages_do_not(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            operator = root / "mission_control.html"
            operator.write_text(
                "<html><head></head><body><main>operator</main></body></html>",
                encoding="utf-8",
            )
            self.assertTrue(ENSURE_MODULE.ensure_fabric(operator))
            first = operator.read_text(encoding="utf-8")
            self.assertIn('name="robots" content="noindex,nofollow,noarchive"', first)
            self.assertIn("luma_command_fabric.css", first)
            self.assertIn("luma_command_fabric.js", first)
            self.assertFalse(ENSURE_MODULE.ensure_fabric(operator))
            self.assertEqual(first, operator.read_text(encoding="utf-8"))

            public = root / "proof_to_pilot.html"
            public.write_text(
                '<html><head><meta name="robots" content="index,follow"></head>'
                "<body><main>public</main></body></html>",
                encoding="utf-8",
            )
            self.assertTrue(ENSURE_MODULE.ensure_fabric(public))
            public_text = public.read_text(encoding="utf-8")
            self.assertIn('content="index,follow"', public_text)
            self.assertNotIn("noindex,nofollow,noarchive", public_text)


if __name__ == "__main__":
    unittest.main()
