from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READY_REPLAY_SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_READY_SOURCE_REPLAY.py"
SCRIPT = ROOT / "code" / "ops" / "BUILD_VALUATION_PROPOSAL_TARGET_PACKET.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def ensure_ready_replay_exists() -> None:
    module = load_module(READY_REPLAY_SCRIPT, "geometry_ready_source_replay_for_valuation_test")
    module.main()


def test_valuation_packet_uses_real_replay_numbers_and_selects_energy_target():
    ensure_ready_replay_exists()
    module = load_module(SCRIPT, "valuation_proposal_target_packet")
    payload = module.build_payload()
    overall = payload["overall_replay_stats"]
    target = payload["recommended_first_proposal_target"]
    valuation = payload["valuation_state"]

    assert payload["schema"] == "valuation_proposal_target_packet_v1"
    assert overall["routes"] >= 10
    assert overall["wins"] >= 1
    assert overall["estimated_rows"] > 0
    assert overall["numeric_samples"] > 0
    assert 0 < overall["honest_route_win_rate_lower_95"] <= overall["honest_route_win_rate"] <= overall["honest_route_win_rate_upper_95"] <= 1

    assert valuation["strongest_lane"] == "wave_resonance_timing"
    assert valuation["strongest_candidate"] == "kuramoto_phase_coupling"
    assert valuation["defensible_money_status"].startswith("sell paid technical evaluation")
    assert target["target_segment"] == "utility_grid_analytics_or_energy_forecasting"
    assert "paid evidence review" in target["proposal_ask"]
    assert target["paid_review_scope_usd"]["status"] == "scoping_range_not_value_claim"


def test_valuation_packet_marks_cumberland_claims_ahead_of_gate_and_blocks_hype():
    ensure_ready_replay_exists()
    module = load_module(SCRIPT, "valuation_proposal_target_packet")
    payload = module.build_payload()
    gates = payload["claim_gates"]
    rendered = module.render_markdown(payload)
    dumped = json.dumps(payload).lower()

    assert gates["field_validation_claim_allowed"] is False
    assert gates["real_dollar_savings_claim_allowed"] is False
    assert gates["fixed_dollar_delta_sale_claim_allowed"] is False
    assert gates["live_trading_or_autonomous_execution_allowed"] is False
    assert gates["medical_or_addiction_treatment_claim_allowed"] is False
    assert gates["grant_award_certainty_allowed"] is False
    assert gates["paid_technical_evaluation_scoping_allowed"] is True

    assert "Phrases ahead of current gates" in rendered
    assert "Do not state 15-35% system efficiency" in rendered
    assert "Reviewer-Safe Proposal Blurb" in rendered
    assert "guaranteed roi claims" in dumped
    assert "guaranteed roi allowed" not in dumped
    assert "field-validation claim allowed: `true`" not in rendered.lower()
