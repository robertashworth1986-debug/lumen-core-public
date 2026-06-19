from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from geometry_championship_v1 import (  # noqa: E402
    DEFAULT_REGISTRY,
    REQUIRED_FAMILY_IDS,
    build_readiness,
    load_registry,
    validate_registry,
    write_run,
)


class GeometryChampionshipV1Tests(unittest.TestCase):
    def test_registry_contains_all_required_families(self) -> None:
        registry = load_registry(DEFAULT_REGISTRY)
        self.assertEqual(validate_registry(registry), [])
        ids = {family["id"] for family in registry["families"]}
        self.assertEqual(ids, REQUIRED_FAMILY_IDS)
        self.assertFalse(registry["cross_lane_ranking_allowed"])

    def test_frobenius_is_a_diagnostic(self) -> None:
        registry = load_registry(DEFAULT_REGISTRY)
        family = next(
            item
            for item in registry["families"]
            if item["id"] == "frobenius_stability"
        )
        self.assertFalse(family["competitor"])

    def test_readiness_does_not_invent_performance_results(self) -> None:
        registry = load_registry(DEFAULT_REGISTRY)
        readiness = build_readiness(registry)
        self.assertEqual(readiness["family_count"], 18)
        self.assertFalse(readiness["championship_ready"])
        self.assertFalse(readiness["performance_results_generated"])
        self.assertFalse(readiness["claim_gate_passed"])
        self.assertEqual(readiness["performance_ready_families"], [])

    def test_frozen_readiness_run_hashes_every_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "readiness"
            summary = write_run(
                DEFAULT_REGISTRY,
                out,
                generated=datetime(2026, 6, 18, tzinfo=timezone.utc),
            )
            self.assertTrue(summary["validation"]["registry_valid"])
            manifest = json.loads(
                (out / "manifest.sha256.json").read_text(encoding="utf-8")
            )
            for name, metadata in manifest["files"].items():
                actual = hashlib.sha256((out / name).read_bytes()).hexdigest()
                self.assertEqual(actual, metadata["sha256"])


if __name__ == "__main__":
    unittest.main()
