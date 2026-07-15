import hashlib
import json
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "grant_submissions" / "funding_sprint_20260709" / "CDC_AI_ACQUISITION_RFI_ARTIFACT_MANIFEST_2026-07-15.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def test_cdc_rfi_manifest_hashes_and_boundaries() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["submission_state"] == "GMAIL_DRAFT_READY_NOT_SENT"
    assert "does not establish transmission" in data["submission_boundary"]

    for artifact in data["artifacts"]:
        path = ROOT / artifact["path"]
        assert path.is_file()
        assert _sha256(path) == artifact["sha256"]


def test_cdc_rfi_pdf_is_two_pages_and_discloses_status() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pdf_record = next(item for item in data["artifacts"] if item["role"] == "send_ready_capability_statement")
    reader = PdfReader(ROOT / pdf_record["path"])
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert len(reader.pages) == 2
    assert "Prototype-stage / in development" in text
    assert "not represented as CDC validation" in text
    assert "autonomous acquisition decisions" in text
