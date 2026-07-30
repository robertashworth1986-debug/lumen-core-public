import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MISSION_CONTROL = ROOT / "dashboard" / "mission_control.html"
EVIDENCE_LEDGER = ROOT / "dashboard" / "evidence" / "index.html"
PROOF_TO_PILOT = ROOT / "dashboard" / "proof_to_pilot.html"
DASHBOARD_PORTAL = ROOT / "dashboard" / "dashboard_portal.html"
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
    assert "['Canonical cards', canonicalCards.length" in page
    assert "External repeat-window evidence" not in page
    assert "external validation pending" in page


def test_proof_to_pilot_maps_field_protocol_and_reviewer_route_fields() -> None:
    page = PROOF_TO_PILOT.read_text(encoding="utf-8")
    field = json.loads((DATA / "field_validation_control_room.json").read_text(encoding="utf-8"))
    routes = json.loads((DATA / "field_validation_outreach_board.json").read_text(encoding="utf-8"))

    assert field["dashboard_cards"]
    assert {"title", "subtitle", "metric", "status"} <= set(field["dashboard_cards"][0])
    assert routes["schema"] == "field_validation_outreach_board_v2"
    assert routes["ranked_targets"]
    assert {
        "organization",
        "protocol_review_fit",
        "routing_status",
        "safe_first_ask",
        "safe_next_action",
        "send_now_allowed",
    } <= set(routes["ranked_targets"][0])
    assert routes["summary"]["send_ready_target_count"] == 0
    assert all(
        row["send_now_allowed"] is False for row in routes["ranked_targets"]
    )

    assert "row.pilot_question || row.subtitle" in page
    assert "row.metric != null" in page
    assert "row.organization || row.buyer_role" in page
    assert "row.protocol_review_fit" in page
    assert "row.routing_status || row.validation_lane" in page
    assert "row.safe_first_ask || row.safe_next_action || row.first_ask" in page


def test_proof_to_pilot_public_evidence_counts_remain_reconciled() -> None:
    register = json.loads((DATA / "measured_source_evidence_register.json").read_text(encoding="utf-8"))["summary"]
    measurement = json.loads((DATA / "live_source_measurement_maximizer.json").read_text(encoding="utf-8"))["summary"]
    harvest = json.loads((DATA / "live_evidence_max_harvest.json").read_text(encoding="utf-8"))["summary"]

    assert register["registry_total_sources"] > 0
    assert 0 < register["registry_enabled_sources"] <= register["registry_total_sources"]
    assert 0 < register["registry_measured_sources"] <= register["registry_enabled_sources"]
    assert register["registry_total_measured_rows"] > 0
    assert register["source_register_rows"] >= register["registry_total_sources"]
    assert register["current_probe_hash_backed_measured_sources"] > 0
    assert register["current_probe_total_measured_rows"] > 0
    assert register["registry_measured_without_snapshot_hash"]
    assert register["current_probe_failed_or_thin_sources"] >= 0
    assert register["reconciliation_required"] is True

    assert measurement["enabled_sources"] == (
        measurement["measured_sources"] + measurement["failed_or_thin_sources"]
    )
    assert measurement["coverage_pct"] == round(
        100.0 * measurement["measured_sources"] / measurement["enabled_sources"],
        2,
    )
    assert harvest["enabled_sources"] == measurement["enabled_sources"]
    assert harvest["measured_sources"] == measurement["measured_sources"]
    assert harvest["failed_or_thin_sources"] == measurement["failed_or_thin_sources"]
    assert harvest["total_measured_rows"] == measurement["total_measured_rows"]
    assert harvest["total_live_context_rows_evaluated"] > 0
    assert harvest["paired_inference_card_count"] > 0
    assert harvest["candidate_beats_named_baseline_count"] <= harvest[
        "paired_inference_card_count"
    ]
    assert harvest["holm_positive_card_count"] <= harvest[
        "paired_inference_card_count"
    ]
    assert harvest["cards_beating_all_registered_baselines_mean_count"] <= harvest[
        "paired_inference_card_count"
    ]
    assert harvest[
        "cards_beating_all_registered_baselines_global_holm_count"
    ] <= harvest["cards_beating_all_registered_baselines_mean_count"]


def test_proof_to_pilot_suppresses_ungated_modeled_value_surface() -> None:
    page = PROOF_TO_PILOT.read_text(encoding="utf-8")
    meter = json.loads((DATA / "live_proof_value_meter.json").read_text(encoding="utf-8"))
    value_gate = meter["value_gate"]

    assert value_gate["allowed_estimated_value_claims"] == 0
    assert value_gate["allowed_estimated_hourly_value_usd"] == 0
    assert value_gate["allowed_estimated_annual_value_usd"] == 0
    assert value_gate["ungated_input_projections_suppressed"] is True
    assert value_gate["safe_claim"]["claim_boundary"]
    assert "blocked_context_only_annual_value_usd" not in page
    assert "estimated_annual_value_surface_usd" not in page


def test_top_replay_source_has_no_globally_corrected_promotion() -> None:
    replay = json.loads((DATA / "top_geometry_live_replay_results.json").read_text(encoding="utf-8"))
    summary = replay["summary"]
    globally_positive = [
        (card["candidate_family_id"], comparison)
        for card in replay["replay_cards"]
        for comparison in card["baseline_comparisons"]
        if comparison["statistically_positive_after_global_holm"] is True
    ]

    assert replay["schema"] == "top_geometry_live_replay_results_v2"
    assert summary["registered_baseline_global_holm_positive_count"] == 0
    assert summary["registered_baseline_comparison_count"] == 22
    assert summary["cards_beating_all_registered_baselines_global_holm_count"] == 0
    assert summary["direct_measured_replay_count"] == 2
    assert summary["source_conditioned_synthetic_stress_count"] == 2
    assert summary["total_performance_rows_evaluated"] > 0
    assert summary["total_performance_rows_evaluated"] == sum(
        card["performance_rows_evaluated"] for card in replay["replay_cards"]
    )
    assert len(globally_positive) == summary["registered_baseline_global_holm_positive_count"]
    assert globally_positive == []
    assert all(
        card["ready_for_live_geometry_claim"] is False
        and card["ready_for_real_dollar_claim"] is False
        and card["field_validation"] is False
        for card in replay["replay_cards"]
    )


def test_current_public_claim_contract_blocks_stale_winner_and_value_language() -> None:
    portal = DASHBOARD_PORTAL.read_text(encoding="utf-8")
    ladder = (DATA / "field_validated_dollar_claim_ladder.json").read_text(
        encoding="utf-8"
    )
    ladder_payload = json.loads(ladder)
    current = ladder_payload["current_truth"]

    for blocked in (
        "Reviewer-Safe Winner State",
        "Current strongest family",
        "$4,520",
        "$39,595,200",
        "money printer",
        "current internal champion",
    ):
        assert blocked.lower() not in portal.lower()
        assert blocked.lower() not in ladder.lower()

    assert "No Current Performance Champion" in portal
    assert "482/1525" in portal
    assert "-0.508191" in portal
    assert "0/6" in portal
    assert current["modeled_dollar_projection_allowed_now"] is False
    assert current["allowed_estimated_hourly_value_usd"] == 0
    assert current["allowed_estimated_annual_value_usd"] == 0
    assert ladder_payload["service_pricing"][
        "service_price_is_model_outcome_value"
    ] is False


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
