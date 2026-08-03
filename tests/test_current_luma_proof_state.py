from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_CURRENT_LUMA_PROOF_STATE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("current_luma_proof_state", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_current_luma_proof_state_merges_registry_ready_replay_and_repeat_evidence():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "current_luma_proof_state.v2"
    assert payload["registry"]["family_count"] >= 140
    assert payload["registry"]["natural_path_family_count"] >= 50
    assert payload["manifest"]["ready_for_benchmark_routes"] >= 300
    assert payload["ready_source_replay"]["routes"] == 4
    assert payload["ready_source_replay"]["direct_measured_replay_count"] == 2
    assert (
        payload["ready_source_replay"][
            "source_conditioned_synthetic_stress_count"
        ]
        == 2
    )
    assert (
        payload["ready_source_replay"][
            "direct_all_baseline_global_holm_positive_count"
        ]
        == 0
    )
    assert (
        payload["ready_source_replay"][
            "legacy_ready_for_benchmark_rows_excluded"
        ]
        >= 300
    )
    assert payload["ready_source_replay"]["numeric_fallback_profile_count"] == 0
    assert payload["ready_source_replay"]["estimated_rows_replayed"] > 0
    assert payload["ready_source_replay"]["numeric_samples_read"] > 0
    assert (
        payload["ready_source_replay"]["candidate_wins"]
        + payload["ready_source_replay"]["candidate_losses_or_ties"]
        == payload["ready_source_replay"]["direct_measured_replay_count"]
    )
    assert len(payload["ready_source_replay"]["replay_chain_sha256"]) == 64
    assert payload["kuramoto_holdout_expansion"]["holdout_count"] >= 1_500
    assert (
        payload["kuramoto_holdout_expansion"]["wins_vs_kalman"]
        < payload["kuramoto_holdout_expansion"]["holdout_count"] / 2
    )
    assert payload["kuramoto_holdout_expansion"]["mean_delta_vs_kalman"] < 0
    assert (
        payload["kuramoto_holdout_expansion"][
            "passes_internal_20_holdout_gate"
        ]
        is False
    )
    assert (
        payload["kuramoto_holdout_expansion"]["candidate_was_protocol_selected"]
        is False
    )
    assert (
        payload["kuramoto_holdout_expansion"][
            "candidate_beats_all_registered_baselines_after_holm"
        ]
        is False
    )
    assert (
        payload["kuramoto_holdout_expansion"][
            "legacy_source_conditioned_claim_superseded"
        ]
        is True
    )
    assert payload["kuramoto_cross_sector_benchmark"]["sector_gain_proven_count"] == 0
    assert payload["kuramoto_cross_sector_benchmark"]["sector_count"] == 6

    by_family = {row["family_id"]: row for row in payload["champion_rankings"]}
    assert "brachistochrone_descent" in by_family
    assert "kuramoto_phase_coupling" in by_family

    brach = by_family["brachistochrone_descent"]
    assert brach["evidence_stage"] == "no_compatible_direct_measured_replay"
    assert brach["repeat_evidence"]["repeat_live_win_count"] == 0
    assert (
        brach["source_conditioned_evidence"]["source_conditioned_replays"] == 0
    )

    kuramoto = by_family["kuramoto_phase_coupling"]
    assert kuramoto["source_conditioned_evidence"] == {}
    assert kuramoto["kuramoto_holdout_evidence"]["holdout_count"] >= 1_500
    assert kuramoto["kuramoto_holdout_evidence"]["mean_delta_vs_kalman"] < 0
    assert kuramoto["evidence_stage"] == "negative_current_cross_sector_benchmark"
    assert "0/6 proven kuramoto sector gains" in kuramoto["safe_claim"].lower()
    assert "neither result supports performance marketing" in kuramoto["safe_claim"].lower()


def test_current_luma_proof_state_keeps_money_and_execution_gates_closed():
    module = load_module()
    payload = module.build_payload()
    gates = payload["gates"]

    assert gates["paid_technical_evaluation_scoping_allowed"] is True
    assert gates["field_validation_claim_allowed"] is False
    assert gates["real_dollar_savings_claim_allowed"] is False
    assert gates["fixed_dollar_delta_sale_claim_allowed"] is False
    assert gates["live_trading_or_autonomous_execution_allowed"] is False
    assert gates["all_registered_families_live_benchmarked"] is False

    valuation = payload["valuation"]
    assert valuation["safe_estimated_annual_value_usd"] == 0
    assert valuation["blocked_context_annual_value_usd"] == 0
    assert len(payload["proof_state_sha256"]) == 64


def test_current_luma_proof_state_markdown_is_reviewer_safe():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)

    assert "Current Luma Proof State" in rendered
    assert "field_validation_claim_allowed: `false`" in rendered
    assert "real_dollar_savings_claim_allowed: `false`" in rendered
    assert "Fixed" not in rendered
    assert "guaranteed" not in rendered.lower()
    assert "Direct all-baseline globally corrected promotions: `0`" in rendered
    assert "Kuramoto measured EIA holdout" in rendered
    assert "NO_CROSS_SECTOR_EFFICIENCY_GAIN_PROVEN" in rendered
