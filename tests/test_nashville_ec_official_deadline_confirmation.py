from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "grant_submissions" / "NASHVILLE_EC_FALL_2026"
RECEIPT = PACKAGE_DIR / "NASHVILLE_EC_OFFICIAL_DEADLINE_CONFIRMATION_2026-07-17.json"
SUMMARY = PACKAGE_DIR / "NASHVILLE_EC_OFFICIAL_DEADLINE_CONFIRMATION_2026-07-17.md"


def test_official_deadline_confirmation_is_bounded_and_auditable() -> None:
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))

    assert payload["schema"] == (
        "lumencore.nashville_ec_official_deadline_confirmation.v1"
    )
    assert payload["status"] == (
        "OFFICIAL_SUPPORT_CONFIRMED_CLOSE_TIME_APPLICATION_NOT_SUBMITTED"
    )

    source = payload["source"]
    assert source["channel"] == "EMAIL_REPLY_TO_DEADLINE_SUPPORT_QUERY"
    assert source["organization"] == "Nashville Entrepreneur Center"
    assert re.fullmatch(r"[0-9a-f]{16}", source["gmail_message_id"])
    assert re.fullmatch(r"[0-9a-f]{16}", source["gmail_thread_id"])
    assert source["received_utc"] == "2026-07-17T16:11:48Z"
    assert source["raw_email_body_stored"] is False

    confirmation = payload["confirmation"]
    sentence = confirmation["bounded_exact_sentence"]
    assert sentence == "Applications are open until 11:59pm tonight on July 17."
    assert hashlib.sha256(sentence.encode("utf-8")).hexdigest() == (
        confirmation["bounded_exact_sentence_sha256"]
    )
    assert confirmation["deadline_date"] == "2026-07-17"
    assert confirmation["timezone_explicit_in_message"] is False
    assert confirmation["operational_timezone"] == "America/Chicago"
    assert confirmation["operational_local_deadline"] == (
        "2026-07-17T23:59:00-05:00"
    )
    assert confirmation["operational_utc_deadline"] == "2026-07-18T04:59:00Z"
    assert confirmation["operational_rule"] == (
        "SUBMIT_EARLY_DO_NOT_WAIT_FOR_THE_STATED_CUTOFF"
    )

    state = payload["application_state"]
    assert state["portal_submission_verified"] is False
    assert state["human_founder_facts_resolved"] is False
    assert state["final_submit_clicked"] is False
    assert state["duplicate_deadline_query_allowed"] is False
    assert "does not prove a portal application" in payload["claim_boundary"]
    assert "explicit inference" in payload["claim_boundary"]


def test_public_summary_matches_receipt_without_overclaiming() -> None:
    rendered = SUMMARY.read_text(encoding="utf-8")
    lowered = rendered.lower()

    assert "11:59 PM tonight, July 17" in rendered
    assert "America/Chicago" in rendered
    assert "reply did not spell out a timezone" in lowered
    assert "application is not submitted" in lowered
    assert "six founder confirmations remain" in lowered
    assert "does not prove a portal application was completed" in lowered
    assert "raw email body stored in this public artifact: `false`" in lowered

    for forbidden in (
        "client_secret",
        "refresh_token",
        "api_key",
        "password:",
        "verification code:",
        "private founder answer:",
    ):
        assert forbidden not in lowered
