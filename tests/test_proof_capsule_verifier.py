from __future__ import annotations

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "proof_capsule_verifier",
    ROOT / "code" / "proof_capsule_verifier.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProofCapsuleVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.capsule_path = (
            ROOT
            / "examples"
            / "proof_capsule"
            / "dice_eia_public_capsule.json"
        )
        self.capsule = MODULE.load_capsule(self.capsule_path)

    def assertFails(self, capsule: dict) -> None:  # noqa: N802
        with self.assertRaises(MODULE.CapsuleError):
            MODULE.validate_capsule(capsule, ROOT)

    def test_public_capsule_verifies(self) -> None:
        result = MODULE.validate_capsule(self.capsule, ROOT)
        self.assertTrue(result["valid"])
        self.assertEqual(result["verifier_version"], "2.0")
        self.assertEqual(result["verified_hash_records"], 1)
        self.assertGreater(result["verified_bytes"], 0)
        self.assertEqual(result["pilot_decision"], "external_review")

    def test_hash_tampering_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["manifest"]["output_hashes"][0]["sha256"] = "0" * 64
        self.assertFails(mutated)

    def test_unlocked_metric_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["locked_metric"]["locked_before_run"] = False
        self.assertFails(mutated)

    def test_missing_negative_result_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["result"]["negative_results"] = []
        self.assertFails(mutated)

    def test_path_escape_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["manifest"]["output_hashes"][0]["path"] = "../outside.txt"
        self.assertFails(mutated)

    def test_windows_absolute_path_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["manifest"]["output_hashes"][0]["path"] = "C:/outside.txt"
        self.assertFails(mutated)

    def test_backslash_path_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["manifest"]["output_hashes"][0]["path"] = (
            "examples\\proof_capsule\\dice_eia_public_summary.txt"
        )
        self.assertFails(mutated)

    def test_redundant_separator_path_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["manifest"]["output_hashes"][0]["path"] = (
            "examples//proof_capsule/dice_eia_public_summary.txt"
        )
        self.assertFails(mutated)

    def test_duplicate_manifest_path_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["manifest"]["input_hashes"] = [
            copy.deepcopy(mutated["manifest"]["output_hashes"][0])
        ]
        self.assertFails(mutated)

    def test_invalid_manifest_hash_format_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["manifest"]["manifest_hash"] = "not-a-digest"
        self.assertFails(mutated)

    def test_unknown_rights_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["source"]["rights_status"] = "unknown"
        self.assertFails(mutated)

    def test_invalid_source_type_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["source"]["type"] = "spreadsheet-ish"
        self.assertFails(mutated)

    def test_non_utc_timestamp_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["run"]["timestamp_utc"] = "2026-06-21T00:15:00-05:00"
        self.assertFails(mutated)

    def test_invalid_timestamp_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["run"]["timestamp_utc"] = "yesterday"
        self.assertFails(mutated)

    def test_evidence_run_type_mismatch_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["run"]["run_type"] = "measured"
        self.assertFails(mutated)

    def test_invalid_code_commit_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["run"]["code_commit"] = "maybe-latest"
        self.assertFails(mutated)

    def test_duplicate_string_list_entry_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        item = mutated["result"]["negative_results"][0]
        mutated["result"]["negative_results"].append(item.upper())
        self.assertFails(mutated)

    def test_non_string_list_entry_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["result"]["failure_notes"].append({"hidden": "value"})
        self.assertFails(mutated)

    def test_missing_external_validation_boundary_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["claim_boundary"]["does_not_prove"] = [
            "agency endorsement",
            "customer deployment",
        ]
        self.assertFails(mutated)

    def test_forbidden_promotional_claim_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["result"]["primary_delta"] = "Guaranteed ROI of 20 percent"
        self.assertFails(mutated)

    def test_invalid_capsule_id_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["capsule_id"] = "bad id with spaces"
        self.assertFails(mutated)

    def test_artifact_size_budget_fails_closed(self) -> None:
        with self.assertRaises(MODULE.CapsuleError):
            MODULE.validate_capsule(
                self.capsule,
                ROOT,
                max_artifact_bytes=1,
            )

    def test_duplicate_json_key_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"
            path.write_text(
                '{"title":"one","title":"two"}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                MODULE.CapsuleError,
                "duplicate JSON key",
            ):
                MODULE.load_capsule(path)

    def test_non_utf8_capsule_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "binary.json"
            path.write_bytes(b"\xff\xfe\x00")
            with self.assertRaisesRegex(
                MODULE.CapsuleError,
                "valid UTF-8",
            ):
                MODULE.load_capsule(path)

    def test_capsule_size_budget_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            MODULE.CapsuleError,
            "capsule exceeds maximum size",
        ):
            MODULE.load_capsule(self.capsule_path, max_bytes=1)

    def test_public_home_uses_proof_to_pilot_story(self) -> None:
        home = (ROOT / "dashboard" / "operator_home.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("One proof path. One bounded decision.", home)
        self.assertIn(
            "Internal replay evidence is not external validation.",
            home,
        )
        self.assertNotIn("One platform. Four products. One truth layer.", home)
        self.assertNotIn(
            "Finish and submit the current NSF Project Pitch.",
            home,
        )
        self.assertNotIn('href="/evidence/"', home)


if __name__ == "__main__":
    unittest.main()
