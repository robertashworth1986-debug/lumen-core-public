from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_TOP_GEOMETRY_LIVE_REPLAY_RESULTS.py"


def load_module():
    spec = importlib.util.spec_from_file_location("top_geometry_live_replay_results", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_top_geometry_live_replay_runs_all_adapters_and_keeps_claim_gate_closed():
    module = load_module()
    payload = module.build_results()

    assert payload["schema"] == "top_geometry_live_replay_results_v2"
    assert payload["summary"]["replay_card_count"] == 5
    assert payload["summary"]["adapter_replay_count"] == 5
    assert payload["summary"]["source_context_only_count"] == 0
    assert payload["summary"]["candidate_beats_named_baseline_count"] == sum(
        1 for card in payload["replay_cards"] if card["candidate_beats_named_baseline"]
    )
    assert payload["summary"]["paired_inference_card_count"] == 5
    assert payload["summary"]["holm_positive_card_count"] == sum(
        1
        for card in payload["replay_cards"]
        if card["paired_inference"]["statistically_positive_after_holm"]
    )
    assert payload["summary"]["registered_baseline_comparison_count"] == 21
    assert payload["summary"]["registered_baseline_mean_win_count"] == sum(
        card["baseline_gauntlet"]["mean_score_win_count"] for card in payload["replay_cards"]
    )
    assert payload["summary"]["registered_baseline_global_holm_positive_count"] == sum(
        card["baseline_gauntlet"]["global_holm_positive_count"] for card in payload["replay_cards"]
    )
    assert (
        payload["summary"]["registered_baseline_global_holm_positive_count"]
        <= payload["summary"]["registered_baseline_mean_win_count"]
    )
    assert payload["summary"]["cards_beating_all_registered_baselines_global_holm_count"] <= payload["summary"]["cards_beating_all_registered_baselines_mean_count"]
    assert payload["summary"]["time_series_measured_source_count"] >= 5
    assert payload["summary"]["time_series_measured_series_count"] >= 8
    assert payload["summary"]["total_live_context_rows_evaluated"] > 4_000
    assert payload["summary"]["unique_snapshot_sha256_count"] >= 10
    assert payload["summary"]["strict_rolling_champion_count"] >= 3
    assert payload["summary"]["triple_source_candidate_replay_count"] == 0
    assert payload["summary"]["single_run_candidate_replay_count"] == 0
    assert payload["summary"]["ready_for_live_geometry_claim"] is False
    assert payload["summary"]["ready_for_real_dollar_claim"] is False
    assert payload["summary"]["field_validation"] is False
    assert payload["summary"]["kraken_live_execution_allowed"] is False
    assert payload["inputs"]["geometry_live_breadth_proof_queue"].endswith(
        "geometry_live_breadth_proof_queue_latest.json"
    )


def test_top_geometry_live_replay_records_candidate_deltas_and_best_geometry():
    module = load_module()
    payload = module.build_results()
    by_lane = {card["lane"]: card for card in payload["replay_cards"]}

    optimal = by_lane["optimal_curve_transport"]
    assert optimal["candidate_family_id"] == "brachistochrone_descent"
    assert optimal["named_baseline"] == "minimum_jerk_curve"
    assert optimal["candidate_beats_named_baseline"] is True
    assert optimal["candidate_score_delta_vs_named_baseline"] > 0
    assert optimal["best_geometry_family_id"] == "brachistochrone_descent"
    assert optimal["rolling_gate_status"] == "rolling_champion"
    assert optimal["evidence_status"] == "repeat_rolling_champion_claim_still_needs_field_validation"
    assert optimal["top_next_run_rank"] == 1

    wave = by_lane["wave_resonance_timing"]
    assert wave["candidate_family_id"] == "kuramoto_phase_coupling"
    assert wave["candidate_beats_named_baseline"] is True
    assert wave["best_geometry_family_id"] == "kuramoto_phase_coupling"
    assert wave["rolling_gate_status"] == "rolling_champion"
    assert wave["top_next_run_rank"] is not None
    assert wave["top_next_run_rank"] >= 1
    assert wave["baseline_gauntlet"]["registered_baseline_count"] == 4
    assert wave["baseline_gauntlet"]["mean_score_win_count"] == 4
    assert wave["baseline_gauntlet"]["global_holm_positive_count"] == 0
    assert wave["baseline_gauntlet"]["candidate_beats_all_registered_baselines_mean"] is True
    assert wave["baseline_gauntlet"]["candidate_beats_all_registered_baselines_after_global_holm"] is False
    assert wave["baseline_gauntlet"]["external_approval_claim"] is False

    branching = by_lane["branching_transport"]
    assert branching["candidate_family_id"] == "leaf_veins"
    assert branching["candidate_beats_named_baseline"] is (
        branching["candidate_score_delta_vs_named_baseline"] > 0
    )
    assert branching["best_geometry_family_id"]
    assert branching["rolling_gate_status"] == "rolling_champion"

    thermal = by_lane["thermal_ventilation"]
    assert thermal["candidate_family_id"] == "thermal_plume_convection"
    assert thermal["candidate_beats_named_baseline"] is True
    assert thermal["best_geometry_family_id"]
    assert thermal["rolling_gate_status"] == "rolling_champion"
    assert thermal["top_next_run_rank"] is not None
    assert thermal["top_next_run_rank"] >= 1

    time_series = by_lane["time_series_model_routing"]
    assert time_series["adapter_status"] == "live_measured_walk_forward_ran"
    assert time_series["named_baseline"] == "naive_last"
    assert time_series["baseline_resolution"] == "adapter_best_baseline"
    assert time_series["candidate_beats_named_baseline"] is (
        time_series["candidate_score_delta_vs_named_baseline"] > 0
    )
    assert time_series["best_geometry_family_id"] == "fractal_brownian_surface"
    assert time_series["ingestion_summary"]["accepted_source_count"] >= 5
    assert time_series["ingestion_summary"]["accepted_series_count"] >= 8
    assert time_series["paired_inference"]["paired_unit_count"] > 700
    interval = time_series["paired_inference"]["bootstrap_mean_delta_ci95"]
    adjusted_p = time_series["paired_inference"]["holm_adjusted_p_value"]
    assert time_series["paired_inference"]["statistically_positive_after_holm"] is (
        interval[0] > 0 and adjusted_p <= 0.05
    )
    assert time_series["baseline_gauntlet"]["registered_baseline_count"] == 5
    assert time_series["baseline_gauntlet"]["candidate_beats_all_registered_baselines_mean"] is (
        time_series["baseline_gauntlet"]["mean_score_win_count"]
        == time_series["baseline_gauntlet"]["registered_baseline_count"]
    )
    assert time_series["rolling_gate_status"] == "not_promoted"


def test_top_geometry_live_replay_markdown_is_reviewer_safe():
    module = load_module()
    payload = module.build_results()
    rendered = module.render_markdown(payload)

    assert "Top Geometry Live Replay Results" in rendered
    assert "Live-context replay only" in rendered
    assert "not field validation" in rendered
    assert "not a real-dollar claim" in rendered
    assert "not permission for live trading" in rendered
    assert "Strict rolling champions" in rendered
    assert "Positive after Holm correction" in rendered
    assert "five preselected top replay cards only" in rendered
    assert "internally registered software baselines, not externally approved standards" in rendered
    assert "Registered Baseline Gauntlet" in rendered
    assert "live_measured_walk_forward_ran" in rendered
    assert "Ready for live geometry claim: `false`" in rendered
    assert "Ready for real-dollar claim: `false`" in rendered
    assert "guaranteed funding" not in rendered.lower()
    assert "guaranteed profit" not in rendered.lower()


def test_top_geometry_live_replay_statistics_are_paired_and_holm_adjusted():
    module = load_module()

    assert module.exact_two_sided_sign_test([1.0, 2.0, 3.0, 4.0, 5.0]) == 0.0625
    cards = [
        {"paired_inference": {"raw_two_sided_sign_test_p_value": 0.01, "bootstrap_mean_delta_ci95": [0.1, 0.2]}},
        {"paired_inference": {"raw_two_sided_sign_test_p_value": 0.03, "bootstrap_mean_delta_ci95": [0.1, 0.2]}},
        {"paired_inference": {"raw_two_sided_sign_test_p_value": 0.20, "bootstrap_mean_delta_ci95": [-0.1, 0.2]}},
    ]

    module.apply_holm_correction(cards)

    assert cards[0]["paired_inference"]["holm_adjusted_p_value"] == 0.03
    assert cards[0]["paired_inference"]["statistically_positive_after_holm"] is True
    assert cards[1]["paired_inference"]["holm_adjusted_p_value"] == 0.06
    assert cards[1]["paired_inference"]["statistically_positive_after_holm"] is False
    assert cards[2]["paired_inference"]["holm_adjusted_p_value"] == 0.20


def test_global_baseline_holm_requires_every_registered_baseline_to_pass():
    module = load_module()
    cards = [
        {
            "baseline_comparisons": [
                {
                    "candidate_beats_baseline_mean": True,
                    "paired_inference": {
                        "raw_two_sided_sign_test_p_value": 0.001,
                        "bootstrap_mean_delta_ci95": [0.1, 0.2],
                    },
                    "global_holm_adjusted_p_value": None,
                    "statistically_positive_after_global_holm": False,
                },
                {
                    "candidate_beats_baseline_mean": False,
                    "paired_inference": {
                        "raw_two_sided_sign_test_p_value": 0.5,
                        "bootstrap_mean_delta_ci95": [-0.2, 0.1],
                    },
                    "global_holm_adjusted_p_value": None,
                    "statistically_positive_after_global_holm": False,
                },
            ]
        }
    ]

    module.apply_global_baseline_holm(cards)

    gauntlet = cards[0]["baseline_gauntlet"]
    assert gauntlet["registered_baseline_count"] == 2
    assert gauntlet["global_holm_positive_count"] == 1
    assert gauntlet["candidate_beats_all_registered_baselines_mean"] is False
    assert gauntlet["candidate_beats_all_registered_baselines_after_global_holm"] is False
    assert gauntlet["external_approval_claim"] is False
