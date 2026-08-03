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

    assert payload["schema"] == "first_buyer_target_board_v2"
    assert summary["recommended_first_buyer"] is None
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

    assert len(candidates) >= 5
    assert candidates[0]["fit_score"] >= candidates[1]["fit_score"]
    assert all(candidate["manual_review_required"] for candidate in candidates)
    assert all(not candidate["send_now_allowed"] for candidate in candidates)
    assert any("EPB" in candidate["organization"] for candidate in candidates)
    assert any("TVA" in candidate["organization"] for candidate in candidates)
    assert "current measured result is deliberately a negative one" in email["body"]
    assert "not a claim that this candidate wins" in email["body"]
    assert email["send_mode"] == "draft_only_not_ready_to_send"
    assert candidates[0]["routing_status"] == "inbound_only_no_new_outreach"
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
    assert "First buyer channel: `None`" in rendered
    assert "Internal performance champion present: `false`" in rendered
    assert "current internal champion" not in rendered.lower()
