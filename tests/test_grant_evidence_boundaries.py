from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from application_context_resolver import load_application_profile  # noqa: E402
from grant_application_factory import (  # noqa: E402
    _resolve_v2_utc,
    build_evidence_summary,
    build_program_spotlights,
    render_budget,
    render_technical_volume,
)


class GrantEvidenceBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        catalog = json.loads(
            (ROOT / "data" / "grant_catalog.json").read_text(encoding="utf-8")
        )
        cls.program = next(
            item
            for item in catalog["programs"]
            if item["id"] == "dod_sbir_26bz_nv063"
        )
        cls.profile = load_application_profile()
        cls.evidence = build_evidence_summary(_resolve_v2_utc())

    def test_nv063_renderer_preserves_evidence_boundaries(self) -> None:
        volume = render_technical_volume(
            self.program,
            self.profile,
            self.evidence,
        )
        self.assertIn("Legacy router audit", volume)
        self.assertIn("not used as submission performance evidence", volume)
        self.assertIn("Preliminary synthetic software evidence", volume)
        self.assertIn("does not establish operational harbor", volume)
        self.assertNotIn("Program-targeted dataset findings", volume)

    def test_navy_topic_does_not_use_generic_dataset_spotlights(self) -> None:
        self.assertEqual(
            build_program_spotlights(
                self.program,
                self.evidence["run_utc"],
            ),
            [],
        )

    def test_navy_budget_separates_six_month_base_and_option(self) -> None:
        budget = render_budget(self.program, self.profile)
        self.assertEqual(budget["total"], 315_000)
        self.assertEqual(
            budget["periods"]["phase_i_base"]["ceiling_usd"],
            200_000,
        )
        self.assertEqual(
            budget["periods"]["phase_i_option"]["ceiling_usd"],
            115_000,
        )
        self.assertEqual(budget["periods"]["phase_i_base"]["months"], 6)
        self.assertEqual(budget["periods"]["phase_i_option"]["months"], 6)


if __name__ == "__main__":
    unittest.main()
