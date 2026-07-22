import copy
import importlib.util
import json
import unittest
from pathlib import Path


VERIFIER_PATH = Path("code/ops/VERIFY_EVIDENCE_GRAPH.py")
GRAPH_PATH = Path("config/evidence_graph_v1.json")

spec = importlib.util.spec_from_file_location("verify_evidence_graph", VERIFIER_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"unable to load verifier from {VERIFIER_PATH}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
load_json_strict = module.load_json_strict
verify_graph = module.verify_graph


class EvidenceGraphTests(unittest.TestCase):
    def setUp(self):
        self.graph = load_json_strict(GRAPH_PATH)

    def test_current_graph_passes(self):
        result = verify_graph(self.graph)
        self.assertTrue(result["valid"])
        self.assertEqual(result["external_complete_count"], 0)
        self.assertEqual(result["field_validated_count"], 0)
        self.assertEqual(result["commercially_validated_count"], 0)

    def test_duplicate_node_rejected(self):
        graph = copy.deepcopy(self.graph)
        graph["nodes"].append(copy.deepcopy(graph["nodes"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate node id"):
            verify_graph(graph)

    def test_unknown_edge_target_rejected(self):
        graph = copy.deepcopy(self.graph)
        graph["edges"].append({"from": "pr-34", "to": "missing", "relationship": "indexes"})
        with self.assertRaisesRegex(ValueError, "unknown node"):
            verify_graph(graph)

    def test_external_complete_requires_execution_support(self):
        graph = copy.deepcopy(self.graph)
        node = next(item for item in graph["nodes"] if item["id"] == "pr-64")
        node["state"] = "external_complete"
        with self.assertRaisesRegex(ValueError, "completed_external_execution"):
            verify_graph(graph)

    def test_pr64_cannot_be_silently_promoted(self):
        graph = copy.deepcopy(self.graph)
        node = next(item for item in graph["nodes"] if item["id"] == "pr-64")
        node["state"] = "first_party_reproduced"
        with self.assertRaisesRegex(ValueError, "PR #64"):
            verify_graph(graph)

    def test_echolock_stays_held_without_indexed_evidence(self):
        graph = copy.deepcopy(self.graph)
        node = next(item for item in graph["nodes"] if item["id"] == "echolock-pilot")
        node["supports"] = ["pilot_complete"]
        with self.assertRaisesRegex(ValueError, "EchoLock"):
            verify_graph(graph)

    def test_json_is_strict_and_serializable(self):
        encoded = json.dumps(self.graph, sort_keys=True, separators=(",", ":"))
        self.assertGreater(len(encoded), 1000)


if __name__ == "__main__":
    unittest.main()
