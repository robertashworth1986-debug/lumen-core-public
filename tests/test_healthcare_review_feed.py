from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = ROOT / "code" / "ops" / "run_healthcare_grants_engine.py"
FEED_SCRIPT = ROOT / "code" / "ops" / "build_healthcare_website_feed.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_engine_urgency_labels_are_review_only():
    module = load_module("healthcare_grants_engine", ENGINE_SCRIPT)

    assert module.action_label(None) == "MANUAL_REVIEW"
    assert module.action_label(-1) == "CLOSED_OR_EXPIRED"
    assert module.action_label(3) == "URGENT_REVIEW"
    assert module.action_label(10) == "EXPEDITED_REVIEW"
    assert module.action_label(20) == "ACTIVE_REVIEW"
    assert module.action_label(40) == "WATCHLIST"
    assert all(
        "SUBMIT" not in module.action_label(days)
        for days in (None, -1, 3, 10, 20, 40)
    )


def test_public_feed_migrates_legacy_actions_to_fail_closed_review_records():
    module = load_module("healthcare_website_feed", FEED_SCRIPT)
    payload = {
        "schema": "healthcare_grants_engine_v1",
        "generated_utc": "2026-07-01T00:00:00Z",
        "scope": {},
        "metrics": {
            "n_scanned": 1,
            "n_scored": 1,
            "n_selected": 1,
        },
        "records": [
            {
                "id": "fixture",
                "number": "TEST-123",
                "title": "Fixture",
                "agency": "Agency",
                "status": "posted",
                "action": "IMMEDIATE_SUBMIT",
                "days_to_close": 3,
                "close_date": "2026-08-01",
                "url": "https://www.grants.gov/search-results-detail/TEST-123",
                "scores": {"composite": 80},
                "source_files": ["fixture.json"],
            }
        ],
    }

    feed = module.build_feed(payload, top_n=1)
    record = feed["records"][0]
    dumped = json.dumps(feed)

    assert feed["schema"] == "healthcare_website_feed_v2"
    assert record["action"] == "URGENT_REVIEW"
    assert record["eligibility_status"] == (
        "UNVERIFIED_REQUIRES_OFFICIAL_SOURCE_REVIEW"
    )
    assert record["deadline_verified_utc"] is None
    assert record["deadline_actionable"] is False
    assert record["submission_authorized"] is False
    assert record["abstention_reason"]
    assert len(record["source_sha256"]) == 64
    assert set(record["links"]) == {
        "review_route",
        "official_source_review_url",
        "alternate_review_urls",
        "source_url",
        "grant_console_query",
    }
    assert feed["summary"]["submission_authorized_count"] == 0
    assert feed["summary"]["deadline_actionable_count"] == 0
    assert feed["summary"]["urgent_or_expedited_review"] == 1
    assert "IMMEDIATE_SUBMIT" not in dumped
    assert "primary_submit_url" not in dumped
    assert "auto_fill" not in dumped
    assert "ai_fill" not in dumped


def test_widget_consumes_only_review_and_draft_routes():
    widget = (
        ROOT / "dashboard" / "js" / "luma_healthcare_grants_embed.js"
    ).read_text(encoding="utf-8")

    assert "links.official_source_review_url" in widget
    assert "links.grant_console_query" in widget
    assert "links.primary_submit_url" not in widget
    assert "links.ai_fill_query" not in widget
    assert "Review Official Source" in widget
    assert "Draft Workspace" in widget
