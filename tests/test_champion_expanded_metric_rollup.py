from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_CHAMPION_EXPANDED_METRIC_ROLLUP.py"


def load_module():
    spec = importlib.util.spec_from_file_location("champion_expanded_metric_rollup", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_expanded_metric_rollup_summarizes_champion_lanes_without_overclaiming():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "champion_expanded_metric_rollup_v1"
    assert summary["champion_family"] == "kuramoto_phase_coupling"
    assert summary["named_baseline"] == "kalman_filter"
    assert summary["holdout_count"] >= 20
    assert summary["holdout_wins"] >= 20
    assert summary["lane_count"] >= 5
    assert summary["strong_lane_count"] >= 3
    assert summary["total_baseline_comparisons"] >= 1_000
    assert summary["total_candidate_wins"] > summary["total_baseline_comparisons"] * 0.7
    assert summary["estimated_rows_replayed"] >= 7_000_000
    assert summary["numeric_samples_read"] >= 90_000
    assert summary["source_system_count"] >= 8
    assert summary["source_file_count"] >= 100
    assert summary["manifest_source_count"] >= 100
    assert summary["route_result_count"] >= 300
    assert summary["manifest_source_count"] >= summary["source_system_count"]
    assert "field_grade_source_hygiene_passed" in summary
    assert summary["suspicious_route_result_count"] >= 0
    assert summary["field_validation_claim_allowed"] is False
    assert summary["real_dollar_savings_claim_allowed"] is False
    assert summary["fixed_frozen_delta_price_claim_allowed"] is False
    assert len(payload["rollup_sha256"]) == 64


def test_expanded_metric_rollup_names_best_and_mixed_lanes():
    module = load_module()
    payload = module.build_payload()
    lanes = {row["lane"]: row for row in payload["lane_scoreboard"]}

    assert lanes["wave_resonance_timing"]["win_rate"] == 1.0
    assert lanes["wave_resonance_timing"]["baseline_comparisons"] >= 500
    assert lanes["wave_resonance_timing"]["status"] == "STRONG_INTERNAL_REPLAY_WIN"
    assert lanes["wave_resonance_timing"]["source_system_count"] >= 4
    assert lanes["wave_resonance_timing"]["source_file_count"] >= 20
    assert lanes["thermal_ventilation"]["win_rate"] == 1.0
    assert lanes["optimal_curve_transport"]["win_rate"] == 1.0
    assert 0.0 < lanes["energy_price_pressure_proxy"]["win_rate"] < 1.0
    assert lanes["energy_price_pressure_proxy"]["status"] == "MIXED_OR_BASELINE_STILL_COMPETITIVE"
    assert lanes["branching_transport"]["status"] == "MIXED_OR_BASELINE_STILL_COMPETITIVE"
    assert "internal locked replay" in lanes["wave_resonance_timing"]["claim_gate"]


def test_expanded_metric_rollup_keeps_source_health_and_next_sources_visible():
    module = load_module()
    payload = module.build_payload()
    source = payload["source_health"]

    assert source["enabled_sources"] >= 20
    assert source["measured_sources"] >= 18
    assert source["coverage_pct"] >= 75
    assert "AIRNOW" in source["measured_source_names"]
    assert "EIA" in source["measured_source_names"]
    assert "EPA_AQS" in source["failed_or_thin_source_names"]
    assert any("ISO/RTO" in item for item in source["missing_or_next_sources"])
    assert any("SAM.gov" in item for item in source["missing_or_next_sources"])
    assert payload["claim_state"]["source_conditioned_replay_claim_allowed"] is True


def test_expanded_metric_rollup_marks_source_hygiene_separately_from_wins():
    module = load_module()
    payload = module.build_payload()
    hygiene = payload["source_hygiene"]

    assert "field_grade_source_hygiene_passed" in hygiene
    assert "suspicious_route_result_count" in hygiene
    assert "stress/noise tests" in hygiene["claim_impact"]
    assert payload["summary"]["field_validation_claim_allowed"] is False
    assert len(payload["next_10_actions"]) == 10


def test_expanded_metric_rollup_adds_dataset_champion_cards():
    module = load_module()
    payload = module.build_payload()
    cards = payload["dataset_champion_cards"]

    assert len(cards) >= 12
    assert any(card["system"] == "energy_grid" for card in cards)
    assert any(card["lane"] == "wave_resonance_timing" for card in cards)
    assert all(card["claim_gate"] for card in cards)
    assert all("external owner" in card["claim_gate"] for card in cards)


def test_expanded_metric_rollup_markdown_is_reviewer_safe():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    dumped = json.dumps(payload).lower()

    assert "Champion Expanded Metric Rollup" in rendered
    assert "Lane Scoreboard" in rendered
    assert "Field-validation claim allowed: `false`" in rendered
    assert "Real-dollar savings claim allowed: `false`" in rendered
    assert "wave_resonance_timing" in rendered
    assert "realized savings" in dumped
    assert "guaranteed profit" not in dumped
    assert "guaranteed grant" not in dumped
    assert "money printer" not in dumped
