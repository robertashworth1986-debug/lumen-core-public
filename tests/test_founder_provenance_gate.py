from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code" / "ops"))

from founder_provenance_gate import build_summary, validate_registry  # noqa: E402


def registry() -> dict:
    return {
        "schema": "lumencore_founder_lexicon_v1",
        "owner": "Robert Ashworth",
        "boundary": "This registry records provenance and does not establish legal priority, registration, certification, or validation.",
        "publication_rules": {
            "raw_private_chats_public": False,
            "raw_private_notebooks_public": False,
            "credentials_or_private_portal_records_public": False,
            "founder_origin_assertion_requires_source": True,
            "pending_terms_may_be_promoted": False,
        },
        "terms": [
            {
                "key": "bounded_light_speed",
                "term": "Bounded Light Speed",
                "family": "founder_operating_principle",
                "founder_origin_asserted": True,
                "first_documented_date": "2026-07-15",
                "evidence_state": "verified_current_repo",
                "public_state": "public_safe",
                "public_definition": "Move fast while preserving evidence custody and claim boundaries.",
                "sources": [
                    {"type": "repo_path", "locator": "docs/source.md"}
                ],
            },
            {
                "key": "iseed",
                "term": "iSeed",
                "family": "founder_lineage_pending",
                "founder_origin_asserted": True,
                "first_documented_date": "unknown",
                "evidence_state": "pending_private_source",
                "public_state": "hold",
                "public_definition": "Definition held until a dated source is verified.",
                "sources": [],
            },
        ],
    }


class FounderProvenanceGateTests(unittest.TestCase):
    def test_valid_registry_passes_with_existing_repo_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "source.md").write_text("source\n", encoding="utf-8")
            findings = validate_registry(registry(), root=root)
            summary = build_summary(registry(), findings)
            self.assertTrue(summary["valid"])
            self.assertEqual(summary["term_count"], 2)
            self.assertEqual(summary["error_count"], 0)

    def test_duplicate_key_fails(self) -> None:
        payload = registry()
        payload["terms"].append(dict(payload["terms"][0]))
        findings = validate_registry(payload, root=None)
        self.assertIn("duplicate_key", {finding.code for finding in findings})

    def test_pending_term_cannot_be_public_safe(self) -> None:
        payload = registry()
        payload["terms"][1]["public_state"] = "public_safe"
        findings = validate_registry(payload, root=None)
        self.assertIn("pending_promoted", {finding.code for finding in findings})

    def test_verified_term_requires_source(self) -> None:
        payload = registry()
        payload["terms"][0]["sources"] = []
        findings = validate_registry(payload, root=None)
        self.assertIn("verified_without_source", {finding.code for finding in findings})

    def test_unsafe_legal_or_performance_claim_fails(self) -> None:
        payload = registry()
        payload["terms"][0]["public_definition"] = (
            "A registered trademark with guaranteed certified performance."
        )
        findings = validate_registry(payload, root=None)
        self.assertIn("unsafe_definition_claim", {finding.code for finding in findings})

    def test_missing_repo_source_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            findings = validate_registry(registry(), root=Path(tmp))
        self.assertIn("missing_repo_source", {finding.code for finding in findings})

    def test_private_source_publication_rules_cannot_be_enabled(self) -> None:
        payload = registry()
        payload["publication_rules"]["raw_private_chats_public"] = True
        findings = validate_registry(payload, root=None)
        self.assertIn("unsafe_publication_rule", {finding.code for finding in findings})


if __name__ == "__main__":
    unittest.main()
