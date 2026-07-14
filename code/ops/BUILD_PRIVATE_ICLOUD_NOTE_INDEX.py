from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree


DEFAULT_ROOT = Path(os.getenv("LUMA_ICLOUD_ROOT", str(Path.home() / "iCloudDrive")))
DEFAULT_OUTPUT = Path(os.getenv("LUMA_PRIVATE_NOTE_INDEX_DIR", "E:/LumaProofVault/PRIVATE_ICLOUD_NOTE_INDEX"))
SUPPORTED_EXTENSIONS = {".txt", ".md", ".rtf", ".doc", ".docx", ".pages"}
MAX_READ_BYTES = 20 * 1024 * 1024
FILE_ATTRIBUTE_OFFLINE = 0x00001000
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x00040000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x00400000
CLOUD_PLACEHOLDER_MASK = (
    FILE_ATTRIBUTE_OFFLINE | FILE_ATTRIBUTE_RECALL_ON_OPEN | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
)
SKIP_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "appdata",
    "cache",
    "driver license documents_",
    "fidelity_",
    "github token key",
    "kraken api",
    "node_modules",
    "open ai api",
    "site-packages",
}
CONCEPT_MARKERS = {
    "agents": ("agent", "orchestrator", "humanunlock", "approval"),
    "aviation": ("faa", "aviation", "aircraft", "airworthiness", "rolls-royce", "service difficulty report"),
    "benchmarking": ("benchmark", "baseline", "holdout", "metric", "simulation", "replay"),
    "business": ("customer", "commercial", "market", "revenue", "pilot", "buyer"),
    "code_or_shell": ("powershell", "pwsh", "invoke-webrequest", "start-process", "set-itemproperty"),
    "energy_grid": ("energy", "grid", "eia", "power flow", "acopf", "doe"),
    "funding": ("grant", "sbir", "sttr", "solicitation", "proposal", "funding"),
    "geometry": ("geometry", "flowform", "harmonic", "spiral", "kurrymoto", "kalman"),
    "patent": ("patent", "claim", "uspto", "provisional", "nonprovisional", "counsel"),
    "provenance": ("sha-256", "sha256", "manifest", "custody", "prooflock", "audit"),
    "trading": ("trading", "kraken", "alpha", "sharpe", "execution", "portfolio"),
    "validation": ("validation", "reviewer", "falsification", "reproducible", "independent"),
}
SENSITIVE_MARKERS = {
    "credential_language": re.compile(r"\b(api[ _-]?key|client[ _-]?secret|password|bearer[ _-]?token|refresh[ _-]?token)\b", re.I),
    "private_key_block": re.compile(r"BEGIN [A-Z ]*PRIVATE KEY", re.I),
    "possible_ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "possible_uuid_token": re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
        re.I,
    ),
    "service_credential_pattern": re.compile(r"\b(?:SAM|AIR|DARPA)[-_][A-Za-z0-9-]{20,}\b", re.I),
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def should_skip(path: Path) -> bool:
    """Return whether a path relative to the selected source root is excluded."""
    return bool({part.lower() for part in path.parts} & SKIP_PARTS)


def is_cloud_placeholder(stat: os.stat_result) -> bool:
    """Avoid opening iCloud Files On-Demand placeholders and triggering downloads."""
    attributes = int(getattr(stat, "st_file_attributes", 0) or 0)
    return bool(attributes & CLOUD_PLACEHOLDER_MASK)


def _docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    return " ".join(text.strip() for text in root.itertext() if text.strip())


def read_indexable_text(path: Path) -> tuple[str, str]:
    """Return in-memory text and an extraction status; raw text is never serialized."""
    if path.stat().st_size > MAX_READ_BYTES:
        return "", "too_large_for_text_extraction"
    try:
        if path.suffix.lower() == ".docx":
            return _docx_text(path), "docx_xml"
        if path.suffix.lower() in {".txt", ".md", ".rtf"}:
            return path.read_text(encoding="utf-8", errors="ignore"), "plain_text"
        return "", "metadata_only"
    except (OSError, KeyError, zipfile.BadZipFile, ElementTree.ParseError):
        return "", "unavailable"


