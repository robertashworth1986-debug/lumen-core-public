from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "VERIFY_EXTERNAL_EVALUATOR_ACCEPTANCE.py"
TEMPLATE = ROOT / "config" / "external_evaluator_acceptance_template_v1.json"
DOCKET = (
    ROOT
    / "evidence"
    / "external_validation"
    / "eia_router_validation_authority_docket_20260714.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "external_evaluator_acceptance", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_inputs():
    return (
        json.loads(TEMPLATE.read_text(encoding="utf-8")),
        json.loads(DOCKET.read_text(encoding="utf-8")),
    )


def completed_receipt(module, tmp_path):
    receipt, docket = load_inputs()
    authority = tmp_path / "authority.txt"
    signature = tmp_path / "signature.txt"
    authority.write_text("evaluator-controlled authority evidence\n", encoding="utf-8")
    signature.write_text("evaluator-controlled signed acceptance\n", encoding="utf-8")

    receipt["accepted_protocol_sha256"] = docket["evidence_lane"][
        "protocol_sha256"
    ]
    receipt["accepted_docket_sha256"] = docket["docket_sha256"]
    receipt["evaluator"].update(
        {
            "name": "Example Independent Evaluator",
            "organization": "Example Evaluation Organization",
            "technical_role": "Forecast evaluation lead",
            "authority_to_review": "Authorized to accept and supervise this evaluation",
            "contact_channel": "Evaluator-controlled private channel",
            "conflict_of_interest_disclosure": "No financial interest disclosed",
            "authority_evidence_sha256": module.file_sha256(authority),
        }
    )
    receipt["acceptance"].update(
        {
            "accepted_utc": "2026-07-14T20:00:00Z",
            "decision": "ACCEPT",
            "evaluation_scope": "Frozen EIA prospective-router protocol only",
            "operator_filled_evaluator_fields": False,
            "will_rehash_portable_inputs": True,
            "will_review_negative_results": True,
            "will_reject_backfill_or_post_target_changes": True,
            "will_sign_only_supported_maturity_level": True,
        }
    )
    receipt["signature"]["method"] = "signed_pdf"
    receipt["signature"]["signed_payload_sha256"] = (
        module.signing_payload_sha256(receipt)
    )
    receipt["signature"]["detached_signature_artifact_sha256"] = (
        module.file_sha256(signature)
    )
    return receipt, docket, authority, signature


def test_unsigned_template_is_valid_and_operator_cannot_fill_evaluator_fields():
    module = load_module()
    receipt, docket = load_inputs()

    report = module.validate_receipt(receipt, docket, expect_template=True)

    assert report["status"] == "UNSIGNED_EVALUATOR_TEMPLATE_VALID"
    assert report["validation_passed"] is True
    assert receipt["operator_may_fill_evaluator_fields"] is False
    assert receipt["level_5_auto_promotion_allowed"] is False
    assert all(value is None for value in receipt["evaluator"].values())
    assert all(value is None for value in receipt["acceptance"].values())
    assert all(value is None for value in receipt["signature"].values())


def test_operator_populated_template_fails_closed():
    module = load_module()
    receipt, docket = load_inputs()
    receipt["evaluator"]["name"] = "Operator supplied a name"

    report = module.validate_receipt(receipt, docket, expect_template=True)

    assert report["status"] == "EVALUATOR_TEMPLATE_FAIL_CLOSED"
    assert report["validation_passed"] is False
    assert "evaluator_fields_blank" in report["failed_checks"]


def test_completed_receipt_requires_both_external_artifacts(tmp_path):
    module = load_module()
    receipt, docket, authority, signature = completed_receipt(module, tmp_path)

    report = module.validate_receipt(receipt, docket, expect_template=False)

    assert report["status"] == "EVALUATOR_ACCEPTANCE_FAIL_CLOSED"
    assert report["validation_passed"] is False
    assert "authority_artifact_present" in report["failed_checks"]
    assert "signature_artifact_present" in report["failed_checks"]
    assert authority.is_file()
    assert signature.is_file()


def test_completed_receipt_verifies_integrity_but_not_identity_or_level_5(tmp_path):
    module = load_module()
    receipt, docket, authority, signature = completed_receipt(module, tmp_path)

    report = module.validate_receipt(
        receipt,
        docket,
        expect_template=False,
        authority_artifact=authority,
        signature_artifact=signature,
    )

    assert report["status"] == (
        "EVALUATOR_ACCEPTANCE_INTEGRITY_READY_IDENTITY_CHECK_REQUIRED"
    )
    assert report["validation_passed"] is True
    assert report["external_identity_verified"] is False
    assert report["evaluator_independence_verified"] is False
    assert report["result_signoff_complete"] is False
    assert report["level_5_promotion_allowed"] is False


def test_hash_or_attestation_tamper_fails_closed(tmp_path):
    module = load_module()
    receipt, docket, authority, signature = completed_receipt(module, tmp_path)
    receipt["acceptance"]["will_review_negative_results"] = False

    report = module.validate_receipt(
        receipt,
        docket,
        expect_template=False,
        authority_artifact=authority,
        signature_artifact=signature,
    )

    assert report["validation_passed"] is False
    assert "required_attestations_accepted" in report["failed_checks"]
    assert "signed_payload_hash_matched" in report["failed_checks"]


def test_docket_or_protocol_hash_tamper_fails_closed(tmp_path):
    module = load_module()
    receipt, docket, authority, signature = completed_receipt(module, tmp_path)
    receipt["accepted_docket_sha256"] = "0" * 64
    receipt["signature"]["signed_payload_sha256"] = (
        module.signing_payload_sha256(receipt)
    )

    report = module.validate_receipt(
        receipt,
        docket,
        expect_template=False,
        authority_artifact=authority,
        signature_artifact=signature,
    )

    assert report["validation_passed"] is False
    assert "accepted_docket_hash_matched" in report["failed_checks"]
