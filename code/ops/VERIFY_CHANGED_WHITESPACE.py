#!/usr/bin/env python3
"""Enforce whitespace on the event-bound change, not unrelated base-branch work."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys


class ContextError(ValueError):
    pass


def commit_sha(value: object, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ContextError(f"invalid {label}")
    if value == "0" * 40:
        raise ContextError(f"zero {label}")
    return value


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    # Inspect actual commit objects; replacement refs must not redefine parents.
    env = dict(os.environ, GIT_NO_REPLACE_OBJECTS="1")
    return subprocess.run(
        ["git", *args], cwd=root, env=env, text=True, capture_output=True,
        timeout=30, check=False,
    )


def git_output(root: Path, *args: str) -> str:
    result = git(root, *args)
    if result.returncode:
        raise ContextError(f"Git context query failed: {result.stderr.strip()}")
    return result.stdout.strip()


def select_comparison(
    root: Path, event_name: str, event: dict, github_sha: str, github_ref: str,
) -> dict:
    expected = commit_sha(github_sha, "GITHUB_SHA")
    checkout = git_output(root, "rev-parse", "--verify", "HEAD^{commit}")
    if checkout != expected:
        raise ContextError("checkout does not equal GITHUB_SHA")
    if not isinstance(event, dict):
        raise ContextError("event must be an object")

    if event_name == "pull_request":
        number = event.get("number")
        if type(number) is not int or number <= 0:
            raise ContextError("invalid pull request number")
        if github_ref != f"refs/pull/{number}/merge":
            raise ContextError("pull request must use its tested merge ref")
        pr = event.get("pull_request")
        if not isinstance(pr, dict):
            raise ContextError("missing pull request context")
        head = commit_sha(pr.get("head", {}).get("sha"), "event PR head")
        event_base = commit_sha(pr.get("base", {}).get("sha"), "event PR base")
        row = git_output(root, "rev-list", "--parents", "--max-count=1", checkout).split()
        if len(row) != 3 or row[0] != checkout or row[2] != head:
            raise ContextError("tested merge must have two parents and the event head second")
        base = commit_sha(row[1], "tested merge first parent")
        git_output(root, "cat-file", "-e", f"{base}^{{commit}}")
        git_output(root, "cat-file", "-e", f"{head}^{{commit}}")
        # Compare the exact two trees. This includes PR changes and merge resolution,
        # but excludes bytes already present unchanged in the tested base parent.
        return dict(event=event_name, checkout=checkout, base=base, head=head,
                    event_base=event_base, event_base_matches_parent=event_base == base,
                    comparison=[base, checkout], basis="tested_merge_first_parent")

    if event_name == "push":
        if not github_ref.startswith("refs/heads/") or event.get("ref") != github_ref:
            raise ContextError("push ref mismatch")
        if event.get("deleted") is not False:
            raise ContextError("push must explicitly be non-deletion")
        if commit_sha(event.get("after"), "push after") != checkout:
            raise ContextError("push after does not equal checkout")
        before = commit_sha(event.get("before"), "push before")
        git_output(root, "cat-file", "-e", f"{before}^{{commit}}")
        # Retain the existing push three-dot comparison and its error behavior.
        return dict(event=event_name, checkout=checkout, base=before,
                    comparison=[f"{before}...{checkout}"], basis="push_event_before")

    raise ContextError(f"unsupported whitespace event: {event_name!r}")


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContextError(f"duplicate event key: {key}")
        result[key] = value
    return result


def main() -> int:
    try:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"),
                           object_pairs_hook=unique_object)
        context = select_comparison(Path.cwd(), os.environ["GITHUB_EVENT_NAME"], event,
                                    os.environ["GITHUB_SHA"], os.environ["GITHUB_REF"])
        print(json.dumps(context, sort_keys=True), flush=True)
        result = git(Path.cwd(), "diff", "--no-ext-diff", "--check", *context["comparison"])
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        return result.returncode
    except (ContextError, json.JSONDecodeError, KeyError, AttributeError, OSError,
            subprocess.SubprocessError) as exc:
        print(f"WHITESPACE_GATE_CONTEXT_INVALID: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
