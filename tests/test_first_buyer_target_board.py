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

    assert payload["schema"] == "first_buyer_target_board_v1"
    assert summary["recommended_first_buyer"] == "EPRI AI for Power / Incubatenergy Labs"
    assert summary["manual_reviewed_outreach_allowed"] is True
    assert summary["send_without_user_review_allowed"] is False
    assert summary["bulk_email_allowed"] is False
    assert summary["contact_scraping_allowed"] is False
    assert summary["field_validation_claim_allowed"] is False
    assert summary["realized_savings_claim_allowed"] is False
    assert summary["fixed_frozen_delta_price_claim_allowed"] is False
    assert summary["proof_holdout_wins"] >= 20
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
    assert "field validation or realized savings yet" in email["body"]
    assert email["send_mode"] == "manual_review_only"
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
    assert "EPRI AI for Power / Incubatenergy Labs" in rendered
