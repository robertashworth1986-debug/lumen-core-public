#!/usr/bin/env python3
"""Fail-closed verifier for config/evidence_graph_v1.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ALLOWED_STATES = {
    "merged_capability",
    "deployed_demo",
    "first_party_reproduced",
    "externally_executable",
    "external_complete",
    "field_validated",
    "commercially_validated",
    "held",
    "historical",
}

ALLOWED_RELATIONSHIPS = {
    "proposed_successor",
    "assurance_foundation_for",
    "stacked_parent",
    "consolidated_into",
    "complements_external_execution",
    "packages",
    "mainline_candidate_for",
    "deploys",
    "commercially_uses",
    "presents",
    "portability_dependency_for_related_route_tests",
    "indexes",
    "holds_until_discoverable",
}

REQUIRED_NODE_FIELDS = {
    "id",
    "type",
    "title",
    "state",
    "supports",
    "does_not_support",
}


def load_json_strict(path: Path) -> dict[str, Any]:
    def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle, object_pairs_hook=reject_duplicate)
    if not isinstance(value, dict):
        raise ValueError("graph root must be an object")
    return value


def require_string_list(node: dict[str, Any], field: str) -> None:
    value = node.get(field)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"node {node.get('id')}: {field} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"node {node.get('id')}: duplicate values in {field}")


def verify_graph(graph: dict[str, Any]) -> dict[str, Any]:
    if graph.get("schema_version") != "1.0":
        raise ValueError("unsupported schema_version")

    declared_states = graph.get("evidence_states")
    if not isinstance(declared_states, list) or set(declared_states) != ALLOWED_STATES:
        raise ValueError("evidence_states must exactly match the verifier state registry")

    nodes = graph.get("nodes")
    edges = graph.get("edges")
    rules = graph.get("promotion_rules")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("nodes must be a non-empty list")
    if not isinstance(edges, list):
        raise ValueError("edges must be a list")
    if not isinstance(rules, list) or not rules:
        raise ValueError("promotion_rules must be a non-empty list")

    by_id: dict[str, dict[str, Any]] = {}
    pr_numbers: set[int] = set()
    for raw_node in nodes:
        if not isinstance(raw_node, dict):
            raise ValueError("every node must be an object")
        missing = REQUIRED_NODE_FIELDS - raw_node.keys()
        if missing:
            raise ValueError(f"node missing required fields: {sorted(missing)}")
        node_id = raw_node["id"]
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("node id must be a non-empty string")
        if node_id in by_id:
            raise ValueError(f"duplicate node id: {node_id}")
        if raw_node["state"] not in ALLOWED_STATES:
            raise ValueError(f"node {node_id}: invalid state {raw_node['state']}")
        require_string_list(raw_node, "supports")
        require_string_list(raw_node, "does_not_support")
        overlap = set(raw_node["supports"]) & set(raw_node["does_not_support"])
        if overlap:
            raise ValueError(f"node {node_id}: contradictory support boundary {sorted(overlap)}")
        if raw_node.get("type") == "pull_request":
            number = raw_node.get("pr_number")
            if not isinstance(number, int) or number <= 0:
                raise ValueError(f"node {node_id}: pull_request requires positive pr_number")
            if number in pr_numbers:
                raise ValueError(f"duplicate pr_number: {number}")
            pr_numbers.add(number)
        by_id[node_id] = raw_node

    edge_keys: set[tuple[str, str, str]] = set()
    for edge in edges:
        if not isinstance(edge, dict):
            raise ValueError("every edge must be an object")
        source = edge.get("from")
        target = edge.get("to")
        relationship = edge.get("relationship")
        if source not in by_id or target not in by_id:
            raise ValueError(f"edge references unknown node: {source} -> {target}")
        if relationship not in ALLOWED_RELATIONSHIPS:
            raise ValueError(f"invalid relationship: {relationship}")
        key = (source, target, relationship)
        if key in edge_keys:
            raise ValueError(f"duplicate edge: {key}")
        edge_keys.add(key)

    external_complete = [node for node in nodes if node["state"] == "external_complete"]
    for node in external_complete:
        if "completed_external_execution" not in node["supports"]:
            raise ValueError(f"node {node['id']}: external_complete requires completed_external_execution")

    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError("promotion rule must be an object")
        if rule.get("from") not in ALLOWED_STATES or rule.get("to") not in ALLOWED_STATES:
            raise ValueError("promotion rule references invalid state")
        requires = rule.get("requires")
        if not isinstance(requires, list) or not requires or any(not isinstance(item, str) for item in requires):
            raise ValueError("promotion rule requires a non-empty string list")

    if "pr-34" not in by_id or by_id["pr-34"]["state"] != "merged_capability":
        raise ValueError("PR #34 must remain represented as the merged assurance foundation")
    if "pr-64" not in by_id or by_id["pr-64"]["state"] != "externally_executable":
        raise ValueError("PR #64 must remain externally executable, not externally complete")
    if "echolock-pilot" not in by_id or by_id["echolock-pilot"]["supports"]:
        raise ValueError("EchoLock must remain held until discoverable evidence is indexed")

    return {
        "valid": True,
        "schema_version": graph["schema_version"],
        "node_count": len(nodes),
        "edge_count": len(edges),
        "pull_request_count": len(pr_numbers),
        "external_complete_count": len(external_complete),
        "field_validated_count": sum(node["state"] == "field_validated" for node in nodes),
        "commercially_validated_count": sum(node["state"] == "commercially_validated" for node in nodes),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="config/evidence_graph_v1.json")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable verification result")
    args = parser.parse_args()

    try:
        result = verify_graph(load_json_strict(Path(args.path)))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failure = {"valid": False, "error": str(exc)}
        print(json.dumps(failure, sort_keys=True) if args.json else f"FAIL: {exc}")
        return 1

    print(json.dumps(result, sort_keys=True) if args.json else f"PASS: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
