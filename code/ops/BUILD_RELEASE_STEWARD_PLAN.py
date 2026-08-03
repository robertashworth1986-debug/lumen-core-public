import argparse
import hashlib
import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "out" / "ops" / "release_steward_plan_latest.json"
SCHEMA = "lumencore.release_steward_plan.v1"
MAX_CONTENT_SCAN_BYTES = 256 * 1024
READ_ONLY_GIT_COMMANDS = frozenset({"status", "diff", "rev-parse"})
SECRET_SUFFIXES = frozenset({".key", ".pem", ".p12", ".pfx"})
ARCHIVE_SUFFIXES = frozenset({".zip", ".7z", ".rar", ".tar", ".gz", ".pdf", ".docx", ".pptx", ".xlsx", ".stl"})
RUNTIME_PARTS = frozenset({"config", "control", "deploy", ".github"})
TEMPORARY_PARTS = frozenset({"tmp", "temp", "node_modules", "__pycache__", ".pytest_cache"})
SECRET_MARKERS = re.compile(
    rb"(?:-----BEGIN [A-Z ]+PRIVATE KEY-----|api[_-]?key\s*[:=]|client[_-]?secret\s*[:=]|password\s*[:=]|token\s*[:=])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class WorktreeChange:
    index_status: str
    worktree_status: str
    path: str
    original_path: str | None = None

    @property
    def is_untracked(self) -> bool:
        return self.index_status == "?" and self.worktree_status == "?"

    @property
    def is_deleted(self) -> bool:
        return self.index_status == "D" or self.worktree_status == "D"


def utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_utc(value: str | None) -> str:
    if value is None:
        return utc_now_text()
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("as-of time must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize_path(value: str) -> str:
    normalized = PurePosixPath(value.replace("\\", "/")).as_posix()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def parse_porcelain_v1_z(raw: bytes) -> list[WorktreeChange]:
    entries = [item for item in raw.split(b"\0") if item]
    changes: list[WorktreeChange] = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        if len(entry) < 3:
            raise ValueError("invalid porcelain status entry")
        status = entry[:2].decode("ascii", errors="replace")
        if entry[2:3] != b" ":
            raise ValueError("invalid porcelain path separator")
        path = normalize_path(entry[3:].decode("utf-8", errors="replace"))
        original_path: str | None = None
        if status[0] in {"R", "C"} or status[1] in {"R", "C"}:
            index += 1
            if index >= len(entries):
                raise ValueError("rename or copy status missing original path")
            original_path = normalize_path(entries[index].decode("utf-8", errors="replace"))
        changes.append(
            WorktreeChange(
                index_status=status[0],
                worktree_status=status[1],
                path=path,
                original_path=original_path,
            )
        )
        index += 1
    return changes


def run_git(repo_root: Path, args: Sequence[str]) -> tuple[int | None, bytes, bytes]:
    if not args or args[0] not in READ_ONLY_GIT_COMMANDS:
        raise ValueError("git command is outside the read-only allowlist")
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        completed = subprocess.run(
            ["git", "-c", "core.fsmonitor=false", "-C", str(repo_root), *args],
            capture_output=True,
            check=False,
            timeout=30,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, b"", b""
    return completed.returncode, completed.stdout, completed.stderr


def classify_path(path: str) -> set[str]:
    normalized = normalize_path(path)
    parts = tuple(part.lower() for part in PurePosixPath(normalized).parts)
    basename = parts[-1] if parts else ""
    suffix = PurePosixPath(basename).suffix.lower()
    categories: set[str] = set()

    if not parts:
        return {"INVALID_PATH"}
    if any(part in TEMPORARY_PARTS for part in parts):
        categories.add("TEMPORARY_OR_CACHE")
    if parts[0] == "grant_submissions" or (parts[0] == "out" and "private" in parts):
        categories.add("PRIVATE_OR_CONTROLLED")
    if parts[0] in {"deploy", ".github"} or "deploy" in parts:
        categories.add("DEPLOYMENT_OR_WORKFLOW")
    if parts[0] == "config" or parts[0] == "control":
        categories.add("RUNTIME_OR_POLICY_CONFIG")
    if parts[0] == "dashboard":
        categories.add("PUBLIC_SURFACE")
    if parts[0] in {"out", "output"}:
        categories.add("GENERATED_ARTIFACT")
    if suffix in ARCHIVE_SUFFIXES:
        categories.add("BINARY_OR_ARCHIVE")
    if (
        basename == ".env"
        or basename.startswith(".env.")
        or any(token in basename for token in ("credential", "private_key", "secret", "password"))
        or suffix in SECRET_SUFFIXES
    ):
        categories.add("SECRET_LIKE_FILENAME")
    if not categories:
        categories.add("SOURCE_OR_DOCUMENTATION")
    return categories


def lane_for_path(path: str) -> str:
    lowered = normalize_path(path).lower()
    if lowered.startswith("code/execution/") or "trading" in lowered or "eia_" in lowered:
        return "trading"
    if lowered.startswith("grant_submissions/") or "grant" in lowered or "opportunit" in lowered:
        return "funding"
    if lowered.startswith(("dashboard/", "deploy/", ".github/")):
        return "public_release"
    if lowered.startswith("docs/") or lowered.startswith("output/"):
        return "reviewer_artifacts"
    if lowered.startswith("tests/"):
        return "verification"
    return "platform"


def content_risk_tags(repo_root: Path, change: WorktreeChange) -> set[str]:
    if change.is_deleted:
        return set()
    categories = classify_path(change.path)
    if {"SECRET_LIKE_FILENAME", "BINARY_OR_ARCHIVE", "TEMPORARY_OR_CACHE"} & categories:
        return set()
    candidate = repo_root / PurePosixPath(change.path)
    try:
        if candidate.is_symlink() or not candidate.is_file() or candidate.stat().st_size > MAX_CONTENT_SCAN_BYTES:
            return set()
        sample = candidate.read_bytes()
    except OSError:
        return {"UNREADABLE_FILE"}
    return {"SECRET_MARKER_REVIEW_REQUIRED"} if SECRET_MARKERS.search(sample) else set()


def review_state(categories: set[str]) -> str:
    blockers = {
        "INVALID_PATH",
        "TEMPORARY_OR_CACHE",
        "PRIVATE_OR_CONTROLLED",
        "GENERATED_ARTIFACT",
        "BINARY_OR_ARCHIVE",
        "SECRET_LIKE_FILENAME",
        "SECRET_MARKER_REVIEW_REQUIRED",
        "UNREADABLE_FILE",
    }
    guarded = {"DEPLOYMENT_OR_WORKFLOW", "RUNTIME_OR_POLICY_CONFIG", "PUBLIC_SURFACE"}
    if blockers & categories:
        return "EXCLUDE_FROM_AUTOMATIC_RELEASE"
    if guarded & categories:
        return "HUMAN_SCOPE_REVIEW_REQUIRED"
    return "BOUNDED_COMMIT_CANDIDATE"


def build_plan_from_changes(
    repo_root: Path,
    changes: Iterable[WorktreeChange],
    *,
    generated_utc: str,
    diff_check_passed: bool,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    category_counts: Counter[str] = Counter()
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for change in sorted(changes, key=lambda item: item.path):
        categories = classify_path(change.path) | content_risk_tags(repo_root, change)
        state = review_state(categories)
        lane = lane_for_path(change.path)
        row = {
            "path": change.path,
            "original_path": change.original_path,
            "index_status": change.index_status,
            "worktree_status": change.worktree_status,
            "untracked": change.is_untracked,
            "deleted": change.is_deleted,
            "lane": lane,
            "categories": sorted(categories),
            "review_state": state,
        }
        rows.append(row)
        category_counts.update(categories)
        groups[(lane, state)].append(row)

    group_rows: list[dict[str, Any]] = []
    for (lane, state), items in sorted(groups.items()):
        pathspecs = [item["path"] for item in items]
        group_rows.append(
            {
                "group_id": f"{lane}:{state.lower()}",
                "lane": lane,
                "review_state": state,
                "path_count": len(items),
                "pathspecs": pathspecs,
                "commit_candidate": state == "BOUNDED_COMMIT_CANDIDATE" and diff_check_passed,
                "push_candidate": False,
                "publish_candidate": False,
            }
        )

    summary = {
        "change_count": len(rows),
        "bounded_commit_candidate_count": sum(row["review_state"] == "BOUNDED_COMMIT_CANDIDATE" for row in rows),
        "human_scope_review_count": sum(row["review_state"] == "HUMAN_SCOPE_REVIEW_REQUIRED" for row in rows),
        "automatic_release_exclusion_count": sum(row["review_state"] == "EXCLUDE_FROM_AUTOMATIC_RELEASE" for row in rows),
        "diff_check_passed": diff_check_passed,
        "status": "PLAN_REQUIRES_SCOPE_REVIEW" if rows else "WORKTREE_CLEAN",
    }
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_utc": generated_utc,
        "mode": "READ_ONLY_DIRTY_WORKTREE_AUDIT",
        "repository": {
            "path": str(repo_root),
            "branch": None,
            "head": None,
        },
        "summary": summary,
        "category_counts": dict(sorted(category_counts.items())),
        "changes": rows,
        "commit_groups": group_rows,
        "authority": {
            "audit_writes_git_index": False,
            "commit_authorized_by_plan": False,
            "push_authorized_by_plan": False,
            "publication_authorized_by_plan": False,
        },
        "claim_boundary": (
            "This plan classifies paths and bounded file metadata. It does not prove content correctness, public safety, test coverage, "
            "remote parity, or authorize a commit, push, deployment, or publication."
        ),
        "safest_next_action": (
            "Review each bounded group, run its relevant tests, commit only the exact reviewed paths, push that commit, then use the "
            "existing sealed public-release stage and canary gates before any publication."
        ),
    }
    payload["plan_sha256"] = canonical_sha256(payload)
    return payload


def build_plan(repo_root: Path = ROOT, *, as_of_utc: str | None = None) -> dict[str, Any]:
    root = repo_root.resolve()
    generated_utc = normalize_utc(as_of_utc)
    status_code, status_stdout, _ = run_git(root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    diff_code, _, _ = run_git(root, ["diff", "--check"])
    branch_code, branch_stdout, _ = run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"])
    head_code, head_stdout, _ = run_git(root, ["rev-parse", "HEAD"])
    if status_code != 0:
        raise RuntimeError("git status failed")
    payload = build_plan_from_changes(
        root,
        parse_porcelain_v1_z(status_stdout),
        generated_utc=generated_utc,
        diff_check_passed=diff_code == 0,
    )
    payload["repository"]["branch"] = branch_stdout.decode("utf-8", errors="replace").strip() if branch_code == 0 else None
    payload["repository"]["head"] = head_stdout.decode("utf-8", errors="replace").strip() if head_code == 0 else None
    payload["plan_sha256"] = canonical_sha256({key: value for key, value in payload.items() if key != "plan_sha256"})
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a fail-closed dirty-worktree commit and publication plan.")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--as-of-utc")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_plan(args.repo_root, as_of_utc=args.as_of_utc)
    if not args.no_write:
        write_json(args.output, payload)
    summary = payload["summary"]
    print(
        json.dumps(
            {
                "status": summary["status"],
                "change_count": summary["change_count"],
                "bounded_commit_candidate_count": summary["bounded_commit_candidate_count"],
                "human_scope_review_count": summary["human_scope_review_count"],
                "automatic_release_exclusion_count": summary["automatic_release_exclusion_count"],
                "plan_sha256": payload["plan_sha256"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
