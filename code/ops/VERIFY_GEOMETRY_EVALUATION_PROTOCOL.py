#!/usr/bin/env python3
"""Fail-closed verifier for the LumenCore geometry evaluation protocol."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Any


EXPECTED_REPOSITORY = "robertashworth1986-debug/lumen-core-public"
MAX_PROTOCOL_BYTES = 500_000

EXPECTED_TOP_LEVEL_KEYS = {
    "schema_version",
    "generated_utc",
    "repository",
    "status",
    "purpose",
    "governing_rule",
    "geometry_models",
    "zero_credit_candidate_labels",
    "related_analysis_methods_not_geometry",
    "claim_levels",
    "task_lanes",
    "required_declarations",
    "required_baselines",
    "required_checks",
    "comparison_rules",
    "claim_level_requirements",
    "evidence_promotion",
    "prohibited_claims",
    "current_result_state",
}

GEOMETRY_MODELS = {
    "euclidean_cartesian",
    "spherical_or_constant_curvature",
    "riemannian_manifold",
    "graph_geodesic",
    "topology_aware",
    "parametric_spiral_helix_branching_gyroid_phyllotactic",
}

ZERO_CREDIT_CANDIDATES = {
    "brachistochrone",
    "logarithmic_spiral",
    "helix",
    "gyroid",
    "voronoi_partition",
    "phyllotactic_packing",
    "mycelium_inspired_network",
    "slime_mold_inspired_network",
    "root_and_leaf_venation_network",
    "vascular_or_bronchial_branching",
    "termite_ventilation_inspired_network",
    "bird_v_formation",
    "schooling_or_flocking_formation",
    "magnetic_field_line_parameterization",
    "toroidal_field_parameterization",
    "circle_packing_flower_of_life_label",
}

ANALYSIS_METHODS = {
    "frobenius_series_local_solution_analysis",
    "dimensional_analysis",
    "stability_and_boundedness_analysis",
    "conservation_or_balance_residual_analysis",
    "mesh_or_resolution_convergence_analysis",
}

CLAIM_LEVELS = [
    "visualization_only",
    "geometric_optimization",
    "physics_informed",
    "physics_constrained",
    "experimentally_validated",
]

TASK_LANES = {
    "routing_and_networks",
    "formation_and_control",
    "sensor_coverage_and_tasking",
    "materials_structures_and_packaging",
    "visualization_and_evidence_navigation",
}

REQUIRED_DECLARATIONS = {
    "task_lane",
    "claim_level",
    "geometry_model",
    "dimensionality",
    "coordinate_system_or_chart",
    "units_for_every_physical_quantity",
    "distance_or_metric_definition",
    "curvature_sign_and_convention",
    "embedding_or_intrinsic_representation",
    "boundary_conditions",
    "initial_conditions",
    "discretization_or_mesh",
    "numerical_tolerances",
    "solver_and_version",
    "random_seed_registry",
    "data_rights_and_source",
    "development_validation_holdout_split",
    "one_primary_metric",
    "acceptance_threshold",
    "compute_and_memory_budget",
    "known_limitations",
}

REQUIRED_BASELINES = {
    "incumbent_or_domain_baseline",
    "straight_or_plain_euclidean_baseline",
    "randomized_or_null_baseline",
    "geometry_only_ablation",
    "control_or_algorithm_only_ablation",
    "hybrid_candidate",
}

REQUIRED_CHECKS = {
    "dimensional_analysis",
    "coordinate_transform_consistency",
    "metric_symmetry_or_declared_asymmetry",
    "distance_nonnegativity_or_declared_pseudometric",
    "curvature_convention_consistency",
    "boundary_and_initial_condition_consistency",
    "numerical_stability",
    "mesh_or_resolution_convergence_where_applicable",
    "invariance_or_equivariance_checks_where_claimed",
    "conservation_or_balance_checks_where_physics_claimed",
    "causality_and_time_order_where_dynamic",
    "constraint_satisfaction",
    "negative_control",
    "out_of_distribution_or_stress_test",
    "uncertainty_or_confidence_interval",
    "compute_cost_accounting",
    "negative_result_retention",
}

COMPARISON_RULES = {
    "one_primary_metric_required": True,
    "secondary_metrics_may_not_override_primary_failure": True,
    "matched_data_and_seed_sets_required": True,
    "matched_compute_budget_required_or_explicitly_normalized": True,
    "post_outcome_tuning_prohibited": True,
    "cross_lane_ranking_prohibited": True,
    "universal_champion_allowed": False,
    "simpler_baseline_wins_ties": True,
    "failure_and_incomplete_results_retained": True,
}

PROHIBITED_CLAIMS = {
    "universal_geometry_superiority",
    "non_euclidean_is_inherently_better",
    "simulation_equals_field_validation",
    "visualization_equals_physics",
    "curved_geometry_implies_quantum_behavior",
    "topological_language_without_defined_invariant",
    "manifold_language_without_defined_metric_or_chart",
    "physics_validated_without_units_and_governing_constraints",
    "experimentally_validated_without_external_record",
}

PROMOTION_TRANSITIONS = [
    ("visualization_only", "geometric_optimization"),
    ("geometric_optimization", "physics_informed"),
    ("physics_informed", "physics_constrained"),
    ("physics_constrained", "experimentally_validated"),
]


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


def load_json_strict(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > MAX_PROTOCOL_BYTES:
        raise ValueError(f"protocol exceeds maximum size of {MAX_PROTOCOL_BYTES} bytes")
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_non_finite,
    )
    if not isinstance(value, dict):
        raise ValueError("protocol root must be an object")
    return value


def _require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _require_exact_string_set(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"{label} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} contains duplicate values")
    if set(value) != expected:
        raise ValueError(f"{label} does not match the verifier registry")


def _require_unique_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"{label} must be a non-empty string list")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} contains duplicate values")
    return value


def _parse_utc(value: Any) -> str:
    timestamp = _require_string(value, "generated_utc")
    if not timestamp.endswith("Z"):
        raise ValueError("generated_utc must end in Z")
    try:
        parsed = datetime.fromisoformat(timestamp[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("generated_utc must be a valid RFC3339 timestamp") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("generated_utc must use UTC")
    return timestamp


def verify_protocol(protocol: dict[str, Any]) -> dict[str, Any]:
    if set(protocol) != EXPECTED_TOP_LEVEL_KEYS:
        missing = sorted(EXPECTED_TOP_LEVEL_KEYS - set(protocol))
        unknown = sorted(set(protocol) - EXPECTED_TOP_LEVEL_KEYS)
        raise ValueError(f"top-level key mismatch: missing={missing}, unknown={unknown}")
    if protocol["schema_version"] != "1.0":
        raise ValueError("unsupported schema_version")
    if protocol["repository"] != EXPECTED_REPOSITORY:
        raise ValueError("repository identity mismatch")
    if protocol["status"] != "adopted_protocol_no_result_promotion":
        raise ValueError("status must preserve adopted/no-promotion boundary")
    generated_utc = _parse_utc(protocol["generated_utc"])
    _require_string(protocol["purpose"], "purpose")
    governing_rule = _require_string(protocol["governing_rule"], "governing_rule")
    if "No geometry is sacred" not in governing_rule:
        raise ValueError("governing rule must preserve baseline-first language")

    _require_exact_string_set(protocol["geometry_models"], GEOMETRY_MODELS, "geometry_models")
    _require_exact_string_set(
        protocol["zero_credit_candidate_labels"],
        ZERO_CREDIT_CANDIDATES,
        "zero_credit_candidate_labels",
    )
    _require_exact_string_set(
        protocol["related_analysis_methods_not_geometry"],
        ANALYSIS_METHODS,
        "related_analysis_methods_not_geometry",
    )
    if protocol["claim_levels"] != CLAIM_LEVELS:
        raise ValueError("claim_levels must preserve the ordered promotion ladder")

    lanes = protocol["task_lanes"]
    if not isinstance(lanes, list) or len(lanes) != len(TASK_LANES):
        raise ValueError("task_lanes must contain the complete lane registry")
    observed_lanes: set[str] = set()
    for lane in lanes:
        if not isinstance(lane, dict) or set(lane) != {
            "id",
            "allowed_models",
            "candidate_metrics",
            "required_physical_or_operational_constraints",
        }:
            raise ValueError("every task lane must use the exact lane schema")
        lane_id = _require_string(lane["id"], "task lane id")
        if lane_id in observed_lanes:
            raise ValueError(f"duplicate task lane: {lane_id}")
        observed_lanes.add(lane_id)
        models = _require_unique_string_list(lane["allowed_models"], f"{lane_id}.allowed_models")
        if not set(models).issubset(GEOMETRY_MODELS):
            raise ValueError(f"{lane_id} references an unknown geometry model")
        _require_unique_string_list(lane["candidate_metrics"], f"{lane_id}.candidate_metrics")
        _require_unique_string_list(
            lane["required_physical_or_operational_constraints"],
            f"{lane_id}.required_physical_or_operational_constraints",
        )
    if observed_lanes != TASK_LANES:
        raise ValueError("task lane ids do not match the verifier registry")

    _require_exact_string_set(
        protocol["required_declarations"], REQUIRED_DECLARATIONS, "required_declarations"
    )
    _require_exact_string_set(protocol["required_baselines"], REQUIRED_BASELINES, "required_baselines")
    _require_exact_string_set(protocol["required_checks"], REQUIRED_CHECKS, "required_checks")
    if protocol["comparison_rules"] != COMPARISON_RULES:
        raise ValueError("comparison_rules drift from the fail-closed registry")

    level_requirements = protocol["claim_level_requirements"]
    if not isinstance(level_requirements, dict) or set(level_requirements) != set(CLAIM_LEVELS):
        raise ValueError("claim_level_requirements must cover every claim level exactly")
    for level, requirements in level_requirements.items():
        _require_unique_string_list(requirements, f"claim_level_requirements.{level}")

    promotions = protocol["evidence_promotion"]
    if not isinstance(promotions, list) or len(promotions) != len(PROMOTION_TRANSITIONS):
        raise ValueError("evidence_promotion must contain the complete ordered ladder")
    for index, promotion in enumerate(promotions):
        if not isinstance(promotion, dict) or set(promotion) != {"from", "to", "requires"}:
            raise ValueError("every evidence promotion must use the exact promotion schema")
        observed = (promotion["from"], promotion["to"])
        if observed != PROMOTION_TRANSITIONS[index]:
            raise ValueError("evidence promotion order or transition drift")
        _require_unique_string_list(promotion["requires"], f"evidence_promotion[{index}].requires")

    _require_exact_string_set(protocol["prohibited_claims"], PROHIBITED_CLAIMS, "prohibited_claims")

    state = protocol["current_result_state"]
    if not isinstance(state, dict) or set(state) != {
        "protocol_adopted",
        "task_specific_experiments_registered",
        "experimentally_validated_results",
        "universal_champion",
    }:
        raise ValueError("current_result_state must use the exact state schema")
    if state["protocol_adopted"] is not True:
        raise ValueError("protocol_adopted must be true")
    for field in ("task_specific_experiments_registered", "experimentally_validated_results"):
        if type(state[field]) is not int or state[field] != 0:
            raise ValueError(f"{field} must remain integer zero until separately reviewed")
    if state["universal_champion"] is not False:
        raise ValueError("universal_champion must remain false")

    return {
        "valid": True,
        "schema_version": protocol["schema_version"],
        "generated_utc": generated_utc,
        "task_lane_count": len(lanes),
        "zero_credit_candidate_count": len(protocol["zero_credit_candidate_labels"]),
        "registered_experiment_count": 0,
        "experimentally_validated_result_count": 0,
        "universal_champion": False,
    }


def verify_repository_contract(root: Path) -> dict[str, Any]:
    document = (root / "docs" / "GEOMETRY_EVALUATION_PROTOCOL_V1.md").read_text(encoding="utf-8")
    index = (root / "EVIDENCE_INDEX.md").read_text(encoding="utf-8")
    required_document_text = (
        "No geometry is sacred",
        "Candidate labels receive zero credit",
        "Frobenius series are classified separately",
        "zero registered task-specific experiments",
        "zero experimentally validated results",
    )
    missing_document = [item for item in required_document_text if item not in document]
    if missing_document:
        raise ValueError(f"protocol document is missing claim boundaries: {missing_document}")
    for required_path in (
        "config/geometry_evaluation_protocol_v1.json",
        "code/ops/VERIFY_GEOMETRY_EVALUATION_PROTOCOL.py",
        "docs/GEOMETRY_EVALUATION_PROTOCOL_V1.md",
    ):
        if required_path not in index:
            raise ValueError(f"EVIDENCE_INDEX.md is missing geometry protocol entrypoint {required_path}")
    return {"repository_contract_valid": True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="config/geometry_evaluation_protocol_v1.json")
    parser.add_argument("--root", default=".")
    parser.add_argument("--skip-repository-contract", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        protocol = load_json_strict(Path(args.path))
        result = verify_protocol(protocol)
        if not args.skip_repository_contract:
            result.update(verify_repository_contract(Path(args.root).resolve()))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        failure = {"valid": False, "error": str(exc)}
        print(json.dumps(failure, sort_keys=True) if args.json else f"FAIL: {exc}")
        return 1
    print(json.dumps(result, sort_keys=True) if args.json else f"PASS: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
