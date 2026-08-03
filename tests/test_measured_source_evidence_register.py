from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_MEASURED_SOURCE_EVIDENCE_REGISTER.py"


def load_module():
    spec = importlib.util.spec_from_file_location("measured_source_evidence_register", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_register_reconciles_registry_and_current_probe_layers():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "measured_source_evidence_register_v1"
    assert payload["status"] == "MEASURED_SOURCE_REGISTER_READY_RECONCILIATION_REQUIRED"
    assert summary["registry_total_sources"] == 17
    assert summary["registry_enabled_sources"] == 17
    assert summary["registry_measured_sources"] == 11
    assert summary["registry_total_measured_rows"] == 44
    assert summary["registry_coverage_pct"] == 64.71
    assert summary["current_probe_total_sources"] == 28
    assert summary["current_probe_enabled_sources"] == 27
    assert summary["current_probe_measured_sources"] == 23
    assert summary["current_probe_hash_backed_measured_sources"] == 23
    assert summary["current_probe_total_measured_rows"] == 2377
    assert summary["current_probe_coverage_pct"] == 85.19
    assert summary["registry_only_sources"] == ["ALPACA", "KRAKEN"]
    assert summary["registry_only_measured_sources"] == ["ALPACA"]
    assert summary["registry_only_measured_rows"] == 1
    assert summary["registry_measured_without_snapshot_hash"] == ["ALPACA"]
    assert summary["registry_source_generated_utc"]
    assert summary["current_probe_source_generated_utc"]
    assert summary["reconciliation_required"] is True
    assert summary["geometry_manifest_row_count"] == 500
    assert summary["geometry_manifest_discovered_row_count"] == 603
    assert summary["geometry_manifest_omitted_row_count"] == 103
    assert summary["kuramoto_benchmark_integrity_pass"] is True
    assert summary["kuramoto_benchmark_status"] == (
        "NO_CROSS_SECTOR_EFFICIENCY_GAIN_PROVEN"
    )
    assert summary["kuramoto_admitted_source_count"] == 6
    assert summary["kuramoto_evaluation_origin_count"] == 786
    assert summary["kuramoto_protocol_matched_strategy_count"] == 10
    assert summary["kuramoto_positive_exploratory_sector_count"] == 0
    assert summary["kuramoto_sector_gain_proven_count"] == 0
    assert summary["kuramoto_frozen_eia_anchor_negative"] is True
    assert summary["kuramoto_cross_sector_efficiency_claim_allowed"] is False
    assert summary["kuramoto_realized_savings_claim_allowed"] is False
    assert len(payload["measured_source_register_sha256"]) == 64


def test_source_rows_are_claim_bounded_and_hash_aware():
    module = load_module()
    payload = module.build_payload()
    rows = {row["source"]: row for row in payload["source_rows"]}

    assert rows["EIA"]["evidence_tier"] == "CURRENT_HASHED_MEASURED_SOURCE"
    assert rows["EIA"]["hash_backed"] is True
    assert len(rows["EIA"]["snapshot_sha256"]) == 64
    assert rows["ALPACA"]["evidence_tier"] == "REGISTRY_MEASURED_NEEDS_HASH_REFRESH"
    assert rows["KRAKEN"]["evidence_tier"] == "REGISTRY_UNMEASURED_OR_DISABLED"

    for row in payload["source_rows"]:
        assert row["claim_boundary"]
        assert row["source_authority_claimed"] is False
        assert row["live_execution_allowed"] is False
        assert row["field_validation_claim_allowed"] is False
        assert row["realized_savings_claim_allowed"] is False
        assert len(row["row_sha256"]) == 64


def test_register_keeps_high_risk_claim_gates_closed():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert summary["field_validation_claim_allowed"] is False
    assert summary["realized_savings_claim_allowed"] is False
    assert summary["award_value_claim_allowed"] is False
    assert summary["source_authority_claimed"] is False
    assert summary["live_trading_allowed"] is False
    assert summary["autonomous_external_action_allowed"] is False
    assert "Measured Source Evidence Register" in rendered
    assert "Reconciliation required: `true`" in rendered
    assert "17-source canonical registry with 17 currently enabled sources" in rendered
    assert "30 merged source rows across the canonical registry and current probe" in rendered
    assert "Current probe coverage: `85.19`%" in rendered
    assert "Registry-only measured rows awaiting current hash refresh: `1`" in rendered
    assert "## Current Kuramoto Head-to-Head" in rendered
    assert "Status: `NO_CROSS_SECTOR_EFFICIENCY_GAIN_PROVEN`" in rendered
    assert "Proven sector gains: `0`" in rendered
    assert "Cross-sector efficiency claim allowed: `false`" in rendered
    assert "Do not claim Kuramoto cross-sector efficiency." in rendered
    assert "Do not claim Kuramoto-attributable dollar savings." in rendered
    assert "Do not claim field validation." in rendered
    assert "api_key" not in lowered
    assert "client_secret" not in lowered
    assert "refresh_token" not in lowered
    assert "private key" not in lowered
    assert "password" not in lowered
