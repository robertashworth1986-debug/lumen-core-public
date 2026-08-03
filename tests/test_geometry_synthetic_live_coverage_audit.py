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

    assert payload["schema"] == "geometry_synthetic_live_coverage_audit_v3"
    assert payload["policy"]["rule"] == (
        "Synthetic discovers. Direct measured replay tests. "
        "Field validation proves operational value."
    )
    assert summary["registered_family_count"] == 140
    assert summary["implementation_present_count"] == 35
    assert summary["implementation_required_count"] == 105
    assert summary["frozen_generated_executed_count"] == 30
    assert summary["source_conditioned_replay_count"] == 4
    assert summary["source_conditioned_replay_receipt_family_count"] == 4
    assert summary["qualified_direct_source_link_count"] == 10
    assert summary["qualified_conditioning_source_link_count"] == 12
    assert summary["context_only_measured_source_link_count"] == 46
    assert summary["direct_source_replay_build_ready_lane_count"] == 3
    assert summary["source_conditioned_simulation_build_ready_lane_count"] == 4
    assert summary["development_preselected_count"] == 4
    assert summary["internal_confirmatory_pass_count"] == 2
    assert summary["confirmatory_nonpromotion_count"] == 2
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

    assert (
        families["mycelium_network"]["synthetic_stage"]
        == "synthetic_benchmark_result_present"
    )
    assert (
        families["slime_mold_routing"]["synthetic_stage"]
        == "synthetic_benchmark_result_present"
    )
    assert (
        families["kuramoto_phase_coupling"]["synthetic_stage"]
        == "synthetic_benchmark_result_present"
    )
    assert (
        families["kuramoto_phase_coupling"]["claimable_stage"]
        == "internal_confirmatory_pass_not_field_validated"
    )
    assert (
        families["kuramoto_phase_coupling"]["live_stage"]
        == "source_conditioned_replay_present"
    )


def test_natural_form_sentinels_are_executed_but_not_promoted_or_field_validated():
    module = load_module()
    payload = module.build_audit()
    sentinels = {row["family"]: row for row in payload["natural_form_sentinel_coverage"]}

    assert set(sentinels) == set(module.NATURAL_FORM_SENTINEL_FAMILIES)
    for family_id in module.NATURAL_FORM_SENTINEL_FAMILIES:
        assert sentinels[family_id]["implementation_present"] is True
        assert sentinels[family_id]["frozen_generated_benchmark_executed"] is True
        assert sentinels[family_id]["disposition"] == "EXECUTED_FROZEN_GENERATED_BENCHMARK"
        assert sentinels[family_id]["source_conditioned_replay"] is None
        assert sentinels[family_id]["field_validated"] is False

    queued = {row["family"] for row in payload["natural_form_tournament_queue"]}
    assert set(module.NATURAL_FORM_SENTINEL_FAMILIES).isdisjoint(queued)


def test_source_specific_protocols_use_lane_baselines_without_claiming_execution():
    module = load_module()
    payload = module.build_audit()
    protocols = {
        row["family"]: row for row in payload["family_source_baseline_protocols"]
    }

    assert len(protocols) == payload["summary"]["registered_family_count"] == 140
    bee = protocols["bee_foraging_paths"]
    assert bee["named_baselines"] == [
        "dijkstra",
        "a_star",
        "min_cost_flow",
        "k_shortest_redundancy",
    ]
    assert set(bee["candidate_measured_source_contexts"]) == {
        "NOAA_NCEI",
        "USGS_WATER",
        "CENSUS",
    }
    assert bee["protocol_status"] == "SYNTHETIC_EXECUTED_NEEDS_SOURCE_ADAPTER"

    flying_v = protocols["bird_v_formation_flocking"]
    assert flying_v["named_baselines"] == [
        "independent_shortest_path",
        "consensus_control",
        "model_predictive_control",
    ]
    assert flying_v["source_conditioned_replay_present"] is False
    assert flying_v["protocol_status"] == "SYNTHETIC_EXECUTED_NEEDS_SOURCE_ADAPTER"
    assert "candidate inputs only" in flying_v["claim_note"]


def test_markdown_answer_is_direct_and_safe():
    module = load_module()
    rendered = module.render_markdown(module.build_audit())

    assert "Geometry Synthetic/Live Coverage Audit" in rendered
    assert "No. 140 families are registered" in rendered
    assert "Implementations still required: `105`" in rendered
    assert "Qualified direct-source links: `10`" in rendered
    assert "Source-conditioned simulation build-ready lanes: `4`" in rendered
    assert "Field-validated families: `0`" in rendered
    assert "guaranteed profit" not in rendered.lower()
    assert "award certainty" in rendered.lower()
