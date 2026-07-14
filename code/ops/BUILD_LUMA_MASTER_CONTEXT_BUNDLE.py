#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = ROOT / "config" / "luma_master_context_registry_v1.json"
DEFAULT_VAULT = Path(os.environ.get("LUMA_PROOF_VAULT", "E:/LumaProofVault"))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def resolve_source(source: dict[str, Any], repo_root: Path, vault_root: Path) -> Path:
    location = source.get("location")
    if location == "repo":
        return repo_root / str(source["path"])
    if location == "vault":
        return vault_root / str(source["path"])
    raise ValueError(f"Unsupported source location for {source.get('id')}: {location}")


def extract_safe_summary(source_id: str, path: Path) -> dict[str, Any]:
    if path.suffix.lower() != ".json":
        return {}
    payload = read_json(path)
    if source_id == "estate_index":
        summary = payload.get("summary", {})
        allowed = (
            "managed_file_count",
            "managed_total_bytes",
            "content_sha256_file_count",
            "sensitive_metadata_only_count",
            "scan_error_count",
            "inventory_chain_sha256",
        )
        return {key: summary.get(key) for key in allowed if key in summary}
    if source_id == "reviewer_context":
        posture = payload.get("current_evidence_posture", {})
        return {
            "highest_repository_wide_supported_level": posture.get("highest_repository_wide_supported_level"),
            "level_5_attained": posture.get("level_5_attained"),
            "proof_card_count": len(payload.get("proof_cards", [])),
            "source_input_chain_sha256": payload.get("source_input_chain_sha256"),
        }
    if source_id == "private_note_capsule":
        summary = payload.get("source_summary", {})
        allowed = (
            "record_count",
            "unique_content_hashes",
            "duplicate_file_count",
            "duplicate_group_count",
            "theoretical_duplicate_reclaimable_bytes",
            "locally_hashed_count",
            "cloud_placeholder_count",
            "sensitive_flagged_count",
        )
        return {key: summary.get(key) for key in allowed if key in summary}
    if source_id == "compaction_overlap_audit":
        summary = payload.get("summary", {})
        allowed = (
            "audited_compaction_count",
            "changed_path_occurrence_count",
            "unique_changed_path_count",
            "repeated_path_count",
            "maximum_occurrences_for_any_path",
            "duplicate_rebuild_detected",
        )
        return {key: summary.get(key) for key in allowed if key in summary}
    return {}


