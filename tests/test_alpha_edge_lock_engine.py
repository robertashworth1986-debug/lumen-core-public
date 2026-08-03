from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_ALPHA_EDGE_LOCK_ENGINE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("alpha_edge_lock_engine", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_current_evidence_fails_closed_with_zero_proven_locks():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "alpha_edge_lock_engine.v2"
    assert payload["status"] == "NO_PROVEN_ALPHA_EDGE"
    assert payload["summary"]["current_alpha_proven"] is False
    assert payload["summary"]["grade_a_locks"] == 0
    assert payload["summary"]["proven_lock_count"] == 0
    assert payload["summary"]["top_harmonic_alpha_edge_score"] == 0.0

    strict = payload["strict_alpha_gate_assessment"]
    assert strict["all_required_gates_passed"] is False
    assert strict["passed_gate_count"] == 0
    assert strict["required_gate_count"] == 9
    assert all(gate["passed"] is False for gate in strict["gates"].values())

    promotion = payload["promotion_gates"]
    assert promotion["live_trading_allowed"] is False
    assert promotion["capital_deployment_allowed"] is False
    assert promotion["public_performance_claim_allowed"] is False
    assert promotion["profit_claim_allowed"] is False
    assert promotion["autonomous_execution_allowed"] is False
    assert promotion["physical_control_deployment_allowed"] is False

    expected_sources = {
        "benchmark_beater",
        "top_system_strategy_baseline",
        "kraken_institutional_gauntlet",
        "symbol_timing_production_gate",
        "kuramoto_cross_sector_benchmark",
        "branching_live_breadth_replay",
        "brachistochrone_control_audit",
    }
    assert set(payload["evidence_sources"]) == expected_sources
    assert all(row["alpha_lock_score"] == 0.0 for row in payload["problem_stack"])
    assert all(row["edge_lock_score"] == 0.0 for row in payload["problem_stack"])
    assert all(row["business_context_only"] is True for row in payload["problem_stack"])


def test_exposure_and_partial_receipt_cannot_create_alpha():
    module = load_module()
    partial_gates = {key: True for key in module.STRICT_ALPHA_GATE_KEYS}
    partial_gates["independent_or_prospective_replication"] = False

    payload = module.build_payload(
        sector_matrix={
            "sector_value_matrix": [
                {
                    "sector": "market_data",
                    "year": 1_000_000_000_000,
                    "modeled_annual_upside_usd": 999_999_999_999,
                    "basis": "MEASURED",
                }
            ]
        },
        benchmark_beater={
            "headline": {
                "overall_verdict": "ROBUST_EDGE",
                "median_alpha_edge_pct": 99.0,
                "positive_sharpe_rate_pct": 100.0,
            },
            "validation": {
                "chronological_no_lookahead": True,
                "roundtrip_cost_bps": 10.0,
                "slippage_bps_per_side": 2.0,
            },
            "strict_alpha_gate_receipt": {
                "candidate_id": "almost_complete_is_not_complete",
                "status": "PASSED",
                "gates": partial_gates,
            },
        },
        top_system_strategy={
            "baseline": {
                "top_flow": "geom_gaussian",
                "top_strategy": "regime_switch",
                "top_algo": "confidence_weighted",
                "top_test_sharpe": 9.0,
                "top_test_vs_baseline": 0.99,
                "total_candidates": 1,
            }
        },
        kraken_gauntlet={},
        symbol_timing={},
        kuramoto={},
        branching_replay={},
        geometry_confirmatory={},
        sim_runs=1_000_000,
        alpha_threshold=1.0,
        edge_threshold=1.0,
    )

    assert payload["status"] == "NO_PROVEN_ALPHA_EDGE"
    assert payload["summary"]["current_alpha_proven"] is False
    assert payload["summary"]["grade_a_locks"] == 0
    assert payload["strict_alpha_gate_assessment"]["passed_gate_count"] == 0
    assert payload["problem_stack"][0]["annual_exposure_usd"] == 1_000_000_000_000
    assert payload["problem_stack"][0]["alpha_lock_score"] == 0.0
    assert payload["problem_stack"][0]["edge_lock_score"] == 0.0
    assert payload["problem_stack"][0]["modeled_annual_upside_usd"] == 0.0
    assert payload["config"]["legacy_cli_parameters_only"] is True


def test_candidate_queue_is_bounded_and_control_candidate_is_not_financial_alpha():
    module = load_module()
    payload = module.build_payload()
    queue = payload["preregistered_candidate_queue"]

    assert 1 <= len(queue) <= 3
    assert all(candidate["current_alpha_proven"] is False for candidate in queue)
    assert all(candidate["live_trading_allowed"] is False for candidate in queue)
    assert all(candidate["capital_deployment_allowed"] is False for candidate in queue)

    control = next(
        candidate
        for candidate in queue
        if candidate["candidate_id"]
        == "brachistochrone_minimum_jerk_phase_locked_foc_hil_v1"
    )
    observations = control["source_observations"]
    assert control["classification"] == "non_trading_control_candidate"
    assert control["domain"] == "control_trajectory_engineering"
    assert control["financial_alpha_candidate"] is False
    assert control["trading_relevance"] == "none"
    assert observations["development_preselected"] is True
    assert observations["synthetic_confirmatory_pass"] is False
    assert observations["paired_aggregate_delta"] == 0.179587
    assert observations["paired_ci95"] == [0.177893, 0.181281]
    assert observations["paired_synthetic_scenario_count"] == 1000
    assert observations["all_condition_guardrails_passed"] is True
    assert observations["smoothness_candidate"] == 0.0884
    assert observations["smoothness_baseline"] == 0.0452
    assert observations["smoothness_candidate_minus_baseline"] == 0.0432
    assert "HIL" in control["preregistration"]["promotion_rule"]
    assert "physical-rig validation" in control["preregistration"]["promotion_rule"]


def test_markdown_keeps_claim_and_deployment_boundaries_visible():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)

    assert "NO_PROVEN_ALPHA_EDGE" in rendered
    assert "Current alpha proven: `false`" in rendered
    assert "Proven locks: `0`" in rendered
    assert "top_problem:" in rendered
    assert "(context only; not alpha)" in rendered
    assert "live_trading_allowed: `false`" in rendered
    assert "capital_deployment_allowed: `false`" in rendered
    assert "public_performance_claim_allowed: `false`" in rendered
    assert "physical_control_deployment_allowed: `false`" in rendered
