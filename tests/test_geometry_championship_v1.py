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
    MINIMUM_FAMILY_COUNT,
    MINIMUM_NATURE_OR_FLOW_LOGIC_FAMILY_COUNT,
    REQUIRED_FAMILY_IDS,
    build_readiness,
    has_native_nature_or_flow_logic,
    load_registry,
    validate_registry,
    write_run,
)


class GeometryChampionshipV1Tests(unittest.TestCase):
    def test_registry_contains_all_required_families(self) -> None:
        registry = load_registry(DEFAULT_REGISTRY)
        self.assertEqual(validate_registry(registry), [])
        ids = {family["id"] for family in registry["families"]}
        self.assertTrue(REQUIRED_FAMILY_IDS.issubset(ids))
        self.assertGreaterEqual(len(ids), registry["minimum_family_count"])
        self.assertGreaterEqual(registry["minimum_family_count"], MINIMUM_FAMILY_COUNT)
        lanes = {family["lane"] for family in registry["families"]}
        self.assertIn("market_signal_geometry", lanes)
        self.assertFalse(registry["cross_lane_ranking_allowed"])

    def test_registry_preserves_native_nature_and_flow_logic_depth(self) -> None:
        registry = load_registry(DEFAULT_REGISTRY)
        native_nature_or_flow = [
            family
            for family in registry["families"]
            if has_native_nature_or_flow_logic(family)
        ]
        readiness = build_readiness(registry)

        self.assertGreaterEqual(
            len(native_nature_or_flow),
            MINIMUM_NATURE_OR_FLOW_LOGIC_FAMILY_COUNT,
        )
        self.assertEqual(
            readiness["nature_or_flow_logic_family_count"],
            len(native_nature_or_flow),
        )
        self.assertGreaterEqual(readiness["benchmark_specified_family_count"], 50)
        self.assertIn(
            "brachistochrone_descent",
            readiness["native_nature_or_flow_logic_families"],
        )
        self.assertIn(
            "kuramoto_phase_coupling",
            readiness["native_nature_or_flow_logic_families"],
        )
        self.assertNotIn(
            "beast_strategy_breakout",
            readiness["native_nature_or_flow_logic_families"],
        )

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
        self.assertGreaterEqual(readiness["family_count"], registry["minimum_family_count"])
        self.assertGreaterEqual(readiness["lane_count"], 12)
        self.assertFalse(readiness["championship_ready"])
        self.assertFalse(readiness["performance_results_generated"])
        self.assertFalse(readiness["claim_gate_passed"])
        self.assertEqual(readiness["performance_ready_families"], [])
        self.assertIsNone(readiness["performance_champion"])
        self.assertTrue(readiness["candidate_rankings"])
        self.assertIsNotNone(readiness["champion_of_champions_candidate"])
        self.assertIn("market_signal_geometry", readiness["lane_candidate_champions"])
        candidate_ids = {row["id"] for row in readiness["candidate_rankings"]}
        self.assertIn("brachistochrone_descent", candidate_ids)
        self.assertIn("order_book_liquidity_contours", candidate_ids)

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
