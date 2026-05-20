#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STACK_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = STACK_ROOT / "out" / "ops"
DEFAULT_EXTERNAL_PATHS = [
    Path(r"C:\Users\Novac\FLOWFORM_TOURNAMENT"),
    Path(r"C:\Users\Novac\Luma_HardValidation_Lab"),
]

HIGH_SIGNAL_RE = re.compile(
    r"(proof|audit|validation|leaderboard|edge|optimizer|flow|regime|risk|kpi|roi|backtest|selection|universe|score|report|truth)",
    re.IGNORECASE,
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def scan_path(root: Path, max_recent: int, max_candidates: int) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "path": str(root),
        "exists": root.exists(),
        "file_count": 0,
        "dir_count": 0,
        "total_size_bytes": 0,
        "extensions": {},
        "recent_files": [],
        "high_signal_candidates": [],
    }
    if not root.exists() or not root.is_dir():
        return summary

    ext_counter: Counter[str] = Counter()
    recent_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []

    for path in root.rglob("*"):
        if path.is_dir():
            summary["dir_count"] += 1
            continue
        if not path.is_file():
            continue

        summary["file_count"] += 1
        try:
            st = path.stat()
            size = int(st.st_size)
            mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
        except Exception:
            size = 0
            mtime = datetime.fromtimestamp(0, tz=timezone.utc)

        summary["total_size_bytes"] += size
        ext = path.suffix.lower() or "<none>"
        ext_counter[ext] += 1

        rel = str(path.relative_to(root)).replace("\\", "/")
        row = {
            "relative_path": rel,
            "size_bytes": size,
            "mtime_utc": mtime.isoformat(),
            "extension": ext,
        }
        recent_rows.append(row)

        lower_rel = rel.lower()
        ext_bonus = 1.0 if ext in {".py", ".json", ".csv", ".md", ".ps1"} else 0.25
        signal_bonus = 2.0 if HIGH_SIGNAL_RE.search(lower_rel) else 0.0
        freshness_bonus = max(0.0, 1.0 - ((datetime.now(timezone.utc) - mtime).total_seconds() / 86400.0 / 30.0))
        size_bonus = min(1.0, size / (256.0 * 1024.0))
        score = round(ext_bonus + signal_bonus + freshness_bonus + size_bonus, 4)
        if score >= 2.2:
            candidate_rows.append(
                {
                    "relative_path": rel,
                    "score": score,
                    "size_bytes": size,
                    "mtime_utc": mtime.isoformat(),
                    "reason": "high_signal_name_or_type",
                }
            )

    summary["extensions"] = dict(sorted(ext_counter.items(), key=lambda item: item[1], reverse=True))

    recent_rows.sort(key=lambda row: row.get("mtime_utc", ""), reverse=True)
    summary["recent_files"] = recent_rows[:max_recent]

    candidate_rows.sort(key=lambda row: (row.get("score", 0.0), row.get("mtime_utc", "")), reverse=True)
    summary["high_signal_candidates"] = candidate_rows[:max_candidates]
    summary["total_size_mb"] = round(summary["total_size_bytes"] / (1024.0 * 1024.0), 3)

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory external folders and produce ingest candidates for optimization context.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory for report artifacts")
    parser.add_argument("--paths", nargs="*", default=[str(p) for p in DEFAULT_EXTERNAL_PATHS], help="External paths to scan")
    parser.add_argument("--max-recent", type=int, default=25, help="Max recent files per path")
    parser.add_argument("--max-candidates", type=int, default=50, help="Max high-signal candidates per path")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    scan_paths = [Path(p) for p in args.paths]

    reports = [scan_path(path, max_recent=max(1, args.max_recent), max_candidates=max(1, args.max_candidates)) for path in scan_paths]
    total_files = sum(int(item.get("file_count", 0)) for item in reports)
    total_size_mb = round(sum(float(item.get("total_size_mb", 0.0)) for item in reports), 3)

    payload = {
        "generated_utc": now_utc(),
        "scope": "external_context_ingest_inventory",
        "paths_scanned": [str(p) for p in scan_paths],
        "summary": {
            "path_count": len(scan_paths),
            "existing_path_count": sum(1 for item in reports if item.get("exists")),
            "total_files": total_files,
            "total_size_mb": total_size_mb,
        },
        "reports": reports,
    }

    tag = utc_tag()
    ts_path = out_dir / f"external_context_inventory_{tag}.json"
    latest_path = out_dir / "external_context_inventory_latest.json"
    save_json(ts_path, payload)
    save_json(latest_path, payload)

    manifest = {
        "generated_utc": payload.get("generated_utc"),
        "summary": payload.get("summary"),
        "artifacts": {
            "timestamped": str(ts_path),
            "latest": str(latest_path),
        },
    }
    manifest_path = out_dir / f"external_context_inventory_manifest_{tag}.json"
    save_json(manifest_path, manifest)

    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
