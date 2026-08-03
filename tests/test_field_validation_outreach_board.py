from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_FIELD_VALIDATION_OUTREACH_BOARD.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "field_validation_outreach_board", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_opportunity_board_keeps_evidence_modes_and_source_breadth_distinct():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    snapshot = payload["proof_snapshot"]

    assert payload["schema"] == "field_validation_outreach_board_v2"
    assert summary["internal_performance_champion_present"] is False
    assert snapshot["current_champion"] is None
    assert snapshot["measured_reference_candidate"] == "kuramoto_phase_coupling"
    assert snapshot["development_selected_candidate"] == "lissajous_phase_paths"
    assert snapshot["reference_candidate_was_protocol_selected"] is False
    assert snapshot["holdout_wins"] == 482
    assert snapshot["holdout_count"] == 1525
    assert snapshot["mean_delta_vs_named_baseline"] == -0.508190706
    assert summary["compatible_route_count"] == 4
    assert summary["direct_measured_route_count"] == 2
    assert summary["conditioned_synthetic_route_count"] == 2
    assert summary["baseline_comparison_count"] == 22
    assert summary["global_holm_positive_count"] == 0
    assert summary["source_inventory_measured_count"] == 24
    assert summary["source_inventory_measured_rows"] == 17081
    assert summary["source_inventory_is_performance_evidence"] is False
    assert "research capacity" in snapshot["claim_boundary"]
    assert len(payload["outreach_board_sha256"]) == 64


def test_targets_remain_historical_research_candidates_not_send_routes():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    targets = payload["ranked_targets"]
    organizations = " ".join(row["organization"] for row in targets)

    assert summary["target_count"] == 5
    assert summary["send_ready_target_count"] == 0
    assert summary["recommended_first_buyer"] is None
    assert all(row["send_now_allowed"] is False for row in targets)
    assert all(
        row["source_freshness_status"]
        == "historical_reference_requires_action_time_official_verification"
        for row in targets
    )
    assert targets[0]["routing_status"] == "inbound_only_no_new_outreach"
    assert "EPRI" in organizations
    assert "EPB" in organizations
    assert "TVA" in organizations


def test_send_gate_and_commercial_offer_are_bounded():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    gate = payload["send_gate"]
    offer = payload["commercial_offer"]

    assert summary["paid_protocol_review_scoping_allowed"] is True
    assert summary["manual_reviewed_outreach_allowed"] is False
    assert summary["send_without_user_review_allowed"] is False
    assert summary["bulk_email_allowed"] is False
    assert summary["contact_scraping_allowed"] is False
    assert summary["field_validation_claim_allowed"] is False
    assert summary["realized_savings_claim_allowed"] is False
    assert summary["fixed_dollar_delta_claim_allowed"] is False

    assert gate["send_allowed"] is False
    assert gate["requires_current_official_source_verification"] is True
    assert gate["requires_duplicate_send_reconciliation"] is True
    assert gate["requires_exact_recipient"] is True
    assert gate["requires_exact_action_time_approval"] is True
    assert gate["epri_inbound_only"] is True
    assert gate["bulk_send_allowed"] is False

    assert offer["paid_protocol_review_usd"]["low"] == 2500
    assert offer["paid_protocol_review_usd"]["high"] == 7500
    assert offer["benchmark_implementation_usd"]["low"] == 7500
    assert offer["benchmark_implementation_usd"]["high"] == 25000
    assert offer["enterprise_valuation_asserted"] is False
    assert payload["draft_template"]["recipient_selected"] is False
    assert payload["draft_template"]["status"] == "draft_only_not_ready_to_send"


def test_board_is_secret_free_and_markdown_is_reviewer_safe():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()
    dumped = json.dumps(payload).lower()

    assert "Protocol Review Opportunity Board" in rendered
    assert "not a field-validation outreach authorization" in lowered
    assert "Current performance champion: `none`" in rendered
    assert "Paired-day wins: `482/1525`" in rendered
    assert "Mean skill delta: `-0.508190706`" in rendered
    assert "Global Holm promotions: `0`" in rendered
    assert "Source inventory: `24` measured sources / `17081` rows" in rendered
    assert "Priceable Offer" in rendered
    assert "Protocol review: `$2,500`-`$7,500`" in rendered
    assert "Send allowed: `false`" in rendered
    assert "EPRI inbound-only: `true`" in rendered
    assert "Bounded Draft Template" in rendered
    assert "Recipient selected: `false`" in rendered
    assert "24/24" not in rendered
    assert "2,506,267" not in rendered
    assert "current internal champion" not in lowered
    assert "plaintext_secret" not in dumped
    assert "private_key_material" not in dumped