def git_snapshot(repo_root: Path) -> dict[str, Any]:
    def run(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return completed.stdout.strip()

    try:
        status_lines = [line for line in run("status", "--short").splitlines() if line.strip()]
        return {
            "available": True,
            "head": run("rev-parse", "HEAD"),
            "branch": run("branch", "--show-current"),
            "dirty_path_count": len(status_lines),
        }
    except (OSError, subprocess.CalledProcessError):
        return {"available": False, "head": None, "branch": None, "dirty_path_count": None}


def build_payload(
    *,
    repo_root: Path,
    vault_root: Path,
    registry_path: Path,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or utc_now()
    registry = read_json(registry_path)
    source_records: list[dict[str, Any]] = []
    canonical_by_role: dict[str, list[str]] = defaultdict(list)
    hashes: dict[str, list[str]] = defaultdict(list)

    for source in registry.get("sources", []):
        source_id = str(source["id"])
        path = resolve_source(source, repo_root, vault_root)
        exists = path.is_file()
        modified_utc = None
        age_hours = None
        digest = None
        size_bytes = None
        safe_summary: dict[str, Any] = {}
        error = None

        if exists:
            try:
                stat = path.stat()
                modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                modified_utc = iso_utc(modified)
                age_hours = round(max((generated_at - modified).total_seconds(), 0.0) / 3600.0, 3)
                size_bytes = stat.st_size
                digest = sha256_file(path)
                hashes[digest].append(source_id)
                safe_summary = extract_safe_summary(source_id, path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                error = f"{type(exc).__name__}: {exc}"

        max_age = source.get("max_age_hours")
        stale = bool(
            exists
            and error is None
            and max_age is not None
            and age_hours is not None
            and age_hours > float(max_age)
        )
        if source.get("canonical"):
            canonical_by_role[str(source["role"])].append(source_id)

        source_records.append(
            {
                "id": source_id,
                "role": source["role"],
                "status": source["status"],
                "canonical": bool(source.get("canonical")),
                "privacy": source["privacy"],
                "location": source["location"],
                "path": source["path"],
                "builder": source.get("builder"),
                "exists": exists,
                "read_error": error,
                "size_bytes": size_bytes,
                "modified_utc": modified_utc,
                "age_hours": age_hours,
                "max_age_hours": max_age,
                "stale": stale,
                "sha256": digest,
                "safe_summary": safe_summary,
            }
        )

    canonical_roles = {role: ids[0] for role, ids in canonical_by_role.items() if len(ids) == 1}
    role_collisions = {role: ids for role, ids in canonical_by_role.items() if len(ids) != 1}
    current_canonical = [row for row in source_records if row["canonical"] and row["status"] == "current"]
    missing = [row["id"] for row in current_canonical if not row["exists"] or row["read_error"]]
    stale = [row["id"] for row in current_canonical if row["stale"]]
    duplicate_groups = [ids for ids in hashes.values() if len(ids) > 1]

    return {
        "schema": "luma_master_context_bundle_v1",
        "generated_utc": iso_utc(generated_at),
        "privacy_boundary": {
            "private_bundle": True,
            "source_bodies_serialized": False,
            "credentials_or_personal_identifiers_allowed": False,
            "public_claim_source": "reviewer_context",
        },
        "startup_order": registry.get("startup_order", []),
        "canonical_source_by_role": canonical_roles,
        "source_records": source_records,
        "integrity": {
            "canonical_role_collision_count": len(role_collisions),
            "canonical_role_collisions": role_collisions,
            "missing_current_canonical_count": len(missing),
            "missing_current_canonical_sources": missing,
            "stale_current_canonical_count": len(stale),
            "stale_current_canonical_sources": stale,
            "exact_duplicate_source_group_count": len(duplicate_groups),
            "exact_duplicate_source_groups": duplicate_groups,
            "canonical_gate_passed": not role_collisions and not missing,
            "freshness_gate_passed": not stale,
        },
        "git": git_snapshot(repo_root),
        "operating_contract": [
            "Load this bundle before creating a new continuity artifact.",
            "Use the canonical source registered for a role; do not rebuild a parallel master file.",
            "Retrieve source bodies only when the active task needs them.",
            "Treat private-note duplicates as review-only and never execute note code automatically.",
            "Keep scientific claims anchored to reviewer evidence, protocols, metrics, and receipts.",
            "Require action-time HumanUnlock for money, filings, submissions, outreach, and live execution.",
        ],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    integrity = payload["integrity"]
    lines = [
        "# Luma Master Context - Latest",
        "",
        "Private metadata bundle. Source bodies are not embedded.",
        "",
        f"- Generated UTC: `{payload['generated_utc']}`",
        f"- Canonical gate passed: `{str(integrity['canonical_gate_passed']).lower()}`",
        f"- Freshness gate passed: `{str(integrity['freshness_gate_passed']).lower()}`",
        f"- Missing canonical sources: `{integrity['missing_current_canonical_count']}`",
        f"- Stale canonical sources: `{integrity['stale_current_canonical_count']}`",
        f"- Exact duplicate registered-source groups: `{integrity['exact_duplicate_source_group_count']}`",
        "",
        "## Startup Order",
        "",
    ]
    lines.extend(f"{index}. `{role}`" for index, role in enumerate(payload["startup_order"], start=1))
    lines.extend(["", "## Canonical Sources", ""])
    lines.append("| Role | Source | Exists | Stale | SHA-256 |")
    lines.append("|---|---|---:|---:|---|")
    records_by_id = {row["id"]: row for row in payload["source_records"]}
    for role, source_id in payload["canonical_source_by_role"].items():
        row = records_by_id[source_id]
        digest = row["sha256"] or "unavailable"
        lines.append(
            f"| {role} | {source_id} | {str(row['exists']).lower()} | "
            f"{str(row['stale']).lower()} | `{digest}` |"
        )
    lines.extend(["", "## Operating Contract", ""])
    lines.extend(f"- {rule}" for rule in payload["operating_contract"])
    lines.extend(["", "## Git Snapshot", ""])
    git = payload["git"]
    lines.extend(
        [
            f"- Available: `{str(git['available']).lower()}`",
            f"- Branch: `{git['branch'] or 'unavailable'}`",
            f"- HEAD: `{git['head'] or 'unavailable'}`",
            f"- Dirty path count: `{git['dirty_path_count']}`",
            "",
        ]
    )
    return "\n".join(lines)


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(payload)
    temp.replace(path)


def write_bundle(
    payload: dict[str, Any],
    *,
    vault_root: Path,
    registry_path: Path,
) -> dict[str, Any]:
    registry = read_json(registry_path)
    output = registry["private_output"]
    output_dir = vault_root / output["vault_relative_dir"]
    stamp = payload["generated_utc"].replace("-", "").replace(":", "")
    run_dir = output_dir / output["run_dir"] / stamp

    json_bytes = stable_json_bytes(payload)
    markdown_bytes = render_markdown(payload).encode("utf-8")
    previous_manifest_path = output_dir / output["latest_manifest"]
    previous_manifest_sha256 = sha256_file(previous_manifest_path) if previous_manifest_path.is_file() else None
    manifest = {
        "schema": "luma_master_context_manifest_v1",
        "generated_utc": payload["generated_utc"],
        "previous_manifest_sha256": previous_manifest_sha256,
        "artifacts": {
            output["latest_json"]: sha256_bytes(json_bytes),
            output["latest_markdown"]: sha256_bytes(markdown_bytes),
        },
    }
    manifest_bytes = stable_json_bytes(manifest)

    for directory in (run_dir, output_dir):
        atomic_write(directory / output["latest_json"], json_bytes)
        atomic_write(directory / output["latest_markdown"], markdown_bytes)
        atomic_write(directory / output["latest_manifest"], manifest_bytes)

    verification = {
        "json_sha256": sha256_file(output_dir / output["latest_json"]),
        "markdown_sha256": sha256_file(output_dir / output["latest_markdown"]),
        "manifest_sha256": sha256_file(output_dir / output["latest_manifest"]),
        "run_dir": str(run_dir),
    }
    if verification["json_sha256"] != manifest["artifacts"][output["latest_json"]]:
        raise RuntimeError("Latest JSON hash verification failed")
    if verification["markdown_sha256"] != manifest["artifacts"][output["latest_markdown"]]:
        raise RuntimeError("Latest Markdown hash verification failed")
    return verification


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the private canonical Luma context bundle.")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--vault-root", type=Path, default=DEFAULT_VAULT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    payload = build_payload(
        repo_root=args.repo_root.resolve(),
        vault_root=args.vault_root.resolve(),
        registry_path=args.registry.resolve(),
    )
    if args.check_only:
        print(json.dumps(payload["integrity"], indent=2, sort_keys=True))
    else:
        verification = write_bundle(payload, vault_root=args.vault_root.resolve(), registry_path=args.registry.resolve())
        print(json.dumps({"integrity": payload["integrity"], "verification": verification}, indent=2, sort_keys=True))
    integrity = payload["integrity"]
    return 0 if integrity["canonical_gate_passed"] and integrity["freshness_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
