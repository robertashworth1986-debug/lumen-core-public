from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)([^\\s\\\"',]+)"),
    re.compile(r"(?i)(secret\s*[:=]\s*)([^\\s\\\"',]+)"),
    re.compile(r"(?i)(token\s*[:=]\s*)([^\\s\\\"',]+)"),
    re.compile(r"(?i)(password\s*[:=]\s*)([^\\s\\\"',]+)")
]

ENV_NAMES = [
    "OPENAI_API_KEY",
    "SAM_API_KEY",
    "SAM_GOV_API_KEY",
    "GRANTS_GOV_API_KEY",
    "GRANTS_API_KEY",
    "UEI",
    "CAGE_CODE",
    "CAGE",
    "FRED_API_KEY",
    "EIA_API_KEY",
    "KRAKEN_API_KEY",
    "KRAKEN_API_SECRET"
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


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


def redact(text: str) -> str:
    out = text or ""
    out = re.sub(r"sk-[A-Za-z0-9_\-]{20,}", "[REDACTED_OPENAI_KEY]", out)
    for pat in SECRET_PATTERNS[1:]:
        out = pat.sub(lambda m: m.group(1) + "[REDACTED]", out)
    return out


def run_py(repo: Path, rel: str, timeout_seconds: int = 120) -> dict[str, Any]:
    path = repo / rel
    base = {
        "path": rel,
        "exists": path.exists(),
        "sha256": sha256_file(path),
        "ran": False,
        "returncode": None,
        "elapsed_seconds": None,
        "timeout": False,
        "stdout_tail": "",
        "stderr_tail": ""
    }

    if not path.exists():
        return base

    if path.suffix.lower() != ".py":
        return base

    start = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(repo),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds
        )
        base.update({
            "ran": True,
            "returncode": proc.returncode,
            "elapsed_seconds": round(time.time() - start, 3),
            "stdout_tail": redact((proc.stdout or "")[-6000:]),
            "stderr_tail": redact((proc.stderr or "")[-6000:])
        })
    except subprocess.TimeoutExpired as exc:
        base.update({
            "ran": True,
            "elapsed_seconds": timeout_seconds,
            "timeout": True,
            "stdout_tail": redact(exc.stdout if isinstance(exc.stdout, str) else ""),
            "stderr_tail": redact(exc.stderr if isinstance(exc.stderr, str) else "")
        })
    except Exception as exc:
        base.update({
            "ran": True,
            "elapsed_seconds": round(time.time() - start, 3),
            "stderr_tail": redact(repr(exc))
        })

    return base


def env_audit(repo: Path) -> dict[str, Any]:
    found_env_files = []
    candidates = [
        repo / ".env",
        repo / "config" / ".env",
        repo / "config" / "luma_live_keys.env",
        Path("C:/LumaTrader/INSTITUTIONAL_STACK_V2/config/luma_live_keys.env"),
        Path("C:/LumenCore/ai_workflow_bridge/.env")
    ]

    seen_names = set()

    for p in candidates:
        if p.exists():
            found_env_files.append(str(p))
            try:
                for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                    if "=" in line and not line.strip().startswith("#"):
                        seen_names.add(line.split("=", 1)[0].strip())
            except Exception:
                pass

    return {
        "environment_variables_present_no_values": {name: bool(os.environ.get(name)) for name in ENV_NAMES},
        "local_env_files_found_no_values": found_env_files,
        "variable_names_seen_in_local_env_files_no_values": sorted([x for x in seen_names if x])
    }


def premium_catalog(repo: Path) -> dict[str, Any]:
    words = [
        "premium", "grant", "evidence", "benchmark", "validation",
        "mission", "dice", "harbor", "sentinel", "weave", "trackcast",
        "federal", "gov", "proof", "coherence", "investor"
    ]

    items = []
    for p in repo.rglob("*"):
        if not p.is_file():
            continue
        if ".git" in p.parts or "__pycache__" in p.parts:
            continue
        rel = p.relative_to(repo).as_posix()
        low = rel.lower()
        if p.suffix.lower() in {".py", ".md", ".json", ".ps1", ".html", ".csv"} and any(w in low for w in words):
            try:
                size = p.stat().st_size
            except Exception:
                size = 0
            items.append({
                "path": rel,
                "size_bytes": size,
                "sha256": sha256_file(p)
            })

    items = sorted(items, key=lambda x: x["size_bytes"], reverse=True)
    return {
        "count": len(items),
        "top_artifacts": items[:120]
    }


def build_report(repo: Path) -> dict[str, Any]:
    plan_path = repo / "config" / "grant_evidence_benchmark_plan.json"
    plan = load_json(plan_path, {})

    lanes = []
    for lane in plan.get("benchmark_lanes", []):
        results = []
        for rel in lane.get("candidate_scripts", []):
            results.append(run_py(repo, rel))

        lanes.append({
            "lane": lane.get("lane"),
            "claim_type": lane.get("claim_type"),
            "candidate_count": len(lane.get("candidate_scripts", [])),
            "existing_count": len([r for r in results if r["exists"]]),
            "ran_count": len([r for r in results if r["ran"]]),
            "passed_count": len([r for r in results if r["ran"] and r["returncode"] == 0]),
            "failed_count": len([r for r in results if r["ran"] and r["returncode"] not in [0, None]]),
            "timeout_count": len([r for r in results if r["timeout"]]),
            "results": results
        })

    blockers = []
    wins = list(plan.get("known_not_blocking", []))

    for lane in lanes:
        if lane["existing_count"] == 0:
            blockers.append(lane["lane"] + ": no expected benchmark scripts found")
        elif lane["passed_count"] == 0:
            blockers.append(lane["lane"] + ": scripts exist but no passing benchmark yet")
        else:
            wins.append(lane["lane"] + ": " + str(lane["passed_count"]) + " command(s) passed")

    return {
        "generated_utc": now_utc(),
        "repo_root": str(repo),
        "plan_sha256": sha256_file(plan_path),
        "live_trading_allowed": False,
        "secret_values_in_report": False,
        "lanes": lanes,
        "wins_not_blocking": wins,
        "detected_blockers": blockers,
        "likely_remaining_blockers": plan.get("likely_remaining_blockers", []),
        "env_audit_no_values": env_audit(repo),
        "premium_catalog": premium_catalog(repo)
    }


