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
    assert sources["manifest_schema"] == "lumencore.erdc_sdc_source_manifest.v2"
    assert sources["manifest_as_of_date"] == "2026-07-29"
    assert sources["current_attachment_set_complete"] is True
    assert sources["source_custody_schema"] == "lumencore.erdc_sdc_source_custody.v1"
    assert sources["source_custody_checks_pass"] is True
    assert len(sources["custody_sources"]) == 2
    assert sources["live_page_snapshot"]["route"] == "COMMERCIAL_SOLUTION"
    assert sources["live_page_snapshot"]["deadline_text"] == (
        "4:00 pm CT on August 7, 2026"
    )
    assert len(sources["files"]) == 2
    assert {row["actual_pages"] for row in sources["files"]} == {7, 13}
    for row in sources["files"]:
        assert row["sha256_match"] is True
        assert row["bytes_match"] is True
        assert row["page_count_match"] is True
        assert row["official_url"].startswith("https://www.erdcwerx.org/")


def test_evidence_ablation_receipt_binds_current_bounded_experiment():
    module = load_module()
    evidence = module.evidence_ablation_receipt()

    assert evidence["receipt_checks_pass"] is True
    assert evidence["schema"] == "lumencore.erdc_sdc_evidence_ablation.v2"
    assert evidence["workflow_count"] == 48
    assert evidence["full_attack_detected_count"] == 7
    assert evidence["full_attack_case_count"] == 7
    assert evidence["full_adverse_outcome_recall"] == 1.0
    assert evidence["full_artifact_bytes_rehash_rate"] == 1.0
    assert evidence["full_predeclared_gate_execution_pass"] is True
    assert evidence["full_posthoc_promotion_change_detected"] is True
    assert evidence["promotion_or_performance_claim_allowed"] is False
    assert evidence["opentelemetry_version"] == "1.59.0"
    assert evidence["slsa_version"] == "1.2"
    assert len(evidence["sha256"]) == 64


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
    assert pdf["all_detected_content_text_12_point"] is True
    assert pdf["minimum_detected_font_size"] >= 12
    assert pdf["maximum_detected_content_font_size"] <= 12.1
    assert pdf["times_new_roman_detected"] is True
    assert pdf["all_physical_page_labels_present"] is True
    assert pdf["body_page_labels_present"] is True
    assert pdf["draft_watermark_present_every_page"] is True
    assert pdf["required_content_markers_present"] is True
    assert pdf["required_acronym_entries_present"] is True
    assert pdf["evidence_ablation_marker_present"] is True
    assert 0 < pdf["bytes"] < 20 * 1024 * 1024
    assert len(pdf["sha256"]) == 64


