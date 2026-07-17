import hashlib
import json
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "grant_submissions" / "funding_sprint_20260709" / "CDC_AI_ACQUISITION_RFI_ARTIFACT_MANIFEST_2026-07-15.json"
RECEIPT = ROOT / "grant_submissions" / "funding_sprint_20260709" / "CDC_AI_ACQUISITION_RFI_ENGAGEMENT_RECEIPT_2026-07-16.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def test_cdc_rfi_manifest_hashes_and_boundaries() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["submission_state"] == "SENT_RECEIPT_CONFIRMED_FOLLOW_UP_PENDING"
    assert "do not establish evaluation" in data["submission_boundary"].lower()

    for artifact in data["artifacts"]:
        path = ROOT / artifact["path"]
        assert path.is_file()
        assert _sha256(path) == artifact["sha256"]


def test_cdc_rfi_engagement_receipt_matches_gmail_and_attachment() -> None:
    data = json.loads(RECEIPT.read_text(encoding="utf-8"))
    attachment = data["submission"]["attachment"]
    attachment_path = ROOT / attachment["path"]

    assert data["opportunity"]["notice_id"] == "75D301-26-RFI-73483"
    assert data["submission"]["gmail_message_id"] == "19f6b1c3b60be492"
    assert data["acknowledgment"]["gmail_message_id"] == "19f6b22814477428"
    assert data["acknowledgment"]["status"] == "RECEIPT_CONFIRMED_FOLLOW_UP_PENDING"
    assert data["acknowledgment"]["reply_required"] is False
    assert attachment_path.stat().st_size == attachment["bytes"]
    assert _sha256(attachment_path) == attachment["sha256"]
    assert "receipt only" in data["claim_boundary"]


def test_cdc_rfi_pdf_is_two_pages_and_discloses_status() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pdf_record = next(item for item in data["artifacts"] if item["role"] == "send_ready_capability_statement")
    reader = PdfReader(ROOT / pdf_record["path"])
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert len(reader.pages) == 2
    assert "Prototype-stage / in development" in text
    assert "not represented as CDC validation" in text
    assert "autonomous acquisition decisions" in text