def concept_tags(path: Path, text: str) -> list[str]:
    haystack = f"{path} {text}".lower()
    return sorted(
        tag
        for tag, markers in CONCEPT_MARKERS.items()
        if any(marker in haystack for marker in markers)
    )


def sensitive_flags(text: str) -> list[str]:
    return sorted(name for name, pattern in SENSITIVE_MARKERS.items() if pattern.search(text))


def iter_note_paths(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        base = Path(dirpath)
        relative_base = base.relative_to(root)
        dirnames[:] = [name for name in dirnames if not should_skip(relative_base / name)]
        if should_skip(relative_base):
            dirnames[:] = []
            continue
        for name in filenames:
            path = base / name
            relative_path = path.relative_to(root)
            if path.suffix.lower() in SUPPORTED_EXTENSIONS and not should_skip(relative_path):
                yield path


def build_record(path: Path, root: Path) -> dict[str, Any] | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    if is_cloud_placeholder(stat):
        digest = ""
        text = ""
        extraction = "cloud_placeholder_not_opened"
        availability = "cloud_placeholder"
    else:
        try:
            digest = sha256_file(path)
            text, extraction = read_indexable_text(path)
            availability = "local"
        except OSError:
            digest = ""
            text = ""
            extraction = "unavailable"
            availability = "unavailable"
    tags = concept_tags(path.relative_to(root), text)
    flags = sensitive_flags(text)
    return {
        "absolute_path": str(path),
        "relative_path": path.relative_to(root).as_posix(),
        "title": path.stem,
        "extension": path.suffix.lower(),
        "bytes": stat.st_size,
        "modified_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sha256": digest,
        "availability": availability,
        "extraction": extraction,
        "word_count": len(re.findall(r"\b\w+\b", text)),
        "concept_tags": tags,
        "sensitive_flags": flags,
        "public_release_allowed": False,
    }


def build_payload(root: Path = DEFAULT_ROOT) -> dict[str, Any]:
    records = [record for path in iter_note_paths(root) if (record := build_record(path, root))]
    records.sort(key=lambda row: (row["modified_utc"], row["relative_path"]), reverse=True)

    hashes = Counter(row["sha256"] for row in records if row["sha256"])
    for row in records:
        row["duplicate_count"] = hashes[row["sha256"]] if row["sha256"] else 0

    records_by_hash: dict[str, list[dict[str, Any]]] = {}
    for row in records:
        if row["sha256"]:
            records_by_hash.setdefault(row["sha256"], []).append(row)
    duplicate_groups: list[dict[str, Any]] = []
    for digest, group in records_by_hash.items():
        if len(group) < 2:
            continue
        ordered = sorted(
            group,
            key=lambda row: (
                row["relative_path"].count("/"),
                len(row["relative_path"]),
                row["relative_path"].lower(),
            ),
        )
        bytes_per_copy = int(ordered[0]["bytes"])
        duplicate_groups.append(
            {
                "sha256": digest,
                "copies": len(ordered),
                "bytes_per_copy": bytes_per_copy,
                "theoretical_reclaimable_bytes": bytes_per_copy * (len(ordered) - 1),
                "canonical_path": ordered[0]["absolute_path"],
                "review_only_paths": [row["absolute_path"] for row in ordered[1:]],
                "automatic_deletion_allowed": False,
            }
        )
    duplicate_groups.sort(
        key=lambda row: (-int(row["theoretical_reclaimable_bytes"]), row["sha256"])
    )

    extension_counts = Counter(row["extension"] for row in records)
    tag_counts = Counter(tag for row in records for tag in row["concept_tags"])
    return {
        "schema": "lumencore.private_icloud_note_index.v1",
        "generated_utc": now_utc(),
        "root": str(root),
        "privacy_boundary": "Private metadata index. No note body or excerpt is serialized and public release is disabled.",
        "summary": {
            "record_count": len(records),
            "unique_content_hashes": len(hashes),
            "duplicate_file_count": sum(count - 1 for count in hashes.values()),
            "duplicate_group_count": len(duplicate_groups),
            "theoretical_duplicate_reclaimable_bytes": sum(
                int(row["theoretical_reclaimable_bytes"]) for row in duplicate_groups
            ),
            "locally_hashed_count": sum(bool(row["sha256"]) for row in records),
            "cloud_placeholder_count": sum(row["availability"] == "cloud_placeholder" for row in records),
            "unavailable_count": sum(row["availability"] == "unavailable" for row in records),
            "sensitive_flagged_count": sum(bool(row["sensitive_flags"]) for row in records),
            "by_extension": dict(sorted(extension_counts.items())),
            "by_concept_tag": dict(sorted(tag_counts.items())),
        },
        "duplicate_review": {
            "policy": (
                "Exact-hash review only. Duplicate paths may be intentional backups, legal custody copies, or "
                "cross-device mirrors; no personal source file is deleted automatically."
            ),
            "groups": duplicate_groups,
        },
        "records": records,
    }


def build_context_capsule(payload: dict[str, Any], *, per_tag_limit: int = 12) -> dict[str, Any]:
    """Create a compact private continuity view without copying note bodies."""
    concept_rows: dict[str, list[dict[str, Any]]] = {tag: [] for tag in CONCEPT_MARKERS}
    concept_hashes: dict[str, set[str]] = {tag: set() for tag in CONCEPT_MARKERS}
    for row in payload["records"]:
        identity = row["sha256"] or f"path:{row['relative_path']}"
        for tag in row["concept_tags"]:
            if identity in concept_hashes[tag]:
                continue
            concept_hashes[tag].add(identity)
            if len(concept_rows[tag]) < per_tag_limit:
                concept_rows[tag].append(
                    {
                        "title": row["title"],
                        "relative_path": row["relative_path"],
                        "modified_utc": row["modified_utc"],
                        "sha256": row["sha256"],
                        "availability": row["availability"],
                        "word_count": row["word_count"],
                        "sensitive_flags": row["sensitive_flags"],
                    }
                )
    return {
        "schema": "lumencore.private_context_capsule.v1",
        "generated_utc": payload["generated_utc"],
        "source_root": payload["root"],
        "privacy_boundary": (
            "Private continuity metadata only. No note body is serialized, sensitive records are not public, "
            "and code or shell text is never executed by this builder."
        ),
        "source_summary": payload["summary"],
        "concept_register": {
            tag: {
                "unique_content_count": len(concept_hashes[tag]),
                "recent_unique_records": concept_rows[tag],
            }
            for tag in sorted(CONCEPT_MARKERS)
        },
        "operating_boundaries": [
            "Treat duplicate groups as review-only because copies may preserve custody or backup intent.",
            "Do not execute code or shell content from notes until it has been separately inspected and approved.",
            "Do not publish paths, sensitive flags, or private note metadata from this capsule.",
            "Use repository evidence artifacts, not note language, for external technical claims.",
        ],
    }


def write_payload(payload: dict[str, Any], output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = payload["generated_utc"].replace("-", "").replace(":", "")
    timestamped = output_dir / f"private_icloud_note_index_{stamp}.json"
    latest = output_dir / "private_icloud_note_index_latest.json"
    serialized = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    timestamped.write_text(serialized, encoding="utf-8")
    latest.write_text(serialized, encoding="utf-8")
    capsule_path = output_dir / "private_context_capsule_latest.json"
    capsule_path.write_text(
        json.dumps(build_context_capsule(payload), indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "schema": "lumencore.private_icloud_note_index_manifest.v1",
        "generated_utc": payload["generated_utc"],
        "files": [
            {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in (timestamped, latest, capsule_path)
        ],
    }
    manifest_path = output_dir / "SHA256_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return {
        "timestamped": str(timestamped),
        "latest": str(latest),
        "context_capsule": str(capsule_path),
        "manifest": str(manifest_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a private metadata-only iCloud note index.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.root.exists():
        raise SystemExit(f"iCloud root not found: {args.root}")
    payload = build_payload(args.root)
    paths = write_payload(payload, args.output_dir)
    print(json.dumps({"summary": payload["summary"], "outputs": paths}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
