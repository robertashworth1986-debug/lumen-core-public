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


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def configure_canonical_inputs(module, tmp_path: Path) -> None:
    source = tmp_path / "measured.csv"
    source.write_text(
        "value\n0.0\n0.4\n0.9\n0.2\n-0.5\n-0.8\n-0.1\n0.7\n1.0\n0.3\n-0.4\n-0.9\n",
        encoding="utf-8",
    )
    holdout = {
        "schema": "kuramoto_holdout_expansion_v2",
        "summary": {
            "candidate": "kuramoto_phase_coupling",
            "candidate_was_protocol_selected": False,
            "development_selected_candidate": "lissajous_phase_paths",
            "named_baseline": "kalman_local_linear_trend",
            "wins_vs_kalman": 482,
            "holdout_count": 1525,
            "mean_delta_vs_kalman": -0.508190706,
            "candidate_holdout_rank": 9,
        },
        "holdout_results": [
            {
                "source_system": "EIA_GRID_VALIDATION",
                "source_path": str(source),
                "source_sha256": "a" * 64,
                "holdout_sha256": "b" * 64,
                "candidate_family": "kuramoto_phase_coupling",
                "baseline": "kalman_local_linear_trend",
                "mean_skill_delta": -0.508190706,
            }
        ],
    }
    stress = {
        "schema": "champion_stress_test_matrix_v2",
        "summary": {
            "internal_performance_champion": False,
            "champion_family": None,
            "development_selected_candidate": "lissajous_phase_paths",
            "direct_measured_route_count": 2,
            "conditioned_synthetic_route_count": 2,
            "baseline_comparison_count": 22,
            "performance_rows_reviewed": 32608,
            "global_holm_positive_count": 0,
            "live_domain_hash_verified": False,
        },
    }
    module.HOLDOUT_JSON = tmp_path / "holdout.json"
    module.STRESS_JSON = tmp_path / "stress.json"
    write_json(module.HOLDOUT_JSON, holdout)
    write_json(module.STRESS_JSON, stress)


def test_phase_proxy_diagnostics_enforces_canonical_nonpromotion_contract(tmp_path):
    module = load_module()
    configure_canonical_inputs(module, tmp_path)
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "champion_phase_proxy_diagnostics_v2"
    assert summary["internal_performance_champion"] is False
    assert summary["champion_family"] is None
    assert summary["audited_reference_candidate"] == "kuramoto_phase_coupling"
    assert summary["reference_candidate_status"] == "negative_measured_reference_not_selected_not_promoted"
    assert summary["development_selected_candidate"] == "lissajous_phase_paths"
    assert summary["candidate_was_development_selected"] is False
    assert summary["named_baseline"] == "kalman_local_linear_trend"
    assert summary["kuramoto_wins_vs_named_baseline"] == 482
    assert summary["kuramoto_paired_holdout_count"] == 1525
    assert summary["kuramoto_mean_delta_vs_named_baseline"] == -0.508191
    assert summary["direct_measured_route_count"] == 2
    assert summary["conditioned_synthetic_route_count"] == 2
    assert summary["baseline_comparison_count"] == 22
    assert summary["performance_rows_reviewed"] == 32608
    assert summary["direct_all_baseline_globally_holm_positive_promotion_count"] == 0
    assert summary["source_inventory_measured_source_count"] == 24
    assert summary["source_inventory_measured_row_count"] == 17081
    assert summary["source_inventory_is_performance_evidence"] is False
    assert summary["canonical_evidence_contract_matches_inputs"] is True
    assert summary["holdout_count"] == 1
    assert summary["usable_numeric_holdout_count"] == 1
    assert summary["non_degenerate_numeric_holdout_count"] == 1
    assert summary["degenerate_numeric_holdout_count"] == 0
    assert summary["degenerate_series_excluded_from_source_means"] is True
    assert summary["descriptive_file_proxy_reporting_allowed"] is True
    assert len(payload["source_summary"]) == 1
    assert len(payload["phase_proxy_sha256"]) == 64


