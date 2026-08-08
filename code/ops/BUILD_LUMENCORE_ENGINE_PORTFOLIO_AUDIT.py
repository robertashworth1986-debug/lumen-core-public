#!/usr/bin/env python3
"""Build a fail-closed, public-safe LumenCore portfolio audit."""

from __future__ import annotations

import argparse
import copy
from functools import lru_cache
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "lumencore_engine_portfolio_v2.json"
DEFAULT_PACKET = ROOT / "config" / "strategic_transaction_packet_v2.json"
DEFAULT_GRAPH = ROOT / "config" / "evidence_graph_v1.json"
DEFAULT_JSON = ROOT / "dashboard" / "data" / "lumencore_engine_portfolio_audit.json"
DEFAULT_MD = ROOT / "docs" / "LUMENCORE_ENGINE_PORTFOLIO_AUDIT_2026-08-08.md"

EVIDENCE_CLASSES = (
    "source",
    "entrypoint",
    "test",
    "documentation",
    "artifact",
    "public_surface",
)
ALLOWED_LANES = {
    "priority_validation_lane",
    "workflow_module",
    "research_lane",
    "concept_lane",
}
FORBIDDEN_PATH_MARKERS = {
    "credential",
    "private_key",
    "secret",
    "token",
    "driver license",
    "insurance card",
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


def read_json(path: Path, *, max_bytes: int = 2_000_000) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raise ValueError(f"JSON exceeds {max_bytes} bytes: {path}")
    payload = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_non_finite,
    )
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def require_sha256(value: Any, label: str) -> str:
    digest = require_text(value, label)
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return digest


