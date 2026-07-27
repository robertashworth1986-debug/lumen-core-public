from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "VERIFY_CODECHECK_INDEPENDENT_EXECUTION_RECEIPT.py"
TEMPLATE = ROOT / "config" / "codecheck_independent_execution_receipt_template_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("codecheck_independent_receipt", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_complete_receipt(tmp_path: Path) -> tuple[Path, Path]:
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    receipt = copy.deepcopy(template)
    artifact_root = tmp_path / "artifacts"
    assertions = [{"assertion_id": f"a{index}", "passed": True} for index in range(31)]
    capsule = {
        "schema": "reviewer_reproducibility_capsule.v1",
        "status": "BOUNDED_REPRODUCIBILITY_PASS",
        "git": {"commit": template["review_target"]["source_commit"]},
        "summary": {
            "dependency_lock_sha256": template["review_target"][
                "dependency_lock_portable_sha256"
            ],
            "authoritative_runtime_match": True,
            "dependency_closure_exact_match": True,
            "deterministic_environment_match": True,
            "fixture_tests_executed": True,
            "fixture_tests_passed": True,
            "relevant_source_clean": True,
            "source_state_verified": True,
            "external_validation_complete": False,
            "agency_certification_complete": False,
        },
        "suites": [
            {"passed": True, "assertions": assertions[:9]},
            {"passed": True, "assertions": assertions[9:19]},
            {"passed": True, "assertions": assertions[19:]},
        ],
    }
    for row in receipt["manifest"]:
        target = artifact_root / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if row["path"].endswith("reviewer_reproducibility_receipt.json"):
            write_json(target, capsule)
        elif row["path"].endswith(".json"):
            write_json(target, {"bomFormat": "CycloneDX"})
        else:
            target.write_text(f"bounded log for {row['path']}\n", encoding="utf-8")
        row["sha256"] = sha256(target)
        row["bytes"] = target.stat().st_size

    receipt["receipt_id"] = "independent-example-001"
    receipt["generated_at_utc"] = "2026-07-22T03:00:00Z"
    receipt["reviewer"].update(
        {
            "full_name": "Example Reviewer",
            "affiliation_or_independent_status": "Independent computational reviewer",
            "identity_reference": "https://example.org/reviewer",
            "relationship_to_author": "No prior relationship",
            "conflict_disclosure": "No financial or professional conflict identified",
            "is_author": False,
            "employed_or_contracted_by_lumencore": False,
            "paid_for_favorable_result": False,
            "reviewer_controlled_environment": True,
        }
    )
    receipt["execution"].update(
        {
            "started_at_utc": "2026-07-22T01:00:00Z",
            "completed_at_utc": "2026-07-22T02:00:00Z",
            "source_tree_clean": True,
            "network_access_during_execution": False,
            "runtime": {
                "system": "Linux",
                "machine": "x86_64",
                "python": "3.11.9",
                "glibc": "2.39",
                "timezone": "UTC",
                "deterministic_environment": {
                    "MKL_NUM_THREADS": "1",
                    "OMP_NUM_THREADS": "4",
                    "OPENBLAS_NUM_THREADS": "1",
                    "PYTHONHASHSEED": "0",
                    "TZ": "UTC",
                },
            },
        }
    )
    capsule_path = artifact_root / receipt["manifest"][0]["path"]
    receipt["result"].update(
        {
            "status": "PASS",
            "capsule_status": "BOUNDED_REPRODUCIBILITY_PASS",
            "suite_count": 3,
            "suite_pass_count": 3,
            "assertion_count": 31,
            "assertion_pass_count": 31,
            "capsule_receipt_sha256": sha256(capsule_path),
        }
    )
    receipt["attestation"].update(
        {
            "signed_by": "Example Reviewer",
            "signed_at_utc": "2026-07-22T02:30:00Z",
            "evidence_url": "https://example.org/reviewer/evidence/001",
        }
    )
    receipt_path = tmp_path / "independent_receipt.json"
    write_json(receipt_path, receipt)
    return receipt_path, artifact_root


def test_complete_independent_receipt_documents_bounded_reproduction(tmp_path):
    module = load_module()
    receipt_path, artifact_root = build_complete_receipt(tmp_path)

    report = module.inspect_receipt(receipt_path, artifact_root)

    assert report["passed"] is True
    assert report["status"] == "DOCUMENTED_INDEPENDENT_REPRODUCTION_PASS"
    assert all(report["checks"].values())
    assert report["manifest"]["all_files_matched"] is True
    assert report["computed_claim_state"]["independent_execution_documented"] is True
    assert report["computed_claim_state"]["bounded_reproduction_passed"] is True
    assert report["computed_claim_state"]["external_validation_complete"] is False
    assert report["computed_claim_state"]["valuation_validation_complete"] is False


def test_artifact_tampering_fails_closed(tmp_path):
    module = load_module()
    receipt_path, artifact_root = build_complete_receipt(tmp_path)
    target = artifact_root / "out" / "codecheck_eia" / "logs" / "eia_wave.log"
    target.write_text("tampered\n", encoding="utf-8")

    report = module.inspect_receipt(receipt_path, artifact_root)

    assert report["passed"] is False
    assert report["checks"]["manifest_artifacts_matched"] is False
    assert report["computed_claim_state"]["independent_execution_documented"] is False


def test_author_operated_or_self_promoted_receipt_is_rejected(tmp_path):
    module = load_module()
    receipt_path, artifact_root = build_complete_receipt(tmp_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["reviewer"]["full_name"] = "Robert Ashworth"
    receipt["reviewer"]["is_author"] = True
    receipt["claim_state"]["external_validation_complete"] = True
    write_json(receipt_path, receipt)

    report = module.inspect_receipt(receipt_path, artifact_root)

    assert report["passed"] is False
    assert report["checks"]["reviewer_independence_documented"] is False
    assert report["result_checks"]["submitted_claim_state_remains_false"] is False


def test_omitted_claim_gate_and_backdated_receipt_are_rejected(tmp_path):
    module = load_module()
    receipt_path, artifact_root = build_complete_receipt(tmp_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    del receipt["claim_state"]["valuation_validation_complete"]
    receipt["generated_at_utc"] = "2026-07-22T01:30:00Z"
    write_json(receipt_path, receipt)

    report = module.inspect_receipt(receipt_path, artifact_root)

    assert report["passed"] is False
    assert report["execution_checks"]["timestamps_valid"] is False
    assert report["result_checks"]["submitted_claim_state_remains_false"] is False


def test_declared_failure_cannot_wrap_a_passing_capsule(tmp_path):
    module = load_module()
    receipt_path, artifact_root = build_complete_receipt(tmp_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["result"]["status"] = "FAIL"
    write_json(receipt_path, receipt)

    report = module.inspect_receipt(receipt_path, artifact_root)

    assert report["passed"] is False
    assert report["result_checks"]["status_matches_capsule"] is False


def test_blank_template_and_unsafe_manifest_path_are_rejected(tmp_path):
    module = load_module()
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    receipt_path = tmp_path / "blank.json"
    write_json(receipt_path, template)

    blank_report = module.inspect_receipt(receipt_path, tmp_path)
    assert blank_report["passed"] is False

    complete_path, artifact_root = build_complete_receipt(tmp_path / "complete")
    receipt = json.loads(complete_path.read_text(encoding="utf-8"))
    receipt["manifest"][0]["path"] = "../private.json"
    write_json(complete_path, receipt)
    unsafe_report = module.inspect_receipt(complete_path, artifact_root)
    assert unsafe_report["passed"] is False
    assert unsafe_report["manifest"]["all_files_matched"] is False
