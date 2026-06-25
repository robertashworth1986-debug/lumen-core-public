from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_PROOF_CARD_PACK.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geometry_proof_card_pack", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_card_pack_builds_reviewer_safe_cards_from_queue_and_replay():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "geometry_proof_card_pack_v1"
    assert summary["proof_card_count"] >= 8
    assert summary["registry_card_count"] >= 7
    assert summary["annex_card_count"] >= 1
    assert summary["strict_rolling_champion_count"] == 0
    assert summary["triple_source_candidate_count"] >= 2
    assert summary["single_run_candidate_count"] >= 1
    assert summary["candidate_win_card_count"] >= 3
    assert summary["ready_for_live_geometry_claim"] is False
    assert summary["ready_for_real_dollar_claim"] is False
    assert summary["field_validation"] is False
    assert summary["kraken_live_execution_allowed"] is False
    assert len(summary["card_chain_sha256"]) == 64
    assert payload["inputs"]["top_geometry_live_replay_results"].endswith(
        "top_geometry_live_replay_results_latest.json"
    )


def test_key_candidate_cards_preserve_truth_and_do_not_overclaim():
    module = load_module()
    payload = module.build_payload()
    cards = {card["family_id"]: card for card in payload["proof_cards"]}

    brach = cards["brachistochrone_descent"]
    assert brach["registry_family"] is True
    assert brach["rolling_gate_status"] == "triple_source_candidate"
    assert brach["readiness_tier"] == "triple_source_candidate_ready_for_repeat_replay"
    assert brach["top_next_run_rank"] == 1
    assert brach["replay_result"]["candidate_beats_named_baseline"] is True
    assert brach["replay_result"]["candidate_score_delta_vs_named_baseline"] > 0
    assert brach["live_evidence"]["source_count"] >= 3
    assert len(brach["card_sha256"]) == 64

    kuramoto = cards["kuramoto_phase_coupling"]
    assert kuramoto["rolling_gate_status"] == "triple_source_candidate"
    assert kuramoto["top_next_run_rank"] == 2
    assert kuramoto["replay_result"]["best_geometry_family_id"] == "kuramoto_phase_coupling"

    thermal = cards["thermal_plume_convection"]
    assert thermal["rolling_gate_status"] == "single_run_candidate"
    assert thermal["readiness_tier"] == "single_run_candidate_needs_more_sources_or_repeat"
    assert thermal["top_next_run_rank"] == 3

    leaf = cards["leaf_veins"]
    assert leaf["readiness_tier"] == "replay_candidate_did_not_beat_named_baseline"
    assert leaf["replay_result"]["candidate_beats_named_baseline"] is False

    crack = cards["crack_propagation_paths"]
    assert crack["readiness_tier"] == "proof_value_priority_needs_live_win"
    assert crack["value_posture"]["ready_for_real_dollar_claim"] is False

    phase = cards["phase_locked_residual_corrector"]
    assert phase["registry_family"] is False
    assert phase["rolling_gate_status"] == "triple_source_candidate"
    assert phase["readiness_tier"].startswith(
        "external_rolling_candidate_not_registry_family::triple_source_candidate"
    )
    assert phase["replay_result"]["adapter_status"] == "external_rolling_gate_annex_no_geometry_adapter"
    assert phase["replay_result"]["candidate_score_delta_vs_named_baseline"] > 0

    for card in cards.values():
        gate = card["claim_gate"]
        assert gate["ready_for_live_geometry_claim"] is False
        assert gate["ready_for_real_dollar_claim"] is False
        assert gate["field_validation"] is False
        assert gate["kraken_live_execution_allowed"] is False
        assert "guaranteed winner" in card["blocked_language"]
        assert "field validated" in card["blocked_language"]


def test_rendered_pack_is_safe_and_hashable():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)

    assert "Geometry Proof Card Pack" in rendered
    assert "Card chain SHA-256" in rendered
    assert "`triple_source_candidate`" in rendered
    assert "`single_run_candidate`" in rendered
    assert "Ready for live geometry claim: `false`" in rendered
    assert "Ready for real-dollar claim: `false`" in rendered
    assert "grant award guaranteed" in rendered
    assert "guaranteed profit" not in rendered.lower()
    assert "live_order_placement" not in json.dumps(payload)
