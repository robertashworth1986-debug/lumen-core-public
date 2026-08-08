import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "code" / "ops" / "VERIFY_PUBLIC_OFFER_CONSISTENCY.py"

spec = importlib.util.spec_from_file_location("verify_public_offer_consistency", VERIFIER_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"unable to load verifier from {VERIFIER_PATH}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PublicOfferConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.strategic = module.load_json_strict(
            ROOT / "config" / "strategic_transaction_packet_v2.json"
        )
        self.sprint = module.load_json_strict(
            ROOT / "config" / "bounded_validation_sprint_v1.json"
        )
        self.docket = module.load_json_strict(ROOT / "dashboard" / "reviewer_docket.json")
        self.surfaces = {
            "readme": (ROOT / "README.md").read_text(encoding="utf-8"),
            "reviewer_start": (ROOT / "docs" / "REVIEWER_START_HERE.md").read_text(
                encoding="utf-8"
            ),
            "home": (ROOT / "dashboard" / "operator_home.html").read_text(
                encoding="utf-8"
            ),
            "proof_to_pilot": (ROOT / "dashboard" / "proof_to_pilot.html").read_text(
                encoding="utf-8"
            ),
            "opportunity_sprint": (
                ROOT / "dashboard" / "opportunity_sprint.html"
            ).read_text(encoding="utf-8"),
        }

    def verify(self, *, strategic=None, sprint=None, docket=None, surfaces=None):
        return module.verify_contracts(
            strategic or self.strategic,
            sprint or self.sprint,
            docket or self.docket,
            surfaces or self.surfaces,
        )

    def test_current_repository_passes(self):
        receipt = module.verify_repository(ROOT)
        self.assertTrue(receipt["valid"])
        self.assertEqual(
            receipt["primary_offer_id"], "buyer-owned-baseline-validation-sprint"
        )
        self.assertEqual(receipt["tier_prices_usd"], [7500, 15000, 25000])
        self.assertEqual(len(receipt["artifact_sha256"]), 8)

    def test_stale_strategic_offer_rejected(self):
        strategic = copy.deepcopy(self.strategic)
        strategic["primary_offer"]["id"] = "prooflock-opportunity-sprint"
        with self.assertRaisesRegex(ValueError, "primary offer id mismatch"):
            self.verify(strategic=strategic)

    def test_stale_docket_url_rejected(self):
        docket = copy.deepcopy(self.docket)
        docket["primary_paid_offer"]["public_url"] = (
            "https://lumen-core.ai/opportunity_sprint.html"
        )
        with self.assertRaisesRegex(ValueError, "public URL mismatch"):
            self.verify(docket=docket)

    def test_tier_price_drift_rejected(self):
        sprint = copy.deepcopy(self.sprint)
        sprint["tiers"][0]["proposed_price_usd"] = 3500
        with self.assertRaisesRegex(ValueError, "tier contract mismatch"):
            self.verify(sprint=sprint)

    def test_old_offer_on_home_rejected(self):
        surfaces = dict(self.surfaces)
        surfaces["home"] += "\nProofLock Opportunity Sprint\n"
        with self.assertRaisesRegex(ValueError, "superseded primary offer"):
            self.verify(surfaces=surfaces)

    def test_secondary_page_without_boundary_rejected(self):
        surfaces = dict(self.surfaces)
        surfaces["opportunity_sprint"] = surfaces["opportunity_sprint"].replace(
            "not the primary public offer", "primary offer"
        )
        with self.assertRaisesRegex(ValueError, "missing canonical offer text"):
            self.verify(surfaces=surfaces)

    def test_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"schema":"v2","schema":"v2"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                module.load_json_strict(path)


if __name__ == "__main__":
    unittest.main()
