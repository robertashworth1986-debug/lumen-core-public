from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "VALIDATE_NASHVILLE_EC_PRIVATE_FACTS.py"
TEMPLATE = ROOT / "config" / "nashville_ec_private_facts_template_v1.json"
WORKFLOW = (
    ROOT
    / "grant_submissions"
    / "NASHVILLE_EC_FALL_2026"
    / "NASHVILLE_EC_PRIVATE_FACT_CAPTURE_WORKFLOW_2026-07-17.md"
)
MIRROR_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "NASHVILLE_EC_FALL_2026"
    / "NASHVILLE_EC_PRIVATE_FACT_CAPTURE_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("nashville_ec_private_facts", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def valid_zero_payload(module):
    return {
        "schema": module.SCHEMA,
        "first_time_founder": True,
        "business_age": "1 to 3 years",
        "full_time_on_lumencore": True,
        "weekly_hours_bracket": "30+",
        "conversation_bracket": "1 to 10",
        "zero_financials_confirmed": True,
        "financial_amounts_usd": None,
        "founder_cash_invested_usd": "40.00",
        "business_debt_usd": 0,
    }


def test_valid_private_facts_create_exact_eleven_question_map():
    module = load_module()
    result = module.validate_private_facts(valid_zero_payload(module))
    answers = {row["question_id"]: row["value"] for row in result["question_answers"]}

    assert result["schema"] == module.OUTPUT_SCHEMA
    assert result["status"] == "VALIDATED_PRIVATE_PORTAL_FILL_MAP"
    assert result["private_portal_only"] is True
    assert result["public_repo_publish_allowed"] is False
    assert result["question_answer_count"] == 11
    assert set(answers) == {
        28, 29, 31, 36, 38, 62, 63, 64, 65, 66, 84
    }
    assert answers[38] == "Yes"
    assert answers[29] == "30+"
    assert answers[84] == "1 to 10"
    assert all(answers[qid] == "$0" for qid in (66, 36, 63, 64, 65))
    assert answers[62] == "$40"
    assert result["final_action_gate"]["final_submission_authorized_at_action_time"] is False
    assert len(result["private_fill_map_sha256"]) == 64


def test_nonzero_financial_confirmation_requires_all_four_amounts():
    module = load_module()
    payload = valid_zero_payload(module)
    payload["zero_financials_confirmed"] = False

    with pytest.raises(ValueError, match="financial_amounts_usd is required"):
        module.validate_private_facts(payload)

    payload["financial_amounts_usd"] = {
        "previous_year_revenue_usd": "1,250.50",
        "trailing_12_month_revenue_usd": 0,
        "grant_funds_received_usd": "$500",
        "investor_capital_received_usd": 0,
    }
    result = module.validate_private_facts(payload)
    answers = {row["question_id"]: row["value"] for row in result["question_answers"]}
    assert answers[66] == "$1250.50"
    assert answers[36] == "$0"
    assert answers[63] == "$500"


def test_invalid_options_currency_and_zero_contradictions_fail_closed():
    module = load_module()
    payload = valid_zero_payload(module)
    payload["weekly_hours_bracket"] = "about 40"
    with pytest.raises(ValueError, match="weekly_hours_bracket"):
        module.validate_private_facts(payload)

    payload = valid_zero_payload(module)
    payload["founder_cash_invested_usd"] = "-1"
    with pytest.raises(ValueError, match=r"between \$0"):
        module.validate_private_facts(payload)

    payload = valid_zero_payload(module)
    payload["financial_amounts_usd"] = {"grant_funds_received_usd": 1}
    with pytest.raises(ValueError, match="cannot be true"):
        module.validate_private_facts(payload)


def test_incomplete_public_template_cannot_accidentally_validate():
    module = load_module()
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    with pytest.raises(ValueError):
        module.validate_private_facts(template)
    assert all(value is None for key, value in template.items() if key != "schema")


def test_private_output_boundary_and_workflow_are_enforced(tmp_path):
    module = load_module()
    public_repo_path = ROOT / "grant_submissions" / "NASHVILLE_EC_FALL_2026" / "facts.json"
    private_repo_path = module.PRIVATE_REPO_DIR / "facts.private.json"
    outside_repo_path = tmp_path / "facts.private.json"

    assert module.output_path_allowed(public_repo_path) is False
    assert module.output_path_allowed(private_repo_path) is True
    assert module.output_path_allowed(outside_repo_path) is True
    assert "grant_submissions/NASHVILLE_EC_FALL_2026/private/" in (
        ROOT / ".gitignore"
    ).read_text(encoding="utf-8")

    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "without placing the answers in public Git history" in workflow
    assert "refuses to write founder facts elsewhere inside the repository" in workflow
    assert "not authorized for publication" in workflow


def test_bounded_e_drive_mirror_contains_no_private_founder_values():
    receipt = json.loads(MIRROR_RECEIPT.read_text(encoding="utf-8-sig"))

    assert receipt["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 5
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["browser_navigation_performed"] is False
    assert receipt["private_founder_values_mirrored"] is False
    assert receipt["destination_root"].startswith("E:/LumaProofVault/")
    for artifact in receipt["artifacts"]:
        source = ROOT / artifact["source"]
        mirror = Path(artifact["destination"])
        assert source.is_file(), artifact["source"]
        assert mirror.is_file(), artifact["destination"]
        assert source.stat().st_size == mirror.stat().st_size == artifact["bytes"]
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest().upper()
        mirror_hash = hashlib.sha256(mirror.read_bytes()).hexdigest().upper()
        assert source_hash == mirror_hash == artifact["sha256"]
        assert artifact["copy_sha256_matched"] is True

    assert "mirrors no founder answer values" in receipt["claim_boundary"]
