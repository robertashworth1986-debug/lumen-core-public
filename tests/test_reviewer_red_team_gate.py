from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_REVIEWER_RED_TEAM_GATE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("reviewer_red_team_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReviewerRedTeamGateTests(unittest.TestCase):
    def test_gate_scores_dice_and_harbor_without_upload_claims(self) -> None:
        module = load_module()
        payload = module.build_gate()

        self.assertEqual(payload["schema"], "reviewer_red_team_gate_v1")
        self.assertEqual(payload["summary"]["packages_reviewed"], 2)
        self.assertEqual(payload["summary"]["ready_for_upload_count"], 0)
        gates = {row["package"]: row for row in payload["reviewer_gates"]}
        self.assertIn("DICE", gates)
        self.assertIn("HarborSentinel", gates)
        self.assertFalse(gates["DICE"]["ready_for_upload"])
        self.assertFalse(gates["HarborSentinel"]["ready_for_upload"])
        self.assertGreaterEqual(gates["DICE"]["scores"]["evidence_score"], 7)
        self.assertGreaterEqual(gates["HarborSentinel"]["scores"]["evidence_score"], 7)
        self.assertIn("BAAT", "\n".join(gates["DICE"]["must_fix_before_upload"]))
        self.assertIn("DSIP", "\n".join(gates["HarborSentinel"]["must_fix_before_upload"]))
        self.assertTrue(
            any(
                "DICE frozen live-breadth replay ready" in fact
                for fact in gates["DICE"]["verified_strengths"]
            )
        )
        self.assertTrue(
            any(item["phrase"] == "frozen live-breadth replay" and item["present"] for item in gates["DICE"]["phrase_checks"])
        )
        self.assertTrue(
            any(item["phrase"] == "provenance-gated live-breadth annex" and item["present"] for item in gates["DICE"]["phrase_checks"])
        )
        self.assertTrue(
            any(
                "AIS review-burden profile ready" in fact
                for fact in gates["HarborSentinel"]["verified_strengths"]
            )
        )
        self.assertTrue(
            any(
                item["phrase"] == "unlabeled public AIS review-burden profile" and item["present"]
                for item in gates["HarborSentinel"]["phrase_checks"]
            )
        )
        self.assertTrue(
            any(
                item["phrase"] == "measurement discipline and chain-of-custody" and item["present"]
                for item in gates["HarborSentinel"]["phrase_checks"]
            )
        )

    def test_gate_sanitizes_sensitive_identifiers_and_preserves_no_claims(self) -> None:
        module = load_module()
        payload = module.build_gate()
        markdown = module.render_markdown(payload)
        serialized = json.dumps(payload).lower() + markdown.lower()

        self.assertNotRegex(serialized, r"uei\s+[a-z0-9]{8,16}")
        self.assertNotRegex(serialized, r"cage/?ncage\s+[a-z0-9]{3,10}")
        self.assertNotIn("sk-" + "proj", serialized)
        self.assertNotIn('"ready_for_upload": true', serialized)
        self.assertIn("guaranteed funding", serialized)
        self.assertIn("do not claim", serialized)
        self.assertIn("does not authorize upload", markdown)

    def test_write_gate_outputs_files(self) -> None:
        module = load_module()
        payload = module.build_gate()
        with tempfile.TemporaryDirectory() as temp_dir:
            old_out = module.OUT
            old_grants = module.GRANTS
            old_json = module.OUT_JSON
            old_md = module.OUT_MD
            try:
                module.OUT = Path(temp_dir) / "out"
                module.GRANTS = Path(temp_dir) / "grant_submissions"
                module.OUT_JSON = module.OUT / "reviewer_red_team_gate_latest.json"
                module.OUT_MD = module.GRANTS / "REVIEWER_RED_TEAM_GATE_2026-06-20.md"
                module.write_gate(payload)
                self.assertTrue(module.OUT_JSON.exists())
                self.assertTrue(module.OUT_MD.exists())
            finally:
                module.OUT = old_out
                module.GRANTS = old_grants
                module.OUT_JSON = old_json
                module.OUT_MD = old_md


if __name__ == "__main__":
    unittest.main()
