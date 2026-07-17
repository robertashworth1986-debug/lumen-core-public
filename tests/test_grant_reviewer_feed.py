from __future__ import annotations

import importlib.util
import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GRANT_REVIEWER_FEED.py"
PUBLIC_FEED = ROOT / "dashboard" / "data" / "grant_reviewer_feed.json"
MIRROR_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "GRANT_REVIEWER_FEED_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
)
TEST_NOW = "2026-07-17T08:00:00Z"


def load_module():
    spec = importlib.util.spec_from_file_location("grant_reviewer_feed", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_reviewer_feed_is_bounded_and_contains_no_private_form_data() -> None:
    module = load_module()
    feed = module.build_feed(TEST_NOW)
    rendered = json.dumps(feed)

    assert feed["schema"] == "grant_reviewer_feed_v2"
    assert feed["priority_candidate"]["opportunity_number"] == "DPA26BZ04-DV016"
    assert feed["priority_candidate"]["eligibility_status"] == "CONDITIONAL_DP2_CANDIDATE"
    assert feed["summary"]["successful_submission_or_received"] == 3
    assert feed["summary"]["agency_tracking_assigned"] == 2
    assert feed["summary"]["agency_received"] == 1
    assert feed["summary"]["rejected_with_errors"] == 1
    assert feed["summary"]["award_receipts"] == 0
    assert "agency_validated" not in feed["summary"]
    assert feed["independent_reproduction"]["status"] == "AWAITING_INDEPENDENT_RUNNER"
    assert feed["independent_reproduction"]["qualification_gate_passed"] is False
    assert feed["independent_reproduction"]["performance_promotion_allowed"] is False
    assert all(row["eligibility_status"] for row in feed["discovered_opportunities"])
    numbers = [row["opportunity_number"] for row in feed["discovered_opportunities"]]
    assert numbers[:4] == [
        "DON26BZ03-NV061",
        "DON26BZ03-NV063",
        "DON26BZ03-NV065",
        "DPA26BZ04-DV016",
    ]
    assert "NOAA-OAR-CPO-2012-2003041" not in numbers
    assert "SHTG-FY-26-01" not in numbers
    assert "SHTG-FY-26-02" not in numbers
    assert feed["curation"]["automated_keyword_matches_published"] is False

    assert "submission_packet" not in rendered.lower()
    assert "@gmail.com" not in rendered.lower()
    assert re.search(r"\b\d{2}-\d{7}\b", rendered) is None
    assert re.search(r"\b\d{3}[-.) ]+\d{3}[-. ]+\d{4}\b", rendered) is None
    assert re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", rendered, re.I) is None
    assert "C:\\" not in rendered
    assert "E:\\" not in rendered


def test_source_health_does_not_invent_zero_record_causes() -> None:
    module = load_module()
    source_health = module.build_feed(TEST_NOW)["source_health"]

    assert source_health["grants_gov"]["records"] == 475
    assert source_health["grants_gov"]["status"] == "HARVESTED_RECORDS_PRESENT"
    for source in ("sam_gov", "sbir_gov"):
        assert source_health[source]["records"] == 0
        assert source_health[source]["status"] == "ZERO_RECORDS_CAUSE_UNVERIFIED"
        boundary = source_health[source]["boundary"].lower()
        assert "does not establish outage" in boundary
        assert "maintenance" in boundary


def test_candidate_authority_deadline_and_recheck_controls_are_explicit() -> None:
    module = load_module()
    feed = module.build_feed(TEST_NOW)
    by_number = {row["opportunity_number"]: row for row in feed["discovered_opportunities"]}

    for number in ("DON26BZ03-NV061", "DON26BZ03-NV063", "DON26BZ03-NV065"):
        candidate = by_number[number]
        assert candidate["deadline_state"] == "OPEN_BY_PUBLISHED_DATES"
        assert candidate["published_window_actionable"] is True
        assert candidate["hours_to_published_deadline"] > 0
        assert candidate["source_authority_status"] == "TOPIC_MIRROR_VERIFIED_DSIP_RECHECK_REQUIRED"
        assert candidate["source_recheck_required"] is True
        assert "unofficial" in candidate["source_authority_boundary"].lower()
        assert candidate["source_url"].startswith("https://www.navysbir.com/")
        assert candidate["official_update_url"].startswith("https://www.dodsbirsttr.mil/")

    falcon = by_number["DPA26BZ04-DV016"]
    assert falcon["deadline_state"] == "OPEN_BY_PUBLISHED_DATES"
    assert falcon["source_authority_status"] == "OFFICIAL_PAGE_VERIFIED"
    assert falcon["source_recheck_required"] is False
    assert falcon["source_url"] == falcon["official_update_url"]

    grants_gov = by_number["24-569"]
    assert grants_gov["deadline_state"] == "DATE_ONLY_TIME_REVERIFY"
    assert grants_gov["source_recheck_required"] is True
    assert grants_gov["eligibility_status"] == "UNVERIFIED"


def test_stale_source_verification_is_downgraded_and_expired_dates_are_not_actionable() -> None:
    module = load_module()
    stale_feed = module.build_feed("2026-07-18T08:00:00Z")
    curated = stale_feed["discovered_opportunities"][:4]
    assert all(row["source_freshness_status"] == "STALE_REVERIFY_REQUIRED" for row in curated)
    assert all(row["source_recheck_required"] is True for row in curated)

    now, _ = module._parse_datetime(TEST_NOW)
    controls = module._deadline_controls(
        {"open_date": "2026-07-01", "close_date": "2026-07-16T12:00:00-04:00"},
        now,
    )
    assert controls["deadline_state"] == "PUBLISHED_DEADLINE_PASSED_REVERIFY"
    assert controls["published_window_actionable"] is False


def test_reviewer_feed_provenance_hashes_and_control_hash_are_complete() -> None:
    module = load_module()
    feed = module.build_feed(TEST_NOW)
    provenance = feed["provenance"]

    assert provenance
    for descriptor in provenance.values():
        path = ROOT / descriptor["relative_path"]
        assert descriptor["present"] is True
        assert descriptor["bytes"] == path.stat().st_size
        assert descriptor["sha256"] == module._sha256(path)
        assert len(descriptor["sha256"]) == 64
        assert not Path(descriptor["relative_path"]).is_absolute()

    unsigned = dict(feed)
    control_sha = unsigned.pop("control_sha256")
    assert control_sha == module._canonical_sha256(unsigned)
    module._validate_public_feed(feed)


def test_public_snapshot_is_valid_and_not_ignored_from_deployment() -> None:
    module = load_module()
    payload = json.loads(PUBLIC_FEED.read_text(encoding="utf-8"))
    module._validate_public_feed(payload)
    assert payload["schema"] == "grant_reviewer_feed_v2"

    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "--", str(PUBLIC_FEED.relative_to(ROOT))],
        cwd=ROOT,
        check=False,
    )
    assert ignored.returncode == 1


def test_bounded_mirror_receipt_is_internally_consistent() -> None:
    receipt = json.loads(MIRROR_RECEIPT.read_text(encoding="utf-8"))
    assert receipt["schema"] == "lumencore.bounded_public_mirror_receipt.v1"
    assert receipt["boundaries"]["in_app_dsip_browser_touched"] is False
    assert receipt["boundaries"]["private_grant_values_mirrored"] is False
    assert receipt["boundaries"]["credentials_mirrored"] is False

    manifest_rows = []
    for row in receipt["files"]:
        manifest_rows.append(
            {
                "relative_path": row["relative_path"],
                "bytes": row["bytes"],
                "sha256": row["sha256"],
            }
        )
        if row.get("storage") == "E_DRIVE_ONLY":
            continue
        source = ROOT / row["relative_path"]
        assert source.stat().st_size == row["bytes"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == row["sha256"]

    rendered = json.dumps(manifest_rows, sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(rendered.encode("utf-8")).hexdigest() == receipt["manifest_sha256"]
