from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
RECEIPT = (
    SPRINT_DIR
    / "NASHVILLE_EC_DEADLINE_PRESERVATION_ENGAGEMENT_RECEIPT_2026-07-17.json"
)
RESPONSE_CONTROL = (
    SPRINT_DIR / "NASHVILLE_EC_DEADLINE_PRESERVATION_RESPONSE_CONTROL_2026-07-17.md"
)
MIRROR_RECEIPT = (
    SPRINT_DIR
    / "NASHVILLE_EC_DEADLINE_PRESERVATION_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
)
MIRROR_RECEIPT_COPY = Path(
    "E:/LumaProofVault/SUBMISSIONS/NASHVILLE_EC_DEADLINE_PRESERVATION_20260717/"
    "grant_submissions/funding_sprint_20260709/"
    "NASHVILLE_EC_DEADLINE_PRESERVATION_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
)


def test_deadline_preservation_receipt_is_bounded_and_auditable() -> None:
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))

    assert payload["schema"] == "lumencore.external_engagement_receipt.v1"
    assert payload["engagement"]["lane_id"] == "nashville_ec_takeoff_fall_2026"
    assert payload["submission"]["status"] == "SENT_NO_ATTACHMENT"
    assert payload["submission"]["sent_utc"] == "2026-07-17T12:05:34Z"
    assert payload["submission"]["attachment"] is None
    assert payload["submission"]["subject"].encode("unicode_escape").decode() == (
        "Fall 2026 TakeOff application \\u2014 July 17 close time"
    )
    assert hashlib.sha256(payload["submission"]["subject"].encode("utf-8")).hexdigest() == (
        payload["submission"]["subject_sha256_utf8"]
    )
    assert re.fullmatch(r"[0-9a-f]{16}", payload["submission"]["gmail_message_id"])
    assert re.fullmatch(r"[0-9a-f]{16}", payload["submission"]["gmail_thread_id"])
    assert payload["submission"]["private_founder_values_stored_in_public_receipt"] is False

    basis = payload["official_basis"]
    assert basis["deadline_date"] == "2026-07-17"
    assert basis["deadline_time_published"] is False
    assert basis["application_url"] == "https://ec.co/apply/"
    assert basis["contact_source_url"].startswith("https://")
    assert basis["recipient"] == "info@ec.co"

    acknowledgment = payload["acknowledgment"]
    assert acknowledgment["status"] == (
        "DEADLINE_PRESERVATION_QUERY_SENT_RESPONSE_PENDING"
    )
    assert acknowledgment["reply_required"] is False
    assert acknowledgment["do_not_duplicate_send"] is True
    assert "not an application" in acknowledgment["bounded_summary"]
    assert "does not prove an application" in payload["claim_boundary"]
    assert "deadline right" in payload["claim_boundary"]


def test_response_control_preserves_exact_boundaries_and_safe_branches() -> None:
    rendered = RESPONSE_CONTROL.read_text(encoding="utf-8")
    lowered = rendered.lower()

    assert "Status: `QUERY_SENT_RESPONSE_PENDING`" in rendered
    assert "Duplicate send allowed: `false`" in rendered
    assert "Email substitutes for portal application: `false`" in rendered
    assert "Exact subject separator: `U+2014 EM DASH`" in rendered
    assert "e37f7384846eae544db40a7f722b67b80fcf41acf73a73618caabde2ed10724c" in rendered
    assert "this email is not an application and does not replace final portal submission" in lowered
    assert "### Exact close time provided" in rendered
    assert "### Technical details requested" in rendered
    assert "### Deadline reported closed" in rendered
    assert "### No response before close" in rendered
    assert "Do not send a duplicate email" in rendered
    assert "do not claim submission without an official confirmation" in rendered

    for forbidden in (
        "client_secret",
        "refresh_token",
        "api_key",
        "session token:",
        "password:",
        "verification code:",
        "private founder answer:",
    ):
        assert forbidden not in lowered


def test_current_deadline_preservation_snapshot_matches_all_sources() -> None:
    receipt = json.loads(MIRROR_RECEIPT.read_text(encoding="utf-8"))

    assert receipt["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 22
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["browser_navigation_performed"] is False
    assert receipt["private_founder_values_mirrored"] is False

    for artifact in receipt["artifacts"]:
        relative = Path(artifact["source"])
        source = ROOT / relative
        destination = Path(artifact["destination"])
        assert relative.is_absolute() is False
        assert ".." not in relative.parts
        assert source.is_file(), artifact["source"]
        assert destination.is_file(), artifact["destination"]
        assert source.stat().st_size == destination.stat().st_size == artifact["bytes"]
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest().upper()
        destination_hash = hashlib.sha256(destination.read_bytes()).hexdigest().upper()
        assert source_hash == destination_hash == artifact["sha256"]
        assert artifact["copy_sha256_matched"] is True

    assert MIRROR_RECEIPT_COPY.is_file()
    assert hashlib.sha256(MIRROR_RECEIPT.read_bytes()).hexdigest() == hashlib.sha256(
        MIRROR_RECEIPT_COPY.read_bytes()
    ).hexdigest()
    assert "does not prove" in receipt["claim_boundary"]