def parse_utc(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("--as-of-utc must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def tracked_repository_objects() -> dict[str, str]:
    result = subprocess.run(
        ["git", "ls-files", "-s", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    tracked: dict[str, str] = {}
    for item in result.stdout.split(b"\0"):
        if not item:
            continue
        metadata, raw_path = item.split(b"\t", 1)
        _, blob_sha, _ = metadata.decode("ascii").split(" ")
        tracked[raw_path.decode("utf-8").replace("\\", "/")] = blob_sha
    return tracked


@lru_cache(maxsize=None)
def git_blob_bytes(blob_sha: str) -> bytes:
    result = subprocess.run(
        ["git", "cat-file", "blob", blob_sha],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return result.stdout


def validate_relative_path(value: Any, label: str) -> str:
    path = require_text(value, label).replace("\\", "/")
    pure = PurePosixPath(path)
    lowered = path.lower()
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"{label} must be repository-relative")
    if any(marker in lowered for marker in FORBIDDEN_PATH_MARKERS):
        raise ValueError(f"{label} contains a private or secret path marker")
    return path


def verify_strategic_binding(
    registry: dict[str, Any],
    packet: dict[str, Any],
    graph: dict[str, Any],
) -> dict[str, Any]:
    position = registry.get("market_position")
    if not isinstance(position, dict):
        raise ValueError("market_position must be an object")
    expected_position_fields = {
        "platform",
        "evidence_layer",
        "canonical_offer_packet",
        "primary_offer_id",
        "priority_lane_id",
        "direct_engine_sales_authorized",
    }
    if set(position) != expected_position_fields:
        raise ValueError("market_position fields mismatch")
    if position["platform"] != "LumenCore" or position["evidence_layer"] != "ProofLock":
        raise ValueError("canonical platform identity mismatch")
    if position["canonical_offer_packet"] != DEFAULT_PACKET.relative_to(ROOT).as_posix():
        raise ValueError("canonical offer packet path mismatch")
    if position["direct_engine_sales_authorized"] is not False:
        raise ValueError("direct engine sales must remain unauthorized")

    if packet.get("schema_version") != "2.0":
        raise ValueError("strategic packet schema mismatch")
    if packet.get("status") != "exploratory_founder_authorized_inquiry":
        raise ValueError("strategic packet status must remain non-binding")
    primary_offer = packet.get("primary_offer")
    if not isinstance(primary_offer, dict):
        raise ValueError("strategic packet primary_offer missing")
    if primary_offer.get("id") != position["primary_offer_id"]:
        raise ValueError("primary offer binding mismatch")

    parsed_contact = urlparse(require_text(packet.get("public_contact_path"), "contact"))
    if parsed_contact.scheme != "https" or parsed_contact.netloc != "lumen-core.ai":
        raise ValueError("public contact must use the official HTTPS domain")

    founder_control = packet.get("founder_control")
    if not isinstance(founder_control, dict):
        raise ValueError("strategic packet founder_control missing")
    for field in (
        "binding_sale_authorized",
        "license_signature_authorized",
        "ip_transfer_authorized",
        "credential_transfer_authorized",
    ):
        if founder_control.get(field) is not False:
            raise ValueError(f"strategic packet authority lock failed: {field}")

    integrity = packet.get("integrity")
    if not isinstance(integrity, dict):
        raise ValueError("strategic packet integrity missing")
    expected_packet_hash = require_sha256(
        integrity.get("packet_sha256"), "strategic packet SHA-256"
    )
    packet_copy = copy.deepcopy(packet)
    packet_copy["integrity"].pop("packet_sha256", None)
    if canonical_sha256(packet_copy) != expected_packet_hash:
        raise ValueError("strategic packet integrity mismatch")

    graph_hash = canonical_sha256(graph)
    if require_sha256(packet.get("evidence_graph_sha256"), "evidence graph SHA-256") != graph_hash:
        raise ValueError("strategic packet evidence graph binding mismatch")

    return {
        "platform": position["platform"],
        "evidence_layer": position["evidence_layer"],
        "primary_offer_id": primary_offer["id"],
        "customer_problem": require_text(
            primary_offer.get("customer_problem"), "customer problem"
        ),
        "public_contact_path": packet["public_contact_path"],
        "priority_lane_id": require_text(position["priority_lane_id"], "priority lane"),
        "direct_engine_sales_authorized": False,
        "strategic_packet_sha256": expected_packet_hash,
        "evidence_graph_sha256": graph_hash,
    }


def observed_maturity(present: dict[str, bool]) -> str:
    if present["source"] and present["entrypoint"] and present["test"]:
        return "tested_implementation"
    if present["source"] and present["entrypoint"]:
        return "runnable_component"
    if present["source"]:
        return "component_only"
    return "concept_only"


def audit_engine(engine: dict[str, Any], tracked: dict[str, str]) -> dict[str, Any]:
    required = {
        "id",
        "name",
        "lane",
        "safe_description",
        "buyer_profile",
        "scoping_use",
        "acceptance_gate",
        "claim_boundary",
        "evidence",
    }
    if not isinstance(engine, dict) or set(engine) != required:
        raise ValueError(f"engine fields mismatch: {engine.get('id') if isinstance(engine, dict) else '?'}")
    engine_id = require_text(engine["id"], "engine id")
    lane = require_text(engine["lane"], f"{engine_id} lane")
    if lane not in ALLOWED_LANES:
        raise ValueError(f"{engine_id}: unsupported lane")

    evidence = engine["evidence"]
    if not isinstance(evidence, dict) or set(evidence) != set(EVIDENCE_CLASSES):
        raise ValueError(f"{engine_id}: evidence classes mismatch")

    audited: dict[str, list[dict[str, Any]]] = {}
    present: dict[str, bool] = {}
    missing_paths: list[str] = []
    untracked_paths: list[str] = []
    for evidence_class in EVIDENCE_CLASSES:
        values = evidence[evidence_class]
        if not isinstance(values, list) or len(values) != len(set(values)):
            raise ValueError(f"{engine_id}: {evidence_class} must be a unique list")
        records: list[dict[str, Any]] = []
        for index, raw_path in enumerate(values):
            path = validate_relative_path(raw_path, f"{engine_id}.{evidence_class}[{index}]")
            absolute = ROOT / path
            exists = absolute.is_file()
            blob_sha = tracked.get(path)
            is_tracked = blob_sha is not None
            blob = git_blob_bytes(blob_sha) if blob_sha is not None else None
            records.append(
                {
                    "path": path,
                    "exists": exists,
                    "tracked": is_tracked,
                    "git_blob_sha": blob_sha,
                    "bytes": len(blob) if blob is not None else None,
                    "sha256": hashlib.sha256(blob).hexdigest()
                    if blob is not None
                    else None,
                }
            )
            if not exists:
                missing_paths.append(path)
            elif not is_tracked:
                untracked_paths.append(path)
        audited[evidence_class] = records
        present[evidence_class] = any(
            record["exists"] and record["tracked"] for record in records
        )

    maturity = observed_maturity(present)
    for field in (
        "name",
        "safe_description",
        "buyer_profile",
        "scoping_use",
        "acceptance_gate",
        "claim_boundary",
    ):
        require_text(engine[field], f"{engine_id}.{field}")

    return {
        "id": engine_id,
        "name": engine["name"],
        "lane": lane,
        "safe_description": engine["safe_description"],
        "buyer_profile": engine["buyer_profile"],
        "scoping_use": engine["scoping_use"],
        "acceptance_gate": engine["acceptance_gate"],
        "claim_boundary": engine["claim_boundary"],
        "observed_maturity": maturity,
        "evidence_classes_present": sum(present.values()),
        "evidence_classes_total": len(EVIDENCE_CLASSES),
        "missing_paths": sorted(missing_paths),
        "untracked_paths": sorted(untracked_paths),
        "evidence": audited,
    }


def payload_sha256(payload: dict[str, Any]) -> str:
    copy_payload = copy.deepcopy(payload)
    copy_payload.pop("integrity", None)
    return canonical_sha256(copy_payload)


def build_payload(
    registry: dict[str, Any],
    packet: dict[str, Any],
    graph: dict[str, Any],
    generated_at_utc: str,
) -> dict[str, Any]:
    if registry.get("schema_version") != "2.0":
        raise ValueError("portfolio registry schema mismatch")
    require_text(registry.get("source_note"), "source_note")
    boundaries = registry.get("boundaries")
    if not isinstance(boundaries, list) or len(boundaries) != len(set(boundaries)):
        raise ValueError("boundaries must be a unique list")
    for boundary in boundaries:
        require_text(boundary, "boundary")

    binding = verify_strategic_binding(registry, packet, graph)
    engines = registry.get("engines")
    if not isinstance(engines, list) or len(engines) != 15:
        raise ValueError("portfolio registry must define exactly 15 lanes")
    ids = [engine.get("id") for engine in engines if isinstance(engine, dict)]
    if len(ids) != 15 or len(ids) != len(set(ids)):
        raise ValueError("portfolio lane ids must be 15 unique strings")
    if binding["priority_lane_id"] not in ids:
        raise ValueError("priority lane is missing from the portfolio")
    if sum(engine.get("lane") == "priority_validation_lane" for engine in engines) != 1:
        raise ValueError("portfolio must define exactly one priority validation lane")

    tracked = tracked_repository_objects()
    audited = [audit_engine(engine, tracked) for engine in engines]
    audited.sort(
        key=lambda item: (
            item["id"] != binding["priority_lane_id"],
            item["lane"],
            item["name"].lower(),
        )
    )
    priority = next(
        engine for engine in audited if engine["id"] == binding["priority_lane_id"]
    )
    maturity_counts = Counter(engine["observed_maturity"] for engine in audited)
    lane_counts = Counter(engine["lane"] for engine in audited)
    missing_path_count = sum(len(engine["missing_paths"]) for engine in audited)
    untracked_path_count = sum(len(engine["untracked_paths"]) for engine in audited)

    payload: dict[str, Any] = {
        "schema": "lumencore_engine_portfolio_audit_v2",
        "generated_at_utc": generated_at_utc,
        "source_registry": DEFAULT_CONFIG.relative_to(ROOT).as_posix(),
        "source_registry_sha256": canonical_sha256(registry),
        "source_registry_hash_scope": "canonical JSON: UTF-8, sorted keys, compact separators",
        "source_note": registry["source_note"],
        "primary_offer_binding": binding,
        "summary": {
            "portfolio_lane_count": len(audited),
            "primary_offer_count": 1,
            "priority_lane_id": priority["id"],
            "priority_lane_maturity": priority["observed_maturity"],
            "priority_lane_scoping_candidate": priority["observed_maturity"]
            in {"tested_implementation", "runnable_component"},
            "maturity_counts": dict(sorted(maturity_counts.items())),
            "lane_counts": dict(sorted(lane_counts.items())),
            "subscription_ready_count": 0,
            "direct_engine_sales_authorized": False,
            "buyer_commitment_evidenced": False,
            "signed_paid_scope_evidenced": False,
            "executed_buyer_pilot_evidenced": False,
            "revenue_evidenced": False,
            "external_validation_evidenced": False,
            "missing_evidence_path_count": missing_path_count,
            "untracked_evidence_path_count": untracked_path_count,
        },
        "engines": audited,
        "boundaries": boundaries,
    }
    payload["integrity"] = {
        "algorithm": "sha256",
        "canonicalization": "utf8-json-sort-keys-compact",
        "hash_scope": "entire payload excluding integrity",
        "payload_sha256": payload_sha256(payload),
    }
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    binding = payload["primary_offer_binding"]
    lines = [
        "# LumenCore Engine Portfolio Audit",
        "",
        f"Generated at: `{payload['generated_at_utc']}`",
        "",
        "## Reviewer decision",
        "",
        "LumenCore is one platform with one primary commercial offer, not 15 finished products.",
        "The 15 founder engine names are retained as internal delivery, workflow, research, or concept lanes.",
        "ProofLock is the evidence layer for the buyer-owned baseline validation sprint.",
        "",
        f"**Customer problem:** {binding['customer_problem']}",
        "",
        "**Primary offer:** Buyer-Owned Baseline Validation Sprint",
        "",
        f"**First market lane:** `{summary['priority_lane_id']}`",
        "",
        "The buyer supplies authorized data, accepts the incumbent baseline, and locks the metric and threshold before execution.",
        "LumenCore returns replay receipts, negative results, hashes, an offline verifier, and a buyer-readable Proof Capsule.",
        "",
        "## Current commercial truth",
        "",
        f"- Portfolio lanes audited: `{summary['portfolio_lane_count']}`",
        f"- Primary offers: `{summary['primary_offer_count']}`",
        f"- Priority-lane maturity: `{summary['priority_lane_maturity']}`",
        f"- Priority lane eligible for buyer scoping: `{str(summary['priority_lane_scoping_candidate']).lower()}`",
        f"- Subscription-ready products: `{summary['subscription_ready_count']}`",
        f"- Missing configured evidence paths: `{summary['missing_evidence_path_count']}`",
        f"- Untracked configured evidence paths: `{summary['untracked_evidence_path_count']}`",
        "- Buyer commitment evidenced: `false`",
        "- Signed paid scope evidenced: `false`",
        "- Executed buyer pilot evidenced: `false`",
        "- Revenue evidenced: `false`",
        "- External validation evidenced: `false`",
        "",
        "## Portfolio lanes",
        "",
        "| Lane | Role | Repository maturity | Evidence classes | Buyer-safe scoping use |",
        "|---|---|---|---:|---|",
    ]
    for engine in payload["engines"]:
        scoping_use = engine["scoping_use"].replace("|", "/")
        lines.append(
            f"| {engine['name']} | `{engine['lane']}` | `{engine['observed_maturity']}` | "
            f"{engine['evidence_classes_present']}/{engine['evidence_classes_total']} | {scoping_use} |"
        )

    lines.extend(["", "## Lane gates", ""])
    for engine in payload["engines"]:
        lines.extend(
            [
                f"### {engine['name']}",
                "",
                f"- Safe description: {engine['safe_description']}",
                f"- Buyer profile: {engine['buyer_profile']}",
                f"- Acceptance gate: {engine['acceptance_gate']}",
                f"- Claim boundary: {engine['claim_boundary']}",
                f"- Missing configured paths: {len(engine['missing_paths'])}",
                "",
            ]
        )

    lines.extend(
        [
            "## Binding and integrity",
            "",
            f"- Strategic packet SHA-256: `{binding['strategic_packet_sha256']}`",
            f"- Evidence graph SHA-256: `{binding['evidence_graph_sha256']}`",
            f"- Portfolio payload SHA-256: `{payload['integrity']['payload_sha256']}`",
            f"- Public contact: <{binding['public_contact_path']}>",
            "",
            "## Boundaries",
            "",
        ]
    )
    lines.extend(f"- {boundary}" for boundary in payload["boundaries"])
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], json_out: Path, md_out: Path) -> None:
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(render_markdown(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the LumenCore portfolio audit.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--strategic-packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--evidence-graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    parser.add_argument("--as-of-utc")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    as_of_utc = args.as_of_utc
    if args.check and as_of_utc is None and args.json_out.exists():
        as_of_utc = read_json(args.json_out).get("generated_at_utc")

    payload = build_payload(
        read_json(args.config),
        read_json(args.strategic_packet),
        read_json(args.evidence_graph),
        parse_utc(as_of_utc),
    )
    rendered_json = json.dumps(payload, indent=2) + "\n"
    rendered_md = render_markdown(payload)

    if args.check:
        mismatches = []
        if not args.json_out.exists() or args.json_out.read_text(encoding="utf-8") != rendered_json:
            mismatches.append(str(args.json_out))
        if not args.md_out.exists() or args.md_out.read_text(encoding="utf-8") != rendered_md:
            mismatches.append(str(args.md_out))
        if mismatches:
            raise SystemExit("stale portfolio audit outputs: " + ", ".join(mismatches))
        return 0

    write_outputs(payload, args.json_out, args.md_out)
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
