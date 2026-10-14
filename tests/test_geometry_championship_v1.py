from __future__ import annotations

import hashlib
import copy
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
    REQUIRED_PROMOTION_CONTROLS,
    build_readiness,
    load_registry,
    validate_registry,
    write_run,
)


class GeometryChampionshipV1Tests(unittest.TestCase):
    def test_disabled_or_missing_required_controls_cannot_validate(self) -> None:
        for control in REQUIRED_PROMOTION_CONTROLS:
            for value in (False, "true", 1, None):
                with self.subTest(control=control, value=value):
                    registry = load_registry(DEFAULT_REGISTRY)
                    registry["promotion_gate"][control] = value
                    self.assertTrue(validate_registry(registry))
                    with self.assertRaises(ValueError):
                        build_readiness(registry)
            registry = load_registry(DEFAULT_REGISTRY)
            del registry["promotion_gate"][control]
            self.assertTrue(validate_registry(registry))

    def test_fold_floor_requires_real_integer_and_preserves_stricter_requirement(self) -> None:
        for value in (False, True, 0, 4, 5.0, "5", None):
            with self.subTest(value=value):
                registry = load_registry(DEFAULT_REGISTRY)
                registry["promotion_gate"]["minimum_validation_folds"] = value
                self.assertTrue(validate_registry(registry))
        registry["promotion_gate"]["minimum_validation_folds"] = 6
        self.assertEqual(validate_registry(registry), [])

    def test_malformed_registry_shapes_return_errors_before_readiness(self) -> None:
        original = load_registry(DEFAULT_REGISTRY)
        malformed = [None, [], {}]
        for value in (None, [], "family"):
            registry = copy.deepcopy(original)
            registry["families"][0] = value
            malformed.append(registry)
        for key, value in (("lane", []), ("status", []), ("status", "unproved_champion"),
                           ("competitor", "false"), ("label", None)):
            registry = copy.deepcopy(original)
            registry["families"][0][key] = value
            malformed.append(registry)
        for registry in malformed:
            with self.subTest(registry=registry):
                self.assertTrue(validate_registry(registry))
                with self.assertRaises(ValueError):
                    build_readiness(registry)

    def test_empty_invalid_or_duplicate_baselines_and_metrics_are_rejected(self) -> None:
        for key in ("baselines", "metrics"):
            for value in ([], "dijkstra", [None], [""], ["same", "same"]):
                with self.subTest(key=key, value=value):
                    registry = load_registry(DEFAULT_REGISTRY)
                    registry["lanes"]["mission_network_routing"][key] = value
                    self.assertTrue(validate_registry(registry))

    def test_duplicate_or_nonfinite_json_is_rejected_before_output_creation(self) -> None:
        for text in ('{"schema":"first","schema":"second"}', '{"value":NaN}',
                     '{"value":Infinity}', '{"value":1e309}', '[]'):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as temp_dir:
                source = Path(temp_dir) / "registry.json"
                source.write_text(text)
                output = Path(temp_dir) / "result"
                with self.assertRaises(ValueError):
                    write_run(source, output)
                self.assertFalse(output.exists())

    def test_invalid_semantics_cannot_leave_a_valid_looking_partial_receipt(self) -> None:
        registry = load_registry(DEFAULT_REGISTRY)
        registry["promotion_gate"]["negative_results_retained"] = False
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "registry.json"
            source.write_text(json.dumps(registry))
            output = Path(temp_dir) / "result"
            with self.assertRaises(ValueError):
                write_run(source, output)
            self.assertFalse(output.exists())

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
        self.assertEqual(readiness["family_count"], 26)
        self.assertFalse(readiness["championship_ready"])
        self.assertFalse(readiness["performance_results_generated"])
        self.assertFalse(readiness["claim_gate_passed"])
        self.assertEqual(readiness["performance_ready_families"], [])

    def test_new_visualizations_do_not_become_performance_ready(self) -> None:
        registry = load_registry(DEFAULT_REGISTRY)
        readiness = build_readiness(registry)
        self.assertEqual(readiness["lane_count"], 11)
        self.assertEqual(len(readiness["legacy_only_families"]), 3)
        self.assertEqual(len(readiness["pending_families"]), 23)
        platonic = next(f for f in registry["families"] if f["id"] == "platonic_solids")
        self.assertEqual(len(platonic["members"]), 5)
        self.assertEqual(platonic["status"], "visualization_only")
        self.assertEqual(readiness["performance_ready_families"], [])

    def test_historical_negative_mycelium_result_is_retained(self) -> None:
        registry = load_registry(DEFAULT_REGISTRY)
        family = next(f for f in registry["families"] if f["id"] == "mycelium_network")
        self.assertEqual(family["status"], "legacy_analogue_only")
        self.assertIn("ranked last", family["located_result"])
        self.assertIn("No routing implementation", family["located_result"])

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
