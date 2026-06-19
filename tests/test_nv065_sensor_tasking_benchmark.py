from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from nv065_sensor_tasking_benchmark import (  # noqa: E402
    CONDITIONS,
    POLICY_CANDIDATES,
    EVIDENCE_BOUNDARY,
    generate_tracks,
    run_suite,
    simulate_policy,
)


class NV065SensorTaskingBenchmarkTests(unittest.TestCase):
    def test_track_generation_is_reproducible(self) -> None:
        left = generate_tracks(seed=22, condition=CONDITIONS[1], horizon=90)
        right = generate_tracks(seed=22, condition=CONDITIONS[1], horizon=90)
        self.assertEqual(left, right)
        self.assertGreater(len(left), CONDITIONS[1].initial_tracks)

    def test_policy_simulation_is_reproducible(self) -> None:
        specs = generate_tracks(seed=44, condition=CONDITIONS[3], horizon=90)
        params = POLICY_CANDIDATES[0]
        left = simulate_policy(
            specs,
            condition=CONDITIONS[3],
            policy="adaptive_sensor_manager",
            params=params,
            horizon=90,
        )
        right = simulate_policy(
            specs,
            condition=CONDITIONS[3],
            policy="adaptive_sensor_manager",
            params=params,
            horizon=90,
        )
        self.assertEqual(left, right)

    def test_adaptive_manager_releases_sensor_tasking_without_losing_fcq(self) -> None:
        specs = generate_tracks(seed=55, condition=CONDITIONS[0], horizon=100)
        params = POLICY_CANDIDATES[0]
        greedy = simulate_policy(
            specs,
            condition=CONDITIONS[0],
            policy="greedy_uncertainty",
            horizon=100,
        )
        adaptive = simulate_policy(
            specs,
            condition=CONDITIONS[0],
            policy="adaptive_sensor_manager",
            params=params,
            horizon=100,
        )
        self.assertLess(adaptive["assignments_per_step"], greedy["assignments_per_step"])
        self.assertGreaterEqual(
            adaptive["critical_fcq_rate"] + 0.02,
            greedy["critical_fcq_rate"],
        )

    def test_suite_separates_development_validation_and_hashes_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "run"
            summary = run_suite(
                out_dir=out,
                development_scenarios=3,
                validation_scenarios=3,
                horizon=90,
            )
            self.assertEqual(summary["evidence_boundary"], EVIDENCE_BOUNDARY)
            self.assertNotEqual(
                summary["development"]["seed_base"],
                summary["validation"]["seed_base"],
            )
            self.assertEqual(
                set(summary["validation"]["conditions"]),
                {condition.name for condition in CONDITIONS},
            )
            nominal = summary["validation"]["conditions"]["nominal"]["metrics"]
            interval = nominal["adaptive_vs_greedy_uncertainty"][
                "critical_fcq_rate"
            ]["bootstrap_95pct_interval"]
            self.assertEqual(len(interval), 2)
            self.assertLessEqual(interval[0], interval[1])
            task_delta = nominal["adaptive_vs_greedy_uncertainty"][
                "assignments_per_step"
            ]["mean_delta"]
            self.assertIsInstance(task_delta, float)
            manifest = json.loads(
                (out / "manifest.sha256.json").read_text(encoding="utf-8")
            )
            for name, metadata in manifest["files"].items():
                actual = hashlib.sha256((out / name).read_bytes()).hexdigest()
                self.assertEqual(actual, metadata["sha256"])


if __name__ == "__main__":
    unittest.main()