def test_compliance_gate_passes_document_controls_but_blocks_submission():
    module = load_module()
    payload = module.build_payload(module.inspect_pdf(), module.source_integrity())
    rows = {row["id"]: row for row in payload["requirements"]}

    assert payload["status"] == (
        "CURRENT_PUBLIC_DRAFT_FORMAT_AND_MARKER_CHECKS_PASS_SEMANTIC_EVIDENCE_AND_PRIVATE_FINALIZATION_REQUIRED"
    )
    assert payload["format_and_marker_checks_pass"] is True
    assert payload["semantic_review_complete"] is False
    assert payload["submission_ready"] is False
    assert payload["funding_currently_available"] is False
    assert payload["deadline"]["safest_operational_cutoff"] == (
        "4:00 PM CT on August 7, 2026"
    )
    assert payload["deadline"]["controlling_cso_pdf_text"] == (
        "1700 EST, 07 AUG 2026"
    )
    assert payload["deadline"]["current_live_page_text"] == (
        "4:00 PM CT on August 7, 2026"
    )
    assert payload["deadline"]["question_submission_cutoff"] == "July 31, 2026"
    assert rows["ROM_01"]["status"] == "PRIVATE_FINALIZATION_REQUIRED"
    assert rows["EXEC_01"]["status"] == "PRIVATE_FINALIZATION_REQUIRED"
    assert rows["SAM_01"]["status"] == "PRIVATE_FINALIZATION_REQUIRED"
    assert rows["CONTACT_01"]["status"] == "PRIVATE_FINALIZATION_REQUIRED"
    assert rows["ACCOUNT_01"]["status"] == "HUMAN_ACCOUNT_ACCESS_REQUIRED"
    assert rows["PORTAL_01"]["status"] == "HUMAN_FINAL_ACTION_REQUIRED"
    for row_id in ("FAQ_03", "FAQ_04", "FAQ_05", "FAQ_06"):
        assert rows[row_id]["status"] == "PASS_BOUNDED"
    assert rows["FORMAT_04"]["status"] == "PASS"
    assert rows["DISCLOSURE_01"]["status"] == "PASS"
    assert payload["summary"]["external_send_allowed_without_human"] is False
    assert payload["summary"]["final_portal_submit_allowed_without_human"] is False
    assert payload["summary"]["pricing_allowed_without_founder_approval"] is False
    assert payload["summary"]["legal_identity_publish_allowed"] is False
    assert payload["summary"]["browser_navigation_performed"] is False
    assert rows["BASELINE_01"]["status"] == "PASS_BOUNDED"
    assert rows["ABLATION_01"]["status"] == "PASS_BOUNDED"
    assert rows["TECH_03"]["status"] == "LOCAL_ONLY_EXTERNAL_REPRODUCIBILITY_REQUIRED"
    assert rows["TRUST_01"]["status"] == "EXTERNAL_TRUST_ROOT_REQUIRED"
    assert rows["METRIC_01"]["status"] == "PASS_BOUNDED"
    assert payload["evidence_ablation"]["receipt_checks_pass"] is True


def test_public_draft_contains_no_private_or_unsupported_claim_markers():
    module = load_module()
    text = "\n".join(page.extract_text() or "" for page in module.PdfReader(str(module.OUT_PDF)).pages)
    lowered = text.lower()
    normalized = re.sub(r"\s+", " ", lowered)

    assert "funding is not currently available" in normalized
    assert "customers, revenue, or realized savings" in normalized
    assert "48 deterministic synthetic workflows" in normalized
    assert "detected 7/7 declared tamper cases" in normalized
    assert "separately pinned local anchor" in normalized
    assert "opentelemetry logs data model 1.59.0" in normalized
    assert "slsa build provenance 1.2" in normalized
    assert "complementary interoperability contexts, not ranked competitors" in normalized
    assert "not an hpcmp workload" in normalized
    assert "not a superiority claim" in normalized
    assert "exact july 29 receipt remains local" in normalized
    assert "140 registered families" not in normalized
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
    assert payload["evidence_ablation"]["receipt_checks_pass"] is True
    assert payload["pdf"]["evidence_ablation_marker_present"] is True
    assert payload["submission_ready"] is False
    assert "not submission-ready" in rendered
    assert "Phase II price and execution commitments" in rendered
    assert "private SAM/contact facts" in rendered
    assert "authenticated portal form" in rendered
    assert "does not claim" in payload["claim_boundary"]
    assert len(payload["gate_sha256"]) == 64


def test_historical_public_mirror_receipt_is_not_current_after_refresh():
    receipt = json.loads(MIRROR_RECEIPT.read_text(encoding="utf-8"))

    assert receipt["artifact_count"] == 6
    assert receipt["all_copies_sha256_matched"] is True
    assert receipt["submission_ready"] is False
    assert receipt["browser_navigation_performed"] is False
    assert len(receipt["required_private_finalization"]) == 3
    historical_paths = {artifact["c_path"] for artifact in receipt["artifacts"]}
    assert not any("2026-07-29" in path for path in historical_paths)
    assert (
        "grant_submissions/funding_sprint_20260709/source_attachments/"
        "W912HZ26SC005/SOURCE_MANIFEST_2026-07-16.json"
    ) in historical_paths
    assert (
        "grant_submissions/funding_sprint_20260709/source_attachments/"
        "W912HZ26SC005/SOURCE_MANIFEST_2026-07-29.json"
    ) not in historical_paths
