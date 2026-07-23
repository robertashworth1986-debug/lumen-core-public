#!/usr/bin/env python3
"""Fail-closed verifier for the canonical LumenCore evidence graph."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any

EXPECTED_REPOSITORY = "robertashworth1986-debug/lumen-core-public"
MAX_GRAPH_BYTES = 2_000_000

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

ALLOWED_NODE_TYPES = {
    "pull_request",
    "evidence_package",
    "deployed_system",
    "pilot_record",
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

PROMOTION_REQUIREMENTS = {
    ("first_party_reproduced", "externally_executable"): {
        "pinned_source",
        "pinned_environment",
        "manifest",
        "reviewer_instructions",
        "blank_external_receipt",
        "claim_boundary",
    },
    ("externally_executable", "external_complete"): {
        "named_non_author_evaluator",
        "independence_disclosure",
        "reviewer_controlled_execution",
        "completed_receipt",
        "ordered_output_hashes",
        "deviations",
        "negative_results",
        "timestamp_order",
    },
    ("external_complete", "field_validated"): {
        "authorized_field_data_owner",
        "field_protocol",
        "accepted_baseline",
        "locked_metric",
        "operational_window",
        "field_result",
        "limitations",
        "external_acceptance_record",
    },
    ("field_validated", "commercially_validated"): {
        "signed_scope_or_purchase_record",
        "buyer_identity_or_private_custody_receipt",
        "delivered_result",
        "payment_or_contract_evidence",
        "publicity_rights_if_named",
    },
}

STATE_REQUIRED_SUPPORTS = {
    "external_complete": {
        "named_non_author_evaluator",
        "independence_disclosure",
        "reviewer_controlled_execution",
        "completed_external_execution",
        "completed_receipt",
        "ordered_output_hashes",
        "deviations",
        "negative_results",
        "timestamp_order",
    },
    "field_validated": PROMOTION_REQUIREMENTS[("external_complete", "field_validated")],
    "commercially_validated": PROMOTION_REQUIREMENTS[
        ("field_validated", "commercially_validated")
    ],
}

REQUIRED_NODE_FIELDS = {
    "id",
    "type",
    "title",
    "state",
    "supports",
    "does_not_support",
}

NODE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PR_REFERENCE_RE = re.compile(r"(?:/pull/|#)(\d+)")
HUMAN_STATE_MARKERS = {
    "merged_capability": "**MERGED**",
    "deployed_demo": "**DEPLOYED DEMO**",
    "first_party_reproduced": "**FIRST-PARTY REPRODUCED**",
    "externally_executable": "**EXTERNALLY EXECUTABLE**",
    "external_complete": "**EXTERNAL COMPLETE**",
    "field_validated": "**FIELD VALIDATED**",
    "commercially_validated": "**COMMERCIALLY VALIDATED**",
    "held": "**HELD**",
    "historical": "**HISTORICAL**",
}
EVIDENCE_LEGEND_HEADING = "## Evidence-state legend"
MARKDOWN_H2_RE = re.compile(r"^##\s+", re.MULTILINE)
LEGEND_STATE_ROW_RE = re.compile(r"^\|\s*(\*\*[^|\n]+\*\*)\s*\|", re.MULTILINE)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


def load_json_strict(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > MAX_GRAPH_BYTES:
        raise ValueError(f"graph exceeds maximum size of {MAX_GRAPH_BYTES} bytes")
    text = raw.decode("utf-8")
    value = json.loads(
        text,
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_non_finite,
    )
    if not isinstance(value, dict):
        raise ValueError("graph root must be an object")
    return value


def require_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def require_string_list(
    node: dict[str, Any],
    field: str,
    *,
    allow_empty: bool = True,
) -> list[str]:
    value = node.get(field)
    if not isinstance(value, list):
        raise ValueError(
            f"node {node.get('id')}: {field} must be a list of non-empty strings"
        )
    if not allow_empty and not value:
        raise ValueError(f"node {node.get('id')}: {field} must not be empty")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(
            f"node {node.get('id')}: {field} must be a list of non-empty strings"
        )
    if len(value) != len(set(value)):
        raise ValueError(f"node {node.get('id')}: duplicate values in {field}")
    return value


def parse_utc_timestamp(value: Any) -> str:
    timestamp = require_non_empty_string(value, "generated_utc")
    if not timestamp.endswith("Z"):
        raise ValueError("generated_utc must be an RFC3339 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(timestamp[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("generated_utc must be a valid RFC3339 UTC timestamp") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("generated_utc must use UTC")
    return timestamp


def verify_graph(graph: dict[str, Any]) -> dict[str, Any]:
    if graph.get("schema_version") != "1.0":
        raise ValueError("unsupported schema_version")
    if graph.get("repository") != EXPECTED_REPOSITORY:
        raise ValueError("repository identity mismatch")
    parse_utc_timestamp(graph.get("generated_utc"))
    require_non_empty_string(graph.get("purpose"), "purpose")
    require_non_empty_string(graph.get("claim_rule"), "claim_rule")

    declared_states = graph.get("evidence_states")
    if (
        not isinstance(declared_states, list)
        or len(declared_states) != len(ALLOWED_STATES)
        or len(declared_states) != len(set(declared_states))
        or set(declared_states) != ALLOWED_STATES
    ):
        raise ValueError(
            "evidence_states must exactly match the unique verifier state registry"
        )

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

        node_id = require_non_empty_string(raw_node["id"], "node id")
        if not NODE_ID_RE.fullmatch(node_id):
            raise ValueError(f"node {node_id}: id must use lowercase kebab-case")
        if node_id in by_id:
            raise ValueError(f"duplicate node id: {node_id}")

        node_type = require_non_empty_string(raw_node["type"], f"node {node_id}: type")
        if node_type not in ALLOWED_NODE_TYPES:
            raise ValueError(f"node {node_id}: invalid type {node_type}")

        require_non_empty_string(raw_node["title"], f"node {node_id}: title")

        state = raw_node["state"]
        if not isinstance(state, str) or state not in ALLOWED_STATES:
            raise ValueError(f"node {node_id}: invalid state {state!r}")

        supports = require_string_list(raw_node, "supports")
        does_not_support = require_string_list(
            raw_node, "does_not_support", allow_empty=False
        )
        overlap = set(supports) & set(does_not_support)
        if overlap:
            raise ValueError(
                f"node {node_id}: contradictory support boundary {sorted(overlap)}"
            )

        for optional_field in (
            "files_of_interest",
            "negative_results",
            "missing_for_promotion",
        ):
            if optional_field in raw_node:
                require_string_list(raw_node, optional_field, allow_empty=False)

        if "canonical_role" in raw_node:
            require_non_empty_string(
                raw_node["canonical_role"], f"node {node_id}: canonical_role"
            )

        required_supports = STATE_REQUIRED_SUPPORTS.get(state, set())
        missing_supports = required_supports - set(supports)
        if missing_supports:
            raise ValueError(
                f"node {node_id}: state {state} is missing required support "
                f"{sorted(missing_supports)}"
            )

        if node_type == "pull_request":
            number = raw_node.get("pr_number")
            if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
                raise ValueError(
                    f"node {node_id}: pull_request requires positive integer pr_number"
                )
            if node_id != f"pr-{number}":
                raise ValueError(f"node {node_id}: pull_request id must equal pr-{number}")
            if number in pr_numbers:
                raise ValueError(f"duplicate pr_number: {number}")
            pr_numbers.add(number)

            merged = raw_node.get("merged")
            if not isinstance(merged, bool):
                raise ValueError(f"node {node_id}: pull_request requires boolean merged")
            if state == "merged_capability" and not merged:
                raise ValueError(f"node {node_id}: merged_capability requires merged=true")
            if merged and state != "merged_capability":
                raise ValueError(
                    f"node {node_id}: merged=true requires merged_capability state"
                )

        by_id[node_id] = raw_node

    edge_keys: set[tuple[str, str, str]] = set()
    for edge in edges:
        if not isinstance(edge, dict):
            raise ValueError("every edge must be an object")
        source = edge.get("from")
        target = edge.get("to")
        relationship = edge.get("relationship")
        if not isinstance(source, str) or not isinstance(target, str):
            raise ValueError("edge endpoints must be node-id strings")
        if source not in by_id or target not in by_id:
            raise ValueError(f"edge references unknown node: {source} -> {target}")
        if source == target:
            raise ValueError(f"self-referential edge is not allowed: {source}")
        if not isinstance(relationship, str) or relationship not in ALLOWED_RELATIONSHIPS:
            raise ValueError(f"invalid relationship: {relationship}")
        key = (source, target, relationship)
        if key in edge_keys:
            raise ValueError(f"duplicate edge: {key}")
        edge_keys.add(key)

    observed_rules: dict[tuple[str, str], set[str]] = {}
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError("promotion rule must be an object")
        source_state = rule.get("from")
        target_state = rule.get("to")
        if source_state not in ALLOWED_STATES or target_state not in ALLOWED_STATES:
            raise ValueError("promotion rule references invalid state")
        if source_state == target_state:
            raise ValueError("promotion rule cannot be self-referential")
        requires = rule.get("requires")
        if (
            not isinstance(requires, list)
            or not requires
            or any(not isinstance(item, str) or not item.strip() for item in requires)
            or len(requires) != len(set(requires))
        ):
            raise ValueError("promotion rule requires a unique non-empty string list")
        key = (source_state, target_state)
        if key in observed_rules:
            raise ValueError(f"duplicate promotion rule: {key}")
        observed_rules[key] = set(requires)

    if set(observed_rules) != set(PROMOTION_REQUIREMENTS):
        raise ValueError("promotion rule transitions do not match the canonical registry")
    for key, expected in PROMOTION_REQUIREMENTS.items():
        if observed_rules[key] != expected:
            raise ValueError(
                f"promotion rule requirements drift for {key[0]} -> {key[1]}"
            )

    if "pr-34" not in by_id or by_id["pr-34"]["state"] != "merged_capability":
        raise ValueError(
            "PR #34 must remain represented as the merged assurance foundation"
        )
    if "pr-64" not in by_id or by_id["pr-64"]["state"] != "externally_executable":
        raise ValueError(
            "PR #64 must remain externally executable, not externally complete"
        )

    echolock = by_id.get("echolock-pilot")
    if (
        echolock is None
        or echolock["state"] != "held"
        or echolock["supports"]
        or not echolock.get("missing_for_promotion")
    ):
        raise ValueError(
            "EchoLock must remain held with no supported pilot claim until "
            "discoverable promotion evidence is indexed"
        )

    external_complete = [
        node for node in nodes if node["state"] == "external_complete"
    ]
    return {
        "valid": True,
        "schema_version": graph["schema_version"],
        "generated_utc": graph["generated_utc"],
        "node_count": len(nodes),
        "edge_count": len(edges),
        "pull_request_count": len(pr_numbers),
        "external_complete_count": len(external_complete),
        "field_validated_count": sum(
            node["state"] == "field_validated" for node in nodes
        ),
        "commercially_validated_count": sum(
            node["state"] == "commercially_validated" for node in nodes
        ),
    }


def verify_repository_contract(
    graph: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    readme_path = root / "README.md"
    index_path = root / "EVIDENCE_INDEX.md"
    map_path = root / "docs" / "PR_CONSOLIDATION_MAP_2026-07-22.md"

    readme = readme_path.read_text(encoding="utf-8")
    index = index_path.read_text(encoding="utf-8")
    consolidation = map_path.read_text(encoding="utf-8")

    required_readme_link = "[Open the Canonical Evidence Index](EVIDENCE_INDEX.md)"
    if required_readme_link not in readme:
        raise ValueError("README must expose the canonical evidence index first")

    for required_path in (
        "config/evidence_graph_v1.json",
        "code/ops/VERIFY_EVIDENCE_GRAPH.py",
        "docs/MACHINE_EVIDENCE_GRAPH.md",
    ):
        if required_path not in index:
            raise ValueError(
                f"EVIDENCE_INDEX.md is missing machine entrypoint {required_path}"
            )

    legend_start = index.find(EVIDENCE_LEGEND_HEADING)
    if legend_start < 0:
        raise ValueError("EVIDENCE_INDEX.md omits the evidence-state legend")
    legend_line_end = index.find("\n", legend_start)
    if legend_line_end < 0:
        raise ValueError("EVIDENCE_INDEX.md evidence-state legend has no table")
    legend_tail = index[legend_line_end + 1 :]
    next_heading = MARKDOWN_H2_RE.search(legend_tail)
    legend = legend_tail[: next_heading.start()] if next_heading else legend_tail
    legend_markers = LEGEND_STATE_ROW_RE.findall(legend)
    marker_counts = {
        marker: legend_markers.count(marker)
        for marker in set(legend_markers)
    }
    expected_markers = set(HUMAN_STATE_MARKERS.values())
    missing_state_markers = sorted(expected_markers - set(legend_markers))
    unexpected_state_markers = sorted(set(legend_markers) - expected_markers)
    duplicate_state_markers = sorted(
        marker for marker, count in marker_counts.items() if count != 1
    )
    if (
        missing_state_markers
        or unexpected_state_markers
        or duplicate_state_markers
    ):
        raise ValueError(
            "EVIDENCE_INDEX.md evidence-state markers do not match the machine registry: "
            f"missing={missing_state_markers}, "
            f"unexpected={unexpected_state_markers}, "
            f"duplicates={duplicate_state_markers}"
        )

    graph_pr_numbers = {
        node["pr_number"]
        for node in graph["nodes"]
        if node.get("type") == "pull_request"
    }
    documented_pr_numbers = {
        int(match)
        for match in PR_REFERENCE_RE.findall(index + "\n" + consolidation)
    }
    missing = graph_pr_numbers - documented_pr_numbers
    if missing:
        raise ValueError(f"PR consolidation documents omit graph PRs: {sorted(missing)}")

    return {
        "repository_contract_valid": True,
        "documented_pull_request_count": len(
            graph_pr_numbers & documented_pr_numbers
        ),
        "readme_entrypoint": "EVIDENCE_INDEX.md",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        default="config/evidence_graph_v1.json",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root used for the human/machine navigation contract",
    )
    parser.add_argument(
        "--skip-repository-contract",
        action="store_true",
        help="Verify only the graph file, without repository navigation files",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable verification result",
    )
    args = parser.parse_args()

    try:
        graph = load_json_strict(Path(args.path))
        result = verify_graph(graph)
        if not args.skip_repository_contract:
            result.update(
                verify_repository_contract(graph, Path(args.root).resolve())
            )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        failure = {"valid": False, "error": str(exc)}
        print(json.dumps(failure, sort_keys=True) if args.json else f"FAIL: {exc}")
        return 1

    print(json.dumps(result, sort_keys=True) if args.json else f"PASS: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
