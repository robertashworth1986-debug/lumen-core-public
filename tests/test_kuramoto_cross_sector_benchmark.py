from __future__ import annotations

import copy
import importlib.util
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_KURAMOTO_CROSS_SECTOR_BENCHMARK.py"
PROTOCOL = ROOT / "config" / "kuramoto_cross_sector_benchmark_protocol_v1.json"
OUTPUT = ROOT / "out" / "ops" / "kuramoto_cross_sector_benchmark_latest.json"
MANIFEST = ROOT / "out" / "ops" / "kuramoto_cross_sector_benchmark_manifest_latest.json"
EXTERNAL_PROTOCOL_TEMPLATE = (
    ROOT / "config" / "kuramoto_sector_external_evaluator_protocol_template_v1.json"
)
EXTERNAL_RESULT_TEMPLATE = (
    ROOT / "config" / "kuramoto_sector_external_evaluator_result_receipt_template_v1.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("kuramoto_cross_sector", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_protocol_is_bounded_fail_closed_and_economically_claim_safe():
    module = load_module()
    protocol = module.load_protocol(PROTOCOL)
    baseline_ids = [row["id"] for row in protocol["baselines"]]

    assert protocol["candidate"]["id"] == "kuramoto_phase_coupling"
    assert baseline_ids == [
        "naive_last",
        "seasonal_naive",
        "rolling_mean_season",
        "ewma_0_2",
        "linear_trend",
        "kalman_local_linear_trend",
        "autoregressive_ridge",
        "fft_extrapolation_top5",
        "uncoupled_harmonic",
    ]
    assert protocol["baseline_scope"]["not_a_global_all_algorithms_claim"] is True
    assert protocol["evaluation"]["history_only_at_each_origin"] is True
    assert protocol["candidate"]["post_result_tuning_allowed"] is False
    assert protocol["economic_translation"]["realized_savings_claim_allowed"] is False
    assert (
        protocol["economic_translation"]["dollar_projection_from_forecast_error_allowed"]
        is False
    )
    assert protocol["economic_translation"]["buyer_approved_cost_of_error_required"] is True
    assert protocol["execution_controls"]["trading_execution_allowed"] is False
    assert protocol["execution_controls"]["external_submission_allowed"] is False


def test_all_allowlisted_sources_have_traceable_strictly_ordered_snapshots():
    module = load_module()
    protocol = module.load_protocol(PROTOCOL)

    for source in protocol["retrospective_sources"]:
        dates, values, receipt = module.load_source_series(source, protocol)
        assert len(dates) == len(values) == receipt["accepted_numeric_rows"]
        assert len(values) >= protocol["source_admission"]["minimum_numeric_rows"]
        assert all(left < right for left, right in zip(dates, dates[1:]))
        assert all(math.isfinite(value) for value in values)
        assert receipt["sha256"] == module.file_sha256(ROOT / source["path"])
        assert receipt["duplicate_timestamp_count"] == 0
        assert receipt["invalid_row_count"] == 0
        assert receipt["read_only"] is True
        assert receipt["credential_serialized"] is False


def test_forecaster_registry_matches_frozen_protocol_and_kuramoto_is_real():
    module = load_module()
    protocol = module.load_protocol(PROTOCOL)
    eia = module.load_eia_module()
    source = protocol["retrospective_sources"][1]
    forecasters = module.build_forecasters(source, protocol, eia)
    history = [
        100.0 + 0.03 * index + 2.0 * math.sin(2.0 * math.pi * index / 12.0)
        for index in range(240)
    ]

    expected = {row["id"] for row in protocol["baselines"]} | {
        protocol["candidate"]["id"]
    }
    assert set(forecasters) == expected
    candidate = forecasters["kuramoto_phase_coupling"](history)
    uncoupled = forecasters["uncoupled_harmonic"](history)
    assert math.isfinite(candidate)
    assert math.isfinite(uncoupled)
    assert candidate != uncoupled


def test_block_statistics_and_holm_adjustment_are_deterministic():
    module = load_module()
    values = [0.1 + (index % 5) * 0.01 for index in range(80)]

    first = module.deterministic_block_bootstrap(
        values, block_length=4, draws=500, seed=20260726
    )
    second = module.deterministic_block_bootstrap(
        values, block_length=4, draws=500, seed=20260726
    )
    assert first == second
    assert first["ci95_lower"] > 0

    rows = [
        {"sign_test_p_value": 0.01},
        {"sign_test_p_value": 0.03},
        {"sign_test_p_value": 0.20},
    ]
    module.holm_adjust(rows)
    assert [row["holm_adjusted_p_value"] for row in rows] == [0.03, 0.06, 0.20]


def test_latest_receipt_preserves_negative_results_and_no_dollar_claim():
    module = load_module()
    payload = read_json(OUTPUT)
    expected = copy.deepcopy(payload)
    observed_hash = expected.pop("evidence_chain_sha256")

    assert payload["schema"] == module.SCHEMA
    assert observed_hash == module.canonical_sha256(module.stable_evidence_core(payload))
    assert payload["status"] == "NO_CROSS_SECTOR_EFFICIENCY_GAIN_PROVEN"
    assert payload["source_failures"] == []
    assert payload["gates"]["configured_source_count"] == 6
    assert payload["gates"]["admitted_source_count"] == 6
    assert payload["gates"]["total_evaluation_origin_count"] == 786
    assert payload["gates"]["sector_gain_proven_count"] == 0
    assert payload["gates"]["cross_sector_efficiency_claim_allowed"] is False
    assert payload["gates"]["realized_savings_claim_allowed"] is False
    assert payload["highest_observed_exploratory_sector"] is None
    assert payload["highest_proven_efficiency_sector"] is None
    assert all(
        row["relative_mae_improvement_vs_best_percent"] < 0
        for row in payload["source_results"]
    )

    anchor = payload["anchored_results"][0]
    assert anchor["candidate"]["strategy"] == "kuramoto_phase_coupling"
    assert anchor["candidate"]["rank"] == 9
    assert anchor["strategy_count"] == 10
    assert anchor["relative_mae_improvement_vs_best_percent"] < 0
    assert anchor["status"] == "NEGATIVE_KURAMOTO_EVIDENCE"


def test_live_breadth_inventory_is_not_promoted_to_performance_evidence():
    payload = read_json(OUTPUT)
    audit = payload["live_breadth_admission_audit"]

    assert audit["explicit_allowlist_only"] is True
    assert audit["manifest_present"] is True
    assert audit["manifest_consistency_pass"] is True
    assert audit["declared_materialized_count_match"] is True
    assert audit["manifest_rows_truncated"] is True
    assert audit["manifest_rows_omitted_count"] > 0
    assert (
        audit["discovered_manifest_row_count"]
        == audit["materialized_manifest_row_count"]
        + audit["manifest_rows_omitted_count"]
    )
    assert "discovery inventory only" in audit["claim_boundary"]
    assert "24/24" not in json.dumps(payload["source_results"])


def test_manifest_hashes_every_written_artifact():
    module = load_module()
    manifest = read_json(MANIFEST)

    for artifact in manifest["artifacts"]:
        path = ROOT / artifact["path"]
        assert path.is_file()
        assert artifact["sha256"] == module.file_sha256(path)
        assert artifact["bytes"] == path.stat().st_size
    assert manifest["artifact_chain_sha256"] == module.canonical_sha256(
        manifest["artifacts"]
    )


def test_external_proof_templates_are_bound_to_the_negative_receipt_and_fail_closed():
    module = load_module()
    protocol_template = read_json(EXTERNAL_PROTOCOL_TEMPLATE)
    result_template = read_json(EXTERNAL_RESULT_TEMPLATE)
    receipt = read_json(OUTPUT)

    assert protocol_template["predecessor"]["protocol_sha256"] == module.file_sha256(
        PROTOCOL
    )
    assert (
        protocol_template["predecessor"]["evidence_chain_sha256"]
        == receipt["evidence_chain_sha256"]
    )
    assert protocol_template["predecessor"]["sector_gain_proven"] is False
    assert protocol_template["economic_contract"]["enabled_before_technical_gate"] is False
    assert protocol_template["economic_contract"]["projection_or_savings_claim_allowed"] is False
    assert (
        protocol_template["acceptance_contract"][
            "prospective_sector_signal_allowed_before_result_receipt"
        ]
        is False
    )
    assert protocol_template["execution_controls"]["external_action_requires_human_approval"] is True
    assert protocol_template["freeze"]["accepted_protocol_payload_sha256"] is None

    assert result_template["status"] == "TEMPLATE_NOT_EVIDENCE"
    assert result_template["technical_result"]["all_required_checks_pass"] is False
    assert result_template["technical_result"]["sector_signal_supported"] is False
    assert result_template["economic_result"]["economic_conversion_complete"] is False
    assert result_template["economic_result"]["savings_claim_allowed"] is False
    assert result_template["negative_result_retained"] is True
    assert result_template["external_action_performed_by_template"] is False


def test_runner_source_has_no_network_submission_or_trading_client():
    source = SCRIPT.read_text(encoding="utf-8").lower()

    assert "import requests" not in source
    assert "import smtplib" not in source
    assert "import webbrowser" not in source
    assert "import selenium" not in source
    assert "import playwright" not in source
    assert "subprocess" not in source
    assert "ccxt" not in source
