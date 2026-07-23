import copy
import importlib.util
import unittest
from pathlib import Path


VERIFIER_PATH = Path("code/ops/VERIFY_EVIDENCE_GRAPH_OVERLAY.py")
OVERLAY_PATH = Path("config/evidence_graph_post_merge_overlay_v1.json")
BASE_GRAPH_PATH = Path("config/evidence_graph_v1.json")
CANONICAL_VERIFIER_PATH = Path("code/ops/VERIFY_EVIDENCE_GRAPH.py")

spec = importlib.util.spec_from_file_location("verify_evidence_graph_overlay", VERIFIER_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"unable to load verifier from {VERIFIER_PATH}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

read_json_strict = module.read_json_strict
verify_overlay = module.verify_overlay


class EvidenceGraphOverlayTests(unittest.TestCase):
    def setUp(self):
        self.overlay, _ = read_json_strict(OVERLAY_PATH)
        self.graph, self.graph_raw = read_json_strict(BASE_GRAPH_PATH)

    def verify(self, overlay=None, graph=None, raw=None):
        return verify_overlay(
            overlay if overlay is not None else self.overlay,
            graph if graph is not None else self.graph,
            raw if raw is not None else self.graph_raw,
            CANONICAL_VERIFIER_PATH,
        )

    def test_current_overlay_passes_but_is_not_canonical_ready(self):
        result = self.verify()
        self.assertTrue(result["valid"])
        self.assertTrue(result["pr_66_merged"])
        self.assertTrue(result["pr_67_merged"])
        self.assertTrue(result["documentation_gap_present"])
        self.assertFalse(result["canonical_ready"])

    def test_base_graph_blob_drift_rejected(self):
        overlay = copy.deepcopy(self.overlay)
        overlay["base_graph_blob_sha"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "blob identity drift"):
            self.verify(overlay=overlay)

    def test_pr66_precondition_drift_rejected(self):
        graph = copy.deepcopy(self.graph)
        node = next(item for item in graph["nodes"] if item["id"] == "pr-66")
        node["merged"] = True
        with self.assertRaisesRegex(ValueError, "base state no longer matches"):
            self.verify(graph=graph)

    def test_pr66_cannot_remain_held(self):
        overlay = copy.deepcopy(self.overlay)
        correction = next(item for item in overlay["corrections"] if item["node_id"] == "pr-66")
        correction["after"]["state"] = "held"
        with self.assertRaisesRegex(ValueError, "corrected state mismatch"):
            self.verify(overlay=overlay)

    def test_pr67_must_be_merged_capability(self):
        overlay = copy.deepcopy(self.overlay)
        correction = next(item for item in overlay["corrections"] if item["node_id"] == "pr-67")
        correction["after"]["state"] = "held"
        correction["after"]["merged"] = False
        with self.assertRaisesRegex(ValueError, "merged capability"):
            self.verify(overlay=overlay)

    def test_pr67_cannot_promote_funding(self):
        overlay = copy.deepcopy(self.overlay)
        correction = next(item for item in overlay["corrections"] if item["node_id"] == "pr-67")
        correction["after"]["supports"].append("funding")
        with self.assertRaisesRegex(ValueError, "prohibited promoted support"):
            self.verify(overlay=overlay)

    def test_pr67_must_retain_nonpromotion_boundaries(self):
        overlay = copy.deepcopy(self.overlay)
        correction = next(item for item in overlay["corrections"] if item["node_id"] == "pr-67")
        correction["after"]["does_not_support"].remove("external_validation")
        with self.assertRaisesRegex(ValueError, "retain all non-promotion boundaries"):
            self.verify(overlay=overlay)

    def test_documentation_gap_cannot_be_silently_closed(self):
        overlay = copy.deepcopy(self.overlay)
        overlay["documentation_gap"]["present"] = False
        with self.assertRaisesRegex(ValueError, "must remain explicit"):
            self.verify(overlay=overlay)

    def test_claim_boundary_drift_rejected(self):
        overlay = copy.deepcopy(self.overlay)
        overlay["claim_boundaries"].remove("no_sale_or_valuation_claim")
        with self.assertRaisesRegex(ValueError, "claim boundaries"):
            self.verify(overlay=overlay)

    def test_duplicate_correction_rejected(self):
        overlay = copy.deepcopy(self.overlay)
        overlay["corrections"][1]["node_id"] = "pr-66"
        with self.assertRaisesRegex(ValueError, "duplicate correction"):
            self.verify(overlay=overlay)


if __name__ == "__main__":
    unittest.main()
