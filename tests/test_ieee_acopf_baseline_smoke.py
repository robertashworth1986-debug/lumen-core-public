from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_IEEE_ACOPF_BASELINE_SMOKE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("ieee_acopf_baseline_smoke", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_ieee_acopf_baseline_smoke_converges_without_candidate_overclaiming():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "ieee_acopf_baseline_smoke_v1"
    assert payload["summary"]["network_count"] == 4
    assert payload["summary"]["converged_count"] == 4
    assert payload["summary"]["all_converged"] is True
    assert payload["summary"]["candidate_execution_started"] is False
    assert payload["summary"]["field_validation_claim_allowed"] is False
    assert payload["summary"]["realized_savings_claim_allowed"] is False
    assert payload["summary"]["beats_optimum_claim_allowed"] is False
    assert {row["network"] for row in payload["results"]} == {"case14", "case30", "case39", "case118"}
    assert all(row["reported_objective"] > 0 for row in payload["results"])
    assert len(payload["receipt_sha256"]) == 64


def test_ieee_acopf_baseline_markdown_names_the_boundary():
    module = load_module()
    rendered = module.render_markdown(module.build_payload())

    assert "Networks converged: `4/4`" in rendered
    assert "Candidate execution started: `false`" in rendered
    assert "does not show that LumenCore beats an optimum" in rendered
