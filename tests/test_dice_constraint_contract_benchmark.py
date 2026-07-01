from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from dice_constraint_contract_benchmark import (  # noqa: E402
    CONDITIONS,
    EVIDENCE_BOUNDARY,
    generate_trial,
    run_protocol,
    run_suite,
)


class DiceConstraintContractBenchmarkTests(unittest.TestCase):
    def test_trial_generation_is_reproducible(self) -> None:
        left = generate_trial(
            seed=41,
            agents=60,
            tasks=120,
            roles=6,
            condition=CONDITIONS[1],
        )
        right = generate_trial(
            seed=41,
            agents=60,
            tasks=120,
            roles=6,
            condition=CONDITIONS[1],
        )
        self.assertEqual(left, right)
        _, tasks = left
        first_half_roles = {task.role for task in tasks[: len(tasks) // 2]}
        self.assertGreater(len(first_half_roles), 1)

    def test_protocol_is_reproducible_and_charges_contract_fields(self) -> None:
        population, tasks = generate_trial(
            seed=52,
            agents=60,
            tasks=120,
            roles=6,
            condition=CONDITIONS[2],
        )
        left = run_protocol(
            seed=52,
            population=population,
            tasks=tasks,
            condition=CONDITIONS[2],
            architecture="constraint_contract",
            margin=0,
        )
        right = run_protocol(
            seed=52,
            population=population,
            tasks=tasks,
            condition=CONDITIONS[2],
            architecture="constraint_contract",
            margin=0,
        )
        self.assertEqual(left, right)
        self.assertGreater(left.contract_fields_transmitted, 0)

    def test_monitor_shift_exposes_false_rejection(self) -> None:
        population, tasks = generate_trial(
            seed=63,
            agents=120,
            tasks=240,
            roles=6,
            condition=CONDITIONS[3],
        )
        result = run_protocol(
            seed=63,
            population=population,
            tasks=tasks,
            condition=CONDITIONS[3],
            architecture="constraint_contract",
            margin=1,
        )
        self.assertGreater(result.false_rejection_rate, 0.0)

    def test_suite_separates_development_and_validation_and_hashes_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "run"
            summary = run_suite(
                out_dir=out,
                development_scenarios=3,
                validation_scenarios=3,
                agents=60,
                tasks=120,
                roles=6,
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
            manifest = json.loads(
                (out / "manifest.sha256.json").read_text(encoding="utf-8")
            )
            for name, metadata in manifest["files"].items():
                actual = hashlib.sha256((out / name).read_bytes()).hexdigest()
                self.assertEqual(actual, metadata["sha256"])


if __name__ == "__main__":
    unittest.main()
