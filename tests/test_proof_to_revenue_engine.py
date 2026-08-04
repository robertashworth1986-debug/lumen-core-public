from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PROOF_TO_REVENUE_ENGINE.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "proof_to_revenue_engine", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_engine_separates_product_process_offer_from_model_performance():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    live_domain = json.loads(
        (
            ROOT
            / "out"
            / "ops"
            / "live_domain_deployment_feed_latest.json"
        ).read_text(encoding="utf-8")
    )
    live_summary = live_domain["summary"]

    assert payload["schema"] == "proof_to_revenue_engine_v3"
    assert summary["revenue_stage"] == (
        "bounded_offers_ready_local_only_domain_stale_recipient_selected_send_blocked"
    )
    assert summary["live_domain_hash_verified"] is False
    assert summary["required_remote_hash_matches"] == (
        live_summary["required_remote_hash_match_count"]
    )
    assert summary["required_feed_count"] == live_summary["required_feed_count"]
    assert summary["sellable_product_lane"] == "prooflock_opportunity_ops"
    assert summary["sellable_product_name"] == (
        "ProofLock Opportunity Operations"
    )
    assert summary["product_internal_evidence_gate_passed"] is True
    assert summary["product_buyer_readiness_gate_passed"] is False
    assert summary["product_process_scoping_allowed"] is True
    assert summary["internal_performance_champion_present"] is False
    assert summary["measured_reference_candidate"] == (
        "kuramoto_phase_coupling"
    )
    assert summary["development_selected_candidate"] == (
        "lissajous_phase_paths"
    )
    assert summary["reference_candidate_was_protocol_selected"] is False
    assert summary["internal_replay_holdout_wins"] == 482
    assert summary["internal_replay_holdout_count"] == 1525
    assert summary["internal_replay_mean_delta"] == -0.508191
    assert summary["cross_sector_benchmark_status"] == (
        "NO_CROSS_SECTOR_EFFICIENCY_GAIN_PROVEN"
    )
    assert summary["cross_sector_gain_proven_count"] == 0
    assert summary["cross_sector_efficiency_claim_allowed"] is False
    assert summary["model_performance_marketing_allowed"] is False


def test_engine_prices_only_bounded_services_and_keeps_outreach_closed():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    offers = payload["commercial_offers"]
    target = payload["target_status"]
    template = payload["safe_draft_template"]

    protocol = offers["source_native_protocol_review"]["price_usd"]
    benchmark = offers["benchmark_implementation"]["price_usd"]
    product = offers["product_process_discovery"]
    assert protocol["low"] == 3500
    assert protocol["high"] == 3500
    assert protocol["duration_business_days"] == 10
    assert protocol["status"] == "candidate_not_committed"
    assert protocol["founder_approved"] is False
    assert protocol["buyer_accepted"] is False
    assert benchmark["low"] == 7500
    assert benchmark["high"] == 25000
    assert product["product_process_scoping_allowed"] is True
    assert product["internal_evidence_gate_passed"] is True
    assert product["buyer_readiness_gate"]["passed"] is False
    assert product["validated_evidence_count"] == product["required_evidence_count"]
    assert product["external_outreach_ready"] is False
    assert product["model_performance_dependency"] is False
    assert product["pricing_status"] == "scope_before_quote_no_price_asserted"
    assert "$3,500-$3,500" not in template["body"]
    assert "candidate fee of $3,500" in template["body"]
    assert "subject to founder approval and written scope confirmation" in template["body"]

    assert summary["paid_protocol_review_scoping_allowed"] is True
    assert summary["pilot_ready_count"] == 0
    assert summary["manual_reviewed_outreach_allowed"] is False
    assert summary["external_outreach_ready"] is False
    assert summary["send_without_user_review_allowed"] is False
    assert summary["bulk_email_allowed"] is False
    assert summary["field_validation_claim_allowed"] is False
    assert summary["realized_savings_claim_allowed"] is False
    assert summary["fixed_frozen_delta_price_claim_allowed"] is False
    assert summary["enterprise_valuation_asserted"] is False
    assert summary["live_trading_or_autonomous_execution_allowed"] is False
    assert summary["safe_estimated_hourly_value_usd"] == 0
    assert summary["safe_estimated_annual_value_usd"] == 0
    assert summary["modeled_dollar_projection_allowed"] is False

    assert target["recipient_selected"] is True
    assert target["recommended_first_buyer"] == "PG&E Research and Development"
    assert target["packet_send_ready"] is False
    assert target["packet_send_gate"] == (
        "BLOCKED_BUSINESS_ADDRESS_AND_EXACT_ACTION_TIME_APPROVAL_REQUIRED"
    )
    assert target["legacy_paid_pilot_queue_excluded"] is True
    assert target["legacy_paid_pilot_queue_schema"] in {
        "paid_pilot_outreach_queue_v1",
        "paid_pilot_outreach_queue_v2",
    }
    assert payload["top_manual_targets"] == [
        {
            "organization": "PG&E Research and Development",
            "buyer_channel_type": "regulated_utility_research_and_innovation_channel",
            "routing_status": "verified_clean_route_action_time_approval_required",
            "send_now_allowed": False,
        }
    ]
    selected_packet = payload["selected_protocol_review_packet"]
    assert selected_packet["recipient_email"] == "innovation@pge.com"
    assert selected_packet["attachment_count"] == 0
    assert selected_packet["send_ready"] is False
    assert selected_packet["hashes_cover_placeholder_draft_only"] is True
    assert template["recipient_selected"] is False
    assert template["send_allowed"] is False
    assert template["status"] == "draft_only_no_recipient_not_ready_to_send"
    assert len(payload["proof_to_revenue_sha256"]) == 64


