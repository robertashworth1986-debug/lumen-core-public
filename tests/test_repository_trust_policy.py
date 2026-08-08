from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
ACTION_USE_RE = re.compile(
    r"^\s*(?:-\s*)?uses:\s*([^#\s]+)(?:\s+#\s*(\S.*))?$",
    re.MULTILINE,
)
FULL_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class RepositoryTrustPolicyTests(unittest.TestCase):
    def test_security_policy_is_bounded_and_has_private_reporting(self):
        text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        lowered = text.casefold()

        self.assertIn("security/advisories/new", text)
        self.assertIn("no response-time guarantee", lowered)
        self.assertIn("a valid hash or signed artifact establishes identity or custody", lowered)
        self.assertIn("must not contain production credentials", lowered)
        for stale_claim in (
            "the live system handles real money",
            "acknowledgement within **48 hours**",
            "resolution timeline communicated within **5 business days**",
            "kraken execution dashboard | ✅ active",
            "evidence ledger api | ✅ active",
        ):
            self.assertNotIn(stale_claim, lowered)

    def test_contribution_policy_preserves_evidence_and_authority_boundaries(self):
        text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        lowered = text.casefold()

        self.assertIn("evidence before claims", lowered)
        self.assertIn("negative results", lowered)
        self.assertIn("historical evidence packets and receipts should not be rewritten", lowered)
        self.assertIn("legal actions outside the code change", lowered)
        self.assertNotIn("production-grade institutional intelligence platform", lowered)
        self.assertNotIn("the live dashboards, evidence ledger, and site infrastructure", lowered)

    def test_every_external_workflow_action_is_immutably_pinned(self):
        failures = []
        action_count = 0

        workflow_paths = [
            *WORKFLOW_DIR.glob("*.yml"),
            *WORKFLOW_DIR.glob("*.yaml"),
        ]
        for path in sorted(workflow_paths):
            text = path.read_text(encoding="utf-8")
            for match in ACTION_USE_RE.finditer(text):
                action = match.group(1)
                comment = match.group(2)
                if action.startswith("./"):
                    continue
                action_count += 1
                if "@" not in action:
                    failures.append(f"{path.name}: missing action ref: {action}")
                    continue
                _, ref = action.rsplit("@", 1)
                if FULL_COMMIT_RE.fullmatch(ref) is None:
                    failures.append(
                        f"{path.name}: external action is not pinned to a full commit: {action}"
                    )
                if not comment:
                    failures.append(
                        f"{path.name}: pinned action lacks a human-readable version comment: {action}"
                    )

        self.assertGreater(action_count, 0)
        self.assertEqual(failures, [], "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
