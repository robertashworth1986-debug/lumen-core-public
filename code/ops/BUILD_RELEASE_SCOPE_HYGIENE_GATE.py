from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "out" / "ops" / "release_scope_hygiene_gate_latest.json"

SCHEMA = "lumencore.release_scope_hygiene_gate.v1"
MODE = "LOCAL_READ_ONLY_GIT_INDEX_OBSERVER"
STAGE_MODE = "LOCAL_READ_ONLY_RELEASE_STAGE_OBSERVER"
STAGE_SCHEMA = "lumencore.public_release_stage_bundle.v1"
READ_ONLY_GIT_COMMANDS = frozenset({"diff", "rev-parse"})

CLAIM_BOUNDARY = (
    "This receipt classifies staged path names using bounded release-hygiene "
    "rules. It does not inspect file contents, prove that permitted files are "
    "correct or public-safe, or authorize a commit, push, merge, release, or "
    "deployment."
)
SAFEST_NEXT_ACTION = (
    "Review the Git index with a human, remove generated or private paths from "
    "the proposed release, and rebuild the change on a clean branch from current "
    "public main. Rerun this gate and the relevant tests before publishing."
)

SECRET_SUFFIXES = frozenset({".key", ".pem", ".p12", ".pfx"})
CACHE_PARTS = frozenset(
    {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
)
ENVIRONMENT_PARTS = frozenset({".venv", "venv", "site-packages"})


def utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def normalize_utc(value: str | None) -> str:
    if value is None:
        return utc_now_text()
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
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
            timeout=20,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"returncode": None, "stdout": b""}
    return {"returncode": completed.returncode, "stdout": completed.stdout}


def _staged_paths(repo_root: Path) -> list[str] | None:
    result = _run_git(
        repo_root,
        ["diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"],
    )
    if result["returncode"] != 0:
        return None
    paths: list[str] = []
    for raw in result["stdout"].split(b"\0"):
        if not raw:
            continue
        decoded = raw.decode("utf-8", errors="replace").replace("\\", "/")
        normalized = PurePosixPath(decoded).as_posix().lstrip("./")
        if normalized:
            paths.append(normalized)
    return paths


def classify_path(path: str) -> set[str]:
    normalized = PurePosixPath(path).as_posix().lstrip("./")
    lowered = normalized.lower()
    parts = tuple(part.lower() for part in PurePosixPath(lowered).parts)
    basename = parts[-1] if parts else ""
    categories: set[str] = set()

    if "node_modules" in parts:
        categories.add("VENDORED_DEPENDENCY_TREE")
    if parts and parts[0] in {"tmp", "temp"}:
        categories.add("TEMPORARY_WORKSPACE")
    if any(part in ENVIRONMENT_PARTS for part in parts):
        categories.add("LOCAL_RUNTIME_ENVIRONMENT")
    if any(part in CACHE_PARTS for part in parts) or basename.endswith(
        (".pyc", ".pyo")
    ):
        categories.add("CACHE_ARTIFACT")
    if lowered.startswith("output/pdf/job_applications/"):
        categories.add("PRIVATE_APPLICATION_PACKET")
    if (
        basename == ".env"
        or basename.startswith(".env.")
        or any(token in basename for token in ("credential", "private_key", "secret"))
        or PurePosixPath(lowered).suffix in SECRET_SUFFIXES
    ):
        categories.add("SECRET_LIKE_FILENAME")
    return categories


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sealed_payload_matches(payload: dict[str, Any], field: str) -> bool:
    declared = str(payload.get(field, "")).casefold()
    unsigned = dict(payload)
    unsigned.pop(field, None)
    return bool(declared) and declared == canonical_sha256(unsigned)


def _stage_manifest_path(repo_root: Path, value: Path) -> Path:
    candidate = value if value.is_absolute() else repo_root / value
    if candidate.is_symlink():
        raise ValueError("stage manifest must not be a symlink")
    resolved = candidate.resolve(strict=True)
    stage_base = (repo_root / ".deploy_stage").resolve(strict=True)
    try:
        resolved.relative_to(stage_base)
    except ValueError as exc:
        raise ValueError("stage manifest is outside .deploy_stage") from exc
    if resolved.name != "manifest.json" or not resolved.is_file():
        raise ValueError("stage manifest must be a regular manifest.json file")
    return resolved


