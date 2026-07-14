#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RECEIPT = (
    ROOT / "config" / "external_evaluator_acceptance_template_v1.json"
)
DEFAULT_DOCKET = (
    ROOT
    / "evidence"
    / "external_validation"
    / "eia_router_validation_authority_docket_20260714.json"
)

EXPECTED_SCHEMA = "external_evaluator_acceptance_receipt.v1"
EXPECTED_PROTOCOL_ID = "LUMENCORE_EIA_EXTERNAL_VALIDATION_AUTHORITY_20260714"
EXPECTED_LANE_ID = "eia_grid_prospective_hybrid_router"
ALLOWED_DECISIONS = {"ACCEPT", "DECLINE"}
ALLOWED_SIGNATURE_METHODS = {
    "third_party_esign",
    "signed_pdf",
    "signed_email",
    "other_evaluator_controlled",
}
EVALUATOR_FIELDS = (
    "name",
    "organization",
    "technical_role",
    "authority_to_review",
    "contact_channel",
    "conflict_of_interest_disclosure",
    "authority_evidence_sha256",
)
ACCEPTANCE_FIELDS = (
    "accepted_utc",
    "decision",
    "evaluation_scope",
)
REQUIRED_TRUE_ATTESTATIONS = (
    "will_rehash_portable_inputs",
    "will_review_negative_results",
    "will_reject_backfill_or_post_target_changes",
    "will_sign_only_supported_maturity_level",
)
SIGNATURE_FIELDS = (
    "method",
    "signed_payload_sha256",
    "detached_signature_artifact_sha256",
)


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
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(character in "0123456789abcdef" for character in value)


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
    signature = payload.get("signature")
    if not isinstance(signature, dict):
        signature = {}
        payload["signature"] = signature
    signature["signed_payload_sha256"] = None
    signature["detached_signature_artifact_sha256"] = None
    return payload


def signing_payload_sha256(receipt: dict[str, Any]) -> str:
    return canonical_sha256(signing_payload(receipt))


def template_checks(
    receipt: dict[str, Any], docket: dict[str, Any]
) -> dict[str, bool]:
    evaluator = receipt.get("evaluator") or {}
    acceptance = receipt.get("acceptance") or {}
    signature = receipt.get("signature") or {}
    return {
        "schema_matched": receipt.get("schema") == EXPECTED_SCHEMA,
        "protocol_id_matched": receipt.get("protocol_id")
        == docket.get("protocol_id")
        == EXPECTED_PROTOCOL_ID,
        "lane_id_matched": receipt.get("evidence_lane_id")
        == docket.get("evidence_lane", {}).get("lane_id")
        == EXPECTED_LANE_ID,
        "accepted_protocol_hash_blank": receipt.get("accepted_protocol_sha256")
        is None,
        "accepted_docket_hash_blank": receipt.get("accepted_docket_sha256") is None,
        "evaluator_fields_blank": all(
            evaluator.get(field) is None for field in EVALUATOR_FIELDS
        ),
        "acceptance_fields_blank": all(
            acceptance.get(field) is None for field in ACCEPTANCE_FIELDS
        ),
        "attestations_blank": all(
            acceptance.get(field) is None for field in REQUIRED_TRUE_ATTESTATIONS
        )
        and acceptance.get("operator_filled_evaluator_fields") is None,
        "signature_fields_blank": all(
            signature.get(field) is None for field in SIGNATURE_FIELDS
        ),
        "operator_substitution_prohibited": receipt.get(
            "operator_may_fill_evaluator_fields"
        )
        is False,
        "level_5_auto_promotion_prohibited": receipt.get(
            "level_5_auto_promotion_allowed"
        )
        is False,
        "claim_boundary_present": is_nonempty_text(receipt.get("claim_boundary"))
        and "does not prove evaluator identity" in receipt["claim_boundary"]
        and "does not authorize Level 5" in receipt["claim_boundary"],
    }


