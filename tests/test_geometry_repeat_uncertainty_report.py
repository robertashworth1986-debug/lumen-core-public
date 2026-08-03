from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT / "code" / "ops" / "BUILD_GEOMETRY_REPEAT_UNCERTAINTY_REPORT.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "geometry_repeat_uncertainty_report", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_uncertainty_report_fail_closes_without_qualified_repeats():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "geometry_repeat_uncertainty_report_v2"
    assert summary["family_count"] == 5
    assert summary["robust_repeat_uncertainty_gate_passed_count"] == 0
    assert summary["total_windows_analyzed"] == 0
    assert summary["total_winning_windows"] == 0
    assert summary["uncertainty_computable"] is False
    assert summary["robust_candidates"] == []
    assert len(summary["uncertainty_chain_sha256"]) == 64

    for row in payload["analyses"]:
        assert row["robust_repeat_uncertainty_gate_passed"] is False
        assert row["window_count"] == 0
        assert row["delta_stats"]["mean_delta"] is None
        assert "independent_repeat_runs_missing" in row["blockers"]


def test_uncertainty_report_keeps_sales_and_field_claim_gates_closed():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    text = json.dumps(payload).lower()

    assert summary["ready_for_field_validation_claim"] is False
    assert summary["ready_for_real_dollar_claim"] is False
    assert summary["ready_for_bulk_sales_claim"] is False
    assert summary["ready_for_live_trading"] is False
    assert "field validation" in text
    assert "fixed-dollar valuation" in text
    assert "live_order_placement" not in text
    assert ("api" + "_key") not in text

    for row in payload["analyses"]:
        gate = row["claim_gate"]
        assert gate["ready_for_field_validation_claim"] is False
        assert gate["ready_for_real_dollar_claim"] is False
        assert gate["ready_for_bulk_sales_claim"] is False
        assert gate["ready_for_live_trading"] is False


def test_uncertainty_report_markdown_is_reviewer_safe():
    module = load_module()
    rendered = module.render_markdown(module.build_payload())

    assert "Geometry Repeat Uncertainty Report" in rendered
    assert "Robust repeat-window candidates: `0`" in rendered
    assert "Uncertainty computable: `false`" in rendered
    assert "Ready for field-validation claim: `false`" in rendered
    assert "Ready for real-dollar claim: `false`" in rendered
    assert "not a prospective field trial" in rendered
