from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "institutional_readiness",
    ROOT / "code" / "ops" / "VERIFY_INSTITUTIONAL_READINESS.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InstitutionalReadinessTests(unittest.TestCase):
    def canonical_payload(self) -> dict:
        return MODULE.read_json(
            ROOT / "config" / "institutional_readiness_register_v1.json"
        )

    def verify_payload(self, payload: dict) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            register = Path(tmp) / "register.json"
            register.write_text(
                json.dumps(payload, indent=2) + "\n", encoding="utf-8"
            )
            return MODULE.verify_register(
                root=ROOT,
                register_path=register,
                dossier_path=ROOT / "docs" / "INSTITUTIONAL_READINESS_DOSSIER.md",
                verified_utc="2026-08-08T00:00:00Z",
            )

    def test_current_repository_emits_bounded_receipt(self) -> None:
        receipt = self.verify_payload(self.canonical_payload())
        self.assertTrue(receipt["valid"])
        self.assertEqual(receipt["production_decision"], "HOLD")
        self.assertEqual(receipt["assurance_domain_count"], 12)
        self.assertEqual(receipt["claim_boundary_count"], 10)
        self.assertGreaterEqual(receipt["evidence_file_count"], 20)
        self.assertEqual(len(receipt["receipt_sha256"]), 64)

    def test_duplicate_json_key_is_rejected(self) -> None:
        source = (
            ROOT / "config" / "institutional_readiness_register_v1.json"
        ).read_text(encoding="utf-8")
        duplicate = source.replace(
            '  "schema_version": "1.0",',
            '  "schema_version": "1.0",\n  "schema_version": "1.0",',
            1,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"
            path.write_text(duplicate, encoding="utf-8")
            with self.assertRaisesRegex(MODULE.ReadinessError, "duplicate JSON key"):
                MODULE.read_json(path)

    def test_non_finite_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nonfinite.json"
            path.write_text('{"value": NaN}', encoding="utf-8")
            with self.assertRaisesRegex(MODULE.ReadinessError, "non-finite"):
                MODULE.read_json(path)

    def test_missing_evidence_path_is_rejected(self) -> None:
        payload = self.canonical_payload()
        payload["assurance_domains"][0]["evidence_paths"][0] = "missing.txt"
        with self.assertRaises((FileNotFoundError, MODULE.ReadinessError)):
            self.verify_payload(payload)

    def test_path_traversal_is_rejected(self) -> None:
        payload = self.canonical_payload()
        payload["assurance_domains"][0]["evidence_paths"][0] = "../README.md"
        with self.assertRaisesRegex(MODULE.ReadinessError, "repository-relative"):
            self.verify_payload(payload)

    def test_status_count_drift_is_rejected(self) -> None:
        payload = self.canonical_payload()
        payload["status_counts"]["open_gap"] = 0
        with self.assertRaisesRegex(MODULE.ReadinessError, "status_counts"):
            self.verify_payload(payload)

    def test_status_promotion_is_rejected(self) -> None:
        payload = self.canonical_payload()
        domain = next(
            item
            for item in payload["assurance_domains"]
            if item["id"] == "legal_certification_and_insurance"
        )
        domain["status"] = "implemented_first_party"
        with self.assertRaisesRegex(MODULE.ReadinessError, "status promotion"):
            self.verify_payload(payload)

    def test_missing_negative_claim_boundary_is_rejected(self) -> None:
        payload = self.canonical_payload()
        payload["claim_boundaries"].remove("no_independent_validation")
        with self.assertRaisesRegex(MODULE.ReadinessError, "negative claim boundary"):
            self.verify_payload(payload)

    def test_live_snapshot_promotion_is_rejected(self) -> None:
        payload = self.canonical_payload()
        payload["live_exact_snapshot_status"] = "exact_current_commit"
        with self.assertRaisesRegex(MODULE.ReadinessError, "falsely promoted"):
            self.verify_payload(payload)

    def test_commercial_promotion_is_rejected(self) -> None:
        payload = self.canonical_payload()
        domain = next(
            item
            for item in payload["assurance_domains"]
            if item["id"] == "commercial_delivery"
        )
        domain["does_not_prove"] = "Paying customer secured and revenue generated."
        with self.assertRaisesRegex(MODULE.ReadinessError, "negative boundary missing"):
            self.verify_payload(payload)

    def test_domain_negative_boundary_is_required(self) -> None:
        payload = self.canonical_payload()
        domain = next(
            item
            for item in payload["assurance_domains"]
            if item["id"] == "repository_supply_chain"
        )
        domain["does_not_prove"] = "All remaining controls require later review."
        with self.assertRaisesRegex(MODULE.ReadinessError, "complete product sbom"):
            self.verify_payload(payload)

    def test_dossier_must_retain_certification_gap(self) -> None:
        payload = self.canonical_payload()
        with tempfile.TemporaryDirectory() as tmp:
            register = Path(tmp) / "register.json"
            dossier = Path(tmp) / "dossier.md"
            register.write_text(json.dumps(payload), encoding="utf-8")
            text = (ROOT / "docs" / "INSTITUTIONAL_READINESS_DOSSIER.md").read_text(
                encoding="utf-8"
            )
            dossier.write_text(
                text.replace("SOC 2, ISO 27001, FedRAMP", "certifications"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(MODULE.ReadinessError, "SOC 2"):
                MODULE.verify_register(
                    root=ROOT,
                    register_path=register,
                    dossier_path=dossier,
                    verified_utc="2026-08-08T00:00:00Z",
                )


if __name__ == "__main__":
    unittest.main()
