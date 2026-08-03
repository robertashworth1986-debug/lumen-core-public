from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT / "code" / "ops" / "BUILD_GEOMETRY_REPEAT_PROOF_VALIDATION.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "geometry_repeat_proof_validation", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_repeat_validation_accepts_only_qualified_direct_measured_cards():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "geometry_repeat_proof_validation_v2"
    assert summary["validated_family_count"] == 5
    assert summary["direct_measured_family_count"] == 2
    assert summary["source_conditioned_synthetic_family_count"] == 2
    assert summary["repeat_confirmation_eligible_count"] == 0
    assert summary["repeat_candidate_gate_passed_count"] == 0
    assert summary["total_windows_replayed"] == 0
    assert summary["historical_proxy_repeat_rows_accepted"] == 0
    assert len(summary["validation_chain_sha256"]) == 64


def test_repeat_validation_preserves_evaluated_vs_registered_candidate():
    module = load_module()
    payload = module.build_payload()
    by_lane = {row["lane"]: row for row in payload["validations"]}

    wave = by_lane["wave_resonance_timing"]
    assert wave["family_id"] == "lissajous_phase_paths"
    assert (
        wave["registered_card_candidate_family_id"]
        == "kuramoto_phase_coupling"
    )
    assert wave["evidence_mode"] == "direct_measured_replay"
    assert wave["registered_baseline_count"] == 6
    assert (
        wave[
            "candidate_beats_all_registered_baselines_after_global_holm"
        ]
        is False
    )
    assert wave["repeat_candidate_gate_passed"] is False
    assert (
        "registered_card_candidate_not_the_protocol_evaluated_candidate"
        in wave["blockers"]
    )

    thermal = by_lane["thermal_ventilation"]
    assert (
        thermal["evidence_mode"]
        == "source_conditioned_synthetic_stress"
    )
    assert thermal["repeat_candidate_gate_passed"] is False
    assert (
        "evidence_mode_not_direct_measured_replay"
        in thermal["blockers"]
    )


def test_repeat_validation_closes_all_formal_claim_gates():
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


def test_repeat_proof_markdown_is_reviewer_safe():
    module = load_module()
    rendered = module.render_markdown(module.build_payload())

    assert "Geometry Repeat Proof Validation" in rendered
    assert "Repeat candidate gates passed: `0`" in rendered
    assert "Ready for real-dollar claim: `false`" in rendered
    assert "Field validation: `false`" in rendered
    assert "`lissajous_phase_paths`" in rendered
    assert "`kuramoto_phase_coupling`" in rendered
    assert "not field validation" in rendered
