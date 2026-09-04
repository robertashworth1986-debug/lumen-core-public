import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments" / "flexible_electronics" / "phase1_trace_reliability.py"
CONFIG = ROOT / "experiments" / "flexible_electronics" / "phase1_trace_reliability_config.json"

spec = importlib.util.spec_from_file_location("flex_phase1", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
assert spec.loader is not None
spec.loader.exec_module(mod)


class FlexibleElectronicsPhase1Tests(unittest.TestCase):
    def test_config_is_explicitly_nonvalidated(self):
        cfg = json.loads(CONFIG.read_text())
        self.assertEqual(cfg["task_lane"], "materials_structures_and_packaging")
        self.assertFalse(cfg["frozen_comparison_rules"]["simulation_equals_experimental_validation"])
        self.assertTrue(cfg["frozen_comparison_rules"]["negative_results_retained"])

    def test_matrix_has_expected_size(self):
        cfg = json.loads(CONFIG.read_text())
        rows = mod.run()
        expected = len(cfg["materials"]) * len(cfg["geometries"]) * len(cfg["bend_radius_mm"]) * len(cfg["stretch_pct"])
        self.assertEqual(len(rows), expected)

    def test_straight_trace_is_shortest_within_each_material_and_condition(self):
        rows = mod.run()
        grouped = {}
        for r in rows:
            key = (r.material, r.bend_radius_mm, r.stretch_pct)
            grouped.setdefault(key, []).append(r)
        for candidates in grouped.values():
            straight = next(r for r in candidates if r.geometry == "straight")
            self.assertLessEqual(straight.path_length_mm, min(r.path_length_mm for r in candidates) + 1e-9)

    def test_no_candidate_can_be_accepted_after_constraint_failure(self):
        for r in mod.run():
            if not (r.manufacturability_pass and r.thermal_pass and r.strain_pass):
                self.assertFalse(r.accepted)
                self.assertGreaterEqual(r.primary_score, 1000.0)

    def test_outputs_include_manifest_and_negative_result_state(self):
        rows = mod.run()
        mod.write_outputs(rows)
        out = ROOT / "out" / "flexible-electronics-phase1"
        summary = json.loads((out / "summary.json").read_text())
        self.assertFalse(summary["experimentally_validated"])
        self.assertTrue(summary["negative_results_retained"])
        self.assertTrue((out / "trace_reliability_matrix.csv").exists())
        self.assertTrue((out / "sha256_manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
