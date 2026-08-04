from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT / "code" / "ops" / "BUILD_VALUATION_PROPOSAL_TARGET_PACKET.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "valuation_proposal_target_packet", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_valuation_packet_prices_service_not_failed_candidate_performance():
    module = load_module()
    payload = module.build_payload()
    overall = payload["overall_locked_sweep_stats"]
    target = payload["recommended_first_proposal_target"]
    valuation = payload["valuation_state"]
    truth = payload["current_truth"]

    assert payload["schema"] == "valuation_proposal_target_packet_v3"
    assert truth["internal_performance_champion_present"] is False
    assert truth["reference_candidate"] == "kuramoto_phase_coupling"
    assert truth["reference_candidate_was_protocol_selected"] is False
    assert truth["reference_candidate_cleared_all_baselines"] is False
    assert truth["reference_mean_delta_vs_named_baseline"] < 0

    assert overall["adapter_backed_route_count"] == 4
    assert overall["direct_measured_route_count"] == 2
    assert overall["source_conditioned_route_count"] == 2
    assert overall["baseline_comparison_count"] == 22
    assert overall["global_holm_positive_count"] == 0
    assert overall["promoted_candidate_count"] == 0
    assert overall["legacy_ready_rows_excluded"] >= 300
    assert overall["numeric_fallback_profiles_used"] == 0

    assert valuation["enterprise_valuation_asserted"] is False
    assert valuation["defensible_money_status"].startswith(
        "Price paid technical evaluation"
    )
    assert (
        target["target_name"]
        == "Source-Native Benchmark and Evidence Protocol Review"
    )
    assert "paid protocol" in target["proposal_ask"]
    assert (
        target["paid_review_scope_usd"]["status"]
        == "candidate_not_committed"
    )
    assert target["paid_review_scope_usd"]["low"] == 3500
    assert target["paid_review_scope_usd"]["high"] == 3500
    assert target["paid_review_scope_usd"]["duration_business_days"] == 10
    assert target["paid_review_scope_usd"]["founder_approved"] is False
    assert target["paid_review_scope_usd"]["buyer_accepted"] is False
    assert target["optional_benchmark_build_usd"]["low"] == 7500
    assert target["optional_benchmark_build_usd"]["high"] == 25000
    assert payload["inputs"]["hypercore_v8_commercial_boundary"] == (
        "config/hypercore_v8_validation_protocol_v1.json"
    )
    assert len(
        payload["input_sha256"]["config/hypercore_v8_validation_protocol_v1.json"]
    ) == 64


def test_valuation_packet_closes_performance_and_value_claims():
    module = load_module()
    payload = module.build_payload()
    gates = payload["claim_gates"]
    rendered = module.render_markdown(payload)
    dumped = json.dumps(payload).lower()

    assert gates["paid_protocol_review_scoping_allowed"] is True
    assert gates["buyer_authorized_field_replay_request_ready"] is False
    assert gates["bounded_estimated_value_claim_allowed"] is False
    assert gates["field_validation_claim_allowed"] is False
    assert gates["real_dollar_savings_claim_allowed"] is False
    assert gates["fixed_dollar_delta_sale_claim_allowed"] is False
    assert gates["live_trading_or_autonomous_execution_allowed"] is False
    assert gates["medical_or_treatment_claim_allowed"] is False
    assert gates["grant_award_certainty_allowed"] is False

    assert "Defensible Money State" in rendered
    assert "Reviewer-Safe Proposal Blurb" in rendered
    assert "Enterprise valuation asserted: `false`" in rendered
    assert "realized savings" in dumped
    assert "guaranteed roi allowed" not in dumped
