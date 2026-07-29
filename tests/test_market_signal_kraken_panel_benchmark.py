from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "code"
    / "ops"
    / "BUILD_MARKET_SIGNAL_KRAKEN_PANEL_BENCHMARK.py"
)
FIXED_GENERATED_UTC = "2026-07-29T20:15:00+00:00"


@pytest.fixture(scope="module")
def module():
    spec = importlib.util.spec_from_file_location(
        "market_signal_kraken_panel_benchmark",
        SCRIPT,
    )
    loaded = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(loaded)
    return loaded


@pytest.fixture(scope="module")
def payload(module):
    return module.build_payload(FIXED_GENERATED_UTC)


def test_protocol_is_pre_scoring_hash_bound_and_fail_closed(module):
    protocol = module.read_json(module.PROTOCOL_PATH)

    assert protocol["schema"] == (
        "market_signal_kraken_panel_benchmark_protocol_v1"
    )
    assert protocol["mode"] == "retrospective_development_paper_replay"
    assert (
        protocol["selection"][
            "candidate_or_baseline_scores_used_in_selection"
        ]
        is False
    )
    assert protocol["selection"]["legacy_alpha_priority_enabled"] is False
    assert (
        protocol["inference"]["confirmatory_inference_allowed"] is False
    )
    assert protocol["inference"]["promotion_eligible"] is False
    assert all(
        value is False
        for value in protocol["claim_controls"].values()
    )


def test_collector_receipt_and_exact_panel_files_are_verified(
    payload,
):
    receipt = payload["inputs"]["collector_receipt"]
    panel = payload["inputs"]["panel_files"]

    assert receipt["execution_authorized"] is False
    assert receipt["pairs_discovered"] == 689
    assert receipt["pairs_selected"] == 20
    assert receipt["pairs_updated"] == 20
    assert receipt["pair_errors"] == 0
    assert len(receipt["file_sha256"]) == 64
    assert [row["pair"] for row in panel] == [
        "BTC/USD",
        "ETH/USD",
        "SOL/USD",
        "XRP/USD",
        "ADA/USD",
        "HYPE/USD",
        "SUI/USD",
        "XMR/USD",
        "LTC/USD",
        "DOGE/USD",
        "ZEC/USD",
        "TAO/USD",
    ]
    assert all(
        row["row_count"] == 720
        and row["hash_verified"] is True
        and len(row["file_sha256"]) == 64
        for row in panel
    )


def test_panel_repairs_series_count_without_claiming_independence(
    payload,
):
    summary = payload["implementation_summary"]

    assert summary["registered_candidate_count"] == 4
    assert summary["implemented_candidate_count"] == 4
    assert summary["registered_baseline_count"] == 4
    assert summary["implemented_baseline_count"] == 4
    assert summary["source_count"] == 1
    assert summary["source_series_count"] == 12
    assert summary["strategy_source_series_result_count"] == 96
    assert summary["evaluation_observation_count_per_series"] == [660]
    assert all(
        row["source_series_cluster_count"] == 12
        and row["pair_count_floor_met"] is True
        and row["independence_assumption_confirmed"] is False
        and row["confirmatory_inference_allowed"] is False
        and row["promotion_eligible"] is False
        for row in payload["comparisons"]
    )


def test_every_strategy_uses_the_same_future_returns_and_timestamps(
    payload,
):
    for series_row in payload["series_results"]:
        assert len(series_row["strategy_results"]) == 8
        assert {
            row["future_return_sha256"]
            for row in series_row["strategy_results"]
        } == {series_row["future_return_sha256"]}
        assert {
            row["evaluation_timestamp_sha256"]
            for row in series_row["strategy_results"]
        } == {series_row["evaluation_timestamp_sha256"]}
        assert {
            row["metrics"]["observation_count"]
            for row in series_row["strategy_results"]
        } == {series_row["evaluation_observation_count"]}


def test_comparison_scope_holm_and_no_promotion_are_explicit(
    payload,
):
    summary = payload["result_summary"]

    assert summary["candidate_source_baseline_comparison_count"] == 16
    assert 0 <= summary["comparison_mean_win_count"] <= 16
    assert 0 <= summary["exploratory_global_holm_positive_count"] <= 16
    assert summary["promotion_count"] == 0
    assert summary["confirmatory_inference_allowed"] is False
    assert len(payload["candidate_diagnostics"]) == 4
    assert all(
        row["promotion_eligible"] is False
        and row["promotion_status"]
        == "BLOCKED_RETROSPECTIVE_COMMON_MARKET_FACTOR"
        for row in payload["candidate_diagnostics"]
    )
    assert all(
        0.0 <= row["raw_cluster_sign_test_p_value"] <= 1.0
        and 0.0 <= row["global_holm_adjusted_p_value"] <= 1.0
        for row in payload["comparisons"]
    )


def test_protocol_or_file_drift_fails_closed(module):
    protocol = module.read_json(module.PROTOCOL_PATH)
    changed = copy.deepcopy(protocol)
    changed["collector_receipt"]["file_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="Collector receipt hash drift"):
        module.validate_protocol(changed)

    changed = copy.deepcopy(protocol)
    changed["selection"]["panel"][0]["file_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="Panel file hash drift"):
        module.validate_protocol(changed)


def test_payload_is_deterministic_for_fixed_inputs(module, payload):
    rebuilt = module.build_payload(FIXED_GENERATED_UTC)

    assert rebuilt == payload
    without_payload_hash = {
        key: value
        for key, value in rebuilt.items()
        if key != "payload_sha256"
    }
    assert rebuilt["payload_sha256"] == module.BASE.stable_sha256(
        without_payload_hash
    )


def test_outputs_and_documentation_preserve_claim_boundary(
    module,
    payload,
    tmp_path,
):
    out_json = tmp_path / "benchmark.json"
    dashboard_json = tmp_path / "dashboard.json"
    manifest_json = tmp_path / "manifest.json"
    doc_path = tmp_path / "benchmark.md"

    manifest = module.write_outputs(
        payload,
        out_json=out_json,
        dashboard_json=dashboard_json,
        manifest_json=manifest_json,
        doc_path=doc_path,
    )
    written = json.loads(out_json.read_text(encoding="utf-8"))
    text = doc_path.read_text(encoding="utf-8")

    assert written == payload
    assert manifest["output"]["file_sha256"] == (
        module.BASE.file_sha256(out_json)
    )
    assert manifest["documentation"]["file_sha256"] == (
        module.BASE.file_sha256(doc_path)
    )
    assert (
        manifest["public_feed"]["public_performance_claim_allowed"]
        is False
    )
    assert manifest["external_actions"] == []
    assert "**No candidate is promoted.**" in text
    assert "Pairs share an exchange" in text
    assert "Promotions: `0`" in text