def test_phase_proxy_diagnostics_keeps_scientific_and_external_claim_gates_closed(tmp_path):
    module = load_module()
    configure_canonical_inputs(module, tmp_path)
    payload = module.build_payload()
    summary = payload["summary"]

    assert summary["phase_measurement_claim_allowed"] is False
    assert summary["model_residual_diagnostic_claim_allowed"] is False
    assert summary["performance_promotion_claim_allowed"] is False
    assert summary["hardware_phase_lock_claim_allowed"] is False
    assert summary["field_validation_claim_allowed"] is False
    assert summary["real_dollar_savings_claim_allowed"] is False

    dumped = json.dumps(payload).lower()
    assert "current internal champion" not in dumped
    assert '"internal_performance_champion": true' not in dumped
    assert "a performance champion is present" not in dumped
    assert "not phase measurements" in dumped
    assert "model-residual diagnostics" in dumped
    assert "not performance evidence" in dumped
    assert "hardware pll measurements" in dumped
    assert "field validation" in dumped
    assert "realized savings" in dumped


def test_phase_proxy_diagnostics_exposes_bounded_source_level_metrics(tmp_path):
    module = load_module()
    configure_canonical_inputs(module, tmp_path)
    payload = module.build_payload()
    sources = {row["source_system"] for row in payload["source_summary"]}

    assert sources == {"EIA_GRID_VALIDATION"}
    for row in payload["source_summary"]:
        assert "mean_phase_coherence_proxy" in row
        assert "mean_phase_slip_proxy_rate" in row
        assert "mean_spectral_concentration_proxy" in row
        assert "mean_abs_residual_lag1_autocorrelation_proxy" in row
        assert "non_degenerate_numeric_holdouts" in row
        assert "degenerate_numeric_holdouts" in row
    assert payload["holdout_phase_diagnostics"][0]["diagnostic_role"] == (
        "file_level_numeric_sequence_proxy_only"
    )


def test_phase_proxy_markdown_names_nonpromotion_boundary(tmp_path):
    module = load_module()
    configure_canonical_inputs(module, tmp_path)
    payload = module.build_payload()
    rendered = module.render_markdown(payload)

    assert "Phase Proxy Diagnostic Nonpromotion Report" in rendered
    assert "Truth Line" in rendered
    assert "Internal performance champion: `false`" in rendered
    assert "Champion family: `none`" in rendered
    assert "Kuramoto paired wins: `482/1525`" in rendered
    assert "Kuramoto mean delta vs named baseline: `-0.508191`" in rendered
    assert "Direct measured routes: `2`" in rendered
    assert "Conditioned-synthetic routes: `2`" in rendered
    assert "Baseline comparisons: `22`" in rendered
    assert "Performance rows reviewed: `32608`" in rendered
    assert "Direct all-baseline globally Holm-positive promotions: `0`" in rendered
    assert "Source inventory: `24` measured sources / `17081` rows" in rendered
    assert "Source inventory is performance evidence: `false`" in rendered
    assert "Phase measurement claim allowed: `false`" in rendered
    assert "Performance promotion claim allowed: `false`" in rendered
    assert "Hardware phase-lock claim allowed: `false`" in rendered
    assert "Degenerate numeric holdouts excluded from source means" in rendered
    assert "They are not phase measurements" in rendered
    assert "hardware PLL measurements" in rendered


def test_write_outputs_uses_only_explicit_temporary_paths(tmp_path):
    module = load_module()
    configure_canonical_inputs(module, tmp_path)
    payload = module.build_payload()
    out_json = tmp_path / "out" / "diagnostics.json"
    dashboard_json = tmp_path / "dashboard" / "diagnostics.json"
    out_md = tmp_path / "docs" / "diagnostics.md"

    module.write_outputs(payload, out_json, dashboard_json, out_md)

    assert json.loads(out_json.read_text(encoding="utf-8"))["schema"] == (
        "champion_phase_proxy_diagnostics_v2"
    )
    assert json.loads(dashboard_json.read_text(encoding="utf-8"))["summary"][
        "internal_performance_champion"
    ] is False
    assert "Phase Proxy Diagnostic Nonpromotion Report" in out_md.read_text(encoding="utf-8")
