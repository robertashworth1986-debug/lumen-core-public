from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_CHAMPION_PHASE_PROXY_DIAGNOSTICS.py"


def load_module():
    spec = importlib.util.spec_from_file_location("champion_phase_proxy_diagnostics", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_phase_proxy_diagnostics_builds_from_current_holdouts():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "champion_phase_proxy_diagnostics_v1"
    assert summary["champion_family"] == "kuramoto_phase_coupling"
    assert summary["named_baseline"] == "kalman_filter"
    assert summary["holdout_count"] >= 24
    assert summary["usable_numeric_holdout_count"] >= 20
    assert summary["phase_proxy_claim_allowed"] is True
    assert len(payload["source_summary"]) >= 4
    assert len(payload["phase_proxy_sha256"]) == 64


def test_phase_proxy_diagnostics_keeps_external_claim_gates_closed():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert summary["hardware_phase_lock_claim_allowed"] is False
    assert summary["field_validation_claim_allowed"] is False
    assert summary["real_dollar_savings_claim_allowed"] is False

    dumped = json.dumps(payload).lower()
    assert "not hardware pll measurements" in dumped
    assert "not field validation" in dumped
    assert "not realized savings" in dumped


def test_phase_proxy_diagnostics_exposes_source_level_metrics():
    module = load_module()
    payload = module.build_payload()
    sources = {row["source_system"] for row in payload["source_summary"]}

    assert {"energy_grid", "market_data"}.issubset(sources)
    for row in payload["source_summary"]:
        assert "mean_phase_coherence_proxy" in row
        assert "mean_phase_slip_proxy_rate" in row
        assert "mean_spectral_concentration_proxy" in row
        assert "mean_abs_residual_lag1_autocorrelation_proxy" in row


def test_phase_proxy_markdown_names_boundary():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)

    assert "Champion Phase Proxy Diagnostics" in rendered
    assert "Truth Line" in rendered
    assert "Hardware phase-lock claim allowed: `false`" in rendered
    assert "not hardware PLL measurements" in rendered
