from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "grant_submissions" / "DLA26BZ03_NV011_MissionWeave"
OUT_JSON = OUT_DIR / "MISSIONWEAVE_DOCUMENTARY_GAP_INDEX_2026-07-18.json"
OUT_MD = OUT_JSON.with_suffix(".md")

SCHEMA = "lumencore.missionweave_documentary_gap_index.v1"
MAX_FILES_DEFAULT = 1_000_000
EVIDENCE_EXTENSIONS = {
    ".csv",
    ".doc",
    ".docx",
    ".jpeg",
    ".jpg",
    ".json",
    ".pdf",
    ".png",
    ".rtf",
    ".txt",
    ".xlsx",
}
SKIP_DIRECTORY_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "node_modules",
    "temp",
    "venv",
}
SKIP_PATH_FRAGMENTS = {
    ("out", "execution"),
    ("output", "clean-checkout"),
    ("proof_vault", "temp"),
}
DOCUMENT_CLASSES = (
    "DD2345_OR_JCP_APPLICATION_EVIDENCE",
    "MISSIONWEAVE_FWA_TRAINING_EVIDENCE",
    "SAM_REPRESENTATIONS_EVIDENCE",
    "MISSIONWEAVE_PORTAL_PREVIEW_RECEIPT",
)
CLAIM_BOUNDARY = (
    "This index records filename and filesystem metadata only. It does not read document "
    "contents, expose candidate paths, verify authenticity or currency, establish eligibility "
    "or compliance, certify training, confirm a Firm PIN, complete a portal gate, or authorize "
    "submission. Zero filename candidates means no qualifying candidate was located under this "
    "bounded search policy; it does not prove that no document exists elsewhere."
)


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def token_set(name: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", name.lower()) if token}


def classify_filename(name: str) -> set[str]:
    suffix = Path(name).suffix.lower()
    if suffix not in EVIDENCE_EXTENSIONS:
        return set()

    lowered = name.lower()
    tokens = token_set(name)
    classes: set[str] = set()

    dd2345 = bool(re.search(r"dd[^a-z0-9]*2345", lowered)) or {
        "dd",
        "2345",
    }.issubset(tokens)
    jcp = "jcp" in tokens or {
        "joint",
        "certification",
        "program",
    }.issubset(tokens)
    if dd2345 or jcp:
        classes.add("DD2345_OR_JCP_APPLICATION_EVIDENCE")

    fwa = "fwa" in tokens and bool(
        tokens & {"annual", "certificate", "certification", "training"}
    )
    full_fwa = {"fraud", "waste", "abuse"}.issubset(tokens) and bool(
        tokens & {"certificate", "certification", "training"}
    )
    if fwa or full_fwa:
        classes.add("MISSIONWEAVE_FWA_TRAINING_EVIDENCE")

    if "sam" in tokens and bool(
        tokens & {"representation", "representations", "reps"}
    ):
        classes.add("SAM_REPRESENTATIONS_EVIDENCE")

    mission = bool(tokens & {"missionweave", "l26bz", "nv011"})
    preview = {"portal", "preview"}.issubset(tokens)
    receipt = bool(tokens & {"receipt", "review"})
    if mission and preview and receipt:
        classes.add("MISSIONWEAVE_PORTAL_PREVIEW_RECEIPT")

    return classes


def should_skip_directory(relative_parts: tuple[str, ...]) -> bool:
    lowered = tuple(part.lower() for part in relative_parts)
    if any(part in SKIP_DIRECTORY_NAMES for part in lowered):
        return True
    return any(
        len(lowered) >= len(fragment)
        and lowered[-len(fragment) :] == fragment
        for fragment in SKIP_PATH_FRAGMENTS
    )


def scan_root(root_id: str, path: Path, max_files: int) -> dict[str, Any]:
    record: dict[str, Any] = {
        "root_id": root_id,
        "present": path.is_dir(),
        "scan_complete": False,
        "scanned_file_count": 0,
        "skipped_directory_count": 0,
        "metadata_error_count": 0,
        "candidate_counts": {name: 0 for name in DOCUMENT_CLASSES},
        "candidate_details_published": False,
    }
    if not path.is_dir():
        record["status"] = "ROOT_MISSING"
        return record

    limit_reached = False

    def onerror(_: OSError) -> None:
        record["metadata_error_count"] += 1

    for current, directories, files in os.walk(
        path, topdown=True, followlinks=False, onerror=onerror
    ):
        current_path = Path(current)
        try:
            relative = current_path.relative_to(path)
            relative_parts = relative.parts
        except ValueError:
            record["metadata_error_count"] += 1
            continue

        kept_directories: list[str] = []
        for directory in directories:
            parts = relative_parts + (directory,)
            if should_skip_directory(parts):
                record["skipped_directory_count"] += 1
            else:
                kept_directories.append(directory)
        directories[:] = kept_directories

        for filename in files:
            if record["scanned_file_count"] >= max_files:
                limit_reached = True
                break
            record["scanned_file_count"] += 1
            for document_class in classify_filename(filename):
                record["candidate_counts"][document_class] += 1
        if limit_reached:
            break

    record["scan_complete"] = not limit_reached and record["metadata_error_count"] == 0
    if limit_reached:
        record["status"] = "FILE_LIMIT_REACHED"
    elif record["metadata_error_count"]:
        record["status"] = "METADATA_ERRORS_PRESENT"
    else:
        record["status"] = "COMPLETE"
    return record


def default_roots() -> list[tuple[str, Path]]:
    return [
        ("repository", ROOT),
        ("icloud_drive", Path.home() / "iCloudDrive"),
        ("proof_vault", Path("E:/LumaProofVault")),
    ]


def build_payload(
    roots: Iterable[tuple[str, Path]] | None = None,
    *,
    generated_utc: str | None = None,
    max_files: int = MAX_FILES_DEFAULT,
) -> dict[str, Any]:
    if max_files <= 0:
        raise ValueError("max_files must be positive")
    root_rows = [scan_root(root_id, path, max_files) for root_id, path in (roots or default_roots())]
    totals = {name: 0 for name in DOCUMENT_CLASSES}
    for row in root_rows:
        for name, count in row["candidate_counts"].items():
            totals[name] += int(count)

    scan_complete = all(row["scan_complete"] for row in root_rows)
    candidate_total = sum(totals.values())
    if not scan_complete:
        status = "METADATA_SCAN_INCOMPLETE"
    elif candidate_total:
        status = "PRIVATE_MANUAL_DOCUMENT_REVIEW_REQUIRED"
    else:
        status = "NO_QUALIFYING_DOCUMENTARY_CANDIDATES_LOCATED"

    gate_decisions = {
        name: (
            "REVIEW_METADATA_CANDIDATE_PRIVATELY"
            if totals[name]
            else "NO_CHANGE_KEEP_GATE_OPEN"
        )
        for name in DOCUMENT_CLASSES
    }
    gate_decisions["DSIP_FIRM_PIN_AVAILABILITY"] = (
        "PORTAL_ONLY_NO_FILE_INFERENCE"
    )

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_utc": generated_utc or utc_now(),
        "status": status,
        "scan_mode": "FILENAME_AND_FILESYSTEM_METADATA_ONLY",
        "controls": {
            "file_contents_read": False,
            "candidate_paths_published": False,
            "symlinks_followed": False,
            "credentials_or_private_values_collected": False,
            "gate_changes_automatic": False,
            "maximum_files_per_root": max_files,
        },
        "search_policy": {
            "document_classes": list(DOCUMENT_CLASSES),
            "evidence_extensions": sorted(EVIDENCE_EXTENSIONS),
            "skipped_directory_names": sorted(SKIP_DIRECTORY_NAMES),
            "skipped_path_fragments": ["/".join(row) for row in sorted(SKIP_PATH_FRAGMENTS)],
        },
        "roots": root_rows,
        "summary": {
            "root_count": len(root_rows),
            "present_root_count": sum(1 for row in root_rows if row["present"]),
            "complete_root_count": sum(1 for row in root_rows if row["scan_complete"]),
            "scanned_file_count": sum(row["scanned_file_count"] for row in root_rows),
            "skipped_directory_count": sum(
                row["skipped_directory_count"] for row in root_rows
            ),
            "metadata_error_count": sum(row["metadata_error_count"] for row in root_rows),
            "candidate_total": candidate_total,
            "candidate_counts": totals,
        },
        "gate_decisions": gate_decisions,
        "next_actions": [
            "Keep the named documentary gates open unless a current record is reviewed privately.",
            "Complete FWA training, Firm PIN verification, and the final preview inside authenticated DSIP.",
            "Treat DD Form 2345/JCP, SAM representations, and portal-preview facts as current only after documentary or portal review.",
        ],
        "claim_boundary": CLAIM_BOUNDARY,
        "outputs": {
            "json": OUT_JSON.relative_to(ROOT).as_posix(),
            "markdown": OUT_MD.relative_to(ROOT).as_posix(),
        },
    }
    payload["index_sha256"] = stable_hash(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# MissionWeave Documentary Gap Index - 2026-07-18",
        "",
        f"Status: `{payload['status']}`",
        f"Index SHA-256: `{payload['index_sha256']}`",
        "",
        "## Scan Boundary",
        "",
        f"- Mode: `{payload['scan_mode']}`",
        f"- Roots complete: `{summary['complete_root_count']}/{summary['root_count']}`",
        f"- Files inspected by name: `{summary['scanned_file_count']}`",
        f"- Candidate records: `{summary['candidate_total']}`",
        "- File contents read: `false`",
        "- Candidate paths published: `false`",
        "- Automatic gate changes: `false`",
        "",
        "## Candidate Counts",
        "",
        "| Documentary class | Count | Gate decision |",
        "|---|---:|---|",
    ]
    for name in DOCUMENT_CLASSES:
        lines.append(
            f"| `{name}` | `{summary['candidate_counts'][name]}` | "
            f"`{payload['gate_decisions'][name]}` |"
        )
    lines.append(
        "| `DSIP_FIRM_PIN_AVAILABILITY` | `n/a` | "
        f"`{payload['gate_decisions']['DSIP_FIRM_PIN_AVAILABILITY']}` |"
    )
    lines.extend(["", "## Next Actions", ""])
    lines.extend(
        f"{index}. {item}" for index, item in enumerate(payload["next_actions"], 1)
    )
    lines.extend(["", "## Claim Boundary", "", payload["claim_boundary"], ""])
    return "\n".join(lines)


def parse_root(value: str) -> tuple[str, Path]:
    root_id, separator, raw_path = value.partition("=")
    if not separator or not root_id.strip() or not raw_path.strip():
        raise argparse.ArgumentTypeError("root must use ROOT_ID=PATH")
    return root_id.strip(), Path(raw_path).expanduser()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", action="append", type=parse_root, dest="roots")
    parser.add_argument("--max-files", type=int, default=MAX_FILES_DEFAULT)
    parser.add_argument("--generated-utc")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    payload = build_payload(
        args.roots,
        generated_utc=args.generated_utc,
        max_files=args.max_files,
    )
    if not args.check_only:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        OUT_JSON.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "scan_complete": payload["summary"]["complete_root_count"]
                == payload["summary"]["root_count"],
                "scanned_file_count": payload["summary"]["scanned_file_count"],
                "candidate_total": payload["summary"]["candidate_total"],
                "index_sha256": payload["index_sha256"],
                "outputs_written": not args.check_only,
            },
            indent=2,
        )
    )
    return 0 if payload["status"] != "METADATA_SCAN_INCOMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
