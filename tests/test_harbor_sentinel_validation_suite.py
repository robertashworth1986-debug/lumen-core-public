from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from harbor_sentinel_validation_suite import run_suite  # noqa: E402


class HarborSentinelValidationSuiteTests(unittest.TestCase):
    def test_suite_separates_development_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "run"
            summary = run_suite(
                out_dir=out,
                development_scenarios=3,
                validation_scenarios=3,
                warmup_steps=60,
                test_steps=80,
            )
            self.assertEqual(summary["development"]["seed_base"], 1_600_000)
            self.assertEqual(summary["validation"]["seed_base"], 1_900_000)
            self.assertEqual(summary["schema"], "harbor_sentinel_validation_suite_v2")
            self.assertTrue(
                summary["score_configuration"][
                    "enable_scene_degradation_gate"
                ]
            )
            self.assertEqual(
                summary["score_configuration"]["source_loss_threshold"],
                5.0,
            )
            self.assertIn("nominal_24_tracks", summary["validation"]["conditions"])
            self.assertIn("combined_stress", summary["validation"]["conditions"])
            combined = summary["validation"]["conditions"]["combined_stress"]
            self.assertIn("source_degradation", combined)
            self.assertGreaterEqual(
                combined["source_degradation"][
                    "median_source_degradation_factor"
                ],
                1.0,
            )
            self.assertTrue((out / "manifest.sha256.json").exists())
            manifest = json.loads(
                (out / "manifest.sha256.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                set(manifest["files"]),
                {"summary.json", "scenario_summary.csv", "SCORECARD.md"},
            )
            for metadata in manifest["files"].values():
                self.assertEqual(len(metadata["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
