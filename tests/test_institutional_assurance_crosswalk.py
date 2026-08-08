from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "institutional_assurance_crosswalk",
    ROOT / "code" / "ops" / "VERIFY_INSTITUTIONAL_ASSURANCE_CROSSWALK.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InstitutionalAssuranceCrosswalkTests(unittest.TestCase):
    def canonical_payload(self) -> dict:
        return MODULE.read_json(
            ROOT / "config" / "institutional_assurance_crosswalk_v1.json"
        )

    def verify_payload(
        self,
        payload: dict,
        *,
        guide_text: str | None = None,
        workflow_text: str | None = None,
    ) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            crosswalk = tmp_path / "crosswalk.json"
            guide = tmp_path / "guide.md"
            workflow = tmp_path / "workflow.yml"
            crosswalk.write_text(
                json.dumps(payload, indent=2) + "\n",
                encoding="utf-8",
            )
            guide.write_text(
                guide_text
                if guide_text is not None
                else (ROOT / "docs" / "INSTITUTIONAL_ASSURANCE_CROSSWALK.md").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            workflow.write_text(
                workflow_text
                if workflow_text is not None
                else (
                    ROOT
                    / ".github"
                    / "workflows"
                    / "institutional-assurance-crosswalk.yml"
                ).read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            return MODULE.verify_crosswalk(
                root=ROOT,
                crosswalk_path=crosswalk,
                guide_path=guide,
                workflow_path=workflow,
                verified_utc="2026-08-08T00:00:00Z",
            )

    def test_current_repository_emits_bounded_receipt(self) -> None:
        receipt = self.verify_payload(self.canonical_payload())
        self.assertTrue(receipt["valid"])
        self.assertEqual(receipt["production_decision"], "HOLD")
        self.assertEqual(receipt["framework_count"], 7)
        self.assertEqual(receipt["control_count"], 14)
        self.assertEqual(receipt["status_counts"]["open_gap"], 1)
        self.assertGreaterEqual(receipt["evidence_file_count"], 20)
        self.assertEqual(len(receipt["receipt_sha256"]), 64)

    def test_duplicate_json_key_is_rejected(self) -> None:
        source = (
            ROOT / "config" / "institutional_assurance_crosswalk_v1.json"
        ).read_text(encoding="utf-8")
        duplicate = source.replace(
            '  "schema_version": "1.0",',
            '  "schema_version": "1.0",\n  "schema_version": "1.0",',
            1,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"
            path.write_text(duplicate, encoding="utf-8")
            with self.assertRaisesRegex(
                MODULE.AssuranceCrosswalkError,
                "duplicate JSON key",
            ):
                MODULE.read_json(path)

    def test_non_finite_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nonfinite.json"
            path.write_text('{"value": NaN}', encoding="utf-8")
            with self.assertRaisesRegex(MODULE.AssuranceCrosswalkError, "non-finite"):
                MODULE.read_json(path)

    def test_missing_evidence_path_is_rejected(self) -> None:
        payload = self.canonical_payload()
        payload["controls"][0]["evidence_paths"][0] = "missing.txt"
        with self.assertRaises((FileNotFoundError, MODULE.AssuranceCrosswalkError)):
            self.verify_payload(payload)

    def test_path_traversal_is_rejected(self) -> None:
        payload = self.canonical_payload()
        payload["controls"][0]["evidence_paths"][0] = "../README.md"
        with self.assertRaisesRegex(
            MODULE.AssuranceCrosswalkError,
            "repository-relative",
        ):
            self.verify_payload(payload)

    def test_status_count_drift_is_rejected(self) -> None:
        payload = self.canonical_payload()
        payload["status_counts"]["open_gap"] = 0
        with self.assertRaisesRegex(MODULE.AssuranceCrosswalkError, "status_counts"):
            self.verify_payload(payload)

    def test_status_promotion_is_rejected(self) -> None:
        payload = self.canonical_payload()
        control = next(item for item in payload["controls"] if item["id"] == "AC-14")
        control["status"] = "implemented_first_party"
        with self.assertRaisesRegex(MODULE.AssuranceCrosswalkError, "status promotion"):
            self.verify_payload(payload)

    def test_unknown_framework_mapping_is_rejected(self) -> None:
        payload = self.canonical_payload()
        payload["controls"][0]["framework_mappings"][0]["framework_id"] = "fake"
        with self.assertRaisesRegex(
            MODULE.AssuranceCrosswalkError,
            "unknown framework reference",
        ):
            self.verify_payload(payload)

    def test_framework_version_drift_is_rejected(self) -> None:
        payload = self.canonical_payload()
        framework = next(
            item for item in payload["frameworks"] if item["id"] == "nist_ssdf_1_1"
        )
        framework["version"] = "SSDF 1.2 final"
        with self.assertRaisesRegex(
            MODULE.AssuranceCrosswalkError,
            "official framework version drift",
        ):
            self.verify_payload(payload)

    def test_framework_url_drift_is_rejected(self) -> None:
        payload = self.canonical_payload()
        payload["frameworks"][0]["official_url"] = "https://example.invalid"
        with self.assertRaisesRegex(
            MODULE.AssuranceCrosswalkError,
            "official framework official_url drift",
        ):
            self.verify_payload(payload)

    def test_missing_control_negative_boundary_is_rejected(self) -> None:
        payload = self.canonical_payload()
        control = next(item for item in payload["controls"] if item["id"] == "AC-10")
        control["evidence_does_not_establish"] = "Other work remains."
        with self.assertRaisesRegex(MODULE.AssuranceCrosswalkError, "asvs level"):
            self.verify_payload(payload)

    def test_positive_certification_promotion_is_rejected(self) -> None:
        payload = self.canonical_payload()
        control = next(item for item in payload["controls"] if item["id"] == "AC-14")
        control["evidence_establishes"] = "The system is SOC 2 certified."
        with self.assertRaisesRegex(
            MODULE.AssuranceCrosswalkError,
            "unsupported assurance promotion",
        ):
            self.verify_payload(payload)

    def test_missing_claim_boundary_is_rejected(self) -> None:
        payload = self.canonical_payload()
        payload["claim_boundaries"].remove("not_a_slsa_level_or_complete_product_provenance")
        with self.assertRaisesRegex(MODULE.AssuranceCrosswalkError, "claim boundary"):
            self.verify_payload(payload)

    def test_guide_must_retain_limitations(self) -> None:
        guide = (
            ROOT / "docs" / "INSTITUTIONAL_ASSURANCE_CROSSWALK.md"
        ).read_text(encoding="utf-8")
        with self.assertRaisesRegex(MODULE.AssuranceCrosswalkError, "No ASVS level"):
            self.verify_payload(
                self.canonical_payload(),
                guide_text=guide.replace("No ASVS level", "No application level"),
            )

    def test_workflow_must_bind_verifier(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "institutional-assurance-crosswalk.yml"
        ).read_text(encoding="utf-8")
        with self.assertRaisesRegex(MODULE.AssuranceCrosswalkError, "workflow binding"):
            self.verify_payload(
                self.canonical_payload(),
                workflow_text=workflow.replace(
                    "python code/ops/VERIFY_INSTITUTIONAL_ASSURANCE_CROSSWALK.py",
                    "echo skipped",
                ),
            )

    def test_receipt_hash_is_deterministic_for_fixed_commit_and_time(self) -> None:
        first = self.verify_payload(copy.deepcopy(self.canonical_payload()))
        second = self.verify_payload(copy.deepcopy(self.canonical_payload()))
        self.assertEqual(first["receipt_sha256"], second["receipt_sha256"])


if __name__ == "__main__":
    unittest.main()
