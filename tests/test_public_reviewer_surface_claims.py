import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MISSION_CONTROL = ROOT / "dashboard" / "mission_control.html"
EVIDENCE_LEDGER = ROOT / "dashboard" / "evidence" / "index.html"
PROOF_TO_PILOT = ROOT / "dashboard" / "proof_to_pilot.html"
DATA = ROOT / "dashboard" / "data"


def test_public_reviewer_surfaces_avoid_inflated_status_language() -> None:
    mission = MISSION_CONTROL.read_text(encoding="utf-8").lower()
    evidence = EVIDENCE_LEDGER.read_text(encoding="utf-8").lower()

    for blocked in (
        "gov-grade alpha coherence",
        "federal evidence-chain grade",
        "institutional ready",
        "undeniable evidence",
        "no cherry-picking",
        "all evidence sha-256 hash-chained",
        "historical closed live trades",
        "rough working model: $1,000",
    ):
        assert blocked not in mission
        assert blocked not in evidence

    assert "external validation pending" in mission
    assert "external field validation remains pending" in evidence


def test_public_linkedin_route_uses_profile_and_local_auth_is_host_gated() -> None:
    mission = MISSION_CONTROL.read_text(encoding="utf-8")

    assert 'href="https://www.linkedin.com/in/robert-ashworth-40a9b7376"' in mission
    assert "const localOperator = location.protocol === 'file:'" in mission
    assert "if (localOperator)" in mission


def test_proof_to_pilot_surface_tracks_current_feed_schema() -> None:
    page = PROOF_TO_PILOT.read_text(encoding="utf-8")

    for current_key in (
        "top_cards",
        "artifact_health",
        "claim_controls",
        "dashboard_cards",
        "ranked_targets",
    ):
        assert current_key in page
    assert "External repeat-window evidence" not in page
    assert "external validation pending" in page


def test_proof_to_pilot_public_evidence_counts_remain_reconciled() -> None:
    register = json.loads((DATA / "measured_source_evidence_register.json").read_text(encoding="utf-8"))["summary"]
    measurement = json.loads((DATA / "live_source_measurement_maximizer.json").read_text(encoding="utf-8"))["summary"]
    harvest = json.loads((DATA / "live_evidence_max_harvest.json").read_text(encoding="utf-8"))["summary"]

    assert register["registry_total_sources"] == 30
    assert register["registry_enabled_sources"] == 29
    assert register["registry_measured_sources"] == 25
    assert register["registry_total_measured_rows"] == 2580
    assert register["current_probe_hash_backed_measured_sources"] == 23
    assert register["current_probe_total_measured_rows"] == 2377
    assert register["registry_measured_without_snapshot_hash"] == ["ALPACA", "KRAKEN"]
    assert register["current_probe_failed_or_thin_sources"] == 4
    assert register["reconciliation_required"] is True

    assert measurement["coverage_pct"] == 86.21
    assert harvest["total_live_context_rows_evaluated"] == 4874
    assert harvest["paired_inference_card_count"] == 5
    assert harvest["candidate_beats_named_baseline_count"] == 4
    assert harvest["holm_positive_card_count"] == 0
    assert harvest["cards_beating_all_registered_baselines_mean_count"] == 4
    assert harvest["cards_beating_all_registered_baselines_global_holm_count"] == 0


def test_proof_to_pilot_uses_only_bounded_modeled_value_surface() -> None:
    page = PROOF_TO_PILOT.read_text(encoding="utf-8")
    meter = json.loads((DATA / "live_proof_value_meter.json").read_text(encoding="utf-8"))
    value_gate = meter["value_gate"]

    assert value_gate["allowed_estimated_value_claims"] == 10
    assert value_gate["allowed_estimated_hourly_value_usd"] == 4520.0
    assert value_gate["allowed_estimated_annual_value_usd"] == 39595200.0
    assert value_gate["safe_claim"]["claim_boundary"]
    assert "blocked_context_only_annual_value_usd" not in page
    assert "estimated_annual_value_surface_usd" not in page


def test_top_replay_source_exposes_two_comparison_passes_without_card_promotion() -> None:
    replay = json.loads((DATA / "top_geometry_live_replay_results.json").read_text(encoding="utf-8"))
    summary = replay["summary"]
    globally_positive = [
        (card["candidate_family_id"], comparison)
        for card in replay["replay_cards"]
        for comparison in card["baseline_comparisons"]
        if comparison["statistically_positive_after_global_holm"] is True
    ]

    assert summary["registered_baseline_global_holm_positive_count"] == 2
    assert summary["registered_baseline_comparison_count"] == 21
    assert summary["cards_beating_all_registered_baselines_global_holm_count"] == 0
    assert len(globally_positive) == summary["registered_baseline_global_holm_positive_count"]
    assert {
        (candidate, comparison["baseline_family_id"])
        for candidate, comparison in globally_positive
    } == {
        ("fractal_brownian_surface", "exponential_smoothing"),
        ("fractal_brownian_surface", "moving_average"),
    }

    for _, comparison in globally_positive:
        inference = comparison["paired_inference"]
        assert inference["paired_unit_count"] > 0
        assert inference["win_count"] + inference["loss_count"] + inference["tie_count"] == inference["paired_unit_count"]
        assert inference["mean_score_delta"] > 0
        assert inference["raw_two_sided_sign_test_p_value"] >= 0
        assert comparison["global_holm_adjusted_p_value"] >= inference["raw_two_sided_sign_test_p_value"]
        assert len(inference["bootstrap_mean_delta_ci95"]) == 2


def test_frozen_hybrid_source_remains_collecting_and_not_passed() -> None:
    reviewer = json.loads((DATA / "quant_hub_reviewer_context.json").read_text(encoding="utf-8"))
    hybrid = next(card for card in reviewer["proof_cards"] if card["proof_id"] == "eia_prospective_router")
    facts = hybrid["facts"]

    assert hybrid["status"] == "WAITING_FOR_FIRST_ELIGIBLE_FORECAST"
    assert facts["prediction_count"] == 0
    assert facts["settlement_count"] == 0
    assert facts["promotion_evaluation_complete"] is False
    assert facts["preliminary_30_days_ready"] is False
    assert facts["confirmatory_90_days_ready"] is False
    assert facts["durability_180_days_ready"] is False
    assert hybrid["claim_boundary"]
