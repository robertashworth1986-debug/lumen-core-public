from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PUBLIC_MAIN_REF = "refs/remotes/origin/main"
DEFAULT_OUTPUT = ROOT / "out" / "ops" / "local_public_branch_drift_gate_latest.json"

SCHEMA = "lumencore.local_public_branch_drift_gate.v1"
MODE = "LOCAL_READ_ONLY_GIT_OBSERVER"
READ_ONLY_GIT_COMMANDS = frozenset(
    {"merge-base", "rev-list", "rev-parse", "status", "symbolic-ref"}
)
COMMIT_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
SAFE_REF_RE = re.compile(r"^[A-Za-z0-9._/-]+$")

CLAIM_BOUNDARY = (
    "This local receipt reports bounded Git graph and worktree observations only. "
    "It does not prove that local changes are committed, reviewed, pushed, merged, "
    "published, deployed, or present on public main. Any unresolved ref, detached "
    "HEAD, divergence, or dirty tracked or untracked state blocks a claim that the "
    "local work is on public main."
)
SAFEST_NEXT_ACTION = (
    "After human review, selective-port approved changes from a clean worktree "
    "created at the current public-main commit; rerun focused and broad checks "
    "there, then review the resulting diff. Never merge this branch wholesale."
)

UNRESOLVED_BLOCKERS = frozenset(
    {
        "REPOSITORY_ROOT_MISSING",
        "NOT_A_GIT_WORKTREE",
        "CURRENT_HEAD_UNRESOLVED",
        "CURRENT_BRANCH_UNRESOLVED",
        "UPSTREAM_REF_UNRESOLVED",
        "UPSTREAM_HASH_UNRESOLVED",
        "PUBLIC_MAIN_REF_UNRESOLVED",
        "MERGE_BASE_UNRESOLVED",
        "AHEAD_BEHIND_UNRESOLVED",
        "WORKTREE_STATUS_UNRESOLVED",
    }
)


def utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def normalize_utc(value: str | None) -> str:
    if value is None:
        return utc_now_text()
    candidate = value.strip()
    parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("as-of time must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(
        timespec="seconds"
    ).replace("+00:00", "Z")


def canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_public_main_ref(value: str) -> str:
    ref = value.strip()
    if (
        not ref.startswith("refs/remotes/")
        or not SAFE_REF_RE.fullmatch(ref)
        or ".." in ref
        or "//" in ref
        or ref.endswith(("/", ".", ".lock"))
    ):
        raise ValueError("public-main ref must be a canonical remote-tracking ref")
    return ref


def _run_git(repo_root: Path, args: Sequence[str]) -> dict[str, Any]:
    if not args or args[0] not in READ_ONLY_GIT_COMMANDS:
        raise ValueError("git command is outside the read-only allowlist")

    command = [
        "git",
        "-c",
        "core.fsmonitor=false",
        "-C",
        str(repo_root),
        *args,
    ]
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            timeout=15,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"returncode": None, "stdout": b""}
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
    }


def _successful_text(result: dict[str, Any]) -> str | None:
    if result["returncode"] != 0:
        return None
    text = result["stdout"].decode("utf-8", errors="replace").strip()
    return text or None


def _commit_hash(result: dict[str, Any]) -> str | None:
    text = _successful_text(result)
    if text is None:
        return None
    candidate = text.lower()
    return candidate if COMMIT_RE.fullmatch(candidate) else None


def _parse_ahead_behind(result: dict[str, Any]) -> tuple[int, int] | None:
    text = _successful_text(result)
    if text is None:
        return None
    fields = text.split()
    if len(fields) != 2:
        return None
    try:
        ahead, behind = (int(field) for field in fields)
    except ValueError:
        return None
    if ahead < 0 or behind < 0:
        return None
    return ahead, behind


def _parse_porcelain_counts(
    result: dict[str, Any],
) -> tuple[int, int] | None:
    if result["returncode"] != 0:
        return None
    records = result["stdout"].split(b"\0")
    tracked = 0
    untracked = 0
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if len(record) < 3 or record[2:3] != b" ":
            return None
        state = record[:2]
        if state == b"??":
            untracked += 1
        elif state != b"!!":
            tracked += 1
        if b"R" in state or b"C" in state:
            if index >= len(records) or not records[index]:
                return None
            index += 1
    return tracked, untracked


