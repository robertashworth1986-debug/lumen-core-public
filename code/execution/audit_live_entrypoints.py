from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RAW_PATTERNS = [
    r"live_executor\.py",
    r"python\s+.*live_executor",
    r"py\s+-3\s+.*live_executor",
    r"RUN_LIVE_COMPOUNDING_STACK",
    r"SUPERVISE_LIVE_COMPOUNDING_STACK",
    r"RUN_EXECUTION",
    r"LAUNCH_EVERYTHING",
    r"ARM_REAL_AUTOPILOT",
    r"approval_autofire_daemon",
    r"kraken_live_growth_controller",
    r"order_router",
]

SAFE_PATTERNS = [
    r"safe_live_executor",
    r"order_safety_gate",
    r"live_data_no_orders_gate",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def should_scan(path: Path) -> bool:
    if ".git" in path.parts:
        return False
    if "__pycache__" in path.parts:
        return False
    if path.suffix.lower() not in {".py", ".ps1", ".cmd", ".bat", ".md", ".json", ".yml", ".yaml"}:
        return False
    return True


def classify_line(line: str) -> tuple[bool, bool, list[str]]:
    raw_hits = [p for p in RAW_PATTERNS if re.search(p, line, flags=re.IGNORECASE)]
    safe_hits = [p for p in SAFE_PATTERNS if re.search(p, line, flags=re.IGNORECASE)]
    return bool(raw_hits), bool(safe_hits), raw_hits + safe_hits


def scan(root: Path) -> dict[str, Any]:
    findings = []

    for path in root.rglob("*"):
        if not path.is_file() or not should_scan(path):
            continue

        try:
            rel = path.relative_to(root).as_posix()
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        file_hits = []
        for idx, line in enumerate(text.splitlines(), start=1):
            raw, safe, patterns = classify_line(line)
            if raw or safe:
                file_hits.append({
                    "line": idx,
                    "raw_live_reference": raw,
                    "safe_reference": safe,
                    "patterns": patterns,
                    "text": line[:300],
                })

        if file_hits:
            raw_count = sum(1 for h in file_hits if h["raw_live_reference"])
            safe_count = sum(1 for h in file_hits if h["safe_reference"])
            findings.append({
                "path": rel,
                "raw_count": raw_count,
                "safe_count": safe_count,
                "hits": file_hits[:40],
            })

    raw_files = [f for f in findings if f["raw_count"] > 0]
    safe_files = [f for f in findings if f["safe_count"] > 0]

    return {
        "generated_utc": now_utc(),
        "repo_root": str(root),
        "summary": {
            "files_with_raw_live_references": len(raw_files),
            "files_with_safe_references": len(safe_files),
            "total_files_with_hits": len(findings),
        },
        "meaning": [
            "Raw live references are not automatically unsafe, but they must route through safe_live_executor/order_safety_gate before any live order path is trusted.",
            "Patch 5 only audits and creates a safe launcher; it does not rewrite every legacy script yet.",
            "No broker orders are submitted by this audit.",
        ],
        "findings": findings,
    }


def write_reports(report: dict[str, Any], root: Path) -> tuple[Path, Path]:
    out_dir = root / "out" / "safety_reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "LATEST_live_entrypoint_audit.json"
    md_path = out_dir / "LATEST_live_entrypoint_audit.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    lines = []
    lines.append("# LumenCore Raw Live Entrypoint Audit")
    lines.append("")
    lines.append(f"- Generated UTC: `{report['generated_utc']}`")
    lines.append(f"- Repo root: `{report['repo_root']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for k, v in report["summary"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Meaning")
    lines.append("")
    for item in report["meaning"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Files With Hits")
    lines.append("")

    for finding in report["findings"]:
        lines.append(f"### `{finding['path']}`")
        lines.append("")
        lines.append(f"- Raw live references: `{finding['raw_count']}`")
        lines.append(f"- Safe references: `{finding['safe_count']}`")
        lines.append("")
        lines.append("| Line | Raw | Safe | Text |")
        lines.append("|---:|---|---|---|")
        for hit in finding["hits"][:20]:
            raw = "YES" if hit["raw_live_reference"] else "NO"
            safe = "YES" if hit["safe_reference"] else "NO"
            text = hit["text"].replace("|", "\\|")
            lines.append(f"| {hit['line']} | {raw} | {safe} | `{text}` |")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    root = repo_root()
    report = scan(root)
    json_path, md_path = write_reports(report, root)

    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    print(f"JSON_REPORT={json_path}")
    print(f"MD_REPORT={md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
