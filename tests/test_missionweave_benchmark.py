from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from missionweave_benchmark import (  # noqa: E402
    CONDITIONS,
    WEIGHT_CANDIDATES,
    generate_cases,
    run_suite,
    simulate_policy,
)


class MissionWeaveBenchmarkTests(unittest.TestCase):
    def test_case_generation_is_reproducible(self) -> None:
        left = generate_cases(seed=4, arrival_rate=0.5, horizon=90)
        right = generate_cases(seed=4, arrival_rate=0.5, horizon=90)
        self.assertEqual(left, right)

    def test_policy_simulation_is_reproducible(self) -> None:
        cases = generate_cases(seed=8, arrival_rate=0.5, horizon=90)
        condition = CONDITIONS[0]
        weights = WEIGHT_CANDIDATES[0]
        left = simulate_policy(
            cases,
            condition=condition,
            policy="missionweave",
            weights=weights,
            horizon=90,
        )
        right = simulate_policy(
            cases,
            condition=condition,
            policy="missionweave",
            weights=weights,
            horizon=90,
        )
        self.assertEqual(left, right)

    def test_cross_trained_policy_uses_nonprimary_skills(self) -> None:
        cases = generate_cases(seed=11, arrival_rate=0.8, horizon=100)
        metrics = simulate_policy(
            cases,
            condition=CONDITIONS[2],
            policy="cross_trained_fifo",
            horizon=100,
        )
        self.assertGreater(metrics["cross_trained_assignments"], 0)

    def test_suite_separates_development_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "run"
            summary = run_suite(
                out_dir=out,
                development_scenarios=3,
                validation_scenarios=3,
                horizon=90,
            )
            self.assertNotEqual(
                summary["development"]["seed_base"],
                summary["validation"]["seed_base"],
            )
            self.assertEqual(
                set(summary["validation"]["conditions"]),
                {condition.name for condition in CONDITIONS},
            )
            nominal = summary["validation"]["conditions"]["nominal"]["metrics"]
            interval = nominal["missionweave_vs_cross_trained_fifo"][
                "on_time_rate"
            ]["bootstrap_95pct_interval"]
            self.assertEqual(len(interval), 2)
            self.assertLessEqual(interval[0], interval[1])
            manifest = json.loads(
                (out / "manifest.sha256.json").read_text(encoding="utf-8")
            )
            for name, metadata in manifest["files"].items():
                actual = hashlib.sha256((out / name).read_bytes()).hexdigest()
                self.assertEqual(actual, metadata["sha256"])


if __name__ == "__main__":
    unittest.main()