def markdown(report: dict[str, Any]) -> str:
    lines = []
    lines.append("# LumenCore Grant Evidence Benchmark Lab")
    lines.append("")
    lines.append("Generated UTC: " + report["generated_utc"])
    lines.append("")
    lines.append("Live trading allowed: false")
    lines.append("Secret values in report: false")
    lines.append("")
    lines.append("## Executive Result")
    lines.append("")
    lines.append("This report builds a reproducible grant evidence package with benchmark lanes, SHA-256 hashes, blocker audit, and reviewer-safe language.")
    lines.append("")
    lines.append("## Benchmark Lane Summary")
    lines.append("")
    lines.append("| Lane | Existing | Ran | Passed | Failed | Timed Out | Claim Type |")
    lines.append("|---|---:|---:|---:|---:|---:|---|")
    for lane in report["lanes"]:
        claim = str(lane["claim_type"]).replace("|", "\\|")
        lines.append("| " + str(lane["lane"]) + " | " + str(lane["existing_count"]) + " | " + str(lane["ran_count"]) + " | " + str(lane["passed_count"]) + " | " + str(lane["failed_count"]) + " | " + str(lane["timeout_count"]) + " | " + claim + " |")

    lines.append("")
    lines.append("## Wins / Not Blocking")
    lines.append("")
    for item in report["wins_not_blocking"]:
        lines.append("- " + item)

    lines.append("")
    lines.append("## Detected Blockers")
    lines.append("")
    if report["detected_blockers"]:
        for item in report["detected_blockers"]:
            lines.append("- " + item)
    else:
        lines.append("- None detected in expected lanes.")

    lines.append("")
    lines.append("## Likely Remaining Grant Blockers")
    lines.append("")
    for item in report["likely_remaining_blockers"]:
        lines.append("- " + item)

    lines.append("")
    lines.append("## Env / Registry Readiness, No Values")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(report["env_audit_no_values"], indent=2, sort_keys=True))
    lines.append("```")

    lines.append("")
    lines.append("## Premium / Grant Artifact Catalog")
    lines.append("")
    lines.append("Artifacts found: " + str(report["premium_catalog"]["count"]))
    lines.append("")
    for item in report["premium_catalog"]["top_artifacts"][:50]:
        lines.append("- " + item["path"] + " | size " + str(item["size_bytes"]) + " | sha256 " + str(item["sha256"]))

    lines.append("")
    lines.append("## Detailed Benchmark Results")
    lines.append("")
    for lane in report["lanes"]:
        lines.append("### " + str(lane["lane"]))
        lines.append("")
        for result in lane["results"]:
            lines.append("#### " + result["path"])
            lines.append("- Exists: " + str(result["exists"]))
            lines.append("- SHA-256: " + str(result["sha256"]))
            lines.append("- Ran: " + str(result["ran"]))
            lines.append("- Return code: " + str(result["returncode"]))
            lines.append("- Timeout: " + str(result["timeout"]))
            if result["stdout_tail"]:
                lines.append("")
                lines.append("Output tail:")
                lines.append("```text")
                lines.append(result["stdout_tail"][-2200:])
                lines.append("```")
            if result["stderr_tail"]:
                lines.append("")
                lines.append("Error tail:")
                lines.append("```text")
                lines.append(result["stderr_tail"][-2200:])
                lines.append("```")
            lines.append("")

    lines.append("## Reviewer-Safe Claim Language")
    lines.append("")
    lines.append("Use: preliminary benchmark, bounded synthetic validation, reproducible evidence package, prototype safety-gated runtime, measured candidate lanes.")
    lines.append("")
    lines.append("Avoid: guaranteed, undeniable, proves superiority, fully autonomous live trading, risk-free.")
    lines.append("")
    lines.append("## Next Work")
    lines.append("")
    lines.append("1. Turn passing lanes into agency-specific evidence cards.")
    lines.append("2. Add missing benchmark scripts where lanes do not pass.")
    lines.append("3. Map budget and milestones to each grant.")
    lines.append("4. Add pilot letters or support validation.")
    lines.append("5. Keep live trading separate from grant science claims.")
    return "\n".join(lines)


def main() -> int:
    repo = root()
    out = repo / "out" / "grant_evidence"
    out.mkdir(parents=True, exist_ok=True)

    report = build_report(repo)
    json_path = out / "LATEST_grant_evidence_benchmark_lab.json"
    md_path = out / "LATEST_grant_evidence_benchmark_lab.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")

    summary = {
        "generated_utc": report["generated_utc"],
        "lanes": [
            {
                "lane": lane["lane"],
                "existing": lane["existing_count"],
                "ran": lane["ran_count"],
                "passed": lane["passed_count"],
                "failed": lane["failed_count"],
                "timeout": lane["timeout_count"]
            }
            for lane in report["lanes"]
        ],
        "detected_blockers": report["detected_blockers"],
        "premium_artifact_count": report["premium_catalog"]["count"]
    }

    print(json.dumps(summary, indent=2, sort_keys=True))
    print("JSON_REPORT=" + str(json_path))
    print("MD_REPORT=" + str(md_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
