from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATE = ROOT / "config" / "codecheck_independent_execution_receipt_template_v1.json"
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


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object at {path}")
    return payload


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and ":" not in value


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
    for row in rows:
        if not isinstance(row, dict):
            observations.append({"safe": False, "matched": False})
            continue
        relative = row.get("path")
        safe = safe_relative_path(relative)
        target = (root / PurePosixPath(relative)).resolve() if safe else root / "__unsafe__"
        contained = safe and target.is_relative_to(root)
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
                    and isinstance(row.get("bytes"), int)
                    and row["bytes"] >= 0
                    and observed_bytes == row["bytes"]
                ),
            }
        )
    observed_paths = [row.get("path") for row in rows if isinstance(row, dict)]
    return {
        "expected_paths": expected_paths,
        "observed_paths": observed_paths,
        "path_order_exact": observed_paths == expected_paths,
        "duplicate_path_count": len(observed_paths) - len(set(observed_paths)),
        "files": observations,
        "all_files_matched": (
            observed_paths == expected_paths
            and len(observations) == len(expected_paths)
            and all(row.get("matched") is True for row in observations)
        ),
    }


def inspect_capsule_receipt(path: Path, expected_commit: str) -> dict[str, Any]:
    try:
        payload = read_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"parsed": False, "error": str(exc)}
    suites = payload.get("suites") if isinstance(payload.get("suites"), list) else []
    assertions = [
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
        "suite_pass_count": sum(suite.get("passed") is True for suite in suites),
        "assertion_count": len(assertions),
        "assertion_pass_count": sum(row.get("passed") is True for row in assertions),
    }
    return {
        "parsed": True,
        "schema_exact": payload.get("schema") == "reviewer_reproducibility_capsule.v1",
        "source_commit_exact": nested_get(payload, "git", "commit") == expected_commit,
        "observed": observed,
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
        ),
    }


def inspect_receipt(
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
