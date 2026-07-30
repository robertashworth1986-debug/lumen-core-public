from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "dashboard" / "proof_to_pilot.html"
DATA = ROOT / "dashboard" / "data"
OFFER_SOURCE = DATA / "evidence_protocol_review_fixed_scope_offer.json"


def _top_replay_validator_results(payloads: list[dict]) -> list[bool]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to exercise the inline replay-evidence validator")

    html = PAGE.read_text(encoding="utf-8")
    match = re.search(r"<script>([\s\S]*?)</script>", html)
    assert match is not None
    script = re.sub(r"\s*boot\(\);\s*$", "", match.group(1))
    request = json.dumps({"script": script, "payloads": payloads})
    runner = """
const fs = require('fs');
const vm = require('vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const context = {};
vm.createContext(context);
vm.runInContext(input.script, context);
process.stdout.write(JSON.stringify(input.payloads.map((payload) => context.topReplayEvidenceValid(payload))));
"""
    result = subprocess.run(
        [node, "-e", runner],
        input=request,
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout)


def _offer_validator_results(payloads: list[dict]) -> list[bool]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to exercise the inline offer-feed validator")

    html = PAGE.read_text(encoding="utf-8")
    match = re.search(r"<script>([\s\S]*?)</script>", html)
    assert match is not None
    script = re.sub(r"\s*boot\(\);\s*$", "", match.group(1))
    request = json.dumps({"script": script, "payloads": payloads})
    runner = """
const fs = require('fs');
const vm = require('vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const context = {};
vm.createContext(context);
vm.runInContext(input.script, context);
process.stdout.write(JSON.stringify(input.payloads.map((payload) => context.offerFeedValid(payload))));
"""
    result = subprocess.run(
        [node, "-e", runner],
        input=request,
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout)


def test_proof_to_pilot_dashboard_references_control_room_feed():
    html = PAGE.read_text(encoding="utf-8")

    assert "Proof-to-Pilot Review Room" in html
    assert "data/proof_to_pilot_control_room.json" in html
    assert "data/paid_pilot_outreach_queue.json" in html
    assert "data/field_validation_control_room.json" in html
    assert "data/field_validation_outreach_board.json" in html
    assert "data/quant_hub_reviewer_context.json" in html
    assert "data/live_proof_value_meter.json" in html
    assert "data/measured_source_evidence_register.json" in html
    assert "data/live_source_measurement_maximizer.json" in html
    assert "data/live_evidence_max_harvest.json" in html
    assert "data/top_geometry_live_replay_results.json" in html
    assert "data/evidence_protocol_review_fixed_scope_offer.json" in html
    assert "renderSummary" in html
    assert "renderGates" in html
    assert "renderCards" in html
    assert "renderArtifacts" in html
    assert "renderOutreachQueue" in html
    assert "renderFieldValidation" in html
    assert "renderFieldOutreach" in html
    assert "renderReviewerContext" in html
    assert "renderModeledOpportunity" in html
    assert "renderSourceRegister" in html
    assert "renderEvidenceHarvest" in html
    assert "renderTopReplay" in html
    assert "renderFrozenHybridStatus" in html
    assert "renderOffer" in html


def test_proof_to_pilot_dashboard_degrades_per_feed_and_fails_closed():
    html = PAGE.read_text(encoding="utf-8")

    assert "Promise.allSettled" in html
    assert "renderSummary({});" in html
    assert "renderGates({});" in html
    assert "renderUnavailableCards" in html
    assert "renderUnavailableArtifacts" in html
    assert "Claim and action gates remain closed." in html
    assert "evidenceFeedsReady ? control : {}" in html
    assert "renderReviewerContextUnavailable" in html
    assert "renderModeledOpportunityUnavailable" in html
    assert "renderSourceRegisterUnavailable" in html
    assert "renderSourceMeasurementUnavailable" in html
    assert "renderEvidenceHarvestUnavailable" in html
    assert "renderTopReplayUnavailable" in html
    assert "renderFrozenHybridUnavailable" in html
    assert "renderOfferUnavailable" in html
    assert "renderOfferIntegrityMismatch" in html
    assert "'topReplay'" in html
    assert "&& hybridCardReady" in html
    assert "degraded:" in html
    assert "Promise.all(Object.values(feeds).map(loadFeed))" not in html


