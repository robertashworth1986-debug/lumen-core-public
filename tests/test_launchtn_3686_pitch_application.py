from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LAUNCHTN_3686_PITCH_APPLICATION.py"
MIRROR_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "LAUNCHTN_3686_PITCH_2026"
    / "LAUNCHTN_3686_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("launchtn_3686_pitch_application", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_manifest_matches_observed_launchtn_form_and_deadline():
    module = load_module()
    payload = module.build_payload("2026-07-17T12:00:00+00:00")

    expected_ids = {
        "company_name",
        "founder_names",
        "founder_phone",
        "founder_linkedin",
        "founder_email",
        "company_website",
        "company_address",
        "company_city",
        "company_state",
        "company_zip",
        "company_county",
        "additional_office",
        "formation_year",
        "company_structure",
        "tennessee_eligibility",
        "full_time_employees",
        "prior_launchtn_capital",
        "product_service",
        "problem_customer",
        "revenue_model",
        "go_to_market",
        "achievements",
        "business_model",
        "primary_product",
        "product_status",
        "industry_sectors",
        "pitch_deck",
        "financials",
        "other_attachment",
        "optional_note",
    }
    assert {row["field_id"] for row in payload["fields"]} == expected_ids
    assert payload["summary"]["field_count"] == 30
    assert payload["summary"]["required_field_count"] == 25
    assert payload["opportunity"]["application_deadline"] == "2026-08-13T23:59:00-05:00"
    assert payload["opportunity"]["cash_prize_usd"] == 10000
    assert payload["opportunity"]["formal_investtn_application"] is False
    assert payload["opportunity"]["portal_schema_status"] == (
        "OBSERVED_WITHOUT_SAVE_OR_SUBMIT_2026-07-17"
    )


def test_narratives_fit_limits_and_preserve_truth_boundaries():
    module = load_module()
    payload = module.build_payload("2026-07-17T12:00:00+00:00")
    by_id = {row["field_id"]: row for row in payload["fields"]}

    for field_id in (
        "product_service",
        "problem_customer",
        "revenue_model",
        "go_to_market",
        "achievements",
    ):
        row = by_id[field_id]
        assert row["within_character_limit"] is True
        assert row["character_count"] <= row["character_limit"]

    assert "Planned, not yet realized" in by_id["revenue_model"]["proposed_answer"]
    assert "no revenue or signed customer" in by_id["revenue_model"]["proposed_answer"]
    assert "not field or independent validation" in by_id["achievements"]["proposed_answer"]
    assert "not endorsements" in by_id["achievements"]["proposed_answer"]
    assert "go/no-go decision" in by_id["problem_customer"]["proposed_answer"]
    assert "guaranteed" not in " ".join(
        row["proposed_answer"].lower() for row in payload["fields"]
    )


def test_private_legal_and_financial_facts_remain_gated():
    module = load_module()
    payload = module.build_payload("2026-07-17T12:00:00+00:00")
    by_id = {row["field_id"]: row for row in payload["fields"]}

    for field_id in ("founder_phone", "founder_email", "company_address", "company_zip"):
        assert by_id[field_id]["status"] == "PRIVATE_PORTAL_ENTRY"
    for field_id in (
        "company_county",
        "formation_year",
        "company_structure",
        "full_time_employees",
        "prior_launchtn_capital",
    ):
        assert by_id[field_id]["status"] == "HUMAN_CONFIRM_REQUIRED"
    assert by_id["tennessee_eligibility"]["status"] == "HUMAN_ATTESTATION_REQUIRED"
    assert by_id["revenue_model"]["status"] == "FOUNDER_PRICING_APPROVAL_REQUIRED"
    assert by_id["pitch_deck"]["status"] == (
        "ATTACHMENT_QA_PASSED_FOUNDER_APPROVAL_REQUIRED"
    )
    assert by_id["financials"]["status"] == (
        "ATTACHMENT_QA_PASSED_FOUNDER_APPROVAL_REQUIRED"
    )
    assert payload["summary"]["final_submit_allowed_without_human"] is False
    assert payload["final_action_gate"]["submit_allowed_without_human"] is False


def test_observed_option_sets_and_recommended_focus_are_exact():
    module = load_module()
    payload = module.build_payload("2026-07-17T12:00:00+00:00")
    by_id = {row["field_id"]: row for row in payload["fields"]}

    assert payload["portal_options"]["business_model"] == ["B2B", "B2C", "D2C", "B2B2C", "Other"]
    assert "Limited Liability Corporation" in payload["portal_options"]["company_structure"]
    assert "My company is headquartered in TN" in payload["portal_options"]["tennessee_eligibility"]
    assert "AI / Machine Learning Tool" in payload["portal_options"]["primary_product"]
    assert "MVP development completed" in payload["portal_options"]["product_status"]
    assert "Data/AI/ML" in payload["portal_options"]["industry_sectors"]
    assert by_id["business_model"]["proposed_answer"] == "B2B"
    assert by_id["primary_product"]["proposed_answer"] == "AI / Machine Learning Tool"
    assert by_id["product_status"]["proposed_answer"] == "MVP development completed"
    assert by_id["industry_sectors"]["proposed_answer"] == (
        "Data/AI/ML; Advanced Energy/Battery Solutions"
    )


