from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code" / "ops"))

from build_opai_consortium_intelligence import (  # noqa: E402
    CrawlEngine,
    CrawlResult,
    HttpResponse,
    build_intelligence_payload,
    canonical_json_hash,
    is_allowed_url,
    parse_public_page,
)


HOME_HTML = b"""
<!doctype html>
<html>
<head>
  <title>OPAI Home</title>
  <meta name="description" content="Public consortium page">
</head>
<body>
  <h1>Uniting the Electric Sector with Advanced AI Solutions</h1>
  <nav>
    <a href="/consortium-membership">Membership</a>
    <a href="/group-materials-and-meetings/data-sharing">Data Sharing</a>
    <a href="https://outside.example/private">Outside</a>
    <a href="mailto:OpenPowerAI@epri.com">Contact</a>
  </nav>
  <img alt="TVA" src="tva.png">
  <script>OpenPowerAI@fake.invalid</script>
</body>
</html>
"""

MEMBERSHIP_HTML = b"""
<!doctype html>
<html>
<head><title>Consortium Membership | OPAI</title></head>
<body>
  <h1>Consortium Membership</h1>
  <p>Contact OpenPowerAI@epri.com to express interest.</p>
  <img alt="Google" src="google.png">
  <img alt="TVA" src="tva.png">
  <img alt="Image" src="generic.png">
  <a href="https://restservice.epri.com/publicattachment/92892">Member Benefits and Expectations</a>
  <form action="https://forms.example/submit" method="post"><input name="email"></form>
</body>
</html>
"""

DATA_SHARING_HTML = b"""
<!doctype html>
<html>
<head><title>Data Sharing | OPAI</title></head>
<body>
  <h1>Data Sharing</h1>
  <p>Next meeting July 15, 2026.</p>
</body>
</html>
"""


class OPAIConsortiumIntelligenceTests(unittest.TestCase):
    def test_public_page_parser_extracts_structure_without_script_content(self) -> None:
        page = parse_public_page(
            HttpResponse(
                url="https://openpowerai.org/consortium-membership",
                status=200,
                content_type="text/html; charset=utf-8",
                body=MEMBERSHIP_HTML,
            )
        )
        self.assertEqual(page.page_type, "membership")
        self.assertIn("openpowerai@epri.com", page.contact_emails)
        self.assertNotIn("fake.invalid", " ".join(page.contact_emails))
        self.assertEqual(page.form_actions, ["https://forms.example/submit"])
        self.assertIn("Google", page.image_alts)
        self.assertTrue(page.raw_sha256)

    def test_crawler_stays_on_allowlist_and_never_submits_form(self) -> None:
        fixtures = {
            "https://openpowerai.org/": HOME_HTML,
            "https://openpowerai.org/consortium-membership": MEMBERSHIP_HTML,
            "https://openpowerai.org/group-materials-and-meetings/data-sharing": DATA_SHARING_HTML,
        }
        fetched: list[str] = []

        def fetcher(url: str) -> HttpResponse:
            fetched.append(url)
            body = fixtures[url]
            return HttpResponse(url=url, status=200, content_type="text/html", body=body)

        engine = CrawlEngine(
            fetcher=fetcher,
            robots_can_fetch=lambda _url: True,
            allowed_hosts=("openpowerai.org",),
            max_pages=10,
            delay_seconds=0,
            sleeper=lambda _seconds: None,
        )
        result = engine.crawl("https://openpowerai.org/")

        self.assertEqual(set(fetched), set(fixtures))
        self.assertNotIn("https://forms.example/submit", fetched)
        self.assertIn("https://outside.example/private", result.skipped_external_urls)
        self.assertTrue(all(is_allowed_url(url, ("openpowerai.org",)) for url in fetched))

    def test_external_redirect_is_blocked_before_parsing(self) -> None:
        fetched: list[str] = []

        def fetcher(url: str) -> HttpResponse:
            fetched.append(url)
            return HttpResponse(
                url="https://outside.example/redirected",
                status=200,
                content_type="text/html",
                body=b"<html><body><h1>Private destination</h1></body></html>",
            )

        engine = CrawlEngine(
            fetcher=fetcher,
            robots_can_fetch=lambda _url: True,
            allowed_hosts=("openpowerai.org",),
            max_pages=2,
            delay_seconds=0,
            sleeper=lambda _seconds: None,
        )
        result = engine.crawl("https://openpowerai.org/")

        self.assertEqual(fetched, ["https://openpowerai.org/"])
        self.assertEqual(result.pages, [])
        self.assertIn("https://outside.example/redirected", result.skipped_external_urls)
        self.assertEqual(result.errors[0].error_type, "ExternalRedirectBlocked")

    def test_robots_disallow_prevents_fetch(self) -> None:
        fetched: list[str] = []

        def fetcher(url: str) -> HttpResponse:
            fetched.append(url)
            return HttpResponse(url=url, status=200, content_type="text/html", body=HOME_HTML)

        engine = CrawlEngine(
            fetcher=fetcher,
            robots_can_fetch=lambda _url: False,
            allowed_hosts=("openpowerai.org",),
            max_pages=2,
            delay_seconds=0,
            sleeper=lambda _seconds: None,
        )
        result = engine.crawl("https://openpowerai.org/")

        self.assertEqual(fetched, [])
        self.assertEqual(result.pages, [])
        self.assertEqual(result.skipped_disallowed_urls, ["https://openpowerai.org/"])

    def test_payload_deduplicates_members_and_keeps_claim_boundary_closed(self) -> None:
        pages = [
            parse_public_page(
                HttpResponse(
                    url="https://openpowerai.org/",
                    status=200,
                    content_type="text/html",
                    body=HOME_HTML,
                )
            ),
            parse_public_page(
                HttpResponse(
                    url="https://openpowerai.org/consortium-membership",
                    status=200,
                    content_type="text/html",
                    body=MEMBERSHIP_HTML,
                )
            ),
            parse_public_page(
                HttpResponse(
                    url="https://openpowerai.org/group-materials-and-meetings/data-sharing",
                    status=200,
                    content_type="text/html",
                    body=DATA_SHARING_HTML,
                )
            ),
        ]
        payload = build_intelligence_payload(
            CrawlResult(
                pages=pages,
                errors=[],
                skipped_external_urls=[],
                skipped_disallowed_urls=[],
            ),
            generated_utc="2026-07-16T00:00:00+00:00",
            allowed_hosts=("openpowerai.org",),
        )

        self.assertEqual(payload["member_candidates"], ["Google", "TVA"])
        self.assertTrue(payload["source_policy"]["read_only"])
        self.assertFalse(payload["source_policy"]["forms_submitted"])
        self.assertIn("does not prove consortium membership", payload["claim_boundary"].lower())
        self.assertEqual(payload["summary"]["pages_fetched"], 3)

    def test_intelligence_hash_is_deterministic(self) -> None:
        payload = {"b": 2, "a": [3, 1]}
        self.assertEqual(canonical_json_hash(payload), canonical_json_hash(payload))
        self.assertEqual(len(canonical_json_hash(payload)), 64)


if __name__ == "__main__":
    unittest.main()
