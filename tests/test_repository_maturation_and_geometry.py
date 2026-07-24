import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path


VERIFIER_PATH = Path("code/ops/VERIFY_REPOSITORY_MATURATION_AND_GEOMETRY.py")
AUDIT_PATH = Path("config/repository_maturation_audit_v1.json")
GEOMETRY_PATH = Path("config/geometry_evaluation_protocol_v1.json")

spec = importlib.util.spec_from_file_location(
    "verify_repository_maturation_and_geometry",
    VERIFIER_PATH,
)
if spec is None or spec.loader is None:
    raise RuntimeError(f"unable to load verifier from {VERIFIER_PATH}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

load_json_strict = module.load_json_strict
verify_audit = module.verify_audit
verify_geometry = module.verify_geometry
verify_docs = module.verify_docs


class RepositoryMaturationAndGeometryTests(unittest.TestCase):
    def setUp(self):
        self.audit = load_json_strict(AUDIT_PATH)
        self.geometry = load_json_strict(GEOMETRY_PATH)

    def test_current_audit_geometry_and_docs_pass(self):
        audit = verify_audit(self.audit)
        geometry = verify_geometry(self.geometry)
        docs = verify_docs(Path(".").resolve())
        self.assertTrue(audit["valid"])
        self.assertEqual(audit["observed_pr_count"], 58)
        self.assertEqual(audit["current_supported_maturity"], "level_3")
        self.assertTrue(geometry["valid"])
        self.assertEqual(geometry["experimentally_validated_results"], 0)
        self.assertFalse(geometry["universal_champion"])
        self.assertTrue(docs["valid"])

    def test_duplicate_pr_across_dispositions_rejected(self):
        audit = copy.deepcopy(self.audit)
        audit["dispositions"]["open_merge_candidate"].append(16)
        with self.assertRaisesRegex(ValueError, "multiple dispositions"):
            verify_audit(audit)

    def test_missing_observed_pr_rejected(self):
        audit = copy.deepcopy(self.audit)
        audit["dispositions"]["open_retire_now"].remove(16)
        with self.assertRaisesRegex(ValueError, "exactly cover"):
            verify_audit(audit)

    def test_unobserved_pr_in_disposition_rejected(self):
        audit = copy.deepcopy(self.audit)
        audit["dispositions"]["open_retire_now"].append(999)
        with self.assertRaisesRegex(ValueError, "exactly cover"):
            verify_audit(audit)

    def test_p0_route_finding_required(self):
        audit = copy.deepcopy(self.audit)
        audit["priority_findings"] = [
            item
            for item in audit["priority_findings"]
            if item["id"] != "p0-public-evidence-route"
        ]
        with self.assertRaisesRegex(ValueError, "P0 public evidence route"):
            verify_audit(audit)

    def test_p0_route_preserves_502_fact(self):
        audit = copy.deepcopy(self.audit)
        finding = next(
            item
            for item in audit["priority_findings"]
            if item["id"] == "p0-public-evidence-route"
        )
        finding["finding"] = "The route needs attention."
        finding["required_action"] = "Review it."
        with self.assertRaisesRegex(ValueError, "HTTP 502 fact"):
            verify_audit(audit)

    def test_maturity_cannot_be_self_promoted(self):
        audit = copy.deepcopy(self.audit)
        audit["current_supported_maturity"] = "level_4"
        with self.assertRaisesRegex(ValueError, "must remain level_3"):
            verify_audit(audit)

    def test_false_claim_cannot_be_removed(self):
        audit = copy.deepcopy(self.audit)
        audit["current_false_claims"].remove("field_validation_complete")
        with self.assertRaisesRegex(ValueError, "false-claim registry drift"):
            verify_audit(audit)

    def test_duplicate_merge_program_pr_rejected(self):
        audit = copy.deepcopy(self.audit)
        audit["merge_program"][1]["pull_requests"].append(69)
        with self.assertRaisesRegex(ValueError, "multiple merge-program"):
            verify_audit(audit)

    def test_merge_order_gap_rejected(self):
        audit = copy.deepcopy(self.audit)
        audit["merge_program"][7]["order"] = 9
        with self.assertRaisesRegex(ValueError, "exactly cover 1 through 8"):
            verify_audit(audit)

    def test_geometry_requires_units_and_curvature(self):
        protocol = copy.deepcopy(self.geometry)
        protocol["required_declarations"].remove("units_for_every_physical_quantity")
        protocol["required_declarations"].remove("curvature_sign_and_convention")
        with self.assertRaisesRegex(ValueError, "missing units, coordinates, metric, curvature"):
            verify_geometry(protocol)

    def test_geometry_requires_plain_and_null_baselines(self):
        protocol = copy.deepcopy(self.geometry)
        protocol["required_baselines"].remove("straight_or_plain_euclidean_baseline")
        with self.assertRaisesRegex(ValueError, "baseline registry drift"):
            verify_geometry(protocol)

    def test_universal_geometry_champion_rejected(self):
        protocol = copy.deepcopy(self.geometry)
        protocol["comparison_rules"]["universal_champion_allowed"] = True
        with self.assertRaisesRegex(ValueError, "universal geometry champion"):
            verify_geometry(protocol)

    def test_experimental_validation_requires_external_record(self):
        protocol = copy.deepcopy(self.geometry)
        protocol["claim_level_requirements"]["experimentally_validated"].remove(
            "independent_or_external_execution_record"
        )
        with self.assertRaisesRegex(ValueError, "external execution record"):
            verify_geometry(protocol)

    def test_unknown_geometry_model_rejected(self):
        protocol = copy.deepcopy(self.geometry)
        protocol["task_lanes"][0]["allowed_models"].append("mystical_geometry")
        with self.assertRaisesRegex(ValueError, "unknown geometry model"):
            verify_geometry(protocol)

    def test_protocol_cannot_claim_adoption_or_results(self):
        protocol = copy.deepcopy(self.geometry)
        protocol["current_result_state"]["protocol_adopted"] = True
        with self.assertRaisesRegex(ValueError, "cannot claim adoption"):
            verify_geometry(protocol)

    def test_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"schema_version":"1.0","schema_version":"1.0"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                load_json_strict(path)

    def test_non_finite_json_number_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nonfinite.json"
            path.write_text('{"value":NaN}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-finite JSON number"):
                load_json_strict(path)


if __name__ == "__main__":
    unittest.main()
