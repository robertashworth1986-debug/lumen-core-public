from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
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


def refresh_manifest_hash(capsule: dict) -> None:
    manifest = capsule["manifest"]
    payload = {
        "manifest_format": manifest["manifest_format"],
        "input_hashes": manifest["input_hashes"],
        "output_hashes": manifest["output_hashes"],
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    manifest["manifest_hash"] = hashlib.sha256(canonical).hexdigest()


class ProofCapsuleVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.capsule_path = (
            ROOT
            / "examples"
            / "proof_capsule"
            / "dice_eia_public_capsule.json"
        )
        self.document = MODULE.load_capsule_document(self.capsule_path)
        self.capsule = self.document.data

    def assertFails(self, capsule: dict) -> None:  # noqa: N802
        with self.assertRaises(MODULE.CapsuleError):
            MODULE.validate_capsule(capsule, ROOT)

    def test_public_capsule_verifies(self) -> None:
        result = MODULE.validate_capsule(
            self.capsule,
            ROOT,
            capsule_file_sha256=self.document.file_sha256,
            capsule_file_bytes=self.document.byte_count,
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["receipt_schema"], "proof-capsule-receipt-v3")
        self.assertEqual(result["verifier_version"], "3.0")
        self.assertEqual(
            result["verification_scope"],
            "capsule-schema-and-custody",
        )
        self.assertEqual(result["capsule_schema_version"], "3.0")
        self.assertTrue(result["capsule_file_custody_complete"])
        self.assertEqual(result["capsule_file_sha256"], self.document.file_sha256)
        self.assertEqual(result["capsule_file_bytes"], self.document.byte_count)
        self.assertEqual(len(result["capsule_canonical_sha256"]), 64)
        self.assertEqual(result["verified_hash_records"], 1)
        self.assertGreater(result["verified_bytes"], 0)
        self.assertEqual(
            result["manifest_format"],
            "proof-capsule-manifest-v3",
        )
        self.assertEqual(result["declared_evidence_type"], "replay")
        self.assertEqual(
            result["declared_external_validation_status"],
            "not_established",
        )
        self.assertFalse(result["external_report_manifest_bound"])
        self.assertFalse(result["external_validator_identity_evaluated"])
        self.assertFalse(result["external_validator_independence_evaluated"])
        self.assertFalse(result["external_validation_conclusion_evaluated"])
        self.assertEqual(result["pilot_decision"], "external_review")
        self.assertFalse(result["release_authorization_evaluated"])
        self.assertTrue(result["human_unlock_required"])

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

    def test_in_memory_validation_does_not_claim_file_custody(self) -> None:
        result = MODULE.validate_capsule(self.capsule, ROOT)
        self.assertFalse(result["capsule_file_custody_complete"])
        self.assertIsNone(result["capsule_file_sha256"])
        self.assertIsNone(result["capsule_file_bytes"])

    def test_windows_alternate_data_stream_path_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["manifest"]["output_hashes"][0]["path"] = (
            "examples/proof_capsule/dice_eia_public_summary.txt:stream"
        )
        self.assertFails(mutated)

    def test_windows_reserved_device_path_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["manifest"]["output_hashes"][0]["path"] = "examples/NUL.txt"
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

    def test_hardlink_alias_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first.txt"
            second = root / "second.txt"
            first.write_text("same artifact", encoding="utf-8")
            try:
                os.link(first, second)
            except OSError as exc:
                self.skipTest(f"hardlinks unavailable: {exc}")
            digest = hashlib.sha256(first.read_bytes()).hexdigest()
            mutated = copy.deepcopy(self.capsule)
            mutated["manifest"]["input_hashes"] = [
                {"path": "first.txt", "sha256": digest}
            ]
            mutated["manifest"]["output_hashes"] = [
                {"path": "second.txt", "sha256": digest}
            ]
            refresh_manifest_hash(mutated)
            with self.assertRaisesRegex(MODULE.CapsuleError, "same file identity"):
                MODULE.validate_capsule(mutated, root)

    def test_symlink_manifest_path_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target.txt"
            link = root / "link.txt"
            target.write_text("target artifact", encoding="utf-8")
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlinks unavailable: {exc}")
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            mutated = copy.deepcopy(self.capsule)
            mutated["manifest"]["input_hashes"] = []
            mutated["manifest"]["output_hashes"] = [
                {"path": "link.txt", "sha256": digest}
            ]
            refresh_manifest_hash(mutated)
            with self.assertRaisesRegex(MODULE.CapsuleError, "symlink"):
                MODULE.validate_capsule(mutated, root)

    def test_invalid_manifest_hash_format_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["manifest"]["manifest_hash"] = "not-a-digest"
        self.assertFails(mutated)

    def test_manifest_role_swap_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["manifest"]["input_hashes"] = mutated["manifest"]["output_hashes"]
        mutated["manifest"]["output_hashes"] = []
        self.assertFails(mutated)

    def test_unknown_top_level_field_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["external_validation_complete"] = True
        self.assertFails(mutated)

    def test_unknown_nested_field_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["result"]["investor_claim"] = "approved"
        self.assertFails(mutated)

    def test_unknown_hash_record_field_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["manifest"]["output_hashes"][0]["verified"] = True
        self.assertFails(mutated)

    def test_old_schema_version_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["schema_version"] = "2.0"
        self.assertFails(mutated)

    def test_old_manifest_format_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["manifest"]["manifest_format"] = "proof-capsule-manifest-v2"
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

    def test_loose_unknown_code_commit_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["run"]["code_commit"] = "unknown but trusted"
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

    def test_normalized_secondary_metric_claim_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["result"]["secondary_metrics"].append(
            "Guaranteed-return-on-investment"
        )
        self.assertFails(mutated)

    def test_noncanonical_unicode_path_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["manifest"]["output_hashes"][0]["path"] = "examples/e\u0301.txt"
        self.assertFails(mutated)

    def test_hyphenated_forbidden_phrase_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["result"]["summary"] = "Field-validated savings are established"
        self.assertFails(mutated)

    def test_hidden_format_character_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["title"] = "Best\u200b in the world"
        self.assertFails(mutated)

    def test_surrounding_whitespace_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["title"] = f" {mutated['title']}"
        self.assertFails(mutated)

    def test_external_label_without_provenance_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["evidence_type"] = "externally_validated"
        self.assertFails(mutated)

    def test_non_external_capsule_cannot_populate_validator_fields(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["external_validation"]["validator_name"] = "Unbound validator"
        self.assertFails(mutated)

    def test_external_validation_report_must_be_manifest_bound(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        mutated["evidence_type"] = "externally_validated"
        mutated["external_validation"] = {
            "status": "established",
            "validator_name": "Unit-test validator",
            "validator_organization": "Unit-test organization",
            "scope": "Unit-test fixture only",
            "completed_at_utc": "2026-06-22T00:00:00Z",
            "report_path": "examples/proof_capsule/not-in-manifest.txt",
            "report_sha256": "0" * 64,
        }
        self.assertFails(mutated)

    def test_manifest_bound_external_validation_fixture_verifies(self) -> None:
        mutated = copy.deepcopy(self.capsule)
        report = mutated["manifest"]["output_hashes"][0]
        mutated["evidence_type"] = "externally_validated"
        mutated["external_validation"] = {
            "status": "established",
            "validator_name": "Unit-test validator",
            "validator_organization": "Unit-test organization",
            "scope": "Unit-test fixture only; no real validation claim",
            "completed_at_utc": "2026-06-22T00:00:00Z",
            "report_path": report["path"],
            "report_sha256": report["sha256"],
        }
        result = MODULE.validate_capsule(mutated, ROOT)
        self.assertEqual(
            result["declared_external_validation_status"],
            "established",
        )
        self.assertTrue(result["external_report_manifest_bound"])
        self.assertFalse(result["external_validator_identity_evaluated"])
        self.assertFalse(result["external_validator_independence_evaluated"])
        self.assertFalse(result["external_validation_conclusion_evaluated"])

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

    def test_aggregate_artifact_size_budget_fails_closed(self) -> None:
        with self.assertRaisesRegex(MODULE.CapsuleError, "aggregate maximum size"):
            MODULE.validate_capsule(
                self.capsule,
                ROOT,
                max_total_artifact_bytes=1,
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

    def test_nonstandard_json_number_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nan.json"
            path.write_text('{"value":NaN}', encoding="utf-8")
            with self.assertRaisesRegex(
                MODULE.CapsuleError,
                "non-standard JSON number",
            ):
                MODULE.load_capsule(path)

    def test_deeply_nested_json_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deep.json"
            path.write_text("[" * 2000 + "0" + "]" * 2000, encoding="utf-8")
            with self.assertRaises(MODULE.CapsuleError):
                MODULE.load_capsule(path)

    def test_capsule_symlink_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target.json"
            link = root / "link.json"
            target.write_text("{}", encoding="utf-8")
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlinks unavailable: {exc}")
            with self.assertRaisesRegex(MODULE.CapsuleError, "not a link"):
                MODULE.load_capsule(link)

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
