from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "repository_security_assurance",
    ROOT / "code" / "ops" / "VERIFY_REPOSITORY_SECURITY_ASSURANCE.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RepositorySecurityAssuranceTests(unittest.TestCase):
    def canonical_payload(self) -> dict:
        return MODULE.read_json(
            ROOT / "config" / "repository_security_assurance_v1.json"
        )

    def verify_payload(self, payload: dict) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "register.json"
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            return MODULE.verify_register(
                root=ROOT,
                register_path=path,
                verified_utc="2026-08-08T14:20:00Z",
            )

    def test_current_repository_emits_bounded_receipt(self) -> None:
        receipt = self.verify_payload(self.canonical_payload())
        self.assertTrue(receipt["valid"])
        self.assertEqual(receipt["production_decision"], "HOLD")
        self.assertEqual(receipt["control_count"], 6)
        self.assertEqual(receipt["claim_boundary_count"], 7)
        self.assertFalse(receipt["workflow_boundaries"]["automatic_merge"])
        self.assertFalse(receipt["workflow_boundaries"]["runtime_scan"])
        self.assertEqual(len(receipt["receipt_sha256"]), 64)

    def test_duplicate_json_key_is_rejected(self) -> None:
        source = (ROOT / "config" / "repository_security_assurance_v1.json").read_text(
            encoding="utf-8"
        )
        duplicate = source.replace(
            '  "schema_version": "1.0",',
            '  "schema_version": "1.0",\n  "schema_version": "1.0",',
            1,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"
            path.write_text(duplicate, encoding="utf-8")
            with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "duplicate"):
                MODULE.read_json(path)

    def test_non_finite_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nonfinite.json"
            path.write_text('{"value": NaN}', encoding="utf-8")
            with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "non-finite"):
                MODULE.read_json(path)

    def test_status_promotion_is_rejected(self) -> None:
        payload = self.canonical_payload()
        payload["controls"][0]["status"] = "externally_audited"
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "promotion"):
            self.verify_payload(payload)

    def test_missing_claim_boundary_is_rejected(self) -> None:
        payload = self.canonical_payload()
        payload["claim_boundaries"].remove("no_penetration_test")
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "claim boundaries"):
            self.verify_payload(payload)

    def test_path_traversal_is_rejected(self) -> None:
        payload = self.canonical_payload()
        payload["controls"][0]["evidence_paths"][0] = "../SECURITY.md"
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "repository-relative"):
            self.verify_payload(payload)

    def test_codeql_action_must_be_immutable(self) -> None:
        text = (ROOT / ".github" / "workflows" / "codeql.yml").read_text(
            encoding="utf-8"
        )
        text = text.replace(
            f"github/codeql-action/init@{MODULE.CODEQL_SHA}",
            "github/codeql-action/init@v4",
        )
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "CodeQL"):
            MODULE.verify_codeql_workflow(text)

    def test_codeql_security_events_permission_is_required(self) -> None:
        text = (ROOT / ".github" / "workflows" / "codeql.yml").read_text(
            encoding="utf-8"
        )
        text = text.replace("security-events: write", "security-events: read")
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "security-events"):
            MODULE.verify_codeql_workflow(text)

    def test_dependency_gate_threshold_cannot_be_weakened(self) -> None:
        text = (ROOT / ".github" / "workflows" / "dependency-review.yml").read_text(
            encoding="utf-8"
        )
        text = text.replace("fail-on-severity: high", "fail-on-severity: critical")
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "fail-on-severity"):
            MODULE.verify_dependency_review_workflow(text)

    def test_dependency_review_remains_read_only(self) -> None:
        text = (ROOT / ".github" / "workflows" / "dependency-review.yml").read_text(
            encoding="utf-8"
        ) + "\n  pull-requests: write\n"
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "read-only"):
            MODULE.verify_dependency_review_workflow(text)

    def test_all_declared_ecosystems_are_required(self) -> None:
        text = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
        text = text.replace("package-ecosystem: docker", "package-ecosystem: omitted")
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "docker"):
            MODULE.verify_dependabot_config(text)

    def test_known_dashboard_dependency_versions_are_locked(self) -> None:
        package = MODULE.read_json(ROOT / "dashboard" / "package.json")
        lock = MODULE.read_json(ROOT / "dashboard" / "package-lock.json")
        MODULE.verify_dashboard_dependencies(package, lock)

    def test_vulnerable_echarts_lock_is_rejected(self) -> None:
        package = MODULE.read_json(ROOT / "dashboard" / "package.json")
        lock = MODULE.read_json(ROOT / "dashboard" / "package-lock.json")
        lock["packages"]["node_modules/echarts"]["version"] = "6.0.0"
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "echarts"):
            MODULE.verify_dashboard_dependencies(package, lock)

    def test_vulnerable_form_data_override_is_rejected(self) -> None:
        package = MODULE.read_json(ROOT / "dashboard" / "package.json")
        lock = MODULE.read_json(ROOT / "dashboard" / "package-lock.json")
        package["overrides"]["form-data"] = "4.0.5"
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "form-data"):
            MODULE.verify_dashboard_dependencies(package, lock)

    def test_security_policy_must_retain_exception_expiry(self) -> None:
        text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        text = text.replace("expiration date", "review date")
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "expiration date"):
            MODULE.verify_security_policy(text)

    def test_dossier_must_retain_zero_vulnerability_boundary(self) -> None:
        text = (ROOT / "docs" / "REPOSITORY_SECURITY_ASSURANCE.md").read_text(
            encoding="utf-8"
        )
        text = text.replace(
            "does not mean zero vulnerabilities", "establishes zero vulnerabilities"
        )
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "zero vulnerabilities"):
            MODULE.verify_dossier(text)


if __name__ == "__main__":
    unittest.main()
