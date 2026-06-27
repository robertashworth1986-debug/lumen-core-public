from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_CHAMPION_STRESS_TEST_MATRIX.py"


def load_module():
    spec = importlib.util.spec_from_file_location("champion_stress_test_matrix", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_champion_stress_matrix_summarizes_current_internal_champion():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "champion_stress_test_matrix_v1"
    assert summary["champion_family"] == "kuramoto_phase_coupling"
    assert summary["named_baseline"] == "kalman_filter"
    assert summary["holdout_count"] >= 24
    assert summary["wins_vs_named_baseline"] == summary["holdout_count"]
    assert summary["wins_vs_best_same_run_baseline"] == summary["holdout_count"]
    assert summary["source_system_count"] >= 4
    assert summary["estimated_rows_replayed"] >= 1_000_000
    assert summary["numeric_samples_read"] >= 50_000
    assert summary["live_domain_hash_verified"] is True
    assert len(payload["stress_matrix_sha256"]) == 64


def test_champion_stress_matrix_keeps_money_claims_bounded():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert summary["manual_paid_pilot_outreach_allowed"] is True
    assert summary["field_validation_claim_allowed"] is False
    assert summary["real_dollar_savings_claim_allowed"] is False
    assert summary["fixed_frozen_delta_price_claim_allowed"] is False
    assert summary["live_trading_or_autonomous_execution_allowed"] is False

    dumped = json.dumps(payload).lower()
    assert "field validated" in dumped
    assert "realized dollar savings" in dumped
    assert "buyer-authorized field replay" in dumped


def test_champion_stress_matrix_has_source_and_blocked_metric_detail():
    module = load_module()
    payload = module.build_payload()

    sources = {row["source_system"] for row in payload["source_system_matrix"]}
    assert {"energy_grid", "market_data"}.issubset(sources)

    gate_by_name = {row["name"]: row for row in payload["metric_stress_tests"]}
    assert gate_by_name["source_conditioned_holdout_depth"]["passed"] is True
    assert gate_by_name["hosted_hash_verification"]["passed"] is True
    assert gate_by_name["buyer_authorized_field_replay"]["blocker"] is True
    assert gate_by_name["phase_slip_and_amplitude_error"]["blocker"] is True
    assert gate_by_name["residual_autocorrelation_and_calibration"]["blocker"] is True


def test_champion_stress_matrix_markdown_answers_next_money_step():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)

    assert "Champion Stress Test Matrix" in rendered
    assert "Truth Line" in rendered
    assert "Metric Battery" in rendered
    assert "Live-domain hash verified: `true`" in rendered
    assert "buyer locks the dataset" in rendered
