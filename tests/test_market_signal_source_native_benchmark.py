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
    / "BUILD_MARKET_SIGNAL_SOURCE_NATIVE_BENCHMARK.py"
)
FIXED_GENERATED_UTC = "2026-07-29T00:00:00+00:00"


@pytest.fixture(scope="module")
def module():
    spec = importlib.util.spec_from_file_location(
        "market_signal_source_native_benchmark", SCRIPT
    )
    loaded = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(loaded)
    return loaded


@pytest.fixture(scope="module")
def payload(module):
    return module.build_payload(FIXED_GENERATED_UTC)


def test_protocol_predeclares_exact_registered_scope_and_fails_closed(module):
    protocol = module.read_json(module.PROTOCOL_PATH)

    assert protocol["schema"] == (
        "market_signal_source_native_benchmark_protocol_v1"
    )
    assert tuple(
        row["family_id"] for row in protocol["candidates"]
    ) == module.EXPECTED_CANDIDATE_IDS
    assert tuple(
        row["baseline_id"] for row in protocol["baselines"]
    ) == module.EXPECTED_BASELINE_IDS
    assert tuple(
        row["source"] for row in protocol["sources"]
    ) == module.EXPECTED_SOURCES
    assert protocol["evaluation"]["warmup_observations"] == 60
    assert (
        protocol["evaluation"]["no_parameter_tuning_on_evaluation"] is True
    )
    assert all(
        value is False for value in protocol["claim_controls"].values()
    )


def test_registered_snapshot_custody_and_counts_are_exact(payload):
    source_rows = {
        row["source"]: row
        for row in payload["inputs"]["source_snapshots"]
    }

    assert set(source_rows) == {
        "KRAKEN_PUBLIC",
        "TWELVE_DATA",
        "ALPHAVANTAGE",
    }
    assert source_rows["KRAKEN_PUBLIC"]["snapshot_row_count"] == 250
    assert source_rows["TWELVE_DATA"]["snapshot_row_count"] == 250
    assert source_rows["ALPHAVANTAGE"]["snapshot_row_count"] == 100
    assert all(row["series_count"] == 1 for row in source_rows.values())
    assert all(
        row["embedded_hash_verified"]
        and row["registered_reference_verified"]
        and row["embedded_canonical_sha256"]
        == row["registered_wiring_matrix_sha256"]
        for row in source_rows.values()
    )
    assert all(len(row["file_sha256"]) == 64 for row in source_rows.values())


def test_implementation_and_observation_counts_are_explicit(payload):
    summary = payload["implementation_summary"]
    observations = {
        row["source"]: row["evaluation_observation_count"]
        for row in payload["series_results"]
    }

    assert summary["registered_candidate_count"] == 4
    assert summary["implemented_candidate_count"] == 4
    assert summary["missing_candidate_implementation_count"] == 0
    assert summary["registered_baseline_count"] == 4
    assert summary["implemented_baseline_count"] == 4
    assert summary["missing_baseline_implementation_count"] == 0
    assert summary["source_count"] == 3
    assert summary["source_series_count"] == 3
    assert summary["strategy_source_series_result_count"] == 24
    assert observations == {
        "KRAKEN_PUBLIC": 190,
        "TWELVE_DATA": 190,
        "ALPHAVANTAGE": 40,
    }


def test_every_strategy_uses_identical_future_returns_and_timestamps(payload):
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


def test_signal_functions_do_not_read_future_observations(module):
    protocol = module.read_json(module.PROTOCOL_PATH)
    candidates, baselines = module.strategy_definitions(protocol)
    closes = [
        100.0
        + 0.18 * index
        + ((index % 7) - 3) * 0.11
        for index in range(90)
    ]

    def returns_from(values):
        return [0.0] + [
            values[index] / values[index - 1] - 1.0
            for index in range(1, len(values))
        ]

    original_returns = returns_from(closes)
    changed_closes = list(closes)
    for index in range(71, len(changed_closes)):
        changed_closes[index] *= 1.0 + 0.03 * (index - 70)
    changed_returns = returns_from(changed_closes)
    evaluation_index = 70

    for strategy_id in module.EXPECTED_CANDIDATE_IDS:
        original = module.candidate_position(
            strategy_id,
            closes,
            original_returns,
            evaluation_index,
            candidates,
        )
        changed = module.candidate_position(
            strategy_id,
            changed_closes,
            changed_returns,
            evaluation_index,
            candidates,
        )
        assert original == changed

    for strategy_id in module.EXPECTED_BASELINE_IDS:
        original = module.baseline_position(
            strategy_id,
            closes,
            original_returns,
            evaluation_index,
            baselines[strategy_id],
            252,
        )
        changed = module.baseline_position(
            strategy_id,
            changed_closes,
            changed_returns,
            evaluation_index,
            baselines[strategy_id],
            252,
        )
        assert original == changed


