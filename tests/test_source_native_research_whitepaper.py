from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT / "code" / "ops" / "BUILD_SOURCE_NATIVE_RESEARCH_WHITEPAPER.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "source_native_research_whitepaper", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_whitepaper_reports_current_negative_result_and_seals_payload():
    module = load_module()
    payload = module.build_payload(
        datetime(2026, 7, 29, 12, tzinfo=timezone.utc)
    )

    assert payload["schema"] == "lumencore.source_native_research_whitepaper.v1"
    assert payload["external_release_authorized"] is False
    assert payload["peer_reviewed"] is False
    assert payload["independently_validated"] is False
    assert payload["current_snapshot"]["registered_family_count"] == 140
    assert payload["current_snapshot"]["implementation_present_count"] == 35
    assert payload["current_snapshot"]["direct_candidate_source_card_count"] == 23
    assert payload["current_snapshot"]["executed_comparison_count"] == 126
    assert payload["current_snapshot"]["global_holm_positive_count"] == 0
    assert payload["current_snapshot"]["promotion_gate_pass_count"] == 0
    assert payload["current_snapshot"]["market_signal_candidate_count"] == 4
    assert payload["current_snapshot"]["market_signal_source_count"] == 3
    assert payload["current_snapshot"]["market_signal_comparison_count"] == 48
    assert (
        payload["current_snapshot"][
            "market_signal_inference_insufficient_count"
        ]
        == 48
    )
    assert (
        payload["current_snapshot"]["market_signal_global_holm_positive_count"]
        == 0
    )
    assert payload["current_snapshot"]["market_signal_panel_pair_count"] == 12
    assert payload["current_snapshot"]["market_signal_panel_comparison_count"] == 16
    assert (
        payload["current_snapshot"][
            "market_signal_panel_global_holm_positive_count"
        ]
        == 1
    )
    assert (
        payload["current_snapshot"][
            "market_signal_panel_all_baseline_mean_winner_count"
        ]
        == 0
    )
    assert payload["current_snapshot"]["market_signal_panel_promotion_count"] == 0
    assert (
        payload["market_signal_panel_result"]["narrow_exploratory_result"][
            "candidate_family_id"
        ]
        == "beast_strategy_trend"
    )
    assert (
        payload["market_signal_panel_result"]["narrow_exploratory_result"][
            "baseline_id"
        ]
        == "ridge_return_baseline"
    )
    assert (
        payload["market_signal_panel_result"]["narrow_exploratory_result"][
            "mean_risk_adjusted_score_delta"
        ]
        == 0.061277644465
    )
    assert (
        payload["market_signal_panel_result"]["narrow_exploratory_result"][
            "raw_p_value"
        ]
        == 0.00634765625
    )
    assert (
        payload["market_signal_panel_result"]["narrow_exploratory_result"][
            "global_holm_adjusted_p_value"
        ]
        == 0.04443359375
    )
    assert payload["market_signal_panel_result"]["promotion_count"] == 0
    assert (
        payload["market_signal_panel_result"]["confirmatory_inference_allowed"]
        is False
    )
    assert any(
        item["path"]
        == "out/ops/market_signal_kraken_panel_benchmark_latest.json"
        and item["exists"] is True
        for item in payload["canonical_source_receipts"]
    )
    assert payload["prospective_protocol"]["eligible_future_observation_count"] == 0
    assert payload["prospective_protocol"]["candidate_scientific_estimator_id"] == (
        "hurst_conditioned_multiscale_increment_heuristic_v1"
    )
    assert all(
        item["status"] == "HISTORICAL_SPECULATIVE_DO_NOT_UPLOAD"
        for item in payload["archived_legacy_whitepapers"]
    )

    unsealed = dict(payload)
    receipt = unsealed.pop("whitepaper_payload_sha256")
    assert module.stable_hash(unsealed) == receipt


def test_whitepaper_copy_is_claim_bounded():
    module = load_module()
    payload = module.build_payload(
        datetime(2026, 7, 29, 12, tzinfo=timezone.utc)
    )
    rendered = module.render_markdown(payload).lower()

    assert "promoted champions: `0`" in rendered
    assert "market-signal comparisons: `48`" in rendered
    assert "market-signal inferentially insufficient: `48`" in rendered
    assert "kraken panel pairs: `12`" in rendered
    assert "kraken panel comparisons: `16`" in rendered
    assert "kraken panel exploratory holm-positive comparisons: `1`" in rendered
    assert "kraken panel all-baseline mean winners: `0`" in rendered
    assert "kraken panel promotions: `0`" in rendered
    assert "one of 16 comparisons was positive" in rendered
    assert "mean unannualized risk-adjusted-score delta 0.061277644465" in rendered
    assert "raw exact sign-test p 0.00634765625" in rendered
    assert "global holm-adjusted p 0.04443359375" in rendered
    assert "zero candidates pass promotion" in rendered
    assert "no alpha, edge, or champion" not in rendered
    assert "performance champion" in rendered
    assert "30-50" not in rendered
    assert "trillion-dollar opportunity" not in rendered
    assert "zero-point energy" not in rendered
    assert "weather control" not in rendered
    assert "wormhole-adjacent" in rendered
    assert "blocked from upload" in rendered


def test_ledger_hash_is_verified():
    module = load_module()
    ledger = module.read_json(module.LEDGER_PATH)

    assert module.verify_ledger_hash(ledger) is True
