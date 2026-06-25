from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_CLAIM_STRENGTH_VALUE_UNLOCK_MAP.py"


def load_module():
    spec = importlib.util.spec_from_file_location("claim_strength_value_unlock_map", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_claim_strength_map_answers_current_money_question_safely():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    money_answer = payload["money_worth_answer"]

    assert payload["schema"] == "claim_strength_value_unlock_map_v1"
    assert summary["strongest_current_claim"] == "bounded_estimated_value_signal_and_paid_pilot_scoping"
    assert summary["safe_estimated_hourly_value_usd"] >= 4500
    assert summary["safe_estimated_annual_value_usd"] >= 39_000_000
    assert summary["blocked_context_annual_value_usd"] > summary["safe_estimated_annual_value_usd"]
    assert summary["measured_estimated_value_lane_count"] == 10
    assert summary["robust_repeat_candidate_count"] >= 1
    assert summary["manual_paid_pilot_outreach_rows"] == 12
    assert len(payload["claim_strength_sha256"]) == 64

    assert "Worth money now as a paid technical evaluation" in money_answer["plain_answer"]
    assert money_answer["defensible_value_signal"]["language"] == "bounded estimated value signal under stated assumptions"
    assert money_answer["blocked_big_number"]["language"] == "context-only value surface; do not present as real savings or revenue"


def test_claim_strength_map_keeps_high_risk_claim_gates_closed():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    rendered = module.render_markdown(payload)

    assert summary["bounded_estimated_value_claim_allowed"] is True
    assert summary["paid_evaluation_offer_allowed"] is True
    assert summary["buyer_authorized_pilot_scoping_ready"] is True
    assert summary["manual_reviewed_outreach_allowed"] is True
    assert summary["field_validation_claim_allowed"] is False
    assert summary["realized_savings_claim_allowed"] is False
    assert summary["fixed_dollar_delta_claim_allowed"] is False
    assert summary["bulk_email_allowed"] is False
    assert summary["live_trading_or_autonomous_execution_allowed"] is False

    assert "Fixed-dollar delta claim allowed: `false`" in rendered
    assert "Field-validation claim allowed: `false`" in rendered
    assert "Realized-savings claim allowed: `false`" in rendered
    assert "guaranteed grant award" in "\n".join(payload["must_not_say"])


def test_claim_strength_map_preserves_current_repeat_winners_and_unlocks():
    module = load_module()
    payload = module.build_payload()
    candidates = {row["family_id"]: row for row in payload["current_repeat_candidates"]}
    unlock_text = json.dumps(payload["highest_value_unlocks"]).lower()

    assert set(candidates) == {"brachistochrone_descent", "kuramoto_phase_coupling"}
    assert candidates["brachistochrone_descent"]["lane"] == "optimal_curve_transport"
    assert candidates["brachistochrone_descent"]["repeat_window_evidence"]["wins"] >= 6
    assert candidates["brachistochrone_descent"]["repeat_window_evidence"]["windows"] >= 6
    assert candidates["kuramoto_phase_coupling"]["lane"] == "wave_resonance_timing"
    assert candidates["kuramoto_phase_coupling"]["repeat_window_evidence"]["wins"] >= 3
    assert candidates["kuramoto_phase_coupling"]["repeat_window_evidence"]["windows"] >= 3
    assert "datacenter_cooling_optimization" in unlock_text
    assert "energy_forecasting" in unlock_text
    assert "buyer-authorized constrained-routing replay" in unlock_text


def test_flower_of_life_note_is_accurate_and_testable():
    module = load_module()
    payload = module.build_payload()
    note = payload["flower_of_life_circle_wave_note"]
    rendered = module.render_markdown(payload)

    assert "overlapping equal-radius circle lattice" in note["answer"]
    assert "A circle is not a wave by itself" in note["answer"]
    assert "circular_wavefront_interference" in note["testable_families"]
    assert "flower_of_life_hex_circle_lattice" in note["testable_families"]
    assert "Flower Of Life / Circles / Waves" in rendered
    assert "Claim boundary" in rendered


def test_claim_strength_surfaces_do_not_expose_sensitive_material():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    text = json.dumps(payload).lower() + rendered.lower()

    blocked_fragments = [
        "api" + "_key",
        "client" + "_sec" + "ret",
        "private" + "_key",
        "bear" + "er ",
        "s" + "k-",
        "pass" + "word",
    ]
    for fragment in blocked_fragments:
        assert fragment not in text
