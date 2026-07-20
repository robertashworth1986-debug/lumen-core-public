from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = (
    ROOT
    / "grant_submissions"
    / "NASHVILLE_EC_FALL_2026"
    / "NASHVILLE_EC_FINANCIAL_AID_E_DRIVE_SYNC_RECEIPT_2026-07-20.json"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_nashville_financial_aid_public_mirror_is_bounded_and_hash_matched():
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))

    assert payload["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert payload["artifact_count"] == len(payload["artifacts"]) == 19
    assert payload["all_sha256_matched_after_copy"] is True
    assert payload["public_action_control_only"] is True
    assert payload["private_founder_values_mirrored"] is False
    assert payload["browser_navigation_performed"] is False

    sources = {row["source"] for row in payload["artifacts"]}
    assert {
        "code/ops/BUILD_NASHVILLE_EC_FINANCIAL_AID_ACTION.py",
        "code/ops/BUILD_NASHVILLE_EC_FINANCIAL_AID_E_DRIVE_SYNC_RECEIPT.py",
        "tests/test_nashville_ec_financial_aid_action.py",
        "tests/test_nashville_ec_financial_aid_e_drive_sync_receipt.py",
        "grant_submissions/NASHVILLE_EC_FALL_2026/"
        "NASHVILLE_EC_FINANCIAL_AID_ACTION_2026-07-20.json",
        "grant_submissions/funding_sprint_20260709/"
        "OUTREACH_FOLLOWUP_ACTION_QUEUE_2026-07-18.json",
    }.issubset(sources)
    assert all("private" not in Path(source).parts for source in sources)

    for artifact in payload["artifacts"]:
        source = ROOT / artifact["source"]
        destination = Path(artifact["destination"])
        assert source.is_file(), artifact["source"]
        assert destination.is_file(), artifact["destination"]
        assert source.stat().st_size == destination.stat().st_size == artifact["bytes"]
        assert sha256_file(source) == sha256_file(destination) == artifact["sha256"]
        assert artifact["copy_sha256_matched"] is True

    receipt_copy = Path(payload["destination_root"]) / RECEIPT.relative_to(ROOT)
    assert receipt_copy.is_file()
    assert sha256_file(RECEIPT) == sha256_file(receipt_copy)
    assert "does not include private founder answers" in payload["claim_boundary"]
