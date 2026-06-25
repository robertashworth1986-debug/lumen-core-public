from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

OUT_JSON = OUT_OPS / "external_proof_drive_intake_latest.json"
OUT_CSV = OUT_OPS / "external_proof_drive_candidates.csv"
DASHBOARD_JSON = DASHBOARD_DATA / "external_proof_drive_intake.json"
OUT_MD = DOCS / "EXTERNAL_PROOF_DRIVE_INTAKE_2026-06-25.md"

SKIP_DIR_NAMES = {
    "$recycle.bin",
    "system volume information",
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
    ".cache",
    "cache",
    "tmp",
    "temp",
}

EXT_POINTS = {
    ".jsonl": 18,
    ".parquet": 18,
    ".feather": 17,
    ".json": 15,
    ".sha256": 15,
    ".csv": 14,
    ".tsv": 12,
    ".md": 9,
    ".xlsx": 9,
    ".xls": 8,
    ".txt": 7,
    ".zip": 6,
    ".pdf": 5,
    ".png": 2,
    ".svg": 2,
}

TOKEN_GROUPS = {
    "proof_chain": {
        "tokens": ("frozen", "freeze", "delta", "proof", "sha", "hash", "manifest", "ledger", "chain", "custody"),
        "points": 10,
    },
    "live_measurement": {
        "tokens": ("live", "measured", "rows", "source", "snapshot", "validation", "field", "outage", "grid"),
        "points": 8,
    },
    "multi_asset": {
        "tokens": ("multi", "asset", "triple", "quant", "market", "kraken", "price", "forecast", "macro", "rates"),
        "points": 8,
    },
    "benchmark": {
        "tokens": ("benchmark", "baseline", "champion", "winner", "replay", "score", "frontier", "gate"),
        "points": 8,
    },
    "geometry": {
        "tokens": ("geometry", "flowform", "harmonic", "phase", "lock", "spiral", "mycelium", "slime", "branching"),
        "points": 7,
    },
    "public_source": {
        "tokens": ("eia", "fred", "noaa", "nrel", "nasa", "epa", "sam", "grants", "darpa", "dod", "doe", "sbir", "sttr"),
        "points": 8,
    },
    "luma_stack": {
        "tokens": ("luma", "lumen", "lumencore", "novacore", "whitehole", "etherframe", "missionweave", "harbor"),
        "points": 5,
    },
}

