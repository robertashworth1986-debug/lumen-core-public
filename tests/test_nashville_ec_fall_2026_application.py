from __future__ import annotations

import importlib.util
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_NASHVILLE_EC_FALL_2026_APPLICATION.py"


def load_module():
    spec = importlib.util.spec_from_file_location("nashville_ec_fall_2026", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_application_packet_covers_the_complete_extracted_form():
    module = load_module()
    payload = module.build_payload(generated_utc="2026-07-17T00:00:00+00:00")

    expected_ids = {
        3, 4, 75, 26, 6, 27, 76, 38, 28, 29, 96, 30, 31, 33, 60, 32, 34,
        35, 37, 84, 85, 95, 94, 88, 89, 66, 36, 62, 63, 64, 65, 61, 83, 82,
        81, 69, 80, 79, 73, 24, 90,
    }
    assert {row["question_id"] for row in payload["fields"]} == expected_ids
    assert payload["summary"]["field_count"] == len(expected_ids)
    assert payload["summary"]["required_field_count"] > 0
    assert payload["summary"]["portal_ready_except_human_facts"] is True
    assert payload["summary"]["final_submit_allowed_without_human"] is False
    assert payload["summary"]["accept_program_terms_allowed_without_human"] is False
    assert payload["summary"]["fee_commitment_allowed_without_human"] is False


def test_application_routes_to_takeoff_without_inventing_traction():
    module = load_module()
    payload = module.build_payload(generated_utc="2026-07-17T00:00:00+00:00")
    by_id = {row["question_id"]: row for row in payload["fields"]}

    assert payload["opportunity"]["recommended_route"] == "TakeOff"
    assert payload["opportunity"]["deadline_date"] == "2026-07-17"
    assert payload["opportunity"]["deadline_time"] is None
    assert payload["opportunity"]["deadline_time_status"] == "NOT_LISTED_ON_OFFICIAL_PAGE"
    assert payload["opportunity"]["operational_finish_target_status"] == (
        "INTERNAL_TARGET_NOT_OFFICIAL_DEADLINE"
    )
    assert payload["program_economics"]["application_fee"] is None
    assert payload["program_economics"]["application_fee_status"] == (
        "NOT_LISTED_ON_REVIEWED_OFFICIAL_PAGES"
    )
    assert payload["program_economics"]["takeoff_program_fee"] == 500
    assert payload["program_economics"]["takeoff_required_to_start"] == 125
    assert payload["program_economics"]["equity_taken"] == 0
    assert payload["program_economics"]["fee_commitment_authorized"] is False
    assert by_id[30]["proposed_answer"] == "I am building a prototype or MVP"
    assert by_id[34]["proposed_answer"] == "MVP built"
    assert by_id[35]["proposed_answer"] == "No"
    assert by_id[37]["proposed_answer"] == "1"
    assert by_id[29]["portal_options"] == ["Less than 10", "10\u201320", "20\u201330", "30+"]
    assert by_id[84]["portal_options"] == ["0", "1 to 10", "11 to 25", "26 to 50", "50+"]
    assert "1 to 10 unless" in by_id[84]["proposed_answer"]
    assert "6 to 10" not in by_id[84]["proposed_answer"]
    assert by_id[61]["proposed_answer"].startswith("No;")
    assert "not customer-result proof" in by_id[85]["proposed_answer"]
    assert "no paid customer or field validation is claimed" in by_id[89]["proposed_answer"]


def test_private_and_uncertain_answers_remain_human_gated():
    module = load_module()
    payload = module.build_payload(generated_utc="2026-07-17T00:00:00+00:00")
    by_id = {row["question_id"]: row for row in payload["fields"]}

    for question_id in (38, 28, 29, 31, 84, 66, 36, 62, 63, 64, 65):
        assert by_id[question_id]["status"] == "HUMAN_CONFIRM_REQUIRED"
    for question_id in (4, 75):
        assert by_id[question_id]["status"] == "PRIVATE_PORTAL_ENTRY"
    for question_id in (83, 82, 81, 69, 80, 79, 73):
        assert by_id[question_id]["status"] == "OPTIONAL_FOUNDER_CHOICE"

    rendered = module.render_markdown(payload)
    assert "@gmail.com" not in rendered
    assert re.search(r"\(\d{3}\)\s*\d{3}-\d{4}", rendered) is None
    assert "guaranteed" not in rendered.lower()
    assert "paying customer" in payload["claim_boundary"]
    assert len(payload["application_packet_sha256"]) == 64


def test_rendered_packet_preserves_sources_and_final_action_gate():
    module = load_module()
    payload = module.build_payload(generated_utc="2026-07-17T00:00:00+00:00")
    rendered = module.render_markdown(payload)

    assert "https://ec.co/apply/" in rendered
    assert "https://ec.co/accelerators/takeoff/" in rendered
    assert "HUMAN_REVIEW_AND_SUBMIT_REQUIRED" in rendered
    assert "Do not accept program fees" in rendered
    assert "Final submit without human: `false`" in rendered
    assert "Verified portal options: 0; 1 to 10; 11 to 25; 26 to 50; 50+" in rendered
