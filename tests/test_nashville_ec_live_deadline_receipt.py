from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_NASHVILLE_EC_LIVE_DEADLINE_RECEIPT.py"
MIRROR_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "NASHVILLE_EC_FALL_2026"
    / "NASHVILLE_EC_LIVE_DEADLINE_RECEIPT_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("nashville_ec_live_deadline_receipt", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def fake_fetcher(url: str) -> dict:
    pages = {
        "https://ec.co/": """
            <html><head><title>Entrepreneur Center</title><script>meeting id: hidden</script></head>
            <body><h1>Fall 2026 Accelerators</h1><p>Applications close July 17.</p>
            <a>Apply Now</a></body></html>
        """,
        "https://ec.co/apply/": """
            <html><head><title>Apply - Entrepreneur Center</title></head><body>
            <h1>Start Your Application</h1><p>Save your progress and finish later</p>
            <p>2026 Fall Program Application</p></body></html>
        """,
        "https://ec.co/accelerators/takeoff/": """
            <html><head><title>TakeOff</title></head><body><h1>TakeOff Accelerator</h1>
            <p>Applications for the Fall 2026 Cohort are open.</p><p>September to December</p>
            </body></html>
        """,
    }
    raw = pages[url].encode("utf-8")
    return {
        "requested_url": url,
        "final_url": url,
        "http_status": 200,
        "content_type": "text/html",
        "etag": None,
        "last_modified": None,
        "raw": raw,
    }


def test_live_receipt_confirms_date_without_inventing_a_close_time():
    module = load_module()
    payload = module.build_payload(
        fetcher=fake_fetcher,
        retrieved_utc="2026-07-17T05:05:00+00:00",
    )

    assert payload["schema"] == "lumencore.nashville_ec_live_deadline_receipt.v1"
    assert payload["status"] == "OFFICIAL_OPEN_DATE_ONLY_DEADLINE_HUMAN_FACTS_REQUIRED"
    assert payload["deadline"]["date"] == "2026-07-17"
    assert payload["deadline"]["date_status"] == "CONFIRMED_ON_OFFICIAL_HOMEPAGE"
    assert payload["deadline"]["time"] is None
    assert payload["deadline"]["time_candidates_near_date"] == []
    assert payload["deadline"]["time_status"] == (
        "NO_CLOSE_TIME_DETECTED_ON_FETCHED_OFFICIAL_PAGES"
    )
    assert payload["deadline"]["operational_rule"] == "SUBMIT_EARLY_NO_MIDNIGHT_ASSUMPTION"
    assert payload["application"]["open_signal_present"] is True


def test_live_receipt_requires_human_review_for_a_time_near_the_deadline():
    module = load_module()

    def timed_fetcher(url: str) -> dict:
        row = fake_fetcher(url)
        if url == "https://ec.co/":
            row["raw"] = row["raw"].replace(b"July 17.", b"July 17 at 4:30 PM.")
        return row

    payload = module.build_payload(
        fetcher=timed_fetcher,
        retrieved_utc="2026-07-17T05:05:00+00:00",
    )

    assert payload["status"] == "OFFICIAL_OPEN_TIME_TEXT_DETECTED_REVIEW_REQUIRED"
    assert payload["deadline"]["time_candidates_near_date"] == ["4:30 PM"]
    assert payload["deadline"]["time_status"] == (
        "TIME_TEXT_DETECTED_NEAR_DATE_REVIEW_REQUIRED"
    )


def test_receipt_hashes_sources_and_never_uses_the_session_browser():
    module = load_module()
    payload = module.build_payload(
        fetcher=fake_fetcher,
        retrieved_utc="2026-07-17T05:05:00+00:00",
    )

    assert payload["integrity"]["source_count"] == 3
    assert payload["integrity"]["all_fetches_http_200_html"] is True
    assert payload["integrity"]["all_expected_markers_present"] is True
    assert payload["integrity"]["raw_html_stored"] is False
    assert payload["integrity"]["network_route"] == "DIRECT_HTTPS_NO_SESSION_BROWSER"
    assert payload["integrity"]["browser_navigation_performed"] is False
    assert payload["application"]["final_submit_allowed_without_human"] is False
    assert payload["application"]["fee_or_terms_acceptance_allowed_without_human"] is False
    assert len(payload["receipt_sha256"]) == 64
    for page in payload["sources"]:
        assert page["http_status"] == 200
        assert len(page["content_sha256"]) == 64
        assert len(page["receipt_sha256"]) == 64
        assert page["raw_html_stored"] is False


def test_visible_text_parser_omits_script_content_and_output_is_public_safe():
    module = load_module()
    fetched = fake_fetcher("https://ec.co/")
    page = module.analyze_page("homepage", fetched, "2026-07-17T05:05:00+00:00")
    payload = module.build_payload(
        fetcher=fake_fetcher,
        retrieved_utc="2026-07-17T05:05:00+00:00",
    )
    rendered = module.render_markdown(payload)

    assert page["all_expected_markers_present"] is True
    assert "meeting id" not in rendered.lower()
    module.ensure_public_safe(rendered)
    assert "no exact closing hour was detected" in rendered.lower()
    assert "session-browser navigation performed: `false`" in rendered.lower()
    assert "does not prove" in rendered.lower()


def test_historical_bounded_e_drive_mirror_receipt_is_consistent():
    receipt = json.loads(MIRROR_RECEIPT.read_text(encoding="utf-8-sig"))

    assert receipt["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 4
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["browser_navigation_performed"] is False
    assert receipt["destination_root"].startswith("E:/LumaProofVault/")
    for artifact in receipt["artifacts"]:
        mirror = Path(artifact["destination"])
        assert mirror.is_file(), artifact["destination"]
        assert artifact["bytes"] == artifact["copy_bytes"]
        assert artifact["sha256"] == artifact["copy_sha256"]
        assert artifact["copy_sha256_matched"] is True
        assert mirror.stat().st_size == artifact["copy_bytes"]
        mirror_hash = hashlib.sha256(mirror.read_bytes()).hexdigest().upper()
        assert mirror_hash == artifact["copy_sha256"]

    assert "does not prove portal submission" in receipt["claim_boundary"]