def test_proof_to_pilot_dashboard_surfaces_fixed_scope_offer_without_claim_promotion():
    html = PAGE.read_text(encoding="utf-8")

    for visible_label in (
        "Buyer evidence protocol review",
        "Candidate fixed fee · founder approval required",
        "Duration after kickoff conditions are met",
        "Fixed scope",
        "Six deliverables",
        "No performance or savings claim:",
    ):
        assert visible_label in html

    for source_field in (
        "payload.product_name",
        "candidate_fixed_fee_usd",
        "duration_business_days",
        "registered_incumbent_baselines_max",
        "candidate_methods_max",
        "evaluation_windows_max",
        "payload.deliverables",
    ):
        assert source_field in html

    assert "does not guarantee performance, savings, revenue, funding, award, acceptance, or a model winner" in html
    assert "Founder approval is required before any price or outreach commitment." in html
    assert "$3,500" not in html


def test_proof_to_pilot_dashboard_fails_closed_for_missing_or_malformed_offer_feed():
    html = PAGE.read_text(encoding="utf-8")

    assert "function offerFeedValid(payload)" in html
    assert "renderOfferUnavailable({ reason: new Error('Offer feed not yet verified') });" in html
    assert "const offerValid = settled.offer.status === 'fulfilled' && offerFeedValid(offer);" in html
    assert "if (settled.offer.status === 'fulfilled' && offerValid) renderOffer(offer);" in html
    assert "else if (settled.offer.status === 'fulfilled') renderOfferIntegrityMismatch();" in html
    assert "else renderOfferUnavailable(settled.offer);" in html
    assert "No product terms, price, duration, scope, or deliverables are inferred" in html
    assert "performance and savings claims remain prohibited." in html


def test_offer_validator_rejects_terms_or_controls_that_are_not_public_safe():
    offer = json.loads(OFFER_SOURCE.read_text(encoding="utf-8"))
    invalid_payloads: list[dict] = []

    missing_deliverable = copy.deepcopy(offer)
    missing_deliverable["deliverables"].pop()
    invalid_payloads.append(missing_deliverable)

    string_price = copy.deepcopy(offer)
    string_price["commercial_terms"]["candidate_fixed_fee_usd"] = "3500"
    invalid_payloads.append(string_price)

    committed_price = copy.deepcopy(offer)
    committed_price["commercial_terms"]["price_committed"] = True
    invalid_payloads.append(committed_price)

    founder_approval_removed = copy.deepcopy(offer)
    founder_approval_removed["commercial_terms"]["founder_price_approval_required"] = False
    invalid_payloads.append(founder_approval_removed)

    production_access_enabled = copy.deepcopy(offer)
    production_access_enabled["scope_limits"]["production_access"] = True
    invalid_payloads.append(production_access_enabled)

    performance_claim_enabled = copy.deepcopy(offer)
    performance_claim_enabled["controls"]["performance_claim_allowed"] = True
    invalid_payloads.append(performance_claim_enabled)

    savings_claim_enabled = copy.deepcopy(offer)
    savings_claim_enabled["controls"]["savings_claim_allowed"] = True
    invalid_payloads.append(savings_claim_enabled)

    blank_product_name = copy.deepcopy(offer)
    blank_product_name["product_name"] = " "
    invalid_payloads.append(blank_product_name)

    invalid_digest = copy.deepcopy(offer)
    invalid_digest["payload_sha256"] = "not-a-digest"
    invalid_payloads.append(invalid_digest)

    results = _offer_validator_results([offer, *invalid_payloads])
    assert results == [True, *([False] * len(invalid_payloads))]


