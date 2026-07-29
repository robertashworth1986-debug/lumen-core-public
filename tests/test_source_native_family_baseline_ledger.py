from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "code"
    / "ops"
    / "BUILD_SOURCE_NATIVE_FAMILY_BASELINE_LEDGER.py"
)


@pytest.fixture(scope="module")
def module_and_payload():
    spec = importlib.util.spec_from_file_location(
        "source_native_family_baseline_ledger", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module, module.build_payload()


def test_ledger_accounts_for_every_family_and_direct_route(
    module_and_payload,
):
    _, payload = module_and_payload
    summary = payload["summary"]

    assert payload["schema"] == "source_native_family_baseline_ledger_v1"
    assert summary["registered_family_count"] == 140
    assert summary["implementation_present_count"] == 35
    assert summary["implementation_required_count"] == 105
    assert summary["lane_count"] == 12
    assert summary["lane_with_qualified_direct_source_count"] == 3
    assert summary["lane_with_executable_direct_adapter_count"] == 3
    assert summary["qualified_direct_source_link_count"] == 10
    assert summary["family_in_direct_source_lane_count"] == 68
    assert summary["implemented_family_in_direct_source_lane_count"] == 10
    assert len(payload["family_ledger"]) == 140
    assert len(payload["source_baseline_route_ledger"]) == 1848


def test_ledger_executes_every_current_adapter_without_promoting_subset_wins(
    module_and_payload,
):
    _, payload = module_and_payload
    summary = payload["summary"]

    assert summary["direct_candidate_family_count"] == 10
    assert summary["direct_candidate_source_card_count"] == 23
    assert summary["executed_direct_source_baseline_comparison_count"] == 126
    assert summary["confirmatory_protocol_comparison_count"] == 6
    assert summary["exploratory_direct_comparison_count"] == 120
    assert summary["blocked_direct_adapter_route_count"] == 0
    assert summary["blocked_implementation_route_count"] == 1722
    assert summary["individual_comparison_global_holm_positive_count"] == 0
    assert summary["candidate_source_beats_every_baseline_mean_count"] == 1
    assert (
        summary[
            "candidate_source_beats_every_baseline_global_holm_count"
        ]
        == 0
    )
    assert summary["internal_source_native_promotion_gate_pass_count"] == 0
    assert all(
        card["public_performance_claim_allowed"] is False
        and card["field_validation_claim_allowed"] is False
        and card["real_dollar_savings_claim_allowed"] is False
        and card["live_execution_allowed"] is False
        for card in payload["candidate_source_cards"]
    )


def test_market_signal_families_run_source_specific_baselines_without_promotion(
    module_and_payload,
):
    _, payload = module_and_payload
    summary = payload["summary"]

    assert summary["market_signal_candidate_count"] == 4
    assert summary["market_signal_source_count"] == 3
    assert summary["market_signal_comparison_count"] == 48
    assert summary["market_signal_descriptive_mean_win_count"] == 22
    assert summary["market_signal_inference_insufficient_count"] == 48
    assert summary["market_signal_global_holm_positive_count"] == 0
    assert summary["market_signal_promoted_candidate_count"] == 0

    market_cards = [
        card
        for card in payload["candidate_source_cards"]
        if card["lane"] == "market_signal_geometry"
    ]
    assert len(market_cards) == 12
    assert {
        card["source"] for card in market_cards
    } == {"KRAKEN_PUBLIC", "TWELVE_DATA", "ALPHAVANTAGE"}
    assert all(
        card["source_specific_baseline_count"] == 4
        and card["inference_sufficient_comparison_count"] == 0
        and card["internal_source_native_promotion_gate_passed"] is False
        and len(card["baseline_comparisons"]) == 4
        for card in market_cards
    )
    assert all(
        comparison["global_holm_adjusted_p_value"] == 1.0
        and comparison["statistically_positive_after_global_holm"] is False
        and comparison["paired_inference"]["inference_sufficient"] is False
        for card in market_cards
        for comparison in card["baseline_comparisons"]
    )


def test_overlapping_retrospective_pairs_do_not_create_subset_research_leads(
    module_and_payload,
):
    _, payload = module_and_payload
    leads = {
        (
            row["source"],
            row["candidate_family_id"],
            row["baseline_family_id"],
        )
        for row in payload["positive_subset_research_leads"]
    }

    assert leads == set()
    retired = payload["retired_retrospective_findings"]
    assert {row["source"] for row in retired} == {"FRED", "TWELVE_DATA"}
    assert all(row["promotion_claim_allowed"] is False for row in retired)
    assert all("retired_after" in row["disposition"] for row in retired)


def test_family_states_separate_confirmatory_exploratory_and_blocked_work(
    module_and_payload,
):
    _, payload = module_and_payload
    families = {
        row["family_id"]: row for row in payload["family_ledger"]
    }

    lissajous = families["lissajous_phase_paths"]
    assert lissajous["confirmatory_direct_route_count"] == 6
    assert lissajous["beats_every_source_native_baseline_count"] == 0

    kuramoto = families["kuramoto_phase_coupling"]
    assert kuramoto["exploratory_direct_route_count"] == 6
    assert kuramoto["globally_corrected_subset_win_count"] == 0

    fractal = families["fractal_brownian_surface"]
    assert fractal["exploratory_direct_route_count"] == 48
    assert fractal["globally_corrected_subset_win_count"] == 0
    assert fractal["beats_every_source_native_baseline_count"] == 0

    heart = families["heart_rate_variability_control"]
    assert heart["implementation_present"] is True
    assert heart["exploratory_direct_route_count"] == 6
    assert heart["blocked_adapter_route_count"] == 0
    assert heart["beats_every_source_native_baseline_count"] == 0

    market = families["order_book_liquidity_contours"]
    assert market["implementation_present"] is False
    assert market["blocked_implementation_route_count"] == 12


def test_rendered_ledger_states_no_alpha_and_preserves_claim_boundaries(
    module_and_payload,
):
    module, payload = module_and_payload
    rendered = module.render_markdown(payload)
    text = rendered.lower()

    assert "current alpha or champion: `none`" in text
    assert "executed comparisons: `126`" in text
    assert "globally corrected individual subset wins: `0`" in text
    assert "full source-native gauntlet passes: `0`" in text
    assert "not a champion, alpha claim, field result, or dollar claim" in text
    assert payload["summary"]["public_performance_claim_allowed"] is False
    assert payload["summary"]["field_validation_claim_allowed"] is False
    assert payload["summary"]["real_dollar_savings_claim_allowed"] is False
    assert len(payload["ledger_sha256"]) == 64