def _build_stage_gate(
    repo_root: Path,
    stage_manifest: Path,
    *,
    generated_utc: str,
) -> dict[str, Any]:
    blockers: list[dict[str, str]] = []
    category_counts: Counter[str] = Counter()
    prohibited_paths: set[str] = set()
    staged_count = 0
    hash_verified_count = 0
    plan_sha256: str | None = None
    manifest_sha256: str | None = None

    try:
        manifest_path = _stage_manifest_path(repo_root, stage_manifest)
    except (OSError, ValueError):
        manifest_path = None
        manifest = None
        blockers.append(
            {
                "code": "STAGE_MANIFEST_UNRESOLVED",
                "detail": "The requested release-stage manifest is missing or outside .deploy_stage.",
            }
        )
    else:
        manifest = _read_json_object(manifest_path)

    if manifest is not None:
        plan_sha256 = str(manifest.get("plan_sha256", "")) or None
        manifest_sha256 = str(manifest.get("manifest_sha256", "")) or None
        if not _sealed_payload_matches(manifest, "manifest_sha256"):
            blockers.append(
                {
                    "code": "STAGE_MANIFEST_HASH_INVALID",
                    "detail": "The release-stage manifest seal does not match its canonical payload.",
                }
            )
        summary = manifest.get("summary", {})
        authority = manifest.get("authority", {})
        files = manifest.get("files")
        contract_valid = (
            manifest.get("schema") == STAGE_SCHEMA
            and manifest.get("stage_state") == "LOCAL_STAGE_READY"
            and isinstance(files, list)
            and bool(files)
            and summary.get("item_count") == len(files)
            and summary.get("files_staged_locally") is True
            and summary.get("public_root_copy_performed") is False
            and summary.get("network_action_performed") is False
            and summary.get("publication_performed") is False
            and summary.get("stage_ready") is True
            and authority.get("human_unlock_required_for_vps_or_publication") is True
            and authority.get("external_action_authorized_by_stage") is False
            and authority.get("credentials_required_for_local_stage") is False
        )
        if not contract_valid:
            blockers.append(
                {
                    "code": "STAGE_CONTRACT_INVALID",
                    "detail": "The stage manifest is not a complete fail-closed local release contract.",
                }
            )
        if isinstance(files, list) and manifest_path is not None:
            stage_root = manifest_path.parent
            seen_paths: set[str] = set()
            staged_count = len(files)
            hash_failure = False
            for row in files:
                if not isinstance(row, dict):
                    hash_failure = True
                    continue
                raw_path = row.get("staged_relative_path")
                if not isinstance(raw_path, str) or not raw_path:
                    hash_failure = True
                    continue
                relative = PurePosixPath(raw_path)
                normalized = relative.as_posix().lstrip("./")
                if (
                    relative.is_absolute()
                    or any(part in {"", ".", ".."} for part in relative.parts)
                    or normalized in seen_paths
                    or row.get("intended_public_target_path") != normalized
                ):
                    hash_failure = True
                    continue
                seen_paths.add(normalized)
                categories = classify_path(normalized)
                category_counts.update(categories)
                if categories:
                    prohibited_paths.add(normalized)
                staged = stage_root / Path(normalized)
                expected_sha256 = str(row.get("source_sha256", "")).casefold()
                expected_bytes = row.get("bytes")
                try:
                    if staged.is_symlink():
                        raise ValueError("staged release file must not be a symlink")
                    resolved = staged.resolve(strict=True)
                    resolved.relative_to(stage_root.resolve(strict=True))
                    valid_file = (
                        resolved.is_file()
                        and isinstance(expected_bytes, int)
                        and expected_bytes >= 0
                        and resolved.stat().st_size == expected_bytes
                        and bool(expected_sha256)
                        and _sha256_file(resolved) == expected_sha256
                    )
                except (OSError, ValueError):
                    valid_file = False
                if valid_file:
                    hash_verified_count += 1
                else:
                    hash_failure = True
            if hash_failure or hash_verified_count != staged_count:
                blockers.append(
                    {
                        "code": "STAGED_FILE_VERIFICATION_FAILED",
                        "detail": "One or more staged files failed path, byte-count, or SHA-256 verification.",
                    }
                )
    elif not blockers:
        blockers.append(
            {
                "code": "STAGE_MANIFEST_UNREADABLE",
                "detail": "The requested release-stage manifest is not readable JSON.",
            }
        )

    if prohibited_paths:
        blockers.append(
            {
                "code": "PROHIBITED_STAGED_PATH_CLASSES",
                "detail": (
                    "One or more staged paths match generated, private, cache, "
                    "runtime-environment, or secret-like release classes."
                ),
            }
        )

    status = (
        "PASS_RELEASE_STAGE_HYGIENE"
        if not blockers
        else "BLOCKED_RELEASE_STAGE_HYGIENE"
    )
    gate: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_utc": generated_utc,
        "mode": STAGE_MODE,
        "summary": {
            "status": status,
            "release_scope_claim_allowed": not blockers,
            "staged_path_count": staged_count,
            "prohibited_staged_path_count": len(prohibited_paths),
            "hash_verified_path_count": hash_verified_count,
        },
        "scope_binding": {
            "plan_sha256": plan_sha256,
            "stage_manifest_sha256": manifest_sha256,
            "manifest_path_recorded": False,
        },
        "prohibited_category_counts": dict(sorted(category_counts.items())),
        "blockers": blockers,
        "claim_boundary": (
            "This receipt verifies the sealed isolated release-stage contract, staged path "
            "classes, byte counts, and SHA-256 parity. It does not semantically validate "
            "content or authorize a commit, push, merge, release, or deployment."
        ),
        "safest_next_action": (
            "Keep the exact stage sealed and require the remaining global gates plus a fresh "
            "HumanUnlock before any public or VPS action."
            if not blockers
            else "Repair the isolated stage or its sealed plan, rebuild it, and rerun this gate."
        ),
        "privacy_controls": {
            "path_names_recorded": False,
            "file_contents_read": False,
            "file_bytes_read_for_sha256_only": True,
            "file_contents_recorded": False,
            "worktree_mutation_performed": False,
        },
    }
    gate["gate_sha256"] = canonical_sha256(gate)
    return gate


