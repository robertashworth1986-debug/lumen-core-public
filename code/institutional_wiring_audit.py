from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
DASHBOARD = ROOT / "dashboard"
OUT = ROOT / "out" / "execution"

MAIN_RE = re.compile(r"if\s+__name__\s*==\s*[\"']__main__[\"']")
PY_PATH_RE = re.compile(r"([A-Za-z0-9_./\\\\:-]+\.py)")

SURFACE_FILES = [
    ROOT / "launch_all_engines.ps1",
    CODE / "luma_supervisor.py",
    CODE / "luma_experience_gateway.py",
    CODE / "FULL_TRUTH_ORCHESTRATOR.py",
    CODE / "RUN_MOONSHOT_TWIN_ENGINE.ps1",
    CODE / "ops" / "RECOVER_LOCAL_RUNTIME.ps1",
]

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "out",
}

CORE_NAME_MARKERS = (
    "engine",
    "orchestrator",
    "watcher",
    "daemon",
    "router",
    "executor",
    "autopilot",
    "supervisor",
    "scanner",
    "runner",
)

ARCHIVE_DIR_MARKERS = {
    "archive",
    "archives",
    "history",
    "snapshots",
}

ARCHIVE_FILE_MARKERS = (
    "backup",
    "premerge",
    "_bak",
    ".bak",
    "_old",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def file_line_count(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            return sum(1 for _ in handle)
    except Exception:
        return 0


def file_mtime_utc(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except Exception:
        return ""


def discover_python_candidates() -> list[Path]:
    discovered: list[Path] = []

    if CODE.exists():
        for path in CODE.rglob("*.py"):
            rel_parts = set(path.relative_to(ROOT).parts)
            if rel_parts.intersection(SKIP_DIR_NAMES):
                continue
            discovered.append(path)

    if DASHBOARD.exists():
        for path in DASHBOARD.glob("*.py"):
            discovered.append(path)

    for path in ROOT.glob("*.py"):
        discovered.append(path)

    unique: dict[str, Path] = {}
    for path in discovered:
        try:
            key = str(path.resolve()).lower()
        except Exception:
            key = str(path).lower()
        unique[key] = path
    return sorted(unique.values())


def discover_secondary_surfaces() -> list[Path]:
    candidates: list[Path] = []

    candidates.extend(ROOT.glob("*.ps1"))

    if CODE.exists():
        candidates.extend(CODE.rglob("RUN*.ps1"))
        candidates.extend(CODE.rglob("START*.ps1"))

    deploy_dir = ROOT / "deploy"
    if deploy_dir.exists():
        candidates.extend(deploy_dir.rglob("*.sh"))

    unique: dict[str, Path] = {}
    for path in candidates:
        try:
            key = str(path.resolve()).lower()
        except Exception:
            key = str(path).lower()
        unique[key] = path

    primary = {str(p.resolve()).lower() for p in SURFACE_FILES if p.exists()}
    out = []
    for path in unique.values():
        try:
            key = str(path.resolve()).lower()
        except Exception:
            key = str(path).lower()
        if key in primary:
            continue
        out.append(path)

    return sorted(out)


def discover_runnable_scripts() -> list[Path]:
    runnables: list[Path] = []
    for path in discover_python_candidates():
        txt = read_text(path)
        if MAIN_RE.search(txt):
            runnables.append(path)

    for surface in SURFACE_FILES:
        if not surface.exists():
            continue
        txt = read_text(surface)
        for match in PY_PATH_RE.findall(txt):
            raw = match.strip().strip('"\'')
            norm = raw.replace("\\", "/")
            if not norm.lower().endswith(".py"):
                continue

            candidate = Path(norm)
            if not candidate.is_absolute():
                candidate = ROOT / norm

            if candidate.exists() and candidate.is_file():
                runnables.append(candidate)

    unique: dict[str, Path] = {}
    for path in runnables:
        try:
            key = str(path.resolve()).lower()
        except Exception:
            key = str(path).lower()
        unique[key] = path

    return sorted(unique.values())


def is_archive_or_backup(path: Path) -> bool:
    try:
        rel_parts = [p.lower() for p in path.relative_to(ROOT).parts]
    except Exception:
        rel_parts = [p.lower() for p in path.parts]

    filename = path.name.lower()
    if any(part in ARCHIVE_DIR_MARKERS for part in rel_parts):
        return True
    if any(marker in filename for marker in ARCHIVE_FILE_MARKERS):
        return True
    return False


def is_core_script_name(path: Path) -> bool:
    name = path.name.lower()
    return any(marker in name for marker in CORE_NAME_MARKERS)


def classify_wiring(runnables: list[Path], include_archive: bool = False) -> dict:
    surface_texts = {}
    for surface in SURFACE_FILES:
        if surface.exists():
            surface_texts[surface] = read_text(surface)

    surface_rel_paths = {str(p.relative_to(ROOT)).replace("\\", "/") for p in surface_texts.keys()}

    secondary_surface_texts = {}
    for surface in discover_secondary_surfaces():
        if surface.exists():
            secondary_surface_texts[surface] = read_text(surface)

    records = []
    for script in runnables:
        rel_script = str(script.relative_to(ROOT)).replace("\\", "/")
        filename = script.name
        line_count = file_line_count(script)
        mtime_utc = file_mtime_utc(script)
        hits: list[str] = []

        if not include_archive and is_archive_or_backup(script):
            records.append(
                {
                    "script": rel_script,
                    "filename": filename,
                    "line_count": line_count,
                    "mtime_utc": mtime_utc,
                    "wired": False,
                    "surface_hits": hits,
                    "classification": "excluded_archive",
                }
            )
            continue

        if rel_script in surface_rel_paths:
            records.append(
                {
                    "script": rel_script,
                    "filename": filename,
                    "line_count": line_count,
                    "mtime_utc": mtime_utc,
                    "wired": True,
                    "surface_hits": [rel_script],
                    "classification": "wiring_surface",
                }
            )
            continue

        for surface_path, txt in surface_texts.items():
            if filename in txt or rel_script in txt:
                hits.append(str(surface_path.relative_to(ROOT)).replace("\\", "/"))

        secondary_hits: list[str] = []
        if not hits:
            for surface_path, txt in secondary_surface_texts.items():
                if filename in txt or rel_script in txt:
                    secondary_hits.append(str(surface_path.relative_to(ROOT)).replace("\\", "/"))

        if hits:
            classification = "wired"
            wired = True
        elif secondary_hits:
            classification = "manual_lane_wired"
            wired = True
            hits = secondary_hits
        elif is_core_script_name(script):
            classification = "unwired_core_candidate"
            wired = False
        else:
            classification = "manual_or_utility"
            wired = False

        records.append(
            {
                "script": rel_script,
                "filename": filename,
                "line_count": line_count,
                "mtime_utc": mtime_utc,
                "wired": wired,
                "surface_hits": hits,
                "classification": classification,
            }
        )

    wired = [r for r in records if r["classification"] == "wired"]
    manual_lane_wired = [r for r in records if r["classification"] == "manual_lane_wired"]
    wiring_surface = [r for r in records if r["classification"] == "wiring_surface"]
    excluded_archive = [r for r in records if r["classification"] == "excluded_archive"]
    unwired_core = [r for r in records if r["classification"] == "unwired_core_candidate"]
    manual_or_utility = [r for r in records if r["classification"] == "manual_or_utility"]
    unwired = [r for r in records if r["classification"] in {"unwired_core_candidate", "manual_or_utility"}]

    return {
        "generated_utc": now_utc(),
        "root": str(ROOT),
        "surface_files": [str(p.relative_to(ROOT)).replace("\\", "/") for p in surface_texts.keys()],
        "counts": {
            "runnable_scripts": len(records),
            "wired": len(wired),
            "manual_lane_wired": len(manual_lane_wired),
            "wiring_surface": len(wiring_surface),
            "excluded_archive": len(excluded_archive),
            "unwired_core_candidates": len(unwired_core),
            "manual_or_utility": len(manual_or_utility),
            "unwired": len(unwired),
        },
        "records": records,
        "manual_lane_wired": manual_lane_wired,
        "wiring_surface": wiring_surface,
        "unwired_core_candidates": unwired_core,
        "manual_or_utility": manual_or_utility,
        "excluded_archive": excluded_archive,
        "unwired": unwired,
    }


def to_markdown(audit: dict, max_rows: int = 200) -> str:
    lines = []
    counts = audit.get("counts", {})
    lines.append("# Institutional Wiring Audit")
    lines.append("")
    lines.append(f"Generated UTC: {audit.get('generated_utc', '')}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Runnable scripts: {counts.get('runnable_scripts', 0)}")
    lines.append(f"- Wired scripts: {counts.get('wired', 0)}")
    lines.append(f"- Manual-lane wired scripts: {counts.get('manual_lane_wired', 0)}")
    lines.append(f"- Wiring surfaces: {counts.get('wiring_surface', 0)}")
    lines.append(f"- Excluded archive/backup scripts: {counts.get('excluded_archive', 0)}")
    lines.append(f"- Unwired core candidates: {counts.get('unwired_core_candidates', 0)}")
    lines.append(f"- Manual or utility scripts: {counts.get('manual_or_utility', 0)}")
    lines.append(f"- Total unwired (core + manual): {counts.get('unwired', 0)}")
    lines.append("")
    lines.append("## Active Wiring Surfaces")
    lines.append("")
    for surf in audit.get("surface_files", []):
        lines.append(f"- {surf}")

    lines.append("")
    lines.append("## Unwired Core Candidates")
    lines.append("")
    lines.append("| Script | Lines | Updated UTC | Classification |")
    lines.append("|---|---:|---|---|")
    for rec in audit.get("unwired_core_candidates", [])[:max_rows]:
        lines.append(
            f"| {rec['script']} | {rec.get('line_count', 0)} | {rec.get('mtime_utc', '')} | {rec['classification']} |"
        )

    manual_rows = max_rows
    lines.append("")
    lines.append("## Manual Or Utility (Unwired)")
    lines.append("")
    lines.append("| Script | Lines | Updated UTC | Classification |")
    lines.append("|---|---:|---|---|")
    for rec in audit.get("manual_or_utility", [])[:manual_rows]:
        lines.append(
            f"| {rec['script']} | {rec.get('line_count', 0)} | {rec.get('mtime_utc', '')} | {rec['classification']} |"
        )

    if len(audit.get("manual_or_utility", [])) > manual_rows:
        lines.append("")
        lines.append(f"... trimmed to first {manual_rows} manual/utility entries")

    if len(audit.get("unwired_core_candidates", [])) > max_rows:
        lines.append("")
        lines.append(f"... trimmed to first {max_rows} core candidate entries")

    return "\n".join(lines) + "\n"


def run(max_rows: int, include_archive: bool, min_lines: int, newest_limit: int) -> tuple[Path, Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    audit_json = OUT / "institutional_wiring_audit.json"
    audit_md = OUT / "institutional_wiring_audit.md"

    runnables = discover_runnable_scripts()

    if min_lines > 0:
        runnables = [p for p in runnables if file_line_count(p) >= min_lines]

    if newest_limit > 0:
        runnables = sorted(runnables, key=lambda p: os.path.getmtime(str(p)), reverse=True)[:newest_limit]

    audit = classify_wiring(runnables, include_archive=include_archive)
    audit_json.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    audit_md.write_text(to_markdown(audit, max_rows=max_rows), encoding="utf-8")
    return audit_json, audit_md


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit runnable scripts for institutional wiring coverage.")
    parser.add_argument("--max-rows", type=int, default=200, help="Maximum unwired rows emitted to markdown report")
    parser.add_argument(
        "--include-archive",
        action="store_true",
        help="Include archive/backup runnable scripts in wiring classification",
    )
    parser.add_argument("--min-lines", type=int, default=0, help="Only include runnable scripts with at least this many lines")
    parser.add_argument(
        "--newest-limit",
        type=int,
        default=0,
        help="Limit audit to N newest runnable scripts after filtering",
    )
    args = parser.parse_args()

    audit_json, audit_md = run(
        max_rows=max(10, int(args.max_rows)),
        include_archive=bool(args.include_archive),
        min_lines=max(0, int(args.min_lines)),
        newest_limit=max(0, int(args.newest_limit)),
    )
    print(f"[AUDIT] wrote {audit_json}")
    print(f"[AUDIT] wrote {audit_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
