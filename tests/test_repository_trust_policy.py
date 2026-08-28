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
    def test_public_resume_and_generator_keep_claims_inside_evidence_boundary(self):
        resume = (ROOT / "RESUME_LUMENCORE.md").read_text(encoding="utf-8").casefold()
        generator = (ROOT / "code" / "lumalinkedin_resume_engine_v1.py").read_text(
            encoding="utf-8"
        ).casefold()

        unsafe_public_claims = (
            "annual modeled value",
            "modeled annual value",
            "router edge",
            "harmonic win rate",
            "institutional-grade",
            "government-grade",
            "production-ready",
            "proven packages",
            "monetizable",
            "cross-sector avoided cost",
            "federal-ready",
            "investor-grade",
            "$52,331,333,340",
        )
        for phrase in unsafe_public_claims:
            self.assertNotIn(phrase, resume)
            self.assertNotIn(phrase, generator)

        required_boundaries = (
            "independent validation",
            "not established",
            "live-order authority",
            "final external submission authority",
            "swe infrastructure specialist / ai trainer",
            "frozen delta",
            "harborsentinel",
            "no outside execution receipt",
        )
        for phrase in required_boundaries:
            self.assertIn(phrase, resume)

    def test_resume_outreach_is_claim_bounded_and_requires_current_run_approval(self):
        dispatcher = (ROOT / "code" / "email_resume_dispatcher.py").read_text(
            encoding="utf-8"
        ).casefold()
        runner = (ROOT / "code" / "ops" / "RUN_EMAIL_RESUME_DISPATCHER.ps1").read_text(
            encoding="utf-8"
        ).casefold()
        pdf_builder = (ROOT / "code" / "build_elite_resume_pdf.py").read_text(
            encoding="utf-8"
        ).casefold()

        for phrase in (
            "master valuation proxy usd:",
            "valuation increment usd:",
            "opportunity fit score:",
        ):
            self.assertNotIn(phrase, dispatcher)

        self.assertIn("--send-approved", dispatcher)
        self.assertIn("--send-approved requires --once", dispatcher)
        self.assertIn("human_send_approval_required", dispatcher)
        self.assertIn("approvedsend", runner)
        self.assertIn("-approvedsend requires -once", runner)
        self.assertIn("--send-approved", runner)
        self.assertNotIn("elite resume</title>", pdf_builder)
        self.assertNotIn(r"c:\lumatrader\institutional_stack_v2", pdf_builder)
        self.assertIn("path(__file__).resolve().parents[1]", pdf_builder)
        self.assertIn('root / "output" / "pdf"', pdf_builder)
        self.assertIn("--no-legacy-copy", pdf_builder)

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
