#!/usr/bin/env python3
"""Verify a bounded post-merge correction overlay for the evidence graph."""

from __future__ import annotations

import argparse
import copy
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

EXPECTED_REPOSITORY = "robertashworth1986-debug/lumen-core-public"
MAX_JSON_BYTES = 2_000_000
REQUIRED_BOUNDARIES = {
    "no_external_validation_promotion",
    "no_submission_claim",
    "no_selection_or_award_claim",
    "no_funding_or_contract_claim",
    "no_sale_or_valuation_claim",
    "no_automatic_merge_authorization",
}


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_non_finite(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


def read_json_strict(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError(f"JSON exceeds maximum size of {MAX_JSON_BYTES} bytes")
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_non_finite,
    )
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value, raw


def git_blob_sha(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def require_utc(value: Any) -> str:
    timestamp = require_string(value, "generated_utc")
    if not timestamp.endswith("Z"):
        raise ValueError("generated_utc must end in Z")
    try:
        parsed = datetime.fromisoformat(timestamp[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("generated_utc must be valid RFC3339 UTC") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("generated_utc must use UTC")
    return timestamp


def require_unique_strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{label} must contain non-empty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} contains duplicates")
    return value


def load_canonical_verifier(path: Path):
    spec = importlib.util.spec_from_file_location("canonical_evidence_verifier", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load canonical verifier from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_overlay(
    overlay: dict[str, Any],
    base_graph: dict[str, Any],
    base_graph_raw: bytes,
    canonical_verifier_path: Path,
) -> dict[str, Any]:
    required_top = {
        "schema_version",
        "generated_utc",
        "repository",
        "base_graph_path",
        "base_graph_blob_sha",
        "purpose",
        "corrections",
        "documentation_gap",
        "claim_boundaries",
    }
    if set(overlay) != required_top:
        raise ValueError("overlay top-level fields mismatch")
    if overlay["schema_version"] != "1.0":
        raise ValueError("unsupported schema_version")
    require_utc(overlay["generated_utc"])
    if overlay["repository"] != EXPECTED_REPOSITORY:
        raise ValueError("repository identity mismatch")
    if overlay["base_graph_path"] != "config/evidence_graph_v1.json":
        raise ValueError("base_graph_path mismatch")
    if overlay["base_graph_blob_sha"] != git_blob_sha(base_graph_raw):
        raise ValueError("base graph blob identity drift")
    require_string(overlay["purpose"], "purpose")

    boundaries = set(require_unique_strings(overlay["claim_boundaries"], "claim_boundaries"))
    if boundaries != REQUIRED_BOUNDARIES:
        raise ValueError("claim boundaries do not match the canonical overlay boundary")

    documentation_gap = overlay["documentation_gap"]
    if not isinstance(documentation_gap, dict) or set(documentation_gap) != {
        "present",
        "missing_paths",
        "rule",
    }:
        raise ValueError("documentation_gap fields mismatch")
    if documentation_gap["present"] is not True:
        raise ValueError("documentation gap must remain explicit until canonical reconciliation")
    required_missing = {
        "EVIDENCE_INDEX.md",
        "docs/PR_CONSOLIDATION_MAP_2026-07-22.md",
    }
    if set(require_unique_strings(documentation_gap["missing_paths"], "missing_paths")) != required_missing:
        raise ValueError("documentation gap paths mismatch")
    require_string(documentation_gap["rule"], "documentation gap rule")

    nodes = base_graph.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("base graph nodes must be a list")
    effective = copy.deepcopy(base_graph)
    effective_nodes = effective["nodes"]
    by_id = {
        node.get("id"): node
        for node in effective_nodes
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }

    corrections = overlay["corrections"]
    if not isinstance(corrections, list) or len(corrections) != 2:
        raise ValueError("exactly two post-merge corrections are required")

    seen: set[str] = set()
    for correction in corrections:
        if not isinstance(correction, dict):
            raise ValueError("each correction must be an object")
        node_id = require_string(correction.get("node_id"), "correction node_id")
        if node_id in seen:
            raise ValueError(f"duplicate correction: {node_id}")
        seen.add(node_id)
        operation = correction.get("operation")

        if node_id == "pr-66":
            if operation != "replace" or set(correction) != {
                "node_id",
                "operation",
                "expected_before",
                "after",
            }:
                raise ValueError("PR #66 correction contract mismatch")
            node = by_id.get(node_id)
            if node is None:
                raise ValueError("PR #66 is missing from the base graph")
            expected = correction["expected_before"]
            if expected != {"state": "held", "merged": False}:
                raise ValueError("PR #66 expected-before state mismatch")
            for key, expected_value in expected.items():
                if node.get(key) != expected_value:
                    raise ValueError("PR #66 base state no longer matches overlay precondition")
            after = correction["after"]
            if after != {"state": "merged_capability", "merged": True}:
                raise ValueError("PR #66 corrected state mismatch")
            node.update(after)

        elif node_id == "pr-67":
            if operation != "add" or set(correction) != {"node_id", "operation", "after"}:
                raise ValueError("PR #67 correction contract mismatch")
            if node_id in by_id:
                raise ValueError("PR #67 already exists in the base graph")
            new_node = correction["after"]
            if not isinstance(new_node, dict) or new_node.get("id") != "pr-67":
                raise ValueError("PR #67 node payload mismatch")
            if new_node.get("state") != "merged_capability" or new_node.get("merged") is not True:
                raise ValueError("PR #67 must be represented as merged capability")
            forbidden_supports = {
                "proposal_submission",
                "selection",
                "award",
                "funding",
                "contract",
                "external_validation",
            }
            supports = set(new_node.get("supports", []))
            does_not_support = set(new_node.get("does_not_support", []))
            if supports & forbidden_supports:
                raise ValueError("PR #67 contains prohibited promoted support")
            if not forbidden_supports <= does_not_support:
                raise ValueError("PR #67 must retain all non-promotion boundaries")
            effective_nodes.append(copy.deepcopy(new_node))
            by_id[node_id] = effective_nodes[-1]
        else:
            raise ValueError(f"unexpected correction target: {node_id}")

    if seen != {"pr-66", "pr-67"}:
        raise ValueError("overlay correction targets mismatch")

    verifier = load_canonical_verifier(canonical_verifier_path)
    graph_result = verifier.verify_graph(effective)
    return {
        "valid": True,
        "overlay_status": "verified_noncanonical_post_merge_correction",
        "base_graph_blob_sha": overlay["base_graph_blob_sha"],
        "effective_pull_request_count": graph_result["pull_request_count"],
        "pr_66_merged": by_id["pr-66"]["merged"],
        "pr_67_merged": by_id["pr-67"]["merged"],
        "documentation_gap_present": documentation_gap["present"],
        "canonical_ready": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "overlay",
        nargs="?",
        default="config/evidence_graph_post_merge_overlay_v1.json",
    )
    parser.add_argument(
        "--base-graph",
        default="config/evidence_graph_v1.json",
    )
    parser.add_argument(
        "--canonical-verifier",
        default="code/ops/VERIFY_EVIDENCE_GRAPH.py",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        overlay, _ = read_json_strict(Path(args.overlay))
        base_graph, base_raw = read_json_strict(Path(args.base_graph))
        result = verify_overlay(
            overlay,
            base_graph,
            base_raw,
            Path(args.canonical_verifier),
        )
    except (OSError, UnicodeError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        failure = {"valid": False, "error": str(exc)}
        print(json.dumps(failure, sort_keys=True) if args.json else f"FAIL: {exc}")
        return 1

    print(json.dumps(result, sort_keys=True) if args.json else f"PASS: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
