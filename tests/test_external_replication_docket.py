from __future__ import annotations

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "external_replication_docket",
    ROOT / "code" / "ops" / "validate_external_replication_docket.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ExternalReplicationDocketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.path = ROOT / "config" / "external_replication_docket_v1.json"
        self.docket = MODULE.load_docket(self.path)

    def reseal(self, payload: dict) -> dict:
        payload["custody"]["payload_sha256"] = MODULE.compute_payload_sha256(payload)
        return payload

    def assert_fails(self, payload: dict, pattern: str | None = None) -> None:
        self.reseal(payload)
        context = (
            self.assertRaisesRegex(MODULE.DocketError, pattern)
            if pattern
            else self.assertRaises(MODULE.DocketError)
        )
        with context:
            MODULE.validate_docket(payload)

    def external_complete(self) -> dict:
        payload = copy.deepcopy(self.docket)
        payload["status"] = "external_complete"
        payload["evaluation"]["source"]["rights_status"] = "public"
        payload["evaluation"]["freeze"].update(
            {
                "protocol_hash": "1" * 64,
                "code_commit": "a" * 40,
                "dependency_lock": "requirements-lock.txt sha256:example",
                "environment_spec": "Python 3.12 / Ubuntu 24.04 / evaluator-owned runner",
                "frozen_utc": "2026-07-20T12:00:00Z",
            }
        )
        payload["independence"].update(
            {
                "evaluator_name": "Qualified Reviewer",
                "organization": "Independent Evaluation Laboratory",
                "role": "Lead evaluator",
                "relationship": "independent",
                "conflict_disclosure": "No financial or employment relationship disclosed.",
                "data_control": "Evaluator controlled the held-out source.",
                "run_control": "Evaluator executed the frozen run.",
                "analysis_control": "Evaluator calculated the locked metric.",
                "publication_permission": "Bounded result sentence approved in writing.",
            }
        )
        payload["reproducibility"].update(
            {
                "input_manifest": "sha256:" + "2" * 64,
                "output_manifest": "sha256:" + "3" * 64,
                "run_receipt": "sha256:" + "4" * 64,
                "tolerance_definition": "Exact manifest equality and metric tolerance fixed at 1e-9.",
            }
        )
        payload["reporting"].update(
            {
                "evidence_class": "external",
                "results_summary": "The evaluator completed the frozen comparison and retained all outcomes.",
                "primary_result": "Candidate result recorded against the locked threshold.",
                "uncertainty_interval": "95% interval recorded in the evaluator report.",
                "sample_size": "Evaluator-owned held-out sample size recorded in the run receipt.",
                "negative_results": ["One adverse secondary finding was retained."],
                "failure_notes": ["No integrity failure; one operational limitation remains."],
                "deviations": ["No unapproved deviation from the frozen protocol."],
                "limitations": ["The result applies only to the named source, comparator, metric, and window."],
            }
        )
        for gate in payload["gates"]:
            payload["gates"][gate] = True
        payload["decision"].update(
            {
                "status": "pilot_candidate",
                "owner": "Independent evaluator and named buyer decision owner",
                "next_gate": "Separate buyer authorization for a bounded pilot.",
                "decided_utc": "2026-07-20T14:00:00Z",
            }
        )
        payload["claim_boundary"] = {
            "proves": [
                "A named evaluator completed the frozen comparison and preserved the signed run receipt.",
                "The recorded result is bounded to the named source, comparator, metric, threshold, and window.",
            ],
            "does_not_prove": [
                "Universal performance",
                "Certification or safety approval",
                "Production deployment or guaranteed savings",
            ],
            "safe_sentence": "A named evaluator completed the predeclared run; interpretation remains bounded to the recorded protocol and written permission.",
        }
        return self.reseal(payload)

    def test_template_verifies_and_remains_hold(self) -> None:
        receipt = MODULE.validate_docket(self.docket)
        self.assertTrue(receipt["valid"])
        self.assertEqual(receipt["status"], "template_unassigned")
        self.assertEqual(receipt["decision"], "hold")
        self.assertEqual(receipt["preregistration_gates_passed"], 0)
        self.assertFalse(receipt["safe_for_external_validation_claim"])

    def test_external_complete_can_pass_only_with_full_evidence(self) -> None:
        receipt = MODULE.validate_docket(self.external_complete())
        self.assertEqual(receipt["status"], "external_complete")
        self.assertEqual(receipt["external_gates_passed"], 2)
        self.assertTrue(receipt["safe_for_external_validation_claim"])

    def test_payload_hash_mutation_fails_closed(self) -> None:
        payload = copy.deepcopy(self.docket)
        payload["title"] = "Changed after sealing"
        with self.assertRaisesRegex(MODULE.DocketError, "payload hash mismatch"):
            MODULE.validate_docket(payload)

    def test_unknown_root_key_fails_closed(self) -> None:
        payload = copy.deepcopy(self.docket)
        payload["approval"] = True
        self.assert_fails(payload, "root key mismatch")

    def test_forbidden_authority_field_fails_closed(self) -> None:
        payload = copy.deepcopy(self.docket)
        payload["reporting"]["action_authority"] = True
        with self.assertRaisesRegex(MODULE.DocketError, "forbidden authority field"):
            MODULE.validate_docket(self.reseal(payload))

    def test_template_cannot_assert_gate(self) -> None:
        payload = copy.deepcopy(self.docket)
        payload["gates"]["evaluator_assigned"] = True
        self.assert_fails(payload, "cannot assert completed gates")

    def test_template_cannot_request_promotion(self) -> None:
        payload = copy.deepcopy(self.docket)
        payload["decision"]["status"] = "pilot_candidate"
        self.assert_fails(payload, "decision must be hold")

    def test_post_outcome_tuning_fails_closed(self) -> None:
        payload = copy.deepcopy(self.docket)
        payload["evaluation"]["design"]["no_post_outcome_tuning"] = False
        self.assert_fails(payload, "no_post_outcome_tuning must be true")

    def test_invalid_confidence_level_fails_closed(self) -> None:
        payload = copy.deepcopy(self.docket)
        payload["evaluation"]["analysis"]["confidence_level"] = 1.2
        self.assert_fails(payload, "between 0 and 1")

    def test_duplicate_list_entry_fails_closed(self) -> None:
        payload = copy.deepcopy(self.docket)
        payload["evaluation"]["analysis"]["failure_rules"].append(
            payload["evaluation"]["analysis"]["failure_rules"][0].upper()
        )
        self.assert_fails(payload, "duplicate entry")

    def test_empty_negative_results_fails_closed(self) -> None:
        payload = copy.deepcopy(self.docket)
        payload["reporting"]["negative_results"] = []
        self.assert_fails(payload, "must not be empty")

    def test_negative_result_requirement_cannot_be_disabled(self) -> None:
        payload = copy.deepcopy(self.docket)
        payload["reproducibility"]["negative_results_required"] = False
        self.assert_fails(payload, "negative_results_required must be true")

    def test_offline_verifier_requirement_cannot_be_disabled(self) -> None:
        payload = copy.deepcopy(self.docket)
        payload["reproducibility"]["offline_verifier_required"] = False
        self.assert_fails(payload, "offline_verifier_required must be true")

    def test_preregistered_requires_all_freeze_gates(self) -> None:
        payload = copy.deepcopy(self.docket)
        payload["status"] = "preregistered"
        payload["reporting"]["evidence_class"] = "preregistered"
        payload["decision"]["status"] = "independent_replication"
        payload["decision"]["decided_utc"] = "2026-07-20T12:00:00Z"
        payload["evaluation"]["source"]["rights_status"] = "public"
        payload["evaluation"]["freeze"].update(
            {
                "protocol_hash": "1" * 64,
                "code_commit": "a" * 40,
                "dependency_lock": "lock.txt",
                "environment_spec": "Python 3.12",
                "frozen_utc": "2026-07-20T12:00:00Z",
            }
        )
        self.assert_fails(payload, "requires all preregistration gates")

    def test_internal_complete_cannot_be_pilot_candidate(self) -> None:
        payload = self.external_complete()
        payload["status"] = "internal_complete"
        payload["reporting"]["evidence_class"] = "internal"
        payload["gates"]["external_run_complete"] = False
        payload["gates"]["reviewer_attestation_present"] = False
        payload["decision"]["status"] = "pilot_candidate"
        payload["claim_boundary"]["does_not_prove"].append(
            "External validation beyond the recorded run"
        )
        self.assert_fails(payload, "cannot promote directly")

    def test_internal_complete_requires_external_boundary(self) -> None:
        payload = self.external_complete()
        payload["status"] = "internal_complete"
        payload["reporting"]["evidence_class"] = "internal"
        payload["gates"]["external_run_complete"] = False
        payload["gates"]["reviewer_attestation_present"] = False
        payload["decision"]["status"] = "independent_replication"
        payload["claim_boundary"]["does_not_prove"] = ["Universal performance"]
        self.assert_fails(payload, "external-validation boundary")

    def test_external_complete_requires_every_gate(self) -> None:
        payload = self.external_complete()
        payload["gates"]["reviewer_attestation_present"] = False
        self.assert_fails(payload, "requires every gate")

    def test_external_complete_rejects_founder_controlled_evaluator(self) -> None:
        payload = self.external_complete()
        payload["independence"]["relationship"] = "founder-controlled"
        self.assert_fails(payload, "cannot be founder-controlled")

    def test_external_complete_rejects_pending_run_receipt(self) -> None:
        payload = self.external_complete()
        payload["reproducibility"]["run_receipt"] = "pending"
        self.assert_fails(payload, "cannot remain")

    def test_unsafe_positive_claim_fails_closed(self) -> None:
        payload = copy.deepcopy(self.docket)
        payload["claim_boundary"]["safe_sentence"] = (
            "External validation established for the platform."
        )
        self.assert_fails(payload, "unsafe positive claim")

    def test_invalid_utc_timestamp_fails_closed(self) -> None:
        payload = self.external_complete()
        payload["decision"]["decided_utc"] = "2026-07-20T14:00:00-05:00"
        self.assert_fails(payload, "explicit UTC Z")

    def test_invalid_protocol_hash_fails_closed(self) -> None:
        payload = self.external_complete()
        payload["evaluation"]["freeze"]["protocol_hash"] = "not-a-hash"
        self.assert_fails(payload, "SHA-256 digest")

    def test_invalid_code_commit_fails_closed(self) -> None:
        payload = self.external_complete()
        payload["evaluation"]["freeze"]["code_commit"] = "latest"
        self.assert_fails(payload, "Git SHA")

    def test_rejected_status_requires_reject_decision(self) -> None:
        payload = copy.deepcopy(self.docket)
        payload["status"] = "rejected"
        self.assert_fails(payload, "requires reject decision")

    def test_duplicate_json_key_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"
            path.write_text('{"schema":"one","schema":"two"}', encoding="utf-8")
            with self.assertRaisesRegex(MODULE.DocketError, "duplicate JSON key"):
                MODULE.load_docket(path)

    def test_nonfinite_json_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nan.json"
            path.write_text('{"value":NaN}', encoding="utf-8")
            with self.assertRaisesRegex(MODULE.DocketError, "non-finite JSON value"):
                MODULE.load_docket(path)

    def test_size_budget_fails_closed(self) -> None:
        with self.assertRaisesRegex(MODULE.DocketError, "exceeds maximum size"):
            MODULE.load_docket(self.path, max_bytes=1)


if __name__ == "__main__":
    unittest.main()
