from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_FIRST_BUYER_TARGET_BOARD.py"


def load_module():
    spec = importlib.util.spec_from_file_location("first_buyer_target_board", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_first_buyer_board_selects_manual_buyer_lane_not_overclaims():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "first_buyer_target_board_v3"
    assert summary["recommended_first_buyer"] == "PG&E Research and Development"
    assert summary["current_official_source_verified_count"] == 3
    assert summary["recipient_selected_count"] == 1
    assert summary["exact_packet_prepared_count"] == 1
    assert summary["send_ready_target_count"] == 0
    assert summary["manual_reviewed_outreach_allowed"] is False
    assert summary["paid_protocol_review_scoping_allowed"] is True
    assert summary["send_without_user_review_allowed"] is False
    assert summary["bulk_email_allowed"] is False
    assert summary["contact_scraping_allowed"] is False
    assert summary["field_validation_claim_allowed"] is False
    assert summary["realized_savings_claim_allowed"] is False
    assert summary["fixed_frozen_delta_price_claim_allowed"] is False
    assert summary["proof_internal_performance_champion_present"] is False
    assert summary["proof_holdout_wins"] < summary["proof_holdout_count"] / 2
    assert summary["proof_locked_global_holm_positive_count"] == 0
    assert summary["proof_legacy_ready_rows_excluded"] >= 300
    assert summary["proof_numeric_fallback_profile_count"] == 0
    assert len(payload["first_buyer_board_sha256"]) == 64


def test_first_buyer_board_has_ranked_sources_and_safe_manual_email():
    module = load_module()
    payload = module.build_payload()
    candidates = payload["candidates"]
    email = payload["primary_manual_email"]

    assert len(candidates) == 3
    assert all(candidate["manual_review_required"] for candidate in candidates)
    assert all(not candidate["send_now_allowed"] for candidate in candidates)
    assert candidates[0]["organization"] == "PG&E Research and Development"
    assert candidates[1]["organization"] == "Southern Company New Ventures"
    assert candidates[2]["organization"] == "Exelon Foundation 2c2i"
    assert not any("EPB" in candidate["organization"] for candidate in candidates)
    assert not any("TVA" in candidate["organization"] for candidate in candidates)
    assert email["recipient_email"] == "innovation@pge.com"
    assert email["candidate_fee_usd"] == 3500
    assert email["candidate_duration_business_days"] == 10
    assert email["attachment_count"] == 0
    assert email["cc"] == []
    assert email["bcc"] == []
    assert email["subject_sha256"] == module.text_sha256(email["subject"])
    assert email["body_sha256"] == module.text_sha256(email["body"])
    assert len(email["packet_sha256"]) == 64
    assert email["hashes_cover_placeholder_draft_only"] is True
    assert email["send_ready"] is False
    assert email["send_mode"] == "draft_only_missing_compliance_fact_and_action_time_approval"
    assert "FOUNDER-APPROVED BUSINESS MAILING ADDRESS REQUIRED" in email["body"]
    assert "not a claim of field performance, savings" in email["body"]
    assert candidates[0]["routing_status"] == "verified_clean_route_action_time_approval_required"
    assert candidates[1]["routing_status"] == "official_contact_route_recipient_unresolved_no_email_send"
    assert candidates[1]["public_contact_route"]["address"].endswith("/contact-us.html")
    assert "g2newventures" not in json.dumps(payload).lower()
    exclusions = payload["excluded_historical_routes"]
    assert any(
        item["organization"] == "EPB Chattanooga"
        and item["relevant_prior_outbound_count"] == 4
        for item in exclusions
    )
    assert any(
        item["organization"] == "TVA / Spark Cleantech"
        and item["relevant_prior_outbound_count"] == 3
        for item in exclusions
    )
    dumped = json.dumps(payload).lower()
    assert "bulk_email_allowed" in dumped
    assert '"bulk_email_allowed": false' in dumped
    assert "guaranteed profit" not in dumped
    assert "guaranteed award" not in dumped


def test_first_buyer_markdown_is_reviewer_safe():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)

    assert "First Buyer Target Board" in rendered
    assert "First buyer channel" in rendered
    assert "Send without user review: `false`" in rendered
    assert "Field-validation claim allowed: `false`" in rendered
    assert "Realized-savings claim allowed: `false`" in rendered
    assert "First buyer channel: `PG&E Research and Development`" in rendered
    assert "Current official sources verified: `3`" in rendered
    assert "Send-ready packets: `0`" in rendered
    assert "## Excluded Historical Routes" in rendered
    assert "EPB Chattanooga" in rendered
    assert "TVA / Spark Cleantech" in rendered
    assert "## Selected Draft Packet" in rendered
    assert "Attachments: `0`" in rendered
    assert "Placeholder-draft hashes only: `true`" in rendered
    assert "Send ready: `false`" in rendered
    assert "Subject SHA-256" in rendered
    assert "Body SHA-256" in rendered
    assert "Internal performance champion present: `false`" in rendered
    assert "current internal champion" not in rendered.lower()
