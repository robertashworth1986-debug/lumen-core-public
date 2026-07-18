from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_bounded_validation_sprint",
    ROOT / "code" / "ops" / "validate_bounded_validation_sprint.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BoundedValidationSprintTests(unittest.TestCase):
    def setUp(self) -> None:
        self.offer_path = ROOT / "config" / "bounded_validation_sprint_v1.json"
        self.offer = MODULE.load_json(self.offer_path)

    def assertFails(self, payload: dict) -> None:  # noqa: N802
        with self.assertRaises(MODULE.OfferValidationError):
            MODULE.validate_offer(payload)

    def test_repository_offer_is_valid_but_not_approved(self) -> None:
        result = MODULE.validate_repository(ROOT)
        self.assertTrue(result["valid"])
        self.assertEqual(result["status"], "proposed_founder_review")
        self.assertEqual(result["tier_count"], 3)
        self.assertEqual(result["proposed_prices_usd"], [7500, 15000, 25000])
        self.assertFalse(result["founder_approved_for_external_use"])
        self.assertFalse(result["legal_review_complete"])

    def test_missing_rights_boundary_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.offer)
        mutated["offer"]["accepted_source_rights"].remove("buyer_authorized")
        self.assertFails(mutated)

    def test_missing_sensitive_data_exclusion_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.offer)
        mutated["offer"]["excluded_without_separate_written_controls"].remove(
            "controlled unclassified information"
        )
        self.assertFails(mutated)

    def test_missing_negative_result_deliverable_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.offer)
        mutated["offer"]["required_deliverables"].remove(
            "failure and negative-result register"
        )
        self.assertFails(mutated)

    def test_duplicate_tier_id_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.offer)
        mutated["tiers"][1]["tier_id"] = mutated["tiers"][0]["tier_id"]
        self.assertFails(mutated)

    def test_non_increasing_prices_fail_closed(self) -> None:
        mutated = copy.deepcopy(self.offer)
        mutated["tiers"][1]["proposed_price_usd"] = 5000
        self.assertFails(mutated)

    def test_more_than_thirty_days_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.offer)
        mutated["tiers"][2]["duration_calendar_days_max"] = 45
        self.assertFails(mutated)

    def test_multiple_primary_metrics_fail_closed(self) -> None:
        mutated = copy.deepcopy(self.offer)
        mutated["tiers"][0]["scope_limits"]["primary_metrics_max"] = 2
        self.assertFails(mutated)

    def test_proposed_offer_cannot_claim_founder_approval(self) -> None:
        mutated = copy.deepcopy(self.offer)
        mutated["approval"]["founder_approved_for_external_use"] = True
        self.assertFails(mutated)

    def test_approved_offer_requires_founder_approval(self) -> None:
        mutated = copy.deepcopy(self.offer)
        mutated["status"] = "approved_for_use"
        self.assertFails(mutated)

    def test_positive_guaranteed_savings_claim_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.offer)
        mutated["commercial_position"] = "This product provides guaranteed savings."
        self.assertFails(mutated)

    def test_duplicate_json_key_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"
            path.write_text(
                '{"schema":"one","schema":"two"}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                MODULE.OfferValidationError,
                "duplicate JSON key",
            ):
                MODULE.load_json(path)

    def test_document_phrase_removal_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir()
            source_offer = (
                ROOT / "docs" / "LUMENCORE_BOUNDED_VALIDATION_SPRINT_OFFER.md"
            ).read_text(encoding="utf-8")
            source_sow = (
                ROOT
                / "docs"
                / "LUMENCORE_BOUNDED_VALIDATION_SPRINT_SOW_TEMPLATE.md"
            ).read_text(encoding="utf-8")
            (docs / "LUMENCORE_BOUNDED_VALIDATION_SPRINT_OFFER.md").write_text(
                source_offer.replace("A favorable result is not promised", "Outcome statement"),
                encoding="utf-8",
            )
            (docs / "LUMENCORE_BOUNDED_VALIDATION_SPRINT_SOW_TEMPLATE.md").write_text(
                source_sow,
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                MODULE.OfferValidationError,
                "required phrase missing",
            ):
                MODULE.validate_documents(root)

    def test_validator_output_is_json_serializable(self) -> None:
        result = MODULE.validate_repository(ROOT)
        encoded = json.dumps(result, sort_keys=True)
        self.assertIn("lumencore_bounded_validation_sprint_v1", encoded)


if __name__ == "__main__":
    unittest.main()