def test_proof_to_pilot_dashboard_renders_accessible_holographic_evidence():
    html = PAGE.read_text(encoding="utf-8")
    reviewer = json.loads((DATA / "quant_hub_reviewer_context.json").read_text(encoding="utf-8"))

    assert len(reviewer["proof_cards"]) >= 9
    assert 'id="canonical-proof-cards" role="list"' in html
    assert 'id="reviewer-count-note" aria-live="polite"' in html
    assert "`${cards.length} source-backed proof ${cards.length === 1 ? 'card' : 'cards'}" in html
    assert "Nine source-backed proof cards" not in html
    assert "cards.map(constellationCardNode)" in html
    assert "constellation-card" in html
    assert "holo-panel" in html
    assert "perspective: 1100px" in html
    assert "prefers-reduced-motion: reduce" in html
    assert "forced-colors: active" in html
    assert ":focus-visible" in html
    assert ".list li { break-inside: avoid; margin-bottom: 8px; overflow-wrap: anywhere; }" in html
    assert "external assets" not in html.lower()


def test_proof_to_pilot_dashboard_whitelists_modeled_value_fields():
    html = PAGE.read_text(encoding="utf-8")

    for allowed_key in (
        "allowed_estimated_value_claims",
        "allowed_estimated_hourly_value_usd",
        "allowed_estimated_annual_value_usd",
        "safeClaim.claim_boundary",
    ):
        assert allowed_key in html
    for excluded_key in (
        "live_breadth_raw_live_measured_annual_value_usd",
        "blocked_context_only_annual_value_usd",
        "sector_capture_math",
        "capture_from_allowed_signal",
    ):
        assert excluded_key not in html
    assert "Bounded estimated signal / hour" in html
    assert "Bounded estimated signal / year" in html
    assert "MODELED · BOUNDED · NOT REALIZED" in html


def test_proof_to_pilot_dashboard_separates_source_layers_and_inference():
    html = PAGE.read_text(encoding="utf-8")

    for source_key in (
        "registry_total_sources",
        "registry_enabled_sources",
        "registry_measured_sources",
        "registry_total_measured_rows",
        "current_probe_hash_backed_measured_sources",
        "current_probe_total_measured_rows",
        "registry_measured_without_snapshot_hash",
        "current_probe_failed_or_thin_sources",
        "reconciliation_required",
    ):
        assert source_key in html
    for safe_label in (
        "registered sources",
        "registry-measured /",
        "continuity-layer rows",
        "current hash-backed measured /",
        "current-probe rows",
        "measured registry-only sources need hash refresh",
        "current failed/thin",
        "candidate mean wins",
        "Holm-positive",
        "beat all registered baselines by mean",
        "globally Holm-positive",
    ):
        assert safe_label in html
    assert "30 measured" not in html.lower()
    assert "30+ measured" not in html.lower()


def test_proof_to_pilot_dashboard_derives_exact_global_holm_rows_from_source_fields():
    html = PAGE.read_text(encoding="utf-8")

    for source_key in (
        "registered_baseline_global_holm_positive_count",
        "registered_baseline_comparison_count",
        "cards_beating_all_registered_baselines_global_holm_count",
        "statistically_positive_after_global_holm === true",
        "candidate_family_id",
        "baseline_family_id",
        "paired_unit_count",
        "win_count",
        "loss_count",
        "tie_count",
        "mean_score_delta",
        "raw_two_sided_sign_test_p_value",
        "global_holm_adjusted_p_value",
        "bootstrap_mean_delta_ci95",
    ):
        assert source_key in html

    for distinction in (
        "comparison-level passes",
        "complete cards pass all registered baselines",
        "Comparison-level passes remain distinct from complete-card promotion",
    ):
        assert distinction in html

    # Candidate and baseline identities must come from the replay feed, not page copy.
    assert "fractal_brownian_surface" not in html
    assert "exponential_smoothing" not in html
    assert "moving_average" not in html


