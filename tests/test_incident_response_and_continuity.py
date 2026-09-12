"""Tests for the incident-response policy binding and tabletop verifier."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "VERIFY_INCIDENT_RESPONSE_AND_CONTINUITY.py"
SPEC = importlib.util.spec_from_file_location("incident_readiness", MODULE_PATH)
assert SPEC and SPEC.loader
readiness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(readiness)

CONTROL_FILES = (
    ".github/workflows/deploy.yml",
    ".github/workflows/incident-response-readiness.yml",
    "code/ops/CLASSIFY_PUBLIC_RELEASE_INCIDENT.py",
    "code/ops/VERIFY_INCIDENT_RESPONSE_AND_CONTINUITY.py",
    "config/incident_response_and_continuity_v1.json",
    "config/institutional_readiness_register_v1.json",
    "docs/INCIDENT_RESPONSE_AND_CONTINUITY_PLAN.md",
    "tests/test_public_release_incident_classifier.py",
)


class IncidentReadinessTests(unittest.TestCase):
    def make_root(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        for relative in CONTROL_FILES:
            source = ROOT / relative
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        return temporary, root

    def test_current_repository_emits_bounded_receipt(self) -> None:
        receipt = readiness.verify(root=ROOT, verified_utc="2026-08-08T00:00:00Z")
        self.assertTrue(receipt["valid"])
        self.assertFalse(receipt["live_recovery_exercised"])
        self.assertFalse(receipt["enterprise_sla_established"])
        self.assertEqual(receipt["automatic_severity_cap"], "SEV-2")
        self.assertEqual(len(receipt["tabletop_scenarios"]), 4)

    def test_plan_boundary_is_required(self) -> None:
        temporary, root = self.make_root()
        self.addCleanup(temporary.cleanup)
        path = root / "docs" / "INCIDENT_RESPONSE_AND_CONTINUITY_PLAN.md"
        path.write_text(path.read_text(encoding="utf-8").replace("No automated workflow may notify", "Automation may notify"), encoding="utf-8")
        with self.assertRaisesRegex(readiness.ContinuityVerificationError, "missing required boundary"):
            readiness.verify(root=root, verified_utc="2026-08-08T00:00:00Z")

    def test_live_workflow_classifier_binding_is_required(self) -> None:
        temporary, root = self.make_root()
        self.addCleanup(temporary.cleanup)
        path = root / ".github" / "workflows" / "deploy.yml"
        path.write_text(path.read_text(encoding="utf-8").replace("incident-classification.json", "classification-removed.json"), encoding="utf-8")
        with self.assertRaisesRegex(readiness.ContinuityVerificationError, "missing required boundary"):
            readiness.verify(root=root, verified_utc="2026-08-08T00:00:00Z")

    def test_readiness_status_cannot_be_promoted_or_demoted(self) -> None:
        temporary, root = self.make_root()
        self.addCleanup(temporary.cleanup)
        path = root / "config" / "institutional_readiness_register_v1.json"
        register = json.loads(path.read_text(encoding="utf-8"))
        domain = next(row for row in register["assurance_domains"] if row["id"] == "incident_response_and_continuity")
        domain["status"] = "implemented_first_party"
        path.write_text(json.dumps(register, indent=2) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(readiness.ContinuityVerificationError, "documented_control"):
            readiness.verify(root=root, verified_utc="2026-08-08T00:00:00Z")

    def test_invalid_verified_time_is_rejected(self) -> None:
        with self.assertRaisesRegex(readiness.ContinuityVerificationError, "ISO-8601"):
            readiness.verify(root=ROOT, verified_utc="not-a-time")

    def test_same_attempt_compensation_authority_remains_narrow(self) -> None:
        policy = json.loads(
            (ROOT / "config" / "incident_response_and_continuity_v1.json").read_text(
                encoding="utf-8"
            )
        )
        automated = " ".join(policy["automated_actions_allowed"]).lower()
        human = " ".join(policy["human_authorization_required"]).lower()
        self.assertIn("same still-running human-approved exact-snapshot workflow attempt", automated)
        self.assertIn("captured allowlisted local static state", automated)
        self.assertIn("arbitrary or earlier rollback capture", human)
        self.assertIn("later incident repair", human)


if __name__ == "__main__":
    unittest.main()