def _blocker(
    code: str,
    message: str,
    *,
    count: int | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {"code": code, "message": message}
    if count is not None:
        row["count"] = count
    return row


def build_gate(
    repo_root: Path,
    *,
    public_main_ref: str = DEFAULT_PUBLIC_MAIN_REF,
    as_of_utc: str | None = None,
) -> dict[str, Any]:
    repo_root = Path(repo_root).resolve()
    public_main_ref = validate_public_main_ref(public_main_ref)
    generated_at = normalize_utc(as_of_utc)

    state: dict[str, Any] = {
        "is_git_worktree": False,
        "head_attached": False,
        "current_branch": None,
        "current_head": None,
        "upstream_ref": None,
        "upstream_hash": None,
        "public_main_ref": public_main_ref,
        "public_main_hash": None,
        "merge_base": None,
        "ahead_of_public_main": None,
        "behind_public_main": None,
        "dirty_tracked_count": None,
        "dirty_untracked_count": None,
        "dirty_total_count": None,
    }
    blockers: list[dict[str, Any]] = []

    if not repo_root.is_dir():
        blockers.append(
            _blocker(
                "REPOSITORY_ROOT_MISSING",
                "The requested local repository root is unavailable.",
            )
        )
    else:
        inside = _successful_text(
            _run_git(repo_root, ["rev-parse", "--is-inside-work-tree"])
        )
        state["is_git_worktree"] = inside == "true"
        if not state["is_git_worktree"]:
            blockers.append(
                _blocker(
                    "NOT_A_GIT_WORKTREE",
                    "The requested root is not a resolved Git worktree.",
                )
            )
        else:
            head = _commit_hash(
                _run_git(repo_root, ["rev-parse", "--verify", "HEAD"])
            )
            state["current_head"] = head
            if head is None:
                blockers.append(
                    _blocker(
                        "CURRENT_HEAD_UNRESOLVED",
                        "The current HEAD commit could not be resolved.",
                    )
                )

            branch = _successful_text(
                _run_git(
                    repo_root,
                    ["symbolic-ref", "--quiet", "--short", "HEAD"],
                )
            )
            if branch is None:
                if head is not None:
                    blockers.append(
                        _blocker(
                            "DETACHED_HEAD",
                            "HEAD is detached, so branch provenance is incomplete.",
                        )
                    )
                else:
                    blockers.append(
                        _blocker(
                            "CURRENT_BRANCH_UNRESOLVED",
                            "The current branch could not be resolved.",
                        )
                    )
            else:
                state["head_attached"] = True
                state["current_branch"] = branch
                upstream_ref = _successful_text(
                    _run_git(
                        repo_root,
                        [
                            "rev-parse",
                            "--abbrev-ref",
                            "--symbolic-full-name",
                            "@{upstream}",
                        ],
                    )
                )
                state["upstream_ref"] = upstream_ref
                if upstream_ref is None:
                    blockers.append(
                        _blocker(
                            "UPSTREAM_REF_UNRESOLVED",
                            "The current branch upstream ref could not be resolved.",
                        )
                    )
                upstream_hash = _commit_hash(
                    _run_git(
                        repo_root,
                        ["rev-parse", "--verify", "@{upstream}^{commit}"],
                    )
                )
                state["upstream_hash"] = upstream_hash
                if upstream_hash is None:
                    blockers.append(
                        _blocker(
                            "UPSTREAM_HASH_UNRESOLVED",
                            "The current branch upstream commit could not be resolved.",
                        )
                    )

            public_hash = _commit_hash(
                _run_git(
                    repo_root,
                    [
                        "rev-parse",
                        "--verify",
                        f"{public_main_ref}^{{commit}}",
                    ],
                )
            )
            state["public_main_hash"] = public_hash
            if public_hash is None:
                blockers.append(
                    _blocker(
                        "PUBLIC_MAIN_REF_UNRESOLVED",
                        "The configured local public-main ref could not be resolved.",
                    )
                )

            if head is not None and public_hash is not None:
                merge_base = _commit_hash(
                    _run_git(
                        repo_root,
                        ["merge-base", "HEAD", public_main_ref],
                    )
                )
                state["merge_base"] = merge_base
                if merge_base is None:
                    blockers.append(
                        _blocker(
                            "MERGE_BASE_UNRESOLVED",
                            "No merge base could be resolved for HEAD and public main.",
                        )
                    )

                counts = _parse_ahead_behind(
                    _run_git(
                        repo_root,
                        [
                            "rev-list",
                            "--left-right",
                            "--count",
                            f"HEAD...{public_main_ref}",
                        ],
                    )
                )
                if counts is None:
                    blockers.append(
                        _blocker(
                            "AHEAD_BEHIND_UNRESOLVED",
                            "Ahead and behind counts could not be resolved.",
                        )
                    )
                else:
                    ahead, behind = counts
                    state["ahead_of_public_main"] = ahead
                    state["behind_public_main"] = behind
                    if ahead:
                        blockers.append(
                            _blocker(
                                "HEAD_AHEAD_OF_PUBLIC_MAIN",
                                "HEAD contains commits absent from public main.",
                                count=ahead,
                            )
                        )
                    if behind:
                        blockers.append(
                            _blocker(
                                "HEAD_BEHIND_PUBLIC_MAIN",
                                "Public main contains commits absent from HEAD.",
                                count=behind,
                            )
                        )
                    if head != public_hash and not (ahead or behind):
                        blockers.append(
                            _blocker(
                                "HEAD_HASH_DIFFERS_FROM_PUBLIC_MAIN",
                                "HEAD does not exactly match the public-main commit.",
                            )
                        )

            worktree_counts = _parse_porcelain_counts(
                _run_git(
                    repo_root,
                    [
                        "status",
                        "--porcelain=v1",
                        "-z",
                        "--untracked-files=all",
                    ],
                )
            )
            if worktree_counts is None:
                blockers.append(
                    _blocker(
                        "WORKTREE_STATUS_UNRESOLVED",
                        "Tracked and untracked worktree counts could not be resolved.",
                    )
                )
            else:
                tracked, untracked = worktree_counts
                state["dirty_tracked_count"] = tracked
                state["dirty_untracked_count"] = untracked
                state["dirty_total_count"] = tracked + untracked
                if tracked:
                    blockers.append(
                        _blocker(
                            "DIRTY_TRACKED_CHANGES",
                            "Tracked worktree changes are present.",
                            count=tracked,
                        )
                    )
                if untracked:
                    blockers.append(
                        _blocker(
                            "DIRTY_UNTRACKED_CHANGES",
                            "Untracked worktree paths are present.",
                            count=untracked,
                        )
                    )

    blocker_codes = {row["code"] for row in blockers}
    detached = "DETACHED_HEAD" in blocker_codes
    unresolved = bool(blocker_codes & UNRESOLVED_BLOCKERS)
    diverged = (
        isinstance(state["ahead_of_public_main"], int)
        and isinstance(state["behind_public_main"], int)
        and (
            state["ahead_of_public_main"] > 0
            or state["behind_public_main"] > 0
            or state["current_head"] != state["public_main_hash"]
        )
    )
    dirty = (
        isinstance(state["dirty_total_count"], int)
        and state["dirty_total_count"] > 0
    )

    if unresolved:
        status = "BLOCKED_GIT_STATE_UNRESOLVED"
    elif detached:
        status = "BLOCKED_DETACHED_HEAD"
    elif diverged and dirty:
        status = "BLOCKED_DIVERGED_AND_DIRTY"
    elif diverged:
        status = "BLOCKED_DIVERGED_FROM_PUBLIC_MAIN"
    elif dirty:
        status = "BLOCKED_DIRTY_WORKTREE"
    elif blockers:
        status = "BLOCKED_GIT_STATE_INCOMPLETE"
    else:
        status = "PASS_CLEAN_AT_PUBLIC_MAIN_COMMIT"

    blockers.sort(key=lambda row: row["code"])
    gate: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": generated_at,
        "mode": MODE,
        "git_state": state,
        "summary": {
            "status": status,
            "public_main_claim_allowed": status
            == "PASS_CLEAN_AT_PUBLIC_MAIN_COMMIT",
            "head_matches_public_main": (
                state["current_head"] is not None
                and state["current_head"] == state["public_main_hash"]
            ),
            "clean_worktree": state["dirty_total_count"] == 0,
            "diverged_from_public_main": diverged,
            "blocker_count": len(blockers),
        },
        "blockers": blockers,
        "claim_boundary": CLAIM_BOUNDARY,
        "safest_next_action": SAFEST_NEXT_ACTION,
        "capability_boundary": {
            "local_git_observation_only": True,
            "read_only_git_subprocesses_only": True,
            "network_access_performed": False,
            "fetch_performed": False,
            "checkout_performed": False,
            "merge_performed": False,
            "rebase_performed": False,
            "stash_performed": False,
            "commit_performed": False,
            "push_performed": False,
            "worktree_mutation_performed": False,
            "changed_path_names_recorded": False,
            "file_contents_recorded": False,
        },
    }
    gate["gate_sha256"] = canonical_sha256(gate)
    return gate


