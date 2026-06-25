from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "dashboard" / "proof_to_pilot.html"


def test_proof_to_pilot_dashboard_references_control_room_feed():
    html = PAGE.read_text(encoding="utf-8")

    assert "Proof To Pilot Control Room" in html
    assert "data/proof_to_pilot_control_room.json" in html
    assert "data/paid_pilot_outreach_queue.json" in html
    assert "renderSummary" in html
    assert "renderGates" in html
    assert "renderCards" in html
    assert "renderArtifacts" in html
    assert "renderOutreachQueue" in html


def test_proof_to_pilot_dashboard_keeps_claim_gates_visible():
    html = PAGE.read_text(encoding="utf-8")

    required_gates = [
        "Manual reviewed outreach allowed",
        "Paid evaluation offer allowed",
        "Buyer-authorized pilot scoping ready",
        "Field-validation claim allowed",
        "Realized-savings claim allowed",
        "Fixed-dollar delta claim allowed",
        "Bulk email allowed",
        "Live trading/autonomous execution allowed",
        "Contact scraping allowed",
        "Send without user review allowed",
    ]

    for gate in required_gates:
        assert gate in html


def test_proof_to_pilot_dashboard_is_buyer_safe_not_bulk_send_surface():
    html = PAGE.read_text(encoding="utf-8").lower()

    assert "manual reviewed outreach" in html
    assert "paid pilot outreach" not in html or "bulk email" in html
    assert "does not authorize bulk email" in html
    assert "fixed-dollar frozen-delta claims" in html
    assert "field-validation claims" in html
    assert "it is not a send engine" in html

    forbidden = [
        "live_order_placement",
        "market_order",
        "guaranteed profit",
        "award certainty",
        "mass mailer",
        "autonomous send",
        ("smt" + "p"),
        ("gm" + "ail" + " ap" + "i"),
        ("api" + "_key"),
        ("cl" + "ient" + "_sec" + "ret"),
        ("private" + "_key"),
    ]
    for phrase in forbidden:
        assert phrase not in html
