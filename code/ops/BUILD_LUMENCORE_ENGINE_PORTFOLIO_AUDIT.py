#!/usr/bin/env python3
"""Build a fail-closed, public-safe LumenCore portfolio audit."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
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
EVIDENCE_BANDS = ("A", "B", "C", "D", "E", "U")
RESULT_STATES = {
    "bounded_positive",
    "mixed",
    "negative",
    "no_result",
    "not_applicable",
    "unverified",
}
RANKED_SYSTEM_FIELDS = {
    "rank",
    "id",
    "name",
    "role",
    "evidence_band",
    "evidence_type",
    "result_state",
    "result_summary",
    "adverse_result",
    "current_gate",
    "evidence_as_of_utc",
    "external_validation",
    "field_validation",
    "commercial_validation",
    "evidence_refs",
}
RAW_API_QUERY_RE = re.compile(
    rb"api[_-]?key=(?!\[?redacted\]?|\$\{|\{\{|<)[A-Za-z0-9_-]{12,}",
    re.IGNORECASE,
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


def validate_relative_path(value: Any, label: str) -> str:
    path = require_text(value, label).replace("\\", "/")
    pure = PurePosixPath(path)
    lowered = path.lower()
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"{label} must be repository-relative")
    if any(marker in lowered for marker in FORBIDDEN_PATH_MARKERS):
        raise ValueError(f"{label} contains a private or secret path marker")
    return path


def current_blob_record(path: str, tracked: dict[str, str]) -> dict[str, Any]:
    absolute = ROOT / path
    exists = absolute.is_file()
    is_tracked = path in tracked
    blob = absolute.read_bytes() if exists else None
    current_blob_sha = None
    if blob is not None:
        header = f"blob {len(blob)}\0".encode("ascii")
        current_blob_sha = hashlib.sha1(header + blob).hexdigest()
    return {
        "path": path,
        "exists": exists,
        "tracked": is_tracked,
        "git_blob_sha": current_blob_sha if is_tracked else None,
        "bytes": len(blob) if blob is not None else None,
        "sha256": hashlib.sha256(blob).hexdigest() if blob is not None else None,
    }


def reject_embedded_api_query(path: str) -> None:
    if path.startswith("tests/"):
        return
    absolute = ROOT / path
    if not absolute.is_file():
        return
    if RAW_API_QUERY_RE.search(absolute.read_bytes()):
        raise ValueError(f"{path}: embedded API credential-like query value")


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
        "commercial_method",
        "canonical_offer_packet",
        "primary_offer_id",
        "priority_lane_id",
        "direct_engine_sales_authorized",
    }
    if set(position) != expected_position_fields:
        raise ValueError("market_position fields mismatch")
    if position["platform"] != "LumenCore" or position["evidence_layer"] != "ProofLock":
        raise ValueError("canonical platform identity mismatch")
    if position["commercial_method"] != "Frozen Delta":
        raise ValueError("canonical commercial method mismatch")
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
        "commercial_method": position["commercial_method"],
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
            record = current_blob_record(path, tracked)
            records.append(record)
            exists = record["exists"]
            is_tracked = record["tracked"]
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
        "implementation_state": maturity,
        "artifact_coverage": {
            "classes_present": sum(present.values()),
            "classes_total": len(EVIDENCE_CLASSES),
            "classes": present,
        },
        "missing_paths": sorted(missing_paths),
        "untracked_paths": sorted(untracked_paths),
        "evidence": audited,
    }


def audit_ranked_system(
    system: dict[str, Any], tracked: dict[str, str]
) -> dict[str, Any]:
    if not isinstance(system, dict) or set(system) != RANKED_SYSTEM_FIELDS:
        raise ValueError(
            f"ranked system fields mismatch: {system.get('id') if isinstance(system, dict) else '?'}"
        )
    system_id = require_text(system["id"], "ranked system id")
    rank = system["rank"]
    if not isinstance(rank, int) or isinstance(rank, bool) or rank < 1:
        raise ValueError(f"{system_id}: rank must be a positive integer")
    band = require_text(system["evidence_band"], f"{system_id}.evidence_band")
    if band not in EVIDENCE_BANDS:
        raise ValueError(f"{system_id}: unsupported evidence band")
    result_state = require_text(system["result_state"], f"{system_id}.result_state")
    if result_state not in RESULT_STATES:
        raise ValueError(f"{system_id}: unsupported result state")
    evidence_type = system["evidence_type"]
    if (
        not isinstance(evidence_type, list)
        or not evidence_type
        or len(evidence_type) != len(set(evidence_type))
    ):
        raise ValueError(f"{system_id}: evidence_type must be a non-empty unique list")
    for index, value in enumerate(evidence_type):
        require_text(value, f"{system_id}.evidence_type[{index}]")
    for field in (
        "name",
        "role",
        "result_summary",
        "adverse_result",
        "current_gate",
        "evidence_as_of_utc",
    ):
        require_text(system[field], f"{system_id}.{field}")
    parse_utc(system["evidence_as_of_utc"])
    for field in (
        "external_validation",
        "field_validation",
        "commercial_validation",
    ):
        if system[field] is not False:
            raise ValueError(f"{system_id}: {field} must remain false")

    refs = system["evidence_refs"]
    if not isinstance(refs, list) or len(refs) != len(set(refs)):
        raise ValueError(f"{system_id}: evidence_refs must be a unique list")
    if band in {"A", "B", "C", "D", "E"} and not refs:
        raise ValueError(f"{system_id}: evidence band {band} requires references")
    audited_refs: list[dict[str, Any]] = []
    for index, raw_path in enumerate(refs):
        path = validate_relative_path(raw_path, f"{system_id}.evidence_refs[{index}]")
        reject_embedded_api_query(path)
        record = current_blob_record(path, tracked)
        if not record["exists"]:
            raise ValueError(f"{system_id}: missing evidence reference: {path}")
        if not record["tracked"]:
            raise ValueError(f"{system_id}: untracked evidence reference: {path}")
        audited_refs.append(record)
    if band == "U" and result_state != "unverified":
        raise ValueError(f"{system_id}: band U must remain unverified")
    if band != "U" and result_state == "unverified":
        raise ValueError(f"{system_id}: only band U may be unverified")

    audited = copy.deepcopy(system)
    audited["evidence_refs"] = audited_refs
    return audited


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
    if registry.get("schema_version") != "2.1":
        raise ValueError("portfolio registry schema mismatch")
    require_text(registry.get("source_note"), "source_note")
    boundaries = registry.get("boundaries")
    if not isinstance(boundaries, list) or len(boundaries) != len(set(boundaries)):
        raise ValueError("boundaries must be a unique list")
    for boundary in boundaries:
        require_text(boundary, "boundary")

    inventory_scope = registry.get("inventory_scope")
    if not isinstance(inventory_scope, dict) or set(inventory_scope) != {
        "registered_implementation_lane_count",
        "evidence_ranked_system_count",
        "comprehensive_for_named_ec_scope",
        "separate_products_implied",
        "unverified_or_absent_states_included",
    }:
        raise ValueError("inventory_scope fields mismatch")
    if inventory_scope["comprehensive_for_named_ec_scope"] is not True:
        raise ValueError("named EC scope must remain comprehensive")
    if inventory_scope["separate_products_implied"] is not False:
        raise ValueError("portfolio must not imply separate products")
    if inventory_scope["unverified_or_absent_states_included"] is not True:
        raise ValueError("unverified and absent states must remain visible")
    band_legend = registry.get("evidence_band_legend")
    if not isinstance(band_legend, dict) or tuple(band_legend) != EVIDENCE_BANDS:
        raise ValueError("evidence band legend mismatch")
    for band, definition in band_legend.items():
        require_text(definition, f"evidence band {band}")

    binding = verify_strategic_binding(registry, packet, graph)
    engines = registry.get("engines")
    registered_count = inventory_scope["registered_implementation_lane_count"]
    if not isinstance(registered_count, int) or registered_count < 1:
        raise ValueError("registered implementation lane count is invalid")
    if not isinstance(engines, list) or len(engines) != registered_count:
        raise ValueError("registered implementation lane count mismatch")
    ids = [engine.get("id") for engine in engines if isinstance(engine, dict)]
    if len(ids) != registered_count or len(ids) != len(set(ids)):
        raise ValueError("registered implementation lane ids must be unique")
    if binding["priority_lane_id"] not in ids:
        raise ValueError("priority lane is missing from the portfolio")
    if sum(engine.get("lane") == "priority_validation_lane" for engine in engines) != 1:
        raise ValueError("portfolio must define exactly one priority validation lane")

    tracked = tracked_repository_objects()
    audited = [audit_engine(engine, tracked) for engine in engines]
    audited.sort(key=lambda item: (item["lane"], item["name"].lower()))
    priority = next(
        engine for engine in audited if engine["id"] == binding["priority_lane_id"]
    )
    maturity_counts = Counter(engine["implementation_state"] for engine in audited)
    lane_counts = Counter(engine["lane"] for engine in audited)
    missing_path_count = sum(len(engine["missing_paths"]) for engine in audited)
    untracked_path_count = sum(len(engine["untracked_paths"]) for engine in audited)

    systems = registry.get("evidence_ranked_systems")
    ranked_count = inventory_scope["evidence_ranked_system_count"]
    if not isinstance(ranked_count, int) or ranked_count < 1:
        raise ValueError("evidence ranked system count is invalid")
    if not isinstance(systems, list) or len(systems) != ranked_count:
        raise ValueError("evidence ranked system count mismatch")
    ranked = [audit_ranked_system(system, tracked) for system in systems]
    ranks = [system["rank"] for system in ranked]
    ranked_ids = [system["id"] for system in ranked]
    ranked_names = [system["name"] for system in ranked]
    if ranks != list(range(1, ranked_count + 1)):
        raise ValueError("evidence ranks must be contiguous and ordered")
    if len(ranked_ids) != len(set(ranked_ids)) or len(ranked_names) != len(set(ranked_names)):
        raise ValueError("evidence-ranked system ids and names must be unique")
    required_named_scope = {
        "lumencore_prooflock",
        "frozen_delta_buyer_owned_validation_sprint",
        "eia_codecheck",
        "harbor_sentinel",
        "dice",
        "missionweave",
        "lumengov_grant_factory",
        "lumatrader_kraken_controls",
        "faa_sdr_10k",
        "lumascout",
        "lumen_infrastructure_sentinel",
        "lumajet",
        "luma_xr_command_room",
        "lumasuit_lumaskin",
        "echoform_identity_architecture",
        "echolock",
        "magneto_magnetic_geometry",
        "cumberland_museum_experience_dome",
        "dungeon",
    }
    if set(ranked_ids) != required_named_scope:
        raise ValueError("evidence-ranked named EC scope mismatch")
    evidence_band_counts = Counter(system["evidence_band"] for system in ranked)

    payload: dict[str, Any] = {
        "schema": "lumencore_engine_portfolio_audit_v3",
        "generated_at_utc": generated_at_utc,
        "source_registry": DEFAULT_CONFIG.relative_to(ROOT).as_posix(),
        "source_registry_sha256": canonical_sha256(registry),
        "source_registry_hash_scope": "canonical JSON: UTF-8, sorted keys, compact separators",
        "source_note": registry["source_note"],
        "inventory_scope": inventory_scope,
        "evidence_band_legend": band_legend,
        "primary_offer_binding": binding,
        "summary": {
            "registered_implementation_lane_count": len(audited),
            "evidence_ranked_system_count": len(ranked),
            "primary_offer_count": 1,
            "configured_priority_lane_id": priority["id"],
            "configured_priority_lane_implementation_state": priority["implementation_state"],
            "configured_priority_is_evidence_rank": False,
            "implementation_state_counts": dict(sorted(maturity_counts.items())),
            "lane_counts": dict(sorted(lane_counts.items())),
            "evidence_band_counts": {
                band: evidence_band_counts.get(band, 0) for band in EVIDENCE_BANDS
            },
            "unverified_or_absent_system_count": evidence_band_counts.get("U", 0),
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
        "evidence_ranked_systems": ranked,
        "registered_implementation_lanes": audited,
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
        "LumenCore is one platform with one primary commercial offer, not a collection of separately validated products.",
        "ProofLock is the evidence and claim-governance layer.",
        "Frozen Delta is the method inside the Buyer-Owned Baseline Validation Sprint: freeze source rights, the accepted baseline, metric, threshold, holdout, failure rules, and allowed claims before execution.",
        "",
        f"**Customer problem:** {binding['customer_problem']}",
        "",
        "**Platform:** LumenCore",
        "",
        "**Evidence layer:** ProofLock",
        "",
        f"**Commercial method:** {binding['commercial_method']}",
        "",
        "**Primary offer:** Buyer-Owned Baseline Validation Sprint",
        "",
        "The buyer supplies authorized data, accepts the incumbent baseline, and locks the metric and threshold before execution.",
        "LumenCore returns replay receipts, negative results, hashes, an offline verifier, and a buyer-readable Proof Capsule.",
        "",
        "## Current commercial truth",
        "",
        f"- Evidence-ranked systems and explicit unverified states: `{summary['evidence_ranked_system_count']}`",
        f"- Registered implementation lanes with artifact coverage: `{summary['registered_implementation_lane_count']}`",
        f"- Primary offers: `{summary['primary_offer_count']}`",
        f"- Configured sector priority is an evidence rank: `{str(summary['configured_priority_is_evidence_rank']).lower()}`",
        f"- Unverified or absent named systems: `{summary['unverified_or_absent_system_count']}`",
        f"- Subscription-ready products: `{summary['subscription_ready_count']}`",
        f"- Missing configured evidence paths: `{summary['missing_evidence_path_count']}`",
        f"- Untracked configured evidence paths: `{summary['untracked_evidence_path_count']}`",
        "- Buyer commitment evidenced: `false`",
        "- Signed paid scope evidenced: `false`",
        "- Executed buyer pilot evidenced: `false`",
        "- Revenue evidenced: `false`",
        "- External validation evidenced: `false`",
        "",
        "## Evidence-ranked systems",
        "",
        "Evidence band is not product readiness. Every ranked record retains a result state, adverse result, current gate, and false external, field, and commercial validation defaults.",
        "",
        "| Rank | Band | System or method | Evidence type | Result state | Bounded result | Adverse result / current gate |",
        "|---:|:---:|---|---|---|---|---|",
    ]
    for system in payload["evidence_ranked_systems"]:
        types = ", ".join(system["evidence_type"]).replace("|", "/")
        result = system["result_summary"].replace("|", "/")
        adverse = system["adverse_result"].replace("|", "/")
        gate = system["current_gate"].replace("|", "/")
        lines.append(
            f"| {system['rank']} | **{system['evidence_band']}** | {system['name']} | "
            f"{types} | `{system['result_state']}` | {result} | {adverse} **Next:** {gate} |"
        )

    lines.extend(["", "### Evidence-band legend", ""])
    for band, definition in payload["evidence_band_legend"].items():
        lines.append(f"- **{band}:** {definition}")

    lines.extend(
        [
            "",
            "## Registered implementation lanes and artifact coverage",
            "",
            "Artifact coverage counts tracked source, entrypoint, test, documentation, artifact, and public-surface classes. It does **not** measure scientific evidence strength, operational reliability, external validation, or commercial readiness.",
            "",
            "| Lane | Role | Implementation state | Artifact coverage | Buyer-safe scoping use |",
            "|---|---|---|---:|---|",
        ]
    )
    for engine in payload["registered_implementation_lanes"]:
        scoping_use = engine["scoping_use"].replace("|", "/")
        coverage = engine["artifact_coverage"]
        lines.append(
            f"| {engine['name']} | `{engine['lane']}` | `{engine['implementation_state']}` | "
            f"{coverage['classes_present']}/{coverage['classes_total']} | {scoping_use} |"
        )

    lines.extend(["", "## Registered-lane gates", ""])
    for engine in payload["registered_implementation_lanes"]:
        lines.extend(
            [
                f"### {engine['name']}",
                "",
                f"- Safe description: {engine['safe_description']}",
                f"- Buyer profile: {engine['buyer_profile']}",
                f"- Acceptance gate: {engine['acceptance_gate']}",
                f"- Claim boundary: {engine['claim_boundary']}",
                f"- Implementation state: `{engine['implementation_state']}`",
                f"- Artifact coverage: {engine['artifact_coverage']['classes_present']}/{engine['artifact_coverage']['classes_total']}",
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
