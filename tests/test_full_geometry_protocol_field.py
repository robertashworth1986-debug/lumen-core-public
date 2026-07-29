from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_FULL_GEOMETRY_PROTOCOL_FIELD.py"


def load_module():
    spec = importlib.util.spec_from_file_location("full_geometry_protocol_field", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_full_registry_is_accounted_for_without_cross_lane_ranking():
    module = load_module()
    payload = module.build_matrix()
    family_ids = [row["family_id"] for row in payload["families"]]

    assert payload["schema"] == "full_geometry_protocol_field_v2"
    assert payload["summary"]["registered_family_count"] == 140
    assert payload["summary"]["registered_lane_count"] == 12
    assert payload["summary"]["all_registered_families_accounted_for"] is True
    assert payload["summary"]["cross_lane_ranking_performed"] is False
    assert payload["claim_gate"]["cross_lane_champion_allowed"] is False
    assert len(family_ids) == len(set(family_ids)) == 140


def test_execution_is_not_inferred_from_registry_specification():
    module = load_module()
    payload = module.build_matrix()
    by_id = {row["family_id"]: row for row in payload["families"]}

    assert by_id["leaf_veins"]["frozen_generated_benchmark_executed"] is True
    assert by_id["leaf_veins"]["source_conditioned_replay"]
    assert by_id["termite_mound_ventilation"]["frozen_generated_benchmark_executed"] is True
    assert by_id["slime_mold_routing"]["implementation_present"] is True
    assert by_id["slime_mold_routing"]["frozen_generated_benchmark_executed"] is True
    assert by_id["slime_mold_routing"]["disposition"] == "EXECUTED_FROZEN_GENERATED_BENCHMARK"
    assert by_id["percolation_threshold_networks"]["implementation_present"] is False
    assert (
        by_id["percolation_threshold_networks"]["disposition"]
        == "PERFORMANCE_IMPLEMENTATION_REQUIRED"
    )
    assert payload["summary"]["all_registered_families_performance_executed"] is False


def test_confirmatory_audit_is_hash_verified_and_nonpromotions_are_retained():
    module = load_module()
    payload = module.build_matrix()
    by_id = {row["family_id"]: row for row in payload["families"]}

    receipt = payload["inputs"]["confirmatory_audit"]
    assert receipt["declared_audit_sha256_valid"] is True
    assert payload["summary"]["confirmatory_audited_count"] == 22
    assert payload["summary"]["development_preselected_count"] == 4
    assert payload["summary"]["internal_confirmatory_pass_count"] == 2
    assert payload["summary"]["confirmatory_nonpromotion_count"] == 2
    assert payload["summary"]["descriptive_only_confirmatory_count"] == 18

    assert by_id["leaf_veins"]["confirmatory_audit"]["decision"] == (
        "NOT_PROMOTED_CONFIRMATORY_GATE_FAILED"
    )
    assert by_id["brachistochrone_descent"]["confirmatory_audit"]["confirmatory_pass"] is False
    assert by_id["thermal_plume_convection"]["confirmatory_audit"]["confirmatory_pass"] is True
    assert by_id["kuramoto_phase_coupling"]["confirmatory_audit"]["confirmatory_pass"] is True
    assert by_id["leaf_veins"]["external_validation"] is False


def test_every_family_carries_lane_protocol_and_claim_boundaries():
    module = load_module()
    payload = module.build_matrix()

    for row in payload["families"]:
        assert row["protocol_baselines"]
        assert row["protocol_metrics"]
        assert row["field_validated"] is False
        assert row["certified_or_operationally_approved"] is False
        assert row["external_validation"] is False
    assert "not field validation" in payload["evidence_boundary"].lower()
    assert payload["summary"]["certification_claim_allowed"] is False
    assert payload["claim_gate"]["internal_lumengrade_is_external_certification"] is False


def test_lane_protocol_lists_remain_structured_ids():
    module = load_module()
    payload = module.build_matrix()
    by_id = {row["family_id"]: row for row in payload["families"]}
    by_lane = {row["lane"]: row for row in payload["lane_summary"]}

    expected = ["dijkstra", "a_star", "min_cost_flow", "k_shortest_redundancy"]
    assert by_id["bee_foraging_paths"]["protocol_baselines"] == expected
    assert by_lane["mission_network_routing"]["protocol_baselines"] == expected
    assert all("[" not in item and "'" not in item for item in expected)


def test_declared_source_hash_mismatch_fails_closed(tmp_path):
    module = load_module()
    evidence = tmp_path / "latest.json"
    evidence.write_text(
        json.dumps(
            {
                "schema": "test",
                "protocol": {"source_sha256": "a" * 64},
                "strategies": [
                    {
                        "kind": "geometry_family",
                        "family_id": "slime_mold_routing",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    families, receipt = module.evidence_geometry_families(
        evidence,
        expected_source_sha256="b" * 64,
    )

    assert families == set()
    assert receipt["source_sha256_valid"] is False
    assert receipt["execution_accepted"] is False
    assert receipt["source_binding_status"] == "source_hash_mismatch_execution_rejected"
