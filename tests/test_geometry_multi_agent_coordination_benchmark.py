from __future__ import annotations

import ast
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "code" / "ops"))

from geometry_multi_agent_coordination_benchmark import (  # noqa: E402
    CONDITIONS,
    DEVELOPMENT_SEED_BASE,
    EVIDENCE_BOUNDARY,
    STRATEGIES,
    VALIDATION_SEED_BASE,
    deterministic_projection,
    generate_scenario,
    run_suite,
    simulate_strategy,
)
from BUILD_FULL_GEOMETRY_PROTOCOL_FIELD import module_geometry_families  # noqa: E402


EXPECTED_BASELINES = {
    "independent_shortest_path",
    "consensus_control",
    "model_predictive_control",
}
EXPECTED_FAMILIES = {
    "bird_v_formation_flocking",
    "boids_swarm_flocking",
    "fish_school_vortex",
    "wolf_pack_pursuit_paths",
}


class GeometryMultiAgentCoordinationBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temp = tempfile.TemporaryDirectory()
        cls.out = Path(cls._temp.name) / "run"
        cls.summary = run_suite(
            cls.out,
            development_scenarios=1,
            validation_scenarios=1,
            bootstrap_resamples=200,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temp.cleanup()

    def test_seeded_scenario_and_metrics_are_reproducible(self) -> None:
        condition = CONDITIONS[3]
        left_scenario = generate_scenario(51_337, condition, split="validation")
        right_scenario = generate_scenario(51_337, condition, split="validation")
        self.assertEqual(left_scenario, right_scenario)

        spec = next(
            item for item in STRATEGIES if item.name == "fish_school_vortex"
        )
        left = simulate_strategy(left_scenario, spec)
        right = simulate_strategy(right_scenario, spec)
        self.assertEqual(deterministic_projection(left), deterministic_projection(right))
        self.assertGreaterEqual(left["runtime_ms"], 0.0)
        self.assertGreaterEqual(right["runtime_ms"], 0.0)

    def test_registry_baselines_are_all_included(self) -> None:
        baselines = {spec.family_id for spec in STRATEGIES if spec.kind == "baseline"}
        self.assertEqual(baselines, EXPECTED_BASELINES)
        leaderboard = self.summary["validation"]["leaderboard"]
        self.assertTrue(EXPECTED_BASELINES.issubset({row["strategy"] for row in leaderboard}))

    def test_frozen_splits_are_separate(self) -> None:
        protocol = self.summary["protocol"]
        self.assertTrue(protocol["frozen_before_validation"])
        self.assertFalse(protocol["split_overlap"])
        self.assertNotEqual(DEVELOPMENT_SEED_BASE, VALIDATION_SEED_BASE)
        development_seeds = {
            row["seed"] for row in self.summary["scenario_receipts"]["development"]
        }
        validation_seeds = {
            row["seed"] for row in self.summary["scenario_receipts"]["validation"]
        }
        self.assertFalse(development_seeds & validation_seeds)
        self.assertFalse(protocol["runtime_used_for_promotion"])

    def test_all_four_declared_families_are_literal_strategy_spec_registrations(self) -> None:
        families = {
            spec.family_id for spec in STRATEGIES if spec.kind == "geometry_family"
        }
        self.assertEqual(families, EXPECTED_FAMILIES)

        source_path = ROOT / "code" / "geometry_multi_agent_coordination_benchmark.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        discovered: set[str] = set()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "StrategySpec"
                and len(node.args) >= 3
            ):
                kind = ast.literal_eval(node.args[1])
                family_id = ast.literal_eval(node.args[2])
                if kind == "geometry_family":
                    discovered.add(family_id)
        self.assertEqual(discovered, EXPECTED_FAMILIES)
        self.assertEqual(module_geometry_families(source_path), EXPECTED_FAMILIES)

    def test_operational_and_superiority_claim_gates_stay_false(self) -> None:
        self.assertEqual(self.summary["evidence_boundary"], EVIDENCE_BOUNDARY)
        claims = self.summary["claim_gate"]
        self.assertTrue(claims["lane_specific_generated_benchmark"])
        self.assertTrue(claims["synthetic_only"])
        for key in (
            "cross_lane_ranking",
            "source_conditioned_evidence",
            "live_evidence",
            "hardware_validation",
            "field_validation",
            "safety_certification",
            "government_approval",
            "universal_superiority",
            "trading_signal",
            "real_dollar_claim",
        ):
            self.assertFalse(claims[key], key)
        self.assertFalse(self.summary["protocol"]["source_conditioned"])
        self.assertTrue(self.summary["protocol"]["no_cross_lane_ranking"])

    def test_losses_and_hashable_runtime_receipts_are_retained(self) -> None:
        negative = self.summary["negative_results"]
        self.assertTrue(negative["retained"])
        self.assertTrue(negative["all_validation_rows_retained"])
        self.assertGreater(negative["loss_count"], 0)
        self.assertTrue(negative["condition_losses_vs_locked_baseline"])
        self.assertEqual(
            negative["validation_row_count"],
            len(CONDITIONS) * len(STRATEGIES),
        )
        self.assertEqual(
            self.summary["execution"]["validation"]["row_count"],
            negative["validation_row_count"],
        )
        manifest = json.loads(
            (self.out / "manifest.sha256.json").read_text(encoding="utf-8")
        )
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
            actual = hashlib.sha256((self.out / name).read_bytes()).hexdigest()
            self.assertEqual(actual, metadata["sha256"])


if __name__ == "__main__":
    unittest.main()
