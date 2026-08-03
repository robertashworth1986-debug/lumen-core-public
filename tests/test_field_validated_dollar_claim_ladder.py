from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_FIELD_VALIDATED_DOLLAR_CLAIM_LADDER.py"


def load_module():
    spec = importlib.util.spec_from_file_location("field_validated_dollar_claim_ladder", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_sector_math_uses_correct_basis_point_values():
    module = load_module()

    assert module.gross_value(1_000_000_000, 0.001) == 10_000
    assert module.windowed_value(10_000, 3) == 2_500
    assert module.gross_value(1_000_000_000, 0.01) == 100_000
    assert module.windowed_value(100_000, 3) == 25_000


def test_claim_ladder_zeros_every_current_model_outcome_value():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "field_validated_dollar_claim_ladder_v2"
    assert payload["direct_answer"]["can_claim_real_savings_right_now"] is False
    assert payload["direct_answer"]["can_claim_bounded_estimated_value_right_now"] is False
    assert payload["direct_answer"]["can_publish_modeled_dollar_projection_right_now"] is False
    assert payload["current_truth"]["current_performance_champion_present"] is False
    assert payload["current_truth"]["modeled_dollar_projection_allowed_now"] is False
    assert payload["current_truth"]["field_validated_savings_claim_allowed_now"] is False
    assert payload["current_truth"]["realized_customer_or_government_savings_allowed_now"] is False
    assert payload["current_truth"]["bounded_estimated_value_claim_allowed_now"] is False
    assert payload["current_truth"]["allowed_estimated_hourly_value_usd"] == 0
    assert payload["current_truth"]["allowed_estimated_annual_value_usd"] == 0
    assert payload["current_truth"]["allowed_realized_savings_usd"] == 0
    assert len(payload["claim_ladder_sha256"]) == 64


def test_service_pricing_is_separate_from_model_value_and_savings():
    module = load_module()
    payload = module.build_payload()
    pricing = payload["service_pricing"]

    assert payload["capture_from_current_safe_estimate"] == []
    assert pricing["paid_protocol_review_usd"]["low"] == 2500
    assert pricing["paid_protocol_review_usd"]["high"] == 7500
    assert pricing["benchmark_implementation_usd"]["low"] == 7500
    assert pricing["benchmark_implementation_usd"]["high"] == 25000
    assert pricing["service_price_is_model_outcome_value"] is False
    assert pricing["service_price_is_realized_savings"] is False
    assert pricing["service_price_is_enterprise_valuation"] is False


def test_public_language_is_fail_closed_and_explains_hypothetical_math():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    text = rendered.lower()

    assert "real savings claim right now: `false`" in text
    assert "field validated savings allowed now: `false`" in text
    assert "modeled dollar projection allowed now: `false`" in text
    assert "claimable annual model-outcome value: `$0.00`" in text
    assert "one percent of $1 billion is $10 million" in text
    assert "math only" in text
    assert "hash identity is custody evidence, not performance evidence" in text
    assert "$4,520" not in rendered
    assert "$39,595,200" not in rendered


def test_reference_candidate_is_negative_evidence_not_a_champion_or_request():
    module = load_module()
    payload = module.build_payload()
    family = payload["reference_candidate"]

    assert family["family_id"] == "kuramoto_phase_coupling"
    assert family["development_selected_candidate"] == "lissajous_phase_paths"
    assert family["candidate_was_protocol_selected"] is False
    assert family["wins_vs_named_baseline"] == 482
    assert family["holdout_count"] == 1525
    assert family["mean_delta_vs_named_baseline"] < 0
    assert family["ready_for_buyer_authorized_field_replay_request"] is False
    assert family["field_validation_claim_allowed"] is False
    assert family["real_dollar_savings_claim_allowed"] is False
    assert "not a performance champion" in family["plain_english"]
