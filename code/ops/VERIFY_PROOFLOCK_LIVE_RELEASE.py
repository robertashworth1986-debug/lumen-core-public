from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_DIR = ROOT / "build_week" / "prooflock_console"
DEFAULT_BASE_URL = "https://lumen-core.ai/build_week/prooflock_console/"
DEFAULT_JSON = ROOT / "docs" / "OPENAI_BUILD_WEEK_PROOFLOCK_PREDEPLOYMENT_GATE_2026-07-18.json"
DEFAULT_MARKDOWN = DEFAULT_JSON.with_suffix(".md")
SCHEMA = "lumencore.prooflock_live_release_gate.v1"
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{7,64}$")
CLAIM_BOUNDARY = (
    "This gate compares public HTTP response bytes with deployable source blobs loaded "
    "from the named Git commit at one observation time. A full match establishes only "
    "observed byte identity for the listed files. It does not prove uninterrupted "
    "availability, correct server configuration, security, engineering performance, "
    "external validation, Build Week eligibility, selection, or authority to submit."
)

FetchResult = dict[str, Any]
Fetcher = Callable[[str, float], FetchResult]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return sha256_bytes(encoded)


def normalize_base_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base URL must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password:
        raise ValueError("base URL must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("base URL must not contain a query or fragment")
    path = parsed.path if parsed.path.endswith("/") else f"{parsed.path}/"
    return urllib.parse.urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), path, "", "")
    )


def validate_source_commit(value: str) -> str:
    normalized = value.strip().lower()
    if not COMMIT_PATTERN.fullmatch(normalized):
        raise ValueError("source commit must be a 7-64 character hexadecimal Git id")
    return normalized


def git_head(root: Path = ROOT) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return validate_source_commit(completed.stdout)


def source_files(source_dir: Path) -> list[Path]:
    if not source_dir.is_dir():
        raise ValueError("deployable source directory is missing")
    rows = sorted(
        (path for path in source_dir.iterdir() if path.is_file() or path.is_symlink()),
        key=lambda path: path.name.lower(),
    )
    if not rows:
        raise ValueError("deployable source directory contains no files")
    return rows


def git_source_snapshot(
    *, root: Path, source_dir: Path, source_commit: str
) -> tuple[str, dict[str, bytes], dict[str, Any]]:
    resolved_root = root.resolve()
    resolved_source = source_dir.resolve()
    try:
        relative_source = resolved_source.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("deployable source directory must be inside the Git root") from exc
    if relative_source == Path("."):
        raise ValueError("deployable source directory must not be the Git root")

    requested_commit = validate_source_commit(source_commit)
    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", f"{requested_commit}^{{commit}}"],
        cwd=resolved_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    resolved_commit = validate_source_commit(resolved.stdout)
    relative_posix = relative_source.as_posix()
    listed = subprocess.run(
        ["git", "ls-tree", "-r", "-z", resolved_commit, "--", relative_posix],
        cwd=resolved_root,
        check=True,
        capture_output=True,
        timeout=10,
    )

    prefix = f"{relative_posix.rstrip('/')}/"
    commit_files: dict[str, bytes] = {}
    commit_symlinks: list[str] = []
    for raw_entry in listed.stdout.split(b"\0"):
        if not raw_entry:
            continue
        metadata, raw_path = raw_entry.split(b"\t", 1)
        mode, object_type, object_id = metadata.decode("ascii").split(" ", 2)
        repo_path = raw_path.decode("utf-8", errors="surrogateescape")
        if not repo_path.startswith(prefix):
            continue
        filename = repo_path[len(prefix) :]
        if not filename or "/" in filename or object_type != "blob":
            continue
        blob = subprocess.run(
            ["git", "cat-file", "blob", object_id],
            cwd=resolved_root,
            check=True,
            capture_output=True,
            timeout=10,
        ).stdout
        commit_files[filename] = blob
        if mode == "120000":
            commit_symlinks.append(filename)

    if not commit_files:
        raise ValueError("named commit contains no deployable source files")

    local_files: dict[str, bytes] = {}
    local_symlinks: list[str] = []
    for path in source_files(source_dir):
        if path.is_symlink():
            local_symlinks.append(path.name)
        else:
            local_files[path.name] = path.read_bytes()

    all_names = sorted(set(commit_files) | set(local_files) | set(local_symlinks))
    mismatched_files = [
        name
        for name in all_names
        if name in local_symlinks
        or name not in commit_files
        or name not in local_files
        or commit_files[name] != local_files[name]
    ]
    verified = not commit_symlinks
    public_provenance = {
        "checked": True,
        "verified": verified,
        "resolved_commit": resolved_commit,
        "tracked_file_count": len(commit_files),
        "worktree_file_count": len(local_files) + len(local_symlinks),
        "worktree_match_count": len(all_names) - len(mismatched_files),
        "worktree_matches_commit": not local_symlinks and not mismatched_files,
        "mismatched_files": mismatched_files,
        "commit_symlinks_rejected": sorted(commit_symlinks),
        "worktree_symlinks_rejected": sorted(local_symlinks),
    }
    return resolved_commit, commit_files, public_provenance


