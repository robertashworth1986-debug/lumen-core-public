from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "out" / "ops" / "external_drive_audit"
OUT_JSON = OUT_DIR / "external_drive_audit_latest.json"
OUT_MD = OUT_DIR / "external_drive_audit_latest.md"

MISSION_KEYWORDS = (
    "luma",
    "lumencore",
    "novacore",
    "grant",
    "sbir",
    "sttr",
    "proof",
    "evidence",
    "audit",
    "hash",
    "manifest",
    "harbor",
    "ais",
    "dice",
    "mission",
    "geometry",
    "benchmark",
    "frozen",
    "delta",
    "trader",
    "kraken",
)

RISK_KEYWORDS = (
    "password",
    "passwd",
    "secret",
    "token",
    "credential",
    "credentials",
    "apikey",
    "api_key",
    "private_key",
    ".env",
    "wallet",
    "seedphrase",
    "seed_phrase",
)

LARGE_DATA_EXTENSIONS = {
    ".zip",
    ".parquet",
    ".csv",
    ".jsonl",
    ".feather",
    ".arrow",
    ".h5",
    ".hdf5",
    ".db",
    ".sqlite",
    ".sqlite3",
}

DOC_EXTENSIONS = {".md", ".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".json", ".txt"}
MEDIA_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mov", ".avi", ".webm"}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except Exception:
        return str(path).replace("\\", "/")


def top_name(path: Path, root: Path) -> str:
    rel = safe_rel(path, root)
    return rel.split("/", 1)[0] if rel else "."


def classify_path(path: Path) -> set[str]:
    text = str(path).lower()
    suffix = path.suffix.lower()
    labels: set[str] = set()
    if any(keyword in text for keyword in MISSION_KEYWORDS):
        labels.add("mission_fit_candidate")
    if any(keyword in text for keyword in RISK_KEYWORDS):
        labels.add("secret_or_sensitive_name_review")
    if suffix in LARGE_DATA_EXTENSIONS:
        labels.add("large_data_or_manifest_candidate")
    if suffix in DOC_EXTENSIONS:
        labels.add("document_or_evidence_candidate")
    if suffix in MEDIA_EXTENSIONS:
        labels.add("visual_or_media_candidate")
    if "$recycle.bin" in text or "system volume information" in text:
        labels.add("system_or_recycle_area_do_not_touch")
    if not labels:
        labels.add("manual_review")
    return labels


def append_largest(bucket: list[dict[str, Any]], item: dict[str, Any], limit: int) -> None:
    bucket.append(item)
    bucket.sort(key=lambda row: int(row.get("bytes", 0) or 0), reverse=True)
    del bucket[limit:]


def scan_drive(root: Path, *, max_files: int, largest_limit: int, top_level_only: bool = False) -> dict[str, Any]:
    if not root.exists():
        raise FileNotFoundError(f"Drive root not found: {root}")
    drive = os.path.splitdrive(str(root.resolve()))[0] or str(root)
    usage = None
    try:
        total, used, free = os.statvfs(str(root))  # type: ignore[attr-defined]
        usage = {"total_bytes": total * used, "free_bytes": free}
    except Exception:
        try:
            import shutil

            disk = shutil.disk_usage(root)
            usage = {
                "total_bytes": disk.total,
                "used_bytes": disk.used,
                "free_bytes": disk.free,
            }
        except Exception:
            usage = {}

    top_dirs: dict[str, dict[str, Any]] = defaultdict(lambda: {"files": 0, "dirs": 0, "bytes": 0})
    extension_counts: Counter[str] = Counter()
    extension_bytes: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    category_bytes: Counter[str] = Counter()
    largest_files: list[dict[str, Any]] = []
    risk_name_hits: list[dict[str, Any]] = []
    mission_fit_examples: list[dict[str, Any]] = []
    recent_files: list[dict[str, Any]] = []
    scanned_files = 0
    scanned_dirs = 0
    skipped_errors: list[str] = []

    if top_level_only:
        for child in root.iterdir():
            try:
                stat = child.stat()
            except Exception as exc:
                skipped_errors.append(f"{safe_rel(child, root)}: {exc}")
                continue
            labels = classify_path(child)
            size = int(stat.st_size) if child.is_file() else 0
            mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            name = child.name
            if child.is_dir():
                scanned_dirs += 1
                top_dirs[name]["dirs"] += 1
            else:
                scanned_files += 1
                top_dirs[name]["files"] += 1
                top_dirs[name]["bytes"] += size
                suffix = child.suffix.lower() or "[no_ext]"
                extension_counts[suffix] += 1
                extension_bytes[suffix] += size
            for label in labels:
                category_counts[label] += 1
                category_bytes[label] += size
            item = {"path": safe_rel(child, root), "bytes": size, "modified_utc": mtime, "labels": sorted(labels)}
            append_largest(largest_files, item, largest_limit)
            recent_files.append(item)
            recent_files.sort(key=lambda row: row["modified_utc"], reverse=True)
            del recent_files[largest_limit:]
            if "secret_or_sensitive_name_review" in labels and len(risk_name_hits) < 100:
                risk_name_hits.append(item)
            if "mission_fit_candidate" in labels and len(mission_fit_examples) < 150:
                mission_fit_examples.append(item)
    else:
        for dirpath, dirnames, filenames in os.walk(root, topdown=True):
            current_dir = Path(dirpath)
            scanned_dirs += 1
            if scanned_files >= max_files:
                break
            top_dirs[top_name(current_dir, root)]["dirs"] += 1
            # Avoid expensive system/recycle walks; keep the fact that they exist.
            dirnames[:] = [
                name
                for name in dirnames
                if name.lower() not in {"$recycle.bin", "system volume information"}
            ]
            for filename in filenames:
                if scanned_files >= max_files:
                    break
                path = current_dir / filename
                try:
                    stat = path.stat()
                except Exception as exc:
                    skipped_errors.append(f"{safe_rel(path, root)}: {exc}")
                    continue
                scanned_files += 1
                size = int(stat.st_size)
                suffix = path.suffix.lower() or "[no_ext]"
                labels = classify_path(path)
                rel = safe_rel(path, root)
                top = top_name(path, root)
                mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

                top_dirs[top]["files"] += 1
                top_dirs[top]["bytes"] += size
                extension_counts[suffix] += 1
                extension_bytes[suffix] += size
                for label in labels:
                    category_counts[label] += 1
                    category_bytes[label] += size

                item = {"path": rel, "bytes": size, "modified_utc": mtime, "labels": sorted(labels)}
                append_largest(largest_files, item, largest_limit)
                append_largest(recent_files, item, largest_limit)
                recent_files.sort(key=lambda row: row["modified_utc"], reverse=True)
                del recent_files[largest_limit:]

                if "secret_or_sensitive_name_review" in labels and len(risk_name_hits) < 100:
                    risk_name_hits.append(item)
                if "mission_fit_candidate" in labels and len(mission_fit_examples) < 150:
                    mission_fit_examples.append(item)

    top_rows = [
        {"name": name, **values}
        for name, values in sorted(top_dirs.items(), key=lambda kv: kv[1]["bytes"], reverse=True)
    ]
    extension_rows = [
        {"extension": ext, "files": extension_counts[ext], "bytes": extension_bytes[ext]}
        for ext, _ in extension_counts.most_common(50)
    ]
    category_rows = [
        {"category": cat, "files": category_counts[cat], "bytes": category_bytes[cat]}
        for cat, _ in category_counts.most_common()
    ]

    return {
        "generated_utc": now_utc(),
        "schema": "external_proof_drive_audit_v1",
        "drive_root": str(root),
        "drive": drive,
        "usage": usage or {},
        "scan_limits": {
            "max_files": max_files,
            "largest_limit": largest_limit,
            "hit_file_limit": scanned_files >= max_files,
            "top_level_only": top_level_only,
        },
        "summary": {
            "scanned_files": scanned_files,
            "scanned_dirs": scanned_dirs,
            "skipped_error_count": len(skipped_errors),
        },
        "top_level": top_rows,
        "extensions": extension_rows,
        "categories": category_rows,
        "largest_files": largest_files,
        "recent_files": recent_files,
        "risk_name_hits": risk_name_hits,
        "mission_fit_examples": mission_fit_examples,
        "skipped_errors": skipped_errors[:100],
        "recommendations": [
            "Do not delete or move files from this audit alone; use it to approve a specific migration or quarantine plan.",
            "Keep raw public datasets under G:/LumaData/<project>/raw and commit only manifests, hashes, schema profiles, and bounded summaries.",
            "Review secret_or_sensitive_name_review hits manually before any public sync, backup, or repo copy.",
            "Treat duplicate-looking pack folders as archives until hashes or human inspection confirm redundancy.",
        ],
    }


def fmt_bytes(value: Any) -> str:
    try:
        size = float(value)
    except Exception:
        return "0 B"
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    idx = 0
    while size >= 1024 and idx < len(units) - 1:
        size /= 1024
        idx += 1
    return f"{size:.2f} {units[idx]}"


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# External Proof Drive Audit",
        "",
        f"Generated UTC: {audit['generated_utc']}",
        "",
        f"Drive root: `{audit['drive_root']}`",
        "",
        "## Summary",
        "",
        f"- Scanned files: {audit['summary']['scanned_files']}",
        f"- Scanned directories: {audit['summary']['scanned_dirs']}",
        f"- Free space: {fmt_bytes(audit.get('usage', {}).get('free_bytes'))}",
        f"- Hit file limit: {audit['scan_limits']['hit_file_limit']}",
        "",
        "## Top-Level Space Use",
        "",
    ]
    for row in audit["top_level"][:25]:
        lines.append(f"- `{row['name']}`: {row['files']} files, {fmt_bytes(row['bytes'])}")
    lines.extend(["", "## Category Counts", ""])
    for row in audit["categories"]:
        lines.append(f"- {row['category']}: {row['files']} files, {fmt_bytes(row['bytes'])}")
    lines.extend(["", "## Largest Files", ""])
    for row in audit["largest_files"][:20]:
        lines.append(f"- `{row['path']}`: {fmt_bytes(row['bytes'])}")
    lines.extend(["", "## Sensitive-Name Review Hits", ""])
    if audit["risk_name_hits"]:
        for row in audit["risk_name_hits"][:30]:
            lines.append(f"- `{row['path']}`: {fmt_bytes(row['bytes'])}")
    else:
        lines.append("- None found by filename scan.")
    lines.extend(["", "## Recommendations", ""])
    lines.extend(f"- {item}" for item in audit["recommendations"])
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "This is a metadata-only, non-destructive audit. It does not prove file contents, does not delete or move data, and must not be used to public-sync secrets or private grant packets.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Non-destructive audit of an external proof/data drive.")
    parser.add_argument("--drive-root", default="G:/")
    parser.add_argument("--max-files", type=int, default=250000)
    parser.add_argument("--largest-limit", type=int, default=50)
    parser.add_argument("--top-level-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = scan_drive(
        Path(args.drive_root),
        max_files=max(1, int(args.max_files)),
        largest_limit=max(5, int(args.largest_limit)),
        top_level_only=bool(args.top_level_only),
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    OUT_MD.write_text(render_markdown(audit).rstrip() + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "scanned_files": audit["summary"]["scanned_files"],
                "scanned_dirs": audit["summary"]["scanned_dirs"],
                "free_space": fmt_bytes(audit.get("usage", {}).get("free_bytes")),
                "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
