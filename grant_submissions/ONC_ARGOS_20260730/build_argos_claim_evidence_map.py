from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ARGOS_DIR = Path(__file__).resolve().parent
ROOT = ARGOS_DIR.parents[1]
DEFAULT_OUTPUT = ARGOS_DIR / "ARGOS_CLAIM_EVIDENCE_MAP_2026-07-27.json"

RESPONSE_MARKDOWN = ARGOS_DIR / "ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.md"
EVIDENCE_GRAPH = ROOT / "config" / "evidence_graph_v1.json"
EVIDENCE_INDEX = ROOT / "EVIDENCE_INDEX.md"
REVIEWER_RECEIPT = (
    ROOT
    / "evidence"
    / "reproducibility"
    / "codecheck_reviewer_container_1c0eb517_20260721"
    / "reviewer_reproducibility_receipt.json"
)

EXPECTED_SOURCE_COMMIT = "1c0eb51754beffac6f4df484914e35efc21c253f"
EXPECTED_RECEIPT_STATUS = "BOUNDED_REPRODUCIBILITY_PASS"
EXPECTED_SUITE_PASS_COUNT = 3
EXPECTED_ASSERTION_PASS_COUNT = 31
TEXT_SUFFIXES = {".json", ".md", ".py"}

MATERIAL_CLAIMS = {
    "BOUNDED_REPRODUCIBILITY_COUNTS": (
        "31 of 31 declared assertions and 3 of 3 suites reproduced in the packaged "
        "clean-run workflow, with dependency and source-state checks."
    ),
    "CUSTODY_AND_VALIDATION_CONTROLS": (
        "Versioned manifests, SHA-256 receipts, schema checks, duplicate-action locks, "
        "and fail-closed gate records support an inspectable evidence workflow."
    ),
    "ADVERSE_RESULT_RETENTION": (
        "Public records preserve failed promotion gates, negative findings, and "
        "unresolved authorities instead of converting them into favorable claims."
    ),
}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def normalized_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return data
    text = data.decode("utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(normalized_bytes(path)).hexdigest()


def fragment_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def graph_node(graph: dict[str, Any], node_id: str) -> dict[str, Any]:
    matches = [
        node
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and node.get("id") == node_id
    ]
    if len(matches) != 1:
        raise ValueError(f"evidence graph must contain exactly one {node_id} node")
    return matches[0]


def required_items_present(values: Any, required: set[str]) -> bool:
    return isinstance(values, list) and required <= set(values)


def build_payload(as_of_utc: str) -> dict[str, Any]:
    evaluated = parse_utc(as_of_utc)
    response = RESPONSE_MARKDOWN.read_text(encoding="utf-8")
    graph = read_json(EVIDENCE_GRAPH)
    evidence_index = EVIDENCE_INDEX.read_text(encoding="utf-8")
    receipt = read_json(REVIEWER_RECEIPT)

    proof_capsule = graph_node(graph, "pr-34")
    benchmark = graph_node(graph, "eia-frozen-benchmark")
    summary = receipt.get("summary", {})
    git = receipt.get("git", {})
    release_manifest = git.get("release_manifest", {})
    suites = receipt.get("suites", [])

    response_fragments_present = {
        claim_id: fragment in response
        for claim_id, fragment in MATERIAL_CLAIMS.items()
    }
    no_unverified_runtime_promotion = all(
        phrase not in response.lower()
        for phrase in (
            "live reviewer surface",
            "production reviewer surface",
            "always available reviewer surface",
        )
    )
    receipt_counts_hold = (
        receipt.get("status") == EXPECTED_RECEIPT_STATUS
        and summary.get("suite_count") == EXPECTED_SUITE_PASS_COUNT
        and summary.get("suite_pass_count") == EXPECTED_SUITE_PASS_COUNT
        and summary.get("assertion_count") == EXPECTED_ASSERTION_PASS_COUNT
        and summary.get("assertion_pass_count") == EXPECTED_ASSERTION_PASS_COUNT
        and all(
            isinstance(row, dict)
            and row.get("passed") is True
            and row.get("fact_projection")
            for row in suites
        )
        and len(suites) == EXPECTED_SUITE_PASS_COUNT
    )
    source_identity_hold = (
        git.get("commit") == EXPECTED_SOURCE_COMMIT
        and release_manifest.get("source_commit") == EXPECTED_SOURCE_COMMIT
        and release_manifest.get("passed") is True
        and git.get("source_state_verified") is True
    )
    receipt_boundaries_hold = (
        summary.get("external_validation_complete") is False
        and summary.get("agency_certification_complete") is False
        and all(
            isinstance(row, dict)
            and isinstance(row.get("fact_projection"), dict)
            and row["fact_projection"].get("promotion_gate_passed") is False
            for row in suites
        )
    )
    custody_graph_hold = (
        proof_capsule.get("state") == "merged_capability"
        and proof_capsule.get("merged") is True
        and required_items_present(
            proof_capsule.get("supports"),
            {
                "artifact_custody",
                "manifest_validation",
                "bounded_claim_enforcement",
                "machine_receipt_generation",
            },
        )
        and required_items_present(
            proof_capsule.get("does_not_support"),
            {
                "underlying_experiment_truth",
                "external_independence",
                "field_performance",
                "commercial_value",
            },
        )
    )
    negative_result_graph_hold = (
        benchmark.get("state") == "first_party_reproduced"
        and required_items_present(
            benchmark.get("supports"),
            {
                "3_of_3_suites",
                "31_of_31_assertions",
                "runtime_and_output_binding",
            },
        )
        and required_items_present(
            benchmark.get("does_not_support"),
            {
                "independent_reproduction",
                "performance_promotion",
            },
        )
        and isinstance(benchmark.get("negative_results"), list)
        and len(benchmark["negative_results"]) >= 1
        and "zero common settled hours" in evidence_index.lower()
        and "external validation: **false**" in evidence_index.lower()
    )

    checks = {
        "material_response_fragments_present": all(response_fragments_present.values()),
        "no_unverified_runtime_promotion": no_unverified_runtime_promotion,
        "reviewer_receipt_counts_hold": receipt_counts_hold,
        "reviewer_receipt_source_identity_hold": source_identity_hold,
        "reviewer_receipt_boundaries_hold": receipt_boundaries_hold,
        "merged_custody_graph_node_hold": custody_graph_hold,
        "negative_result_graph_node_hold": negative_result_graph_hold,
    }

    claim_entries = [
        {
            "claim_id": "BOUNDED_REPRODUCIBILITY_COUNTS",
            "response_fragment_sha256": fragment_sha256(
                MATERIAL_CLAIMS["BOUNDED_REPRODUCIBILITY_COUNTS"]
            ),
            "evidence_level": "FIRST_PARTY_REPRODUCED_NAMED_PACKAGE",
            "supported": (
                response_fragments_present["BOUNDED_REPRODUCIBILITY_COUNTS"]
                and receipt_counts_hold
                and source_identity_hold
                and receipt_boundaries_hold
                and negative_result_graph_hold
            ),
            "evidence": {
                "receipt_path": rel(REVIEWER_RECEIPT),
                "receipt_sha256": sha256(REVIEWER_RECEIPT),
                "source_commit": EXPECTED_SOURCE_COMMIT,
                "suite_pass_count": summary.get("suite_pass_count"),
                "assertion_pass_count": summary.get("assertion_pass_count"),
                "evidence_graph_node": "eia-frozen-benchmark",
            },
            "does_not_support": [
                "independent_reproduction",
                "external_validation",
                "agency_certification",
                "field_performance",
                "health_it_prior_performance",
            ],
        },
        {
            "claim_id": "CUSTODY_AND_VALIDATION_CONTROLS",
            "response_fragment_sha256": fragment_sha256(
                MATERIAL_CLAIMS["CUSTODY_AND_VALIDATION_CONTROLS"]
            ),
            "evidence_level": "MERGED_CAPABILITY",
            "supported": (
                response_fragments_present["CUSTODY_AND_VALIDATION_CONTROLS"]
                and custody_graph_hold
            ),
            "evidence": {
                "evidence_graph_path": rel(EVIDENCE_GRAPH),
                "evidence_graph_node": "pr-34",
                "canonical_role": proof_capsule.get("canonical_role"),
            },
            "does_not_support": list(proof_capsule.get("does_not_support", [])),
        },
        {
            "claim_id": "ADVERSE_RESULT_RETENTION",
            "response_fragment_sha256": fragment_sha256(
                MATERIAL_CLAIMS["ADVERSE_RESULT_RETENTION"]
            ),
            "evidence_level": "FIRST_PARTY_REPRODUCED_WITH_NEGATIVE_RESULTS",
            "supported": (
                response_fragments_present["ADVERSE_RESULT_RETENTION"]
                and negative_result_graph_hold
                and receipt_boundaries_hold
            ),
            "evidence": {
                "evidence_graph_path": rel(EVIDENCE_GRAPH),
                "evidence_graph_node": "eia-frozen-benchmark",
                "negative_result_count": len(benchmark.get("negative_results", [])),
                "evidence_index_path": rel(EVIDENCE_INDEX),
                "protocol_amendment_present": bool(receipt.get("protocol_amendment")),
            },
            "does_not_support": [
                "favorable_performance_promotion",
                "external_validation",
                "health_domain_correctness",
            ],
        },
    ]
    all_claims_supported = all(row["supported"] for row in claim_entries)
    status = (
        "VERIFIED_BOUNDED_CLAIM_MAP"
        if all(checks.values()) and all_claims_supported
        else "FAIL_CLAIM_TRACEABILITY"
    )
    sources = (RESPONSE_MARKDOWN, EVIDENCE_GRAPH, EVIDENCE_INDEX, REVIEWER_RECEIPT)

    return {
        "schema": "lumencore.argos_claim_evidence_map.v1",
        "generated_utc": evaluated.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notice_id": "ONC-ARGOS-SSN-2026-OS351107",
        "status": status,
        "response": {
            "path": rel(RESPONSE_MARKDOWN),
            "sha256": sha256(RESPONSE_MARKDOWN),
            "material_claim_count": len(claim_entries),
        },
        "checks": checks,
        "response_fragment_checks": response_fragments_present,
        "claims": claim_entries,
        "source_custody": [
            {
                "path": rel(path),
                "sha256": sha256(path),
                "hash_mode": "TEXT_UTF8_LF",
            }
            for path in sources
        ],
        "runtime_observation_boundary": (
            "This offline map does not assert live-domain availability. Runtime routes "
            "must be checked separately at action time."
        ),
        "claim_boundary": (
            "This map binds three affirmative engineering statements in the Argos "
            "response to named public evidence. It does not establish health IT prior "
            "performance, partner authority, HHS authorization, external validation, "
            "field performance, submission, acceptance, selection, award, or funding."
        ),
        "external_action_performed": False,
        "submission_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the bounded Project Argos claim-to-evidence map."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--as-of-utc")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    as_of = args.as_of_utc
    if args.check and not as_of and args.output.is_file():
        as_of = read_json(args.output)["generated_utc"]
    if not as_of:
        as_of = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = build_payload(as_of)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    current = args.output.is_file() and args.output.read_text(encoding="utf-8") == rendered

    if not args.check:
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
        status = "WRITTEN"
    else:
        status = "CURRENT" if current else "STALE"

    print(
        json.dumps(
            {
                "status": status,
                "decision": payload["status"],
                "claim_count": len(payload["claims"]),
                "all_claims_supported": all(
                    claim["supported"] for claim in payload["claims"]
                ),
                "external_action_performed": False,
                "submission_authorized": False,
                "output": str(args.output),
            },
            indent=2,
        )
    )
    return (
        0
        if status != "STALE"
        and payload["status"] == "VERIFIED_BOUNDED_CLAIM_MAP"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
