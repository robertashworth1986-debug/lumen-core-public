from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT_DIR = ROOT / "out" / "ops"

ICLOUD_ROOT = Path(r"C:\Users\Novac\iCloudDrive")
C_DRIVE_ROOT = Path("C:\\")

DEEP_SCAN_ROOTS = [
    ICLOUD_ROOT / "The master master dossier",
    ICLOUD_ROOT / "Big bad pitch deck_",
    ICLOUD_ROOT / "Grants",
    ICLOUD_ROOT / "Formal submission_",
    ICLOUD_ROOT / "LumenCore_SBIR",
    ICLOUD_ROOT / "Doe work space",
    ICLOUD_ROOT / "DoD",
    ICLOUD_ROOT / "LumenCore_Patent_Bundle",
    ICLOUD_ROOT / "Non-prob.patent_",
    ICLOUD_ROOT / "Lawyer patent addendum_",
    ICLOUD_ROOT / "Data sets",
    ICLOUD_ROOT / "EVIDENCE",
    ICLOUD_ROOT / "Test key for grant",
    Path(r"C:\01_Overview"),
    Path(r"C:\02_Technical"),
    Path(r"C:\03_Commercial"),
    Path(r"C:\04_Proof"),
]

SKIP_DIR_NAMES = {
    ".git",
    ".trash",
    ".venv",
    "venv",
    "env",
    "env311",
    "node_modules",
    "site-packages",
    "__pycache__",
    "$recycle.bin",
    "system volume information",
}

SENSITIVE_PATTERN = re.compile(
    r"(?i)(password|passwd|credential|secret|token|api[ _-]?key|"
    r"personal[ _-]?key|private[ _-]?key|driver.?license|passport|"
    r"social.?security|bank|routing|account.?number|kraken|fidelity|"
    r"tax.?return|w-?2|1099|medical|hipaa)"
)

