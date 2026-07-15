from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT / "code" / "ops" / "VERIFY_FALCON_INDEPENDENT_REPRODUCTION_RECEIPT.py"
)
TEMPLATE_PATH = (
    ROOT / "config" / "falcon_independent_reproduction_receipt_template_v1.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "verify_falcon_independent_reproduction_receipt", MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_template() -> dict:
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def completed_receipt(module, tmp_path: Path) -> tuple[dict, Path, Path]:
    receipt = load_template()
    independence = tmp_path / "independence.txt"
    signature = tmp_path / "signature.txt"
    independence.write_text("reviewer-controlled independence evidence", encoding="utf-8")
    signature.write_text("reviewer-controlled signature artifact", encoding="utf-8")
    receipt["reviewer"] = {
        "name": "Independent Reviewer",
        "organization": "Independent Lab",
        "technical_role": "Reproduction evaluator",
        "contact_channel": "reviewer@example.invalid",
        "conflict_of_interest_disclosure": "No financial relationship disclosed.",
        "independence_basis": "No role in protocol design or source execution.",
        "independence_evidence_sha256": module.file_sha256(independence),
    }
    receipt["reproduction"] = {
        "executed_utc": "2026-07-15T20:00:00Z",
        "decision": "REPRODUCED_FROZEN_NULL_RESULT",
        "environment_summary": "Independent clean runner with pinned model revision.",
        "source_packet_rehashed": True,
        "source_hashes_match": True,
        "trace_chain_verified": True,
        "model_weights_verified": True,
        "result_recomputed_from_traces": True,
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
        "notes": "The failed qualification and all three errors were reproduced.",
        "operator_filled_reviewer_fields": False,
    }
    receipt["signature"] = {
        "method": "signed_email",
        "signed_payload_sha256": None,
        "detached_signature_artifact_sha256": module.file_sha256(signature),
    }
    receipt["signature"]["signed_payload_sha256"] = module.signing_payload_sha256(
        receipt
    )
    return receipt, signature, independence


def test_unsigned_template_is_valid_and_cannot_promote_performance():
    module = load_module()
    report = module.validate_receipt(load_template(), expect_template=True)

    assert report["receipt_integrity_passed"] is True
    assert report["status"] == "UNSIGNED_INDEPENDENT_REPRODUCTION_TEMPLATE_VALID"
    assert report["frozen_null_result_independently_reproduced"] is False
    assert report["performance_promotion_allowed"] is False


def test_completed_reproduction_receipt_binds_exact_null_result(tmp_path):
    module = load_module()
    receipt, signature, independence = completed_receipt(module, tmp_path)

    report = module.validate_receipt(
        receipt,
        expect_template=False,
        signature_artifact=signature,
        independence_artifact=independence,
    )

    assert report["receipt_integrity_passed"] is True
    assert report["status"] == "FROZEN_NULL_RESULT_INDEPENDENTLY_REPRODUCED"
    assert report["frozen_null_result_independently_reproduced"] is True
    assert report["performance_promotion_allowed"] is False


def test_metric_tamper_fails_closed(tmp_path):
    module = load_module()
    receipt, signature, independence = completed_receipt(module, tmp_path)
    receipt["reproduction"]["correct_decisions"] = 30
    receipt["signature"]["signed_payload_sha256"] = module.signing_payload_sha256(
        receipt
    )

    report = module.validate_receipt(
        receipt,
        expect_template=False,
        signature_artifact=signature,
        independence_artifact=independence,
    )

    assert report["receipt_integrity_passed"] is False
    assert "technical_outcome_valid" in report["failed_checks"]
    assert report["performance_promotion_allowed"] is False


def test_signature_artifact_tamper_fails_closed(tmp_path):
    module = load_module()
    receipt, signature, independence = completed_receipt(module, tmp_path)
    signature.write_text("changed after signing", encoding="utf-8")

    report = module.validate_receipt(
        receipt,
        expect_template=False,
        signature_artifact=signature,
        independence_artifact=independence,
    )

    assert report["receipt_integrity_passed"] is False
    assert "signature_artifact_hash_matched" in report["failed_checks"]