def test_engine_preserves_negative_model_evidence_and_safe_draft():
    module = load_module()
    payload = module.build_payload()
    evidence = payload["current_model_evidence"]
    template = payload["safe_draft_template"]
    dumped = json.dumps(payload).lower()

    assert evidence["candidate_family"] == "kuramoto_phase_coupling"
    assert evidence["development_selected_candidate"] == (
        "lissajous_phase_paths"
    )
    assert evidence["candidate_was_protocol_selected"] is False
    assert "482/1525" in evidence["direct_measured_result"]
    assert "mean skill -0.508191" in evidence["direct_measured_result"]
    assert evidence["sector_gain_proven_count"] == 0
    assert evidence["sector_count"] == 6
    assert evidence["external_cross_sector_replication_complete"] is False
    assert evidence["prospective_cross_sector_holdout_complete"] is False

    assert "not claiming guaranteed awards, model superiority" in template["body"]
    assert "human-controlled workflow" in template["body"]
    assert "realized savings" in dumped
    assert "fixed value per frozen delta" in dumped
    assert "cross-sector efficiency gain" in dumped
    assert "24/24" not in dumped
    assert "2,506,267" not in dumped


def test_proof_to_revenue_markdown_answers_current_questions():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)

    assert "Proof To Revenue Engine" in rendered
    assert "Current Model Evidence" in rendered
    assert "Bounded Commercial Offers" in rendered
    assert "Target Gate" in rendered
    assert "External Unlock" in rendered
    assert "What To Ask Next" in rendered
    assert "Proven sector gains: `0/6`" in rendered
    assert "Internal performance champion present: `false`" in rendered
    assert "Pilot-ready candidates: `0`" in rendered
    assert "Manual reviewed outreach allowed: `false`" in rendered
    assert "External outreach ready: `false`" in rendered
    assert "Modeled dollar projection allowed: `false`" in rendered
    assert (
        "Source-native protocol review candidate: `$3,500` fixed for `10` business days"
        in rendered
    )
    assert "Benchmark implementation: `$7,500`-`$25,000`" in rendered
    assert "Recipient selected: `true`" in rendered
    assert "Recommended first buyer: `PG&E Research and Development`" in rendered
    assert "Selected packet send ready: `false`" in rendered
    assert "Legacy paid-pilot queue excluded: `true`" in rendered