def test_attachment_requirements_and_source_receipts_are_auditable():
    module = load_module()
    payload = module.build_payload("2026-07-17T12:00:00+00:00")

    assert payload["summary"]["required_attachment_gates"] == 2
    assert {row["id"] for row in payload["required_attachments"]} == {
        "launchtn_pitch_deck",
        "launchtn_financial_model",
    }
    assert all(row["founder_approval_required"] for row in payload["required_attachments"])
    assert payload["summary"]["required_attachments_present"] == 2
    assert payload["summary"]["required_attachments_qa_passed"] == 2
    assert all(row["present"] for row in payload["required_attachments"])
    assert all(row["qa_hash_matches"] for row in payload["required_attachments"])
    assert all(
        row["status"] == "QA_PASSED_FOUNDER_APPROVAL_REQUIRED"
        for row in payload["required_attachments"]
    )
    assert all(
        row["sha256"] == row["expected_sha256"]
        for row in payload["required_attachments"]
    )
    assert all(row["qa_checks"] for row in payload["required_attachments"])
    assert all(row["present"] for row in payload["source_artifacts"].values())
    assert all(
        re.fullmatch(r"[0-9a-f]{64}", row["sha256"] or "")
        for row in payload["source_artifacts"].values()
    )
    assert re.fullmatch(r"[0-9a-f]{64}", payload["application_packet_sha256"])


def test_rendered_map_is_private_safe_and_final_action_gated():
    module = load_module()
    payload = module.build_payload("2026-07-17T12:00:00+00:00")
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Final submit without founder review: `false`" in rendered
    assert "HUMAN_FACTS_FOUNDER_APPROVAL_AND_FINAL_PREVIEW_REQUIRED" in rendered
    assert "This is not the formal InvestTN investment application" in rendered
    assert "@gmail.com" not in lowered
    assert re.search(r"\(\d{3}\)\s*\d{3}-\d{4}", rendered) is None
    assert "meeting id" not in lowered
    assert "passcode" not in lowered
    assert "api_key" not in lowered
    assert "permission to submit without a founder-reviewed final preview" in lowered


def test_launchtn_bounded_mirror_receipt_matches_source_and_e_drive():
    receipt = json.loads(MIRROR_RECEIPT.read_text(encoding="utf-8"))

    assert receipt["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 17
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["browser_navigation_performed"] is False
    assert receipt["private_founder_values_mirrored"] is False
    destination = Path(receipt["destination_root"])
    for artifact in receipt["artifacts"]:
        source = ROOT / artifact["source"]
        mirror = destination / source.name
        assert source.is_file(), artifact["source"]
        assert mirror.is_file(), str(mirror)
        assert source.stat().st_size == artifact["bytes"], artifact["source"]
        assert mirror.stat().st_size == artifact["bytes"], artifact["source"]
        assert hashlib.sha256(source.read_bytes()).hexdigest().upper() == artifact["sha256"]
        assert hashlib.sha256(mirror.read_bytes()).hexdigest().upper() == artifact["sha256"]
        assert artifact["copy_sha256_matched"] is True

    mirrored_sources = {artifact["source"] for artifact in receipt["artifacts"]}
    assert {
        "code/ops/BUILD_LAUNCHTN_3686_PITCH_APPLICATION.py",
        "tests/test_launchtn_3686_pitch_application.py",
        "grant_submissions/LAUNCHTN_3686_PITCH_2026/LAUNCHTN_3686_APPLICATION_MANIFEST_2026-07-17.json",
        "grant_submissions/LAUNCHTN_3686_PITCH_2026/LAUNCHTN_3686_PORTAL_FIELD_MAP_2026-07-17.md",
        "grant_submissions/LAUNCHTN_3686_PITCH_2026/LUMENCORE_3686_FINANCIAL_MODEL_2026-07-17.xlsx",
        "grant_submissions/LAUNCHTN_3686_PITCH_2026/LUMENCORE_3686_PITCH_DECK_2026-07-17.pptx",
        "code/ops/BUILD_EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER.py",
        "code/ops/BUILD_NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD.py",
    }.issubset(mirrored_sources)
    assert "does not prove submission" in receipt["claim_boundary"].lower()
