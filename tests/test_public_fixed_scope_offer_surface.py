from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "dashboard" / "proof_to_pilot.html"
OFFER = ROOT / "dashboard" / "data" / "evidence_protocol_review_fixed_scope_offer.json"


def test_public_offer_feed_remains_bounded_and_uncommitted() -> None:
    payload = json.loads(OFFER.read_text(encoding="utf-8"))
    terms = payload["commercial_terms"]
    controls = payload["controls"]

    assert payload["schema"] == "lumencore.evidence_protocol_review_fixed_scope_offer.v1"
    assert payload["product_id"] == "prooflock_evidence_protocol_review_sprint_v1"
    assert len(payload["deliverables"]) == 6
    assert terms["candidate_fixed_fee_usd"] == 3500
    assert terms["price_committed"] is False
    assert terms["founder_price_approval_required"] is True
    assert controls["founder_price_approved"] is False
    assert controls["external_send_allowed"] is False
    assert controls["performance_claim_allowed"] is False
    assert controls["savings_claim_allowed"] is False
    assert controls["field_validation_claim_allowed"] is False


def test_public_page_loads_offer_feed_and_fails_closed() -> None:
    html = PAGE.read_text(encoding="utf-8")

    assert "data/evidence_protocol_review_fixed_scope_offer.json" in html
    assert "function offerFeedValid(payload)" in html
    assert "renderOfferUnavailable" in html
    assert "renderOfferIntegrityMismatch" in html
    assert "Buyer evidence protocol review" in html
    assert "Candidate fixed fee · founder approval required" in html
    assert "No performance or savings claim:" in html
    assert "$3,500" not in html


def test_public_page_uses_text_nodes_for_offer_feed_values() -> None:
    html = PAGE.read_text(encoding="utf-8")

    assert "title.textContent = escapeText(payload.product_name)" in html
    assert "purpose.textContent = escapeText(payload.purpose)" in html
    assert "item.textContent = escapeText(value)" in html
    assert "panel.replaceChildren(summary, detail, boundary)" in html
