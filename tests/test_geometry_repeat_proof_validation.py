from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_REPEAT_PROOF_VALIDATION.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geometry_repeat_proof_validation", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_repeat_proof_validation_promotes_only_repeat_live_candidates():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    by_family = {row["family_id"]: row for row in payload["validations"]}

    assert payload["schema"] == "geometry_repeat_proof_validation_v1"
    assert summary["validated_family_count"] >= 4
    assert summary["repeat_candidate_gate_passed_count"] >= 2
    assert summary["total_windows_replayed"] >= 20
    assert summary["total_live_context_rows_evaluated"] > 500
    assert len(summary["validation_chain_sha256"]) == 64

    brach = by_family["brachistochrone_descent"]
    assert brach["available_window_count"] >= 5
    assert brach["repeat_live_win_count"] >= 5
    assert brach["distinct_win_hash_count"] >= 5
    assert brach["min_source_count"] >= 5
    assert brach["candidate_best_geometry_count"] >= 5
    assert brach["repeat_candidate_gate_passed"] is True

    kuramoto = by_family["kuramoto_phase_coupling"]
    assert kuramoto["available_window_count"] >= 5
    assert kuramoto["repeat_live_win_count"] >= 5
    assert kuramoto["distinct_win_hash_count"] >= 5
    assert kuramoto["min_source_count"] >= 4
    assert kuramoto["candidate_best_geometry_count"] >= 5
    assert kuramoto["repeat_candidate_gate_passed"] is True


def test_repeat_proof_validation_keeps_weaker_rows_out_of_claim_lane():
    module = load_module()
    payload = module.build_payload()
    by_family = {row["family_id"]: row for row in payload["validations"]}

    leaf = by_family["leaf_veins"]
    assert leaf["repeat_candidate_gate_passed"] is False
    assert leaf["evidence_stage"] == "not_repeat_promoted"

    thermal = by_family["thermal_plume_convection"]
    assert thermal["repeat_live_win_count"] >= 5
    assert thermal["min_source_count"] < 3
    assert thermal["repeat_candidate_gate_passed"] is False
    assert thermal["evidence_stage"] == "not_repeat_promoted"


def test_repeat_proof_validation_closes_all_formal_claim_gates():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    text = json.dumps(payload).lower()

    assert summary["ready_for_live_geometry_claim"] is False
    assert summary["ready_for_real_dollar_claim"] is False
    assert summary["field_validation"] is False
    assert summary["kraken_live_execution_allowed"] is False
    assert "realized savings" in text
    assert "award certainty" in text
    assert "live_order_placement" not in text
    assert ("api" + "_key") not in text

    for row in payload["validations"]:
        claim_gate = row["claim_gate"]
        assert claim_gate["ready_for_live_geometry_claim"] is False
        assert claim_gate["ready_for_real_dollar_claim"] is False
        assert claim_gate["field_validation"] is False
        assert claim_gate["kraken_live_execution_allowed"] is False


def test_repeat_proof_markdown_is_buyer_safe():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)

    assert "Geometry Repeat Proof Validation" in rendered
    assert "Repeat candidate gates passed:" in rendered
    assert "Ready for real-dollar claim: `false`" in rendered
    assert "Field validation: `false`" in rendered
    assert "`brachistochrone_descent`" in rendered
    assert "`kuramoto_phase_coupling`" in rendered
    assert "not field validation" in rendered
    assert "not prove field validation" in rendered
