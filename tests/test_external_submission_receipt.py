from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "EXTERNAL_SUBMISSION_RECEIPT_2026-07-13.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def test_external_submission_receipt_matches_local_attachments():
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert payload["schema"] == "external_submission_receipt.v1"

    rows = payload["submissions"]
    assert {row["notice_id"] for row in rows} == {"ACCAPGAIDPRFI4", "80TECH26RFI0020"}
    assert len({row["gmail_message_id"] for row in rows}) == len(rows)

    for row in rows:
        attachment = ROOT / row["attachment"]
        assert row["result"] == "SENT_WITH_ATTACHMENT"
        assert attachment.is_file()
        assert attachment.stat().st_size == row["attachment_bytes"]
        assert sha256_file(attachment) == row["attachment_sha256"]
        assert all(address.endswith((".gov", ".mil")) for address in row["recipients"])
        assert "acceptance" in row["claim_boundary"]