def completed_checks(
    receipt: dict[str, Any],
    docket: dict[str, Any],
    *,
    signature_artifact: Path | None,
    authority_artifact: Path | None,
) -> dict[str, bool]:
    evaluator = receipt.get("evaluator") or {}
    acceptance = receipt.get("acceptance") or {}
    signature = receipt.get("signature") or {}
    signature_exists = bool(signature_artifact and signature_artifact.is_file())
    authority_exists = bool(authority_artifact and authority_artifact.is_file())
    signature_hash = file_sha256(signature_artifact) if signature_exists else None
    authority_hash = file_sha256(authority_artifact) if authority_exists else None
    decision = acceptance.get("decision")
    return {
        "schema_matched": receipt.get("schema") == EXPECTED_SCHEMA,
        "protocol_id_matched": receipt.get("protocol_id")
        == docket.get("protocol_id")
        == EXPECTED_PROTOCOL_ID,
        "lane_id_matched": receipt.get("evidence_lane_id")
        == docket.get("evidence_lane", {}).get("lane_id")
        == EXPECTED_LANE_ID,
        "accepted_protocol_hash_matched": receipt.get(
            "accepted_protocol_sha256"
        )
        == docket.get("evidence_lane", {}).get("protocol_sha256"),
        "accepted_docket_hash_matched": receipt.get("accepted_docket_sha256")
        == docket.get("docket_sha256"),
        "evaluator_fields_complete": all(
            is_nonempty_text(evaluator.get(field))
            for field in EVALUATOR_FIELDS
            if field != "authority_evidence_sha256"
        ),
        "authority_evidence_hash_valid": is_sha256(
            evaluator.get("authority_evidence_sha256")
        ),
        "authority_artifact_present": authority_exists,
        "authority_artifact_hash_matched": bool(
            authority_hash
            and authority_hash == evaluator.get("authority_evidence_sha256")
        ),
        "decision_valid": decision in ALLOWED_DECISIONS,
        "accepted_utc_valid": is_timezone_aware_iso8601(
            acceptance.get("accepted_utc")
        ),
        "evaluation_scope_present": is_nonempty_text(
            acceptance.get("evaluation_scope")
        ),
        "operator_did_not_fill_evaluator_fields": acceptance.get(
            "operator_filled_evaluator_fields"
        )
        is False,
        "required_attestations_accepted": all(
            acceptance.get(field) is True for field in REQUIRED_TRUE_ATTESTATIONS
        ),
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
            "operator_may_fill_evaluator_fields"
        )
        is False,
        "level_5_auto_promotion_prohibited": receipt.get(
            "level_5_auto_promotion_allowed"
        )
        is False,
    }


def validate_receipt(
    receipt: dict[str, Any],
    docket: dict[str, Any],
    *,
    expect_template: bool,
    signature_artifact: Path | None = None,
    authority_artifact: Path | None = None,
) -> dict[str, Any]:
    if expect_template:
        checks = template_checks(receipt, docket)
        passed = all(checks.values())
        status = (
            "UNSIGNED_EVALUATOR_TEMPLATE_VALID"
            if passed
            else "EVALUATOR_TEMPLATE_FAIL_CLOSED"
        )
        decision = None
    else:
        checks = completed_checks(
            receipt,
            docket,
            signature_artifact=signature_artifact,
            authority_artifact=authority_artifact,
        )
        passed = all(checks.values())
        decision = (receipt.get("acceptance") or {}).get("decision")
        if not passed:
            status = "EVALUATOR_ACCEPTANCE_FAIL_CLOSED"
        elif decision == "DECLINE":
            status = "EVALUATOR_ROLE_DECLINED_INTEGRITY_VERIFIED"
        else:
            status = "EVALUATOR_ACCEPTANCE_INTEGRITY_READY_IDENTITY_CHECK_REQUIRED"

    failed = [name for name, value in checks.items() if not value]
    return {
        "schema": "external_evaluator_acceptance_validation.v1",
        "status": status,
        "validation_passed": passed,
        "expect_template": expect_template,
        "decision": decision,
        "check_count": len(checks),
        "check_pass_count": sum(1 for value in checks.values() if value),
        "failed_checks": failed,
        "checks": checks,
        "receipt_sha256": canonical_sha256(receipt),
        "signed_payload_sha256": signing_payload_sha256(receipt),
        "external_identity_verified": False,
        "evaluator_independence_verified": False,
        "result_signoff_complete": False,
        "level_5_promotion_allowed": False,
        "claim_boundary": (
            "This validator checks schema, frozen protocol and docket identities, "
            "attestations, and supplied artifact hashes. It does not authenticate "
            "the evaluator, establish legal authority or independence, verify the "
            "semantics of a signature artifact, complete result signoff, or authorize "
            "Level 5 promotion."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed validator for an evaluator-owned acceptance receipt."
    )
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--docket", type=Path, default=DEFAULT_DOCKET)
    parser.add_argument("--expect-template", action="store_true")
    parser.add_argument("--signature-artifact", type=Path)
    parser.add_argument("--authority-artifact", type=Path)
    args = parser.parse_args()

    receipt = read_json(args.receipt.resolve())
    docket = read_json(args.docket.resolve())
    report = validate_receipt(
        receipt,
        docket,
        expect_template=args.expect_template,
        signature_artifact=(
            args.signature_artifact.resolve() if args.signature_artifact else None
        ),
        authority_artifact=(
            args.authority_artifact.resolve() if args.authority_artifact else None
        ),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["validation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
