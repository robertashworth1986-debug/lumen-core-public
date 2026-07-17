from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "proof_capsule_verifier", ROOT / "code" / "proof_capsule_verifier.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProofCapsuleVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.capsule_path = ROOT / "examples" / "proof_capsule" / "dice_eia_public_capsule.json"
        self.capsule = json.loads(self.capsule_path.read_text(encoding="utf-8"))

    def test_public_capsule_verifies(self) -> None:
        result = MODULE.validate_capsule(self.capsule, ROOT)
        self.assertTrue(result["valid"])
        self.assertEqual(result["verified_hash_records"], 1)
        self.assertEqual(result["pilot_decision"], "external_review")

    def test_hash_tampering_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["manifest"]["output_hashes"][0]["sha256"] = "0" * 64
        with self.assertRaises(MODULE.CapsuleError):
            MODULE.validate_capsule(mutated, ROOT)

    def test_unlocked_metric_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["locked_metric"]["locked_before_run"] = False
        with self.assertRaises(MODULE.CapsuleError):
            MODULE.validate_capsule(mutated, ROOT)

    def test_missing_negative_result_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["result"]["negative_results"] = []
        with self.assertRaises(MODULE.CapsuleError):
            MODULE.validate_capsule(mutated, ROOT)

    def test_path_escape_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["manifest"]["output_hashes"][0]["path"] = "../outside.txt"
        with self.assertRaises(MODULE.CapsuleError):
            MODULE.validate_capsule(mutated, ROOT)

    def test_public_home_uses_proof_to_pilot_story(self) -> None:
        home = (ROOT / "dashboard" / "operator_home.html").read_text(encoding="utf-8")
        self.assertIn("One proof path. One bounded decision.", home)
        self.assertIn("Internal replay evidence is not external validation.", home)
        self.assertNotIn("One platform. Four products. One truth layer.", home)
        self.assertNotIn("Finish and submit the current NSF Project Pitch.", home)
        self.assertNotIn('href="/evidence/"', home)


if __name__ == "__main__":
    unittest.main()
