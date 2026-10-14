from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATE = ROOT / "config" / "codecheck_independent_execution_receipt_template_v1.json"
FROZEN_PROTOCOL = ROOT / "config" / "reviewer_reproducibility_protocol_v1.json"
FROZEN_PROTOCOL_SHA256 = "c69fb78965cdf420e8354042f1e90d11c6b7dde59f0a4d9fb27d9dec58f4cb01"
MAX_JSON_BYTES = 16_777_216
MAX_ARTIFACT_BYTES = 268_435_456
SHA256 = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_RUNTIME = {
    "system": "Linux",
    "machine": "x86_64",
    "python": "3.11.9",
    "glibc": "2.39",
    "timezone": "UTC",
}
EXPECTED_ENVIRONMENT = {
    "MKL_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "4",
    "OPENBLAS_NUM_THREADS": "1",
    "PYTHONHASHSEED": "0",
    "TZ": "UTC",
}


def reject_duplicate_keys(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_nonfinite(value: str) -> None:
    raise ValueError(f"nonfinite JSON value: {value}")


def finite_json_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite JSON number")
    return number


def read_json(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        raw = stream.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError("JSON exceeds size limit")
    payload = json.loads(raw, object_pairs_hook=reject_duplicate_keys, parse_constant=reject_nonfinite, parse_float=finite_json_float)
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object at {path}")
    return payload


def file_sha256(path: Path) -> str:
    if path.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ValueError("artifact exceeds size limit")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and not any(part in {"", ".", ".."} for part in value.split("/")) and ":" not in value


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def parse_utc(value: Any) -> datetime | None:
    if not nonempty(value) or not value.endswith("Z"):
        return None
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None


def nested_get(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def inspect_manifest(
    rows: Any,
    expected_paths: list[str],
    artifact_root: Path,
) -> dict[str, Any]:
    observations: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        rows = []
    root = artifact_root.resolve()
    for row in rows[:len(expected_paths) + 1]:
        if not isinstance(row, dict):
            observations.append({"safe": False, "matched": False})
            continue
        relative = row.get("path")
        safe = safe_relative_path(relative)
        lexical_target = root / PurePosixPath(relative) if safe else root / "__unsafe__"
        target = lexical_target.resolve()
        symlinked = safe and any(part.is_symlink() for part in (lexical_target, *lexical_target.parents) if part != root and part.is_relative_to(root))
        contained = safe and target.is_relative_to(root) and not symlinked
        present = contained and target.is_file()
        observed_sha = file_sha256(target) if present else None
        observed_bytes = target.stat().st_size if present else None
        observations.append(
            {
                "path": relative,
                "safe": safe,
                "contained": contained,
                "present": present,
                "expected_sha256": row.get("sha256"),
                "observed_sha256": observed_sha,
                "expected_bytes": row.get("bytes"),
                "observed_bytes": observed_bytes,
                "matched": (
                    present
                    and isinstance(row.get("sha256"), str)
                    and bool(SHA256.fullmatch(row["sha256"]))
                    and observed_sha == row["sha256"]
                    and type(row.get("bytes")) is int
                    and 0 <= row["bytes"] <= MAX_ARTIFACT_BYTES
                    and observed_bytes == row["bytes"]
                ),
            }
        )
    observed_paths = [row.get("path") for row in rows if isinstance(row, dict)]
    return {
        "expected_paths": expected_paths,
        "observed_paths": observed_paths,
        "path_order_exact": observed_paths == expected_paths,
        "duplicate_path_count": len([p for p in observed_paths if isinstance(p, str)]) - len({p for p in observed_paths if isinstance(p, str)}),
        "files": observations,
        "all_files_matched": (
            observed_paths == expected_paths
            and len(observations) == len(expected_paths)
            and all(row.get("matched") is True for row in observations)
        ),
    }


def canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def frozen_protocol() -> dict[str, Any]:
    raw = FROZEN_PROTOCOL.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != FROZEN_PROTOCOL_SHA256:
        raise ValueError("reviewer protocol differs from the reviewed pin")
    return read_json(FROZEN_PROTOCOL)


def exact_value(actual: Any, expected: Any) -> bool:
    """Do not accept bools as counts or malformed containers as scalar facts."""
    return type(actual) is type(expected) and actual == expected


def inspect_assertions(rows: Any, expected: dict[str, Any], *, tolerance: float | None = None, relative_tolerance: float | None = None) -> dict[str, Any]:
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        return {"valid": False, "passed": False, "rows": []}
    expected_ids = list(expected)
    if [row.get("assertion_id") for row in rows] != expected_ids:
        return {"valid": False, "passed": False, "rows": rows}
    valid = True
    computed = []
    for row, assertion_id in zip(rows, expected_ids):
        reference = expected[assertion_id]
        metric = type(reference) is float
        allowed = {"assertion_id", "actual", "expected", "passed"}
        actual = row.get("actual")
        row_valid = exact_value(row.get("expected"), reference) and type(row.get("passed")) is bool
        if metric:
            absolute = tolerance if relative_tolerance is None else None
            relative = relative_tolerance
            if absolute is not None:
                allowed.add("absolute_tolerance")
                row_valid = row_valid and exact_value(row.get("absolute_tolerance"), absolute)
            if relative is not None:
                allowed.add("relative_tolerance")
                row_valid = row_valid and exact_value(row.get("relative_tolerance"), relative)
            allowed.update({"absolute_difference", "relative_difference"})
            numeric = type(actual) in {int, float} and math.isfinite(actual)
            difference = abs(actual - reference) if numeric else None
            relative_difference = (difference / abs(reference) if reference else (0.0 if difference == 0.0 else None)) if numeric else None
            passed = numeric and ((absolute is not None and difference <= absolute) or (relative is not None and relative_difference is not None and relative_difference <= relative))
            row_valid = row_valid and numeric and exact_value(row.get("absolute_difference"), difference)
            if relative_difference is not None:
                row_valid = row_valid and exact_value(row.get("relative_difference"), relative_difference)
            else:
                row_valid = row_valid and "relative_difference" not in row
        else:
            passed = exact_value(actual, reference)
            row_valid = row_valid and isinstance(actual, (str, int, bool)) and type(actual) is type(reference)
        row_valid = row_valid and set(row).issubset(allowed) and {"assertion_id", "actual", "expected", "passed"}.issubset(row) and row.get("passed") is bool(passed)
        valid = valid and row_valid
        computed.append(bool(passed))
    return {"valid": valid, "passed": all(computed), "rows": rows}


PROJECTION_EXTRAS = {
    "eia_wave": {"evaluation_rows", "baseline_comparison_count"},
    "eia_residual": {"evaluation_rows", "holm_positive_point_improvement_count"},
    "mda_open_set": {"fixture_chain_sha256"},
}
UNPROJECTED_ASSERTIONS = {"panel_rows", "holdout_rows", "holdout_authorities"}


def inspect_suite(row: Any, contract: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {"valid": False, "negative_gates_preserved": False, "assertions": []}
    identity = all(row.get(key) == contract[key] for key in ("suite_id", "kind", "runner"))
    facts = row.get("fact_projection")
    projection_valid = isinstance(facts, dict) and row.get("fact_projection_sha256") == canonical_sha256(facts)
    # A runner exception is a documented non-pass, not an invented assertion set.
    if row.get("assertions") == [] and row.get("passed") is False:
        error = row.get("error")
        valid = identity and projection_valid and facts == {} and isinstance(error, dict) and nonempty(error.get("type")) and nonempty(error.get("message"))
        return {"valid": bool(valid), "negative_gates_preserved": bool(valid), "assertions": []}
    expected = {key: value for key, value in contract["expected"].items() if key not in {"tolerance", "relative_tolerance"}}
    assertions = inspect_assertions(row.get("assertions"), expected, tolerance=contract["expected"].get("tolerance"), relative_tolerance=contract["expected"].get("relative_tolerance"))
    projected_ids = set(expected) - UNPROJECTED_ASSERTIONS
    expected_keys = projected_ids | PROJECTION_EXTRAS[contract["runner"]]
    projection_valid = projection_valid and set(facts or {}) == expected_keys
    if projection_valid:
        by_id = {assertion["assertion_id"]: assertion for assertion in assertions["rows"]}
        projection_valid = all(key in by_id and exact_value(facts[key], by_id[key].get("actual")) for key in projected_ids)
        for key in PROJECTION_EXTRAS[contract["runner"]]:
            value = facts[key]
            if key == "fixture_chain_sha256":
                projection_valid = projection_valid and isinstance(value, str) and bool(SHA256.fullmatch(value))
            else:
                projection_valid = projection_valid and type(value) is int and value >= 0
        if contract["runner"] == "eia_wave":
            projection_valid = projection_valid and facts["baseline_comparison_count"] == 6
        if contract["runner"] == "eia_residual":
            projection_valid = projection_valid and facts["holm_positive_point_improvement_count"] <= expected["baseline_comparison_count"]
    gates = [key for key, value in expected.items() if value is False]
    preserved = projection_valid and all(facts.get(key) is False for key in gates)
    valid = identity and assertions["valid"] and projection_valid and type(row.get("passed")) is bool and row.get("passed") is assertions["passed"]
    return {"valid": bool(valid), "negative_gates_preserved": bool(preserved), "assertions": assertions["rows"]}


def inspect_capsule_receipt(path: Path, expected_commit: str) -> dict[str, Any]:
    try:
        payload = read_json(path)
        protocol = frozen_protocol()
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        return {"parsed": False, "error": str(exc)}
    suites = payload.get("suites") if isinstance(payload.get("suites"), list) else []
    suite_inspections = [inspect_suite(row, contract) for row, contract in zip(suites, protocol["suites"])]
    frozen = payload.get("frozen_input") if isinstance(payload.get("frozen_input"), dict) else {}
    input_contract = protocol["frozen_inputs"][0]
    input_assertions = inspect_assertions(frozen.get("assertions"), {
        "compressed_sha256": input_contract["compressed_sha256"],
        "uncompressed_sha256": input_contract["uncompressed_sha256"],
        "row_chain_sha256": input_contract["row_chain_sha256"],
        "row_count": input_contract["row_count"],
        "credential_serialized": False,
    })
    frozen_valid = input_assertions["valid"] and frozen.get("input_id") == input_contract["input_id"] and frozen.get("path") == input_contract["path"] and frozen.get("passed") is input_assertions["passed"]
    assertions = input_assertions["rows"] + [
        assertion
        for suite in suites
        if isinstance(suite, dict) and isinstance(suite.get("assertions"), list)
        for assertion in suite["assertions"]
        if isinstance(assertion, dict)
    ]
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    observed = {
        "capsule_status": payload.get("status"),
        "suite_count": len(suites),
        "suite_pass_count": sum(isinstance(suite, dict) and suite.get("passed") is True for suite in suites),
        "assertion_count": len(assertions),
        "assertion_pass_count": sum(row.get("passed") is True for row in assertions),
    }
    return {
        "parsed": True,
        "schema_exact": payload.get("schema") == "reviewer_reproducibility_capsule.v1",
        "source_commit_exact": nested_get(payload, "git", "commit") == expected_commit,
        "observed": observed,
        "protocol_facts_reconciled": (
            payload.get("protocol_id") == protocol["protocol_id"]
            and len(suites) == len(protocol["suites"])
            and all(row["valid"] for row in suite_inspections)
            and frozen_valid
            and all(exact_value(summary.get(key), observed[key]) for key in ("suite_count", "suite_pass_count", "assertion_count", "assertion_pass_count"))
            and summary.get("frozen_input_passed") is input_assertions["passed"]
            and (payload.get("status") != "BOUNDED_REPRODUCIBILITY_PASS" or (input_assertions["passed"] and all(row.get("passed") is True for row in suites)))
            and payload.get("capsule_sha256") == canonical_sha256({key: value for key, value in payload.items() if key != "capsule_sha256"})
        ),
        "dependency_lock_sha256": nested_get(payload, "summary", "dependency_lock_sha256"),
        "protocol_controls_passed": all(
            summary.get(key) is True
            for key in (
                "authoritative_runtime_match",
                "dependency_closure_exact_match",
                "deterministic_environment_match",
                "fixture_tests_executed",
                "fixture_tests_passed",
                "relevant_source_clean",
                "source_state_verified",
            )
        ),
        "negative_gates_preserved": (
            summary.get("external_validation_complete") is False
            and summary.get("agency_certification_complete") is False
            and len(suite_inspections) == len(protocol["suites"])
            and all(row["negative_gates_preserved"] for row in suite_inspections)
        ),
    }


def _inspect_receipt(
    receipt_path: Path,
    artifact_root: Path,
    template_path: Path = DEFAULT_TEMPLATE,
) -> dict[str, Any]:
    template = read_json(template_path)
    receipt = read_json(receipt_path)
    target = template["review_target"]
    reviewer = receipt.get("reviewer") if isinstance(receipt.get("reviewer"), dict) else {}
    execution = receipt.get("execution") if isinstance(receipt.get("execution"), dict) else {}
    runtime = execution.get("runtime") if isinstance(execution.get("runtime"), dict) else {}
    environment = (
        runtime.get("deterministic_environment")
        if isinstance(runtime.get("deterministic_environment"), dict)
        else {}
    )
    result = receipt.get("result") if isinstance(receipt.get("result"), dict) else {}
    attestation = (
        receipt.get("attestation") if isinstance(receipt.get("attestation"), dict) else {}
    )
    claim_state = (
        receipt.get("claim_state") if isinstance(receipt.get("claim_state"), dict) else {}
    )
    expected_paths = [row["path"] for row in template["manifest"]]
    manifest = inspect_manifest(receipt.get("manifest"), expected_paths, artifact_root)
    capsule_path = artifact_root / PurePosixPath(expected_paths[0])
    capsule = inspect_capsule_receipt(capsule_path, target["source_commit"])

    started = parse_utc(execution.get("started_at_utc"))
    completed = parse_utc(execution.get("completed_at_utc"))
    signed = parse_utc(attestation.get("signed_at_utc"))
    generated = parse_utc(receipt.get("generated_at_utc"))
    receipt_claims_false = (
        set(claim_state) == set(template["claim_state"])
        and all(value is False for value in claim_state.values())
    )
    result_claim_keys = {
        "external_validation_complete",
        "agency_certification_complete",
        "field_validation_complete",
        "economic_validation_complete",
        "valuation_validation_complete",
    }
    result_claims_false = result_claim_keys.issubset(result) and all(
        result.get(key) is False
        for key in result_claim_keys
    )
    reviewer_name = reviewer.get("full_name")
    reviewer_checks = {
        "full_name_present": nonempty(reviewer_name),
        "reviewer_is_not_author_name": (
            nonempty(reviewer_name) and reviewer_name.strip().casefold() != "robert ashworth"
        ),
        "affiliation_or_status_present": nonempty(
            reviewer.get("affiliation_or_independent_status")
        ),
        "identity_reference_is_https": (
            nonempty(reviewer.get("identity_reference"))
            and reviewer["identity_reference"].startswith("https://")
        ),
        "relationship_disclosed": nonempty(reviewer.get("relationship_to_author")),
        "conflict_disclosed": nonempty(reviewer.get("conflict_disclosure")),
        "is_author_false": reviewer.get("is_author") is False,
        "not_employed_or_contracted": (
            reviewer.get("employed_or_contracted_by_lumencore") is False
        ),
        "not_paid_for_favorable_result": reviewer.get("paid_for_favorable_result") is False,
        "reviewer_controlled_environment": reviewer.get("reviewer_controlled_environment") is True,
    }
    target_checks = {
        key: nested_get(receipt, "review_target", key) == value
        for key, value in target.items()
    }
    execution_checks = {
        "source_url_exact": execution.get("source_acquisition_url") == target["source_url"],
        "source_commit_exact": execution.get("source_commit") == target["source_commit"],
        "source_tree_clean": execution.get("source_tree_clean") is True,
        "run_command_exact": execution.get("run_command") == target["run_command"],
        "network_disabled": execution.get("network_access_during_execution") is False,
        "dependency_lock_exact": (
            execution.get("dependency_lock_sha256")
            == target["dependency_lock_portable_sha256"]
        ),
        "runtime_exact": all(runtime.get(key) == value for key, value in EXPECTED_RUNTIME.items()),
        "deterministic_environment_exact": environment == EXPECTED_ENVIRONMENT,
        "timestamps_valid": (
            started is not None
            and completed is not None
            and completed >= started
            and signed is not None
            and signed >= completed
            and generated is not None
            and generated >= signed
        ),
    }
    capsule_observed = capsule.get("observed", {}) if capsule.get("parsed") else {}
    result_checks = {
        "status_completed": result.get("status") in {"PASS", "FAIL", "PARTIAL"},
        "status_matches_capsule": (
            (result.get("status") == "PASS")
            == (capsule_observed.get("capsule_status") == "BOUNDED_REPRODUCIBILITY_PASS")
        ),
        "capsule_parsed": capsule.get("parsed") is True,
        "capsule_schema_exact": capsule.get("schema_exact") is True,
        "capsule_source_commit_exact": capsule.get("source_commit_exact") is True,
        "capsule_protocol_facts_reconciled": capsule.get("protocol_facts_reconciled") is True,
        "capsule_outcome_matches": all(
            result.get(key) == capsule_observed.get(key)
            for key in (
                "capsule_status",
                "suite_count",
                "suite_pass_count",
                "assertion_count",
                "assertion_pass_count",
            )
        ),
        "capsule_hash_matches_manifest": (
            bool(manifest["files"])
            and result.get("capsule_receipt_sha256")
            == manifest["files"][0].get("observed_sha256")
        ),
        "capsule_dependency_lock_exact": (
            capsule.get("dependency_lock_sha256")
            == target["dependency_lock_portable_sha256"]
        ),
        "capsule_protocol_controls_passed": capsule.get("protocol_controls_passed") is True,
        "negative_gates_preserved": capsule.get("negative_gates_preserved") is True,
        "result_claims_remain_false": result_claims_false,
        "submitted_claim_state_remains_false": receipt_claims_false,
    }
    attestation_checks = {
        "text_exact": attestation.get("text") == template["attestation"]["text"],
        "signed_by_reviewer": nonempty(reviewer_name)
        and attestation.get("signed_by") == reviewer_name,
        "evidence_url_is_https": (
            nonempty(attestation.get("evidence_url"))
            and attestation["evidence_url"].startswith("https://")
        ),
    }
    checks = {
        "schema_exact": receipt.get("schema") == template["schema"],
        "receipt_id_present": nonempty(receipt.get("receipt_id")),
        "generated_at_utc_valid": generated is not None,
        "target_exact": all(target_checks.values()),
        "reviewer_independence_documented": all(reviewer_checks.values()),
        "execution_protocol_matched": all(execution_checks.values()),
        "manifest_artifacts_matched": manifest["all_files_matched"],
        "capsule_result_consistent": all(result_checks.values()),
        "attestation_complete": all(attestation_checks.values()),
        "claim_boundary_exact": receipt.get("claim_boundary") == template["claim_boundary"],
    }
    independent_documented = all(checks.values())
    bounded_pass = (
        independent_documented
        and result.get("status") == "PASS"
        and result.get("capsule_status") == "BOUNDED_REPRODUCIBILITY_PASS"
        and result.get("suite_count") == 3
        and result.get("suite_pass_count") == 3
        and result.get("assertion_count") == 31
        and result.get("assertion_pass_count") == 31
    )
    status = "INVALID_OR_INCOMPLETE_RECEIPT"
    if independent_documented:
        status = (
            "DOCUMENTED_INDEPENDENT_REPRODUCTION_PASS"
            if bounded_pass
            else "DOCUMENTED_INDEPENDENT_EXECUTION_NONPASS"
        )
    return {
        "schema": "lumencore.codecheck_independent_execution_verification.v1",
        "status": status,
        "passed": independent_documented,
        "receipt_sha256": file_sha256(receipt_path),
        "checks": checks,
        "target_checks": target_checks,
        "reviewer_checks": reviewer_checks,
        "execution_checks": execution_checks,
        "result_checks": result_checks,
        "attestation_checks": attestation_checks,
        "manifest": manifest,
        "capsule": capsule,
        "computed_claim_state": {
            "independent_execution_documented": independent_documented,
            "bounded_reproduction_passed": bounded_pass,
            "reviewer_identity_reference_present": reviewer_checks["identity_reference_is_https"],
            "codecheck_certificate_issued": False,
            "external_validation_complete": False,
            "scientific_validation_complete": False,
            "field_validation_complete": False,
            "economic_validation_complete": False,
            "valuation_validation_complete": False,
        },
        "claim_boundary": template["claim_boundary"],
    }


def inspect_receipt(
    receipt_path: Path,
    artifact_root: Path,
    template_path: Path = DEFAULT_TEMPLATE,
) -> dict[str, Any]:
    try:
        return _inspect_receipt(receipt_path, artifact_root, template_path)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, UnicodeError, RecursionError, OverflowError) as exc:
        return {
            "schema": "lumencore.codecheck_independent_execution_verification.v1",
            "status": "INVALID_OR_INCOMPLETE_RECEIPT",
            "passed": False,
            "error": {"type": type(exc).__name__, "message": str(exc)},
            "computed_claim_state": {
                "independent_execution_documented": False,
                "bounded_reproduction_passed": False,
                "external_validation_complete": False,
                "field_validation_complete": False,
                "economic_validation_complete": False,
                "valuation_validation_complete": False,
            },
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify a third-party execution receipt and its six CODECHECK artifacts."
    )
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--json-out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = inspect_receipt(args.receipt, args.artifact_root, args.template)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
