from __future__ import annotations

import importlib.util
import json
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "public_assurance_suite",
    ROOT / "code" / "ops" / "run_public_assurance_suite.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PublicAssuranceSuiteTests(unittest.TestCase):
    def make_fixture(
        self,
        root: Path,
        *,
        result: dict | None = None,
        exit_code: int = 0,
        stdout: str | None = None,
    ) -> dict:
        source = root / "fixture.txt"
        source.write_text("bounded fixture\n", encoding="utf-8")
        script = root / "check.py"
        if stdout is None:
            stdout = json.dumps(result or {"valid": True, "state": "hold"})
        script.write_text(
            textwrap.dedent(
                f"""
                print({stdout!r})
                raise SystemExit({exit_code})
                """
            ),
            encoding="utf-8",
        )
        return {
            "check_id": "fixture_check",
            "command": ("{python}", "check.py"),
            "sources": ("fixture.txt", "check.py"),
            "expected": {"valid": True, "state": "hold"},
        }

    def test_valid_custom_suite_emits_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = self.make_fixture(
                root, result={"valid": True, "state": "hold"}
            )
            receipt = MODULE.run_suite(
                root,
                commit="a" * 40,
                checks=(spec,),
                timeout_seconds=5,
            )
            self.assertTrue(receipt["valid"])
            self.assertEqual(receipt["check_count"], 1)
            self.assertEqual(receipt["commit"], "a" * 40)
            self.assertEqual(len(receipt["source_files"]), 2)
            self.assertEqual(
                receipt["checks"][0]["public_result"]["state"], "hold"
            )

    def test_nonzero_check_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = self.make_fixture(root, exit_code=7)
            with self.assertRaisesRegex(MODULE.AssuranceError, "exited 7"):
                MODULE.run_suite(root, checks=(spec,), timeout_seconds=5)

    def test_invalid_json_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = self.make_fixture(root, stdout="not json")
            with self.assertRaisesRegex(MODULE.AssuranceError, "not valid JSON"):
                MODULE.run_suite(root, checks=(spec,), timeout_seconds=5)

    def test_result_contract_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = self.make_fixture(
                root, result={"valid": True, "state": "promote"}
            )
            with self.assertRaisesRegex(MODULE.AssuranceError, "contract mismatch"):
                MODULE.run_suite(root, checks=(spec,), timeout_seconds=5)

    def test_missing_source_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = self.make_fixture(root)
            (root / "fixture.txt").unlink()
            with self.assertRaisesRegex(
                MODULE.AssuranceError, "required source file is missing"
            ):
                MODULE.run_suite(root, checks=(spec,), timeout_seconds=5)

    def test_path_escape_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = self.make_fixture(root)
            spec["sources"] = ("../outside.txt",)
            with self.assertRaisesRegex(MODULE.AssuranceError, "not canonical"):
                MODULE.run_suite(root, checks=(spec,), timeout_seconds=5)

    def test_duplicate_check_id_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = self.make_fixture(root)
            with self.assertRaisesRegex(
                MODULE.AssuranceError, "duplicate assurance check_id"
            ):
                MODULE.run_suite(root, checks=(spec, spec), timeout_seconds=5)

    def test_invalid_commit_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = self.make_fixture(root)
            with self.assertRaisesRegex(MODULE.AssuranceError, "commit must be"):
                MODULE.run_suite(
                    root, commit="latest", checks=(spec,), timeout_seconds=5
                )

    def test_default_commands_are_argument_arrays(self) -> None:
        self.assertIsInstance(MODULE.DEFAULT_CHECKS[0]["command"], tuple)
        self.assertEqual(MODULE.DEFAULT_CHECKS[0]["command"][0], "{python}")

    def test_default_capsule_contract_requires_v3_custody_boundaries(self) -> None:
        capsule = MODULE.DEFAULT_CHECKS[0]
        self.assertEqual(capsule["check_id"], "proof_capsule_v3")
        expected = capsule["expected"]
        self.assertEqual(expected["receipt_schema"], "proof-capsule-receipt-v3")
        self.assertEqual(expected["verifier_version"], "3.0")
        self.assertTrue(expected["capsule_file_custody_complete"])
        self.assertEqual(
            expected["declared_external_validation_status"],
            "not_established",
        )
        self.assertFalse(expected["external_validator_identity_evaluated"])
        self.assertFalse(expected["external_validator_independence_evaluated"])
        self.assertFalse(expected["external_validation_conclusion_evaluated"])
        self.assertFalse(expected["release_authorization_evaluated"])
        self.assertTrue(expected["human_unlock_required"])

    def test_strict_json_rejects_duplicate_keys(self) -> None:
        with self.assertRaisesRegex(MODULE.AssuranceError, "duplicate JSON key"):
            MODULE._strict_json(
                '{"valid":true,"valid":false}', context="fixture"
            )

    def test_strict_json_rejects_nonfinite_values(self) -> None:
        with self.assertRaisesRegex(MODULE.AssuranceError, "non-finite value"):
            MODULE._strict_json('{"value":NaN}', context="fixture")


if __name__ == "__main__":
    unittest.main()