def write_gate(gate: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(gate, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a local-only, fail-closed public-main branch-drift gate."
    )
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument(
        "--public-main-ref",
        default=DEFAULT_PUBLIC_MAIN_REF,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--as-of-utc")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return nonzero when the public-main claim is blocked.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    gate = build_gate(
        args.repo_root,
        public_main_ref=args.public_main_ref,
        as_of_utc=args.as_of_utc,
    )
    write_gate(gate, args.output)
    state = gate["git_state"]
    print(f"LOCAL_PUBLIC_BRANCH_DRIFT_STATUS={gate['summary']['status']}")
    print(
        "LOCAL_PUBLIC_BRANCH_DRIFT_AHEAD_BEHIND="
        f"{state['ahead_of_public_main']}/{state['behind_public_main']}"
    )
    print(
        "LOCAL_PUBLIC_BRANCH_DRIFT_DIRTY_TRACKED_UNTRACKED="
        f"{state['dirty_tracked_count']}/{state['dirty_untracked_count']}"
    )
    print(f"LOCAL_PUBLIC_BRANCH_DRIFT_GATE_SHA256={gate['gate_sha256']}")
    print(f"LOCAL_PUBLIC_BRANCH_DRIFT_OUTPUT={args.output}")
    if args.strict and not gate["summary"]["public_main_claim_allowed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
