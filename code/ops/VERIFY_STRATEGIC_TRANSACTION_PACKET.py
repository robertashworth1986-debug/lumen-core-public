#!/usr/bin/env python3
"""Fail-closed verifier for the public-safe LumenCore transaction packet."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

EXPECTED_REPOSITORY = "robertashworth1986-debug/lumen-core-public"
EXPECTED_STATUS = "exploratory_founder_authorized_inquiry"
MAX_PACKET_BYTES = 500_000

REQUIRED_TOP_LEVEL = {
    "schema_version",
    "generated_utc",
    "repository",
    "status",
    "purpose",
    "public_contact_path",
    "transaction_options",
    "public_assets",
    "diligence_requirements",
    "private_until_qualified_diligence",
    "claim_boundaries",
    "founder_control",
    "asking_price",
}

REQUIRED_OPTION_STRUCTURES = {
    "whole_company_acquisition",
    "exclusive_field_of_use_license",
    "non_exclusive_technology_license",
    "acquihire_plus_defined_ip_license",
    "paid_validation_pilot_with_option",
}

REQUIRED_CLAIM_BOUNDARIES = {
    "no_external_validation_claim",
    "no_customer_adoption_claim",
    "no_revenue_claim",
    "no_field_performance_claim",
    "no_certified_safety_claim",
    "no_agency_endorsement_claim",
    "no_award_claim",
    "no_public_transaction_valuation",
    "no_binding_transfer_without_definitive_agreement",
}

REQUIRED_FOUNDER_CONTROL = {
    "external_inquiries_authorized": True,
    "nda_signature_authorized": False,
    "binding_sale_authorized": False,
    "license_signature_authorized": False,
    "ip_transfer_authorized": False,
    "credential_transfer_authorized": False,
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


def load_json_strict(path: Path, *, max_bytes: int = MAX_PACKET_BYTES) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raise ValueError(f"JSON exceeds maximum size of {max_bytes} bytes")
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_non_finite,
    )
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def require_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def require_unique_string_list(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    if not allow_empty and not value:
        raise ValueError(f"{label} must not be empty")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{label} must contain non-empty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} contains duplicate values")
    return value


def require_utc_timestamp(value: Any) -> str:
    timestamp = require_non_empty_string(value, "generated_utc")
    if not timestamp.endswith("Z"):
        raise ValueError("generated_utc must end in Z")
    try:
        parsed = datetime.fromisoformat(timestamp[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("generated_utc must be a valid RFC3339 timestamp") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("generated_utc must use UTC")
    return timestamp


def verify_packet(packet: dict[str, Any], evidence_graph: dict[str, Any]) -> dict[str, Any]:
    missing = REQUIRED_TOP_LEVEL - packet.keys()
    extra = packet.keys() - REQUIRED_TOP_LEVEL
    if missing or extra:
        raise ValueError(
            f"packet top-level fields mismatch; missing={sorted(missing)} extra={sorted(extra)}"
        )

    if packet["schema_version"] != "1.0":
        raise ValueError("unsupported schema_version")
    require_utc_timestamp(packet["generated_utc"])
    if packet["repository"] != EXPECTED_REPOSITORY:
        raise ValueError("repository identity mismatch")
    if packet["status"] != EXPECTED_STATUS:
        raise ValueError("transaction packet must remain exploratory and non-binding")
    require_non_empty_string(packet["purpose"], "purpose")

    contact = require_non_empty_string(packet["public_contact_path"], "public_contact_path")
    parsed_contact = urlparse(contact)
    if parsed_contact.scheme != "https" or parsed_contact.netloc != "lumen-core.ai":
        raise ValueError("public_contact_path must use the official HTTPS LumenCore domain")

    options = packet["transaction_options"]
    if not isinstance(options, list) or not options:
        raise ValueError("transaction_options must be a non-empty list")
    option_ids: set[str] = set()
    structures: set[str] = set()
    for option in options:
        if not isinstance(option, dict):
            raise ValueError("every transaction option must be an object")
        if set(option) != {
            "id",
            "structure",
            "available_for_discussion",
            "requires",
            "does_not_authorize",
        }:
            raise ValueError("transaction option fields mismatch")
        option_id = require_non_empty_string(option["id"], "transaction option id")
        if option_id in option_ids:
            raise ValueError(f"duplicate transaction option id: {option_id}")
        option_ids.add(option_id)
        structure = require_non_empty_string(option["structure"], f"option {option_id} structure")
        structures.add(structure)
        if option["available_for_discussion"] is not True:
            raise ValueError(f"option {option_id} must be explicitly discussion-only")
        require_unique_string_list(option["requires"], f"option {option_id} requires")
        blocked = require_unique_string_list(
            option["does_not_authorize"], f"option {option_id} does_not_authorize"
        )
        if not any(item in blocked for item in ("binding_sale", "pre-agreement_use", "automatic_acquisition", "ownership_transfer", "automatic_parent_ip_assignment")):
            raise ValueError(f"option {option_id} lacks a clear non-transfer boundary")

    if structures != REQUIRED_OPTION_STRUCTURES:
        raise ValueError("transaction option structures do not match the canonical set")

    graph_nodes = evidence_graph.get("nodes")
    if not isinstance(graph_nodes, list):
        raise ValueError("evidence graph nodes must be a list")
    by_id = {
        node.get("id"): node
        for node in graph_nodes
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }

    assets = packet["public_assets"]
    if not isinstance(assets, list) or not assets:
        raise ValueError("public_assets must be a non-empty list")
    asset_ids: set[str] = set()
    for asset in assets:
        if not isinstance(asset, dict) or set(asset) != {
            "graph_node_id",
            "evidence_state",
            "role",
        }:
            raise ValueError("public asset fields mismatch")
        node_id = require_non_empty_string(asset["graph_node_id"], "graph_node_id")
        if node_id in asset_ids:
            raise ValueError(f"duplicate public asset: {node_id}")
        asset_ids.add(node_id)
        node = by_id.get(node_id)
        if node is None:
            raise ValueError(f"public asset references unknown evidence node: {node_id}")
        if asset["evidence_state"] != node.get("state"):
            raise ValueError(f"public asset state mismatch for {node_id}")
        require_non_empty_string(asset["role"], f"asset {node_id} role")

    require_unique_string_list(packet["diligence_requirements"], "diligence_requirements")
    require_unique_string_list(
        packet["private_until_qualified_diligence"],
        "private_until_qualified_diligence",
    )
    boundaries = set(
        require_unique_string_list(packet["claim_boundaries"], "claim_boundaries")
    )
    if boundaries != REQUIRED_CLAIM_BOUNDARIES:
        raise ValueError("claim boundaries do not match the canonical non-promotion set")

    founder_control = packet["founder_control"]
    if founder_control != REQUIRED_FOUNDER_CONTROL:
        raise ValueError("founder control must preserve all binding action and transfer locks")

    asking_price = packet["asking_price"]
    if not isinstance(asking_price, dict) or set(asking_price) != {
        "public",
        "amount",
        "currency",
        "rule",
    }:
        raise ValueError("asking_price fields mismatch")
    if asking_price["public"] is not False:
        raise ValueError("public asking price is prohibited before scoped diligence")
    if asking_price["amount"] is not None or asking_price["currency"] is not None:
        raise ValueError("asking price amount and currency must remain null")
    require_non_empty_string(asking_price["rule"], "asking price rule")

    return {
        "valid": True,
        "schema_version": packet["schema_version"],
        "status": packet["status"],
        "transaction_option_count": len(options),
        "public_asset_count": len(assets),
        "binding_sale_authorized": founder_control["binding_sale_authorized"],
        "ip_transfer_authorized": founder_control["ip_transfer_authorized"],
        "public_asking_price": asking_price["public"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "packet",
        nargs="?",
        default="config/strategic_transaction_packet_v1.json",
    )
    parser.add_argument(
        "--evidence-graph",
        default="config/evidence_graph_v1.json",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        packet = load_json_strict(Path(args.packet))
        graph = load_json_strict(Path(args.evidence_graph), max_bytes=2_000_000)
        result = verify_packet(packet, graph)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        failure = {"valid": False, "error": str(exc)}
        print(json.dumps(failure, sort_keys=True) if args.json else f"FAIL: {exc}")
        return 1

    print(json.dumps(result, sort_keys=True) if args.json else f"PASS: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
