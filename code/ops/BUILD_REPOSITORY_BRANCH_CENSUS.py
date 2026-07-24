#!/usr/bin/env python3
"""Build a fail-closed census of every fetched remote branch in this repository."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Any, Iterable

MAX_JSON_BYTES = 2_000_000
EXPECTED_REPOSITORY = "robertashworth1986-debug/lumen-core-public"


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_non_finite(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


def load_json_strict(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError(f"JSON exceeds maximum size of {MAX_JSON_BYTES} bytes")
    result = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_non_finite,
    )
    if not isinstance(result, dict):
        raise ValueError("JSON root must be an object")
    return result


def run_git(arguments: list[str], *, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(arguments)} failed with exit {completed.returncode}: "
            f"{completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def list_remote_branches(remote: str = "origin") -> dict[str, str]:
    prefix = f"refs/remotes/{remote}/"
    output = run_git(
        [
            "for-each-ref",
            "--format=%(refname)|%(objectname)",
            f"refs/remotes/{remote}",
        ]
    )
    branches: dict[str, str] = {}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        refname, separator, sha = line.partition("|")
        if not separator or not refname.startswith(prefix):
            raise ValueError(f"malformed remote branch record: {line}")
        name = refname[len(prefix) :]
        if name == "HEAD":
            continue
        if not name or name.startswith("/") or ".." in name:
            raise ValueError(f"unsafe remote branch name: {name!r}")
        if name in branches:
            raise ValueError(f"duplicate remote branch: {name}")
        if len(sha) != 40 or any(character not in "0123456789abcdef" for character in sha):
            raise ValueError(f"invalid commit SHA for branch {name}: {sha}")
        branches[name] = sha
    if not branches:
        raise ValueError("no remote branches were fetched")
    return branches


def is_ancestor(candidate_sha: str, default_sha: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", candidate_sha, default_sha],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    raise RuntimeError(
        f"git merge-base failed with exit {completed.returncode}: {completed.stderr.strip()}"
    )


def validate_registry(registry: dict[str, Any]) -> list[dict[str, Any]]:
    if registry.get("schema_version") != "1.0":
        raise ValueError("unsupported registry schema_version")
    if registry.get("repository") != EXPECTED_REPOSITORY:
        raise ValueError("registry repository identity mismatch")
    if registry.get("default_branch") != "main":
        raise ValueError("registry default branch must be main")
    entries = registry.get("observed_pr_heads")
    if not isinstance(entries, list) or not entries:
        raise ValueError("observed_pr_heads must be a non-empty list")

    seen_numbers: set[int] = set()
    seen_heads: set[str] = set()
    allowed_states = {"open", "merged", "closed_unmerged"}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"number", "state", "head"}:
            raise ValueError("every observed PR head must contain number, state, and head")
        number = entry["number"]
        state = entry["state"]
        head = entry["head"]
        if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
            raise ValueError("PR number must be a positive integer")
        if number in seen_numbers:
            raise ValueError(f"duplicate PR number: {number}")
        seen_numbers.add(number)
        if state not in allowed_states:
            raise ValueError(f"PR #{number}: invalid state {state!r}")
        if not isinstance(head, str) or not head or head.startswith("/") or ".." in head:
            raise ValueError(f"PR #{number}: unsafe head branch")
        if head in seen_heads:
            raise ValueError(f"duplicate PR head branch: {head}")
        seen_heads.add(head)
    return entries


def classify_branches(
    branches: dict[str, str],
    registry_entries: Iterable[dict[str, Any]],
    default_branch: str,
) -> dict[str, Any]:
    if default_branch not in branches:
        raise ValueError(f"default branch {default_branch!r} was not fetched")

    by_head = {entry["head"]: entry for entry in registry_entries}
    missing_open_heads = sorted(
        entry["head"]
        for entry in registry_entries
        if entry["state"] == "open" and entry["head"] not in branches
    )
    if missing_open_heads:
        raise ValueError(f"open PR head branches missing from remote census: {missing_open_heads}")

    unknown = sorted(name for name in branches if name != default_branch and name not in by_head)
    deleted_historical = sorted(
        entry["head"]
        for entry in registry_entries
        if entry["state"] != "open" and entry["head"] not in branches
    )

    return {
        "unknown_non_pr_branches": unknown,
        "missing_open_pr_heads": missing_open_heads,
        "deleted_historical_pr_heads": deleted_historical,
    }


def build_receipt(registry_path: Path, *, remote: str = "origin") -> dict[str, Any]:
    registry = load_json_strict(registry_path)
    entries = validate_registry(registry)
    default_branch = registry["default_branch"]
    branches = list_remote_branches(remote)
    classification = classify_branches(branches, entries, default_branch)
    default_sha = branches[default_branch]
    by_head = {entry["head"]: entry for entry in entries}

    records: list[dict[str, Any]] = []
    for branch in sorted(branches):
        sha = branches[branch]
        pr = by_head.get(branch)
        records.append(
            {
                "branch": branch,
                "sha": sha,
                "is_default": branch == default_branch,
                "merged_into_default": branch == default_branch or is_ancestor(sha, default_sha),
                "observed_pr_number": pr["number"] if pr else None,
                "observed_pr_state": pr["state"] if pr else None,
            }
        )

    return {
        "schema_version": "1.0",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "repository": EXPECTED_REPOSITORY,
        "remote": remote,
        "default_branch": default_branch,
        "default_sha": default_sha,
        "remote_branch_count": len(records),
        "observed_pr_head_count": len(entries),
        "unknown_non_pr_branch_count": len(classification["unknown_non_pr_branches"]),
        **classification,
        "branches": records,
        "valid": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("config/known_pr_head_branches_v1.json"),
    )
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    receipt = build_receipt(args.registry, remote=args.remote)
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
