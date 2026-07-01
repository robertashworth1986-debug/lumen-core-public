from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from geometry_optimal_curve_transport_benchmark import (  # noqa: E402
    CONDITIONS,
    EVIDENCE_BOUNDARY,
    STRATEGIES,
    evaluate_strategy,
    generate_scenario,
    run_suite,
)


class GeometryOptimalCurveTransportBenchmarkTests(unittest.TestCase):
    def test_scenario_generation_is_reproducible(self) -> None:
        condition = CONDITIONS[2]
        left = generate_scenario(8844, condition, split="validation")
        right = generate_scenario(8844, condition, split="validation")

        self.assertEqual(left, right)
        self.assertEqual(left.split, "validation")
        self.assertEqual(left.start, (0.0, condition.vertical_drop))
        self.assertEqual(left.end, (condition.horizontal_distance, 0.0))
        self.assertGreater(left.field_drag, 0.0)
        self.assertGreaterEqual(left.obstacle_bias, 0.0)

    def test_strategy_evaluation_is_reproducible(self) -> None:
        scenario = generate_scenario(9977, CONDITIONS[0], split="development")
        spec = next(item for item in STRATEGIES if item.name == "brachistochrone_descent")

        left = evaluate_strategy(scenario, spec)
        right = evaluate_strategy(scenario, spec)

        self.assertEqual(left, right)
        self.assertEqual(left["kind"], "geometry_family")
        self.assertEqual(left["family_id"], "brachistochrone_descent")
        self.assertGreaterEqual(left["score"], 0.0)
        self.assertLessEqual(left["score"], 1.0)
        self.assertGreater(left["travel_time"], 0.0)

    def test_suite_writes_hashable_outputs_and_blocks_operational_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "run"
            summary = run_suite(out, development_scenarios=2, validation_scenarios=2)

            self.assertEqual(summary["schema"], "geometry_optimal_curve_transport_benchmark_v1")
            self.assertEqual(summary["evidence_boundary"], EVIDENCE_BOUNDARY)
            self.assertEqual(summary["lane"], "optimal_curve_transport")
            self.assertEqual(summary["registry_first_test"], "brachistochrone_curve_v1")
            self.assertNotEqual(
                summary["development"]["seed_base"],
                summary["validation"]["seed_base"],
            )
            self.assertEqual(
                {row["strategy"] for row in summary["validation"]["leaderboard"]},
                {spec.name for spec in STRATEGIES},
            )
            self.assertEqual(summary["claim_gate"]["lane_specific_generated_benchmark"], True)
            self.assertEqual(summary["claim_gate"]["global_geometry_champion"], False)
            self.assertEqual(summary["claim_gate"]["robotics_validation"], False)
            self.assertEqual(summary["claim_gate"]["cabling_validation"], False)
            self.assertEqual(summary["claim_gate"]["field_validation"], False)
            self.assertEqual(summary["claim_gate"]["trading_signal"], False)
            self.assertEqual(summary["claim_gate"]["real_dollar_claim"], False)
            self.assertIn(
                summary["promotion_gate"]["gate"],
                {"candidate_geometry_beats_best_baseline", "baseline_still_leads"},
            )

            manifest = json.loads((out / "manifest.sha256.json").read_text(encoding="utf-8"))
            self.assertEqual(
                set(manifest["files"]),
                {
                    "summary.json",
                    "SCORECARD.md",
                    "scenario_summary.csv",
                    "leaderboard.csv",
                },
            )
            for name, metadata in manifest["files"].items():
                actual = hashlib.sha256((out / name).read_bytes()).hexdigest()
                self.assertEqual(actual, metadata["sha256"])

            scorecard = (out / "SCORECARD.md").read_text(encoding="utf-8")
            self.assertIn("Generated optimal-curve benchmark candidate only", scorecard)
            self.assertIn("not robotics", scorecard)
            self.assertIn("real-dollar performance", scorecard)


if __name__ == "__main__":
    unittest.main()
