from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_public_live_breadth_manifest as public_manifest


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_payload(payload: Any) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def strict_sha256(value: Any) -> str | None:
    return public_manifest.strict_sha256(value)


def positive_int(value: Any) -> int | None:
    parsed = public_manifest.safe_int(value)
    return parsed if parsed is not None and parsed > 0 else None


def positive_float(value: Any) -> float | None:
    return public_manifest.safe_float(value)


def evidence_present(item: dict[str, Any]) -> bool:
    url = str(item.get("rights_evidence_url") or "").strip()
    digest = strict_sha256(item.get("rights_evidence_sha256"))
    return url.startswith(("https://", "http://")) or digest is not None


def item_blockers(item: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if item.get("rights_status") != "verified_for_review":
        blockers.append("rights_status_verified_for_review")
    if not evidence_present(item):
        blockers.append("rights_evidence_url_or_sha256")
    if item.get("relevance_status") != "verified":
        blockers.append("decision_relevance_verified")
    if not str(item.get("intended_decision") or "").strip():
        blockers.append("intended_decision")
    if positive_int(item.get("minimum_rows")) is None:
        blockers.append("minimum_rows")
    if not str(item.get("minimum_rows_basis") or "").strip():
        blockers.append("minimum_rows_basis")
    if positive_float(item.get("max_age_hours")) is None:
        blockers.append("max_age_hours")
    if not str(item.get("max_age_basis") or "").strip():
        blockers.append("max_age_basis")
    if strict_sha256(item.get("dataset_snapshot_sha256")) is None:
        blockers.append("dataset_snapshot_sha256")
    if public_manifest.parse_utc(item.get("dataset_snapshot_observed_utc")) is None:
        blockers.append("dataset_snapshot_observed_utc")
    return blockers


def build_item(
    row: dict[str, Any],
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    existing = existing or {}
    source = str(row.get("source") or "").strip()
    item = {
        "source": source,
        "source_ref": public_manifest.source_ref(source),
        "sector": str(row.get("sector") or "unknown").strip().lower() or "unknown",
        "registry_observation": {
            "enabled": row.get("enabled") is True,
            "first_party_measured_flag": row.get("measured") is True,
            "probe_status": public_manifest.classify_probe(row),
            "observed_rows": public_manifest.safe_int(row.get("rows")),
            "last_probe_utc": row.get("last_probe_utc"),
            "registry_row_sha256": sha256_payload(row),
        },
        "rights_status": existing.get("rights_status", "unknown"),
        "rights_evidence_url": existing.get("rights_evidence_url"),
        "rights_evidence_sha256": existing.get("rights_evidence_sha256"),
        "rights_note": existing.get("rights_note"),
        "relevance_status": existing.get("relevance_status", "unknown"),
        "intended_decision": existing.get("intended_decision"),
        "relevance_note": existing.get("relevance_note"),
        "minimum_rows": existing.get("minimum_rows"),
        "minimum_rows_basis": existing.get("minimum_rows_basis"),
        "max_age_hours": existing.get("max_age_hours"),
        "max_age_basis": existing.get("max_age_basis"),
        "dataset_snapshot_sha256": existing.get("dataset_snapshot_sha256"),
        "dataset_snapshot_observed_utc": existing.get("dataset_snapshot_observed_utc"),
    }
    item["blockers"] = item_blockers(item)
    item["ready_for_protocol_review"] = not item["blockers"]
    return item


def build_worklist(
    registry: dict[str, Any],
    registry_sha256: str,
    generated_utc: str | None = None,
    existing_governance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    generated_at = public_manifest.parse_utc(generated_utc or now_utc())
    if generated_at is None:
        raise ValueError("generated_utc must be an ISO-8601 timestamp")
    rows = registry.get("rows")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("Registry must contain a JSON object row array")

    existing_sources = (existing_governance or {}).get("sources", {})
    if not isinstance(existing_sources, dict):
        raise ValueError("Existing governance must contain a sources object")

    items = [
        build_item(row, existing_sources.get(str(row.get("source") or "")))
        for row in rows
    ]
    items.sort(key=lambda item: item["source"])
    source_names = [item["source"] for item in items]
    if not all(source_names) or len(source_names) != len(set(source_names)):
        raise ValueError("Source identifiers must be present and unique")

    worklist: dict[str, Any] = {
        "schema": "private_live_breadth_governance_worklist_v1",
        "generated_utc": generated_at.isoformat(),
        "classification": "PRIVATE_DO_NOT_PUBLISH",
        "purpose": (
            "Collect the source-owner decisions and evidence needed before a source can "
            "be promoted into the public review-ready breadth count."
        ),
        "registry_sha256": registry_sha256.lower(),
        "registry_generated_utc": registry.get("generated_utc"),
        "registry_max_age_hours": (existing_governance or {}).get(
            "registry_max_age_hours"
        ),
        "protocol_review": {
            "approval_status": "pending",
            "reviewed_by_role": None,
            "reviewed_utc": None,
            "review_note": None,
        },
        "items": items,
        "instructions": [
            "Use only authorized provider terms, licenses, contracts, or written owner decisions as rights evidence.",
            "Set minimum row depth and maximum age from the named decision, not from the observed values.",
            "Bind the exact underlying dataset snapshot with SHA-256.",
            "Do not approve the worklist until every promoted source has no blockers.",
            "Keep this source-named worklist private; publish only the pseudonymous manifest.",
        ],
    }
    worklist["summary"] = summarize_worklist(worklist)
    worklist["integrity"] = {
        "algorithm": "sha256",
        "canonicalization": "utf8-json-sort-keys-compact",
        "worklist_sha256": worklist_sha256(worklist),
    }
    return worklist


def summarize_worklist(worklist: dict[str, Any]) -> dict[str, Any]:
    items = worklist.get("items", [])
    return {
        "sources": len(items),
        "sources_ready_for_protocol_review": sum(
            bool(item.get("ready_for_protocol_review")) for item in items
        ),
        "sources_blocked": sum(bool(item.get("blockers")) for item in items),
        "blocking_fields": sum(len(item.get("blockers", [])) for item in items),
    }


def worklist_sha256(worklist: dict[str, Any]) -> str:
    payload = deepcopy(worklist)
    payload.pop("summary", None)
    payload.pop("integrity", None)
    return sha256_payload(payload)


def verify_worklist(worklist: dict[str, Any]) -> bool:
    integrity = worklist.get("integrity")
    expected = integrity.get("worklist_sha256") if isinstance(integrity, dict) else None
    return strict_sha256(expected) == worklist_sha256(worklist)


def promote_worklist(worklist: dict[str, Any]) -> dict[str, Any]:
    if worklist.get("schema") != "private_live_breadth_governance_worklist_v1":
        raise ValueError("Unsupported worklist schema")
    if not verify_worklist(worklist):
        raise ValueError("Worklist integrity check failed")

    review = worklist.get("protocol_review")
    if not isinstance(review, dict) or review.get("approval_status") != "approved":
        raise ValueError("Protocol review approval is required")
    if not str(review.get("reviewed_by_role") or "").strip():
        raise ValueError("Protocol reviewer role is required")
    if public_manifest.parse_utc(review.get("reviewed_utc")) is None:
        raise ValueError("Protocol reviewed_utc is required")
    if positive_float(worklist.get("registry_max_age_hours")) is None:
        raise ValueError("registry_max_age_hours must be accepted before promotion")

    sources: dict[str, Any] = {}
    for item in worklist.get("items", []):
        blockers = item_blockers(item)
        if blockers:
            raise ValueError(
                f"Source {item.get('source_ref', 'unknown')} is blocked: {', '.join(blockers)}"
            )
        source = str(item.get("source") or "").strip()
        sources[source] = {
            "rights_status": item["rights_status"],
            "rights_evidence_url": item.get("rights_evidence_url"),
            "rights_evidence_sha256": item.get("rights_evidence_sha256"),
            "rights_note": item.get("rights_note"),
            "relevance_status": item["relevance_status"],
            "intended_decision": item["intended_decision"],
            "relevance_note": item.get("relevance_note"),
            "minimum_rows": positive_int(item["minimum_rows"]),
            "minimum_rows_basis": item["minimum_rows_basis"],
            "max_age_hours": positive_float(item["max_age_hours"]),
            "max_age_basis": item["max_age_basis"],
            "dataset_snapshot_sha256": strict_sha256(
                item["dataset_snapshot_sha256"]
            ),
            "dataset_snapshot_observed_utc": item[
                "dataset_snapshot_observed_utc"
            ],
        }

    governance = {
        "schema": "public_live_breadth_governance_v1",
        "registry_sha256": worklist["registry_sha256"],
        "registry_max_age_hours": positive_float(
            worklist["registry_max_age_hours"]
        ),
        "protocol": {
            "approval_status": "approved",
            "reviewed_by_role": review["reviewed_by_role"],
            "reviewed_utc": review["reviewed_utc"],
            "worklist_sha256": worklist["integrity"]["worklist_sha256"],
        },
        "sources": sources,
    }
    return public_manifest.seal_governance(governance)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or promote a private live-breadth governance worklist."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--registry", type=Path, required=True)
    build_parser.add_argument("--existing-governance", type=Path)
    build_parser.add_argument("--output", type=Path, required=True)
    build_parser.add_argument("--generated-at")

    promote_parser = subparsers.add_parser("promote")
    promote_parser.add_argument("--worklist", type=Path, required=True)
    promote_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "build":
        registry = load_json(args.registry)
        existing = (
            load_json(args.existing_governance) if args.existing_governance else None
        )
        worklist = build_worklist(
            registry,
            public_manifest.file_sha256(args.registry),
            generated_utc=args.generated_at,
            existing_governance=existing,
        )
        write_json(args.output, worklist)
        print(json.dumps({"output": str(args.output), **worklist["summary"]}, indent=2))
        return 0

    worklist = load_json(args.worklist)
    governance = promote_worklist(worklist)
    write_json(args.output, governance)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sources": len(governance["sources"]),
                "governance_sha256": governance["integrity"]["governance_sha256"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