ARCHIVE_REVIEW_TOKENS = (
    "installer",
    "setup",
    "download",
    "cache",
    "thumbnail",
    "screenshot",
    "copy of",
    "old",
    "backup",
    "tmp",
    "temp",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_payload(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def normalized_text(path: Path) -> str:
    return str(path).lower().replace("\\", "/")


def relative_depth(root: Path, path: Path) -> int:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return 999
    return len(rel.parts)


def score_file(root: Path, path: Path, stat: os.stat_result) -> dict[str, Any]:
    haystack = normalized_text(path)
    ext = path.suffix.lower()
    score = EXT_POINTS.get(ext, 0)
    matched_groups: list[str] = []
    matched_tokens: list[str] = []

    for group, spec in TOKEN_GROUPS.items():
        group_tokens = [token for token in spec["tokens"] if token in haystack]
        if group_tokens:
            matched_groups.append(group)
            matched_tokens.extend(group_tokens[:4])
            score += int(spec["points"])
            if len(group_tokens) > 1:
                score += min(4, len(group_tokens) - 1)

    archive_tokens = [token for token in ARCHIVE_REVIEW_TOKENS if token in haystack]
    penalty = 0
    if archive_tokens:
        penalty += 8 + (2 * min(len(archive_tokens), 4))
    if ext in {".exe", ".dll", ".msi", ".iso", ".dmg", ".tmp", ".log"}:
        penalty += 12
    if stat.st_size == 0:
        penalty += 10
    if stat.st_size > 2_000_000_000:
        penalty += 4

    net_score = max(0, score - penalty)
    has_live = "live_measurement" in matched_groups
    has_proof = "proof_chain" in matched_groups
    has_multi = "multi_asset" in matched_groups
    has_benchmark = "benchmark" in matched_groups

    if has_live and has_proof and (has_multi or has_benchmark) and net_score >= 42:
        evidence_class = "live_frozen_triple_threat_candidate"
    elif net_score >= 50:
        evidence_class = "proof_rail_candidate"
    elif net_score >= 32:
        evidence_class = "research_candidate"
    elif net_score >= 18:
        evidence_class = "context_candidate"
    elif penalty >= 12:
        evidence_class = "archive_review_candidate"
    else:
        evidence_class = "low_signal"

    return {
        "path": str(path),
        "relative_path": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
        "name": path.name,
        "extension": ext,
        "size_bytes": stat.st_size,
        "mtime_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "depth": relative_depth(root, path),
        "score": net_score,
        "raw_score": score,
        "penalty": penalty,
        "matched_groups": matched_groups,
        "matched_tokens": sorted(set(matched_tokens)),
        "archive_review_tokens": archive_tokens,
        "evidence_class": evidence_class,
        "metadata_hash": sha256_payload(
            {
                "relative_path": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
                "size_bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
        ),
    }


def scan_drive(root: Path, max_files: int, max_depth: int) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    archive_review: list[dict[str, Any]] = []
    extension_counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    dirs_seen = 0
    files_seen = 0
    skipped_dirs = 0
    errors: list[dict[str, str]] = []
    duplicate_groups: dict[tuple[str, int], list[str]] = defaultdict(list)

    stack = [root]
    while stack and files_seen < max_files:
        current = stack.pop()
        try:
            with os.scandir(current) as iterator:
                entries = list(iterator)
        except OSError as exc:
            errors.append({"path": str(current), "error": str(exc)})
            continue

        dirs_seen += 1
        for entry in entries:
            try:
                path = Path(entry.path)
                if entry.is_dir(follow_symlinks=False):
                    if entry.name.lower() in SKIP_DIR_NAMES:
                        skipped_dirs += 1
                        continue
                    if relative_depth(root, path) < max_depth:
                        stack.append(path)
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
                stat = entry.stat(follow_symlinks=False)
            except OSError as exc:
                errors.append({"path": entry.path, "error": str(exc)})
                continue

            files_seen += 1
            scored = score_file(root, path, stat)
            extension_counts[scored["extension"] or "<none>"] += 1
            class_counts[scored["evidence_class"]] += 1
            duplicate_groups[(scored["name"].lower(), int(scored["size_bytes"]))].append(scored["path"])

            if scored["evidence_class"] != "low_signal":
                candidates.append(scored)
            if scored["evidence_class"] == "archive_review_candidate":
                archive_review.append(scored)
            if files_seen >= max_files:
                break

    candidates.sort(key=lambda row: (row["score"], row["size_bytes"]), reverse=True)
    archive_review.sort(key=lambda row: (row["penalty"], -row["score"], row["size_bytes"]), reverse=True)
    duplicates = [
        {"name": key[0], "size_bytes": key[1], "paths": paths[:20], "count": len(paths)}
        for key, paths in duplicate_groups.items()
        if len(paths) > 1
    ]
    duplicates.sort(key=lambda row: (row["count"], row["size_bytes"]), reverse=True)

    return {
        "generated_utc": now_utc(),
        "schema": "external_proof_drive_intake.v1",
        "scan_root": str(root),
        "max_files": max_files,
        "max_depth": max_depth,
        "summary": {
            "dirs_seen": dirs_seen,
            "files_seen": files_seen,
            "skipped_dirs": skipped_dirs,
            "errors": len(errors),
            "candidate_count": len(candidates),
            "live_frozen_triple_threat_candidate_count": class_counts.get("live_frozen_triple_threat_candidate", 0),
            "proof_rail_candidate_count": class_counts.get("proof_rail_candidate", 0),
            "research_candidate_count": class_counts.get("research_candidate", 0),
            "context_candidate_count": class_counts.get("context_candidate", 0),
            "archive_review_candidate_count": class_counts.get("archive_review_candidate", 0),
            "low_signal_count": class_counts.get("low_signal", 0),
            "duplicate_name_size_group_count": len(duplicates),
            "delete_performed": False,
        },
        "boundary": (
            "Read-only evidence intake. No files are deleted, moved, copied, or modified. "
            "Archive recommendations are review candidates only."
        ),
        "class_counts": dict(class_counts),
        "extension_counts": dict(extension_counts.most_common(40)),
        "top_candidates": candidates[:150],
        "archive_review_candidates": archive_review[:100],
        "duplicate_name_size_groups": duplicates[:75],
        "errors": errors[:50],
    }


def add_content_hashes(payload: dict[str, Any], limit: int, max_bytes: int) -> None:
    hashed = 0
    skipped = 0
    for row in payload.get("top_candidates", [])[: max(0, limit)]:
        path = Path(str(row.get("path", "")))
        size_bytes = int(row.get("size_bytes", 0) or 0)
        if size_bytes > max_bytes:
            row["content_hash_status"] = "skipped_too_large"
            skipped += 1
            continue
        try:
            row["content_sha256"] = sha256_file(path)
            row["content_hash_status"] = "hashed"
            hashed += 1
        except OSError as exc:
            row["content_hash_status"] = f"error: {exc}"
            skipped += 1
    payload["summary"]["content_hash_count"] = hashed
    payload["summary"]["content_hash_skipped_count"] = skipped
def write_candidates_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "score",
        "evidence_class",
        "path",
        "extension",
        "size_bytes",
        "mtime_utc",
        "matched_groups",
        "matched_tokens",
        "archive_review_tokens",
        "metadata_hash",
        "content_sha256",
        "content_hash_status",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "score": row.get("score"),
                    "evidence_class": row.get("evidence_class"),
                    "path": row.get("path"),
                    "extension": row.get("extension"),
                    "size_bytes": row.get("size_bytes"),
                    "mtime_utc": row.get("mtime_utc"),
                    "matched_groups": "|".join(row.get("matched_groups", [])),
                    "matched_tokens": "|".join(row.get("matched_tokens", [])),
                    "archive_review_tokens": "|".join(row.get("archive_review_tokens", [])),
                    "metadata_hash": row.get("metadata_hash"),
                    "content_sha256": row.get("content_sha256", ""),
                    "content_hash_status": row.get("content_hash_status", ""),
                }
            )


def build_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# External Proof Drive Intake",
        "",
        f"Generated UTC: {payload['generated_utc']}",
        f"Scan root: `{payload['scan_root']}`",
        "",
        "## Boundary",
        "",
        payload["boundary"],
        "",
        "## Summary",
        "",
        f"- Files scanned: {summary['files_seen']}",
        f"- Directories scanned: {summary['dirs_seen']}",
        f"- Candidate files: {summary['candidate_count']}",
        f"- Live frozen triple-threat candidates: {summary['live_frozen_triple_threat_candidate_count']}",
        f"- Proof-rail candidates: {summary['proof_rail_candidate_count']}",
        f"- Research candidates: {summary['research_candidate_count']}",
        f"- Archive review candidates: {summary['archive_review_candidate_count']}",
        f"- Duplicate name+size groups: {summary['duplicate_name_size_group_count']}",
        f"- Content hashes added: {summary.get('content_hash_count', 0)}",
        f"- Delete performed: {summary['delete_performed']}",
        "",
        "## Top Evidence Candidates",
        "",
    ]
    for row in payload["top_candidates"][:25]:
        lines.append(
            f"- score {row['score']:>3} | {row['evidence_class']} | `{row['path']}`"
        )
    lines.extend(["", "## Archive Review Only", ""])
    for row in payload["archive_review_candidates"][:15]:
        lines.append(
            f"- penalty {row['penalty']:>3} | score {row['score']:>3} | `{row['path']}`"
        )
    lines.extend(
        [
            "",
            "## Next Use",
            "",
            "Promote only the top candidates that contain measurable rows, frozen hashes, baseline comparisons, or live-source provenance into the live evidence rail. Do not delete archive-review candidates until a human confirms they are not unique evidence.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only external proof drive intake scanner.")
    parser.add_argument("--root", required=True, help="External drive or folder to scan, for example E:")
    parser.add_argument("--max-files", type=int, default=50000)
    parser.add_argument("--max-depth", type=int, default=10)
    parser.add_argument("--hash-top", type=int, default=150, help="Content-hash this many top candidates.")
    parser.add_argument("--hash-max-mb", type=int, default=50, help="Skip content hashing above this size in MB.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Scan root does not exist or is not a directory: {root}")
    payload = scan_drive(root=root, max_files=max(1, args.max_files), max_depth=max(1, args.max_depth))
    add_content_hashes(payload, limit=max(0, args.hash_top), max_bytes=max(1, args.hash_max_mb) * 1024 * 1024)
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_candidates_csv(OUT_CSV, payload["top_candidates"])
    write_text(OUT_MD, build_markdown(payload))
    print(f"wrote {OUT_JSON}")
    print(f"wrote {DASHBOARD_JSON}")
    print(f"wrote {OUT_CSV}")
    print(f"wrote {OUT_MD}")
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