def build_gate(
    repo_root: Path,
    *,
    as_of_utc: str | None = None,
    stage_manifest: Path | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    generated_utc = normalize_utc(as_of_utc)
    if stage_manifest is not None:
        return _build_stage_gate(
            repo_root,
            stage_manifest,
            generated_utc=generated_utc,
        )
    inside = _run_git(repo_root, ["rev-parse", "--is-inside-work-tree"])
    staged_paths = _staged_paths(repo_root) if inside["returncode"] == 0 else None

    category_counts: Counter[str] = Counter()
    prohibited_paths: set[str] = set()
    if staged_paths is not None:
        for path in staged_paths:
            categories = classify_path(path)
            category_counts.update(categories)
            if categories:
                prohibited_paths.add(path)

    blockers: list[dict[str, str]] = []
    if inside["returncode"] != 0 or staged_paths is None:
        blockers.append(
            {
                "code": "GIT_INDEX_STATE_UNRESOLVED",
                "detail": "The staged Git index could not be read locally.",
            }
        )
        status = "BLOCKED_GIT_INDEX_STATE_UNRESOLVED"
    elif prohibited_paths:
        blockers.append(
            {
                "code": "PROHIBITED_STAGED_PATH_CLASSES",
                "detail": (
                    "One or more staged paths match generated, private, cache, "
                    "runtime-environment, or secret-like release classes."
                ),
            }
        )
        status = "BLOCKED_PROHIBITED_STAGED_PATH_CLASSES"
    else:
        status = "PASS_RELEASE_SCOPE_HYGIENE"

    gate: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_utc": generated_utc,
        "mode": MODE,
        "summary": {
            "status": status,
            "release_scope_claim_allowed": not blockers,
            "staged_path_count": None if staged_paths is None else len(staged_paths),
            "prohibited_staged_path_count": (
                None if staged_paths is None else len(prohibited_paths)
            ),
        },
        "prohibited_category_counts": dict(sorted(category_counts.items())),
        "blockers": blockers,
        "claim_boundary": CLAIM_BOUNDARY,
        "safest_next_action": SAFEST_NEXT_ACTION,
        "privacy_controls": {
            "path_names_recorded": False,
            "file_contents_read": False,
            "file_bytes_read_for_sha256_only": False,
            "file_contents_recorded": False,
            "worktree_mutation_performed": False,
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
        description="Build a local read-only staged release-scope hygiene gate."
    )
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--as-of-utc")
    parser.add_argument(
        "--stage-manifest",
        type=Path,
        help="Verify one sealed local stage beneath .deploy_stage instead of the Git index.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return nonzero when the release-scope hygiene claim is blocked.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    gate = build_gate(
        args.repo_root,
        as_of_utc=args.as_of_utc,
        stage_manifest=args.stage_manifest,
    )
    write_gate(gate, args.output)
    summary = gate["summary"]
    print(f"RELEASE_SCOPE_HYGIENE_STATUS={summary['status']}")
    print(
        "RELEASE_SCOPE_HYGIENE_STAGED_PROHIBITED="
        f"{summary['staged_path_count']}/{summary['prohibited_staged_path_count']}"
    )
    print(f"RELEASE_SCOPE_HYGIENE_GATE_SHA256={gate['gate_sha256']}")
    print(f"RELEASE_SCOPE_HYGIENE_OUTPUT={args.output}")
    if args.strict and not summary["release_scope_claim_allowed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
