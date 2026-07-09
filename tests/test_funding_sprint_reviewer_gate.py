from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_FUNDING_SPRINT_REVIEWER_GATE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("funding_sprint_reviewer_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_reviewer_gate_builds_cards_and_scans_boundary_language():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "funding_sprint_reviewer_gate_v1"
    assert payload["reviewer_gate_clear"] is True
    assert payload["summary"]["markdown_file_count"] >= 18
    assert payload["summary"]["proof_card_count"] == 6
    assert payload["summary"]["unsafe_secret_count"] == 0
    assert payload["summary"]["unsafe_claim_count"] == 0
    assert payload["summary"]["boundary_hit_count"] > 0
    assert payload["summary"]["autonomous_external_action_allowed"] is False
    assert payload["summary"]["live_trading_allowed"] is False
    assert payload["summary"]["final_submission_allowed_without_human"] is False
    assert len(payload["gate_sha256"]) == 64


def test_active_lane_cards_keep_human_gates_and_hashes():
    module = load_module()
    payload = module.build_payload()
    cards = {card["lane"]: card for card in payload["proof_cards"]}

    expected = {
        "Air Force Advanced Automation Contract RFI",
        "NASA Data Center Infrastructure RFI",
        "DLA MissionWeave DSIP SBIR",
        "FHWA TSMO Data Initiative",
        "DOE Advanced Nuclear Licensing Cost-Share",
        "NSF SBIR/STTR Project Pitch",
    }
    assert set(cards) == expected

    for card in cards.values():
        assert card["artifact_present"] is True
        assert len(card["artifact_sha256"]) == 64
        assert len(card["card_sha256"]) == 64
        assert "Human" in card["human_gate"]
        assert card["reviewer_posture"] == "ready_for_human_review"

    assert "Firm PIN" in cards["DLA MissionWeave DSIP SBIR"]["next_gate"]
    assert "Partner-first" in cards["DOE Advanced Nuclear Licensing Cost-Share"]["claim_boundary"]
    assert "invitation-gated" in cards["NSF SBIR/STTR Project Pitch"]["claim_boundary"]


def test_rendered_markdown_preserves_no_autonomous_submission_rule():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)

    assert "Funding Sprint Reviewer Gate" in rendered
    assert "Reviewer gate clear: `true`" in rendered
    assert "Autonomous external action allowed: `false`" in rendered
    assert "Live trading allowed: `false`" in rendered
    assert "Final submission without human allowed: `false`" in rendered
    assert "No portal submission" in rendered
