from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_REPEAT_UNCERTAINTY_REPORT.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geometry_repeat_uncertainty_report", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_uncertainty_report_promotes_two_robust_repeat_candidates():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    by_family = {row["family_id"]: row for row in payload["analyses"]}

    assert payload["schema"] == "geometry_repeat_uncertainty_report_v1"
    assert summary["family_count"] >= 4
    assert summary["robust_repeat_uncertainty_gate_passed_count"] == 2
    assert summary["total_windows_analyzed"] >= 24
    assert summary["total_winning_windows"] >= 21
    assert len(summary["uncertainty_chain_sha256"]) == 64

    brach = by_family["brachistochrone_descent"]
    assert brach["win_count"] == brach["window_count"] == 6
    assert brach["delta_stats"]["min_delta"] > 0.06
    assert brach["delta_stats"]["normal_t_lower_95_delta"] > 0.06
    assert brach["wilson_lower_95_win_rate"] > 0.6
    assert brach["one_sided_sign_test_p_value"] == 0.015625
    assert brach["robust_repeat_uncertainty_gate_passed"] is True
    assert brach["blockers"] == []

    kuramoto = by_family["kuramoto_phase_coupling"]
    assert kuramoto["win_count"] == kuramoto["window_count"] == 6
    assert kuramoto["delta_stats"]["min_delta"] > 0.14
    assert kuramoto["delta_stats"]["normal_t_lower_95_delta"] > 0.15
    assert kuramoto["wilson_lower_95_win_rate"] > 0.6
    assert kuramoto["one_sided_sign_test_p_value"] == 0.015625
    assert kuramoto["robust_repeat_uncertainty_gate_passed"] is True
    assert kuramoto["blockers"] == []


def test_uncertainty_report_blocks_unstable_or_under_sourced_rows():
    module = load_module()
    payload = module.build_payload()
    by_family = {row["family_id"]: row for row in payload["analyses"]}

    leaf = by_family["leaf_veins"]
    assert leaf["robust_repeat_uncertainty_gate_passed"] is False
    assert "not_all_windows_positive" in leaf["blockers"]
    assert "non_positive_min_delta" in leaf["blockers"]
    assert "sign_test_not_below_0_05" in leaf["blockers"]

    thermal = by_family["thermal_plume_convection"]
    assert thermal["win_count"] == thermal["window_count"] == 6
    assert thermal["delta_stats"]["normal_t_lower_95_delta"] > 0
    assert thermal["robust_repeat_uncertainty_gate_passed"] is False
    assert "minimum_source_count_below_3" in thermal["blockers"]


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
    assert "Robust repeat-window candidates: `2`" in rendered
    assert "Ready for field-validation claim: `false`" in rendered
    assert "Ready for real-dollar claim: `false`" in rendered
    assert "`brachistochrone_descent`" in rendered
    assert "`kuramoto_phase_coupling`" in rendered
    assert "not a prospective field trial" in rendered
    assert "Real-dollar claims require" in rendered
