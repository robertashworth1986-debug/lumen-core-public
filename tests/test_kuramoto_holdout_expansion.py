from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_KURAMOTO_HOLDOUT_EXPANSION.py"


def load_module():
    spec = importlib.util.spec_from_file_location("kuramoto_holdout_expansion", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_kuramoto_holdout_expansion_uses_complete_measured_eia_holdout():
    module = load_module()
    payload = module.build_payload(max_routes=20, sample_limit=750)
    summary = payload["summary"]

    assert payload["schema"] == "kuramoto_holdout_expansion_v2"
    assert summary["evidence_mode"] == "direct_measured_replay"
    assert summary["candidate"] == "kuramoto_phase_coupling"
    assert summary["development_selected_candidate"] == "lissajous_phase_paths"
    assert summary["candidate_was_protocol_selected"] is False
    assert summary["named_baseline"] == "kalman_local_linear_trend"
    assert summary["source_systems"] == ["EIA_GRID_VALIDATION"]
    assert summary["panel_row_count"] == 14_704
    assert summary["authority_count"] == 8
    assert summary["holdout_count"] == 1_525
    assert summary["paired_authority_month_count"] == 56
    assert 0.0 <= summary["win_rate_vs_kalman"] <= 1.0
    assert 0.0 <= summary["wilson_95_win_rate_lower"] <= summary["wilson_95_win_rate_upper"] <= 1.0
    assert len(summary["holdout_chain_sha256"]) == 64


def test_kuramoto_loses_source_specific_gauntlet_and_keeps_gates_closed():
    module = load_module()
    payload = module.build_payload(max_routes=20, sample_limit=750)
    summary = payload["summary"]
    gates = payload["claim_gates"]

    assert summary["registered_baseline_count"] == 6
    assert summary["registered_baseline_mean_win_count"] == 0
    assert summary["registered_baseline_gate_pass_count"] == 0
    assert summary["candidate_beats_all_registered_baselines_mean"] is False
    assert summary["candidate_beats_all_registered_baselines_after_holm"] is False
    assert summary["protocol_grade_internal_champion"] is False
    assert summary["ready_for_buyer_authorized_field_replay_request"] is False
    assert summary["mean_delta_vs_kalman"] < 0
    assert summary["mean_delta_vs_best_baseline"] < 0
    assert gates["field_validation_claim_allowed"] is False
    assert gates["real_dollar_savings_claim_allowed"] is False
    assert gates["fixed_dollar_delta_sale_claim_allowed"] is False
    assert gates["live_trading_or_autonomous_execution_allowed"] is False
    assert gates["buyer_authorized_field_pilot_required"] is True

    for row in payload["holdout_results"]:
        assert row["lane"] == "wave_resonance_timing"
        assert row["candidate_family"] == "kuramoto_phase_coupling"
        assert row["source_system"] == "EIA_GRID_VALIDATION"
        assert row["evidence_mode"] == "direct_measured_replay"
        assert row["daily_pair_count"] == 1_525
        assert row["candidate_beats_baseline_mean"] is False
        assert row["passes_comparison_gate"] is False
        assert len(row["source_sha256"]) == 64
        assert len(row["holdout_sha256"]) == 64


def test_kuramoto_holdout_markdown_is_reviewer_safe():
    module = load_module()
    payload = module.build_payload(max_routes=20, sample_limit=750)
    rendered = module.render_markdown(payload)
    dumped = json.dumps(payload).lower()

    assert "Kuramoto Holdout Expansion" in rendered
    assert "negative result" in rendered
    assert "Source-Specific Baseline Gauntlet" in rendered
    assert "field_validation_claim_allowed: `false`" in rendered
    assert "real_dollar_savings_claim_allowed: `false`" in rendered
    assert "guaranteed" not in dumped
    assert "money printer" not in dumped
