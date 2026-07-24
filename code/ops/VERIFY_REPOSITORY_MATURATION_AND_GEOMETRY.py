#!/usr/bin/env python3
"""Fail-closed verifier for the repository maturation and geometry protocols."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Any

EXPECTED_REPOSITORY = "robertashworth1986-debug/lumen-core-public"
MAX_JSON_BYTES = 2_000_000

EXPECTED_PRODUCT_SPINE = [
    "proof_capsule",
    "prooflock",
    "external_replication_contract",
    "independent_executor_package",
    "bounded_paid_pilot",
    "buyer_or_transaction_packet",
]

EXPECTED_DISPOSITION_KEYS = {
    "merged_canonical",
    "closed_preserved_research_or_superseded",
    "open_active_external_or_deadline",
    "open_merge_candidate",
    "open_consolidation_source",
    "open_retire_now",
    "open_replace_overlay",
}

EXPECTED_RETIRE_NOW = {16, 42, 53, 56, 58, 59, 63, 65}
EXPECTED_MERGE_ORDER = set(range(1, 9))
EXPECTED_FALSE_CLAIMS = {
    "independent_validation_complete",
    "field_validation_complete",
    "commercial_validation_complete",
    "certified_safety",
    "agency_endorsement",
    "universal_geometry_superiority",
    "audited_revenue",
    "public_transaction_valuation",
}

EXPECTED_GEOMETRY_MODELS = {
    "euclidean_cartesian",
    "spherical_or_constant_curvature",
    "riemannian_manifold",
    "graph_geodesic",
    "topology_aware",
    "parametric_spiral_helix_branching_gyroid_phyllotactic",
}

EXPECTED_CLAIM_LEVELS = [
    "visualization_only",
    "geometric_optimization",
    "physics_informed",
    "physics_constrained",
    "experimentally_validated",
]

REQUIRED_GEOMETRY_DECLARATIONS = {
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

REQUIRED_GEOMETRY_CHECKS = {
    "dimensional_analysis",
    "coordinate_transform_consistency",
    "curvature_convention_consistency",
    "numerical_stability",
    "constraint_satisfaction",
    "negative_control",
    "out_of_distribution_or_stress_test",
    "uncertainty_or_confidence_interval",
    "compute_cost_accounting",
    "negative_result_retention",
}

REQUIRED_PROHIBITED_GEOMETRY_CLAIMS = {
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
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError(f"JSON exceeds maximum size of {MAX_JSON_BYTES} bytes")
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_non_finite,
    )
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def require_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def require_unique_strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{label} must contain non-empty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} contains duplicate values")
    return value


def require_unique_positive_ints(value: Any, label: str, *, allow_empty: bool = False) -> list[int]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError(f"{label} must be a {'possibly empty ' if allow_empty else 'non-empty '}list")
    if any(not isinstance(item, int) or isinstance(item, bool) or item <= 0 for item in value):
        raise ValueError(f"{label} must contain positive integers")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} contains duplicate pull requests")
    return value


def require_utc_timestamp(value: Any, label: str = "generated_utc") -> str:
    timestamp = require_non_empty_string(value, label)
    if not timestamp.endswith("Z"):
        raise ValueError(f"{label} must end in Z")
    try:
        parsed = datetime.fromisoformat(timestamp[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{label} must be valid RFC3339 UTC") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{label} must use UTC")
    return timestamp


def verify_audit(audit: dict[str, Any]) -> dict[str, Any]:
    if audit.get("schema_version") != "1.0":
        raise ValueError("unsupported audit schema_version")
    require_utc_timestamp(audit.get("generated_utc"))
    if audit.get("repository") != EXPECTED_REPOSITORY:
        raise ValueError("audit repository identity mismatch")
    require_non_empty_string(audit.get("purpose"), "audit purpose")
    if audit.get("canonical_lane") != "proof_to_pilot_technical_claim_assurance":
        raise ValueError("canonical lane drift")
    if audit.get("canonical_product_spine") != EXPECTED_PRODUCT_SPINE:
        raise ValueError("canonical product spine drift")

    observed = require_unique_positive_ints(
        audit.get("observed_pull_requests"), "observed_pull_requests"
    )
    dispositions = audit.get("dispositions")
    if not isinstance(dispositions, dict) or set(dispositions) != EXPECTED_DISPOSITION_KEYS:
        raise ValueError("disposition registry keys mismatch")

    disposition_flat: list[int] = []
    for name in sorted(EXPECTED_DISPOSITION_KEYS):
        values = require_unique_positive_ints(
            dispositions[name], f"dispositions.{name}", allow_empty=True
        )
        disposition_flat.extend(values)

    if len(disposition_flat) != len(set(disposition_flat)):
        raise ValueError("pull request appears in multiple dispositions")
    if set(disposition_flat) != set(observed):
        missing = sorted(set(observed) - set(disposition_flat))
        extra = sorted(set(disposition_flat) - set(observed))
        raise ValueError(
            f"dispositions must exactly cover observed pull requests; missing={missing} extra={extra}"
        )
    if set(dispositions["open_retire_now"]) != EXPECTED_RETIRE_NOW:
        raise ValueError("open_retire_now registry drift")

    findings = audit.get("priority_findings")
    if not isinstance(findings, list) or not findings:
        raise ValueError("priority_findings must be a non-empty list")
    finding_ids: set[str] = set()
    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError("every priority finding must be an object")
        finding_id = require_non_empty_string(finding.get("id"), "finding id")
        if finding_id in finding_ids:
            raise ValueError(f"duplicate finding id: {finding_id}")
        finding_ids.add(finding_id)
        if finding.get("severity") not in {"p0", "p1", "p2"}:
            raise ValueError(f"finding {finding_id}: invalid severity")
        require_non_empty_string(finding.get("state"), f"finding {finding_id} state")
        require_non_empty_string(finding.get("finding"), f"finding {finding_id} text")
        require_non_empty_string(
            finding.get("required_action"), f"finding {finding_id} required_action"
        )

    route_finding = next(
        (item for item in findings if item.get("id") == "p0-public-evidence-route"),
        None,
    )
    if route_finding is None or route_finding.get("severity") != "p0":
        raise ValueError("P0 public evidence route finding is required")
    route_text = " ".join(
        str(route_finding.get(key, ""))
        for key in ("finding", "required_action")
    )
    if "/evidence/" not in route_text or "502" not in route_text:
        raise ValueError("P0 route finding must preserve the /evidence/ HTTP 502 fact")

    merge_program = audit.get("merge_program")
    if not isinstance(merge_program, list) or len(merge_program) != 8:
        raise ValueError("merge_program must contain eight ordered actions")
    orders: set[int] = set()
    merge_prs: list[int] = []
    for item in merge_program:
        if not isinstance(item, dict):
            raise ValueError("every merge program item must be an object")
        order = item.get("order")
        if not isinstance(order, int) or isinstance(order, bool):
            raise ValueError("merge order must be an integer")
        orders.add(order)
        merge_prs.extend(
            require_unique_positive_ints(item.get("pull_requests"), f"merge order {order} pull_requests")
        )
        require_non_empty_string(item.get("action"), f"merge order {order} action")
        require_non_empty_string(item.get("outcome"), f"merge order {order} outcome")
    if orders != EXPECTED_MERGE_ORDER:
        raise ValueError("merge order must exactly cover 1 through 8")
    if len(merge_prs) != len(set(merge_prs)):
        raise ValueError("pull request appears in multiple merge-program actions")

    retirement = audit.get("retirement_program")
    if not isinstance(retirement, dict) or set(retirement) != {
        "retire_now",
        "retire_after_successor",
    }:
        raise ValueError("retirement_program fields mismatch")
    retire_now = require_unique_positive_ints(
        retirement["retire_now"].get("pull_requests"),
        "retirement_program.retire_now.pull_requests",
    )
    if set(retire_now) != EXPECTED_RETIRE_NOW:
        raise ValueError("retirement retire-now set must match dispositions")

    maturity = audit.get("maturity_definition")
    if not isinstance(maturity, dict) or list(maturity) != [
        "level_1", "level_2", "level_3", "level_4", "level_5", "level_6"
    ]:
        raise ValueError("maturity_definition must contain ordered levels 1 through 6")
    if audit.get("current_supported_maturity") != "level_3":
        raise ValueError("current supported maturity must remain level_3")
    false_claims = set(
        require_unique_strings(audit.get("current_false_claims"), "current_false_claims")
    )
    if false_claims != EXPECTED_FALSE_CLAIMS:
        raise ValueError("current false-claim registry drift")

    return {
        "valid": True,
        "observed_pr_count": len(observed),
        "open_merge_candidate_count": len(dispositions["open_merge_candidate"]),
        "open_retire_now_count": len(dispositions["open_retire_now"]),
        "merge_action_count": len(merge_program),
        "current_supported_maturity": audit["current_supported_maturity"],
    }


def verify_geometry(protocol: dict[str, Any]) -> dict[str, Any]:
    if protocol.get("schema_version") != "1.0":
        raise ValueError("unsupported geometry schema_version")
    require_utc_timestamp(protocol.get("generated_utc"))
    if protocol.get("repository") != EXPECTED_REPOSITORY:
        raise ValueError("geometry repository identity mismatch")
    if protocol.get("status") != "protocol_only_no_result_promotion":
        raise ValueError("geometry protocol must remain non-promotional")
    require_non_empty_string(protocol.get("purpose"), "geometry purpose")
    require_non_empty_string(protocol.get("governing_rule"), "geometry governing_rule")

    models = set(require_unique_strings(protocol.get("geometry_models"), "geometry_models"))
    if models != EXPECTED_GEOMETRY_MODELS:
        raise ValueError("geometry model registry drift")
    levels = require_unique_strings(protocol.get("claim_levels"), "claim_levels")
    if levels != EXPECTED_CLAIM_LEVELS:
        raise ValueError("claim-level registry drift")

    declarations = set(
        require_unique_strings(protocol.get("required_declarations"), "required_declarations")
    )
    if not REQUIRED_GEOMETRY_DECLARATIONS.issubset(declarations):
        raise ValueError("geometry declarations are missing units, coordinates, metric, curvature, or protocol controls")

    baselines = set(require_unique_strings(protocol.get("required_baselines"), "required_baselines"))
    if baselines != REQUIRED_BASELINES:
        raise ValueError("required geometry baseline registry drift")
    checks = set(require_unique_strings(protocol.get("required_checks"), "required_checks"))
    if not REQUIRED_GEOMETRY_CHECKS.issubset(checks):
        raise ValueError("required geometry checks are incomplete")

    comparison = protocol.get("comparison_rules")
    required_true = {
        "one_primary_metric_required",
        "secondary_metrics_may_not_override_primary_failure",
        "matched_data_and_seed_sets_required",
        "post_outcome_tuning_prohibited",
        "cross_lane_ranking_prohibited",
        "simpler_baseline_wins_ties",
        "failure_and_incomplete_results_retained",
    }
    if not isinstance(comparison, dict):
        raise ValueError("comparison_rules must be an object")
    for key in required_true:
        if comparison.get(key) is not True:
            raise ValueError(f"comparison rule must remain true: {key}")
    if comparison.get("universal_champion_allowed") is not False:
        raise ValueError("universal geometry champion must remain prohibited")

    lanes = protocol.get("task_lanes")
    if not isinstance(lanes, list) or len(lanes) < 5:
        raise ValueError("at least five task-specific geometry lanes are required")
    lane_ids: set[str] = set()
    for lane in lanes:
        if not isinstance(lane, dict):
            raise ValueError("every geometry task lane must be an object")
        lane_id = require_non_empty_string(lane.get("id"), "task lane id")
        if lane_id in lane_ids:
            raise ValueError(f"duplicate task lane: {lane_id}")
        lane_ids.add(lane_id)
        allowed = set(require_unique_strings(lane.get("allowed_models"), f"lane {lane_id} allowed_models"))
        if not allowed.issubset(EXPECTED_GEOMETRY_MODELS):
            raise ValueError(f"lane {lane_id} references an unknown geometry model")
        require_unique_strings(lane.get("candidate_metrics"), f"lane {lane_id} candidate_metrics")
        require_unique_strings(
            lane.get("required_physical_or_operational_constraints"),
            f"lane {lane_id} constraints",
        )

    level_requirements = protocol.get("claim_level_requirements")
    if not isinstance(level_requirements, dict) or list(level_requirements) != EXPECTED_CLAIM_LEVELS:
        raise ValueError("claim-level requirement registry mismatch")
    for level in EXPECTED_CLAIM_LEVELS:
        require_unique_strings(level_requirements[level], f"claim level {level} requirements")
    if "independent_or_external_execution_record" not in level_requirements["experimentally_validated"]:
        raise ValueError("experimental validation requires an external execution record")

    promotions = protocol.get("evidence_promotion")
    expected_transitions = list(zip(EXPECTED_CLAIM_LEVELS, EXPECTED_CLAIM_LEVELS[1:]))
    if not isinstance(promotions, list) or len(promotions) != len(expected_transitions):
        raise ValueError("geometry evidence-promotion registry mismatch")
    observed_transitions: list[tuple[str, str]] = []
    for promotion in promotions:
        if not isinstance(promotion, dict):
            raise ValueError("every geometry promotion must be an object")
        observed_transitions.append((promotion.get("from"), promotion.get("to")))
        require_unique_strings(promotion.get("requires"), "geometry promotion requirements")
    if observed_transitions != expected_transitions:
        raise ValueError("geometry promotion transitions must be ordered and adjacent")

    prohibited = set(
        require_unique_strings(protocol.get("prohibited_claims"), "prohibited_claims")
    )
    if prohibited != REQUIRED_PROHIBITED_GEOMETRY_CLAIMS:
        raise ValueError("prohibited geometry claim registry drift")

    result_state = protocol.get("current_result_state")
    if not isinstance(result_state, dict):
        raise ValueError("current_result_state must be an object")
    if result_state.get("protocol_adopted") is not False:
        raise ValueError("protocol cannot claim adoption from its own draft")
    if result_state.get("task_specific_experiments_registered") != 0:
        raise ValueError("no task-specific experiment is registered by this protocol")
    if result_state.get("experimentally_validated_results") != 0:
        raise ValueError("no experimentally validated geometry result exists")
    if result_state.get("universal_champion") is not False:
        raise ValueError("universal geometry champion must remain false")

    return {
        "valid": True,
        "geometry_model_count": len(models),
        "claim_level_count": len(levels),
        "task_lane_count": len(lanes),
        "experimentally_validated_results": 0,
        "universal_champion": False,
    }


def verify_docs(root: Path) -> dict[str, Any]:
    required = {
        "audit_doc": root / "docs/REPOSITORY_MATURATION_AUDIT_2026-07-24.md",
        "geometry_doc": root / "docs/GEOMETRY_EVALUATION_PROTOCOL_V1.md",
        "audit_json": root / "config/repository_maturation_audit_v1.json",
        "geometry_json": root / "config/geometry_evaluation_protocol_v1.json",
    }
    missing = [name for name, path in required.items() if not path.is_file()]
    if missing:
        raise ValueError(f"required maturation files are missing: {missing}")
    audit_text = required["audit_doc"].read_text(encoding="utf-8")
    geometry_text = required["geometry_doc"].read_text(encoding="utf-8")
    if "Proof Capsule -> ProofLock" not in audit_text:
        raise ValueError("audit documentation omits the canonical product spine")
    if "HTTP 502" not in audit_text or "/evidence/" not in audit_text:
        raise ValueError("audit documentation omits the public evidence-route defect")
    if "No geometry is sacred until it wins" not in geometry_text:
        raise ValueError("geometry documentation omits the governing rule")
    if "Simulation is not field validation" not in audit_text:
        raise ValueError("audit documentation omits the simulation boundary")
    return {"valid": True, "required_file_count": len(required)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--audit",
        default="config/repository_maturation_audit_v1.json",
    )
    parser.add_argument(
        "--geometry",
        default="config/geometry_evaluation_protocol_v1.json",
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        audit_result = verify_audit(load_json_strict(Path(args.audit)))
        geometry_result = verify_geometry(load_json_strict(Path(args.geometry)))
        docs_result = verify_docs(Path(args.root).resolve())
        result = {
            "valid": True,
            "audit": audit_result,
            "geometry": geometry_result,
            "docs": docs_result,
        }
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        failure = {"valid": False, "error": str(exc)}
        print(json.dumps(failure, sort_keys=True) if args.json else f"FAIL: {exc}")
        return 1

    print(json.dumps(result, sort_keys=True) if args.json else f"PASS: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
