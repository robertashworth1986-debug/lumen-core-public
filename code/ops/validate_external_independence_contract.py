#!/usr/bin/env python3
"""Apply strict evaluator-independence semantics to a validated replication docket."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

VERSION = "1.0.0"
PLACEHOLDER_VALUES = {
    "pending",
    "unknown",
    "unassigned",
    "not run",
    "not_run",
    "none",
    "n a",
    "na",
    "tbd",
    "to be determined",
}
INDEPENDENT_RELATIONSHIPS = {
    "independent",
    "independent evaluator",
    "independent external evaluator",
    "external independent evaluator",
}
AFFILIATION_MARKERS = {
    "founder",
    "self",
    "self review",
    "self reviewer",
    "lumencore",
    "robert ashworth",
    "founder controlled",
    "company controlled",
}
NONDISCLOSURE_MARKERS = {
    "not disclosed",
    "undisclosed",
    "declined to disclose",
    "no disclosure",
}
CONTROL_PREFIXES = (
    "evaluator ",
    "independent evaluator ",
    "external evaluator ",
    "evaluation laboratory ",
    "independent laboratory ",
)


class IndependenceError(ValueError):
    """Raised when evaluator-independence assertions are internally inconsistent."""


def _load_base_validator() -> ModuleType:
    path = Path(__file__).with_name("validate_external_replication_docket.py")
    spec = importlib.util.spec_from_file_location(
        "lumencore_external_replication_base", path
    )
    if spec is None or spec.loader is None:
        raise IndependenceError(f"cannot load base validator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = _load_base_validator()


def _canonical_words(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _required_text(parent: dict[str, Any], key: str, *, context: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise IndependenceError(f"{context}.{key} must be a non-empty string")
    normalized = _canonical_words(value)
    if normalized in PLACEHOLDER_VALUES:
        raise IndependenceError(f"{context}.{key} cannot remain {value!r}")
    return value.strip()


def _contains_affiliation_marker(value: str) -> str | None:
    normalized = _canonical_words(value)
    for marker in sorted(AFFILIATION_MARKERS, key=len, reverse=True):
        if re.search(rf"(?:^|\s){re.escape(marker)}(?:$|\s)", normalized):
            return marker
    return None


def _require_non_affiliated(value: str, *, context: str) -> None:
    marker = _contains_affiliation_marker(value)
    if marker:
        raise IndependenceError(
            f"{context} contains disallowed affiliation marker: {marker}"
        )


def _validate_control_statement(value: str, *, context: str) -> None:
    _require_non_affiliated(value, context=context)
    normalized = _canonical_words(value)
    if not normalized.startswith(CONTROL_PREFIXES):
        raise IndependenceError(
            f"{context} must identify evaluator or independent-laboratory control"
        )


def validate_independence_contract(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the base docket, then enforce strict independence consistency."""

    receipt = BASE.validate_docket(payload)
    status = receipt["status"]
    gates = payload["gates"]
    independence = payload["independence"]

    assigned = gates["evaluator_assigned"] is True
    active_evaluator_states = {
        "preregistered",
        "internal_complete",
        "external_complete",
    }
    if status in active_evaluator_states and not assigned:
        raise IndependenceError(f"{status} requires evaluator_assigned=true")

    if assigned:
        evaluator_name = _required_text(
            independence, "evaluator_name", context="independence"
        )
        organization = _required_text(
            independence, "organization", context="independence"
        )
        _required_text(independence, "role", context="independence")
        relationship = _required_text(
            independence, "relationship", context="independence"
        )
        conflict = _required_text(
            independence, "conflict_disclosure", context="independence"
        )
        data_control = _required_text(
            independence, "data_control", context="independence"
        )
        run_control = _required_text(
            independence, "run_control", context="independence"
        )
        analysis_control = _required_text(
            independence, "analysis_control", context="independence"
        )
        _required_text(
            independence, "publication_permission", context="independence"
        )

        _require_non_affiliated(evaluator_name, context="independence.evaluator_name")
        _require_non_affiliated(organization, context="independence.organization")
        conflict_value = _canonical_words(conflict)
        if any(marker in conflict_value for marker in NONDISCLOSURE_MARKERS):
            raise IndependenceError(
                "independence.conflict_disclosure must contain an actual disclosure"
            )

        relationship_value = _canonical_words(relationship)
        if relationship_value not in INDEPENDENT_RELATIONSHIPS:
            raise IndependenceError(
                "independence.relationship must use a canonical "
                "independent-evaluator value"
            )

        _validate_control_statement(
            data_control, context="independence.data_control"
        )
        _validate_control_statement(run_control, context="independence.run_control")
        _validate_control_statement(
            analysis_control, context="independence.analysis_control"
        )

    receipt = dict(receipt)
    receipt.update(
        {
            "independence_contract_valid": True,
            "independence_contract_version": VERSION,
            "evaluator_assignment_consistent": True,
            "claim_boundary_note": (
                "This gate checks internal consistency only; it does not authenticate "
                "the evaluator, organization, signature, or asserted control."
            ),
        }
    )
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "docket",
        type=Path,
        nargs="?",
        default=Path("config/external_replication_docket_v1.json"),
    )
    parser.add_argument("--max-bytes", type=int, default=BASE.DEFAULT_MAX_BYTES)
    args = parser.parse_args(argv)

    try:
        payload = BASE.load_docket(args.docket, max_bytes=args.max_bytes)
        receipt = validate_independence_contract(payload)
    except (BASE.DocketError, IndependenceError, OSError, ValueError) as exc:
        print(
            json.dumps({"valid": False, "error": str(exc)}, indent=2),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
