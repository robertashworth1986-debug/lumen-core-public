from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from geometry_branching_transport_benchmark import (  # noqa: E402
    CONDITIONS,
    EVIDENCE_BOUNDARY,
    STRATEGIES,
    evaluate_strategy,
    generate_scenario,
    run_suite,
)


class GeometryBranchingTransportBenchmarkTests(unittest.TestCase):
    def test_scenario_generation_is_reproducible(self) -> None:
        condition = CONDITIONS[1]
        left = generate_scenario(1234, condition, split="validation")
        right = generate_scenario(1234, condition, split="validation")

        self.assertEqual(left, right)
        self.assertEqual(left.split, "validation")
        self.assertEqual(len(left.sinks), condition.sink_count)
        self.assertGreater(len(left.edge_risk), 0)
        self.assertTrue(all(0.0 <= risk <= 1.0 for risk in left.edge_risk.values()))

    def test_strategy_evaluation_is_reproducible(self) -> None:
        scenario = generate_scenario(2244, CONDITIONS[2], split="development")
        spec = next(item for item in STRATEGIES if item.name == "crack_propagation_paths")

        left = evaluate_strategy(scenario, spec)
        right = evaluate_strategy(scenario, spec)

        self.assertEqual(left, right)
        self.assertEqual(left["kind"], "geometry_family")
        self.assertEqual(left["family_id"], "crack_propagation_paths")
        self.assertGreaterEqual(left["score"], 0.0)
        self.assertLessEqual(left["score"], 1.0)

    def test_suite_writes_hashable_outputs_and_keeps_claims_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "run"
            summary = run_suite(out, development_scenarios=2, validation_scenarios=2)

            self.assertEqual(summary["schema"], "geometry_branching_transport_benchmark_v1")
            self.assertEqual(summary["evidence_boundary"], EVIDENCE_BOUNDARY)
            self.assertEqual(summary["lane"], "branching_transport")
            self.assertNotEqual(
                summary["development"]["seed_base"],
                summary["validation"]["seed_base"],
            )
            self.assertEqual(
                {row["strategy"] for row in summary["validation"]["leaderboard"]},
                {spec.name for spec in STRATEGIES},
            )
            self.assertEqual(
                summary["claim_gate"],
                {
                    "performance_result_generated": True,
                    "global_geometry_champion": False,
                    "lane_specific_generated_benchmark": True,
                    "field_validation": False,
                    "real_dollar_claim": False,
                },
            )
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
            self.assertIn("Generated benchmark candidate only", scorecard)
            self.assertNotIn("field validation", scorecard.lower().replace("not field validation", ""))


if __name__ == "__main__":
    unittest.main()
