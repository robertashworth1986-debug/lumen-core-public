from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_KURAMOTO_HOLDOUT_EXPANSION.py"


def load_module():
    spec = importlib.util.spec_from_file_location("kuramoto_holdout_expansion", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_kuramoto_holdout_expansion_runs_20_plus_source_conditioned_routes():
    module = load_module()
    payload = module.build_payload(max_routes=20, sample_limit=750)
    summary = payload["summary"]

    assert payload["schema"] == "kuramoto_holdout_expansion_v1"
    assert summary["candidate"] == "kuramoto_phase_coupling"
    assert summary["named_baseline"] == "kalman_filter"
    assert summary["holdout_count"] >= 20
    assert summary["estimated_rows_replayed"] > 0
    assert summary["numeric_samples_read"] > 0
    assert 0.0 <= summary["win_rate_vs_kalman"] <= 1.0
    assert 0.0 <= summary["wilson_95_win_rate_lower"] <= summary["wilson_95_win_rate_upper"] <= 1.0
    assert len(summary["holdout_chain_sha256"]) == 64


def test_kuramoto_holdout_expansion_hashes_sources_and_keeps_gates_closed():
    module = load_module()
    payload = module.build_payload(max_routes=20, sample_limit=750)
    gates = payload["claim_gates"]

    assert gates["field_validation_claim_allowed"] is False
    assert gates["real_dollar_savings_claim_allowed"] is False
    assert gates["fixed_dollar_delta_sale_claim_allowed"] is False
    assert gates["live_trading_or_autonomous_execution_allowed"] is False
    assert gates["buyer_authorized_field_pilot_required"] is True

    for row in payload["holdout_results"]:
        assert row["lane"] == "wave_resonance_timing"
        assert row["candidate_family"] == "kuramoto_phase_coupling"
        assert row["named_baseline"] == "kalman_filter"
        assert len(row["source_sha256"]) == 64
        assert len(row["holdout_sha256"]) == 64
        assert row["delta_vs_kalman"] is not None


def test_kuramoto_holdout_markdown_is_reviewer_safe():
    module = load_module()
    payload = module.build_payload(max_routes=20, sample_limit=750)
    rendered = module.render_markdown(payload)
    dumped = json.dumps(payload).lower()

    assert "Kuramoto Holdout Expansion" in rendered
    assert "not field validation" in rendered
    assert "field_validation_claim_allowed: `false`" in rendered
    assert "real_dollar_savings_claim_allowed: `false`" in rendered
    assert "guaranteed" not in dumped
    assert "money printer" not in dumped
