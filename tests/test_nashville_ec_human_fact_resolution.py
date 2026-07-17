from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_NASHVILLE_EC_HUMAN_FACT_RESOLUTION.py"


def load_module():
    spec = importlib.util.spec_from_file_location("nashville_ec_human_fact_resolution", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_resolution_collapses_eleven_fields_into_six_prompts():
    module = load_module()
    payload = module.build_payload("2026-07-16T23:59:00Z")

    assert payload["schema"] == "lumencore.nashville_ec_human_fact_resolution.v1"
    assert payload["status"] == "SIX_FOUNDER_CONFIRMATIONS_REQUIRED"
    assert payload["summary"]["required_human_portal_fields"] == 11
    assert payload["summary"]["evidence_supported_candidate_fields"] == 6
    assert payload["summary"]["founder_attestation_only_fields"] == 3
    assert payload["summary"]["private_accounting_fields"] == 2
    assert payload["summary"]["concise_confirmation_prompts"] == 6
    assert payload["summary"]["optional_demographics_may_be_skipped"] is True
    assert payload["summary"]["final_submit_allowed_without_live_preview"] is False


def test_age_and_conversation_candidates_are_bounded():
    module = load_module()
    payload = module.build_payload("2026-07-16T23:59:00Z")
    evidence = payload["evidence_observations"]

    assert evidence["business_age_floor"]["candidate"] == "1 to 3 years"
    assert evidence["business_age_floor"]["as_of_date"] == "2026-07-16"
    assert "does not prove" in evidence["business_age_floor"]["limit"]

    conversations = evidence["institutional_conversation_floor"]
    assert conversations["distinct_two_sided_human_threads"] == 14
    assert conversations["distinct_institutional_domains"] == 8
    assert conversations["candidate"].startswith("1 to 10 unless")
    assert conversations["conservative_fallback"] == "1 to 10"
    assert conversations["portal_options"] == ["0", "1 to 10", "11 to 25", "26 to 50", "50+"]
    assert "not proof of a customer" in conversations["limit"]

    live_form = evidence["live_form_schema"]
    assert live_form["saved_or_submitted"] is False
    assert live_form["weekly_hours_options"] == ["Less than 10", "10\u201320", "20\u201330", "30+"]


def test_financial_candidates_remain_founder_confirmed():
    module = load_module()
    payload = module.build_payload("2026-07-16T23:59:00Z")
    candidates = payload["candidate_answers"]

    zero_row = next(row for row in candidates if row["question_ids"] == [66, 36, 63, 64])
    assert zero_row["candidate"] == "$0 for each field"
    assert zero_row["status"] == "CONSISTENT_WITH_CLAIM_LEDGER_FOUNDER_CONFIRMATION"

    founder_cash = next(row for row in candidates if row["question_ids"] == [62])
    business_debt = next(row for row in candidates if row["question_ids"] == [65])
    assert founder_cash["candidate"] is None
    assert business_debt["candidate"] is None
    assert founder_cash["status"] == "PRIVATE_ACCOUNTING_TOTAL_REQUIRED"
    assert business_debt["status"] == "PRIVATE_ACCOUNTING_TOTAL_REQUIRED"


def test_rendered_resolution_is_concise_private_safe_and_send_gated():
    module = load_module()
    payload = module.build_payload("2026-07-16T23:59:00Z")
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Six-Line Founder Reply" in rendered
    assert "First-time founder: YES or NO" in rendered
    assert "business age:" in rendered
    assert "Discovery/sales conversation bracket: 0 / 1 to 10 / 11 to 25 / 26 to 50 / 50+" in rendered
    assert "6 to 10" not in rendered
    assert "Do not click final submit" in rendered
    assert "No candidate becomes a submitted fact" in rendered
    assert "full legal name:" not in lowered
    assert "signatory email:" not in lowered
    assert "street address" not in lowered
    assert "meeting id" not in lowered
    assert "passcode" not in lowered
    assert "zoom.us" not in lowered
    assert "api_key" not in lowered


def test_six_prompts_cover_every_human_required_question():
    module = load_module()
    payload = module.build_payload("2026-07-16T23:59:00Z")

    covered = {
        question_id
        for prompt in payload["confirmation_prompts"]
        for question_id in prompt["covers_question_ids"]
    }
    assert covered == module.REQUIRED_HUMAN_QUESTION_IDS
