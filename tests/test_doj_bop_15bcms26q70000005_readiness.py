from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "grant_submissions" / "DOJ_BOP_15BCMS26Q70000005"
MANIFEST = PACKAGE / "DOJ_BOP_15BCMS26Q70000005_SOURCE_MANIFEST_2026-07-16.json"
DECISION = PACKAGE / "DOJ_BOP_15BCMS26Q70000005_GO_NO_GO_2026-07-16.md"
OUTREACH = PACKAGE / "DOJ_BOP_15BCMS26Q70000005_PARTNER_OUTREACH_TEMPLATE_2026-07-16.md"
SYNC_RECEIPT = PACKAGE / "DOJ_BOP_AND_CDC_E_DRIVE_SYNC_RECEIPT_2026-07-16.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def test_official_source_bundle_is_complete_and_hash_locked() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["solicitation"]["notice_id"] == "15BCMS26Q70000005"
    assert data["solicitation"]["latest_revision_uuid"] == "52680f2a89c241b3a055c35d816b7f20"
    assert data["solicitation"]["offer_deadline_official_text"] == "07/23/2026 11:00 ET"
    assert data["custody"]["all_metadata_sizes_match_downloaded_files"] is True

    records = [data["source_bundle"], *data["attachments"]]
    for record in records:
        path = ROOT / record["path"]
        assert path.is_file()
        assert path.stat().st_size == record["bytes"]
        assert _sha256(path) == record["sha256"]

    assert {item["name"] for item in data["attachments"]} == {
        "15BCMS26Q70000005 Historical Medical Claims Data Analysis.pdf",
        "15BCMS26Q70000005 Mod 001.pdf",
        "Sample Data.xlsx",
    }


def test_decision_preserves_hard_compliance_and_human_gates() -> None:
    text = DECISION.read_text(encoding="utf-8")

    assert "Solo-prime posture: `NO_GO`" in text
    assert "Partner posture: `CONDITIONAL_GO_ONLY_IF_ALL_HARD_GATES_CLOSE`" in text
    assert "Final email state: `DO_NOT_SEND`" in text
    assert "HIPAA compliance officer" in text
    assert "HSPD-12" in text
    assert "FIPS 140-2" in text
    assert "ATO/ATT" in text
    assert "firm-fixed price" in text.lower()
    assert "neutral evaluation" in text
    assert "does not claim HIPAA compliance" in text


def test_partner_template_is_bounded_and_not_send_ready() -> None:
    text = OUTREACH.read_text(encoding="utf-8")

    assert "Status: `DRAFT_NOT_SENT`" in text
    assert "We are not representing LumenCore as HIPAA compliant" in text
    assert "No government data is in our possession" in text
    assert "Obtain action-time approval before sending" in text
    assert "[Name]" in text
    assert "[Organization]" in text


def test_e_drive_sync_receipt_is_bounded_and_manifest_linked() -> None:
    data = json.loads(SYNC_RECEIPT.read_text(encoding="utf-8"))
    packages = {item["name"]: item for item in data["packages"]}

    assert data["vault_root"] == "E:\\LumaProofVault\\SUBMISSIONS"
    assert packages["DOJ_BOP_15BCMS26Q70000005"]["artifact_count"] == 7
    assert packages["DOJ_BOP_15BCMS26Q70000005"]["hash_matches"] == 7
    assert packages["CDC_AI_ACQUISITION_RFI_75D301"]["artifact_count"] == 5
    assert packages["CDC_AI_ACQUISITION_RFI_75D301"]["hash_matches"] == 5
    assert packages["DOJ_BOP_15BCMS26Q70000005"]["source_manifest_sha256"] == _sha256(MANIFEST)
    assert "mirror integrity only" in data["claim_boundary"]
