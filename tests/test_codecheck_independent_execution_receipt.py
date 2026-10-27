from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "VERIFY_CODECHECK_INDEPENDENT_EXECUTION_RECEIPT.py"
TEMPLATE = ROOT / "config" / "codecheck_independent_execution_receipt_template_v1.json"
REAL_CAPSULE = ROOT / "evidence/reproducibility/codecheck_reviewer_container_1c0eb517_20260721/reviewer_reproducibility_receipt.json"


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
    # Administrative fixture only: preserve the actual frozen capsule's shape,
    # including 26 suite assertions and five separate frozen-input assertions.
    capsule = json.loads(REAL_CAPSULE.read_text(encoding="utf-8"))
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
    assert report["capsule"]["observed"]["assertion_count"] == 31
    assert report["capsule"]["protocol_facts_reconciled"] is True
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


def rewrite_capsule(receipt_path, artifact_root, mutation, *, recompute_projection_hashes=True):
    receipt = json.loads(receipt_path.read_text())
    path = artifact_root / receipt["manifest"][0]["path"]
    capsule = json.loads(path.read_text())
    mutation(capsule)
    if recompute_projection_hashes:
        for suite in capsule.get("suites", []):
            if isinstance(suite, dict) and "fact_projection" in suite:
                suite["fact_projection_sha256"] = hashlib.sha256(json.dumps(suite["fact_projection"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    capsule["capsule_sha256"] = hashlib.sha256(json.dumps({key: value for key, value in capsule.items() if key != "capsule_sha256"}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    write_json(path, capsule)
    receipt["manifest"][0].update(sha256=sha256(path), bytes=path.stat().st_size)
    receipt["result"]["capsule_receipt_sha256"] = sha256(path)
    write_json(receipt_path, receipt)


@pytest.mark.parametrize("mutation", [
    "missing_frozen_input", "missing_input_assertion", "duplicate_input_assertion",
    "wrong_input_identity", "missing_suite", "duplicate_suite", "wrong_suite_id",
    "missing_assertion", "duplicate_assertion", "wrong_assertion_id",
    "altered_expected", "false_assertion_pass", "altered_tolerance",
    "contradictory_projection", "promoted_gate", "projection_hash",
    "boolean_count", "malformed_suite", "malformed_assertion", "malformed_input",
    "malformed_projection", "string_pass", "capsule_hash", "wrong_protocol_id",
    "rewritten_negative_gate", "nonfinite_actual",
])
def test_rehashed_inconsistent_capsules_are_rejected(tmp_path, mutation):
    module = load_module()
    receipt_path, artifact_root = build_complete_receipt(tmp_path)

    def change(capsule):
        suite = capsule["suites"][0]
        if mutation == "missing_frozen_input": capsule.pop("frozen_input")
        elif mutation == "missing_input_assertion": capsule["frozen_input"]["assertions"].pop()
        elif mutation == "duplicate_input_assertion": capsule["frozen_input"]["assertions"][0] = copy.deepcopy(capsule["frozen_input"]["assertions"][1])
        elif mutation == "wrong_input_identity": capsule["frozen_input"]["input_id"] = "different-input"
        elif mutation == "missing_suite": capsule["suites"].pop()
        elif mutation == "duplicate_suite": capsule["suites"][1] = copy.deepcopy(suite)
        elif mutation == "wrong_suite_id": suite["suite_id"] = "unreviewed_suite"
        elif mutation == "missing_assertion": suite["assertions"].pop()
        elif mutation == "duplicate_assertion": suite["assertions"][0] = copy.deepcopy(suite["assertions"][1])
        elif mutation == "wrong_assertion_id": suite["assertions"][0]["assertion_id"] = "unreviewed_assertion"
        elif mutation == "altered_expected": suite["assertions"][0]["expected"] += 1
        elif mutation == "false_assertion_pass": suite["assertions"][0]["actual"] += 1
        elif mutation == "altered_tolerance": suite["assertions"][5]["absolute_tolerance"] = 1.0
        elif mutation == "contradictory_projection": suite["fact_projection"]["best_strategy"] = "unreviewed_strategy"
        elif mutation == "promoted_gate": suite["fact_projection"]["promotion_gate_passed"] = True
        elif mutation == "projection_hash": suite["fact_projection_sha256"] = "0" * 64
        elif mutation == "boolean_count": capsule["summary"]["suite_count"] = True
        elif mutation == "malformed_suite": capsule["suites"][0] = None
        elif mutation == "malformed_assertion": suite["assertions"][0] = None
        elif mutation == "malformed_input": capsule["frozen_input"] = []
        elif mutation == "malformed_projection": suite["fact_projection"] = [{"bad": True}]
        elif mutation == "string_pass": suite["assertions"][0]["passed"] = "true"
        elif mutation == "wrong_protocol_id": capsule["protocol_id"] = "unreviewed-protocol"
        elif mutation == "rewritten_negative_gate":
            assertion = next(row for row in suite["assertions"] if row["assertion_id"] == "promotion_gate_passed")
            assertion.update(actual=True, expected=True, passed=True)
            suite["fact_projection"]["promotion_gate_passed"] = True
        elif mutation == "nonfinite_actual": suite["assertions"][5]["actual"] = float("nan")
        else: capsule["capsule_sha256"] = "0" * 64

    if mutation == "capsule_hash":
        receipt = json.loads(receipt_path.read_text())
        path = artifact_root / receipt["manifest"][0]["path"]
        capsule = json.loads(path.read_text()); change(capsule); write_json(path, capsule)
        receipt["manifest"][0].update(sha256=sha256(path), bytes=path.stat().st_size)
        receipt["result"]["capsule_receipt_sha256"] = sha256(path); write_json(receipt_path, receipt)
    else:
        rewrite_capsule(receipt_path, artifact_root, change, recompute_projection_hashes=mutation != "projection_hash")
    report = module.inspect_receipt(receipt_path, artifact_root)
    assert report["passed"] is False
    assert report["computed_claim_state"]["bounded_reproduction_passed"] is False


def test_truthful_computation_failure_remains_documented(tmp_path):
    module = load_module()
    receipt_path, artifact_root = build_complete_receipt(tmp_path)

    def change(capsule):
        suite = capsule["suites"][1]
        assertion = next(row for row in suite["assertions"] if row["assertion_id"] == "best_mase")
        assertion.update(actual=1.0, passed=False, absolute_difference=abs(1.0 - assertion["expected"]), relative_difference=abs(1.0 - assertion["expected"]) / abs(assertion["expected"]))
        suite["fact_projection"]["best_mase"] = 1.0
        suite["passed"] = False
        capsule["status"] = "BOUNDED_REPRODUCIBILITY_FAIL"
        capsule["summary"].update(suite_pass_count=2, assertion_pass_count=30)

    rewrite_capsule(receipt_path, artifact_root, change)
    receipt = json.loads(receipt_path.read_text())
    receipt["result"].update(status="FAIL", capsule_status="BOUNDED_REPRODUCIBILITY_FAIL", suite_pass_count=2, assertion_pass_count=30)
    write_json(receipt_path, receipt)
    report = module.inspect_receipt(receipt_path, artifact_root)
    assert report["passed"] is True
    assert report["status"] == "DOCUMENTED_INDEPENDENT_EXECUTION_NONPASS"


def test_runner_exception_is_documented_without_invented_assertions(tmp_path):
    module = load_module()
    receipt_path, artifact_root = build_complete_receipt(tmp_path)

    def change(capsule):
        suite = capsule["suites"][0]
        suite.update(passed=False, assertions=[], fact_projection={}, error={"type": "ValueError", "message": "bounded fixture failure"})
        capsule["status"] = "BOUNDED_REPRODUCIBILITY_FAIL"
        capsule["summary"].update(suite_pass_count=2, assertion_count=22, assertion_pass_count=22)

    rewrite_capsule(receipt_path, artifact_root, change)
    receipt = json.loads(receipt_path.read_text())
    receipt["result"].update(status="PARTIAL", capsule_status="BOUNDED_REPRODUCIBILITY_FAIL", suite_pass_count=2, assertion_count=22, assertion_pass_count=22)
    write_json(receipt_path, receipt)
    report = module.inspect_receipt(receipt_path, artifact_root)
    assert report["passed"] is True
    assert report["status"] == "DOCUMENTED_INDEPENDENT_EXECUTION_NONPASS"


def test_contracted_review_does_not_meet_current_template_eligibility(tmp_path):
    module = load_module()
    receipt_path, artifact_root = build_complete_receipt(tmp_path)
    receipt = json.loads(receipt_path.read_text())
    receipt["reviewer"]["employed_or_contracted_by_lumencore"] = True
    write_json(receipt_path, receipt)
    report = module.inspect_receipt(receipt_path, artifact_root)
    assert report["passed"] is False
    assert report["reviewer_checks"]["not_employed_or_contracted"] is False


@pytest.mark.parametrize("content", ["null", "[]", '{"schema":1,"schema":2}', '{"value":NaN}', '{"value":Infinity}', '{"value":1e999}'])
def test_malformed_receipt_json_fails_closed(tmp_path, content):
    module = load_module()
    path = tmp_path / "bad.json"; path.write_text(content)
    assert module.inspect_receipt(path, tmp_path)["passed"] is False


def test_protocol_drift_and_symlink_artifacts_fail_closed(tmp_path, monkeypatch):
    module = load_module()
    receipt_path, artifact_root = build_complete_receipt(tmp_path)
    protocol = tmp_path / "protocol.json"
    protocol.write_text(module.FROZEN_PROTOCOL.read_text().replace('"relative_tolerance": 0.01', '"relative_tolerance": 1.0'))
    monkeypatch.setattr(module, "FROZEN_PROTOCOL", protocol)
    assert module.inspect_receipt(receipt_path, artifact_root)["passed"] is False
    monkeypatch.setattr(module, "FROZEN_PROTOCOL", ROOT / "config/reviewer_reproducibility_protocol_v1.json")
    path = artifact_root / "out/codecheck_eia/logs/eia_wave.log"
    replacement = artifact_root / "replacement.log"; path.rename(replacement); path.symlink_to(replacement)
    assert module.inspect_receipt(receipt_path, artifact_root)["passed"] is False


def test_truthfully_failed_promotion_cannot_self_promote_negative_gates(tmp_path):
    module = load_module()
    receipt_path, artifact_root = build_complete_receipt(tmp_path)

    def change(capsule):
        suite = capsule["suites"][0]
        assertion = next(row for row in suite["assertions"] if row["assertion_id"] == "promotion_gate_passed")
        assertion.update(actual=True, passed=False)
        suite["fact_projection"]["promotion_gate_passed"] = True
        suite["passed"] = False
        capsule["status"] = "BOUNDED_REPRODUCIBILITY_FAIL"
        capsule["summary"].update(suite_pass_count=2, assertion_pass_count=30)

    rewrite_capsule(receipt_path, artifact_root, change)
    receipt = json.loads(receipt_path.read_text())
    receipt["result"].update(status="FAIL", capsule_status="BOUNDED_REPRODUCIBILITY_FAIL", suite_pass_count=2, assertion_pass_count=30)
    write_json(receipt_path, receipt)
    report = module.inspect_receipt(receipt_path, artifact_root)
    assert report["passed"] is False
    assert report["capsule"]["protocol_facts_reconciled"] is True
    assert report["result_checks"]["negative_gates_preserved"] is False


@pytest.mark.parametrize("raw", [b'{"schema":1,"schema":2}', b'\xff', b'[' * 1200])
def test_malformed_capsule_json_is_rejected_after_rehash(tmp_path, raw):
    module = load_module()
    receipt_path, artifact_root = build_complete_receipt(tmp_path)
    receipt = json.loads(receipt_path.read_text())
    path = artifact_root / receipt["manifest"][0]["path"]
    path.write_bytes(raw)
    receipt["manifest"][0].update(sha256=sha256(path), bytes=path.stat().st_size)
    receipt["result"]["capsule_receipt_sha256"] = sha256(path)
    write_json(receipt_path, receipt)
    assert module.inspect_receipt(receipt_path, artifact_root)["passed"] is False
