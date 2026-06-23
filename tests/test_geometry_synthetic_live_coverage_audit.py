from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_SYNTHETIC_LIVE_COVERAGE_AUDIT.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geometry_synthetic_live_coverage_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_audit_keeps_synthetic_live_and_field_validation_separate():
    module = load_module()
    payload = module.build_audit()
    summary = payload["summary"]

    assert payload["schema"] == "geometry_synthetic_live_coverage_audit_v1"
    assert payload["policy"]["rule"] == "Synthetic discovers. Live proves. Field validation wins awards."
    assert summary["registered_family_count"] >= 75
    assert summary["synthetic_benchmark_result_count"] >= 4
    assert summary["proof_priority_candidate_count"] >= 10
    assert summary["field_validated_family_count"] == 0
    assert summary["claimable_family_count"] == 0
    assert "No." in summary["safe_answer_to_have_we_tested_all"]


def test_requested_candidate_universe_tracks_core_nature_and_baseline_items():
    module = load_module()
    payload = module.build_audit()
    coverage = {row["requested_candidate"]: row for row in payload["requested_universe_coverage"]}

    assert coverage["mycelium/fungus networks"]["matched_families"] == ["mycelium_network"]
    assert coverage["slime mold / Physarum routing"]["matched_families"] == ["slime_mold_routing"]
    assert coverage["bee foraging / waggle routing"]["matched_families"] == ["bee_foraging_paths"]
    assert coverage["brachistochrone paths"]["matched_families"] == ["brachistochrone_descent"]
    assert coverage["Dijkstra shortest path"]["coverage_stage"] == "covered_as_baseline"
    assert coverage["min-cost flow"]["coverage_stage"] == "covered_as_baseline"


def test_unvalidated_registry_candidates_remain_visible():
    module = load_module()
    payload = module.build_audit()
    families = {row["family"]: row for row in payload["family_coverage"]}

    assert families["mycelium_network"]["synthetic_stage"] == "registered_but_test_spec_missing"
    assert families["slime_mold_routing"]["synthetic_stage"] == "test_spec_ready_no_result"
    assert families["kuramoto_phase_coupling"]["synthetic_stage"] == "synthetic_benchmark_result_present"
    assert families["kuramoto_phase_coupling"]["claimable_stage"] == "controlled_synthetic_result_only"
    assert families["kuramoto_phase_coupling"]["live_stage"] == "live_sources_wired_for_replay_not_live_win"


def test_markdown_answer_is_direct_and_safe():
    module = load_module()
    rendered = module.render_markdown(module.build_audit())

    assert "Geometry Synthetic/Live Coverage Audit" in rendered
    assert "No. The registered universe is ranked" in rendered
    assert "Field-validated families: `0`" in rendered
    assert "guaranteed profit" not in rendered.lower()
    assert "award certainty" in rendered.lower()
