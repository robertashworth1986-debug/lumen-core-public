from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_READY_SOURCE_REPLAY.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "geometry_ready_source_replay", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_ready_source_replay_is_compatibility_gated():
    module = load_module()
    payload = module.build_payload(max_routes=6, sample_limit=750)
    summary = payload["summary"]
    gates = payload["claim_gates"]

    assert payload["schema"] == "geometry_ready_source_replay_v2"
    assert summary["cards_reviewed"] == 5
    assert summary["routes_replayed"] == 4
    assert summary["direct_measured_replay_count"] == 2
    assert summary["source_conditioned_synthetic_stress_count"] == 2
    assert summary["no_compatible_replay_input_count"] == 1
    assert summary["candidate_win_count"] == 0
    assert summary["direct_all_baseline_global_holm_positive_count"] == 0
    assert summary["source_conditioned_named_baseline_mean_win_count"] == 1
    assert summary["legacy_ready_for_benchmark_rows_excluded"] >= 300
    assert summary["numeric_fallback_profile_count"] == 0
    assert len(summary["replay_chain_sha256"]) == 64

    assert gates["field_validation_claim_allowed"] is False
    assert gates["real_dollar_savings_claim_allowed"] is False
    assert gates["fixed_dollar_delta_sale_claim_allowed"] is False
    assert gates["live_trading_or_autonomous_execution_allowed"] is False
    assert gates["medical_or_addiction_treatment_claim_allowed"] is False
    assert gates["buyer_authorized_field_pilot_required"] is True


def test_ready_source_replay_preserves_mode_and_source_specific_baselines():
    module = load_module()
    payload = module.build_payload()
    by_lane = {
        row["lane"]: row for row in payload["ready_source_replay_results"]
    }

    wave = by_lane["wave_resonance_timing"]
    assert wave["candidate_family"] == "lissajous_phase_paths"
    assert wave["registered_candidate_family"] == "kuramoto_phase_coupling"
    assert wave["evidence_mode"] == "direct_measured_replay"
    assert wave["registered_baseline_count"] == 6
    assert wave["registered_baseline_mean_win_count"] == 0
    assert wave["candidate_beats_all_registered_baselines_after_global_holm"] is False

    thermal = by_lane["thermal_ventilation"]
    assert thermal["candidate_family"] == "thermal_plume_convection"
    assert thermal["evidence_mode"] == "source_conditioned_synthetic_stress"
    assert thermal["candidate_beats_named_baseline"] is True
    assert thermal["candidate_beats_all_registered_baselines_after_global_holm"] is False

    optimal = by_lane["optimal_curve_transport"]
    assert optimal["evidence_mode"] == "no_compatible_replay_input"
    assert optimal["performance_rows_evaluated"] == 0

    for result in payload["ready_source_replay_results"]:
        assert len(result["route_sha256"]) == 64
        assert (
            result["claim_gates"]["real_dollar_savings_claim_allowed"]
            is False
        )


def test_ready_source_replay_markdown_is_reviewer_safe():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    dumped = json.dumps(payload).lower()

    assert "Compatibility-Gated Results" in rendered
    assert "Direct measured replay and source-conditioned synthetic stress" in rendered
    assert "Legacy generic ready rows excluded" in rendered
    assert "guaranteed award" not in dumped
    assert "live_order_placement" not in dumped
    assert "heroin-like" not in dumped
