from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_NASHVILLE_EC_FINANCIAL_AID_ACTION.py"
PUBLIC_JSON = (
    ROOT
    / "grant_submissions"
    / "NASHVILLE_EC_FALL_2026"
    / "NASHVILLE_EC_FINANCIAL_AID_ACTION_2026-07-20.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "nashville_ec_financial_aid_action", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def founder_facts(module):
    return {
        "schema": module.FOUNDER_FACTS_SCHEMA,
        "first_time_founder": True,
        "business_age": "1 to 3 years",
        "full_time_on_lumencore": True,
        "weekly_hours_bracket": "30+",
        "conversation_bracket": "1 to 10",
        "zero_financials_confirmed": True,
        "financial_amounts_usd": None,
        "founder_cash_invested_usd": 4321,
        "business_debt_usd": 987,
    }


def test_public_action_preserves_deadline_uncertainty_and_form_schema():
    module = load_module()
    payload = module.build_public_action()
    module.validate_public_action(payload)

    assert payload["status"] == "FINANCIAL_AID_FORM_REQUEST_RECEIVED_ACTION_OPEN"
    assert payload["deadline"]["date"] == "2026-07-22"
    assert payload["deadline"]["time"] is None
    assert payload["deadline"]["timezone"] is None
    assert payload["deadline"]["time_status"] == "NOT_STATED_IN_MESSAGE"
    assert payload["deadline"]["timezone_status"] == "NOT_STATED_IN_MESSAGE"
    assert payload["live_form_observation"]["required_identity_field_count"] == 2
    assert payload["live_form_observation"]["required_financial_question_count"] == 3
    assert payload["live_form_observation"]["optional_context_field_count"] == 1
    assert payload["live_form_observation"]["form_submitted_during_observation"] is False
    assert payload["routing"] == {
        "email_reply_required": False,
        "initial_application_resubmission_required": False,
        "financial_aid_form_action_required": True,
        "duplicate_application_send_allowed": False,
        "final_form_submit_human_gated": True,
        "builder_can_submit_form": False,
    }
    assert len(payload["action_receipt_sha256"]) == 64


def test_public_action_is_deterministic_and_matches_generated_artifact():
    module = load_module()
    first = module.build_public_action()
    second = module.build_public_action()
    actual = json.loads(PUBLIC_JSON.read_text(encoding="utf-8"))

    assert first == second == actual
    module.validate_public_action(actual)


def test_private_response_uses_confirmed_financial_classification():
    module = load_module()
    payload = module.build_private_response(
        founder_facts(module),
        fee_coverage="None of it",
        generated_utc="2026-07-20T23:40:00Z",
    )
    answers = {row["field"]: row for row in payload["answers"]}

    assert payload["status"] == "READY_FOR_FOUNDER_REVIEW_AND_SUBMIT"
    assert payload["private_portal_only"] is True
    assert payload["public_repo_publish_allowed"] is False
    assert answers["What is your current monthly revenue?"]["value_usd"] == 0
    assert (
        answers["Have you raised any outside capital in the last 12 months?"][
            "value"
        ]
        == "No"
    )
    assert payload["source_fact_summary"]["founder_cash_invested_usd"] == 4321
    assert payload["source_fact_summary"][
        "founder_cash_is_not_revenue_or_outside_capital"
    ] is True
    assert payload["final_action_gate"]["all_required_answers_assembled"] is True
    assert payload["final_action_gate"]["submission_performed"] is False
    assert len(payload["private_response_sha256"]) == 64


def test_fee_coverage_remains_human_gated_when_not_confirmed():
    module = load_module()
    payload = module.build_private_response(
        founder_facts(module), generated_utc="2026-07-20T23:40:00Z"
    )
    answers = {row["field"]: row for row in payload["answers"]}

    assert payload["status"] == "PROGRAM_FEE_COVERAGE_CONFIRMATION_REQUIRED"
    assert answers["How much of the program fee can you cover right now?"]["value"] == (
        "None of it"
    )
    assert answers["How much of the program fee can you cover right now?"]["status"] == (
        "FOUNDER_CONFIRMATION_REQUIRED"
    )
    assert payload["final_action_gate"]["program_fee_coverage_confirmed"] is False
    assert payload["final_action_gate"]["all_required_answers_assembled"] is False
    optional = answers["Anything about your situation you'd like us to know?"]
    assert optional["status"] == "PROGRAM_FEE_COVERAGE_CONFIRMATION_REQUIRED"
    assert "I cannot cover" not in optional["value"]


def test_invalid_financial_facts_and_fee_option_fail_closed():
    module = load_module()
    facts = founder_facts(module)
    facts["zero_financials_confirmed"] = False
    with pytest.raises(ValueError, match="require founder confirmation"):
        module.build_private_response(facts)

    with pytest.raises(ValueError, match="live form option"):
        module.build_private_response(
            founder_facts(module), fee_coverage="Almost all of it"
        )


def test_private_output_boundary_and_public_redaction(tmp_path):
    module = load_module()
    public_path = (
        ROOT
        / "grant_submissions"
        / "NASHVILLE_EC_FALL_2026"
        / "financial_answers.json"
    )
    private_path = module.PRIVATE_DIR / "financial_answers.private.json"
    assert module.private_output_allowed(public_path) is False
    assert module.private_output_allowed(private_path) is True
    assert module.private_output_allowed(tmp_path / "financial_answers.json") is True

    rendered = json.dumps(module.build_public_action(), sort_keys=True).lower()
    for forbidden in (
        "@gmail.com",
        "message_id",
        "thread_id",
        "crd8xtigpe7c4aeajf",
        "founder_cash_invested_usd",
        "business_debt_usd",
        "client_secret",
        "refresh_token",
        "api_key",
    ):
        assert forbidden not in rendered
