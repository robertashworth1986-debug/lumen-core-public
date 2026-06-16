from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


IGNORE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", ".next", ".cache"
}

DATA_EXTS = {".csv", ".txt", ".json", ".jsonl", ".parquet", ".md"}
SCRIPT_EXTS = {".py", ".ps1"}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def candidate_roots(repo: Path) -> list[tuple[str, Path]]:
    roots = [
        ("repo", repo),
        ("C_LumenCore", Path("C:/LumenCore")),
        ("C_LumaTrader", Path("C:/LumaTrader")),
        ("C_LumaTraderLivePipeline", Path("C:/LumaTraderLivePipeline")),
        ("C_LumaTrader_Institutional", Path("C:/LumaTrader/INSTITUTIONAL_STACK_V2")),
        ("C_LumenCore_Bridge", Path("C:/LumenCore/ai_workflow_bridge")),
        ("User_LumenCoreAI", Path.home() / "LumenCoreAI"),
    ]
    return [(label, root) for label, root in roots if root.exists()]


def safe_rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except Exception:
        return path.name


def file_preview_stats(path: Path) -> dict[str, Any]:
    stat = path.stat()
    line_count = None
    try:
        if path.suffix.lower() in {".csv", ".txt", ".md", ".json", ".jsonl"} and stat.st_size <= 5_000_000:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                line_count = sum(1 for _ in f)
    except Exception:
        line_count = None

    return {
        "name": path.name,
        "suffix": path.suffix.lower(),
        "size_bytes": stat.st_size,
        "line_count_if_text": line_count,
        "sha256": sha256_file(path),
    }


def walk_limited(root: Path, max_files: int = 25000):
    seen = 0
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        cur = Path(current)

        for d in dirs:
            dpath = cur / d
            low = dpath.name.lower()
            if "master_universe" in low or "trackcast" in low:
                yield "dir", dpath
                seen += 1
                if seen >= max_files:
                    return

        for f in files:
            path = cur / f
            seen += 1
            if seen >= max_files:
                return
            yield "file", path


def discover(repo: Path) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = {
        "master_universe_dirs": [],
        "latest_files": [],
        "anom_files": [],
        "trackcast_data_files": [],
        "trackcast_scripts": [],
        "regime_shift_scripts": [],
        "anomaly_scripts": [],
        "forecast_scripts": [],
    }

    for root_label, root in candidate_roots(repo):
        for kind, path in walk_limited(root):
            low = path.as_posix().lower()
            name = path.name.lower()

            if kind == "dir":
                if "master_universe" in name:
                    try:
                        child_count = len([x for x in path.iterdir()])
                    except Exception:
                        child_count = None
                    buckets["master_universe_dirs"].append({
                        "root_label": root_label,
                        "relative_path": safe_rel(root, path),
                        "child_count": child_count,
                    })
                continue

            suffix = path.suffix.lower()

            if name == "latest.txt" or name.startswith("latest."):
                if suffix in DATA_EXTS:
                    item = {"root_label": root_label, "relative_path": safe_rel(root, path)}
                    item.update(file_preview_stats(path))
                    buckets["latest_files"].append(item)

            if "anom" in low and suffix in DATA_EXTS:
                item = {"root_label": root_label, "relative_path": safe_rel(root, path)}
                item.update(file_preview_stats(path))
                buckets["anom_files"].append(item)

            if "trackcast" in low and suffix in DATA_EXTS:
                item = {"root_label": root_label, "relative_path": safe_rel(root, path)}
                item.update(file_preview_stats(path))
                buckets["trackcast_data_files"].append(item)

            if "trackcast" in low and suffix in SCRIPT_EXTS:
                item = {"root_label": root_label, "relative_path": safe_rel(root, path)}
                item.update(file_preview_stats(path))
                buckets["trackcast_scripts"].append(item)

            if "regime_shift" in name and suffix in SCRIPT_EXTS:
                item = {"root_label": root_label, "relative_path": safe_rel(root, path)}
                item.update(file_preview_stats(path))
                buckets["regime_shift_scripts"].append(item)

            if "anomaly" in name and suffix in SCRIPT_EXTS:
                item = {"root_label": root_label, "relative_path": safe_rel(root, path)}
                item.update(file_preview_stats(path))
                buckets["anomaly_scripts"].append(item)

            if "forecast" in name and suffix in SCRIPT_EXTS:
                item = {"root_label": root_label, "relative_path": safe_rel(root, path)}
                item.update(file_preview_stats(path))
                buckets["forecast_scripts"].append(item)

    for key in buckets:
        buckets[key] = buckets[key][:40]

    return buckets