def test_cost_turnover_drawdown_and_risk_metrics_are_bounded(payload):
    for series_row in payload["series_results"]:
        for strategy in series_row["strategy_results"]:
            metrics = strategy["metrics"]
            assert metrics["total_turnover"] >= 0.0
            assert metrics["mean_turnover"] >= 0.0
            assert metrics["total_assumed_cost"] >= 0.0
            assert metrics["mean_assumed_cost"] >= 0.0
            assert 0.0 <= metrics["maximum_drawdown"] <= 1.0
            assert 0.0 <= metrics["positive_net_return_rate"] <= 1.0
            assert isinstance(metrics["risk_adjusted_score"], float)
            assert all(
                len(value) == 64
                for value in strategy["sequence_hashes"].values()
            )
            assert all(
                value is False
                for value in strategy["claim_allowed"].values()
            )


def test_cluster_inference_and_global_holm_retain_negative_result(payload):
    negative = payload["negative_result_summary"]

    assert negative["candidate_source_baseline_comparison_count"] == 48
    assert negative["global_holm_positive_count"] == 0
    assert negative["global_holm_nonpositive_count"] == 48
    assert negative["inference_insufficient_comparison_count"] == 48
    assert (
        negative[
            "candidate_beats_every_source_baseline_after_global_holm_count"
        ]
        == 0
    )
    assert negative["candidate_passes"] == []
    assert all(
        row["source_series_cluster_count"] == 1
        and row["inference_sufficient"] is False
        and row["raw_cluster_sign_test_p_value"] == 1.0
        and row["global_holm_adjusted_p_value"] == 1.0
        and row["statistically_positive_after_global_holm"] is False
        for row in payload["comparisons"]
    )


def test_payload_is_deterministic_for_fixed_inputs_and_timestamp(module, payload):
    rebuilt = module.build_payload(FIXED_GENERATED_UTC)

    assert rebuilt == payload
    assert len(rebuilt["payload_sha256"]) == 64
    without_payload_hash = {
        key: value
        for key, value in rebuilt.items()
        if key != "payload_sha256"
    }
    assert rebuilt["payload_sha256"] == module.stable_sha256(
        without_payload_hash
    )


def test_snapshot_or_protocol_drift_fails_closed(module):
    protocol = module.read_json(module.PROTOCOL_PATH)
    registry = module.read_json(
        module.ROOT / protocol["inputs"]["family_registry"]
    )
    wiring_matrix = module.read_json(
        module.ROOT / protocol["inputs"]["source_wiring_matrix"]
    )
    changed_protocol = copy.deepcopy(protocol)
    changed_protocol["sources"][0]["snapshot_embedded_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="Protocol snapshot differs"):
        module.validate_protocol(changed_protocol, registry, wiring_matrix)

    snapshot = module.read_json(
        module.ROOT / protocol["sources"][0]["snapshot_path"]
    )
    changed_snapshot = copy.deepcopy(snapshot)
    changed_snapshot["rows"][0]["close"] = "1.0"
    with pytest.raises(ValueError, match="embedded SHA-256"):
        module.verify_embedded_snapshot_hash(changed_snapshot)


def test_outputs_include_exact_file_and_manifest_hashes(
    module, payload, tmp_path
):
    out_json = tmp_path / "market_signal_source_native_benchmark.json"
    dashboard_json = tmp_path / "dashboard_market_signal_source_native_benchmark.json"
    manifest_json = tmp_path / "market_signal_source_native_manifest.json"
    doc_path = tmp_path / "market_signal_source_native_benchmark.md"

    manifest = module.write_outputs(
        payload,
        out_json=out_json,
        manifest_json=manifest_json,
        doc_path=doc_path,
        dashboard_json=dashboard_json,
    )
    written_payload = json.loads(out_json.read_text(encoding="utf-8"))
    written_dashboard_payload = json.loads(
        dashboard_json.read_text(encoding="utf-8")
    )
    written_manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    without_manifest_hash = {
        key: value
        for key, value in written_manifest.items()
        if key != "manifest_sha256"
    }

    assert written_payload == payload
    assert written_dashboard_payload == payload
    assert manifest == written_manifest
    assert manifest["output"]["file_sha256"] == module.file_sha256(out_json)
    assert manifest["documentation"]["file_sha256"] == module.file_sha256(
        doc_path
    )
    assert manifest["public_feed"]["file_sha256"] == module.file_sha256(
        dashboard_json
    )
    assert (
        manifest["public_feed"]["public_performance_claim_allowed"] is False
    )
    assert manifest["manifest_sha256"] == module.stable_sha256(
        without_manifest_hash
    )
    assert manifest["external_actions"] == []


def test_documentation_states_exact_negative_and_safety_boundaries(
    module, payload
):
    text = module.render_markdown(payload)

    assert "**No candidate is promoted.**" in text
    assert "Registered candidates: `4`" in text
    assert "Implemented candidates: `4`" in text
    assert "Missing candidate implementations: `0`" in text
    assert "Candidate/source/baseline comparisons: `48`" in text
    assert "Globally Holm-positive comparisons: `0`" in text
    assert "Inferentially insufficient comparisons: `48`" in text
    assert "Alpha claim allowed: `false`" in text
    assert "Live trading allowed: `false`" in text
    assert "External action allowed: `false`" in text
    assert "not realized or expected trading outcomes" in text
