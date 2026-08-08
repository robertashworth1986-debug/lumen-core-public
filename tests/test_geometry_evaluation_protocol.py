import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


VERIFIER_PATH = Path("code/ops/VERIFY_GEOMETRY_EVALUATION_PROTOCOL.py")
PROTOCOL_PATH = Path("config/geometry_evaluation_protocol_v1.json")

spec = importlib.util.spec_from_file_location("verify_geometry_protocol", VERIFIER_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"unable to load verifier from {VERIFIER_PATH}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

load_json_strict = module.load_json_strict
verify_protocol = module.verify_protocol
verify_repository_contract = module.verify_repository_contract


class GeometryEvaluationProtocolTests(unittest.TestCase):
    def setUp(self):
        self.protocol = load_json_strict(PROTOCOL_PATH)

    def test_current_protocol_and_repository_contract_pass(self):
        result = verify_protocol(self.protocol)
        contract = verify_repository_contract(Path(".").resolve())
        self.assertTrue(result["valid"])
        self.assertTrue(contract["repository_contract_valid"])
        self.assertEqual(result["registered_experiment_count"], 0)
        self.assertEqual(result["experimentally_validated_result_count"], 0)
        self.assertFalse(result["universal_champion"])

    def test_unknown_top_level_key_rejected(self):
        protocol = copy.deepcopy(self.protocol)
        protocol["marketing_score"] = 100
        with self.assertRaisesRegex(ValueError, "top-level key mismatch"):
            verify_protocol(protocol)

    def test_duplicate_candidate_label_rejected(self):
        protocol = copy.deepcopy(self.protocol)
        protocol["zero_credit_candidate_labels"].append(
            protocol["zero_credit_candidate_labels"][0]
        )
        with self.assertRaisesRegex(ValueError, "duplicate values"):
            verify_protocol(protocol)

    def test_frobenius_cannot_be_reclassified_as_geometry(self):
        protocol = copy.deepcopy(self.protocol)
        protocol["geometry_models"].append("frobenius_series_local_solution_analysis")
        with self.assertRaisesRegex(ValueError, "geometry_models"):
            verify_protocol(protocol)

    def test_candidate_label_cannot_be_silently_removed(self):
        protocol = copy.deepcopy(self.protocol)
        protocol["zero_credit_candidate_labels"].remove("mycelium_inspired_network")
        with self.assertRaisesRegex(ValueError, "zero_credit_candidate_labels"):
            verify_protocol(protocol)

    def test_cross_lane_ranking_cannot_be_enabled(self):
        protocol = copy.deepcopy(self.protocol)
        protocol["comparison_rules"]["cross_lane_ranking_prohibited"] = False
        with self.assertRaisesRegex(ValueError, "comparison_rules"):
            verify_protocol(protocol)

    def test_secondary_metric_cannot_rescue_primary_failure(self):
        protocol = copy.deepcopy(self.protocol)
        protocol["comparison_rules"]["secondary_metrics_may_not_override_primary_failure"] = False
        with self.assertRaisesRegex(ValueError, "comparison_rules"):
            verify_protocol(protocol)

    def test_post_outcome_tuning_cannot_be_enabled(self):
        protocol = copy.deepcopy(self.protocol)
        protocol["comparison_rules"]["post_outcome_tuning_prohibited"] = False
        with self.assertRaisesRegex(ValueError, "comparison_rules"):
            verify_protocol(protocol)

    def test_universal_champion_rejected(self):
        protocol = copy.deepcopy(self.protocol)
        protocol["current_result_state"]["universal_champion"] = True
        with self.assertRaisesRegex(ValueError, "universal_champion"):
            verify_protocol(protocol)

    def test_unreviewed_experiment_count_rejected(self):
        protocol = copy.deepcopy(self.protocol)
        protocol["current_result_state"]["task_specific_experiments_registered"] = 1
        with self.assertRaisesRegex(ValueError, "must remain integer zero"):
            verify_protocol(protocol)

    def test_boolean_cannot_impersonate_zero_count(self):
        protocol = copy.deepcopy(self.protocol)
        protocol["current_result_state"]["experimentally_validated_results"] = False
        with self.assertRaisesRegex(ValueError, "must remain integer zero"):
            verify_protocol(protocol)

    def test_promotion_ladder_order_cannot_drift(self):
        protocol = copy.deepcopy(self.protocol)
        protocol["evidence_promotion"][0], protocol["evidence_promotion"][1] = (
            protocol["evidence_promotion"][1],
            protocol["evidence_promotion"][0],
        )
        with self.assertRaisesRegex(ValueError, "promotion order"):
            verify_protocol(protocol)

    def test_unknown_lane_model_rejected(self):
        protocol = copy.deepcopy(self.protocol)
        protocol["task_lanes"][0]["allowed_models"].append("sacred_geometry")
        with self.assertRaisesRegex(ValueError, "unknown geometry model"):
            verify_protocol(protocol)

    def test_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"schema_version":"1.0","schema_version":"1.0"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                load_json_strict(path)

    def test_non_finite_json_number_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nan.json"
            path.write_text('{"value":NaN}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-finite JSON number"):
                load_json_strict(path)

    def test_protocol_is_strict_json(self):
        encoded = json.dumps(self.protocol, sort_keys=True, allow_nan=False)
        self.assertGreater(len(encoded), 5000)


if __name__ == "__main__":
    unittest.main()