CATEGORY_RULES = [
    ("submission_record", re.compile(r"(?i)(submissionfiles|submitted|receipt|confirmation|tracking)")),
    ("patent_ip", re.compile(r"(?i)(patent|provisional|claim|prior.?art|novelty|intellectual.?property)")),
    ("grant_application", re.compile(r"(?i)(grant|sbir|sttr|proposal|concept.?paper|technical.?volume)")),
    ("benchmark_evidence", re.compile(r"(?i)(benchmark|kpi|stability|evidence|proof|metric|simulation|delta)")),
    ("commercialization", re.compile(r"(?i)(commercial|investor|market|pitch|customer|revenue|roi)")),
    ("technical_reference", re.compile(r"(?i)(technical|architecture|algorithm|geometry|flowform|harmonic)")),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_stat(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
        return {
            "size_bytes": stat.st_size if path.is_file() else None,
            "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        }
    except OSError:
        return {"size_bytes": None, "modified_utc": None}


def classify(path: Path) -> list[str]:
    text = str(path)
    categories = [name for name, pattern in CATEGORY_RULES if pattern.search(text)]
    return categories or ["uncategorized"]


def is_sensitive(path: Path) -> bool:
    return bool(SENSITIVE_PATTERN.search(path.name))


def iter_top_level(root: Path) -> Iterable[Path]:
    try:
        yield from root.iterdir()
    except OSError:
        return


def iter_deep_files(root: Path, max_files: int) -> tuple[list[Path], int]:
    files: list[Path] = []
    excluded = 0
    if not root.exists():
        return files, excluded

    for current, dirs, names in os.walk(root):
        current_path = Path(current)
        kept_dirs: list[str] = []
        for name in dirs:
            candidate = current_path / name
            if name.lower() in SKIP_DIR_NAMES or is_sensitive(candidate):
                excluded += 1
            else:
                kept_dirs.append(name)
        dirs[:] = kept_dirs

        for name in names:
            candidate = current_path / name
            if is_sensitive(candidate):
                excluded += 1
                continue
            files.append(candidate)
            if len(files) >= max_files:
                return files, excluded
    return files, excluded


def entry(path: Path, scan_kind: str) -> dict[str, Any]:
    stat = safe_stat(path)
    return {
        "path": str(path),
        "name": path.name,
        "type": "directory" if path.is_dir() else "file",
        "scan_kind": scan_kind,
        "categories": classify(path),
        **stat,
    }


def build_catalog(max_files_per_root: int) -> dict[str, Any]:
    top_level_entries: list[dict[str, Any]] = []
    for root in (ICLOUD_ROOT, C_DRIVE_ROOT):
        for path in iter_top_level(root):
            top_level_entries.append(entry(path, "top_level_metadata"))

    file_entries: list[dict[str, Any]] = []
    roots: list[dict[str, Any]] = []
    excluded_total = 0
    for root in DEEP_SCAN_ROOTS:
        files, excluded = iter_deep_files(root, max_files=max_files_per_root)
        excluded_total += excluded
        roots.append(
            {
                "path": str(root),
                "exists": root.exists(),
                "indexed_files": len(files),
                "excluded_entries": excluded,
                "truncated": len(files) >= max_files_per_root,
            }
        )
        file_entries.extend(entry(path, "allowlisted_deep_metadata") for path in files)

    category_counts: Counter[str] = Counter()
    extension_counts: Counter[str] = Counter()
    for row in file_entries:
        category_counts.update(row["categories"])
        extension_counts[Path(row["path"]).suffix.lower() or "[no extension]"] += 1

    submission_candidates = [
        row
        for row in file_entries
        if "submission_record" in row["categories"]
    ]

    return {
        "schema_version": "1.0",
        "generated_utc": now_iso(),
        "policy": {
            "mode": "metadata_only",
            "content_read": False,
            "files_copied": False,
            "file_hashes_computed": False,
            "sensitive_name_exclusion": True,
            "note": (
                "Top-level folders are cataloged broadly. Recursive indexing is limited "
                "to grant, patent, evidence, technical, and commercialization roots."
            ),
        },
        "top_level_entries": sorted(top_level_entries, key=lambda row: row["path"].lower()),
        "deep_scan_roots": roots,
        "files": sorted(file_entries, key=lambda row: row["path"].lower()),
        "summary": {
            "top_level_entry_count": len(top_level_entries),
            "deep_file_count": len(file_entries),
            "excluded_entry_count": excluded_total,
            "category_counts": dict(category_counts.most_common()),
            "extension_counts": dict(extension_counts.most_common(30)),
            "submission_candidate_count": len(submission_candidates),
        },
        "submission_candidates": submission_candidates,
    }


def render_markdown(catalog: dict[str, Any]) -> str:
    summary = catalog["summary"]
    lines = [
        "# External Evidence Source Catalog",
        "",
        f"Generated: {catalog['generated_utc']}",
        "",
        "This is a read-only metadata catalog. It does not copy, hash, or read source contents.",
        "",
        "## Summary",
        "",
        f"- Top-level entries: {summary['top_level_entry_count']}",
        f"- Allowlisted files indexed: {summary['deep_file_count']}",
        f"- Sensitive or dependency entries excluded: {summary['excluded_entry_count']}",
        f"- Submission-record candidates: {summary['submission_candidate_count']}",
        "",
        "## Evidence Categories",
        "",
    ]
    for name, count in summary["category_counts"].items():
        lines.append(f"- {name}: {count}")

    lines.extend(["", "## Deep-Scan Roots", ""])
    for row in catalog["deep_scan_roots"]:
        state = "available" if row["exists"] else "missing"
        suffix = " (truncated)" if row["truncated"] else ""
        lines.append(
            f"- `{row['path']}`: {state}, {row['indexed_files']} files, "
            f"{row['excluded_entries']} excluded{suffix}"
        )

    lines.extend(["", "## Submission Candidates", ""])
    candidates = catalog["submission_candidates"]
    if not candidates:
        lines.append("- None found by filename.")
    else:
        for row in candidates[:100]:
            lines.append(f"- `{row['path']}`")

    lines.extend(
        [
            "",
            "## Evidence Rule",
            "",
            "A cataloged artifact is a lead, not proof. Grant claims should cite the source, "
            "state whether the value is measured or modeled, and identify the validation protocol.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-files-per-root", type=int, default=15_000)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    catalog = build_catalog(max_files_per_root=max(1, args.max_files_per_root))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "external_source_catalog.json"
    md_path = args.output_dir / "external_source_catalog.md"
    json_path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(catalog), encoding="utf-8")

    print(json.dumps({"json": str(json_path), "markdown": str(md_path), **catalog["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