def test_proof_to_pilot_dashboard_fails_closed_when_top_replay_is_unavailable():
    html = PAGE.read_text(encoding="utf-8")

    assert "['reviewerContext', 'valueMeter', 'sourceRegister', 'sourceMeasurement', 'evidenceHarvest', 'topReplay']" in html
    assert "const topReplayValid = settled.topReplay.status === 'fulfilled' && topReplayEvidenceValid(topReplay);" in html
    assert "&& hybridCardReady && topReplayValid" in html
    assert "if (settled.topReplay.status === 'fulfilled' && topReplayValid) renderTopReplay(topReplay);" in html
    assert "else if (settled.topReplay.status === 'fulfilled') renderTopReplayIntegrityMismatch();" in html
    assert "else renderTopReplayUnavailable(settled.topReplay);" in html
    assert "Comparison-level inference unavailable" in html
    assert "0 complete-card promotions inferred" in html
    assert "All claim and action gates remain closed." in html
    assert "Top replay evidence unavailable · freshness unknown" in html


def test_proof_to_pilot_dashboard_rejects_top_replay_integrity_mismatch():
    html = PAGE.read_text(encoding="utf-8")
    assert "function topReplayEvidenceValid(payload)" in html
    assert "positiveCount !== positiveRows.length" in html
    assert "actualComparisonCount = replayCards.reduce" in html
    assert "comparisonCount !== actualComparisonCount" in html
    assert "candidate_beats_all_registered_baselines_after_global_holm === true" in html
    assert "completeCardCount !== actualCompleteCardCount" in html
    assert "typeof row.candidate === 'string'" in html
    assert "row.candidate.trim().length > 0" in html
    assert "typeof row.baseline === 'string'" in html
    assert "row.baseline.trim().length > 0" in html
    assert "row.wins + row.losses + row.ties === row.pairedUnits" in html
    for required_check in (
        "finiteStatistic(row.meanScoreDelta)",
        "Number(row.meanScoreDelta) > 0",
        "rawP >= 0",
        "rawP <= 1",
        "globalHolmP >= 0",
        "globalHolmP <= 0.05",
        "ci95.length === 2",
        "ci95.every(finiteStatistic)",
        "Number(ci95[0]) > 0",
    ):
        assert required_check in html
    assert "Integrity mismatch: the global-Holm summary does not reconcile with complete strict comparison rows" in html
    assert "Top replay evidence unavailable · integrity mismatch · claim gates closed" in html


def test_top_replay_validator_behavior_rejects_count_and_positive_row_mutations():
    replay = json.loads((DATA / "top_geometry_live_replay_results.json").read_text(encoding="utf-8"))
    invalid_payloads: list[dict] = []

    comparison_count_mismatch = copy.deepcopy(replay)
    comparison_count_mismatch["summary"]["registered_baseline_comparison_count"] += 1
    invalid_payloads.append(comparison_count_mismatch)

    complete_card_mismatch = copy.deepcopy(replay)
    complete_card_mismatch["replay_cards"][0]["baseline_gauntlet"]["candidate_beats_all_registered_baselines_after_global_holm"] = True
    invalid_payloads.append(complete_card_mismatch)

    positive_replay = copy.deepcopy(replay)
    positive_card = next(
        card for card in positive_replay["replay_cards"] if card["baseline_comparisons"]
    )
    positive_comparison = positive_card["baseline_comparisons"][0]
    positive_comparison["statistically_positive_after_global_holm"] = True
    positive_comparison["global_holm_adjusted_p_value"] = 0.01
    positive_comparison["paired_inference"].update(
        {
            "paired_unit_count": 10,
            "win_count": 10,
            "loss_count": 0,
            "tie_count": 0,
            "mean_score_delta": 0.2,
            "raw_two_sided_sign_test_p_value": 0.001,
            "bootstrap_mean_delta_ci95": [0.1, 0.3],
        }
    )
    positive_replay["summary"]["registered_baseline_global_holm_positive_count"] = 1

    def positive_pair(payload: dict) -> tuple[dict, dict]:
        for card in payload["replay_cards"]:
            for comparison in card["baseline_comparisons"]:
                if comparison["statistically_positive_after_global_holm"] is True:
                    return card, comparison
        raise AssertionError("Expected a strict global-Holm-positive comparison")

    candidate_missing = copy.deepcopy(positive_replay)
    positive_pair(candidate_missing)[0]["candidate_family_id"] = " "
    invalid_payloads.append(candidate_missing)

    baseline_missing = copy.deepcopy(positive_replay)
    positive_pair(baseline_missing)[1]["baseline_family_id"] = ""
    invalid_payloads.append(baseline_missing)

    nonpositive_mean = copy.deepcopy(positive_replay)
    positive_pair(nonpositive_mean)[1]["paired_inference"]["mean_score_delta"] = 0
    invalid_payloads.append(nonpositive_mean)

    nonpositive_ci = copy.deepcopy(positive_replay)
    positive_pair(nonpositive_ci)[1]["paired_inference"]["bootstrap_mean_delta_ci95"][0] = 0
    invalid_payloads.append(nonpositive_ci)

    raw_p_out_of_range = copy.deepcopy(positive_replay)
    positive_pair(raw_p_out_of_range)[1]["paired_inference"]["raw_two_sided_sign_test_p_value"] = 1.01
    invalid_payloads.append(raw_p_out_of_range)

    raw_p_negative = copy.deepcopy(positive_replay)
    positive_pair(raw_p_negative)[1]["paired_inference"]["raw_two_sided_sign_test_p_value"] = -0.000001
    invalid_payloads.append(raw_p_negative)

    adjusted_p_out_of_range = copy.deepcopy(positive_replay)
    positive_pair(adjusted_p_out_of_range)[1]["global_holm_adjusted_p_value"] = 0.050001
    invalid_payloads.append(adjusted_p_out_of_range)

    adjusted_p_negative = copy.deepcopy(positive_replay)
    positive_pair(adjusted_p_negative)[1]["global_holm_adjusted_p_value"] = -0.000001
    invalid_payloads.append(adjusted_p_negative)

    results = _top_replay_validator_results([replay, positive_replay, *invalid_payloads])
    assert results == [True, True, *([False] * len(invalid_payloads))]