def score_discovery(buckets: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    score = 0
    reasons = []

    if buckets["master_universe_dirs"]:
        score += 3
        reasons.append("master_universe directory discovered")

    if buckets["latest_files"]:
        score += 2
        reasons.append("latest data file discovered")

    if buckets["anom_files"]:
        score += 2
        reasons.append("anomaly data/source discovered")

    if buckets["trackcast_data_files"]:
        score += 2
        reasons.append("TrackCast data artifact discovered")

    if buckets["regime_shift_scripts"]:
        score += 1
        reasons.append("regime shift script discovered")

    if buckets["anomaly_scripts"]:
        score += 1
        reasons.append("anomaly script discovered")

    if buckets["forecast_scripts"]:
        score += 1
        reasons.append("forecast script discovered")

    passed = score >= 4

    return {
        "score": score,
        "pass": passed,
        "reasons": reasons,
        "meaning": (
            "Existing TrackCast stack is discoverable and benchmark-ready at the structural level."
            if passed
            else "Existing TrackCast stack was not sufficiently discoverable from known roots."
        )
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = []
    lines.append("# TrackCast Existing Stack Benchmark")
    lines.append("")
    lines.append("Generated UTC: " + report["generated_utc"])
    lines.append("")
    lines.append("## Result")
    lines.append("")
    lines.append("- Pass: " + str(report["score"]["pass"]))
    lines.append("- Score: " + str(report["score"]["score"]))
    lines.append("- Meaning: " + report["score"]["meaning"])
    lines.append("")
    lines.append("## Reasons")
    lines.append("")
    for reason in report["score"]["reasons"]:
        lines.append("- " + reason)

    lines.append("")
    lines.append("## Discovery Buckets")
    lines.append("")
    for bucket, items in report["discovery"].items():
        lines.append("### " + bucket)
        lines.append("")
        lines.append("- Count shown: " + str(len(items)))
        lines.append("")
        for item in items[:20]:
            lines.append("- root_label=" + str(item.get("root_label")) + " path=" + str(item.get("relative_path")) + " size=" + str(item.get("size_bytes")) + " sha256=" + str(item.get("sha256")))
        lines.append("")

    lines.append("## Reviewer-Safe Claim")
    lines.append("")
    lines.append("TrackCast existing-stack discovery verifies that local stack artifacts and/or scripts are present without printing secrets or raw data. This supports integration readiness, while the benchmark lane still needs direct algorithmic performance evidence for production claims.")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    repo = repo_root()
    out = repo / "out" / "grant_evidence"
    out.mkdir(parents=True, exist_ok=True)

    discovery = discover(repo)
    score = score_discovery(discovery)

    report = {
        "generated_utc": now_utc(),
        "repo_root_label": "repo",
        "secret_values_in_report": False,
        "discovery": discovery,
        "score": score,
    }

    json_path = out / "LATEST_trackcast_existing_stack_benchmark.json"
    md_path = out / "LATEST_trackcast_existing_stack_benchmark.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(report, md_path)

    print(json.dumps({
        "pass": score["pass"],
        "score": score["score"],
        "reasons": score["reasons"],
        "json_report": str(json_path),
        "md_report": str(md_path),
    }, indent=2))

    return 0 if score["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