def request_url(base_url: str, filename: str, source_commit: str) -> str:
    encoded_name = urllib.parse.quote(filename, safe="")
    target = urllib.parse.urljoin(base_url, encoded_name)
    base = urllib.parse.urlsplit(base_url)
    parsed = urllib.parse.urlsplit(target)
    if (parsed.scheme, parsed.netloc) != (base.scheme, base.netloc):
        raise ValueError("release file URL escaped the configured origin")
    if not parsed.path.startswith(base.path):
        raise ValueError("release file URL escaped the configured path")
    return urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urllib.parse.urlencode({"prooflock_audit": source_commit[:12]}),
            "",
        )
    )


def fetch_http_bytes(url: str, timeout_seconds: float) -> FetchResult:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "*/*",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "LumenCore-ProofLock-Live-Gate/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return {
            "status": int(response.status),
            "body": response.read(),
            "final_url": response.geturl(),
        }


def same_public_target(requested_url: str, final_url: str) -> bool:
    requested = urllib.parse.urlsplit(requested_url)
    final = urllib.parse.urlsplit(final_url)
    return (
        requested.scheme.lower(),
        requested.netloc.lower(),
        requested.path,
    ) == (final.scheme.lower(), final.netloc.lower(), final.path)


def verify_live_release(
    *,
    source_dir: Path,
    base_url: str,
    source_commit: str,
    expected_files: Mapping[str, bytes] | None = None,
    source_provenance: Mapping[str, Any] | None = None,
    fetcher: Fetcher = fetch_http_bytes,
    generated_utc: str | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    normalized_base = normalize_base_url(base_url)
    normalized_commit = validate_source_commit(source_commit)
    if timeout_seconds <= 0:
        raise ValueError("timeout must be positive")

    provenance = {
        "checked": bool(source_provenance and source_provenance.get("checked")),
        "verified": bool(source_provenance and source_provenance.get("verified")),
        "resolved_commit": str(
            source_provenance.get("resolved_commit", "")
            if source_provenance
            else ""
        ),
        "tracked_file_count": int(
            source_provenance.get("tracked_file_count", 0)
            if source_provenance
            else 0
        ),
        "worktree_file_count": int(
            source_provenance.get("worktree_file_count", 0)
            if source_provenance
            else 0
        ),
        "worktree_match_count": int(
            source_provenance.get("worktree_match_count", 0)
            if source_provenance
            else 0
        ),
        "worktree_matches_commit": bool(
            source_provenance.get("worktree_matches_commit", False)
            if source_provenance
            else False
        ),
        "mismatched_files": sorted(
            str(name)
            for name in (
                source_provenance.get("mismatched_files", [])
                if source_provenance
                else []
            )
        ),
        "commit_symlinks_rejected": sorted(
            str(name)
            for name in (
                source_provenance.get("commit_symlinks_rejected", [])
                if source_provenance
                else []
            )
        ),
        "worktree_symlinks_rejected": sorted(
            str(name)
            for name in (
                source_provenance.get("worktree_symlinks_rejected", [])
                if source_provenance
                else []
            )
        ),
    }
    provenance["verified"] = bool(
        provenance["checked"]
        and provenance["verified"]
        and provenance["resolved_commit"] == normalized_commit
    )

    if expected_files is None:
        source_entries: list[tuple[str, Path | None, bytes | None]] = [
            (path.name, path, None) for path in source_files(source_dir)
        ]
    else:
        if not expected_files:
            raise ValueError("expected source snapshot contains no files")
        source_entries = [
            (name, None, body)
            for name, body in sorted(expected_files.items(), key=lambda item: item[0].lower())
        ]

    rows: list[dict[str, Any]] = []
    for filename, path, expected_body in source_entries:
        row: dict[str, Any] = {
            "file": filename,
            "http_status": None,
            "redirect_valid": False,
            "byte_match": False,
            "local_bytes": None,
            "live_bytes": None,
            "local_sha256": None,
            "live_sha256": None,
            "state": "FETCH_ERROR",
        }
        if path is not None and path.is_symlink():
            row["state"] = "SYMLINK_REJECTED"
            row["error_type"] = "SymlinkRejected"
            rows.append(row)
            continue

        local_bytes = expected_body if expected_body is not None else path.read_bytes()
        row["local_bytes"] = len(local_bytes)
        row["local_sha256"] = sha256_bytes(local_bytes)
        target = request_url(normalized_base, filename, normalized_commit)
        try:
            fetched = fetcher(target, timeout_seconds)
            status = int(fetched["status"])
            body = fetched["body"]
            final_url = str(fetched.get("final_url") or target)
            if not isinstance(body, bytes):
                raise TypeError("fetcher body must be bytes")
            row["http_status"] = status
            row["redirect_valid"] = same_public_target(target, final_url)
            row["live_bytes"] = len(body)
            row["live_sha256"] = sha256_bytes(body)
            row["byte_match"] = bool(
                status == 200 and row["redirect_valid"] and body == local_bytes
            )
            if status != 200:
                row["state"] = "HTTP_ERROR"
            elif not row["redirect_valid"]:
                row["state"] = "REDIRECT_REJECTED"
            elif row["byte_match"]:
                row["state"] = "MATCH"
            else:
                row["state"] = "CONTENT_MISMATCH"
        except Exception as exc:  # Record the public failure type, not local paths.
            row["state"] = "FETCH_ERROR"
            row["error_type"] = type(exc).__name__
        rows.append(row)

    match_count = sum(1 for row in rows if row["byte_match"])
    all_current = (
        bool(rows) and match_count == len(rows) and provenance["verified"]
    )
    status = (
        "CURRENT_HEAD_DEPLOYED"
        if all_current
        else "STALE_OR_INCOMPLETE_DEPLOYMENT_HOLD"
    )
    if all_current:
        next_actions = [
            "Preserve this receipt as current-head live-byte evidence.",
            "Keep founder review, video publication, and final Devpost submission as separate human gates.",
        ]
    else:
        next_actions = ["Do not present the live route as current-head evidence."]
        if not provenance["verified"]:
            next_actions.append(
                "Restore exact byte identity between the deployable worktree directory and the named Git commit before release."
            )
        next_actions.extend(
            [
                "After explicit release approval, deploy the exact bounded console directory from the named source commit.",
                "Rerun this gate and require every listed file to return HTTP 200 with an exact byte match before final Devpost review.",
            ]
        )
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_utc": generated_utc or utc_now(),
        "status": status,
        "source_commit": normalized_commit,
        "base_url": normalized_base,
        "controls": {
            "byte_preserving_fetch": True,
            "cache_bust_key": normalized_commit[:12],
            "redirect_must_preserve_origin_and_path": True,
            "symlinks_followed": False,
            "credentials_collected": False,
            "source_commit_bytes_verified": provenance["verified"],
            "deployment_performed": False,
            "submission_performed": False,
        },
        "source_provenance": provenance,
        "summary": {
            "file_count": len(rows),
            "http_200_count": sum(
                1 for row in rows if row["http_status"] == 200
            ),
            "redirect_valid_count": sum(1 for row in rows if row["redirect_valid"]),
            "byte_match_count": match_count,
            "mismatch_count": len(rows) - match_count,
        },
        "submission_gate": "PASS" if all_current else "HOLD",
        "deployment_required": not all_current,
        "mismatched_files": [row["file"] for row in rows if not row["byte_match"]],
        "files": rows,
        "next_actions": next_actions,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    payload["gate_sha256"] = stable_hash(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# ProofLock Current-Head Live Release Gate",
        "",
        f"- Observed UTC: `{payload['generated_utc']}`",
        f"- Source commit: `{payload['source_commit']}`",
        f"- Git source bytes verified: `{str(payload['source_provenance']['verified']).lower()}`",
        f"- Worktree raw bytes match commit: `{str(payload['source_provenance']['worktree_matches_commit']).lower()}`",
        f"- Status: `{payload['status']}`",
        f"- Submission gate: `{payload['submission_gate']}`",
        f"- Byte matches: `{summary['byte_match_count']}/{summary['file_count']}`",
        f"- Gate SHA-256: `{payload['gate_sha256']}`",
        "",
        "## File Evidence",
        "",
        "| File | HTTP | Redirect | Byte match | State |",
        "|---|---:|---|---|---|",
    ]
    for row in payload["files"]:
        lines.append(
            f"| `{row['file']}` | `{row['http_status']}` | "
            f"`{str(row['redirect_valid']).lower()}` | "
            f"`{str(row['byte_match']).lower()}` | `{row['state']}` |"
        )
    lines.extend(["", "## Required Actions", ""])
    lines.extend(
        f"{index}. {item}"
        for index, item in enumerate(payload["next_actions"], start=1)
    )
    lines.extend(["", "## Claim Boundary", "", payload["claim_boundary"], ""])
    return "\n".join(lines)


def write_outputs(
    payload: dict[str, Any], json_path: Path, markdown_path: Path
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--source-commit")
    parser.add_argument("--generated-utc")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    requested_commit = args.source_commit or git_head()
    resolved_commit, expected_files, source_provenance = git_source_snapshot(
        root=ROOT,
        source_dir=args.source_dir,
        source_commit=requested_commit,
    )
    payload = verify_live_release(
        source_dir=args.source_dir,
        base_url=args.base_url,
        source_commit=resolved_commit,
        expected_files=expected_files,
        source_provenance=source_provenance,
        generated_utc=args.generated_utc,
        timeout_seconds=args.timeout_seconds,
    )
    if not args.no_write:
        write_outputs(payload, args.output_json, args.output_markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "submission_gate": payload["submission_gate"],
                "source_commit": payload["source_commit"],
                "byte_match_count": payload["summary"]["byte_match_count"],
                "file_count": payload["summary"]["file_count"],
                "gate_sha256": payload["gate_sha256"],
                "outputs_written": not args.no_write,
            },
            indent=2,
        )
    )
    return 0 if payload["submission_gate"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
