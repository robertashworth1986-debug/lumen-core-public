from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_CHAMPION_SOURCE_ABLATION.py"


def load_module():
    spec = importlib.util.spec_from_file_location("champion_source_ablation", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_source_ablation_uses_current_nonpromotion_contract():
    module = load_module()
    payload = module.build_payload()
    contract = payload["canonical_evidence_contract"]
    summary = payload["summary"]

    assert payload["schema"] == "champion_source_ablation_v2"
    assert payload["artifact_role"] == "nonpromotion_source_ablation_diagnostic"
    assert contract == {
        "performance_champion_present": False,
        "direct_measured_routes": 2,
        "conditioned_synthetic_routes": 2,
        "baseline_comparisons": 22,
        "performance_rows": 32608,
        "direct_all_baseline_global_holm_positive_promotions": 0,
        "inventory_measured_sources": 24,
        "inventory_measured_rows": 17081,
        "inventory_is_performance_evidence": False,
    }
    assert summary["contract_matches_expected"] is True
    assert summary["performance_champion_present"] is False
    assert summary["promotion_candidate_present"] is False
    assert len(payload["source_ablation_sha256"]) == 64


def test_kuramoto_is_negative_reference_and_not_selected():
    module = load_module()
    payload = module.build_payload()
    reference = payload["reference_audit"]

    assert reference["family"] == "kuramoto_phase_coupling"
    assert reference["status"] == "negative_measured_reference_not_development_selected"
    assert reference["development_selected_candidate"] == "lissajous_phase_paths"
    assert reference["was_development_selected"] is False
    assert reference["wins_vs_kalman"] == 482
    assert reference["holdout_count"] == 1525
    assert reference["mean_delta_vs_kalman"] == -0.508191
    assert reference["candidate_beats_all_registered_baselines_after_holm"] is False
    assert reference["supports_performance_champion_claim"] is False
    assert reference["supports_promotion"] is False
    assert payload["summary"]["reference_matches_expected"] is True


def test_single_source_ablation_fails_closed():
    module = load_module()
    payload = module.build_payload()

    assert payload["summary"]["source_system_count"] == 1
    assert payload["summary"]["source_ablation_count"] == 1
    assert payload["summary"]["evaluable_source_ablation_count"] == 0
    assert payload["summary"]["source_ablation_supports_promotion_count"] == 0

    diagnostic = payload["leave_one_source_out"][0]
    assert diagnostic["withheld_source_system"] == "EIA_GRID_VALIDATION"
    assert diagnostic["remaining_source_system_count"] == 0
    assert diagnostic["remaining_baseline_comparison_count"] == 0
    assert diagnostic["diagnostic_evaluable"] is False
    assert diagnostic["supports_performance_champion_claim"] is False
    assert diagnostic["supports_promotion"] is False
    assert "not evaluable" in diagnostic["claim_gate"]


def test_source_ablation_keeps_every_external_claim_gate_closed():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    dumped = json.dumps(payload).lower()

    assert summary["field_validation_claim_allowed"] is False
    assert summary["performance_superiority_claim_allowed"] is False
    assert summary["real_dollar_savings_claim_allowed"] is False
    assert summary["fixed_dollar_delta_sale_claim_allowed"] is False
    assert summary["live_trading_or_autonomous_execution_allowed"] is False
    assert "current internal champion" not in dumped
    assert "buyer-authorized field replay request ready" not in dumped
    assert "inventory only" in dumped


def test_source_ablation_writes_only_explicit_temporary_outputs(tmp_path):
    module = load_module()
    payload = module.build_payload()
    out_json = tmp_path / "out" / "diagnostic.json"
    dashboard_json = tmp_path / "dashboard" / "diagnostic.json"
    out_md = tmp_path / "docs" / "diagnostic.md"

    module.write_outputs(
        payload,
        out_json=out_json,
        dashboard_json=dashboard_json,
        out_md=out_md,
    )

    assert json.loads(out_json.read_text(encoding="utf-8"))["schema"] == (
        "champion_source_ablation_v2"
    )
    assert json.loads(dashboard_json.read_text(encoding="utf-8"))[
        "artifact_role"
    ] == "nonpromotion_source_ablation_diagnostic"
    rendered = out_md.read_text(encoding="utf-8")
    assert "# Source Ablation Nonpromotion Diagnostic" in rendered
    assert "Performance champion present: `false`" in rendered
    assert "Wins vs named Kalman baseline: `482/1525`" in rendered
    assert "Supports promotion: `false`" in rendered
