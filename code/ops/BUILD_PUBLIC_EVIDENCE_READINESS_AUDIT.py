from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "ops"
DOCS = ROOT / "docs"

JSON_OUT = OUT / "public_evidence_readiness_audit_latest.json"
MD_OUT = DOCS / "PUBLIC_EVIDENCE_READINESS_AUDIT_2026-06-19.md"

PUBLIC_EVIDENCE_RUNS = [
    ROOT / "evidence" / "geometry_championship_v1" / "20260619T_GEOMETRY_READINESS_V2_EXPANDED",
]

PUBLIC_DOCS = [
    ROOT / "docs" / "DICE_PRELIMINARY_BENCHMARK_2026-06-13.md",
    ROOT / "docs" / "HARBOR_SENTINEL_VALIDATION_2026-06-13.md",
    ROOT / "docs" / "LUMAUNIVERSE_RESEARCH_EVIDENCE_AUDIT_2026-06-18.md",
    ROOT / "evidence" / "agency_alignment_memo.md",
]

RISKY_PHRASES = [
    "field validated",
    "operationally validated",
    "operational defense performance",
    "ssds integration",
    "cmmc certified",
    "classified-environment performance",
    "trading profit",
    "guaranteed award",
    "guaranteed superior",
    "demo site committed",
    "universal edge",
    "universal superiority",
]

NEGATION_MARKERS = (
    "do not",
    "does not",
    "did not",
    "not ",
    "no ",
    "without ",
    "never ",
    "exclude",
    "outside",
    "not establish",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_manifest(run_dir: Path) -> dict[str, Any]:
    manifest = run_dir / "manifest.sha256.json"
    result: dict[str, Any] = {
        "run_dir": rel(run_dir),
        "manifest": rel(manifest),
        "exists": manifest.exists(),
        "matched": 0,
        "expected": 0,
        "mismatches": [],
    }
    if not manifest.exists():
        result["mismatches"].append("missing manifest.sha256.json")
        return result

    data = load_json(manifest)
    files = data.get("files", {}) if isinstance(data, dict) else {}
    result["schema"] = data.get("schema") if isinstance(data, dict) else None
    result["generated_utc"] = data.get("generated_utc") if isinstance(data, dict) else None
    result["expected"] = len(files)

    for name, expected in files.items():
        target = run_dir / name
        if not target.exists():
            result["mismatches"].append(f"{name}: missing")
            continue
        actual_bytes = target.stat().st_size
        actual_sha = sha256_file(target)
        expected_bytes = int(expected.get("bytes", -1))
        expected_sha = str(expected.get("sha256", ""))
        if actual_bytes == expected_bytes and actual_sha == expected_sha:
            result["matched"] += 1
        else:
            result["mismatches"].append(
                f"{name}: expected {expected_bytes}/{expected_sha}, got {actual_bytes}/{actual_sha}"
            )
    return result


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def positive_claim_hits(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return [{"line": None, "phrase": "missing", "context": rel(path)}]

    hits = []
    lines = read_text(path).lower().splitlines()
    for idx, line in enumerate(lines):
        prior = " ".join(lines[max(idx - 2, 0):idx])
        context = f"{prior} {line}".strip()
        for phrase in RISKY_PHRASES:
            if phrase not in line:
                continue
            if any(marker in context for marker in NEGATION_MARKERS):
                continue
            hits.append({"line": idx + 1, "phrase": phrase, "context": line.strip()[:220]})
    return hits


def doc_status(path: Path) -> dict[str, Any]:
    hits = positive_claim_hits(path)
    exists = path.exists()
    return {
        "path": rel(path),
        "exists": exists,
        "bytes": path.stat().st_size if exists else None,
        "positive_claim_hits": hits,
        "ok": exists and not hits,
    }


def build_audit() -> dict[str, Any]:
    manifests = [verify_manifest(path) for path in PUBLIC_EVIDENCE_RUNS]
    docs = [doc_status(path) for path in PUBLIC_DOCS]
    blockers = []
    for row in manifests:
        blockers.extend(f"{row['run_dir']}: {item}" for item in row["mismatches"])
    for row in docs:
        if not row["exists"]:
            blockers.append(f"{row['path']}: missing")
        for hit in row["positive_claim_hits"]:
            blockers.append(f"{row['path']}:{hit['line']}: unbounded claim phrase `{hit['phrase']}`")

    return {
        "generated_utc": now_utc(),
        "schema": "public_evidence_readiness_audit_v1",
        "posture": "PUBLIC_SAFE_READY" if not blockers else "PUBLIC_SAFE_BLOCKED",
        "summary": {
            "manifests_matched": sum(row["matched"] for row in manifests),
            "manifests_expected": sum(row["expected"] for row in manifests),
            "docs_checked": len(docs),
            "blockers": len(blockers),
        },
        "manifests": manifests,
        "docs": docs,
        "blockers": blockers,
        "claim_boundary": (
            "Public evidence may show reproducible synthetic benchmarks, manifest integrity, "
            "and candidate-family governance. It must not imply portal submission readiness, "
            "field validation, classified performance, CMMC certification, partner commitment, "
            "or trading profit."
        ),
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Public Evidence Readiness Audit",
        "",
        f"Generated UTC: {audit['generated_utc']}",
        "",
        f"Posture: {audit['posture']}",
        "",
        "## Summary",
        "",
        f"- Manifest hashes matched: {audit['summary']['manifests_matched']}/{audit['summary']['manifests_expected']}",
        f"- Public docs checked: {audit['summary']['docs_checked']}",
        f"- Blockers: {audit['summary']['blockers']}",
        "",
        "## Claim Boundary",
        "",
        audit["claim_boundary"],
        "",
        "## Evidence Manifests",
        "",
    ]
    for row in audit["manifests"]:
        lines.append(f"- {row['run_dir']}: {row['matched']}/{row['expected']} matched")
    lines.extend(["", "## Public Documents", ""])
    for row in audit["docs"]:
        lines.append(f"- {row['path']}: {'ok' if row['ok'] else 'review'}")
    lines.extend(["", "## Blockers", ""])
    if audit["blockers"]:
        lines.extend(f"- {item}" for item in audit["blockers"])
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    audit = build_audit()
    JSON_OUT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    MD_OUT.write_text(render_markdown(audit), encoding="utf-8")
    print(
        json.dumps(
            {
                "posture": audit["posture"],
                "blockers": len(audit["blockers"]),
                "json": rel(JSON_OUT),
                "md": rel(MD_OUT),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
