from __future__ import annotations

import importlib.util
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_ERDC_SDC_SOLUTION_BRIEF.py"
MIRROR_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "ERDC_SDC_PUBLIC_MIRROR_RECEIPT_2026-07-17.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_module():
    spec = importlib.util.spec_from_file_location("erdc_sdc_solution_brief", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_source_pdfs_match_the_official_manifest():
    module = load_module()
    sources = module.source_integrity()

    assert sources["all_source_checks_pass"] is True
    assert len(sources["files"]) == 2
    assert {row["actual_pages"] for row in sources["files"]} == {6, 7}
    for row in sources["files"]:
        assert row["sha256_match"] is True
        assert row["bytes_match"] is True
        assert row["page_count_match"] is True
        assert row["official_url"].startswith("https://www.erdcwerx.org/")


def test_generated_pdf_meets_body_page_font_size_and_file_controls():
    module = load_module()
    pdf = module.inspect_pdf()

    assert pdf["exists"] is True
    assert pdf["physical_page_count"] == 7
    assert pdf["cover_pages"] == 1
    assert pdf["acronym_pages"] == 1
    assert pdf["body_page_count"] == 5
    assert pdf["all_pages_letter_portrait"] is True
    assert pdf["all_non_watermark_text_within_one_inch_margins"] is True
    assert pdf["all_detected_text_at_least_12_point"] is True
    assert pdf["minimum_detected_font_size"] >= 12
    assert pdf["times_new_roman_detected"] is True
    assert pdf["body_page_labels_present"] is True
    assert pdf["draft_watermark_present_every_page"] is True
    assert pdf["required_content_markers_present"] is True
    assert 0 < pdf["bytes"] < 20 * 1024 * 1024
    assert len(pdf["sha256"]) == 64


def test_compliance_gate_passes_document_controls_but_blocks_submission():
    module = load_module()
    payload = module.build_payload(module.inspect_pdf(), module.source_integrity())
    rows = {row["id"]: row for row in payload["requirements"]}

    assert payload["status"] == (
        "TECHNICAL_DRAFT_PASS_PRIVATE_ROM_AND_SAM_FINALIZATION_REQUIRED"
    )
    assert payload["technical_document_checks_pass"] is True
    assert payload["submission_ready"] is False
    assert payload["funding_currently_available"] is False
    assert payload["deadline"]["official_live_page_text"] == (
        "4:00 PM CT on August 7, 2026"
    )
    assert rows["ROM_01"]["status"] == "PRIVATE_FINALIZATION_REQUIRED"
    assert rows["SAM_01"]["status"] == "PRIVATE_FINALIZATION_REQUIRED"
    assert rows["PORTAL_01"]["status"] == "HUMAN_FINAL_ACTION_REQUIRED"
    assert rows["FORMAT_04"]["status"] == "PASS"
    assert rows["DISCLOSURE_01"]["status"] == "PASS"
    assert payload["summary"]["external_send_allowed_without_human"] is False
    assert payload["summary"]["final_portal_submit_allowed_without_human"] is False
    assert payload["summary"]["pricing_allowed_without_founder_approval"] is False
    assert payload["summary"]["legal_identity_publish_allowed"] is False
    assert payload["summary"]["browser_navigation_performed"] is False


def test_public_draft_contains_no_private_or_unsupported_claim_markers():
    module = load_module()
    text = "\n".join(page.extract_text() or "" for page in module.PdfReader(str(module.OUT_PDF)).pages)
    lowered = text.lower()
    normalized = re.sub(r"\s+", " ", lowered)

    assert "funding is not currently available" in normalized
    assert "no open-market customer deployment is claimed" in normalized
    assert "no classified handling" in normalized
    assert "does not claim" in normalized
    assert "not for submission" in normalized
    assert re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I) is None
    assert re.search(r"\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b", text) is None
    assert "meeting id" not in lowered
    assert "passcode" not in lowered
    assert "api key" not in lowered
    assert "guaranteed award" not in lowered


def test_written_gate_matches_current_pdf_and_is_claim_bounded():
    module = load_module()
    payload = json.loads(module.OUT_JSON.read_text(encoding="utf-8"))
    rendered = module.OUT_MD.read_text(encoding="utf-8")

    assert payload["pdf"]["sha256"] == module.sha256_file(module.OUT_PDF)
    assert payload["source_integrity"]["all_source_checks_pass"] is True
    assert payload["submission_ready"] is False
    assert "not submission-ready" in rendered
    assert "Phase II-only price" in rendered
    assert "private SAM-matched legal identity/address" in rendered
    assert "does not claim" in payload["claim_boundary"]
    assert len(payload["gate_sha256"]) == 64


def test_public_mirror_receipt_binds_current_c_drive_artifacts():
    receipt = json.loads(MIRROR_RECEIPT.read_text(encoding="utf-8"))

    assert receipt["artifact_count"] == 6
    assert receipt["all_copies_sha256_matched"] is True
    assert receipt["submission_ready"] is False
    assert receipt["browser_navigation_performed"] is False
    assert len(receipt["required_private_finalization"]) == 3
    for artifact in receipt["artifacts"]:
        path = ROOT / artifact["c_path"]
        assert path.is_file()
        assert path.stat().st_size == artifact["bytes"]
        assert sha256_file(path) == artifact["sha256"]
