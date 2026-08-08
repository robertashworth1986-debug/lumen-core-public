from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


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


if __name__ == "__main__":
    unittest.main()
