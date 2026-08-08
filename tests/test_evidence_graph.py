import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


VERIFIER_PATH = Path("code/ops/VERIFY_EVIDENCE_GRAPH.py")
GRAPH_PATH = Path("config/evidence_graph_v1.json")

spec = importlib.util.spec_from_file_location(
    "verify_evidence_graph",
    VERIFIER_PATH,
)
if spec is None or spec.loader is None:
    raise RuntimeError(f"unable to load verifier from {VERIFIER_PATH}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

load_json_strict = module.load_json_strict
verify_graph = module.verify_graph
verify_repository_contract = module.verify_repository_contract


class EvidenceGraphTests(unittest.TestCase):
    def setUp(self):
        self.graph = load_json_strict(GRAPH_PATH)

    def test_current_graph_and_repository_contract_pass(self):
        result = verify_graph(self.graph)
        contract = verify_repository_contract(self.graph, Path(".").resolve())
        self.assertTrue(result["valid"])
        self.assertTrue(contract["repository_contract_valid"])
        self.assertEqual(result["external_complete_count"], 0)
        self.assertEqual(result["field_validated_count"], 0)
        self.assertEqual(result["commercially_validated_count"], 0)

    def test_duplicate_node_rejected(self):
        graph = copy.deepcopy(self.graph)
        graph["nodes"].append(copy.deepcopy(graph["nodes"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate node id"):
            verify_graph(graph)

    def test_duplicate_state_registry_entry_rejected(self):
        graph = copy.deepcopy(self.graph)
        graph["evidence_states"].append(graph["evidence_states"][0])
        with self.assertRaisesRegex(ValueError, "unique verifier state registry"):
            verify_graph(graph)

    def test_invalid_node_type_rejected(self):
        graph = copy.deepcopy(self.graph)
        graph["nodes"][0]["type"] = "marketing_claim"
        with self.assertRaisesRegex(ValueError, "invalid type"):
            verify_graph(graph)

    def test_boolean_pr_number_rejected(self):
        graph = copy.deepcopy(self.graph)
        node = next(item for item in graph["nodes"] if item["id"] == "pr-34")
        node["pr_number"] = True
        with self.assertRaisesRegex(ValueError, "positive integer pr_number"):
            verify_graph(graph)

    def test_merged_capability_requires_merged_true(self):
        graph = copy.deepcopy(self.graph)
        node = next(item for item in graph["nodes"] if item["id"] == "pr-34")
        node["merged"] = False
        with self.assertRaisesRegex(ValueError, "requires merged=true"):
            verify_graph(graph)

    def test_unknown_edge_target_rejected(self):
        graph = copy.deepcopy(self.graph)
        graph["edges"].append(
            {"from": "pr-34", "to": "missing", "relationship": "indexes"}
        )
        with self.assertRaisesRegex(ValueError, "unknown node"):
            verify_graph(graph)

    def test_self_referential_edge_rejected(self):
        graph = copy.deepcopy(self.graph)
        graph["edges"].append(
            {"from": "pr-34", "to": "pr-34", "relationship": "indexes"}
        )
        with self.assertRaisesRegex(ValueError, "self-referential"):
            verify_graph(graph)

    def test_external_complete_requires_full_execution_support(self):
        graph = copy.deepcopy(self.graph)
        node = next(item for item in graph["nodes"] if item["id"] == "pr-49")
        node["state"] = "external_complete"
        with self.assertRaisesRegex(ValueError, "missing required support"):
            verify_graph(graph)

    def test_field_validation_requires_field_support(self):
        graph = copy.deepcopy(self.graph)
        node = next(
            item for item in graph["nodes"] if item["id"] == "eia-frozen-benchmark"
        )
        node["state"] = "field_validated"
        with self.assertRaisesRegex(ValueError, "missing required support"):
            verify_graph(graph)

    def test_commercial_validation_requires_commercial_support(self):
        graph = copy.deepcopy(self.graph)
        node = next(
            item for item in graph["nodes"] if item["id"] == "eia-frozen-benchmark"
        )
        node["state"] = "commercially_validated"
        with self.assertRaisesRegex(ValueError, "missing required support"):
            verify_graph(graph)

    def test_pr74_cannot_be_silently_reclassified(self):
        graph = copy.deepcopy(self.graph)
        node = next(item for item in graph["nodes"] if item["id"] == "pr-74")
        node["state"] = "first_party_reproduced"
        with self.assertRaisesRegex(ValueError, "merged=true requires merged_capability"):
            verify_graph(graph)

    def test_current_pr_dispositions_are_explicit(self):
        nodes = {item["id"]: item for item in self.graph["nodes"]}

        for pr_number in (49, 52, 60, 64):
            node = nodes[f"pr-{pr_number}"]
            self.assertEqual(node["state"], "historical")
            self.assertFalse(node["merged"])

        for pr_number in (66, 67, 74, 98, 99, 100, 101, 131, 132):
            node = nodes[f"pr-{pr_number}"]
            self.assertEqual(node["state"], "merged_capability")
            self.assertTrue(node["merged"])

        self.assertFalse(
            any(
                node["state"]
                in {"external_execution_complete", "field_validated", "commercially_validated"}
                for node in nodes.values()
            )
        )

    def test_pr101_cannot_be_silently_reclassified(self):
        graph = copy.deepcopy(self.graph)
        node = next(item for item in graph["nodes"] if item["id"] == "pr-101")
        node["state"] = "historical"
        node["merged"] = False
        with self.assertRaisesRegex(ValueError, "PR #101"):
            verify_graph(graph)

    def test_current_offer_cannot_be_silently_reclassified(self):
        graph = copy.deepcopy(self.graph)
        node = next(item for item in graph["nodes"] if item["id"] == "pr-131")
        node["state"] = "historical"
        node["merged"] = False
        with self.assertRaisesRegex(ValueError, "PR #131"):
            verify_graph(graph)

    def test_current_offer_must_remain_single(self):
        graph = copy.deepcopy(self.graph)
        node = next(item for item in graph["nodes"] if item["id"] == "pr-131")
        node["supports"].remove("single_primary_offer")
        with self.assertRaisesRegex(ValueError, "single-primary-offer"):
            verify_graph(graph)

    def test_current_portfolio_cannot_be_silently_reclassified(self):
        graph = copy.deepcopy(self.graph)
        node = next(item for item in graph["nodes"] if item["id"] == "pr-132")
        node["state"] = "historical"
        node["merged"] = False
        with self.assertRaisesRegex(ValueError, "PR #132"):
            verify_graph(graph)

    def test_current_portfolio_must_remain_one_platform_one_offer(self):
        graph = copy.deepcopy(self.graph)
        node = next(item for item in graph["nodes"] if item["id"] == "pr-132")
        node["supports"].remove("one_platform_one_offer_positioning")
        with self.assertRaisesRegex(ValueError, "one-platform-one-offer"):
            verify_graph(graph)

    def test_echolock_stays_held_without_indexed_evidence(self):
        graph = copy.deepcopy(self.graph)
        node = next(
            item for item in graph["nodes"] if item["id"] == "echolock-pilot"
        )
        node["supports"] = ["pilot_complete"]
        with self.assertRaisesRegex(ValueError, "EchoLock"):
            verify_graph(graph)

    def test_duplicate_promotion_rule_rejected(self):
        graph = copy.deepcopy(self.graph)
        graph["promotion_rules"].append(copy.deepcopy(graph["promotion_rules"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate promotion rule"):
            verify_graph(graph)

    def test_promotion_requirement_drift_rejected(self):
        graph = copy.deepcopy(self.graph)
        graph["promotion_rules"][0]["requires"].append("invented_gate")
        with self.assertRaisesRegex(ValueError, "requirements drift"):
            verify_graph(graph)

    def test_strict_loader_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text(
                '{"schema_version":"1.0","schema_version":"1.0"}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                load_json_strict(path)

    def test_strict_loader_rejects_non_finite_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nan.json"
            path.write_text('{"value":NaN}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-finite JSON number"):
                load_json_strict(path)

    def test_repository_contract_requires_documented_graph_prs(self):
        graph = copy.deepcopy(self.graph)
        graph["nodes"].append(
            {
                "id": "pr-999",
                "type": "pull_request",
                "title": "Undocumented review lane",
                "pr_number": 999,
                "state": "held",
                "merged": False,
                "supports": [],
                "does_not_support": ["canonical_status"],
            }
        )
        with self.assertRaisesRegex(ValueError, "omit graph PRs"):
            verify_repository_contract(graph, Path(".").resolve())

    def test_repository_contract_requires_full_human_state_legend(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / "README.md").write_text(
                Path("README.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (root / "EVIDENCE_INDEX.md").write_text(
                Path("EVIDENCE_INDEX.md")
                .read_text(encoding="utf-8")
                .replace("| **HISTORICAL** |", "| **PAST RECORD** |"),
                encoding="utf-8",
            )
            (root / "docs" / "PR_CONSOLIDATION_MAP_2026-07-22.md").write_text(
                Path("docs/PR_CONSOLIDATION_MAP_2026-07-22.md").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "evidence-state markers"):
                verify_repository_contract(self.graph, root)

    def test_repository_contract_scopes_state_markers_to_legend_table(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / "README.md").write_text(
                Path("README.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (root / "EVIDENCE_INDEX.md").write_text(
                Path("EVIDENCE_INDEX.md")
                .read_text(encoding="utf-8")
                .replace(
                    "| **MERGED** | Present on the default branch. |\n",
                    "",
                    1,
                ),
                encoding="utf-8",
            )
            (root / "docs" / "PR_CONSOLIDATION_MAP_2026-07-22.md").write_text(
                Path("docs/PR_CONSOLIDATION_MAP_2026-07-22.md").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "evidence-state markers"):
                verify_repository_contract(self.graph, root)

    def test_json_is_strict_and_serializable(self):
        encoded = json.dumps(
            self.graph,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        self.assertGreater(len(encoded), 1000)


if __name__ == "__main__":
    unittest.main()
