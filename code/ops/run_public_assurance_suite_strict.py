#!/usr/bin/env python3
"""Run the public assurance suite with strict independence and source-custody checks."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence

VERSION = "1.0.0"


class StrictAssuranceError(ValueError):
    """Raised when the strict public-assurance boundary fails closed."""


def _load_base_runner() -> ModuleType:
    path = Path(__file__).with_name("run_public_assurance_suite.py")
    spec = importlib.util.spec_from_file_location(
        "lumencore_public_assurance_base", path
    )
    if spec is None or spec.loader is None:
        raise StrictAssuranceError(f"cannot load base assurance runner: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = _load_base_runner()


def strict_default_checks() -> tuple[dict[str, Any], ...]:
    checks = copy.deepcopy(BASE.DEFAULT_CHECKS)
    found = False
    for spec in checks:
        if spec.get("check_id") != "external_replication_docket_v1":
            continue
        found = True
        spec["command"] = (
            "{python}",
            "code/ops/validate_external_independence_contract.py",
            "config/external_replication_docket_v1.json",
        )
        spec["sources"] = tuple(spec["sources"]) + (
            "code/ops/validate_external_independence_contract.py",
        )
        spec["expected"] = dict(spec["expected"])
        spec["expected"]["independence_contract_valid"] = True
    if not found:
        raise StrictAssuranceError(
            "base suite is missing external_replication_docket_v1"
        )
    return tuple(checks)


STRICT_DEFAULT_CHECKS = strict_default_checks()


def _source_snapshot(
    root: Path, checks: Sequence[Mapping[str, Any]]
) -> dict[str, dict[str, Any]]:
    snapshot: dict[str, dict[str, Any]] = {}
    casefold_paths: dict[str, str] = {}
    for spec in checks:
        check_id = BASE._check_id(spec.get("check_id"))
        raw_sources = spec.get("sources")
        if not isinstance(raw_sources, (tuple, list)) or not raw_sources:
            raise StrictAssuranceError(
                f"{check_id}.sources must be a non-empty array"
            )
        for raw in raw_sources:
            canonical = BASE._canonical_path(raw)
            marker = canonical.casefold()
            prior_case = casefold_paths.get(marker)
            if prior_case is not None and prior_case != canonical:
                raise StrictAssuranceError(
                    "case-insensitive source-path collision: "
                    f"{prior_case} vs {canonical}"
                )
            casefold_paths[marker] = canonical
            digest, byte_count = BASE._sha256_file(
                BASE._resolve_under_root(root, canonical)
            )
            observed = {"path": canonical, "sha256": digest, "bytes": byte_count}
            prior = snapshot.get(canonical)
            if prior is not None and prior != observed:
                raise StrictAssuranceError(
                    f"source changed while preparing snapshot: {canonical}"
                )
            snapshot[canonical] = observed
    return snapshot


def run_strict_suite(
    root: Path,
    *,
    commit: str = "unknown",
    checks: Sequence[Mapping[str, Any]] = STRICT_DEFAULT_CHECKS,
    timeout_seconds: int = BASE.DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    root = root.resolve()
    before = _source_snapshot(root, checks)
    receipt = BASE.run_suite(
        root,
        commit=commit,
        checks=checks,
        timeout_seconds=timeout_seconds,
    )
    after = _source_snapshot(root, checks)
    if before != after:
        changed = sorted(
            path
            for path in set(before) | set(after)
            if before.get(path) != after.get(path)
        )
        raise StrictAssuranceError(
            "listed source bytes changed during assurance execution: "
            + ", ".join(changed)
        )

    receipt_sources = {item["path"]: item for item in receipt["source_files"]}
    if receipt_sources != before:
        raise StrictAssuranceError(
            "aggregate receipt source index does not match the strict pre-run snapshot"
        )

    strict_receipt = dict(receipt)
    strict_receipt.update(
        {
            "strict_runner_version": VERSION,
            "source_pre_post_match": True,
            "strict_independence_check": "external_replication_docket_v1",
        }
    )
    boundary = copy.deepcopy(strict_receipt["claim_boundary"])
    boundary["proves"].append(
        "The listed source files matched the receipt immediately before "
        "and after execution."
    )
    boundary["does_not_prove"].append(
        "Absence of a transient in-process mutation, evaluator identity, "
        "signature authenticity, or external control"
    )
    strict_receipt["claim_boundary"] = boundary
    return strict_receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--commit", default="unknown")
    parser.add_argument(
        "--timeout-seconds", type=int, default=BASE.DEFAULT_TIMEOUT_SECONDS
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    try:
        receipt = run_strict_suite(
            args.root,
            commit=args.commit,
            timeout_seconds=args.timeout_seconds,
        )
    except (BASE.AssuranceError, StrictAssuranceError, OSError, ValueError) as exc:
        print(
            json.dumps({"valid": False, "error": str(exc)}, indent=2),
            file=sys.stderr,
        )
        return 1

    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
