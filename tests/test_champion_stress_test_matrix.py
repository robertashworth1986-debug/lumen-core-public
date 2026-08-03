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


def test_stress_matrix_enforces_canonical_v2_nonpromotion_truth():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "champion_stress_test_matrix_v2"
    assert summary["internal_performance_champion"] is False
    assert summary["champion_family"] is None
    assert summary["audited_candidate_family"] == "kuramoto_phase_coupling"
    assert summary["development_selected_candidate"] == "lissajous_phase_paths"
    assert summary["candidate_was_protocol_selected"] is False
    assert summary["named_baseline"] == "kalman_local_linear_trend"
    assert summary["paired_day_wins_vs_named_baseline"] == 482
    assert summary["paired_day_count"] == 1525
    assert summary["mean_skill_delta_vs_named_baseline"] == -0.508191
    assert summary["registered_baseline_gate_pass_count"] == 0
    assert summary["registered_baseline_count"] == 6
    assert summary["direct_measured_route_count"] == 2
    assert summary["conditioned_synthetic_route_count"] == 2
    assert summary["baseline_comparison_count"] == 22
    assert summary["global_holm_positive_count"] == 0
    assert summary["conditioned_named_baseline_mean_win_count"] == 1
    assert summary["performance_rows_reviewed"] == 32608
    assert summary["legacy_rows_excluded"] == 358
    assert summary["numeric_fallback_count"] == 0
    assert summary["source_inventory_is_performance_evidence"] is False

    gates = {row["name"]: row for row in payload["metric_stress_tests"]}
    assert gates["development_selection"]["passed"] is False
    assert gates["all_registered_source_baselines"]["actual"] == "0/6"
    assert gates["global_holm_promotion"]["actual"] == "0/22"
    assert gates["external_validation"]["passed"] is False

    routes = {row["lane"]: row for row in payload["route_matrix"]}
    assert routes["wave_resonance_timing"]["status"] == "DIRECT_MEASURED_NONPROMOTION"
    assert routes["time_series_model_routing"]["status"] == "DIRECT_MEASURED_NONPROMOTION"
    assert routes["thermal_ventilation"]["status"] == "CONDITIONED_SYNTHETIC_RESEARCH_LEAD"
    assert routes["branching_transport"]["status"] == "CONDITIONED_SYNTHETIC_RESEARCH_LEAD"
    assert all(row["performance_claim_allowed"] is False for row in payload["conditioned_research_leads"])
    assert len(payload["stress_matrix_sha256"]) == 64


def test_stress_matrix_renderer_and_main_emit_only_reviewer_safe_v2(
    tmp_path: Path, monkeypatch
):
    module = load_module()
    out_json = tmp_path / "out.json"
    dashboard_json = tmp_path / "dashboard.json"
    doc_md = tmp_path / "stress.md"
    monkeypatch.setattr(module, "OUT_JSON", out_json)
    monkeypatch.setattr(module, "DASHBOARD_JSON", dashboard_json)
    monkeypatch.setattr(module, "DOC_MD", doc_md)

    module.main()

    payload = json.loads(out_json.read_text(encoding="utf-8"))
    rendered = doc_md.read_text(encoding="utf-8")
    dumped = json.dumps(payload).lower()
    assert payload["schema"] == "champion_stress_test_matrix_v2"
    assert json.loads(dashboard_json.read_text(encoding="utf-8")) == payload
    assert "no internal performance champion is present" in rendered.lower()
    assert "source breadth is inventory, not performance evidence" in rendered.lower()
    assert "24/24" not in dumped
    assert "source-conditioned replay winner" not in dumped
    assert "buyer-authorized field replay request ready" not in dumped
    assert "current internal champion" not in dumped