def test_proof_to_pilot_dashboard_derives_frozen_hybrid_collection_status():
    html = PAGE.read_text(encoding="utf-8")

    for source_key in (
        "row.proof_id === 'eia_prospective_router'",
        "sourceCard.status",
        "first_allowed_target_date",
        "prediction_count",
        "settlement_count",
        "promotion_evaluation_complete",
        "preliminary_30_days_ready",
        "confirmatory_90_days_ready",
        "durability_180_days_ready",
        "sourceCard.claim_boundary",
    ):
        assert source_key in html

    assert 'id="frozen-hybrid-status" aria-live="polite"' in html
    assert "Collecting evidence · has not passed" in html
    assert "The hybrid is not treated as passed and all claim gates remain closed." in html


def test_proof_to_pilot_dashboard_keeps_claim_gates_visible():
    html = PAGE.read_text(encoding="utf-8")

    required_gates = [
        "Manual reviewed outreach allowed",
        "Paid evaluation offer allowed",
        "Buyer-authorized pilot scoping ready",
        "Field-validation claim allowed",
        "Realized-savings claim allowed",
        "Fixed-dollar delta claim allowed",
        "Bulk email allowed",
        "Live trading/autonomous execution allowed",
        "Contact scraping allowed",
        "Send without user review allowed",
    ]

    for gate in required_gates:
        assert gate in html


def test_proof_to_pilot_dashboard_is_buyer_safe_not_bulk_send_surface():
    html = PAGE.read_text(encoding="utf-8").lower()

    assert "manual reviewed outreach" in html
    assert "paid pilot outreach" not in html or "bulk email" in html
    assert "does not authorize bulk email" in html
    assert "fixed-dollar frozen-delta claims" in html
    assert "field-validation claims" in html
    assert "it is not a send engine" in html

    forbidden = [
        "live_order_placement",
        "market_order",
        "guaranteed profit",
        "award certainty",
        "mass mailer",
        "autonomous send",
        ("smt" + "p"),
        ("gm" + "ail" + " ap" + "i"),
        ("api" + "_key"),
        ("cl" + "ient" + "_sec" + "ret"),
        ("private" + "_key"),
    ]
    for phrase in forbidden:
        assert phrase not in html
