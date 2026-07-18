from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = (
    ROOT
    / "grant_submissions"
    / "OPENAI_BUILD_WEEK_20260721"
    / "OPENAI_BUILD_WEEK_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_build_week_e_drive_mirror_preserves_paths_and_hashes():
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    destination_root = Path(payload["destination_root"])

    assert payload["schema"] == "lumencore.openai_build_week_e_drive_sync_receipt.v1"
    assert payload["artifact_count"] == len(payload["artifacts"]) == 23
    assert payload["all_sha256_matched_after_copy"] is True
    assert payload["relative_paths_preserved"] is True
    assert payload["private_files_mirrored"] is False
    assert payload["browser_navigation_performed"] is False
    assert destination_root == Path("E:/LumaProofVault/OPPORTUNITIES/OPENAI_BUILD_WEEK_20260721")
    assert any(
        row["source"].endswith("OPENAI_BUILD_WEEK_PUBLIC_DEMO_RECEIPT_2026-07-18.json")
        for row in payload["artifacts"]
    )

    for row in payload["artifacts"]:
        source = ROOT / row["source"]
        destination = destination_root / row["source"]
        assert source.is_file(), row["source"]
        assert destination.is_file(), str(destination)
        assert source.stat().st_size == destination.stat().st_size == row["bytes"]
        assert sha256(source) == sha256(destination) == row["sha256"]
        assert row["copy_sha256_matched"] is True

    receipt_copy = Path(payload["receipt_copy_destination"])
    assert receipt_copy.is_file()
    assert sha256(RECEIPT) == sha256(receipt_copy)
    assert "does not prove continuous public-demo availability" in payload["claim_boundary"]
