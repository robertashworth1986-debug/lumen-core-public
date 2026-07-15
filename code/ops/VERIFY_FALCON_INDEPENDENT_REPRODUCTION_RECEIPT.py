#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RECEIPT = (
    ROOT / "config" / "falcon_independent_reproduction_receipt_template_v1.json"
)

EXPECTED_SCHEMA = "falcon_independent_reproduction_receipt.v1"
EXPECTED_LANE_ID = "falcon_permutation_calibrated_router_v3"
EXPECTED_FROZEN_EVIDENCE = {
    "protocol_sha256": "6384d5f9755e70e868052b0887c4a8d981068de85fbd89c968c874c1808521d9",
    "runner_sha256": "aa4c37b20b5d732ede34ec25f33897b5dc059756455dc1176b3480ba5e74daa9",
    "source_manifest_sha256": "2b6ad75db13396a26ab2600da73e764b33400f815945e3e9f057cf699bfb5bcb",
    "trace_terminal_sha256": "a2b51eb22f287f939909028f06218e0f7077e65b414ac9b8af858b21a83015ec",
    "model_id": "Qwen/Qwen2.5-1.5B-Instruct",
    "model_revision": "989aa7980e4cf806f80c7fef2b1adb7bc71aa306",
    "model_weights_sha256": "dd924a11b4c220f385b51ffa522daea7c9f3d850e31b162bb5661df483c6d3ee",
    "public_feed_file_sha256": "8527167a01635085fd67e6a093007679d0dac78b00e4979ef5169332417ce8a8",
    "custody_packet_manifest_sha256": "b10f3ff0586e01fa859d5bf49f6466f39033c4022d3e1a1a99a4f1bbcca66598",
}
EXPECTED_RESULT = {
    "status": "FROZEN_NULL_RESULT_PRESERVED",
    "qualification_gate_passed": False,
    "correct_decisions": 27,
    "decision_count": 30,
    "overall_accuracy": 0.9,
    "unsupported_output_rate": 0.0,
    "mean_permutation_agreement": 0.822222,
    "minimum_permutation_agreement": 0.333333,
    "failed_checks": [
        "mean_permutation_agreement",
        "minimum_permutation_agreement",
        "per_context_accuracy",
    ],
}
REVIEWER_FIELDS = (
    "name",
    "organization",
    "technical_role",
    "contact_channel",
    "conflict_of_interest_disclosure",
    "independence_basis",
    "independence_evidence_sha256",
)
REPRODUCTION_FIELDS = (
    "executed_utc",
    "decision",
    "environment_summary",
    "source_packet_rehashed",
    "source_hashes_match",
    "trace_chain_verified",
    "model_weights_verified",
    "result_recomputed_from_traces",
    "correct_decisions",
    "decision_count",
    "overall_accuracy",
    "unsupported_output_rate",
    "mean_permutation_agreement",
    "minimum_permutation_agreement",
    "failed_checks",
    "notes",
    "operator_filled_reviewer_fields",
)
SIGNATURE_FIELDS = (
    "method",
    "signed_payload_sha256",
    "detached_signature_artifact_sha256",
)
ALLOWED_DECISIONS = {
    "REPRODUCED_FROZEN_NULL_RESULT",
    "DID_NOT_REPRODUCE",
}
ALLOWED_SIGNATURE_METHODS = {
    "third_party_esign",
    "signed_pdf",
    "signed_email",
    "other_reviewer_controlled",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object at {path}")
    return value


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def is_nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_timezone_aware_iso8601(value: Any) -> bool:
    if not is_nonempty_text(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def signing_payload(receipt: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(receipt)
    signature = payload.setdefault("signature", {})
    signature["signed_payload_sha256"] = None
    signature["detached_signature_artifact_sha256"] = None
    return payload


def signing_payload_sha256(receipt: dict[str, Any]) -> str:
    return canonical_sha256(signing_payload(receipt))


def frozen_evidence_matches(receipt: dict[str, Any]) -> bool:
    frozen = receipt.get("frozen_evidence")
    if not isinstance(frozen, dict):
        return False
    expected_result = frozen.get("expected_result")
    return all(
        frozen.get(key) == value for key, value in EXPECTED_FROZEN_EVIDENCE.items()
    ) and expected_result == EXPECTED_RESULT


def template_checks(receipt: dict[str, Any]) -> dict[str, bool]:
    reviewer = receipt.get("reviewer") or {}
    reproduction = receipt.get("reproduction") or {}
    signature = receipt.get("signature") or {}
    return {
        "schema_matched": receipt.get("schema") == EXPECTED_SCHEMA,
        "lane_id_matched": receipt.get("evidence_lane_id") == EXPECTED_LANE_ID,
        "frozen_evidence_matched": frozen_evidence_matches(receipt),
        "reviewer_fields_blank": all(
            reviewer.get(field) is None for field in REVIEWER_FIELDS
        ),
        "reproduction_fields_blank": all(
            reproduction.get(field) is None for field in REPRODUCTION_FIELDS
        ),
        "signature_fields_blank": all(
            signature.get(field) is None for field in SIGNATURE_FIELDS
        ),
        "operator_substitution_prohibited": receipt.get(
            "operator_may_fill_reviewer_fields"
        )
        is False,
        "performance_promotion_prohibited": receipt.get(
            "performance_promotion_allowed"
        )
        is False,
        "claim_boundary_present": is_nonempty_text(receipt.get("claim_boundary"))
        and "does not convert the failed qualification" in receipt["claim_boundary"],
    }


def result_matches_expected(reproduction: dict[str, Any]) -> bool:
    exact_fields = (
        "correct_decisions",
        "decision_count",
        "failed_checks",
    )
    float_fields = (
        "overall_accuracy",
        "unsupported_output_rate",
        "mean_permutation_agreement",
        "minimum_permutation_agreement",
    )
    return all(
        reproduction.get(field) == EXPECTED_RESULT[field] for field in exact_fields
    ) and all(
        isinstance(reproduction.get(field), (int, float))
        and math.isclose(
            float(reproduction[field]),
            float(EXPECTED_RESULT[field]),
            rel_tol=0.0,
            abs_tol=1e-6,
        )
        for field in float_fields
    )


def completed_checks(
    receipt: dict[str, Any],
    *,
    signature_artifact: Path | None,
    independence_artifact: Path | None,
) -> dict[str, bool]:
    reviewer = receipt.get("reviewer") or {}
    reproduction = receipt.get("reproduction") or {}
    signature = receipt.get("signature") or {}
    decision = reproduction.get("decision")
    signature_exists = bool(signature_artifact and signature_artifact.is_file())
    independence_exists = bool(
        independence_artifact and independence_artifact.is_file()
    )
    signature_hash = file_sha256(signature_artifact) if signature_exists else None
    independence_hash = (
        file_sha256(independence_artifact) if independence_exists else None
    )
    reproduced = decision == "REPRODUCED_FROZEN_NULL_RESULT"
    mismatch_documented = decision == "DID_NOT_REPRODUCE" and is_nonempty_text(
        reproduction.get("notes")
    )
    technical_outcome_valid = (
        all(
            reproduction.get(field) is True
            for field in (
                "source_packet_rehashed",
                "source_hashes_match",
                "trace_chain_verified",
                "model_weights_verified",
                "result_recomputed_from_traces",
            )
        )
        and result_matches_expected(reproduction)
        if reproduced
        else mismatch_documented
    )
    return {
        "schema_matched": receipt.get("schema") == EXPECTED_SCHEMA,
        "lane_id_matched": receipt.get("evidence_lane_id") == EXPECTED_LANE_ID,
        "frozen_evidence_matched": frozen_evidence_matches(receipt),
        "reviewer_fields_complete": all(
            is_nonempty_text(reviewer.get(field))
            for field in REVIEWER_FIELDS
            if field != "independence_evidence_sha256"
        ),
        "independence_hash_valid": is_sha256(
            reviewer.get("independence_evidence_sha256")
        ),
        "independence_artifact_present": independence_exists,
        "independence_artifact_hash_matched": bool(
            independence_hash
            and independence_hash == reviewer.get("independence_evidence_sha256")
        ),
        "decision_valid": decision in ALLOWED_DECISIONS,
        "executed_utc_valid": is_timezone_aware_iso8601(
            reproduction.get("executed_utc")
        ),
        "environment_summary_present": is_nonempty_text(
            reproduction.get("environment_summary")
        ),
        "operator_did_not_fill_reviewer_fields": reproduction.get(
            "operator_filled_reviewer_fields"
        )
        is False,
        "technical_outcome_valid": technical_outcome_valid,
        "signature_method_allowed": signature.get("method")
        in ALLOWED_SIGNATURE_METHODS,
        "signed_payload_hash_valid": is_sha256(
            signature.get("signed_payload_sha256")
        ),
        "signed_payload_hash_matched": signature.get("signed_payload_sha256")
        == signing_payload_sha256(receipt),
        "signature_artifact_hash_valid": is_sha256(
            signature.get("detached_signature_artifact_sha256")
        ),
        "signature_artifact_present": signature_exists,
        "signature_artifact_hash_matched": bool(
            signature_hash
            and signature_hash
            == signature.get("detached_signature_artifact_sha256")
        ),
        "operator_substitution_prohibited": receipt.get(
            "operator_may_fill_reviewer_fields"
        )
        is False,
        "performance_promotion_prohibited": receipt.get(
            "performance_promotion_allowed"
        )
        is False,
    }


def validate_receipt(
    receipt: dict[str, Any],
    *,
    expect_template: bool,
    signature_artifact: Path | None = None,
    independence_artifact: Path | None = None,
) -> dict[str, Any]:
    if expect_template:
        checks = template_checks(receipt)
        decision = None
        reproduced = False
        status = (
            "UNSIGNED_INDEPENDENT_REPRODUCTION_TEMPLATE_VALID"
            if all(checks.values())
            else "INDEPENDENT_REPRODUCTION_TEMPLATE_FAIL_CLOSED"
        )
    else:
        checks = completed_checks(
            receipt,
            signature_artifact=signature_artifact,
            independence_artifact=independence_artifact,
        )
        decision = (receipt.get("reproduction") or {}).get("decision")
        reproduced = decision == "REPRODUCED_FROZEN_NULL_RESULT" and all(
            checks.values()
        )
        if not all(checks.values()):
            status = "INDEPENDENT_REPRODUCTION_RECEIPT_FAIL_CLOSED"
        elif reproduced:
            status = "FROZEN_NULL_RESULT_INDEPENDENTLY_REPRODUCED"
        else:
            status = "INDEPENDENT_REPRODUCTION_DISAGREEMENT_RECORDED"

    passed = all(checks.values())
    return {
        "schema": "falcon_independent_reproduction_validation.v1",
        "status": status,
        "receipt_integrity_passed": passed,
        "frozen_null_result_independently_reproduced": reproduced,
        "decision": decision,
        "check_count": len(checks),
        "check_pass_count": sum(1 for value in checks.values() if value),
        "failed_checks": [name for name, value in checks.items() if not value],
        "checks": checks,
        "receipt_sha256": canonical_sha256(receipt),
        "signing_payload_sha256": signing_payload_sha256(receipt),
        "external_identity_verified_by_software": False,
        "reviewer_independence_verified_by_software": False,
        "performance_promotion_allowed": False,
        "claim_boundary": (
            "This validator checks the frozen evidence identity, reviewer-supplied "
            "fields, reproduced values, and supplied artifact hashes. It does not "
            "authenticate the reviewer, prove legal authority or independence, "
            "interpret signature semantics, convert the null result into a pass, "
            "or authorize a performance or deployment claim."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed validator for a reviewer-owned FALCON reproduction receipt."
    )
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--expect-template", action="store_true")
    parser.add_argument("--signature-artifact", type=Path)
    parser.add_argument("--independence-artifact", type=Path)
    parser.add_argument("--print-signing-payload-sha256", action="store_true")
    args = parser.parse_args()

    receipt = read_json(args.receipt.resolve())
    if args.print_signing_payload_sha256:
        print(signing_payload_sha256(receipt))
        return 0
    report = validate_receipt(
        receipt,
        expect_template=args.expect_template,
        signature_artifact=(
            args.signature_artifact.resolve() if args.signature_artifact else None
        ),
        independence_artifact=(
            args.independence_artifact.resolve()
            if args.independence_artifact
            else None
        ),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["receipt_integrity_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
